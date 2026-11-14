# R8 保活云端返回夹具根因：Activity identity 不是保活业务失败

基线9e300f9f7c56bddb2151e63d6a160c5bc645db93；真实diagnostics运行43586767169。全部原始artifact/logcat/截图/报告保留，不改变已有断言，不修改App行为。

## 原始证据
- `diag-9e300f9-evidence/artifact/diag-product/mcp-keepalive-on.png`、同名XML：亲眼复看设置页底部MCP开关打开，无权限窗遮挡；XML resource-id=mcp-keepalive-switch、checked=true、visible-to-user=true、bounds=[837,1075][974,1201]。这是line118先前截图，不冒充line136之后画面。没有line136后现场截图/XML；不假造。
- `diag-product/keepalive-report.json`：defaultOn、permissionDeniedFailClosed、defaultOnNoPermissionRetainsChoice、noNotificationWithoutPermission、bindFailureUiOnAndHintRetained、startingNotActive、onNotification、backgroundHttp、offPortClosed、offNotificationRemoved、businessAndTokenAndErrorsUnchanged、stopDisablesChoice、stopInactive实际均true；最终passed=false。
- `diag-logcat-live.txt` 47741/47777-47818：初次ActivityScenario launch为MAIN+LAUNCHER，MainActivity@53068ab CREATED/STARTED/RESUMED。
- 49387-49466：pressHome后同@53068ab PAUSED/STOPPED。
- 49682：10:52:15.540 返回命令实际只有cmp，没有MAIN/LAUNCHER。
- 49700-49710：新的MainActivity@85b1dd PRE_ON_CREATE/CREATED/STARTED/RESUMED；ActivityScenario每次明确拒绝：intent does not match，初launch MAIN+LAUNCHER、activity.getIntent()只有flg=0x10400000 cmp。
- 50260-50269：line136 `performScrollTo`找不到mcp-keepalive-switch。
- MainActivity.kt:58/141：tab实例默认0，设置仅tab==3时存在；新建实例因此不是原设置页。不能把包出现等同恢复已创建的设置页。

## 最小修复与范围
仅给McpKeepAliveTest.kt:134/181两条云端返回命令补上初launch同源的`-a android.intent.action.MAIN -c android.intent.category.LAUNCHER`。不改变manifest launchMode、不把tab永久设为settings，不改变服务/同步/token/业务逻辑，不force-stop/clear-task/recreate。

保持全部原test方法、assertIsOff/On、端口/通知/取消/文件SHA、真实系统channel拒绝与10秒deadline逐字不变。旧测试整文件保存在`resume-third/McpKeepAliveTest.kt.before.original`。新增`qa/test_keepalive_return_fixture.py`四例合成检查：两处原命令分别RED，字节还原/负向身份检查原先即绿；修复后须四例全绿。这仅证夹具形态与断言不变；真实Activity reuse/后续channel拒绝链仍待新同源云端运行，不先称Android通过。
