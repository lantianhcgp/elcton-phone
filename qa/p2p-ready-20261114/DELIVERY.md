# 手机P2P准备回执0.2.8/code10候选交付

构建源码2097f32ab9ef573e060ef42d076799c9c274e38b，精确CI43568230547：https://github.com/lantianhcgp/elcton-phone/actions/runs/43568230547。

实际包已取回并独立aapt2/apksigner验证；包名com.hcbiu.elcton，0.2.8/code10，v2/v3有效，证书仍fc08a0b474a8ffca5887bd5c88ac15e865a63a64eca81c10f344496c46d9ad94。

路径：/storage/emulated/0/Documents/elcton-WearEngine-真机联调-20261113-123000/phone/hc课程表-0.2.8-code10-2097f32-p2p-signed.apk
8183987字节，SHA256=d5778fd80f1bd3758d0c9f2cead660af49aaf6912e2638dc16616bec808bc633。

CI22 suites/89 tests/0 failures/0 errors/0 skipped。原JUnit20文件逐字不改，默认冻结8/0.2.6不改；本棒CI显式-PelctonP2pCandidate=true生成候选10/0.2.8，真实BuildConfig和最终二进制manifest分开硬验证。纯host88/88，Python75/75，真实Kotlin MCP HTTP自测1164断言通过。

手机仅在等待READY、没有活动事务、PacketIngress已校验且空transferId的准备ERROR显示实际码；原ACK/APPLIED/授权/日志/MCP安全契约不动。超时文案不再归咎用户未点开始接收。未自动安装/拉起App，真实联调归用户。

搭配表源73c7823ca69deb5e176df52dda89fd02940db67c的1.1.15/code1000118、watchapp.nexus.0zzip；HAP SHA256=8865474d76d278f6d61050f4cebca1c1a70b0f5f391f653523d9c9018c91bac0。

完整源码根因/官方引文/判读检查单（表仓同分支）：
https://github.com/lantianhcgp/elcton/blob/fix/p2p-ready-receipt-20261114/qa/p2p-ready-20261114/ROOT-CAUSE.md
https://github.com/lantianhcgp/elcton/blob/fix/p2p-ready-receipt-20261114/qa/p2p-ready-20261114/DELIVERY.md

交付证据为后续[skip ci]文档提交，产品文件与2097f32构建字节完全相同。真机READY/206/APPLIED尚未验，禁止把SDK/CI绿冒充真机成功。
