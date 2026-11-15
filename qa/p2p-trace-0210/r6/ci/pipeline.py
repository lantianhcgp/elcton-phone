#!/usr/bin/env python3
"""R6 explicit-action CLI. Default/help/self-test NEVER dispatch. No push/build/ADB."""
import argparse
import datetime
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time
from urllib.parse import quote
import zipfile
from r6_common import (ROOT, HERE, REPO, BRANCH, api, pages, require, sha40, run_id,
    read_json, save, new_out, digest, inventory, exact_readback, select_asset, zip_members, archive_readback)
sys.dont_write_bytecode = True


def branch_head(sha):
    sha40(sha)
    branch = api('/branches/' + quote(BRANCH, safe=''))
    require(branch['commit']['sha'] == sha, 'Remote diag branch is not exact reviewed workflow head')
    return branch


def reviewed(args):
    closure = read_json(args.review/'dual-closure.json')
    require(closure['passed'] is True and closure['axes'], 'Actual dual review not passed')
    for axis in closure['axes']:
        require(digest(args.review/(axis['axis']+'-raw.txt')) == axis['raw_sha256'], 'Review raw fingerprint mismatch')
    manifest = read_json(args.review/'reviewed-manifest.json')
    require(manifest, 'Empty reviewed source manifest')
    for path, expected in manifest.items():
        raw = subprocess.check_output(['git','show',args.sha+':'+path],cwd=ROOT,timeout=30)
        import hashlib
        require(hashlib.sha256(raw).hexdigest()==expected, 'Committed reviewed input differs: '+path)
    return {'closure':closure,'manifest':manifest}


def dispatch(args):
    """Only called through the literal dispatch-build or dispatch-ui subcommand."""
    workflow = 'build.yml' if args.command=='dispatch-build' else 'ui-smoke.yml'
    branch = branch_head(args.sha)
    inputs = {}
    proof = reviewed(args) if workflow=='build.yml' else None
    if workflow=='ui-smoke.yml':
        sha40(args.build_sha); run_id(args.build_run)
        build = read_json(args.build_receipt)
        require(build['passed'] is True and build['source_sha']==args.build_sha and build['build_run']==args.build_run, 'Actual binary/Gradle build receipt differs')
        bound = exact_readback(args.build_run,args.build_sha,'build.yml',True)
        require(bound['run-api']['conclusion']=='success', 'Exact build run is RED')
        if args.suite=='full':
            require(args.previous_registration is not None, 'Register diagnostics BEFORE second/full dispatch')
            previous = read_json(args.previous_registration)
            require(previous['inputs']=={'build_run':args.build_run,'build_sha':args.build_sha,
                    'api_level':'33','navigation_mode':'three-button','qa_suite':'diagnostics'}, 'Previous registered diagnostics inputs differ')
            require(previous['workflow_sha']==args.sha and previous['run']['id'], 'Previous registered workflow head differs')
        inputs={'build_run':args.build_run,'build_sha':args.build_sha,'api_level':'33',
                'navigation_mode':'three-button','qa_suite':args.suite}
    before = pages('/actions/workflows/'+workflow+'/runs?head_sha='+args.sha+'&event=workflow_dispatch', 'workflow_runs')
    ids={r['id'] for r in before['workflow_runs']}
    out=new_out(args.out)
    save(out,'before-runs.json',before)
    save(out,'dispatch-intent.json',{'workflow':workflow,'workflow_sha':args.sha,'branch':BRANCH,'inputs':inputs,'review':proof})
    # Explicit POST; gh owns authentication. Credentials and redirect URLs never saved.
    payload={'ref':BRANCH,'inputs':inputs}
    api('/actions/workflows/'+workflow+'/dispatches',payload)
    save(out,'dispatch-accepted.json',{'posted':True,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),
                                    'scope':'POST accepted, not run registered or success'})
    end=time.monotonic()+120
    while True:
        after=pages('/actions/workflows/'+workflow+'/runs?head_sha='+args.sha+'&event=workflow_dispatch','workflow_runs')
        new=[r for r in after['workflow_runs'] if r['id'] not in ids]
        if len(new)>1:
            save(out,'ambiguous-runs.json',after)
            raise AssertionError('Ambiguous new runs; preserve intent and DO NOT repeat dispatch or choose latest')
        if new:
            r=api('/actions/runs/'+str(new[0]['id']))
            require(r['head_sha']==args.sha and r['head_branch']==BRANCH and r['event']=='workflow_dispatch'
                    and r['path']=='.github/workflows/'+workflow, 'Exact registered workflow mismatch')
            branch_head(args.sha)
            registration={'run':r,'inputs':inputs,'workflow_sha':args.sha,'workflow':workflow,
                          'before_ids':sorted(ids),'scope':'Distinct exact run registration, NOT execution PASS'}
            save(out,'registered.json',registration)
            print(json.dumps({'registered_run':r['id'],'workflow_sha':args.sha,'inputs':inputs,'receipt':str(out/'registered.json')}))
            return
        if time.monotonic()>end:
            save(out,'registration-timeout.json',after)
            raise AssertionError('Registration timeout; read back this saved intent, NEVER re-dispatch blindly')
        time.sleep(3)


def readback(args, wait=False):
    workflow='build.yml' if args.kind=='build' else 'ui-smoke.yml'
    out=new_out(args.out); start=time.monotonic(); polls=[]
    while True:
        row=exact_readback(args.run,args.sha,workflow)
        polls.append({'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':row['run-api']['status'],
                      'conclusion':row['run-api']['conclusion'],'run_attempt':row['run-api']['run_attempt']})
        if not wait or row['run-api']['status']=='completed' or time.monotonic()-start>=args.seconds: break
        time.sleep(10)
    for k,v in row.items(): save(out,k+'.json',v)
    save(out,'polls.json',polls)
    print(json.dumps({'run':args.run,'head':args.sha,'attempt':row['run-api']['run_attempt'],
                      'status':row['run-api']['status'],'conclusion':row['run-api']['conclusion'],
                      'artifacts':row['artifacts']['total_count'],'out':str(out)}))
    if wait: return 0 if row['run-api']['status']=='completed' and row['run-api']['conclusion']=='success' else 1
    return 0


def fetch(args):
    workflow='build.yml' if args.kind=='build' else 'ui-smoke.yml'
    sha40(args.source); row=exact_readback(args.run,args.sha,workflow,True)
    if args.kind=='build':
        require(args.source==args.sha and row['run-api']['conclusion']=='success','Build exact source/conclusion mismatch')
    name=('android-probe-' if args.kind=='build' else 'android-ui-')+args.sha
    asset=select_asset(row['artifacts']['artifacts'],row['attempt-api'],name,args.run,args.sha)
    # Check extraction budget BEFORE downloading; ZIP expansion cannot be predicted by compressed size alone.
    out=new_out(args.out)
    for k,v in row.items(): save(out,k+'.json',v)
    normalized={'databaseId':int(args.run),'headSha':args.sha,'headBranch':BRANCH,
                'status':row['run-api']['status'],'conclusion':row['run-api']['conclusion'],
                'event':row['run-api']['event'],'url':row['run-api']['html_url']}
    save(out,'run-exact.json' if args.kind=='build' else 'run.json',normalized)
    save(out,'exact-artifact.json',{'run_id':args.run,'run_attempt':row['run-api']['run_attempt'],'artifact':asset})
    require(shutil.disk_usage(out).free > asset['size_in_bytes']+128*1024*1024, 'Not enough free space for ZIP; use remote evidence host')
    archive=out/'artifact-original.zip'
    with archive.open('xb') as stream:
        result=subprocess.run(['gh','api','repos/'+REPO+'/actions/artifacts/'+str(asset['id'])+'/zip'],
                              stdout=stream,stderr=subprocess.PIPE,timeout=600,cwd=ROOT)
    require(result.returncode==0,'gh artifact download failed; token/redirect not printed; exit='+str(result.returncode))
    require(archive.stat().st_size==asset['size_in_bytes'],'Remote artifact byte size mismatch')
    if asset.get('digest'): require(asset['digest']=='sha256:'+digest(archive),'Remote artifact SHA mismatch')
    with zipfile.ZipFile(archive) as z:
        members=zip_members(z)
        expanded=sum(v.file_size for v in members.values() if not v.is_dir())
        require(shutil.disk_usage(out).free > expanded+128*1024*1024,'Not enough free space for full artifact; ZIP retained, DO NOT copy old tree')
        for name,item in members.items():
            if item.is_dir(): continue
            target=out/'artifact'/name; target.parent.mkdir(parents=True,exist_ok=True)
            with z.open(item) as source, target.open('xb') as stream:
                shutil.copyfileobj(source,stream,length=1024*1024)
    checked=archive_readback(archive,out/'artifact')
    save(out,'zip-readback.json',checked)
    if args.kind=='build':
        pins=list((out/'artifact').rglob('source-sha.txt'))
        require(len(pins)==1 and pins[0].read_bytes()==(args.source+'\n').encode(),'Exact literal build source-sha.txt mismatch')
        require(len(list((out/'artifact').rglob('elcton-phone-probe.apk')))==1 and
                len(list((out/'artifact').rglob('elcton-ui-tests.apk')))==1,'Missing/duplicate signed main/test APK')
    fresh=api('/actions/runs/'+args.run)
    require(fresh['run_attempt']==row['run-api']['run_attempt'] and fresh['status']=='completed', 'Run rerun during fetch; exact attempt changed')
    save(out,'post-fetch-run-api.json',fresh)
    rows=inventory(out)
    save(out,'inventory.json',{'fetched':True,'run':args.run,'source_sha':args.source,'workflow_sha':args.sha,
         'run_attempt':row['run-api']['run_attempt'],'artifact_id':asset['id'],'conclusion':row['run-api']['conclusion'],'inventory':rows})
    print(json.dumps({'fetched':True,'run':args.run,'attempt':row['run-api']['run_attempt'],'artifact_id':asset['id'],
                      'zip_bytes':checked['archive_bytes'],'zip_sha256':checked['archive_sha256'],'files':len(rows),'out':str(out)}))


def main():
    if sys.argv[1:]==['--self-test']:
        import self_test
        return self_test.main()
    p=argparse.ArgumentParser(description=__doc__)
    s=p.add_subparsers(dest='command',required=True)
    build=s.add_parser('dispatch-build'); build.add_argument('--review',type=Path,required=True)
    ui=s.add_parser('dispatch-ui'); ui.add_argument('--suite',choices=('diagnostics','full'),required=True)
    ui.add_argument('--build-run',required=True); ui.add_argument('--build-sha',required=True)
    ui.add_argument('--build-receipt',type=Path,required=True); ui.add_argument('--previous-registration',type=Path)
    for x in (build,ui): x.add_argument('--sha',required=True); x.add_argument('--out',type=Path,required=True)
    for cmd in ('readback','wait','fetch'):
        x=s.add_parser(cmd); x.add_argument('--run',required=True); x.add_argument('--sha',required=True)
        x.add_argument('--kind',choices=('build','android'),required=True); x.add_argument('--out',type=Path,required=True)
        if cmd=='wait': x.add_argument('--seconds',type=int,default=1800)
        if cmd=='fetch': x.add_argument('--source',required=True)
    a=p.parse_args(); sha40(a.sha)
    if a.command.startswith('dispatch-'): dispatch(a); return 0
    run_id(a.run)
    if a.command=='fetch': fetch(a); return 0
    return readback(a,a.command=='wait')

if __name__=='__main__':
    raise SystemExit(main())
