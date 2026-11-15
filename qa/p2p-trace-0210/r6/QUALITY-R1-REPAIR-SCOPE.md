# R6 QUALITY R1 repair scope (authorized diagnostics only)

Real rejected issue Q-R6-001: DiagnosticRuntime final condition observes trace sequence S, then trace-only event S+1 arrives before `writing.set(false)`. Its callback sees writing=true and does not enqueue a worker, while finally checks only business revision. Pending event has no eventual writer wake.

Only DiagnosticRuntime diagnostic worker may change: record processed trace sequence and re-check both old business revision and trace sequence after release. Failure policy must remain quiescent until a later observation. No SDK calls, callback wrappers, READY/attempt guards, observer return values, timeouts, MCP tool/revision contract or existing assertions may change. Three other production source hashes remain frozen. No device/Chromium/Release/haps/watch/留白 action.

Before changing product: a deterministic HOST-only bytecode/barrier lane executes actual compiled Runtime and emits after final check but before writer release. Original source bytes/hash and original QUALITY R1 JSON/raw stay sealed. HOST instrumentation must be precise and receipted; do not claim Android/native acceptance. Same unchanged case must be assertion RED, then GREEN after minimal diagnostic fix. Original Runtime fault/stop race tests remain exact.

After fix: current-only Runtime source identity is explicitly migrated (previous row preserved); all other identities/literals frozen. Original manifest and prior migration evidence are not overwritten. Full current Python133/JVM171+HOST/HTTP re-run and source-linked independent SPEC then QUALITY delta review must pass before CI. New rejected receipts are never converted to PASS in place.
