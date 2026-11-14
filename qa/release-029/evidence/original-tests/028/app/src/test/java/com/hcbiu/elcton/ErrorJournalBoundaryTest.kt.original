package com.hcbiu.elcton

import java.io.File
import java.nio.file.Files
import java.util.concurrent.Callable
import java.util.concurrent.Executors
import java.util.concurrent.TimeUnit
import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Test

class ErrorJournalBoundaryTest {
    @Test fun defaultRingKeepsLast128FullRecordsAndSerializesConcurrentAppends() {
        val dir = Files.createTempDirectory("elcton-journal-boundary-").toFile()
        val file = File(dir, "diagnostics/wear-errors.jsonl")
        val journal = ErrorJournal(file)
        val workers = Executors.newFixedThreadPool(4)
        try {
            val tasks = (0 until 160).map { index -> Callable {
                journal.append(WearErrorRecord.capture(Exception("SYNTHETIC error-$index"), "checkPermission", index.toLong()))
            } }
            workers.invokeAll(tasks, 20, TimeUnit.SECONDS).forEach { it.get() }
            val lines = file.readLines(Charsets.UTF_8)
            assertEquals(128, lines.size)
            val messages = lines.map { JSONObject(it).getString("message") }
            assertEquals(128, messages.toSet().size)
            assertEquals(128, journal.tail(128).length())
            val reopened = ErrorJournal(file)
            assertEquals(journal.latestFull(), reopened.latestFull())
            assertEquals(journal.tail(128).toString(), reopened.tail(128).toString())
        } finally {
            workers.shutdownNow()
        }
    }

    @Test fun failedReplacementLeavesPreviousCompleteErrorReadable() {
        val dir = Files.createTempDirectory("elcton-journal-write-failure-").toFile()
        val file = File(dir, "diagnostics/wear-errors.jsonl")
        val journal = ErrorJournal(file)
        journal.append(WearErrorRecord.capture(Exception("SYNTHETIC preserved"), "scan", 1L))
        val before = file.readText(Charsets.UTF_8)
        val moved = File(dir, "preserved-diagnostics")
        check(file.parentFile!!.renameTo(moved))
        // A file, rather than a directory, blocks the next write without deleting history.
        file.parentFile!!.writeText("SYNTHETIC unavailable directory", Charsets.UTF_8)
        try {
            journal.append(WearErrorRecord.capture(Exception("SYNTHETIC rejected write"), "scan", 2L))
            fail("The persistence failure must be observable to its runtime caller")
        } catch (_: Exception) { }
        assertEquals(before, File(moved, file.name).readText(Charsets.UTF_8))
        assertEquals(1, journal.tail(128).length())
        assertEquals("SYNTHETIC preserved", journal.tail(1).getJSONObject(0).getString("message"))
    }
}
