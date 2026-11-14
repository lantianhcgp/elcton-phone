#!/usr/bin/env python3
"""The diagnostic scope exception must reject unrelated lifecycle/UI/SDK mutations."""
from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
BASE = '18cd94ea1689c7e3d59a26afd4121cd2a665b4d7'
ACTIVITY = 'app/src/main/java/com/hcbiu/elcton/MainActivity.kt'
PROBE = 'app/src/main/java/com/hcbiu/elcton/WearProbe.kt'


class DiagnosticSourceGateTest(unittest.TestCase):
    def module(self):
        from qa import diag_source_gate
        return diag_source_gate

    def source(self, path):
        return (ROOT / path).read_text()

    def test_exact_authorized_observation_reverses_to_version_025_baseline(self):
        gate = self.module()
        self.assertEqual([], gate.scope_errors(self.source(ACTIVITY), self.source(PROBE)))
        for path, restore in [(ACTIVITY, gate.without_activity_diagnostics), (PROBE, gate.without_probe_diagnostics)]:
            baseline = subprocess.check_output(['git', 'show', BASE + ':' + path], cwd=ROOT, text=True)
            self.assertEqual(baseline, restore(self.source(path)))

    def test_business_callback_mutation_is_rejected_not_filtered(self):
        gate = self.module()
        source = self.source(ACTIVITY)
        self.assertIn('displayWeek++', source)
        self.assertTrue(gate.scope_errors(source.replace('displayWeek++', 'displayWeek+=2', 1), self.source(PROBE)))

    def test_swapping_scan_and_cancel_callbacks_is_rejected(self):
        gate = self.module()
        source = self.source(ACTIVITY)
        a, b = '{probe.authorizeAndScan()}', '{probe.cancel()}'
        source = source.replace(a, 'SWAP_SENTINEL').replace(b, a).replace('SWAP_SENTINEL', b)
        self.assertTrue(gate.scope_errors(source, self.source(PROBE)))

    def test_unrequested_activity_lifecycle_side_effect_is_rejected(self):
        gate = self.module()
        source = self.source(ACTIVITY).replace('super.onCreate(savedInstanceState)', 'super.onCreate(savedInstanceState);probe.cancel()', 1)
        self.assertTrue(gate.scope_errors(source, self.source(PROBE)))

    def test_sdk_authorization_branch_mutation_is_rejected(self):
        gate = self.module()
        source = self.source(PROBE)
        self.assertIn('if(granted)scan(gen)else{', source)
        self.assertTrue(gate.scope_errors(self.source(ACTIVITY), source.replace('if(granted)scan(gen)else{', 'if(true)scan(gen)else{', 1)))

    def test_transport_send_success_code_mutation_is_rejected(self):
        gate = self.module()
        source = self.source(PROBE)
        self.assertIn('code!=207', source)
        self.assertTrue(gate.scope_errors(self.source(ACTIVITY), source.replace('code!=207', 'code!=0', 1)))

    def test_missing_or_duplicated_authorized_diagnostic_seam_is_rejected(self):
        gate = self.module()
        source = self.source(ACTIVITY)
        self.assertIn('.testTag("version-capsule")', source)
        for mutation in [source.replace('.testTag("version-capsule")', '', 1), source + '\n' + gate.ACTIVITY_INITIALIZER]:
            self.assertTrue(gate.scope_errors(mutation, self.source(PROBE)))

    def test_lost_full_message_persistence_is_rejected(self):
        gate = self.module()
        source = self.source(PROBE).replace('diagnostics?.record(record)', 'diagnostics?.read()', 1)
        self.assertTrue(gate.scope_errors(self.source(ACTIVITY), source))


if __name__ == '__main__':
    unittest.main(verbosity=2)
