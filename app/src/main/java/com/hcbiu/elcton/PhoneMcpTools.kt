package com.hcbiu.elcton

import org.json.JSONArray
import org.json.JSONObject

/** New capabilities are appended without altering the four diagnostic tools. */
class PhoneMcpTools(private val invoke: (String, JSONObject) -> JSONObject) : McpToolProvider {
    override fun list(): JSONArray = JSONArray().apply {
        put(tool("sync_connect", "Connect to a scanned paired device; returns accepted, not READY", props("device_id" to string()), listOf("device_id")))
        put(tool("sync_disconnect", "Disconnect and stop waiting for sync receipts", JSONObject()))
        put(tool("start_import", "Read watch snapshot into the shared import preview; confirm optionally", props("confirm" to boolean())))
        put(tool("start_publish", "Publish the current phone schedule through the same UI sync engine", props("confirm" to boolean(), "force" to boolean()), listOf("confirm")))
        put(tool("abort", "Cancel current import/transfer, invalidate callbacks and stop waiting", JSONObject()))
        put(tool("courses_read", "Read current phone courses, revision and pending import", JSONObject(), readOnly = true))
        put(tool("courses_write", "Validate shared import preview; confirm=true replaces phone data with backup", props("document" to JSONObject().put("type", "object"), "confirm" to boolean(), "expected_revision" to integer()), listOf("document")))
        put(tool("pickup_import", "Fetch a six-digit pickup code into the same shared import flow", props("pickup" to string().put("pattern", "^[0-9]{6}$"), "confirm" to boolean()), listOf("pickup"), openWorld = true))
        put(tool("devices_list", "Read paired devices; refresh=true checks existing authorization without UI", props("refresh" to boolean()), readOnly = false))
        put(tool("pairing_state", "Read the last observed pairing and authorization state, never guess", JSONObject(), readOnly = true))
        put(tool("sync_state", "Read sync acceptance/completion and import preview state", JSONObject(), readOnly = true))
    }

    override fun validArguments(name: String, arguments: JSONObject): Boolean {
        val keys = arguments.keys().asSequence().toSet()
        fun optionalBoolean(key: String) = !arguments.has(key) || arguments.opt(key) is Boolean
        return when (name) {
            "sync_connect" -> keys == setOf("device_id") && arguments.opt("device_id") is String && arguments.getString("device_id").let { it.isNotBlank() && it.length <= 256 }
            "sync_disconnect", "abort", "courses_read", "pairing_state", "sync_state" -> keys.isEmpty()
            "start_import" -> keys.all { it == "confirm" } && optionalBoolean("confirm")
            "start_publish" -> keys.all { it in setOf("confirm", "force") } && arguments.opt("confirm") is Boolean && optionalBoolean("force")
            "courses_write" -> keys.all { it in setOf("document", "confirm", "expected_revision") } && arguments.opt("document") is JSONObject && optionalBoolean("confirm") && (!arguments.has("expected_revision") || exactInteger(arguments.opt("expected_revision"))?.let { it >= 0 } == true)
            "pickup_import" -> keys.all { it in setOf("pickup", "confirm") } && arguments.opt("pickup") is String && Regex("[0-9]{6}").matches(arguments.getString("pickup")) && optionalBoolean("confirm")
            "devices_list" -> keys.all { it == "refresh" } && optionalBoolean("refresh")
            else -> true
        }
    }

    override fun call(name: String, arguments: JSONObject): JSONObject {
        if (name !in NAMES) return error("unknown_tool")
        if (!validArguments(name, arguments)) return error("invalid_arguments")
        return try {
            val data = invoke(name, JSONObject(arguments.toString()))
            result(data, data.has("error"))
        } catch (_: Exception) { error("tool_failed") }
    }

    private fun string() = JSONObject().put("type", "string")
    private fun boolean() = JSONObject().put("type", "boolean").put("default", false)
    private fun integer() = JSONObject().put("type", "integer").put("minimum", 0).put("maximum", 9007199254740990L)
    private fun props(vararg fields: Pair<String, JSONObject>) = JSONObject().apply { fields.forEach { put(it.first, it.second) } }
    private fun tool(name: String, description: String, properties: JSONObject, required: List<String> = emptyList(), readOnly: Boolean = false, openWorld: Boolean = false) = JSONObject()
        .put("name", name).put("description", description)
        .put("inputSchema", JSONObject().put("type", "object").put("properties", properties).put("required", JSONArray(required)).put("additionalProperties", false))
        .put("annotations", JSONObject().put("readOnlyHint", readOnly).put("destructiveHint", name in setOf("courses_write", "start_publish", "start_import", "pickup_import")).put("openWorldHint", openWorld))
    private fun error(code: String) = result(JSONObject().put("error", code), true)
    private fun result(data: JSONObject, failed: Boolean) = JSONObject().put("isError", failed).put("structuredContent", data)
        .put("content", JSONArray().put(JSONObject().put("type", "text").put("text", data.toString())))
    companion object {
        val NAMES = setOf("sync_connect", "sync_disconnect", "start_import", "start_publish", "abort", "courses_read", "courses_write", "pickup_import", "devices_list", "pairing_state", "sync_state")
    }
}
