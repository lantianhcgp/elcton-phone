#!/usr/bin/env python3
"""A successful instrumentation run cannot mask a failed pixel gate."""
import unittest
from pathlib import Path


class FinalReportGateTest(unittest.TestCase):
    def test_success_report_is_emitted_only_after_color_coverage_and_crash_checks(self):
        source = Path(__file__).with_name("emulator_install_and_tour.py").read_text()
        success_report = source.rfind("(out/'report.json').write_text")
        pixel_gate = source.rfind("'qa/verify_system_bars.py'")
        coverage_gate = source.rfind("'Incomplete component-tour coverage'")
        crash_gate = source.rfind("'Application crashed'")
        self.assertGreater(success_report, pixel_gate, "report marks success before the pixel gate")
        self.assertGreater(success_report, coverage_gate, "report marks success before coverage gate")
        self.assertGreater(success_report, crash_gate, "report marks success before crash gate")
        self.assertIn("'system_bar_pixels'", source)


if __name__ == "__main__":
    unittest.main(verbosity=2)
