#!/usr/bin/env python3
"""Q-R6-001 targeted actual JVM Runtime, HOST-only ASM barrier; never a full JVM/CI lane."""
import argparse
import difflib
import hashlib
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import zipfile

p = argparse.ArgumentParser()
p.add_argument('--phase', choices=['red', 'green'], required=True)
p.add_argument('--out', required=True)
p.add_argument('--deps', default='/data/data/com.termux/files/home/.hermes/tmp/elcton-jvm-test')
p.add_argument('--reuse-compiled-red', help='Reuse only pre-fix successful compile; validate all Kotlin input SHAs')
a = p.parse_args()
root = pathlib.Path(__file__).resolve().parents[4]
host = pathlib.Path(__file__).resolve().parent
out = pathlib.Path(a.out).resolve()
assert out.is_relative_to(root / 'qa/p2p-trace-0210/r6/evidence')
assert out.name.startswith('wakeup-')
out.mkdir(exist_ok=False)
gen = out / 'generated'; gen.mkdir()
s = root / 'app/src/main/java/com/hcbiu/elcton'
product = [s / (n + '.kt') for n in ['DiagnosticRuntime', 'P2pTrace', 'PacketIngress', 'PhoneSnapshot', 'Wire', 'WearErrorRecord', 'ErrorJournal', 'McpToken', 'McpToolProvider', 'DiagnosticTools', 'DiagnosticMcpServer']]
legacy = [root / 'qa/runtime_revision_host' / n for n in ['HostBuildConfig.kt.in', 'HostLog.kt.in', 'DiagnosticRuntimeRevisionTest.kt.in']]
legacy.append(root / 'qa/p2p-trace-0210/runtime-fault-host/P2pRuntimeFaultTest.kt.in')
templates = legacy + [host / 'RuntimeWakeupTest.kt.in', host / 'InjectWakeBarrier.java.in', pathlib.Path(__file__).resolve()]
protected = [s / (n + '.kt') for n in ['WearProbe', 'SyncEngine', 'P2pTrace', 'SendAttempts']]
protected += [root / 'app/build.gradle.kts', root / 'qa/p2p-trace-0210/r6/current-identity.json']
inputs = list(dict.fromkeys(product + templates + protected))
sha = lambda f: hashlib.sha256(f.read_bytes()).hexdigest()
receipt = {'phase': a.phase, 'origin': 'host-test', 'root': str(root), 'out': str(out), 'inputs': {str(f): sha(f) for f in inputs}, 'commands': []}
source_dir = out / 'sources'; source_dir.mkdir()
compile_files = []
for f in product:
    (source_dir / (f.name + '.source.txt')).write_bytes(f.read_bytes())
    target = gen / f.name; target.write_bytes(f.read_bytes()); compile_files.append(target)
for f in templates:
    (source_dir / (f.name + '.source.txt')).write_bytes(f.read_bytes())
    if f.name.endswith('.kt.in'):
        target = gen / f.name.removesuffix('.in'); target.write_bytes(f.read_bytes()); compile_files.append(target)
(source_dir / 'protected-hashes.json').write_text(json.dumps({str(f): sha(f) for f in protected}, indent=2) + '\n')
(out / 'source-manifest.json').write_text(json.dumps(receipt, indent=2) + '\n')

def run(name, cmd):
    r = subprocess.run(cmd, cwd=root, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=170)
    (out / (name + '.raw.log')).write_text(r.stdout)
    (out / (name + '.exit.txt')).write_text(str(r.returncode) + '\n')
    receipt['commands'].append({'name': name, 'argv': cmd, 'exit': r.returncode})
    (out / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(name + ': exit=' + str(r.returncode), flush=True)
    if len(r.stdout) <= 12000: print(r.stdout, flush=True)
    else: print(r.stdout[-12000:], flush=True)
    return r

kotlinc_path = shutil.which('kotlinc')
assert kotlinc_path is not None, 'kotlinc is required for actual JVM lane'
k = pathlib.Path(kotlinc_path).resolve().parent.parent
compiler = k / 'lib/kotlin-compiler.jar'
deps = pathlib.Path(a.deps)
cp = os.pathsep.join(str(deps / (n + '.jar')) for n in ['json', 'junit', 'hamcrest'])
jar = out / 'actual-runtime.jar'
(out / 'before-manifest.freeze.json').write_text(json.dumps(receipt, indent=2) + '\n')
if a.reuse_compiled_red:
    assert a.phase == 'red', 'only prerequisite RED compile may be reused'
    prior = pathlib.Path(a.reuse_compiled_red).resolve()
    prior_manifest = json.loads((prior / 'source-manifest.json').read_text())
    for f in product + legacy + [host / 'RuntimeWakeupTest.kt.in']:
        assert prior_manifest['inputs'][str(f)] == sha(f), 'reuse requires exact compiled source/template SHA'
    assert (prior / 'compile.exit.txt').read_text().strip() == '0'
    shutil.copyfile(prior / 'actual-runtime.jar', jar)
    shutil.copyfile(prior / 'compile.raw.log', out / 'compile.raw.log')
    (out / 'compile.exit.txt').write_text('0\n')
    receipt['commands'].append({'name': 'compile', 'exit': 0, 'reused_prerequisite_compile_from': str(prior), 'jar_sha256': sha(jar), 'all_compiled_kotlin_input_sha_equal': True})
    print('compile: reused verified actual pre-fix jar; Kotlin inputs identical', flush=True)
else:
    r = run('compile', ['nice', '-n', '10', 'kotlinc', '-J-Xmx384m', *map(str, compile_files), '-classpath', cp, '-include-runtime', '-d', str(jar)])
    if r.returncode: sys.exit(r.returncode)
java = gen / 'InjectWakeBarrier.java'; java.write_bytes((host / 'InjectWakeBarrier.java.in').read_bytes())
asmclasses = out / 'asm-classes'; asmclasses.mkdir()
r = run('compile-asm', ['javac', '-J-Xmx128m', '-cp', str(compiler), '-d', str(asmclasses), str(java)])
if r.returncode: sys.exit(r.returncode)
original = out / 'DiagnosticRuntime.original.class'
with zipfile.ZipFile(jar) as z: original.write_bytes(z.read('com/hcbiu/elcton/DiagnosticRuntime.class'))
overlay = out / 'host-overlay'; patched = overlay / 'com/hcbiu/elcton/DiagnosticRuntime.class'
r = run('instrument', ['java', '-Xmx128m', '-cp', str(asmclasses) + os.pathsep + str(compiler), 'InjectWakeBarrier', str(original), str(patched), str(out)])
if r.returncode: sys.exit(r.returncode)
for label, path in [('original', str(jar)), ('instrumented', str(overlay) + os.pathsep + str(jar))]:
    r = run(label + '-javap', ['javap', '-c', '-p', '-classpath', path, 'com.hcbiu.elcton.DiagnosticRuntime'])
    if r.returncode: sys.exit(r.returncode)
(out / 'host-bytecode.diff').write_text(''.join(difflib.unified_diff((out / 'original.instructions.txt').read_text().splitlines(True), (out / 'instrumented.instructions.txt').read_text().splitlines(True), fromfile='original', tofile='HOST-barrier')))
(out / 'bytecode-sha.json').write_text(json.dumps({'original_class': sha(original), 'instrumented_class': sha(patched), 'actual_runtime_jar': sha(jar), 'instruction_inverse_equal': sha(out / 'original.instructions.txt') == sha(out / 'inverse.instructions.txt')}, indent=2) + '\n')
work = out / 'wakeup-work'; work.mkdir()
r = run('wakeup-junit', ['java', '-Xmx128m', '-Ddiag.evidence=' + str(out), '-Ddiag.work=' + str(work), '-cp', str(overlay) + os.pathsep + str(jar) + os.pathsep + cp, 'org.junit.runner.JUnitCore', 'com.hcbiu.elcton.RuntimeWakeupTest'])
text = r.stdout
receipt['wakeup_summary'] = {'exit': r.returncode, 'true_assertion_red': 'java.lang.AssertionError: Q-R6-001 last trace event' in text, 'cases_expected': 6}
if a.phase == 'red':
    assert r.returncode == 1 and receipt['wakeup_summary']['true_assertion_red'], 'RED must fail actual last-event disk assertion, never compiler/infrastructure'
    assert 'Tests run: 6,  Failures: 1' in text
else:
    assert r.returncode == 0 and 'OK (6 tests)' in text
    legacy_work = out / 'legacy-runtime4'; legacy_work.mkdir()
    r = run('original-runtimefault4', ['java', '-Xmx128m', '-Ddiag.evidence=' + str(legacy_work), '-Ddiag.work=' + str(legacy_work), '-cp', str(jar) + os.pathsep + cp, 'org.junit.runner.JUnitCore', 'com.hcbiu.elcton.P2pRuntimeFaultTest', 'com.hcbiu.elcton.DiagnosticRuntimeRevisionTest'])
    assert r.returncode == 0 and 'OK (4 tests)' in r.stdout
    stop_work = out / 'original-stoprevision1'; stop_work.mkdir()
    r = run('original-stoprevision1', ['java', '-Xmx128m', '-Ddiag.evidence=' + str(stop_work), '-Ddiag.work=' + str(stop_work), '-cp', str(jar) + os.pathsep + cp, 'org.junit.runner.JUnitCore', 'com.hcbiu.elcton.DiagnosticRuntimeRevisionTest'])
    assert r.returncode == 0 and 'OK (1 test)' in r.stdout
assert all(sha(pathlib.Path(f)) == h for f, h in receipt['inputs'].items()), 'source changed while executing'
receipt['sources_unchanged_during_execution'] = True
receipt['validated'] = True
(out / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
print('VALIDATED ' + a.phase + ' RuntimeSHA=' + receipt['inputs'][str(s / 'DiagnosticRuntime.kt')], flush=True)
