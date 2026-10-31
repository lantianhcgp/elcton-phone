package com.hcbiu.elcton

import org.junit.Assert.*
import org.junit.Test

class WireTest {
    @Test fun asciiAndCrcAreIdenticalToWatchProtocol() {
        assertEquals("cbf43926", Wire.crc32("123456789"))
        assertEquals("\\u8bed\\u6587", Wire.ascii("语文"))
    }
    @Test fun chunksCountTheEntireJsonEnvelopeNotJustPayload() {
        val text = Wire.ascii("{\"name\":\"" + "语文".repeat(180) + "\"}")
        val chunks = Wire.chunks(text, "t-one")
        assertEquals(text, chunks.joinToString("") { it.data })
        assertTrue(chunks.all { it.message.toByteArray(Charsets.UTF_8).size <= 1024 })
    }
}
