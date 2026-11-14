package com.hcbiu.elcton

import org.json.JSONArray
import org.json.JSONObject
import java.io.File
import java.io.FileOutputStream
import java.nio.file.Files
import java.nio.file.StandardCopyOption

/** One process-owned journal. Keeps complete records, not truncated lines or SDK summaries. */
class ErrorJournal(private val file: File, private val maxRecords: Int = 128) {
    init { require(maxRecords in 1..128) { "Invalid journal capacity" } }
    private val records: MutableList<JSONObject> = loadRecords()

    private fun loadRecords(): MutableList<JSONObject> {
        if (!file.isFile) return mutableListOf()
        val lines = file.readLines(Charsets.UTF_8).filter { it.isNotBlank() }
        val parsed = lines.map { runCatching { JSONObject(it) }.getOrNull() }
        if (parsed.any { it == null }) {
            val archive = File(file.parentFile, file.name + ".recovery-" + java.util.UUID.randomUUID())
            Files.copy(file.toPath(), archive.toPath())
        }
        return parsed.filterNotNull().takeLast(maxRecords).toMutableList()
    }

    @Synchronized fun append(record: WearErrorRecord) {
        val next = (records + record.toJson()).takeLast(maxRecords)
        val text = next.joinToString(separator = "\n", postfix = "\n") { it.toString() }
        replaceDiagnosticFile(file, text)
        records.clear()
        records.addAll(next)
    }

    @Synchronized fun tail(limit: Int = 20): JSONArray {
        require(limit in 1..128) { "Invalid journal limit" }
        return JSONArray().apply { records.takeLast(limit).forEach { put(JSONObject(it.toString())) } }
    }

    @Synchronized fun latestFull(): String = records.lastOrNull()?.optString("full", "").orEmpty()
}

/** No destructive fallback: a failed write leaves the previous complete diagnostic file intact. */
internal fun replaceDiagnosticFile(file: File, text: String) {
    val parent = file.parentFile ?: throw java.io.IOException("Diagnostic directory missing")
    check(parent.isDirectory || parent.mkdirs()) { "Cannot create diagnostic directory" }
    val temporary = File.createTempFile(".diagnostic-", ".tmp", parent)
    FileOutputStream(temporary).use { output ->
        output.write(text.toByteArray(Charsets.UTF_8))
        output.fd.sync()
    }
    Files.move(temporary.toPath(), file.toPath(), StandardCopyOption.ATOMIC_MOVE, StandardCopyOption.REPLACE_EXISTING)
}
