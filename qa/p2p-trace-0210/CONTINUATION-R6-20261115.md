# CONTINUATION R6 — 0.2.10诊断版（时限停靠，尚未CI/交包）

## 当前结论

L3-r2已修：真实afterREADY adapter独立Task成功/失败/SendResult真RED三目标失败 → 同测试GREEN8/8（含原HOST SDK3）。原READY/SendAttempts/SDK callback/业务守卫未改。

独立QUALITY r1随后提出Q-R6-001：writer终检与释放writing间的末条trace事件可漏唤醒。真实actual Runtime JVM仅HOST ASM barrier确证RED（6例只1失败；seq2/disk1/pending1/writingfalse，重复同失败） → 最少Runtime局部processedTraceSeq和退出revision OR seq复查 → 同6例GREEN（disk/state2/pending0）+原Runtime4/stop1绿，磁盘异常/quota仍静默不自旋。没有产品testhook。

最终全当前HOST回归真实通过：JVM171/171、Python133/133零skip、HTTP3784/3784、Runtime4、HOST native8、actual Huawei jar typecheck exit0。表端445/445实跑冻结；9461基线再逐文件blob核、35旧测试行为/非版本字节冻结。源码身份门只获批3源码+newP2pTrace/版本字面迁移，原旧029manifest不改。

最新独立SPEC Q1正式PASS41input/31checks；最后QUALITY Q1时限停靠，未有正式通过回执。被中断的QUALITY委派deleg_4697310b/sa-0-a249a4e4仅partial不作PASS。不要以原SPEC/旧QUALITY当新通过。

没有Android CI，没新APK，没本轮签名/版本APK实测或APK SHA。未推本轮500+文件、没有Release、未触设备/表端/表盘/留白/haps。实际源码HEAD仍de3e6f182c2def5a52d33f33684777f1fc941ccd；本地有白名单staging，旧未选scratch全保留。不要git add -A。

## 当前四产品SHA（必须复读live工作树）

- WearProbe.kt: 18a693e7a075d1d52a5cc639ff8df005025b18df85318e6dcfe3a321b1d2611c
- SyncEngine.kt: 8e0559a571e527e7f5b311cfd770d22c53398bff87fae4adda3a2605e1cce8af
- DiagnosticRuntime.kt: c82a665d3b06ca53b19c0f8c63eef369a2d4ea4f48c53c1e9e6936969f38a2d6
- P2pTrace.kt: 9ddb3b0787f8a931d1165793b3501e556e84672f62f43e8c15d54109b6d5dca8

## 原件和最终输入

root ~/elcton-phone-diagnostics-0210-20261115；branch diag/p2p-trace-0.2.10-20261115。

- R6-AUTHORIZATION-AND-PLAN.md（用户两裁决：12/0210纯字面；3SHA+P2pTrace身份数据）
- r6/reviews/input-q1/reviewed-manifest.json：41 inputs，SHA256 93a41045e9896bb419eade7c56cb38242b025cd73604ca9ae28abf2b33327a8d
- r6/reviews/r6-spec-q1.json + spec-q1-raw.txt：独立正式PASS；spec-q1-readback-continuation.json 31checks全部true；旧spec-r1 false/旧spec-r2 pass都保留
- r6/reviews/r6-quality-r1.json + quality-raw.txt：Q-R6-001真实拒绝，永不覆盖
- r6/FINAL-L3.json、r6/FINAL-WAKEUP.json：真实RED/GREEN与原件路径SHA
- r6/evidence/wakeup-red-20261115-1643、wakeup-green-20261115-1646、wakeup-final-20261115-1648；1642仅prereq3finally计数故障，非RED，原件保留
- r6/evidence/final-q1-complete-1658/receipt.json：当前全部HOST passed=true；实际full-jvm复用source72rows全匹配的final-q1-regression-1650 jar/171raw；前三helper失败目录保留归因（7想当然实际6、旧receipt键不存在、HTTP错入口）
- r6/evidence/frozen-scope-q1-1650/receipt.json：9461内容核/35behavior不改
- r6/evidence/identity-migration/table.json + identity-migration-q1/：旧→R5→最终新SHA；r6/current-identity.json为当前登记，旧qa/release-029/approved-release-delta.json冻结
- r6/evidence/q1-scope-output-only-proof/：恢复旧新scope辅助确切R2 SHA744b7a8...（旧out=QA / '...'，index已当前不可充旧输入）
- r6/PUBLISH-CANDIDATE.json：最后510文件/约9.8MB零PAT/privatekey/Bearer凭据扫描，仍可能需更新QUALITY新原件；publish脚本白名单不拿生成fake.kt/jar/keys
- 当前Docs唯一进度已更新，备份/storage/emulated/0/Documents/.backup/elcton-R6-progress-20261115-170617.md

## 下一棒唯一主链

1. 读上述精确原件，hash41input和4product live字节。没有漂移则不要再修代码/重跑2GB或171/133；先续最后独立QUALITY仅Q1增量，需真实r6-quality-q1.json + quality-q1-raw.txt，含input_manifest_sha256/inputs与空security/logic/missing才能通过。partial不算。
2. 真双审后：python -B qa/p2p-trace-0210/close_r6_reviews.py --manifest qa/p2p-trace-0210/r6/reviews/input-q1/reviewed-manifest.json --spec r6-spec-q1.json --spec-raw spec-q1-raw.txt --quality r6-quality-q1.json --quality-raw quality-q1-raw.txt；闭合写reviews/closure。
3. 更新prepare_r6_publish白名单纳入新QUALITY/closure/本断点等（commit_r6_reviewed.py当前新文件未列FIXED，纳入才入仓）；运行publish扫描、精确git add白名单(禁-A)与commit_r6_reviewed.py，必git show source:41path身份全核。只diag分支推，不动master/release/PR/Release。
4. 推后verify_r6_remote.py --sha SOURCE --manifest ...PUBLISH-CANDIDATE.json --out ...必须实际ref/treeblob/size读回。SHA本轮尚未产生，不要猜。
5. 原build.yml workflow_dispatch：pipeline.py dispatch-build --sha SOURCE --review ...reviews/closure --out ...ci/execution/build-dispatch；run_id真实registered再后台wait（notify），不盲重发。精确source/attempt/artifactID下载main/testAPK/XML，原153+new19严格172case注册/核，不混HOST171。
6. 真实apksigner稳定证书fc08a0b474a8ffca5887bd5c88ac15e865a63a64eca81c10f344496c46d9ad94、包com.hcbiu.elcton code12/name0210、source pin/Gradle/HTTP全部原门。
7. 原ui-smoke diagnostics注册先行后full同source/build；两个modeAPI33/three-button；原完整JSON/像素/assertions全核，不改UI行为或断言凑绿。均用云端不动用户设备；临时artifact注意约1GB可用，禁止删原件。
8. 两UI实际passed后finalize_r6_delivery.py凭真实3receipt+main APK验签/SHA，非覆盖落Documents/.../phone/ + DELIVERY（完整旧→新SHA）。此helper已写但未实际用，字段务必匹配真实原回执，如字段不符只修新helper不伪造。
9. 最终证据另commit [skip ci]，准确主包SOURCE仍用prodcommit；远端白名单readback、Docs进度与最终回复。

## 安全/声明红线

本轮允许仅R4观测计划+两迁移裁决；不动READY/SendAttempts/SDK callback/业务断言。表端445源码、表盘、留白、haps不碰；设备操作归发起方。所有原件/拒绝/失败只保留不删。凭据不得回显/入仓。HOST/ASM不能作Android或真机证明。诊断包不是握手修复，真机根因仍unknown。不发Release、不拿旧029当0210。
