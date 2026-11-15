#!/usr/bin/env python3
"""R7 cached baseline corroboration: no repeated 2GB content hash; explicit limits."""
import argparse
import ast
import hashlib
import json
from pathlib import Path
import subprocess
import time

ROOT = Path(__file__).resolve().parents[2]
QA = Path(__file__).resolve().parent
Q = QA / 'r6'
BASE = 'bb26c64b67e1cfa7903cd709c2aac482f6490e6b'
PRIOR = Q / 'evidence/frozen-scope-q1-1650/receipt.json'
PRIOR_SHA = '827f1404da0ee56361c5d93e0f8ded1f1cb16b3ed4fa48d765c483dcea3740c3'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT, timeout=90)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    assert '..' not in args.out.parts
    out = args.out.absolute()
    assert not any(p.is_symlink() for p in (out, *out.parents))
    out = out.resolve()
    assert out != (Q / 'evidence').resolve() and out.is_relative_to((Q / 'evidence').resolve())
    assert not out.exists()
    prior_raw = PRIOR.read_bytes()
    assert sha(prior_raw) == PRIOR_SHA
    prior = json.loads(prior_raw)
    assert prior['base'] == BASE and prior['base_entries'] == 9461
    for key in ('all_other_base_entries_unchanged', 'all_original_sourcegate_predicates_byte_identical',
                'original_business_assertions_byte_identical', 'workflow_bytes_frozen'):
        assert prior[key] is True
    tree = json.loads((Q / 'evidence/before/base-tree.json').read_bytes())
    assert tree['base'] == BASE and len(tree['entries']) == 9461
    declared = {r['path']: (r['mode'], r['oid']) for r in tree['entries']}
    assert len(declared) == 9461
    actual = {}
    for row in git('ls-tree', '-rz', BASE).split(b'\x00'):
        if not row:
            continue
        info, path = row.split(b'\t', 1)
        mode, kind, oid = info.decode().split()
        assert kind == 'blob'
        actual[path.decode()] = (mode, oid)
    assert actual == declared, 'Original tree record differs from Git baseline'
    assert all((ROOT / p).exists() or (ROOT / p).is_symlink() for p in declared)
    diff_paths = set(git('diff', '--name-only', '-z', BASE).decode().split('\x00')) - {''}
    product = set(prior['allowed_diagnostic_paths'])
    expected = product | set(prior['literal_migrations']) | {prior['allowed_identity_gate_path']}
    assert (diff_paths & set(declared)) == expected, 'Unauthorized tracked baseline drift'
    identity = json.loads((Q / 'current-identity.json').read_bytes())
    for path, row in identity['source_identities'].items():
        assert sha((ROOT / path).read_bytes()) == row['current_sha256']
    inverses = {}
    for path, record in prior['literal_migrations'].items():
        raw = (ROOT / path).read_bytes()
        assert sha(raw) == record['current_sha256']
        reverted = raw
        for change in record['counts']:
            assert reverted.count(change['new'].encode()) == change['count']
            reverted = reverted.replace(change['new'].encode(), change['old'].encode())
        original = git('show', BASE + ':' + path)
        assert reverted == original and sha(original) == record['old_sha256']
        inverses[path] = {'current_sha256': sha(raw), 'reverse_sha256': sha(reverted),
                          'all_nonliteral_bytes_identical': True}
    for path, record in prior['old_test_files'].items():
        assert sha((ROOT / path).read_bytes()) == record['current_sha256']
    inventory = json.loads((QA / 'baseline.json').read_bytes())['old_tests']
    assert isinstance(inventory, dict)
    original_tests = {}
    for path, record in inventory.items():
        raw = (ROOT / path).read_bytes()
        for change in prior['literal_migrations'].get(path, {}).get('counts', []):
            raw = raw.replace(change['new'].encode(), change['old'].encode())
        old_sha = record if isinstance(record, str) else record['sha256']
        assert sha(raw) == old_sha
        original_tests[path] = old_sha
    tests = sorted((ROOT / 'app/src/test/java/com/hcbiu/elcton').glob('*Test.kt'))
    assert len(tests) == prior['current_test_classes'] == 35
    gate = (ROOT / prior['allowed_identity_gate_path']).read_bytes()
    left = gate.index(b'# R6 migrates ONLY the current identity data')
    right = gate.index(b'def reverse_exact(text, path):', left)
    assert gate[:left] + gate[right:] == git('show', BASE + ':' + prior['allowed_identity_gate_path'])
    fixture = (Q / 'fixtures/P2pTraceBaselineEngine.kt').read_bytes()
    assert sha(fixture) == prior['new_test_only_baseline_sha256']
    workflows = {p: sha((ROOT / p).read_bytes()) for p in ('.github/workflows/build.yml', '.github/workflows/ui-smoke.yml')}
    for path in workflows:
        assert (ROOT / path).read_bytes() == git('show', BASE + ':' + path)
    git('diff', '--check')
    result = {'passed': True, 'base': BASE, 'baseline_entries': 9461,
              'prior_full_content_receipt_sha256': PRIOR_SHA, 'baseline_rehashed_this_run': False,
              'verification_method': 'Exact original Git tree + current Git tracked diff/cache + every small frozen test/source/literal inverse; prior full-content receipt inherited',
              'limitation': 'Not a fresh full-content hash of the 2GB baseline; Git status/cache used per explicit R7 no-repeat-hash constraint',
              'baseline_changed_paths': sorted(expected), 'literal_migrations': inverses,
              'original_test_files': original_tests, 'current_test_classes': 35,
              'all_nonliteral_behavior_assertions_identical': True, 'source_identities': identity['source_identities'],
              'workflow_sha256': workflows, 'devices': [], 'watch_writes': [], 'haps': [],
              'at': time.strftime('%Y-%m-%d %H:%M:%S %z')}
    out.mkdir(parents=True, exist_ok=False)
    with (out / 'receipt.json').open('x') as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)
        stream.write('\n')
    print(json.dumps({k: result[k] for k in ('passed', 'baseline_entries', 'current_test_classes', 'baseline_rehashed_this_run', 'verification_method')}, ensure_ascii=False))


if __name__ == '__main__':
    main()
