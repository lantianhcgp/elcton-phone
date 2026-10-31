package com.hcbiu.elcton

import java.util.Base64

/** Host-only bridge executing the identical pure Kotlin publication/import classes.
 * Android authorization, WearProbe and the actual P2P SDK are deliberately not emulated.
 */
private fun decode(value: String) = String(Base64.getDecoder().decode(value), Charsets.UTF_8)
private fun encode(value: String) = Base64.getEncoder().encodeToString(value.toByteArray(Charsets.UTF_8))
fun main() {
    var publication: TransferSession? = null
    var returned: ExportSession? = null
    fun current(accepted: Boolean = true) {
        val item = checkNotNull(publication)
        println(listOf("P", accepted, item.complete, item.error ?: "", encode(item.currentMessage ?: "")).joinToString("\t"))
    }
    fun exportState(accepted: Boolean = true) {
        val item = checkNotNull(returned)
        if (item.result != null) {
            println(listOf("RESULT", accepted, item.error ?: "", item.sourceRevision, encode(checkNotNull(item.result))).joinToString("\t"))
        } else {
            val message = "{" + Wire.header(if(item.initialized)"EXPORT_NEXT" else "EXPORT_REQUEST",item.id) +
                (if(item.initialized)",\"seq\":"+item.nextSequence else "") + "}"
            println(listOf("E", accepted, item.error ?: "", encode(message)).joinToString("\t"))
        }
    }
    generateSequence(::readLine).forEach { line ->
        val parts = line.split('\t')
        when (parts[0]) {
            "publish" -> { publication=TransferSession(decode(parts[1]),parts[2],parts[3],parts[4].toLong(),parts[5],parts[6].toBooleanStrict());current() }
            "reply" -> current(checkNotNull(publication).reply(parts[1],parts[2],parts[3].toInt(),parts[4],parts[5].toLong(),parts[6]))
            "transport" -> { checkNotNull(publication).transportSucceeded();current() }
            "timeout" -> current(checkNotNull(publication).timeout())
            "cancel" -> { val item=checkNotNull(publication);println("C\t"+encode("{"+Wire.header("CANCEL",item.transferId)+"}"));publication=null }
            "export" -> { returned=ExportSession(parts[1]);exportState() }
            "meta" -> exportState(checkNotNull(returned).meta(parts[1],parts[2].toInt(),parts[3],parts[4].toInt(),parts[5].toLong()))
            "chunk" -> exportState(checkNotNull(returned).chunk(parts[1],parts[2].toInt(),decode(parts[3])))
            "quit" -> return
            else -> error("Unknown host command")
        }
    }
}
