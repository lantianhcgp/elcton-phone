package com.hcbiu.elcton

import org.json.JSONObject
import java.util.concurrent.CountDownLatch
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicBoolean
import java.util.concurrent.atomic.AtomicLong
import java.util.concurrent.atomic.AtomicReference

/** Scheduling only, never a second business state machine. All UI/MCP business runs on one owner. */
class MainThreadActions(
    private val post: ((() -> Unit) -> Boolean),
    private val isMain: () -> Boolean,
    private val timeoutMs: Long = 3000L
) {
    private val epoch = AtomicLong(0)
    fun invalidate() { epoch.incrementAndGet() }
    private fun failure(code: String) = JSONObject().put("error", code)
    private fun run(action: () -> JSONObject): JSONObject =
        try { action() } catch (_: Exception) { failure("action_failed") }

    fun invoke(action: () -> JSONObject): JSONObject {
        val expected = epoch.get()
        if (isMain()) return run(action)
        val done = CountDownLatch(1)
        val abandoned = AtomicBoolean(false)
        val result = AtomicReference(failure("action_dispatch_timeout"))
        val posted = try { post {
            try {
                result.set(when {
                    abandoned.get() -> failure("action_dispatch_cancelled")
                    expected != epoch.get() -> failure("mcp_session_stopped")
                    else -> run(action)
                })
            } finally { done.countDown() }
        } } catch (_: Exception) { false }
        if (!posted) { abandoned.set(true); return failure("action_dispatch_unavailable") }
        return try {
            if (!done.await(timeoutMs, TimeUnit.MILLISECONDS)) {
                abandoned.set(true)
                failure("action_dispatch_timeout")
            } else result.get()
        } catch (_: InterruptedException) {
            abandoned.set(true)
            Thread.currentThread().interrupt()
            failure("action_interrupted")
        }
    }
}
