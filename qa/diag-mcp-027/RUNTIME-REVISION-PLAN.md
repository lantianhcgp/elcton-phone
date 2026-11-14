# MCP 监听状态持久化一致性最小修复

目标：真实端口停止后不能因写入合并使 state.json 永久保留 running=true；保留QUALITY-R2原失败报告。

范围：DiagnosticRuntime.kt；只为受控文件写入测试增加默认原replaceDiagnosticFile的依赖注入(如需要)。监听开始/停止必须让revision参与原writing合并协议，不改变观测、工具、token、地址、WE或服务行为。

1. 真实Runtime写入屏障停在捕获旧状态后、替换state文件前。
2. 执行stopListener，验证socket和内存状态停止，放开旧写入。
3. 原实现RED：最终文件仍true；固定原断言/输入。
4. 最小revision增量后GREEN：最终文件false；重复start/stop、原失败日志保留。
5. 两阶段限时复查只审本次Runtime增量和确定性反例；产品/其它原源码SHA保持。

证明级别：host平台适配(Log/BuildConfig)只为执行真实Kotlin诊断类，不能当Android通知投递证明；Android外部客户端和FGS另由原CI验收。
