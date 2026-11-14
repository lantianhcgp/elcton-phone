#!/usr/bin/env python3
"""Continue original cloud predicates with complete immutable-file hardlink snapshot.
Only snapshot transport changes: no second 600MB copy, constant-memory SHA256.
Acceptance methods/thresholds/JSON comparisons are loaded verbatim, never changed.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import stat
import sys

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('original_cloud_verifier_immutable', HERE / 'verifiers/verify_cloud.py')
assert spec and spec.loader
M = importlib.util.module_from_spec(spec)
spec.loader.exec_module(M)


def digest(path):
    with Path(path).open('rb') as file:
        return hashlib.file_digest(file, 'sha256').hexdigest()


def inventory(directory):
    result = {}
    for path in sorted(directory.rglob('*')):
        M.require(not path.is_symlink(), 'Symlink artifact input refused')
        if path.is_file():
            M.require(stat.S_ISREG(path.stat().st_mode), 'Nonregular artifact input')
            result[path.relative_to(directory).as_posix()] = {'bytes': path.stat().st_size, 'sha256': digest(path)}
    return result


class ContinuationGate(M.Gate):
    def snapshot(self):
        before = inventory(self.args.incoming)
        declared = M.read_json(self.args.incoming / 'inventory.json')
        M.require(declared['source_sha'] == self.args.source and str(declared['run']) == self.args.run,
                  'Fetch inventory identity mismatch')
        M.compare({k: v for k, v in before.items() if k != 'inventory.json'}, declared['inventory'], 'ALL fetched files before')
        raw = self.out / 'raw'
        raw.mkdir()
        for path in sorted(self.args.incoming.rglob('*')):
            M.require(not path.is_symlink(), 'Symlink artifact input refused')
            if path.is_file():
                target = raw / path.relative_to(self.args.incoming)
                target.parent.mkdir(parents=True, exist_ok=True)
                os.link(path, target, follow_symlinks=False)
        linked = inventory(raw)
        M.compare(linked, before, 'ALL snapshot files exact SHA/bytes')
        self.write('input-inventory.json', before)
        self.art = raw / 'artifact'
        self.before = before
        return {'raw_files': len(before), 'snapshot': str(raw),
                'scope': 'Native same-byte hardlink snapshot of original complete isolated files; all SHA256/bytes checked, no links followed'}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', required=True)
    parser.add_argument('--run', required=True)
    parser.add_argument('--suite', choices=('diagnostics', 'full'), required=True)
    parser.add_argument('--incoming', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    args.incoming = args.incoming.resolve(); args.out = args.out.resolve()
    M.require(len(args.source) == 40 and all(c in '0123456789abcdef' for c in args.source), 'Invalid source SHA')
    M.require(args.run.isdecimal() and not args.run.startswith('0'), 'Invalid run')
    M.require(args.out.is_relative_to(M.ROOT / 'qa/release-029/evidence'), 'Output outside evidence')
    M.require(not args.out.is_relative_to(args.incoming) and not args.incoming.is_relative_to(args.out), 'Overlapping input/output')
    args.out.mkdir(parents=True, exist_ok=False)
    gate = ContinuationGate(args)
    gate.write('execution.json', {'argv':sys.argv, 'source':args.source, 'run':args.run, 'suite':args.suite,
                                'incoming':str(args.incoming), 'out':str(args.out), 'python':sys.version,
                                'original_tool_sha256':digest(HERE / 'verifiers/verify_cloud.py'),
                                'continuation_tool_sha256':digest(__file__), 'scope':'HOST ONLY, no adb/network/CI/device'})
    methods = ('clients', 'diagnostics', 'background', 'full', 'tour', 'check', 'write')
    M.require(all(getattr(ContinuationGate, name).__code__ is getattr(M.Gate, name).__code__ for name in methods),
              'Original acceptance method changed')
    gate.write('original-method-identity.json', {'passed':True, 'unchanged_code_objects':list(methods),
                                               'original_compare_unchanged':True,
                                               'scope':'Only snapshot() overridden; criteria/flags/thresholds/full JSON comparison unchanged'})
    gate.write('criteria-sha256.json', {name:digest(M.ROOT / 'qa' / (name + '.py')) for name in M.CRITERIA})
    gate.check('input-snapshot-all-bytes', gate.snapshot)
    gate.check('exact-run-success', lambda:M.check_run(M.read_json(args.out / 'raw/run.json'),args.source,args.run))
    gate.check('local-client-raw-logs',gate.clients)
    gate.check(args.suite + '-complete',gate.diagnostics if args.suite == 'diagnostics' else gate.full)
    def final_snapshot_check():
        M.compare(inventory(args.out / 'raw'),gate.before,'ALL snapshot files after original predicates')
        M.compare(inventory(args.incoming),gate.before,'ALL incoming files after original predicates')
        return {'files':len(gate.before),'same_exact_bytes_before_and_after':True}
    gate.check('snapshot-inputs-unchanged-after-original-gates',final_snapshot_check)
    receipt={'passed':not gate.errors,'source_sha':args.source,'run_id':args.run,'suite':args.suite,
             'checks':gate.checks,'errors':gate.errors,'details':gate.details,
             'scope':'All ORIGINAL artifact predicates on all-byte SHA-verified snapshot; first failed copy remains untouched; no product/criteria change',
             'external_binding':'Parent verifies exact actual API/attempt/build inputs/APK binding'}
    gate.write('receipt.json',receipt)
    print(json.dumps({k:v for k,v in receipt.items() if k != 'details'},ensure_ascii=False),flush=True)
    return 0 if receipt['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
