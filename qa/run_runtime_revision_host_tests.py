#!/usr/bin/env python3
"""Bounded genuine Runtime race test. Log/BuildConfig adapters are HOST TEST ONLY.
No Android instrumentation/build/notification delivery claim. New evidence directory required.
"""
import argparse
import hashlib
import os
import pathlib
import subprocess
import sys

p = argparse.ArgumentParser()
p.add_argument('--deps', required=True)
p.add_argument('--out', required=True)
p.add_argument('--runtime-source', help='Archived old Runtime source for RED; copied into ignored build dir')
a = p.parse_args()
root = pathlib.Path(__file__).resolve().parents[1]
deps = pathlib.Path(a.deps).resolve()
out = pathlib.Path(a.out).resolve()
out.mkdir(parents=True, exist_ok=False)  # Never overwrite earlier RED/GREEN evidence.
source = root / 'app/src/main/java/com/hcbiu/elcton'
names = ['DiagnosticRuntime', 'WearErrorRecord', 'ErrorJournal', 'McpToken', 'DiagnosticTools', 'DiagnosticMcpServer']
generated = root / '.diag-build' / (out.name + '-generated')
generated.mkdir(parents=True, exist_ok=False)
runtime_source = pathlib.Path(a.runtime_source) if a.runtime_source else source / 'DiagnosticRuntime.kt'
runtime_bytes = runtime_source.read_bytes()
(generated / 'DiagnosticRuntime.kt').write_bytes(runtime_bytes)
for template in sorted((root / 'qa/runtime_revision_host').glob('*.kt.in')):
    (generated / template.name.removesuffix('.in')).write_bytes(template.read_bytes())
files = [source / (n + '.kt') for n in names if n != 'DiagnosticRuntime'] + sorted(generated.glob('*.kt'))
(out / 'DiagnosticRuntime.source.txt').write_bytes(runtime_bytes)
(out / 'DiagnosticRuntimeRevisionTest.source.txt').write_bytes((root / 'qa/runtime_revision_host/DiagnosticRuntimeRevisionTest.kt.in').read_bytes())
(out / 'inputs.sha256').write_text(''.join(hashlib.sha256(f.read_bytes()).hexdigest() + '  ' + str(f.relative_to(root)) + '\n' for f in files))
cp = os.pathsep.join(str(deps / (n + '.jar')) for n in ['json', 'junit', 'hamcrest'])
jar = generated / 'runtime-tests.jar'
commands = [
    ['kotlinc', *map(str, files), '-classpath', cp, '-include-runtime', '-d', str(jar)],
    ['java', '-Ddiag.evidence=' + str(out), '-Ddiag.work=' + str(generated), '-cp', str(jar) + os.pathsep + cp,
     'org.junit.runner.JUnitCore', 'com.hcbiu.elcton.DiagnosticRuntimeRevisionTest'],
]
print('HOST ONLY: real DiagnosticRuntime, Socket and state file; test-only Log/BuildConfig', flush=True)
for label, cmd in zip(['compile', 'junit'], commands):
    result = subprocess.run(cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=90)
    (out / (label + '.log')).write_text(result.stdout)
    (out / (label + '.exit')).write_text(str(result.returncode) + '\n')
    print(result.stdout, flush=True)
    if result.returncode:
        sys.exit(result.returncode)
