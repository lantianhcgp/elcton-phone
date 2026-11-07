#!/usr/bin/env python3
"""Fail closed on non-UI changes, callback drift, or lost product semantics.

This source-level guard supplements, never replaces, CI unit/instrumentation tests.
It intentionally pins the user's pre-refactor baseline. It does not compile Android.
"""
import argparse
import collections
import json
import re
import subprocess
from pathlib import Path

BASE = "519f0d5450f77ce4ba757a644b2144607b0a5c06"
ACTIVITY = "app/src/main/java/com/hcbiu/elcton/MainActivity.kt"
ALLOWED = {ACTIVITY, "app/src/main/java/com/hcbiu/elcton/M3xTheme.kt",
           "app/src/main/java/com/hcbiu/elcton/ExpressiveComponents.kt", "qa/ui_only_gate.py"}


def git(*args):
    return subprocess.check_output(["git", *args], text=True).strip()


def normalized(text):
    # Preserve literal contents, including whitespace in user-facing messages.
    return "".join(re.findall(r'"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|\w+|[^\s]', text))


def block(text, opening):
    assert text[opening] == "{"
    depth, i = 0, opening
    while i < len(text):
        if text.startswith("//", i):
            end = text.find("\n", i)
            i = len(text) if end < 0 else end
            continue
        if text.startswith("/*", i):
            end = text.find("*/", i + 2)
            assert end >= 0, "Unclosed comment"
            i = end + 2
            continue
        if text.startswith('"""', i):
            end = text.find('"""', i + 3)
            assert end >= 0, "Unclosed raw string"
            i = end + 3
            continue
        if text[i] in ('"', "'"):
            quote = text[i]
            i += 1
            while i < len(text):
                if text[i] == "\\":
                    i += 2
                elif text[i] == quote:
                    i += 1
                    break
                else:
                    i += 1
            continue
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return text[opening:i + 1]
        i += 1
    raise AssertionError("Unbalanced Kotlin block")


def between(text, start, end):
    assert text.count(start) == 1, start
    remainder = text.split(start, 1)[1]
    assert end in remainder, (start, end)
    return remainder.split(end, 1)[0]


def callbacks(text):
    patterns = (
        r"onClick\s*=\s*(\{)",
        r"\.clickable\s*(\{)",
        r"(?:OutlinedTextField|ExpressiveField)\s*\([^,]+,\s*(\{)",
    )
    positions = set()
    for pattern in patterns:
        positions.update(m.start(1) for m in re.finditer(pattern, text))
    return collections.Counter(normalized(block(text, p)) for p in positions)


def enabled_conditions(text):
    values = []
    for match in re.finditer(r"\benabled\s*=", text):
        i, start, depth = match.end(), match.end(), 0
        while i < len(text):
            c = text[i]
            if c in "([{":
                depth += 1
            elif c in ")]}":
                if depth == 0:
                    break
                depth -= 1
            if c == "," and depth == 0:
                break
            i += 1
        values.append(normalized(text[start:i]))
    return collections.Counter(values)


def activity_checks(old, new):
    errors = []
    protected = (
        ("class MainActivity : ComponentActivity() {", "private val openFile"),
        ("private val openFile", "override fun onCreate"),
        ("override fun onCreate", "        setContent {"),
        ("    private fun save", "    @Composable private fun Product"),
        ("@Composable private fun CourseEditor(existing:Course?) {", "        Column(Modifier.fillMaxSize())"),
        ("@Composable private fun Settings(){", "        Column(Modifier.fillMaxSize()"),
        ("@Composable private fun ImportDialog(){", "        AlertDialog("),
    )
    for start, end in protected:
        try:
            if normalized(between(old, start, end)) != normalized(between(new, start, end)):
                errors.append("Protected activity section changed: " + start)
        except AssertionError:
            errors.append("Protected activity section missing/ambiguous: " + start)
    tail = "    private fun dayLabel"
    if normalized(old.split(tail, 1)[1]) != normalized(new.split(tail, 1)[1]):
        errors.append("dayLabel/lifecycle changed")
    if callbacks(old) != callbacks(new):
        errors.append("Action/value-change callback drift")
    if enabled_conditions(old) != enabled_conditions(new):
        errors.append("Enabled-state condition drift")
    tags = r'\.testTag\(("(?:\\.|[^"\\])*")\)'
    if collections.Counter(re.findall(tags, old)) != collections.Counter(re.findall(tags, new)):
        errors.append("Product testTag drift")
    for literal in ('"nav-today","nav-week","nav-devices","nav-settings"',
                    'BackHandler(editing){editing=false;editingCourse=null}',
                    'if(!editing&&tab<=1&&loadError==null)',
                    'valnow=LocalDate.now();valweek=book.weekAt(now);vallist=book.forDay(now.dayOfWeek.value,week)',
                    'vallist=book.forDay(selectedDay,displayWeek)',
                    'if(showImport)ImportDialog()', 'valproposed=pendingImport!!'):
        if literal not in normalized(new):
            errors.append("Protected condition/data source missing: " + literal)
    return errors


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    old = git("show", BASE + ":" + ACTIVITY)
    new = Path(ACTIVITY).read_text()
    errors = activity_checks(old, new)
    changed = set(git("diff", "--name-only", BASE, "--", ".").splitlines())
    # This historical working-tree file is deliberately not part of this refactor.
    changed.discard(".ai-memory/handoff.md")
    errors.extend("Non-UI file changed: " + p for p in sorted(changed - ALLOWED))
    untracked = set(git("ls-files", "--others", "--exclude-standard").splitlines())
    errors.extend("Unexpected new source: " + p for p in sorted(untracked)
                  if not p.startswith("qa/__pycache__/") and p not in ALLOWED)
    staged = set(git("diff", "--cached", "--name-only").splitlines())
    errors.extend("Forbidden staged file: " + p for p in sorted(staged - ALLOWED))
    for p in sorted(ALLOWED - {ACTIVITY, "qa/ui_only_gate.py"}):
        if Path(p).exists() and re.search(r"\b(?:ScheduleStore|WearProbe|TransferSession|PacketIngress|PhoneSnapshot)\b|mutableStateOf|LaunchedEffect", Path(p).read_text()):
            errors.append("New UI helper depends on business/state side effects: " + p)
    negative = {}
    if args.self_test:
        for label, before, after in (
            ("callback mutation", "displayWeek++", "displayWeek+=2"),
            ("lifecycle mutation", "probe.onBackground()", "probe.close()"),
            ("semantic tag mutation", '"add-course"', '"lost-course"'),
            ("input mutation", '{name=it;error=""}', '{name=it.trim();error=""}'),
        ):
            assert before in new, label
            negative[label] = bool(activity_checks(old, new.replace(before, after, 1)))
        negative["non-UI file whitelist"] = "app/src/main/java/com/hcbiu/elcton/WearProbe.kt" not in ALLOWED
        assert all(negative.values()), ("Guard self-test failed", negative)
    report = {"passed": not errors, "base": BASE, "head": git("rev-parse", "HEAD"),
              "callback_count": sum(callbacks(new).values()),
              "enabled_condition_count": sum(enabled_conditions(new).values()),
              "negative_controls": negative, "errors": errors,
              "scope": "Source invariants; actual Kotlin compile and runtime are verified by GitHub CI"}
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    raise SystemExit(0 if report["passed"] else 1)


if __name__ == "__main__":
    main()
