# DELIVERY-R8 — 0.2.10 诊断版实际交付

版本：12 / 0.2.10；包名 com.hcbiu.elcton。仅诊断观测，不声称真机握手已修复；根因仍 unknown。
不发 Release；未安装、未操作用户设备；表端/表盘/留白/haps未动。

APK：/storage/emulated/0/Documents/elcton-WearEngine-真机联调-20261113-123000/phone/hc课程表-0.2.10-code12-b3eb5568-诊断版-signed.apk
字节数：8253700
SHA256：6a5dd165136f4928c4d172cacd32b5b541fec1784b2de08d23b72db57609969d
源码提交：b3eb55680b51f5fbdf392d402acdcdae168f2b20
同签名证书 SHA256：fc08a0b474a8ffca5887bd5c88ac15e865a63a64eca81c10f344496c46d9ad94
真实 apksigner v2=true，signers=1。

## 身份迁移（完整旧→最终新SHA）

WearProbe.kt
旧：15eb45798a6cb4536500b5aebc30715a2c7ee3190fff79175cab0c23eabe8b8a
R5：8858aa73e7c69e9b7d3cafbf19fe26c224300409536f8a921dca1e77bff8b7d1
Q2：18a693e7a075d1d52a5cc639ff8df005025b18df85318e6dcfe3a321b1d2611c
最终（仅编译分隔空格）：18a693e7a075d1d52a5cc639ff8df005025b18df85318e6dcfe3a321b1d2611c

SyncEngine.kt
旧：84176876bb297cecfaa8070362bbc0d72b0b99c095557919ba12c9978d26f4e7
R5：f59966880018477c7bbab7768ca5e0b2bc5ad3e83594fc45e0ab7ff367ca63a2
Q2：8e0559a571e527e7f5b311cfd770d22c53398bff87fae4adda3a2605e1cce8af
最终（仅编译分隔空格）：84533ebc792f0c108c79f043698a20ec89018a9dba19dbb606ae1bc6d3cc4e1a

DiagnosticRuntime.kt
旧：270a35fb2c47fddd4466ea2847bc3d06aef44202eca350342f6077680ae6eb64
R5：e6e10f6ddb3f4cd620879509a28e61433139feddf84b90d783e34167ecfe2cc7
Q2：c82a665d3b06ca53b19c0f8c63eef369a2d4ea4f48c53c1e9e6936969f38a2d6
最终（仅编译分隔空格）：c82a665d3b06ca53b19c0f8c63eef369a2d4ea4f48c53c1e9e6936969f38a2d6

P2pTrace.kt
旧：新增，无旧SHA
R5：ba747e234bb4f61bb5ffb801a8abac6e5a4eba28014c7627febf4ad84c0c0bc8
Q2：9ddb3b0787f8a931d1165793b3501e556e84672f62f43e8c15d54109b6d5dca8
最终（仅编译分隔空格）：9ffa02c51407301d8c308257609feea1961897076758f6da5ffe5ce53949f084

版本字面：11 / 0.2.9 → 12 / 0.2.10；行为断言零改。

## CI 与评审链索引

build：https://github.com/lantianhcgp/elcton-phone/actions/runs/43715446826
diagnostics：https://github.com/lantianhcgp/elcton-phone/actions/runs/43718640929
full：https://github.com/lantianhcgp/elcton-phone/actions/runs/43720799962
当前真双审 manifest：d4b04ff2789bc67ca17a14a73f5550290f0cef66f881340976196997c0400624
spec：qa/p2p-trace-0210/r6/reviews/r7-spec-q3-continuation.json SHA256=17558e0101a1401c451a75a200db7a46ef1bc0da9b21e6ec4776394a02879016
quality：qa/p2p-trace-0210/r6/reviews/r7-quality-q3-continuation.json SHA256=378d7c45b2b497660f2b14641265700123a7267eb52165d804839efd38f27b98
历史链：r6-spec-r1 FAIL → r6-spec-r2 PASS → r6-quality-r1 FAIL(Q-R6-001) → r6-spec-q1 PASS → r6-quality-q1 FAIL(helper) → Q2双审PASS → Kotlin1.9.24编译失败 → 当前Q3纯空格增量双审（全部原件保留）。

## 真实执行证据

HOST：JVM171、Python133零skip、HTTP3784、原表445源冻结；L3 afterREADY真RED→GREEN。
Q-R6-001：真实HOST barrier RED→GREEN，原失败/quota/stop race与原断言保持。
Android/云端构建、UI、实际 artifact/run_attempt 和完整精确 testcase/pixel 原门禁均以以下JSON为依据，非HOST替代。

构建回执：/data/data/com.termux/files/home/elcton-phone-diagnostics-0210-20261115/qa/p2p-trace-0210/r6/ci/r8/build-verification/receipt.json
诊断UI回执：/data/data/com.termux/files/home/elcton-phone-diagnostics-0210-20261115/qa/p2p-trace-0210/r6/ci/r8/diagnostics-verification/receipt.json
完整UI回执：/data/data/com.termux/files/home/elcton-phone-diagnostics-0210-20261115/qa/p2p-trace-0210/r6/ci/r8/full-verification/receipt.json
交付JSON：/data/data/com.termux/files/home/elcton-phone-diagnostics-0210-20261115/qa/p2p-trace-0210/r6/ci/r8/delivery-final/receipt.json

旧029包未覆盖；所有RED和拒绝原件保留。请发起方自行装机/真机取流水，设备验收未由本轮执行。
