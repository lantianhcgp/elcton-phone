#!/usr/bin/env python3
"""Read-only exact R10 binding; writes only new reviewer evidence in this directory."""
import ast
import datetime
import difflib
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path('/data/data/com.termux/files/home/elcton-phone-release-029-20261114')
BASE = ROOT / 'qa/release-029/evidence/resume-1720'
F = BASE / 'final-review-r10-fourth'
OUT = F / 'spec-probes'
PIN = 'e034de2f924dd6d96e31caa8e5a62e52474de718'
HEAD = '44df9d0fd36aecaa22613e9aa73c5c7d4ed94416'

def sha(b): return hashlib.sha256(b).hexdigest()
def canonical(o): return json.dumps(o, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode('utf-8')
def git(*args):
    p = subprocess.run(['git', '--no-pager', *args], cwd=ROOT, capture_output=True)
    if p.returncode: raise RuntimeError('git failed: ' + str(args[:3]) + ': ' + p.stderr.decode()[:500])
    return p.stdout

def sections(b):
    chunks = re.split(b'(?=^diff --git )', b, flags=re.M)
    out = {}
    for c in chunks:
        if not c: continue
        first = c.split(b'\n', 1)[0]
        key = first.decode().split(' b/', 1)[1]
        assert key not in out
        out[key] = c
    return out

def check():
    errors=[]
    prep=json.loads((F/'prepare.json').read_bytes())
    reviewed=json.loads((F/'reviewed-manifest.json').read_bytes())
    product=json.loads((F/'product-manifest.json').read_bytes())
    r8=BASE/'final-review-r8'
    old=json.loads((r8/'reviewed-manifest.json').read_bytes())
    oldproduct=json.loads((r8/'product-manifest.json').read_bytes())
    live={}
    checks=[]
    for path,expected in reviewed.items():
        raw=(ROOT/path).read_bytes(); live[path]=sha(raw)
        checks.append({'path':path,'bytes':len(raw),'expected_sha256':expected,'actual_sha256':live[path],'matched':live[path]==expected})
        if live[path]!=expected: errors.append('live drift: '+path)
    for path,expected in product.items():
        if live.get(path)!=expected: errors.append('product drift: '+path)
    if len(reviewed)!=128 or len(product)!=37: errors.append('input count')
    if sha(canonical(reviewed))!=prep['reviewed_manifest_sha256']: errors.append('reviewed canonical')
    if sha(canonical(product))!=prep['product_manifest_sha256']: errors.append('product canonical')
    if git('rev-parse','HEAD').decode().strip()!=HEAD: errors.append('HEAD drift')
    if git('rev-parse',PIN).decode().strip()!=PIN: errors.append('pin invalid')
    tracked=set(git('ls-files','-z').decode().rstrip('\0').split('\0'))
    diff=git('diff','--no-ext-diff',PIN,'--',*sorted(reviewed))
    untracked=[]
    for path in sorted(set(reviewed)-tracked):
        p=subprocess.run(['git','diff','--no-index','--','/dev/null',path],cwd=ROOT,capture_output=True)
        if p.returncode not in (0,1): raise RuntimeError('untracked diff failed')
        diff+=p.stdout; untracked.append(path)
    saved=(F/'current.diff').read_bytes()
    if diff!=saved or sha(diff)!=prep['diff_sha256'] or len(diff)!=prep['diff_bytes']: errors.append('complete diff mismatch')
    candidates={}
    for name in ('candidate-before.json','candidate-after.json'):
        b=(F/name).read_bytes(); candidates[name]={'bytes':len(b),'sha256':sha(b)}
        if sha(b)!=prep[name.replace('.json','').replace('-','_')+'_sha256']: errors.append(name+' mismatch')
    if (F/'candidate-before.json').read_bytes()!=(ROOT/'qa/release-029/approved-release-delta.json').read_bytes(): errors.append('live candidate mismatch')
    candidate=json.loads((F/'candidate-before.json').read_bytes())
    candidate_checks={}
    for kind in ('guarded_source_sha256','immutable_source_sha256','lineage_sha256'):
        rows=candidate.get(kind,{})
        candidate_checks[kind]={'count':len(rows),'mismatches':[p for p,h in rows.items() if sha((ROOT/p).read_bytes())!=h]}
        if candidate_checks[kind]['mismatches']: errors.append('candidate '+kind)
    patch_checks=[]
    for p,rows in candidate['patches'].items():
        for row in rows:
            before=row['before'].encode(); after=row['after'].encode()
            ok=sha(before)==row['before_sha256'] and sha(after)==row['after_sha256'] and before==git('show',row['before_commit']+':'+p) and after==(ROOT/p).read_bytes()
            patch_checks.append({'path':p,'matched_full_before_after_git':ok})
            if not ok: errors.append('candidate full patch '+p)
    changed=sorted(p for p in old.keys()&reviewed.keys() if old[p]!=reviewed[p])
    added=sorted(reviewed.keys()-old.keys()); removed=sorted(old.keys()-reviewed.keys())
    prodhead=[]
    for p,h in product.items():
        if oldproduct.get(p)!=h or sha(git('show',HEAD+':'+p))!=h: prodhead.append(p)
    if prodhead: errors.append('R8/HEAD product mismatch')
    app_tests=[p for p in reviewed if p.startswith(('app/src/test/','app/src/androidTest/'))]
    oldtest_drift=[p for p in app_tests if p in old and old[p]!=live[p]]
    headtest_drift=[p for p in app_tests if sha(git('show',HEAD+':'+p))!=live[p]]
    if oldtest_drift or headtest_drift: errors.append('existing app tests drift')
    olddiff=(r8/'current.diff').read_bytes()
    s0,s1=sections(olddiff),sections(diff)
    same=sorted(p for p in s0.keys()&s1.keys() if s0[p]==s1[p])
    changed_sections=sorted(p for p in s0.keys()&s1.keys() if s0[p]!=s1[p])
    added_sections=sorted(s1.keys()-s0.keys())
    hold=BASE/'resume-third/r9'
    source=(ROOT/'qa/emulator_install_and_tour.py').read_bytes()
    marker=b'    # Diagnostic-only block. Failure must not skip any original harvest decision.\n'
    start=source.index(marker); end=source.index(b'    if archive.returncode or not archive.stdout:',start)
    reverse=source[:start]+source[end:]
    original=(hold/'emulator_install_and_tour.py.before.original').read_bytes()
    workflow=(ROOT/'.github/workflows/ui-smoke.yml').read_bytes()
    wrapper=b'python3 -B qa/cloud_emulator_observer.py -- python3 qa/emulator_install_and_tour.py'
    workflow_reverse=workflow.replace(wrapper,b'python3 qa/emulator_install_and_tour.py')
    preserve={'harvest_full_reverse_equal':reverse==original,'harvest_original_git_equal':original==git('show',HEAD+':qa/emulator_install_and_tour.py'),
              'workflow_single_replacement':workflow.count(wrapper)==1,
              'workflow_full_reverse_equal':workflow_reverse==(hold/'ui-smoke.yml.before.original').read_bytes()}
    if not all(preserve.values()): errors.append('original source/workflow preservation')
    chain={}
    closure=json.loads((r8/'dual-closure.json').read_bytes())
    for axis in ('spec','standards'):
        b=(r8/(axis+'-raw.txt')).read_bytes(); raw=json.loads(b)
        chain[axis]={'raw_sha256':sha(b),'passed':raw['passed'],'zero_blockers':not(raw['security_concerns'] or raw['logic_errors'] or raw['missing_requirements']),
                     'manifest_matches':raw.get('reviewed_manifest_sha256',raw.get('bindings',{}).get('reviewed_manifest_sha256'))==sha(canonical(old)),
                     'diff_matches':raw.get('diff_sha256',raw.get('bindings',{}).get('diff_sha256'))==sha(olddiff)}
        if not all(v for k,v in chain[axis].items() if k!='raw_sha256'): errors.append('R8 chain '+axis)
        if sha(b) not in json.dumps(closure): errors.append('R8 closure '+axis)
    chain['dual_closure_sha256']=sha((r8/'dual-closure.json').read_bytes())
    chain['reviewed_manifest_sha256']=sha(canonical(old)); chain['diff_sha256']=sha(olddiff)
    old_raws={a:sha((BASE/'final-review-r9-continuation'/(a+'-raw.txt')).read_bytes()) for a in ('spec','standards')}
    result={'checked_at':datetime.datetime.now().astimezone().isoformat(),'passed':not errors,'mismatches':errors,'actual_head':HEAD,'head_pin':PIN,
            'reviewed_files':len(reviewed),'product_files':len(product),'reviewed_manifest_sha256':sha(canonical(reviewed)),
            'product_sha256':sha(canonical(product)),'diff_bytes':len(diff),'diff_sha256':sha(diff),'prepare_raw_sha256':sha((F/'prepare.json').read_bytes()),
            'canonical_encoding':'sort_keys=True,separators=(comma,colon),ensure_ascii=False,UTF-8,no newline',
            'manifested_untracked_append':untracked,'complete_live_diff_rebuilt_equal':diff==saved,'candidates':candidates,'candidate_checks':candidate_checks,
            'candidate_full_patch_checks':patch_checks,'all_live_files':checks,'r8_changed':changed,'r8_added':added,'r8_removed':removed,
            'r8_unchanged_count':len(old)-len(changed)-len(removed),'r8_all_37_product_HEAD_match':not prodhead,'old_app_test_files':len(app_tests),
            'old_app_test_drift':oldtest_drift,'HEAD_app_test_drift':headtest_drift,
            'cumulative_sections':{'r8':len(s0),'r10':len(s1),'unchanged':len(same),'changed':changed_sections,'added':added_sections,'removed':sorted(s0.keys()-s1.keys())},
            'preservation':preserve,'r8_chain':chain,'r9_original_raw_sha256':old_raws}
    return result,diff,b''.join(s1[p] for p in sorted(set(changed_sections+added_sections)))

if __name__=='__main__':
    name=sys.argv[1]
    r,d,delta=check()
    with (OUT/(name+'.json')).open('x') as f: json.dump(r,f,ensure_ascii=False,indent=2); f.write('\n')
    if name=='binding-initial':
        with (OUT/'regenerated-current.diff').open('xb') as f: f.write(d)
        with (OUT/'r8-r10-cumulative-changed-sections.diff').open('xb') as f: f.write(delta)
    print(json.dumps({k:v for k,v in r.items() if k in ('passed','mismatches','reviewed_files','product_files','reviewed_manifest_sha256','product_sha256','diff_sha256','diff_bytes','r8_changed','r8_added','r8_unchanged_count','cumulative_sections','old_app_test_files')},ensure_ascii=False))
    sys.exit(0 if r['passed'] else 1)
