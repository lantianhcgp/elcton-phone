#!/usr/bin/env python3
"""Synthetic checks of explicit cloud UI permission setup, not an Android PASS."""
import ast
from pathlib import Path
import unittest
from typing import Any, Callable, cast

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'qa/emulator_install_and_tour.py'


class NotificationFixtureTest(unittest.TestCase):
    def fixture(self, sdk, granted=True, grant_error=None):
        module = ast.parse(SOURCE.read_text())
        nodes = [node for node in module.body if isinstance(node, ast.FunctionDef) and node.name == 'prepare_ui_notifications']
        self.assertEqual(1, len(nodes), 'one explicit UI-only notification preparation helper')
        calls = []
        def shell(command):
            calls.append(command)
            if command == 'getprop ro.build.version.sdk':
                return str(sdk)
            if command == 'pm grant com.hcbiu.elcton android.permission.POST_NOTIFICATIONS':
                if grant_error:
                    raise grant_error
                return ''
            if command == 'dumpsys package com.hcbiu.elcton':
                return 'android.permission.POST_NOTIFICATIONS: granted=' + str(granted).lower()
            raise AssertionError('unexpected device command: ' + command)
        namespace: dict[str, Any] = {'shell': shell}
        executable = ast.Module(body=cast(list[ast.stmt], nodes), type_ignores=[])
        exec(compile(executable, str(SOURCE), 'exec'), namespace)
        return cast(Callable[[], dict[str, Any]], namespace['prepare_ui_notifications']), calls

    def test_api32_does_not_attempt_runtime_notification_grant(self):
        prepare, calls = self.fixture(32)
        self.assertEqual({'sdk': 32, 'notification_fixture': 'not-required'}, prepare())
        self.assertEqual(['getprop ro.build.version.sdk'], calls)

    def test_api33_grants_before_readback_and_records_exact_scope(self):
        prepare, calls = self.fixture(33)
        result = prepare()
        self.assertEqual({'sdk': 33, 'notification_fixture': 'pregranted-ui-only', 'granted': True}, result)
        self.assertEqual(['getprop ro.build.version.sdk', 'pm grant com.hcbiu.elcton android.permission.POST_NOTIFICATIONS', 'dumpsys package com.hcbiu.elcton'], calls)

    def test_api33_failed_readback_is_not_reported_as_permission_pass(self):
        prepare, _ = self.fixture(33, granted=False)
        with self.assertRaises(AssertionError):
            prepare()

    def test_grant_failure_is_propagated_before_instrumentation(self):
        error = RuntimeError('actual shell failure')
        prepare, calls = self.fixture(33, grant_error=error)
        with self.assertRaises(RuntimeError) as raised:
            prepare()
        self.assertIs(error, raised.exception)
        self.assertEqual(2, len(calls))


if __name__ == '__main__':
    unittest.main(verbosity=2)
