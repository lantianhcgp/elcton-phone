
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
