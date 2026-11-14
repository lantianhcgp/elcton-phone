package com.hcbiu.elcton

import org.junit.Assert.*
import org.junit.Test

class ProtocolIngressAuditTest {
    private val empty="{\"schema\":\"elcton.schedule\",\"version\":1,\"settings\":{\"semesterStart\":\"2026-09-01\"},\"courses\":[]}"
    @Test fun snapshotVersionDoesNotAcceptStringsOrFractions() {
        for(value in listOf("\"1\"","1.9","true")) {
            assertThrows(IllegalArgumentException::class.java) { PhoneSnapshot.encode(empty.replace("\"version\":1","\"version\":"+value)) }
        }
        assertEquals(empty,PhoneSnapshot.encode(empty))
    }
    @Test fun yearZeroIsRejectedEvenThoughLocalDateCanParseIt() {
        assertThrows(IllegalArgumentException::class.java) { PhoneSnapshot.encode(empty.replace("2026-09-01","0000-09-01")) }
    }
    @Test fun malformedParserExceptionNeverAppearsInUiDiagnostic() {
        val secret="PRIVATE_COURSE_FROM_MALFORMED_JSON"
        val shown=UserFacingError.explain("Expected ':' after a key at 29 [character 0 line 1] "+secret)
        assertFalse(shown.contains(secret))
        val validationMethod=UserFacingError::class.java.methods.find {it.name=="validation"}
        assertNotNull("Safe validation error function is missing",validationMethod)
        val safe=validationMethod!!.invoke(UserFacingError,"JSON failed "+secret).toString()
        assertFalse(safe.contains(secret))
    }
    @Test fun peerPacketMustBeStrictAsciiAndHaveAnExactNumericVersion() {
        val clazz=runCatching {Class.forName("com.hcbiu.elcton.PacketIngress")}.getOrNull()
        assertNotNull("Strict peer ingress is missing",clazz)
        val instance=clazz!!.getField("INSTANCE").get(null)
        val parse=clazz.getMethod("watch",String::class.java)
        val good="{\"protocol\":\"elcton.sync\",\"version\":1,\"sender\":\"watch\",\"type\":\"ACK\",\"transferId\":\"t1\",\"seq\":-1}"
        assertNotNull(parse.invoke(instance,good))
        for(bad in listOf(good.replace("\"version\":1","\"version\":1.9"),good.replace("\"version\":1","\"version\":\"1\""),good.replace("\"t1\"","12"),good.replace("t1","私有课程"),good.replace("\"seq\":-1","\"seq\":1.5"))) {
            assertNull(parse.invoke(instance,bad))
        }
    }
    @Test fun wholeOperationDeadlineIsNotExtendedByPacketActivity() {
        val clazz=runCatching {Class.forName("com.hcbiu.elcton.OperationDeadline")}.getOrNull()
        assertNotNull("Whole-operation deadline is missing",clazz)
        val guard=clazz!!.getConstructor().newInstance()
        val begin=clazz.getMethod("begin",Long::class.javaPrimitiveType,Long::class.javaPrimitiveType)
        val expired=clazz.getMethod("expired",Long::class.javaPrimitiveType)
        begin.invoke(guard,100L,45000L)
        assertEquals(false,expired.invoke(guard,45099L));assertEquals(true,expired.invoke(guard,45100L))
        clazz.getMethod("clear").invoke(guard);assertEquals(false,expired.invoke(guard,999999L))
    }
    @Test fun callbackAttemptsDoNotLetAnOldSendTerminateTheCurrentPacket() {
        val clazz=runCatching {Class.forName("com.hcbiu.elcton.SendAttempts")}.getOrNull()
        assertNotNull("Packet-level callback guard is missing",clazz)
        val guard=clazz!!.getConstructor().newInstance()
        val issue=clazz.getMethod("issue")
        val accepts=clazz.getMethod("accepts",Long::class.javaPrimitiveType)
        val first=issue.invoke(guard) as Long
        val next=issue.invoke(guard) as Long
        assertEquals(false,accepts.invoke(guard,first));assertEquals(true,accepts.invoke(guard,next))
        clazz.getMethod("invalidate").invoke(guard)
        assertEquals(false,accepts.invoke(guard,next))
    }
}
