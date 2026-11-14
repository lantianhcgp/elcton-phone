#!/usr/bin/env python3
"""Exact run-attempt artifact fetch; saves actual originals, never creates acceptance."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import zipfile
from urllib.parse import urlsplit, unquote
import requests

p = argparse.ArgumentParser()
p.add_argument('--run', required=True)
p.add_argument('--sha', required=True)
p.add_argument('--kind', choices=('build', 'android'), required=True)
p.add_argument('--out', required=True)
a = p.parse_args()
repo = 'lantianhcgp/elcton-phone'
out = Path(a.out)
out.mkdir(parents=True, exist_ok=False)

def save(name, value):
    with (out / name).open('x') as file:
        json.dump(value, file, ensure_ascii=False, indent=2)
        file.write('\n')

def api(path):
    done = subprocess.run(['gh', 'api', 'repos/' + repo + path], capture_output=True, timeout=55)
    done.check_returncode()
    return json.loads(done.stdout)

run = api('/actions/runs/' + a.run)
assert str(run['id']) == a.run and run['head_sha'] == a.sha and run['status'] == 'completed'
assert run['head_branch'] == 'release/0.2.9-20261114'
if a.kind == 'build':
    assert run['conclusion'] == 'success'
save('run-api.json', run)
attempt = api('/actions/runs/' + a.run + '/attempts/' + str(run['run_attempt']))
assert attempt['head_sha'] == a.sha and attempt['run_attempt'] == run['run_attempt']
assert attempt['status'] == 'completed' and attempt['conclusion'] == run['conclusion']
save('attempt-api.json', attempt)
# Include the familiar read-only receipt consumed by original QA verifiers.
view = subprocess.run(['gh', 'run', 'view', a.run, '--repo', repo, '--json',
                      'databaseId,headSha,status,conclusion,url,jobs,event,workflowName,headBranch'],
                     capture_output=True, timeout=55)
view.check_returncode()
normalized = json.loads(view.stdout)
assert normalized['headSha'] == a.sha and str(normalized['databaseId']) == a.run
save('run-exact.json' if a.kind == 'build' else 'run.json', normalized)
assets = api('/actions/runs/' + a.run + '/artifacts?per_page=100')
assert len(assets['artifacts']) == assets['total_count'], 'Artifact pagination incomplete'
save('artifacts.json', assets)
name = ('android-probe-' if a.kind == 'build' else 'android-ui-') + a.sha
matches = [x for x in assets['artifacts'] if x['name'] == name and not x['expired']
           and x['created_at'] >= attempt['run_started_at']]
assert len(matches) == 1, 'Exact-attempt artifact absent or ambiguous'
asset = matches[0]
assert asset['workflow_run']['id'] == int(a.run) and asset['workflow_run']['head_sha'] == a.sha
save('exact-artifact.json', {'run_id': a.run, 'run_attempt': run['run_attempt'], 'artifact': asset})
# Authenticate only at api.github.com; requests strips auth on cross-host redirects.
key = None
for line in (Path.home() / '.git-credentials').read_text().splitlines():
    parts = urlsplit(line)
    if parts.hostname == 'github.com' and parts.password:
        key = unquote(parts.password)
        break
assert key, 'GitHub credential absent'
response = requests.get('https://api.github.com/repos/' + repo + '/actions/artifacts/' + str(asset['id']) + '/zip',
                        headers={'Author' + 'ization': 'token ' + key,
                                 'Accept': 'application/vnd.github+json'}, stream=True, timeout=(25, 90))
response.raise_for_status()
archive = out / 'artifact-original.zip'
with archive.open('xb') as file:
    for block in response.iter_content(1024 * 1024):
        file.write(block)
response.close()
with zipfile.ZipFile(archive) as captured:
    assert captured.testzip() is None, 'Original artifact ZIP CRC failure'
    for item in captured.infolist():
        name = Path(item.filename)
        assert not name.is_absolute() and '..' not in name.parts, 'Unsafe ZIP member path'
        if item.is_dir():
            continue
        target = out / 'artifact' / name
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open('xb') as file:
            file.write(captured.read(item))
if a.kind == 'build':
    pins = list((out / 'artifact').rglob('source-sha.txt'))
    assert len(pins) == 1 and pins[0].read_text().strip() == a.sha
    assert len(list((out / 'artifact').rglob('elcton-phone-probe.apk'))) == 1
    assert len(list((out / 'artifact').rglob('elcton-ui-tests.apk'))) == 1
rows = {str(path.relative_to(out)): {'bytes': path.stat().st_size,
                                       'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
        for path in out.rglob('*') if path.is_file()}
save('inventory.json', {'fetched': True, 'run': a.run, 'source_sha': a.sha,
                       'run_attempt': run['run_attempt'], 'artifact_id': asset['id'],
                       'conclusion': run['conclusion'], 'inventory': rows})
print(json.dumps({'fetched': True, 'run': a.run, 'run_attempt': run['run_attempt'],
                  'artifact_id': asset['id'], 'files': len(rows), 'conclusion': run['conclusion'],
                  'source_sha': a.sha, 'out': str(out.resolve())}), flush=True)
