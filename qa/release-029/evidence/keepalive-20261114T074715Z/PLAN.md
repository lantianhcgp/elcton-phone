# Keepalive policy / STOP evidence (0.2.9)

## Scope

Only `McpKeepAlive.kt`, new `McpKeepAlivePolicy.kt`, and new `McpKeepAlivePolicyTest.kt` are owned Kotlin sources. This directory contains new, additive evidence. Historical tests/logs are read-only. No device actions, installation, git add/commit/push, signing, watch, or Scope edits.

## Approved public test seam

`McpKeepAlivePolicy.enabled(savedChoice: Boolean?)` and `canStart(savedChoice, notificationsAvailable, stopRequested)` are pure policy inputs/outputs. Requirements: missing key defaults true; explicit false remains false; notification denial vetoes start without rewriting the enabled choice; on a late queued start, current false and the process STOP fence veto restarting.

RED uses a minimal extraction of the existing 0.2.7 behavior: missing key false, saved-choice + notification gate, no process STOP fence. It does not claim to be a real Android execution or a new instrumented test. Keep the identical test source for GREEN; do not weaken old tests to fit the new default.

## Android pending

Only the parent runs genuine emulator service/notification/socket checks. Notification STOP must confirm actual delivery (not merely `input tap` exit), synchronous false preference, listener and in-flight socket closure, abort on the shared PhoneRuntime, foreground service removed, notification removed, active=false, and no late-start reopen. Genuine phone/background/MIUI/WE results remain pending for the user.
