#!/usr/bin/env python3
"""Real filesystem guards for private token output; no shell, app, or mocked HTTP."""
import os
from pathlib import Path
import stat
import tempfile
import unittest
from termux_mcp import store_private


class TokenPrivateFileTests(unittest.TestCase):
    def test_new_and_existing_token_file_remain_0600(self):
        with tempfile.TemporaryDirectory(dir=Path.home()) as directory:
            file = Path(directory) / 'subdir/token'
            token = b'a' * 64  # SYNTHETIC fixture only.
            store_private(file, token)
            self.assertEqual(token, file.read_bytes())
            self.assertEqual(0o600, stat.S_IMODE(file.stat().st_mode))
            os.chmod(file, 0o644)
            store_private(file, b'b' * 64)
            self.assertEqual(b'b' * 64, file.read_bytes())
            self.assertEqual(0o600, stat.S_IMODE(file.stat().st_mode))

    def test_shared_documents_path_is_rejected_before_write(self):
        with self.assertRaisesRegex(ValueError, 'Termux private home'):
            store_private(Path('/storage/emulated/0/Documents/DO_NOT_CREATE_mcp_token'), b'a' * 64)

    def test_final_symlink_is_rejected_without_touching_target(self):
        with tempfile.TemporaryDirectory(dir=Path.home()) as directory:
            root = Path(directory)
            real = root / 'real'
            real.write_bytes(b'unchanged')
            link = root / 'token'
            link.symlink_to(real)
            with self.assertRaises(OSError):
                store_private(link, b'a' * 64)
            self.assertEqual(b'unchanged', real.read_bytes())

    def test_parent_symlink_outside_home_is_rejected(self):
        with tempfile.TemporaryDirectory(dir=Path.home()) as directory:
            link = Path(directory) / 'shared'
            link.symlink_to('/storage/emulated/0/Documents', target_is_directory=True)
            with self.assertRaisesRegex(ValueError, 'Termux private home'):
                store_private(link / 'DO_NOT_CREATE_mcp_token', b'a' * 64)


if __name__ == '__main__':
    unittest.main(verbosity=2)
