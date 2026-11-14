# elcton-phone 0.2.6 / code8：部分交付，外部 MCP 验收未通过

## 当前结论

已产出稳定签名 APK 并真机覆盖安装成功；完整错误对话框与版本胶囊的真实 Android 模拟器仪器断言通过。但外部 Python HTTP 自测在真实 Android 上返回 `HTTP framing`，真机后台进程又被 MIUI 冻结，外部 MCP 全链尚未通过。不得将本报告解读为「全部验收完成」或「Wear Engine 授权问题修好」。

## APK 与签名

- 交付文件：`/storage/emulated/0/Documents/elcton-WearEngine-真机联调-20261113-123000/phone/hc课程表-0.2.6-code8-e4513f8d-signed.apk`
- APK SHA256：`9f2418467f5680274a768350fe9552a761e17662c2b1b6841e05890841ef0c3e`
- 文件大小：8,442,125 bytes。
- 应用 ID：`com.hcbiu.elcton`；版本 `0.2.6` / `8`，AAPT 与真机 dumpsys 均已读回。
- APK 源 SHA：`e4513f8d60020c36f79ac6d1e9d25043ed3bbdde`。
- 签名证书 SHA256：`fc08a0b474a8ffca5887bd5c88ac15e865a63a64eca81c10f344496c46d9ad94`，与 0.2.5 完整指纹相同，apksigner 校验通过。
- 签名构建：[43533718997](https://github.com/lantianhcgp/elcton-phone/actions/runs/43533718997)，成功。
- `adb install -r` 返回 `Success`；安装前后前台均为 QQ，未执行真机 `am start`。
- 保留所有旧 APK；未覆盖旧包。只推 `feat/diag-mcp-026`，未合并 master。

## 实现边界

- 错误包含时间戳、原始 message、异常类型、cause 链及可取得的 WE 错误码；Log.w 的 tag 为 `ElctonWear`，应用内 JSONL 环形错误记录和「连接诊断」读取同一完整记录。
- 仅新增观测，不改变 authorizeAndScan / scan / 传输业务链。`qa/diag_source_gate.py` 对照固定 0.2.5 基线逐字验证批准的观测差异。
- MCP 监听 `127.0.0.1:8766`，仅四个只读工具：`error_tail`、`diag_read`、`version_info`、`fs_read`。token 位于应用私有 `files/mcp/token`，模式 0600；不在证据里回显。
- 版本胶囊读取 BuildConfig，不再写死 0.2.4。

## 已通过的真实验证

- 签名 CI：84 项 JUnit，0 failures / 0 errors / 0 skipped。
- CI Kotlin host HTTP：1,164 条断言；本地另用真实 Android org.json 子集跑同一 HTTP 自测亦通过。
- 本地 Python QA：最终 71 项通过（包含 CI 环境修复的测试）；CI 构建时尚未包含后来新增的 3 项工作流断言，不能混称为同一测试源。
- 两轴独立代码审查通过，详见 `evidence/review-summary.md`；这不代替外部 Android 验收。
- 真实 Android API33 模拟器仪器断言通过：BuildConfig 版本胶囊、3293 字符完整 SYNTHETIC 错误、两层 cause、滚动首尾、关闭按钮、Activity recreate、应用内 raw Socket HTTP 四工具、token 0600、业务文件未变。
- 三张实际截图已由父会话看图，独立 PNG 像素统计逐值复核通过。测试错误明确为 SYNTHETIC，不是实际手表报错。

## 未通过项与失败保留

- [模拟器 run 43535414635](https://github.com/lantianhcgp/elcton-phone/actions/runs/43535414635)：仪器部分 PASS，但后续 `normal-app-read-only-http` 阶段的外部 Python 客户端失败，输出：`{"ok": false, "failure": "HTTP framing", "token": "REDACTED"}`。**该 run 整体 failure**，不是成功 run。
- 真机进程已后台启动且 8766 监听，但 `dumpsys greezer` 列出课程表 PID 31852 为冻结进程。非 UI 广播和一次进程解冻尝试后仍没有得到有效 HTTP 响应。不能断言这能解释模拟器失败；两个问题须分别定位。
- 尚未从 0.2.6 取得新一次真实 WE checkPermission 异常，本轮没有擅自触发授权/扫描流程或拉起手机前台。
- 早期两个模拟器失败是 CI 环境问题：Pillow 与 runner Python 版本不兼容；emulator-runner 分行执行多行 if。仅修 QA workflow，APK 产品源码及稳定签名构建 workflow 没变；没有为这些环境失败重装真机。

## MCP 自测复现示例（尚未通过，不是成功承诺）

ADB 恢复连接后，在仓根执行；私有 token 由脚本读取，日志脱敏：

```sh
export ANDROID_SERIAL=<实际连接地址>
adb forward tcp:8766 tcp:8766
python -B qa/mcp_http_selftest.py --url http://127.0.0.1:8766 --adb-token com.hcbiu.elcton --adb-token-path files/mcp/token --adb-serial "$ANDROID_SERIAL"
```

必须应用进程可运行；MIUI 冻结时仅 forward 不足以保证响应。本轮未修改省电策略、未添加常驻前台服务。临时无线调试开关的恢复结果另记 `evidence/device-cleanup.json`。

## 后续尚需的验收

先定位并修复真实 Android 外部 HTTP framing 失败，然后重跑精确 APK 模拟器全链；再验证真机后台可达性。在这些项通过前，本版本仅为已安装的诊断候选包，不应宣布可直接完成 HMS 根因自探。
