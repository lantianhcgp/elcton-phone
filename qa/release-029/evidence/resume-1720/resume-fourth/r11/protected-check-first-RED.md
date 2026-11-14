# Parent protected-delivery observer RED retained

Actual first recheck wrapper exited1 before any write:
FileNotFoundError: [Errno 2] No such file or directory: 'passed'

The wrapper treated the real {passed, checked_at, rows, physical_device_actions} JSON envelope as a path->row mapping. The source baseline has never used that guessed shape. No APK/HAP bytes were changed. The corrected parent observer reads the explicit original rows array, keeps expected3, SHA256-checks all three actual files, and records real exit0 in r11/protected-deliveries-exact.json. This is an observer-schema error, not evidence of changed delivery bytes.
