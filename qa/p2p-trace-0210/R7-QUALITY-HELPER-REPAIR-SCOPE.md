# R7 QUALITY Q1 helper-only repair scope

Authorization: the user's R7 task permits fixing actual QUALITY FAILs within the diagnostic scope and requires every failure original retained. This correction restores the already-authorized historical evidence identity rather than changing any product or old assertion.

Actual independently reviewed failures (retain Q1 report/raw verbatim):
- Q-R7-Q1-001: migrate_r6_quality_identity.py overwrote evidence/identity-migration/table.json. Restore its exact original bytes only from saved previous-table.json.source.txt after verifying the original SPEC R2-bound SHA 4f12c91fbed49afe409a9361f8e23c3540f6db8234d34ad4969033764eb8944d. Before restoring, preserve the present overwritten bytes in a new exclusive repair evidence directory and bind both hashes. The current Q1 table remains at identity-migration-q1/table.json. No historical review JSON/raw/manifest edits.
- Q-R7-Q1-002: containment guards in run_r6_final_regressions.py and check_r6_scope.py accept parent traversal/symlink ancestry, and scope allows an existing output. Reject parent segments and every symlink ancestor; check resolved containment and create output exclusively before any write. Do not change substantive baseline/test/identity predicates or production input.

Repair tasks:
1. Write focused HOST/helper tests first; execute against exact current script prefixes or isolated sandbox with frozen required data to obtain genuine RED. No 2GB full baseline reading, no full compiler run for this test, no files outside an exclusive repair sandbox.
2. Minimal output/migration helper fixes only. Same tests GREEN. Save both raw outputs, exits, before/after script bytes, SHA-bound diffs, unchanged test bytes and evidence restoration receipt.
3. Update delivery helper's identity-table path to current Q1 path (presentation only); product four SHA/versions/old behavior assertions stay unchanged.
4. Freeze fresh input-q2 manifest that extends all 41 Q1 inputs plus repair/helper evidence and final publishing/closure/delivery wiring. Obtain independent SPEC then QUALITY on that exact manifest. Q1 FAIL remains original, never re-labelled PASS.

No commit/push/CI before genuine new dual closure and fresh full current-source regressions. No device/MCP/ADB/rish/browser, watch writes/build, /haps, Release/PR or secret output. Original source/test gates, 9461 baseline and watch445 predicates remain unchanged; cached baseline/Git identity plus prior full-content evidence replaces forbidden repeated 2GB hash, with this limitation stated.
