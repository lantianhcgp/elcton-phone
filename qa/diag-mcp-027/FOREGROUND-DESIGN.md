# 本地只读 MCP 前台服务：Android 14 最小设计与 CI 验收

核查日期：2026-11-14。范围：`com.hcbiu.elcton`，compile/target 34、min 26；仅监听 `127.0.0.1:8766`；只读研究。本文是设计建议，不表示服务已经实现或 Android 实机验收通过。

## 1. 结论与适用条件

**`specialUse` 是本场景可论证的候选类型，不是官方对 local HTTP diagnostic server 的点名批准，更不是任意保活豁免。**

- 官方把 `specialUse` 定义为其他类型未覆盖的「有效」FGS 用途；AOSP `ServiceInfo` 进一步说明：无法归入其他类型，也不能用 `JobInfo.Builder` 完成的用途。[S1][S2]
- 本场景成立的理由应是：用户主动开启一个持续诊断会话，需要离开界面后仍接收同机客户端的即时、鉴权、只读请求。持续 HTTP listener 不是可延期的一次性 Job。若目的只是让课程表 App 永远不被杀、空闲时占着进程，不能仅靠 subtype 字符串把它变成合规 FGS；官方要求任务对用户可感知，并明确不要仅为避免 idle 而启动 FGS。[S10][S11]
- 不建议借用 `connectedDevice`：本用途不是与外部蓝牙/USB/网络设备交互；不建议用 `remoteMessaging`，它用于设备间文本消息连续性。`dataSync` 包含实际数据传输/本地文件处理，但不应仅因使用 HTTP 就把持续待命诊断服务包装成同步任务；用途若以后变成有限导出，应重新分类。[S1]
- `shortService` 有约 3 分钟限时且不支持 sticky，不能用来实现本需求；`systemExempted` 只供满足特殊资格的应用，不是第三方保活兜底。[S1]
- subtype 为自由文本用途说明，随 Google Play 提交会被审查；能在系统上启动 ≠ 商店已批准。此研究不涉及 Play 提交，也不涉及 AGC/证书/credential。[S1]

### 必需声明与版本分支

建议的 Manifest 形状（仅示意，不是本次产品改动）：

```xml
<uses-permission android:name="android.permission.INTERNET" />
<uses-permission android:name="android.permission.FOREGROUND_SERVICE" />
<uses-permission android:name="android.permission.FOREGROUND_SERVICE_SPECIAL_USE" />
<uses-permission android:name="android.permission.POST_NOTIFICATIONS" />

<service android:name=".McpKeepAliveService"
    android:exported="false"
    android:stopWithTask="false"
    android:foregroundServiceType="specialUse">
    <property android:name="android.app.PROPERTY_SPECIAL_USE_FGS_SUBTYPE"
        android:value="User-enabled diagnostic session serving authenticated read-only application diagnostics to on-device clients over 127.0.0.1:8766; remains available while the user switches apps; user can stop it from settings or its ongoing notification." />
</service>
```

保留现有 `usesCleartextTraffic="false"`、包 ID、HMS metadata 与业务权限；只读 MCP 不需要位置、麦克风、蓝牙权限。

- Android 14 + target34：Manifest 的 type 和类型专属权限都必须正确；调用 `startForeground` 时明确使用 `FOREGROUND_SERVICE_TYPE_SPECIAL_USE`。缺专属权限抛 `SecurityException`；传入未声明类型抛 `IllegalArgumentException`，无类型声明会触发类型异常。[S1][S6]
- `specialUse` 无类型专属 runtime prerequisites；AOSP 策略只列 `FOREGROUND_SERVICE_SPECIAL_USE`，`foregroundOnlyPermission=false`。这不取消通用后台启动限制。[S3]
- AOSP 对该权限声明为 `normal|appop|instant`：不向用户请求危险运行时授权，但也不应解释为系统/AppOps 无法限制。[S4]
- 最少依赖可直接用框架 API：API34+ 用带 type 的 `startForeground`；API26–33 用两参数版本，不把新 type 强塞给旧系统。若用 `ServiceCompat`，确认 androidx-core 至少 1.12，并在旧系统使用兼容分支。[S6][S12]

## 2. 通知权限：平台事实与本项目策略要分开

Android 13+ 的 `POST_NOTIFICATIONS` 约束通知展示。官方明确：**启动 FGS 不需要先获得这个权限，但始终必须向 `startForeground` 提供有效 notification。** 拒绝后，FGS 的运行提示仍在 Task Manager / Active apps，普通通知抽屉不展示它。[S5] AOSP 通知服务也按权限抑制普通通知，而不是把 `specialUse` 列成通知豁免。[S13]

本项目用户授权要求是「设置开关 + 常驻通知」，建议采取更严格的产品策略：

1. `keepAliveEnabled` 默认 false；仅用户在可见设置页开启时，API33+ 请求通知权限。不是 App 启动自动弹权限，也不是 granted 就自动 opt-in。
2. 权限拒绝、取消/划走对话框：不开 FGS、不先写 true、不重试轰炸；开关仍 off。既有被动 HTTP 可存在，但 UI 不得显示「保持运行已开启」。这是产品选择，不是 Android 禁止 FGS 的结论。
3. 获准后还检查 app 通知总开关与专用 channel 未被禁用；API26–32 同样存在用户关闭 channel 的情况。失败时给设置入口，保持 off。
4. 创建专用 channel，建议 `IMPORTANCE_LOW` 而不是 MIN；notification 有 small icon、正整数 ID、打开设置的显式 immutable PendingIntent，以及显式「停止」action。不显示 token、业务文件内容或原错误全文。可选择立即展示 FGS notification，避免系统延后展示影响「开关已开」的验收。
5. 不把 `setOngoing(true)` 理解成绝不可划除。Android14 允许用户在解锁时划除这类通知；划除不是本项目的显式停止 action。保留应用设置和系统 Active apps 停止入口，不循环重发通知与用户对抗。[S9]
6. 运行后用户关闭通知/权限，系统并不必然停掉 FGS。至少在再次进入设置、再次启动或 sticky 重建时重新检查并停止不满足本项目可见性条件的会话；如果要求权限撤销立即停，应另做真实验收，不能假定 `onDestroy` 自动发生。

## 3. 最小生命周期与用户退出边界

### 启动、运行、停止

- **默认 off 指前台保活 off，不是全局 MCP 禁用。** 现有 0.2.6 的 Application 被动 HTTP 可保留；它只在普通进程活着时提供服务，不承诺后台可达。用户主动关闭保持运行，应立即关闭当次 listener 与服务。下次用户正常冷启动恢复被动 HTTP 不等于偷偷恢复 FGS，UI/测试应分别观察 `listenerRunning` 与 `keepAlive/foreground`。
- 用户在可见 Activity 中开启，持久化显式 opt-in，再调用 `startForegroundService`。服务立即创建通知并提升 foreground，**不要先读大文件、等 HTTP bind 或做 SDK 调用**；初始化/绑定交给后台执行，失败后撤销本次开启并释放服务。[S6]
- `DiagnosticRuntime` 应继续为唯一 listener 所有者，拆分诊断初始化、幂等 `startListener` 与 `stopListener`；FGS 复用它，不创建第二个 8766 server。显式关闭与排队中的 start 要串行化/检查当前许可，避免关后重开。
- 已开启的 FGS 与 Activity 生命周期分离：Home、Activity recreate、任务从最近任务列表划走不是显式 opt-out；`stopWithTask=false` 是建议的会话策略。不要在 `onTaskRemoved` 或 `onDestroy` 安排重启。
- 通知停止 action 指向非导出服务的显式 STOP intent，不需新增 receiver。共同停止路径先将 opt-in 持久化为 false，再关闭 listener/活动连接、移除 foreground notification、`stopSelf`。不能仅移除通知而让 listener 继续跑。
- `onDestroy` 只做幂等资源清理，不自动把 opt-in 写回 false：系统回收与用户退出不是同一事件。HTTP/诊断异常应失效关闭或显示真实失败，不做无限自重启，不调用 WearEngine。

### START_STICKY：允许恢复，不是永生

AOSP `Service.java` 明确：[S7]

- `START_STICKY` 保留 started 状态，系统以后会**尝试**重建；可能收到 `intent == null`，必须处理。
- Android12 的后台 FGS 新启动限制不影响系统对已运行 sticky FGS 的重启；应用自己在后台调用 start，即使称为 sticky，仍受限制。

建议每次 `onStartCommand` 都读最新 opt-in/通知条件；仅许可仍有效且已成功提升 foreground、开始会话才返回 `START_STICKY`。STOP、false、初始化失败返回 `START_NOT_STICKY` 并停止，null intent 不能默认打开。持久化标志是用户的选择，不是允许任意后台入口冷启动 FGS 的许可证。

`Application.onCreate` 不无条件 `startForegroundService`：它可能由后台组件或系统恢复触发；普通恢复入口放在可见/RESUMED Activity，系统 sticky 恢复则在已创建的 Service 自身处理。[S6][S7] 退出后台期间权限回调返回时也需检查 Activity 是否仍可见；不符合条件则推迟到用户再次进入，不吞异常后报成功。

- Task Manager 的 Stop（Android13+）移除整个 App 进程、Activity 栈和 FGS 通知，**不发送应用回调**；不能依靠 `onDestroy` 清理持久化选择。[S8]
- 设置中的 force-stop / 系统 Stop 不是内存回收，不能以 sticky 绕过用户停止。下次用户主动打开可按 UI 政策恢复之前选择，但不能后台自行复活；若需要把系统 Stop 永久解释成 opt-out，可在下次启动结合 `ApplicationExitInfo.REASON_USER_REQUESTED` 决策，属于额外产品选择。[S8]
- AOSP 重启队列有延迟/退避且关机不安排重启，不承诺固定时间或永不被杀。[S14]

### Android12/14 与省电边界

Android12+ / target31+ 的背景新启动通常抛 `ForegroundServiceStartNotAllowedException`；显式用户交互属于豁免情况之一，但最小路线就是从可见设置 Activity 开始，不依赖 alarms、boot 或白名单。[S6] Android14 额外检查 type 权限，以及 camera/mic/location 等 while-in-use 条件；`specialUse` 没有这种额外传感器前置条件，却仍受一般背景启动规则。[S3][S6]

**不新增** WAKE_LOCK、alarms、jobs 复活链、bootreceiver、battery optimization exemption 或轮询看门狗。FGS 只提供合法生命周期/优先级，不保证 CPU 不休眠、不保证 Doze 或 OEM 策略下始终能处理 TCP。[S11] 官方 Doze 通用网络限制不能直接当作「已经证明 loopback 被阻断」；同机回环和长锁屏表现本次没有实测，不把超时归因到某个 OEM/AGC。

## 4. 现有 CI 脚本读审与最少改动建议

本次只读检查 `qa/diag_emulator_smoke.py`、`DiagnosticsUiTest.kt`、`DiagnosticRuntime.kt`、`ElctonApplication.kt`、Manifest、Gradle 与 `.github/workflows/ui-smoke.yml`。检查时产品仍为 0.2.6/code8，Application 被动启动 server，Manifest 未声明 FGS/通知权限。这是并行工作树的时间点观察，不替父任务断言后续状态。

### 保留已有可信证据链

- 脚本 L162–187 先核验 GitHub Linux CI、APK/test/source 同 SHA、真实签名，再限定唯一 `emulator-*` 和 `ro.kernel.qemu=1`。保留这些 guard；任何新增测试/权限操作都在 guard 后，不添加本地/真机通路。
- L201–206 指定一个 `DiagnosticsUiTest`，并严格要求 `OK (1 test)`；L116–154 独立核验 receipt、SHA、PNG 像素和 UI XML。最少改动可把 FGS 用例加进现有一个 `@Test`，不必放宽 test count。若另加测试类，明确指定类并验证实际预期数，不能删掉成功/失败解析门禁。
- L208–247 在 instrumentation 结束后 force-stop → 真正启动 MainActivity → adb forward → HTTP/NIO/持久化/业务文件指纹。这一段值得保留，但目前 Activity 仍在前台，没有 Home 后服务/端口证据。
- `Harness.shell` 不像 `Harness.adb` 自身完整重验 serial 格式；新增命令优先走 `adb()` 的统一 guard，或统一 strengthen guard，不新增裸 subprocess 的设备操作。

### 最小 instrumentation 接缝（未来实现，不是已通过项）

在现有单个测试中，沿用 Compose tag + UiAutomator + 真实 Socket；新增稳定的设置控件 tag 和 receipt 子对象 `foregroundMcp`，不要加生产「测试启动/kill」HTTP 工具：

1. **首次默认状态**：干净 CI 安装时断言开关 false、无 FGS/notification；被动 listener 可正常存在。`install -r` 不证明首次默认状态，旧数据需在注入 SYNTHETIC 之前明确清理或证明 emulator 全新。
2. **拒绝**（API33+）：进入真正设置、点击开启、通过系统权限对话框拒绝；断言 opt-in 仍 false、无 FGS、无对应 notification；不把 passive listener 的存在算违规。权限初态在 host 安装后、首次 instrumentation 前设置；**不要在正在运行的 target instrumentation 中撤销 runtime permission**，撤销可能杀进程。[S15] 已拒绝测试后可用允许/测试授权建立后续 granted 初态，记录实际权限，不伪造回调。
3. **允许并开启**：点击真实设置开关；断言持久化许可、对应 ServiceRecord foreground、API34 的 `specialUse`、有效 notification/channel 与真实 `127.0.0.1:8766` RPC。通知实际出现用有超时的 UiAutomator 等待，不只检查一个产品布尔值。
4. **Activity recreate 与 Home**：真实 Activity 离开后还可读四工具，错误全文/白名单文件保持；但 instrumentation 本身会改变进程重要性，所以该断言只证明逻辑分离，不独立证明正常后台保活。
5. **关闭**：点关闭后服务/notification 消失，当前 listener 关闭，新连接失败、已有连接结束；等待有截止时间，不能把 401、500 或某个 RPC 方法失败当作「端口已关闭」。off 后 Activity recreate 不能重新 bind。
6. **通知停止 action**：重新开启后点真实停止 action，确认 persisted false、服务/端口关闭。最后为下述正常进程段显式重新开启一次，并在 receipt 标记 `leaveEnabledForHost=true`。

receipt 至少记录：默认/拒绝/允许/关闭/通知停止的实际状态、API、sourceSha、qaRun、组件名、类型、notification ID/channel、真实 HTTP 结果与前后业务指纹。token 只记录 REDACTED。Python `verify_evidence` 应逐项 require，缺字段/false 就 fail；新增 host verifier 单测覆盖缺项、错 run、错 type/未授权却 reported on 等反例。

### instrumentation 结束后的独立后台证据：不可省略

在脚本正常冷启动段（L208 以后）复用 existing persisted opt-in，仅从真实可见 MainActivity 恢复服务：

1. 确认授权/开关有效、service 处于 foreground，health 就绪；保留 APK/source/version/业务指纹门禁。0.2.7 升级时明确改 receipt/version/code 的固定预期，不能顺手放宽证书/SHA。
2. 从 CI emulator 按 Home，保存真实 Activity 已非 resumed、service `isForeground=true` 和 type 的 dumpsys；继续通过 adb forward 做有鉴权 RPC 与现有 `mcp_http_selftest.py` / curl、urllib 实际客户端检查。建议带 `time.monotonic()` 截止时间的短窗口（例如 30 秒、间隔探测），记录每次实际时间/status/错误，而不是只 sleep 后宣称保活。
3. 收集 notification/UI、service、logcat、真实 HTTP 与业务文件 before/after；失败保留证据。新的 log gate 包含 app FATAL、FGS 提升超时/类型/权限异常，不用只匹配一种 crash。
4. 可在主成功证据完成后加独立 system Stop 阶段（仅经 guard 的 CI emulator，官方提供 `cmd activity stop-app PACKAGE`）：断言进程/服务/端口离开且短观察窗内不自复活。force-stop 可另验，但**不可当成 sticky 内存回收恢复测试**。[S8]

真实 sticky kill/restart 另列专项：普通 `am kill` 对重要 FGS 可能不生效，不能命令返回 0 就称杀过；直接调用 `onStartCommand(null)` 单测也不是系统恢复证据。若后来加隔离的 CI 受控进程回收，需证明旧 PID 消失、新 PID、真实系统恢复/通知/端口及重新读取 opt-in，且不暴露生产 kill 接口。本轮最低验收不包含该项。

现有脚本 `screen-ready` 设置 stayon 和很长 screen timeout，因此新增 Home 段仍是**亮屏普通后台**验收，不是锁屏/Doze/息屏耐久测试。不要增加 deviceidle 白名单来把测试改成有利条件。

### CI 范围与完成条件

- API34 必跑：type/专属权限；API33 必跑：通知 runtime permission；现有 API30 可回归旧 foreground 分支。保留 Python3.12、单行 emulator-runner selector、同 SHA artifact 及 `always()` 上传证据。
- 现有截图测试使用较新的框架能力且工作流声明 API30+，不能直接把 API26 加入同套件就声称 min26 兼容。API26–29 需要独立轻量 service-only instrumentation 或标记未运行；源码/编译检查不等于设备验收。
- PASS 仅能表示所选 API 的 CI emulator、SYNTHETIC 数据、有限亮屏窗口；不证明当前真机、OEM 杀后台、休眠回环、重启恢复或商店审核。任何硬项没跑/证据缺失标 BLOCKED/NOT_TESTED，不冒充整体通过。

## 5. 本次实际验证与未实测

实际执行：`python3 -B qa/diag_emulator_smoke.py --self-test`，exit 0，3 个本地 verifier 测试通过（标识格式、真实签名摘要匹配门禁、空白像素拒绝）。该分支不创建 Harness，不调用 adb，不代表 Android FGS 已验证。

未运行：Gradle/Android 构建、CI workflow、任何 emulator/真机 adb/rish、FGS 启动、通知 grant/deny 实机、Home 后保活、sticky 恢复、系统 Stop、息屏/Doze、OEM 策略、Play 审查。未操作 AGC、凭据、签名链、Documents 或 git push；本次仅新增本 Markdown。

获取问题：Jina 读取三个指定文档均返回 HTTP401；Exa 对旧通知页面超时、对 `/fgs/overview` 路径未找到。按 agent-reach 路线用 Exa 定位，最终直接读取官方页面（含通知旧 URL 的 `?hl=en`、官方 Compose 对应页面、真正 `/fgs` overview）和 pinned AOSP `android-14.0.0_r1` 补齐正文；不依赖搜索摘要或第三方回答下结论。

## 6. 官方/AOSP 来源

- [S1] Android：FGS types（已读 specialUse 与相关类型正文） https://developer.android.com/develop/background-work/services/fgs/service-types
- [S2] AOSP Android14 `ServiceInfo.java`，L477–485：无法归类且无法 Job 化，subtype 提示 https://android.googlesource.com/platform/frameworks/base/+/android-14.0.0_r1/core/java/android/content/pm/ServiceInfo.java
- [S3] AOSP Android14 `ForegroundServiceTypePolicy.java`，L580–596：specialUse permission / foregroundOnlyPermission https://android.googlesource.com/platform/frameworks/base/+/android-14.0.0_r1/core/java/android/app/ForegroundServiceTypePolicy.java
- [S4] AOSP Android14 framework Manifest，L7042–7049：normal|appop|instant https://android.googlesource.com/platform/frameworks/base/+/android-14.0.0_r1/core/res/AndroidManifest.xml
- [S5] Android：notification runtime permission（旧 URL 直接读正文成功；Exa 定位官方 Compose 对应页） https://developer.android.com/develop/ui/views/notifications/notification-permission?hl=en ；https://developer.android.com/develop/ui/compose/notifications/notification-permission
- [S6] Android：FGS launch / background-start restrictions https://developer.android.com/develop/background-work/services/fgs/launch ；https://developer.android.com/develop/background-work/services/fgs/restrictions-bg-start
- [S7] AOSP Android14 `Service.java`，L390–412：START_STICKY、null intent 与 Android12 restart 例外 https://android.googlesource.com/platform/frameworks/base/+/android-14.0.0_r1/core/java/android/app/Service.java
- [S8] Android：user-initiated Stop、无 callback、官方测试入口 https://developer.android.com/develop/background-work/services/fgs/handle-user-stopping
- [S9] Android14：ongoing notifications 可划除及 cached-app 资源边界 https://developer.android.com/about/versions/14/behavior-changes-all#non-dismissable-notifications
- [S10] Android：FGS overview，only user-noticeable work https://developer.android.com/develop/background-work/services/fgs
- [S11] Android：Doze/App Standby，CPU/网络限制、勿仅为防 idle 开 FGS https://developer.android.com/training/monitoring-device-state/doze-standby
- [S12] AndroidX `ServiceCompat.startForeground`，core1.12/旧系统类型兼容 https://developer.android.com/reference/androidx/core/app/ServiceCompat
- [S13] AOSP Android14 `NotificationManagerService.java`，L7320–7332、7364–7366：blocked notification / runtime permission https://android.googlesource.com/platform/frameworks/base/+/android-14.0.0_r1/services/core/java/com/android/server/notification/NotificationManagerService.java
- [S14] AOSP Android14 `ActiveServices.java`，L4588–4592、4700–4727、5941–5957：关机不重启、重启延迟及 sticky/non-sticky 状态 https://android.googlesource.com/platform/frameworks/base/+/android-14.0.0_r1/services/core/java/com/android/server/am/ActiveServices.java
- [S15] AOSP Android14 `PermissionManagerServiceImpl.java`，权限撤销 callback 的 killUid 路径（存在特殊 skip 条件，不能假定撤销永不杀进程） https://android.googlesource.com/platform/frameworks/base/+/android-14.0.0_r1/services/core/java/com/android/server/pm/permission/PermissionManagerServiceImpl.java
