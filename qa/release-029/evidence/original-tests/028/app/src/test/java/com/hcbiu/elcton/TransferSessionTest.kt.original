package com.hcbiu.elcton

import org.junit.Assert.*
import org.junit.Test

class TransferSessionTest {
    @Test fun transportSuccessNeverMeansTheWatchSavedData() {
        val payload = "{\"schema\":\"elcton.schedule\",\"version\":1,\"settings\":{\"semesterStart\":\"2026-09-01\"},\"courses\":[]}"
        val session = TransferSession(payload, "t1", "school", 1, "", false)
        assertTrue(session.currentMessage!!.contains("\"type\":\"BEGIN\""))
        session.transportSucceeded()
        assertFalse(session.complete)
        assertFalse(session.reply("ACK", "wrong", -1, "", 0, ""))
        assertTrue(session.reply("ACK", "t1", -1, "", 0, ""))
        val chunks = Wire.chunks(payload, "t1")
        chunks.forEach { assertTrue(session.reply("ACK", "t1", it.seq, "", 0, "")) }
        assertTrue(session.currentMessage!!.contains("\"type\":\"END\""))
        session.transportSucceeded()
        assertFalse(session.complete)
        assertTrue(session.reply("APPLIED", "t1", 0, Wire.crc32(payload), 1, ""))
        assertTrue(session.complete)
        assertNull(session.currentMessage)
    }
    @Test fun invalidAppliedIsNotAcceptedAndRetryCountIsBounded() {
        val session = TransferSession("{}", "t1", "school", 1, "", false)
        assertFalse(session.reply("APPLIED", "t1", 0, "00000000", 1, ""))
        repeat(3) { assertTrue(session.timeout()) }
        assertFalse(session.timeout())
        assertEquals("TIMEOUT", session.error)
        assertFalse(session.complete)
    }
}
