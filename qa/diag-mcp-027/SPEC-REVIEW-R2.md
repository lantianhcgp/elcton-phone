# 0.2.7 规格复查 R2

独立只读 SPEC 复查：PASS（限制为R1两个代码缺口），2026-11-14 10:50:05 完成。父会话先逐行核查新实现，随后核对独立结论及其下列内容SHA，三文件未漂移。

- McpKeepAlive.kt: 0f27a1158c1c3525ec7a5b0b2880da48048d64dc00459552b2696dc8710abf41
- McpKeepAliveSettings.kt: a9a09df2bd60c2b9a7f712f5f7985cd207f4cd713ae00da46b7f8f76b52a22b3
- McpKeepAliveTest.kt: 0fdd4643640805984376251c5a0ca6691d5aed9195f1bf8797ef79c89d2dae88

1. 通知复核在active提前返回前；不可用disable(reason)，停止端口、服务和通知。新仪器负例在active状态把专用channel降NONE，复核UIoff与端口关闭。
2. 状态/提示为Compose事件可观察值；偏好监听在主线程更新；checked仅真active时on，启动中显示独立提示；disable保留端口绑定失败原因。真实ServerSocket占端口负例核失败后UIoff和完整错误提示，不靠click/ON_RESUME。

本地receipt缺键/非布尔等负向6测试绿；这些只证明verifier不是Android执行。独立审查未跑Android编译或仪器；真机仍受禁止装机/抢前台与旧包冻结阻塞，不能宣布全通。

下一阶段质量审查针对同一代码，先spec再quality；所有R1原失败证据保留。
