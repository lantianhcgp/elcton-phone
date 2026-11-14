package com.hcbiu.elcton

import org.json.JSONObject
import java.io.ByteArrayOutputStream
import java.net.HttpURLConnection
import java.net.URL
import java.nio.ByteBuffer
import java.nio.charset.CodingErrorAction

/** Fixed public read-only pickup endpoint; never accepts a URL, credential or device id from MCP. */
class PickupClient(private val endpoint: String = ENDPOINT) {
    @Volatile private var connection: HttpURLConnection? = null
    @Volatile private var cancelled = false

    fun cancel() { cancelled = true; connection?.disconnect() }
    fun fetch(pickup: String): String {
        require(Regex("[0-9]{6}").matches(pickup)) { "取件码必须是六位数字" }
        check(!cancelled) { "取件码导入已取消" }
        val url = URL(endpoint + "?action=get&pickup=" + pickup)
        val current = url.openConnection() as HttpURLConnection
        connection = current
        current.instanceFollowRedirects = false
        current.connectTimeout = 8000
        current.readTimeout = 10000
        current.requestMethod = "GET"
        current.setRequestProperty("Accept", "application/json")
        current.setRequestProperty("Cache-Control", "no-store")
        val start = System.nanoTime()
        try {
            check(!cancelled) { "取件码导入已取消" }
            val status = current.responseCode
            if (status != 200) throw IllegalArgumentException(if (status == 404) "取件码不存在" else "取件码服务暂不可用")
            require(current.contentLengthLong <= 65536) { "取件码响应过大" }
            val bytes = current.inputStream.use { input ->
                val out = ByteArrayOutputStream(); val buffer = ByteArray(4096)
                while (true) {
                    check(!cancelled) { "取件码导入已取消" }
                    check(System.nanoTime() - start < 20_000_000_000L) { "取件码服务超时" }
                    val count = input.read(buffer)
                    if (count < 0) break
                    require(out.size() + count <= 65536) { "取件码响应过大" }
                    out.write(buffer, 0, count)
                }
                out.toByteArray()
            }
            val text = Charsets.UTF_8.newDecoder().onMalformedInput(CodingErrorAction.REPORT)
                .onUnmappableCharacter(CodingErrorAction.REPORT).decode(ByteBuffer.wrap(bytes)).toString()
            return parseResponse(text)
        } finally { current.disconnect(); connection = null }
    }

    companion object {
        // HTTPS on this public server has an invalid certificate. Match its documented HTTP read
        // route with a domain-only Android cleartext exception; never disable TLS validation.
        const val ENDPOINT = "http://kebiao.qingyun3.com/api.php"
        fun parseResponse(raw: String): String {
            require(raw.length <= 65536) { "取件码响应过大" }
            val response = try { JSONObject(raw) } catch (_: Exception) { throw IllegalArgumentException("取件码响应格式无效") }
            require(response.opt("code") == "ok") { "取件码服务未返回课表" }
            val doc = if (response.opt("doc") is JSONObject) response.getJSONObject("doc") else response
            return PhoneSnapshot.encode(doc.toString())
        }
    }
}
