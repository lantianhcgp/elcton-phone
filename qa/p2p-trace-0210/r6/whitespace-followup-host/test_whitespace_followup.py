"""Pinned byte compatibility regression; not Kotlin compilation or behavior proof."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[4]
EVIDENCE = ROOT / "qa/p2p-trace-0210/r6/evidence/r7-ci-whitespace-followup"
FIRST = ROOT / "qa/p2p-trace-0210/r6/evidence/r7-ci-whitespace"
MODE = "live"
FOLLOWUP = {"P2pTrace.kt": (77, 138, 141, 150, 153, 158, 161),
            "SyncEngine.kt": (370, 371), "P2pTraceEngineTest.kt": (65,)}
TOTALS = {"P2pTrace.kt": 14, "SyncEngine.kt": 5, "P2pTraceEngineTest.kt": 2}

def sha(data):
    return hashlib.sha256(data).hexdigest()

class WhitespaceFollowupTest(unittest.TestCase):
    def test_eleven_pinned_spaces_and_twenty_one_committed_byte_inverse(self):
        m = json.loads((EVIDENCE / "mutation.json").read_text())
        first = json.loads((FIRST / "mutation.json").read_text())
        self.assertEqual(m["commit"], "a0881bf7c1d97724ea166f0e51988902c280a5cc")
        self.assertEqual(set(m["files"]), set(FOLLOWUP))
        counts, totals, defects = [], [], []
        for name, pins in FOLLOWUP.items():
            e = m["files"][name]
            before = (EVIDENCE / e["before_snapshot"]).read_bytes()
            baseline = subprocess.check_output(["git", "show", m["commit"] + ":" + e["path"]], cwd=ROOT)
            self.assertEqual(baseline, (EVIDENCE / e["committed_snapshot"]).read_bytes())
            self.assertEqual(sha(before), e["before_sha256"])
            if name in first["files"]:
                self.assertEqual(sha(before), first["files"][name]["after_sha256"])
                self.assertEqual(before, (FIRST / first["files"][name]["after_snapshot"]).read_bytes())
            else:
                self.assertEqual(before, baseline)
            current = before if MODE == "before" else (ROOT / e["path"]).read_bytes()
            defects += [name + ":" + str(current[:q.start()].count(b"\n") + 1)
                        for q in re.finditer(rb'"else\b|\belse"', current)]
            expected = before
            old_lines = before.splitlines(keepends=True)
            self.assertEqual(sorted(set(x["line"] for x in e["mutations"])), list(pins))
            for edit in reversed(e["mutations"]):
                o, col = edit["before_byte_offset_0based"], edit["line_byte_offset_0based"]
                self.assertEqual(edit["insert_hex"], "20")
                self.assertEqual(o, sum(map(len, old_lines[:edit["line"] - 1])) + col)
                if name == "P2pTraceEngineTest.kt" and col == old_lines[64].index(b'"else"') + 1:
                    self.assertEqual(before[o-1:o+4], b'"else')
                else:
                    self.assertEqual(before[o-4:o+1], b'else"')
                expected = expected[:o] + b" " + expected[o:]
            if MODE == "before":
                continue
            self.assertEqual(current, expected, name + ": exact pinned insertions only")
            self.assertEqual(sha(current), e["after_sha256"])
            self.assertEqual([i+1 for i,(a,b) in enumerate(zip(old_lines,current.splitlines(keepends=True))) if a!=b], list(pins))
            inverse = current
            for edit in reversed(e["mutations"]):
                o = edit["after_byte_offset_0based"]
                self.assertEqual(inverse[o:o+1], b" ")
                inverse = inverse[:o] + inverse[o+1:]
            self.assertEqual(inverse, before, name + ": inverse to first10 candidate")
            counts.append(len(current)-len(before))
            full = current
            offsets = [x["after_byte_offset_0based"] for x in e["mutations"]]
            if name in first["files"]:
                for edit in first["files"][name]["mutations"]:
                    original_o = edit["after_byte_offset_0based"]
                    offsets.append(original_o + sum(x["before_byte_offset_0based"] <= original_o for x in e["mutations"]))
            self.assertEqual(len(set(offsets)), TOTALS[name])
            for o in sorted(offsets, reverse=True):
                self.assertEqual(full[o:o+1], b" ")
                full = full[:o] + full[o+1:]
            self.assertEqual(full, baseline, name + ": complete byte inverse to commit")
            self.assertEqual(len(current)-len(baseline), TOTALS[name])
            totals.append(len(current)-len(baseline))
        for path, fingerprint in m["protected_historical_sha256"].items():
            self.assertEqual(sha((ROOT / path).read_bytes()), fingerprint, "historical file changed: " + path)
        self.assertEqual(defects, [], "remaining quote-else/else-quote lexical defects")
        self.assertEqual(sum(counts), 11)
        self.assertEqual(sum(totals), 21)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", choices=("before", "live"), default="live")
    MODE = parser.parse_args().source
    unittest.main(argv=[__file__], verbosity=2)
