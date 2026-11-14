#!/usr/bin/env python3
"""Prevent interpreter drift and preserve exact APK source during QA-only CI reruns."""
from pathlib import Path
import re
import unittest

class DiagnosticWorkflowEnvironmentTest(unittest.TestCase):
    def test_python_is_fixed_before_pillow_without_changing_pinned_pixels(self):
        s = (Path(__file__).resolve().parents[1] / '.github/workflows/ui-smoke.yml').read_text()
        self.assertIn('uses: actions/setup-python@v5', s)
        self.assertIn("python-version: '3.12'", s)
        self.assertLess(s.index('uses: actions/setup-python@v5'), s.index('Pillow==11.2.1'))
        self.assertIn('Pillow==11.2.1', s)
        self.assertIn('ram-size: 2048M', s)
        self.assertIn('-gpu swiftshader_indirect', s)
    def test_action_script_lines_are_standalone_shell_programs(self):
        import subprocess
        s = (Path(__file__).resolve().parents[1] / '.github/workflows/ui-smoke.yml').read_text()
        tail = s.split('          script:', 1)[1].split('      - uses:', 1)[0]
        commands = [line.strip() for line in tail.splitlines() if line.strip() not in ('', '|')]
        self.assertTrue(commands)
        for command in commands:
            run = subprocess.run(['sh', '-n', '-c', command], capture_output=True, text=True)
            self.assertEqual(run.returncode, 0, 'Action runs each line separately: ' + command)
    def test_exact_apk_checkout_may_be_pinned_for_qa_only_environment_fix(self):
        s = (Path(__file__).resolve().parents[1] / '.github/workflows/ui-smoke.yml').read_text()
        self.assertIn('build_sha:', s)
        self.assertIn('ref: ${{ inputs.build_sha || github.sha }}', s)
        self.assertIn('run-id: ${{ inputs.build_run }}', s)

if __name__ == '__main__':
    unittest.main(verbosity=2)
