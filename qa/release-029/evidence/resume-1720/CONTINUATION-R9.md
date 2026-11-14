# 0.2.9第三轮 R9补证准确断点

本文件仅当前事实，不是交付完成证明。旧CONTINUATION-9e300f9/R8与全部RED原件不覆盖。

- HEAD仍44df9d0fd36aecaa22613e9aa73c5c7d4ed94416；release/0.2.9-20261114，R9为未提交QA-only补证。
- R8 build43590339873/Gradle153与diag43590599162均真实绿；main0.2.9/code11 fc08/v2/CRC、SHA5358a42bbc5aaa84fcb517a69d56f4cf69f63e609122cba85978786dfda405d3。diag331原件/3PNG/15flag负例独立绿。不是十分钟真机测试。
- R8 full43590641863最新RED cold-pink-dark instrumentation=OK1后harvest=false、ADB shell1/console5554拒绝。676原件全留；独立ROOT-CAUSE-FULL-R8.md逐行核。完整theme23绿、palette59部分图绿，不算full通过。
- R9只新增cloud observer围一次原full记录emulator PID/memory/cgroup/console/dmesg/crashdata，不改child退出码/重试/配置。每次harvest自包含inline9语句记录原raw RC/stdout/stderr；逆恢复原AST。原72 app输入与所有已有断言不改；SDK/GPU/window/RAM保持原值。
- 新7测试首RED7→GREEN7；旧孤立helper测试首115 errors1确为外helper NameError，保留所有首source/log；改observer为inline，新增孤立加载RED3→GREEN7。旧test一字未改。
- 新JVM152、HTTP3784、Runtime1、Termux15状态200已重跑绿。完整Python115续件正在完成汇总（不能拿首错误当绿）。最新127项完整输入重新冻结final-review-r9-continuation，与之前r9不同且旧指纹保留，待新独立双轴。
- 待全回归绿+新双轴绑定→新精确提交/push/readback/CI→两新同源云端绿→新包不覆盖→最新报告+尾证据push→逐字独立读回。
- R9完整回归现在实际JVM152/152、Python115/115零skip、HTTP3784、Runtime1/1、Termux15 status200且closed均绿。最新127项/37产品/518052B累计diff已独立封至final-review-r9-continuation，原首r9指纹不覆盖；两新独立review在审、未push。
- 不碰真机/表端/表盘/Scope/签名材料；真机纯MCP链与10分钟后台继续pending归发起方。旧0.2.8/1.1.15/9e300f9候选三包保持原SHA/大小。
