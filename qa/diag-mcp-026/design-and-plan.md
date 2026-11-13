# elcton-phone 0.2.6 诊断与只读 MCP 实现计划

Goal: 在不改变 Wear Engine 授权、扫描、传输行为和签名身份的前提下，取得原始异常消息/错误码/原因链并通过本机鉴权 MCP 查询。
Architecture: 沿用 lite-widget 的 ServerSocket + org.json JSON-RPC over HTTP 形态，但只绑定 IPv4 loopback、所有 RPC 强制鉴权、仅四个只读工具。纯 JVM 错误记录和 MCP 核心可在 Termux/CI 使用真实 Kotlin HTTP 服务自测，Android Application 只负责生命周期和 SDK 状态观测。
Tech Stack: 现有 Kotlin/Compose、Java 17、org.json、JUnit4、Python 标准库。无新增 App 依赖、SDK、云服务或前台保活服务。

## 已批准规格来源

本次用户简报“elcton-phone 0.2.6——错误可观测性 + MCP”。其中明确批准的测试边界为错误记录公开接口和 MCP HTTP/工具接口。版本 0.2.6 / code8；签名证书固定 fc08a0b474a8ffca5887bd5c88ac15e865a63a64eca81c10f344496c46d9ad94；只在 feat/diag-mcp-026 工作。

## 基线与读取

- 工程 CI 实际所在仓：lantianhcgp/elcton-phone（公开仓）。
- 0.2.5/code7 基线：18cd94ea1689c7e3d59a26afd4121cd2a665b4d7，成功 run 43381678300，workflow build.yml。
- 主工作树当前是 feat/ui-material-expressive / 6cd27de，.ai-memory/handoff.md 有预存改动，保持不变。
- 实现工作树：/data/data/com.termux/files/home/elcton-phone-diag-mcp-026。
- 已通读 WearProbe、MainActivity、UserFacingError、Manifest、build.yml、ui-smoke.yml、QA host runner、隐私/适配/签名配置测试及 README/project_memory。
- lite-widget 参照：McpServer.kt、McpService.kt、Prefs.kt、App.kt。只复用协议/工具形态，不复制其匿名/查询参数鉴权、宽松路径检查、0.0.0.0 监听或前台服务。

## 对外合同

1. ErrorJournal 使用 files/diagnostics/wear-errors.jsonl，最近128条，UTF-8 JSONL、原子替换、并发安全；长 message 不静默截断。WearErrorRecord 记录 epoch毫秒+ISO时间、阶段、异常全类名、完整 message、root/cause链及可用的 SDK errorCode；原因链循环终止并明确标记。
2. Log.w("ElctonWear", full) 与连接诊断共用完整格式。只有 SDK 异常进入此出口；课表校验和主页面仍用 UserFacingError 的有限提示，原有隐私门禁不弱化。
3. MCP POST /mcp 监听 127.0.0.1:8766；持久 token 首次启动由 SecureRandom 生成至 files/mcp/token，0600，不进入诊断/日志/fs_read。
4. initialize、ping、tools/list、tools/call 与 initialized notification 是最小兼容子集。所有调用要求 Authorization Bearer 头；拒绝匿名、URL token、大小写变换的 token；notifications 返回 HTTP202 空体。JSON-RPC 正确保留合法 id，非法请求/参数返回规范错误。
5. error_tail({limit:1..128})、diag_read({})、version_info({})、fs_read({path})，只读无 WE 调用。fs_read 精确白名单 diagnostics/wear-errors.jsonl 和 diagnostics/state.json，拒绝绝对路径/..、符号链接逃逸、目录、token、课表和 SharedPreferences，单文件上限256KiB，超量明确报错不截断。
6. HTTP 限制：有限连接线程与队列，header/body长度上限、socket超时、完整 Content-Length 验证，错误回包不回显 token/body/私人路径。
7. Application 中初始化观测/服务；不在 companion 构造期访问 Context。进程被系统杀死后需正常启动 App 才恢复，不自动抢前台、不增保活服务。
8. diag_read 返回经白名单的状态、阶段/时间、最新错误及 MCP 运行状态；不读取/发送课表、不枚举或连接 WE。

## 实现切片（RED → GREEN）

### 1. 完整错误与环形文件
Create: WearErrorRecord.kt、ErrorJournal.kt、ErrorJournalTest.kt。
先写一个公开边界反射测试并真实执行，确认缺接口而失败；实现后执行真实 Kotlin/JUnit。逐一补长消息、null、多层cause、cause循环、errorCode、128条淘汰、重启读回、JSONL转义和并发 append 场景，每条先红再绿。测试依赖沿用现成 host-deps，无 Android SDK 假实现。

公开接口：WearErrorRecord.capture(error:Throwable, phase:String, timestampMs:Long, errorCode:(Throwable)->Int? = {null})；record.full、record.toJson()；ErrorJournal(file:File,maxRecords:Int=128).append(record)、tail(limit:Int=20):JSONArray、latestFull():String。

### 2. 鉴权只读 HTTP MCP
Create: McpToken.kt、DiagnosticTools.kt、DiagnosticMcpServer.kt、对应 *Test.kt、qa/McpHost.kt、qa/mcp_http_selftest.py。
先红后绿验证真实 ServerSocket HTTP；测试工具集、身份和鉴权、合法/非法JSON-RPC、分包读取、多字节Content-Length、参数类型、路径边界/符号链接、token持久化/权限、通知202、server停止资源关闭。

公开接口：DiagnosticTools(filesDir:File,errorTail:(Int)->JSONArray,diagRead:()->JSONObject,versionInfo:()->JSONObject)；DiagnosticMcpServer(token:String,tools:DiagnosticTools,port:Int=8766).start():Int、stop()、running:Boolean、boundPort:Int；McpToken.loadOrCreate(file:File):String。
真实 host selftest 必须启动上述 Kotlin 生产服务，Python 只作客户端，严禁用 Python 假服务器替代生产代码。

### 3. Android 观测与版本
Create: DiagnosticRuntime.kt、ElctonApplication.kt、DiagnosticsIntegrationTest.kt、DiagnosticsUiTest.kt。
Modify: WearProbe.kt 的 publish/describe 观测出口及阶段参数（其余业务逻辑字节级保持）；MainActivity.kt 的可滚动完整诊断与 BuildConfig 胶囊；Manifest 仅 Application name；build.gradle.kts 仅 BuildConfig/版本。
先执行源码范围测试证明旧出口/版本/无App启动服务缺失；实现后核对diff及既有隐私门禁。捕获日志文件写失败时不影响原 fail 行为，fallback仍写完整logcat。

### 4. CI 门禁
Modify: qa/run_host_tests.py 加纯 JVM 新模块和真实 McpHost；build.yml 加真实 HTTP 自测步骤/证据artifact，稳定签名步骤保持原样。
Create: diag-mcp-smoke.yml，独立模拟器仅测试此功能，安装精确 signed artifact，仪器/HTTP读取与版本/可滚动诊断验证，无真实手机前台操作。
Run: python -B qa/run_host_tests.py --deps <existing host-deps> --out <private evidence>；python -B qa/mcp_http_selftest.py --classpath <actual jar+json>；既有全部 Python QA tests；CI testDebugUnitTest/assembleDebug/assembleDebugAndroidTest；模拟器专用 smoke。

### 5. 审查与交付
以 18cd94e 为固定比较点，分别作规格/标准审查，读回新提交和精确 CI run。下载 artifact，校验 GitHub digest/source-sha、ZIP CRC、version/code、apksigner签名、固定证书。签名私钥不出CI。
新APK不覆盖旧文件：/storage/emulated/0/Documents/elcton-WearEngine-真机联调-20261113-123000/phone/hc课程表-0.2.6-code8-<sourceSha前8>-signed.apk；写 SHA256 附件。
先且只试 adb install -r；INSTALL_FAILED_USER_RESTRICTED 立即停止安装尝试，给路径；不卸载/清数据/改安全设置。若安装成功读回 package+安装实物hash；forward/只读查询不启动Activity。无进程无法读MCP时如实注明，不绕过用户不抢前台红线。
证据/报告提交 qa/diag-mcp-026，原始个人日志、真实token和构建缓存只在git排除目录。最终回复包含包+SHA、CI run、实际测数、HTTP结果和 forward 示例，不把环境诊断版当WE根因修复或通信成功。
