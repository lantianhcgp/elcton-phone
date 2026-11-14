#!/usr/bin/env python3
"""Exact diagnostic-only exception, not a general weakening of the historical UI gate.

The reviewed observation delta is reversed literally. The resulting activity and
WearProbe must be byte-for-byte equal to the pinned 0.2.5 source. Any extra edit,
lost error outlet, or duplicate seam fails closed. No errors or keys are filtered.
"""
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BASE = '18cd94ea1689c7e3d59a26afd4121cd2a665b4d7'
ACTIVITY = 'app/src/main/java/com/hcbiu/elcton/MainActivity.kt'
PROBE = 'app/src/main/java/com/hcbiu/elcton/WearProbe.kt'
APPROVED = json.loads((ROOT / 'qa/diag-mcp-026/approved-observation-delta.json').read_text())
assert APPROVED['baseline'] == BASE
assert set(APPROVED['patches']) == {ACTIVITY, PROBE}
ACTIVITY_INITIALIZER = APPROVED['patches'][ACTIVITY][0]['after']
KEEPALIVE = json.loads((ROOT / 'qa/diag-mcp-027/approved-keepalive-delta.json').read_text())
assert KEEPALIVE['baseline'] == 'cd2a3e062b97d778c79b76b544071b1077534af7'
assert set(KEEPALIVE['patches']) == {ACTIVITY}


def baseline(path):
    return subprocess.check_output(['git', 'show', BASE + ':' + path], cwd=ROOT, text=True)


def reverse_exact(text, path):
    if path == ACTIVITY:
        for change in reversed(KEEPALIVE['patches'][ACTIVITY]):
            expected = change['after']
            if not expected or text.count(expected) != 1:
                raise ValueError('Missing or ambiguous authorized keepalive delta: ' + path)
            text = text.replace(expected, change['before'], 1)
    for change in reversed(APPROVED['patches'][path]):
        expected = change['after']
        if not expected or text.count(expected) != 1:
            raise ValueError('Missing or ambiguous authorized observation delta: ' + path)
        text = text.replace(expected, change['before'], 1)
    return text


def without_activity_diagnostics(text):
    return reverse_exact(text, ACTIVITY)


def without_probe_diagnostics(text):
    return reverse_exact(text, PROBE)


def scope_errors(activity, probe):
    errors = []
    for path, text in [(ACTIVITY, activity), (PROBE, probe)]:
        try:
            restored = reverse_exact(text, path)
            if restored != baseline(path):
                errors.append('Unapproved non-diagnostic source mutation: ' + path)
        except ValueError as error:
            errors.append(str(error))
    return errors


if __name__ == '__main__':
    errors = scope_errors((ROOT / ACTIVITY).read_text(), (ROOT / PROBE).read_text())
    print(json.dumps({'passed': not errors, 'base': BASE, 'errors': errors,
                      'scope': 'Exact observation-only source delta; not hardware success'}, ensure_ascii=False))
    raise SystemExit(1 if errors else 0)
