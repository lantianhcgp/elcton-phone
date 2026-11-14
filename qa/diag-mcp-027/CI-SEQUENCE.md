# CI 验收顺序隔离

0.2.7 QA 保留原全部仪器/error/source/cert/像素/普通冷启动断言；新增保活测试共一个 instrumentation testcase，十一个状态硬布尔 + API33+ denied permission，不能只信passed。

执行顺序：
1. DiagnosticsUiTest (真实BuildConfig/完整SYNTHETIC错误/滚动/截图/私有错误持久化)
2. 普通进程force-stop/coldstart，curl+urllib真实HTTP自测，再实际设置开关→Home→5秒内3次原PID/FGS/HTTP probe→通知停止或真实开关停止→端口关/通知消失/偏好off/业务token错误SHA不变。
3. 仅模拟器force-stop、建立permission-denied状态，McpKeepAliveTest负例最后跑：真实ServerSocket占8766→绑定失败提示和UIoff；成功后台；already-active的专用channel降NONE→resumeChoice→停端口/UIoff。
4. always取原文日志/图/XML+JSON；exact1test+十布尔+sourceSHA+qaRun硬验；不跑真机adb、不改产品测试hook。

为何最后：pm revoke通知运行时权限可终止目标进程；channel被NONE后delete/recreate同ID可能继承设置，不能假复原为LOW。让有意破坏性负例位于普通foreground/后台测量之后，避免假阳性/误报产品故障。测试fixture降channel只在模拟器，最后force-stop无驻留；不承诺Doze/sticky重启/MIUI证明，5秒3sample明确有限范围。

本地回归：强化receipt missing/false/int/字符串逐一拒；原像素/SHA门不变。当前尚未实际跑AndroidCI，不能标模拟器绿。
