#!/usr/bin/env python3
"""R8 helper-only POST HTTP status regression. All replies are offline fixtures."""
from pathlib import Path
import ast
import importlib.util
import io
import json
from types import SimpleNamespace
import unittest

P = Path(__file__).with_name('ui_transport.py')


def actual_api():
    spec = importlib.util.spec_from_file_location('r8_http_fixture', P)
    assert spec is not None and spec.loader is not None
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    tree = ast.parse(P.read_bytes())
    main = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'main')
    api = next(n for n in ast.walk(main) if isinstance(n, ast.FunctionDef) and n.name == 'api')
    outer = ast.parse('def factory():\n    post_count = 0\n').body[0]
    assert isinstance(outer, ast.FunctionDef)
    outer.body += [api, ast.parse('return api').body[0]]
    module = ast.fix_missing_locations(ast.Module(body=[outer], type_ignores=[]))
    payload = {'ref': m.BRANCH, 'inputs': {'build_run': '43715446826', 'build_sha': m.SOURCE,
               'api_level': '33', 'navigation_mode': 'three-button', 'qa_suite': 'full'}}
    return m, module, payload


class PostStatus(unittest.TestCase):
    def call_fixture(self, status):
        m, module, payload = actual_api()
        calls = []
        def fake_run(*a, **kw):
            calls.append(a)
            return SimpleNamespace(returncode=0, stdout=b'\nR8-HTTP-STATUS:' + status.encode())
        ns = dict(vars(m))
        ns.update(args=['dispatch-ui'], suite='full', config='', log=io.StringIO(),
                  subprocess=SimpleNamespace(run=fake_run), time=SimpleNamespace(time=lambda: 0, sleep=lambda n: None))
        exec(compile(module, str(P), 'exec'), ns)
        return ns['factory'](), payload, calls

    def test_empty_http302_fails_without_retry(self):
        api, payload, calls = self.call_fixture('302')
        with self.assertRaisesRegex(AssertionError, 'exact HTTP204'):
            api('/actions/workflows/ui-smoke.yml/dispatches', payload)
        self.assertEqual(len(calls), 1)

    def test_true_http204_accepted_once(self):
        api, payload, calls = self.call_fixture('204')
        self.assertIsNone(api('/actions/workflows/ui-smoke.yml/dispatches', payload))
        self.assertEqual(len(calls), 1)
        self.assertIn('--write-out', calls[0][0])


if __name__ == '__main__':
    unittest.main(verbosity=2)
