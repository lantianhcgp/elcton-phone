# 0.2.7 质量审查 R1

独立质量审查 REQUEST_CHANGES（2026-11-14 10:54:38）；同一SPEC-R2三文件内容指纹，未与Android实测混淆。

P2实质反例：用户已明确开启保活→Home→从通知进入系统通知设置关闭专用channel→返回Home，不回App。现实现只在resumeChoice/onStartCommand复核canNotify，Service可能仍active且listener开却没有可见通知。原channelNONE测试主动resumeChoice只证明恢复入口，不能证明后台failclosed。

最小修复边界：Service生命周期中动态监听系统自身通知设置变更；事件发生即重核自身canNotify，失效就关当前端口/通知/服务。只动态进程内监听，非导出，不增Manifest广播/boot/轮询/唤醒锁/省电权限。用模拟器真实系统通知UI操作再返回Home，禁止直接调用resumeChoice或手发synthetic broadcast冒充系统实测。真机不安装不抢前台。

其余质量审查未发现token公开/导出入口、已接受peer关闭或假想on-off-on旧实例问题。WE/AGC/签名不变。原R1两spec缺口已PASS，新的质量缺口必须fix后re-review，未完成前不push。
