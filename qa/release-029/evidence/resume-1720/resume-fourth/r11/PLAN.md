# R11 — observed crashdata containment correction, QA only

Original frozen R10 remains final-review-r10-fourth; its SPEC=false and all old R9/RED receipts remain immutable. Parent actual 5-test security probe returned exit1 / failures3 before any correction; saved crash-containment-RED.*. Source originals and hashes are pinned in this directory's before-manifest.json.

## Exact scope

Only qa/cloud_emulator_observer.py crashdata helper safety plus additive regression/attribution. No product/old app test/assertion/harvest decision/exit/retry/UI workflow resource changes. R10 complete HOST success is historical and will not substitute for R11 full regression/new independent axes.

## Minimal correction

1. Open both existing source and output directory paths component-by-component from a trusted root descriptor. Every component uses O_DIRECTORY|O_NOFOLLOW, rejects .., and retains the final descriptor; no Path.resolve lexical trust.
2. Use that pinned output descriptor for every crashdata output, including the empty source-absent index and the final index. Index leaf must use O_CREAT|O_EXCL|O_NOFOLLOW with mode600, not lexical Path.open.
3. Retain source/output descendant dirfd traversal, approved crash filenames, bounds, regular-file/inode checks and no hard-linked sources; no extra reading outside the permitted source. Reject observation-only unsafe paths; original child exit still determined only by child wait.
4. R10 STANDARDS also found an unbounded zero-byte-file/entry/depth/index case. Bound scanned entries, copied files, directory depth and index UTF-8 bytes; use lazy scandir rather than unbounded listdir. Stop traversal when any aggregate budget is exhausted, and record bounded budget metadata via the pinned output descriptor. Keep per-file32MiB/total64MiB limits and source nlink/inode checks.
5. The identical new 5-test independent security probe must become GREEN5 without changing its assertions. Add its exact tests to repository QA discovery, preserving the initial probe/source bytes and RED receipt; add resource-cap regressions before fixing, retain their initial RED. All existing 123 Python tests plus additive new tests must execute zero skips; JVM/HTTP/Runtime/Termux rerun, exact product/old tests/harvest inverse preserved, then fresh complete review binding.

No claim about old emulator disappearance mechanism or physical acceptance. New code correction does not itself supply Android/full PASS.
