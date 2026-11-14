package com.hcbiu.elcton

import java.io.File
import java.nio.file.Files
import org.json.JSONArray
import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Test

class ErrorJournalTest {
    @Test fun malformedOldLineIsArchivedWithoutLosingValidHistoryOrBlockingNewErrors() {
        val dir = Files.createTempDirectory("elcton-journal-recovery-").toFile()
        val file = File(dir, "wear-errors.jsonl")
        val first = WearErrorRecord.capture(IllegalStateException("old error"), "scan", 0L).toJson()
        val raw = first.toString() + "\n{partial record\n"
        file.writeText(raw, Charsets.UTF_8)
        val journal = ErrorJournal(file, 128)
        journal.append(WearErrorRecord.capture(IllegalStateException("new error"), "checkPermission", 1L))
        assertEquals(2, journal.tail(128).length())
        assertEquals("old error", journal.tail(128).getJSONObject(0).getString("message"))
        val archives = dir.listFiles()!!.filter { it.name.startsWith("wear-errors.jsonl.recovery-") }
        assertEquals("Malformed bytes must be preserved instead of deleted", 1, archives.size)
        assertEquals(raw, archives.single().readText(Charsets.UTF_8))
        assertEquals(2, file.readLines(Charsets.UTF_8).size)
    }

    @Test fun ringKeepsLastRecordsAcrossRestartAsCompleteUtf8JsonLines() {
        val clazz = runCatching { Class.forName("com.hcbiu.elcton.ErrorJournal") }.getOrNull()
        assertNotNull("Persistent bounded error journal is required", clazz)
        val file = File(Files.createTempDirectory("elcton-journal-").toFile(), "diagnostics/wear-errors.jsonl")
        val journal = clazz!!.getConstructor(File::class.java, Int::class.javaPrimitiveType).newInstance(file, 3)
        val text = "原始Scope unauthorized 8\n引号\"反斜线\\" + "甲".repeat(6000)
        val append = clazz.getMethod("append", WearErrorRecord::class.java)
        repeat(5) { index -> append.invoke(journal, WearErrorRecord.capture(IllegalStateException("$index:$text"), "checkPermission", index.toLong())) }
        val lines = file.readLines(Charsets.UTF_8)
        assertEquals(3, lines.size)
        assertEquals("2:$text", JSONObject(lines[0]).getString("message"))
        assertEquals("4:$text", JSONObject(lines[2]).getString("message"))
        val reopened = clazz.getConstructor(File::class.java, Int::class.javaPrimitiveType).newInstance(file, 3)
        val tail = clazz.getMethod("tail", Int::class.javaPrimitiveType).invoke(reopened, 2) as JSONArray
        assertEquals(2, tail.length())
        assertEquals("3:$text", tail.getJSONObject(0).getString("message"))
        assertTrue((clazz.getMethod("latestFull").invoke(reopened) as String).contains("4:$text"))
    }
}
