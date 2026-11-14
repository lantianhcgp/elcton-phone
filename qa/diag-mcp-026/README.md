# 0.2.6 / code 8 诊断与 MCP 使用说明

本版本把 Wear Engine SDK 的完整原始异常（message、errorCode、cause 链和 UTC 时间戳）从 `WearProbe.describe` 记录到 `ElctonWear` logcat 及应用私有 `files/diagnostics/wear-errors.jsonl`（最近 128 条完整 JSONL）。连接诊断支持选择文本和纵向滚动；主页面的简短友好提示保持原规则。版本胶囊使用 `BuildConfig.VERSION_NAME`。

只读 MCP 是进程内 HTTP JSON-RPC，绑定 `127.0.0.1:8766`，不暴露 LAN、不启动前台服务、不会自主授权/扫描/传输。App 进程结束后端口关闭。令牌第一次进程启动时生成，私有 `files/mcp/token`，0600；保留安装数据的升级继续复用令牌。令牌不在日志、HTTP 返回或仓库证据中回显。

## 四个工具

- `error_tail`：`{"limit":20}`，范围 1..128，返回 `errors` 数组；各项完整原 message/cause/full。
- `diag_read`：不带参数，当前被动观察状态、最后错误及 MCP 启动状态；不额外调用 WE。
- `version_info`：不带参数，实际构建版本、包名、SDK 版本。
- `fs_read`：`{"path":"diagnostics/state.json"}` 或 `{"path":"diagnostics/wear-errors.jsonl"}`。只有这两个应用私有白名单文件允许读取，绝对路径、遍历、token、课表、符号链接及写入/删除不允许。单文件读取上限 256 KiB，超限明确报错，完整错误另可通过 `error_tail` 获取。

JSON-RPC `POST /mcp`，`Authorization: Bearer <实际私有令牌>`；握手、工具发现、工具调用均鉴权。`GET /health` 仅返回固定 `{"ok":true}`，不含版本、状态或令牌。回复携带 JSON-RPC id；非法 JSON/参数、非法 id、重复头、过大/超时请求和未知方法明确拒绝。通知不触发工具读取。

## 本机 / ADB 只读自测

前提：安装本版本，且 App 进程已经运行。`run-as` 只对本次稳定签名的 debuggable 联调包可用。

    export ANDROID_SERIAL=127.0.0.1:43111
    adb forward tcp:8766 tcp:8766
    python -B qa/mcp_http_selftest.py --url http://127.0.0.1:8766 --adb-token com.hcbiu.elcton --adb-token-path files/mcp/token --adb-serial "$ANDROID_SERIAL"

自测脚本通过 `adb exec-out run-as` 在内存读取 token，不保存 token 到 Documents、不打印请求/响应敏感字节。`--url` 模式只做 HTTP/工具边界检查，不写日志、不注入合成错误、不停止 App。不主动把真机 UI 拉到前台。若进程未运行，本次探测会明确记录不可达；不能把 loopback forward 创建成功当成 MCP 可达。

## 构建和验证

仓库实际 CI 来源是 `lantianhcgp/elcton-phone`，0.2.5 基线 `18cd94ea1689c7e3d59a26afd4121cd2a665b4d7` / run `43381678300`。本工作只在 `feat/diag-mcp-026`，不合并 master。

- `qa/run_host_tests.py --deps <真实JVM依赖目录> --out <日志目录>`：运行真实非 Android Kotlin/JUnit，不仿造 WE SDK。
- `qa/mcp_http_selftest.py --classpath <真实已编译Kotlin+JSON classpath>`：启动生产 Kotlin HTTP 服务，不使用 Python 假服务。
- `python -B -m unittest discover -s qa -p 'test_*.py' -v`：保留既有 Python QA；精确逆向审定的观测增量后，Activity/WearProbe 必须逐字恢复到固定 0.2.5 基线，额外业务改变和缺失错误出口均拒。
- CI `testDebugUnitTest assembleDebug assembleDebugAndroidTest` 及真实 Gradle Test classpath HTTP 自测。
- CI 模拟器 `DiagnosticsUiTest`：实际 Android 版本胶囊、完整合成错误、Activity 重建、诊断头尾滚动和关闭按钮、私有令牌 mode、真实 NIO/HTTP 白名单读取；所有注入数据标记 `SYNTHETIC`，不冒充 WE 或 FIT3 实测。

生产签名步骤与基线保持逐字一致；最终产物还必须独立验签、核对 APK SHA256、准确的 source-sha 和包内 versionName/versionCode 后再交付。固定签名 SHA256：`fc08a0b474a8ffca5887bd5c88ac15e865a63a64eca81c10f344496c46d9ad94`。

## 结论边界

本版本解决“错误被套话吞掉”和只读自探通道，不宣称已经修复 Wear Engine 授权拒绝、HMS 兼容性或真实蓝牙传输。根因须读取本机新版本真实错误记录后继续判断。证据在仓内 `qa/diag-mcp-026/` 和关联 CI artifacts；旧包、旧测试、失败记录保留。
