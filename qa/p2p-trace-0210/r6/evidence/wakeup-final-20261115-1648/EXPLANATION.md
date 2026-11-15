# Q-R6-001：真实 JVM RED → 最小 Runtime GREEN

## 取证对象与边界

- 编译当前真实 `DiagnosticRuntime`、`P2pTrace` 与已有 MCP/错误日志依赖；没有改写或模拟 Runtime/Trace。
- `Log` / `BuildConfig` 仅沿用旧 HOST 适配模板，不代表 Android 实机执行。
- 新 `.kt.in` / `.java.in` 在 `r6/runtime-wakeup-host/`；运行生成的 `.kt`、`.class`、`.jar` 全在 `r6/evidence/wakeup-*`。没有 staging/commit、完整 JVM/Python 回归、CI、remote、SDK 或设备调用。

## 精确 barrier 与透明性

Kotlin 本次实际字节码将 finally 的 `writing.set(false)` 复制到正常结束、`Exception` catch、catch-all 三条路径。初始工具把副本数假定为 2，因此在任何产品修改前停止；这只是 instrumentation prerequisite failure，不作为 RED，原目录完整保留。

校正 HOST 工具的严格副本数后，ASM 在真实编译 `persistLater$lambda$0(DiagnosticRuntime)` 的三处 `GETFIELD Runtime.writing / ICONST_0 / AtomicBoolean.set(Z)` 中，紧贴 `set(false)` 前添加：

```
ALOAD 0
INVOKESTATIC HostWakeBarrier.beforeRelease(DiagnosticRuntime):void
```

原 AtomicBoolean 接收者与 false 在操作数栈保留；HOST 调用净栈变化为零。正常路径的点在最后 `revision/traceSeq` 比较及 break 之后、`writing=false` 之前。没有替换原指令、字段、分支或产品调用；没有在产品加 test hook。各阶段 `host-bytecode.diff` / `original-*.raw.log` / `instrumented-*.raw.log` / `instrumentation-proof.txt` 保存实物；删除新增两条指令后的 normalized 原始指令、label/line/frame/try-catch 序列逐项相同，所有原 MethodInsn 调用计数相同。原始及 overlay `.class` SHA 各自记录。

只为明确允许的 JVM 调度插入 latch：进入 HOST barrier 后测试线程发出真实 `P2pTrace.emit`，同步执行原 onChanged → 原 persistLater CAS，随后解除 latch。没有伪造写入结果或 sequence。目标调用固定为初始 CLOSE、退出窗口中的 UNREG_TASK_OK 两次 emit，不调用 observe/SDK/listener/manual-persist。其余独立 case 用原 observe/stateWriter seam 做 revision 与磁盘故障测试，不改变目标 case。

## 真实 RED

先封存未改产品 SHA，再成功编译真实源文件。首次成功 barrier 测试与独立重复运行均为 `Tests run: 6, Failures: 1`；失败仅为目标 `java.lang.AssertionError: Q-R6-001 last trace event ... expected:<2> but was:<1>`，不是编译或基础设施失败。

解除 barrier、连续三次真实 executor fence 后：revision=0、traceSeq=2、ringSeq=2、diskSeq=1、stateSeq=1、pending=1、writing=false、stateWrites=1。证明最后事件在内存，却在 writer 静默时没有写入真实文件。五项既有策略对照测试在 RED 已通过。

## 唯一产品修复

`DiagnosticRuntime.persistLater()` 仅增加局部 `processedTraceSeq`，在完成该轮 stateWriter 后赋值为该轮入口捕获的 `traceVersion`；释放 writing 后以 `revision != persisted || sequence != processedTraceSeq` 决定后继排队。原 `!failed && persisted >= 0` 闸保持不变。

- 捕获的是本轮已处理 sequence，不在 finally 重新捕获“当前”sequence，否则会吞掉退出窗口中的新事件。
- 不使用 pending 或“最后成功磁盘 seq”作为续排条件，磁盘异常、quota 仍可保留 pending 而静默，不产生自持续写入。
- 没有新增 timer、executor、SDK 调用、callback wrapper 或业务行为；`WearProbe` / `SyncEngine` / `P2pTrace` / `SendAttempts`、原测试及版本/identity 未由本修复修改。

## GREEN 与冻结

RED 与 GREEN 新测试、ASM 模板、runner、旧 HOST assertions 均逐文件 SHA 相同。GREEN 同一六项全部通过，目标 diskSeq=stateSeq=2、pending=0、writing=false、stateWrites=2，只有一个后继写入。state 异常 case 即使窗口中同时增加 revision/traceSeq 也只写一次，须后续显式 observe 才恢复；trace 写失败与 quota 均无自旋。

原未 instrumented Runtime jar 另跑原 runtime fault/revision 四项（4/4），再独立跑原 stop revision（1/1），保留真实 loopback HTTP 200、stop 后连接拒绝及落盘 running=false。产品冻结时间、最后 Runtime SHA 与全部 raw 路径在 `FINAL-Q1.json` 和 `after-green-source.freeze.json`。

父代理独立 SPEC → QUALITY 重审、identity 更新、全 JVM/Python/CI 与后续交付门不属于本次声称完成范围。
