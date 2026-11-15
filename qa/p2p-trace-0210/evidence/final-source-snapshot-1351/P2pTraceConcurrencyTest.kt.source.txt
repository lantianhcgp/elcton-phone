package com.hcbiu.elcton

import org.junit.Assert.*
import org.junit.Test
import java.util.concurrent.CountDownLatch
import java.util.concurrent.TimeUnit

/** HOST latch proof: writer is held inside write, emit/read complete before it is released. */
class P2pTraceConcurrencyTest {
    @Test fun blockedWriterDoesNotHoldAppendOrReadLock() {
        val type=Class.forName("com.hcbiu.elcton.P2pTrace")
        val trace=type.getConstructor(String::class.java,kotlin.jvm.functions.Function0::class.java,kotlin.jvm.functions.Function0::class.java).newInstance("host-test",{1L},{2L})
        val emit=type.getMethod("emit",String::class.java,String::class.java,Map::class.java)
        val read=type.getMethod("read",Long::class.javaPrimitiveType,Int::class.javaPrimitiveType)
        emit.invoke(trace,"engine","SEND_CALL",emptyMap<String,Any?>())
        val entered=CountDownLatch(1);val release=CountDownLatch(1);val completed=CountDownLatch(1)
        val writer=Thread{type.getMethod("persist",kotlin.jvm.functions.Function1::class.java).invoke(trace,{_:String->entered.countDown();release.await();true})}
        writer.start(); assertTrue("writer entered real write",entered.await(5,TimeUnit.SECONDS))
        val observer=Thread{emit.invoke(trace,"engine","SEND_RESULT",emptyMap<String,Any?>());read.invoke(trace,0L,128);completed.countDown()}
        observer.start()
        try { assertTrue("emit and read must complete while writer remains blocked",completed.await(5,TimeUnit.SECONDS)); assertEquals(1L,release.count) }
        finally { release.countDown();writer.join(5000);observer.join(5000) }
        assertFalse(writer.isAlive);assertFalse(observer.isAlive)
    }
}
