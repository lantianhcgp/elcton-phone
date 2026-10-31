package com.hcbiu.elcton

import android.content.Context
import android.util.AtomicFile
import java.io.File
import java.util.UUID
import java.time.LocalDate

/** Small private, verified JSON store with a last-good backup. No automatic destructive reset on read error. */
class ScheduleStore(context: Context) {
    private val main=AtomicFile(File(context.filesDir,"timetable.json"))
    private val backup=AtomicFile(File(context.filesDir,"timetable-last-good.json"))
    private var last: ScheduleBook?=null
    @Synchronized fun load(): ScheduleBook {
        if(main.baseFile.exists()||File(main.baseFile.path+".bak").exists()) {
            val book=ScheduleBook.decode(String(main.readFully(),Charsets.UTF_8))
            last=book; return book
        }
        val book=ScheduleBook.empty(UUID.randomUUID().toString(), LocalDate.now().withMonth(9).withDayOfMonth(1).toString())
        save(book); return book
    }
    private fun write(file: AtomicFile,text: String) {
        val stream=file.startWrite()
        try { stream.write(text.toByteArray(Charsets.UTF_8));file.finishWrite(stream) }
        catch(e:Exception){file.failWrite(stream);throw e}
        check(String(file.readFully(),Charsets.UTF_8)==text){"保存后的校验不一致"}
    }
    @Synchronized fun save(book: ScheduleBook) {
        val text=book.storageJson()
        check(ScheduleBook.decode(text)==book){"课表校验不一致"}
        val previous=last
        if(previous!=null && previous!=book)write(backup,previous.storageJson())
        write(main,text)
        last=book
    }
    @Synchronized fun restore(): ScheduleBook {
        val book=ScheduleBook.decode(String(backup.readFully(),Charsets.UTF_8))
        val restored=book.copy(revision=maxOf(last?.revision?:0,book.revision)+1)
        write(main,restored.storageJson());last=restored;return restored
    }
    fun hasBackup(): Boolean = backup.baseFile.exists() || File(backup.baseFile.path+".bak").exists()
}
