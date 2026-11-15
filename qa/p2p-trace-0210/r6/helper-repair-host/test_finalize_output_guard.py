#!/usr/bin/env python3
"""Exact delivery main prefix: no APK/read/network after output creation."""
import ast
from pathlib import Path
import sys
import tempfile
import unittest

QA = Path(__file__).resolve().parents[2]
TEXT = (QA / 'finalize_r6_delivery.py').read_text()
TREE = ast.parse(TEXT)
FUNC = next(n for n in TREE.body if isinstance(n, ast.FunctionDef) and n.name == 'main')
PREFIX = []
for node in FUNC.body:
    PREFIX.append(node)
    if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call) and isinstance(node.value.func, ast.Attribute) and node.value.func.attr == 'mkdir':
        break
else:
    raise AssertionError('Exact output creation missing')
CODE = compile(ast.Module(body=PREFIX, type_ignores=[]), 'actual-finalize-main-prefix', 'exec')

class OutputTests(unittest.TestCase):
    def run_prefix(self, root, path):
        import argparse
        import re
        old = sys.argv
        sys.argv = ['finalize_r6_delivery.py', '--source', 'a' * 40, '--build-receipt', 'unused', '--diagnostics-receipt', 'unused', '--full-receipt', 'unused', '--apk', 'unused', '--out', str(path)]
        try:
            exec(CODE, {'argparse': argparse, 're': re, 'Path': Path, 'Q': root})
        finally:
            sys.argv = old

    def test_valid(self):
        with tempfile.TemporaryDirectory() as tmp:
            q = Path(tmp); (q / 'ci').mkdir()
            out = q / 'ci/new'
            self.run_prefix(q, out)
            self.assertTrue(out.is_dir())
            self.assertEqual(list(out.iterdir()), [])

    def test_traversal(self):
        with tempfile.TemporaryDirectory() as tmp:
            q = Path(tmp); (q / 'ci').mkdir()
            with self.assertRaises((AssertionError, SystemExit)):
                self.run_prefix(q, q / 'ci/../escape')
            self.assertFalse((q / 'escape').exists())

    def test_symlink(self):
        with tempfile.TemporaryDirectory() as tmp:
            q = Path(tmp); (q / 'ci').mkdir(); (q / 'external').mkdir()
            (q / 'ci/link').symlink_to(q / 'external', target_is_directory=True)
            with self.assertRaises((AssertionError, SystemExit)):
                self.run_prefix(q, q / 'ci/link/escape')
            self.assertFalse((q / 'external/escape').exists())

    def test_existing(self):
        with tempfile.TemporaryDirectory() as tmp:
            q = Path(tmp); out = q / 'ci/old'; out.mkdir(parents=True)
            with self.assertRaises(FileExistsError):
                self.run_prefix(q, out)
            self.assertEqual(list(out.iterdir()), [])

if __name__ == '__main__':
    unittest.main(verbosity=2)
