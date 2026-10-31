package com.hcbiu.elcton

import org.junit.Assert.*
import org.junit.Test
import java.time.LocalDate

class ScheduleBookTest {
    private fun course(id: String = "c1", week: String = "all") = Course(
        id, "语文", "A301", "测试教师", 6, 1, 1, "08:00", "08:45", week, 1
    )
    @Test fun emptyBookIsNotDemonstrationData() {
        val b = ScheduleBook.empty("book1", "2026-09-01")
        assertEquals(0, b.courses.size)
        assertEquals("book1", b.datasetId)
        assertEquals(b, ScheduleBook.decode(b.storageJson()))
    }
    @Test fun editingPreservesCourseIdentityAndAdvancesSourceRevision() {
        val b = ScheduleBook.empty("book1", "2026-09-01").put(course())
        val changed = b.put(course().copy(name = "数学"))
        assertEquals(1, changed.courses.size)
        assertEquals("c1", changed.courses[0].id)
        assertEquals(b.revision + 1, changed.revision)
    }
    @Test fun deletingAndRestartingDoesNotRestoreTheCourse() {
        val b = ScheduleBook.empty("book1", "2026-09-01").put(course()).remove("c1")
        assertTrue(ScheduleBook.decode(b.storageJson()).courses.isEmpty())
    }
    @Test fun weeklyFilterUsesMondayBoundaryAndIncludesSaturday() {
        val b = ScheduleBook.empty("book1", "2026-09-01").put(course("odd", "odd")).put(course("even", "even"))
        assertEquals(1, b.weekAt(LocalDate.parse("2026-09-05")))
        assertEquals(listOf("odd"), b.forDay(6,1).map { it.id })
        assertEquals(listOf("even"), b.forDay(6,2).map { it.id })
        assertEquals(2, b.weekAt(LocalDate.parse("2026-09-07")))
    }
    @Test fun invalidCourseCannotReplaceLastValidState() {
        val b = ScheduleBook.empty("book1", "2026-09-01").put(course())
        assertThrows(IllegalArgumentException::class.java) { b.put(course().copy(endTime="07:00")) }
        assertEquals("语文", b.courses[0].name)
    }
    @Test fun importKeepsDatasetIdentityAndCreatesAnExplicitNewRevision() {
        val b = ScheduleBook.empty("book1", "2026-09-01")
        val input = b.put(course()).wireJson()
        val imported = b.importSnapshot(input, remoteRevision=7)
        assertEquals("book1", imported.datasetId)
        assertEquals(8L, imported.revision)
        assertEquals("语文", imported.courses[0].name)
        assertEquals(PhoneSnapshot.encode(input), imported.wireJson())
    }
}
