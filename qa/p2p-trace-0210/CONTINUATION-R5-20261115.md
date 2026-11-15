# R5 CONTINUATION — 手机纯观测诊断版未交付

## 当前结论与授权

2026-11-15用户已批按R4 PHONE-DIAGNOSTIC-PATCH-PLAN.md实施手机纯观测。写权限仅该方案，不改通信行为、超时/重试/指纹/过滤或旧断言。表端/表盘/留白冻结，/haps不碰，设备/装机/握手由发起方负责。

R5尚未完成：观测补丁已落盘及修R1，但独立SPEC r2拒绝L3-r2。version仍11/0.2.9，未出CI/APK，没有0.2.10验签/SHA256，不得拿旧包当新包。握手真机根因仍unknown。本文件是断点，不是继续写产品的授权。

## 唯一焦点：L3-r2，先补真实RED再修观测

- 合法READY接受后原sendAttempts.invalidate()已作废HELLO attempt。
- P2pTrace context仍保留该attempt。WearProbe.stale只对nativeGeneration及诊断context.matches，所以adapter迟到Task OK/FAIL和SendResult可能标stale=false。
- 同一failure进入engine，原sendAttempts.accepts(attempt)为false，engine观测却stale=true，原业务正确拒绝推进。
- 问题是诊断因果标签不一致，尚未发现由此改业务守卫，不能作为握手根因。
- r2实证：当前native-host jar真实private send→真实onMessage(READY)；adapter OK/FAIL stale=false，engine FAIL stale=true。HOST假SDK，非设备时序。完整见reviews/r5-spec-r2.json。
- 下一棒仅从原attempt生命周期/已有闭包同步诊断有效性；不改原READY/SendAttempts/SDK回调/业务行为。新增afterREADY adapter反例先红后绿，覆盖独立Task终态，不假定真实Task可成功又失败。

## 精确目录和源码

- 独立worktree：/data/data/com.termux/files/home/elcton-phone-diagnostics-0210-20261115
- branch：diag/p2p-trace-0.2.10-20261115；产品base/HEAD仍bb26c64b67e1cfa7903cd709c2aac482f6490e6b（证据提交不代表产品代码已提交）。
- 原目录：/data/data/com.termux/files/home/elcton-phone-release-029-20261114，原先dirty证据保留；以新worktree Git基线为准，不误报旧dirty为R5回归。
- 仅3旧产品源码有diff：WearProbe.kt、SyncEngine.kt、DiagnosticRuntime.kt；新增P2pTrace.kt。所有其他Git基线9461条目（含8历史symlink）不变。
- WearProbe SHA256：8858aa73e7c69e9b7d3cafbf19fe26c224300409536f8a921dca1e77bff8b7d1
- SyncEngine SHA256：f59966880018477c7bbab7768ca5e0b2bc5ad3e83594fc45e0ab7ff367ca63a2
- DiagnosticRuntime SHA256：e6e10f6ddb3f4cd620879509a28e61433139feddf84b90d783e34167ecfe2cc7
- P2pTrace SHA256：ba747e234bb4f61bb5ffb801a8abac6e5a4eba28014c7627febf4ad84c0c0bc8
- 精确可重建：evidence/final-source-snapshot-1351/tracked-product.diff + *.kt.source.txt。快照内两份P2pReady*是旧保护副本，不算新增；实际新增6测试+1产品文件。

## 实测与诚实门禁归因

- 表端原445/445、fail0/skip0；源码冻结，未新建HAP。
- 旧手机冻结0.2.9：JVM152/152、Python133/133重新执行绿，仅基线证据不是R5新源结果。
- 最终R5新源：JVM171/171（原152+新19；6个新增测试类，35全库存类），native HOST旧/新adapter oracle3/3，Runtime文件/socket/fault4/4，原HTTP/MCP3784断言最终重跑通过。
- 真实Huawei wearengine.jar/tasks.jar类型编译0；Android类型外壳仍HOST假边界，不是Android全编译/设备SDK执行/CI。
- SPEC r1拒绝原件、r2拒绝原件都保留；r2产品与发布均false，不启动QUALITY，不把测试绿当成审查绿。
- 原Python完整suite在R1时点133/4fail/skip0。最终第一次重跑129/4fail/skip1是缺MCP_HTTP_TEST_CLASSPATH导致4client方法缺席，原件保留，不能称全量；最终修环境重跑同旧断言/同jar，准确结果另见FINAL-RESULTS.json及evidence/final-original-python-full-1354。
- 新观测测试反射RED5、Engine RED5、锁/ingress RED2，R1修正语义RED5、native listener attach真RED1；失败原件不改。早期native missing OperationDeadline/null Void fake模型失败是夹具错误，不算目标RED。
- Runtime满quota/路径异常/坏snapshot测试立即GREEN，只是验证既有修正，不虚称测试先红。

## 版本/发布授权边界待决

用户目标已明确code12/name0.2.10，同签名fc08a0b474a8ffca5887bd5c88ac15e865a63a64eca81c10f344496c46d9ad94。
然而旧JVM文本断言、installed-version/UI门、verify_apk和source reversibility/工作流门固定11/0.2.9/原源码SHA。新观测+升级必触旧身份预期。两次clarify未收到选择：不改/skip旧断言、不塞假旧版本注释、不自迁门禁。
需要发起方明确：仅迁版本/获批源码身份期望并保留旧原件，还是旧身份门只对冻结0.2.9跑且新0.2.10完整门另行归因。业务断言一概不可改。

## 后续实际交付链（本轮未执行）

1. 仅修L3-r2→全量新测试和原业务oracle→独立SPEC PASS再QUALITY PASS。
2. 明确版本/源码身份门授权，versionCode12/versionName0.2.10，不改业务预期。
3. 精确CI head SHA/run/attempt/jobs/logs/artifact绑定，真实testDebugUnitTest+HTTP+instrumentation/UI完整门。
4. 稳定同证书签APK→真实apksigner verify全链→manifest版本→非覆盖下载到Documents指定phone目录→SHA256。
5. 用户装机；发起方在表周视图→同步→开始接收后MCP握手，拉fetch-logs --app elcton + error_tail/diag_read.p2p.events对时序。此Agent不操作设备。

## 保留/发布纪律

本轮GitHub只能证据[skip ci]隔离分支，产品未审过所以只发布diff/source.txt快照，不发布可执行产品commit、APK、Release、master或PR。
原jar/生成Kotlin/Runtime token全保留本地，不入公开仓。R5中间数据已打包并逐项哈希验证LOCAL archive（原件未删），archive不上传；公开清单必须白名单并扫描真实token/私钥。
Gradle test sourceSets递归qa，生成的*.kt和fake模板不能当正式sourceSet编译；模板保留.kt.in、原失败*.kt仅本地/归档，发证据.source.txt。
唯一Documents进度：/storage/emulated/0/Documents/elcton-WearEngine-真机联调-20261113-123000/进度.md。
