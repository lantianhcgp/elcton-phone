#!/usr/bin/env python3
"""Re-run final current production/test inputs serially, preserving each old lane.
No migration, dispatch, device, assertion edits or file deletion. Fails closed.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import time

ROOT = Path(__file__).resolve().parents[2]
DEPS = Path.home()/'.hermes/tmp/elcton-jvm-test'
QA = Path(__file__).resolve().parent
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--resume-compiled', type=Path)
    a = p.parse_args()
    if '..' in a.out.parts:
        p.error('Output must not contain parent traversal')
    out = a.out.absolute()
    if any(path.is_symlink() for path in (out, *out.parents)):
        p.error('Output must not have symlink ancestry')
    base = (QA/'r6/evidence').resolve()
    out = out.resolve()
    if out == base or not out.is_relative_to(base):
        p.error('Output must be a new directory within R6 evidence')
    out.mkdir(parents=True, exist_ok=False)
    sources = sorted((ROOT/'app/src/main').rglob('*.kt')) + sorted((ROOT/'app/src/test').rglob('*.kt'))
    watched = sources + [ROOT/'qa/diag_source_gate.py', QA/'r6/current-identity.json', ROOT/'app/build.gradle.kts']
    manifest = {str(f.relative_to(ROOT)): sha(f) for f in watched}
    rows = []
    (out/'source-manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
    def run(label, argv, env=None, cwd=ROOT):
        r = subprocess.run(argv, cwd=cwd, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        (out/(label+'.raw.log')).write_text(r.stdout)
        row = {'lane': label, 'exit': r.returncode, 'argv': argv, 'raw_sha256': sha(out/(label+'.raw.log'))}
        rows.append(row)
        (out/'receipt.json').write_text(json.dumps({'rows': rows, 'source_manifest_sha256': sha(out/'source-manifest.json'),
                    'scope':'Actual HOST current-source execution, no Android/device or CI claim'},indent=2)+'\n')
        print(json.dumps({'lane':label,'exit':r.returncode}), flush=True)
        assert r.returncode == 0, label+' actual execution failed; raw preserved'
        return r.stdout
    if a.resume_compiled:
        prior=a.resume_compiled.absolute()
        assert prior.is_relative_to(QA/'r6/evidence')
        assert json.loads((prior/'source-manifest.json').read_bytes())==manifest, 'Cannot reuse stale compiled inputs'
        receipt=json.loads((prior/'full-jvm/receipt.json').read_bytes())
        assert {c['name']:c['exit'] for c in receipt['commands']} == {'compile':0,'junit':0}
        assert (prior/'full-jvm/compile.exit').read_text().strip()=='0'
        assert (prior/'full-jvm/junit.exit').read_text().strip()=='0'
        assert 'OK (171 tests)' in (prior/'full-jvm/junit.log').read_text()
        jar=prior/'full-jvm/host-tests.jar'
        rows.append({'lane':'full-jvm','exit':0,'reused_actual_prior_source_identical_compile':str(prior),'jar_sha256':sha(jar), 'raw_sha256':sha(prior/'full-jvm/junit.log')})
    else:
        run('full-jvm', ['nice','-n','10','python','-B',str(QA/'run_host.py'),'--deps',str(DEPS),'--out',str(out/'full-jvm')])
        jar = out/'full-jvm/host-tests.jar'
    cp = os.pathsep.join(str(DEPS/(n+'.jar')) for n in ['json','junit','hamcrest'])
    classes = ['com.hcbiu.elcton.P2pTraceRuntimeTest','com.hcbiu.elcton.DiagnosticsIntegrationTest']
    raw = run('app-cwd', ['java','-cp',str(jar)+os.pathsep+cp,'org.junit.runner.JUnitCore',*classes],cwd=ROOT/'app')
    assert 'OK (6 tests)' in raw
    env = dict(os.environ, MCP_HTTP_TEST_CLASSPATH=str(jar)+os.pathsep+cp, PYTHONDONTWRITEBYTECODE='1')
    raw = run('python-all', ['python','-B','-m','unittest','discover','-s','qa','-p','test_*.py','-v'],env)
    match = re.search(r'Ran (\d+) tests',raw)
    assert match and int(match.group(1)) == 133 and re.search(r'\bOK\s*$',raw) and 'skipped' not in raw.lower()
    raw = run('http', ['python','-B','qa/mcp_http_selftest.py','--classpath',str(jar)+os.pathsep+cp],env)
    http_result=json.loads(raw)
    assert http_result['ok'] is True and http_result['assertions']==3784 and http_result['all_raw_checks_passed'] is True
    run('runtime-fault-and-stop', ['nice','-n','10','python','-B',str(QA/'run_runtime_fault_host.py'),'--deps',str(DEPS),'--out',str(out/'runtime')])
    run('native-adapter', ['nice','-n','10','python','-B',str(QA/'run_native_host.py'),'--deps',str(DEPS),'--out',str(out/'native')])
    run('actual-sdk-type', ['nice','-n','10','python','-B',str(QA/'run_native_host.py'),'--deps',str(DEPS),'--out',str(out/'actual-sdk'),'--actual-sdk','--skip-junit'])
    assert all(sha(ROOT/f)==h for f,h in manifest.items()), 'Current source changed during final lanes'
    result = {'passed':True,'rows':rows,'source_manifest_sha256':sha(out/'source-manifest.json'),'jar_sha256':sha(jar),
            'source_rows':len(manifest),'source_drift':[],'jvm':171,'python':133,'python_skip':0,'app_cwd':6,'http_assertions':3784,
            'scope':'Real HOST full regressions only; Android CI and device are separate','at':time.strftime('%Y-%m-%d %H:%M:%S %z')}
    (out/'receipt.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result),flush=True)

if __name__=='__main__':main()
