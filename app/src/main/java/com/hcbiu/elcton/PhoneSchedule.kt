package com.hcbiu.elcton

/** One validated schedule repository shared by the editor and local MCP. */
interface ScheduleRepository {
    fun load(): ScheduleBook
    fun save(book: ScheduleBook)
    fun restore(): ScheduleBook
    fun hasBackup(): Boolean
}

class PhoneSchedule(private val repository: ScheduleRepository, private val changed: (State) -> Unit = {}) {
    data class State(
        val book: ScheduleBook = ScheduleBook.empty("unloaded", "2026-09-01"),
        val loadError: String? = null,
        val notice: String = "",
        val pendingImport: ScheduleBook? = null,
        val importBaseRevision: Long? = null
    )
    var state = State()
        private set

    init {
        state = try { State(book = repository.load()) }
        catch (_: Exception) { State(loadError = "手机课表读取失败；原文件未重置。可在设置恢复备份。") }
    }

    private fun publish(next: State) { state = next; changed(next) }
    fun notice(text: String) { publish(state.copy(notice = text)) }
    fun hasBackup(): Boolean = repository.hasBackup()

    fun save(next: ScheduleBook): Boolean = try {
        check(state.loadError == null) { "请先恢复无法读取的课表" }
        require(next.datasetId == state.book.datasetId && next.revision >= state.book.revision) { "课表已更新，请重新读取" }
        next.wireJson() // The same strict ingress as import and synchronization.
        repository.save(next)
        publish(state.copy(book = next, notice = "已保存在手机，尚未同步到手表"))
        true
    } catch (error: Exception) {
        notice(UserFacingError.validation(error.message)); false
    }

    fun prepareImport(raw: String, remoteRevision: Long = 0): Boolean = try {
        check(state.loadError == null) { "请先恢复无法读取的课表" }
        val proposed = state.book.importSnapshot(raw, remoteRevision)
        publish(state.copy(pendingImport = proposed, importBaseRevision = state.book.revision, notice = "请确认导入预览；尚未替换手机课表"))
        true
    } catch (error: Exception) {
        notice("无法导入：" + UserFacingError.validation(error.message)); false
    }

    fun confirmImport(): Boolean {
        val proposed = state.pendingImport ?: return false
        if (state.importBaseRevision != state.book.revision) {
            notice("预览后手机课表已更新，请重新检查导入内容")
            return false
        }
        if (!save(proposed)) return false
        publish(state.copy(pendingImport = null, importBaseRevision = null))
        return true
    }
    fun cancelImport() { publish(state.copy(pendingImport = null, importBaseRevision = null)) }
    fun restore(): Boolean = try {
        val restored = repository.restore()
        publish(State(book = restored, notice = "已恢复上一版本")); true
    } catch (error: Exception) { notice("恢复失败：" + UserFacingError.validation(error.message)); false }
}
