# Original pre-push scanner execution RED — retained

Command (cwd=/data/data/com.termux/files/home/elcton-phone-release-029-20261114):
python -B qa/release-029/evidence/resume-1720/resume-third/scan_pre_push.py --out qa/release-029/evidence/resume-1720/resume-fourth/pre-push-scan-first.json

Actual tool exit_code: 1
Actual stdout/stderr (tool returned):
Traceback (most recent call last):
  File "/data/data/com.termux/files/home/elcton-phone-release-029-20261114/qa/release-029/evidence/resume-1720/resume-third/scan_pre_push.py", line 57, in <module>
    raise AssertionError('Listed file missing: ' + name)
AssertionError: Listed file missing: qa/release-029/evidence/resume-1720/final-review-r10-fourth/spec-probes/crash-output-ancestor/link-parent

The original scanner script is unchanged. It treats a deliberately created dangling symlink from an independent security probe as a missing ordinary file. No PASS receipt was written. This record is the actual returned tool output, not a re-created subprocess run. A new evidence-only scanner will preserve git symlink payload bytes without following links; it will retain all original ordinary-file/archive credential checks. The old failed record is not green and is not overwritten.
