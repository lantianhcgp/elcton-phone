#!/usr/bin/env python3
"""Cloud fixture intent identity checks; synthetic, not Android lifecycle proof."""
from pathlib import Path
import re
import shlex
import unittest

ROOT = Path(__file__).resolve().parents[1]
TEST = ROOT / 'app/src/androidTest/java/com/hcbiu/elcton/McpKeepAliveTest.kt'
BEFORE = ROOT / 'qa/release-029/evidence/resume-1720/resume-third/McpKeepAliveTest.kt.before.original'
OLD = 'am start -n com.hcbiu.elcton/.MainActivity'
NEW = OLD + ' -a android.intent.action.MAIN -c android.intent.category.LAUNCHER'


def launcher_identity(command):
    tokens = shlex.split(command)
    if tokens[:2] != ['am', 'start']:
        return None
    values = {}
    for flag in ('-n', '-a', '-c'):
        if tokens.count(flag) != 1:
            return None
        index = tokens.index(flag)
        if index + 1 == len(tokens):
            return None
        values[flag] = tokens[index + 1]
    return values


class KeepAliveReturnFixtureTest(unittest.TestCase):
    def commands(self):
        return re.findall(r'device\.executeShellCommand\("(am start [^"]+)"\)', TEST.read_text())

    def assert_launcher_return(self, command):
        self.assertEqual({'-n': 'com.hcbiu.elcton/.MainActivity',
                          '-a': 'android.intent.action.MAIN',
                          '-c': 'android.intent.category.LAUNCHER'},
                         launcher_identity(command), 'return must reuse initial launcher intent')
        self.assertEqual(shlex.split(NEW), shlex.split(command), 'no extra force/relaunch flags')

    def test_first_return_before_channel_denial_reuses_launched_activity(self):
        commands = self.commands()
        self.assertEqual(2, len(commands))
        self.assert_launcher_return(commands[0])

    def test_second_return_after_channel_denial_reuses_launched_activity(self):
        commands = self.commands()
        self.assertEqual(2, len(commands))
        self.assert_launcher_return(commands[1])

    def test_all_existing_assertions_and_other_fixture_bytes_are_unchanged(self):
        original = BEFORE.read_bytes()
        current = TEST.read_bytes()
        self.assertEqual(2, original.count(OLD.encode()))
        self.assertEqual(original, current.replace(NEW.encode(), OLD.encode()),
                         'only the two emulator return intents may change')

    def test_component_only_action_missing_and_category_missing_are_rejected(self):
        for command in (OLD, OLD + ' -a android.intent.action.MAIN',
                        OLD + ' -c android.intent.category.LAUNCHER',
                        NEW + ' -c android.intent.category.LAUNCHER'):
            with self.subTest(command=command):
                self.assertIsNone(launcher_identity(command))


if __name__ == '__main__':
    unittest.main(verbosity=2)
