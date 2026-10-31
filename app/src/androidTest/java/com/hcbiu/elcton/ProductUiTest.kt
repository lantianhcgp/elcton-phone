package com.hcbiu.elcton

import androidx.compose.ui.test.*
import androidx.compose.ui.test.junit4.createAndroidComposeRule
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

/** One lifecycle, real semantic taps and typed fields; screenshots are shell-owned simulator evidence. */
@RunWith(AndroidJUnit4::class)
class ProductUiTest {
    @get:Rule val ui = createAndroidComposeRule<MainActivity>()
    private fun shot(name: String) {
        ui.waitForIdle()
        val automation=InstrumentationRegistry.getInstrumentation().uiAutomation
        automation.executeShellCommand("mkdir -p /sdcard/Download/elcton-qa").use { p -> java.io.FileInputStream(p.fileDescriptor).readBytes() }
        automation.executeShellCommand("screencap -p /sdcard/Download/elcton-qa/$name.png").use { p -> java.io.FileInputStream(p.fileDescriptor).readBytes() }
        automation.executeShellCommand("uiautomator dump /sdcard/Download/elcton-qa/$name.xml").use { p -> java.io.FileInputStream(p.fileDescriptor).readBytes() }
    }
    @Test fun inspectAllProductScreensAndCriticalEditsInOneSession() {
        ui.onNodeWithTag("nav-today").assertExists();shot("01-today-empty")
        ui.onNodeWithTag("nav-week").performClick();shot("02-week-empty")
        ui.onNodeWithTag("add-course").performClick();shot("03-editor-empty")
        ui.onNodeWithTag("course-save").performClick();ui.onNodeWithText("请输入课程名称").assertExists();shot("04-editor-invalid")
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
        ui.onNodeWithText("关闭").performClick()
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
        ui.onNodeWithTag("nav-today").performClick();shot("18-return-today")
    }
}
