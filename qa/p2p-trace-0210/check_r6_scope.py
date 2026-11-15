#!/usr/bin/env python3
"""R6 frozen-scope: complete git baseline + exact permitted literal inversions.
New rows are registered separately, never alter original assertions or evidence.
"""
import argparse
from pathlib import Path
import hashlib
import json
import os
import subprocess
import time
ROOT = Path(__file__).resolve().parents[2]
QA = Path(__file__).resolve().parent
BASE = 'bb26c64b67e1cfa7903cd709c2aac482f6490e6b'
PRODUCT = {f'app/src/main/java/com/hcbiu/elcton/{n}.kt' for n in ('WearProbe','SyncEngine','DiagnosticRuntime')}
VERSION = {
    'app/build.gradle.kts': [('versionCode = 12', 'versionCode = 11'), ('versionName = "0.2.10"', 'versionName = "0.2.9"')],
    'app/src/test/java/com/hcbiu/elcton/DiagnosticsIntegrationTest.kt': [('versionCode = 12','versionCode = 11'), ('0.2.10','0.2.9')],
    'qa/P2pCandidateBuildTest.kt': [('assertEquals(12, BuildConfig.VERSION_CODE)','assertEquals(11, BuildConfig.VERSION_CODE)'), ('0.2.10','0.2.9')],
    'app/src/androidTest/java/com/hcbiu/elcton/DiagnosticsUiTest.kt': [('0.2.10','0.2.9'), ('assertEquals(12L, installed.longVersionCode)','assertEquals(11L, installed.longVersionCode)'), ('assertEquals(12, version.getInt("versionCode"))','assertEquals(11, version.getInt("versionCode"))')],
    'qa/test_mcp027_scope.py': [('versionCode = 12','versionCode = 11'), ('0.2.10','0.2.9')],
    'qa/release-029/verify_apk.py': [("'12', '0.2.10'", "'11', '0.2.9'")],
    'qa/diag_emulator_smoke.py': [('"0.2.10"','"0.2.9"'), ('report.get("packageCode") == 12','report.get("packageCode") == 11'), ('version.get("versionCode") == 12','version.get("versionCode") == 11')],
}
GATE = 'qa/diag_source_gate.py'


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, default=QA/'r6/evidence/frozen-scope-final')
    args = parser.parse_args()
    if '..' in args.out.parts:
        parser.error('Output must not contain parent traversal')
    out = args.out.absolute()
    if any(path.is_symlink() for path in (out, *out.parents)):
        parser.error('Output must not have symlink ancestry')
    base = (QA/'r6/evidence').resolve()
    out = out.resolve()
    if out == base or not out.is_relative_to(base):
        parser.error('Output must be a new directory within R6 evidence')
    out.mkdir(parents=True, exist_ok=False)
    assert not (out/'receipt.json').exists(), 'Preserve prior completed scope receipt'
    tree = json.loads((QA/'r6/evidence/before/base-tree.json').read_bytes())
    assert tree['base'] == BASE and len(tree['entries']) == 9461
    expected = PRODUCT | set(VERSION) | {GATE}
    # Exact full-content read of ALL baseline entries. New R5/R6 evidence is not
    # part of the old baseline, and no deleted old path is excluded.
    changed = set()
    for row in tree['entries']:
        p = ROOT/row['path']
        assert p.exists() or p.is_symlink(), 'Missing baseline path: '+row['path']
        data = os.readlink(p).encode() if p.is_symlink() else p.read_bytes()
        oid = hashlib.sha1(b'blob '+str(len(data)).encode()+b'\x00'+data).hexdigest()
        if oid != row['oid']: changed.add(row['path'])
    assert changed == expected, sorted(changed ^ expected)
    inverses = {}
    for path, changes in VERSION.items():
        current = (ROOT/path).read_bytes()
        restored = current
        counts = []
        for new, old in changes:
            assert restored.count(new.encode()) > 0, (path,new)
            counts.append({'new':new,'old':old,'count':restored.count(new.encode())})
            restored = restored.replace(new.encode(),old.encode())
        original = git('show', BASE+':'+path)
        assert restored == original, 'Nonliteral version/test delta: '+path
        inverses[path] = {'old_sha256':sha(original),'current_sha256':sha(current), 'reverse_sha256':sha(restored),'counts':counts,'all_other_bytes_unchanged':True}
    original_gate = git('show',BASE+':'+GATE)
    current_gate = (ROOT/GATE).read_bytes()
    left = current_gate.index(b'# R6 migrates ONLY the current identity data')
    right = current_gate.index(b'def reverse_exact(text, path):',left)
    restored_gate = current_gate[:left] + current_gate[right:]
    assert restored_gate == original_gate, 'Original source gate predicates changed'
    old_test_files = [x for x in tree['entries'] if (x['path'].startswith('app/src/test/') or x['path'].startswith('app/src/androidTest/') or x['path']=='qa/P2pCandidateBuildTest.kt') and x['path'].endswith('.kt')]
    old_tests = {}
    for row in old_test_files:
        path=row['path']; current=(ROOT/path).read_bytes();original=git('show',BASE+':'+path)
        restored=current
        for new,old in VERSION.get(path,[]):restored=restored.replace(new.encode(),old.encode())
        assert restored == original
        old_tests[path]={'old_sha256':sha(original),'current_sha256':sha(current),'non_version_bytes_unchanged':True}
    # Independent R5 inventory includes retained original audit test classes too.
    r5=json.loads((QA/'baseline.json').read_bytes())
    frozen_inventory=r5['old_tests']
    if isinstance(frozen_inventory,dict):
        for path,value in frozen_inventory.items():
            data=(ROOT/path).read_bytes()
            for new,old in VERSION.get(path,[]):data=data.replace(new.encode(),old.encode())
            expected_sha=value if isinstance(value,str) else value.get('sha256')
            assert expected_sha==sha(data),(path,'R5 original test identity')
    identity=json.loads((QA/'r6/current-identity.json').read_bytes())
    for path,row in identity['source_identities'].items(): assert sha((ROOT/path).read_bytes())==row['current_sha256']
    build_tests = sorted((ROOT/'app/src/test/java/com/hcbiu/elcton').glob('*Test.kt'))
    assert len(build_tests)==35
    fixture=ROOT/'qa/p2p-trace-0210/r6/fixtures/P2pTraceBaselineEngine.kt'
    base_engine=git('show',BASE+':app/src/main/java/com/hcbiu/elcton/SyncEngine.kt').decode()
    expected_fixture='package com.hcbiu.elcton\n\n'+base_engine[base_engine.index('class SyncEngine('):].replace('class SyncEngine(','class P2pTraceBaselineEngine(',1)
    assert fixture.read_text()==expected_fixture
    dcheck=subprocess.run(['git','diff','--check'],cwd=ROOT,capture_output=True)
    assert dcheck.returncode==0
    record={'at':time.strftime('%Y-%m-%d %H:%M:%S %z'),'base':BASE,'base_entries':len(tree['entries']),
        'allowed_diagnostic_paths':sorted(PRODUCT),'literal_migrations':inverses,'allowed_identity_gate_path':GATE,
        'all_original_sourcegate_predicates_byte_identical':True,'all_other_base_entries_unchanged':True,
        'old_test_files':old_tests,'current_test_classes':len(build_tests),'original_business_assertions_byte_identical':True,
        'source_identities':identity['source_identities'],'new_test_only_baseline_sha256':sha(fixture.read_bytes()),
        'workflow_bytes_frozen':True,'devices':[],'haps':[],'diff_check_exit':0}
    (out/'receipt.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n')
    (out/'allowed-source.diff').write_bytes(git('diff','--binary',BASE,'--',*sorted(expected)))
    print(json.dumps({k:v for k,v in record.items() if k not in ('old_test_files','source_identities','literal_migrations')},ensure_ascii=False))


if __name__=='__main__':main()
