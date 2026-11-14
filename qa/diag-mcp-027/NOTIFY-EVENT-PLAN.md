# 0.2.7 通知失效事件最小修订

用户已授权默认关闭的 MCP 前台保活和常驻通知。质量R1的后台反例属于本功能关闭边界，不扩充其他省电策略。

Files: McpKeepAlive.kt、McpKeepAliveTest.kt；QA仅硬化既有报告字段。

1. 先在原测试保留所有默认关/绑定失败/HTTP/指纹/关闭断言，新增真实系统通知频道设置 UI 操作。Home 后监听必须在不恢复 MainActivity、不直接 resumeChoice 前关闭。先验证原产品无动态处理的结构RED；结构失败不称Android失败。
2. 启动服务 try 内注册自身三种系统通知阻止事件，API33+ NOT_EXPORTED；收到事件只重查自身 canNotify 后 disable/stop，不信 extras、不启服务、不写业务。
3. onDestroy 注销；保留原通知/端口/START_STICKY explicit choice 处理。原被动 Application 不注册。
4. Android 收据新增 backgroundChannelDeniedEventStops=true；每项缺失/false/nonboolean继续 failclosed。模拟器真实UI路径最后运行，避免频道变更污染普通后台测量。
5. 原12项source/scope全绿与Python85全绿（1项真实依赖另4项已跑）；SPEC先、质量后绑定两文件真实SHA。门禁与最新审查过后才push隔离分支。
6. 同签名构建APK后用API33与34模拟器真实curl/urllib及普通后台三次采样；APK和仪器包逐SHA/证书对照。真机不可前台则硬验收BLOCKED，不能绕禁装/抢前台。
