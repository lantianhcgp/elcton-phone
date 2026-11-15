# R5 手机纯观测诊断版 Implementation Plan

Goal: 实施用户已批R4诊断方案，只观测；交付code12/name0.2.10、同签名fc08a0b474a8ffca5887bd5c88ac15e865a63a64eca81c10f344496c46d9ad94的精确CI APK。真机归发起方，无任何设备操作。
Architecture: 单个P2pTrace只拥有诊断状态，以diag_read.p2p追加有界事件；保留原4/15 MCP schema。WearProbe原native入口与SyncEngine原业务判定分别观察，关联现有generation/attempt，但它们数值不假定相同。JSON/字段读取/写入失败在diagnostic-only try/catch隔离；沿原DiagnosticRuntime单线程writer，无新服务/定时器。
Tech Stack: 现有Kotlin/JVM17、Android34、WearEngine5.0.3.301、JUnit4、org.json；不加依赖。

## 前置门
- 方案只读：/data/data/com.termux/files/home/we-handshake-repair-20261115-watch/qa/we-handshake-20261115/research/r4/PHONE-DIAGNOSTIC-PATCH-PLAN.md，R4原件不改。
- 手机独立worktree ~/elcton-phone-diagnostics-0210-20261115，base bb26c64b67e1cfa7903cd709c2aac482f6490e6b；原0.2.9目录只读。
- baseline.json保护9447文件/35旧测试/114表端文件。/haps零操作，不启动MCP/ADB/rish或Chromium。
- 版本门禁冲突单独未闭合：旧DiagnosticsIntegrationTest两条期待11/0.2.9；用户禁止改旧断言。clarify未回复，不擅改、不skip、不注释旧版本凑绿。先保留版本11/0.2.9做观测TDD与全量，随后版本冲突另裁决。

## 1. 事件写入器 RED→GREEN
Create app/src/test/java/com/hcbiu/elcton/P2pTraceTest.kt，用反射令缺实现成为断言失败而非编译错误。覆盖schema1、origin=host-test、sid/seq/wallMs/elapsedMs、关联字段、限128条/2048B、dropped、序号/分页真实性、匿名ID、敏感字段不落、异常clock/serializer/writer不影响业务、满配额trace_storage_full不自动清理。
运行真实kotlinc+JUnit，保存RED原输出及退出码；之后Create app/src/main/java/com/hcbiu/elcton/P2pTrace.kt最小实现。不得加入业务回调封装或SDK调用。

## 2. 引擎与适配器观测 RED→GREEN
Create P2pTraceEngineTest/P2pTraceAdapterTest等新增文件；旧SyncEngine五参constructor保留，fake transport/clock与未打点oracle业务返回、SDK参数/次数/顺序、守卫逐项一致。
Modify仅WearProbe.kt/SyncEngine.kt/DiagnosticRuntime.kt；必要诊断内部辅助只放P2pTrace.kt。不改PacketIngress/SendAttempts/Wire等保护文件。
必须覆盖：CONNECT_REQUEST、PEER_CONFIG；REG_CALL/TASK_OK/TASK_FAIL；SEND_CALL/TASK_OK/TASK_FAIL/RESULT（分层，不将Task成功当207）；RX_NATIVE_ENTRY在原generation/type/data过滤前且不新增Message getter读取；原读取结果一次捕获供观察；RX_ADAPTER_REJECT/RX_DECODE；RX_ENGINE_ENTRY/PROTOCOL_ACCEPT/REJECT；READY_ACCEPT只在原合法路径；INSTALL_TIMEOUT/REG_TIMEOUT、HELLO_RETRY约5秒×3、READY_TIMEOUT约20秒、CLOSE/CANCEL/FAIL及清理原因、UNREG_CALL/TASK_OK/FAIL。捕获作废前代次和cause，注销后果不伪作原因。
clock覆盖t0/5/10/15 HELLO、t20耗尽以及更早sendFail/取消；迟到/重复回调、旧generation、非法sender/version/超大/非ASCII、字段异常。新listener只观测；不包裹原业务回调。

## 3. 诊断存储与兼容
DiagnosticRuntime追加有界p2p对象/event尾部；旧字段不删改，error_tail仅旧错误，工具列表/权限/确认完全不变。磁盘使用原writer；新追加流水有明确配额，不删数据，只报告新增停止。读回算实际buffer/dropped/has_more，不虚报全量。

## 4. 完整回归与双审
旧表测试命令node --test --test-reporter=tap tests/*.test.mjs，必须445/445、fail0、skipped0；只读执行不改文件。
手机保留原JUnit152、原AndroidGradle153及原Python133/HTTP/MCP/UI门禁全部；新增测试单独统计。精确命令按CI-BASELINE-NOTES.md真实路径。父独立SPEC→QUALITY，每轴哈希绑定当前源码/新测试/RED/GREEN；拒绝原件保留，冻结输入后不覆盖回执。

## 5. 版本与精确CI
用户版本code12/name0.2.10。同证书，权限/依赖不变。保留qa/release-029/verify_apk.py原断言，为新版本新建版本检查器；若旧测试版本断言仍冲突，不宣称全绿，写准确断点。
新增或最小workflow只替换本轮版本验证入口，原gradle/HTTP/signing/完整诊断+fullUI命令/断言不删减。按SHA找run、attempt、唯一artifact ID，保留失败。UI输入build_run/build_sha钉本轮APK，diagnostics/full两套原门禁全走，均不操作真机。

## 6. 交付与读回
APK唯一新增名：hc课程表-0.2.10-code12-<sha7>-P2P观测诊断-signed.apk；路径=/storage/emulated/0/Documents/elcton-WearEngine-真机联调-20261113-123000/phone/。不得覆盖旧包，使用exclusive-create并核sha；实际apksigner verify、二进制版本/事件/diag接口/签名同链，SHA256报告。
工作证据仅qa/p2p-trace-0210推GitHub并精确读回，Documents仅唯一进度+交付APK。未完成时写CONTINUATION-R5-*.md，不冒充修复/真机通过。
