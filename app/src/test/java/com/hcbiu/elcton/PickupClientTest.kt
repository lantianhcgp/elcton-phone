package com.hcbiu.elcton

import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Test

/** Production pickup parser/client. HTTP fixtures are read-only synthetic evidence, not the live site. */
class PickupClientTest {
    private val document = "{\"schema\":\"elcton.schedule\",\"version\":1,\"settings\":{\"semesterStart\":\"2026-09-01\"},\"courses\":[]}"
    private fun response(doc: JSONObject = JSONObject(document)) = doc.put("code", "ok").toString()
    @Test fun flatPublicApiDocumentIsParsedThroughStrictExistingIngress() {
        assertEquals(PhoneSnapshot.encode(document), PickupClient.parseResponse(response()))
    }
    @Test fun nestedPublicApiDocumentUsesTheSameIngress() {
        assertEquals(PhoneSnapshot.encode(document), PickupClient.parseResponse(JSONObject().put("code", "ok").put("doc", JSONObject(document)).toString()))
    }
    @Test fun notFoundAndServerErrorsAreNeverImported() {
        for (raw in listOf("{}", "{\"code\":\"error\"}", "{\"code\":200}", "{\"code\":\"ok\",\"doc\":{}}", "not-json")) {
            assertTrue(runCatching { PickupClient.parseResponse(raw) }.isFailure)
        }
    }
    @Test fun malformedFieldsAndHugeResponsesAreRejectedWithoutTruncation() {
        val changed=JSONObject(document).getJSONObject("settings").put("semesterStart", "not-date")
        assertTrue(runCatching { PickupClient.parseResponse(response(JSONObject(document).put("settings",changed))) }.isFailure)
        assertTrue(runCatching { PickupClient.parseResponse("x".repeat(65537)) }.isFailure)
    }
    @Test fun invalidPickupNeverOpensANetworkConnection() {
        val client=PickupClient("http://127.0.0.1:1/api.php")
        for (code in listOf("12345", "1234567", "12345a", " 123456", "１２３４５６", "123456&x=1"))
            assertTrue(runCatching { client.fetch(code) }.exceptionOrNull() is IllegalArgumentException)
    }
    @Test fun cancellationBeforeFetchIsTerminal() {
        val client=PickupClient("http://127.0.0.1:1/api.php");client.cancel()
        assertTrue(runCatching { client.fetch("123456") }.exceptionOrNull() is IllegalStateException)
    }
    @Test fun realHttpClientFetchesExactlyTheSixDigitGetRoute() {
        fixture(200, response()) { url, request ->
            assertEquals(PhoneSnapshot.encode(document), PickupClient(url).fetch("123456"))
            assertTrue(request().startsWith("GET /api.php?action=get&pickup=123456 HTTP/1.1"))
        }
    }
    @Test fun redirect404AndOversizedContentAreRejectedByRealClient() {
        for (status in listOf(302,404,500)) fixture(status,"{}") {url,_->
            assertTrue(runCatching { PickupClient(url).fetch("123456") }.isFailure)
        }
        fixture(200,"x".repeat(65537)) {url,_-> assertTrue(runCatching { PickupClient(url).fetch("123456") }.isFailure) }
    }
    @Test fun malformedUtf8ResponseIsRejected() {
        fixtureBytes(200, byteArrayOf(0xC3.toByte(),0x28)) {url,_-> assertTrue(runCatching { PickupClient(url).fetch("123456") }.isFailure) }
    }
    private fun fixture(status:Int,body:String,run:(String,()->String)->Unit)=fixtureBytes(status,body.toByteArray(Charsets.UTF_8),run)
    private fun fixtureBytes(status:Int,body:ByteArray,run:(String,()->String)->Unit) {
        val server=java.net.ServerSocket(0,1,java.net.InetAddress.getByName("127.0.0.1"));server.soTimeout=3000
        val request=java.util.concurrent.atomic.AtomicReference("")
        val failure=java.util.concurrent.atomic.AtomicReference<Throwable?>()
        val thread=Thread {
            try { server.accept().use {socket->
                socket.soTimeout=3000
                val input=socket.getInputStream().bufferedReader(Charsets.US_ASCII)
                val lines=mutableListOf<String>()
                while(true){val line=input.readLine()?:break;if(line.isEmpty())break;lines.add(line)}
                request.set(lines.joinToString("\r\n"))
                val header="HTTP/1.1 $status Test\r\nContent-Length: ${body.size}\r\nConnection: close\r\nContent-Type: application/json\r\n\r\n"
                socket.getOutputStream().write(header.toByteArray(Charsets.US_ASCII));socket.getOutputStream().write(body);socket.getOutputStream().flush()
            }} catch(error:Throwable){failure.set(error)}
        }
        thread.start()
        try { run("http://127.0.0.1:${server.localPort}/api.php") {request.get()} }
        finally { thread.join(4000);server.close() }
        assertFalse("fixture thread must close",thread.isAlive)
        // Oversize rejection may intentionally close early; peer socket reset is not product data.
        failure.get()?.let {if(it !is java.net.SocketException)throw AssertionError("HTTP fixture failed",it)}
    }
}
