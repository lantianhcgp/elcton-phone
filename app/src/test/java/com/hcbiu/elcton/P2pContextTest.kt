package com.hcbiu.elcton

import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Test

/** R5 r1 real producer counterexamples; HOST, no SDK or device claim. */
class P2pContextTest {
    private fun events(t:P2pTrace):List<JSONObject> { val a=t.read(0,128).getJSONArray("events");return (0 until a.length()).map{a.getJSONObject(it)} }
    @Test fun aNewConnectionMustNotInheritAnOldAttempt() {
        val t=P2pTrace("host-test",{1L},{2L})
        t.bind(7,9,3); t.bind(8,deviceRef=4)
        assertNull("new generation inherited previous attempt",t.context().attemptId)
        assertEquals(4,t.context().deviceRef)
    }
    @Test fun normalPhoneHelloIsOutgoingMetadataNotWatchSenderReject() {
        val h=P2pTraceEngineTest().Harness("SyncEngine",true); h.start()
        val send=events(h.trace as P2pTrace).first{it.getString("stage")=="SEND_CALL"}
        assertEquals("phone",send.getString("sender"))
        assertEquals("accepted",send.getString("reason"))
        assertEquals(1,send.getInt("protocolVersion"))
        assertEquals("phone-outgoing",send.getString("direction"))
    }
    @Test fun oldHelloTaskFailureIsStaleAfterSameGenerationRetryAndReady() {
        for(ready in listOf(false,true)) {
            val h=P2pTraceEngineTest().Harness("SyncEngine",true); h.start()
            val old=h.transport.sendFail!!
            if(ready) { h.transport.receiver!!(P2pTraceEngineTest.READY);h.clock.advance(0) }
            else h.clock.advance(5000)
            val before=h.updates.toList();old("late original failure");h.clock.advance(0)
            assertEquals(before,h.updates)
            val failed=events(h.trace as P2pTrace).last{it.getString("stage")=="SEND_TASK_FAIL"}
            assertTrue("old attempt Task failure marked current",failed.getBoolean("stale"))
        }
    }
    @Test fun readyAndRxEventsRetainTheRelatedSendAttempt() {
        val h=P2pTraceEngineTest().Harness("SyncEngine",true);h.start()
        h.transport.receiver!!(P2pTraceEngineTest.READY);h.clock.advance(0)
        val es=events(h.trace as P2pTrace);val sent=es.first{it.getString("stage")=="SEND_CALL"}
        for(stage in listOf("RX_ENGINE_ENTRY","RX_PROTOCOL_ACCEPT","READY_ACCEPT"))
            assertEquals("$stage dropped related attempt",sent.getLong("attemptId"),es.single{it.getString("stage")==stage}.getLong("attemptId"))
    }
    @Test fun transferReferencesDistinguishIdsWithoutPrivateText() {
        val h=P2pTraceEngineTest().Harness("SyncEngine",true);h.start()
        fun ack(id:String)="{\"protocol\":\"elcton.sync\",\"version\":1,\"sender\":\"watch\",\"type\":\"ACK\",\"transferId\":\"$id\",\"seq\":0}"
        for(id in listOf("PRIVATE_A","PRIVATE_B","PRIVATE_A")){h.transport.receiver!!(ack(id));h.clock.advance(0)}
        val refs=events(h.trace as P2pTrace).filter{it.getString("stage")=="RX_PROTOCOL_ACCEPT"}.map{it.getString("transferRef")}
        assertEquals(3,refs.size);assertEquals(refs[0],refs[2]);assertNotEquals("different IDs collapsed",refs[0],refs[1])
        assertFalse((h.trace as P2pTrace).read(0,128).toString().contains("PRIVATE_"))
    }
}
