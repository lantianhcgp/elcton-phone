package com.hcbiu.elcton

import org.json.JSONArray
import org.json.JSONObject
import java.io.File
import java.nio.ByteBuffer
import java.nio.channels.FileChannel
import java.nio.charset.CodingErrorAction
import java.nio.file.Files
import java.nio.file.LinkOption
import java.nio.file.StandardOpenOption

/** Read-only diagnostic boundary. It deliberately has no Android or WearEngine dependency. */
class DiagnosticTools(
    private val filesDir: File,
    private val errorTail: (Int) -> JSONArray,
    private val diagRead: () -> JSONObject,
    private val versionInfo: () -> JSONObject
) : McpToolProvider {
    override fun list(): JSONArray {
        val limit = JSONObject().put("type", "integer").put("minimum", 1).put("maximum", 128).put("default", 20)
        val path = JSONObject().put("type", "string").put("enum", JSONArray(ALLOWED_FILES.toList()))
        return JSONArray()
            .put(description("error_tail", "Read recent sanitized diagnostic errors", JSONObject().put("limit", limit)))
            .put(description("diag_read", "Read the current diagnostic snapshot", JSONObject()))
            .put(description("version_info", "Read application version information", JSONObject()))
            .put(description("fs_read", "Read an explicitly allowed diagnostic file", JSONObject().put("path", path), "path"))
    }

    private fun description(name: String, text: String, properties: JSONObject, vararg required: String): JSONObject =
        JSONObject().put("name", name).put("description", text)
            .put("inputSchema", JSONObject().put("type", "object").put("properties", properties)
                .put("required", JSONArray(required.toList())).put("additionalProperties", false))
            .put("annotations", JSONObject().put("readOnlyHint", true).put("destructiveHint", false).put("openWorldHint", false))

    override fun validArguments(name: String, arguments: JSONObject): Boolean {
        val keys = arguments.keys().asSequence().toSet()
        return when (name) {
            "error_tail" -> keys.all { it == "limit" } && (!arguments.has("limit") || validLimit(arguments.opt("limit")))
            "diag_read", "version_info" -> keys.isEmpty()
            "fs_read" -> keys == setOf("path") && arguments.opt("path") is String
            else -> true // Unknown tools are tool errors rather than parameter errors.
        }
    }

    private fun validLimit(value: Any?): Boolean =
        (value is Int || value is Long || value is Short || value is Byte) && (value as Number).toLong() in 1L..128L

    override fun call(name: String, arguments: JSONObject): JSONObject {
        if (!validArguments(name, arguments)) return failure("invalid_arguments")
        return try {
            when (name) {
                "error_tail" -> success(JSONObject().put("errors", errorTail(if (arguments.has("limit")) (arguments.get("limit") as Number).toInt() else 20)))
                "diag_read" -> success(diagRead())
                "version_info" -> success(versionInfo())
                "fs_read" -> readFile(arguments.getString("path"))
                else -> failure("unknown_tool")
            }
        } catch (_: Exception) { failure("tool_failed") }
    }

    private fun readFile(relative: String): JSONObject {
        if (relative !in ALLOWED_FILES) return failure("file_not_allowed")
        return try {
            val root = filesDir.canonicalFile.toPath()
            var path = root
            for (part in relative.split('/')) {
                path = path.resolve(part)
                if (Files.isSymbolicLink(path)) return failure("file_not_allowed")
            }
            if (!path.toRealPath().startsWith(root) || !Files.isRegularFile(path, LinkOption.NOFOLLOW_LINKS))
                return failure("file_unavailable")
            val buffer = ByteBuffer.allocate(MAX_FILE_BYTES + 1)
            FileChannel.open(path, StandardOpenOption.READ, LinkOption.NOFOLLOW_LINKS).use { channel ->
                if (channel.size() > MAX_FILE_BYTES) return failure("file_too_large")
                while (buffer.hasRemaining() && channel.read(buffer) != -1) { }
            }
            val length = buffer.position()
            if (length > MAX_FILE_BYTES) return failure("file_too_large")
            buffer.flip()
            val text = Charsets.UTF_8.newDecoder().onMalformedInput(CodingErrorAction.REPORT)
                .onUnmappableCharacter(CodingErrorAction.REPORT).decode(buffer).toString()
            success(JSONObject().put("text", text).put("bytes", length))
        } catch (_: Exception) { failure("file_unavailable") }
    }

    private fun success(data: JSONObject): JSONObject = result(data, false)
    private fun failure(code: String): JSONObject = result(JSONObject().put("error", code), true)
    private fun result(data: JSONObject, isError: Boolean): JSONObject = JSONObject()
        .put("content", JSONArray().put(JSONObject().put("type", "text").put("text", data.toString())))
        .put("isError", isError).put("structuredContent", data)

    companion object {
        const val MAX_FILE_BYTES = 256 * 1024
        private val ALLOWED_FILES = setOf("diagnostics/wear-errors.jsonl", "diagnostics/state.json")
    }
}
