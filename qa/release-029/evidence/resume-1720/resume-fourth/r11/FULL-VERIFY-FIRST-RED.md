# Actual full local verification execution RED — originals immutable

Cloud full43600975926 is actually completed/success (exact source84a6c40/build43600711386), artifact14115534555 downloaded completely and CRC/inventory generated.

First offline verification actual command/log/execution:
- exact-cloud-pipeline/full-verify.execution.json: exit1, started2026-11-14T21:53:47.177764+08:00, ended21:54:19.588185+08:00.
- full-verify.log is0B, SHA e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855.
- full-verification/ contains execution/criteria/partial raw snapshot but no receipt/input-inventory/failure traceback.
- actual partial raw/artifact-original.zip is194191360B versus incoming exact214397210B. Five metadata files absent. All original936-file inventory and incoming original ZIP are preserved. No verifier live process remains. Cause of this local process exit is unknown: do NOT label OOM/disk/Android assertion without proof.
- parent pipeline then exited1 on missing full-verification/receipt.json; no pipeline-result exists. This is never green.

Continuation uses a NEW isolated verifier output and original unchanged pure criteria/full JSON comparison. All complete input files are SHA256/size-verified through file_digest, native hardlink snapshot avoids second huge copy, then exact snapshot/input checks repeat after original gates. No change to first failed snapshot/partial archive/log/execution, candidate, original predicates, thresholds, signal/harvest/CI or cloud run. No re-dispatch merely to fix local evidence transport. Independent acceptance waits for a real exit0 receipt.
