# Round 1 review disposition

原完整回执：spec.json / standards.json，均passed=false，保留不修改。

- STD-BUILD/L1：MainActivity使用Build无import，确认，补android.os.Build；Android compile仍必须CI真跑，不把JVM绿冒作它。
- STD-STOP/L2：确认，真实调度RED保存于review-r1-effective-red，旧dispatcher复现中断未撤销和STOP后仍写。抽出MainThreadActions（仅调度非业务），epoch+interrupt/timeout放弃标记；cancelAll先invalidate；PhoneRuntime执行前仍核enablefalse。所有UI/MCP唯一PhoneActions不变。
- STD-IMPORT/L3：确认，RED发现2026-10-01编辑被旧2026-09-01覆盖。startImport记录起始revision；receiveImport若变化只留预览、不自动确认。无修改原editor版本/存盘断言。
- STD-REGISTRATION：确认，RED发现unregisters4→5误清replacement。陈旧success不能无条件全局unregister；只有peer=null、selected空且非busy（无替换接收器/扫描）才能安全兜底。实际native旧receiver始终由WearProbe按item/receiver身份release，保持旧无新会话清理断言不变。新replacement反例必须绿。
- spec M1 replace:true：撤销申请中；原用户简报全文只写start_publish动作名，没有replace:true字段要求。当前SPEC也只要求显式confirm与UI覆盖检查。原UI已经用force传递覆盖选择，保留相同语义，不增加凭空规格或改原测试。请原规格审查核原简报后修正此虚构引文。

建议：旧四只读工具的readOnly字段保持兼容，新增写能力在PhoneMcpTools.list/schema与通知/设置说明，服务能力不能靠旧字段推断。取件API仅域名HTTP例外、明确CRC只是校验；未改TLS验证。

本文件只是父级归因，不是第二轮green审查。必须真测本轮源码并拿到新双轴回执后才能推包。
