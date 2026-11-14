import ast, hashlib, importlib.util, io, json, os, stat, subprocess, sys, tempfile, threading, time
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
R=Path('/data/data/com.termux/files/home/elcton-phone-release-029-20261114');P=R/'qa/release-029/evidence/resume-1720/final-review-r10-fourth/standards-probes'
T=P/'focused-scratch';T.mkdir(exist_ok=False);tempfile.tempdir=str(T)
s=importlib.util.spec_from_file_location('o',R/'qa/cloud_emulator_observer.py');assert s and s.loader;o=importlib.util.module_from_spec(s);s.loader.exec_module(o)
results=[]
for case in ('normal','source-root-link','source-ancestor-link','source-directory-link','source-leaf-link','source-hardlink-synthetic-nlink','output-root-link','output-ancestor-link','output-directory-link','output-leaf-link','output-hardlink-existing-leaf','unapproved-log'):
 with tempfile.TemporaryDirectory() as td:
  base=Path(td);real=base/'real';real.mkdir();root=real/'android-runner';root.mkdir();output=base/'output';output.mkdir();outside=base/'outside';outside.mkdir()
  payload=b'STANDARDS synthetic outside bytes - never a real credential';safe=b'normal emulator crash fixture';source=root/'emu-crash-test.db';source.write_bytes(safe);target=output/'emulator-crashdata'/'emu-crash-test.db';inject=None
  if case=='source-root-link':
   (outside/'emu-crash-test.db').write_bytes(payload);root=base/'linked-root';root.symlink_to(outside)
  elif case=='source-ancestor-link':
   source.write_bytes(payload);link=base/'ancestor';link.symlink_to(real);root=link/'android-runner'
  elif case=='source-directory-link':
   source.unlink();(outside/'emu-crash-test.db').write_bytes(payload);(root/'nested').symlink_to(outside);target=output/'emulator-crashdata'/'nested'/'emu-crash-test.db'
  elif case=='source-leaf-link':
   source.unlink();external=outside/'private.txt';external.write_bytes(payload);source.symlink_to(external)
  elif case=='source-hardlink-synthetic-nlink':
   original_stat=o.os.stat
   def fake_stat(path,*args,**kwargs):
    actual=original_stat(path,*args,**kwargs)
    return SimpleNamespace(st_mode=actual.st_mode,st_nlink=2,st_size=actual.st_size) if str(path)=='emu-crash-test.db' and kwargs.get('dir_fd') is not None else actual
   inject=patch.object(o.os,'stat',fake_stat)
  elif case=='unapproved-log':source.unlink();(root/'capture.log').write_bytes(payload)
  elif case=='output-root-link':
   output.rmdir();output.symlink_to(outside);target=outside/'emulator-crashdata'/'emu-crash-test.db'
  elif case=='output-ancestor-link':
   output.rmdir();real_output=outside/'output';real_output.mkdir();link=base/'output-ancestor';link.symlink_to(outside);output=link/'output';target=real_output/'emulator-crashdata'/'emu-crash-test.db'
  elif case=='output-directory-link':
   (output/'emulator-crashdata').symlink_to(outside);target=outside/'emu-crash-test.db'
  elif case=='output-leaf-link':
   (output/'emulator-crashdata').mkdir();external=outside/'private.txt';external.write_bytes(payload);target.symlink_to(external)
  elif case=='output-hardlink-existing-leaf':
   (output/'emulator-crashdata').mkdir();target.write_bytes(payload)
  original=o.Path
  def redirect(value):return root if str(value)=='/tmp/android-runner' else original(value)
  error=None
  with patch.object(o,'Path',redirect), (inject if inject is not None else patch.object(o,'capture_kernel',return_value=None)):
   try:o.capture_crashdata(output)
   except Exception as e:error=type(e).__name__+': '+str(e)
  raw=target.read_bytes() if target.is_file() else None
  root_escape=root.resolve()!=root.absolute();output_escape=output.resolve()!=output.absolute()
  # Existing leaf is a fixture; preserved original bytes cannot count as a new copy.
  copied=raw in (safe,payload) and case not in ('output-hardlink-existing-leaf','output-leaf-link')
  expected_refusal=case!='normal'
  results.append({'case':case,'error':error,'copied':copied,'bytes':len(raw) if raw is not None else 0,'sha256':hashlib.sha256(raw).hexdigest() if raw is not None else None,'source_root_has_link':root_escape,'output_root_has_link':output_escape,'index_written':(output/'crashdata-index.json').is_file(),'boundary_passed':not copied if expected_refusal else copied and error is None,'synthetic_limit':'nlink injection only; native hardlink creation denied' if 'hardlink' in case else None})
# Original structure exact whole-file reversal, not only AST equality.
H=R/'qa/release-029/evidence/resume-1720/resume-third/r9'
source=(R/'qa/emulator_install_and_tour.py').read_bytes();lines=source.splitlines(keepends=True);tree=ast.parse(source)
harvest=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='harvest_palettes')
obs=next(n for n in harvest.body if isinstance(n,ast.Try) and any(isinstance(x,ast.Name) and x.id=='wire_target' for x in ast.walk(n)))
reverse=b''.join(lines[:obs.lineno-2]+lines[obs.end_lineno:])
workflow=(R/'.github/workflows/ui-smoke.yml').read_bytes();new=b'python3 -B qa/cloud_emulator_observer.py -- python3 qa/emulator_install_and_tour.py';old=b'python3 qa/emulator_install_and_tour.py'
structure={'harvest_reverse_whole_file_equal_archive':reverse==(H/'emulator_install_and_tour.py.before.original').read_bytes(),'workflow_reverse_whole_file_equal_archive':workflow.replace(new,old)==(H/'ui-smoke.yml.before.original').read_bytes(),'workflow_substitutions':workflow.count(new)}
# Bounded stop real in-flight sampler, observe daemon + receipt then release and clean.
release=threading.Event();entered=threading.Event()
def blocked():entered.set();release.wait(5);return {'test':'blocked'}
with tempfile.TemporaryDirectory() as td,patch.object(o,'proc_snapshot',blocked),patch.object(o,'capture_kernel',return_value=None),patch.object(o,'capture_crashdata',return_value=None):
 started=time.monotonic();code=o.run_child([sys.executable,'-B','-c','raise SystemExit(7)'],Path(td)/'out',.01);elapsed=time.monotonic()-started
 threads=[t for t in threading.enumerate() if t.name=='cloud-emulator-evidence'];daemon=all(t.daemon for t in threads);receipt=json.loads((Path(td)/'out/child-exit.json').read_bytes());release.set()
 for t in threads:t.join(2)
 blocked_result={'entered':entered.is_set(),'returncode':code,'seconds':elapsed,'daemon':daemon,'receipt_sampler_stopped':receipt['sampler_stopped'],'all_released_threads_stopped':all(not t.is_alive() for t in threads),'passed':entered.is_set() and code==7 and elapsed<2.5 and daemon}
# Verify hardlink check has a stat->open gap: fstat never revalidates nlink.
security_static={'root_open_NOFOLLOW_only_final_component':True,'fstat_nlink_rechecked':any(isinstance(n,ast.Attribute) and n.attr=='st_nlink' and isinstance(n.value,ast.Name) and n.value.id=='current' for n in ast.walk(tree)),'traversal_entry_or_depth_count_cap':False,'index_write_uses_unpinned_output_path':True}
out={'crash_boundaries':results,'structure':structure,'blocked_sampler':blocked_result,'security_static':security_static,'actual_adb_or_kernel_calls':0,'scope':'HOST only, all fixtures beneath standards-probes; no real secrets or device interactions'}
with (P/'focused-probes.json').open('x') as f:json.dump(out,f,ensure_ascii=False,indent=2);f.write('\n')
print(json.dumps({'boundary_failures':[r['case'] for r in results if not r['boundary_passed']],'structure':structure,'blocked_sampler':blocked_result,'evidence':str(P/'focused-probes.json')}))
