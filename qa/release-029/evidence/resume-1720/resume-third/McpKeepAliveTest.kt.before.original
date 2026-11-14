package com.hcbiu.elcton

import android.Manifest
import android.app.NotificationManager
import android.content.Intent
import android.os.Build
import android.provider.Settings
import androidx.compose.ui.test.*
import androidx.compose.ui.test.junit4.createAndroidComposeRule
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import androidx.test.uiautomator.UiDevice
import org.json.JSONObject
import org.junit.Assert.*
import org.junit.rules.ExternalResource
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import java.io.File
import java.net.InetSocketAddress
import java.net.Socket
import java.net.ServerSocket
import androidx.test.uiautomator.By
import androidx.test.uiautomator.Until
import java.security.MessageDigest

/** Emulator-only public settings/service/HTTP lifecycle; never touches a real phone or WE. */
@RunWith(AndroidJUnit4::class)
class McpKeepAliveTest {
    // Destructive last fixture only: reset the earlier explicit STOP choice before Activity launch.
    // Suppress only the one-shot OS prompt; denial must still retain intended-on.
    @get:Rule(order = 0) val freshDeniedChoice = object : ExternalResource() {
        override fun before() {
            val i = InstrumentationRegistry.getInstrumentation()
            check(InstrumentationRegistry.getArguments().getString("diag_emulator") == "true")
            i.targetContext.getSharedPreferences("mcp_session", 0).edit()
                .remove("keep_running").putBoolean("default_notification_prompted", true).commit().also { check(it) }
        }
    }
    @get:Rule(order = 1) val ui = createAndroidComposeRule<MainActivity>()
    private val instrumentation get() = InstrumentationRegistry.getInstrumentation()
    private val device get() = UiDevice.getInstance(instrumentation)
    private fun files(): Map<String, String?> = listOf("timetable.json", "timetable-last-good.json", "diagnostics/wear-errors.jsonl", "mcp/token").associateWith {
        val file = File(ui.activity.filesDir, it)
        if (file.isFile) MessageDigest.getInstance("SHA-256").digest(file.readBytes()).joinToString("") { b -> "%02x".format(b) } else null
    }
    private fun health(): Boolean = Socket().use { socket ->
        socket.connect(InetSocketAddress("127.0.0.1", 8766), 1500); socket.soTimeout = 3000
        socket.getOutputStream().apply { write("GET /health HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\n\r\n".toByteArray()); flush() }
        socket.getInputStream().readBytes().toString(Charsets.UTF_8).startsWith("HTTP/1.1 200 ")
    }
    private fun stopped(): Boolean = try { Socket().use { it.connect(InetSocketAddress("127.0.0.1", 8766), 500) }; false } catch (_: java.io.IOException) { true }

    @Test fun defaultOffOptInKeepsBackgroundHttpAndOffStopsPort() {
        val args = InstrumentationRegistry.getArguments()
        check(args.getString("diag_emulator") == "true") { "Emulator harness only" }
        val source = args.getString("diag_source_sha") ?: error("Missing checkout SHA")
        val runtime = (ui.activity.application as ElctonApplication).diagnostics
        val manager = ui.activity.getSystemService(NotificationManager::class.java)
        val report = JSONObject().put("passed", false).put("sourceSha", source).put("qaRun", args.getString("diag_run"))
            .put("scope", "real Android emulator; no WE calls or real phone installation")
        val directory = File(ui.activity.filesDir, "qa-diag-evidence").apply { mkdirs() }
        val output = File(directory, "keepalive-report.json")
        output.writeText(report.toString())
        val before = files()
        try {
            assertTrue(McpKeepAlive.enabled(ui.activity))
            ui.onNodeWithTag("nav-settings").performClick()
            ui.onNodeWithTag("mcp-keepalive-switch").performScrollTo().assertIsOn()
            report.put("defaultOn", true)
            if (Build.VERSION.SDK_INT < 33) {
                ui.waitUntil(10000) { McpKeepAlive.active }
                assertTrue(manager.activeNotifications.any { it.id == McpKeepAlive.NOTIFICATION_ID })
            }
            if (Build.VERSION.SDK_INT >= 33) {
                assertFalse("permission denied must not start a service", McpKeepAlive.canNotify(ui.activity))
                assertFalse(McpKeepAlive.enable(ui.activity))
                assertTrue("permission denial is not user opt-out", McpKeepAlive.enabled(ui.activity))
                assertFalse(McpKeepAlive.active)
                assertFalse(runtime.read().getJSONObject("mcp").getBoolean("running"))
                assertTrue("denial closes the real loopback listener", stopped())
                assertFalse(manager.activeNotifications.any { it.id == McpKeepAlive.NOTIFICATION_ID })
                ui.onNodeWithTag("mcp-keepalive-switch").assertIsOn()
                report.put("permissionDeniedFailClosed", true).put("defaultOnNoPermissionRetainsChoice", true)
                    .put("noNotificationWithoutPermission", true)
                instrumentation.uiAutomation.grantRuntimePermission("com.hcbiu.elcton", Manifest.permission.POST_NOTIFICATIONS)
            }
            // Exercise the real foreground Service's bind failure, not a mocked result.
            ui.runOnUiThread { McpKeepAlive.disable(ui.activity) }
            ui.waitUntil(10000) { stopped() }
            ServerSocket().use { occupied ->
                occupied.reuseAddress = true
                occupied.bind(InetSocketAddress("127.0.0.1", 8766))
                ui.runOnUiThread {
                    assertTrue(McpKeepAlive.enable(ui.activity))
                    assertFalse("a queued service start is not active", McpKeepAlive.active)
                }
                ui.waitUntil(10000) { McpKeepAlive.enabled(ui.activity) && !McpKeepAlive.active &&
                    !runtime.read().getJSONObject("mcp").getBoolean("running") && McpKeepAlive.failure.contains("端口启动失败") }
                ui.onNodeWithTag("mcp-keepalive-switch").assertIsOn()
                ui.onNodeWithTag("mcp-keepalive-status").performScrollTo().assertIsDisplayed()
                    .assertTextEquals("MCP 端口启动失败；保持运行未启动，开启偏好已保留")
                // No click or ON_RESUME: the already-visible settings must publish failure.
                ui.waitForIdle()
                ui.onNodeWithTag("mcp-keepalive-status").assertTextEquals(McpKeepAlive.failure)
            }
            assertTrue("after releasing the test socket no product listener remains", stopped())
            report.put("bindFailureUiOnAndHintRetained", true).put("startingNotActive", true)
            // Retained-on is inactive after bind failure; explicitly turn off then on to retry.
            ui.onNodeWithTag("mcp-keepalive-switch").performScrollTo().assertIsOn().performClick()
            ui.onNodeWithTag("mcp-keepalive-switch").assertIsOff().performClick()
            ui.waitUntil(10000) { McpKeepAlive.active && runtime.read().getJSONObject("mcp").getBoolean("running") }
            ui.onNodeWithTag("mcp-keepalive-switch").assertIsOn()
            assertTrue(McpKeepAlive.enabled(ui.activity)); assertTrue(health())
            assertTrue(manager.activeNotifications.any { it.id == McpKeepAlive.NOTIFICATION_ID })
            ui.onNodeWithTag("mcp-keepalive-switch").performScrollTo()
            val image = File(directory, "mcp-keepalive-on.png")
            assertTrue(device.takeScreenshot(image))
            device.dumpWindowHierarchy(File(directory, "mcp-keepalive-on.xml"))
            assertTrue(device.pressHome())
            assertTrue("real HTTP responds with Activity backgrounded", health())
            report.put("onNotification", true).put("backgroundHttp", true)
            // Returning to the emulator's already-created Activity is not a phone foreground action.
            ui.runOnUiThread { McpKeepAlive.disable(ui.activity) }
            ui.waitUntil(10000) { !McpKeepAlive.active && !runtime.read().getJSONObject("mcp").getBoolean("running") }
            assertTrue("switch-off must close the actual listener", stopped())
            assertFalse(McpKeepAlive.enabled(ui.activity))
            assertFalse(manager.activeNotifications.any { it.id == McpKeepAlive.NOTIFICATION_ID })
            assertEquals(before, files())
            report.put("offPortClosed", true).put("offNotificationRemoved", true).put("businessAndTokenAndErrorsUnchanged", true)
                .put("stopDisablesChoice", true).put("stopInactive", true)
            // Use the actual system channel UI while the Activity stays backgrounded.
            // App-side channel mutation or an explicit resumeChoice would mask this defect.
            device.executeShellCommand("am start -n com.hcbiu.elcton/.MainActivity")
            assertTrue(device.wait(Until.hasObject(By.pkg("com.hcbiu.elcton")), 10000))
            ui.onNodeWithTag("mcp-keepalive-switch").performScrollTo().assertIsOff().performClick()
            ui.waitUntil(10000) { McpKeepAlive.active && runtime.read().getJSONObject("mcp").getBoolean("running") }
            ui.onNodeWithTag("mcp-keepalive-switch").assertIsOn()
            assertTrue(device.pressHome())
            assertTrue("listener must be live before the system UI blocks the channel", health())
            try {
                instrumentation.targetContext.startActivity(Intent(Settings.ACTION_CHANNEL_NOTIFICATION_SETTINGS)
                    .putExtra(Settings.EXTRA_APP_PACKAGE, instrumentation.targetContext.packageName)
                    .putExtra(Settings.EXTRA_CHANNEL_ID, McpKeepAlive.CHANNEL)
                    .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK))
                assertTrue("system notification settings must be visible",
                    device.wait(Until.hasObject(By.pkg("com.android.settings")), 10000))
                // AOSP API 33/34 uses a Settings switch; older releases may use android's ID.
                val channelSwitch = device.wait(Until.findObject(By.res("com.android.settings", "switch_widget")), 5000)
                    ?: device.wait(Until.findObject(By.res("android", "switch_widget")), 5000)
                    ?: error("System channel notification switch not found")
                assertTrue("channel switch must initially allow notifications", channelSwitch.isChecked)
                channelSwitch.click()
                val deadline = android.os.SystemClock.uptimeMillis() + 10000
                while (manager.getNotificationChannel(McpKeepAlive.CHANNEL)?.importance != NotificationManager.IMPORTANCE_NONE &&
                    android.os.SystemClock.uptimeMillis() < deadline) {
                    android.os.SystemClock.sleep(100)
                }
                assertEquals(NotificationManager.IMPORTANCE_NONE, manager.getNotificationChannel(McpKeepAlive.CHANNEL)?.importance)
                assertFalse(McpKeepAlive.canNotify(ui.activity))
                assertTrue(device.pressHome())
                // Do not resume MainActivity (or call resumeChoice) before these assertions.
                val stoppedDeadline = android.os.SystemClock.uptimeMillis() + 10000
                while ((!McpKeepAlive.enabled(ui.activity) || McpKeepAlive.active ||
                    runtime.read().getJSONObject("mcp").getBoolean("running") || !stopped() ||
                    manager.activeNotifications.any { it.id == McpKeepAlive.NOTIFICATION_ID }) &&
                    android.os.SystemClock.uptimeMillis() < stoppedDeadline) {
                    android.os.SystemClock.sleep(100)
                }
                assertTrue("notification denial must retain opt-in without Activity resume", McpKeepAlive.enabled(ui.activity))
                assertFalse(McpKeepAlive.active)
                assertFalse(runtime.read().getJSONObject("mcp").getBoolean("running"))
                assertTrue("background notification loss must close the actual listener", stopped())
                assertFalse(manager.activeNotifications.any { it.id == McpKeepAlive.NOTIFICATION_ID })
                report.put("backgroundChannelDeniedEventStops", true)
            } catch (error: Throwable) {
                device.dumpWindowHierarchy(File(directory, "mcp-channel-denied-failure.xml"))
                device.takeScreenshot(File(directory, "mcp-channel-denied-failure.png"))
                throw error
            }
            device.executeShellCommand("am start -n com.hcbiu.elcton/.MainActivity")
            assertTrue(device.wait(Until.hasObject(By.pkg("com.hcbiu.elcton")), 10000))
            ui.onNodeWithTag("mcp-keepalive-switch").assertIsOn()
            assertEquals(before, files())
            report.put("activeChannelDeniedStopsAndUiOn", true).put("passed", true)
        } finally {
            // Channel NONE may persist: the parent harness runs this instrument last.
            // Deleting/recreating the same channel can resurrect its blocked importance.
            ui.runOnUiThread { McpKeepAlive.disable(ui.activity) }
            output.writeText(report.toString())
        }
    }
}
