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
import androidx.core.content.ContextCompat
import androidx.compose.runtime.getValue
import androidx.compose.runtime.setValue
import androidx.compose.runtime.mutableStateOf

/** Default-on, user-owned same-device MCP session. No alarms, boot receivers, or wakelocks. */
object McpKeepAlive {
    const val CHANNEL = "mcp_diagnostic_session"
    const val NOTIFICATION_ID = 8766
    const val STOP = "com.hcbiu.elcton.MCP_STOP"
    private const val PREFS = "mcp_session"
    private const val ENABLED = "keep_running"
    private const val NOTIFICATIONS_UNAVAILABLE = "通知不可用；保持运行未启动，开启偏好已保留"
    // Serialize a delivered start with STOP, including callers outside Android's main thread.
    internal val lifecycleLock = Any()
    @Volatile private var stopRequested = false
    // Activity actions and Service callbacks publish on Android's main thread.
    var active: Boolean by mutableStateOf(false)
        internal set
    var failure: String by mutableStateOf("")
        internal set

    internal fun preferences(context: Context): SharedPreferences = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
    private fun savedChoice(context: Context): Boolean? = preferences(context).let {
        if (it.contains(ENABLED)) it.getBoolean(ENABLED, false) else null
    }
    fun enabled(context: Context): Boolean = McpKeepAlivePolicy.enabled(savedChoice(context))
    private fun choice(context: Context, value: Boolean): Boolean = preferences(context).edit().putBoolean(ENABLED, value).commit()
    internal fun canStart(context: Context): Boolean = McpKeepAlivePolicy.canStart(savedChoice(context), canNotify(context), stopRequested)
    fun canNotify(context: Context): Boolean {
        if (Build.VERSION.SDK_INT >= 33 && context.checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED) return false
        val manager = context.getSystemService(NotificationManager::class.java)
        val channel = manager.getNotificationChannel(CHANNEL)
        if (!manager.areNotificationsEnabled() || channel?.importance == NotificationManager.IMPORTANCE_NONE) return false
        if (Build.VERSION.SDK_INT >= 28 && channel?.group != null &&
            manager.getNotificationChannelGroup(channel.group)?.isBlocked == true) return false
        return true
    }
    /** Call only from a visible Activity's explicit user interaction/resume of its enabled choice. */
    fun enable(context: Context): Boolean = synchronized(lifecycleLock) {
        if (!choice(context, true)) {
            suspendSession(context, "未能保存开关；没有开启保持运行")
            return@synchronized false
        }
        stopRequested = false
        if (!canNotify(context)) {
            suspendSession(context, NOTIFICATIONS_UNAVAILABLE)
            return@synchronized false
        }
        try {
            failure = ""
            context.startForegroundService(Intent(context, McpKeepAliveService::class.java))
            true
        } catch (error: Exception) {
            suspendSession(context, "保持运行启动失败：" + error.javaClass.simpleName)
            Log.w("ElctonMcp", failure)
            false
        }
    }
    fun disable(context: Context, reason: String = ""): Unit = synchronized(lifecycleLock) {
        // Durable opt-out precedes closing sockets; the fence also covers a failed disk commit.
        stopRequested = true
        val choiceSaved = try { choice(context, false) } catch (error: Exception) {
            Log.w("ElctonMcp", "Cannot persist MCP stop: " + error.javaClass.simpleName)
            false
        }
        if (!choiceSaved) {
            failure = listOf(reason, "未能保存关闭状态；当前服务已停止").filter { it.isNotEmpty() }.joinToString("；")
        } else failure = reason
        releaseSession(context, cancelSync = true)
        Log.i("ElctonMcp", "MCP stop handled; active=false; choiceSaved=" + choiceSaved)
    }
    /** Notification loss is not user opt-out: close the real port but retain the saved choice. */
    internal fun suspendSession(context: Context, reason: String): Unit = synchronized(lifecycleLock) {
        failure = reason
        releaseSession(context, cancelSync = false)
    }
    private fun releaseSession(context: Context, cancelSync: Boolean) {
        val app = context.applicationContext as? ElctonApplication
        fun cleanup(label: String, action: () -> Unit) {
            try { action() } catch (error: Exception) {
                failure = listOf(failure, label + "：" + error.javaClass.simpleName).filter { it.isNotEmpty() }.joinToString("；")
                Log.w("ElctonMcp", label + "：" + error.javaClass.simpleName)
            }
        }
        // Socket closure is synchronous and must finish before cancelling the shared engine.
        cleanup("MCP 监听停止失败") { app?.diagnostics?.stopListener() }
        if (cancelSync) cleanup("同步取消失败") { app?.cancelPhoneIfInitialized() }
        cleanup("保持运行服务停止失败") { context.stopService(Intent(context, McpKeepAliveService::class.java)) }
        active = false
        cleanup("通知移除失败") { context.getSystemService(NotificationManager::class.java).cancel(NOTIFICATION_ID) }
    }
    fun resumeChoice(context: Context): Unit = synchronized(lifecycleLock) {
        if (!enabled(context) || stopRequested) return@synchronized
        if (!canNotify(context)) {
            suspendSession(context, NOTIFICATIONS_UNAVAILABLE)
            return@synchronized
        }
        if (!active) enable(context)
    }
}

class McpKeepAliveService : Service() {
    private val runtime get() = (application as ElctonApplication).diagnostics
    private var stopReceiverRegistered = false
    private val stopReceiver = object : BroadcastReceiver() {
        override fun onReceive(context: Context?, intent: Intent?) {
            if (intent?.action != McpKeepAlive.STOP) return
            // Registered only while this service lives: STOP cannot create a new service.
            Log.i("ElctonMcp", "MCP notification STOP delivered")
            McpKeepAlive.disable(this@McpKeepAliveService)
            stopSelf()
        }
    }
    private var notificationReceiverRegistered = false
    private val notificationBlockReceiver = object : BroadcastReceiver() {
        override fun onReceive(context: Context?, intent: Intent?) {
            // The OS event is only a prompt to re-read our own channel/global state.
            // Never trust extras, restart the service, or turn a broadcast into opt-in.
            if (!McpKeepAlive.canNotify(this@McpKeepAliveService)) {
                McpKeepAlive.suspendSession(this@McpKeepAliveService, "通知不可用；保持运行已停止，开启偏好已保留")
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
    private fun registerStopReceiver() {
        if (stopReceiverRegistered) return
        // AndroidX supplies the signature-permission fallback on API 26-32 as well.
        ContextCompat.registerReceiver(this, stopReceiver, IntentFilter(McpKeepAlive.STOP), ContextCompat.RECEIVER_NOT_EXPORTED)
        stopReceiverRegistered = true
    }
    override fun onBind(intent: Intent?): IBinder? = null
    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int = synchronized(McpKeepAlive.lifecycleLock) {
        // Handle a pre-upgrade service PendingIntent too; new notifications use broadcast.
        if (intent?.action == McpKeepAlive.STOP) {
            McpKeepAlive.disable(this); stopSelf(); return@synchronized START_NOT_STICKY
        }
        // Includes sticky recreation and queued starts; always re-read the latest saved choice.
        if (!McpKeepAlive.canStart(this)) {
            val reason = if (McpKeepAlive.enabled(this) && !McpKeepAlive.canNotify(this))
                "通知不可用；保持运行未启动，开启偏好已保留" else McpKeepAlive.failure
            McpKeepAlive.suspendSession(this, reason)
            stopSelf(); return@synchronized START_NOT_STICKY
        }
        try {
            // Dynamic only: observe while this service lives, never wake a stopped app.
            registerStopReceiver()
            registerNotificationBlockReceiver()
            val manager = getSystemService(NotificationManager::class.java)
            manager.createNotificationChannel(NotificationChannel(McpKeepAlive.CHANNEL, "同机 MCP 会话", NotificationManager.IMPORTANCE_LOW))
            if (!McpKeepAlive.canStart(this)) {
                McpKeepAlive.suspendSession(this, "通知不可用或保持运行已停止")
                stopSelf(); return@synchronized START_NOT_STICKY
            }
            val open = PendingIntent.getActivity(this, 0, Intent(this, MainActivity::class.java), PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE)
            val stop = PendingIntent.getBroadcast(this, 1, Intent(McpKeepAlive.STOP).setPackage(packageName), PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE)
            val builder = Notification.Builder(this, McpKeepAlive.CHANNEL)
                .setSmallIcon(android.R.drawable.stat_notify_sync_noanim)
                .setContentTitle("MCP 保持运行")
                .setContentText("同机 MCP · 127.0.0.1:8766 · 停止会关闭连接与同步")
                .setContentIntent(open).setOngoing(true).setOnlyAlertOnce(true)
                .addAction(Notification.Action.Builder(null, "停止", stop).build())
            if (Build.VERSION.SDK_INT >= 31) builder.setForegroundServiceBehavior(Notification.FOREGROUND_SERVICE_IMMEDIATE)
            val notification = builder.build()
            // Promote before binding or touching any diagnostic file.
            if (Build.VERSION.SDK_INT >= 34) startForeground(McpKeepAlive.NOTIFICATION_ID, notification, ServiceInfo.FOREGROUND_SERVICE_TYPE_SPECIAL_USE)
            else startForeground(McpKeepAlive.NOTIFICATION_ID, notification)
            if (!runtime.startListener()) {
                McpKeepAlive.suspendSession(this, "MCP 端口启动失败；保持运行未启动，开启偏好已保留")
                stopSelf(); return@synchronized START_NOT_STICKY
            }
            if (!McpKeepAlive.canStart(this)) {
                McpKeepAlive.suspendSession(this, "通知不可用或保持运行已停止")
                stopSelf(); return@synchronized START_NOT_STICKY
            }
            McpKeepAlive.failure = ""
            McpKeepAlive.active = true
            START_STICKY
        } catch (error: Exception) {
            McpKeepAlive.suspendSession(this, "保持运行失败；开启偏好已保留：" + error.javaClass.simpleName)
            Log.w("ElctonMcp", McpKeepAlive.failure)
            stopSelf(); return@synchronized START_NOT_STICKY
        }
    }
    override fun onDestroy() {
        if (stopReceiverRegistered) {
            unregisterReceiver(stopReceiver)
            stopReceiverRegistered = false
        }
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
