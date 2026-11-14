# full43590641863 / cold-pink-dark：R8 新原件独立只读归因

## 结论先行

**这次 RED 的直接原因已经定位：`cold-pink-dark` 的 Android instrumentation 成功后，主机 `harvest_palettes()` 未取回有效归档，触发取证 fail-closed；不是此次 PaletteUiTest 产品断言失败。** 新原件还独立证明随后 `adb shell` 返回 1、模拟器 console 5554 拒绝连接，属于与此前描述同型的取证/运行环境失效症状。但**模拟器为什么失去服务、是否由反复 run-as tar 导致、tar 的确切 RC/字节数，现有新原件不能证明**，不把旧根因报告当作新证据。

范围：只读本机新 artifact、原失败日志、当前/提交源码；没有网络查询或 dispatch CI，没有手机 adb，没有修改代码、产品 APK、测试 APK、旧证据。唯一新增本报告。

路径简写：
- `F = qa/release-029/evidence/resume-1720/full-44df9d0-evidence`
- `A = F/artifact`
- `L = qa/release-029/evidence/resume-1720/full-44df9d0-failure/actual.log`
- 全部路径相对 `/data/data/com.termux/files/home/elcton-phone-release-029-20261114`。

## 1. 新原件身份与完整性

- `F/run.json:2-4,94-108`：run `43590641863`、source `44df9d0fd36aecaa22613e9aa73c5c7d4ed94416`，失败 step 是 Exercise real APK；upload-artifact 成功。
- `full-44df9d0-dispatch/dispatch-inputs.json:2-6`：build_run=`43590339873`，build_sha 为上述完整 SHA，API33 / three-button / full。
- `F/artifacts.json`：唯一 artifact ID `14112252769`，名称 `android-ui-44df9d0fd36aecaa22613e9aa73c5c7d4ed94416`，workflow_run.id=`43590641863`。这是本地取回的元数据，未另作远端查询。
- 本次 Python 遍历核验 `inventory.json` 的 **676 个条目**全部 SHA256/大小相符；其中 artifact **672 文件**，无额外/缺失文件；download.exit=`0`。这证明“本地文件与取回时 inventory 一致”，不等同于从未知的 guest 私有目录补全证据。
- `qa/emulator_install_and_tour.py`、`qa/verify_palette_evidence.py`、`PaletteUiTest.kt`、`.github/workflows/ui-smoke.yml` 当前字节均与该提交 `git show` 相同，调用链不是读错版本。

## 2. 已证明的直接失败链

1. `A/palette-host.json:139-148`：`cold-pink-dark` 的 `passed=true, exit_code=0, timed_out=false`，两个 force-stop 后 PID 均空。`A/palette-cold-pink-dark-instrumentation.txt:15-23` 是 STATUS_CODE 0、Time 4.062、**OK (1 test)**、INSTRUMENTATION_CODE -1。这里 -1 是 instrumentation 完成结果，不是 host RC -1；host RC 是 0。
2. 两份 raw bin 与 host 的对应 stdout/stderr **逐字节相符**：stdout 722 字节、SHA256=`15b1e9feed8cdc246dff8539d6673a8b1fdd5964c81a109f190350862b7da24a`；stderr 155 字节、SHA256=`3f5854d93a2496effd0f16a20da7bdac12a7c95f5fdbc2e5ceec11c889ebe15c`。stderr 只有三条 s_glBindAttribLocation，没有 AssertionError/FAILURES。
3. `qa/emulator_install_and_tour.py:125-137` 先记 raw/RC；`:141` 随后调用 harvest。`:145-154` 将“instrumentation 不过 **或** harvested=false”合并为同一 Palette phase failed。
4. `A/report.json:2-8`：`stage=palette-cold-pink-dark`、instrumentation OK、timed_out=false、**harvested=false**；因此实际走的是 harvest 失败支路，而不是产品断言失败支路。
5. `A/palette-harvest-error.txt` **0 字节**，且 inventory `:191-193` 对应空文件 SHA256。对应源码 `:104-106`：`if archive.returncode or not archive.stdout`，写入 `archive.stderr` 后返回 False。TimeoutExpired 会在 `:101-103` 写 timeout bin 并经 `:142-144` 写非空异常；tar 解析失败会在 `:118-119` 写非空异常。新件没有这些 timeout bin。因此已定位到“archive 返回后 RC 非零或 stdout 为空、captured stderr 为空”的前置判断；**不能进一步从空 error 文件猜定 archive RC=1，也不能把 stdout 断言为 0 字节**，因为正常返回的 archive RC/stdout 未被保存。
6. `A/palette-logcat-error.txt:1`：`CalledProcessError: Command '['adb', 'shell']' returned non-zero exit status 1.`，对应源码 `:147-152` 的补采 logcat。此次没有 logcat timeout bin：这是 RC1，不是已证的超时。
7. `L:243-249`：最终是主机 AssertionError，源码栈 `:166 → :154`，time=`2026-11-14T11:42:52Z`；`:250-253` 才进入 action cleanup，`adb -s emulator-5554 emu kill` 得到 **TCP5554 Connection refused**。console 在该次 kill 请求时已不可连；不能倒因为“cleanup kill 杀死了先前 harvest”。也不能仅据端口拒绝断言 QEMU 的确切退出信号/是否 OOM。

**精确边界：instrumentation 成功 → harvest 不合格 → 补采 logcat RC1 → cleanup 时 console 拒绝。底层 emulator/ADB 失效机制仍未封口。**

## 3. 最后成功 phase、已覆盖与未覆盖

- `palette-host.json` 共 **13 个已执行 phase**（warm + 12 个 cold 配色/明暗），全部 RC0 / OK1 / 无超时；每个 phase 的 raw bytes、host 内容和 force-stop 记录均核验一致。
- 最后“instrumentation 成功”的 phase 是 **cold-pink-dark**；最后“instrumentation + 文件 harvest 完整”的 phase 是 **cold-pink-light**。后者 process/result JSON 均在 `palette-product`；process pid=9828, PINK/LIGHT，result PINK/DARK，businessBefore=businessAfter。
- result 的 DARK 不是 LIGHT phase 标错：`PaletteUiTest.kt:341-348` 冷启动先核当前组合、拍证，再选择下一组合；最后 PINK/DARK 会选择 SYSTEM。`cold-pink-dark` OK1 因而说明该次测试走完当期断言和写 result 的源码路径；但对应 guest 文件没有取回，不能把“应写入”冒认为“主机已取得”。
- `A` 缺 `r3-cold-pink-dark-process.json`、`r3-cold-pink-dark-result.json`、`r3-pink-dark-cold` PNG/XML/state/attempts。`system`、`cold-system` 根本未执行，`palette-report.json` 和后续 ProductUiTest/report/system-bars 验收也未到达（主脚本 `:157-175`）。
- 对新件只读执行提交中的原 `verify_product()`（Python -B，无写输出）：manifest 要求 **74 个 capture**，已取回 **59 个 capture 全部通过**，现有 capture 无像素/层级/状态错误；整体仍 False，只缺 15 个 capture 与末三期 process/result 证明，验证返回 43 条缺项/缺组合错误，没有其他错误。它是本次本机复核，不冒认 CI 的 palette-report 已成功。
- `A/theme-report.json:2-12`：真实新件已完整通过 23 张、四个 theme phase、errors=[]。warm 的 PINK/DARK options PNG 视觉复核为真实暗色设置、粉色选中，不是空白或错误页；**它不能替代缺失的 cold-pink-dark 证据**。

## 4. adb tar harvest 路径及“是否反复 tar 杀死模拟器”

真实调用：`ui-smoke.yml:101` full → `emulator_install_and_tour.py:157-166` 每期 → `execute_palette_phase:141` → `harvest_palettes:99`：

```text
subprocess.run(['adb','shell'],
  input=b'run-as com.hcbiu.elcton tar -cf - -C files qa-palette-evidence/2f63ab6d-8c83-4772-91cd-d57bff423a42\n',
  capture_output=True, timeout=60)
```

- 不是按期/增量归档：每次 tar **整个当前 UUID 目录**（含此前 warm/cold PNG/XML/state/process/result/所有 attempts），再逐文件重写到同一新建 host 目录。guest UUID 来自 `PaletteUiTest.kt:37-40`；无旧 run 目录复用。
- 13 个已执行 phase 意味着 harvest 被调用 13 次；前 12 次成功取回，失败点为第 13 次。前期 archived run 的 59 个 capture、12 对 process/result 均在本地，不是“每次 tar 都把模拟器杀死”。
- 按已取回文件按 receipt.phase 分组、累计每次整个目录，前 12 次重复 harvest 的**内容字节下界为 241,061,510**（不含 tar header/padding）；当前 guest 目录此前已取回内容为 22,317,360 字节。重复传输是源码已证事实和值得缩小的云端执行面，但没有资源/进程时间序列，**不能把该字节量升级为 OOM 原因**。
- 此链没有 emu kill / adb kill-server / 杀 QEMU 命令，唯一 am force-stop 在测试前且只针对产品/测试包。`L:233-242` 确有 gfxstream ColorBuffer/context 错误，但没 fatal signal、killed、内核 OOM、QEMU 退出码或失败瞬间 PID；它们早于最后 host 报错，不能仅据图形日志给 GPU 根因定案。
- 新 diag `43590599162` 本地元数据 success/source 相同，host passed=true/stage complete；`diag_emulator_smoke.py:110-149` 已有精确 serial、raw 先保存、`exec-out run-as ... tar` 取回路线。其归档约 1.1–1.4 MB，成功只是可复用的传输范式，**不证明 22 MB 累积 palette 归档在同样资源下也必过**。

## 5. 最小继续路径（建议；本任务未实施/未启动）

1. **冻结产品/测试和所有判据**：继续用 build43590339873 的原主包/测试包及 source44df9d0；API33、three-button、GPU/window、RAM/heap/core、资源配置不改。不要把 harvested 条件改成忽略，不删 cold/system phase，不把旧文件或 warm 截图补作 cold。
2. **先在真实云端 harvest 调用边界补零行为取证**：每期/每命令独立文件保存 phase、argv/stdin、start/end/耗时、RC、stdout.bin、stderr.bin、归档大小/SHA、tar member count/解析结果、上个成功 harvest；report 分开记录 instrumentation_passed 和 harvest_passed。特别必须在 `:104` 之前保存正常返回的 archive，logcat 的 CalledProcessError 也保存其 output/stderr，不能只留异常字符串。live logcat 应覆盖 theme/palette 前半程，不能仍只从当前 `:177` 的 ProductUiTest 才启动。
3. **优先单一主机传输改动**：将此 run 的二进制 tar 取回采用已有 diag 范式 `adb -s emulator-5554 exec-out run-as com.hcbiu.elcton tar -cf - -C files qa-palette-evidence/<原 UUID>`，明确 emulator serial、保持超时/原安全路径/UUID/哈希/完整性门禁。不要因一次失败直接重启模拟器或无限重试。此举针对 stdin-fed adb shell 的传输面，是待验改动，不宣称已经治好。
4. **若仍随累计归档复发，再单独缩小重复执行面**：只取新增/该期文件（phase-bound capture + process/result + 所有 attempts），每次用 guest 文件清单做差、host 保留既有文件、归档仍保持 `qa-palette-evidence/<UUID>/...` 前缀供原路径验证；最终用原 74-capture/15-phase/全部断言完整验收。不能用“仅最终 tar 一次”牺牲失败当期证据，也不要使用未验证 toybox 支持的 tar 参数。
5. **注意当前真实 checkout 约束**：`ui-smoke.yml:39-41` 以 build_sha 钉 checkout；主脚本 `:16` 把 APK source 与该 checkout HEAD 严格对账。只修改另一 revision 的 qa 脚本、仍填 build_sha=44df9d0，实际不会运行新脚本。应以 **QA-only 工作流外层取证/传输包装**或独立 `harness_ref` 隔离执行云端修补，产品 checkout 与 source identity 检查仍指向44df9d0，另外保存 workflow/harness SHA 和最小差异；不可松掉 source identity 来凑绿。若不支持隔离，则需先设计该云端执行入口，不应盲目重复 dispatch。
6. 真全绿标准：保留原新 RED；新云端结果跑完 theme → palette 全 15 phase/74 capture、process/run/hash/pixel 门禁 → 原 ProductUiTest/28图/IME/system-bars 门禁，同时 exactAPK/test/signature/source 与 build 对账。现有59/59局部通过和diag绿都不能代替它。

## 6. 下一次必须补的证据 / 尚待检验假设

- **archive 真 RC/正常 stdout**：区分 adb 通道返回空、远端 tar 非零、归档完整性/输出截断；当前只能确认源码前置分支返回 False。
- **失效前后状态**：在每次 instrument 返回及 tar 开始/结束立即采云主机 QEMU/adb PID、`adb devices -l`/get-state、console5554与adb5037 listener、QEMU wait status。host 自身 free/df、cgroup memory.events/pressure、允许时 dmesg/journal OOM、emulator stderr 与 `/tmp/android-runner/emu-crash-37.2.13.db` 一并保留；没有 OOM 记录前不判 OOM。
- **通信存活但取回坏**：此时读取 guest run 私有目录清单/大小及本期 process/result，确认 PINK/DARK 是否已写入、是否仍能用 direct exec-out 得到同 UUID 归档；不要先 force-stop/reset 擦掉现场。
- **反复 tar 假设**：需命令时间戳 + emulator PID/退出信号 + 同资源下 direct/incremental 单变量对照。当前13次累计采集/第13次失败只是关联；“run-as tar 杀死模拟器”尚未证明。
- **图形或 guest system 崩溃假设**：需 crash/tombstone/guest kernel/连续logcat佐证。只有 early gfxstream ERROR 和 late console拒绝不足以判定。

保护记录：旧 `resume-third/ROOT-CAUSE-FULL.md` 仅取 hash 作未改验证，没有读取或复用其内容；SHA256=`a8f0a702e29491f2feb5719b6a500d64a35105dc588352241868c4a88940a136`。新 `L` SHA256=`c55675185f09a501e6cbcab678754e43574f571501ea58043c23a4aa739a70ee`。调查开始时间为本机 2026-11-14T19:46:18+08:00。
