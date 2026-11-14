# 0.2.9第三轮 R8准确续跑状态

这是进行中断点，不是完成证明；此前CONTINUATION-9e300f9.md与全部RED原件不覆盖。

- 本地目录：/data/data/com.termux/files/home/elcton-phone-release-029-20261114
- 分支：release/0.2.9-20261114
- 当前HEAD仍9e300f9f7c56bddb2151e63d6a160c5bc645db93；尚未push R8。
- 原full43586804691全部620项artifact与actual.log已取。独立ROOT-CAUSE-FULL.md证明cold-teal-dark用例实际OK，随后harvest false/ADB shell/console失效；具体外部原因证据不足，不改产品/配色断言/SDK/GPU/工作流，计划新同源runner全量重跑。
- 原diagnostics43586767169 logcat49700-49710证明component-only返回新建Activity@85b1dd，ActivityScenario因缺MAIN/LAUNCHER不认，原设置页@53068ab没恢复。只补McpKeepAliveTest两处返回命令的MAIN+LAUNCHER；37产品文件未改，旧全部断言/deadline/次数/业务SHA检查不变。before完整独占，新增4 fixture RED2→GREEN4，严格整文件可逆。
- 本地全量真实：JVM152/152；Python108/108零skip（原104+新增4）；HTTP3784；Runtime1；Termux tools/list15项200并收尾关监听。只属于本地host验证，不冒充Android或真机。
- final-review-r8冻结125完整输入/37产品；累计diff499323B。prepare及全输入清单已生成；独立SPEC/STANDARDS在审。未取得双绿不push。
- 旧0.2.8/1.1.15/9e300f9候选共3文件实际SHA/大小未变；9e300f9候选SHA15aafee2af9509bc61f3780f74cef712fc47dfdedcb487cdd34e7d59d9a1d8b7，不覆盖。
- 下一节点：核两原raw/指纹→隔离分支提交push/readback→精确CI主/测试APK0.2.9/code11与固定fc08全证书验签→新同源diagnostics/full实际全绿→新文件独占交付→报告+尾证据push逐字读回。
- 真机纯MCP全链、后台10分钟保活均pending归发起方；未安装/启动/点击手机，未碰表端/表盘/Scope/签名材料。

主要证据均位于qa/release-029/evidence/resume-1720/resume-third与final-review-r8，Documents只续写进度。

## R8源码提交节点（续追加，不抹掉历史）
- 当前精确源码44df9d0fd36aecaa22613e9aa73c5c7d4ed94416；已push release/0.2.9-20261114，外部分支读回相同SHA。
- 原双轴raw均passed=true、三类阻塞空，125项/37产品/499323B完整累计diff匹配，dual-closure已封；原两处返回夹具修复与断言保真已验证。
- 精确build43590339873已运行（尚未completed）；ci-44df9d0-r8后台轮询、remote-44df9d0-readback后台全部远端字节读回，均有完成通知。
- 待build绿才按本source/build串行注册diagnostics/full，再并行等待；新包独占文件，不覆盖9e300f9候选/旧包。Android与真机仍非已通过。

## R8两云端实结论（续追加）
- build43590339873绿；下载主包0.2.9/code11 SHA5358a42bbc5aaa84fcb517a69d56f4cf69f63e609122cba85978786dfda405d3、8237316B；test APK无AGP version字段（不能假称code11），实际runner/target/fc08/v2/CRC绑定均绿。真实Gradle XML153/153、30 suites零skip。
- diagnostics43590599162绿、331原件取回并逐SHA/bytes复核，原3PNG/XML检查与全部15 keepalive反例门重验绿。普通冷进程外部HTTP3659、Android直接rawSocket133、host raw3784；外部EOF不支持原边界保留，不称all_raw_checks_passed；屏幕亮着Home5秒3探测，非真机十分钟。
- full43590641863仍RED，676原件/完整log已取。新cold-pink-dark instrumentation实际OK1，之后harvested=false且ADB shell/console5554失效，同型环境取证失败复发；独立只读取证正在定位，未改产品/原断言/GPU/SDK配置、不拿13个OK冒充full绿。
- 最新全绿收口仍阻塞于full；未写最终交付报告/不覆盖旧候选。真机仍pending归发起方。
