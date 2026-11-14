# 0.2.9/code11 合并版规格与证据索引

授权来源：2026-11-14 用户《0.2.9 合并版——还清两条待办》完整任务。本文件只补充实现边界，不改用户验收层级。

基线：fix/p2p-ready-receipt-20261114 e034de2f924dd6d96e31caa8e5a62e52474de718（产品2097f32）。合入 feat/diag-mcp-027 1e14980f19cf5c510722d9521d9762586a3a91eb。独立工作树 elcton-phone-release-029-20261114；不动原树、旧APK、表端、签名及Scope。

架构：应用级 PhoneRuntime 拥有唯一同步引擎和课表库。Activity只是观察状态与调用动作；MCP同一实例、同一状态机。WearEngine的授权弹窗仅在可见Activity可用时显式请求；MCP不启动Activity、不注入UI，缺权限返回需要用户授权而非伪成功。协议TransferSession、ExportSession、PacketIngress和0.2.8准备ERROR回执规则保留。

工具：保留 error_tail/diag_read/version_info/fs_read 的构造与行为；动作 sync_connect/sync_disconnect/start_import/start_publish/abort，数据 courses_read/courses_write，另 pickup_import/devices_list/pairing_state/sync_state。写/替换显式confirm=true且遵循UI导入预览/确认和覆盖检查，不自动发布；pending状态不宣称完成。所有工具只通过127.0.0.1原Bearer鉴权。

保活：无偏好键默认开，历史明确关闭保留；Activity可见启动/恢复，不后台弹通知权限。通知停止应同一进程内先关闭监听和在途socket、同步任务取消，再停止服务与移除通知；停止状态持久化，迟到启动不得重开。通知不可用明确提示且不谎称保活。无新boot/alarm/wakelock。

测试边界：公开同步动作、共享实例、传输回执/超时/陈旧回调、课表校验/备份/读写、取件码网络边界、MCP鉴权/参数/真实HTTP、默认开/停止及在途socket。每新工具有测试，原89与0.2.7相关测试不删不skip。

历史规格冲突：旧测试写死0.2.6/8、0.2.7/9、0.2.8/10、默认关、Activity拥有业务与四工具全清单。已向用户请求仅按新规格对齐；超时工具要求采用最佳判断继续。只变这些直接冲突断言，保留原件与RED及一对一归因；不得放宽鉴权、协议、签名、课表或计数断言。历史审查/日志原件不改。

交付层：真实回归、CI APK 0.2.9/code11及apksigner fc08a0b474a8ffca5887bd5c88ac15e865a63a64eca81c10f344496c46d9ad94，Termux真实Kotlin tools/list逐名对照，证据推release/0.2.9-20261114并GitHub blob独立逐字读回。

真机层：用户装机后纯MCP导入→同步→回读及退后台10分钟health200/error_tail可读；本棒不安装不拉起不点击，一律pending。HOST/模拟器夹具不能代替蓝牙或MIUI验收。
