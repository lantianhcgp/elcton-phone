# R8-QUALITY-HTTP-EMPTY-01 — helper-only fix

- Changed only `ui_transport.py` line 101: `not post_body.strip()` → `post_body == b''`, exactly once; all other bytes exact-inverse verified.
- Original before SHA256: `910c8b3d2baae1f218621142f2559dd046187902e540a195a173b69994ce9a11`.
- Live after SHA256: `56ed545dde2aee95292220770a3f3b23962178b68e4039cb2542829728f5916b`.
- Initial genuine live RED: original 24 PASS; new 6, one whitespace-204 failure; returncodes `[0,0,0,0,1]`. Initial GREEN: 30/30; returncodes all zero. Both receipts retained unchanged.
- Updated eight-test genuine snapshot RED: 18 + 1 + 3 + 2 + 8 = 32; three whitespace/tab/newline failures; actual returncodes `[0,0,0,0,1]`.
- Updated live GREEN: 18 + 1 + 3 + 2 + 8 = 32/32 PASS; actual returncodes `[0,0,0,0,0]`, aggregate 0.
- Eight fixtures: mixed whitespace, tab-only, newline-only, nonempty, missing status, 302, curl failure, exact empty 204. Every fixture one mocked call, zero retries/sleeps, no credential logging; exact empty 204 accepted both before and after.
- Full AST inverse normalizes exactly one new Compare back to the original predicate. 58 protected existing fingerprints unchanged, including all old tests, pipeline/common, finalizer and historical FAIL/RED receipts.
- Existing fixture loader is named `actual_api`, not `load_api`; new test aliases it locally, no old test edits.
- Initial runner JSON missed fixture lines because unittest prefixes them; original raw/JSON preserved, `red-fixtures.json` parsed from actual raw, updated runner parsing used only in new outputs.
- No network, dispatch, device, source/build, service, git, commit or push operations. No product PASS claimed.

## Files
- Before: `ui_transport.before.py.txt`; executable identical copy `before8/ui_transport.py`.
- New test: `test_http_empty_q1.py`; runner `run_offline.py`.
- Initial results: `red.raw.log`, `red.json`, `red-fixtures.json`, `green.raw.log`, `green.json`.
- Final results: `red8.raw.log`, `red8.json`, `green8.raw.log`, `green8.json`.
- Scope proof: `before-manifest.json`, `helper-only.diff`, `inverse-ast-proof.json`.
- Report: `REPORT.md`, `report.json`.

All paths below `/data/data/com.termux/files/home/elcton-phone-diagnostics-0210-20261115/qa/p2p-trace-0210/r6/ci/r8/http-empty-q1`. Stop after this report; active full run untouched.
