#!/usr/bin/env python3
"""Final commit of exact independently reviewed source/evidence whitelist; no push.
The caller must explicitly run this only after actual dual review closure exists.
"""
import hashlib
import json
from pathlib import Path
import subprocess
ROOT = Path(__file__).resolve().parents[2]
Q = Path(__file__).resolve().parent/'r6'
BASEHEAD = 'de3e6f182c2def5a52d33f33684777f1fc941ccd'
BRANCH = 'diag/p2p-trace-0.2.10-20261115'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()

def git(*args):
    return subprocess.check_output(['git',*args],cwd=ROOT)

def main():
    assert git('branch','--show-current').decode().strip()==BRANCH
    assert git('rev-parse','HEAD').decode().strip()==BASEHEAD, 'Unexpected prior commit; no blind recommit'
    closure=json.loads((Q/'reviews/closure/dual-closure.json').read_bytes())
    assert closure['passed'] is True and len(closure['axes'])==2
    inputs=json.loads((Q/'reviews/closure/reviewed-manifest.json').read_bytes())
    assert all(sha(ROOT/path)==h for path,h in inputs.items()), 'Current review bytes changed'
    regression=json.loads((Q/'evidence/r7-final-regression/receipt.json').read_bytes())
    assert regression['passed'] is True and (regression['jvm'],regression['python'],regression['python_skip'],regression['http_assertions'])==(171,133,0,3784)
    assert all(row['exit']==0 for row in regression['rows'])
    regression_inputs=json.loads((Q/'evidence/r7-final-regression/source-manifest.json').read_bytes())
    assert all(sha(ROOT/p)==h for p,h in regression_inputs.items()), 'Post-review regression source drift'
    watch=json.loads((Q/'evidence/r7-watch-frozen/receipt.json').read_bytes())
    assert watch['passed'] is True and watch['exit']==0
    assert watch['counts']=={'tests':445,'pass':445,'fail':0,'skipped':0} and watch['input_unchanged'] is True
    whitelist=json.loads((Q/'PUBLISH-CANDIDATE.json').read_bytes())
    assert not whitelist['risk_matches']
    rows=whitelist['paths']
    assert set(inputs)<=set(rows), 'Missing reviewed input in staged whitelist'
    for path,row in rows.items():
        p=ROOT/path
        assert p.is_file() and not p.is_symlink() and sha(p)==row['sha256'] and p.stat().st_size==row['bytes']
    subprocess.run(['git','add','--',*rows],cwd=ROOT,check=True)
    staged=set(git('diff','--cached','--name-only').decode().splitlines())
    assert staged<=set(rows) and staged, 'Unexpected staged path or empty commit'
    assert sorted(p for p in staged if p.startswith('qa/') and p.endswith('.kt')) == sorted(['qa/P2pCandidateBuildTest.kt','qa/p2p-trace-0210/r6/fixtures/P2pTraceBaselineEngine.kt'])
    assert not any(p.endswith(('.jar','.apk','.jks','.pem','.zip','.p12')) for p in staged)
    for path in inputs:
        assert hashlib.sha256(git('show',':'+path)).hexdigest()==inputs[path], 'Staged reviewer input differs: '+path
    subprocess.run(['git','commit','-m','fix(diagnostics): align attempt validity and close trace wakeup race for 0.2.10'],cwd=ROOT,check=True)
    head=git('rev-parse','HEAD').decode().strip()
    assert head!=BASEHEAD and len(head)==40
    for path in inputs:
        assert hashlib.sha256(git('show',head+':'+path)).hexdigest()==inputs[path], 'Committed review bytes mismatch'
    out=Q/'evidence/final-source-commit'
    out.mkdir(parents=True,exist_ok=False)
    (out/'receipt.json').write_text(json.dumps({'source_sha':head,'previous_head':BASEHEAD,'branch':BRANCH,
        'reviewed_files':len(inputs),'committed_files':len(staged),'review_input_sha256':sha(Q/'reviews/closure/reviewed-manifest.json'),
        'committed_whitelist':list(sorted(staged)),'pushed':False,'release_created':False},indent=2)+'\n')
    print(json.dumps({'source_sha':head,'branch':BRANCH,'files':len(staged),'pushed':False}))

if __name__=='__main__':main()
