package com.hcbiu.elcton

import org.junit.Assert.*
import org.junit.Test
import org.json.JSONObject

/** HOST equivalence against unchanged PacketIngress, all legal packet families and field boundaries. */
class P2pTraceIngressTest {
    @Test fun diagnosticClassifierAgreesWithOriginalWithoutReturningPrivateText() {
        val c=Class.forName("com.hcbiu.elcton.P2pTrace").getField("Companion").get(null)
        val method=c.javaClass.getMethod("classify",String::class.java)
        val samples=mutableListOf<String>()
        fun packet(type:String,fields:String="",id:String="t-1")="{\"protocol\":\"elcton.sync\",\"version\":1,\"sender\":\"watch\",\"type\":\"$type\",\"transferId\":\"$id\"$fields}"
        samples+=P2pTraceEngineTest.READY
        samples+=packet("ACK",",\"seq\":-1");samples+=packet("ACK",",\"seq\":127");samples+=packet("APPLIED",",\"digest\":\"1234abcd\",\"sourceRevision\":1")
        samples+=packet("EXPORT_META",",\"length\":32768,\"chunks\":128,\"digest\":\"1234abcd\",\"sourceRevision\":0")
        samples+=packet("EXPORT_CHUNK",",\"seq\":127,\"data\":\"PRIVATE_COURSE\"")
        samples+=packet("ERROR",",\"code\":\"READY_FAIL\"","");samples+=packet("CANCELLED");samples+=packet("EXPORT_CLOSED")
        val valid=samples.toList();assertTrue(valid.all{PacketIngress.watch(it)!=null})
        for(raw in valid){samples+=raw.replace("elcton.sync","PRIVATE_PROTOCOL");samples+=raw.replace("watch","PRIVATE_SENDER");samples+=raw.replace("\"version\":1","\"version\":1.5");samples+=raw.replace("\"version\":1","\"version\":\"1\"");samples+=raw.replace("t-1","PRIVATE_BAD_ID!")}
        samples+=listOf("","中","X".repeat(1025),"{",packet("PRIVATE_TYPE"),packet("ACK",",\"seq\":128"),packet("ACK",",\"seq\":-2"),packet("ACK",",\"seq\":1.2"),packet("EXPORT_CHUNK",",\"seq\":0,\"data\":\"${"X".repeat(901)}\""),P2pTraceEngineTest.READY.replace("8192","0"),P2pTraceEngineTest.READY.replace("false","\"false\""))
        for(raw in samples){@Suppress("UNCHECKED_CAST") val observed=method.invoke(c,raw) as Map<String,Any?>;assertEquals("classification differs on length ${raw.length}",PacketIngress.watch(raw)!=null,observed["reason"]=="accepted");assertFalse(JSONObject(observed).toString().contains("PRIVATE_"))}
    }
}
