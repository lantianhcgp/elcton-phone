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
           "app/src/main/java/com/hcbiu/elcton/ExpressiveComponents.kt", "qa/ui_only_gate.py",
           "app/src/androidTest/java/com/hcbiu/elcton/ThemeUiTest.kt",
           "qa/test_theme_source.py", "qa/test_theme_evidence.py", "qa/verify_theme_evidence.py",
           "qa/emulator_install_and_tour.py"}
UI_HELPERS = {"app/src/main/java/com/hcbiu/elcton/M3xTheme.kt",
              "app/src/main/java/com/hcbiu/elcton/ExpressiveComponents.kt"}


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
        r"onDismissRequest\s*=\s*(\{)",
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


def syntax_mask(text):
    """Hide literals/comments without changing offsets for balanced-call parsing."""
    chars = list(text)
    i = 0
    while i < len(text):
        start = i
        if text.startswith("//", i):
            end = text.find("\n", i)
            i = len(text) if end < 0 else end
        elif text.startswith("/*", i):
            end = text.find("*/", i + 2)
            assert end >= 0, "Unclosed comment"
            i = end + 2
        elif text.startswith('"""', i):
            end = text.find('"""', i + 3)
            assert end >= 0, "Unclosed raw string"
            i = end + 3
        elif text[i] in ('"', "'"):
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
        else:
            i += 1
            continue
        chars[start:i] = " " * (i - start)
    return "".join(chars)


def control_bindings(text):
    """Bind each action and enabled predicate to its tag/label and dialog context."""
    mask = syntax_mask(text)
    stack, spans = [], []
    for i, char in enumerate(mask):
        if char == "(":
            stack.append(i)
        elif char == ")":
            assert stack, "Unbalanced Kotlin call"
            spans.append((stack.pop(), i))
    assert not stack, "Unbalanced Kotlin call"
    function_starts = list(re.finditer(r"@Composable\s+private\s+fun\s+(\w+)", text))
    targets = (r"onClick\s*=\s*(\{)", r"onDismissRequest\s*=\s*(\{)",
               r"(?:OutlinedTextField|ExpressiveField)\s*\([^,]+,\s*(\{)")
    bindings = []
    for pattern in targets:
        for match in re.finditer(pattern, text):
            pos = match.start(1)
            containing = sorted(((a, b) for a, b in spans if a < pos < b), key=lambda pair: pair[1] - pair[0])
            assert containing, "Callback has no owner"
            a, b = containing[0]
            owner = re.search(r"(\w+)\s*$", text[:a])
            assert owner, "Unnamed callback owner"
            name = owner.group(1)
            args = text[a + 1:b]
            end = b + 1
            while end < len(mask) and mask[end].isspace():
                end += 1
            content = block(text, end) if end < len(mask) and mask[end] == "{" else ""
            tag_match = re.search(r'\.testTag\(', args)
            tag = None
            if tag_match:
                tag_start = a + 1 + tag_match.end() - 1
                tag_end = next(q for p, q in spans if p == tag_start)
                tag = normalized(text[tag_start + 1:tag_end])
            labels = re.findall(r'Text\(("(?:\\.|[^"\\])*")', content)
            if name in ("OutlinedTextField", "ExpressiveField"):
                labels = re.findall(r'label\s*=\s*\{\s*Text\(("(?:\\.|[^"\\])*")', args)
            if name == "AlertDialog":
                tag = None
                labels = re.findall(r'title\s*=\s*\{\s*Text\(("(?:\\.|[^"\\])*")', args)
            identity = ("tag:" + tag) if tag else ("label:" + "|".join(labels))
            assert tag or labels, "Control has no stable semantic identity: " + name
            dialogs = []
            for outer_a, outer_b in reversed(containing[1:]):
                outer_name = re.search(r"(\w+)\s*$", text[:outer_a])
                if outer_name and outer_name.group(1) == "AlertDialog":
                    title = re.search(r'title\s*=\s*\{\s*Text\(("(?:\\.|[^"\\])*")', text[outer_a:outer_b])
                    assert title, "Dialog has no title"
                    dialogs.append(title.group(1))
            function = next((m.group(1) for m in reversed(function_starts) if m.start() < pos), "")
            role = "dismiss" if "onDismissRequest" in pattern else "input" if "TextField" in pattern else "click"
            enabled = enabled_conditions(args)
            bindings.append((function, tuple(dialogs), identity, role, normalized(block(text, pos)), tuple(sorted(enabled.items()))))
    return collections.Counter(bindings)


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
    try:
        if control_bindings(old) != control_bindings(new):
            errors.append("Control/callback/enabled binding drift")
    except (AssertionError, AttributeError) as error:
        errors.append("Control binding parse failed: " + str(error))
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


def theme_checks(source):
    """A narrow exception for the user-requested presentation-only preference."""
    errors = []
    forbidden = r"\b(?:ScheduleStore|WearProbe|TransferSession|PacketIngress|PhoneSnapshot|ScheduleBook|LaunchedEffect|DisposableEffect|rememberCoroutineScope|File|HttpClient|URL)\b"
    if re.search(forbidden, syntax_mask(source)):
        errors.append("Theme helper touches business/data/network or asynchronous effects")
    reads = re.findall(r'getSharedPreferences\s*\(([^)]*)\)', source)
    if reads != ['"ui-theme", Context.MODE_PRIVATE']:
        errors.append("Theme preferences must use only the isolated ui-theme namespace")
    writes = re.findall(r'put\w+\s*\(([^)]*)\)', source)
    if writes != ['"mode", mode.name'] or re.search(r'\.(?:clear|remove|commit)\s*\(', source):
        errors.append("Theme preferences may only apply the mode enum")
    if re.findall(r'getString\s*\(([^)]*)\)', source) != ['"mode", ThemeMode.LIGHT.name']:
        errors.append("Theme preferences must have the literal LIGHT fallback")
    if source.count('mutableStateOf(') != 1:
        errors.append("Only one presentation theme state is permitted")
    if not all(token in source for token in ('ThemeMode.LIGHT -> false', 'ThemeMode.DARK -> true',
                                              'ThemeMode.SYSTEM -> isSystemInDarkTheme()')):
        errors.append("Theme mode resolution does not match the three-way contract")
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
    for p in sorted(UI_HELPERS):
        if not Path(p).exists():
            continue
        helper = Path(p).read_text()
        if p.endswith("/M3xTheme.kt"):
            errors.extend(theme_checks(helper))
        elif re.search(r"\b(?:ScheduleStore|WearProbe|TransferSession|PacketIngress|PhoneSnapshot)\b|mutableStateOf|LaunchedEffect", helper):
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
        first, second = "{probe.authorizeAndScan()}", "{probe.cancel()}"
        assert new.count(first) == new.count(second) == 1
        swapped = new.replace(first, "CALLBACK_SWAP_SENTINEL").replace(second, first).replace("CALLBACK_SWAP_SENTINEL", second)
        negative["callback ownership swap"] = "Control/callback/enabled binding drift" in activity_checks(old, swapped)
        first, second = "enabled=!probeState.busy", "enabled=probeState.ready&&!probeState.busy"
        enabled_swap = new.replace(first, "ENABLED_SWAP_SENTINEL", 1).replace(second, first, 1).replace("ENABLED_SWAP_SENTINEL", second)
        negative["enabled ownership swap"] = "Control/callback/enabled binding drift" in activity_checks(old, enabled_swap)
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
