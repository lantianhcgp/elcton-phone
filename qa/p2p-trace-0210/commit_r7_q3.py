#!/usr/bin/env python3
"""Explicit Q3 whitelist/commit, not a review and never pushes or dispatches."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess

ROOT=Path(__file__).resolve().parents[2]
QA=Path(__file__).resolve().parent
Q=QA/'r6'
BEFORE='a0881bf7c1d97724ea166f0e51988902c280a5cc'
BRANCH='diag/p2p-trace-0.2.10-20261115'
sha=lambda raw:hashlib.sha256(raw).hexdigest()
def git(*args):
    return subprocess.check_output(['git',*args],cwd=ROOT)

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--commit',action='store_true')
    args=parser.parse_args()
    assert git('branch','--show-current').decode().strip()==BRANCH
    assert git('rev-parse','HEAD').decode().strip()==BEFORE
    closure_path=Q/'reviews/closure-q3/dual-closure.json'
    closure=json.loads(closure_path.read_bytes())
    manifest_path=Q/'reviews/closure-q3/reviewed-manifest.json'
    inputs=json.loads(manifest_path.read_bytes())
    assert closure['passed'] is True and closure['manifest_sha256']==sha(manifest_path.read_bytes())
    assert {row['axis'] for row in closure['axes']}=={'spec','quality'}
    assert all(sha((ROOT/p).read_bytes())==h for p,h in inputs.items())
    fresh=Q/'evidence/r7-final-regression-q3'
    regression=json.loads((fresh/'receipt.json').read_bytes())
    assert regression['passed'] is True and len(regression['rows'])==7 and all(x['exit']==0 for x in regression['rows'])
    assert (regression['jvm'],regression['python'],regression['python_skip'],regression['http_assertions'])==(171,133,0,3784)
    for row in regression['rows']:
        assert 'reused_actual_prior_source_identical_compile' not in row
        assert row['raw_sha256']==sha((fresh/(row['lane']+'.raw.log')).read_bytes())
    source_manifest=json.loads((fresh/'source-manifest.json').read_bytes())
    assert all(sha((ROOT/p).read_bytes())==h for p,h in source_manifest.items())
    compile_receipt=json.loads((fresh/'full-jvm/receipt.json').read_bytes())
    assert [x['exit'] for x in compile_receipt['commands']]==[0,0]
    assert 'OK (171 tests)' in (fresh/'full-jvm/junit.log').read_text()
    watch=json.loads((Q/'evidence/r7-watch-frozen-q3/receipt.json').read_bytes())
    assert watch['passed'] is True and watch['counts']=={'tests':445,'pass':445,'fail':0,'skipped':0} and watch['input_unchanged'] is True
    old_publish=Q/'PUBLISH-CANDIDATE.json'
    saved=Q/'ci/r7-publish-source-a088.json'
    if not saved.exists():saved.write_bytes(old_publish.read_bytes())
    result=subprocess.run(['python','-B',str(QA/'prepare_r6_publish.py')],cwd=ROOT,capture_output=True,text=True)
    assert result.returncode==0,result.stdout+result.stderr
    chosen=set(json.loads(old_publish.read_bytes())['paths'])
    chosen.update(inputs)
    extra=['register_r7_ci_identity.py','register_r7_ci_final_identity.py','close_r7_q3_reviews.py','commit_r7_q3.py',
        'R7-CI-WHITESPACE-REPAIR-SCOPE.md','R7-CI-WHITESPACE-FOLLOWUP-SCOPE.md']
    chosen.update('qa/p2p-trace-0210/'+p for p in extra)
    folders=[Q/'evidence'/p for p in ['r7-ci-whitespace','r7-ci-whitespace-followup','r7-ci-identity','r7-ci-identity-final',
        'r7-ci-compiler-red','r7-ci-compiler-green','r7-ci-compiler-green-final','r7-ci-parent-readback','r7-final-regression-q3','r7-watch-frozen-q3']]
    folders += [Q/'reviews',Q/'whitespace-host',Q/'whitespace-followup-host',Q/'ci/r7-build-failure-attempt1',Q/'ci/r7-failed-log-attempt1',Q/'ci/r7-build-wait-retry1']
    ends=('.json','.md','.txt','.log','.tap','.diff','.py','.kt.in','.java.in','.exit')
    for folder in folders:
        assert folder.is_dir(),folder
        for path in folder.rglob('*'):
            if path.is_file() and path.name.endswith(ends) and not any(k in path.parts for k in ('generated','runtime-files','wakeup-work','host-overlay','asm-classes')):
                chosen.add(str(path.relative_to(ROOT)))
    for path in (Q/'ci').glob('r7*'):
        if path.is_file() and path.suffix in ('.py','.md','.json','.jsonl'):
            chosen.add(str(path.relative_to(ROOT)))
    patterns=[re.compile(x) for x in [rb'ghp_[A-Za-z0-9]{20,}',rb'github_pat_[A-Za-z0-9_]{20,}',rb'sk-[A-Za-z0-9]{20,}',rb'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----',rb'Bearer [A-Za-z0-9_-]{24,}']]
    rows={}
    for name in sorted(chosen):
        p=ROOT/name
        assert p.is_file() and not p.is_symlink() and not name.endswith(('.jar','.apk','.zip','.pem','.p12','.jks','.class','.bin','.keystore'))
        assert not any(k in p.parts for k in ('generated','runtime-files','wakeup-work','host-overlay','asm-classes'))
        raw=p.read_bytes()
        assert not any(pat.search(raw) for pat in patterns),'Secret format risk: '+name
        rows[name]={'bytes':len(raw),'sha256':sha(raw),'blob':hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\x00'+raw).hexdigest()}
    publish=Q/'ci/r7-publish-q3.json'
    assert not publish.exists()
    publish.write_text(json.dumps({'paths':rows,'risk_matches':[],'scope':'Explicit Q3 text/source whitelist, no binaries, credentials or original evidence mutation'},indent=2)+'\n')
    if not args.commit:
        print(json.dumps({'prepared':True,'files':len(rows),'manifest':str(publish),'committed':False}));return
    subprocess.run(['git','diff','--check'],cwd=ROOT,check=True)
    subprocess.run(['git','add','--',*rows],cwd=ROOT,check=True)
    staged=set(git('diff','--cached','--name-only','-z').decode().split('\x00'))-{''}
    assert staged and staged<=set(rows)
    for p,h in inputs.items():assert sha(git('show',':'+p))==h
    subprocess.run(['git','commit','--quiet','-m','fix(diagnostics): separate Kotlin 1.9 string tokens without behavior changes'],cwd=ROOT,check=True)
    source=git('rev-parse','HEAD').decode().strip()
    assert source!=BEFORE
    for p,h in inputs.items():assert sha(git('show',source+':'+p))==h
    result={'source_sha':source,'previous_source':BEFORE,'branch':BRANCH,'files_changed':len(staged),'whitelist_files':len(rows),
        'review_inputs':len(inputs),'review_manifest_sha256':sha(manifest_path.read_bytes()),'fresh_regression_sha256':sha((fresh/'receipt.json').read_bytes()),
        'pushed':False,'scope':'Actual reviewed Q3 lexical-only source+identity+text evidence commit; no push/CI/device'}
    with (Q/'ci/r7-source-commit-q3.json').open('x') as f:json.dump(result,f,indent=2);f.write('\n')
    print(json.dumps(result))

if __name__=='__main__':main()
