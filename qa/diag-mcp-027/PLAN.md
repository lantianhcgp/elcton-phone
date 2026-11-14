# MCP 外部通路 0.2.7 实施计划

> 按用户已批准简报实现；HTTP、保活、token、验收分别核实。

Goal: 外部 curl/urllib 可读取只读 MCP；不将模拟器成功当真机成功。
Architecture: 保留 127.0.0.1:8766 与四工具及私有凭据；HTTP 与 Android 生命周期分层。默认无前台服务，保持原被动进程启动模式。用户开启设置开关后 foreground service/常驻通知保活，关闭即关闭当前 listener 和服务。不加唤醒锁、自动白名单、开机广播或 WE 调用。
Tech Stack: 原 Kotlin/Compose、Android API26–34、Python stdlib、curl；原 CI 稳定重签不变。

## 范围与验收 seams
- HTTP POST /mcp：真实客户端正常返回、UTF8 Content-Length、鉴权、非法请求、连接关闭；先 RED 再 GREEN。特别区分 adb forward half-close 与 direct TCP。
- UI：设置「MCP 保持运行」默认 false；通知授权拒绝不默启；on/off 与真实服务/端口一致。token 不放 UI/公共目录，用现有 rish + debug run-as 捕获至内存/Termux 私有0600。
- 安全：应用ID、HMS元数据、WE业务文件、证书指纹、原错误全文保持；字节门禁拒绝额外差异。
- 真机：不 install、不 am start、不触锁屏；仅自然/现有前台状态读。辅助 deviceidle 白名单实验先记原值、后独立恢复并读回。
- CI：固定 Python3.12，emulator-runner 单行 selector，APK/source 同 SHA；模拟器可 install/start，不得指向真机。

## 分工与执行
1. 独立 HTTP 子代理只改 DiagnosticMcpServer.kt、DiagnosticMcpServerTest.kt、mcp_http_selftest.py 和新增真实客户端测试；保存定位/RED/GREEN。
2. 父会话改 DiagnosticRuntime.kt/ElctonApplication.kt；新增 McpKeepAlive.kt/诊断设置组件；MainActivity 仅加独立组件接线；Manifest 增所需 FGS/通知权限与非导出服务；version 0.2.7/code9。
3. 写保活仪器测试：默认关、授权拒绝、开启常驻服务、后台HTTP、关闭端口，错误持久化与业务指纹不变。精确扩展 source gate 的批准 UI 差异，不过滤其他变化。
4. Python helper 通过 rish stdin/run-as 直接捕获token，格式校验后0600保存；curl/urllib请求响应只脱敏 credential 字段，错误全文不截断。真实前台不可用则记录硬验收BLOCKED，不伪造。
5. 本地真实 Kotlin/JUnit/Python；规格审查PASS后代码质量审查；CI构建签名/模拟器curl+urllib通过才交候选APK。
6. 新APK放现有 phone/ 目录新文件；SHA256/apksigner读回；证据推 feat/diag-mcp-027；更新原 DELIVERY.md 并保留0.2.6失败。停止自己临时进程/进度cron；不动并行AGC浏览器。

## 当前已核
起点 cd2a3e062b97d778c79b76b544071b1077534af7；原工作树未修改。0.2.6 外部CI整体 failure 43535414635，内部instrumentationPASS；真机curl HTTP000/rish uid2000可用/run-as可用。没有安装或主动启动App。
