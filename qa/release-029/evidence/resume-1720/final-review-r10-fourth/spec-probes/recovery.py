#!/usr/bin/env python3
"""New continuation, retain both environment-only failure outputs and prior probe bytes."""
import ctypes
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from unittest.mock import patch
R=Path('/data/data/com.termux/files/home/elcton-phone-release-029-20261114')
O=R/'qa/release-029/evidence/resume-1720/final-review-r10-fourth/spec-probes'
scope={};source=(O/'run_probes.py').read_text();exec(compile(source[:source.index("results={'started_at'")],'probe definitions','exec'),scope);load=scope['load']
results={'crash':[],'daemon':[],'security_counterexamples':[],'actual_adb_calls':0,'issues':[]}
for mode in ('normal','source-leaf','source-dir','source-root','output-root','output-dir','output-leaf','unapproved-log'):
    b=O/('crash-'+mode);out=b/'output'
    if mode=='normal':assert (out/'emulator-crashdata/emu-crash-regular.db').read_bytes()==b'normal bounded crash payload'
    elif mode!='output-root':assert not [p for p in out.rglob('*') if p.is_file() and not p.is_symlink() and p.name!='crashdata-index.json']
    else:assert not (b/'outside/emulator-crashdata').exists()
    results['crash'].append({'mode':mode,'verified_prior_real_execution':True})
b=O/'crash-source-hardlink';libc=ctypes.CDLL(None,use_errno=True);link=libc.link;link.argtypes=[ctypes.c_char_p,ctypes.c_char_p];link.restype=ctypes.c_int
rc=link(os.fsencode(b/'outside/fixture'),os.fsencode(b/'allowed/emu-crash-hardlink.db'));errno=ctypes.get_errno()
results['issues'].append({'probe':'hardlink','first_failure':'os.link missing','second_failure':'libc link returned nonzero','retry_rc':rc,'retry_errno':errno,'source_exists':(b/'outside/fixture').exists(),'destination_exists':(b/'allowed/emu-crash-hardlink.db').exists(),'not_claimed_exercised':True})
# Execute only still-unexecuted later probes; earlier files are never overwritten.
continuation=(O/'continuation.py').read_text();tail=continuation[continuation.index('# Truly stuck daemon'):]
exec(compile(tail,'continuation-remaining','exec'),globals())
