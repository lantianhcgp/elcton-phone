#!/usr/bin/env python3
"""Independent R9 counterexamples; real OS children, mocked diagnostic collectors only."""
import ast
import datetime
import importlib.util
import io
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tarfile
import threading
import time
import traceback
import unittest
from unittest.mock import patch

R=Path('/data/data/com.termux/files/home/elcton-phone-release-029-20261114')
O=R/'qa/release-029/evidence/resume-1720/final-review-r10-fourth/spec-probes'
sys.path.insert(0,str(R))
sys.path.insert(0,str(R/'qa'))

def load():
    s=importlib.util.spec_from_file_location('independent_spec_observer',R/'qa/cloud_emulator_observer.py')
    m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m

def child(mode,code,signal_number=None):
    script='''import importlib.util,json,sys,threading
from pathlib import Path
from unittest.mock import patch
s=importlib.util.spec_from_file_location('isolated_spec',sys.argv[1]);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
m.capture_kernel=lambda p:None;m.capture_crashdata=lambda p:None
mode=sys.argv[2];code=int(sys.argv[3]);out=Path(sys.argv[4]);marker=Path(sys.argv[5]);sig=int(sys.argv[6])
command=[sys.executable,'-c','from pathlib import Path;import sys,os,signal;p=Path(sys.argv[1]);p.write_text(p.read_text()+"X" if p.exists() else "X");sig=int(sys.argv[3]);signal.signal(sig,signal.SIG_DFL) if sig and sig!=signal.SIGKILL else None;os.kill(os.getpid(),sig) if sig else sys.exit(int(sys.argv[2]))',str(marker),str(code),str(sig)]
orig_open=Path.open;orig_mkdir=Path.mkdir;orig_start=threading.Thread.start
class FailClose:
 def __enter__(self): return self
 def write(self,v): return len(v)
 def __exit__(self,*a): raise OSError('independent close-only failure')
def open_fault(p,*a,**kw):
 if p.name=='child-exit.json' and mode=='receipt':raise OSError('independent final receipt failure')
 if p.name=='child-exit.json' and mode=='receipt-close':return FailClose()
 return orig_open(p,*a,**kw)
def mkdir_fault(p,*a,**kw):
 if p==out and mode=='directory':raise OSError('independent init failure')
 return orig_mkdir(p,*a,**kw)
def start_fault(t,*a,**kw):
 if mode=='thread':raise RuntimeError('independent thread start failure')
 return orig_start(t,*a,**kw)
with patch.object(Path,'open',open_fault),patch.object(Path,'mkdir',mkdir_fault),patch.object(threading.Thread,'start',start_fault):
 m.exit_like_child(m.run_child(command,out,interval=.01))
'''
    pth=O/(mode+'-'+str(code)+'-'+str(signal_number or 0));pth.mkdir()
    args=[sys.executable,'-B','-c',script,str(R/'qa/cloud_emulator_observer.py'),mode,str(code),str(pth/'output'),str(pth/'marker'),str(signal_number or 0)]
    t=time.monotonic();p=subprocess.run(args,capture_output=True,timeout=8);elapsed=time.monotonic()-t
    (pth/'stdout.bin').write_bytes(p.stdout);(pth/'stderr.bin').write_bytes(p.stderr)
    actual={'mode':mode,'requested_exit':code,'signal':signal_number,'native_returncode':p.returncode,'elapsed_seconds':elapsed,'marker':(pth/'marker').read_text(),'stdout_bytes':len(p.stdout),'stderr_bytes':len(p.stderr)}
    with (pth/'execution.json').open('x') as f:json.dump(actual,f,indent=2)
    assert actual['marker']=='X','child not executed once'
    assert p.returncode==(-signal_number if signal_number else code),'child native exit changed'
    return actual

def harvest_wire():
    current=(R/'qa/emulator_install_and_tour.py').read_text()
    old=(R/'qa/release-029/evidence/resume-1720/resume-third/r9/emulator_install_and_tour.py.before.original').read_text()
    cases=[]
    for code in (0,1):
        for fault in ('open','close','directory'):
            pair=[]
            for label,src in [('original',old),('R10',current)]:
                out=O/('wire-'+str(code)+'-'+fault+'-'+label);out.mkdir();target=out/'palette-product';target.mkdir()
                run='independent-run';stream=io.BytesIO();raw=b'independent successful crash-free payload'
                with tarfile.open(fileobj=stream,mode='w') as tf:
                    item=tarfile.TarInfo('qa-palette-evidence/'+run+'/proof.bin');item.size=len(raw);tf.addfile(item,io.BytesIO(raw))
                transport=subprocess.CompletedProcess(['adb','shell'],code,stream.getvalue() if not code else b'',b'original tar failure' if code else b'')
                node=next(n for n in ast.parse(src).body if isinstance(n,ast.FunctionDef) and n.name=='harvest_palettes')
                scope={'Path':Path,'out':out,'palette_target':target,'palette_run':run,'subprocess':subprocess,'io':io,'tarfile':tarfile}
                exec(compile(ast.Module(body=[node],type_ignores=[]),label,'exec'),scope)
                original_open=Path.open;original_mkdir=Path.mkdir
                class FailClose:
                    def __enter__(self):return self
                    def write(self,v):return len(v)
                    def __exit__(self,*a):raise OSError('independent wire close failure')
                def fail_open(p,*a,**kw):
                    if 'palette-harvest-wire' in p.parts:
                        if fault=='close':return FailClose()
                        if fault=='open':raise OSError('independent wire open failure')
                    return original_open(p,*a,**kw)
                def fail_mkdir(p,*a,**kw):
                    if 'palette-harvest-wire' in p.parts and fault=='directory':raise OSError('independent wire directory failure')
                    return original_mkdir(p,*a,**kw)
                with patch.object(subprocess,'run',return_value=transport) as call,patch.object(Path,'open',fail_open),patch.object(Path,'mkdir',fail_mkdir):
                    returned=scope['harvest_palettes']();assert call.call_count==1
                actual={'returned':returned,'proof_bytes':(target/'proof.bin').read_bytes().hex() if (target/'proof.bin').exists() else None,'error_text':(out/'palette-harvest-error.txt').read_text() if (out/'palette-harvest-error.txt').exists() else None}
                pair.append(actual)
            assert pair[0]==pair[1],'wire failure changed original result'
            cases.append({'exit':code,'fault':fault,'baseline_equal':True,'result':pair[1]})
    return cases

def crash_probe(mode):
    m=load();b=O/('crash-'+mode);b.mkdir();root=b/'allowed';root.mkdir();out=b/'output';out.mkdir();outside=b/'outside';outside.mkdir()
    secret=outside/'fixture';secret.write_bytes(b'private synthetic fixture, not actual credentials')
    expected=b'normal bounded crash payload';error=None
    if mode=='normal':(root/'emu-crash-regular.db').write_bytes(expected)
    elif mode=='source-leaf':(root/'emu-crash-link.db').symlink_to(secret)
    elif mode=='source-dir':(outside/'emu-crash-regular.db').write_bytes(secret.read_bytes());(root/'nested').symlink_to(outside,target_is_directory=True)
    elif mode=='source-root':root.rmdir();root.symlink_to(outside,target_is_directory=True)
    elif mode=='source-hardlink':os.link(secret,root/'emu-crash-hardlink.db')
    elif mode=='output-root':(root/'emu-crash-regular.db').write_bytes(expected);out.rmdir();out.symlink_to(outside,target_is_directory=True)
    elif mode=='output-dir':(root/'nested').mkdir();(root/'nested/emu-crash-regular.db').write_bytes(expected);(out/'emulator-crashdata').mkdir();(out/'emulator-crashdata/nested').symlink_to(outside,target_is_directory=True)
    elif mode=='output-leaf':(root/'emu-crash-regular.db').write_bytes(expected);(out/'emulator-crashdata').mkdir();(out/'emulator-crashdata/emu-crash-regular.db').symlink_to(secret)
    elif mode=='unapproved-log':(root/'plain.log').write_bytes(secret.read_bytes())
    path_original=m.Path
    with patch.object(m,'Path',side_effect=lambda v:root if str(v)=='/tmp/android-runner' else path_original(v)):
        try:m.capture_crashdata(out)
        except OSError as e:error=type(e).__name__
    assert secret.read_bytes()==b'private synthetic fixture, not actual credentials','outside modified'
    if mode=='normal':assert (out/'emulator-crashdata/emu-crash-regular.db').read_bytes()==expected
    else:
        copied=[p for p in out.rglob('*') if p.is_file() and not p.is_symlink() and p.name!='crashdata-index.json'] if not out.is_symlink() else []
        assert not copied,'symlink/unknown input copied'
        assert not (outside/'emu-crash-regular.db').exists() or mode=='source-dir','outside output written'
    return {'mode':mode,'normal_copied_exact':mode=='normal','escape_rejected':mode!='normal','caught_error':error}

results={'started_at':datetime.datetime.now().astimezone().isoformat(),'actual_adb_calls':0,'failures':[]}
def record(name,fn):
    try:results[name]=fn()
    except Exception as e:
        results['failures'].append({'probe':name,'type':type(e).__name__,'message':str(e),'traceback':traceback.format_exc()})

with (O/'observer15.log').open('x') as log:
    suite=unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromName(name) for name in ('qa.test_cloud_observer','qa.test_cloud_observer_isolation'))
    count=suite.countTestCases();runner=unittest.TextTestRunner(stream=log,verbosity=2);res=runner.run(suite)
results['observer15']={'discovered':count,'tests_run':res.testsRun,'errors':len(res.errors),'failures':len(res.failures),'skipped':len(res.skipped),'passed':res.wasSuccessful() and count==15 and res.testsRun==15 and not res.skipped}
record('wire_io',harvest_wire)
record('child_io',lambda:[child(mode,code) for mode in ('receipt','receipt-close','thread','directory') for code in (0,7)])
record('native_signals',lambda:[child('native',0,int(sig)) for sig in (signal.SIGTERM,signal.SIGPIPE,signal.SIGKILL)])
record('crash_boundary',lambda:[crash_probe(m) for m in ('normal','source-leaf','source-dir','source-root','source-hardlink','output-root','output-dir','output-leaf','unapproved-log')])
record('cloud_guard',lambda:guard()) if False else None
m=load();guards=[]
with patch.dict(os.environ,{},clear=True),patch.object(m.subprocess,'run') as adb:
    try:m.verify_cloud_emulator();raise AssertionError('nonCI accepted')
    except RuntimeError:pass
    assert adb.call_count==0
for listing,accepted in [('List of devices attached\nemulator-5554\tdevice\n',True),('List of devices attached\nphysical-id\tdevice\n',False),('List of devices attached\nemulator-5554\tdevice\nemulator-5556\tdevice\n',False),('List of devices attached\nemulator-5554\toffline\n',False)]:
    with patch.dict(os.environ,{'GITHUB_ACTIONS':'true','CI':'true'}),patch.object(m.subprocess,'run',return_value=subprocess.CompletedProcess(['adb','devices'],0,listing,'')):
        try:value=m.verify_cloud_emulator();actual=True
        except RuntimeError:actual=False
    assert actual==accepted;guards.append({'accepted':actual,'expected':accepted})
results['cloud_guard']={'nonCI_zero_adb':True,'mock_cases':guards}
results['passed']=not results['failures'] and results['observer15']['passed']
results['finished_at']=datetime.datetime.now().astimezone().isoformat()
with (O/'independent-execution.json').open('x') as f:json.dump(results,f,ensure_ascii=False,indent=2);f.write('\n')
print(json.dumps({'passed':results['passed'],'observer15':results['observer15'],'wire_cases':len(results.get('wire_io',[])),'child_cases':len(results.get('child_io',[])),'signal_cases':len(results.get('native_signals',[])),'crash_cases':len(results.get('crash_boundary',[])),'failures':results['failures']},ensure_ascii=False))
sys.exit(0 if results['passed'] else 1)
