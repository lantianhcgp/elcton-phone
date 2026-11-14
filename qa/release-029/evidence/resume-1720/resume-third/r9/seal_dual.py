#!/usr/bin/env python3
"""Seal independent verdicts only when every actual input/raw binding matches."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

p = argparse.ArgumentParser()
p.add_argument('--review', required=True)
a = p.parse_args()
root = Path.cwd()
review = root / a.review
h = lambda b: hashlib.sha256(b).hexdigest()
canon = lambda mapping: h(json.dumps(mapping, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode())
prepare = json.loads((review / 'prepare.json').read_bytes())
manifest = json.loads((review / 'reviewed-manifest.json').read_bytes())
products = json.loads((review / 'product-manifest.json').read_bytes())
for mapping, count_key, sha_key in [(manifest, 'reviewed_files', 'reviewed_manifest_sha256'),
                                    (products, 'product_files', 'product_manifest_sha256')]:
    assert len(mapping) == prepare[count_key] and canon(mapping) == prepare[sha_key]
    for path, digest in mapping.items():
        assert h((root / path).read_bytes()) == digest, 'Current reviewed byte drift: ' + path
raw_diff = (review / 'current.diff').read_bytes()
assert h(raw_diff) == prepare['diff_sha256'] and len(raw_diff) == prepare['diff_bytes']
axes = []
for axis in ('spec', 'standards'):
    raw = (review / (axis + '-raw.txt')).read_bytes()
    report = json.loads(raw)
    blockers = [report[key] for key in ('security_concerns', 'logic_errors', 'missing_requirements')]
    assert report['axis'] == axis
    assert report['passed'] is True and report['passed'] == (not any(blockers)), 'Not a consistent PASS'
    binding = report.get('bindings', {})
    for key in ('reviewed_manifest_sha256', 'diff_sha256'):
        assert report.get(key, binding.get(key)) == prepare[key], axis + ' stale binding: ' + key
    product_sha = report.get('product_manifest_sha256', report.get('source_manifest_sha256', binding.get('product_manifest_sha256')))
    if product_sha is not None:
        assert product_sha == prepare['product_manifest_sha256'], 'Product compact binding drift'
    else:
        supplied = report.get('product_sha256', report.get('product_fingerprints', {}))
        assert supplied == products and len(supplied) == len(products), 'Every product fingerprint must match'
    axes.append({'axis': axis, 'raw_sha256': h(raw), 'passed': True})
receipt = {'passed': True, 'head_at_review': subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
           'reviewed_files': len(manifest), 'product_files': len(products), 'axes': axes,
           'bindings': prepare, 'scope': 'Independent current source+QA identity/review, NOT cloud/physical acceptance'}
with (review / 'dual-closure.json').open('x') as file:
    json.dump(receipt, file, indent=2)
    file.write('\n')
print(json.dumps({k: v for k, v in receipt.items() if k != 'bindings'}))
