#!/usr/bin/env python3
"""Fail-closed, byte-exact authorized 0.2.7 product boundary tests."""
from pathlib import Path
import subprocess
import unittest
import xml.etree.ElementTree as ET
ROOT = Path(__file__).resolve().parents[1]
BASE = 'cd2a3e062b97d778c79b76b544071b1077534af7'

class Mcp027ScopeTests(unittest.TestCase):
    def test_we_and_signing_and_themes_remain_exact(self):
        paths = ['app/src/main/java/com/hcbiu/elcton/WearProbe.kt', 'app/src/main/java/com/hcbiu/elcton/M3xTheme.kt', '.github/workflows/build.yml']
        for name in paths:
            expected = subprocess.check_output(['git', 'show', BASE + ':' + name], cwd=ROOT)
            self.assertEqual(expected, (ROOT / name).read_bytes(), name)

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
        self.assertIn('versionCode = 9', text)
        self.assertIn('versionName = "0.2.7"', text)

if __name__ == '__main__':
    unittest.main(verbosity=2)
