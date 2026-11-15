#!/usr/bin/env python3
"""Pure helper tests only: in-memory fixtures, no gh/ADB/build/network/file writes."""
import importlib.util
import io
import json
from pathlib import Path
import unittest
import zipfile

HERE = Path(__file__).resolve().parent

class HelperTests(unittest.TestCase):
    def test_helpers_exist(self):
        self.assertTrue((HERE / 'r6_common.py').is_file(), 'R6 explicit identity helper not implemented')

    def setUp(self):
        if not (HERE / 'r6_common.py').is_file():
            return
        import r6_common
        self.c = r6_common

    def test_literal_tokens_not_normalized(self):
        if not hasattr(self, 'c'): return
        self.c.sha40('a' * 40)
        self.c.run_id('123')
        for value in ('A' * 40, ' ' + 'a' * 40, 'a' * 39):
            with self.assertRaises(AssertionError): self.c.sha40(value)
        for value in ('0123', '123 ', '0'):
            with self.assertRaises(AssertionError): self.c.run_id(value)

    def test_all_case_labels_preserved(self):
        if not hasattr(self, 'c'): return
        original = [['C', 'original label'], ['C', 'second']]
        registered = original + [['N', 'new label']]
        self.c.check_cases(registered, original, registered)
        for actual in (registered[:-1], registered + registered[:1], [['C', 'renamed']] + registered[1:]):
            with self.assertRaises(AssertionError): self.c.check_cases(actual, original, registered)
        with self.assertRaises(AssertionError): self.c.check_cases(registered[1:], original, registered[1:])

    def test_crc_and_unsafe_member_checks(self):
        if not hasattr(self, 'c'): return
        safe = io.BytesIO()
        with zipfile.ZipFile(safe, 'w') as z: z.writestr('dist/source-sha.txt', 'a' * 40 + '\n')
        safe.seek(0)
        with zipfile.ZipFile(safe) as z: self.c.zip_members(z)
        for name in ('../escape', '/absolute', 'a/../escape'):
            bad = io.BytesIO()
            with zipfile.ZipFile(bad, 'w') as z: z.writestr(name, b'test fixture')
            bad.seek(0)
            with zipfile.ZipFile(bad) as z:
                with self.assertRaises(AssertionError): self.c.zip_members(z)

    def test_original_complete_json_comparator(self):
        if not hasattr(self, 'c'): return
        import verify_r6
        m, proof = verify_r6.cloud_module()
        m.compare({'rgb': (1, 2, 3), 'passed': True}, {'rgb': [1, 2, 3], 'passed': True}, 'fixture')
        for bad in ({'rgb': [1, 2, 4], 'passed': True}, {'rgb': [1, 2, 3]}, {'rgb': [1, 2, 3], 'passed': False}):
            with self.assertRaises(AssertionError): m.compare({'rgb': (1, 2, 3), 'passed': True}, bad, 'fixture')
        self.assertTrue(proof['all_non_version_ast_unchanged'])
        self.assertTrue(proof['labels_unchanged'])

    def test_original_binary_adaptation_is_narrow(self):
        if not hasattr(self, 'c'): return
        import verify_r6
        source, proof = verify_r6.binary_source()
        compile(source, 'r6-binary-adaptation', 'exec')
        self.assertEqual(proof['original_case_count'], 153)
        self.assertIn("(package, '12', '0.2.10')", source)
        self.assertIn("(package, '', '')", source)
        self.assertIn('Incomplete or duplicate Gradle tests', source)

    def test_attempt_ambiguity_is_rejected(self):
        if not hasattr(self, 'c'): return
        attempt = {'run_started_at': '2026-11-15T01:00:00Z', 'run_attempt': 2}
        asset = {'id': 1, 'name': 'android-ui-' + 'a' * 40, 'expired': False,
                 'created_at': '2026-11-15T01:00:01Z', 'workflow_run': {'id': 123, 'head_sha': 'a' * 40}}
        self.assertEqual(self.c.select_asset([asset], attempt, asset['name'], '123', 'a' * 40)['id'], 1)
        with self.assertRaises(AssertionError): self.c.select_asset([asset, dict(asset, id=2)], attempt, asset['name'], '123', 'a' * 40)
        with self.assertRaises(AssertionError): self.c.select_asset([dict(asset, created_at='2026-11-14T00:00:00Z')], attempt, asset['name'], '123', 'a' * 40)


def main():
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(HelperTests))
    return 0 if result.wasSuccessful() else 1

if __name__ == '__main__':
    raise SystemExit(main())
