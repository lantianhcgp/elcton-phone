package com.hcbiu.elcton

import org.junit.Assert.*
import org.junit.Test

/** Direct public error seam edge cases; all messages are explicitly synthetic. */
class ErrorRecordBoundaryTest {
    @Test fun preservesNullMessageAndCodeOnNestedCause() {
        val error = Exception(null as String?, IllegalStateException("SYNTHETIC nested code"))
        val record = WearErrorRecord.capture(error, "checkPermission", 123L) { if (it === error.cause) 1004 else null }
        val json = record.toJson()
        assertTrue(json.isNull("message"))
        assertEquals(1004, json.getInt("errorCode"))
        assertEquals(2, json.getJSONArray("causes").length())
        assertTrue(record.full.contains("<null message>"))
        assertTrue(record.full.contains("[errorCode=1004]"))
        assertTrue(record.full.contains("SYNTHETIC nested code"))
    }

    @Test fun preservesLongMultilineUnicodeMessageWithoutEllipsis() {
        val message = "SYNTHETIC 原始消息\n\"引号\"\\路径🙂" + "甲".repeat(16000) + "\nEND-OF-FULL-MESSAGE"
        val record = WearErrorRecord.capture(IllegalStateException(message), "requestPermission", 1L)
        assertEquals(message, record.toJson().getString("message"))
        assertTrue(record.full.endsWith("END-OF-FULL-MESSAGE"))
        assertTrue(record.full.contains(message))
    }

    @Test fun cyclicCauseChainTerminatesWithExplicitMarker() {
        val a = Exception("SYNTHETIC A")
        val b = Exception("SYNTHETIC B")
        a.initCause(b); b.initCause(a)
        val record = WearErrorRecord.capture(a, "getCommonDevice", 0L)
        assertEquals(2, record.toJson().getJSONArray("causes").length())
        assertTrue(record.toJson().getBoolean("causeCycle"))
        assertTrue(record.full.endsWith("[cause cycle detected]"))
    }

    @Test fun errorCodeAccessorFailureCannotHideOriginalMessage() {
        val record = WearErrorRecord.capture(Exception("SYNTHETIC original"), "p2p.send", 0L) { throw UnsupportedOperationException("SYNTHETIC code unavailable") }
        assertTrue(record.toJson().isNull("errorCode"))
        assertEquals("SYNTHETIC original", record.toJson().getString("message"))
        assertTrue(record.full.contains("SYNTHETIC original"))
    }

    @Test fun causeGetterFailurePreservesFullOriginalMessageAndReportsReadFailure() {
        val message = "SYNTHETIC original\n" + "甲🙂".repeat(16000) + "\nEND-OF-FULL-MESSAGE"
        var reads = 0
        val original = object : Exception(message) {
            override val cause: Throwable?
                get() { reads++; throw IllegalStateException("SYNTHETIC cause unavailable") }
        }
        val record = WearErrorRecord.capture(original, "checkPermission", 0L)
        val json = record.toJson()
        assertEquals(message, json.getString("message"))
        assertEquals(1, json.getJSONArray("causes").length())
        assertFalse(json.getBoolean("causeCycle"))
        assertTrue(record.full.contains(message))
        assertEquals(1, reads)
        assertReadFailure(record, 0, "cause", IllegalStateException::class.java.name, 0)
    }

    @Test fun nestedCauseGetterFailureRetainsTheWholeCapturedPrefix() {
        val nestedMessage = "SYNTHETIC nested\n" + "乙".repeat(16000) + "\nNESTED-END"
        val nested = object : Exception(nestedMessage) {
            override val cause: Throwable?
                get() = throw UnsupportedOperationException("SYNTHETIC nested cause unavailable")
        }
        val message = "SYNTHETIC root\n" + "丙".repeat(16000) + "\nROOT-END"
        val record = WearErrorRecord.capture(Exception(message, nested), "p2p.send", 0L)
        val json = record.toJson()
        assertEquals(message, json.getString("message"))
        assertEquals(nestedMessage, json.getJSONArray("causes").getJSONObject(1).getString("message"))
        assertEquals(2, json.getJSONArray("causes").length())
        assertFalse(json.getBoolean("causeCycle"))
        assertTrue(record.full.contains(message))
        assertTrue(record.full.contains(nestedMessage))
        assertReadFailure(record, 0, "cause", UnsupportedOperationException::class.java.name, 1)
    }

    @Test fun messageGetterFailureStillPreservesCodeAndNestedCause() {
        var reads = 0
        val original = object : Exception("SYNTHETIC inaccessible", Exception("SYNTHETIC nested")) {
            override val message: String?
                get() { reads++; throw IllegalArgumentException("SYNTHETIC message unavailable") }
        }
        val record = WearErrorRecord.capture(original, "checkPermission", 0L) { if (it === original) 8 else null }
        val json = record.toJson()
        assertTrue(json.isNull("message"))
        assertEquals(8, json.getInt("errorCode"))
        assertEquals(2, json.getJSONArray("causes").length())
        assertEquals("SYNTHETIC nested", json.getJSONArray("causes").getJSONObject(1).getString("message"))
        assertFalse(json.getBoolean("causeCycle"))
        assertEquals(1, reads)
        assertReadFailure(record, 0, "message", IllegalArgumentException::class.java.name, 0)
    }

    @Test fun codeSupplierFailureIsReportedWithoutStoppingTheCauseChain() {
        val nested = Exception("SYNTHETIC nested code")
        val original = Exception("SYNTHETIC original", nested)
        var calls = 0
        val record = WearErrorRecord.capture(original, "p2p.send", 0L) {
            calls++
            if (it === original) throw AssertionError("SYNTHETIC code unavailable")
            1004
        }
        val json = record.toJson()
        assertEquals("SYNTHETIC original", json.getString("message"))
        assertEquals(1004, json.getInt("errorCode"))
        assertTrue(json.getJSONArray("causes").getJSONObject(0).isNull("errorCode"))
        assertEquals(2, json.getJSONArray("causes").length())
        assertEquals(2, calls)
        assertReadFailure(record, 0, "errorCode", AssertionError::class.java.name, 0)
    }

    @Test fun diagnosticFailureMetadataNeverReadsTheFailingThrowablePayload() {
        var payloadReads = 0
        val diagnosticFailure = object : AssertionError() {
            override val message: String?
                get() { payloadReads++; throw AssertionError("SYNTHETIC forbidden message read") }
            override val cause: Throwable?
                get() { payloadReads++; throw AssertionError("SYNTHETIC forbidden cause read") }
            override fun toString(): String {
                payloadReads++; throw AssertionError("SYNTHETIC forbidden coercion")
            }
        }
        val original = object : Exception() {
            override val message: String? get() = throw diagnosticFailure
            override val cause: Throwable? get() = throw diagnosticFailure
        }
        val result = runCatching { WearErrorRecord.capture(original, "checkPermission", 0L) { throw diagnosticFailure } }
        assertTrue("diagnostic throwable must not escape capture", result.isSuccess)
        val record = result.getOrThrow()
        assertEquals(3, record.toJson().getJSONArray("diagnosticFailures").length())
        assertFalse(record.toJson().getBoolean("causeCycle"))
        assertReadFailure(record, 0, "message", diagnosticFailure.javaClass.name, 0)
        assertReadFailure(record, 1, "errorCode", diagnosticFailure.javaClass.name, 0)
        assertReadFailure(record, 2, "cause", diagnosticFailure.javaClass.name, 0)
        assertEquals(0, payloadReads)
    }

    @Test fun causeGetterFailureCannotReplaceTheOriginalBusinessFailureExit() {
        val original = object : Exception("SYNTHETIC original business failure") {
            override val cause: Throwable?
                get() = throw IllegalStateException("SYNTHETIC diagnostic failure")
        }
        var observed: WearErrorRecord? = null
        // Public record seam, not a Wear Engine substitute: observation precedes unchanged rethrow.
        val escaped = try {
            observed = WearErrorRecord.capture(original, "checkPermission", 0L)
            throw original
        } catch (failure: Throwable) {
            failure
        }
        assertTrue("diagnostics must not replace the original business throwable", escaped === original)
        assertNotNull(observed)
        assertEquals("SYNTHETIC original business failure", observed!!.toJson().getString("message"))
    }

    @Test fun identityCycleDetectionNeverInvokesThrowableEqualityOrHashCode() {
        val original = object : Exception("SYNTHETIC self cycle") {
            override val cause: Throwable get() = this
            override fun equals(other: Any?): Boolean = throw AssertionError("SYNTHETIC forbidden equality")
            override fun hashCode(): Int = throw AssertionError("SYNTHETIC forbidden hash")
        }
        val record = WearErrorRecord.capture(original, "getCommonDevice", 0L)
        assertEquals(1, record.toJson().getJSONArray("causes").length())
        assertTrue(record.toJson().getBoolean("causeCycle"))
        assertEquals(0, record.toJson().getJSONArray("diagnosticFailures").length())
        assertTrue(record.full.endsWith("[cause cycle detected]"))
    }

    @Test fun ordinaryDeepCauseChainIsNotTruncatedOrMarkedAsAReadFailure() {
        var original: Throwable? = null
        val messages = (0 until 300).map { "SYNTHETIC cause $it\n" + "丁".repeat(80) + " END-$it" }
        messages.asReversed().forEach { original = Exception(it, original) }
        val record = WearErrorRecord.capture(original!!, "p2p.send", 0L)
        val json = record.toJson()
        val causes = json.getJSONArray("causes")
        assertEquals(messages.size, causes.length())
        messages.forEachIndexed { index, message ->
            assertEquals(message, causes.getJSONObject(index).getString("message"))
            assertTrue(record.full.contains(message))
        }
        assertFalse(json.getBoolean("causeCycle"))
        assertEquals(0, json.getJSONArray("diagnosticFailures").length())
    }

    @Test fun providedPrimaryMessageIsNeverReadAgainWhileNestedMessagesAreCapturedOnce() {
        var rootReads = 0
        var nestedReads = 0
        val nestedMessage = "SYNTHETIC nested\n" + "尾".repeat(16000)
        val nested = object : Exception() {
            override val message: String?
                get() { nestedReads++; return nestedMessage }
        }
        val original = object : Exception(null as String?, nested) {
            override val message: String?
                get() { rootReads++; return "SYNTHETIC business read $rootReads\n" + "首".repeat(16000) }
        }
        val primaryMessage = original.message // The one existing business read.
        val record = captureProvided(original, primaryMessage)
        val json = record.toJson()
        assertEquals(1, rootReads)
        assertEquals(1, nestedReads)
        assertEquals(primaryMessage, json.getString("message"))
        assertEquals(nestedMessage, json.getJSONArray("causes").getJSONObject(1).getString("message"))
        assertTrue(record.full.contains(primaryMessage!!))
        assertTrue(record.full.contains(nestedMessage))
        assertEquals(0, json.getJSONArray("diagnosticFailures").length())
    }

    @Test fun providedNullMessageDoesNotFallBackToTheThrowableGetter() {
        var reads = 0
        val original = object : Exception() {
            override val message: String?
                get() { reads++; throw AssertionError("SYNTHETIC forbidden root reread") }
        }
        val record = WearErrorRecord.captureWithMessage(original, "checkPermission", 0L, null)
        assertEquals(0, reads)
        assertTrue(record.toJson().isNull("message"))
        assertEquals(0, record.toJson().getJSONArray("diagnosticFailures").length())
        assertTrue(record.full.contains("<null message>"))
    }

    @Test fun providedMessageStillIsolatesCodeAndCauseFailures() {
        val original = object : Exception() {
            override val message: String? get() = throw AssertionError("SYNTHETIC forbidden root reread")
            override val cause: Throwable? get() = throw IllegalStateException("SYNTHETIC cause unavailable")
        }
        val record = captureProvided(original, "SYNTHETIC supplied original") {
            throw UnsupportedOperationException("SYNTHETIC code unavailable")
        }
        assertEquals("SYNTHETIC supplied original", record.toJson().getString("message"))
        assertFalse(record.toJson().getBoolean("causeCycle"))
        assertEquals(2, record.toJson().getJSONArray("diagnosticFailures").length())
        assertReadFailure(record, 0, "errorCode", UnsupportedOperationException::class.java.name, 0)
        assertReadFailure(record, 1, "cause", IllegalStateException::class.java.name, 0)
    }

    private fun captureProvided(error: Throwable, message: String?,
                                errorCode: (Throwable) -> Int? = { null }): WearErrorRecord =
        WearErrorRecord.captureWithMessage(error, "checkPermission", 0L, message, errorCode)

    private fun assertReadFailure(record: WearErrorRecord, failureIndex: Int, field: String,
                                  type: String, causeIndex: Int) {
        val failure = record.toJson().getJSONArray("diagnosticFailures").getJSONObject(failureIndex)
        assertEquals(field, failure.getString("field"))
        assertEquals(type, failure.getString("type"))
        assertEquals(causeIndex, failure.getInt("causeIndex"))
        assertTrue(record.full.contains("[diagnostic read failed: $field@$causeIndex ($type)]"))
    }
}
