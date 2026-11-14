package com.hcbiu.elcton

import org.junit.Assert.*
import org.junit.Test

class PhoneSnapshotTest {
    @Test fun orderedSharedDataMatchesTheWatchGoldenVector() {
        val raw = "{\"courses\":[],\"version\":1,\"schema\":\"elcton.schedule\",\"settings\":{\"vibrationEnabled\":true,\"semesterStart\":\"2026-09-01\"}}"
        assertEquals("{\"schema\":\"elcton.schedule\",\"version\":1,\"settings\":{\"semesterStart\":\"2026-09-01\"},\"courses\":[]}", PhoneSnapshot.encode(raw))
    }
    @Test fun newerSchemaAndInvalidCalendarDateAreRejected() {
        val raw = "{\"schema\":\"elcton.schedule\",\"version\":2,\"settings\":{\"semesterStart\":\"2026-09-01\"},\"courses\":[]}"
        assertThrows(IllegalArgumentException::class.java) { PhoneSnapshot.encode(raw) }
        assertThrows(java.time.format.DateTimeParseException::class.java) { PhoneSnapshot.encode(raw.replace("\"version\":2","\"version\":1").replace("2026-09-01","2026-02-30")) }
    }
}
