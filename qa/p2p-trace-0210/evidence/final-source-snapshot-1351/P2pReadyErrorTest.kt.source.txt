package com.hcbiu.elcton

import org.junit.Assert.*
import org.junit.Test

/** Valid peer handshake errors must not be reworded as a missing-receiver diagnosis. */
class P2pReadyErrorTest {
    private fun peer(type:String="ERROR",code:String="CORRUPT_JOURNAL",id:String="") = PacketIngress.watch("{\"protocol\":\"elcton.sync\",\"version\":1,\"sender\":\"watch\",\"type\":\"$type\",\"transferId\":\"$id\",\"code\":\"$code\"}")!!
    private fun failure(awaiting:Boolean,active:Boolean,type:String="ERROR",code:String="CORRUPT_JOURNAL",id:String=""):String? {
        val method=PacketIngress::class.java.methods.find{it.name=="preparationError"}
        assertNotNull("Waiting-for-READY has no error dispatch",method)
        return method!!.invoke(PacketIngress,peer(type,code,id),awaiting,active) as String?
    }
    @Test fun matchingHandshakeErrorReachesUserWithFinitePeerCode() {
        val message=failure(true,false)
        assertNotNull(message);assertTrue(message!!.contains("CORRUPT_JOURNAL"));assertFalse(message.contains("开始接收"))
        assertTrue(failure(true,false,code="300")!!.contains("300"))
    }
    @Test fun staleOrActiveTransferErrorDoesNotAbortPreparation() {
        assertNull(failure(false,false));assertNull(failure(true,true));assertNull(failure(true,false,id="old-transfer"))
    }
}
