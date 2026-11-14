import ast, hashlib, importlib.util, io, json, os, subprocess, sys, tarfile, tempfile, threading, time, unittest
from pathlib import Path
from unittest.mock import patch
R=Path('/data/data/com.termux/files/home/elcton-phone-release-029-20261114');P=R/'qa/release-029/evidence/resume-1720/final-review-r10-fourth/standards-probes';T=P/'controls-scratch';T.mkdir();tempfile.tempdir=str(T);sys.path.insert(0,str(R))
s=importlib.util.spec_from_file_location('o',R/'qa/cloud_emulator_observer.py');assert s and s.loader;o=importlib.util.module_from_spec(s);s.loader.exec_module(o)
from qa.test_cloud_observer import harvest_scope
results={'fault_controls':[],'wire_controls':[]}
for fault in ('receipt','directory','thread'):
 for code in (0,7):
  with tempfile.TemporaryDirectory() as td:
   output=Path(td)/'out';marker=Path(td)/'once';oldopen=Path.open;oldmkdir=Path.mkdir
   def failopen(path,*a,**k):
    if path.name=='child-exit.json':raise OSError('synthetic receipt failure')
    return oldopen(path,*a,**k)
   def failmkdir(path,*a,**k):
    if path==output:raise OSError('synthetic directory failure')
    return oldmkdir(path,*a,**k)
   injector=patch.object(Path,'open',failopen) if fault=='receipt' else patch.object(Path,'mkdir',failmkdir) if fault=='directory' else patch.object(threading.Thread,'start',side_effect=RuntimeError('synthetic thread start failure'))
   child=[sys.executable,'-B','-c','from pathlib import Path;import sys;p=Path(sys.argv[1]);p.write_text(p.read_text()+"X" if p.exists() else "X");sys.exit(int(sys.argv[2]))',str(marker),str(code)]
   with patch.object(o,'capture_kernel',return_value=None),patch.object(o,'capture_crashdata',return_value=None),injector:ret=o.run_child(child,output,.01)
   results['fault_controls'].append({'fault':fault,'child_exit':code,'returned':ret,'once':marker.read_text(),'passed':ret==code and marker.read_text()=='X'})
for success in (False,True):
 for fault in ('open','mkdir'):
  with tempfile.TemporaryDirectory() as td:
   scope=harvest_scope(td,'run');b=io.BytesIO();raw=b'synthetic payload'
   with tarfile.open(fileobj=b,mode='w') as t:
    e=tarfile.TarInfo('qa-palette-evidence/run/payload.bin');e.size=len(raw);t.addfile(e,io.BytesIO(raw))
   oldopen=Path.open;oldmkdir=Path.mkdir
   def failopen(path,*a,**k):
    if 'palette-harvest-wire' in path.parts:raise OSError('wire open fail')
    return oldopen(path,*a,**k)
   def failmkdir(path,*a,**k):
    if path.name=='palette-harvest-wire':raise OSError('wire mkdir fail')
    return oldmkdir(path,*a,**k)
   result=subprocess.CompletedProcess(['adb','shell'],0 if success else 1,b.getvalue() if success else b'',b'original error')
   with patch.object(subprocess,'run',return_value=result),patch.object(Path,'open',failopen) if fault=='open' else patch.object(Path,'mkdir',failmkdir):ret=scope['harvest_palettes']()
   mandatory=(scope['palette_target']/'payload.bin').read_bytes()==raw if success else (Path(td)/'palette-harvest-error.txt').read_text()=='original error'
   results['wire_controls'].append({'success_tar':success,'fault':fault,'return':ret,'mandatory_original_io':mandatory,'passed':ret==success and mandatory})
# Empty allowed files evade content byte limits: all entries+index continue without an entry cap.
with tempfile.TemporaryDirectory() as td:
 root=Path(td)/'root';root.mkdir();output=Path(td)/'out';output.mkdir()
 for n in range(257):(root/(str(n)+'.dmp')).write_bytes(b'')
 original=o.Path
 with patch.object(o,'Path',lambda x:root if str(x)=='/tmp/android-runner' else original(x)):o.capture_crashdata(output)
 index=json.loads((output/'crashdata-index.json').read_bytes())
 results['zero_size_resource_probe']={'fixture_files':257,'copied_entries':len(index),'total_content_bytes':sum(x['bytes'] for x in index),'index_bytes':(output/'crashdata-index.json').stat().st_size,'no_static_entry_count_depth_or_index_cap':True,'limits':{'file_bytes':o.CRASH_FILE_LIMIT,'total_bytes':o.CRASH_TOTAL_LIMIT},'synthetic_only':True}
# All signals are real children and native wrapper exit, no guard/device execution.
results['native_signals']=[]
script=('import importlib.util,sys;from pathlib import Path;s=importlib.util.spec_from_file_location("o",sys.argv[1]);o=importlib.util.module_from_spec(s);s.loader.exec_module(o);o.capture_kernel=lambda p:None;o.capture_crashdata=lambda p:None;o.exit_like_child(o.run_child(sys.argv[3:],Path(sys.argv[2]),.01))')
for sig in (15,13,9):
 with tempfile.TemporaryDirectory() as td:
  child=[sys.executable,'-B','-c','import signal,os,sys;s=int(sys.argv[1]);signal.signal(s,signal.SIG_DFL) if s!=9 else None;os.kill(os.getpid(),s)',str(sig)]
  direct=subprocess.run(child,capture_output=True,timeout=5).returncode;wrapped=subprocess.run([sys.executable,'-B','-c',script,str(R/'qa/cloud_emulator_observer.py'),str(Path(td)/'out'),*child],capture_output=True,timeout=6).returncode
  results['native_signals'].append({'signal':sig,'direct':direct,'wrapped':wrapped,'passed':direct==wrapped==-sig})
results['actual_adb_or_kernel_calls']=0
with (P/'controls.json').open('x') as f:json.dump(results,f,ensure_ascii=False,indent=2);f.write('\n')
print(json.dumps({'all_controls_passed':all(x['passed'] for k in ('fault_controls','wire_controls','native_signals') for x in results[k]),'zero_size_resource_probe':results['zero_size_resource_probe']}))
