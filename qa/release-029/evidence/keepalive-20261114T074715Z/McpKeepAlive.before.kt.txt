package com.hcbiu.elcton

import android.Manifest
import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.content.pm.PackageManager
import android.content.pm.ServiceInfo
import android.os.Build
import android.os.IBinder
import android.util.Log
import android.content.SharedPreferences
import androidx.compose.runtime.getValue
import androidx.compose.runtime.setValue
import androidx.compose.runtime.mutableStateOf

/** Explicit user-owned diagnostic session. No alarms, boot receivers, SDK actions, or wakelocks. */
object McpKeepAlive {
    const val CHANNEL = "mcp_diagnostic_session"
    const val NOTIFICATION_ID = 8766
    const val STOP = "com.hcbiu.elcton.MCP_STOP"
    private const val PREFS = "mcp_session"
    private const val ENABLED = "keep_running"
    // Activity actions and Service callbacks publish on Android's main thread.
    var active: Boolean by mutableStateOf(false)
        internal set
    var failure: String by mutableStateOf("")
        internal set

    internal fun preferences(context: Context): SharedPreferences = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
    fun enabled(context: Context): Boolean = preferences(context).getBoolean(ENABLED, false)
    private fun choice(context: Context, value: Boolean): Boolean = preferences(context).edit().putBoolean(ENABLED, value).commit()
    fun canNotify(context: Context): Boolean {
        if (Build.VERSION.SDK_INT >= 33 && context.checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED) return false
        val manager = context.getSystemService(NotificationManager::class.java)
        val channel = manager.getNotificationChannel(CHANNEL)
        if (!manager.areNotificationsEnabled() || channel?.importance == NotificationManager.IMPORTANCE_NONE) return false
        if (Build.VERSION.SDK_INT >= 28 && channel?.group != null &&
            manager.getNotificationChannelGroup(channel.group)?.isBlocked == true) return false
        return true
    }
    /** Call only from a visible Activity's explicit user interaction/resume of a previous choice. */
    fun enable(context: Context): Boolean {
        if (!canNotify(context)) { failure = "需要允许通知后才能保持运行"; return false }
        if (!choice(context, true)) { failure = "未能保存开关；没有开启保持运行"; return false }
        return try {
            failure = ""
            context.startForegroundService(Intent(context, McpKeepAliveService::class.java))
            true
        } catch (error: Exception) {
            choice(context, false)
            (context.applicationContext as? ElctonApplication)?.diagnostics?.stopListener()
            failure = "保持运行启动失败：" + error.javaClass.simpleName
            Log.w("ElctonMcp", failure)
            false
        }
    }
    fun disable(context: Context, reason: String = "") {
        if (!choice(context, false)) {
            failure = listOf(reason, "未能保存关闭状态；当前服务已停止").filter { it.isNotEmpty() }.joinToString("；")
        } else failure = reason
        // Close immediately, even if the Service has not received its pending start yet.
        (context.applicationContext as? ElctonApplication)?.diagnostics?.stopListener()
        context.stopService(Intent(context, McpKeepAliveService::class.java))
        active = false
        context.getSystemService(NotificationManager::class.java).cancel(NOTIFICATION_ID)
    }
    fun resumeChoice(context: Context) {
        if (!enabled(context)) return
        if (!canNotify(context)) {
            disable(context, "通知不可用；保持运行已关闭")
            return
        }
        if (!active) enable(context)
    }
}

class McpKeepAliveService : Service() {
    private val runtime get() = (application as ElctonApplication).diagnostics
    private var notificationReceiverRegistered = false
    private val notificationBlockReceiver = object : BroadcastReceiver() {
        override fun onReceive(context: Context?, intent: Intent?) {
            // The OS event is only a prompt to re-read our own channel/global state.
            // Never trust extras, restart the service, or turn a broadcast into opt-in.
            if (!McpKeepAlive.canNotify(this@McpKeepAliveService)) {
                McpKeepAlive.disable(this@McpKeepAliveService, "通知不可用；保持运行已关闭")
                stopSelf()
            }
        }
    }
    private fun registerNotificationBlockReceiver() {
        if (notificationReceiverRegistered) return
        val filter = IntentFilter().apply {
            addAction(NotificationManager.ACTION_APP_BLOCK_STATE_CHANGED)
            addAction(NotificationManager.ACTION_NOTIFICATION_CHANNEL_BLOCK_STATE_CHANGED)
            addAction(NotificationManager.ACTION_NOTIFICATION_CHANNEL_GROUP_BLOCK_STATE_CHANGED)
        }
        if (Build.VERSION.SDK_INT >= 33) registerReceiver(notificationBlockReceiver, filter, Context.RECEIVER_NOT_EXPORTED)
        else registerReceiver(notificationBlockReceiver, filter)
        notificationReceiverRegistered = true
    }
    override fun onBind(intent: Intent?): IBinder? = null
    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        if (intent?.action == McpKeepAlive.STOP) {
            McpKeepAlive.disable(this); stopSelf(); return START_NOT_STICKY
        }
        // Includes system sticky recreation with a null Intent; false never becomes opt-in.
        if (!McpKeepAlive.enabled(this) || !McpKeepAlive.canNotify(this)) {
            McpKeepAlive.disable(this); stopSelf(); return START_NOT_STICKY
        }
        try {
            // Dynamic only: observe while this service lives, never wake a stopped app.
            registerNotificationBlockReceiver()
            val manager = getSystemService(NotificationManager::class.java)
            manager.createNotificationChannel(NotificationChannel(McpKeepAlive.CHANNEL, "MCP 诊断会话", NotificationManager.IMPORTANCE_LOW))
            if (!McpKeepAlive.canNotify(this)) {
                McpKeepAlive.disable(this, "通知不可用；保持运行已关闭")
                stopSelf(); return START_NOT_STICKY
            }
            val open = PendingIntent.getActivity(this, 0, Intent(this, MainActivity::class.java), PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE)
            val stop = PendingIntent.getService(this, 1, Intent(this, McpKeepAliveService::class.java).setAction(McpKeepAlive.STOP), PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE)
            val builder = Notification.Builder(this, McpKeepAlive.CHANNEL)
                .setSmallIcon(android.R.drawable.stat_notify_sync_noanim)
                .setContentTitle("MCP 保持运行")
                .setContentText("仅同机只读诊断 · 127.0.0.1:8766")
                .setContentIntent(open).setOngoing(true).setOnlyAlertOnce(true)
                .addAction(Notification.Action.Builder(null, "停止", stop).build())
            if (Build.VERSION.SDK_INT >= 31) builder.setForegroundServiceBehavior(Notification.FOREGROUND_SERVICE_IMMEDIATE)
            val notification = builder.build()
            // Promote before binding or touching any diagnostic file.
            if (Build.VERSION.SDK_INT >= 34) startForeground(McpKeepAlive.NOTIFICATION_ID, notification, ServiceInfo.FOREGROUND_SERVICE_TYPE_SPECIAL_USE)
            else startForeground(McpKeepAlive.NOTIFICATION_ID, notification)
            if (!runtime.startListener()) {
                McpKeepAlive.disable(this, "MCP 端口启动失败；保持运行已关闭")
                stopSelf(); return START_NOT_STICKY
            }
            McpKeepAlive.active = true
            return START_STICKY
        } catch (error: Exception) {
            McpKeepAlive.disable(this, "保持运行失败：" + error.javaClass.simpleName)
            Log.w("ElctonMcp", McpKeepAlive.failure)
            stopSelf(); return START_NOT_STICKY
        }
    }
    override fun onDestroy() {
        if (notificationReceiverRegistered) {
            unregisterReceiver(notificationBlockReceiver)
            notificationReceiverRegistered = false
        }
        // System destruction cleans resources; it is not silently reinterpreted as user opt-out.
        runtime.stopListener()
        McpKeepAlive.active = false
        stopForeground(STOP_FOREGROUND_REMOVE)
        super.onDestroy()
    }
}
