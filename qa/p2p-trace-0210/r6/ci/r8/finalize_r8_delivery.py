#!/usr/bin/env python3
"""R8 output-metadata adapter; reviewed R6 file is never edited.

Import/proof helpers do not deliver. CLI retains the original arguments and
executes the original checks only after read-only R8 collision preflight.
Offline tests must not be interpreted as real delivery/build/signature PASS.
"""
import argparse
import ast
import copy
import hashlib
from pathlib import Path
import re
import subprocess

HERE = Path(__file__).resolve().parent
ORIGINAL = HERE.parents[2] / 'finalize_r6_delivery.py'
ROOT = ORIGINAL.parents[2]
SOURCE = 'b3eb55680b51f5fbdf392d402acdcdae168f2b20'
BRANCH = 'diag/p2p-trace-0.2.10-20261115'
ORIGINAL_SHA256 = '5e631132ed51fcea7a4406dbdecfe75dcf1ea4edeec3531a2c05e1ff3fbcbe03'
# Exactly five single output-metadata lines, including their original newlines.
METADATA_SPANS = (
    (75,
     "    target=PHONE/('hc课程表-0.2.10-code12-'+a.source[:8]+'-'+digest[:8]+'-signed.apk')\n",
     "    target=PHONE/('hc课程表-0.2.10-code12-'+a.source[:8]+'-诊断版-signed.apk')\n"),
    (92,
     "    lines=['# R6 DELIVERY — 0.2.10 诊断版实际交付','',\n",
     "    lines=['# DELIVERY-R8 — 0.2.10 诊断版实际交付','',\n"),
    (116,
     "    (out/'DELIVERY.md').write_text(report)\n",
     "    (out/'DELIVERY-R8.md').write_text(report)\n"),
    (117,
     "    (Q/'DELIVERY.md').write_text(report)\n",
     "    (Q/'DELIVERY-R8.md').write_text(report)\n"),
    (118,
     "    phone_report=target.with_suffix('.DELIVERY.md')\n",
     "    phone_report=PHONE/'DELIVERY-R8.md'\n"),
)


def inverse_metadata(candidate):
    restored = candidate
    for _, old, new in reversed(METADATA_SPANS):
        old, new = old.encode('utf-8'), new.encode('utf-8')
        assert restored.count(new) == 1, 'R8 metadata inverse span not unique'
        restored = restored.replace(new, old, 1)
    return restored


def normalized_ast_equal(original, candidate):
    """Normalize ONLY enumerated metadata, then compare the complete AST.

    Each candidate statement must match its exact authorized form; line 92
    normalizes only the first title literal, not the surrounding report list.
    Attributes (line/column offsets) are the only ignored AST information.
    """
    dump = lambda node: ast.dump(node, include_attributes=False)
    try:
        left, right = ast.parse(original), ast.parse(candidate)
        old_main = next(n for n in left.body if isinstance(n, ast.FunctionDef) and n.name == 'main')
        new_main = next(n for n in right.body if isinstance(n, ast.FunctionDef) and n.name == 'main')
        for line, old, new in METADATA_SPANS:
            old_node = next(n for n in old_main.body if n.lineno == line)
            index = next(i for i, n in enumerate(new_main.body) if n.lineno == line)
            new_node = new_main.body[index]
            if line == 92:
                old_title = ast.literal_eval(old.strip()[len('lines=['):-len(",'',")])
                new_title = ast.literal_eval(new.strip()[len('lines=['):-len(",'',")])
                if (dump(old_node.value.elts[0]) != dump(ast.Constant(old_title)) or
                        dump(new_node.value.elts[0]) != dump(ast.Constant(new_title))):
                    return False
                new_node.value.elts[0] = copy.deepcopy(old_node.value.elts[0])
            else:
                if (dump(old_node) != dump(ast.parse(old.strip()).body[0]) or
                        dump(new_node) != dump(ast.parse(new.strip()).body[0])):
                    return False
                new_main.body[index] = copy.deepcopy(old_node)
        return dump(left) == dump(right)
    except (SyntaxError, StopIteration, AttributeError, ValueError, TypeError):
        return False


def verify_metadata(original, candidate):
    assert hashlib.sha256(original).hexdigest() == ORIGINAL_SHA256, 'Original not pinned reviewed bytes'
    assert inverse_metadata(candidate) == original, 'Nonmetadata bytes changed'
    assert normalized_ast_equal(original, candidate), 'Nonmetadata AST changed'
    return True


def adapt_metadata(original):
    assert hashlib.sha256(original).hexdigest() == ORIGINAL_SHA256, 'Original not pinned reviewed bytes'
    candidate = original
    spans = []
    for line, old_text, new_text in METADATA_SPANS:
        old, new = old_text.encode('utf-8'), new_text.encode('utf-8')
        assert original.splitlines(keepends=True)[line - 1] == old, 'Reviewed line mismatch'
        assert candidate.count(old) == 1 and candidate.count(new) == 0, 'Metadata span not unique'
        start = original.index(old)
        spans.append({'line': line, 'original_start': start, 'original_end': start + len(old),
                      'before': old_text, 'after': new_text})
        candidate = candidate.replace(old, new, 1)
    verify_metadata(original, candidate)
    return candidate, {
        'original_sha256': hashlib.sha256(original).hexdigest(), 'original_bytes': len(original),
        'transformed_sha256': hashlib.sha256(candidate).hexdigest(), 'transformed_bytes': len(candidate),
        'changed_spans': spans, 'inverse_exact': True, 'normalized_ast_equal': True,
        'scope': 'Five output metadata spans only; all original checks/assertions retained',
    }


def load_reviewed():
    if not __debug__:
        raise RuntimeError('Optimized Python refuses delivery: original assertions must remain active')
    branch = subprocess.check_output(['git', 'branch', '--show-current'], cwd=ROOT, timeout=30).decode().strip()
    assert branch == BRANCH, 'Unauthorized branch'
    original = ORIGINAL.read_bytes()
    committed = subprocess.check_output(
        ['git', 'show', SOURCE + ':qa/p2p-trace-0210/finalize_r6_delivery.py'], cwd=ROOT, timeout=30)
    assert original == committed, 'Original disk differs from reviewed committed finalizer'
    candidate, _ = adapt_metadata(original)
    namespace = {'__file__': str(ORIGINAL), '__name__': 'r8_reviewed_finalizer'}
    exec(compile(candidate, str(ORIGINAL), 'exec', dont_inherit=True, optimize=0), namespace)
    assert namespace['ROOT'] == ROOT and namespace['Q'] == ORIGINAL.parent / 'r6'
    return namespace


def _no_symlink(path):
    assert '..' not in path.parts, 'R8 path traversal refused'
    assert not any(p.is_symlink() for p in (path, *path.parents)), 'R8 path symlink refused'


def preflight(source, out, q, phone):
    """Read-only: refuse ALL R8 outputs before any original mkdir/copy.

    Q/out report write_text is deliberately unchanged. This absence preflight
    is not a concurrent-writer lock; original APK/phone report opens stay x/xb.
    """
    assert re.fullmatch('[0-9a-f]{40}', source), 'Malformed source'
    assert source == SOURCE, 'R8 only authorizes the exact built source, not workflow HEAD'
    out, q, phone = (Path(p).absolute() for p in (out, q, phone))
    for path in (out, q, phone):
        _no_symlink(path)
    base = (q / 'ci').resolve()
    out = out.resolve()
    assert out != base and out.is_relative_to(base), 'Output must be new below R6 ci'
    targets = {
        'out': out,
        'apk': phone / ('hc课程表-0.2.10-code12-' + source[:8] + '-诊断版-signed.apk'),
        'q_report': q / 'DELIVERY-R8.md', 'phone_report': phone / 'DELIVERY-R8.md',
        'out_report': out / 'DELIVERY-R8.md', 'receipt': out / 'receipt.json',
        'signature_log': out / 'apksigner.raw.log', 'manifest_log': out / 'badging.raw.log',
    }
    for path in targets.values():
        _no_symlink(path)
        assert not path.exists(), 'Existing R8 output never overwritten: ' + str(path)
    return targets


def main():
    namespace = load_reviewed()
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', required=True)
    for name in ('build-receipt', 'diagnostics-receipt', 'full-receipt', 'apk', 'out'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    preflight(args.source, args.out, namespace['Q'], namespace['PHONE'])
    # Original argv, __file__, ROOT/Q/PHONE, binary/identity/closure/run/PASS gates.
    # No stub receipt or signer/badging substitute exists in this adapter.
    namespace['main']()


if __name__ == '__main__':
    main()
