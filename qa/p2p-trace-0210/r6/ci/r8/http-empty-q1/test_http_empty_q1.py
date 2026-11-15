#!/usr/bin/env python3
"""R8-QUALITY-HTTP-EMPTY-01: real nested API, offline responses only."""
from pathlib import Path
import io
import json
import sys
from types import SimpleNamespace
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import test_post_http_status as original_fixture
# The existing file calls its loader actual_api; preserve its bytes.
load_api = getattr(original_fixture, 'load_api', original_fixture.actual_api)


class ExactEmpty204(unittest.TestCase):
    def exercise(self, stdout, returncode=0):
        module, tree, payload = load_api()
        calls = []
        sleeps = []
        log = io.StringIO()
        secret = 'OFFLINE_ONLY_CREDENTIAL_SENTINEL_Q1'
        def fake_run(*args, **kwargs):
            calls.append(args[0])
            self.assertEqual(len(calls), 1, 'POST retry forbidden')
            return SimpleNamespace(returncode=returncode, stdout=stdout)
        def fake_sleep(seconds):
            sleeps.append(seconds)
            raise AssertionError('POST retry sleep forbidden')
        namespace = dict(vars(module))
        namespace.update(args=['dispatch-ui'], suite='full',
                         config='header = "Authorization: Bearer ' + secret + '"\n',
                         log=log, subprocess=SimpleNamespace(run=fake_run),
                         time=SimpleNamespace(time=lambda: 0, sleep=fake_sleep))
        exec(compile(tree, str(original_fixture.P), 'exec'), namespace)
        api = namespace['factory']()
        accepted = False
        error = None
        value = None
        try:
            value = api('/actions/workflows/ui-smoke.yml/dispatches', payload)
            accepted = True
        except AssertionError as exc:
            error = str(exc)
        self.assertEqual(len(calls), 1)
        self.assertEqual(sleeps, [])
        self.assertNotIn('--retry', calls[0])
        self.assertNotIn('--location', calls[0])
        self.assertNotIn(secret, log.getvalue())
        self.assertNotIn('Authorization', log.getvalue())
        self.assertNotIn('Bearer', log.getvalue())
        rows = [json.loads(line) for line in log.getvalue().splitlines()]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['attempt'], 1)
        self.assertEqual(rows[0]['method'], 'POST')
        self.assertEqual(rows[0]['exit'], returncode)
        self.assertIs(rows[0]['credential_values_not_saved'], True)
        print(json.dumps({'fixture': self._testMethodName, 'stdout_repr': repr(stdout),
                          'curl_returncode': returncode, 'accepted': accepted,
                          'post_calls': len(calls), 'retry_sleeps': len(sleeps),
                          'credential_logging': False}, sort_keys=True), flush=True)
        return accepted, error, value

    def reject(self, stdout, returncode=0):
        accepted, error, _ = self.exercise(stdout, returncode)
        self.assertFalse(accepted, 'Non-exact empty HTTP204 response was accepted')
        self.assertIn('DO NOT repeat POST', error or '')

    def test_whitespace_204_rejected(self):
        self.reject(b' \t\r\n\nR8-HTTP-STATUS:204')

    def test_tab_only_204_rejected(self):
        self.reject(b'\t\nR8-HTTP-STATUS:204')

    def test_newline_only_204_rejected(self):
        self.reject(b'\n\nR8-HTTP-STATUS:204')

    def test_nonempty_204_rejected(self):
        self.reject(b'nonempty\nR8-HTTP-STATUS:204')

    def test_missing_status_rejected(self):
        self.reject(b'')

    def test_empty_302_rejected(self):
        self.reject(b'\nR8-HTTP-STATUS:302')

    def test_failed_curl_204_rejected(self):
        self.reject(b'\nR8-HTTP-STATUS:204', returncode=7)

    def test_exact_empty_204_accepted(self):
        accepted, error, value = self.exercise(b'\nR8-HTTP-STATUS:204')
        self.assertTrue(accepted)
        self.assertIsNone(error)
        self.assertIsNone(value)


if __name__ == '__main__':
    unittest.main(verbosity=2)
