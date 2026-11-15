#!/usr/bin/env python3
"""Independent Q1 read-only evidence verifier. No compiler/test/device execution."""
import hashlib, json, pathlib, re, subprocess, collections, datetime
ROOT = pathlib.Path('/data/data/com.termux/files/home/elcton-phone-diagnostics-0210-20261115')
Q = ROOT / 'qa/p2p-trace-0210/r6'
checks = []

def sha(p):
    return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()

def check(name, ok, **detail):
    checks.append(dict(check=name, passed=bool(ok), **detail))

def load(p):
    return json.loads(pathlib.Path(p).read_bytes())

mp = Q/'reviews/input-q1/reviewed-manifest.json'
manifest_bytes = mp.read_bytes()
m = json.loads(manifest_bytes)
oldp = Q/'reviews/input-r2/reviewed-manifest.json'
old = load(oldp)
actual = {k: sha(ROOT/k) for k in m}
check('final_input_manifest', actual == m, files=len(m), mismatches=[k for k in m if actual[k] != m[k]], sha256=sha(mp))
allowed = {'app/src/main/java/com/hcbiu/elcton/DiagnosticRuntime.kt', 'qa/p2p-trace-0210/check_r6_scope.py', 'qa/p2p-trace-0210/r6/current-identity.json'}
changed = [k for k in old if actual.get(k) != old[k]]
check('previous_SPEC32_exact_delta', set(old) <= set(m) and set(changed) == allowed, old_files=len(old), changed=changed, additions=sorted(set(m)-set(old)))
spec = load(Q/'reviews/r6-spec-r2.json')
quality = load(Q/'reviews/r6-quality-r1.json')
check('previous_reviews_identity', spec['passed'] is True and quality['passed'] is False and spec['input_manifest_sha256'] == sha(oldp) == quality['input_manifest_sha256'] and [x['id'] for x in quality['logic_errors']] == ['Q-R6-001'])
for filename, copyname in [('r6-quality-r1.json','reviews__r6-quality-r1.json'),('quality-raw.txt','reviews__quality-raw.txt')]:
    check('rejected_original_preserved_'+filename, (Q/'reviews'/filename).read_bytes() == (Q/'evidence/quality-r1-rejection'/copyname).read_bytes(), sha256=sha(Q/'reviews'/filename))
source = ROOT/'app/src/main/java/com/hcbiu/elcton/DiagnosticRuntime.kt'
red = Q/'evidence/wakeup-red-20261115-1643'
green = Q/'evidence/wakeup-green-20261115-1646'
before = (red/'sources/DiagnosticRuntime.kt.source.txt').read_text()
expected = before.replace('            var persisted = -1L\n', '            var persisted = -1L\n            var processedTraceSeq = -1L\n',1).replace('                    persisted = version\n','                    persisted = version\n                    processedTraceSeq = traceVersion\n',1).replace('                if (!failed && persisted >= 0 && synchronized(lock) { revision } != persisted) persistLater()','                if (!failed && persisted >= 0 &&\n                    (synchronized(lock) { revision } != persisted || p2pTrace.sequence() != processedTraceSeq)) persistLater()',1)
check('Runtime_only_exact_authorized_transform', source.read_text() == expected, pre_sha256=sha(red/'sources/DiagnosticRuntime.kt.source.txt'), current_sha256=sha(source), inserted=4, removed=1)
path='qa/p2p-trace-0210/check_r6_scope.py'
index = subprocess.check_output(['git','show',':'+path],cwd=ROOT)
scope = (ROOT/path).read_bytes()
expected_scope=index.replace(b'import argparse\n', b'import argparse\n')
expected_scope=index.replace(b'from pathlib import Path\n',b'import argparse\nfrom pathlib import Path\n',1).replace(b"    out = QA / 'r6/evidence/frozen-scope-final'",b"    parser = argparse.ArgumentParser()\n    parser.add_argument('--out', type=Path, default=QA/'r6/evidence/frozen-scope-final')\n    args = parser.parse_args()\n    out = args.out.absolute()\n    assert out.is_relative_to(QA/'r6/evidence')",1)
check('scope_helper_only_output_argument_all_predicates_retained', hashlib.sha256(index).hexdigest()==old[path] and expected_scope==scope)
identity = load(Q/'current-identity.json')
prev = load(Q/'evidence/identity-migration-q1/previous-current-identity.json.source.txt')
wanted=json.loads(json.dumps(prev))
rp='app/src/main/java/com/hcbiu/elcton/DiagnosticRuntime.kt'
wanted['source_identities'][rp].update(previous_r6_sha256=prev['source_identities'][rp]['current_sha256'],current_sha256=sha(source),current_bytes=source.stat().st_size)
wanted['quality_repair_identity']=identity['quality_repair_identity']
check('identity_only_Runtime_current_migration', wanted==identity and sha(Q/'evidence/identity-migration-q1/previous-current-identity.json.source.txt') == old['qa/p2p-trace-0210/r6/current-identity.json'] and sha(ROOT/identity['old_manifest'])==identity['old_manifest_sha256'])
table=load(Q/'evidence/identity-migration-q1/table.json')
check('identity_table_and_other_three_source_hashes', table['source_identities']==identity['source_identities'] and table['version_identity']==identity['version_identity'] and table['new_manifest_sha256']==sha(Q/'current-identity.json') and table['previous_r6_manifest_sha256']==old['qa/p2p-trace-0210/r6/current-identity.json'] and all(sha(ROOT/k)==v['current_sha256'] for k,v in identity['source_identities'].items()))
fr=load(Q/'evidence/frozen-scope-q1-1650/receipt.json')
check('frozen_scope_receipt_reconciliation_not_2GB_rehash', fr['base']=='bb26c64b67e1cfa7903cd709c2aac482f6490e6b' and fr['base_entries']==9461 and fr['all_other_base_entries_unchanged'] and fr['original_business_assertions_byte_identical'] and fr['all_original_sourcegate_predicates_byte_identical'] and fr['source_identities']==identity['source_identities'] and all(sha(ROOT/k)==v['current_sha256'] for k,v in fr['old_test_files'].items()) and all(sha(ROOT/k)==v['current_sha256'] for k,v in fr['literal_migrations'].items()), old_tests=len(fr['old_test_files']), base_rehash=False, receipt_sha256=sha(Q/'evidence/frozen-scope-q1-1650/receipt.json'))
rr=load(red/'receipt.json'); gg=load(green/'receipt.json')
check('RED_GREEN_input_identity', set(rr['inputs'])==set(gg['inputs']) and [k for k in rr['inputs'] if rr['inputs'][k]!=gg['inputs'][k]]==[str(source)], input_count=len(rr['inputs']))
archive_errors=[]
for lane,receipt in [(red,rr),(green,gg)]:
    for k,v in receipt['inputs'].items():
        p=pathlib.Path(k); archive=lane/'sources'/(p.name+'.source.txt')
        if archive.exists():
            if sha(archive)!=v:archive_errors.append(str(archive))
        elif k != str(source) and k in gg['inputs'] and gg['inputs'][k]==v and k != str(Q/'current-identity.json'):
            if sha(p)!=v:archive_errors.append(k)
    bc=load(lane/'bytecode-sha.json')
    check('ASM_inverse_and_classes_'+lane.name, bc['instruction_inverse_equal'] and sha(lane/'original.instructions.txt')==sha(lane/'inverse.instructions.txt') and bc['original_class']==sha(lane/'DiagnosticRuntime.original.class') and bc['instrumented_class']==sha(lane/'host-overlay/com/hcbiu/elcton/DiagnosticRuntime.class') and bc['actual_runtime_jar']==sha(lane/'actual-runtime.jar'))
    a=(lane/'original.instructions.txt').read_text().splitlines();b=(lane/'instrumented.instructions.txt').read_text().splitlines();hook='INVOKESTATIC com/hcbiu/elcton/HostWakeBarrier.beforeRelease(Lcom/hcbiu/elcton/DiagnosticRuntime;)V false'; clean=[]; sites=0
    for i,line in enumerate(b):
        if line==hook:
            if not clean or clean[-1]!='ALOAD 0': raise AssertionError('invalid HOST hook load')
            clean.pop();sites+=1
        else:clean.append(line)
    check('ASM_three_only_stackneutral_hooks_'+lane.name, clean==a and sites==3, release_sites=sites)
check('archived_RED_GREEN_sources_sha', not archive_errors, mismatches=archive_errors)
rawred=(red/'wakeup-junit.raw.log').read_text();rawrep=(red/'repeat/wakeup-junit.raw.log').read_text();rawgreen=(green/'wakeup-junit.raw.log').read_text()
check('true_RED6_one_assertion_and_repeat_GREEN6', all('Tests run: 6,  Failures: 1' in t and 'java.lang.AssertionError: Q-R6-001 last trace event' in t and 'expected:<2> but was:<1>' in t for t in [rawred,rawrep]) and 'OK (6 tests)' in rawgreen and (red/'compile.exit.txt').read_text().strip()=='0' and (red/'wakeup-junit.exit.txt').read_text().strip()=='1' and (green/'wakeup-junit.exit.txt').read_text().strip()=='0')
x=load(red/'trace-only-after-release.json');y=load(green/'trace-only-after-release.json')
check('real_final_files_and_one_successor', x['revision']==y['revision']==0 and x['traceSeq']==y['traceSeq']==2 and x['diskSeq']==x['stateSeq']==1 and x['pending']==1 and x['stateWrites']==1 and not x['writing'] and y['diskSeq']==y['stateSeq']==2 and y['pending']==0 and y['stateWrites']==2 and not y['writing'], RED=x, GREEN=y)
for p in [red,green]:
    f=load(p/'state-failure-quiescent.json');t=load(p/'trace-failure-quiescent.json');q=load(p/'quota-quiescent.json')
    check('no_spin_failure_quota_'+p.name, f['stateWrites']==t['stateWrites']==q['stateWrites']==1 and f['pending']==t['pending']==1 and q['fileBytes']==2097152 and all(not v['writing'] for v in [f,t,q]))
check('old_unmodified_Runtime4_Stop1', 'OK (4 tests)' in (green/'original-runtimefault4.raw.log').read_text() and 'OK (1 test)' in (green/'original-stoprevision1.raw.log').read_text() and all('real_socket_health=200' in (green/f).read_text() and 'real_socket_refused=true' in (green/f).read_text() and 'final_file_running=false' in (green/f).read_text() for f in ['original-runtimefault4.raw.log','original-stoprevision1.raw.log']))
report=load(Q/'FINAL-WAKEUP.json'); refs=[]
def recurse(x):
    if isinstance(x,dict):
        if isinstance(x.get('path'),str) and isinstance(x.get('sha256'),str):refs.append(x)
        for v in x.values():recurse(v)
    elif isinstance(x,list):
        for v in x:recurse(v)
recurse(report)
check('FINAL_WAKEUP_all_exact_references', all(sha(pathlib.Path(v['path']))==v['sha256'] for v in refs), refs=len(refs))
final=Q/'evidence/final-q1-complete-1658';f=load(final/'receipt.json');sm=load(final/'source-manifest.json')
check('current_final72_source_rows', len(sm)==f['source_rows']==72 and all(sha(ROOT/k)==v for k,v in sm.items()) and f['source_manifest_sha256']==sha(final/'source-manifest.json') and not f['source_drift'])
raw_errors=[]
for row in f['rows']:
    raw=(pathlib.Path(row['reused_actual_prior_source_identical_compile'])/'full-jvm/junit.log') if row['lane']=='full-jvm' else final/(row['lane']+'.raw.log')
    if row['exit']!=0 or sha(raw)!=row['raw_sha256']:raw_errors.append(row['lane'])
full=pathlib.Path(f['rows'][0]['reused_actual_prior_source_identical_compile'])/'full-jvm'
fullr=load(full/'receipt.json')
check('full171_source_binding_and_jar', all(sha(ROOT/k)==v for k,v in fullr['files'].items() if k!='baseline_renamed') and 'OK (171 tests)' in (full/'junit.log').read_text() and sha(full/'host-tests.jar')==f['jar_sha256'] and [c['exit'] for c in fullr['commands']]==[0,0], files=len(fullr['files']))
py=(final/'python-all.raw.log').read_text();app=(final/'app-cwd.raw.log').read_text();http=load(final/'http.raw.log')
check('final_full171_python133skip0_http3784_appcwd6', f['passed'] is True and not raw_errors and 'Ran 133 tests' in py and re.search(r'\bOK\s*$',py) is not None and 'skip' not in py.lower() and 'OK (6 tests)' in app and http['ok'] is True and http['assertions']==3784 and http['all_raw_checks_passed'] is True, mismatches=raw_errors, recorded_lanes=len(f['rows']))
for lane in ['runtime','native','actual-sdk']:
    rec=load(final/lane/'receipt.json'); fields=rec.get('files',rec.get('sources',{})); errors=[k for k,v in fields.items() if (ROOT/k).is_file() and sha(ROOT/k)!=v]
    cmds=rec.get('steps',rec.get('commands',[]))
    check('final_'+lane+'_source_and_raw', not errors and all(c['exit']==0 for c in cmds), source_rows=len(fields), mismatches=errors)
check('final_native8_runtime4_SDK_typecheck_only', 'OK (8 tests)' in (final/'native/junit.log').read_text() and 'OK (4 tests)' in (final/'runtime/junit.log').read_text() and load(final/'actual-sdk/receipt.json')['actual_sdk'] is True and load(final/'actual-sdk/receipt.json')['steps'][0]['exit']==0)
check('manifest_unchanged_through_readback', mp.read_bytes()==manifest_bytes and {k:sha(ROOT/k) for k in m}==m)
result={'axis':'spec','independent_readback_only':True,'created_at':datetime.datetime.now().astimezone().isoformat(),'input_manifest_path':str(mp),'input_manifest_sha256':hashlib.sha256(manifest_bytes).hexdigest(),'reviewed_inputs':m,'checks':checks,'all_checks_pass':all(x['passed'] for x in checks),'compile_or_test_rerun':False,'device_CI_publish_actions':False}
out=Q/'reviews/spec-q1-readback.json'
out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'all_checks_pass':result['all_checks_pass'],'checks':len(checks),'failed':[x for x in checks if not x['passed']],'inputs':len(m),'input_manifest_sha256':result['input_manifest_sha256'],'receipt':str(out)},ensure_ascii=False))
