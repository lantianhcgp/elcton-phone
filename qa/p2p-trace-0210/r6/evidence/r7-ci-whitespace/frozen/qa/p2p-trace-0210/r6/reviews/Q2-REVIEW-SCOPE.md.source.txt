# R7 Q2 review boundary

User authority: R7 QUALITY FAIL修到绿, pure diagnostic scope; original failures retained. Q1 rejected helper correctness only, explicitly accepted the frozen Runtime c82a665d product repair.

## Already implemented and really exercised
- Q-R7-Q1-001: migration no longer overwrites old table; old table restored exactly to SPEC R2 bound 4f12c91f…, current Q1 table remains 102cc847… and overwritten snapshot retained.
- Q-R7-Q1-002: regression/scope output containment checks normalize path, reject parent traversal/symlinks before directory creation. Real exact-main-prefix HOST tests RED 6 cases / 7 assertion failures → GREEN 6, no source/old tests changed.
- Same guard shape on the new final delivery helper separately reproduced RED 4 / 2 failures → GREEN 4. Actual main prefix only, no APK/device operation.
- Parent additions to new delivery helper: required filename, actual build-row SHA/size/package/version, committed four-source hashes, committed review-manifest hashes and raw/closure provenance before delivery copy, CI URLs and complete identity/review indexes. These additions are not represented as worker-reviewed; current helper is included fresh in Q2.
- Commit helper now requires actual new R7 regression and watch receipts before commit. Publish uses explicit whitelist and secret scan. Closure checks axis/raw/manifest mappings against both genuine reviews.
- Cached scope helper reconciles the original full 9461-row/2GB content-hash receipt by immutable SHA, Git index blob+stat coverage and whole 35-test source readback; it explicitly does NOT claim a fresh massive full content hash. This obeys R7 no repeated2GB hash rule. It must still reject any protected product/test drift.

## Reviewer responsibilities
Start from input-q2/reviewed-manifest.json and its current live hashes. Read the original Q1 FAIL JSON/raw and original SPEC Q1; inherit unchanged source conclusions only when identity exactly matches. Audit all helper modifications and new files listed in Q2-DELTA.json, verify RED/GREEN raw and exact old table restoration. No broad reimplementation, product edits, test edits, device/network/CI or massive hashing. Parent will run full regression only after dual PASS.

Fail closed for any real security/logic/scope defect. Style suggestions are not false blockers. If blocked, write the actual FAIL JSON/raw before returning. Do not create PASS-shaped placeholders. Reports must carry axis, passed, input_files, input_manifest_sha256, reviewed_inputs, raw_reply_sha256, relevant source/evidence coverage and explicit security_concerns/logic_errors/missing/critical/important arrays.

SPEC first, then independent QUALITY of exactly the same frozen Q2 inputs. Current Q2 is authoritative; prior FAILs, reports and their frozen manifests remain byte-identical historical evidence.
