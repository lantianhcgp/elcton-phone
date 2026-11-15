# FIX-R1-CONTINUATION — R5 independent SPEC r1 observation repairs

## Stop / scope

- Writer began **2026-11-15 13:24:04 +08:00**, hard stop **13:44:00**. Product frozen **13:40:00.315101**; final source verification **13:41:08.029871**. Stopped before the hard box; do not resume product edits on this receipt.
- Repository: `/data/data/com.termux/files/home/elcton-phone-diagnostics-0210-20261115`; HEAD/base remains `bb26c64b67e1cfa7903cd709c2aac482f6490e6b`.
- Full original `reviews/r5-spec-r1.json` and R4 approved patch plan read. This writer changed **WearProbe.kt, SyncEngine.kt, P2pTrace.kt** only in product; **DiagnosticRuntime.kt unchanged during this continuation** (it retains the pre-existing R5 diff from base).
- Only three tracked product files differ from base: WearProbe/SyncEngine/DiagnosticRuntime. No tracked test/assertion, protocol, fingerprint, timeout/retry, SDK packet getter, callback business guard, Gradle, version, CI, push, commit, staging, device, browser, watch, HAP or watchface action.
- Parent alone owns `native-host` templates/runner and independent SPEC r2. This writer did not modify them.

## Implemented observation repair

- **L1:** send and release retain the original SDK call → original failure-listener chain and business catch. Store its returned Task; the added success-listener registration and lambda are separately isolated with `catch(Throwable)`. Attach failure is not forwarded to business failure/describe. No second SDK call, setter, executor or scheduler.
- **L2:** `bind` preserves previous attempt/native/device only within the same engine generation. Fresh post-`++generation` connection bind occurs before installed/peer setup. Registration context resets attempt, captures independent native generation, and is stored on the existing NativeRegistration. Related RX/cleanup can borrow the latest attempt only for an exact engine/native generation pair. Engine stage helper merges the relevant captured/current context; send callbacks retain their captured send attempt. Device reference is the current list index, not an SDK getter.
- **L3:** engine SEND_TASK_FAIL/sync failure stale metadata now includes `!sendAttempts.accepts(attempt)` in addition to original closed/generation facts. Adapter send Task/result stale observes native generation and trace-context generation/native/attempt equality, without gating or swallowing original callback dispatch. Close cleanup keeps a `close` diagnostic trigger through the unchanged close→cancel business path.
- **S4:** outgoing PHONE metadata is separate from watch ingress (`direction`, phone sender, accepted HELLO); integer `protocolVersion` is emitted. Instance metadata uses SID-salted SHA-256 keys and a maximum 128-entry anonymous-reference map (`r1`, `r2`, …), never raw transfer IDs/text in events or retained keys. Existing companion ingress classification and original PacketIngress business result remain separate. Queue 128/event 2048-byte bounds unchanged.

## Real evidence (no stale jars credited)

| Lane | Compile | JUnit | Evidence |
|---|---:|---:|---|
| New semantic RED, current r1 before repair | 0 | 1; 5/5 failures | `evidence/fix-r1-red-1325` |
| Full current HOST suite + unchanged baseline Engine oracle | 0 | 0; **171/171** | `evidence/fix-r1-green-1333` |
| Real current Runtime fault tests + unchanged original socket/file race | 0 | 0; **4/4** | `evidence/fix-r1-runtime-1337` |
| Parent exact original/current WearProbe fake API oracle | 0 | 0; **3/3** | `evidence/native-green-1336` |

- The new five RED failures demonstrate phone sender=other, cross-generation attempt=9 inheritance, transferRef=present collapse, RX/READY missing attempt, old same-generation Task failure stale=false. Same unchanged five tests are included in the 171 GREEN (original 152 + earlier new 14 + this new 5); all original Engine business call/state comparisons passed.
- Parent native RED `native-red-nullfix-1333` was read: compile0/JUnit1, 3 tests with **one target failure** on success-listener attach. Original error count0/failure listeners true versus pre-fix error count2/listeners false and extra send_fail. The same target tests GREEN3 were read and exact current source hashes checked. Earlier parent missing dependency/null fake seam failures are harness failures, not target RED; preserved, not credited.
- Runtime three new fault tests are **verification GREEN only**, not RED→GREEN product changes: 2MiB quota preserves existing log and original state writes; log-path failure continues state writes and remains quiescent without a new observation; malformed trace-tail snapshot cannot skip original read/state fields. Existing race still obtains actual loopback health200, stops the real socket, and persists final running=false. No Runtime product changes were needed here.
- New fault Runtime construction explicitly uses `host-test`; original two-argument legacy race constructor remains unchanged and its historical phone-device origin is not hardware evidence. Production trace clock remains actual `System.nanoTime()/1_000_000`; no business scheduler clock change.
- At 13:41:08 all available current compiler-input hashes in each of the three GREEN lanes matched; frozen four source/six new test hashes matched; `git diff --check` exit0. Receipt has exact argv/exits/log SHA, no skip/relabel.
- Environment warnings (jansi libc.so.6 and earlier existing Kotlin reflection warnings) did not block compile0. No invented Android/device execution.

## Exact current product SHA-256

```
WearProbe.kt         8858aa73e7c69e9b7d3cafbf19fe26c224300409536f8a921dca1e77bff8b7d1
SyncEngine.kt        f59966880018477c7bbab7768ca5e0b2bc5ad3e83594fc45e0ab7ff367ca63a2
DiagnosticRuntime.kt e6e10f6ddb3f4cd620879509a28e61433139feddf84b90d783e34167ecfe2cc7
P2pTrace.kt          ba747e234bb4f61bb5ffb801a8abac6e5a4eba28014c7627febf4ad84c0c0bc8
```

Machine receipts:
- `evidence/FIX-R1-PRODUCT-FROZEN.json`: exact four product and six new-test hashes, freeze time.
- `evidence/FIX-R1-CURRENT-SOURCE-RECEIPT.json`: exact compilation/log hashes, per-lane exits/counts and drift checks.

## Files authored by this continuation

- Modified product: WearProbe.kt, SyncEngine.kt, P2pTrace.kt.
- Added `app/src/test/java/com/hcbiu/elcton/P2pContextTest.kt` (5 semantic tests; no old test edits).
- Added `qa/p2p-trace-0210/runtime-fault-host/P2pRuntimeFaultTest.kt.in`, `run_runtime_fault_host.py` (3 real Runtime fault tests plus the original race).
- Added `evidence/fix-r1-red-1325`, `fix-r1-green-1333`, `fix-r1-runtime-1337`, freeze/current receipts and this continuation. New generated Kotlin inputs are outside the repository tempdir; evidence copies use `.source.txt`. Jars/raw files remain untracked; no staging of artifacts.

## Remaining / honest boundary

1. **Independent SPEC r2 pending** on this frozen source. L1–L3/S4 are implemented and targeted observed gates pass, not independently certified complete. New native oracle primarily covers L1/SDK-call/getter/receiver/callback fidelity; it does not replace exhaustive adapter generation/attempt causal scenarios. Parent may review late Task immediately after READY invalidation (trace still retains the last attempt until the next bind), stale registration cleanup metadata, and the no-cross-native-pair rule independently. Do not claim untested cases proved.
2. Version remains **code11/name0.2.9**. Two prior parent questions about 12/0.2.10 versus old version/source locks remain unanswered. No migration, skip, fake old-source strings or changed assertions. Current original Python133/4 exact-source-lock failures remain a parent-recorded unresolved gate; this writer did not rerun/relabel them or reuse them as GREEN.
3. **No full Android CI/build/APK/install/signature/device proof.** Parent actual-Huawei SDK type lane is separate and was not awaited/credited here; neither it nor fake Android API tests equal real Android full compilation or hardware results. Parent owns HTTP rerun/receipt, not credited by this writer.
4. SourceSet recursion over historical qa evidence `.kt` remains a release/staging risk noted in SPEC r1. Existing generated evidence was not deleted/renamed; final authorized staging must whitelist templates/tests/source and exclude jars and evidence-generated Kotlin.
5. Root cause of phone↔watch handshake remains unknown; this is pure observability repair, not a handshake or course-transfer success claim. Stop at this boundary rather than exceeding the time box or device/CI authorization.
