package com.hcbiu.elcton

import org.junit.Assert.*
import org.junit.Test

class ExportSessionTest {
    @Test fun chunksBecomeAnImportCandidateOnlyAfterLengthAndChecksumMatch() {
        val session=ExportSession("export1")
        val data="{\"hello\":\"world\"}"
        assertTrue(session.meta("export1",data.length,Wire.crc32(data),2,4))
        assertEquals(0,session.nextSequence)
        assertFalse(session.chunk("wrong",0,data.take(8)))
        assertTrue(session.chunk("export1",0,data.take(8)))
        assertNull(session.result)
        assertTrue(session.chunk("export1",1,data.drop(8)))
        assertEquals(data,session.result)
        assertEquals(4L,session.sourceRevision)
    }
    @Test fun badChecksumOrReplayCannotCorruptAnImport() {
        val s=ExportSession("e1")
        assertTrue(s.meta("e1",2,"00000000",1,1))
        assertTrue(s.chunk("e1",0,"{}"))
        assertNull(s.result)
        assertEquals("CORRUPT_EXPORT",s.error)
        assertFalse(s.chunk("e1",0,"{}"))
    }
}
