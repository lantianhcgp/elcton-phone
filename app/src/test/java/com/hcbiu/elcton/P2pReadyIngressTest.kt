package com.hcbiu.elcton

import org.junit.Assert.*
import org.junit.Test

/** Real ingress parser, not Android or Bluetooth emulation. */
class P2pReadyIngressTest {
    private fun error(code: String) = "{\"protocol\":\"elcton.sync\",\"version\":1,\"sender\":\"watch\",\"type\":\"ERROR\",\"transferId\":\"\",\"code\":\"$code\"}"
    @Test fun publishedFileFailuresAreNotDiscardedBeforeReadyDispatch() {
        for (code in listOf("300", "301", "302")) assertNotNull("Missing native file failure $code", PacketIngress.watch(error(code)))
    }
    @Test fun errorCodesRemainBoundedAndDoNotAcceptPrivateTextsOrUnknownNumbers() {
        for (code in listOf("private timetable", "lower_case", "A".repeat(49))) assertNull(PacketIngress.watch(error(code)))
        assertNotNull(PacketIngress.watch(error("CORRUPT_JOURNAL")))
    }
}
