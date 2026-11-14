#!/usr/bin/env python3
"""Continuation: preserve first os.link environment failure; do not edit earlier evidence."""
import ctypes
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from unittest.mock import patch

R=Path('/data/data/com.termux/files/home/elcton-phone-release-029-20261114')
O=R/'qa/release-029/evidence/resume-1720/final-review-r10-fourth/spec-probes'
scope={}
source=(O/'run_probes.py').read_text();exec(compile(source[:source.index("results={'started_at'")],'read-only probe definitions','exec'),scope)
load=scope['load'];crash_probe=scope['crash_probe']
results={'crash':[],'daemon':[],'security_counterexamples':[],'environment_failure_preserved':'independent-execution.json','actual_adb_calls':0}
for mode in ('output-root','output-dir','output-leaf','unapproved-log'):
    results['crash'].append(crash_probe(mode))
# These were executed before the first environment failure; inspect original evidence.
for mode in ('normal','source-leaf','source-dir','source-root'):
    b=O/('crash-'+mode);out=b/'output'
    if mode=='normal':assert (out/'emulator-crashdata/emu-crash-regular.db').read_bytes()==b'normal bounded crash payload'
    else:assert not [p for p in out.rglob('*') if p.is_file() and not p.is_symlink() and p.name!='crashdata-index.json']
    results['crash'].append({'mode':mode,'verified_initial_execution_outputs':True})
# Android CPython omits os.link, so exercise real libc hard-link operation, not a fake stat.
b=O/'crash-source-hardlink';libc=ctypes.CDLL(None,use_errno=True);link=libc.link;link.argtypes=[ctypes.c_char_p,ctypes.c_char_p];link.restype=ctypes.c_int
assert link(os.fsencode(b/'outside/fixture'),os.fsencode(b/'allowed/emu-crash-hardlink.db'))==0,'libc link failed'
m=load();orig=m.Path
with patch.object(m,'Path',side_effect=lambda v:b/'allowed' if str(v)=='/tmp/android-runner' else orig(v)):
    m.capture_crashdata(b/'output')
assert not (b/'output/emulator-crashdata/emu-crash-hardlink.db').exists()
results['crash'].append({'mode':'source-hardlink','real_libc_link':True,'nlink':(b/'allowed/emu-crash-hardlink.db').stat().st_nlink,'copied':False})
# Truly stuck daemon in a real Python process; no release Event hidden in the test.
for target in ('sample','finalizer'):
    b=O/('daemon-'+target);b.mkdir()
    script='''import importlib.util,sys,threading
from pathlib import Path
s=importlib.util.spec_from_file_location('o',sys.argv[1]);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
m.capture_kernel=lambda p:None;m.capture_crashdata=lambda p:None
entered=threading.Event()
def blocked(*a):entered.set();threading.Event().wait();return {}
if sys.argv[3]=='sample':m.proc_snapshot=blocked
else:m.capture_kernel=blocked
code=m.run_child([sys.executable,'-c','raise SystemExit(7)'],Path(sys.argv[2]),interval=.01)
assert entered.is_set();m.exit_like_child(code)
'''
    started=time.monotonic();p=subprocess.run([sys.executable,'-B','-c',script,str(R/'qa/cloud_emulator_observer.py'),str(b/'output'),target],capture_output=True,timeout=5);elapsed=time.monotonic()-started
    (b/'stdout.bin').write_bytes(p.stdout);(b/'stderr.bin').write_bytes(p.stderr)
    assert p.returncode==7
    results['daemon'].append({'target':target,'native_exit':p.returncode,'seconds':elapsed,'bounded_process_exit':True})
# Output ancestor symlink: NOFOLLOW on the leaf is not NOFOLLOW on its ancestors.
b=O/'crash-output-ancestor';b.mkdir();allowed=b/'source';allowed.mkdir();(allowed/'emu-crash-normal.db').write_bytes(b'normal crash fixture')
outside=b/'outside';outside.mkdir();(outside/'output').mkdir();(b/'link-parent').symlink_to(outside,target_is_directory=True);output=b/'link-parent/output';m=load();orig=m.Path
with patch.object(m,'Path',side_effect=lambda v:allowed if str(v)=='/tmp/android-runner' else orig(v)):
    m.capture_crashdata(output)
actual=(outside/'output/emulator-crashdata/emu-crash-normal.db').is_file()
results['security_counterexamples'].append({'case':'output-ancestor-symlink','copy_through_symlink':actual,'actual_resolved_output':str(output.resolve()),'lexical_output':str(output),'no_actual_secret':True})
# Swap output leaf after the directory was pinned: lexical index write follows the new symlink.
b=O/'crash-output-swap-index';b.mkdir();root=b/'source';root.mkdir();(root/'emu-crash-normal.db').write_bytes(b'normal crash fixture');output=b/'output';output.mkdir();outside=b/'outside';outside.mkdir();m=load();orig=m.Path;real_open=m.os.open;swapped=[]
def open_swap(p,flags,*a,**kw):
    fd=real_open(p,flags,*a,**kw)
    if isinstance(p,Path) and p==output and not swapped:
        output.rename(b/'pinned-output');output.symlink_to(outside,target_is_directory=True);swapped.append(True)
    return fd
with patch.object(m,'Path',side_effect=lambda v:root if str(v)=='/tmp/android-runner' else orig(v)),patch.object(m.os,'open',open_swap):
    m.capture_crashdata(output)
results['security_counterexamples'].append({'case':'output-replaced-after-dirfd-open','outside_index_written':(outside/'crashdata-index.json').is_file(),'pinned_copy_exists':(b/'pinned-output/emulator-crashdata/emu-crash-normal.db').is_file(),'no_actual_secret':True})
with (O/'continuation-execution.json').open('x') as f:json.dump(results,f,ensure_ascii=False,indent=2);f.write('\n')
print(json.dumps(results,ensure_ascii=False))
