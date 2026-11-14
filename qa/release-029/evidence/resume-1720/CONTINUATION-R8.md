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
