package com.hcbiu.elcton

import org.junit.Assert.*
import org.junit.Test

class PhoneScheduleTest {
    private val raw = "{\"schema\":\"elcton.schedule\",\"version\":1,\"settings\":{\"semesterStart\":\"2026-09-01\"},\"courses\":[]}"
    private class Repository : ScheduleRepository {
        var book = ScheduleBook.empty("phone", "2026-09-01")
        var previous: ScheduleBook? = null
        var writes = 0
        var broken = false
        override fun load(): ScheduleBook { if(broken) error("private-source-content"); return book }
        override fun save(book: ScheduleBook) { previous = this.book; this.book = book; writes++ }
        override fun restore(): ScheduleBook = requireNotNull(previous).copy(revision = book.revision + 1)
        override fun hasBackup() = previous != null
    }
    @Test fun sharedPhoneDataLayerExistsRatherThanAnMcpOnlyStore() {
        val repo = Repository(); val layer = PhoneSchedule(repo)
        assertEquals(repo.book, layer.state.book)
    }
    @Test fun previewCannotOverwriteBeforeExplicitConfirmation() {
        val repo = Repository(); val layer = PhoneSchedule(repo)
        assertTrue(layer.prepareImport(raw)); assertEquals(0, repo.writes)
        assertNotNull(layer.state.pendingImport); assertEquals(1, layer.state.book.revision)
        assertTrue(layer.confirmImport()); assertEquals(1, repo.writes); assertEquals(2, layer.state.book.revision)
        assertNull(layer.state.pendingImport); assertTrue(layer.hasBackup())
    }
    @Test fun stalePreviewCannotReplaceNewerEditorData() {
        val repo = Repository(); val layer = PhoneSchedule(repo)
        assertTrue(layer.prepareImport(raw))
        assertTrue(layer.save(layer.state.book.withSemester("2026-09-08")))
        assertFalse(layer.confirmImport()); assertEquals("2026-09-08", repo.book.semesterStart); assertEquals(1, repo.writes)
    }
    @Test fun corruptStorageIsNeverSilentlyResetOrReplaced() {
        val repo = Repository().apply { broken = true }; val layer = PhoneSchedule(repo)
        assertNotNull(layer.state.loadError); assertFalse(layer.prepareImport(raw)); assertFalse(layer.save(layer.state.book))
        assertEquals(0, repo.writes); assertFalse(layer.state.notice.contains("private-source-content"))
    }
    @Test fun badImportPreservesOldDataAndAbortDiscardsPreview() {
        val repo = Repository(); val layer = PhoneSchedule(repo)
        assertFalse(layer.prepareImport("not-json PRIVATE_COURSE")); assertEquals(0, repo.writes)
        assertFalse(layer.state.notice.contains("PRIVATE_COURSE"))
        assertTrue(layer.prepareImport(raw)); layer.cancelImport(); assertNull(layer.state.pendingImport); assertFalse(layer.confirmImport())
        assertEquals(0, repo.writes)
    }
    @Test fun foreignDatasetOrOldRevisionIsRejected() {
        val repo = Repository(); val layer = PhoneSchedule(repo)
        assertFalse(layer.save(layer.state.book.copy(datasetId = "other")))
        assertFalse(layer.save(layer.state.book.copy(revision = 0))); assertEquals(0, repo.writes)
    }
}
