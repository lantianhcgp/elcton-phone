package com.hcbiu.elcton

import org.json.JSONArray
import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Test
import java.io.File
import java.lang.reflect.InvocationTargetException
import java.nio.file.Files

class DiagnosticToolsTest {
    private fun withDir(block: (File) -> Unit) {
        val dir = Files.createTempDirectory("mcp-tools-test-").toFile()
        try { block(dir) } finally { dir.deleteRecursively() }
    }
    private fun tools(dir: File, tail: (Int) -> JSONArray = { n -> JSONArray().put(JSONObject().put("requested", n)) },
        diag: () -> JSONObject = { JSONObject().put("connected", false) },
        version: () -> JSONObject = { JSONObject().put("versionName", "test-host") }): Any {
        val type = try { Class.forName("com.hcbiu.elcton.DiagnosticTools") }
        catch (_: ClassNotFoundException) { throw AssertionError("DiagnosticTools implementation missing") }
        return type.constructors.single().newInstance(dir, tail, diag, version)
    }
    private fun call(tools: Any, name: String, args: JSONObject = JSONObject()): JSONObject =
        try { tools.javaClass.getMethod("call", String::class.java, JSONObject::class.java).invoke(tools, name, args) as JSONObject }
        catch (e: InvocationTargetException) { throw e.targetException }
    private fun data(result: JSONObject): JSONObject {
        val text = result.getJSONArray("content").getJSONObject(0)
        assertEquals("text", text.getString("type"))
        val parsed = JSONObject(text.getString("text"))
        assertEquals(parsed.toString(), result.getJSONObject("structuredContent").toString())
        return parsed
    }
    private fun error(result: JSONObject) { assertTrue(result.getBoolean("isError")); data(result) }

    @Test fun schemasDescribeExactlyFourReadOnlyTools() = withDir { dir ->
        val instance = tools(dir)
        val list = instance.javaClass.getMethod("list").invoke(instance) as JSONArray
        assertEquals(setOf("error_tail", "diag_read", "version_info", "fs_read"), (0 until list.length()).map { list.getJSONObject(it).getString("name") }.toSet())
        assertEquals(4, list.length())
        for (i in 0 until list.length()) {
            val item = list.getJSONObject(i)
            val schema = item.getJSONObject("inputSchema")
            assertEquals("object", schema.getString("type"))
            assertFalse(schema.getBoolean("additionalProperties"))
            assertTrue(schema.has("required"))
            assertTrue(item.getJSONObject("annotations").getBoolean("readOnlyHint"))
            if (item.getString("name") == "fs_read") assertEquals("path", schema.getJSONArray("required").getString(0))
            if (item.getString("name") == "error_tail") {
                val limit = schema.getJSONObject("properties").getJSONObject("limit")
                assertEquals("integer", limit.getString("type"))
                assertEquals(1, limit.getInt("minimum")); assertEquals(128, limit.getInt("maximum"))
                assertEquals(20, limit.getInt("default"))
            }
        }
    }

    @Test fun callbacksReturnActualObjectsAndTailDefaultAndBounds() = withDir { dir ->
        val instance = tools(dir)
        assertFalse(call(instance, "version_info").getBoolean("isError"))
        assertEquals("test-host", data(call(instance, "version_info")).getString("versionName"))
        assertFalse(data(call(instance, "diag_read")).getBoolean("connected"))
        for (n in listOf(1, 20, 128)) {
            val args = if (n == 20) JSONObject() else JSONObject().put("limit", n)
            assertEquals(n, data(call(instance, "error_tail", args)).getJSONArray("errors").getJSONObject(0).getInt("requested"))
        }
    }

    @Test fun wrongTypesUnknownKeysAndInvalidLimitsAreRejectedBeforeCallbacks() = withDir { dir ->
        var hits = 0
        val instance = tools(dir, tail = { hits++; JSONArray() }, diag = { hits++; JSONObject() }, version = { hits++; JSONObject() })
        for (value in listOf<Any>(0, 129, -1, 1.5, 1.0, "20", true, JSONObject.NULL))
            error(call(instance, "error_tail", JSONObject().put("limit", value)))
        for (name in listOf("error_tail", "diag_read", "version_info", "fs_read"))
            error(call(instance, name, JSONObject().put("surprise", "secret-request")))
        error(call(instance, "fs_read"))
        for (value in listOf<Any>(1, true, JSONObject.NULL)) error(call(instance, "fs_read", JSONObject().put("path", value)))
        assertEquals(0, hits)
    }

    @Test fun unknownToolAndProviderFailuresAreSanitized() = withDir { dir ->
        val instance = tools(dir, diag = { throw IllegalStateException("token-secret /private/path") })
        for (result in listOf(call(instance, "token-secret"), call(instance, "diag_read"))) {
            error(result)
            assertFalse(result.toString().contains("token-secret")); assertFalse(result.toString().contains("/private/path"))
        }
    }

    @Test fun fsReadOnlyExactWhitelistAndStrictUtf8WithBoundedReads() = withDir { dir ->
        File(dir, "diagnostics").mkdir()
        val state = File(dir, "diagnostics/state.json").apply { writeText("{\"状态\":\"离线🙂\"}", Charsets.UTF_8) }
        val errors = File(dir, "diagnostics/wear-errors.jsonl").apply { writeText("{\"error\":1}\n") }
        val instance = tools(dir)
        for (path in listOf("diagnostics/state.json", "diagnostics/wear-errors.jsonl")) {
            val result = call(instance, "fs_read", JSONObject().put("path", path))
            assertFalse(result.getBoolean("isError"))
            assertEquals(File(dir, path).readText(), data(result).getString("text"))
        }
        for (bad in listOf(state.absolutePath, "../diagnostics/state.json", "diagnostics/../diagnostics/state.json", "./diagnostics/state.json", "diagnostics//state.json", "diagnostics", "mcp.token", "schedule.json", "shared_prefs/preferences.xml", "diagnostics/state.json\u0000")) {
            val result = call(instance, "fs_read", JSONObject().put("path", bad))
            error(result); assertFalse(result.toString().contains(bad))
        }
        state.writeBytes(ByteArray(256 * 1024) { 65 })
        assertEquals(256 * 1024, data(call(instance, "fs_read", JSONObject().put("path", "diagnostics/state.json"))).getString("text").length)
        state.appendText("x")
        val tooLarge = call(instance, "fs_read", JSONObject().put("path", "diagnostics/state.json"))
        error(tooLarge); assertEquals("file_too_large", data(tooLarge).getString("error"))
        errors.writeBytes(byteArrayOf(0xc3.toByte(), 0x28))
        error(call(instance, "fs_read", JSONObject().put("path", "diagnostics/wear-errors.jsonl")))
        assertTrue(state.delete())
        error(call(instance, "fs_read", JSONObject().put("path", "diagnostics/state.json")))
        assertTrue(state.mkdir())
        error(call(instance, "fs_read", JSONObject().put("path", "diagnostics/state.json")))
    }

    @Test fun fsRejectsSymbolicFilesAndSymbolicParentEscape() = withDir { dir ->
        val outside = Files.createTempDirectory("mcp-outside-test-").toFile()
        try {
            val source = File(outside, "state.json").apply { writeText("secret") }
            val diagnostics = File(dir, "diagnostics").apply { mkdir() }
            val link = File(diagnostics, "state.json")
            Files.createSymbolicLink(link.toPath(), source.toPath())
            error(call(tools(dir), "fs_read", JSONObject().put("path", "diagnostics/state.json")))
            assertTrue(link.delete()); assertTrue(diagnostics.delete())
            Files.createSymbolicLink(diagnostics.toPath(), outside.toPath())
            error(call(tools(dir), "fs_read", JSONObject().put("path", "diagnostics/state.json")))
        } finally { outside.deleteRecursively() }
    }
}
