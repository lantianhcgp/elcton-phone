package com.hcbiu.elcton

import org.json.JSONObject
import org.json.JSONTokener
import java.io.ByteArrayOutputStream
import java.io.InputStream
import java.net.InetAddress
import java.net.InetSocketAddress
import java.net.ServerSocket
import java.net.Socket
import java.net.SocketTimeoutException
import java.nio.ByteBuffer
import java.nio.charset.CodingErrorAction
import java.security.MessageDigest
import java.util.Locale
import java.util.concurrent.ArrayBlockingQueue
import java.util.concurrent.ConcurrentHashMap
import java.util.concurrent.RejectedExecutionException
import java.util.concurrent.ThreadPoolExecutor
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicInteger

/** One-request-per-connection, loopback-only authenticated HTTP JSON-RPC endpoint. */
class DiagnosticMcpServer(private val token: String, private val tools: McpToolProvider, private val port: Int = 8766) {
    // Preserve the exact historical constructor used by diagnostic consumers/tests.
    constructor(token: String, tools: DiagnosticTools, port: Int = 8766) : this(token, tools as McpToolProvider, port)
    init {
        require(token.isNotEmpty() && token.length <= 256 && token.all { it.code in 33..126 }) { "Invalid MCP credential" }
        require(port in 0..65535) { "Invalid MCP port" }
    }
    @Volatile var running: Boolean = false
        private set
    @Volatile var boundPort: Int = 0
        private set
    private var listener: ServerSocket? = null
    private var acceptor: Thread? = null
    private var pool: ThreadPoolExecutor? = null
    private val clients = ConcurrentHashMap.newKeySet<Socket>()
    private val credential = token.toByteArray(Charsets.US_ASCII)

    @Synchronized fun start(): Int {
        if (running) return boundPort
        val socket = ServerSocket()
        try {
            socket.reuseAddress = true
            socket.bind(InetSocketAddress(InetAddress.getByName("127.0.0.1"), port), 16)
            val serial = AtomicInteger()
            val executor = ThreadPoolExecutor(4, 4, 0L, TimeUnit.MILLISECONDS, ArrayBlockingQueue(8),
                { task -> Thread(task, "diag-mcp-worker-${serial.incrementAndGet()}").apply { isDaemon = true } })
            listener = socket; pool = executor; boundPort = socket.localPort; running = true
            acceptor = Thread({ acceptLoop(socket, executor) }, "diag-mcp-accept").apply { isDaemon = true; start() }
            return boundPort
        } catch (_: Exception) { socket.close(); throw IllegalStateException("MCP listener unavailable") }
    }

    @Synchronized fun stop() {
        running = false
        listener?.runCatching { close() }; listener = null
        clients.forEach { it.runCatching { close() } }; clients.clear()
        val executor = pool; pool = null
        executor?.shutdownNow()
        val thread = acceptor; acceptor = null
        if (thread !== Thread.currentThread()) thread?.join(1000)
        // Catch sockets accepted concurrently with the first close pass.
        clients.forEach { it.runCatching { close() } }; clients.clear()
        if (!Thread.currentThread().name.startsWith("diag-mcp-worker-")) executor?.awaitTermination(1000, TimeUnit.MILLISECONDS)
        boundPort = 0
    }

    private fun acceptLoop(socket: ServerSocket, executor: ThreadPoolExecutor) {
        while (!socket.isClosed) {
            val client = try { socket.accept() } catch (_: Exception) { break }
            clients.add(client)
            if (socket.isClosed) { close(client); continue }
            try {
                client.soTimeout = READ_TIMEOUT_MS
                executor.execute { handle(client) }
            } catch (_: RejectedExecutionException) {
                try { respond(client, 503, httpError("busy")) } catch (_: Exception) { } finally { close(client) }
            } catch (_: Exception) { close(client) }
        }
    }

    private fun close(socket: Socket) { clients.remove(socket); socket.runCatching { close() } }
    private class HttpFailure(val status: Int, val code: String) : Exception()
    private data class Request(val method: String, val target: String, val headers: Map<String, String>)

    private fun handle(socket: Socket) {
        try {
            val input = socket.getInputStream()
            val request = readHeaders(input)
            if (request.target == "/health" && request.method == "GET") {
                respond(socket, 200, JSONObject().put("ok", true).toString()); return
            }
            if (request.target != "/mcp") throw HttpFailure(404, "not_found")
            if (request.method != "POST") throw HttpFailure(405, "method_not_allowed")
            if (!authorized(request.headers["authorization"])) throw HttpFailure(401, "unauthorized")
            if (request.headers.containsKey("transfer-encoding")) throw HttpFailure(400, "invalid_framing")
            val lengthText = request.headers["content-length"] ?: throw HttpFailure(411, "length_required")
            if (!lengthText.matches(Regex("[0-9]+"))) throw HttpFailure(400, "invalid_length")
            val length = lengthText.toLongOrNull() ?: throw HttpFailure(413, "body_too_large")
            if (length > MAX_BODY_BYTES) throw HttpFailure(413, "body_too_large")
            request.headers["content-type"]?.let {
                if (!it.substringBefore(';').trim().equals("application/json", true)) throw HttpFailure(415, "unsupported_media_type")
            }
            val bytes = ByteArray(length.toInt())
            var offset = 0
            while (offset < bytes.size) {
                val read = input.read(bytes, offset, bytes.size - offset)
                if (read < 0) throw HttpFailure(400, "incomplete_body")
                offset += read
            }
            val text = try {
                Charsets.UTF_8.newDecoder().onMalformedInput(CodingErrorAction.REPORT).onUnmappableCharacter(CodingErrorAction.REPORT)
                    .decode(ByteBuffer.wrap(bytes)).toString()
            } catch (_: Exception) { throw HttpFailure(400, "invalid_utf8") }
            val reply = dispatch(text)
            respond(socket, if (reply == null) 202 else 200, reply)
        } catch (e: HttpFailure) { runCatching { respond(socket, e.status, httpError(e.code)) } }
        catch (_: SocketTimeoutException) { runCatching { respond(socket, 408, httpError("read_timeout")) } }
        catch (_: Exception) { runCatching { respond(socket, 500, httpError("request_failed")) } }
        finally { close(socket) }
    }

    private fun readHeaders(input: InputStream): Request {
        var total = 0
        fun line(): String {
            val bytes = ByteArrayOutputStream()
            while (true) {
                val value = input.read()
                if (value < 0) throw HttpFailure(400, "incomplete_headers")
                if (++total > MAX_HEADER_BYTES) throw HttpFailure(431, "headers_too_large")
                if (value == 13) {
                    val next = input.read()
                    if (++total > MAX_HEADER_BYTES) throw HttpFailure(431, "headers_too_large")
                    if (next != 10) throw HttpFailure(400, "invalid_headers")
                    return String(bytes.toByteArray(), Charsets.US_ASCII)
                }
                if (value == 10 || value > 126 || (value < 32 && value != 9)) throw HttpFailure(400, "invalid_headers")
                bytes.write(value)
            }
        }
        val request = line().split(' ')
        if (request.size != 3 || request[0].isEmpty() || !request[0].all { it in 'A'..'Z' } ||
            !request[1].startsWith('/') || request[2] !in setOf("HTTP/1.1", "HTTP/1.0")) throw HttpFailure(400, "invalid_request_line")
        val headers = mutableMapOf<String, String>()
        while (true) {
            val value = line()
            if (value.isEmpty()) break
            if (headers.size >= 64) throw HttpFailure(431, "headers_too_large")
            val colon = value.indexOf(':')
            if (colon <= 0) throw HttpFailure(400, "invalid_headers")
            val name = value.substring(0, colon)
            if (!name.matches(Regex("[!#$%&'*+.^_`|~0-9A-Za-z-]+"))) throw HttpFailure(400, "invalid_headers")
            val key = name.lowercase(Locale.ROOT)
            if (headers.containsKey(key)) throw HttpFailure(400, "duplicate_header")
            headers[key] = value.substring(colon + 1).trim(' ', '\t')
        }
        return Request(request[0], request[1], headers)
    }

    private fun authorized(header: String?): Boolean {
        if (header == null) return false
        val match = Regex("(?i:Bearer) ([\\x21-\\x7e]+)").matchEntire(header) ?: return false
        return MessageDigest.isEqual(credential, match.groupValues[1].toByteArray(Charsets.US_ASCII))
    }

    private fun dispatch(text: String): String? {
        val syntax = StrictJson(text)
        val value = try {
            // Never let org.json coerce a JSON-RPC identity to Double/Long (or reject infinity).
            JSONTokener(syntax.validate()).nextValue()
        } catch (_: Exception) { return rpcError("null", -32700, "Parse error") }
        if (value !is JSONObject) return rpcError("null", -32600, "Invalid Request")
        val id = syntax.idToken ?: "null"
        val validId = syntax.validId
        if (value.opt("jsonrpc") != "2.0" || value.opt("method") !is String || !validId)
            return rpcError(if (validId) id else "null", -32600, "Invalid Request")
        val notification = syntax.idToken == null
        fun error(code: Int, message: String): String? = if (notification) null else rpcError(id, code, message)
        fun result(data: JSONObject): String? = if (notification) null else rpcReply(id, "result", data)
        val rawParams = if (value.has("params")) value.opt("params") else JSONObject()
        if (rawParams !is JSONObject) return error(-32602, "Invalid params")
        val params = rawParams
        return when (value.getString("method")) {
            "initialize" -> {
                if (params.keys().asSequence().any { it !in setOf("protocolVersion", "capabilities", "clientInfo") } ||
                    (params.has("protocolVersion") && params.opt("protocolVersion") !is String) ||
                    (params.has("capabilities") && params.opt("capabilities") !is JSONObject) ||
                    (params.has("clientInfo") && params.opt("clientInfo") !is JSONObject)) return error(-32602, "Invalid params")
                val requested = params.optString("protocolVersion", "2025-03-26")
                val protocol = if (requested in setOf("2024-11-05", "2025-03-26", "2025-06-18")) requested else "2025-03-26"
                result(JSONObject().put("protocolVersion", protocol).put("capabilities", JSONObject().put("tools", JSONObject().put("listChanged", false)))
                    .put("serverInfo", JSONObject().put("name", "elcton-diagnostics").put("version", "1")))
            }
            "ping", "notifications/initialized" -> if (params.length() != 0) error(-32602, "Invalid params") else result(JSONObject())
            "tools/list" -> if (params.length() != 0) error(-32602, "Invalid params") else result(JSONObject().put("tools", tools.list()))
            "tools/call" -> {
                if (params.keys().asSequence().any { it !in setOf("name", "arguments") } || params.opt("name") !is String)
                    return error(-32602, "Invalid params")
                val args = if (params.has("arguments")) params.opt("arguments") else JSONObject()
                if (args !is JSONObject || !tools.validArguments(params.getString("name"), args)) return error(-32602, "Invalid params")
                // Notifications are not calls and must not trigger callbacks or file I/O.
                if (notification) null else result(tools.call(params.getString("name"), args))
            }
            else -> error(-32601, "Method not found")
        }
    }

    // id is exclusively a complete RFC8259 token captured by StrictJson, or the literal null.
    // Serialize the envelope independently: JSONObject.numberToString is lossy on Android.
    private fun rpcReply(id: String, member: String, data: JSONObject): String =
        "{\"jsonrpc\":\"2.0\",\"id\":$id,\"$member\":$data}"
    private fun rpcError(id: String, code: Int, message: String) =
        rpcReply(id, "error", JSONObject().put("code", code).put("message", message))
    private fun httpError(code: String) = JSONObject().put("error", code).toString()
    private fun respond(socket: Socket, status: Int, payload: String?) {
        val bytes = payload?.toByteArray(Charsets.UTF_8) ?: ByteArray(0)
        val reason = when (status) {
            200 -> "OK"; 202 -> "Accepted"; 400 -> "Bad Request"; 401 -> "Unauthorized"; 404 -> "Not Found"; 405 -> "Method Not Allowed"
            408 -> "Request Timeout"; 411 -> "Length Required"; 413 -> "Payload Too Large"; 415 -> "Unsupported Media Type"
            431 -> "Request Header Fields Too Large"; 503 -> "Service Unavailable"; else -> "Internal Server Error"
        }
        val auth = if (status == 401) "WWW-Authenticate: Bearer\r\n" else ""
        val headers = "HTTP/1.1 $status $reason\r\nContent-Type: application/json; charset=utf-8\r\nContent-Length: ${bytes.size}\r\nConnection: close\r\nCache-Control: no-store\r\n$auth\r\n"
        socket.getOutputStream().apply { write(headers.toByteArray(Charsets.US_ASCII)); write(bytes); flush() }
    }

    /** org.json is permissive (especially on Android); reject non-RFC8259 syntax first. */
    private class StrictJson(private val text: String) {
        private var i = 0
        private var idStart = -1
        private var idEnd = -1
        var idToken: String? = null
            private set
        var validId = true
            private set
        fun validate(): String {
            space(); value(0); space(); if (i != text.length) bad()
            // Mask only the validated top-level id before org.json sees it. Nested ids are data.
            return if (idStart < 0) text else text.substring(0, idStart) + "null" + text.substring(idEnd)
        }
        private fun bad(): Nothing = throw IllegalArgumentException("Invalid JSON")
        private fun space() { while (i < text.length && text[i] in " \r\n\t") i++ }
        private fun value(depth: Int) {
            if (depth > 64 || i >= text.length) bad()
            when (text[i]) {
                '{' -> {
                    i++; space(); val keys = mutableSetOf<String>()
                    if (take('}')) return
                    while (true) {
                        if (i >= text.length || text[i] != '"') bad()
                        val start = i; string()
                        val key = JSONTokener(text.substring(start, i)).nextValue() as String
                        if (!keys.add(key)) bad()
                        space(); if (!take(':')) bad(); space()
                        val valueStart = i
                        value(depth + 1)
                        if (depth == 0 && key == "id") {
                            idStart = valueStart; idEnd = i; idToken = text.substring(valueStart, i)
                            validId = text[valueStart] == '"' || text[valueStart] == 'n' ||
                                text[valueStart] == '-' || text[valueStart] in '0'..'9'
                        }
                        space()
                        if (take('}')) return
                        if (!take(',')) bad(); space()
                    }
                }
                '[' -> {
                    i++; space(); if (take(']')) return
                    while (true) { value(depth + 1); space(); if (take(']')) return; if (!take(',')) bad(); space() }
                }
                '"' -> string()
                't' -> literal("true")
                'f' -> literal("false")
                'n' -> literal("null")
                '-', in '0'..'9' -> number()
                else -> bad()
            }
        }
        private fun take(c: Char): Boolean { if (i < text.length && text[i] == c) { i++; return true }; return false }
        private fun literal(word: String) { if (!text.startsWith(word, i)) bad(); i += word.length }
        private fun string() {
            i++
            while (i < text.length) {
                val c = text[i++]
                if (c == '"') return
                if (c.code < 32) bad()
                if (c == '\\') {
                    if (i >= text.length) bad()
                    when (text[i++]) {
                        '"', '\\', '/', 'b', 'f', 'n', 'r', 't' -> { }
                        'u' -> { repeat(4) { if (i >= text.length || text[i++] !in "0123456789abcdefABCDEF") bad() } }
                        else -> bad()
                    }
                }
            }
            bad()
        }
        private fun number() {
            take('-')
            if (!take('0')) { if (i >= text.length || text[i] !in '1'..'9') bad(); while (i < text.length && text[i] in '0'..'9') i++ }
            if (take('.')) { val start = i; while (i < text.length && text[i] in '0'..'9') i++; if (i == start) bad() }
            if (take('e') || take('E')) { if (!take('+')) take('-'); val start = i; while (i < text.length && text[i] in '0'..'9') i++; if (i == start) bad() }
        }
    }

    companion object {
        const val READ_TIMEOUT_MS = 2000
        const val MAX_HEADER_BYTES = 16 * 1024
        const val MAX_BODY_BYTES = 64 * 1024
    }
}
