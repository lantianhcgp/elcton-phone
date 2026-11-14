# HTTP framing 定位与最小修复（0.2.7 候选，非 Android 完成验收）

## 结论与置信度

- 已确认的 selftest 缺陷（高置信）：原 `Suite.request()` 对完整 Content-Length HTTP 请求一律调用 `shutdown(SHUT_WR)`；普通 HTTP 请求不需要写 EOF。对“客户端 EOF 即关闭整个转发连接”的**明确 synthetic TCP 夹具**，原请求收到空字节并报 `HTTP framing`，只改普通请求为不 half-close 后同一个生产 0.2.6 jar 正常响应。
- 原 Android run 43535414635 的真实根因仍未确认：旧日志只有 `HTTP framing`，没有字节数/TCP 轨迹；报告记载内部 Socket 四工具通过、normal-app urllib health ready。与 half-close 转发策略假设相符，但本次没有运行 adb、Android 模拟器或真机，**不能声称已证实 adb 的 EOF 实现，或已修复 Android 外部验收**。
- 服务端源码只按字节 Content-Length 读请求，响应 `Content-Length = UTF-8 bytes.size`；未找到依赖客户端 EOF 的产品缺陷。`DiagnosticMcpServer.kt`、`DiagnosticMcpServerTest.kt` 均未修改。
- 父会话的真机 connect timeout 属独立可达性问题，不纳入本 JVM HTTP 结论。

## 仅本子任务的文件变更

- 修改 `qa/mcp_http_selftest.py`：普通 HTTP 请求与非 EOF framing 用例不 half-close；强制运行真实 urllib/curl；公共响应校验仍检查 UTF-8 字节长度、Connection close、重复响应头、token 不回显。
- 创建 `qa/test_mcp_clients.py`：启动真实生产 Kotlin host（真实 org.json），direct with/without EOF 对照、完整 POST 经过 synthetic EOF-closing relay、direct URL 的 curl/urllib、relay URL 明确 transport 分组报告，共四项。
- 证据写入本目录 `http-*`；编译临时产物在仓内 `.diag-build/http-027/`。未触碰真机/adb、AGC、CI、git 提交推送、业务/运行时文件或 Documents。

## RED → GREEN 真实执行

依赖：

- 旧 jar：`/data/data/com.termux/files/home/elcton-phone-diag-mcp-026/.diag-build/final-host-026/host-tests.jar`
- 真实 Android API33 org.json 子集：同级 `android-json-api33.jar`（在 JVM 上运行，不等于 Android Runtime）
- 当前源码编译：server/tools/token + `qa/McpHost.kt` + 原 server JUnit；真实 JUnit/hamcrest 来自 `~/erbian/core/lib/`。

命令（完整展开命令在各日志中）：

```sh
python -B qa/test_mcp_clients.py --classpath <真实host.jar:真实json.jar>
python -B qa/mcp_http_selftest.py --classpath <真实host.jar:真实json.jar>
java -Xmx256m -cp <当前host.jar:真实json.jar:junit.jar:hamcrest.jar> org.junit.runner.JUnitCore com.hcbiu.elcton.DiagnosticMcpServerTest
python -B -m unittest discover -s qa -p test_mcp_http_selftest.py -v
```

| 真实执行 | 结果 | 证据 |
| --- | --- | --- |
| 原 0.2.6 jar + 原 selftest，direct JVM host | PASS，1,164 assertions | `http-baseline-026-direct.log` |
| 新测试 + 修复前 selftest | RED，3 tests 中 2 fail：relay framing、未强制 curl/urllib | `http-red-clients.log` |
| 当前源码真实 Kotlin 编译 | exit 0；Jansi Termux 原生库警告不阻断编译 | `http-current-compile.log` |
| 原服务端 JUnit，当前源码 + 真实 Android JSON on JVM | PASS，14 tests | `http-current-junit.log` |
| 更新 selftest，当前源码真实 host | PASS，3,784 assertions，urllib/curl 均执行，EOF supported，全部 raw checks 通过 | `http-green-current-selftest.log` |
| 新客户端/relay 回归，当前源码 host | PASS，4 tests | `http-green-current-clients.log` |
| 原 shutdown race Python 回归（保留原文件） | PASS，6 tests | `http-green-existing-python-final.log` |
| `--url` 指向真实本机 JVM host | PASS，3,649 assertions，EOF supported，全部 raw checks 通过 | `http-url-transport-reports.json` |
| `--url` 经 synthetic EOF-closing relay | 普通客户端与其余 framing PASS，3,637 assertions；明确 EOF unsupported，`all_raw_checks_passed=false` | `http-url-transport-reports.json` |

断言数增加源于真实客户端重复验证与严格响应头检查，不把数字视为新增业务测试数。

## 不放宽验收

- urllib 与 curl 都真实 POST `/mcp`，多字节中文/emoji id 来回保持，Content-Length 按 UTF-8 bytes 验证。
- 两客户端均检查四只读工具列表、实际四工具请求、所有 MCP 操作及四工具的无 token/错误 scheme/错误或不同大小写 token 均 401；scheme 大小写不敏感保持原行为。
- 负数/非数字/重复 Content-Length、Transfer-Encoding、重复认证头、折叠头、缺失长度、超大 body/header、非法 UTF-8、partial body 有限 408 全保留。
- 只有检测出“健康对照不 half-close 成功，写 EOF 空响应/零字节 reset，再次普通对照成功”的 URL transport，会明确列出唯一被排除项 `Truncated body rejected (requires client write EOF)`。它不是 PASS；相同断言仍由 direct production-host selftest 和原 JUnit 验证 400。已有字节的截断/非法 framing/reset 不会被 capability 分组吞掉。
- curl credential 仅经 stdin config，禁 verbose/redirect/proxy，所有证据 token REDACTED。
- host `stop` 回执、进程退出及 listener 关闭均实测验证；最后 `/proc` 核查 `qa.McpHostKt` PID 残留为零，见 `http-host-cleanup.json`。

## 父会话仍需执行

对精确 0.2.7/code9 APK 重跑 Android CI 外部 `/mcp` curl/urllib（脚本现为硬标准），记录 `write_eof_transport`；如果 forward EOF unsupported，不能将 EOF 专项宣称通过。真机后台/前台可达性、keepalive 修改由父会话单独验证。本报告没有替代这些 Android 验收。
