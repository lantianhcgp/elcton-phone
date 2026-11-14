# 0.2.9第三轮 R10准确时限断点（未全绿交付）

本轮运行时限已到；此文件只记录已真实执行事实，不是完成报告。此前CONTINUATION-9e300f9/R8/R9及首RED/重跑RED/拒绝审查/失败脚本原件均保留。

## 精确源码/已完成阶段

- 工作目录：/data/data/com.termux/files/home/elcton-phone-release-029-20261114
- 分支：release/0.2.9-20261114；HEAD仍44df9d0fd36aecaa22613e9aa73c5c7d4ed94416，远端已一致。当前R9/R10 QA-only观测变更未commit/push。
- R8两条McpKeepAliveTest返回命令补MAIN/LAUNCHER，不改既有断言/产品。原line136根因及原测试字节备份在resume-third/ROOT-CAUSE-KEEPALIVE.md、McpKeepAliveTest.kt.before.original；新4例实际RED2→GREEN4。
- R8双轴125 reviewed/37 products、499323B累计diff精确绿并封；原R8回执在final-review-r8。
- R8 build43590339873真实success，Gradle XML153/153零失败零skip、30 suites；主APK0.2.9/code11固定fc08证书、v2/CRC绿，8237316B、SHA5358a42bbc5aaa84fcb517a69d56f4cf69f63e609122cba85978786dfda405d3。testAPK实际AGP无版本字段（不能称code11），runner/target/fc08/v2/CRC已验。二进制/原验证失败在download-44df9d0；实际最终receipt=actual-binary-verification-continuation-2/receipt.json。
- 44df9d0全部2099文件远端tar逐字读回一致，回执remote-44df9d0-readback/all-files-readback.json。
- diagnostics43590599162真实success，331原件取回与逐SHA/bytes复核；原3PNG/XML复算、15 keepalive flag负例拒绝全部绿，原scope与普通Home亮屏5秒3探测/实际notification STOP保留。外部HTTP3659+Android直Socket133+host raw3784；外部writeEOF不支持仍明示，不假称所有raw外链通过。独立receipt=resume-third/diag-independent-verification.json。

## 当前真实阻塞

- full43590641863失败，676原件在full-44df9d0-evidence/，原失败log在full-44df9d0-failure/actual.log。
- 新cold-pink-dark instrumentation实际OK1后harvest=false；补采ADB shellRC1、cleanup时console5554拒绝连接。完整theme23过、palette59部分图过/13期仪器OK，不是full完整通过。独立ROOT-CAUSE-FULL-R8.md；底层模拟器消失具体机制未封，不能直接说GPU/OOM原因已证。
- 当前旧两云端结论只属于44df9d0；后续QA改动必须重新全回归/全审查/精确出包/两新同源云端，不能继承旧success为最新通过。

## R9补证与独立拒绝（原件不覆盖）

- 加qa/cloud_emulator_observer.py cloud-only包装原full一次，host emulator PID/meminfo/cgroup/console/dmesg/crashdata；palette harvest只追加raw stdout/stderr/RC。SDK/GPU/window/RAM/heap与产品不改。
- 首external helper让旧harvest孤立装载测试NameError，Python115 errors1完整保留。改observer为inline自包含，旧test不改，完整Python115/115零skip、JVM152/152、HTTP3784、Runtime1/1、Termux15 200+closed实绿；在resume-third/r9。
- 冻结R9-continuation127/37与518052B差分，但两原轴拒绝：SPEC3logic、STANDARDS1security4logic。raw=final-review-r9-continuation/spec-raw.txt（SHA7a8864c81c6fb7755a6d33e30b870fbd11a254f9c6c03af90f15fed3d2f6d380）、standards-raw.txt（SHA3c28026a015ffa0055580efb14ad78b4aa19a150dc4286428bc26a61cc0e7eea）。禁push这一旧拒绝指纹。
- 问题：observer写盘影响harvest，receipt/采样启动失败改变child执行/exit，负信号SystemExit不等价，join无限阻塞，crash symlink逃逸。原代码/finding/合成反例保存resume-third/r9/review-corrections。

## R10现在已真实修/验（仅QA观察层）

- palette wire完整自包含diagnostic-only try+with，任何观察异常不跳原error/parse/return；逆删除该块后原完整harvest文件逐字节一致。
- observer目录/线程启动/采样/收尾/receipt全部诊断隔离；原child只Popen一次、真实返回不被观察错误替换。daemon观察线程+1秒有界join；native SIGTERM/SIGPIPE/SIGKILL原样重新发信号，负数不直接sys.exit。
- crash仅明确emu-crash-*和.dmp，源/输出dirfd逐祖先O_NOFOLLOW，拒symlink/hardlink/路径逃逸，文件32MiB/累计64MiB有界复制。观察捕获可能失败会明确记录，不能拿补证失败替代child成功/失败。
- qa/test_cloud_observer_isolation.py新8测试实际RED4fail5error→原7+新8共15/15绿；SIGKILL新增subcase首夹具signal设置误用及修正原件全留，最后SIGTERM/SIGPIPE/SIGKILL均原生等价绿。
- R10真实JVM重新编译/执行152/152绿（host-final-r10）；15隔离最终绿（resume-third/r10/observer-isolation-final.log/.exit）；旧52测试源码、37产品完全不动，完整harvest逆字节绿（resume-third/r10/immutable-and-isolation.json）。
- R10完整Python（将包含原115+新增8）、HTTP/Runtime/Termux尚未执行；尚未生成R10最新freeze/独立review/新CI/两新云端，不允许自称最新全绿。

## 下一棒最短主链

1. 先核当前QA文件/原false回执/新15+JVM实际日志与git状态，严守未commit/push的R10身份。
2. 完整Python discover用真实CP：MCP_HTTP_TEST_CLASSPATH=/data/data/com.termux/files/home/elcton-phone-release-029-20261114/qa/release-029/evidence/resume-1720/host-final-r10/host-tests.jar:/data/data/com.termux/files/home/.hermes/tmp/elcton-jvm-test/json.jar；PYTHONDONTWRITEBYTECODE=1；python -B -m unittest discover -s qa -p 'test_*.py' -v；实际数量/零skip从日志核，不凭预计123报成功。
3. HTTP3784、Runtime、Termux15生产类listener200+closed完整执行，独占新日志，全部旧日志保留。
4. git add新增qa/test_cloud_observer_isolation.py等让prepare包含新文件；prepare_candidate.py生成独占final-review-r10。两新独立SPEC/STANDARDS必须实际绑定最新所有输入，重点R9拒绝反例全部修完、范围/退出码/资源/路径；不能改旧false或继承旧green。
5. 两回执真绿→seal最新指纹→秘密扫描→独立release分支commit/push/readback→精确新build及实际main/test二进制签名/版本/XML验收。所有当前新增证据（含reject/失误）提交到仓库，不删原件。
6. 同最新source/build串行注册diagnostics/full再并行等待。带observer的full第一次可给模拟器消失确切证据，不保证一定绿；若RED取证根因再最小修复，不改原判据/GPU配置猜绿。
7. 两云端完整绿→新APK独占Documents文件（不覆盖9e300f9候选）→真实最新数量/证据范围的最终报告→尾部证据push→全部远端字节独立读回。

## 保护与交付边界

- 原9e300f9候选：/storage/emulated/0/Documents/elcton-WearEngine-真机联调-20261113-123000/phone/hc课程表-0.2.9-code11-9e300f9-合并版-signed.apk，SHA15aafee2af9509bc61f3780f74cef712fc47dfdedcb487cdd34e7d59d9a1d8b7。
- 旧0.2.8 APK、1.1.15 HAP原SHA/bytes与该候选均不动，最近protected-deliveries-before-final.json已验三项。
- 本轮没有安装/拉起/点击/ADB真机、表端/表盘/Scope/签名材料操作；真机纯MCP「导入→同步→回读」、后台10分钟health/error_tail始终pending归发起方。
- 未创建/交付全绿报告、未把44df9d0主包复制覆盖候选；不能把本文件当完成交付。
- 手机本轮最近检查无java/chromium/emulator重进程残留。存储最近只有约1.6GB空余；不自动删数据，必要仅保真压缩归档。

## 第四轮续写：R10全HOST已绿，新审查中

- 2026-11-14实际新回归全部执行：JVM152/152；Python123/123零skip（原115+新增8）；HTTP3784；Runtime1/1；Termux15项HTTP200+listenerclosed。每项原log/execution SHA真核，运行输入全SHA不变。完整回执=resume-fourth/gates-r10/complete.json。
- 精确逆恢复与旧源保护=resume-fourth/exact-preservation.json：37产品、35App测试原bytes不动，harvest全文件去新增独立try+注释逐字节等同基线，workflow仅单wrapper替换。
- 保护旧包三件=resume-fourth/protected-inputs-at-start.json。没有真机ADB/MCP/前台操作。
- 新freeze=final-review-r10-fourth，reviewed128/product37，reviewed_manifest_sha256=a7981889ef03ecc15a99f0ca745e69e9f27e1fab8bd0af7ebd7476ed23e58f81，product_manifest_sha256=72a773083cecfef06f9fdf43f423f38b8948c0108e2e3235bf078056b3651138，diff533891B/SHA1e0b25c34289899baa580ca2d035c655c93d713a14719aec10443af0afe45f44。
- 新独立SPEC/STANDARDS审查并行已发：raw将分别独占新增，旧R9false两件不动。通过前不commit/push，旧full43590641863仍RED。准备最新通用独立artifact复验工具中；不得把准备工具或旧diag绿当新云端PASS。

## 第四轮 R11真实续写（最新全HOST绿，新双轴pending）

- R10新的SPEC1security/STANDARDS1security1logic真实拒绝，两个raw原件都保留；祖先symlink/index词法写TOCTOU和empty-files/unbounded scans实证，不push此false输入。父安全5反例首跑RED3、资源5反例首跑RED3/2error原件全保留。
- R11只改QA crash观察：所有祖先逐组件O_PATH/NOFOLLOW，源/目标/index各pinned dirfd；scan≤256、copy≤64、depth≤8、index≤32768、原32/64MiB帽同；缺O_PATH/打开失败只跳观察。原child/harvest判据/重试/exit与产品不改。首修Android根O_RDONLY权限失败、scope locator两次错误原件保留，修的是新观察器不改产品/旧断言。
- R11新增安全5+资源5、父原5全部实际GREEN；旧54个既有测试文件与37产品逐字节相同；去独立观测try+精确新增注释整文件还原原harvest字节相同。证明=resume-fourth/r11/scope-verified.json。
- 最新完整实际回归=resume-fourth/gates-r11/complete.json：JVM152/152、Python133/133零skip、HTTP3784、Runtime1/1、Termux15项HTTP200+listenerclosed；152运行输入全SHA不变。旧回归不是替代证据。
- 新freeze=final-review-r11-fourth；130files/37products/549989B；reviewed856a6c8f94f63a47ec8fdf0192015d01ccc59d138c14bbcafd5cd58279d74534；diff0173d7ecf6e7bc92cfe2d359e0cb6f8630e5641cb68a9b6ea0079e06648ddd14；product72a773083cecfef06f9fdf43f423f38b8948c0108e2e3235bf078056b3651138；两独立轴已启动，绿前仍禁push。
- 676旧full原件父逐项SHA通过；cold-pink-dark测试OK后harvest失败、ADB RC1/console5554拒连已证，OOM/GPU根因未证实。合法解=新云runner同原配置全跑，不改原断言/产品。两最新云端尚未跑；HEAD仍44df9d0，真机两项仍pending归发起方。
- 新通用云artifact校验器已由父对旧diag绿、旧full红及3mutations独立实跑自证；它不是最新云端PASS。精确build原44df9d0的153/153与fc08/v2也由新校验器实跑自证，仍不替代最新build。
- 三件保护旧包最新核验=resume-fourth/r11/protected-deliveries-exact.json，SHA原样；没有真机ADB/MCP/前台操作。
