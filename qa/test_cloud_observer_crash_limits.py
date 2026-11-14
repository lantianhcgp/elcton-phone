#!/usr/bin/env python3
"""Additive crashdata resource/ancestor/pinned-index regression from real R10 rejects."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


def observer():
    spec = importlib.util.spec_from_file_location('observer_crash_limits', ROOT / 'qa/cloud_emulator_observer.py')
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class CrashBudgetTests(unittest.TestCase):
    def fixture(self, directory):
        base = Path(directory)
        source = base / 'source'
        output = base / 'output'
        source.mkdir()
        output.mkdir()
        return source, output

    def capture(self, source, output, configure=None):
        module = observer()
        real_path = module.Path
        if configure is not None:
            configure(module)
        with patch.object(module, 'Path', side_effect=lambda value: source if str(value) == '/tmp/android-runner' else real_path(value)):
            module.capture_crashdata(output)
        return module

    def test_empty_crashes_cannot_create_unbounded_files_or_index(self):
        with tempfile.TemporaryDirectory() as directory:
            source, output = self.fixture(directory)
            for n in range(257):
                (source / ('emu-crash-' + str(n) + '.dmp')).write_bytes(b'')
            module = self.capture(source, output)
            payloads = list((output / 'emulator-crashdata').glob('*.dmp'))
            self.assertLessEqual(len(payloads), 64, 'Zero-byte payloads bypassed copy budget')
            self.assertLessEqual((output / 'crashdata-index.json').stat().st_size, 32768, 'Index is not bounded')
            budget = json.loads((output / 'crashdata-budget.json').read_bytes())
            self.assertEqual(budget['copied_files'], len(payloads))
            self.assertTrue(budget['stopped_reason'] in ('copy-limit', 'scan-limit', 'index-limit'))
            self.assertLessEqual(budget['scanned_entries'], module.CRASH_SCAN_LIMIT)

    def test_scan_budget_uses_lazy_directory_iterator_not_listdir(self):
        with tempfile.TemporaryDirectory() as directory:
            source, output = self.fixture(directory)
            for n in range(257):
                (source / ('ignored-' + str(n) + '.log')).write_bytes(b'')
            with patch.object(os, 'listdir', side_effect=AssertionError('Unbounded listdir prohibited')):
                module = self.capture(source, output)
            budget = json.loads((output / 'crashdata-budget.json').read_bytes())
            self.assertLessEqual(budget['scanned_entries'], module.CRASH_SCAN_LIMIT)
            self.assertEqual(budget['stopped_reason'], 'scan-limit')
            self.assertEqual(json.loads((output / 'crashdata-index.json').read_bytes()), [])

    def test_directory_depth_bound_prevents_unbounded_fd_recursion(self):
        with tempfile.TemporaryDirectory() as directory:
            source, output = self.fixture(directory)
            nested = source
            for _ in range(20):
                nested = nested / 'nested'
                nested.mkdir()
            (nested / 'emu-crash-deep.dmp').write_bytes(b'fixture')
            module = self.capture(source, output)
            self.assertFalse((output / 'emulator-crashdata').joinpath(*(['nested'] * 20), 'emu-crash-deep.dmp').exists())
            budget = json.loads((output / 'crashdata-budget.json').read_bytes())
            self.assertEqual(budget['stopped_reason'], 'depth-limit')
            self.assertLessEqual(budget['max_depth'], module.CRASH_DEPTH_LIMIT)

    def test_index_size_limit_precedes_new_copy(self):
        with tempfile.TemporaryDirectory() as directory:
            source, output = self.fixture(directory)
            for n in range(30):
                (source / ('emu-crash-' + str(n) + '-' + 'x' * 120 + '.dmp')).write_bytes(b'fixture')
            module = self.capture(source, output, configure=lambda m: setattr(m, 'CRASH_INDEX_LIMIT', 500))
            self.assertLessEqual((output / 'crashdata-index.json').stat().st_size, 500)
            budget = json.loads((output / 'crashdata-budget.json').read_bytes())
            self.assertEqual(budget['stopped_reason'], 'index-limit')
            records = json.loads((output / 'crashdata-index.json').read_bytes())
            payloads = list((output / 'emulator-crashdata').glob('*.dmp'))
            self.assertEqual(len(payloads), len(records), 'Copy ran despite index budget')
            self.assertEqual(budget['copied_files'], len(payloads))

    def test_total_payload_limit_stops_before_additional_file(self):
        with tempfile.TemporaryDirectory() as directory:
            source, output = self.fixture(directory)
            for n in range(4):
                (source / ('emu-crash-' + str(n) + '.dmp')).write_bytes(b'12345678')
            module = self.capture(source, output, configure=lambda m: setattr(m, 'CRASH_TOTAL_LIMIT', 12))
            budget = json.loads((output / 'crashdata-budget.json').read_bytes())
            self.assertEqual(budget['stopped_reason'], 'total-limit')
            self.assertLessEqual(budget['content_bytes'], 12)
            self.assertEqual(budget['copied_files'], 1)
            record = json.loads((output / 'crashdata-index.json').read_bytes())[0]
            self.assertEqual(record['bytes'], 8)
            self.assertEqual(record['sha256'], hashlib.sha256(b'12345678').hexdigest())


if __name__ == '__main__':
    unittest.main(verbosity=2)
