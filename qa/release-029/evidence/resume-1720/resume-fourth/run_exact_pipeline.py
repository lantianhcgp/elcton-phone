#!/usr/bin/env python3
"""Exact reviewed source CI+two cloud jobs; no local device, no false PASS synthesis.
Push is performed separately only after the actual dual closure is verified.
"""
import argparse
import concurrent.futures
import datetime
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[5]
OLD = ROOT / 'qa/release-029/evidence/resume-1720'
REPO = 'lantianhcgp/elcton-phone'
BRANCH = 'release/0.2.9-20261114'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--sha', required=True)
    parser.add_argument('--review', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    assert len(args.sha) == 40 and all(c in '0123456789abcdef' for c in args.sha)
    out = args.out
    out.mkdir(parents=True, exist_ok=False)
    review = args.review
    closure = json.loads((review / 'dual-closure.json').read_bytes())
    assert closure['passed'] is True
    for axis in closure['axes']:
        assert hashlib.sha256((review / (axis['axis'] + '-raw.txt')).read_bytes()).hexdigest() == axis['raw_sha256']
    manifest = json.loads((review / 'reviewed-manifest.json').read_bytes())
    for path, digest in manifest.items():
        raw = subprocess.check_output(['git', 'show', args.sha + ':' + path], cwd=ROOT)
        assert hashlib.sha256(raw).hexdigest() == digest, 'Committed reviewed input differs: ' + path

    def execute(command, label, timeout):
        start = datetime.datetime.now().astimezone().isoformat()
        print(json.dumps({'stage': label, 'state': 'started', 'at': start}), flush=True)
        with (out / (label + '.log')).open('xb') as stream:
            child = subprocess.run(command, cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT, timeout=timeout)
        receipt = {'command': command, 'started_at': start,
                   'ended_at': datetime.datetime.now().astimezone().isoformat(), 'exit_code': child.returncode,
                   'raw_sha256': hashlib.sha256((out / (label + '.log')).read_bytes()).hexdigest()}
        (out / (label + '.execution.json')).open('x').write(json.dumps(receipt, indent=2) + '\n')
        print(json.dumps({'stage': label, 'state': 'completed', 'exit_code': child.returncode}), flush=True)
        return child.returncode

    def query(command):
        return json.loads(subprocess.check_output(['gh'] + command, cwd=ROOT, timeout=60))

    branch = query(['api', 'repos/' + REPO + '/branches/release%2F0.2.9-20261114'])
    assert branch['commit']['sha'] == args.sha, 'External branch not exact source'
    before = query(['run', 'list', '--repo', REPO, '--workflow', 'build.yml', '--commit', args.sha,
                    '--limit', '30', '--json', 'databaseId,headSha,status,conclusion,url,event'])
    assert len(before) <= 1, 'Ambiguous exact-source build; do not blindly choose latest'
    build_wait = out / 'build-wait'
    rc = execute([sys.executable, '-B', str(OLD / 'ci_exact_wait.py'), '--repo', REPO, '--sha', args.sha,
                  '--workflow', 'build.yml', '--out', str(build_wait), '--seconds', '1500'], 'build-wait', 1600)
    if rc:
        return rc
    build = json.loads((build_wait / 'completed.json').read_bytes())
    assert build['headSha'] == args.sha and build['conclusion'] == 'success'
    build_id = str(build['databaseId'])
    incoming = out / 'build-artifact'
    rc = execute([sys.executable, '-B', str(OLD / 'resume-fourth/fetch_exact_attempt.py'), '--run', build_id,
                  '--sha', args.sha, '--kind', 'build', '--out', str(incoming)], 'build-fetch', 480)
    if rc:
        return rc
    rc = execute([sys.executable, '-B', str(OLD / 'resume-fourth/verify_exact_build.py'), '--incoming', str(incoming),
                  '--run', build_id, '--sha', args.sha, '--out', str(out / 'build-verification')], 'build-verify', 240)
    if rc:
        return rc
    print(json.dumps({'milestone': 'actual-build-verified', 'sha': args.sha, 'build_run': build_id}), flush=True)
    # Register each dispatch sequentially so two concurrent runs with the same SHA are not misattributed.
    registered = {}
    for suite in ('diagnostics', 'full'):
        dispatch = out / (suite + '-dispatch')
        rc = execute([sys.executable, '-B', str(OLD / 'dispatch_android.py'), '--sha', args.sha,
                      '--build', build_id, '--suite', suite, '--api', '33', '--out', str(dispatch)], suite + '-dispatch', 180)
        if rc:
            return rc
        registration = json.loads((dispatch / 'registered.json').read_bytes())
        assert registration['inputs']['qa_suite'] == suite
        assert registration['inputs']['build_sha'] == args.sha and registration['inputs']['build_run'] == build_id
        registered[suite] = str(registration['run']['databaseId'])
    (out / 'cloud-registered.json').open('x').write(json.dumps({'source_sha': args.sha, 'build_run': build_id, 'runs': registered}, indent=2) + '\n')
    print(json.dumps({'milestone': 'both-cloud-runs-registered', 'sha': args.sha, 'runs': registered}), flush=True)

    def cloud(suite, run_id):
        wait = out / (suite + '-wait')
        # A RED is still fetched and independently read; it cannot become a green pipeline receipt.
        rc = execute([sys.executable, '-B', str(OLD / 'ci_exact_wait.py'), '--repo', REPO, '--sha', args.sha,
                      '--workflow', 'ui-smoke.yml', '--run', run_id, '--out', str(wait), '--seconds', '2400'], suite + '-wait', 2500)
        artifact = out / (suite + '-artifact')
        fetch_rc = execute([sys.executable, '-B', str(OLD / 'resume-fourth/fetch_exact_attempt.py'), '--run', run_id,
                            '--sha', args.sha, '--kind', 'android', '--out', str(artifact)], suite + '-fetch', 600)
        if fetch_rc:
            return {'suite': suite, 'run': run_id, 'passed': False, 'wait_exit': rc, 'fetch_exit': fetch_rc}
        verify = out / (suite + '-verification')
        verify_rc = execute([sys.executable, '-B', str(OLD / 'resume-fourth/verifiers/verify_cloud.py'), '--source', args.sha,
                             '--run', run_id, '--suite', suite, '--incoming', str(artifact), '--out', str(verify)], suite + '-verify', 480)
        receipt = json.loads((verify / 'receipt.json').read_bytes())
        return {'suite': suite, 'run': run_id, 'passed': rc == 0 and verify_rc == 0 and receipt['passed'] is True,
                'wait_exit': rc, 'verify_exit': verify_rc, 'receipt': str(verify / 'receipt.json'),
                'receipt_sha256': hashlib.sha256((verify / 'receipt.json').read_bytes()).hexdigest()}

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        futures = {pool.submit(cloud, suite, run): suite for suite, run in registered.items()}
        results = []
        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            results.append(result)
            print(json.dumps({'milestone': 'cloud-independent-result', **result}), flush=True)
    report = {'passed': all(row['passed'] for row in results) and len(results) == 2,
              'source_sha': args.sha, 'build_run': build_id, 'cloud_results': results,
              'physical_device_status': 'pending, owner validation; no device actions',
              'scope': 'Actual exact build and two exact fresh cloud artifacts independently rechecked; delivery/remote tail still pending'}
    (out / 'pipeline-result.json').open('x').write(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(report, ensure_ascii=False), flush=True)
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
