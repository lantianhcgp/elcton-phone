#!/usr/bin/env python3
"""Push one exact reviewed committed R9 source; read back external branch before success."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

p = argparse.ArgumentParser()
p.add_argument('--review', required=True)
p.add_argument('--out', required=True)
a = p.parse_args()
root = Path.cwd()
review = root / a.review
out = root / a.out
out.mkdir(exist_ok=False)
repo = 'lantianhcgp/elcton-phone'
branch = 'release/0.2.9-20261114'
h = lambda b: hashlib.sha256(b).hexdigest()

def run(cmd):
    result = subprocess.run(cmd, capture_output=True, timeout=240)
    if result.returncode:
        raise RuntimeError(cmd[0] + ' failed: ' + str(result.returncode))
    return result.stdout

closure = json.loads((review / 'dual-closure.json').read_bytes())
assert closure['passed'] is True
manifest = json.loads((review / 'reviewed-manifest.json').read_bytes())
sha = run(['git', 'rev-parse', 'HEAD']).decode().strip()
assert run(['git', 'branch', '--show-current']).decode().strip() == branch
assert not run(['git', 'diff', '--name-only']) and not run(['git', 'diff', '--cached', '--name-only'])
for path, digest in manifest.items():
    assert h((root / path).read_bytes()) == h(run(['git', 'show', sha + ':' + path])) == digest
for row in closure['axes']:
    assert h((review / (row['axis'] + '-raw.txt')).read_bytes()) == row['raw_sha256']
result = subprocess.run(['git', 'push', 'origin', 'HEAD:' + branch], capture_output=True, timeout=600)
(out / 'actual.stdout.bin').open('xb').write(result.stdout)
(out / 'actual.stderr.bin').open('xb').write(result.stderr)
(out / 'actual.exit').open('x').write(str(result.returncode) + '\n')
result.check_returncode()
remote = json.loads(run(['gh', 'api', 'repos/' + repo + '/git/ref/heads/' + branch]))['object']['sha']
assert remote == sha
receipt = {'passed': True, 'sha': sha, 'remote_sha': remote, 'reviewed_files': len(manifest),
           'dual_closure_sha256': h((review / 'dual-closure.json').read_bytes()), 'scope': 'push/readback only; not cloud acceptance'}
(out / 'receipt.json').open('x').write(json.dumps(receipt, indent=2) + '\n')
print(json.dumps(receipt))
