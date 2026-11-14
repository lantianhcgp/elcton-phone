#!/usr/bin/env python3
"""Actual main/test binary verification plus complete exact Gradle XML assertions."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import zipfile
import xml.etree.ElementTree as ET

p = argparse.ArgumentParser()
p.add_argument('--incoming', required=True)
p.add_argument('--sha', required=True)
p.add_argument('--run', required=True)
p.add_argument('--out', required=True)
a = p.parse_args()
incoming = Path(a.incoming)
out = Path(a.out)
out.mkdir(parents=True, exist_ok=False)
CERT = 'fc08a0b474a8ffca5887bd5c88ac15e865a63a64eca81c10f344496c46d9ad94'
run = json.loads((incoming / 'run-exact.json').read_bytes())
assert str(run['databaseId']) == a.run and run['headSha'] == a.sha
assert run['status'] == 'completed' and run['conclusion'] == 'success'
artifact = incoming / 'artifact'
pins = list(artifact.rglob('source-sha.txt'))
assert len(pins) == 1 and pins[0].read_text().strip() == a.sha

def invoke(command, name):
    executed = subprocess.run(command, capture_output=True, timeout=75)
    with (out / (name + '.stdout.bin')).open('xb') as file:
        file.write(executed.stdout)
    with (out / (name + '.stderr.bin')).open('xb') as file:
        file.write(executed.stderr)
    with (out / (name + '.exit')).open('x') as file:
        file.write(str(executed.returncode) + '\n')
    executed.check_returncode()
    return executed.stdout.decode()

rows = []
for filename, package in (('elcton-phone-probe.apk', 'com.hcbiu.elcton'),
                          ('elcton-ui-tests.apk', 'com.hcbiu.elcton.test')):
    matches = list(artifact.rglob(filename))
    assert len(matches) == 1
    apk = matches[0]
    badging = invoke(['aapt2', 'dump', 'badging', str(apk)], filename + '.badging')
    version = re.search(r"package: name='([^']+)' versionCode='([^']*)' versionName='([^']*)'", badging)
    assert version and version[1] == package
    if package == 'com.hcbiu.elcton':
        assert version.groups() == (package, '11', '0.2.9')
    else:
        assert version.groups() == (package, '', '')
        tree = invoke(['aapt2', 'dump', 'xmltree', str(apk), '--file', 'AndroidManifest.xml'], filename + '.xmltree')
        assert 'E: instrumentation ' in tree and 'androidx.test.runner.AndroidJUnitRunner' in tree
        assert re.search(r'android:targetPackage[^\n]*="com\.hcbiu\.elcton"', tree)
    signer = invoke(['java', '-Xmx256m', '-jar', str(Path.home() / 'rb_build/bt/android-14/lib/apksigner.jar'),
                     'verify', '--verbose', '--print-certs', str(apk)], filename + '.signer')
    digest = re.search(r'certificate SHA-256 digest: ([0-9a-fA-F]+)', signer)
    assert digest and digest[1].lower() == CERT
    assert 'Number of signers: 1' in signer
    assert 'Verified using v2 scheme (APK Signature Scheme v2): true' in signer
    with zipfile.ZipFile(apk) as captured:
        assert captured.testzip() is None
    rows.append({'name': filename, 'path': str(apk.resolve()), 'package': package,
                 'versionCode': version[2], 'versionName': version[3], 'bytes': apk.stat().st_size,
                 'sha256': hashlib.sha256(apk.read_bytes()).hexdigest(), 'signer_sha256': CERT,
                 'v2': True, 'zip_crc': True})
xmls = sorted(artifact.rglob('TEST-*.xml'))
assert xmls, 'Real Gradle JUnit XML absent'
suites = []
cases = []
for file in xmls:
    suite = ET.parse(file).getroot()
    assert suite.tag == 'testsuite'
    count = len(suite.findall('testcase'))
    assert count == int(suite.attrib['tests']), 'Declared/actual suite count mismatch'
    assert all(int(suite.attrib.get(key, '0')) == 0 for key in ('failures', 'errors', 'skipped'))
    for case in suite.findall('testcase'):
        assert not any(case.findall(key) for key in ('failure', 'error', 'skipped'))
        cases.append([case.attrib.get('classname'), case.attrib.get('name')])
    suites.append({'path': str(file.relative_to(artifact)), 'tests': count,
                   'sha256': hashlib.sha256(file.read_bytes()).hexdigest()})
assert len(cases) == 153 and len({tuple(x) for x in cases}) == 153, 'Incomplete or duplicate Gradle tests'
receipt = {'passed': True, 'source_sha': a.sha, 'build_run': a.run,
           'scope': 'actual signed APK/manifest/CRC/hash plus all actual Gradle XML; NOT cloud/physical PASS',
           'rows': rows, 'gradle': {'tests': len(cases), 'suites': len(suites), 'skipped': 0,
                                  'failures': 0, 'errors': 0, 'suite_rows': suites, 'test_cases': cases},
           'test_apk_version_fields': 'AGP instrumentation artifact has actually empty versions; not release APK'}
with (out / 'receipt.json').open('x') as file:
    json.dump(receipt, file, ensure_ascii=False, indent=2)
    file.write('\n')
print(json.dumps({'passed': True, 'source_sha': a.sha, 'build_run': a.run,
                  'gradle_tests': len(cases), 'gradle_suites': len(suites),
                  'main_sha256': rows[0]['sha256'], 'main_bytes': rows[0]['bytes'],
                  'signer': CERT, 'version': '0.2.9/code11'}), flush=True)
