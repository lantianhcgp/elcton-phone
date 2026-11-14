package qa

import com.hcbiu.elcton.*
import org.json.JSONArray
import org.json.JSONObject
import java.io.File

/** Termux JVM evidence: actual production listener and both production tool providers.
 * No Android dispatch/WE success is substituted. Action calls fail closed in this list-only host.
 */
fun main(args: Array<String>) {
    require(args.size == 1)
    val root=File(args[0]);require(root.isDirectory && root.listFiles().orEmpty().isEmpty())
    val token=McpToken.loadOrCreate(File(root,"mcp/token"))
    val diagnostics=DiagnosticTools(root,{JSONArray()},{JSONObject().put("scope","termux-production-jvm-list-only")},
        {JSONObject().put("versionName","0.2.9").put("versionCode",11).put("scope","host-not-apk")})
    val tools=CombinedMcpTools(diagnostics,PhoneMcpTools {_,_->JSONObject().put("error","android_runtime_not_started_in_host")})
    val server=DiagnosticMcpServer(token,tools,0)
    val shutdown=Thread {server.stop()}
    Runtime.getRuntime().addShutdownHook(shutdown)
    try {
        println(JSONObject().put("port",server.start()).put("scope","Termux JVM production HTTP/list; not Android/WE").toString());System.out.flush()
        while(readlnOrNull()?.let {it!="stop"} == true) {}
    } finally { server.stop(); Runtime.getRuntime().removeShutdownHook(shutdown) }
}
