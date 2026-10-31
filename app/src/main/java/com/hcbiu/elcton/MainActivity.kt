package com.hcbiu.elcton

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp
import org.json.JSONObject

/** First installable vertical slice: real devices + real sync, with an editable structured snapshot. */
class MainActivity : ComponentActivity() {
    private lateinit var probe: WearProbe
    private var probeState by mutableStateOf(WearProbe.State())
    private var tab by mutableIntStateOf(0)
    private var input by mutableStateOf("{\"schema\":\"elcton.schedule\",\"version\":1,\"settings\":{\"semesterStart\":\"2026-09-01\"},\"courses\":[]}")
    private var inputError by mutableStateOf<String?>(null)
    private var confirmPublish by mutableStateOf(false)
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        input = getSharedPreferences("schedule", MODE_PRIVATE).getString("snapshot", input) ?: input
        probe = WearProbe(this) { probeState = it }
        setContent {
            MaterialTheme(colorScheme = darkColorScheme(primary = Color(0xFFA89FFF), background = Color(0xFF0B0E14), surface = Color(0xFF171B28))) {
                Scaffold(
                    bottomBar = { NavigationBar {
                        listOf("课表", "设备").forEachIndexed { index, label ->
                            NavigationBarItem(selected = tab == index, onClick = { tab = index }, icon = { Text(if (index == 0) "课" else "表") }, label = { Text(label) })
                        }
                    }}
                ) { padding ->
                    Column(Modifier.fillMaxSize().padding(padding).padding(horizontal = 20.dp).verticalScroll(rememberScrollState()), verticalArrangement = Arrangement.spacedBy(14.dp)) {
                        Spacer(Modifier.height(12.dp))
                        Text("hc课程表", style = MaterialTheme.typography.headlineMedium)
                        Text("0.1.0 · 通信探针", color = MaterialTheme.colorScheme.onSurfaceVariant)
                        Text("先验证可靠同步；此版不是完整编辑器，也不代表所有 Wear Engine 手表已验收。", style = MaterialTheme.typography.bodySmall)
                        if (tab == 0) SnapshotEditor() else DevicePanel()
                        Spacer(Modifier.height(24.dp))
                    }
                }
                if (confirmPublish) AlertDialog(
                    onDismissRequest = { confirmPublish = false },
                    title = { Text(if (probeState.dirty) "确认替换手表课表" else "确认发送课表") },
                    text = { Text("手表可能已有课表。探针版保留上一提交槽，但尚未实现完整导出回传。此次将用手机快照替换选中手表的活动课表；空快照会清空课程。") },
                    confirmButton = { TextButton(onClick = { confirmPublish = false; if (saveSnapshot()) probe.publishSnapshot(input, true) }) { Text("确认替换") } },
                    dismissButton = { TextButton(onClick = { confirmPublish = false }) { Text("取消") } }
                )
            }
        }
    }
    @Composable private fun SnapshotEditor() {
        Text("结构化课表", style = MaterialTheme.typography.titleLarge)
        Text("粘贴 elcton.schedule v1 JSON。课程字段含 id、星期、节次、起止时间、单/双周；旧系统可导出同格式。", style = MaterialTheme.typography.bodySmall)
        OutlinedTextField(value = input, onValueChange = { input = it; inputError = null }, modifier = Modifier.fillMaxWidth().heightIn(min = 220.dp, max = 380.dp), label = { Text("课表 JSON") })
        inputError?.let { Text(it, color = MaterialTheme.colorScheme.error) }
        Button(onClick = { saveSnapshot() }) { Text("校验并保存到手机") }
        val parsed = runCatching { JSONObject(input) }.getOrNull()
        val courses = parsed?.optJSONArray("courses")
        Text("${courses?.length() ?: 0} 条课程 · 学期 ${parsed?.optJSONObject("settings")?.optString("semesterStart").orEmpty()}")
        if (courses != null) {
            for (i in 0 until minOf(courses.length(), 12)) {
                val course = courses.optJSONObject(i) ?: continue
                Text("周${course.optInt("dayOfWeek")}  ${course.optString("startTime")}  ${course.optString("name")}", style = MaterialTheme.typography.bodyMedium)
            }
        }
        Text("未保存的编辑不自动发送。真人设备测试前请先在手表打开同步接收页。", style = MaterialTheme.typography.bodySmall)
    }
    @Composable private fun DevicePanel() {
        Text(probeState.status, style = MaterialTheme.typography.titleLarge)
        Text(probeState.detail, color = MaterialTheme.colorScheme.onSurfaceVariant)
        Button(onClick = { probe.authorizeAndScan() }, enabled = !probeState.busy) { Text("授权并查询设备") }
        probeState.devices.forEach { device ->
            OutlinedButton(onClick = { probe.connect(device) }, enabled = !probeState.busy, modifier = Modifier.fillMaxWidth()) {
                Text("${device.name.orEmpty()} · ${if (device.isConnected) "已连接" else "未连接"}\n${device.model.orEmpty()} / P2P ${device.p2pCapability}")
            }
        }
        Text("手表先进入：周视图 → 同步 → 开始接收。此版不会假装已实现自动拉起或其他运行时通装。", style = MaterialTheme.typography.bodySmall)
        Button(onClick = { if (saveSnapshot()) confirmPublish = true }, enabled = probeState.ready && !probeState.busy) { Text("同步当前手机课表") }
        OutlinedButton(onClick = { probe.cancel() }) { Text("断开并停止同步") }
        Text("生产签名固定；控制台指纹登记与 Wear Engine 审批仍需核对。SDK 错误直接显示，不生成成功回执。", style = MaterialTheme.typography.bodySmall)
    }
    private fun saveSnapshot(): Boolean {
        return try {
            val snapshot = PhoneSnapshot.encode(input)
            input = snapshot
            check(getSharedPreferences("schedule", MODE_PRIVATE).edit().putString("snapshot", snapshot).commit()) { "手机保存失败" }
            inputError = null; true
        } catch (e: Exception) { inputError = e.message ?: "无效课表"; false }
    }
    override fun onStop() { if (::probe.isInitialized) probe.onBackground(); super.onStop() }
    override fun onDestroy() { if (::probe.isInitialized) probe.close(); super.onDestroy() }
}
