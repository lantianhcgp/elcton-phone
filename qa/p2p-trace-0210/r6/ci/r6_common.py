#!/usr/bin/env python3
"""R6 exact identity/readback primitives. No import-time I/O or dispatch."""
import hashlib
import json
from pathlib import Path, PurePosixPath
from typing import Any
import re
import stat
import subprocess
import zipfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
OLD = Path('/data/data/com.termux/files/home/elcton-phone-release-029-20261114')
FOURTH = Path('qa/release-029/evidence/resume-1720/resume-fourth')
REPO = 'lantianhcgp/elcton-phone'
BRANCH = 'diag/p2p-trace-0.2.10-20261115'
CERT = 'fc08a0b474a8ffca5887bd5c88ac15e865a63a64eca81c10f344496c46d9ad94'
PINS = {'verifiers/verify_cloud.py': '1093d106014452ced8eb484034013b1cf9e480c21b2151965aff7649918f64e6',
        'verify_exact_build.py': 'aae2a5419a5e86244618553527f89d50ac112d4a312f4af98b9367f21accfaf1',
        'verify_cloud_snapshot_map.py': '3cd44b787e7804c322a87ced1c6eae67a580680bc66c137290e4307d37641ad3'}

def require(condition, label):
    if not condition: raise AssertionError(label)

def sha40(value):
    require(isinstance(value, str) and re.fullmatch('[0-9a-f]{40}', value), 'Malformed literal source SHA')
    return value

def run_id(value):
    require(isinstance(value, str) and re.fullmatch('[1-9][0-9]*', value), 'Malformed literal run ID')
    return value

def digest(path):
    with Path(path).open('rb') as stream: return hashlib.file_digest(stream, 'sha256').hexdigest()

def read_json(path):
    def unique(pairs):
        out = {}
        for k, v in pairs:
            require(k not in out, 'Duplicate JSON key: ' + k); out[k] = v
        return out
    return json.loads(Path(path).read_bytes(), object_pairs_hook=unique,
                      parse_constant=lambda x: (_ for _ in ()).throw(ValueError(x)))

def save(directory, name, data):
    with (Path(directory) / name).open('x') as stream:
        json.dump(data, stream, indent=2, ensure_ascii=False, allow_nan=False); stream.write('\n')

def new_out(path):
    require('..' not in Path(path).parts, 'Output parent traversal refused')
    path = Path(path).absolute()
    require(path.is_relative_to(HERE) and path != HERE, 'New output must be below exclusive R6 ci directory')
    require(not any(p.is_symlink() for p in (path, *path.parents)), 'Symlink output refused')
    path.mkdir(parents=True, exist_ok=False)
    return path

def original(name):
    path = OLD / FOURTH / name
    require(name in PINS and digest(path) == PINS[name], 'Original criterion fingerprint changed: ' + str(path))
    return path.read_text()

def inventory(directory):
    directory = Path(directory)
    require(directory.is_dir() and not directory.is_symlink(), 'Input root must be a real directory')
    rows = {}
    for p in sorted(directory.rglob('*')):
        require(not p.is_symlink(), 'Symlink input refused: ' + str(p))
        if p.is_file():
            require(stat.S_ISREG(p.stat().st_mode), 'Nonregular input refused')
            rows[p.relative_to(directory).as_posix()] = {'bytes': p.stat().st_size, 'sha256': digest(p)}
    return rows

def check_cases(actual, original_cases, registered, label='Incomplete or duplicate Gradle tests'):
    a, o, r = [list(map(tuple, group)) for group in (actual, original_cases, registered)]
    require(all(len(x) == 2 and all(isinstance(k, str) and k for k in x) for group in (a, o, r) for x in group), 'Malformed testcase label')
    require(len(o) == len(set(o)) and len(r) == len(set(r)) and len(a) == len(set(a)), 'Incomplete or duplicate Gradle tests')
    require(set(o) <= set(r), 'Original testcase set/labels missing from registered set')
    require(set(a) == set(r) and len(a) == len(r), 'Incomplete or duplicate Gradle tests')

def zip_members(z):
    require(z.testzip() is None, 'Original artifact ZIP CRC failure')
    rows = {}
    for item in z.infolist():
        name = PurePosixPath(item.filename)
        require(not name.is_absolute() and '..' not in name.parts and '\\' not in item.filename and name.parts, 'Unsafe ZIP member path')
        require(not stat.S_ISLNK(item.external_attr >> 16), 'ZIP symlink refused')
        require(item.filename not in rows, 'Duplicate ZIP member')
        rows[item.filename] = item
    return rows

def archive_readback(archive, directory):
    """Stream all ZIP bytes and compare every extracted file; no second copy."""
    rows = {}
    with zipfile.ZipFile(archive) as z:
        for name, item in zip_members(z).items():
            if item.is_dir(): continue
            h = hashlib.sha256(); size = 0
            with z.open(item) as stream:
                while block := stream.read(1024 * 1024): h.update(block); size += len(block)
            rows[name] = {'bytes': size, 'sha256': h.hexdigest()}
    require(rows == inventory(directory), 'Complete ZIP/extracted size/SHA inventory differs')
    return {'archive_bytes': Path(archive).stat().st_size, 'archive_sha256': digest(archive),
            'zip_crc': True, 'files': rows}

def api(path, payload=None) -> Any:
    cmd = ['gh', 'api', 'repos/' + REPO + path]
    if payload is not None: cmd += ['--method', 'POST', '--input', '-']
    result = subprocess.run(cmd, input=None if payload is None else json.dumps(payload).encode(),
                            capture_output=True, timeout=90, cwd=ROOT)
    require(result.returncode == 0, 'gh API failed (credential not printed); exit=' + str(result.returncode))
    return json.loads(result.stdout) if result.stdout.strip() else None

def pages(path, key):
    rows = []; page = 1; total = None
    while True:
        result = api(path + ('&' if '?' in path else '?') + 'per_page=100&page=' + str(page))
        require(total is None or total == result['total_count'], 'API total changed during pagination; retry readback')
        total = result['total_count']; rows += result[key]
        require(len(rows) <= total, 'API enumerated count exceeds total')
        if len(rows) == total: break
        require(result[key], 'API pagination incomplete'); page += 1
    require(len({x['id'] for x in rows}) == total, 'Duplicate/paginated API rows')
    return {'total_count': total, key: rows}

def exact_readback(run, head, workflow, complete=False):
    run_id(run); sha40(head)
    current = api('/actions/runs/' + run)
    require(str(current['id']) == run and current['head_sha'] == head and current['head_branch'] == BRANCH, 'Exact run/head/diag branch mismatch')
    require(current['path'] == '.github/workflows/' + workflow and current['event'] == 'workflow_dispatch', 'Workflow/event mismatch')
    attempt = api('/actions/runs/' + run + '/attempts/' + str(current['run_attempt']))
    for k in ('id', 'head_sha', 'head_branch', 'run_attempt', 'status', 'conclusion'):
        require(attempt[k] == current[k], 'Exact attempt mismatch: ' + k)
    if complete: require(current['status'] == 'completed', 'Run is not complete')
    assets = pages('/actions/runs/' + run + '/artifacts', 'artifacts')
    return {'run-api': current, 'attempt-api': attempt, 'artifacts': assets}

def select_asset(assets, attempt, name, run, head):
    matches = [a for a in assets if a['name'] == name and not a['expired'] and a['created_at'] >= attempt['run_started_at']]
    require(len(matches) == 1, 'Exact-attempt artifact absent or ambiguous: ' + name)
    asset = matches[0]
    require(asset['workflow_run']['id'] == int(run) and asset['workflow_run']['head_sha'] == head, 'Artifact run/workflow-head mismatch')
    return asset

def offline_binding(incoming, run, source, workflow_head, kind):
    run_id(run); sha40(source); sha40(workflow_head)
    incoming = Path(incoming)
    before = inventory(incoming); declared = read_json(incoming / 'inventory.json')
    require({k:v for k,v in before.items() if k != 'inventory.json'} == declared['inventory'], 'ALL fetched files differ from declared size/SHA')
    require(str(declared['run']) == run and declared['source_sha'] == source and declared['workflow_sha'] == workflow_head, 'Fetch identity mismatch')
    current, attempt = read_json(incoming/'run-api.json'), read_json(incoming/'attempt-api.json')
    require(str(current['id']) == run and current['head_sha'] == workflow_head and current['head_branch'] == BRANCH, 'Exact saved run/head/branch mismatch')
    require(current['path'] == '.github/workflows/' + ('build.yml' if kind == 'build' else 'ui-smoke.yml') and current['event'] == 'workflow_dispatch', 'Saved workflow/event mismatch')
    for key in ('id','head_sha','head_branch','run_attempt','status','conclusion'):
        require(current[key] == attempt[key], 'Saved exact attempt mismatch: ' + key)
    require(current['status'] == 'completed' and current['conclusion'] == 'success', 'Saved exact run not completed/success')
    assets = read_json(incoming/'artifacts.json')
    require(len(assets['artifacts']) == assets['total_count'], 'Incomplete saved artifact list')
    selected = read_json(incoming/'exact-artifact.json')
    expected_name = ('android-probe-' if kind == 'build' else 'android-ui-') + workflow_head
    asset = select_asset(assets['artifacts'], attempt, expected_name, run, workflow_head)
    require(asset == selected['artifact'] and selected['run_attempt'] == current['run_attempt'], 'Selected asset identity mismatch')
    archive = archive_readback(incoming/'artifact-original.zip', incoming/'artifact')
    require(archive['archive_bytes'] == asset['size_in_bytes'], 'Remote artifact size differs')
    if asset.get('digest'): require(asset['digest'] == 'sha256:' + archive['archive_sha256'], 'Remote artifact SHA digest differs')
    return before, archive

if __name__ == '__main__':
    import sys
    if sys.argv[1:] == ['--self-test']:
        import self_test
        raise SystemExit(self_test.main())
    raise SystemExit('No actions at this entrypoint; use --self-test')
