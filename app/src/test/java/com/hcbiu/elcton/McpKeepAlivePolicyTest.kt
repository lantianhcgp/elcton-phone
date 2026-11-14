package com.hcbiu.elcton

import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/** Public, Android-free choice/start policy. Service delivery and real sockets need emulator evidence. */
class McpKeepAlivePolicyTest {
    private fun root(): java.io.File = generateSequence(java.io.File("").absoluteFile) { it.parentFile }
        .first { java.io.File(it, "app/src/main/AndroidManifest.xml").isFile }
    private fun source(name: String) = java.io.File(root(), "app/src/main/java/com/hcbiu/elcton/$name").readText()
    @Test fun missingPreferenceDefaultsToEnabled() {
        assertTrue("A new user has not explicitly opted out", McpKeepAlivePolicy.enabled(null))
    }

    @Test fun historicalExplicitFalseIsPreserved() {
        assertFalse("An upgrade must not overwrite an explicit opt-out", McpKeepAlivePolicy.enabled(false))
    }

    @Test fun historicalExplicitTrueIsPreserved() {
        assertTrue(McpKeepAlivePolicy.enabled(true))
    }

    @Test fun defaultChoiceCanStartWhenNotificationsAreAvailable() {
        assertTrue(McpKeepAlivePolicy.canStart(null, notificationsAvailable = true))
    }

    @Test fun notificationDenialBlocksStartWithoutChangingDefaultChoice() {
        assertFalse(McpKeepAlivePolicy.canStart(null, notificationsAvailable = false))
        assertTrue("Unavailable notifications are not user opt-out", McpKeepAlivePolicy.enabled(null))
    }

    @Test fun returningNotificationPermissionDoesNotOverrideExplicitFalse() {
        assertFalse(McpKeepAlivePolicy.canStart(false, notificationsAvailable = false))
        assertFalse(McpKeepAlivePolicy.canStart(false, notificationsAvailable = true))
    }

    @Test fun latestOptOutVetoesAPreviouslyAllowedQueuedStart() {
        assertTrue(McpKeepAlivePolicy.canStart(true, notificationsAvailable = true))
        // onStartCommand must use the current saved value, not the value when enable queued it.
        assertFalse(McpKeepAlivePolicy.canStart(false, notificationsAvailable = true))
    }

    @Test fun retainedIntentionIsNotShownAsAnOffSwitchDuringStartOrPermissionFailure() {
        val source=source("McpKeepAliveSettings.kt")
        assertTrue("switch must represent saved intent, not service liveness", source.contains("val checked = enabledChoice\n"))
        assertFalse(source.contains("val checked = enabledChoice && McpKeepAlive.active"))
        assertTrue("live status remains separate", source.contains("enabledChoice && !McpKeepAlive.active"))
    }

    @Test fun nonUserStartupFailuresKeepIntendedOnButCloseTheSession() {
        val source=source("McpKeepAlive.kt")
        val bindFailure=source.substringAfter("if (!runtime.startListener()) {").substringBefore("}\n")
        assertTrue("Bind failure closes resources without interpreting it as user opt-out",
            bindFailure.contains("McpKeepAlive.suspendSession(this,") && !bindFailure.contains("McpKeepAlive.disable("))
        assertTrue(bindFailure.contains("保持运行未启动，开启偏好已保留"))
        val serviceFailure=source.substringAfter("        } catch (error: Exception) {\n            McpKeepAlive.").substringBefore("    override fun onDestroy()")
        assertTrue("Unexpected startup exception also preserves the user's choice",serviceFailure.startsWith("suspendSession(this,"))
    }

    @Test fun stopFenceVetoesLateStartEvenIfSavingFalseFailed() {
        assertFalse(
            "Failing to persist STOP must not let this process restart its listener",
            McpKeepAlivePolicy.canStart(true, notificationsAvailable = true, stopRequested = true)
        )
    }
}
