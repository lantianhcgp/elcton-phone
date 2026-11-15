#!/usr/bin/env python3
"""Byte-exact candidate release reversal; historical approvals are not rewritten.

0.2.9 first reverses its complete Activity/SDK-adapter transformation, then the
original READY/KEEPALIVE and observation deltas, all the way to pinned 0.2.5.
Engine/runtime hashes separately protect relocated decisions. Passing this gate
is source identity only, NOT independent approval or hardware acceptance.
See qa/release-029/SPEC.md and TEST-ATTRIBUTION.md for the migration lineage.
"""
import hashlib
import json
from functools import lru_cache
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BASE = '18cd94ea1689c7e3d59a26afd4121cd2a665b4d7'
HEAD_PIN = 'e034de2f924dd6d96e31caa8e5a62e52474de718'
ACTIVITY = 'app/src/main/java/com/hcbiu/elcton/MainActivity.kt'
PROBE = 'app/src/main/java/com/hcbiu/elcton/WearProbe.kt'
ENGINE = 'app/src/main/java/com/hcbiu/elcton/SyncEngine.kt'
APPROVED = json.loads((ROOT / 'qa/diag-mcp-026/approved-observation-delta.json').read_text())
assert APPROVED['baseline'] == BASE
assert set(APPROVED['patches']) == {ACTIVITY, PROBE}
ACTIVITY_INITIALIZER = APPROVED['patches'][ACTIVITY][0]['after']
READY = json.loads((ROOT / 'qa/p2p-ready-20261114/approved-ready-delta.json').read_text())
assert READY['baseline'] == 'cd2a3e062b97d778c79b76b544071b1077534af7'
assert set(READY['patches']) == {PROBE}
KEEPALIVE = json.loads((ROOT / 'qa/diag-mcp-027/approved-keepalive-delta.json').read_text())
assert KEEPALIVE['baseline'] == 'cd2a3e062b97d778c79b76b544071b1077534af7'
assert set(KEEPALIVE['patches']) == {ACTIVITY}
RELEASE = json.loads((ROOT / 'qa/release-029/approved-release-delta.json').read_text())
assert RELEASE['baseline'] == BASE
assert RELEASE['head_pin'] == HEAD_PIN
assert RELEASE['release'] == '0.2.9' and RELEASE['version_code'] == 11
assert RELEASE['status'] == 'candidate_pending_independent_review'
assert RELEASE['independent_approvals'] == []
assert set(RELEASE['patches']) == {ACTIVITY, PROBE}
CURRENT_KEEPALIVE = RELEASE['current_keepalive']
assert set(CURRENT_KEEPALIVE['patches']) == {ACTIVITY}
CURRENT_READY_DISPATCH = '        PacketIngress.preparationError(message, awaitingReady, session != null || exporting != null)?.let { fail(it); return }\n'
CURRENT_READY_TIMEOUT = READY['patches'][PROBE][1]['after']


def digest(data):
    return hashlib.sha256(data).hexdigest()


@lru_cache(maxsize=None)
def pinned_bytes(commit, path):
    return subprocess.check_output(['git', 'show', commit + ':' + path], cwd=ROOT)


def baseline(path):
    return pinned_bytes(BASE, path).decode('utf-8')


# Complete before texts must be the specified original branches, not a newly
# inferred baseline. Whole-source after texts are candidates for separate review.
for _path, _commit in [(ACTIVITY, '1e14980f19cf5c510722d9521d9762586a3a91eb'), (PROBE, HEAD_PIN)]:
    assert len(RELEASE['patches'][_path]) == 1
    _change = RELEASE['patches'][_path][0]
    assert _change['before_commit'] == _commit
    assert _change['before'].encode('utf-8') == pinned_bytes(_commit, _path)
    assert digest(_change['before'].encode('utf-8')) == _change['before_sha256']
    assert digest(_change['after'].encode('utf-8')) == _change['after_sha256']


def reverse_exact(text, path):
    # Required order: complete release -> READY/KEEPALIVE -> observation -> 0.2.5.
    for change in reversed(RELEASE['patches'].get(path, [])):
        expected = change['after']
        if not expected or text.count(expected) != 1:
            raise ValueError('Missing or ambiguous candidate release delta: ' + path)
        text = text.replace(expected, change['before'], 1)
        if digest(text.encode('utf-8')) != change['before_sha256']:
            raise ValueError('Unapproved source outside exact release delta: ' + path)
    for deltas in (READY, KEEPALIVE):
        for change in reversed(deltas['patches'].get(path, [])):
            expected = change['after']
            if not expected or text.count(expected) != 1:
                raise ValueError('Missing or ambiguous authorized merge delta: ' + path)
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


def build_workflow_errors(text=None):
    specification = RELEASE['build_workflow']
    path = specification['path']
    original = pinned_bytes(HEAD_PIN, path)
    if digest(original) != specification['baseline_sha256']:
        return ['Build workflow baseline pin mismatch']
    expected = original.decode('utf-8')
    for change in specification['allowed_replacements']:
        if expected.count(change['before']) != 1:
            return ['Missing or ambiguous release workflow replacement']
        expected = expected.replace(change['before'], change['after'], 1)
    actual = (ROOT / path).read_bytes() if text is None else text.encode('utf-8')
    errors = []
    if actual != expected.encode('utf-8'):
        errors.append('Unapproved build workflow mutation: ' + path)
    signing = specification['staged_signing_before']
    verifier = specification['signing_verifier_replacement']
    if signing.count(verifier['before']) != 1:
        errors.append('Staged signing verifier is missing or ambiguous')
    else:
        # The sole permitted signing-step difference is the verifier path.
        signing = signing.replace(verifier['before'], verifier['after'], 1)
        if actual.count(signing.encode('utf-8')) != 1:
            errors.append('Stable staged signing block changed')
    return errors


def boundary_errors(source_overrides=None):
    overrides = {} if source_overrides is None else dict(source_overrides)
    guards = RELEASE['guarded_source_sha256']
    frozen = RELEASE['immutable_source_sha256']
    paths = set(guards) | set(frozen)
    errors = ['Unknown guarded source override: ' + path for path in overrides if path not in paths]
    # Read disk bytes as well: universal-newline conversion must not hide CRLF edits.
    for path, changes in RELEASE['patches'].items():
        if digest((ROOT / path).read_bytes()) != changes[0]['after_sha256']:
            errors.append('Candidate release disk bytes changed: ' + path)
    expected_main = {path for path in paths | set(RELEASE['patches']) if path.startswith('app/src/main/')}
    actual_main = {path.relative_to(ROOT).as_posix() for path in (ROOT / 'app/src/main').rglob('*') if path.is_file()}
    if actual_main != expected_main:
        errors.append('Unapproved main-source inventory delta: ' + repr(sorted(actual_main ^ expected_main)))
    for group in (guards, frozen):
        for path, expected in group.items():
            if path in overrides:
                supplied = overrides[path]
                data = supplied.encode('utf-8') if isinstance(supplied, str) else supplied
            else:
                data = (ROOT / path).read_bytes()
            if digest(data) != expected:
                errors.append('Unapproved guarded source mutation: ' + path)
            if path in frozen and digest(pinned_bytes(HEAD_PIN, path)) != expected:
                errors.append('Immutable source baseline identity mismatch: ' + path)
    errors.extend(build_workflow_errors())
    return errors


def scope_errors(activity, probe, engine=None, source_overrides=None):
    """Engine defaults to disk; explicit source enables relocated negative tests.

    source_overrides allows exact runtime/schedule mutation controls without
    writing product files. Omitted overrides never omit any source guard.
    """
    errors = []
    for path, text in [(ACTIVITY, activity), (PROBE, probe)]:
        try:
            restored = reverse_exact(text, path)
            if restored.encode('utf-8') != pinned_bytes(BASE, path):
                errors.append('Unapproved non-diagnostic source mutation: ' + path)
        except ValueError as error:
            errors.append(str(error))
    overrides = {} if source_overrides is None else dict(source_overrides)
    if engine is not None:
        if ENGINE in overrides:
            errors.append('Engine supplied twice; ambiguous mutation input')
        overrides[ENGINE] = engine
    errors.extend(boundary_errors(overrides))
    return errors


if __name__ == '__main__':
    errors = scope_errors((ROOT / ACTIVITY).read_text(), (ROOT / PROBE).read_text())
    print(json.dumps({'passed': not errors, 'base': BASE, 'errors': errors,
                      'release_delta_status': RELEASE['status'],
                      'scope': 'Exact candidate source identity; independent review and hardware acceptance pending'}, ensure_ascii=False))
    raise SystemExit(1 if errors else 0)
