package com.hcbiu.elcton

/** Short actionable UI text; detailed SDK exceptions stay in a separate diagnostic panel. */
object UserFacingError {
    fun explain(message:String):String {
        val m=message.lowercase()
        return when {
            "health app not exist" in m || "health app not installed" in m -> "未安装华为运动健康。安装并登录后，先在运动健康配对手表。"
            "auth" in m || "permission" in m || "not support" in m -> "Wear Engine 权限或设备能力未满足。请检查运动健康授权与服务开通状态。"
            "connect" in m || "timeout" in m -> "暂时无法连接手表。请打开运动健康，确认连接正常后重试。"
            else -> "Wear Engine 暂不可用。没有发送或覆盖课表，可打开诊断记录查看原因。"
        }
    }
}
