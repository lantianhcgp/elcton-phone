import ast
import contextlib
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

ROOT=Path('/data/data/com.termux/files/home/elcton-phone-release-029-20261114')
P=ROOT/'qa/release-029/evidence/resume-1720/final-review-r11-fourth/spec-probes'
TMP=P/'temp'
TMP.mkdir(exist_ok=False)
os.environ.update({'TMPDIR':str(TMP),'PYTHONDONTWRITEBYTECODE':'1','PYTHONPATH':str(ROOT)})
tempfile.tempdir=str(TMP)
sys.path.insert(0,str(ROOT))
def load(path,name):
    s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def sha(b):return hashlib.sha256(b).hexdigest()
def save(name,v):
    with (P/name).open('xb') as f:f.write((json.dumps(v,ensure_ascii=False,indent=2)+'\n').encode())
def funcs(raw):
    tree=ast.parse(raw)
    return {n.name:ast.dump(n,include_attributes=False) for n in tree.body if isinstance(n,(ast.FunctionDef,ast.ClassDef))}

oldprobe=ROOT/'qa/release-029/evidence/resume-1720/resume-fourth/test_crash_observer_containment.py'
newprobe=ROOT/'qa/test_cloud_observer_crash_containment.py'
assert funcs(oldprobe.read_bytes())==funcs(newprobe.read_bytes()),'Security probe original methods/assertions differ'
oldharvest=ROOT/'qa/release-029/evidence/resume-1720/resume-third/r9/emulator_install_and_tour.py.before.original'
currentharvest=(ROOT/'qa/emulator_install_and_tour.py').read_bytes()
lines=currentharvest.splitlines(keepends=True); tree=ast.parse(currentharvest)
fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='harvest_palettes')
block=[n for n in fn.body if isinstance(n,ast.Try) and any(isinstance(x,ast.Name) and x.id=='wire_target' for x in ast.walk(n))]
assert len(block)==1
b=block[0]; start=b.lineno-2
assert lines[start].strip()==b'# Diagnostic-only block. Failure must not skip any original harvest decision.'
reversed_raw=b''.join(lines[:start]+lines[b.end_lineno:])
assert reversed_raw==oldharvest.read_bytes(),'Entire harvest file inverse differs'
oldworkflow=subprocess.check_output(['git','show','44df9d0fd36aecaa22613e9aa73c5c7d4ed94416:.github/workflows/ui-smoke.yml'],cwd=ROOT)
workflow=(ROOT/'.github/workflows/ui-smoke.yml').read_bytes()
replacement=b'python3 -B qa/cloud_emulator_observer.py -- python3 qa/emulator_install_and_tour.py'
assert workflow.count(replacement)==1
assert workflow.replace(replacement,b'python3 qa/emulator_install_and_tour.py')==oldworkflow,'Workflow non-wrapper drift'

results=[]
for i,path in enumerate([ROOT/'qa/test_cloud_observer.py',ROOT/'qa/test_cloud_observer_isolation.py',newprobe,ROOT/'qa/test_cloud_observer_crash_limits.py',oldprobe]):
    module=load(path,'spec_original_'+str(i)); suite=unittest.defaultTestLoader.loadTestsFromModule(module)
    expected=(7,8,5,5,5)[i]; assert suite.countTestCases()==expected
    stream=io.StringIO();started=time.monotonic();result=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
    raw=stream.getvalue().encode()
    with (P/('tests-'+str(i)+'.log')).open('xb') as f:f.write(raw)
    row={'path':str(path),'source_sha256':sha(path.read_bytes()),'count':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'skips':len(result.skipped),'passed':result.wasSuccessful() and not result.skipped,'seconds':time.monotonic()-started,'log_sha256':sha(raw),'failed_ids':[t.id() for t,msg in result.failures+result.errors]}
    results.append(row);print(json.dumps(row))
    if not row['passed']:
        save('probe-first-blocker.json',results);raise SystemExit(1)

m=load(ROOT/'qa/cloud_emulator_observer.py','spec_absent_source')
with tempfile.TemporaryDirectory(dir=TMP) as d:
    base=Path(d); out=base/'out';out.mkdir(); absent=base/'absent';outside=base/'outside';outside.mkdir();pinned=base/'pinned';realpath=m.Path;realopen=m.os.open;swapped=[]
    def opened(path,flags,*a,**kw):
        fd=realopen(path,flags,*a,**kw)
        if flags & os.O_DIRECTORY and not swapped:
            st=os.fstat(fd);target=out.stat()
            if (st.st_dev,st.st_ino)==(target.st_dev,target.st_ino):
                out.rename(pinned);out.symlink_to(outside,target_is_directory=True);swapped.append(True)
        return fd
    with patch.object(m,'Path',side_effect=lambda v:absent if str(v)=='/tmp/android-runner' else realpath(v)),patch.object(m.os,'open',side_effect=opened):
        m.capture_crashdata(out)
    assert swapped==[True] and list(outside.iterdir())==[]
    assert json.loads((pinned/'crashdata-index.json').read_bytes())==[]
    budget=json.loads((pinned/'crashdata-budget.json').read_bytes())
    assert budget['stopped_reason']=='source-absent'
    assert (pinned/'crashdata-index.json').stat().st_mode & 0o777 == 0o600
    extra={'source_absent_index_race_reached':True,'outside_writes':0,'index_written_to_pinned_fd':True,'index_mode':'0600','budget':budget}
with tempfile.TemporaryDirectory(dir=TMP) as d:
    out=Path(d)/'out';out.mkdir(); index=out/'crashdata-index.json';index.write_bytes(b'original index fixture'); absent=Path(d)/'missing'
    with patch.object(m,'Path',side_effect=lambda v:absent if str(v)=='/tmp/android-runner' else realpath(v)):
        try:m.capture_crashdata(out)
        except FileExistsError:pass
        else:raise AssertionError('Existing index was not fail-closed')
    assert index.read_bytes()==b'original index fixture'
    extra['existing_index_exclusive_rejected_without_overwrite']=True
save('focused-execution.json',{'passed':True,'original_test_results':results,'original_security_methods_ast_identical':True,'harvest_whole_file_inverse_exact':True,'workflow_single_wrapper_inverse_exact':True,'extra_local_fake_filesystem':extra,'scope':'local fixture filesystem / actual child OS processes only; no ADB/CI/device; 30 original cases zero skip plus two index branch probes'})
print('FOCUSED_OK',sum(r['count'] for r in results),json.dumps(extra))
