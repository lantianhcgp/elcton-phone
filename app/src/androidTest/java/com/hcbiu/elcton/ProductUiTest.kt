package com.hcbiu.elcton

import androidx.compose.ui.test.*
import androidx.compose.ui.test.junit4.createAndroidComposeRule
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import androidx.test.uiautomator.UiDevice
import androidx.test.uiautomator.By
import androidx.test.uiautomator.Until
import java.util.regex.Pattern
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

/** One lifecycle, real semantic taps and typed fields; screenshots are shell-owned simulator evidence. */
@RunWith(AndroidJUnit4::class)
class ProductUiTest {
    @get:Rule val ui = createAndroidComposeRule<MainActivity>()
    private fun assertWindowChrome() {
        ui.runOnUiThread {
            val window = ui.activity.window
            val background = ui.activity.getColor(R.color.phone_background)
            org.junit.Assert.assertEquals("status bar follows the page", background, window.statusBarColor)
            org.junit.Assert.assertEquals("system navigation follows the page", background, window.navigationBarColor)
            org.junit.Assert.assertEquals("no different navigation divider", background, window.navigationBarDividerColor)
            val darkIcons = android.view.View.SYSTEM_UI_FLAG_LIGHT_STATUS_BAR or android.view.View.SYSTEM_UI_FLAG_LIGHT_NAVIGATION_BAR
            org.junit.Assert.assertEquals("light icons on the dark window", 0, window.decorView.systemUiVisibility and darkIcons)
            org.junit.Assert.assertFalse("no status bar contrast scrim", window.isStatusBarContrastEnforced)
            org.junit.Assert.assertFalse("no navigation contrast scrim", window.isNavigationBarContrastEnforced)
        }
    }
    private val chromeScenes = setOf(
        "01-today-empty", "02-week-empty", "03-editor-empty", "04-editor-invalid",
        "05-week-course", "06-editor-filled", "07-week-edited", "08-settings",
        "09-settings-invalid", "13-device", "14-device-unavailable",
        "15-editor-bottom", "17-course-deleted", "20-restored-course",
        "21-confirmed-empty-import", "22-return-today", "24-file-exported",
        "27-file-imported-course", "28-restarted-file-import", "29-keyboard-visible"
    )
    private val navigationMode get() = InstrumentationRegistry.getArguments().getString("navigation_mode", "three-button")!!
    private fun hasRenderedChrome(file: java.io.File): Boolean {
        val bitmap = android.graphics.BitmapFactory.decodeFile(file.absolutePath) ?: return false
        try {
            fun visible(bounds: android.graphics.Rect?, threshold: Int): Boolean {
                if (bounds == null || bounds.isEmpty || bounds.left < 0 || bounds.top < 0 ||
                    bounds.right > bitmap.width || bounds.bottom > bitmap.height) return false
                var count = 0
                for (y in bounds.top until bounds.bottom) for (x in bounds.left until bounds.right) {
                    val rgb = bitmap.getPixel(x, y)
                    if (android.graphics.Color.red(rgb) > threshold && android.graphics.Color.green(rgb) > threshold &&
                        android.graphics.Color.blue(rgb) > threshold && ++count >= 12) return true
                }
                return false
            }
            val label = device.findObject(By.pkg("com.hcbiu.elcton").text("今日")) ?: return false
            if (!visible(label.visibleBounds, 100)) return false
            val insets = ui.activity.window.decorView.rootWindowInsets ?: return false
            if (insets.isVisible(android.view.WindowInsets.Type.ime())) return true
            return when (navigationMode) {
                "three-button" -> listOf("back", "home_button", "recent_apps").all {
                    visible(device.findObject(By.res("com.android.systemui", it))?.visibleBounds, 180)
                }
                "gestural" -> visible(android.graphics.Rect(bitmap.width / 3,
                    bitmap.height - insets.getInsets(android.view.WindowInsets.Type.navigationBars()).bottom,
                    bitmap.width * 2 / 3, bitmap.height), 180)
                else -> error("Unknown navigation mode: $navigationMode")
            }
        } finally { bitmap.recycle() }
    }
    private fun shot(name: String) {
        ui.waitForIdle()
        if (!name.endsWith("-picker")) assertWindowChrome()
        // Semantics becoming idle does not guarantee that SurfaceFlinger has the new frame.
        // Wait for an actual HWUI frame commit before taking the full-screen/IME image.
        val committed = java.util.concurrent.CountDownLatch(1)
        if (!name.endsWith("-picker")) {
            ui.runOnUiThread {
                val decor = ui.activity.window.decorView
                check(decor.isHardwareAccelerated) { "UI evidence requires a hardware-rendered window" }
                decor.viewTreeObserver.registerFrameCommitCallback { committed.countDown() }
                decor.invalidate()
            }
            check(committed.await(5, java.util.concurrent.TimeUnit.SECONDS)) { "Frame commit timed out: $name" }
        } else {
            // SAF belongs to DocumentsUI; our stopped activity cannot commit a visible frame.
            check(device.wait(Until.hasObject(By.pkg("com.google.android.documentsui")), 5000) ||
                  device.wait(Until.hasObject(By.pkg("com.android.documentsui")), 5000)) { "SAF window not visible" }
            device.waitForIdle(1000)
        }
        val directory=java.io.File(InstrumentationRegistry.getInstrumentation().targetContext.filesDir,"qa-evidence")
        check(directory.isDirectory || directory.mkdirs()) { "Cannot create private evidence directory" }
        // Color-only margins can hide an uncommitted first frame or a SystemUI icon fade.
        // Poll actual captured pixels against live bounds; do not sleep and assume readiness.
        val screenshot = java.io.File(directory,"$name.png")
        if (name in chromeScenes) {
            ui.waitUntil(10000) {
                device.takeScreenshot(screenshot) && hasRenderedChrome(screenshot)
            }
        } else {
            check(device.takeScreenshot(screenshot)) { "Screenshot failed: $name" }
        }
        device.dumpWindowHierarchy(java.io.File(directory,"$name.xml"))
        val navigation=if(name.endsWith("-picker")) null else ui.onAllNodesWithTag("nav-week").fetchSemanticsNodes().firstOrNull()?.boundsInWindow
        java.io.File(directory,"$name-state.json").writeText(org.json.JSONObject().apply {
            put("name",name)
            put("navigationMode",navigationMode)
            put("imeVisible",ui.activity.window.decorView.rootWindowInsets?.isVisible(android.view.WindowInsets.Type.ime()) == true)
            put("screenHeight",device.displayHeight)
            put("statusBarHeight",ui.activity.window.decorView.rootWindowInsets?.getInsets(android.view.WindowInsets.Type.statusBars())?.top ?: 0)
            put("navigationTop",navigation?.top ?: org.json.JSONObject.NULL)
            put("navigationBottom",navigation?.bottom ?: org.json.JSONObject.NULL)
        }.toString())
    }
    private val device get() = UiDevice.getInstance(InstrumentationRegistry.getInstrumentation())
    private fun waitForKeyboard(baselineNavigationBottom: Float) {
        val automation=InstrumentationRegistry.getInstrumentation().uiAutomation
        val ime=automation.executeShellCommand("settings get secure default_input_method").use { p ->
            java.io.FileInputStream(p.fileDescriptor).readBytes().toString(Charsets.UTF_8).trim().substringBefore('/')
        }
        check(ime.isNotEmpty() && ime != "null") { "No installed input method" }
        check(device.wait(Until.hasObject(By.pkg(ime)),10000)) { "Input-method window not visible" }
        ui.waitUntil(10000) {
            val bottom=ui.onNodeWithTag("nav-week").fetchSemanticsNode().boundsInWindow.bottom
            ui.activity.window.decorView.rootWindowInsets?.isVisible(android.view.WindowInsets.Type.ime()) == true &&
                bottom < baselineNavigationBottom-device.displayHeight*0.15f
        }
    }
    private fun waitForApp() {
        ui.waitUntil(10000) { ui.onAllNodesWithTag("nav-settings").fetchSemanticsNodes().isNotEmpty() }
    }
    private fun saveExportFile() {
        ui.onNodeWithText("保存文件").performClick()
        val filename = device.wait(Until.findObject(By.clazz("android.widget.EditText")),10000)
            ?: throw AssertionError("SAF filename field not found")
        filename.text = "elcton-qa-export.json"
        shot("23-file-export-picker")
        val save = device.wait(Until.findObject(By.text(Pattern.compile("(?i)save|保存"))),5000)
            ?: throw AssertionError("SAF save action not found")
        save.click()
        waitForApp()
        ui.waitUntil(10000) { ui.onAllNodesWithText("课表已导出").fetchSemanticsNodes().isNotEmpty() }
        shot("24-file-exported")
    }
    private fun importExportedFile() {
        ui.onNodeWithTag("nav-settings").performClick()
        ui.onNodeWithTag("import-file").performScrollTo().performClick()
        val exported = device.wait(Until.findObject(By.text("elcton-qa-export.json")),10000)
            ?: throw AssertionError("SAF exported timetable not found")
        shot("25-file-import-picker")
        exported.click()
        waitForApp()
        ui.waitUntil(10000) { ui.onAllNodesWithTag("import-confirm").fetchSemanticsNodes().isNotEmpty() }
        shot("26-file-import-preview")
        ui.onNodeWithTag("import-confirm").performClick()
        ui.onNodeWithTag("nav-week").performClick()
        ui.onNodeWithTag("week-day-6").performClick()
        ui.onNodeWithText("数学测试课程").assertExists()
        shot("27-file-imported-course")
        ui.activityRule.scenario.recreate()
        ui.onNodeWithTag("nav-week").performClick()
        ui.onNodeWithTag("week-day-6").performClick()
        ui.onNodeWithText("数学测试课程").assertExists()
        shot("28-restarted-file-import")
    }
    @Test fun inspectAllProductScreensAndCriticalEditsInOneSession() {
        ui.onNodeWithTag("nav-today").assertExists();shot("01-today-empty")
        ui.onNodeWithTag("nav-week").performClick();shot("02-week-empty")
        ui.onNodeWithTag("add-course").performClick()
        ui.onNodeWithTag("course-name").assertIsDisplayed()
        ui.onNodeWithTag("course-save").assertIsDisplayed()
        shot("03-editor-empty")
        ui.onNodeWithTag("course-save").performClick();ui.onNodeWithText("请输入课程名称").assertExists();shot("04-editor-invalid")
        val navigationBeforeKeyboard=ui.onNodeWithTag("nav-week").fetchSemanticsNode().boundsInWindow.bottom
        ui.onNodeWithTag("course-name").performClick()
        waitForKeyboard(navigationBeforeKeyboard)
        ui.onNodeWithTag("course-save").assertIsDisplayed()
        ui.onNodeWithTag("nav-week").assertIsDisplayed()
        shot("29-keyboard-visible")
        device.pressBack()
        ui.waitForIdle()
        ui.onNodeWithTag("course-name").performTextInput("语文测试课程")
        ui.onNodeWithTag("course-teacher").performTextInput("测试教师")
        ui.onNodeWithTag("course-location").performTextInput("A301")
        ui.onNodeWithTag("course-day-6").performScrollTo().performClick()
        ui.onNodeWithTag("course-save").performClick()
        ui.onNodeWithTag("week-day-6").performClick();ui.onNodeWithText("语文测试课程").assertExists();shot("05-week-course")
        ui.onNodeWithText("语文测试课程").performClick();shot("06-editor-filled")
        ui.onNodeWithTag("course-name").performTextReplacement("数学测试课程")
        ui.onNodeWithTag("course-save").performClick();ui.onNodeWithText("数学测试课程").assertExists();shot("07-week-edited")
        ui.onNodeWithTag("nav-settings").performClick();shot("08-settings")
        ui.onNodeWithTag("semester-input").performTextReplacement("2026-02-30")
        ui.onNodeWithTag("semester-save").performClick();ui.onNodeWithText("请输入有效日期（YYYY-MM-DD）").assertExists();shot("09-settings-invalid")
        ui.onNodeWithTag("semester-input").performTextReplacement("2026-09-01")
        ui.onNodeWithTag("semester-save").performClick()
        ui.onNodeWithTag("import-paste").performScrollTo().performClick();shot("10-import")
        val payload="{\"schema\":\"elcton.schedule\",\"version\":1,\"settings\":{\"semesterStart\":\"2026-09-01\"},\"courses\":[]}"
        ui.onNodeWithTag("import-input").performTextInput(payload)
        ui.onNodeWithTag("import-check").performClick();shot("11-import-preview")
        ui.onNodeWithTag("import-cancel").performClick()
        ui.onNodeWithTag("export-preview").performScrollTo().performClick();shot("12-export-preview")
        saveExportFile()
        ui.onNodeWithTag("nav-devices").performClick();shot("13-device")
        ui.onNodeWithTag("scan-devices").performClick()
        ui.waitUntil(20000) { ui.onAllNodesWithText("未安装华为运动健康",substring=true).fetchSemanticsNodes().isNotEmpty() }
        shot("14-device-unavailable")
        ui.onNodeWithTag("nav-week").performClick();ui.onNodeWithTag("week-day-6").performClick()
        ui.onNodeWithText("数学测试课程").performClick()
        ui.onNodeWithTag("course-delete").performScrollTo().assertIsDisplayed()
        shot("15-editor-bottom")
        ui.onNodeWithTag("course-delete").performClick()
        ui.waitUntil(5000) { ui.onAllNodesWithTag("delete-confirm").fetchSemanticsNodes().isNotEmpty() }
        shot("16-delete-confirm")
        ui.onNodeWithTag("delete-confirm").assertIsDisplayed().performClick()
        ui.onAllNodesWithText("数学测试课程").assertCountEquals(0);shot("17-course-deleted")
        ui.onNodeWithTag("nav-settings").performClick()
        ui.onNodeWithTag("restore-backup").performScrollTo().performClick()
        shot("19-restore-confirm")
        ui.onNodeWithText("恢复",useUnmergedTree=true).performClick()
        ui.onNodeWithTag("nav-week").performClick();ui.onNodeWithTag("week-day-6").performClick()
        ui.onNodeWithText("数学测试课程").assertExists();shot("20-restored-course")
        ui.onNodeWithTag("nav-settings").performClick()
        ui.onNodeWithTag("import-paste").performScrollTo().performClick()
        ui.onNodeWithTag("import-input").performTextInput(payload)
        ui.onNodeWithTag("import-check").performClick()
        ui.onNodeWithTag("import-confirm").performClick()
        ui.onNodeWithTag("nav-week").performClick();ui.onNodeWithTag("week-day-6").performClick()
        ui.onAllNodesWithText("数学测试课程").assertCountEquals(0);shot("21-confirmed-empty-import")
        ui.onNodeWithTag("nav-today").performClick();shot("22-return-today")
        val loaded=ScheduleStore(ui.activity).load()
        org.junit.Assert.assertTrue("empty import persists after a fresh store",loaded.courses.isEmpty())
        importExportedFile()
    }
}
