package com.hcbiu.elcton

import org.json.JSONArray
import org.json.JSONObject
import java.util.ArrayDeque

/** Diagnostics only: bounded in-memory append, no SDK, disk, timer or executor. */
class P2pTrace(
    val origin: String,
    private val wallClock: () -> Long,
    private val elapsedClock: () -> Long
) {
    data class Context(val generation: Int? = null, val attemptId: Long? = null,
        val nativeGeneration: Long? = null, val deviceRef: Int? = null, val trigger: String = "none",
        val attemptCurrent: (() -> Boolean)? = null)
    private val lock = Any()
    private val sid = "s-" + java.lang.Long.toUnsignedString(System.nanoTime(),36)
    private val tail = ArrayDeque<String>()
    private val pending = ArrayDeque<String>()
    private var seq = 0L
    private var dropped = 0L
    private var storage = "ok"
    private var context = Context()
    private val transferRefs = linkedMapOf<String,String>()
    private var refSerial = 0L
    private var changed: (() -> Unit)? = null
    private var peerPackage: String? = null
    private var peerFingerprint: String? = null
    fun peerIdentity(pkg: String, fingerprint: String) { synchronized(lock) { peerPackage=pkg; peerFingerprint=fingerprint } }
    init { require(origin == "phone-device" || origin == "host-test") }
    fun onChanged(callback: () -> Unit) { synchronized(lock) { changed=callback } }
    fun bind(generation:Int, attemptId:Long?=null, deviceRef:Int?=null, trigger:String="none", attemptCurrent:(()->Boolean)?=null) {
        synchronized(lock) {
            val previous=if(context.generation==generation)context else Context()
            context=Context(generation,attemptId ?: previous.attemptId,previous.nativeGeneration,
                deviceRef ?: previous.deviceRef,trigger,
                attemptCurrent ?: if(attemptId==null)previous.attemptCurrent else null)
        }
    }
    fun bindRegistration(c:Context):Context = synchronized(lock) {
        val registered=c.copy(attemptId=null)
        if(context.generation==c.generation)context=registered
        registered
    }
    /** Only the captured registration's exact two-generation pair can borrow a recent send. */
    fun related(c:Context):Context = synchronized(lock) {
        if(context.generation==c.generation && context.nativeGeneration==c.nativeGeneration)
            c.copy(attemptId=context.attemptId,trigger=context.trigger) else c
    }
    fun matches(c:Context):Boolean = synchronized(lock) {
        context.generation==c.generation && context.nativeGeneration==c.nativeGeneration && context.attemptId==c.attemptId
    }
    fun metadata(raw:String,outgoing:Boolean=false):Map<String,Any?> {
        val m=parseMetadata(raw,outgoing)
        val id=m["transferRef"] as? String
        val ref=if(id.isNullOrEmpty())"none" else synchronized(lock) {
            // Salted keys, no raw transferId retained; bounded per trace SID.
            val digest=java.security.MessageDigest.getInstance("SHA-256").digest((sid+":"+id).toByteArray(Charsets.UTF_8))
                .joinToString(""){"%02x".format(it)}
            transferRefs[digest] ?: run {
                if(transferRefs.size==128)transferRefs.remove(transferRefs.keys.first())
                ("r"+(++refSerial)).also{transferRefs[digest]=it}
            }
        }
        return m+mapOf("transferRef" to ref)
    }
    fun context(): Context = synchronized(lock) { context }
    fun sequence(): Long = synchronized(lock) { seq }
    fun fields(c:Context):Map<String,Any?> = mapOf("generation" to c.generation,"attemptId" to c.attemptId,
        "nativeGeneration" to c.nativeGeneration,"deviceRef" to c.deviceRef,"trigger" to c.trigger)
    fun emit(layer:String, stage:String, fields:Map<String,Any?>) {
        var notify:(()->Unit)?=null
        synchronized(lock) {
            seq++
            try {
                val e=JSONObject().put("schema",1).put("origin",origin).put("sid",sid).put("seq",seq)
                    .put("wallMs",wallClock()).put("elapsedMs",elapsedClock()).put("layer",if(layer=="adapter")"adapter" else "engine")
                    .put("stage",if(stage in STAGES)stage else "OTHER").put("outcome","observed").put("stale",false)
                    .put("bytes",JSONObject.NULL).put("generation",JSONObject.NULL).put("nativeGeneration",JSONObject.NULL)
                    .put("attemptId",JSONObject.NULL).put("dropped",dropped)
                for((key,value) in fields) {
                    if(key in NUMBERS && (value is Byte || value is Short || value is Int || value is Long))e.put(key,value)
                    else if(key=="stale" && value is Boolean)e.put(key,value)
                    else if(key in LABELS && value is String)e.put(key,if(value in SAFE_LABELS || (key=="transferRef" && value.matches(Regex("r[0-9]{1,19}"))))value else "other")
                }
                e.put("truncated",false).put("originalBytes",0)
                val original=e.toString().toByteArray(Charsets.UTF_8).size
                e.put("originalBytes",original)
                var line=e.toString()
                if(line.toByteArray(Charsets.UTF_8).size>2048) {
                    e.put("truncated",true)
                    for(key in LABELS)e.remove(key)
                    line=e.toString()
                }
                check(line.toByteArray(Charsets.UTF_8).size<=2048)
                val evicted=if(tail.size==128){dropped++;tail.removeFirst()}else null
                tail.addLast(line)
                if(storage!="trace_storage_full") {
                    if(pending.size==128){if(pending.removeFirst()!=evicted)dropped++}
                    pending.addLast(line)
                }
                notify=changed
            } catch(_:Throwable) { dropped++ }
        }
        try { notify?.invoke() }catch(_:Throwable){}
    }
    fun read(afterSeq:Long,limit:Int):JSONObject = synchronized(lock) {
        val selected=tail.map{JSONObject(it)}.filter{it.getLong("seq")>afterSeq}
        val page=selected.take(limit.coerceIn(1,128))
        val oldest=tail.firstOrNull()?.let{JSONObject(it).getLong("seq")}?:0L
        JSONObject().put("schema",1).put("origin",origin).put("sid",sid).put("traceSeq",seq).put("clockBasis","monotonic-supplied-ms")
            .put("events",JSONArray(page)).put("buffer",tail.size).put("dropped",dropped).put("storage",storage)
            .put("afterSeq",afterSeq).put("nextSeq",page.lastOrNull()?.getLong("seq")?:afterSeq)
            .put("oldestSeq",oldest).put("has_more",selected.size>page.size || (oldest>0 && afterSeq<oldest-1))
            .put("peerPackage",peerPackage ?: JSONObject.NULL).put("peerFingerprint",peerFingerprint ?: JSONObject.NULL)
    }
    /** Called only by the existing DiagnosticRuntime writer. false = quota exhausted. */
    fun persist(write:(String)->Boolean) {
        while(true) {
            val line=synchronized(lock) { if(storage=="trace_storage_full")return; pending.firstOrNull() } ?: return
            try {
                val accepted=write(line+"\n")
                synchronized(lock) {
                    if(!accepted){storage="trace_storage_full";return}
                    if(pending.firstOrNull()==line)pending.removeFirst()
                    storage="ok"
                }
            }catch(_:Throwable){synchronized(lock){storage="trace_write_failed"};return}
        }
    }
    companion object {
        private val NUMBERS=setOf("generation","nativeGeneration","attemptId","deviceRef","bytes","resultCode","retry","protocolVersion")
        private val LABELS=setOf("outcome","reason","trigger","type","protocol","sender","transferRef","direction")
        private val SAFE_LABELS=setOf("observed","ok","fail","sync_exception","none","connect","scan","cancel","close","fail_cleanup","register_replace","stale_registration","task_fail_cleanup","sync_fail_cleanup","ready_timeout","install_timeout","reg_timeout","generation","type","data","size","ascii","empty","json","protocol","version","sender","transferId","fields","accepted","other","READY","HELLO","ACK","APPLIED","EXPORT_META","EXPORT_CHUNK","ERROR","CANCELLED","EXPORT_CLOSED","CANCEL","BEGIN","CHUNK","END","EXPORT_REQUEST","EXPORT_NEXT","EXPORT_DONE","elcton.sync","watch","phone","present","phone-outgoing","watch-ingress")
        private val STAGES=setOf("CONNECT_REQUEST","PEER_CONFIG","REG_CALL","REG_TASK_OK","REG_TASK_FAIL","SEND_CALL","SEND_TASK_OK","SEND_TASK_FAIL","SEND_RESULT","RX_NATIVE_ENTRY","RX_ADAPTER_REJECT","RX_DECODE","RX_ENGINE_ENTRY","RX_PROTOCOL_ACCEPT","RX_PROTOCOL_REJECT","READY_ACCEPT","INSTALL_TIMEOUT","REG_TIMEOUT","HELLO_RETRY","READY_TIMEOUT","FAIL","CANCEL","CLOSE","UNREG_CALL","UNREG_TASK_OK","UNREG_TASK_FAIL")
        /** Read-only replica; never replaces the original PacketIngress result. No raw fields escape. */
        fun classify(raw:String):Map<String,Any?> = parseMetadata(raw,false).let {
            it+mapOf("transferRef" to (if((it["transferRef"] as? String).isNullOrEmpty())"none" else "present"))
        }
        fun classifyOutgoing(raw:String):Map<String,Any?> = parseMetadata(raw,true).let {
            it+mapOf("transferRef" to (if((it["transferRef"] as? String).isNullOrEmpty())"none" else "present"))
        }
        private fun parseMetadata(raw:String,outgoing:Boolean):Map<String,Any?> {
            if(raw.isEmpty())return mapOf("reason" to "empty")
            if(raw.length>1024)return mapOf("reason" to "size")
            if(raw.any{it.code !in 32..126})return mapOf("reason" to "ascii")
            val m=try{JSONObject(raw)}catch(_:Throwable){return mapOf("reason" to "json")}
            val type=m.opt("type") as? String
            val base=mapOf("type" to (if(type in SAFE_LABELS)type else "other"),
                "protocol" to (if(m.opt("protocol")=="elcton.sync")"elcton.sync" else "other"),
                "sender" to (if(m.opt("sender") in setOf("watch","phone"))m.opt("sender") else "other"),
                "protocolVersion" to exactInteger(m.opt("version")),
                "direction" to if(outgoing)"phone-outgoing" else "watch-ingress",
                "transferRef" to (m.opt("transferId") as? String))
            val reason=when {
                m.opt("protocol")!="elcton.sync"->"protocol"
                exactInteger(m.opt("version"))!=1L->"version"
                m.opt("sender")!=(if(outgoing)"phone" else "watch")->"sender"
                m.opt("type") !is String->"type"
                m.opt("transferId") !is String->"transferId"
                else->if(outgoing || PacketIngress.watch(raw)!=null)"accepted" else "fields"
            }
            return base+mapOf("reason" to reason)
        }
    }
}
