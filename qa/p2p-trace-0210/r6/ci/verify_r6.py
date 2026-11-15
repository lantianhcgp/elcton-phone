#!/usr/bin/env python3
"""R6 binary and zero-copy full original cloud criteria; never dispatch/build/ADB."""
import argparse
import ast
import hashlib
import json
import marshal
from pathlib import Path
import sys
import types
import xml.etree.ElementTree as ET
from r6_common import (ROOT, OLD, HERE, FOURTH, original, require, read_json, save,
                       new_out, digest, inventory, check_cases, offline_binding)
sys.dont_write_bytecode = True


def literal_only(before, after, label):
    """Prove ALL AST including assertion labels unchanged except 11/0.2.9 literals."""
    left, right = ast.parse(before), ast.parse(after)
    changes = []
    class Version(ast.NodeTransformer):
        def visit_Constant(self, node):
            if type(node.value) is int and node.value == 11:
                changes.append({'line': node.lineno, 'before': 11, 'after': 12}); node.value = 12
            elif node.value == '0.2.9':
                changes.append({'line': node.lineno, 'before': '0.2.9', 'after': '0.2.10'}); node.value = '0.2.10'
            return node
    transformed = Version().visit(left)
    require(ast.dump(transformed, include_attributes=False) == ast.dump(right, include_attributes=False), label + ': change outside version literals')
    return {'all_non_version_ast_unchanged': True, 'labels_unchanged': True, 'version_literals': changes}


def cloud_module():
    path = OLD / FOURTH / 'verifiers/verify_cloud.py'
    before = original('verifiers/verify_cloud.py')
    token = "(d.PACKAGE,'0.2.9',11)"
    require(before.count(token) == 1, 'Original background version span missing/ambiguous')
    after = before.replace(token, "(d.PACKAGE,'0.2.10',12)", 1)
    proof = literal_only(before, after, 'Original full cloud verifier')
    proof.update(original_path=str(path), original_sha256=digest(path),
                 effective_sha256=hashlib.sha256(after.encode()).hexdigest())
    m = types.ModuleType('r6_original_cloud'); m.__file__ = str(path)
    exec(compile(after, str(path), 'exec'), m.__dict__)
    # Path/metadata relocation only; criteria functions are unmodified current QA.
    m.__dict__['ROOT'] = ROOT
    sys.path.insert(0, str(ROOT))
    methods = ('clients','diagnostics','background','full','tour','check','write')
    proof['method_code_sha256'] = {name: hashlib.sha256(marshal.dumps(getattr(m.Gate, name).__code__)).hexdigest() for name in methods}
    return m, proof


def binary_source():
    path = OLD / FOURTH / 'verify_exact_build.py'
    before = original('verify_exact_build.py')
    old_version = "(package, '11', '0.2.9')"
    old_count = "assert len(cases) == 153 and len({tuple(x) for x in cases}) == 153, 'Incomplete or duplicate Gradle tests'"
    require(before.count(old_version) == before.count(old_count) == 1, 'Original binary adaptation span ambiguous')
    after = before.replace(old_version, "(package, '12', '0.2.10')", 1)
    # The original fixed 153 guard becomes a STRICT registered set equality,
    # with 153 original actual XML labels retained. Not >=153 or substring matching.
    after = after.replace(old_count, "check_cases(cases, ORIGINAL_CASES, REGISTERED_CASES, 'Incomplete or duplicate Gradle tests')", 1)
    after = after.replace("'version': '0.2.9/code11'", "'version': '0.2.10/code12'", 1)
    # Reversibility is stronger than selectively inspecting assertions.
    inverse = after.replace("(package, '12', '0.2.10')", old_version, 1).replace(
        "check_cases(cases, ORIGINAL_CASES, REGISTERED_CASES, 'Incomplete or duplicate Gradle tests')", old_count, 1).replace(
        "'version': '0.2.10/code12'", "'version': '0.2.9/code11'", 1)
    require(inverse == before, 'Binary helper adaptation not exact reversible')
    return after, {'original_path': str(path), 'original_sha256': digest(path),
                   'effective_sha256': hashlib.sha256(after.encode()).hexdigest(),
                   'original_case_count': 153, 'original_labels_unchanged': True,
                   'all_other_assertions_byte_identical': True,
                   'adaptations': ['main version tuple 11/0.2.9 -> 12/0.2.10',
                                   'strict registered complete actual testcase set, includes original 153 exact labels',
                                   'printed version metadata only']}


def register_cases(args):
    """Offline source/manifest registration; no Gradle or Kotlin compilation."""
    baseline = OLD / FOURTH / 'r11/exact-cloud-pipeline/build-verification/receipt.json'
    old = read_json(baseline)['gradle']['test_cases']
    require(len(old) == len({tuple(x) for x in old}) == 153, 'Original real Gradle 153 labels lost')
    added = read_json(args.added_cases)
    require(isinstance(added, list) and added == read_json(HERE/'added-cases.json') and len(added)==19,
            'Require all 19 registered R6 exact labels; no inferred post-build inventory')
    import re
    sources = {}
    observed = []
    for classname in sorted({row[0] for row in added}):
        path = 'app/src/test/java/' + classname.replace('.', '/') + '.kt'
        text = (ROOT/path).read_text()
        found = re.findall(r'@Test(?:\([^)]*\))?\s+fun\s+(?:`([^`]+)`|([A-Za-z_][A-Za-z_0-9]*))\s*\(', text)
        observed += [[classname, a or b] for a,b in found]
        sources[path] = digest(ROOT/path)
    require({tuple(x) for x in observed} == {tuple(x) for x in added} and len(observed)==19, 'Current source labels differ from registered 19')
    fixture = 'qa/p2p-trace-0210/r6/fixtures/P2pTraceBaselineEngine.kt'
    sources[fixture] = digest(ROOT/fixture)
    require(sources[fixture]=='af97a6fd8e3a9941b6cc11d533423cdb049f038782a6bd9791c8ed8ac5c274e9', 'Exact class-only baseline fixture changed')
    registered = old + added
    check_cases(registered, old, registered)
    out = new_out(args.out)
    save(out, 'testcases.json', {'source_sha': args.source, 'original_receipt': str(baseline),
         'original_receipt_sha256': digest(baseline), 'original_cases': old, 'added_cases': added,
         'test_cases': registered, 'tests': len(registered), 'source_sha256': sources,
         'scope': 'Required future actual Gradle XML set, NOT test execution'})
    print(json.dumps({'registered': len(registered), 'original': 153, 'manifest': str(out/'testcases.json')}))


def verify_build(args):
    manifest = read_json(args.case_manifest)
    require(manifest['source_sha'] == args.source, 'Case manifest source not final build SHA')
    baseline = OLD / FOURTH / 'r11/exact-cloud-pipeline/build-verification/receipt.json'
    require(digest(baseline) == manifest['original_receipt_sha256'], 'Original actual case receipt changed')
    old = read_json(baseline)['gradle']['test_cases']
    require(manifest['original_cases'] == old and len(old) == 153, 'Original 153 labels changed')
    require(manifest['test_cases'] == old + manifest['added_cases'], 'Registered case list changed')
    require(manifest['added_cases']==read_json(HERE/'added-cases.json') and manifest['tests']==172, 'Exact registered R6 172 cases required')
    import subprocess
    for path, expected in manifest['source_sha256'].items():
        raw = subprocess.check_output(['git','show',args.source+':'+path],cwd=ROOT,timeout=30)
        require(hashlib.sha256(raw).hexdigest()==expected, 'Final committed testcase/fixture differs: '+path)
    before, archive = offline_binding(args.incoming, args.run, args.source, args.source, 'build')
    source, proof = binary_source()
    require('..' not in Path(args.out).parts, 'Build output traversal refused')
    out = Path(args.out).absolute()
    require(not any(p.is_symlink() for p in (out, *out.parents)), 'Build output symlink refused')
    require(out.is_relative_to(HERE) and not out.exists(), 'New build output must be below R6 ci')
    require(not out.is_relative_to(args.incoming.absolute()), 'Build output overlaps input')
    namespace = {'__name__': 'r6_original_binary', '__file__': str(OLD/FOURTH/'verify_exact_build.py'),
                 'check_cases': check_cases, 'ORIGINAL_CASES': old, 'REGISTERED_CASES': manifest['test_cases']}
    argv = sys.argv
    sys.argv = [namespace['__file__'], '--incoming', str(args.incoming), '--sha', args.source,
                '--run', args.run, '--out', str(out)]
    try: exec(compile(source, namespace['__file__'], 'exec'), namespace)
    finally: sys.argv = argv
    require(inventory(args.incoming) == before, 'Complete build input changed during verification')
    save(out, 'original-code-proof.json', proof)
    save(out, 'complete-input-readback.json', {'before': before, 'after': before, 'archive': archive})
    save(out, 'case-manifest-readback.json', manifest)


def verify_cloud(args):
    m, proof = cloud_module()
    before, archive = offline_binding(args.incoming, args.run, args.source, args.workflow_sha, 'android')
    criteria = {}
    for name in m.CRITERIA:
        old = OLD/'qa'/(name+'.py'); current = ROOT/'qa'/(name+'.py')
        if name == 'diag_emulator_smoke':
            criteria[name] = literal_only(old.read_text(), current.read_text(), 'Current diag_emulator_smoke')
        else:
            require(old.read_bytes() == current.read_bytes(), 'Frozen current criterion changed: ' + str(current))
            criteria[name] = {'byte_identical': True}
        criteria[name].update(path=str(current), original_sha256=digest(old), current_sha256=digest(current))
    out = new_out(args.out)
    require(not out.is_relative_to(args.incoming.absolute()), 'Cloud output overlaps input')
    args.out = out
    class ZeroGate(m.Gate):
        def snapshot(self):
            now = inventory(self.args.incoming)
            m.compare(now, before, 'ALL original fetched bytes before')
            declared = m.read_json(self.args.incoming/'inventory.json')
            m.compare({k:v for k,v in now.items() if k != 'inventory.json'}, declared['inventory'], 'ALL fetched files')
            self.art = self.args.incoming/'artifact'
            self.write('input-inventory.json', now)
            self.write('snapshot-map.json', {key: str(self.args.incoming/key) for key in now})
            return {'raw_files':len(now), 'snapshot':str(self.args.incoming), 'zero_copy':True}
    methods = ('clients','diagnostics','background','full','tour','check','write')
    require(all(getattr(ZeroGate,k).__code__ is getattr(m.Gate,k).__code__ for k in methods), 'Original full assertion methods not inherited')
    gate = ZeroGate(args)
    gate.write('execution.json', {'argv':sys.argv,'source':args.source,'workflow_sha':args.workflow_sha,
        'run':args.run,'suite':args.suite,'python':sys.version,'tool_sha256':digest(__file__),
        'scope':'OFFLINE ONLY zero ADB/device/network/CI execution; original full criteria'})
    gate.write('criteria-sha256.json', criteria)
    gate.write('original-method-identity.json', proof)
    gate.write('complete-archive-readback.json', archive)
    gate.check('input-snapshot-all-bytes', gate.snapshot)
    gate.check('exact-run-success', lambda:m.check_run(m.read_json(args.incoming/'run.json'),args.workflow_sha,args.run))
    def inputs():
        registration = read_json(args.registration)
        require(str(registration['run']['id']) == args.run and registration['workflow_sha'] == args.workflow_sha, 'Registered exact UI workflow head/run differs')
        require(registration['inputs'] == {'build_run':args.build_run,'build_sha':args.source,'api_level':'33',
                'navigation_mode':'three-button','qa_suite':args.suite}, 'Original explicit UI inputs differ')
        build = read_json(args.build_receipt)
        require(build['passed'] is True and build['source_sha']==args.source and build['build_run']==args.build_run, 'Verified actual build binding differs')
        if args.suite == 'diagnostics':
            host = m.read_json(args.incoming/'artifact/diag-host-report.json')
            require(host['sdk']=='33' and host['navigationMode']=='three-button', 'Actual diagnostics SDK/navigation differs')
            build = read_json(args.build_receipt)
            require(build['passed'] is True and build['source_sha']==args.source and build['build_run']==args.build_run, 'Verified actual build binding differs')
            require(host['apkSha256'] == {'main':build['rows'][0]['sha256'],'tests':build['rows'][1]['sha256']}, 'Actual diagnostics main/test APK hashes differ')
        else:
            env = m.read_json(args.incoming/'artifact/environment.json')
            require(env['sdk']=='33' and env['navigation_mode']=='three-button', 'Actual full SDK/navigation differs')
        return registration
    gate.check('registered-original-inputs-and-build', inputs)
    gate.check('local-client-raw-logs', gate.clients)
    gate.check(args.suite+'-complete', gate.diagnostics if args.suite=='diagnostics' else gate.full)
    def after():
        m.compare(inventory(args.incoming), before, 'ALL original input bytes after')
        for name,row in criteria.items(): require(digest(Path(row['path']))==row['current_sha256'], 'Criterion changed during gates: '+name)
        return {'files':len(before),'same_exact_bytes_before_and_after':True}
    gate.check('snapshot-inputs-unchanged-after-original-gates', after)
    receipt = {'passed':not gate.errors,'source_sha':args.source,'workflow_sha':args.workflow_sha,
        'run_id':args.run,'suite':args.suite,'checks':gate.checks,'errors':gate.errors,'details':gate.details,
        'scope':'All ORIGINAL full assertions and COMPLETE JSON, current 12/0.2.10 literals only; offline not new device proof'}
    gate.write('receipt.json', receipt)
    print(json.dumps({'passed':receipt['passed'],'errors':gate.errors,'receipt':str(out/'receipt.json')},ensure_ascii=False))
    return 0 if receipt['passed'] else 1


def main():
    if sys.argv[1:] == ['--self-test']:
        import self_test
        return self_test.main()
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    reg = sub.add_parser('register-cases'); reg.add_argument('--added-cases', type=Path, required=True)
    b = sub.add_parser('build'); b.add_argument('--case-manifest', type=Path, required=True)
    c = sub.add_parser('cloud')
    c.add_argument('--workflow-sha', required=True); c.add_argument('--suite', choices=('diagnostics','full'), required=True)
    c.add_argument('--registration',type=Path,required=True); c.add_argument('--build-run',required=True)
    c.add_argument('--build-receipt',type=Path,required=True)
    for p in (reg,b,c):
        p.add_argument('--source', required=True); p.add_argument('--out',type=Path,required=True)
    for p in (b,c):
        p.add_argument('--incoming',type=Path,required=True); p.add_argument('--run',required=True)
    args = parser.parse_args()
    from r6_common import sha40
    sha40(args.source)
    if args.command=='register-cases': register_cases(args); return 0
    if args.command=='build': verify_build(args); return 0
    return verify_cloud(args)

if __name__=='__main__':
    raise SystemExit(main())
