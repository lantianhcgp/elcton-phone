package com.hcbiu.elcton

import org.json.JSONArray
import org.json.JSONObject
import java.time.LocalDate
import java.time.temporal.ChronoUnit

/** Stable course identifiers are never recreated when editing or importing. */
data class Course(
    val id: String, val name: String, val location: String, val teacher: String,
    val dayOfWeek: Int, val startPeriod: Int, val endPeriod: Int,
    val startTime: String, val endTime: String, val weekType: String, val colorIndex: Int
) {
    fun json(): JSONObject = JSONObject().put("id",id).put("name",name).put("location",location)
        .put("teacher",teacher).put("dayOfWeek",dayOfWeek).put("startPeriod",startPeriod)
        .put("endPeriod",endPeriod).put("startTime",startTime).put("endTime",endTime)
        .put("weekType",weekType).put("weeks",JSONArray()).put("colorIndex",colorIndex)
    companion object {
        fun decode(c: JSONObject) = Course(c.getString("id"),c.getString("name"),c.getString("location"),
            c.getString("teacher"),c.getInt("dayOfWeek"),c.getInt("startPeriod"),c.getInt("endPeriod"),
            c.getString("startTime"),c.getString("endTime"),c.getString("weekType"),c.getInt("colorIndex"))
    }
}

data class ScheduleBook(val datasetId: String, val revision: Long, val semesterStart: String, val courses: List<Course>) {
    init {
        require(Regex("[A-Za-z0-9_-]{1,64}").matches(datasetId)) { "无效课表标识" }
        require(revision in 0..9007199254740990L) { "无效课表版本" }
        semesterDate(semesterStart)
    }
    private fun document(): JSONObject = JSONObject().put("schema","elcton.schedule").put("version",1)
        .put("settings",JSONObject().put("semesterStart",semesterStart)).put("courses",JSONArray(courses.map { it.json() }))
    fun wireJson(): String = PhoneSnapshot.encode(document().toString())
    fun storageJson(): String = JSONObject(wireJson()).put("datasetId",datasetId).put("sourceRevision",revision).toString()
    fun put(course: Course): ScheduleBook {
        require(course.name.isNotBlank()) { "请输入课程名称" }
        val result=copy(revision=revision+1, courses=courses.filterNot { it.id==course.id }+course)
        result.wireJson()
        return result
    }
    fun remove(id: String): ScheduleBook = if (courses.none {it.id==id}) this else copy(revision=revision+1,courses=courses.filterNot {it.id==id})
    fun withSemester(start: String): ScheduleBook {
        semesterDate(start)
        return if(start==semesterStart)this else copy(semesterStart=start,revision=revision+1)
    }
    fun importSnapshot(raw: String, remoteRevision: Long = 0): ScheduleBook {
        require(remoteRevision in 0..9007199254740989L) { "无效课表版本" }
        val canonical=JSONObject(PhoneSnapshot.encode(raw))
        val list=canonical.getJSONArray("courses")
        return copy(revision=maxOf(revision,remoteRevision)+1,semesterStart=canonical.getJSONObject("settings").getString("semesterStart"),
            courses=(0 until list.length()).map {Course.decode(list.getJSONObject(it))})
    }
    fun weekAt(date: LocalDate): Int {
        val start=LocalDate.parse(semesterStart)
        val monday=start.minusDays((start.dayOfWeek.value-1).toLong())
        val days=ChronoUnit.DAYS.between(monday,date)
        return maxOf(1,(days/7).toInt()+1)
    }
    fun forDay(day: Int, week: Int): List<Course> = courses.filter {
        it.dayOfWeek==day && (it.weekType=="all" || it.weekType=="odd"&&week%2==1 || it.weekType=="even"&&week%2==0)
    }.sortedWith(compareBy({it.startPeriod},{it.startTime},{it.id}))
    fun overlaps(course: Course): List<Course> = courses.filter {
        it.id!=course.id && it.dayOfWeek==course.dayOfWeek && it.startTime<course.endTime && course.startTime<it.endTime &&
            (it.weekType=="all" || course.weekType=="all" || it.weekType==course.weekType)
    }
    companion object {
        fun empty(id: String, semester: String) = ScheduleBook(id,1,semester,emptyList())
        fun decode(raw: String): ScheduleBook {
            val normalized=JSONObject(PhoneSnapshot.encode(raw))
            val original=JSONObject(raw)
            val id = original.opt("datasetId")
            val revision = exactInteger(original.opt("sourceRevision"))
            require(id is String) { "无效课表标识" }
            require(revision != null && revision >= 0) { "无效课表版本" }
            val courses=normalized.getJSONArray("courses")
            return ScheduleBook(id,revision,
                normalized.getJSONObject("settings").getString("semesterStart"),(0 until courses.length()).map {Course.decode(courses.getJSONObject(it))})
        }
    }
}
