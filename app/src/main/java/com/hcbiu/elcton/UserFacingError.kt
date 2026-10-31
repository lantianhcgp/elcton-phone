package com.hcbiu.elcton

/** Only finite local validation messages and exception types may reach UI or logs. */
object UserFacingError {
    private val local = setOf(
        "请输入课程名称", "请填写有效节次", "输入过长", "仅支持 elcton.schedule v1", "学期日期格式错误",
        "课程数量超出当前保护上限", "课程时间格式错误", "课程 ID 为空或重复", "结束时间必须晚于开始时间",
        "不支持的周类型", "自定义周尚未实现，不静默丢弃", "快照超出当前协议保护上限", "无效课表标识",
        "无效课表版本", "导入文件过大", "无法读取文件", "无法写入文件", "请先恢复无法读取的课表",
        "课表 JSON 格式或字段无效", "保存后的校验不一致", "课表校验不一致"
    ) + listOf("id", "name", "location", "teacher", "startTime", "endTime", "weekType").map { "字段 $it 类型或长度错误" } +
        listOf("dayOfWeek", "startPeriod", "endPeriod", "colorIndex").map { "字段 $it 范围错误" }

    fun validation(message: String?): String = message?.takeIf { it in local }
        ?: "课表格式或操作无效，请检查输入后重试。"

    fun diagnostic(error: Exception): String = error.javaClass.simpleName.takeIf { Regex("[A-Za-z0-9_]{1,80}").matches(it) }
        ?: "Exception"

    fun explain(message:String):String {
        val m=message.lowercase()
        return when {
            "health app not exist" in m || "health app not installed" in m -> "未安装华为运动健康。安装并登录后，先在运动健康配对手表。"
            "auth" in m || "permission" in m || "not support" in m -> "Wear Engine 权限或设备能力未满足。请检查运动健康授权与服务开通状态。"
            "connect" in m || "timeout" in m -> "暂时无法连接手表。请打开运动健康，确认连接正常后重试。"
            else -> "Wear Engine 暂不可用。可打开诊断记录查看错误类型；如已开始同步，请重新连接核对手表最终版本。"
        }
    }
}
