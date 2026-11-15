#!/usr/bin/env python3
"""Independent helper-only QUALITY probes; no real API, APK, CI or device."""
import ast
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time
from types import SimpleNamespace

START = 1794750609.1436253
D = Path(__file__).resolve().parent.parent
R = D.parents[4]
S = 'b3eb55680b51f5fbdf392d402acdcdae168f2b20'
REPORT = D / 'reviews'
RAW = REPORT / 'quality-r8-helpers-raw.txt'
STATE = REPORT / 'quality-r8-offline-results.json'
lines = ['Independent QUALITY helper-only offline execution; fixtures are NOT real API responses.']
fingerprints = {}
blobs = {}

def read(path):
    path = Path(path)
    if str(path) not in blobs:
        raw = path.read_bytes()
        blobs[str(path)] = raw
        fingerprints[str(path)] = hashlib.sha256(raw).hexdigest()
        lines.append('READ ' + str(path) + ' SHA256=' + fingerprints[str(path)] + ' bytes=' + str(len(raw)))
    return blobs[str(path)]

def load(path, name):
    raw = read(path)
    ns = {'__file__': str(path), '__name__': name}
    exec(compile(raw, str(path), 'exec', dont_inherit=True, optimize=0), ns)
    return SimpleNamespace(**ns)

spec_path = REPORT / 'spec-r8-helpers-http-q1.json'
spec = json.loads(read(spec_path))
assert fingerprints[str(spec_path)] == '0b16fdad8c5e66cb2142acc43d4f040b4967802c824b4ccd63e0071f43c60a0b'
assert spec['passed'] == (not (spec['security_concerns'] or spec['logic_errors'] or spec['missing_requirements']))
assert len(spec['input_fingerprints']) == 51
parent = json.loads(read(D / 'spec-http-q1-parent-readback.json'))
assert parent['passed'] and parent['input_count'] == 51 and not parent['drift']
assert parent['receipt_sha256'] == fingerprints[str(spec_path)]
# SHA-only preservation proof: no review/rerun of product, gates, CI or cloud.
drift = []
for path, expected in spec['input_fingerprints'].items():
    actual = hashlib.sha256(read(path)).hexdigest()
    if actual != expected:
        drift.append({'path': path, 'expected': expected, 'actual': actual})
lines.append('SPEC 51-input SHA-only verification drift=' + json.dumps(drift))
read(D / 'metadata-proof.json')
read(D / 'metadata-report.md')
read(D / 'R8-TRANSPORT-SCOPE.md')
read(__file__)
u = load(D / 'ui_transport.py', 'quality_transport')
f = load(D / 'finalize_r8_delivery.py', 'quality_finalizer')
original = read(f.ORIGINAL)
committed = subprocess.check_output(['git', 'show', S + ':qa/p2p-trace-0210/finalize_r6_delivery.py'], cwd=R, timeout=20)
assert original == committed
candidate, metadata = f.adapt_metadata(original)
assert f.inverse_metadata(candidate) == original
assert f.normalized_ast_equal(original, candidate)
assert len(metadata['changed_spans']) == 5
lines.append('METADATA ' + json.dumps(metadata, ensure_ascii=False))
proof = u.command_proof()
lines.append('COMMAND_PROOF ' + json.dumps(proof))
# Extra original gate is only hashed against pinned git bytes, never executed/reviewed.
verify_path = D.parent / 'verify_r6.py'
if verify_path.is_file():
    assert read(verify_path) == subprocess.check_output(['git', 'show', S + ':' + str(verify_path.relative_to(R))], cwd=R, timeout=20)
    lines.append('VERIFY_BYTE_PROOF true')

tests = []
for name, count in [('test_finalize_r8_metadata.py', 18), ('test_dns_parameters.py', 1), ('test_transport_edges.py', 3), ('test_post_http_status.py', 2)]:
    path = D / name
    read(path)
    p = subprocess.run([sys.executable, '-B', str(path)], cwd=R, capture_output=True, timeout=35)
    text = (p.stdout + p.stderr).decode('utf-8', errors='replace')
    lines.append('COMMAND ' + repr([sys.executable, '-B', str(path)]) + ' EXIT=' + str(p.returncode))
    lines.append(text)
    import re
    matches = re.findall(r'Ran (\d+) tests? in', text)
    actual_count = int(matches[-1]) if matches else None
    tests.append({'file': str(path), 'sha256': fingerprints[str(path)], 'exit_code': p.returncode, 'count': actual_count, 'expected_count': count, 'raw_sha256': hashlib.sha256(p.stdout + p.stderr).hexdigest(), 'passed': p.returncode == 0 and actual_count == count and 'skipped=' not in text})

# Compile the actual nested api unmodified into a test factory. No main()/I/O.
tree = ast.parse(read(D / 'ui_transport.py'))
main_node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'main')
api_node = next(n for n in ast.walk(main_node) if isinstance(n, ast.FunctionDef) and n.name == 'api')
outer = ast.parse('def factory():\n    post_count = 0\n').body[0]
outer.body += [api_node, ast.parse('return api').body[0]]
module = ast.fix_missing_locations(ast.Module(body=[outer], type_ignores=[]))
payload = {'ref': u.BRANCH, 'inputs': {'build_run': '43715446826', 'build_sha': S, 'api_level': '33', 'navigation_mode': 'three-button', 'qa_suite': 'full'}}

def factory(replies, command='dispatch-ui'):
    calls = []
    log = io.StringIO()
    def fake_run(*args, **kwargs):
        calls.append({'argv': args[0], 'stdin_sha256': hashlib.sha256(kwargs['input']).hexdigest(), 'timeout': kwargs['timeout']})
        item = replies[min(len(calls)-1, len(replies)-1)]
        if isinstance(item, Exception):
            raise item
        return SimpleNamespace(returncode=item[0], stdout=item[1])
    ns = dict(vars(u))
    ns.update(args=[command], suite='full', config='header = "Authorization: Bearer OFFLINE-FIXTURE"\n', log=log,
              subprocess=SimpleNamespace(run=fake_run), time=SimpleNamespace(time=lambda: 0, sleep=lambda _: None))
    exec(compile(module, str(D/'ui_transport.py'), 'exec', dont_inherit=True, optimize=0), ns)
    return ns['factory'](), calls, log

fixtures = []
for name, reply, expected in [
    ('empty204', (0, b'\nR8-HTTP-STATUS:204'), True),
    ('redirect302', (0, b'\nR8-HTTP-STATUS:302'), False),
    ('missing-status', (0, b''), False),
    ('nonempty204', (0, b'x\nR8-HTTP-STATUS:204'), False),
    ('whitespace204', (0, b' \t\r\n\nR8-HTTP-STATUS:204'), False),
    ('curl-failure204', (28, b'\nR8-HTTP-STATUS:204'), False),
    ('timeout', subprocess.TimeoutExpired('fixture-curl', 55), False),
]:
    api, calls, log = factory([reply])
    error = None
    try:
        api('/actions/workflows/ui-smoke.yml/dispatches', payload)
        accepted = True
    except (AssertionError, subprocess.TimeoutExpired) as e:
        accepted = False
        error = str(e)
    before_second = len(calls)
    try:
        api('/actions/workflows/ui-smoke.yml/dispatches', payload)
        second_refused = False
    except AssertionError:
        second_refused = True
    row = {'fixture': name, 'accepted': accepted, 'expected': expected, 'calls': before_second, 'second_refused': second_refused, 'second_added_calls': len(calls)-before_second, 'error': error, 'log_excludes_fixture_credential': 'OFFLINE-FIXTURE' not in log.getvalue(), 'no_location': all('--location' not in c['argv'] for c in calls), 'no_retry': all('--retry' not in c['argv'] for c in calls)}
    fixtures.append(row)
    lines.append('POST_FIXTURE ' + json.dumps(row))

get_probes = []
for name, replies, expected in [('third-success', [(6,b''),(6,b''),(0,b'{"fixture": true}')], True), ('all-fail', [(6,b'')], False), ('malformed-json', [(0,b'{')], False)]:
    api, calls, log = factory(replies, 'readback')
    try:
        value = api('/actions/runs/43720799962')
        accepted = True
        error = None
    except (AssertionError, json.JSONDecodeError) as e:
        accepted = False
        error = str(e)
    row = {'fixture': name, 'accepted': accepted, 'expected': expected, 'calls': len(calls), 'dns_pinned': ['--resolve' in c['argv'] for c in calls], 'error': error}
    get_probes.append(row)
    lines.append('GET_FIXTURE ' + json.dumps(row))

invalid = []
for path, p in [('/actions/workflows/build.yml/dispatches', payload), ('/actions/workflows/ui-smoke.yml/dispatches', {**payload, 'ref': 'main'}), ('/actions/workflows/ui-smoke.yml/dispatches', {'ref':u.BRANCH,'inputs':{**payload['inputs'],'build_run':'0'}})]:
    api, calls, log = factory([(0,b'\nR8-HTTP-STATUS:204')])
    try:
        api(path,p)
        refused = False
    except AssertionError:
        refused = True
    row = {'refused':refused,'calls':len(calls),'path':path}
    invalid.append(row)
    lines.append('SCOPE_FIXTURE '+json.dumps(row))

optimized = subprocess.run([sys.executable, '-O', '-B', str(D/'finalize_r8_delivery.py')], capture_output=True, timeout=15)
lines.append('OPTIMIZED_FINALIZER EXIT=' + str(optimized.returncode) + '\n' + optimized.stderr.decode())
assert optimized.returncode and b'Optimized Python refuses delivery' in optimized.stderr

# Independent collision checks use temp storage only; no receipt/APK success simulation.
preflight_probes = []
with tempfile.TemporaryDirectory(prefix='quality-r8-offline-') as tmp:
    root = Path(tmp)
    q = root/'qa'/'r6'
    phone = root/'phone'
    (q/'ci').mkdir(parents=True)
    phone.mkdir()
    out = q/'ci'/'new'
    target = f.preflight(S,out,q,phone)
    assert not out.exists() and target['apk'].name == 'hc课程表-0.2.10-code12-b3eb5568-诊断版-signed.apk'
    for name in ('apk','q_report','phone_report'):
        p = target[name]
        p.write_bytes(b'QUALITY-PROTECTED')
        try:
            f.preflight(S,out,q,phone)
            rejected = False
        except AssertionError:
            rejected = True
        preserved = p.read_bytes() == b'QUALITY-PROTECTED'
        preflight_probes.append({'target':name,'rejected':rejected,'preserved':preserved,'out_absent':not out.exists()})
        p.unlink()
lines.append('PREFLIGHT '+json.dumps(preflight_probes))

end_drift = []
for path, expected in fingerprints.items():
    actual = hashlib.sha256(Path(path).read_bytes()).hexdigest()
    if actual != expected:
        end_drift.append({'path':path,'expected':expected,'actual':actual})
lines.append('POST_TEST_FINGERPRINT_DRIFT '+json.dumps(end_drift))
lines.append('ELAPSED_SECONDS '+str(time.time()-START))
result = {'fingerprints':fingerprints,'spec_input_count':51,'spec_input_drift':drift,'end_drift':end_drift,'metadata':metadata,'command_proof':proof,'offline_tests':tests,'post_fixtures':fixtures,'get_fixtures':get_probes,'invalid_post_fixtures':invalid,'preflight_fixtures':preflight_probes,'optimized_finalizer_refused':True,'seconds':time.time()-START}
raw = ('\n'.join(lines)+'\n').encode()
with RAW.open('xb') as out:
    out.write(raw)
result['raw_path'] = str(RAW)
result['raw_sha256'] = hashlib.sha256(raw).hexdigest()
with STATE.open('x') as out:
    json.dump(result,out,ensure_ascii=False,indent=2)
    out.write('\n')
print(json.dumps({'state':str(STATE),'raw':str(RAW),'raw_sha256':result['raw_sha256'],'test_counts':[(t['count'],t['exit_code']) for t in tests],'post_mismatches':[p for p in fixtures if p['accepted']!=p['expected']],'get':get_probes,'drift':drift+end_drift,'seconds':result['seconds']},ensure_ascii=False))
