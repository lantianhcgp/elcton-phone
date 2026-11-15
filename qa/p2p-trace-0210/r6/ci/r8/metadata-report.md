# R8 metadata adapter — 仅离线 helper 验证

- 原 R6 finalizer 与 git show b3eb5568 逐字节相等、未编辑；旧 R6 DELIVERY.md 未改。
- 仅五处输出元数据：L75 源码 sha8 诊断包名；L92 DELIVERY-R8 标题；L116/L117 DELIVERY-R8.md；L118 PHONE/DELIVERY-R8.md（原 x 写法保留）。
- 精确逆变换恢复原字节；仅枚举元数据规范化后完整 AST 相等；所有原安全/签名/manifest/源码/closure/run/PASS/size/hash/路径断言保留。
- R8 全部输出目标（含报告）先做只读不存在/非符号链接/无穿越预检；源码固定为授权 b3eb55680b51f5fbdf392d402acdcdae168f2b20，不取 workflow HEAD。
- 真实离线测试：18 PASS，0 FAIL，0 ERROR，0 SKIP，exit 0。初始 RED：18 FAIL，exit 1，原 log 保留。
- 四项非元数据篡改负测（v2 bool/identity/cert/artifact name）、碰撞/符号链接/穿越/源码身份负测通过。真实 wrapper 仅在临时隔离目录拒绝碰撞或触发原 false-PASS 守卫；无伪成功交付回执。
- 未执行交付、联网、构建、设备、commit/push，未写真实 phone 路径。父会话须另行全门禁/独立评审，不将 helper PASS 当交付 PASS。
- 原 Q/out 报告 write_text 保持不变；预检不是并发锁，PHONE 原 x/xb 保留。

原 SHA256：5e631132ed51fcea7a4406dbdecfe75dcf1ea4edeec3531a2c05e1ff3fbcbe03

转换 SHA256：28c6ef9a01d6d783ffc93137ca10673b6afec5acbf1e1e740adaad055d79f2f7

证明：/data/data/com.termux/files/home/elcton-phone-diagnostics-0210-20261115/qa/p2p-trace-0210/r6/ci/r8/metadata-proof.json

测试日志：/data/data/com.termux/files/home/elcton-phone-diagnostics-0210-20261115/qa/p2p-trace-0210/r6/ci/r8/metadata-tests-green.log
