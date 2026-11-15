# R7 continuation — final source and CI green, APK NOT DELIVERED

## Authoritative current conclusion

This run reached its execution time budget while the bounded artifact download was running. There is NO verified or delivered 0.2.10 APK. Build success is NOT delivery success. Do not repeat the completed source work, substitute an old APK, or treat pending binary/UI gates as green.

Root: /data/data/com.termux/files/home/elcton-phone-diagnostics-0210-20261115
Only branch: diag/p2p-trace-0.2.10-20261115
Final application/build source: b3eb55680b51f5fbdf392d402acdcdae168f2b20
Previous failed build source: a0881bf7c1d97724ea166f0e51988902c280a5cc
Remote final source tree: 65fcf8b28d573301792720ce1968459195998646
932 selected text/source/evidence blobs and sizes were read back from the remote tree. Master remained 519f0d5450f77ce4ba757a644b2144607b0a5c06 at the final push readback. No master/release write, PR or Release.

Any later commit containing this handoff is EVIDENCE ONLY. The actual APK source remains b3eb55680b51f5fbdf392d402acdcdae168f2b20. Read the current remote diag HEAD before UI dispatch: pipeline.py requires its --sha to equal the current branch HEAD. Use that HEAD as the UI workflow SHA and explicitly pass --build-sha b3eb55680b51f5fbdf392d402acdcdae168f2b20. Do not silently rebind the application source to a documentation commit.

## Completed and independently verified

1. QUALITY Q1 produced genuine FAILs: historical identity-table overwrite and output path traversal. The product Runtime race fix was accepted. Helper-only corrections ran real RED6/7 assertion failures -> GREEN6. Old migration table restored exactly to SHA 4f12c91fbed49afe409a9361f8e23c3540f6db8234d34ad4969033764eb8944d; Q1 table SHA 102cc847b76cda3ccc201843174ff6030de2704cd257d9bc8937b604c676d9fe retained separately. All failures/raw originals remain.
2. Q2 independent SPEC and QUALITY passed on 63 inputs. First actual Android build43710014774/attempt1 failed Kotlin1.9.24 syntax and produced no artifacts. Local compiler2.4.20 had accepted that syntax; CI/toolchain was NOT upgraded.
3. Actual pinned Kotlin1.9.24 RED reproduced 11 literal-prefix errors. A first ten-space candidate still failed and was retained. Actual lexical matrix confirmed BOTH separators are necessary. Final changes versus a0881bf7 are exactly21 ASCII spaces: P2pTrace14, SyncEngine5, new diagnostic P2pTraceEngineTest2. No string values, assertion tokens, SDK callbacks, guards, READY, SendAttempts, protocol, retry, timeout or filtering changes. P2pTraceEngineTest is not in the original frozen35 baseline test inventory; those original files were not changed.
4. Final actual Kotlin1.9.24 HOST compile exit0 and JUnit171/171. Evidence: r6/evidence/r7-ci-compiler-green-final/. This is HOST, not physical/Android acceptance.
5. Q3 first SPEC stopped on its own wrong historical-finalizer reconstruction. Actual committed Q2 finalizer was then read directly from a0881bf7 and verified against the Q2 manifest SHA 0abc0f8586765c355d17104181b43f661bfa6b944e7ed6c06b9fe9beb9274e77. The original incomplete FAIL was kept, not rewritten.
6. Continued independent SPEC and QUALITY both passed on 90 exact live inputs. Manifest SHA d4b04ff2789bc67ca17a14a73f5550290f0cef66f881340976196997c0400624. SPEC report SHA17558e0101a1401c451a75a200db7a46ef1bc0da9b21e6ec4776394a02879016; QUALITY report SHA378d7c45b2b497660f2b14641265700123a7267eb52165d804839efd38f27b98. Actual reports/raw: r6/reviews/r7-spec-q3-continuation.json, spec-q3-continuation-raw.txt, r7-quality-q3-continuation.json, quality-q3-continuation-raw.txt. Closure: r6/reviews/closure-q3/. All90 inputs were also checked against committed b3eb5568.
7. AFTER dual closure, unchanged runner performed another genuine fresh full regression without resume/copy: JVM171, app-cwd6, Python133 zero skip, HTTP3784, Runtime4, native adapter8, Huawei jar type-check exit0. Every original raw/return code/72-source manifest was read back. Evidence: r6/evidence/r7-final-regression-q3/. Original watch source was only read/executed as HOST:445/445, zero fail/skip, before/after input SHA equal in r6/evidence/r7-watch-frozen-q3/.
8. Original9461 baseline protection was corroborated by immutable prior full-content receipt, exact Git tree/current permitted diff and complete original35-test/literal inverses. Explicitly NOT a repeated fresh2GB hash, per R7 resource rule. CI workflows and original behavioral criteria remain byte-identical.
9. Final source b3eb5568 was committed, pushed and remotely read back. Current final identity table is r6/evidence/r7-ci-identity-final/table.json. Exact source SHA values: WearProbe18a693e7a075d1d52a5cc639ff8df005025b18df85318e6dcfe3a321b1d2611c; SyncEngine84533ebc792f0c108c79f043698a20ec89018a9dba19dbb606ae1bc6d3cc4e1a; DiagnosticRuntimec82a665d3b06ca53b19c0f8c63eef369a2d4ea4f48c53c1e9e6936969f38a2d6; P2pTrace9ffa02c51407301d8c308257609feea1961897076758f6da5ffe5ce53949f084. Version12/0.2.10 unchanged.

## Actual final CI/build binding

Final build run: 43715446826
URL: https://github.com/lantianhcgp/elcton-phone/actions/runs/43715446826
Source: b3eb55680b51f5fbdf392d402acdcdae168f2b20
Workflow: .github/workflows/build.yml
Event: workflow_dispatch; inputs {}; run_attempt1
Exact run and attempt completed/success; one complete build job success, no failed steps. Artifacts total2, enumerated exactly:
- android-probe-b3eb55680b51f5fbdf392d402acdcdae168f2b20, id14162980048, size9072788 bytes, official digest sha256:e012b8060373a1e4c18009b8ff457d223834c923666e664fc778f35e1d2004f0.
- diagnostics-http-b3eb55680b51f5fbdf392d402acdcdae168f2b20, id14161844466, size35175 bytes.

Original run/attempt/artifact JSON: r6/ci/r7-build-final-wait/.
Actual registration: r6/ci/r7-build-dispatch-final/registered.json.
Case registration: r6/ci/r7-case-registration-final/testcases.json, REQUIRED exact172 labels=original153+new19. Registration is not independently verified binary/Gradle execution.

## Download state — inspect this before another download

The final bounded background fetch was still running at the last tool observation (20:57:43 CST), and its output archive was0 bytes because the isolated curl wrapper buffers the response before writing. It may finish after this handoff; do not assume it was completed or stopped.
Tracked session: proc_524da13f4e9e; last observed PID4639.
Command: python -B qa/p2p-trace-0210/r6/ci/r7_curl_readonly_transport.py fetch --kind build --run 43715446826 --sha b3eb55680b51f5fbdf392d402acdcdae168f2b20 --source b3eb55680b51f5fbdf392d402acdcdae168f2b20 --out qa/p2p-trace-0210/r6/ci/r7-build-fetch-final-success

Current target: r6/ci/r7-build-fetch-final-success/.
Current transport log: r6/ci/r7-build-fetch-final-success.curl-transport.jsonl.
Read process status and actual files on resumption. Only a successful complete inventory.json plus exact original pipeline verification is a successful fetch. ZIP size/digest/CRC, every extracted byte and source-sha.txt must match the official artifact. Locate actual main/test APK paths from the fetched inventory, not guessed directory layouts.

Earlier failures remain: original gh GET retries exhausted with TLS handshake timeouts before fetch output creation; first curl adapter lacked subprocess.PIPE and stopped before ZIP transfer. It was corrected only in the isolated transport adapter; original gates unchanged. r7-build-fetch-final-curl-first-failed/ preserves its saved API/attempt/asset/empty archive/failure note. Do not overwrite failed directories. All curl/gh failures and old artifacts are retained. No POST retry was used.

The original pipeline/common/verify_r6.py files remain byte-identical to the reviewed source. r7_curl_readonly_transport.py substitutes only official HTTPS GET/download transport, uses TLS hostname verification, no insecure TLS, rejects POST, and calls all original run/attempt/artifact/CRC/SHA/count predicates unchanged. Its optional --resolve address20.205.243.168 came from an actual independent DoH response; rediscover if stale, never disable TLS. Credentials stay in private git storage and subprocess stdin, never in reports/visible argv.

## Remaining mandatory chain

1. Settle/read the existing bounded fetch. If it failed, preserve originals and use a NEW exclusive output directory for another exact artifact download. Do not dispatch another build merely to get a ZIP.
2. Run r6/ci/verify_r6.py build with --source b3eb55680b51f5fbdf392d402acdcdae168f2b20 --run43715446826 (as separate argv), the ACTUAL fetched --incoming, case manifest r6/ci/r7-case-registration-final/testcases.json and NEW --out under r6/ci. It must verify main12/0.2.10, package com.hcbiu.elcton, test instrumentation target, stable signer fc08a0b474a8ffca5887bd5c88ac15e865a63a64eca81c10f344496c46d9ad94, v2/one signer/CRC and all actual172 exact Gradle testcase labels. NOT YET RUN.
3. Only after true build verification, original pipeline dispatch-ui: register diagnostics FIRST, then full using genuine previous-registration. Set build_run43715446826/build_sha b3eb5568 explicitly, API33/three-button. For --sha use the current remote diag HEAD (a documentation-only handoff commit may have advanced it), and verify workflow/test/application blobs are still the built source. Never blindly repeat an accepted POST or choose ambiguous runs.
4. Wait/fetch exact two UI runs/attempts/artifact IDs. Run verify_r6.py cloud for diagnostics and full with the actual registration, actual build receipt and workflow SHA. Preserve ALL original complete JSON/pixel gates, zero-copy old600MB tree, no reduced assertions. NO UI RUN WAS DISPATCHED IN R7 YET.
5. Inspect actual UI images component by component, retaining numerical pixel gates. Do not replace cloud with phone/ADB/rish/MCP/Chromium. Cloud emulator is the only authorized UI execution here.
6. After both original UI receipts PASS, execute committed finalize_r6_delivery.py with actual signed main APK, sourceb3eb5568, true build/diagnostics/full receipts and new output directory. It requires current final table and closure-q3. Target /storage/emulated/0/Documents/elcton-WearEngine-真机联调-20261113-123000/phone/hc课程表-0.2.10-code12-b3eb5568-<actual_apksha8>-signed.apk plus DELIVERY report. Never overwrite an old APK. APK SHA256 is currently NOT KNOWN/NOT VERIFIED.
7. Publish selected nonsecret source/evidence and final handoff to the same diag branch only; read back exact ref/tree/content. Evidence commit SHA and actual application source SHA are separate. Update the single Documents progress file at every major verified node.

## Red lines and status

No device operation/installation, watch/app/table edits, /haps, watchface, Liubai, Release or PR. Do not change protocol/timeout/retry/fingerprint/filtering/READY/SendAttempts/SDK business callbacks/old behavior assertions/old35 tests/9461 baseline/watch445. Original failed logs and evidence never deleted. Jars/generated.kt/APKs/tokens never staged. Credential values never printed or committed. Unknown physical reverse-handshake root cause remains UNKNOWN; HOST or emulator successes do not prove it fixed.

Single user progress file: /storage/emulated/0/Documents/elcton-WearEngine-真机联调-20261113-123000/进度.md.
R7 delivery status: qa/p2p-trace-0210/r6/R7-DELIVERY-STATUS.json.
No signed APK has been copied to the phone delivery directory by this run.
