package com.hcbiu.elcton

import android.app.Activity
import android.os.Handler
import android.os.Looper
import com.huawei.wearengine.HiWear
import com.huawei.wearengine.auth.AuthCallback
import com.huawei.wearengine.auth.Permission
import com.huawei.wearengine.device.Device
import com.huawei.wearengine.p2p.Message
import com.huawei.wearengine.p2p.Receiver
import com.huawei.wearengine.p2p.SendCallback
import org.json.JSONObject

/** Real Wear Engine integration. No SDK result is manufactured when Health/authorization is unavailable. */
class WearProbe(private val activity: Activity, private val update: (State) -> Unit) {
    data class State(
        val status: String = "等待连接", val detail: String = "先安装并打开华为运动健康，与手表保持连接。",
        val devices: List<Device> = emptyList(), val selected: String = "", val ready: Boolean = false,
        val busy: Boolean = false, val digest: String = "", val dirty: Boolean = false, val revision: Long = 0,
        val maxBytes: Int = 8192
    )
    private val handler = Handler(Looper.getMainLooper())
    private val p2p by lazy { HiWear.getP2pClient(activity) }
    private var state = State()
    private var receiver: Receiver? = null
    private var registeredDevice: Device? = null
    private var generation = 0
    private var timer: Runnable? = null
    private var session: TransferSession? = null
    private var closed = false
    private var handshakeAttempts = 0
    private var awaitingPermission = false
    private val watchPackage = "watchapp.nexus.0zzip"
    private val watchFingerprint = "8926257d1bd9ff653dcd84100d53cbbabbd39371fdda5126dfb37429e55c67be"

    private fun publish(next: State) { state = next; update(next) }
    private fun main(block: () -> Unit): Unit { handler.post { if (!closed && !activity.isFinishing) block() } }
    private fun fail(message: String) {
        generation++; cancelTimer(); session = null; awaitingPermission = false; unregister()
        publish(state.copy(status = "操作未完成", detail = message.take(200), busy = false, ready = false))
    }
    private fun cancelTimer() { timer?.let(handler::removeCallbacks); timer = null }
    private fun deadline(millis: Long, action: () -> Unit) {
        cancelTimer(); val job = Runnable { if (!closed) action() }; timer = job; handler.postDelayed(job, millis)
    }
    fun authorizeAndScan() {
        if (state.busy) return
        val gen = ++generation
        publish(state.copy(status = "检查授权", busy = true, ready = false))
        deadline(20000) { fail("授权检查超时；请确认运动健康可用。") }
        try {
            HiWear.getAuthClient(activity).checkPermission(Permission.DEVICE_MANAGER)
                .addOnSuccessListener { granted -> main {
                    if (gen != generation) return@main
                    if (granted) scan(gen) else {
                        cancelTimer()
                        awaitingPermission = true
                        publish(state.copy(status = "等待用户授权", busy = true))
                        HiWear.getAuthClient(activity).requestPermission(object : AuthCallback {
                            override fun onOk(permissions: Array<Permission>) = main {
                                if (gen == generation) { awaitingPermission = false; scan(gen) }
                            }
                            override fun onCancel() = main { if (gen == generation) fail("你取消了授权，未查询或发送课表。") }
                        }, Permission.DEVICE_MANAGER).addOnFailureListener { e -> main { if (gen == generation) fail(describe(e)) } }
                    }
                }}.addOnFailureListener { e -> main { if (gen == generation) fail(describe(e)) } }
        } catch (e: Exception) { fail(describe(e)) }
    }
    private fun scan(gen: Int) {
        publish(state.copy(status = "查询配对设备", busy = true))
        deadline(15000) { fail("设备查询超时，请检查运动健康连接。") }
        try {
            HiWear.getDeviceClient(activity).commonDevice
                .addOnSuccessListener { devices -> main {
                    if (gen != generation) return@main
                    cancelTimer()
                    val found = devices.orEmpty()
                    publish(state.copy(status = if (found.isEmpty()) "未找到支持的设备" else "选择同步设备",
                        detail = "依据实际连接和 P2P 能力判断，不以 FIT3 型号筛选。", devices = found, busy = false))
                }}.addOnFailureListener { e -> main { if (gen == generation) fail(describe(e)) } }
        } catch (e: Exception) { fail(describe(e)) }
    }
    fun connect(device: Device) {
        if (state.busy) return
        if (!DevicePolicy.canAttemptSync(device.isConnected, device.p2pCapability, Device.DEVICE_CAPABILITY_SUPPORT, Device.DEVICE_CAPABILITY_NOT_SUPPORT)) {
            fail("该设备未连接或明确不支持应用间 P2P 通信。"); return
        }
        unregister(); val gen = ++generation
        publish(state.copy(status = "检查手表应用", selected = device.uuid.orEmpty(), busy = true, ready = false, dirty = false))
        deadline(15000) { fail("安装检查超时；请保持手表和运动健康连接。") }
        try {
            p2p.setPeerPkgName(watchPackage).setPeerFingerPrint(watchFingerprint)
            p2p.isAppInstalled(device, watchPackage).addOnSuccessListener { installed -> main {
                if (gen != generation) return@main
                if (!installed) { fail("设备上未安装本次配套课表 App。其他运行时的独立包还在适配，不能用此 Lite 包硬装。"); return@main }
                cancelTimer()
                val callback = Receiver { message -> main {
                    if (gen != generation || message.type != Message.MESSAGE_TYPE_DATA) return@main
                    val bytes = message.data ?: return@main
                    if (bytes.size <= 1024) onMessage(bytes.toString(Charsets.UTF_8))
                }}
                receiver = callback; registeredDevice = device
                p2p.registerReceiver(device, callback).addOnSuccessListener { main {
                    if (gen != generation) return@main
                    handshakeAttempts = 0
                    publish(state.copy(status = "等待手表准备", detail = "请在手表进入：周视图 → 同步 → 开始接收。", busy = true))
                    hello()
                }}.addOnFailureListener { e -> main { if (gen == generation) fail(describe(e)) } }
            }}.addOnFailureListener { e -> main { if (gen == generation) fail(describe(e)) } }
        } catch (e: Exception) { fail(describe(e)) }
    }
    private fun hello() {
        if (registeredDevice == null) { fail("请先连接设备。"); return }
        send("{" + Wire.header("HELLO", "") + "}")
        deadline(5000) {
            if (++handshakeAttempts <= 3) hello() else fail("未收到 READY。请打开手表同步页并开始接收；未发送任何课表。")
        }
    }
    private fun onMessage(text: String) {
        val message = try { JSONObject(text) } catch (_: Exception) { return }
        if (message.optString("protocol") != "elcton.sync" || message.optInt("version") != 1 || message.optString("sender") != "watch") return
        val type = message.optString("type")
        if (type == "READY" && session == null) {
            cancelTimer()
            val limit = message.optInt("maxBytes", 0)
            if (limit !in 1..32768) { fail("对端能力信息无效，未发送课表。"); return }
            publish(state.copy(status = "手表已准备", detail = "下一步发送当前本地快照，保存确认后才算成功。", ready = true, busy = false,
                digest = message.optString("digest"), dirty = message.optBoolean("localDirty"), revision = message.optLong("sourceRevision"), maxBytes = limit))
            return
        }
        val current = session ?: return
        if (!current.reply(type, message.optString("transferId"), message.optInt("seq", -99), message.optString("digest"), message.optLong("sourceRevision"), message.optString("code"))) return
        cancelTimer()
        if (current.complete) {
            session = null
            publish(state.copy(status = "同步成功", detail = "手表已保存并读回确认，版本 ${current.revision}。", busy = false, digest = current.digest, dirty = false, revision = current.revision))
        } else if (current.error != null) fail("手表拒绝本次提交：${current.error}。旧课表仍保留。")
        else transmitCurrent()
    }
    fun publishSnapshot(text: String, force: Boolean) {
        if (!state.ready || state.busy || registeredDevice == null) return
        if (text.toByteArray(Charsets.UTF_8).size > state.maxBytes) { fail("快照超出当前设备安全预算。分片懒加载路线仍在实现，不删课程截断。"); return }
        try {
            session = TransferSession(text, "t-" + System.currentTimeMillis().toString(36), "school", maxOf(1L, state.revision + 1), state.digest, force)
            publish(state.copy(status = "发送课表", detail = "正在发送 BEGIN，等待应用层确认。", busy = true))
            transmitCurrent()
        } catch (e: Exception) { fail(describe(e)) }
    }
    private fun transmitCurrent() {
        val current = session ?: return
        val message = current.currentMessage ?: return
        publish(state.copy(status = if (current.acceptedChunks == current.chunkCount) "等待保存确认" else "发送课表",
            detail = "已确认 ${current.acceptedChunks}/${current.chunkCount} 包；未收到 APPLIED 前不算成功。"))
        send(message)
        deadline(5000) { if (session === current) { if (current.timeout()) transmitCurrent() else fail("确认超时，旧课表保留；请重新连接核对已提交状态。") } }
    }
    private fun send(text: String) {
        val device = registeredDevice ?: return
        val gen = generation
        if (text.toByteArray(Charsets.UTF_8).size > 1024) { fail("消息超出 1 KB，未发送。"); return }
        try {
            p2p.send(device, Message.Builder().setPayload(text.toByteArray(Charsets.UTF_8)).build(), object : SendCallback {
                override fun onSendResult(code: Int) = main {
                    if (gen == generation && code != 207) fail("Wear Engine 发送失败（$code），没有保存成功证据。")
                    else session?.transportSucceeded()
                }
                override fun onSendProgress(progress: Long) { /* data progress is not application commit */ }
            }).addOnFailureListener { e -> main { if (gen == generation) fail(describe(e)) } }
        } catch (e: Exception) { fail(describe(e)) }
    }
    fun cancel() {
        session?.let { send("{" + Wire.header("CANCEL", it.transferId) + "}") }
        generation++; cancelTimer(); session = null; unregister()
        publish(state.copy(status = "已断开", detail = "没有继续后台同步。", busy = false, ready = false))
    }
    private fun unregister() {
        receiver?.let { try { p2p.unregisterReceiver(it) } catch (_: Exception) {} }
        receiver = null; registeredDevice = null
    }
    fun onBackground() { if (!awaitingPermission) cancel() }
    fun close() { awaitingPermission = false; cancel(); closed = true }
    private fun describe(e: Exception): String = "${e.javaClass.simpleName}: ${e.message.orEmpty()}".take(200)
}
