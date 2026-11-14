#!/usr/bin/env python3
"""Fixture-only identity negatives; never changes repository evidence or links."""
import importlib.util
import io
from pathlib import Path
import tarfile
import unittest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('exact_readback', HERE / 'remote_readback_exact.py')
assert spec and spec.loader
M = importlib.util.module_from_spec(spec)
spec.loader.exec_module(M)


def fixture(mode='ok'):
    stream = io.BytesIO()
    with tarfile.open(fileobj=stream, mode='w') as archive:
        items = [('a.txt', b'original', False), ('probe-link', b'/outside/literal-do-not-follow', True)]
        if mode == 'missing':
            items = items[:1]
        if mode == 'duplicate':
            items.append(items[0])
        for name, data, link in items:
            member = tarfile.TarInfo('repository/' + name)
            if link and mode != 'link-as-file':
                member.type = tarfile.SYMTYPE
                member.linkname = ('/mutated' if mode == 'wrong-link' else data.decode())
                archive.addfile(member)
            else:
                if mode == 'one-byte' and name == 'a.txt':
                    data = b'originaL'
                member.size = len(data)
                archive.addfile(member, io.BytesIO(data))
    stream.seek(0)
    return stream


class CompareTests(unittest.TestCase):
    def test_exact_ordinary_and_literal_symlink(self):
        expected = {'a.txt': {'mode': '100644', 'oid': 'a'}, 'probe-link': {'mode': '120000', 'oid': 'b'}}
        blobs = {'a': b'original', 'b': b'/outside/literal-do-not-follow'}
        with tarfile.open(fileobj=fixture(), mode='r|') as archive:
            rows = M.compare_archive(archive, expected, blobs.__getitem__)
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows['probe-link']['git_mode'], '120000')
        self.assertEqual(rows['probe-link']['bytes'], len(blobs['b']))

    def test_all_negatives_rejected(self):
        expected = {'a.txt': {'mode': '100644', 'oid': 'a'}, 'probe-link': {'mode': '120000', 'oid': 'b'}}
        blobs = {'a': b'original', 'b': b'/outside/literal-do-not-follow'}
        for mode in ('one-byte', 'wrong-link', 'link-as-file', 'missing', 'duplicate'):
            with self.subTest(mode=mode):
                with tarfile.open(fileobj=fixture(mode), mode='r|') as archive:
                    with self.assertRaises(AssertionError):
                        M.compare_archive(archive, expected, blobs.__getitem__)


if __name__ == '__main__':
    unittest.main(verbosity=2)
