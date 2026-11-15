#!/usr/bin/env python3
"""Exclusive offline helper test receipts; never invoke transport main."""
from pathlib import Path
import hashlib
import json
import os
import re
import subprocess
import sys
import time

Q = Path(__file__).resolve().parent
E = Q.parent
ROOT = E.parents[5]
phase = sys.argv[1]
assert phase in ('red', 'green')
files = [E/'test_finalize_r8_metadata.py', E/'test_dns_parameters.py',
         E/'test_transport_edges.py', E/'test_post_http_status.py',
         Q/'test_http_empty_q1.py']
rows = []
raw_path = Q/(phase+'.raw.log')
json_path = Q/(phase+'.json')
assert not raw_path.exists() and not json_path.exists()
env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
with raw_path.open('x') as raw:
    for path in files:
        argv = [sys.executable, '-B', str(path)]
        started = time.time()
        result = subprocess.run(argv, cwd=ROOT, env=env, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, timeout=30)
        output = result.stdout.decode('utf-8', errors='replace')
        counts = re.findall(r'^Ran (\d+) tests? in ', output, re.MULTILINE)
        assert len(counts) == 1, output
        fixtures = [json.loads(line[line.index('{"accepted"'):]) for line in output.splitlines()
                    if '{"accepted"' in line]
        row = {'file': str(path), 'argv': argv, 'returncode': result.returncode,
               'tests_run': int(counts[0]), 'started_at_epoch': started,
               'completed_at_epoch': time.time(), 'fixtures': fixtures}
        rows.append(row)
        raw.write('ARGV '+json.dumps(argv)+'\n'+output+'\nACTUAL_RETURNCODE '+str(result.returncode)+'\n\n')
        raw.flush()
receipt = {'phase': phase, 'helper_sha256': hashlib.sha256((E/'ui_transport.py').read_bytes()).hexdigest(),
           'raw_log': str(raw_path), 'rows': rows,
           'original_tests_run': sum(row['tests_run'] for row in rows[:-1]),
           'new_tests_run': rows[-1]['tests_run'],
           'total_tests_run': sum(row['tests_run'] for row in rows),
           'actual_returncodes': [row['returncode'] for row in rows],
           'aggregate_returncode': int(any(row['returncode'] != 0 for row in rows))}
with json_path.open('x') as target:
    json.dump(receipt, target, indent=2)
    target.write('\n')
print(json.dumps(receipt, indent=2))
sys.exit(receipt['aggregate_returncode'])
