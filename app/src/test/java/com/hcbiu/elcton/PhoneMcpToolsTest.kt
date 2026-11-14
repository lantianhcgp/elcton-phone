package com.hcbiu.elcton

import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Test

class PhoneMcpToolsTest {
    private val names = listOf("sync_connect", "sync_disconnect", "start_import", "start_publish", "abort", "courses_read", "courses_write", "pickup_import", "devices_list", "pairing_state", "sync_state")
    private fun args(name: String): JSONObject = when(name) {
        "sync_connect" -> JSONObject().put("device_id", "paired-device")
        "start_publish" -> JSONObject().put("confirm", true)
        "courses_write" -> JSONObject().put("document", JSONObject().put("schema", "elcton.schedule"))
        "pickup_import" -> JSONObject().put("pickup", "012345")
        else -> JSONObject()
    }
    private fun assertRouted(name: String) {
        var count = 0
        var received = ""
        val input = args(name)
        val tools = PhoneMcpTools { actual, arguments ->
            count++; received = actual
            assertEquals(input.toString(), arguments.toString())
            JSONObject().put("accepted", true).put("state", "pending")
        }
        val result = tools.call(name, input)
        assertFalse(result.getBoolean("isError")); assertEquals(1, count); assertEquals(name, received)
        assertEquals("pending", result.getJSONObject("structuredContent").getString("state"))
        assertEquals(result.getJSONObject("structuredContent").toString(), JSONObject(result.getJSONArray("content").getJSONObject(0).getString("text")).toString())
    }
    @Test fun syncConnectRoutesToTheSharedAction() = assertRouted("sync_connect")
    @Test fun syncDisconnectRoutesToTheSharedAction() = assertRouted("sync_disconnect")
    @Test fun startImportRoutesToTheSharedAction() = assertRouted("start_import")
    @Test fun startPublishRoutesToTheSharedAction() = assertRouted("start_publish")
    @Test fun abortRoutesToTheSharedAction() = assertRouted("abort")
    @Test fun coursesReadRoutesToTheSharedData() = assertRouted("courses_read")
    @Test fun coursesWriteRoutesToTheSharedData() = assertRouted("courses_write")
    @Test fun pickupImportPreservesLeadingZeroAndRoutesToTheSharedImport() = assertRouted("pickup_import")
    @Test fun devicesListRoutesToTheSharedPairing() = assertRouted("devices_list")
    @Test fun pairingStateReportsOnlyObservedData() = assertRouted("pairing_state")
    @Test fun syncStateRoutesToTheSharedState() = assertRouted("sync_state")
    @Test fun everyRequestedActionAndDataToolHasARealContractBoundary() {
        val list = PhoneMcpTools { _, _ -> JSONObject() }.list()
        assertEquals(names, (0 until list.length()).map { list.getJSONObject(it).getString("name") })
        for(i in 0 until list.length()) {
            val tool = list.getJSONObject(i)
            assertFalse(tool.getJSONObject("inputSchema").getBoolean("additionalProperties"))
            assertTrue(tool.has("annotations"))
        }
    }
    @Test fun invalidArgumentsRejectBeforeAnyBusinessAction() {
        var calls = 0
        val tools = PhoneMcpTools { _, _ -> calls++; JSONObject() }
        for(name in names) assertTrue(tools.call(name, args(name).put("surprise", "secret-input")).getBoolean("isError"))
        for(name in listOf("sync_connect", "courses_write", "pickup_import", "start_publish")) assertTrue(tools.call(name, JSONObject()).getBoolean("isError"))
        for(value in listOf<Any>("true", 1, JSONObject.NULL)) {
            assertTrue(tools.call("start_publish", JSONObject().put("confirm", value)).getBoolean("isError"))
            assertTrue(tools.call("devices_list", JSONObject().put("refresh", value)).getBoolean("isError"))
        }
        for(value in listOf<Any>(123456, "12345", "1234567", " 123456", "１２３４５６", "12/456")) assertTrue(tools.call("pickup_import", JSONObject().put("pickup", value)).getBoolean("isError"))
        for(value in listOf<Any>(-1, 1.5, "1", JSONObject.NULL)) assertTrue(tools.call("courses_write", args("courses_write").put("expected_revision", value)).getBoolean("isError"))
        assertEquals(0, calls)
    }
    @Test fun providerFailuresAndUnknownToolsNeverEchoSecrets() {
        val tools = PhoneMcpTools { _, _ -> throw IllegalStateException("private-token /private/file") }
        for(result in listOf(tools.call("courses_read", JSONObject()), tools.call("private-token", JSONObject()))) {
            assertTrue(result.getBoolean("isError")); assertFalse(result.toString().contains("private-token")); assertFalse(result.toString().contains("/private/file"))
        }
    }
}
