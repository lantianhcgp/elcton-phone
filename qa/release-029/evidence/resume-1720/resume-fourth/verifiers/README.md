# Independent cloud artifact verifier (offline, evidence-only)

Run from any cwd using an absolute script path:

```text
python -B verify_cloud.py --source <exact-40-lowercase-hex> --run <exact-run-id> --suite diagnostics|full --incoming <fetch-root> --out <new-dir-under-qa/release-029/evidence>
```

`incoming` is the parent's fetch root: `run.json` (gh `headSha`, `databaseId`, `status`, `conclusion`), `artifact/`, optionally original `inventory.json`. The tool snapshots ALL input files to new `out/raw/`, verifies bytes/hashes against the original inventory when supplied, and executes only the snapshot. Existing output directories are refused. `receipt.json` always fails closed after gate failures; `failures.log` retains tracebacks, and full original RED reports/hosts are copied verbatim (including `harvested:false`). No old raw, product, config or test edits.

Key functions: `compare` (whole JSON after tuple→array serialization only); `Gate.diagnostics` (original PNG/XML/keepalive verifiers, 15 tools and saved wire); `Gate.background` (original `foreground_receipt` through file-only playback, real notification STOP/persisted opt-out/closure); `Gate.full` (23 theme + 74 palette complete original report recomputations); `Gate.tour` (AST-selected original pure verifier span, not importing the adb-running tour); original `verify_system_bars.inspect` for every original app-owned scene.

No adb, socket, API, CI, install, Git write, JVM rerun or physical device activity. `CompletedProcess` objects wrap saved wire only; they are not fresh execution results. Saved signer text is compared, but actual APK bytes/signatures and current remote run/attempt/input/artifact binding still require the parent's independent fetch/binary check. Original full acceptance is not demonstrated by the old RED fixture; the parent must exercise the latest genuine complete full artifact.

Scope must not expand: ordinary background = finite 5s / 3 emulator probes, NOT 10-minute, Doze/MIUI/watch/physical proof. Local Kotlin host log = 3784 raw checks (local JVM). Android external URL = 3659, unsupported `write EOF` explicitly retained with `all_raw_checks_passed:false`; additional normal Android Socket assertions = 133. Never describe external Android as all 3784 raw checks.

`test_verify_cloud.py --out <NEW-dir>` runs actual old diag/old full subprocesses and four minimal negatives (source mismatch, `passed:false`, original keepalive `defaultOn:false`, PNG 1px complete-report mismatch). The pixel fixture still passes original statistical thresholds: it proves complete comparison is strict, NOT that every single pixel must fail original thresholds. Fixtures are memory/temp only. First preimplementation RED remains in `selftest-01-preimplementation`; real execution records, receipts and raw are under subsequent numbered selftest directories.
