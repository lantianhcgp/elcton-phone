#!/usr/bin/env python3
"""Commit the exact dual-reviewed input plus all retained evidence; never pushes itself."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

parser = argparse.ArgumentParser()
parser.add_argument('--review', type=Path, required=True)
parser.add_argument('--out', type=Path, required=True)
args = parser.parse_args()
root = Path.cwd()
review = args.review
out = args.out
out.mkdir(parents=True, exist_ok=False)
closure = json.loads((review / 'dual-closure.json').read_bytes())
assert closure['passed'] is True
manifest = json.loads((review / 'reviewed-manifest.json').read_bytes())
for path, expected in manifest.items():
    assert hashlib.sha256((root / path).read_bytes()).hexdigest() == expected, 'Current reviewed input changed: ' + path
for axis in closure['axes']:
    raw = (review / (axis['axis'] + '-raw.txt')).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == axis['raw_sha256']
    value = json.loads(raw)
    assert value['passed'] is True
    assert all(isinstance(value[key], list) and not value[key] for key in ('security_concerns', 'logic_errors', 'missing_requirements'))
assert subprocess.check_output(['git', 'branch', '--show-current']).decode().strip() == 'release/0.2.9-20261114'
# Only recorded QA changes and evidence may differ from the previously pushed source.
changed = subprocess.check_output(['git', 'diff', '--name-only', 'HEAD', '-z']).split(b'\0')
allowed = {'.github/workflows/ui-smoke.yml', 'qa/cloud_emulator_observer.py', 'qa/emulator_install_and_tour.py',
           'qa/release-029/ANDROID-HARNESS-ATTRIBUTION.md', 'qa/release-029/RESUME-CHANGES.md',
           'qa/test_cloud_observer.py', 'qa/test_cloud_observer_isolation.py',
           'qa/test_cloud_observer_crash_containment.py', 'qa/test_cloud_observer_crash_limits.py'}
assert all(not row or row.decode() in allowed or row.decode().startswith('qa/release-029/evidence/') for row in changed), 'Unexpected current scope change'
subprocess.run(['git', 'add', '--', '.'], check=True, timeout=240)
# No source/fixture/receipt content conversion at the index boundary.
for path, expected in manifest.items():
    assert hashlib.sha256(subprocess.check_output(['git', 'show', ':' + path])).hexdigest() == expected, 'Staged reviewed input differs: ' + path
command = ['git', 'commit', '-m', 'fix(qa): isolate and bound cloud emulator observation for 0.2.9']
with (out / 'actual.log').open('xb') as stream:
    result = subprocess.run(command, stdout=stream, stderr=subprocess.STDOUT, timeout=300)
(out / 'actual.exit').open('x').write(str(result.returncode) + '\n')
result.check_returncode()
sha = subprocess.check_output(['git', 'rev-parse', 'HEAD']).decode().strip()
for path, expected in manifest.items():
    assert hashlib.sha256(subprocess.check_output(['git', 'show', sha + ':' + path])).hexdigest() == expected
receipt = {'passed': True, 'source_sha': sha, 'reviewed_files': len(manifest),
           'scope': 'exact current reviewed committed bytes; push/build/cloud/delivery pending',
           'dual_closure_sha256': hashlib.sha256((review / 'dual-closure.json').read_bytes()).hexdigest()}
(out / 'receipt.json').open('x').write(json.dumps(receipt, indent=2) + '\n')
print(json.dumps(receipt), flush=True)
