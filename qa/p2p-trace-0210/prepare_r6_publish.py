#!/usr/bin/env python3
"""White-list R6 source/evidence, no stage/push until independent review succeeds.
Never picks up generated HOST .kt/jars/Android artifacts/tokens or R5 scratch.
"""
from pathlib import Path
import hashlib
import json
import re
import subprocess
ROOT=Path(__file__).resolve().parents[2]
QA=Path(__file__).resolve().parent
P='qa/p2p-trace-0210/'
FIXED=[
'app/build.gradle.kts','app/src/androidTest/java/com/hcbiu/elcton/DiagnosticsUiTest.kt',
'app/src/main/java/com/hcbiu/elcton/WearProbe.kt','app/src/main/java/com/hcbiu/elcton/SyncEngine.kt',
'app/src/main/java/com/hcbiu/elcton/DiagnosticRuntime.kt','app/src/main/java/com/hcbiu/elcton/P2pTrace.kt',
'app/src/test/java/com/hcbiu/elcton/DiagnosticsIntegrationTest.kt',
'qa/P2pCandidateBuildTest.kt','qa/diag_emulator_smoke.py','qa/diag_source_gate.py',
'qa/release-029/verify_apk.py','qa/test_mcp027_scope.py',
]+[P+x for x in ['R6-AUTHORIZATION-AND-PLAN.md','baseline.json','baseline-worktree-amendment.json',
'run_host.py','run_native_host.py','run_runtime_fault_host.py','check_r6_scope.py',
'register_r6_identity.py','generate_ci_baseline.py','prepare_r6_publish.py','close_r6_reviews.py','verify_r6_remote.py','run_r6_final_regressions.py','migrate_r6_quality_identity.py','prepare_r6_q1_review.py','finalize_r6_delivery.py','commit_r6_reviewed.py','rerun_r7_watch_frozen.py','verify_r7_cached_scope.py','prepare_r7_q2_review.py','R7-AUTHORIZATION-AND-PLAN.md','R7-QUALITY-HELPER-REPAIR-SCOPE.md','CONTINUATION-R6-20261115.md']]+[P+'r6/evidence/SCOPE-AMENDMENT-NEW-TEST-PATH.md',P+'r6/QUALITY-R1-REPAIR-SCOPE.md']
EVIDENCE=[
'adapter-before-20261115-1542','adapter-red-20261115-1542','adapter-green-20261115-1544',
'adapter-jvm-green-20261115-1545','before','frozen-scope-final','identity-migration',
'version-migration','watch-frozen-445','python-http-final-1553','runtime-final-1551','actual-sdk-final-1556',
'gradle-cwd-preflight-1615','final-current-cwd-1616','review-round1-seal','spec-r2-parent-readback','precommit-whitespace','helper-sanity-1634','quality-r1-rejection','identity-migration-q1','wakeup-host-parent-read','wakeup-red-parent-readback','final-q1-regression-1650','frozen-scope-q1-1650','final-q1-complete-1654','final-q1-complete-1656','final-q1-complete-1658','wakeup-final-20261115-1648','wakeup-parent-final-readback','q1-scope-output-only-proof','spec-q1-parent-readback','r7-final-regression','r7-watch-frozen','r7-quality-parent-readback','r7-helper-repair','r7-q2-parent-readback','r7-scope-cache-check','r7-delivery-helper-guard'
]
ALLOWED_ENDINGS=('.json','.md','.txt','.log','.tap','.diff','.py','.kt.in','.java.in','.exit')


def main():
    paths=set(FIXED)
    for f in (ROOT/'app/src/test/java/com/hcbiu/elcton').glob('P2p*Test.kt'):
        if f.name in {'P2pContextTest.kt','P2pTraceConcurrencyTest.kt','P2pTraceEngineTest.kt','P2pTraceIngressTest.kt','P2pTraceRuntimeTest.kt','P2pTraceTest.kt'}:paths.add(str(f.relative_to(ROOT)))
    for folder in ('native-host','runtime-fault-host'):
        for f in (QA/folder).glob('*.kt.in'):paths.add(str(f.relative_to(ROOT)))
    paths.add(P+'r6/fixtures/P2pTraceBaselineEngine.kt')
    paths.add(P+'r6/current-identity.json')
    paths.add(P+'r6/FINAL-L3.json')
    for f in (QA/'r6/ci').iterdir():
        if f.is_file() and f.name.endswith(('.py','.md','.json')):paths.add(str(f.relative_to(ROOT)))
    for folder in EVIDENCE:
        d=QA/'r6/evidence'/folder
        assert d.is_dir(),d
        for f in d.rglob('*'):
            if f.is_file() and f.name.endswith(ALLOWED_ENDINGS) and '/runtime-files/' not in str(f):
                paths.add(str(f.relative_to(ROOT)))
    for d in [QA/'r6/reviews', QA/'r6/reviews/input', QA/'r6/reviews/input-r2', QA/'r6/reviews/input-q1', QA/'r6/reviews/closure']:
        if not d.exists(): continue
        for f in d.rglob('*'):
            if f.is_file() and f.name.endswith(ALLOWED_ENDINGS) and '/runtime-files/' not in str(f):
                paths.add(str(f.relative_to(ROOT)))
    for pattern in ['wakeup-red-*','wakeup-green-*']:
        for folder in (QA/'r6/evidence').glob(pattern):
            for f in folder.rglob('*'):
                if f.is_file() and f.name.endswith(ALLOWED_ENDINGS) and f.suffix not in ['.kt','.java'] and not any(x in f.parts for x in ['wakeup-work','legacy-runtime4','original-stoprevision1','generated']):
                    paths.add(str(f.relative_to(ROOT)))
    for folder in [QA/'r6/runtime-wakeup-host', QA/'r6/helper-repair-host']:
        for f in folder.iterdir():
            if f.is_file() and f.name.endswith(('.kt.in','.java.in','.py','.md')):paths.add(str(f.relative_to(ROOT)))
    for f in (QA/'r6').glob('FINAL-*'):paths.add(str(f.relative_to(ROOT)))
    secret_patterns=[re.compile(x) for x in (
        rb'ghp_[A-Za-z0-9]{20,}',rb'github_pat_[A-Za-z0-9_]{20,}',rb'sk-[A-Za-z0-9]{20,}',
        rb'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----',
        rb'Bearer [A-Za-z0-9_-]{24,}',
    )]
    rows={};risks=[]
    for path in sorted(paths):
        f=ROOT/path
        assert f.is_file() and not f.is_symlink(),path
        assert not path.endswith(('.jar','.apk','.jks','.zip','.tar.gz','.pem'))
        assert '/runtime-files/' not in path and '/ci/evidence/' not in path
        raw=f.read_bytes()
        for pattern in secret_patterns:
            if pattern.search(raw):risks.append({'path':path,'pattern':pattern.pattern.decode(),'no_credential_values_printed':True})
        rows[path]={'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),'blob':hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\x00'+raw).hexdigest()}
    record={'paths':rows,'risk_matches':risks,'no_binary_host_kt_artifacts_or_token_files':True,'scan_scope':'R6 selected source/evidence only; existing public repository visibility unchanged'}
    destination=QA/'r6/PUBLISH-CANDIDATE.json'
    destination.write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'files':len(rows),'bytes':sum(x['bytes'] for x in rows.values()),'risk_matches':risks,'manifest':str(destination)},ensure_ascii=False))
    assert not risks,'Private R6 push blocked until actual secret classified'

if __name__=='__main__':main()
