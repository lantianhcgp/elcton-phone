"""Focused R7 host tests: execute real guards, never compilation/large hashing.

Created before checking the Q1 final gate. Sandboxes are local TemporaryDirectory
children, and production evidence is read-only. Migration fixture is populated
from independent saved original evidence after the gate is confirmed.
"""
import ast
import contextlib
import io
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

QA = Path(__file__).resolve().parents[2]
ROOT = QA.parents[1]
GUARD_SCRIPTS = ('run_r6_final_regressions.py', 'check_r6_scope.py')


def guard_namespace(script, root, output):
    """Compile unchanged AST nodes of actual main through output mkdir only."""
    source = (QA / script).read_text()
    tree = ast.parse(source, filename=str(QA / script))
    main = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'main')
    stop = next(i for i, n in enumerate(main.body)
                if isinstance(n, ast.Expr) and isinstance(n.value, ast.Call)
                and isinstance(n.value.func, ast.Attribute) and n.value.func.attr == 'mkdir')
    # Top-level imports/constants/helpers are actual source nodes too; omit main
    # entrypoint, so tests cannot accidentally execute the non-guard work.
    definitions = [n for n in tree.body if not isinstance(n, ast.If) and n is not main]
    namespace = {'__name__': 'r7_guard_probe', '__file__': str(QA / script)}
    exec(compile(ast.Module(body=definitions, type_ignores=[]), str(QA / script), 'exec'), namespace)
    namespace['ROOT'] = root
    namespace['QA'] = root / 'qa/p2p-trace-0210'
    prefix = ast.Module(body=main.body[:stop + 1], type_ignores=[])
    with patch.object(sys, 'argv', [script, '--out', str(root / output)]):
        exec(compile(prefix, str(QA / script), 'exec'), namespace)
    return namespace


class OutputGuardTests(unittest.TestCase):
    def test_valid_new_output(self):
        for script in GUARD_SCRIPTS:
            with self.subTest(script=script), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                output = 'qa/p2p-trace-0210/r6/evidence/focused-valid'
                guard_namespace(script, root, output)
                self.assertTrue((root / output).is_dir())

    def test_reject_parent_traversal(self):
        for script in GUARD_SCRIPTS:
            with self.subTest(script=script), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                output = 'qa/p2p-trace-0210/r6/evidence/../escape'
                with self.assertRaises((SystemExit, ValueError)):
                    guard_namespace(script, root, output)
                self.assertFalse((root / output).exists())

    def test_reject_symlink_ancestor(self):
        for script in GUARD_SCRIPTS:
            with self.subTest(script=script), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                base = root / 'qa/p2p-trace-0210/r6/evidence'
                outside = root / 'outside'
                base.mkdir(parents=True)
                outside.mkdir()
                (base / 'link').symlink_to(outside, target_is_directory=True)
                output = 'qa/p2p-trace-0210/r6/evidence/link/escape'
                with self.assertRaises((SystemExit, ValueError)):
                    guard_namespace(script, root, output)
                self.assertEqual(list(outside.iterdir()), [])

    def test_reject_existing_empty_output(self):
        for script in GUARD_SCRIPTS:
            with self.subTest(script=script), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                output = 'qa/p2p-trace-0210/r6/evidence/existing-empty'
                (root / output).mkdir(parents=True)
                with self.assertRaises((SystemExit, ValueError, FileExistsError)):
                    guard_namespace(script, root, output)
                self.assertEqual(list((root / output).iterdir()), [])


class MigrationTests(unittest.TestCase):
    def test_actual_migration_preserves_original_table_and_registers_q1(self):
        import hashlib
        import json
        import runpy
        sha = lambda raw: hashlib.sha256(raw).hexdigest()
        frozen = QA / 'r6/evidence/identity-migration-q1'
        before = (frozen / 'previous-current-identity.json.source.txt').read_bytes()
        original = (frozen / 'previous-table.json.source.txt').read_bytes()
        expected_current = (QA / 'r6/current-identity.json').read_bytes()
        expected_table = (frozen / 'table.json').read_bytes()
        old = json.loads(before)
        current = json.loads(expected_current)
        self.assertEqual(sha(original), '4f12c91fbed49afe409a9361f8e23c3540f6db8234d34ad4969033764eb8944d')
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            q = root / 'qa/p2p-trace-0210/r6'
            table = q / 'evidence/identity-migration/table.json'
            table.parent.mkdir(parents=True)
            table.write_bytes(original)
            (q / 'current-identity.json').write_bytes(before)
            for path, row in current['source_identities'].items():
                raw = (frozen / (Path(path).name + '.current.source.txt')).read_bytes()
                self.assertEqual(sha(raw), row['current_sha256'])
                dest = root / path
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(raw)
            manifest = (ROOT / old['old_manifest']).read_bytes()
            self.assertEqual(sha(manifest), old['old_manifest_sha256'])
            dest = root / old['old_manifest']
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(manifest)
            runtime = 'app/src/main/java/com/hcbiu/elcton/DiagnosticRuntime.kt'
            namespace = runpy.run_path(str(QA / 'migrate_r6_quality_identity.py'), run_name='r7_isolated_migration')
            namespace['main'].__globals__.update(ROOT=root, Q=q)
            argv = ['migrate_r6_quality_identity.py', '--expected-runtime-sha256', current['source_identities'][runtime]['current_sha256']]
            with patch.object(sys, 'argv', argv), contextlib.redirect_stdout(io.StringIO()) as captured:
                namespace['main']()
            self.assertTrue(json.loads(captured.getvalue())['registered'])
            # Validate real migration succeeds before the targeted immutability assertion.
            self.assertEqual((q / 'current-identity.json').read_bytes(), expected_current)
            self.assertEqual((q / 'evidence/identity-migration-q1/table.json').read_bytes(), expected_table)
            self.assertEqual((q / 'evidence/identity-migration-q1/previous-table.json.source.txt').read_bytes(), original)
            self.assertEqual((root / old['old_manifest']).read_bytes(), manifest)
            self.assertEqual(table.read_bytes(), original, 'Historical SPEC R2 table was overwritten')


class DeliveryIdentityTests(unittest.TestCase):
    def test_both_identity_table_reads_use_q1(self):
        tree = ast.parse((QA / 'finalize_r6_delivery.py').read_text())
        reads = [n for n in ast.walk(tree) if isinstance(n, ast.Call)
                 and isinstance(n.func, ast.Name) and n.func.id == 'read'
                 and n.args and isinstance(n.args[0], ast.BinOp)
                 and isinstance(n.args[0].right, ast.Constant)
                 and str(n.args[0].right.value).endswith('/table.json')]
        self.assertEqual(len(reads), 2)
        self.assertEqual([n.args[0].right.value for n in reads],
                         ['evidence/identity-migration-q1/table.json'] * 2)


if __name__ == '__main__':
    unittest.main(verbosity=2)
