package com.hcbiu.elcton

import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Test
import java.util.concurrent.ConcurrentLinkedQueue
import java.util.concurrent.CountDownLatch
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicReference

/** Real pending-work/interruption primitives; no Android/WE success is simulated. */
class MainThreadActionsTest {
    private class Harness(timeout:Long=1000L) {
        val pending=ConcurrentLinkedQueue<()->Unit>()
        val posted=CountDownLatch(1)
        val dispatcher=MainThreadActions({block->pending.add(block);posted.countDown();true},{false},timeout)
        val reply=AtomicReference<JSONObject>()
        var worker:Thread?=null
        fun start(action:()->JSONObject){worker=Thread{reply.set(dispatcher.invoke(action))}.apply{start()};assertTrue(posted.await(2,TimeUnit.SECONDS))}
        fun drain(){while(true){val block=pending.poll()?:break;block()}}
        fun join(){worker!!.join(2000);assertFalse("worker terminates",worker!!.isAlive)}
    }
    @Test fun stopInvalidatesQueuedWritesEvenWhenInterruptedWorkerHasNotRunCleanup() {
        val h=Harness();var writes=0;h.start{writes++;JSONObject().put("saved",true)}
        h.dispatcher.invalidate();h.drain();h.join()
        assertEquals(0,writes);assertEquals("mcp_session_stopped",h.reply.get().getString("error"))
    }
    @Test fun interruptedRequestCannotExecuteAfterItsSocketIsClosed() {
        val h=Harness();var calls=0;h.start{calls++;JSONObject()}
        h.worker!!.interrupt();h.join();h.drain()
        assertEquals(0,calls);assertEquals("action_interrupted",h.reply.get().getString("error"))
    }
    @Test fun timedOutQueuedWorkIsRevokedRatherThanWrittenLater() {
        val h=Harness(25);var writes=0;h.start{writes++;JSONObject()};h.join();h.drain()
        assertEquals(0,writes);assertEquals("action_dispatch_timeout",h.reply.get().getString("error"))
    }
    @Test fun freshEpochExecutesAndExceptionsCannotStrandTheWaitingThread() {
        val h=Harness();h.dispatcher.invalidate();h.start{JSONObject().put("read",true)};h.drain();h.join();assertTrue(h.reply.get().getBoolean("read"))
        val failed=Harness();failed.start{error("PRIVATE_COURSE_CONTENT")};failed.drain();failed.join()
        assertEquals("action_failed",failed.reply.get().getString("error"));assertFalse(failed.reply.get().toString().contains("PRIVATE_COURSE_CONTENT"))
    }
    @Test fun failedPostCannotLeaveAnUnboundedWait() {
        val dispatcher=MainThreadActions({false},{false},25)
        assertEquals("action_dispatch_unavailable",dispatcher.invoke{JSONObject()}.getString("error"))
    }
}
