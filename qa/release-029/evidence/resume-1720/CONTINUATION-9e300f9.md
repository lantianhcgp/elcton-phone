# 0.2.9 续跑终态：最新包已出，完整Android验收仍RED

本轮再达运行时限；此文件是准确断点，不是完成证明。全部旧证据、首失败、重跑失败保留。

## 当前精确输入
- 工作目录：/data/data/com.termux/files/home/elcton-phone-release-029-20261114
- APK源码提交：9e300f9f7c56bddb2151e63d6a160c5bc645db93
- 分支：release/0.2.9-20261114；不碰master/表端/表盘/Scope。
- 最新R7独立双轴原始回执：final-review-r7/spec-raw.txt、standards-raw.txt；原始passed=true且无阻塞项。完整124输入/37产品文件精确绑定；产品与17443eb一致。
- R6补回Activity持久化diagnostic显示，原34个Kotlin测试未变。
- R7只补云端UI通知预授权环境，新夹具4例RED→GREEN；原UI断言、业务与签名不变。

## 确实已过
- Python104/104零skip；生产JVM152/152；HTTP3784断言；Termux15工具清单200，收尾监听关闭。
- 精确构建43586510256 success，实际Gradle XML153/153零失败零skip（30套XML）。主APK/测试APK均固定完整公证书fc08a0b474a8ffca5887bd5c88ac15e865a63a64eca81c10f344496c46d9ad94；实际aapt2读0.2.9/code11，APK v2验签通过。
- 主APK新文件独占落盘：/storage/emulated/0/Documents/elcton-WearEngine-真机联调-20261113-123000/phone/hc课程表-0.2.9-code11-9e300f9-合并版-signed.apk
- APK8237316B，SHA256=15aafee2af9509bc61f3780f74cef712fc47dfdedcb487cdd34e7d59d9a1d8b7。
- 远端独立归档逐字读回1047文件、157791457B，回执remote-code-readback-9e300f9/all-files-readback.json。该回执覆盖9e300f9当时树，不覆盖后写尾部证据。
- 旧0.2.8 APK SHA d5778fd80f1bd3758d0c9f2cead660af49aaf6912e2638dc16616bec808bc633，旧1.1.15 HAP SHA 8865474d76d278f6d61050f4cebca1c1a70b0f5f391f653523d9c9018c91bac0，独占复制后复核未变。

## 最新真实Android RED（不能冒作全绿）
1. diagnostics43586767169 failure：完整artifact已取回diag-9e300f9-evidence/artifact/，319项下载清单及原完整日志在同目录。原diagnostic入口失败已越过，instrumentationReceipt.passed=true；host已到keepalive-instrumentation，但最终passed=false。keepalive-instrumentation.log实报McpKeepAliveTest.kt:136 performScrollTo找不到testTag=mcp-keepalive-switch。对应原测试顺序：pressHome、disable、实际停止断言、am start MainActivity、UiDevice包出现后，直接查开关。下一棒先读该测试完整上下文、实际截图/XML/logcat，再区分Activity重建/导航恢复/观测时序，禁止改断言凑绿。
2. full43586804691 failure，失败步骤Exercise real APK without a paired device。最新full artifact/日志尚未取回，具体失败原因未知，不沿用旧NoCompose错误推断。下一棒先按run+SHA取回准确artifact/失败日志。

## 剩余步骤（准确顺序）
- 先读取最新full失败及诊断line136实际取证，定位最小根因；所有测试不改绿、证据不删，超授权期待变更须先停靠。
- 若需修产品/QA，保留before/RED，重跑完整Python/JVM/HTTP并重新独立绑定完整最新源码+QA，不复用旧指纹。
- 同源精确CI及两套云端Android回归真正全绿后才能说交付层完成；新包独占文件名，不覆盖任何已落盘包。
- 最终报告依据实际新成功回执生成，不运行旧make_delivery_report.py（硬编码旧SHA/run）。final_report_from_actual.py也是未执行的严格模板，需先核最新报告schema；不得从模板当成成功输出。
- 最终尾部证据push/独立读回，再报告准确完成范围。

## 真机层
纯MCP导入→同步→回读、退后台10分钟health200/error_tail继续pending归发起方；本轮从未安装/启动/点击手机。云端只测有限Home亮屏保活，不能代替MIUI/Doze/实体手表证明。
