package com.hcbiu.elcton

import org.json.JSONArray
import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Test
import java.io.File
import java.lang.reflect.InvocationTargetException
import java.net.InetAddress
import java.net.ServerSocket
import java.net.Socket
import java.nio.file.Files

class DiagnosticMcpServerTest {
    private val token = "aB".repeat(32)
    private data class Reply(val status: Int, val headers: Map<String, String>, val body: ByteArray) {
        fun json() = JSONObject(String(body, Charsets.UTF_8))
    }
    private fun instance(dir: File, credential: String = token): Any {
        val type = try { Class.forName("com.hcbiu.elcton.DiagnosticMcpServer") }
        catch (_: ClassNotFoundException) { throw AssertionError("DiagnosticMcpServer implementation missing") }
        val tools = DiagnosticTools(dir, { n -> JSONArray().put(JSONObject().put("requested", n)) },
            { JSONObject().put("connected", false).put("label", "离线🙂") },
            { JSONObject().put("versionName", "host") })
        return try { type.getConstructor(String::class.java, DiagnosticTools::class.java, Int::class.javaPrimitiveType).newInstance(credential, tools, 0) }
        catch (e: InvocationTargetException) { throw e.targetException }
    }
    private fun invoke(server: Any, name: String): Any? =
        try { server.javaClass.getMethod(name).invoke(server) } catch (e: InvocationTargetException) { throw e.targetException }
    private fun withServer(block: (Any, Int, File) -> Unit) {
        val dir = Files.createTempDirectory("mcp-server-test-").toFile()
        val server = instance(dir)
        try { block(server, invoke(server, "start") as Int, dir) }
        finally { invoke(server, "stop"); dir.deleteRecursively() }
    }
    private fun exchange(port: Int, bytes: ByteArray, shutdown: Boolean = true): Reply {
        Socket("127.0.0.1", port).use { socket ->
            socket.soTimeout = 7000
            socket.getOutputStream().write(bytes); socket.getOutputStream().flush()
            if (shutdown) socket.shutdownOutput()
            val raw = socket.getInputStream().readBytes()
            val boundary = raw.indices.firstOrNull { i -> i + 3 < raw.size && raw[i] == 13.toByte() && raw[i+1] == 10.toByte() && raw[i+2] == 13.toByte() && raw[i+3] == 10.toByte() }
                ?: throw AssertionError("Missing HTTP response")
            val lines = String(raw, 0, boundary, Charsets.US_ASCII).split("\r\n")
            val headers = lines.drop(1).associate { it.substringBefore(':').lowercase() to it.substringAfter(':').trim() }
            val body = raw.copyOfRange(boundary + 4, raw.size)
            assertEquals(body.size, headers.getValue("content-length").toInt())
            assertEquals("close", headers.getValue("connection"))
            assertFalse(String(raw, Charsets.UTF_8).contains(token))
            return Reply(lines[0].split(' ')[1].toInt(), headers, body)
        }
    }
    private fun raw(port: Int, request: String, shutdown: Boolean = true) = exchange(port, request.toByteArray(Charsets.UTF_8), shutdown)
    private fun post(port: Int, body: String, auth: String? = "Bearer $token", path: String = "/mcp"): Reply {
        val bytes = body.toByteArray(Charsets.UTF_8)
        val headers = "POST $path HTTP/1.1\r\nHost: localhost\r\nContent-Type: application/json\r\nContent-Length: ${bytes.size}\r\n" +
            (auth?.let { "Authorization: $it\r\n" } ?: "") + "\r\n"
        return exchange(port, headers.toByteArray(Charsets.US_ASCII) + bytes)
    }
    private fun rpc(method: String, id: Any? = 1, params: Any? = JSONObject()): String =
        JSONObject().put("jsonrpc", "2.0").put("id", id ?: JSONObject.NULL).put("method", method).put("params", params ?: JSONObject.NULL).toString()

    @Test fun rejectsEmptyOrWhitespaceTokens() {
        val dir = Files.createTempDirectory("mcp-empty-").toFile()
        try { for (bad in listOf("", " ", "\n", "abc def")) {
            try { instance(dir, bad); fail("Empty or invalid credentials must fail closed") } catch (_: IllegalArgumentException) { }
        } } finally { dir.deleteRecursively() }
    }

    @Test fun authenticatedRequestsPreserveStringNumberAndNullIds() = withServer { _, port, _ ->
        for (id in listOf<Any>("标识🙂", 19, 9223372036854775807L, 1.5, JSONObject.NULL)) {
            val reply = post(port, rpc("ping", id))
            assertEquals(200, reply.status)
            if (id is Number) assertEquals(id.toString(), reply.json().get("id").toString()) else assertEquals(id, reply.json().get("id"))
            assertEquals("2.0", reply.json().getString("jsonrpc")); assertEquals(0, reply.json().getJSONObject("result").length())
        }
    }

    @Test fun numericIdsAreEchoedAsExactJsonTokensOverProductionHttp() = withServer { _, port, _ ->
        val ids = listOf("9223372036854775809", "-9223372036854775809", "1e999", "-1E+999",
            "1.2300e+004", "-0", "0.00", "0e0", "1e-999", "123456789012345678901234567890.1234567890")
        for (id in ids) {
            val reply = post(port, "{\"jsonrpc\":\"2.0\",\"method\":\"ping\",\"id\":$id}")
            assertEquals(200, reply.status)
            val text = String(reply.body, Charsets.UTF_8)
            assertTrue("Numeric id token changed: $id -> $text", Regex("\"id\"\\s*:\\s*" + Regex.escape(id) + "(?=\\s*[,}])").containsMatchIn(text))
            assertTrue(text.contains("\"result\":{}"))
        }
    }

    @Test fun numericIdsStayExactOnEveryRpcErrorAndEscapedTopLevelKeys() = withServer { _, port, _ ->
        val id = "9223372036854775809"
        for ((fields, code) in listOf(
            "\"jsonrpc\":\"1.0\",\"method\":\"ping\"" to -32600,
            "\"jsonrpc\":\"2.0\",\"method\":false" to -32600,
            "\"jsonrpc\":\"2.0\",\"method\":\"unknown\"" to -32601,
            "\"jsonrpc\":\"2.0\",\"method\":\"ping\",\"params\":[]" to -32602)) {
            val reply = post(port, "{$fields,\"id\":$id}")
            assertEquals(200, reply.status)
            val text = String(reply.body, Charsets.UTF_8)
            assertTrue(Regex("\"id\"\\s*:\\s*" + id + "(?=\\s*[,}])").containsMatchIn(text))
            assertEquals(code, reply.json().getJSONObject("error").getInt("code"))
        }
        val reply = post(port, "{\"params\":{\"clientInfo\":{\"id\":7}},\"i\\u0064\":1.00E+009,\"method\":\"initialize\",\"jsonrpc\":\"2.0\"}")
        assertEquals(200, reply.status)
        assertTrue(String(reply.body, Charsets.UTF_8).contains("\"id\":1.00E+009"))
    }

    @Test fun nestedIdsDoNotTurnNotificationsIntoCallsOrReadFiles() {
        val dir = Files.createTempDirectory("mcp-notification-").toFile()
        var accesses = 0
        val guardedRoot = object : File(dir.absolutePath) {
            override fun getCanonicalFile(): File { accesses++; return super.getCanonicalFile() }
        }
        val tools = DiagnosticTools(guardedRoot,
            { accesses++; JSONArray() }, { accesses++; JSONObject() }, { accesses++; JSONObject() })
        val server = DiagnosticMcpServer(token, tools, 0)
        try {
            val port = server.start()
            for ((name, arguments) in listOf(
                "fs_read" to "{\"path\":\"diagnostics/state.json\"}",
                "diag_read" to "{}", "error_tail" to "{}", "version_info" to "{}")) {
                val reply = post(port, "{\"jsonrpc\":\"2.0\",\"method\":\"tools/call\",\"params\":{\"name\":\"$name\",\"arguments\":$arguments}}")
                assertEquals(202, reply.status); assertEquals(0, reply.body.size)
            }
            val nested = post(port, "{\"jsonrpc\":\"2.0\",\"method\":\"initialize\",\"params\":{\"clientInfo\":{\"id\":1}}}")
            assertEquals(202, nested.status); assertEquals(0, nested.body.size)
            assertEquals("Notifications must not access file paths or callbacks", 0, accesses)
        } finally { server.stop(); dir.deleteRecursively() }
    }

    @Test fun rejectsNonScalarIdsAndEscapedDuplicateIdKeys() = withServer { _, port, _ ->
        for (id in listOf("true", "false", "{}", "[]")) {
            val reply = post(port, "{\"jsonrpc\":\"2.0\",\"method\":\"ping\",\"id\":$id}")
            assertEquals(200, reply.status)
            assertEquals(-32600, reply.json().getJSONObject("error").getInt("code"))
            assertEquals(JSONObject.NULL, reply.json().get("id"))
        }
        val duplicate = post(port, "{\"jsonrpc\":\"2.0\",\"method\":\"ping\",\"id\":1,\"i\\u0064\":2}")
        assertEquals(-32700, duplicate.json().getJSONObject("error").getInt("code"))
    }

    @Test fun everyMcpMethodAndNotificationRequiresStrictBearerAuthentication() = withServer { _, port, _ ->
        val bodies = listOf(rpc("initialize"), rpc("ping"), rpc("tools/list"), rpc("tools/call"), "{\"jsonrpc\":\"2.0\",\"method\":\"notifications/initialized\"}")
        for (body in bodies) for (auth in listOf(null, "Bearer", "Bearer ", "Bearer wrong", "Bearer ${token.lowercase()}", "Basic $token"))
            assertEquals(401, post(port, body, auth).status)
        assertEquals(200, post(port, rpc("ping"), "bEaReR $token").status)
        assertEquals(200, raw(port, "POST /mcp HTTP/1.1\r\naUtHoRiZaTiOn: bEaReR $token\r\nContent-Length: 40\r\n\r\n{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"ping\"}").status)
        assertEquals(404, post(port, rpc("ping"), null, "/mcp?token=$token").status)
    }

    @Test fun healthIsAnonymousMinimalAndOnlyExactPathsAreAccepted() = withServer { _, port, _ ->
        val health = raw(port, "GET /health HTTP/1.1\r\nHost: localhost\r\n\r\n")
        assertEquals(200, health.status); assertEquals(setOf("ok"), health.json().keys().asSequence().toSet())
        for (path in listOf("/mcp/extra", "/mcpx", "/mcp/", "/mcp?x=1", "/%6dcp", "/health?x=1"))
            assertEquals(404, post(port, rpc("ping"), path = path).status)
        assertEquals(405, raw(port, "GET /mcp HTTP/1.1\r\n\r\n").status)
    }

    @Test fun initializeAndToolCallsUseActualCallbacksAndJsonText() = withServer { _, port, dir ->
        val init = post(port, rpc("initialize", params = JSONObject().put("protocolVersion", "2025-03-26").put("capabilities", JSONObject()).put("clientInfo", JSONObject().put("name", "test").put("version", "1"))))
        assertEquals(200, init.status); assertEquals("2025-03-26", init.json().getJSONObject("result").getString("protocolVersion"))
        assertTrue(init.json().getJSONObject("result").getJSONObject("capabilities").has("tools"))
        val list = post(port, rpc("tools/list")).json().getJSONObject("result").getJSONArray("tools")
        assertEquals(4, list.length())
        File(dir, "diagnostics").mkdir(); File(dir, "diagnostics/state.json").writeText("{\"中文\":\"🙂\"}")
        for (name in listOf("version_info", "diag_read", "error_tail", "fs_read")) {
            val args = when (name) { "error_tail" -> JSONObject().put("limit", 128); "fs_read" -> JSONObject().put("path", "diagnostics/state.json"); else -> JSONObject() }
            val result = post(port, rpc("tools/call", params = JSONObject().put("name", name).put("arguments", args))).json().getJSONObject("result")
            assertFalse(result.getBoolean("isError")); assertEquals(result.getJSONObject("structuredContent").toString(), JSONObject(result.getJSONArray("content").getJSONObject(0).getString("text")).toString())
        }
    }

    @Test fun notificationsAreAuthenticated202WithEmptyBody() = withServer { _, port, _ ->
        for (method in listOf("notifications/initialized", "ping", "tools/list", "unknown")) {
            val reply = post(port, JSONObject().put("jsonrpc", "2.0").put("method", method).toString())
            assertEquals(202, reply.status); assertEquals(0, reply.body.size)
        }
    }

    @Test fun jsonRpcErrorsHaveCorrectCodesAndNeverEchoRequests() = withServer { _, port, _ ->
        fun check(body: String, code: Int) {
            val reply = post(port, body); assertEquals(200, reply.status)
            assertEquals(code, reply.json().getJSONObject("error").getInt("code"))
            assertFalse(String(reply.body, Charsets.UTF_8).contains("private-secret"))
        }
        for (body in listOf("{", "", "{\"jsonrpc\":\"2.0\"} trailing", "{\"a\":1,\"a\":2}")) check(body, -32700)
        for (body in listOf("[]", "42", "null", "{}", "{\"jsonrpc\":\"1.0\",\"method\":\"ping\",\"id\":1}", "{\"jsonrpc\":\"2.0\",\"method\":9,\"id\":1}", "{\"jsonrpc\":\"2.0\",\"method\":\"ping\",\"id\":true}")) check(body, -32600)
        check(rpc("private-secret"), -32601)
        for (body in listOf(rpc("ping", params = JSONArray()), rpc("tools/call"), rpc("tools/call", params = JSONObject().put("name", "diag_read").put("arguments", JSONArray())), rpc("tools/call", params = JSONObject().put("name", "error_tail").put("arguments", JSONObject().put("limit", "20"))), rpc("tools/call", params = JSONObject().put("name", "diag_read").put("arguments", JSONObject().put("private-secret", true))))) check(body, -32602)
        val result = post(port, rpc("tools/call", params = JSONObject().put("name", "private-secret").put("arguments", JSONObject()))).json().getJSONObject("result")
        assertTrue(result.getBoolean("isError")); assertFalse(result.toString().contains("private-secret"))
    }

    @Test fun malformedAndAmbiguousFramingIsRejected() = withServer { _, port, _ ->
        val header = "POST /mcp HTTP/1.1\r\nAuthorization: Bearer $token\r\n"
        for (framing in listOf("Content-Length: -1", "Content-Length: abc", "Content-Length: 1\r\nContent-Length: 1", "Content-Length: 0\r\nTransfer-Encoding: chunked", "Content-Length: 0\r\nAuthorization: Bearer $token", "Content-Length: 2\r\n folded: x"))
            assertEquals(400, raw(port, header + framing + "\r\n\r\n").status)
        assertEquals(411, raw(port, header + "\r\n").status)
        assertEquals(400, raw(port, header + "Content-Length: 9\r\n\r\n{}").status)
        assertEquals(413, raw(port, header + "Content-Length: 65537\r\n\r\n").status)
        assertEquals(431, raw(port, header + "X-Large: " + "x".repeat(17000) + "\r\nContent-Length: 0\r\n\r\n").status)
        val bytes = (header + "Content-Length: 2\r\n\r\n").toByteArray() + byteArrayOf(0xc3.toByte(), 0x28)
        assertEquals(400, exchange(port, bytes).status)
    }

    @Test fun partialBodiesTimeoutAndStopClosesActiveSocketsThenRestarts() = withServer { server, port, _ ->
        val header = "POST /mcp HTTP/1.1\r\nAuthorization: Bearer $token\r\nContent-Length: 9\r\n\r\n{"
        assertEquals(408, raw(port, header, shutdown = false).status)
        val client = Socket("127.0.0.1", port)
        client.soTimeout = 4000
        client.getOutputStream().write("POST /mcp HTTP/1.1\r\n".toByteArray())
        invoke(server, "stop")
        assertEquals(false, invoke(server, "getRunning")); assertEquals(0, invoke(server, "getBoundPort"))
        assertEquals(-1, client.getInputStream().read()); client.close()
        try { Socket("127.0.0.1", port).close(); fail("Stopped port is still open") } catch (_: java.io.IOException) { }
        val restarted = invoke(server, "start") as Int
        assertTrue(restarted > 0); assertEquals(restarted, invoke(server, "start"))
        assertEquals(200, post(restarted, rpc("ping")).status)
    }

    @Test fun bindsOnlyIpv4LoopbackAndBoundedPoolRejectsOverload() = withServer { server, port, _ ->
        assertEquals(true, invoke(server, "getRunning")); assertEquals(port, invoke(server, "getBoundPort"))
        // A specific bind must permit another local address to own the same port.
        ServerSocket().use { other -> other.bind(java.net.InetSocketAddress(InetAddress.getByName("127.0.0.2"), port)) }
        val sockets = (0 until 20).map { Socket("127.0.0.1", port).apply { soTimeout = 7000 } }
        try {
            val overload = sockets.last().getInputStream().readBytes()
            assertTrue(String(overload, Charsets.US_ASCII).startsWith("HTTP/1.1 503"))
            invoke(server, "stop")
        } finally { sockets.forEach { it.close() } }
    }
}
