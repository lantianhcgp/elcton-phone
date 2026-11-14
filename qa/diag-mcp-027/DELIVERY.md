# 0.2.7 / code9：外部 MCP 交付及未通过项

状态：SIGNED APK PRODUCED；ACCEPTANCE FAILED/BLOCKED。不得称真机 MCP 全通或全部修复完成。

## 实际 APK

- 源提交：762e46dc5c7d172191e3b0a1b50027c05b524082，分支 feat/diag-mcp-027，未合并 master。
- 签名构建：https://github.com/lantianhcgp/elcton-phone/actions/runs/43552199858 （success）。
- 文件：/storage/emulated/0/Documents/elcton-WearEngine-真机联调-20261113-123000/phone/hc课程表-0.2.7-code9-762e46dc-signed.apk
- 字节：8200371。
- SHA256：e13687cf6b19ba8d1ebb0f68bdea3a0152d082843b6cbde038f185c09d198fcc
- 证书 SHA256：fc08a0b474a8ffca5887bd5c88ac15e865a63a64eca81c10f344496c46d9ad94，与原 0.2.6 身份相同，apksigner 验证通过。
- 编译后二进制 manifest：com.hcbiu.elcton / versionName=0.2.7 / versionCode=9。ZIP 校验通过，包内未发现私钥/PAT/真机 token。
- 同名 .apk.sha256 已创建并逐字节核对。旧包未覆盖。未安装到真机。

## 已实现及证实的范围

- 设置「MCP 保持运行」默认关；明确开启才用非导出前台服务、持续通知；不新增唤醒锁、开机启动、自动白名单或 WE/AGC 行为。
- 通知频道/global/group 关闭通过服务存活期间动态注册的系统广播复核通知权限并停止；恢复入口再次复核。API33/34 完整动态验收未通过，不能仅凭静态复审宣称这些路径全部正常。
- token 用现有 Shizuku/rish + run-as，保存在 Python 内存或 Termux 私有 home 的0600文件，不进公共目录、剪贴板、日志。完整取用见 TERMUX.md；此方案依赖当前原签名 debuggable APK，不冒称商店 release 通用读取。
- HTTP 服务端字节未改；修正外部 selftest 默认请求 half-close 的错误假设。CI 的真实 APK 经 adb forward 用 curl/urllib 完整 Content-Length 请求已通过；需要写 EOF 的截断体负例在该转发路径明确报告 unsupported，未悄悄算通过。
- Runtime 监听 start/stop 纳入原 revision 合并落盘协议。真实 Socket/写入屏障旧 RED：内存 false/端口拒绝但文件 true；同模板 GREEN：文件 false，JUnit 1项通过，真实文件保留。原失败及 SPEC/QUALITY 原件均保留。

## 已通过的实际测试

- 本地 Python 86项（1项依赖 skip，单独真实客户端4项执行通过）；production Kotlin host 84项；真实 Socket 屏障1项。
- Android Gradle CI 单元测试：19份XML，84项，0 failure/error/skip。
- 签名构建 CI production JVM HTTP：3784断言，curl+urllib。该层不是 Android/真机。
- API33 模拟器真实 APK：诊断 instrumentation/首尾文字/像素门通过；普通 App HTTP 3637断言 curl+urllib 通过；Home 后3次真实版本/error读取与前台服务状态均成功。错误数据在模拟器明确为 SYNTHETIC，不能替代现成真机 WE 异常。

## 未通过的硬验收

1. 真机：没有安装0.2.7、没有主动拉起 App 或解锁。原0.2.6 journal 确有 `WearEngineException [errorCode=8]: Scope unauthorized`，但这是私有文件核验，不是 error_tail 成功。Termux loopback curl/urllib 多次真实请求均 connect timeout/0字节。最新仅系统 reported-resumed 状态下重试仍 curl28、urllib timeout；ActivityManager 的 resumed 字段不等于已活跃可达。早期 MIUI freezer 证据与辅助白名单添加/恢复读回保留。白名单添加成功但未改善，已恢复。
2. API33 run43552523971：failure，stage=ordinary-background-fgs。点击真实通知「停止」后首 socket 探测仍返回 HTTP/1.1 200 OK 响应头，停止验收失败，后续 destructive keepalive instrumentation 未执行。本轮未证明是异步回调尚未完成还是产品停止路径缺陷，不凭猜测修改结果。
3. API34 run43552577848：failure，Exercise real APK without a paired device 步骤失败。完整失败原文在对应 GitHub artifact；不把未知细节冒写成与API33同根因。

API33：https://github.com/lantianhcgp/elcton-phone/actions/runs/43552523971
API34：https://github.com/lantianhcgp/elcton-phone/actions/runs/43552577848

## 请求、响应及证据位置

- 真机原始失败请求/响应：evidence/real-device-026/foreground-retry-curl/request.http、response-original.http、curl-stderr.txt、receipt.json（Authorization 唯一脱敏；响应原文0字节，不伪造HTTP000响应）。早期失败及私有journal也保留。
- 签名/包交付：evidence/apk-delivery-receipt.json、apk-signature-027.txt、apk-secret-audit-027.json、ci-unit-test-count-43552199858.json。
- 构建 HTTP 原日志：evidence/build-http-43552199858/。
- 各 CI 完整 artifact 保留在原 GitHub runs；仓内补充关键失败回执，不删除任何旧失败、旧APK或旧报告。
- 取用步骤：TERMUX.md；最短只读命令 `python -B qa/termux_mcp.py --tool error_tail --limit 128`，无需 adb forward。未达HTTP200/记录真实返回前不得宣称通路成功。

本轮交付候选包供后续修复/验收；签名成功不等于可放心宣称 MCP 功能验收通过。仍需解决通知停止硬门并在用户允许的真机部署状态重验现成 error_tail。WE业务/AGC/签名未改，未开启默认保活，未更改其他省电策略。
