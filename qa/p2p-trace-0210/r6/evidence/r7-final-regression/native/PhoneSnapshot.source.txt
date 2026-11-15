package com.hcbiu.elcton

import org.json.JSONArray
import org.json.JSONException
import org.json.JSONObject

/** Reject JSON coercions and numbers outside the exact integer range shared with JavaScript. */
internal fun exactInteger(value: Any?): Long? = when (value) {
    is Byte, is Short, is Int, is Long -> (value as Number).toLong().takeIf { it in -9007199254740990L..9007199254740990L }
    else -> null
}

internal fun semesterDate(start: String): java.time.LocalDate {
    require(Regex("[0-9]{4}-[0-9]{2}-[0-9]{2}").matches(start) && start.take(4) != "0000") { "学期日期格式错误" }
    return java.time.LocalDate.parse(start)
}

/** Strict ingress; this probe does not silently normalize newer schemas or drop courses. */
object PhoneSnapshot {
    fun encode(raw: String): String = try {
        encodeDocument(raw)
    } catch (_: JSONException) {
        // JSON exception messages can include the original course/teacher text. Never propagate them.
        throw IllegalArgumentException("课表 JSON 格式或字段无效")
    }
    private fun encodeDocument(raw: String): String {
        require(raw.length <= 65536) { "输入过长" }
        val input = JSONObject(raw)
        require(input.opt("schema") == "elcton.schedule" && exactInteger(input.opt("version")) == 1L) { "仅支持 elcton.schedule v1" }
        val startValue = input.getJSONObject("settings").opt("semesterStart")
        require(startValue is String) { "学期日期格式错误" }
        val start = startValue
        semesterDate(start)
        val list = input.getJSONArray("courses")
        require(list.length() <= 200) { "课程数量超出当前保护上限" }
        val ids = mutableSetOf<String>()
        val courses = mutableListOf<JSONObject>()
        fun str(c: JSONObject, key: String, max: Int): String {
            val value = c.get(key)
            require(value is String && value.length <= max) { "字段 $key 类型或长度错误" }
            return value
        }
        fun number(c: JSONObject, key: String, low: Int, high: Int): Int {
            val value = c.get(key)
            val integer = exactInteger(value)
            require(integer != null && integer in low.toLong()..high.toLong()) { "字段 $key 范围错误" }
            return integer.toInt()
        }
        fun time(c: JSONObject, key: String): String {
            val value = str(c, key, 5)
            require(Regex("([01][0-9]|2[0-3]):[0-5][0-9]").matches(value)) { "课程时间格式错误" }
            return value
        }
        for (i in 0 until list.length()) {
            val c = list.getJSONObject(i)
            val id = str(c, "id", 64)
            require(id.isNotEmpty() && ids.add(id)) { "课程 ID 为空或重复" }
            val course = JSONObject()
            course.put("id", id); course.put("name", str(c,"name",80)); course.put("location",str(c,"location",80)); course.put("teacher",str(c,"teacher",80))
            course.put("dayOfWeek",number(c,"dayOfWeek",1,7)); val first=number(c,"startPeriod",1,24)
            course.put("startPeriod",first); course.put("endPeriod",number(c,"endPeriod",first,24))
            val from=time(c,"startTime");val to=time(c,"endTime");require(to>from){"结束时间必须晚于开始时间"}
            course.put("startTime",from);course.put("endTime",to)
            val week=str(c,"weekType",4);require(week in listOf("all","odd","even")){"不支持的周类型"}
            require(c.getJSONArray("weeks").length()==0){"自定义周尚未实现，不静默丢弃"}
            course.put("weekType",week);course.put("weeks",JSONArray());course.put("colorIndex",number(c,"colorIndex",0,7))
            courses+=course
        }
        courses.sortWith(compareBy({it.getInt("dayOfWeek")},{it.getInt("startPeriod")},{it.getString("startTime")},{it.getString("id")}))
        fun courseJson(c: JSONObject): String = "{" + listOf(
            "id" to Wire.quote(c.getString("id")), "name" to Wire.quote(c.getString("name")),
            "location" to Wire.quote(c.getString("location")), "teacher" to Wire.quote(c.getString("teacher")),
            "dayOfWeek" to c.getInt("dayOfWeek").toString(), "startPeriod" to c.getInt("startPeriod").toString(),
            "endPeriod" to c.getInt("endPeriod").toString(), "startTime" to Wire.quote(c.getString("startTime")),
            "endTime" to Wire.quote(c.getString("endTime")), "weekType" to Wire.quote(c.getString("weekType")),
            "weeks" to "[]", "colorIndex" to c.getInt("colorIndex").toString()
        ).joinToString(",") { (name, value) -> Wire.quote(name) + ":" + value } + "}"
        val encoded = "{\"schema\":\"elcton.schedule\",\"version\":1,\"settings\":{\"semesterStart\":" +
            Wire.quote(start) + "},\"courses\":[" + courses.joinToString(",") { courseJson(it) } + "]}"
        require(encoded.length<=32768){"快照超出当前协议保护上限"}
        return encoded
    }
}
