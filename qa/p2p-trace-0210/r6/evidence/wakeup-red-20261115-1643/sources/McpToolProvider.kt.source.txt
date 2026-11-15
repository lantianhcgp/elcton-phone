package com.hcbiu.elcton

import org.json.JSONArray
import org.json.JSONObject

interface McpToolProvider {
    fun list(): JSONArray
    fun validArguments(name: String, arguments: JSONObject): Boolean
    fun call(name: String, arguments: JSONObject): JSONObject
}

/** Composition only: all actions still resolve to the single application business runtime. */
class CombinedMcpTools(private vararg val providers: McpToolProvider) : McpToolProvider {
    private fun owner(name: String) = providers.firstOrNull { provider ->
        val list = provider.list()
        (0 until list.length()).any { list.getJSONObject(it).getString("name") == name }
    }
    override fun list(): JSONArray = JSONArray().apply {
        val names = mutableSetOf<String>()
        providers.forEach { provider ->
            val list = provider.list()
            for (i in 0 until list.length()) {
                val item = list.getJSONObject(i)
                check(names.add(item.getString("name"))) { "Duplicate MCP tool" }
                put(item)
            }
        }
    }
    override fun validArguments(name: String, arguments: JSONObject) = owner(name)?.validArguments(name, arguments) ?: true
    override fun call(name: String, arguments: JSONObject): JSONObject = owner(name)?.call(name, arguments)
        ?: JSONObject().put("isError", true).put("structuredContent", JSONObject().put("error", "unknown_tool"))
            .put("content", JSONArray().put(JSONObject().put("type", "text").put("text", "{\"error\":\"unknown_tool\"}")))
}
