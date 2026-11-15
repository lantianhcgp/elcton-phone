"""Narrow byte/source regression; not a compiler or a business-behavior test."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[4]
EVIDENCE = ROOT / "qa/p2p-trace-0210/r6/evidence/r7-ci-whitespace"
COMMIT = "a0881bf7c1d97724ea166f0e51988902c280a5cc"
SITES = {"P2pTrace.kt": (77, 138, 141, 150, 153, 158, 161),
         "SyncEngine.kt": (370, 371, 395)}
MODE = "live"


def sha(data):
    return hashlib.sha256(data).hexdigest()


class WhitespaceRepairTest(unittest.TestCase):
    def test_exact_ten_spaces_lexical_separation_and_git_byte_inverse(self):
        manifest = json.loads((EVIDENCE / "mutation.json").read_text())
        self.assertEqual(manifest["commit"], COMMIT)
        self.assertEqual(set(manifest["files"]), set(SITES))
        count, defects = 0, []
        for name, pins in SITES.items():
            entry = manifest["files"][name]
            before = (EVIDENCE / entry["before_snapshot"]).read_bytes()
            git_bytes = subprocess.check_output(
                ["git", "show", COMMIT + ":" + entry["path"]], cwd=ROOT)
            self.assertEqual(before, git_bytes, name)
            self.assertEqual(sha(before), entry["before_sha256"])
            current = ((EVIDENCE / entry["before_snapshot"]).read_bytes()
                       if MODE == "before" else (ROOT / entry["path"]).read_bytes())
            old_lines, new_lines = before.splitlines(keepends=True), current.splitlines(keepends=True)
            self.assertEqual(len(old_lines), len(new_lines))
            self.assertEqual([m["line"] for m in entry["mutations"]], list(pins))
            expected = before
            for mutation in reversed(entry["mutations"]):
                offset = mutation["before_byte_offset_0based"]
                self.assertEqual(before[offset - 1:offset + 4], b'"else')
                expected = expected[:offset] + b" " + expected[offset:]
            inverse = current
            for mutation in reversed(entry["mutations"]):
                line = mutation["line"]
                column = mutation["line_byte_offset_0based"]
                if new_lines[line - 1][column - 1:column + 4] == b'"else':
                    defects.append(name + ":" + str(line))
                if current != expected:
                    continue
                self.assertEqual(old_lines[line - 1].decode(), mutation["old_line"])
                self.assertEqual(new_lines[line - 1].decode(), mutation["new_line"])
                self.assertEqual(new_lines[line - 1][column - 1:column + 5], b'" else')
                offset = mutation["after_byte_offset_0based"]
                self.assertEqual(inverse[offset:offset + 1], b" ")
                inverse = inverse[:offset] + inverse[offset + 1:]
                count += 1
            if MODE != "before":
                self.assertEqual(current, expected, name + ": only pinned ASCII-space insertions allowed")
                self.assertEqual(len(current) - len(before), len(pins))
                self.assertEqual(sha(current), entry["after_sha256"])
                self.assertEqual([i + 1 for i, (a, b) in enumerate(zip(old_lines, new_lines)) if a != b], list(pins))
                self.assertEqual(inverse, before, name + ": byte inverse")
        self.assertEqual(defects, [], "pinned quote-else lexical defects in actual source bytes")
        self.assertEqual(count, 10, "exactly ten one-byte insertions")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", choices=("before", "live"), default="live")
    MODE = parser.parse_args().source
    unittest.main(argv=[__file__], verbosity=2)
