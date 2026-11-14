# 0.2.9 测试期望重定位（逐项归因，不是历史PASS冒充现行PASS）

依据：用户简报明确 0.2.9/code11、保活默认开、从Activity抽取唯一共享业务，并允许合并冲突自行裁决。两次clarify均超时且工具要求采用最佳判断；本文件不把超时称为用户点选或新增授权。只对直接矛盾的版本/默认值/所在文件进行归因，安全和协议谓词仍完整。

原件：e034de2(fix/p2p-ready-receipt-20261114)、1e14980(feat/diag-mcp-027)、`evidence/original-tests/relocations.json` 的73项SHA。原字节不改；`.original`后缀只防Gradle重复编译历史类。所有RED保留，包括merge-host-initial后Python失败和current-full-before-alignment。

## JVM
- DiagnosticsIntegrationTest.versionCapsuleUsesRealInstalledBuildVersion：0.2.7/9 → 0.2.9/11，仍测试当前Gradle源及BuildConfig胶囊。
- DiagnosticsIntegrationTest.sdkErrorOutletPreservesRawAndPersistsStructuredRecord：SDK outlet仍在WearProbe，只匹配等价导入Log与新的it/error变量和空格；phase/code/message/持久化/原始message/诊断异常隔离的每项断言不删。
- DiagnosticsIntegrationTest.appLifecycleAndLocalServiceAreExplicitAndNotExported：无首次Application裸监听而由FGS晋升后绑定；默认值false→缺省true（显式false保留），并保留非导出/specialUse/无WakeLock/无manifest启动接收器/ResumeChoice/Settings断言。
- P2pCandidateBuildTest.actualGeneratedBuildConfigIsBoundToExplicitBuildProfile：原0.2.8/code10当前构建等值期望与明确0.2.9/code11冲突；续跑保留原件和version-binding-red，只将READY=true分支两项等值期望迁移为11/0.2.9，APPLICATION_ID及READY=false 8/0.2.6分支完全不动。真实GeneratedBuildConfig测试必须由Android Gradle执行，源码核对不算通过。
- test_mcp_clients四个原测试、每个断言及EOF归因不改。夹具新增严格--release-tools参数，使用原DiagnosticTools+生产PhoneMcpTools组合的真实15项list/validation；没有参数仍原4工具不变，并由原HTTP3784断言继续测试。仅测试启动输入多该参数，HTTP谓词不改，动作提供器明确失败不伪造Android执行。首4例2失败日志保留resume-1720/http-clients/0.log，前件逐字保留harness-migration/before。

## Python/源码门
- test_diag_source_gate：原字节逆向门仍要求唯一完整批准delta且逆向返回0.2.5基线；新增0.2.9完整发布源SHA，由独立审查确认后才能固化。业务回调/生命周期/权限/207/诊断错误outlet/胶囊等负例仍必须使门红。
- test_diag_source_gate.scan/cancel：原UI probe调用迁移到phone.scan/phone.disconnect，不允许交换；displayWeek/产品UI不随迁移改变。
- test_diag_source_gate.SDK auth判定与P2p成功码：相应权限判断迁移到SyncEngine，code!=207迁移为code==207 ? success : failure，两向错误变异仍须拒绝。不取消任何判定。
- test_p2p_ready_source_gate：prepared ERROR、READY超时文案移到SyncEngine；注册/授权/包名在适配器或引擎对应位置。相同缺失/重复/真值/207→206/包名变异全部拒绝。
- test_mcp027_scope：0.2.7/9→0.2.9/11；不能再要求已授权抽取的WearProbe整文件不变。改为精确冻结全部未授权协议/WE配置/主题/签名shell段，另以完整批准delta核WearProbe。构建workflow仅增加发布分支和新版二进制检查器，稳定签名段逐字不变。
- 原Theme/Palette与其像素门：不改，其调用共享源门自动增加现行release delta。
- test_keepalive_gate和McpKeepAliveTest：默认关→默认开；权限拒绝仍fail-closed关闭监听/服务，但不能当作用户关闭偏好。停止/在途socket/绑定失败/后台通知丢失/持久化数据/权限/事件顺序断言完整；新增STOP回执与迟到启动拒绝。

## 数量与层级
现行JVM全量（含新工具）与Android Gradle全量实际数量从JUnit/XML解析，不推定“89+N”。Python的原环境/证据缺件skip按其原规则原样保留并单列，不宣称零skip。HOST JVM/真实Android模拟器/物理手机分层；前两者不证明蓝牙或MIUI十分钟保活。真机由用户验收，pending。
