#!/usr/bin/env python3
"""Verify the actual 0.2.9 binary manifest; signing verification is separate, unchanged."""
import json
import os
from pathlib import Path
import re
import subprocess
import sys

apk, out = map(Path, sys.argv[1:])
aapt = Path(os.environ['ANDROID_HOME']) / 'build-tools/34.0.0/aapt'
result = subprocess.run([str(aapt), 'dump', 'badging', str(apk)], text=True, capture_output=True, check=True)
match = re.search(r"package: name='([^']+)' versionCode='([^']+)' versionName='([^']+)'", result.stdout)
assert match and match.groups() == ('com.hcbiu.elcton', '11', '0.2.9'), 'Final APK binary version mismatch'
report = {'passed': True, 'package': match[1], 'versionCode': int(match[2]), 'versionName': match[3],
          'scope': 'Actual binary APK manifest only; not device/WE acceptance'}
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report))
