package qa

import com.hcbiu.elcton.DiagnosticMcpServer
import com.hcbiu.elcton.DiagnosticTools
import com.hcbiu.elcton.McpToken
import com.hcbiu.elcton.CombinedMcpTools
import com.hcbiu.elcton.PhoneMcpTools
import org.json.JSONArray
import org.json.JSONObject
import java.io.File

/** Host-only fixture. Production server and tools are exercised without Android or WearEngine. */
fun main(args: Array<String>) {
    require(args.size == 1 || (args.size == 2 && args[1] == "--release-tools")) {
        "Expected temporary fixture directory and optional --release-tools"
    }
    val root = File(args[0])
    require(root.isDirectory && root.listFiles().orEmpty().isEmpty()) { "Fixture must be a new empty directory" }
    val errors = listOf(
        JSONObject().put("time", "fixture-1").put("code", "synthetic_one").put("message", "synthetic 一"),
        JSONObject().put("time", "fixture-2").put("code", "synthetic_two").put("message", "synthetic 二🙂")
    )
    val state = JSONObject().put("connected", false).put("label", "离线🙂").put("source", "synthetic-host-fixture")
    val diagnostics = File(root, "diagnostics").apply { mkdir() }
    File(diagnostics, "wear-errors.jsonl").writeText(errors.joinToString("\n", postfix = "\n"), Charsets.UTF_8)
    File(diagnostics, "state.json").writeText(state.toString(), Charsets.UTF_8)
    val token = McpToken.loadOrCreate(File(root, "mcp.token"))
    val tools = DiagnosticTools(root,
        { limit -> JSONArray(errors.takeLast(limit)) },
        { if (File(root, "fail.diag").exists()) throw IllegalStateException("private-secret /private/path"); JSONObject(state.toString()) },
        { JSONObject().put("versionName", "host-fixture").put("source", "synthetic-host-fixture") })
    // Legacy no-flag host remains exactly four tools. Release clients exercise the
    // real combined list/validation; no Android action is fabricated in a JVM.
    val selected = if (args.size == 2) CombinedMcpTools(tools, PhoneMcpTools { _, _ ->
        JSONObject().put("error", "android_runtime_not_started_in_host")
    }) else tools
    val server = DiagnosticMcpServer(token, selected, 0)
    val hook = Thread({ server.stop() }, "diag-mcp-host-shutdown")
    Runtime.getRuntime().addShutdownHook(hook)
    try {
        println(JSONObject().put("ready", true).put("port", server.start()).toString())
        System.out.flush()
        while (true) {
            val command = readlnOrNull() ?: break
            if (command == "stop") break
        }
        server.stop()
        println(JSONObject().put("stopped", true).put("running", server.running).put("boundPort", server.boundPort).toString())
        System.out.flush()
    } finally {
        server.stop()
        Runtime.getRuntime().removeShutdownHook(hook)
    }
}
