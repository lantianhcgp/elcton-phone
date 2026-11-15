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

## R8 实际验收结果与交付补充

交付节点：2026-11-15 22:22；原交付器实际 exit=0。主 APK 8,253,700 字节，SHA256 与 R7 官方构建主 APK 完全一致；phone/ 原有 28 份文件逐字节未改。<sha8> 使用实际构建源前缀 b3eb5568，APK 摘要单独列明，不混淆两种身份。

构建 run 43715446826 / attempt 1：实际 Gradle XML 36 suites、172 unique testcase，精确等于旧 153＋新 19；失败 0、错误 0、跳过 0。旧测试标签一一保留，不以 HOST 171 或注册标签代替实际执行。主/测试 APK 均为稳定证书 fc08…ad94、v2 单 signer；测试 APK 不作为用户主包交付。

诊断 UI run 43718640929 / attempt 1：官方云端 success；原 verify_r6.py cloud 实际 exit=0，12 门 passed、errors=[]。API33 / three-button；版本 0.2.10、诊断長错误首尾、MCP 保活、通知等均由实际模拟器原图/完整 JSON/原像素门复验，328＋元数据输入全量前后字节相同。SYNTHETIC-BEGIN/END 和 210301031 只是注入夹具，不是真机故障根因。

完整 UI run 43720799962 / attempt 1：官方云端 success；原 verify_r6.py cloud 实际 exit=0，11 门 passed、errors=[]，935 原输入零复制/前后完整字节相同。原 tour 28、theme 23、palette 74 场景及键盘/系统栏逐值通过；API33 / three-button 确切绑定。完整 UI 使用 build_sha=b3eb5568…，工作流 HEAD=4fc3363f…，只读断点 HEAD 不是新的 APK 源。

视觉目检：28 product tour 全页面接触图与关键原组件放大由父执行；另 97 theme/palette 原场景全页面浏览，62 个配色场景有组件接触图放大，11 份原生裁图直接查看；父补看亮/暗日期错误、设备、今日、编辑共 8 份原组件裁图，并抽核六配色/系统栏。未确认所看可见组件有裁字/重叠；不把全图浏览冒称每场景每组件原生分辨率验收。滚动区外内容不作通过判断，主题键盘由系统控制，不外推 MIUI/Doze/真机握手。

辅助传输/交付接线：原 pipeline/common/verify/finalizer 字节保持；仅隔离 GET DNS 参数兜底、单 POST 禁跳转/精确 HTTP204 空 body 判据、5 处输出 metadata 行和新负测。真实网络失败/漏 previous-registration 的拒绝/302 及空白 body 反例全部保留。空白 204 判据一处收紧，原 24＋当前新 8＝32 项实跑零失败/错误/跳过；第一 6／30 记录与后计数说明不一致的 SPEC FAIL 不删除、不重写。

最终增量独立双审（不替代原产品 90 输入双审）：
- SPEC：r6/ci/r8/reviews/spec-r8-http-empty-count-q2.json，SHA256=5a12b5dc39d37a376e41d57b08fac92d08c2e49f36452de7d4f4b0d16d96da72；88 输入 live 零漂移。
- QUALITY：r6/ci/r8/reviews/quality-r8-http-empty-q2.json，SHA256=f13c4d967f53d50edd094041a4f7a788ed481b37f221daf874acfb7016eac58d；88 输入 live 零漂移。
- 父读回：r6/ci/r8/helper-final-dual-parent-readback.json；原产品评审闭合仍为 r6/reviews/closure-q3/。

关键验收回执 SHA256：
- build：abd21c42d4d080fca1965e65e1d12709d25cb2e6efe3909c0a5e38701ceab7c9
- full：96386ab327f331714850b94f53f3b6347b0e3d8de197d9f720f6443dbfbf6959
- 交付：r6/ci/r8/delivery-final/receipt.json，原门精确 APK/签名/manifest/源码身份/90 review 指纹已实跑。
- 文本/原图证据最终只推 diag/p2p-trace-0.2.10-20261115，所有原 artifact ZIP、超大运行日志本地保留并列 SHA 索引；不发 Release/PR，不上传主/测试 APK 或凭据。

红线状态：纯诊断观测；旧断言、9461/旧 35、表端 445 冻结；本轮未操作设备/装机/表端/表盘/留白/haps。真机握手底层根因仍 unknown。已出包，停止开发/云端派发，仅结束证据发布与读回。
