# R9云端取证补齐设计及当前门禁

基线44df9d0。新full43590641863精确RED的独立报告见../ROOT-CAUSE-FULL-R8.md；676原件与13期仪器OK/59张部分图原验收完整保留。不是配色断言错误；完整palette/full未绿。

## 已授权边界内的单一补证

- 产品37文件、原app单元/仪器72项、McpKeepAliveTest全部断言、SDK/GPU/window/RAM/heap/资源参数均不改。
- `qa/cloud_emulator_observer.py`仅在GITHUB_ACTIONS/CI且单一就绪emulator下，包装一次原full入口，连续采host emulator PID/status/oom_score、meminfo/cgroup memory/console端口；子进程结束后保存sudo只读dmesg与已有emulator crashdata。
- 子进程stdout/stderr继承原action日志、原exit原样返回，不retry、kill、restart或改设置；只后台轻线程1秒采样，结尾join。
- palette harvest在返回后原判据之前只追加自包含inline9语句stdout.bin/stderr.bin/RC/bytes写入，不改原tar执行、timeout、路径/UUID/提取安全/return predicates或execute_palette_phase。首external helper导致旧函数孤立装载NameError，旧test不改，失败115 errors1保留；仅将observer inline自包含。
- 七个新增合成测试先实际RED7/7，再GREEN7/7；含失败RC7原样只跑1次、success不是Android证明、离开CI零adb调用、原全AST逆恢复、失败/empty archive仍false、成功tar原bytes。此绿不是cloud通过。
- 工作流只有full脚本调用增加外层observer一处替换；逆变换原完整workflow逐字节一致、sh -n exit0；app72项原SHA完全相同。

## 当前

新的完整JVM152/152已重跑绿；Python/HTTP/Runtime/Termux回归仍待实际汇总。新127项输入冻结准备并发独立SPEC/STANDARDS，审观测fail-closed语义及全部旧范围；不继承R8审查绿为R9。

随后精确CI新包同源，按顺序注册diagnostics+full、并行等，不套旧APK/新QA不同源；两云端全绿前不交最终报告或新包。旧0.2.8 APK、1.1.15 HAP、9e300f9候选不覆盖；真机仍pending归发起方，本轮不安装/拉起/点击。
