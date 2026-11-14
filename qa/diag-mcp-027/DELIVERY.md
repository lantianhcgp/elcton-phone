# 0.2.7 / code9 外部 MCP 交付核验

当前状态：构建前候选；真机硬验收 BLOCKED，不代表「外部全通」。后续构建/模拟器结果按真实回执追加，不以本地源码门禁替代。

## 本次实现

- 原 HTTP 服务端字节未改。修正外部 selftest 对完整 Content-Length 请求默认 half-close 的错误假设；curl/urllib 强制真实执行。原 Android framing 根因需精确 APK CI 再证实，不把 synthetic EOF-closing relay 当 adb 事实。
- 设置「MCP 保持运行」默认关；明确开启才用非导出前台 Service 与持续通知，用户关/通知停止即关当前 listener/连接/服务。Android14 使用 local-only diagnostic specialUse 声明；无唤醒锁、开机广播、WE/AGC调用或默认改省电。
- 通知失效通过仅存活服务注册的系统通知事件立即停止；恢复入口再次复核，启动中不宣称active；Service绑定失败即时更新UIoff并保留提示，活动状态+偏好监听驱动，无轮询。监听start/stop纳入落盘revision合并协议，真实Socket/写入屏障已验证旧RED文件true→新GREEN文件false。
- 私有 token 经现有 Shizuku/rish + run-as 捕获到Termux内存或0600私有文件，无adb配对、不显示在屏幕或公共目录。取用指南 TERMUX.md。
- 版本0.2.7/code9；原四只读工具、127.0.0.1:8766、认证、WE业务、签名身份不变。

## 已核事实

- 当前纯 Kotlin JUnit 84项通过；Python QA最新86项通过，1项依赖发现skip另在真实host回归4项通过。所有源门禁12项通过，拒绝非批准WE/UI改动。
- 原0.2.6真JVM baseline 1164断言；当前源码真实curl/urllib自测3784断言；真实客户端/relay回归4项；所有完整原始HTTP负例保留，transport EOF专项若unsupported单列，绝不冒称通过。
- 旧签名证书apksigner读回：fc08a0b474a8ffca5887bd5c88ac15e865a63a64eca81c10f344496c46d9ad94。新包仍待实际构建和比对。
- live token literal扫描与git相关凭据签名扫描无命中；Termux token私有0600/64字节只记录mode/长度无值。

## 真机硬项未满足（禁止假造成功响应）

- 原0.2.6/code8仍安装；未安装0.2.7、未主动am start/抢前台/解锁/调用WE。
- 当前系统记录已有resumedActivity但MIUI freezer日志记录PID26578被冻结，线程D状态；shell与Termux同net namespace。两侧实际connect/health失败，Termux curl退出28，0响应字节，urllib超时。
- 按简报授权deviceidle白名单添加成功，HTTP仍超时；随后独立恢复并读回不存在。无持久系统省电改动。
- rish/run-as读原错误日志确有2条 `WearEngineException [errorCode=8]: Scope unauthorized`。evidence/real-device-026/existing-private-error-journal.jsonl为原始私有文件内容，不是error_tail HTTP响应，不能替代硬验收。
- 实际请求配置/失败原文/退出码/freezer/白名单效果与恢复已保存；不存在成功完整HTTP响应，绝不拼一个。

## 证据

- HTTP定位：evidence/http-FINDINGS.md 与 http-* 原RED/GREEN。
- 真机：evidence/real-device-026/，curl-attempt-request.http 与 curl-original-response-or-failure.txt、urllib-receipt.json。
- 规格R1/质量R1、R2失败原件保留；通知后台事件SPEC-R3通过，Runtime revision真实屏障RED/GREEN和最新两阶段增量复核结果随证据收录。
- CI顺序：CI-SEQUENCE.md（普通cold/background先验，notification/channel破坏负例放最后）；原source/cert/像素/assert数量不削弱。
- 0.2.6失败43535414635仍在原 qa/diag-mcp-026/DELIVERY.md 与证据，不覆盖旧APK，不合并master。

## 待追加的真实结果

APK源SHA、签名构建/模拟器精确run、下载后SHA256/bytes/证书、PNG逐组件目检、残留进程/定时停止状态。除这组正在执行项目外，真机0.2.7前台+Termux error_tail仍为BLOCKED，须另获安装/真实前台机会才能通过。
