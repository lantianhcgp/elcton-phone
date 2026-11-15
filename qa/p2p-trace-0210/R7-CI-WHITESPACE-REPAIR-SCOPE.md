# R7 CI Kotlin 1.9.24 whitespace-only repair scope

Actual failure: run43710014774 / sourcea0881bf7c1d97724ea166f0e51988902c280a5cc / attempt1, step Unit tests and actual APK, compileDebugKotlin. No artifacts. Exact original log is r6/ci/r7-failed-log-attempt1/failed.log and API/attempt/job originals are retained.

CI fixes Kotlin plugin1.9.24; actual local kotlinc is2.4.20. Ten newly added diagnostic expressions have a string closing quote immediately followed by else. CI reports Unsupported [literal prefixes and suffixes] at exactly seven P2pTrace lines77,138,141,150,153,158,161 and three SyncEngine lines370,371,395.

R7's authorized pure-diagnostic completion includes the smallest compile-compatible spelling correction: add one separating ASCII space before else at exactly these10 sites. No string content, protocol, guard, callback, retry, timeout, filtering, READY/SendAttempts, test assertion or compiler/toolchain changes. No broad formatting. Four Q2 SHA are preserved as historical inputs; after two source whitespace changes new current SHA identities are separately registered, old tables/old review closures retained.

Requirements before new source push:
1. Preserve original current files/identity/Q2 reviews and real CI failure.
2. Exercise Kotlin1.9.24 actual compiler RED then the exact correction GREEN. Use a narrow original-source slice/full isolated HOST compile; no fabricated output.
3. Verify exact inverse removes only the10 added spaces and restores all source bytes to committeda0881bf7; unchanged other2 product sources, all protected tests/workflow, version12/0.2.10. Behavior-token and old whole-byte invariants remain.
4. New current identity/table must preserve old/R5/Q2 hashes, use distinct table/closure paths, never overwrite original Q1/R2 evidence or reviews.
5. Independent delta SPEC then QUALITY, actual full regression, whitelist narrow commit to the same diag branch; actual new CI build172 and original UI gates. Old failed build remains failed.

No devices, /haps, Release/PR, master/release branch or credential publication. No upgrade from Kotlin1.9.24 to hide failure. Unknown real-device handshake root cause remains unknown.
