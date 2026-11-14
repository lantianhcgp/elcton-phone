#!/usr/bin/env python3
"""Commit/push ONLY completed evidence/report tail; freeze all reviewed source and fixtures."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

parser = argparse.ArgumentParser()
parser.add_argument('--source', required=True)
parser.add_argument('--review', type=Path, required=True)
parser.add_argument('--out', type=Path, required=True)
args = parser.parse_args()
root = Path.cwd()
out = args.out
out.mkdir(parents=True, exist_ok=False)
manifest = json.loads((args.review / 'reviewed-manifest.json').read_bytes())
closure = json.loads((args.review / 'dual-closure.json').read_bytes())
assert closure['passed'] is True
branch = subprocess.check_output(['git', 'branch', '--show-current']).decode().strip()
assert branch == 'release/0.2.9-20261114'
for path, expected in manifest.items():
    assert hashlib.sha256((root / path).read_bytes()).hexdigest() == expected
    assert hashlib.sha256(subprocess.check_output(['git', 'show', args.source + ':' + path])).hexdigest() == expected
for axis in closure['axes']:
    assert hashlib.sha256((args.review / (axis['axis'] + '-raw.txt')).read_bytes()).hexdigest() == axis['raw_sha256']
allowed = 'qa/release-029/evidence/'
changes = subprocess.check_output(['git', 'diff', '--name-only', 'HEAD', '-z']).split(b'\0')
new = subprocess.check_output(['git', 'ls-files', '--others', '--exclude-standard', '-z']).split(b'\0')
assert all(not p or p.decode().startswith(allowed) for p in changes + new), 'Tail write changed non-evidence scope'
subprocess.run(['git', 'add', '--', allowed], check=True, timeout=240)
assert not subprocess.check_output(['git', 'diff', '--name-only']), 'Unstaged current write left outside tail'
with (out / 'commit.log').open('xb') as stream:
    child = subprocess.run(['git', 'commit', '-m', 'docs(qa): seal 0.2.9 exact cloud acceptance and immutable tail evidence [skip ci]'],
                           stdout=stream, stderr=subprocess.STDOUT, timeout=300)
(out / 'commit.exit').open('x').write(str(child.returncode) + '\n')
child.check_returncode()
sha = subprocess.check_output(['git', 'rev-parse', 'HEAD']).decode().strip()
for path, expected in manifest.items():
    assert hashlib.sha256(subprocess.check_output(['git', 'show', sha + ':' + path])).hexdigest() == expected
with (out / 'push.log').open('xb') as stream:
    child = subprocess.run(['git', 'push', 'origin', 'HEAD:' + branch], stdout=stream, stderr=subprocess.STDOUT, timeout=600)
(out / 'push.exit').open('x').write(str(child.returncode) + '\n')
child.check_returncode()
actual = json.loads(subprocess.check_output(['gh', 'api', 'repos/lantianhcgp/elcton-phone/branches/release%2F0.2.9-20261114']))['commit']['sha']
assert actual == sha
value = {'passed': True, 'evidence_sha': sha, 'build_source_sha': args.source,
         'remote_sha': actual, 'reviewed_source_files_unchanged': len(manifest),
         'scope':'Only completed raw evidence and report changed; exact branch readback; ALL external tail bytes readback still pending'}
(out / 'receipt.json').open('x').write(json.dumps(value, indent=2) + '\n')
print(json.dumps(value), flush=True)
