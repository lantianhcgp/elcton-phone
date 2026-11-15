package com.hcbiu.elcton

import org.json.JSONArray
import org.json.JSONObject
import java.time.Instant
import java.util.Collections
import java.util.IdentityHashMap

/** Explicit SDK-only diagnostics. Local course validation still uses UserFacingError. */
class WearErrorRecord private constructor(
    val timestampMs: Long,
    val phase: String,
    private val causes: List<Cause>,
    private val causeCycle: Boolean,
    private val diagnosticFailures: List<ReadFailure>
) {
    private data class Cause(val type: String, val message: String?, val code: Int?)
    private data class ReadFailure(val causeIndex: Int, val field: String, val type: String)
    val full: String
        get() = buildString {
            append(Instant.ofEpochMilli(timestampMs)).append(" · ").append(phase)
            causes.forEachIndexed { index, cause ->
                append('\n').append(if (index == 0) "exception: " else "caused by: ")
                    .append(cause.type)
                cause.code?.let { append(" [errorCode=").append(it).append(']') }
                append(": ").append(cause.message ?: "<null message>")
            }
            if (causeCycle) append("\n[cause cycle detected]")
            diagnosticFailures.forEach { failure ->
                append("\n[diagnostic read failed: ").append(failure.field)
                    .append('@').append(failure.causeIndex).append(" (")
                    .append(failure.type).append(")]")
            }
        }

    fun toJson(): JSONObject = JSONObject()
        .put("timestampMs", timestampMs)
        .put("timestamp", Instant.ofEpochMilli(timestampMs).toString())
        .put("phase", phase)
        .put("type", causes.first().type)
        .put("message", causes.first().message ?: JSONObject.NULL)
        .put("errorCode", causes.firstNotNullOfOrNull { it.code } ?: JSONObject.NULL)
        .put("causes", JSONArray().apply {
            causes.forEach { cause -> put(JSONObject()
                .put("type", cause.type)
                .put("message", cause.message ?: JSONObject.NULL)
                .put("errorCode", cause.code ?: JSONObject.NULL)) }
        })
        .put("causeCycle", causeCycle)
        .put("diagnosticFailures", JSONArray().apply {
            diagnosticFailures.forEach { failure -> put(JSONObject()
                .put("causeIndex", failure.causeIndex)
                .put("field", failure.field)
                .put("type", failure.type)) }
        })
        .put("full", full)

    companion object {
        fun capture(error: Throwable, phase: String, timestampMs: Long,
                    errorCode: (Throwable) -> Int? = { null }): WearErrorRecord =
            captureSafely(error, phase, timestampMs, null, false, errorCode)

        /** Use the primary message already read by business code, including an explicit null. */
        fun captureWithMessage(error: Throwable, phase: String, timestampMs: Long,
                               primaryMessage: String?,
                               errorCode: (Throwable) -> Int? = { null }): WearErrorRecord =
            captureSafely(error, phase, timestampMs, primaryMessage, true, errorCode)

        private fun captureSafely(error: Throwable, phase: String, timestampMs: Long,
                                  primaryMessage: String?, primaryMessageProvided: Boolean,
                                  errorCode: (Throwable) -> Int?): WearErrorRecord {
            val seen = Collections.newSetFromMap(IdentityHashMap<Throwable, Boolean>())
            val causes = mutableListOf<Cause>()
            val failures = mutableListOf<ReadFailure>()
            var current: Throwable? = error
            while (current != null && seen.add(current)) {
                val item = current
                val index = causes.size
                val message = if (index == 0 && primaryMessageProvided) primaryMessage
                    else readSafely(index, "message", failures) { item.message }
                val code = readSafely(index, "errorCode", failures) { errorCode(item) }
                causes += Cause(item.javaClass.name, message, code)
                // A failed read ends the unavailable tail, not the business path or a false cycle.
                current = readSafely(index, "cause", failures) { item.cause }
            }
            return WearErrorRecord(timestampMs, phase, causes, current != null, failures)
        }

        private inline fun <T> readSafely(causeIndex: Int, field: String,
                                          failures: MutableList<ReadFailure>, read: () -> T?): T? =
            try {
                read()
            } catch (failure: Throwable) {
                // Do not read message/cause/toString on the diagnostic failure itself.
                failures += ReadFailure(causeIndex, field, failure.javaClass.name)
                null
            }
    }
}
