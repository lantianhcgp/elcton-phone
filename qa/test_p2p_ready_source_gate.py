#!/usr/bin/env python3
"""Exact release relocation does not relax the historical READY negative controls.

Lineage: qa/release-029/TEST-ATTRIBUTION.md. READY dispatch/auth/timeouts moved
into SyncEngine; SDK identity remains in WearProbe. All original methods remain.
"""
import unittest
from pathlib import Path
from qa import diag_source_gate as gate
ROOT=Path(__file__).resolve().parents[1]

class P2pReadySourceGateTest(unittest.TestCase):
    def source(self,path):return (ROOT/path).read_bytes().decode('utf-8')
    def test_only_reviewed_ready_delta_reverses_to_pinned_original(self):
        activity,probe=self.source(gate.ACTIVITY),self.source(gate.PROBE)
        self.assertEqual([],gate.scope_errors(activity,probe))
        self.assertEqual(gate.baseline(gate.PROBE),gate.without_probe_diagnostics(probe))
    def test_missing_or_duplicated_ready_dispatch_is_not_filtered(self):
        activity,probe=self.source(gate.ACTIVITY),self.source(gate.PROBE)
        engine=self.source(gate.ENGINE)
        seam=gate.CURRENT_READY_DISPATCH
        self.assertEqual(1,engine.count(seam))
        for mutation in [engine.replace(seam,'',1),engine.replace(seam,seam+seam,1),engine.replace(seam,seam.replace('awaitingReady','true'),1)]:
            self.assertTrue(gate.scope_errors(activity,probe,mutation))
    def test_unapproved_transport_and_permission_edits_still_fail(self):
        activity,probe=self.source(gate.ACTIVITY),self.source(gate.PROBE)
        engine=self.source(gate.ENGINE)
        for before,after in [('code != 207','code != 206'),('if (granted) scan(gen)','if (true) scan(gen)')]:
            self.assertIn(before,engine)
            self.assertTrue(gate.scope_errors(activity,probe,engine.replace(before,after,1)))
        before,after='watchPackage="watchapp.nexus.0zzip"','watchPackage="different"'
        self.assertIn(before,probe)
        self.assertTrue(gate.scope_errors(activity,probe.replace(before,after,1)))
    def test_timeout_words_are_finite_and_not_a_version_test_comment(self):
        engine=self.source(gate.ENGINE)
        self.assertIn(READY_TEXT:=gate.CURRENT_READY_TIMEOUT,engine)
        self.assertTrue(gate.scope_errors(self.source(gate.ACTIVITY),self.source(gate.PROBE),engine.replace(READY_TEXT,'start again',1)))

if __name__=='__main__':unittest.main(verbosity=2)
