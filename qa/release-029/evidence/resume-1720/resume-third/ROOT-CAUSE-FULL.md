# full 43586804691 只读根因报告

## 结论与证明边界

**已证明：失败不是 cold-teal-dark 的 UI/配色断言，而是该 instrumentation 已成功返回后，主机取回 palette 证据失败。随后设备 ADB shell 与 emulator console 都不可用。运行属于取证/模拟器会话失效 RED，不能按产品配色崩溃处理。**

**未证明：为什么 emulator console 消失；现有证据不能区分 QEMU 崩溃、外部杀进程、OOM、端口/ADB 故障等。不能宣称“SwiftShader 崩溃/OOM 已定位”，也不能证明此前成功用例结束后的产品绝无后台异常。**

以下路径均相对仓库根 `/data/data/com.termux/files/home/elcton-phone-release-029-20261114`。

- E = `qa/release-029/evidence/resume-1720/full-9e300f9-evidence/`
- A = E 下 `artifact/`
- F = `qa/release-029/evidence/resume-1720/full-9e300f9-failure/actual.log`
- HEAD = `9e300f9f7c56bddb2151e63d6a160c5bc645db93`

## 已证明的因果链（不是末尾报错猜测）

1. **精确身份**：`E/run.json:2-4` 绑定 run `43586804691`、failure 与上述 SHA。`E/artifacts.json` 的唯一 artifact ID 为 `14111000940`，workflow_run 绑定同 run/SHA。只读逐项核验 `E/inventory.json` 中全部 620 清单项的存在、bytes、SHA256，结果 `INVENTORY_MISMATCH []`。
2. **用例实际成功**：`A/palette-cold-teal-dark-instrumentation.txt:15-23` 为 `INSTRUMENTATION_STATUS_CODE: 0`、`Time: 4.913`、`OK (1 test)`、`INSTRUMENTATION_CODE: -1`。后者是本轮成功输出的正常终态，不是异常。`A/palette-host.json:95-104` 同时记录 passed=true、exit_code=0、timed_out=false、两个 force-stop 后 PID 为空。
3. **真正触发失败的是 harvest**：`A/report.json:3-8` 保留同一成功 instrumentation，但 `stage=palette-cold-teal-dark`、`timed_out=false`、`harvested=false`。`qa/emulator_install_and_tour.py:134-137` 先判 instrumentation 并保存原始结果；`:140-146` 再取证；`:145` 用 `not phase_passed or not collected` 合并两类故障；`:154` 无差别抛 `Palette phase failed`。只读抽取源码原 AST 判定式，按九份真实 wire stdout/返回码重算，九项均 true；因此本次走的是 `not collected`，不是 `not phase_passed`。
4. **采集失败细节没有保全**：`qa/emulator_install_and_tour.py:97-120` 运行 `run-as ... tar`，若返回码非零或 stdout 为空只写 stderr，再返回 false；没有保存该 harvest 的实际 rc/stdout。`A/palette-harvest-error.txt` 经工具实测是 0 bytes，不能据此补造具体 ADB/tar 错误。`A/palette-logcat-error.txt:1` 是 `CalledProcessError: Command [adb, shell] returned non-zero exit status 1.`。源码 `:147-152` 表明这是紧接 harvest 失败后的诊断采集再次失败。
5. **console 也已不可用，但不是 crash 栈**：`F:239-245` 为 Python 通用 assertion；`:246-248` 是随后 action 收尾 `adb -s emulator-5554 emu kill`，报 `could not connect to TCP port 5554: Connection refused`。独立于某个应用包的 console 监听也不存在，单一产品 Java 异常不足以解释这两个通道失效；但未采到 host PID/退出信号，不能将此直接等同于“已证明 emulator 崩溃”。

## 已有成功阶段与缺失阶段

- Actions 设置 job/checkout、Python、Java、Gradle、精确 signed APK 下载、显示依赖、JVM 回归、KVM、X display 均 success（`E/run.json:15-92`）；失败后的 artifact upload 也 success（`:102-108`）。
- API33 模拟器正常 boot（`F:213-218`）；主 APK 与测试 APK 安装均 Success（`:227-234`）；三键导航和通知预授权已执行，`A/notification-fixture.json:2-4` 为 sdk=33/pregranted-ui-only/granted=true。
- JVM 自测真实返回 3784 assertions/all_raw_checks_passed=true（`A/client-jvm-selftest.log:1`）；real-client 4 tests OK（`A/client-jvm-regression.log:1-10`）。这些明示是 JVM/synthetic callbacks，不是 Android 证据。
- Theme 全部四阶段成功：initial、cold-dark、cold-system-dark、cold-light-under-dark-system（`A/theme-host.json:6-44`）。原报告 `A/theme-report.json:2-12` 为 passed=true、23 screenshots、errors=[]；本子任务用原 `verify_theme_evidence.verify_product` 对真实 PNG/XML/state 只读重验，得到 passed=true、23 scenes、errors=[]，经 JSON 序列化边界后与原报告完整相等。
- Palette 九个 instrumentation 成功：warm，purple LIGHT/DARK，blue LIGHT/DARK，green LIGHT/DARK，teal LIGHT/DARK（`A/palette-host.json:7-104`；最后一项尚未成功 harvest）。九份原 stdout.bin/stderr.bin 与 host JSON 文本逐字节一致。
- 已落盘 palette 为 warm 的 48 张和前七个 cold 阶段各一张，共 55 张；本子任务逐张调用原 `verify_palette_evidence.inspect_capture`，真实结果 55/55 passed、failures=[]。这是**现有部分 captures 的逐张验证**，不是完整 palette suite GREEN。
- 最后成功 harvest 的 `A/palette-product/r3-cold-teal-light-result.json:1` 记录业务 hash 前后相等，结束状态 TEAL+DARK，正是下个 cold-teal-dark 的输入。该阶段源码 `PaletteUiTest.kt:341-348` 先检查 TEAL+DARK 并拍 cold 图，再切 ORANGE+LIGHT；`:364-368` 完成业务 hash 相等断言后写 result。最后阶段 instrument 已 OK，但其 cold 图/process/result 没被取回，不能补报磁盘验证成功。
- **未运行/未验收**：cold-orange-light/dark、cold-pink-light/dark、system、cold-system、整体 palette verifier 及冻结 ProductUiTest 后续 tour。阶段顺序见 `qa/verify_palette_evidence.py:35-36`；主脚本在 `:166` 中止，`:167-185` 不曾到达。`A/palette-host.json` 顶层 passed=false 正确；不能仅凭 nine OK 改成绿色。

## 近改核对与排除错误归因

- `git diff b9ce478..HEAD -- qa/emulator_install_and_tour.py app/src/androidTest/java/com/hcbiu/elcton/PaletteUiTest.kt .github/workflows` 显示只有主脚本新增 `prepare_ui_notifications`（现行 `:29-40`），PaletteUiTest 与工作流无近改。通知授权确已成功读回；不是旧通知弹窗/NoCompose 首因。
- 同区间产品 MainActivity 近改只有诊断 fallback（`:52-55`）和 ComponentActivity permission override 签名（`:531-533`），无配色/采集改动；未找到本次故障支持的产品修改目标。这不是“产品一定无问题”的普遍证明。
- `F:86-91` 记录 emulator `37.2.13.0`、gfxstream/SwiftShader。`:209-210`、`:235-238` 的 ColorBuffer/texture 警告早于最终 failure，且真实 theme 23 与 palette 55 图原门禁重验都绿，不能把警告、headless 参数或图片文件大小当崩溃/黑屏根因。
- `F:101` 的“Storing crashdata ... detection is enabled”是启动时启用崩溃采集，不是发生 crash 的证据。当前 full artifact 无 emulator crash database/minidump、host OOM/exit 信号、palette live logcat；主脚本的 live logcat 到后面的 `:176-178` 才启动，本轮未到达。

## 最小建议（仅建议，未实施、未验证）

1. **本轮不改产品、不改原测试/断言/签名/SDK/GPU/资源配置。** 将这次 run 留为环境/取证失败 RED；已定位的是 successful instrumentation 后的 evidence harvest failure，不是可据此修改产品的断言失败。
2. 经父任务/用户明确授权后，优先在新的云端 runner 用同 SHA、同 APK/test 身份和同冻结配置执行原 full suite；本子任务没有发起任何 CI。全部剩余 phases、完整 palette gate、原 ProductUiTest 都必须真绿才可称 full 验收成功。不能跳过采集失败或降低原门禁。
3. 若同型失效复发，最小后续取证是 palette 开始前保全 host emulator stdout/stderr、PID/退出信号、crash DB/runner OOM 信息，并保全每次 harvest 的原 stdout/stderr/rc 和 live logcat。现阶段只是补证建议；无需立即重签或重做产品。若有授权改 QA 可将通用报错区分 instrumentation 与 harvest，但这只能改善错误归因，不能作为修复证明。

## 本子任务执行边界

只读本地已下载证据/源码，运行原离线 verifier 与 SHA/AST 检查；未访问手机、未执行任何 adb/am/MCP 操作、未触发/重跑 CI、未修改产品/测试/工作流、未删改任何旧证据。只新增本文件，使用独占创建（O_EXCL）避免覆盖。未深挖父代理负责的 McpKeepAliveTest:136。
