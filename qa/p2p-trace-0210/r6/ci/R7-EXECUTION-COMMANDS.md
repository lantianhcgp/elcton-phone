# R7 exact execution commands after real Q2 dual closure

Root: /data/data/com.termux/files/home/elcton-phone-diagnostics-0210-20261115
Branch: diag/p2p-trace-0.2.10-20261115
This file is a command reference, not a PASS receipt. S and each RUN must come from actual git/API output. No devices, /haps, Release or PR.

## Source review and fresh regression

```text
python -B qa/p2p-trace-0210/close_r6_reviews.py --manifest qa/p2p-trace-0210/r6/reviews/input-q2/reviewed-manifest.json --spec r6-spec-q2.json --spec-raw spec-q2-raw.txt --quality r6-quality-q2.json --quality-raw quality-q2-raw.txt
python -B qa/p2p-trace-0210/run_r6_final_regressions.py --out qa/p2p-trace-0210/r6/evidence/r7-final-regression
python -B qa/p2p-trace-0210/rerun_r7_watch_frozen.py --out qa/p2p-trace-0210/r6/evidence/r7-watch-frozen
```

The full regression must be a fresh compile: no --resume-compiled and no copied old receipts. Run the long serial process through terminal(background=true, notify_on_complete=true), not a foreground timeout. Parent must read real compile/JUnit/HTTP/native/SDK raw and input hashes, not only aggregate fields. The watch runner writes solely in the phone evidence directory and independently verifies all watch source hashes before/after.

## Exact whitelist and remote identity

After real regression/raw checks only:

```text
python -B qa/p2p-trace-0210/prepare_r6_publish.py
python -B qa/p2p-trace-0210/commit_r6_reviewed.py
```

Read the actual new HEAD=S, push explicit HEAD:refs/heads/diag/p2p-trace-0.2.10-20261115, then run verify_r6_remote.py with S, PUBLISH-CANDIDATE.json and a new exclusive output directory. Also GET master and compare its stored anchor. No add -A, master push, PR or Release.

## Build

```text
python -B qa/p2p-trace-0210/r6/ci/verify_r6.py register-cases --source S --added-cases qa/p2p-trace-0210/r6/ci/added-cases.json --out qa/p2p-trace-0210/r6/ci/r7-case-registration
python -B qa/p2p-trace-0210/r6/ci/pipeline.py dispatch-build --sha S --review qa/p2p-trace-0210/r6/reviews/closure --out qa/p2p-trace-0210/r6/ci/r7-build-dispatch
```

Use the actual registered build RUN, wait in a notified background process, fetch by exact run/attempt/artifact ID, then execute verify_r6.py build with actual incoming root and registered testcases.json. Failure directories/raw stay retained and may not be reused or overwritten. Registration ambiguity is a stop/readback condition, not a retry POST.

## UI and delivery

After real signed build/manifest/172 tests verification, register diagnostics first with all explicit API33/three-button inputs and exact build RUN/S. Register full only with the genuine diagnostics registered.json. Wait/fetch exact runs independently, execute verify_r6.py cloud on both complete artifacts (original complete JSON/pixel assertions, no 600MB old tree copy). Re-read current exact remote run attempts after verification.

Only after both receipts PASS use finalize_r6_delivery.py with S, actual build/diagnostics/full receipts and the actual signed main APK. Target filename is hc课程表-0.2.10-code12-<source8>-<apksha8>-signed.apk in the user's phone directory. No physical installation or handshake claim.

Final evidence-only commit/push may contain a newer HEAD, but must preserve all application, test and workflow blobs from S. CI/APK/source identity continues to be S, never silently rebound to the documentation commit. Final report includes both exact source and evidence commit references.
