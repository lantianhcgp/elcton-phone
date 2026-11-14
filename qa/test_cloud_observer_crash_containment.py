#!/usr/bin/env python3
"""Independent actual-filesystem negatives for the R10 crash observer; no ADB/device."""
import importlib.util
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


def observer():
    spec = importlib.util.spec_from_file_location('crash_observer_containment_probe', ROOT / 'qa/cloud_emulator_observer.py')
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class CrashContainment(unittest.TestCase):
    def run_capture(self, source, output, custom_open=None):
        module = observer()
        real_path = module.Path
        source_redirect = lambda value: source if str(value) == '/tmp/android-runner' else real_path(value)
        with patch.object(module, 'Path', side_effect=source_redirect):
            if custom_open is None:
                try:
                    module.capture_crashdata(output)
                except OSError:
                    pass  # Rejected observer-only capture is legal; assert zero escaped writes below.
            else:
                with patch.object(module.os, 'open', side_effect=custom_open(module.os.open)):
                    try:
                        module.capture_crashdata(output)
                    except OSError:
                        pass

    def test_output_ancestor_symlink_rejected(self):
        with tempfile.TemporaryDirectory() as home:
            base = Path(home)
            source = base / 'source'
            source.mkdir()
            (source / 'emu-crash-normal.db').write_bytes(b'crash fixture, not a secret')
            outside = base / 'outside'
            outside.mkdir()
            (outside / 'output').mkdir()
            (base / 'linked-parent').symlink_to(outside, target_is_directory=True)
            self.run_capture(source, base / 'linked-parent/output')
            self.assertEqual(list((outside / 'output').iterdir()), [], 'Observer wrote through output ancestor symlink')

    def test_source_ancestor_symlink_rejected(self):
        with tempfile.TemporaryDirectory() as home:
            base = Path(home)
            outside = base / 'outside'
            outside.mkdir()
            source = outside / 'source'
            source.mkdir()
            (source / 'emu-crash-normal.db').write_bytes(b'crash fixture, not a secret')
            (base / 'linked-parent').symlink_to(outside, target_is_directory=True)
            output = base / 'output'
            output.mkdir()
            self.run_capture(base / 'linked-parent/source', output)
            self.assertFalse((output / 'emulator-crashdata/emu-crash-normal.db').exists(), 'Observer read through source ancestor symlink')

    def test_index_written_only_through_pinned_output_fd(self):
        with tempfile.TemporaryDirectory() as home:
            base = Path(home)
            source = base / 'source'
            source.mkdir()
            (source / 'emu-crash-normal.db').write_bytes(b'normal crash fixture')
            output = base / 'output'
            output.mkdir()
            outside = base / 'outside'
            outside.mkdir()
            pinned = base / 'pinned-output'
            swapped = []

            def custom(real_open):
                def opened(path, flags, *args, **kwargs):
                    fd = real_open(path, flags, *args, **kwargs)
                    if flags & os.O_DIRECTORY and not swapped:
                        inode = os.fstat(fd)
                        target = output.stat()
                        if (inode.st_dev, inode.st_ino) == (target.st_dev, target.st_ino):
                            output.rename(pinned)
                            output.symlink_to(outside, target_is_directory=True)
                            swapped.append(True)
                    return fd
                return opened
            self.run_capture(source, output, custom_open=custom)
            self.assertEqual(swapped, [True], 'Real output dirfd race was not reached')
            self.assertEqual(list(outside.iterdir()), [], 'Observer index escaped to replaced lexical output')
            self.assertTrue((pinned / 'crashdata-index.json').is_file(), 'Index was not written in pinned output')
            self.assertEqual((pinned / 'emulator-crashdata/emu-crash-normal.db').read_bytes(), b'normal crash fixture')

    def test_regular_copy_index_and_payload_remain_exact(self):
        with tempfile.TemporaryDirectory() as home:
            base = Path(home)
            source = base / 'source'
            source.mkdir()
            (source / 'emu-crash-normal.db').write_bytes(b'normal crash fixture')
            output = base / 'output'
            output.mkdir()
            self.run_capture(source, output)
            self.assertEqual((output / 'emulator-crashdata/emu-crash-normal.db').read_bytes(), b'normal crash fixture')
            self.assertTrue((output / 'crashdata-index.json').is_file())

    def test_index_leaf_symlink_rejected_without_external_write(self):
        with tempfile.TemporaryDirectory() as home:
            base = Path(home)
            source = base / 'source'
            source.mkdir()
            (source / 'emu-crash-normal.db').write_bytes(b'normal crash fixture')
            output = base / 'output'
            output.mkdir()
            outside = base / 'outside'
            outside.mkdir()
            (output / 'crashdata-index.json').symlink_to(outside / 'new-file')
            self.run_capture(source, output)
            self.assertFalse((outside / 'new-file').exists())


if __name__ == '__main__':
    unittest.main(verbosity=2)

