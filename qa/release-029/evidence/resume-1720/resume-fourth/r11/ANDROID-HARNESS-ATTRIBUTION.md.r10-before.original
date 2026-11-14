# Android 0.2.9 harness migration — local schema GREEN, Android pending

Scope: only DiagnosticsUiTest.kt, McpKeepAliveTest.kt, diag_emulator_smoke.py, test_keepalive_gate.py and this new release evidence. No production source edits, local adb/rish/install, git commit or push.

## Exact contract relocation

- Installed/package/cold/background version checks: 0.2.7/code9 → 0.2.9/code11. All token 0600/non-echo, loopback, complete HTTP length, error journal, original full-text/scroll/pixel and business-file assertions remain.
- `passiveRuntimePersistsAndShowsCompleteSyntheticError` remains unchanged in name and purpose. Exact tools/list grows from the original four to 15 without duplicates; the four original schemas/annotations and all original calls are independently asserted. The diagnostic `mcp.readOnly` snapshot assertion remains true.
- `defaultOffOptInKeepsBackgroundHttpAndOffStopsPort` retains its historical method name so no old test is removed. Its default choice expectation is now on; notification denial, bind failure and background channel denial retain true choice while listener/service/notification stay inactive. This is NOT weakened fail-closed behavior.
- Receipt mapping: `defaultOff` → `defaultOn`; `noDefaultNotification` → `noNotificationWithoutPermission` (API33+ denied fixture) and default-on enabled notification is still asserted. `bindFailureUiOffAndHintRetained` → `bindFailureUiOnAndHintRetained`; `activeChannelDeniedStopsAndUiOff` → `activeChannelDeniedStopsAndUiOn`. All original backgroundHttp/offPortClosed/offNotificationRemoved/businessAndTokenAndErrorsUnchanged/startingNotActive/permissionDeniedFailClosed/backgroundChannelDeniedEventStops semantics remain. Added defaultOnNoPermissionRetainsChoice, stopDisablesChoice, stopInactive.
- Normal startup receives POST_NOTIFICATIONS before MainActivity/instrumentation launch; no initial toggle is used to manufacture an off default. Destructive last instrumentation resets only emulator test preferences to an absent keep_running choice and sets the one-shot notification prompt guard before Activity launch. The real denial remains asserted.
- Normal background evidence stays bounded to offsets 0/2.5/5 seconds with the original foregroundId/isForeground/same PID/not-resumed/not-instrumented checks. This does not prove the user's ten-minute physical-phone requirement.
- STOP is the real visible notification action only, with no settings/service fallback. Before the first post-ack health/closure probe, wait for new notification STOP + completed stop event, durable keep_running=false, and absence of the service. Every original closure/notification/file assertion remains afterward.
- Added `sharedPhoneSurvivesRecreationAndPureMcpCourseFixtureRoundTrips`: real Activity recreation identity, real authenticated loopback courses_write preview/confirmed write and courses_read, disk and shared schedule checks, protected token/journal checks. All four timetable/backup files restore their exact prior bytes/absence. Fixture is emulator-only; no sync/pickup/scan/real WearEngine call is made. Separate method invocation preserves each existing exact-one-test result gate.

## Evidence and pending work

Baseline old schema: `python qa/test_keepalive_gate.py` ran 7 tests, exit 0. After changing only expected receipt keys, before changing the verifier, `python -B qa/test_keepalive_gate.py` ran 7 tests with 2 expected failures, exit 1 (android-harness-contract-red.log/.exit). These are local schema tests, not Android execution.

Cloud CI must compile and execute all three Android methods on API33/34. No Android PASS is claimed. Production McpKeepAliveService still called disable() for bind failure at the time of this migration; parent must make bind failure retain true preference and align its failure hint to `MCP 端口启动失败；保持运行未启动，开启偏好已保留`. Parent owns the final 15-tool HTTP/JVM client migration/build/CI. Physical phone, real WearEngine and ten-minute user proof remain pending.

Local reproduction from `/data/data/com.termux/files/home/elcton-phone-release-029-20261114`:

```
python -B qa/test_keepalive_gate.py
python -B qa/diag_emulator_smoke.py --self-test
git diff --check -- app/src/androidTest/java/com/hcbiu/elcton/DiagnosticsUiTest.kt app/src/androidTest/java/com/hcbiu/elcton/McpKeepAliveTest.kt qa/diag_emulator_smoke.py qa/test_keepalive_gate.py
```

Cloud-only full Android reproduction after matching signed APK/test/source artifacts are placed in incoming and the workflow provisions its sole verified emulator: `python3 -B qa/diag_emulator_smoke.py`. The original local/phone refusal guard is unchanged.

## R8 same-Activity return fixture correction

Run43586767169 at source9e300f9 failed at McpKeepAliveTest.kt:136. Its original logcat lines49700-49710 proves the component-only return constructed another Activity with an intent not matching ActivityScenario's original MAIN+LAUNCHER, resetting its per-instance navigation to today. Only the two emulator `am start` return commands at134/181 receive MAIN+LAUNCHER. No product/manifest/launchMode changes; every existing assertion, deadline, count, file identity, and background system-channel rejection path stays byte-identical. Full original test bytes are preserved as `evidence/resume-1720/resume-third/McpKeepAliveTest.kt.before.original`; the new four-case `qa/test_keepalive_return_fixture.py` proves exact whole-file reversal and rejects missing intent identity. Original RED2/4 and subsequent GREEN4/4 are kept. This is synthetic fixture verification only, not an Android PASS; fresh matched main/test APK execution is required.

## R9 cloud-only failure observation

`qa/cloud_emulator_observer.py` records host process/memory/cgroup/console/kernel/crash evidence around the original full-suite child once. It requires GitHub Actions plus a sole verified emulator, forwards the actual child exit, and never retries/kills it or changes device, SDK, GPU, RAM, window, preferences or assertions. The original palette helper gains one add-only self-contained inline raw-wire block; its full AST after removing that exact block equals the prior helper. `execute_palette_phase` and all original theme/product/palette predicates remain exact. `qa/test_cloud_observer.py` is seven synthetic observer/AST/exit/identity cases (RED7→GREEN7); it is not Android acceptance. Preserve both full RED runs and all raw reports. R9 must receive full fresh regression, independent review bindings, exact build and both cloud suites before delivery.

## R10 review-counterexample observation isolation

Original R9 independent SPEC=false (3 logic), STANDARDS=false (1 security/4 logic), inputs/raw counterexamples are retained. Only observer implementation is corrected: diagnostic wire construction/open/write/close has an independent try boundary; original harvest/parse/error/return statements stay exact. Observer directory/start/sampler/finalizer/receipt errors cannot prevent or replace the original single child; daemon diagnostics have bounded joins and native signal exit is re-raised (including SIGKILL). Crash inputs use pinned source/output directory handles and O_NOFOLLOW at every ancestor/leaf, reject symlink/hardlink/unapproved log inputs and copy bounded explicit emulator crash files. New eight synthetic isolation tests cover disk failure, start/dir failure, blocked sampler, native signals, and symlink escape; original seven cases and all pre-R9 tests/assertions remain. Observation success and actual Android full-suite success are distinct.
