package com.hcbiu.elcton

import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Test

class SnapshotPrivacyAuditTest {
    private val empty = "{\"schema\":\"elcton.schedule\",\"version\":1,\"settings\":{\"semesterStart\":\"2026-09-01\"},\"courses\":[]}"
    private fun validation(message: String?): String {
        val method = UserFacingError::class.java.methods.find { it.name == "validation" }
        assertNotNull("Safe validation feedback is required", method)
        return method!!.invoke(UserFacingError, message) as String
    }
    @Test fun semesterAndCourseStringsCannotBeCoercedFromOtherJsonTypes() {
        val numericDate = JSONObject(empty).put("settings", JSONObject().put("semesterStart", 20260901)).toString()
        assertThrows(IllegalArgumentException::class.java) { PhoneSnapshot.encode(numericDate) }
        val c = Course("c1", "课程", "教室", "教师", 1, 1, 1, "08:00", "08:45", "all", 0).json()
        val raw = JSONObject(empty).put("courses", org.json.JSONArray().put(c.put("name", 42))).toString()
        assertThrows(IllegalArgumentException::class.java) { PhoneSnapshot.encode(raw) }
    }
    @Test fun parserErrorsAreGenericButKnownLocalValidationIsActionable() {
        val secret = "PRIVATE_COURSE_2937"
        assertFalse(validation("Expected ':' " + secret).contains(secret))
        assertFalse(validation("字段 " + secret + " 范围错误").contains(secret))
        assertEquals("请输入课程名称", validation("请输入课程名称"))
        assertEquals("结束时间必须晚于开始时间", validation("结束时间必须晚于开始时间"))
        assertTrue(validation("字段 startPeriod 范围错误").contains("startPeriod"))
        assertNotNull(validation(null))
    }
    @Test fun diagnosticContainsOnlyExceptionTypeNotMessageOrCause() {
        val method = UserFacingError::class.java.methods.find { it.name == "diagnostic" }
        assertNotNull("Sanitized SDK diagnostic is required", method)
        val exception = IllegalStateException("PRIVATE_COURSE", RuntimeException("PRIVATE_TEACHER"))
        assertEquals("IllegalStateException", method!!.invoke(UserFacingError, exception))
    }
    @Test fun unknownFailureNeverPromisesThatBothSchedulesWereUntouched() {
        val text = UserFacingError.explain("internal something")
        assertFalse(text.contains("没有发送或覆盖课表"))
        assertTrue(text.contains("核对"))
    }
    @Test fun storageRevisionCannotBeCoercedOrExceededAndYearZeroCannotBeEdited() {
        val book = ScheduleBook.empty("school", "2026-09-01")
        for (revision in listOf<Any>("1", 1.5, -1, 9007199254740991L)) {
            val raw = JSONObject(book.storageJson()).put("sourceRevision", revision).toString()
            assertThrows(IllegalArgumentException::class.java) { ScheduleBook.decode(raw) }
        }
        assertThrows(IllegalArgumentException::class.java) { book.withSemester("0000-09-01") }
        assertThrows(IllegalArgumentException::class.java) { book.importSnapshot(empty, -1) }
    }
}
