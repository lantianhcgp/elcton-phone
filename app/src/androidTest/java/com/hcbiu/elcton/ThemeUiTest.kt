package com.hcbiu.elcton

import android.content.Context
import android.content.res.Configuration
import android.graphics.BitmapFactory
import android.graphics.Rect
import android.os.Process
import android.view.View
import android.view.WindowInsets
import androidx.compose.ui.test.*
import androidx.compose.ui.test.junit4.createAndroidComposeRule
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import androidx.test.uiautomator.By
import androidx.test.uiautomator.UiDevice
import androidx.test.uiautomator.Until
import org.json.JSONArray
import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import java.io.File
import java.io.FileInputStream
import java.security.MessageDigest
import java.util.UUID
import java.util.concurrent.CountDownLatch
import java.util.concurrent.TimeUnit

/** Real UI actions. Host force-stops between phases to prove process-cold persistence. */
@RunWith(AndroidJUnit4::class)
class ThemeUiTest {
    @get:Rule val ui = createAndroidComposeRule<MainActivity>()
    private val instrumentation get() = InstrumentationRegistry.getInstrumentation()
    private val device get() = UiDevice.getInstance(instrumentation)
    private val args get() = InstrumentationRegistry.getArguments()
    private val phase get() = args.getString("theme_phase", "initial")!!
    private val navigationMode get() = args.getString("navigation_mode", "three-button")!!
    private val directory get() = File(instrumentation.targetContext.filesDir, "qa-theme-evidence").apply {
        check(isDirectory || mkdirs()) { "Cannot create theme evidence directory" }
    }
    private val preferences get() = instrumentation.targetContext.getSharedPreferences("ui-theme", Context.MODE_PRIVATE)
    private fun mode() = preferences.getString("mode", "LIGHT")!!
    private fun systemDark() = ui.activity.resources.configuration.uiMode and Configuration.UI_MODE_NIGHT_MASK == Configuration.UI_MODE_NIGHT_YES
    private fun bounds(rect: Rect) = JSONArray(listOf(rect.left, rect.top, rect.right, rect.bottom))
    private fun hash(file: File) = MessageDigest.getInstance("SHA-256").digest(file.readBytes()).joinToString("") { "%02x".format(it) }
    private fun shell(command: String): String = instrumentation.uiAutomation.executeShellCommand(command).use {
        FileInputStream(it.fileDescriptor).readBytes().toString(Charsets.UTF_8).trim()
    }
    private fun imePackage() = shell("settings get secure default_input_method").substringBefore('/')
    private fun imeBounds(): Rect? {
        val pkg = imePackage()
        if (pkg.isEmpty() || pkg == "null") return null
        val all = device.findObjects(By.pkg(pkg)).map { it.visibleBounds }.filter { !it.isEmpty }
        if (all.isEmpty()) return null
        return Rect(all.first()).apply { all.drop(1).forEach { union(it) } }
    }
    private fun assertChrome(dark: Boolean) {
        ui.runOnUiThread {
            val window = ui.activity.window
            val expected = if (dark) 0xFF0C0F15.toInt() else 0xFFF9F5FF.toInt()
            assertEquals("status bar follows selected theme", expected, window.statusBarColor)
            assertEquals("navigation follows selected theme", expected, window.navigationBarColor)
            assertEquals("divider follows selected theme", expected, window.navigationBarDividerColor)
            val mask = View.SYSTEM_UI_FLAG_LIGHT_STATUS_BAR or View.SYSTEM_UI_FLAG_LIGHT_NAVIGATION_BAR
            assertEquals("system icon polarity", if (dark) 0 else mask, window.decorView.systemUiVisibility and mask)
            assertFalse(window.isStatusBarContrastEnforced)
            assertFalse(window.isNavigationBarContrastEnforced)
        }
    }
    private fun snapshot(): JSONObject {
        val nav = ui.onNodeWithTag("nav-week").fetchSemanticsNode().boundsInWindow
        val error = ui.onAllNodesWithText("请输入有效日期（YYYY-MM-DD）").fetchSemanticsNodes().firstOrNull()?.boundsInWindow
        val ime = imeBounds()
        val result = JSONObject().apply {
            put("mode", mode()); put("systemDark", systemDark()); put("pid", Process.myPid())
            put("screenWidth", device.displayWidth); put("screenHeight", device.displayHeight)
            put("navigationMode", navigationMode)
            put("navigationTop", nav.top); put("navigationBottom", nav.bottom)
            put("activity", ui.activity.javaClass.name)
            val themeNodes = JSONObject()
            for (value in listOf("light", "dark", "system")) {
                ui.onAllNodesWithTag("theme-$value").fetchSemanticsNodes().firstOrNull()?.boundsInWindow?.let {
                    themeNodes.put(value, JSONArray(listOf(it.left, it.top, it.right, it.bottom)))
                }
            }
            put("themeOptionBounds", themeNodes)
            put("dateErrorBounds", if (error == null) JSONObject.NULL else JSONArray(listOf(error.left, error.top, error.right, error.bottom)))
            put("imePackage", imePackage()); put("imeBounds", if (ime == null) JSONObject.NULL else bounds(ime))
        }
        ui.runOnUiThread {
            val window = ui.activity.window
            val insets = window.decorView.rootWindowInsets
            result.put("imeVisible", insets?.isVisible(WindowInsets.Type.ime()) == true)
            result.put("imeBottom", insets?.getInsets(WindowInsets.Type.ime())?.bottom ?: 0)
            result.put("statusBarHeight", insets?.getInsets(WindowInsets.Type.statusBars())?.top ?: 0)
            result.put("systemNavigationHeight", insets?.getInsets(WindowInsets.Type.navigationBars())?.bottom ?: 0)
            result.put("chromeArgb", window.statusBarColor)
            result.put("uiFlags", window.decorView.systemUiVisibility)
        }
        return result
    }
    private fun committedFrame() {
        val latch = CountDownLatch(1)
        ui.runOnUiThread {
            val decor = ui.activity.window.decorView
            check(decor.isHardwareAccelerated) { "Theme evidence needs an actual HWUI frame" }
            decor.viewTreeObserver.registerFrameCommitCallback { latch.countDown() }
            decor.invalidate()
        }
        check(latch.await(5, TimeUnit.SECONDS)) { "No committed theme frame" }
    }
    private fun rendered(file: File, state: JSONObject, dark: Boolean, needsIme: Boolean): Boolean {
        val bitmap = BitmapFactory.decodeFile(file.absolutePath) ?: return false
        try {
            val expected = if (dark) 0xFF0C0F15.toInt() else 0xFFF9F5FF.toInt()
            val navBottom = state.getDouble("navigationBottom").toInt()
            for (y in listOf(10, bitmap.height / 3, navBottom - 10)) {
                if (y !in 0 until bitmap.height) return false
                for (x in listOf(1, 2, bitmap.width - 3, bitmap.width - 2)) {
                    if (bitmap.getPixel(x, y) != expected) return false
                }
            }
            val label = device.findObject(By.pkg("com.hcbiu.elcton").text("今日")) ?: return false
            val box = label.visibleBounds
            var contrasting = 0
            for (y in box.top until box.bottom) for (x in box.left until box.right) {
                val rgb = bitmap.getPixel(x, y)
                val r = android.graphics.Color.red(rgb); val g = android.graphics.Color.green(rgb); val b = android.graphics.Color.blue(rgb)
                if (if (dark) minOf(r, g, b) > 100 else maxOf(r, g, b) < 180) contrasting++
            }
            if (contrasting < 12) return false
            if (needsIme) {
                if (!state.getBoolean("imeVisible") || state.isNull("imeBounds")) return false
                val ime = state.getJSONArray("imeBounds")
                // Gboard's accessibility union includes a drop shadow above its actual window.
                // Keep raw bounds in the receipt; validate content using the independent IME inset.
                val insetTop = bitmap.height - state.getInt("imeBottom")
                if (insetTop < navBottom - 12 || ime.getInt(1) > insetTop + 12) return false
                val top = maxOf(ime.getInt(1), insetTop).coerceAtLeast(0)
                val bottom = minOf(ime.getInt(3), bitmap.height - state.getInt("systemNavigationHeight"))
                if (bottom - top < bitmap.height * .14) return false
                if (state.isNull("dateErrorBounds")) return false
                val error = state.getJSONArray("dateErrorBounds")
                if (error.getDouble(1) < state.getInt("statusBarHeight") || error.getDouble(3) >= state.getDouble("navigationTop")) return false
                var bright = 0; var ink = 0; var total = 0
                for (y in top until bottom step 5) for (x in 12 until bitmap.width - 12 step 5) {
                    val rgb = bitmap.getPixel(x, y)
                    val low = minOf(android.graphics.Color.red(rgb), android.graphics.Color.green(rgb), android.graphics.Color.blue(rgb))
                    if (low > 180) bright++
                    if (low < 145) ink++
                    total++
                }
                if (total == 0 || bright.toFloat() / total < .45f || ink < 12) return false
            } else if (state.getBoolean("imeVisible")) return false
            return true
        } finally { bitmap.recycle() }
    }
    private fun capture(name: String, dark: Boolean, needsIme: Boolean = false) {
        ui.waitForIdle(); assertChrome(dark)
        val attempts = File(directory, "attempts").apply { mkdirs() }
        val deadline = System.nanoTime() + TimeUnit.SECONDS.toNanos(25)
        var attempt = 0
        while (System.nanoTime() < deadline) {
            attempt++
            committedFrame()
            val before = snapshot()
            val id = UUID.randomUUID().toString()
            val picture = File(attempts, "$name-$attempt.png")
            val xml = File(attempts, "$name-$attempt.xml")
            val xmlBefore = File(attempts, "$name-$attempt-before.xml")
            device.dumpWindowHierarchy(xmlBefore)
            check(device.takeScreenshot(picture)) { "Theme screenshot failed" }
            device.dumpWindowHierarchy(xml)
            val after = snapshot()
            val xmlStable = hash(xmlBefore) == hash(xml)
            val stable = before.toString() == after.toString() && xmlStable
            val pixelReady = stable && rendered(picture, after, dark, needsIme)
            val receipt = JSONObject().apply {
                put("name", name); put("captureId", id); put("phase", phase); put("attempt", attempt)
                put("expectedDark", dark); put("requiresIme", needsIme)
                put("before", before); put("after", after); put("stable", stable); put("pixelReady", pixelReady)
                put("pngSha256", hash(picture)); put("xmlSha256", hash(xml))
                put("xmlBeforeSha256", hash(xmlBefore)); put("xmlStable", xmlStable)
            }
            File(attempts, "$name-$attempt-state.json").writeText(receipt.toString())
            if (pixelReady) {
                picture.copyTo(File(directory, "$name.png"), overwrite = true)
                xml.copyTo(File(directory, "$name.xml"), overwrite = true)
                File(directory, "$name-state.json").writeText(receipt.toString())
                return
            }
            ui.waitForIdle()
        }
        error("Theme/IME PNG, XML and state never converged: $name after $attempt actual captures")
    }
    private fun settings() {
        ui.onNodeWithTag("nav-today").performClick()
        ui.onNodeWithTag("nav-settings").performClick()
        ui.waitForIdle()
    }
    private fun choose(value: String, dark: Boolean) {
        settings()
        ui.onNodeWithTag("theme-${value.lowercase()}").performScrollTo().performClick().assertIsSelected()
        for (other in listOf("LIGHT", "DARK", "SYSTEM").filter { it != value }) {
            ui.onNodeWithTag("theme-${other.lowercase()}").assertIsNotSelected()
        }
        ui.waitForIdle(); assertEquals(value, mode()); assertChrome(dark)
    }
    private fun options(name: String, value: String, dark: Boolean) {
        settings()
        ui.onNodeWithTag("theme-${value.lowercase()}").performScrollTo().assertIsSelected().assertIsDisplayed()
        for (name in listOf("light", "dark", "system")) {
            ui.onNodeWithTag("theme-$name").assertIsDisplayed()
        }
        for (label in listOf("亮色", "暗色", "跟随系统")) {
            ui.onNodeWithText(label).assertIsDisplayed()
        }
        capture(name, dark)
    }
    private fun tour(prefix: String, dark: Boolean) {
        ui.onNodeWithTag("nav-today").performClick(); capture("$prefix-today", dark)
        ui.onNodeWithTag("nav-week").performClick(); capture("$prefix-week", dark)
        ui.onNodeWithTag("add-course").performClick(); capture("$prefix-editor", dark)
        ui.onNodeWithTag("nav-devices").performClick(); capture("$prefix-devices", dark)
        settings(); capture("$prefix-settings", dark)
    }
    private fun dateErrorIme(name: String, dark: Boolean) {
        settings()
        val baseline = ui.onNodeWithTag("nav-week").fetchSemanticsNode().boundsInWindow.bottom
        ui.onNodeWithTag("semester-input").performClick().performTextReplacement("2026-02-30")
        ui.onNodeWithTag("semester-input").performClick()
        check(device.wait(Until.hasObject(By.pkg(imePackage())), 10000)) { "No actual input-method window" }
        ui.waitUntil(10000) {
            val insets = ui.activity.window.decorView.rootWindowInsets
            insets?.isVisible(WindowInsets.Type.ime()) == true &&
                ui.onNodeWithTag("nav-week").fetchSemanticsNode().boundsInWindow.bottom < baseline - device.displayHeight * .15f
        }
        ui.onNodeWithTag("semester-save").assertIsDisplayed().performClick()
        ui.onNodeWithText("请输入有效日期（YYYY-MM-DD）").assertIsDisplayed()
        ui.onNodeWithTag("semester-input").performClick()
        ui.onNodeWithText("请输入有效日期（YYYY-MM-DD）").assertIsDisplayed()
        capture(name, dark, true)
        device.pressBack()
        ui.waitUntil(10000) { ui.activity.window.decorView.rootWindowInsets?.isVisible(WindowInsets.Type.ime()) == false }
    }
    private fun checkMode(expected: String, dark: Boolean) {
        assertEquals(expected, mode()); assertChrome(dark)
        options("r2-$phase", expected, dark)
    }
    private fun setSystemDark(dark: Boolean) {
        shell("cmd uimode night " + if (dark) "yes" else "no")
        ui.waitUntil(15000) { runCatching { systemDark() == dark && ui.onAllNodesWithTag("nav-today").fetchSemanticsNodes().isNotEmpty() }.getOrDefault(false) }
        ui.waitForIdle()
    }
    @Test fun inspectThemeAndPersistencePhase() {
        ui.waitUntil(15000) { ui.onAllNodesWithTag("nav-today").fetchSemanticsNodes().isNotEmpty() }
        File(directory, "r2-$phase-process.json").writeText(JSONObject().apply {
            put("phase", phase); put("pid", Process.myPid()); put("mode", mode()); put("systemDark", systemDark())
            put("navigationMode", navigationMode); put("previousHostForceStop", args.getString("previous_force_stop", "false"))
        }.toString())
        when (phase) {
            "initial" -> {
                assertFalse("A clean install has no stored theme", preferences.contains("mode"))
                assertFalse("Host starts system light", systemDark())
                tour("r2-light", false); options("r2-light-options", "LIGHT", false)
                dateErrorIme("r2-light-date-error-ime", false)
                choose("DARK", true); options("r2-dark-options", "DARK", true)
                tour("r2-dark", true); dateErrorIme("r2-dark-date-error-ime", true)
            }
            "cold-dark" -> {
                assertFalse(systemDark()); checkMode("DARK", true)
                choose("SYSTEM", false); options("r2-system-light-options", "SYSTEM", false)
            }
            "cold-system-dark" -> {
                assertTrue(systemDark()); checkMode("SYSTEM", true)
                ui.onNodeWithTag("nav-today").performClick(); capture("r2-system-dark-today", true)
                setSystemDark(false); options("r2-system-live-light-options", "SYSTEM", false)
                choose("LIGHT", false); options("r2-explicit-light-options", "LIGHT", false)
                setSystemDark(true); options("r2-explicit-light-under-dark-system", "LIGHT", false)
            }
            "cold-light-under-dark-system" -> {
                assertTrue(systemDark()); checkMode("LIGHT", false)
                choose("DARK", true); options("r2-legacy-dark-selected", "DARK", true)
            }
            else -> error("Unsupported theme phase: $phase")
        }
        File(directory, "r2-$phase-result.json").writeText(JSONObject().apply {
            put("passed", true); put("phase", phase); put("pid", Process.myPid()); put("mode", mode())
            put("systemDark", systemDark()); put("navigationMode", navigationMode)
        }.toString())
    }
}
