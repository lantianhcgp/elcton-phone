#!/usr/bin/env python3
"""Helper-only offline tests: no APK, signer, build, network, or delivery run."""
import ast
import hashlib
import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
ORIGINAL = HERE.parents[2] / 'finalize_r6_delivery.py'
SOURCE = 'b3eb55680b51f5fbdf392d402acdcdae168f2b20'
ORIGINAL_SHA = '5e631132ed51fcea7a4406dbdecfe75dcf1ea4edeec3531a2c05e1ff3fbcbe03'


class R8MetadataTests(unittest.TestCase):
    maxDiff = 160

    def setUp(self):
        path = HERE / 'finalize_r8_delivery.py'
        self.assertTrue(path.is_file(), 'R8 adapter not implemented yet')
        spec = importlib.util.spec_from_file_location('r8_adapter_test', path)
        self.adapter = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.adapter)
        self.original = ORIGINAL.read_bytes()
        self.temp = tempfile.TemporaryDirectory(dir=HERE, prefix='.offline-helper-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.q = self.root / 'qa' / 'r6'
        self.phone = self.root / 'isolated-phone'
        (self.q / 'ci').mkdir(parents=True)
        self.phone.mkdir()
        self.out = self.q / 'ci' / 'new-output'

    def preflight(self, out=None, source=SOURCE):
        return self.adapter.preflight(source, self.out if out is None else out,
                                      self.q, self.phone)

    def test_exact_inverse_full_ast_and_five_spans(self):
        candidate, proof = self.adapter.adapt_metadata(self.original)
        self.assertEqual(hashlib.sha256(self.original).hexdigest(), ORIGINAL_SHA)
        self.assertTrue(self.adapter.inverse_metadata(candidate) == self.original,
                        'metadata inverse differs from original bytes')
        self.assertTrue(self.adapter.normalized_ast_equal(self.original, candidate))
        self.assertEqual(len(proof['changed_spans']), 5)
        self.assertTrue(proof['inverse_exact'] and proof['normalized_ast_equal'])
        self.assertEqual(proof['transformed_sha256'], hashlib.sha256(candidate).hexdigest())

    def reject_mutation(self, old, new):
        candidate, _ = self.adapter.adapt_metadata(self.original)
        self.assertEqual(candidate.count(old), 1)
        mutated = candidate.replace(old, new, 1)
        with self.assertRaises(AssertionError):
            self.adapter.verify_metadata(self.original, mutated)
        self.assertFalse(self.adapter.normalized_ast_equal(self.original, mutated))

    def test_reject_signature_boolean_mutation(self):
        self.reject_mutation(b'Verified using v2 scheme (APK Signature Scheme v2): true',
                             b'Verified using v2 scheme (APK Signature Scheme v2): false')

    def test_reject_identity_guard_mutation(self):
        self.reject_mutation(b"table['source_identities']==current",
                             b"table['source_identities']!=current")

    def test_reject_expected_certificate_mutation(self):
        self.reject_mutation(b"CERT = 'fc08a0b", b"CERT = '0c08a0b")

    def test_reject_artifact_source_name_mutation(self):
        self.reject_mutation(b"main['name']=='elcton-phone-probe.apk'",
                             b"main['name']=='other.apk'")

    def test_original_pinned_and_original_globals_preserved(self):
        namespace = self.adapter.load_reviewed()
        self.assertEqual(namespace['__file__'], str(ORIGINAL))
        self.assertEqual(namespace['ROOT'], ORIGINAL.parents[2])
        self.assertEqual(namespace['Q'], ORIGINAL.parent / 'r6')
        self.assertEqual(namespace['CERT'],
                         'fc08a0b474a8ffca5887bd5c88ac15e865a63a64eca81c10f344496c46d9ad94')
        self.assertTrue(namespace['main'].__globals__ is namespace)
        mutated = self.original.replace(b'import time\n', b'import time # mutation\n', 1)
        with self.assertRaises(AssertionError):
            self.adapter.adapt_metadata(mutated)

    def test_preflight_exact_source_filename_and_no_writes(self):
        targets = self.preflight()
        self.assertEqual(targets['apk'].name,
                         'hc课程表-0.2.10-code12-b3eb5568-诊断版-signed.apk')
        self.assertEqual(targets['q_report'], self.q / 'DELIVERY-R8.md')
        self.assertEqual(targets['phone_report'], self.phone / 'DELIVERY-R8.md')
        self.assertEqual(targets['out_report'], self.out / 'DELIVERY-R8.md')
        self.assertFalse(self.out.exists())
        self.assertEqual(list(self.phone.iterdir()), [])

    def test_reject_existing_apk_preserves_bytes(self):
        target = self.phone / 'hc课程表-0.2.10-code12-b3eb5568-诊断版-signed.apk'
        target.write_bytes(b'old helper-only bytes')
        with self.assertRaises(AssertionError):
            self.preflight()
        self.assertEqual(target.read_bytes(), b'old helper-only bytes')
        self.assertFalse(self.out.exists())

    def test_reject_existing_q_report(self):
        target = self.q / 'DELIVERY-R8.md'
        target.write_text('old q report')
        with self.assertRaises(AssertionError):
            self.preflight()
        self.assertEqual(target.read_text(), 'old q report')
        self.assertFalse(self.out.exists())

    def test_reject_existing_phone_report(self):
        target = self.phone / 'DELIVERY-R8.md'
        target.write_text('old phone report')
        with self.assertRaises(AssertionError):
            self.preflight()
        self.assertEqual(target.read_text(), 'old phone report')
        self.assertFalse(self.out.exists())

    def test_reject_existing_output_directory_and_report(self):
        self.out.mkdir()
        target = self.out / 'DELIVERY-R8.md'
        target.write_text('old out report')
        with self.assertRaises(AssertionError):
            self.preflight()
        self.assertEqual(target.read_text(), 'old out report')

    def test_reject_dangling_report_symlink(self):
        (self.q / 'DELIVERY-R8.md').symlink_to(self.root / 'missing')
        with self.assertRaises(AssertionError):
            self.preflight()
        self.assertFalse(self.out.exists())

    def test_reject_symlink_output_parent(self):
        link = self.q / 'ci' / 'alias'
        link.symlink_to(self.q / 'ci', target_is_directory=True)
        with self.assertRaises(AssertionError):
            self.preflight(link / 'child')
        self.assertFalse((self.q / 'ci' / 'child').exists())

    def test_reject_symlink_phone_parent(self):
        alias = self.root / 'phone-alias'
        alias.symlink_to(self.phone, target_is_directory=True)
        with self.assertRaises(AssertionError):
            self.adapter.preflight(SOURCE, self.out, self.q, alias)
        self.assertFalse(self.out.exists())

    def test_reject_traversal_and_outside_ci(self):
        for target in (self.q / 'ci' / '..' / 'bad', self.root / 'outside', self.q / 'ci'):
            with self.assertRaises(AssertionError):
                self.preflight(target)
        self.assertFalse(self.out.exists())

    def test_reject_wrong_or_malformed_source(self):
        for source in ('4fc3363f2b30073f1a71de4d4073460b81ec537f', SOURCE.upper(), '../x'):
            with self.assertRaises(AssertionError):
                self.preflight(source=source)
        self.assertFalse(self.out.exists())

    def isolated_namespace(self):
        namespace = self.adapter.load_reviewed()
        # Test-only isolated execution namespace; production globals/config untouched.
        namespace['Q'], namespace['PHONE'] = self.q, self.phone
        return namespace

    def argv(self):
        return ['r8-helper-test', '--source', SOURCE, '--build-receipt', str(self.root/'build.json'),
                '--diagnostics-receipt', str(self.root/'diag.json'),
                '--full-receipt', str(self.root/'full.json'),
                '--apk', str(self.root/'missing-no-apk'), '--out', str(self.out)]

    def test_actual_wrapper_rejects_collision_before_original_mkdir(self):
        namespace = self.isolated_namespace()
        (self.phone / 'DELIVERY-R8.md').write_text('protected')
        with patch.object(self.adapter, 'load_reviewed', return_value=namespace), \
             patch.object(sys, 'argv', self.argv()), self.assertRaises(AssertionError):
            self.adapter.main()
        self.assertFalse(self.out.exists())
        self.assertEqual((self.phone / 'DELIVERY-R8.md').read_text(), 'protected')

    def test_actual_wrapper_reaches_unchanged_false_pass_guard_only(self):
        namespace = self.isolated_namespace()
        for name in ('build', 'diag', 'full'):
            (self.root / (name + '.json')).write_text('{"passed": false}')
        old = self.q / 'DELIVERY.md'
        old.write_text('R6 protected helper-only status')
        with patch.object(self.adapter, 'load_reviewed', return_value=namespace), \
             patch.object(sys, 'argv', self.argv()), self.assertRaises(AssertionError):
            self.adapter.main()
        self.assertTrue(self.out.is_dir(), 'unchanged original mkdir was not reached')
        self.assertEqual(list(self.out.iterdir()), [])
        self.assertEqual(list(self.phone.iterdir()), [])
        self.assertFalse((self.q / 'DELIVERY-R8.md').exists())
        self.assertEqual(old.read_text(), 'R6 protected helper-only status')


if __name__ == '__main__':
    unittest.main(verbosity=2)
