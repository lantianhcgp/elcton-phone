#!/usr/bin/env python3
"""Helper-only transport edge tests. No network/dispatch/device actions."""
from pathlib import Path
import importlib.util
import subprocess
import sys
import unittest

P = Path(__file__).with_name('ui_transport.py')


def load():
    spec = importlib.util.spec_from_file_location('r8_transport_test', P)
    assert spec is not None and spec.loader is not None
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


class TransportEdges(unittest.TestCase):
    def test_single_post_never_follows_redirect(self):
        m = load()
        args = m.curl_command('/actions/workflows/ui-smoke.yml/dispatches', post=True)
        self.assertNotIn('--location', args)
        self.assertNotIn('--retry', args)
        self.assertNotIn('--insecure', args)
        self.assertNotIn('-k', args)
        self.assertIn('--resolve', args)
        self.assertEqual(args[-1], 'https://api.github.com/repos/lantianhcgp/elcton-phone/actions/workflows/ui-smoke.yml/dispatches')

    def test_optimized_cli_fails_before_io(self):
        p = subprocess.run([sys.executable, '-O', '-B', str(P)], capture_output=True)
        self.assertNotEqual(p.returncode, 0)
        self.assertIn(b'Optimized Python refuses', p.stderr)
        self.assertNotIn(b'AssertionError', p.stderr)

    def test_optimized_invalid_post_cannot_be_accepted(self):
        code = ('import importlib.util;'
                f's=importlib.util.spec_from_file_location("r8opt",{str(P)!r});'
                'm=importlib.util.module_from_spec(s);s.loader.exec_module(m);'
                'm.allowed_post("/actions/workflows/build.yml/dispatches",{},"full")')
        p = subprocess.run([sys.executable, '-O', '-B', '-c', code], capture_output=True)
        self.assertNotEqual(p.returncode, 0)
        self.assertIn(b'Optimized Python refuses', p.stderr)


if __name__ == '__main__':
    unittest.main(verbosity=2)
