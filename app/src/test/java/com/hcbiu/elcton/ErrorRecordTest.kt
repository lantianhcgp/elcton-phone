package com.hcbiu.elcton

import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Test

/** Public diagnostic record seam; no SDK class is imitated. */
class ErrorRecordTest {
    @Test fun fullSdkMessageAndCauseAreAvailableWithoutChangingPrimaryUiPrivacy() {
        val clazz = runCatching { Class.forName("com.hcbiu.elcton.WearErrorRecord") }.getOrNull()
        assertNotNull("Full Wear Engine diagnostic record is required", clazz)
        val companion = clazz!!.getField("Companion").get(null)
        val capture = companion.javaClass.methods.single { it.name == "capture" && it.parameterCount == 4 }
        val error = IllegalStateException("Scope unauthorized: original code 8", RuntimeException("cause details\nsecond line"))
        val record = capture.invoke(companion, error, "checkPermission", 0L, { _: Throwable -> 8 })
        val json = record.javaClass.getMethod("toJson").invoke(record) as JSONObject
        assertEquals("Scope unauthorized: original code 8", json.getString("message"))
        assertEquals("1970-01-01T00:00:00Z", json.getString("timestamp"))
        assertEquals("checkPermission", json.getString("phase"))
        assertEquals(8, json.getInt("errorCode"))
        assertEquals(2, json.getJSONArray("causes").length())
        assertEquals("cause details\nsecond line", json.getJSONArray("causes").getJSONObject(1).getString("message"))
        val full = record.javaClass.getMethod("getFull").invoke(record) as String
        assertTrue(full.contains("Scope unauthorized: original code 8"))
        assertTrue(full.contains("cause details\nsecond line"))
        assertTrue(full.contains("1970-01-01T00:00:00Z"))
        assertFalse(UserFacingError.explain(error.message!!).contains("original code 8"))
    }
}
