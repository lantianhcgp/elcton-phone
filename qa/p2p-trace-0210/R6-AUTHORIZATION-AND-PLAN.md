# R6 0.2.10 纯观测诊断版 — 2026-11-15授权与执行计划

## 用户本轮裁决（高于R5历史断点）

唯一焦点：修 L3-r2 → 完整回归与独立SPEC再QUALITY → 精确Android CI → 同证书验签/版本/SHA256 → APK非覆盖落Documents phone/。不发Release、不操作设备、不动表端/表盘/留白或/haps。

允许 versionCode 11→12、versionName 0.2.9→0.2.10及仅版本字面的断言/清单更新。
允许 WearProbe.kt / SyncEngine.kt / DiagnosticRuntime.kt 三个获批纯观测diff身份门迁移，新增P2pTrace.kt身份登记；报告列旧SHA→R5 SHA→R6 SHA。迁移是新源码钉扎，不改行为断言，不放宽匹配条件、不skip任何旧测试，原拒绝/RED/旧身份原件全保留。
其余9461基线条目保留，版本与身份迁移的明确例外单独登记；35原JVM测试类库存及全部业务断言冻结，表端445/445源码冻结。不得把旧0.2.9绿件算新源绿。

依据：R4 PHONE-DIAGNOSTIC-PATCH-PLAN.md全文已读；R5精确断点commit de3e6f182c2def5a52d33f33684777f1fc941ccd已从本地及GitHub API取证；r5-spec-r2.json真实拒绝已核。

## L3-r2最小修复合同

合法READY后sendAttempts.invalidate原guard已拒绝HELLO attempt；adapter Task/SendResult不得继续标stale=false。
先新增真实afterREADY adapter HOST反例：每个Task仅一个终态，success/failure/result独立实例；用真实WearProbe/SyncEngine发送与READY方法、fake SDK seam，断言两层标签一致及ready状态/业务调用/定时器不变。先运行取得目标真RED，失败原件封存。
只在新诊断状态/已有闭包同步attempt有效性；不更改READY条件、SendAttempts类、SDK回调业务原句、原generation/attempt守卫、定时器/重试/cleanup顺序。不增加SDK调用/Receiver/服务/线程。

## 顺序与职责

1. 父：源码/R5输入/基线条目封存、授权登记、唯一Documents进度更新；子代理唯一产品writer。
2. writer：新反例真RED→最少诊断修复→GREEN，原SDK oracle复跑；只改3获批源码/P2pTrace、新增测试/独立HOST夹具；无git提交/CI/设备。
3. 父：仅版本与身份迁移，保留原门禁manifest新旧可逆来源，不改业务断言。必要时新manifest承载授权delta，旧证据不改。
4. 最终源完整JVM/全部133 Python/真实HTTP/Runtime/HOST/真实Huawei jar typecheck/表445；每lane新目录输出、输入SHA/命令/原返回码/skip统计。
5. 完整当前diff+新增文件+R4/R6合同绑定指纹，独立SPEC PASS后再独立QUALITY；最多两轮针对性修正，拒绝件保留。未过不出包。
6. 白名单stage产品/测试/QA身份迁移（不stage生成kt/jar/token/旧局部数据）；精确commit不推master，只隔离branch；dispatch原build.yml（不改冻结workflow）。绑定head/run/attempt/artifact，执行Android真实单测/HTTP/原云端仪器与UI门，不替换为HOST。
7. apksigner verify -v --print-certs，同certificate SHA256 fc08a0b474a8ffca5887bd5c88ac15e865a63a64eca81c10f344496c46d9ad94；真实binary package/version= com.hcbiu.elcton /12/0.2.10；SHA256及实际新观测字节核验。
8. APK非覆盖落 /storage/emulated/0/Documents/elcton-WearEngine-真机联调-20261113-123000/phone/；DELIVERY含版本/源码身份表、真实test/CI/readback证据、真机根因unknown。
9. 证据主要GitHub；Documents仅唯一进度+用户明确请求DELIVERY/包，不新建散乱证据。凭据/token不回显不入仓，旧数据不删除。

## 资源

14:08本机剩余约1.33GB（实测）；不在手机安装/构建Gradle，不启动Chromium/常驻服务。HOST编译串行或最多一个重编译，CI并行可用；生成夹具在独立临时/证据目录，不进入qa递归Gradle sourceSet。
