#!/usr/bin/env python3
"""Exact new authorized delta does not relax the old observation-only gate."""
import unittest
from pathlib import Path
from qa import diag_source_gate as gate
ROOT=Path(__file__).resolve().parents[1]

class P2pReadySourceGateTest(unittest.TestCase):
    def source(self,path):return (ROOT/path).read_text()
    def test_only_reviewed_ready_delta_reverses_to_pinned_original(self):
        activity,probe=self.source(gate.ACTIVITY),self.source(gate.PROBE)
        self.assertEqual([],gate.scope_errors(activity,probe))
        self.assertEqual(gate.baseline(gate.PROBE),gate.without_probe_diagnostics(probe))
    def test_missing_or_duplicated_ready_dispatch_is_not_filtered(self):
        activity,probe=self.source(gate.ACTIVITY),self.source(gate.PROBE)
        seam='        PacketIngress.preparationError(m,awaitingReady,session!=null||exporting!=null)?.let { fail(it);return }\n'
        self.assertEqual(1,probe.count(seam))
        for mutation in [probe.replace(seam,'',1),probe.replace(seam,seam+seam,1),probe.replace(seam,seam.replace('awaitingReady','true'),1)]:
            self.assertTrue(gate.scope_errors(activity,mutation))
    def test_unapproved_transport_and_permission_edits_still_fail(self):
        activity,probe=self.source(gate.ACTIVITY),self.source(gate.PROBE)
        for before,after in [('code!=207','code!=206'),('if(granted)scan(gen)else{','if(true)scan(gen)else{'),('watchPackage="watchapp.nexus.0zzip"','watchPackage="different"')]:
            self.assertIn(before,probe)
            self.assertTrue(gate.scope_errors(activity,probe.replace(before,after,1)))
    def test_timeout_words_are_finite_and_not_a_version_test_comment(self):
        probe=self.source(gate.PROBE)
        self.assertIn(READY_TEXT:=gate.READY['patches'][gate.PROBE][1]['after'],probe)
        self.assertTrue(gate.scope_errors(self.source(gate.ACTIVITY),probe.replace(READY_TEXT,'start again',1)))

if __name__=='__main__':unittest.main(verbosity=2)
