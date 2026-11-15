#!/usr/bin/env python3
"""Offline R8 official DNS transport parameter regression; no network/device."""
import importlib.util
from pathlib import Path
import unittest

P = Path(__file__).with_name('ui_transport.py')

class DnsParameters(unittest.TestCase):
    def test_exact_https_sni_and_no_insecure_or_wrong_host(self):
        spec = importlib.util.spec_from_file_location('r8_dns_transport_under_test', P)
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.assertTrue(hasattr(module, 'curl_command'), 'Official verified DNS argument helper missing')
        args = module.curl_command('/actions/runs/43718640929')
        self.assertEqual(args[-1], 'https://api.github.com/repos/lantianhcgp/elcton-phone/actions/runs/43718640929')
        self.assertEqual(args[args.index('--resolve') + 1], 'api.github.com:443:20.205.243.168')
        self.assertEqual(args[args.index('--config') + 1], '-')
        self.assertNotIn('--insecure', args)
        self.assertNotIn('-k', args)
        self.assertNotIn('--retry', args)
        with self.assertRaises(AssertionError):
            module.curl_command('https://another-host.test')
        with self.assertRaises(AssertionError):
            module.curl_command('/../dispatches')

if __name__ == '__main__':
    unittest.main(verbosity=2)
