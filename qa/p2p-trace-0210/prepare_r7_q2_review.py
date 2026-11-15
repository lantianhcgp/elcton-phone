#!/usr/bin/env python3
"""Create an exclusive Q2 snapshot without changing any previous review."""
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
QA = Path(__file__).resolve().parent
REVIEWS = QA / 'r6/reviews'
def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    previous = REVIEWS / 'input-q1/reviewed-manifest.json'
    before = json.loads(previous.read_bytes())
    assert len(before) == 41 and sha(previous) == '93a41045e9896bb419eade7c56cb38242b025cd73604ca9ae28abf2b33327a8d'
    failure = json.loads((REVIEWS / 'r6-quality-q1.json').read_bytes())
    assert failure['passed'] is False and failure['input_manifest_sha256'] == sha(previous)
    assert failure['raw_sha256'] == sha(REVIEWS / 'quality-q1-raw.txt')
    helpers = ['check_r6_scope.py', 'run_r6_final_regressions.py', 'migrate_r6_quality_identity.py']
    expected_changed = {'qa/p2p-trace-0210/' + p for p in helpers}
    changed = {p for p, h in before.items() if sha(ROOT / p) != h}
    assert changed == expected_changed, 'Unapproved Q1 input drift: ' + str(changed)
    extra = [
        'prepare_r7_q2_review.py', 'finalize_r6_delivery.py', 'close_r6_reviews.py',
        'commit_r6_reviewed.py', 'prepare_r6_publish.py', 'rerun_r7_watch_frozen.py',
        'verify_r7_cached_scope.py', 'R7-AUTHORIZATION-AND-PLAN.md',
        'R7-QUALITY-HELPER-REPAIR-SCOPE.md', 'r6/reviews/Q2-REVIEW-SCOPE.md',
        'r6/helper-repair-host/test_helper_repair.py',
        'r6/helper-repair-host/test_finalize_output_guard.py',
        'r6/evidence/identity-migration/table.json',
        'r6/evidence/r7-helper-repair/receipt.json', 'r6/evidence/r7-helper-repair/recovery.json',
        'r6/evidence/r7-helper-repair/before-bindings.json',
        'r6/evidence/r7-helper-repair/red.raw.log', 'r6/evidence/r7-helper-repair/green.raw.log',
        'r6/evidence/r7-delivery-helper-guard/receipt.json',
        'r6/evidence/r7-delivery-helper-guard/red.raw.log',
        'r6/evidence/r7-delivery-helper-guard/green.raw.log',
        'r6/evidence/r7-scope-cache-check/receipt.json',
    ]
    paths = set(before) | {'qa/p2p-trace-0210/' + p for p in extra}
    snapshot = REVIEWS / 'input-q2'
    current = {}
    for path in sorted(paths):
        f = ROOT / path
        assert f.is_file() and not f.is_symlink(), path
        current[path] = sha(f)
    snapshot.mkdir(exist_ok=False)
    (snapshot / 'reviewed-manifest.json').write_text(json.dumps(current, indent=2) + '\n')
    delta = {'previous_manifest_sha256': sha(previous), 'current_manifest_sha256': sha(snapshot / 'reviewed-manifest.json'),
             'unchanged_prior_inputs': sorted(set(before) - changed),
             'changed_prior_inputs': sorted(changed), 'new_inputs': sorted(set(current) - set(before)),
             'input_files': len(current), 'four_product_changes': 0,
             'historical_review_edits': False, 'scope': 'Fresh helper-only Q2 review snapshot; no test execution'}
    (snapshot / 'Q2-DELTA.json').write_text(json.dumps(delta, indent=2) + '\n')
    with (snapshot / 'current-helper.diff').open('wb') as stream:
        subprocess.run(['git', 'diff', 'HEAD', '--', *sorted(expected_changed), 'qa/p2p-trace-0210/finalize_r6_delivery.py', 'qa/p2p-trace-0210/close_r6_reviews.py'], cwd=ROOT, stdout=stream, check=True)
    print(json.dumps({'frozen': True, 'inputs': len(current), 'manifest_sha256': delta['current_manifest_sha256'], 'changed_prior_inputs': sorted(changed), 'out': str(snapshot)}))

if __name__ == '__main__':
    main()
