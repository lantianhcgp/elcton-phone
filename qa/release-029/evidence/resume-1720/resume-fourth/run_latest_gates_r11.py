#!/usr/bin/env python3
"""Execute original complete gate entrypoints; immutable new evidence, no acceptance rewrite."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[5]
OUT = Path(__file__).resolve().parent / 'gates-r11'
DEPS = Path.home() / '.hermes/tmp/elcton-jvm-test'
OUT.mkdir(exist_ok=False)
os.chdir(ROOT)
ENV = {**os.environ, 'PYTHONDONTWRITEBYTECODE': '1'}


def save(name, value):
    with (OUT / name).open('x') as file:
        json.dump(value, file, ensure_ascii=False, indent=2)
        file.write('\n')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


inputs = {}
for base in ('app/src/main', 'app/src/test', 'app/src/androidTest', 'qa'):
    for path in (ROOT / base).rglob('*'):
        if path.is_file() and '__pycache__' not in path.parts and '/evidence/' not in path.as_posix():
            inputs[path.relative_to(ROOT).as_posix()] = digest(path)
for name in ('app/build.gradle.kts', '.github/workflows/build.yml', '.github/workflows/ui-smoke.yml'):
    inputs[name] = digest(ROOT / name)
save('inputs-before.json', inputs)


def run(label, command, timeout=240, environment=None):
    started = time.monotonic()
    with (OUT / (label + '.raw.log')).open('xb') as log:
        result = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT,
                                cwd=ROOT, env=environment or ENV, timeout=timeout)
    elapsed = time.monotonic() - started
    row = {'command': command, 'exit_code': result.returncode, 'seconds': elapsed,
           'log_sha256': digest(OUT / (label + '.raw.log'))}
    save(label + '.execution.json', row)
    text = (OUT / (label + '.raw.log')).read_text(errors='replace')
    if result.returncode != 0:
        print(json.dumps({'label': label, **row, 'last_lines': text.splitlines()[-12:]}), flush=True)
        raise SystemExit(result.returncode)
    print(json.dumps({'label': label, 'exit_code': result.returncode, 'seconds': elapsed,
                      'last_lines': text.splitlines()[-3:]}), flush=True)
    return text, row


host, host_execution = run('host', [sys.executable, '-B', 'qa/run_host_tests.py', '--deps', str(DEPS),
                                  '--out', str(OUT / 'host')], timeout=300)
host_match = re.search(r'OK \((\d+) tests\)', host)
assert host_match is not None and int(host_match[1]) == 152, 'Unexpected actual host count'
classpath = str(OUT / 'host/host-tests.jar') + os.pathsep + str(DEPS / 'json.jar')
python_env = {**ENV, 'MCP_HTTP_TEST_CLASSPATH': classpath}
python, python_execution = run('python', [sys.executable, '-B', '-m', 'unittest', 'discover', '-s', 'qa',
                                       '-p', 'test_*.py', '-v'], timeout=420, environment=python_env)
python_match = re.search(r'Ran (\d+) tests? in', python)
assert python_match is not None and re.search(r'^OK\s*$', python, re.MULTILINE), 'Missing complete Python success'
assert not re.search(r'^OK\s*\(', python, re.MULTILINE), 'Skipped/expected-failure unittest footer'
http, http_execution = run('http', [sys.executable, '-B', 'qa/mcp_http_selftest.py', '--classpath', classpath], timeout=180)
http_report = json.loads(http.strip().splitlines()[-1])
assert http_report['ok'] is True and http_report['all_raw_checks_passed'] is True, 'Raw HTTP suite not passed'
runtime, runtime_execution = run('runtime', [sys.executable, '-B', 'qa/run_runtime_revision_host_tests.py',
                                         '--deps', str(DEPS), '--out', str(OUT / 'runtime-r11-fourth')], timeout=240)
assert re.search(r'OK \(1 test\)', runtime), 'Runtime test not completed'
termux, termux_execution = run('termux', [sys.executable, '-B', 'qa/release-029/termux_tools_list.py',
                                       '--classpath', classpath, '--out', str(OUT / 'termux')], timeout=45)
termux_report = json.loads((OUT / 'termux/receipt.json').read_bytes())
assert termux_report['passed'] is True and termux_report['count'] == 15
assert termux_report['http_status'] == 200 and termux_report['listener_closed_after_test'] is True
assert all(digest(ROOT / path) == value for path, value in inputs.items()), 'Gate inputs changed while running'
receipt = {'passed': True, 'checked_at': datetime.datetime.now().astimezone().isoformat(),
           'head': subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
           'host_tests': int(host_match[1]), 'python_tests': int(python_match[1]), 'python_skipped': 0,
           'http_report': http_report, 'runtime_tests': 1,
           'termux': {'count': 15, 'http_status': 200, 'listener_closed': True},
           'inputs_unchanged': True, 'inputs_manifest_sha256': digest(OUT / 'inputs-before.json'),
           'scope': 'complete current HOST gates only; NOT Android CI/cloud/physical WE acceptance'}
save('complete.json', receipt)
print(json.dumps(receipt, ensure_ascii=False), flush=True)

