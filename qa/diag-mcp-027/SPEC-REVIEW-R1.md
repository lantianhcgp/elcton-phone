# 0.2.7 规格符合性审查 R1

审查对象：默认关闭的前台诊断会话、token 私有取用；父会话复核源码和证据后记录。此时未构建 APK。

审查结论：MUSTFIX。

1. resumeChoice 先检查 active 提前返回，通知 channel/授权关闭后仍可保持运行。恢复入口必须先核查 canNotify，即使 active 也需停止失效会话。
2. UI 开关只在点击/ON_RESUME 从偏好复制，Service 异步失败时不能及时显示 false；端口绑定失败提示先写后被 disable 清空。需要事件驱动状态同步，保留失败提示，不增加后台轮询。

实跑 source scope 12 项通过，但不替代 Service 与 UI 的 Android 断言。WE/签名/默认开启/额外省电行为未发现范围漂移。真正 curl/urllib error_tail 仍 BLOCKED：安装旧包0.2.6，被MIUI冻结，禁止安装/抢前台；私有文件已确认现成 errorCode8 记录，不冒充HTTP成功。

下一步：独立修复 worker 改3个保活文件及仪器负例；SPEC re-review PASS 后才开始质量审查。完整交付仍需真实构建、API33/34 模拟器、签名一致读取和真机硬标准注明。
