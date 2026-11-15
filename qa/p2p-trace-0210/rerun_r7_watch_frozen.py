#!/usr/bin/env python3
"""Read-only frozen watch HOST rerun; outputs only in diagnostic phone worktree."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import time

ROOT = Path(__file__).resolve().parents[2]
Q = Path(__file__).resolve().parent / 'r6'
WATCH = Path.home() / 'we-handshake-repair-20261115-watch'
ORIGINAL = Q / 'evidence/watch-frozen-445/receipt.json'


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    assert '..' not in args.out.parts, 'Output parent traversal refused'
    out = args.out.absolute()
    assert not any(p.is_symlink() for p in (out, *out.parents)), 'Symlink output refused'
    out = out.resolve()
    assert out.is_relative_to((Q / 'evidence').resolve()) and not out.exists() and out != (Q / 'evidence').resolve()
    baseline = json.loads(ORIGINAL.read_bytes())
    assert baseline['exit'] == 0 and baseline['tests'] == baseline['pass'] == 445
    assert baseline['fail'] == baseline['skip'] == 0 and baseline['input_unchanged'] is True
    inputs = baseline['input_hashes']
    assert all(digest(WATCH / p) == h for p, h in inputs.items())
    head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=WATCH).decode().strip()
    assert head == baseline['head']
    argv = baseline['argv']
    assert argv[:3] == ['node', '--test', '--test-reporter=tap']
    tests = [str(p) for p in sorted((WATCH / 'tests').glob('*.test.mjs'))]
    assert argv[3:] == tests
    out.mkdir(parents=True, exist_ok=False)
    start = time.monotonic()
    proc = subprocess.run(['nice', '-n', '10', *argv], cwd=WATCH, capture_output=True)
    with (out / 'watch.raw.tap').open('xb') as file:
        file.write(proc.stdout)
    with (out / 'watch.stderr.log').open('xb') as file:
        file.write(proc.stderr)
    raw = proc.stdout.decode()
    counts = {}
    for key in ('tests', 'pass', 'fail', 'skipped'):
        found = re.findall(r'^# ' + key + r' (\d+)\s*$', raw, re.MULTILINE)
        assert len(found) == 1, 'TAP complete count missing or ambiguous: ' + key
        counts[key] = int(found[0])
    unchanged = all(digest(WATCH / p) == h for p, h in inputs.items())
    passed = proc.returncode == 0 and counts == {'tests': 445, 'pass': 445, 'fail': 0, 'skipped': 0} and unchanged
    row = {'passed': passed, 'exit': proc.returncode, 'argv': ['nice', '-n', '10', *argv],
           'head': head, 'counts': counts, 'input_hashes': inputs, 'input_unchanged': unchanged,
           'original_receipt_sha256': digest(ORIGINAL), 'raw_sha256': digest(out / 'watch.raw.tap'),
           'seconds': time.monotonic() - start,
           'scope': 'Read-only frozen watch HOST445; no source writes, build, device, /haps or physical acceptance'}
    with (out / 'receipt.json').open('x') as file:
        json.dump(row, file, ensure_ascii=False, indent=2)
        file.write('\n')
    print(json.dumps({k: v for k, v in row.items() if k not in ('input_hashes', 'argv')}, ensure_ascii=False))
    assert passed, 'Frozen watch actual rerun failed; original raw preserved'


if __name__ == '__main__':
    main()
