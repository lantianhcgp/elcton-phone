# 保活实现与旧 STOP200 归因

## 已完成的本棒范围

- 仅修改 `app/src/main/java/com/hcbiu/elcton/McpKeepAlive.kt`；新增 `McpKeepAlivePolicy.kt`、`app/src/test/java/com/hcbiu/elcton/McpKeepAlivePolicyTest.kt`，本目录为新增证据。
- 无偏好键默认 true；历史 false 不由 resume/通知事件覆盖。通知不可用时停止真实监听及服务、active=false，开启偏好保留且明确 failure；不请求权限或启动 Activity。
- 通知 STOP 使用 package-scoped、immutable 的 `PendingIntent.getBroadcast`；服务存活期间以 `ContextCompat.RECEIVER_NOT_EXPORTED` 动态注册，STOP 不冷启动服务，无需新增 manifest receiver。保留旧 service STOP 分支以兼容遗留 PendingIntent。
- STOP：进程 fence=true → 同步 commit(false) → diagnostics.stopListener()（原 server.stop 同步关闭监听及 clients）→ Application.cancelPhoneIfInitialized()（父已实现；只取消既有共享 PhoneRuntime，不冷构造 SDK）→ stopService → active=false → cancel notification。失败逐项记录，不因前一清理异常跳过后续清理。当前偏好与 STOP fence 在每个服务启动实时检查；START/STOP 串行化。
- 通知改为同机 MCP 文案，不再写“四个只读工具”，不展示 token。

## 真实 RED → GREEN

- `red/compile.exit = 0`；JUnit 8 tests / 4 failures，缺少默认开启与进程 STOP fence；非编译错误或拼写错误。
- `green/compile.exit = 0`；JUnit `OK (8 tests)`，exit=0；`final-junit.log` 再运行仍 `OK (8 tests)`。
- RED/GREEN 测试源字节完全一致，GREEN 生产 policy 与最终文件字节一致。记录 source、SHA256、命令、编译/JUnit exit 与原始日志。
- RED 策略为旧 0.2.7 缺省 false / choice+notification 的最小纯逻辑抽取；它不是 Android 服务测试或历史已经执行过的 STOP 生命周期验证。
- 本地 kotlinc 编译成功但打印 Termux Jansi glibc 原生库加载 warning；未影响 JUnit，不将其隐藏或称为零警告。

## 0.2.7 STOP200 可证事实

原件：`qa/diag-mcp-027/evidence/android-43552523971-key/`，CI run 43552523971、source 762e46dc5c7d172191e3b0a1b50027c05b524082、API33。`old-stop-facts.json` 保存本棒从原件解析的事实。

- `normal-stop-port-0.bin` 真有 130 字节 `HTTP/1.1 200 OK` 响应头，SHA256 `432744751801c3e3b0a0bf1de5f2c0d2f8885919a256917a3ba3dd927f4ad18b`。Content-Length=11，但原件只有响应头；只能证明当时 socket 返回了 200 headers。
- XML 中按原选择规则找到唯一、enabled/clickable=true 的停止按钮，bounds `[147,978][283,1104]`；tap_node 会输入中心坐标。tap 与 collapse 日志均 0 字节，只证明命令未输出；没有事件送达/服务处理/偏好 false 的读回凭据。
- 原 harness 在通知 tap 后直接塌下 shade 并探 socket，`require(closed)` 在 for 内，第 0 次 200 就退出。后续 stop-services、off-notification、switch false 与 stopPath 写回均未执行。原 report passed=false/stage=ordinary-background-fgs，未声称停止通过。
- 所以这是“点击后的首探仍 200”未解决证据，不是“STOP handler 已完成后仍 200”或“必然因为 queued start 复活”的根因证据。可能有事件未送达/未处理、调度竞态等，原件无法区分；不猜。
- `readonly-recheck.json`：本棒读取的旧 key evidence、旧 McpKeepAliveTest.kt、旧 gate/harness 未变（changed=[]）。

## 父接入建议 / pending

- 父维护 Application/Settings/Activity/Manifest：Application 仅诊断初始化，推荐 `diagnostics.start(false)`，socket 开启由 visible resumeChoice/Settings enable 的 FGS 提升后承担，避免默认 true + 拒通知冷后台创建窗口仍先启动 socket。
- `ContextCompat` API26-32 非导出兼容使用 AndroidX 自动合并的签名权限；CI 确认 merged manifest 与现有 core 版本。service subtype 文案建议父改掉旧 read-only 描述，不新增 boot/alarm/wakelock。
- 旧 Android 测试明确写 defaultOff/permission denied 清 false，与新规格冲突，本棒不修改、不跳过、不伪称通过。
- 真实 Android 编译/模拟器 pending，由父执行；没有做真机、安装、拉起、点击、签名或提交。
- 可靠 STOP 验收须真 SystemUI action，确认 delivery+commit 完成后即探真实 socket（连接拒绝/reset/EOF，超时及 HTTP错误不是关闭），同时在途 socket 断开、同一 PhoneRuntime 同步任务取消、service/notification 移除、active=false；晚到 start/Activity 再 resume 不重开。必须记录停止完成屏障、原始 HTTP与状态，不靠 sleep 或 tap 命令退出码猜完成。
