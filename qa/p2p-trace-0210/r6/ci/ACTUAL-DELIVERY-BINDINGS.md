# R6 actual artifact contract (before any CI dispatch)

- Explicit diag branch only; no master/release mutation, no Release, no device access.
- Review closure must be actual SPEC Q1 then QUALITY Q1 on same 41 current SHA manifest. R1 rejection and old SPEC stay immutable.
- Source commit must contain every reviewed blob exactly; `git show <source>:<path>` SHA readback checks all 41.
- Original build.yml workflow bytes frozen and workflow_dispatch. Exact artifact android-probe-<source> contains main APK, test APK, actual Gradle XMLs, source-sha.txt.
- Exact required Android Gradle inventory 172 = original actual 153 labels + new 19 labels. No HOST substituted, no skipped classes, no inclusive count acceptance.
- Actual original HTTP selftest from Gradle Android classpath must pass in build job before signing.
- Original diagnostics/full ui-smoke workflows on same source with build_run/build_sha pinned. API33/three-button; original complete original JSON/pixel/test assertions enforced, never fake snapshots.
- Bind run_id/run_attempt/actual jobs/attempt artifact creation time + ID, safe ZIP CRC/digest/expanded byte readback; same name from other attempts rejected.
- Only actual stable production signing accepted: certificate fc08a0b474a8ffca5887bd5c88ac15e865a63a64eca81c10f344496c46d9ad94. apksigner v2=true/signers1, package com.hcbiu.elcton, code12/name0.2.10.
- Verified main binary only non-covering Documents phone path. No UI-test APK delivered as main. Existing 029 never overwritten. All RED and rejection originals retained.
- Handshake root cause still unknown. Install/handshake acceptance belongs to initiator.
