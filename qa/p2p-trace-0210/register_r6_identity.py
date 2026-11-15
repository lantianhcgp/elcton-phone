#!/usr/bin/env python3
"""R6 current identity registration: never rewrites the frozen 0.2.9 record.
Run only after the diagnostic writer has frozen. Exclusive output directory.
"""
import copy
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
QA = Path(__file__).resolve().parent
BASE = 'bb26c64b67e1cfa7903cd709c2aac482f6490e6b'
PRODUCT = 'app/src/main/java/com/hcbiu/elcton/'
OLD_MANIFEST = 'qa/release-029/approved-release-delta.json'
R5 = json.loads((QA / 'r6/evidence/before/snapshot.json').read_text())


def digest(data):
    return hashlib.sha256(data).hexdigest()


def base_bytes(path):
    return subprocess.check_output(['git', 'show', BASE + ':' + path], cwd=ROOT)


def main():
    old = (ROOT / OLD_MANIFEST).read_bytes()
    assert digest(old) == R5['files'][OLD_MANIFEST]['r5_sha256']
    prior = json.loads(old)
    rows = {}
    for name in ('WearProbe', 'SyncEngine', 'DiagnosticRuntime', 'P2pTrace'):
        path = PRODUCT + name + '.kt'
        current = (ROOT / path).read_bytes()
        before = base_bytes(path) if name != 'P2pTrace' else None
        rows[path] = {
            'old_sha256': digest(before) if before is not None else None,
            'r5_sha256': R5['files'][path]['r5_sha256'],
            'current_sha256': digest(current),
            'current_bytes': len(current),
        }
    probe = PRODUCT + 'WearProbe.kt'
    assert digest(prior['patches'][probe][0]['after'].encode()) == rows[probe]['old_sha256']
    gradle_path = 'app/build.gradle.kts'
    old_gradle, new_gradle = base_bytes(gradle_path), (ROOT / gradle_path).read_bytes()
    expected = old_gradle.replace(b'versionCode = 11', b'versionCode = 12').replace(
        b'versionName = "0.2.9"', b'versionName = "0.2.10"')
    assert old_gradle.count(b'versionCode = 11') == 1 and old_gradle.count(b'versionName = "0.2.9"') == 1
    assert new_gradle == expected, 'Version migration contains nonliteral drift'
    manifest = {
        'schema': 1, 'base': BASE, 'release': '0.2.10', 'version_code': 12,
        'authorization': 'R6 explicit user ruling 2026-11-15; diagnostics only + version/identity migration',
        'old_manifest': OLD_MANIFEST, 'old_manifest_sha256': digest(old),
        'source_identities': rows,
        'probe_current_after': (ROOT / probe).read_text(),
        'version_identity': {
            'path': gradle_path, 'old_sha256': digest(old_gradle), 'current_sha256': digest(new_gradle),
            'old_code': 11, 'current_code': 12, 'old_name': '0.2.9', 'current_name': '0.2.10',
        },
        'frozen': {'business_assertions': 'unchanged', 'SDK_callbacks_and_guards': 'unchanged',
                   'old_release_manifest': 'unchanged', 'build_workflows': 'unchanged'},
        'scope': 'Exact candidate source identity registration; NOT independent approval or hardware acceptance',
    }
    dest = QA / 'r6/current-identity.json'
    with dest.open('x') as file:
        json.dump(manifest, file, ensure_ascii=False, indent=2)
        file.write('\n')
    evidence = QA / 'r6/evidence/identity-migration'
    evidence.mkdir(parents=True, exist_ok=False)
    with (evidence / 'table.json').open('x') as file:
        json.dump({'source_identities': rows, 'version_identity': manifest['version_identity'],
                   'old_manifest_sha256': digest(old), 'new_manifest_sha256': digest(dest.read_bytes())},
                  file, ensure_ascii=False, indent=2)
        file.write('\n')
    (evidence / 'original-manifest.json.source.txt').write_bytes(old)
    for name in ('WearProbe', 'SyncEngine', 'DiagnosticRuntime', 'P2pTrace'):
        (evidence / (name + '.kt.current.source.txt')).write_bytes((ROOT / (PRODUCT + name + '.kt')).read_bytes())
    print(json.dumps({'manifest': str(dest), 'table': str(evidence / 'table.json'),
                      'source_rows': rows, 'version': manifest['version_identity']}, ensure_ascii=False))


if __name__ == '__main__':
    main()
