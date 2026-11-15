# R6 scope amendment — test source path only

Following completed first scope check (9461 entries, all contents verified) a new R5 diagnostic test P2pTraceRuntimeTest (NOT one of the 35 frozen baseline files) failed when JUnit working directory was app/. Two failures were FileNotFoundException; complete raw and old new-test source remain in evidence/gradle-cwd-preflight-1615.

The sole subsequent test edit changes three File paths to resolve an existing project root from the actual working directory, plus the exact root resolver. Every assertion, label, regexp, cardinality and original callback/guard check is unchanged. The precise inverse restores SHA256 d6d3b801d3bbfbb5a264457aeee0658e847aeaaa3e0fabb3cb6e052ff03fec43, as independently recorded in source-path-fix-proof.json and reviews/input-r2/new-diagnostic-test-path-fix.json.

New test source SHA256: 85cac5a68fe22e07e56d18aebb709d4e92874b4ebc186fe50721bbfc9873a127. Input-r2 binds all 32 production/new-test/gate/fixture files; only this new test changed from previous 31-source record, added-cases registration is additionally bound. Four production source identities remain identical to current-identity.json. Old 9461 rows and all 35 baseline test entries remain untouched after the completed scope check.

Final input executes real full JVM171/171, actual app-cwd target7/7, Python133/133 skip0 and HTTP3784/3784 at evidence/final-current-cwd-1616. These are HOST JVM checks, not Android or native-device proof.

No blanket rewrite of assertions or old baseline has occurred. The first RED and all prior SPEC rejections remain original.
