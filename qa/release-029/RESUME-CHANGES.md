# 0.2.9 续跑修正与绑定说明

- 最新用户简报：按断点继续最终回归/精确绑定/CI/验签/交付，不修改测试凑绿、删证据、换签名或碰真机/表端。
- 读取断点后实跑全量 Python：96例，4失败、历史1skip。失败均为候选清单仍停在 R1修复前：MainActivity补Build import，PhoneActions导入revision保护，PhoneRuntime队列撤销，SyncEngine陈旧注册清理未进入旧候选；不是授权后安全谓词应被放宽。原96例日志保留 resume-1720/python-before-rebind.log。
- R2的实际 McpKeepAlive 两处变更已核：bind失败与启动异常从disable改suspendSession，偏好不写false、真实监听/服务/通知关闭；R2原spec回执passed=false及standards旧manifest绿均保留，不作为最终审查。
- 新发现的UI矛盾：已有AndroidTest明确断言通知拒绝/端口失败后开关IsOn，但产品用enabledChoice && active，因此正在启动/被拒绝时显示Off。添加现行独立反例10例中的1失败；保持原Android测试不变，仅把开关渲染改为enabledChoice，服务active/failure独立显示。新反例RED：switch-intent-red/junit.log。
- 新增源码测试的文件定位沿已有DiagnosticsIntegrationTest同一root()父链，兼容Gradle在app目录运行；不改断言或skip。
- 原候选approved-release-delta.json先逐字保存candidate-before再刷新；before文本仍固定两支git原物，immutable源码须与HEAD_PIN原SHA相同。只重新记录完整after与新代码守卫，状态仍candidate_pending_independent_review，independent_approvals=[]。门禁源码和原负例不改。
- 最终独立回执要同时绑定全部产品/测试/QA/workflow候选清单和完整current.diff（包含未跟踪新增文件）。候选身份绿不代替审查绿；模拟器/JVM不代替真机。
- 续跑补跑classpath客户端发现4例2失败：原4工具McpHost被URL15项严格检查拒绝。保留首失败日志和三个原测试/夹具逐字快照，仅加入严格release-tools输入选择，既有4工具host无参行为及HTTP3784断言不变。版本构建测试等值10/0.2.8→明确11/0.2.9，原非READY分支不动；完整归因见TEST-ATTRIBUTION.md。不存在测试删除、断言放宽或把源码版本判断当AndroidPASS。
- R3双轴原始回执分别保存，产品候选与后续QA迁移清单不可混用；R4须独立审阅完整最新输入，产品37文件SHA若无漂移须逐项证明。
- 首次真实Android CI 43582496281在compileDebugKotlin拒绝MainActivity权限回调签名Array<out String>，父类要求Array<String>；完整原失败日志/before已保留。仅去override参数out方差，回调内容、权限处理、全部测试、SDK/签名不动。R5完整重新绑定、独立双轴增量核验，必须以新SHA真实Android CI过为准。
- R5实际build43583832086绿、Gradle153/153、APK真实版本签名正确；Android诊断43584056185在recreate后找不到diagnostic入口：UI抽取漏了原e034de2 onCreate恢复持久化latestFull到probeState.diagnostic那句。R6仅在观察者copy补空diagnostic，engine不动/原所有测试不改。原完整UI43584098560同首帧NoCompose失败，无fatal，原套件保持逐字相同，独立以实际日志调查并原样重跑，不能猜产品crash。R6/root及首RED全部保留。

