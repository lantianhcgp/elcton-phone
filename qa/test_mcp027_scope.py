#!/usr/bin/env python3
"""Fail-closed 0.2.9 boundary, with every original 0.2.7 method retained.

Version/adapter/workflow relocations: qa/release-029/TEST-ATTRIBUTION.md.
Candidate byte identity does not substitute for separate independent approval.
"""
from pathlib import Path
import subprocess
import unittest
import xml.etree.ElementTree as ET
ROOT = Path(__file__).resolve().parents[1]
from qa import diag_source_gate as gate
BASE = gate.HEAD_PIN

class Mcp027ScopeTests(unittest.TestCase):
    def test_we_and_signing_and_themes_remain_exact(self):
        # Whole adapter is the exact candidate transform, reversed to 0.2.5.
        self.assertEqual([], gate.scope_errors((ROOT / gate.ACTIVITY).read_text(),
                                              (ROOT / gate.PROBE).read_text()))
        for name in gate.RELEASE['immutable_source_sha256']:
            expected = subprocess.check_output(['git', 'show', BASE + ':' + name], cwd=ROOT)
            self.assertEqual(expected, (ROOT / name).read_bytes(), name)
        workflow = gate.RELEASE['build_workflow']
        expected = subprocess.check_output(['git', 'show', BASE + ':' + workflow['path']], cwd=ROOT).decode('utf-8')
        for change in workflow['allowed_replacements']:
            self.assertEqual(1, expected.count(change['before']))
            expected = expected.replace(change['before'], change['after'], 1)
        self.assertEqual(expected.encode('utf-8'), (ROOT / workflow['path']).read_bytes())
        signing = workflow['staged_signing_before']
        verifier = workflow['signing_verifier_replacement']
        self.assertEqual(1, signing.count(verifier['before']))
        self.assertIn(signing.replace(verifier['before'], verifier['after'], 1), expected)
        self.assertEqual([], gate.build_workflow_errors())
        for mutation in (expected + '\n# unapproved workflow edit\n',
                         expected.replace('--ks-key-alias elcton', '--ks-key-alias different', 1)):
            self.assertTrue(gate.build_workflow_errors(mutation))

    def test_private_local_service_and_no_new_power_behaviour(self):
        xml = ET.parse(ROOT / 'app/src/main/AndroidManifest.xml').getroot()
        ns = '{http://schemas.android.com/apk/res/android}'
        services = xml.findall('application/service')
        self.assertEqual(1, len(services), 'exactly the approved local MCP service')
        self.assertEqual('.McpKeepAliveService', services[0].get(ns + 'name'))
        self.assertEqual('false', services[0].get(ns + 'exported'))
        self.assertEqual('specialUse', services[0].get(ns + 'foregroundServiceType'))
        self.assertTrue(services[0].find('property') is not None)
        property_element = services[0].find('property')
        assert property_element is not None
        self.assertEqual('android.app.PROPERTY_SPECIAL_USE_FGS_SUBTYPE', property_element.get(ns + 'name'))
        permission = {p.get(ns + 'name') for p in xml.findall('uses-permission')}
        self.assertEqual({'android.permission.INTERNET', 'android.permission.FOREGROUND_SERVICE', 'android.permission.FOREGROUND_SERVICE_SPECIAL_USE', 'android.permission.POST_NOTIFICATIONS'}, permission)
        self.assertFalse(xml.findall('application/receiver'), 'no boot/broadcast wakeups')
        application = xml.find('application')
        self.assertIsNotNone(application)
        assert application is not None
        self.assertEqual('false', application.get(ns + 'allowBackup'))
        self.assertEqual('false', application.get(ns + 'usesCleartextTraffic'))
        metadata = application.find('meta-data')
        self.assertIsNotNone(metadata)
        assert metadata is not None
        self.assertEqual('appid=118599721', metadata.get(ns + 'value'))

    def test_version_027_code9(self):
        text = (ROOT / 'app/build.gradle.kts').read_text()
        # Keep the historical method name for count/lineage; explicit release requirement.
        self.assertIn('versionCode = 11', text)
        self.assertIn('versionName = "0.2.9"', text)

if __name__ == '__main__':
    unittest.main(verbosity=2)
