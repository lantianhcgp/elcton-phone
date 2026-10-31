# 同步首阶段开发检查点

已确认：公开手机仓库、手机主编辑、手表查看/删除/导出、不自动合并；尽可能Wear Engine手表，FIT3主真机；自主验收朋友hmlwsim。

当前：手机目录 elcton-phone；手表独立 elcton-wear-sync/feat/wearengine-sync（基线feat/lan-sync-probe，不是旧master）；模拟器独立 elcton-sim-qa/qa/elcton-wearengine。

已验证：表端Node 18项测试通过，涉及协议、回执、双槽、重启回读、表端删除、模拟器file.get与UTF-8偏移。手机SDK5.0.3.301实际AAR已javap验证；公开身份匹配配置已生成，秘密留仓库外。

未完成：手机Wire/DevicePolicy与通信UI、CI产物、hmlwsim真正点击多尺寸巡检、代码审查与推送。表端自动拉起/后台生命周期、多运行时安装包、导出回传完整UI为后续阶段，不得称成品。

恢复：先运行 elcton-wear-sync 的 node --test tests/*.test.mjs，读Documents/课表同步方案/首阶段实施计划.md，再核对git状态。

阻塞：申请状态最新只读请求resultCode1004 auth failed，不能据此判已开通/拒绝；手机生产签名指纹尚未登记控制台。继续实现模拟测试，不停工，但真实Wear Engine同步待验证。
