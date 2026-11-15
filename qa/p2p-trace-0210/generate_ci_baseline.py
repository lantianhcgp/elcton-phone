#!/usr/bin/env python3
"""Generate one CI-only frozen business baseline class, no callbacks/types duplicated.
The business-only source is pinned to the pre-diagnostic bb26c64 commit.
"""
from pathlib import Path
import hashlib
import json
import subprocess
ROOT = Path(__file__).resolve().parents[2]
BASE = 'bb26c64b67e1cfa7903cd709c2aac482f6490e6b'
SOURCE = 'app/src/main/java/com/hcbiu/elcton/SyncEngine.kt'
raw = subprocess.check_output(['git', 'show', BASE + ':' + SOURCE], cwd=ROOT)
text = raw.decode()
assert text.count('class SyncEngine(') == 1
baseline = 'package com.hcbiu.elcton\n\n' + text[text.index('class SyncEngine('):].replace('class SyncEngine(', 'class P2pTraceBaselineEngine(', 1)
dest = ROOT / 'qa/p2p-trace-0210/r6/fixtures/P2pTraceBaselineEngine.kt'
dest.parent.mkdir(parents=True, exist_ok=True)
with dest.open('x') as file:
    file.write(baseline)
print(json.dumps({'base': BASE, 'baseline_source_sha256': hashlib.sha256(raw).hexdigest(),
                  'generated_path': str(dest), 'generated_sha256': hashlib.sha256(dest.read_bytes()).hexdigest(),
                  'transformation': 'only class rename + package; shared interfaces/imports use real current sources',
                  'scope': 'test-only baseline; no APK product inclusion'}))
