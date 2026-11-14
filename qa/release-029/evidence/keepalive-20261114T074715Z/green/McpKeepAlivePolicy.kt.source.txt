package com.hcbiu.elcton

/** Pure choice/start policy; each start must pass the latest saved choice, never a queued snapshot. */
object McpKeepAlivePolicy {
    fun enabled(savedChoice: Boolean?): Boolean = savedChoice ?: true

    fun canStart(
        savedChoice: Boolean?,
        notificationsAvailable: Boolean,
        stopRequested: Boolean = false
    ): Boolean = enabled(savedChoice) && notificationsAvailable && !stopRequested
}
