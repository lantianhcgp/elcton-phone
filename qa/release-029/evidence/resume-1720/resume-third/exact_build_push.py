#!/usr/bin/env python3
"""Push only a committed, fully bound and independently approved R8 candidate."""
import hashlib
import json
from pathlib import Path
import subprocess

D = Path(__file__).resolve().parent
R = D.parents[4]
REVIEW = D.parent / 'final-review-r8'
REPO = 'lantianhcgp/elcton-phone'
BRANCH = 'release/0.2.9-20261114'


def run(argv, **kwargs):
    r = subprocess.run(argv, capture_output=True, cwd=R, timeout=180, **kwargs)
    if r.returncode:
        raise RuntimeError('Command failed: ' + argv[0] + ' exit=' + str(r.returncode))
    return r.stdout


def h(b):
    return hashlib.sha256(b).hexdigest()


closure = json.loads((REVIEW / 'dual-closure.json').read_bytes())
if closure.get('passed') is not True:
    raise RuntimeError('Independent dual-axis closure is not PASS')
manifest = json.loads((REVIEW / 'reviewed-manifest.json').read_bytes())
for p, expected in manifest.items():
    if h((R / p).read_bytes()) != expected:
        raise RuntimeError('Reviewed file drift: ' + p)
sha = run(['git', 'rev-parse', 'HEAD']).decode().strip()
if run(['git', 'branch', '--show-current']).decode().strip() != BRANCH:
    raise RuntimeError('Wrong branch')
if run(['git', 'diff', '--name-only']) or run(['git', 'diff', '--cached', '--name-only']):
    raise RuntimeError('Tracked worktree/index must be clean')
for p, expected in manifest.items():
    if h(run(['git', 'show', sha + ':' + p])) != expected:
        raise RuntimeError('Committed source does not match review: ' + p)
for row in closure['axes']:
    raw = REVIEW / (row['axis'] + '-raw.txt')
    if h(raw.read_bytes()) != row['raw_sha256']:
        raise RuntimeError('Independent raw verdict drift')
print(json.dumps({'prepared_sha': sha, 'reviewed_files': len(manifest), 'dual_bound': True}), flush=True)
r = subprocess.run(['git', 'push', 'origin', 'HEAD:' + BRANCH], cwd=R, capture_output=True, timeout=240)
(D / 'push-actual.log').open('xb').write(r.stdout + r.stderr)
(D / 'push-actual.exit').open('x').write(str(r.returncode) + '\n')
if r.returncode:
    raise RuntimeError('Push failed; actual output/exit retained')
remote = json.loads(run(['gh', 'api', 'repos/' + REPO + '/git/ref/heads/' + BRANCH]).decode())['object']['sha']
if remote != sha:
    raise RuntimeError('External branch did not read back exact source SHA')
receipt = {'passed': True, 'sha': sha, 'remote_sha': remote, 'reviewed_files': len(manifest), 'dual_closure_sha256': h((REVIEW / 'dual-closure.json').read_bytes()), 'scope': 'source push/readback only; Android acceptance remains pending'}
(D / 'push-readback.json').open('x').write(json.dumps(receipt, indent=2) + '\n')
print(json.dumps(receipt), flush=True)
