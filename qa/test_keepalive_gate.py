#!/usr/bin/env python3
"""Local receipt-schema negative tests only: NO adb/Android execution."""
import unittest
from pathlib import Path
import diag_emulator_smoke as gate

SHA = "a" * 40
RUN = "receipt-negative-test"
KEYS = ("defaultOff", "noDefaultNotification", "onNotification", "backgroundHttp",
        "offPortClosed", "offNotificationRemoved", "businessAndTokenAndErrorsUnchanged",
        "bindFailureUiOffAndHintRetained", "startingNotActive", "activeChannelDeniedStopsAndUiOff",
        "backgroundChannelDeniedEventStops")


class KeepAliveGateTests(unittest.TestCase):
    def test_receipt_validator_is_available(self):
        self.assertTrue(callable(getattr(gate, "verify_keepalive_report", None)),
                        "CI must independently fail closed on the FGS receipt")

    def receipt(self):
        return {"passed": True, "sourceSha": SHA, "qaRun": RUN,
                **dict.fromkeys(KEYS, True), "permissionDeniedFailClosed": True}

    def test_current_receipt_and_pre33_branch(self):
        report = self.receipt()
        self.assertIs(report, gate.verify_keepalive_report(report, SHA, RUN, 33))
        del report["permissionDeniedFailClosed"]
        self.assertIs(report, gate.verify_keepalive_report(report, SHA, RUN, 30))

    def test_every_hard_assertion_rejects_missing_false_and_non_boolean(self):
        for key in ("passed", *KEYS, "permissionDeniedFailClosed"):
            for value in (None, False, 1, "true", [], {}):
                with self.subTest(key=key, value=value), self.assertRaises(AssertionError):
                    report = self.receipt()
                    if value is None:
                        del report[key]
                    else:
                        report[key] = value
                    gate.verify_keepalive_report(report, SHA, RUN, 34)

    def test_wrong_run_or_source_and_non_object_fail(self):
        for field, value in (("sourceSha", "b" * 40), ("sourceSha", SHA + "\n"), ("qaRun", "other")):
            with self.subTest(field=field, value=value), self.assertRaises(AssertionError):
                report = self.receipt(); report[field] = value
                gate.verify_keepalive_report(report, SHA, RUN, 33)
        for report in (None, [], True):
            with self.assertRaises(AssertionError):
                gate.verify_keepalive_report(report, SHA, RUN, 33)

    def test_notification_denial_runs_after_ordinary_background_measurement(self):
        source = (Path(__file__).resolve().parent / 'diag_emulator_smoke.py').read_text()
        self.assertLess(source.index('self.verify_normal_background(suite'), source.index('keepalive = self.adb('))
        self.assertLess(source.index('keepalive = self.adb('), source.index('verify_keepalive_report(keepalive_report'))
        self.assertIn('"keepalive-final-stop"', source)
        # Do not skip any receipt key when sequencing the destructive fixtures.
        body = source[source.index('def verify_keepalive_report('):source.index('def verify_one_test(')]
        for key in KEYS:
            self.assertTrue('"' + key + '"' in body, 'missing hard receipt key ' + key)

    def test_navigation_selector_uses_actual_026_bottom_bar_not_duplicate_header(self):
        import xml.etree.ElementTree as ET
        root = Path(__file__).resolve().parents[1]
        original = ET.parse(root / 'qa/diag-mcp-026/evidence/android-43535414635/diag-product/settings-version.xml').getroot()
        labels = [node for node in original.iter('node') if node.get('package') == gate.PACKAGE and node.get('text') == '设置']
        self.assertEqual(2, len(labels), 'Actual prior settings screenshot has a header and a navigation label')
        selected = gate.settings_navigation_node(original)
        self.assertEqual('true', selected.get('focusable'))
        self.assertEqual('true', selected.get('selected'))
        self.assertEqual(['设置'], [node.get('text') for node in selected.iter('node') if node.get('text')])
        for mutation in ('missing-navigation-label', 'disabled-navigation'):
            with self.subTest(mutation=mutation), self.assertRaises(AssertionError):
                tree = ET.parse(root / 'qa/diag-mcp-026/evidence/android-43535414635/diag-product/settings-version.xml').getroot()
                tab = gate.settings_navigation_node(tree)
                if mutation == 'disabled-navigation':
                    tab.set('enabled', 'false')
                else:
                    for node in tab.iter('node'):
                        if node.get('text') == '设置':
                            node.set('text', 'not-the-target')
                gate.settings_navigation_node(tree)

    def test_exact_one_test_result_gate(self):
        import subprocess
        def result(text, code=0):
            return subprocess.CompletedProcess([], code, text.encode(), b"")
        gate.verify_one_test(result("Time: 0.3\n\nOK (1 test)\n"), "fixture")
        for text, code in (("OK (2 tests)\n", 0), ("prefix OK (1 test)\n", 0),
                           ("OK (1 test)\nOK (1 test)\n", 0), ("OK (1 test)\nFAILURES\n", 0),
                           ("OK (1 test)\nINSTRUMENTATION_ABORTED\n", 0), ("OK (1 test)\n", 1)):
            with self.subTest(text=text, code=code), self.assertRaises(AssertionError):
                gate.verify_one_test(result(text, code), "fixture")


if __name__ == "__main__":
    unittest.main(verbosity=2)
