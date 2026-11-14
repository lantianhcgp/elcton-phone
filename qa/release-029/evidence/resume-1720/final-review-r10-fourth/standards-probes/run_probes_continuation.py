import ast, hashlib, importlib.util, io, json, os, signal, subprocess, sys, tarfile, tempfile, threading, time, unittest
from pathlib import Path
from unittest.mock import patch
import ctypes
def native_link(src,dst):
 libc=ctypes.CDLL(None,use_errno=True);link=libc.link;link.argtypes=[ctypes.c_char_p,ctypes.c_char_p];link.restype=ctypes.c_int
 if link(os.fsencode(src),os.fsencode(dst))!=0:raise OSError(ctypes.get_errno(),'libc link failed')
R=Path('/data/data/com.termux/files/home/elcton-phone-release-029-20261114')
P=R/'qa/release-029/evidence/resume-1720/final-review-r10-fourth/standards-probes'
TMP=P/'scratch-continuation'; TMP.mkdir(exist_ok=False); tempfile.tempdir=str(TMP)
sys.path.insert(0,str(R));os.chdir(R)
# Never invoke real adb, kernel capture, device/app runtime or CI.
spec=importlib.util.spec_from_file_location('standards_observer', R/'qa/cloud_emulator_observer.py');o=importlib.util.module_from_spec(spec);spec.loader.exec_module(o)
from qa.test_cloud_observer import harvest_scope
suite=unittest.defaultTestLoader.loadTestsFromNames(['qa.test_cloud_observer','qa.test_cloud_observer_isolation'])
with (P/'observer15-continuation.raw.log').open('x') as log:
 result=unittest.TextTestRunner(stream=log,verbosity=2).run(suite)
results={'observer15':{'discovered':suite.countTestCases(),'tests_run':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'skipped':len(result.skipped),'passed':result.wasSuccessful()}}
# Real native direct-v-wrapper controls, receipts, once execution, independent of repository tests.
signal_script=('import importlib.util,sys;from pathlib import Path;'
 's=importlib.util.spec_from_file_location("o",sys.argv[1]);o=importlib.util.module_from_spec(s);s.loader.exec_module(o);'
 'o.capture_kernel=lambda p:None;o.capture_crashdata=lambda p:None;'
 'o.exit_like_child(o.run_child(sys.argv[3:],Path(sys.argv[2]),interval=.01))')
results['native_signals']=[]
for sig in (signal.SIGTERM,signal.SIGPIPE,signal.SIGKILL):
 with tempfile.TemporaryDirectory() as td:
  child=[sys.executable,'-B','-c','import os,sys,signal;s=int(sys.argv[1]);signal.signal(s,signal.SIG_DFL) if s!=signal.SIGKILL else None;os.kill(os.getpid(),s)',str(int(sig))]
  direct=subprocess.run(child,capture_output=True,timeout=5)
  wrapped=subprocess.run([sys.executable,'-B','-c',signal_script,str(R/'qa/cloud_emulator_observer.py'),str(Path(td)/'output'),*child],capture_output=True,timeout=6)
  results['native_signals'].append({'signal':int(sig),'direct':direct.returncode,'wrapped':wrapped.returncode,'passed':direct.returncode==wrapped.returncode==-int(sig)})
results['receipt_directory_thread_failures']=[]
for fault in ('receipt','directory','thread'):
 for code in (0,7):
  with tempfile.TemporaryDirectory() as td:
   output=Path(td)/'output';marker=Path(td)/'once'
   child=[sys.executable,'-B','-c','from pathlib import Path;import sys;p=Path(sys.argv[1]);p.write_text(p.read_text()+"X" if p.exists() else "X");sys.exit(int(sys.argv[2]))',str(marker),str(code)]
   original_open=Path.open;original_mkdir=Path.mkdir
   def open_fault(path,*a,**k):
    if path.name=='child-exit.json':raise OSError('standards receipt failure')
    return original_open(path,*a,**k)
   def mkdir_fault(path,*a,**k):
    if path==output:raise OSError('standards directory failure')
    return original_mkdir(path,*a,**k)
   injector=patch.object(Path,'open',open_fault) if fault=='receipt' else patch.object(Path,'mkdir',mkdir_fault) if fault=='directory' else patch.object(threading.Thread,'start',side_effect=RuntimeError('standards thread failure'))
   with patch.object(o,'capture_kernel',return_value=None),patch.object(o,'capture_crashdata',return_value=None),injector:
    actual=o.run_child(child,output,interval=.01)
   results['receipt_directory_thread_failures'].append({'fault':fault,'child_exit':code,'returned':actual,'once':marker.read_text(),'passed':actual==code and marker.read_text()=='X'})
# Normal and failed wire plus injected open/mkdir failures (entire original function AST only).
results['wire_controls']=[]
for success in (False,True):
 for fault in ('none','open','mkdir'):
  with tempfile.TemporaryDirectory() as td:
   scope=harvest_scope(td,'run')
   content=b'synthetic payload, not a secret'; archive=io.BytesIO()
   with tarfile.open(fileobj=archive,mode='w') as t:
    entry=tarfile.TarInfo('qa-palette-evidence/run/item.bin');entry.size=len(content);t.addfile(entry,io.BytesIO(content))
   transport=subprocess.CompletedProcess(['adb','shell'],0 if success else 1,archive.getvalue() if success else b'',b'original-error' if not success else b'')
   original_open=Path.open;original_mkdir=Path.mkdir
   def fail_open(path,*a,**k):
    if 'palette-harvest-wire' in path.parts:raise OSError('standards wire open failure')
    return original_open(path,*a,**k)
   def fail_mkdir(path,*a,**k):
    if path.name=='palette-harvest-wire':raise OSError('standards wire mkdir failure')
    return original_mkdir(path,*a,**k)
   injector=patch.object(Path,'open',fail_open) if fault=='open' else patch.object(Path,'mkdir',fail_mkdir) if fault=='mkdir' else patch.object(o,'capture_kernel',return_value=None)
   with patch.object(subprocess,'run',return_value=transport),injector:
    returned=scope['harvest_palettes']()
   mandatory=(scope['palette_target']/'item.bin').read_bytes()==content if success else (Path(td)/'palette-harvest-error.txt').read_text()=='original-error'
   results['wire_controls'].append({'success_tar':success,'fault':fault,'returned':returned,'original_mandatory_io':mandatory,'passed':returned==success and mandatory})
# Source/output roots, ancestors and leaves. All escape targets are synthetic and under evidence scratch.
results['crash_boundary']=[]
for case in ('normal','source-root-link','source-ancestor-link','source-directory-link','source-leaf-link','source-hardlink','output-root-link','output-ancestor-link','output-directory-link','output-leaf-link','output-hardlink','unapproved-log'):
 with tempfile.TemporaryDirectory() as td:
  base=Path(td); real=base/'real';real.mkdir(); root=real/'android-runner';root.mkdir();output=base/'output';output.mkdir();outside=base/'outside';outside.mkdir()
  payload=b'synthetic outside bytes - not credentials';safe=b'normal emulator crash fixture'
  source=root/'emu-crash-test.db';source.write_bytes(safe);target=output/'emulator-crashdata'/'emu-crash-test.db';expected_safe=case=='normal'
  if case=='source-root-link':
   (outside/'emu-crash-test.db').write_bytes(payload);link=base/'linked-root';link.symlink_to(outside);root=link
  elif case=='source-ancestor-link':
   source.write_bytes(payload);link=base/'ancestor';link.symlink_to(real);root=link/'android-runner'
  elif case=='source-directory-link':
   source.unlink();(outside/'emu-crash-test.db').write_bytes(payload);(root/'nested').symlink_to(outside);target=output/'emulator-crashdata'/'nested'/'emu-crash-test.db'
  elif case=='source-leaf-link':source.unlink();external=outside/'private.txt';external.write_bytes(payload);source.symlink_to(external)
  elif case=='source-hardlink':source.unlink();external=outside/'private.txt';external.write_bytes(payload);native_link(external,source)
  elif case=='unapproved-log':source.unlink();(root/'capture.log').write_bytes(payload)
  elif case=='output-root-link':
   output.rmdir();output.symlink_to(outside);target=outside/'emulator-crashdata'/'emu-crash-test.db'
  elif case=='output-ancestor-link':
   output.rmdir();real_output=outside/'output';real_output.mkdir();link=base/'output-ancestor';link.symlink_to(outside);output=link/'output';target=real_output/'emulator-crashdata'/'emu-crash-test.db'
  elif case=='output-directory-link':
   (output/'emulator-crashdata').symlink_to(outside);target=outside/'emu-crash-test.db'
  elif case in ('output-leaf-link','output-hardlink'):
   (output/'emulator-crashdata').mkdir();external=outside/'private.txt';external.write_bytes(payload)
   if case=='output-leaf-link':target.symlink_to(external)
   else:native_link(external,target)
  original=o.Path
  def redirect(value):return root if str(value)=='/tmp/android-runner' else original(value)
  error=None
  with patch.object(o,'Path',redirect):
   try:o.capture_crashdata(output)
   except Exception as ex:error=type(ex).__name__+': '+str(ex)
  changed=(outside/'private.txt').read_bytes()!=payload if (outside/'private.txt').is_file() else False
  copied=target.is_file() and not target.is_symlink() and target.read_bytes()==(safe if expected_safe or case.startswith('output') else payload)
  accepted=(output/'crashdata-index.json').is_file()
  if case=='normal':passed=copied and accepted and not error
  elif case in ('source-ancestor-link','output-ancestor-link','output-root-link','output-directory-link','source-root-link','source-directory-link','source-leaf-link','source-hardlink','unapproved-log'):passed=not copied and not changed
  else:passed=not changed and error is not None
  results['crash_boundary'].append({'case':case,'exception':error,'copied_expected_bytes':copied,'index_written':accepted,'outside_changed':changed,'passed':passed})
# CI guard is mocked and cannot contact a real adb.
results['cloud_guard']=[]
for stdout in ('List of devices attached\nemulator-5554\tdevice\n','List of devices attached\nphone123\tdevice\n','List of devices attached\nemulator-5554\tdevice\nemulator-5556\tdevice\n'):
 with patch.dict(os.environ,{'GITHUB_ACTIONS':'true','CI':'true'}),patch.object(o.subprocess,'run',return_value=subprocess.CompletedProcess(['adb','devices'],0,stdout,'')):
  try:ret=o.verify_cloud_emulator();err=None
  except Exception as e:ret=None;err=type(e).__name__
 results['cloud_guard'].append({'fixture':stdout,'accepted':ret is not None,'error':err})
results['actual_adb_or_kernel_calls']=0
results['scope']='HOST only, temporary synthetic bytes inside standards-probes/scratch; no config/product/test mutations or real adb'
with (P/'independent-probes-continuation.json').open('x') as f:json.dump(results,f,ensure_ascii=False,indent=2);f.write('\n')
failures=[row for row in results['crash_boundary'] if not row['passed']]
print(json.dumps({'observer15':results['observer15'],'native_signals':results['native_signals'],'boundary_failures':failures,'all_other_controls_passed':all(x['passed'] for k in ('wire_controls','receipt_directory_thread_failures','native_signals') for x in results[k]),'evidence':str(P/'independent-probes-continuation.json')},ensure_ascii=False))
