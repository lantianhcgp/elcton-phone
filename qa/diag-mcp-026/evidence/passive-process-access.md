# 非前台 MCP 唤醒取证

为避免真机验收 `am start` 抢占前台，核对 0.2.5 APK 自带的 AndroidX ProfileInstaller Receiver：

- APK 内 `META-INF/androidx.profileinstaller_profileinstaller.version` = `1.3.1`。
- 0.2.5 AndroidManifest.xml 声明 `androidx.profileinstaller.ProfileInstallReceiver` 为 exported=true，受 `android.permission.DUMP`（adb shell）保护。
- Google Maven 官方 `profileinstaller-1.3.1-sources.jar` 中 `ProfileInstallReceiver.onReceive`：仅在四个固定 `androidx.profileinstaller.action.*` 动作匹配时做 profile/cache 操作；其他 action 直接返回。
- 因此本次可用一个不匹配原分支的显式诊断 action，让已有 Receiver 仅触发 Application 创建；不打开 Activity、不请求 WE 授权/扫描、不执行 profile 写入或删除。
- 这是待真实运行验证的访问办法，不是已验证成功或新增产品接口。最终以实际 broadcast、PID、forward、HTTP 与前台组件前后对比为证据。

官方源码： https://dl.google.com/dl/android/maven2/androidx/profileinstaller/profileinstaller/1.3.1/profileinstaller-1.3.1-sources.jar
