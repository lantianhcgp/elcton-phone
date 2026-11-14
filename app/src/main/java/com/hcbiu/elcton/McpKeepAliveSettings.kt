package com.hcbiu.elcton

import android.Manifest
import android.content.Intent
import android.content.SharedPreferences
import android.os.Handler
import android.os.Looper
import android.os.Build
import android.provider.Settings
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalLifecycleOwner
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.semantics.testTagsAsResourceId
import androidx.compose.ui.unit.dp
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.LifecycleEventObserver

/** No token in screenshots, clipboard or shared storage. Settings own the explicit session. */
@OptIn(androidx.compose.ui.ExperimentalComposeUiApi::class)
@Composable
fun McpKeepAliveSettings() {
    val context = LocalContext.current
    val owner = LocalLifecycleOwner.current
    var enabledChoice by remember { mutableStateOf(McpKeepAlive.enabled(context)) }
    var pendingPermission by remember { mutableStateOf(false) }
    var uiMessage by remember { mutableStateOf("") }
    // Read observable Service state directly: a queued start is not an active session.
    val checked = enabledChoice && McpKeepAlive.active
    val message = McpKeepAlive.failure.ifEmpty { uiMessage }
    fun enableFromVisibleUi() {
        if (!owner.lifecycle.currentState.isAtLeast(Lifecycle.State.RESUMED)) {
            uiMessage = "回到设置页后再开启保持运行"
            return
        }
        uiMessage = ""
        McpKeepAlive.enable(context)
    }
    val permission = rememberLauncherForActivityResult(ActivityResultContracts.RequestPermission()) { granted ->
        pendingPermission = false
        if (granted) enableFromVisibleUi()
        else { uiMessage = "通知未获允许，保持运行仍为关闭" }
    }
    DisposableEffect(owner, context) {
        val prefs = McpKeepAlive.preferences(context)
        val main = Handler(Looper.getMainLooper())
        var disposed = false
        val listener = SharedPreferences.OnSharedPreferenceChangeListener { _, _ ->
            val refresh = Runnable { if (!disposed) enabledChoice = McpKeepAlive.enabled(context) }
            if (Looper.myLooper() == Looper.getMainLooper()) refresh.run() else main.post(refresh)
        }
        prefs.registerOnSharedPreferenceChangeListener(listener)
        enabledChoice = McpKeepAlive.enabled(context)
        val observer = LifecycleEventObserver { _, event ->
            if (event == Lifecycle.Event.ON_RESUME) {
                McpKeepAlive.resumeChoice(context)
                enabledChoice = McpKeepAlive.enabled(context)
            }
        }
        owner.lifecycle.addObserver(observer)
        onDispose {
            disposed = true
            prefs.unregisterOnSharedPreferenceChangeListener(listener)
            owner.lifecycle.removeObserver(observer)
        }
    }
    ExpressivePanel {
        SectionHeading("MCP 诊断")
        Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(12.dp)) {
            Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                Text("MCP 保持运行", style = MaterialTheme.typography.titleMedium)
                Text("默认关闭；开启后显示常驻通知", style = MaterialTheme.typography.bodySmall, color = M3x.OnSurfaceVariant)
            }
            Switch(checked = checked, enabled = !pendingPermission,
                modifier = Modifier.semantics { testTagsAsResourceId = true }.testTag("mcp-keepalive-switch"),
                onCheckedChange = { value ->
                    if (!value) {
                        uiMessage = ""
                        McpKeepAlive.disable(context)
                    } else if (Build.VERSION.SDK_INT >= 33 && !McpKeepAlive.canNotify(context) &&
                        context.checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) != android.content.pm.PackageManager.PERMISSION_GRANTED) {
                        pendingPermission = true
                        permission.launch(Manifest.permission.POST_NOTIFICATIONS)
                    } else enableFromVisibleUi()
                })
        }
        if (enabledChoice && !McpKeepAlive.active && message.isEmpty()) {
            Text("正在启动保持运行…", style = MaterialTheme.typography.bodySmall, modifier = Modifier.testTag("mcp-keepalive-starting"))
        }
        Text("仅同机 127.0.0.1:8766，四个只读工具。开启便于切换到 Termux；关闭会立即停止本次端口。系统仍可能限制休眠与后台运行。",
            style = MaterialTheme.typography.bodySmall, color = M3x.OnSurfaceVariant)
        Text("诊断 token 保存在应用私有目录；Termux 经 Shizuku/run-as 读取，不展示、不复制到公共目录。",
            style = MaterialTheme.typography.labelSmall, color = M3x.OnSurfaceVariant)
        if (message.isNotEmpty()) {
            Text(message, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.error, modifier = Modifier.testTag("mcp-keepalive-status"))
            if (!McpKeepAlive.canNotify(context)) TextButton(onClick = {
                context.startActivity(Intent(Settings.ACTION_APP_NOTIFICATION_SETTINGS).putExtra(Settings.EXTRA_APP_PACKAGE, context.packageName))
            }) { Text("通知设置") }
        }
    }
}
