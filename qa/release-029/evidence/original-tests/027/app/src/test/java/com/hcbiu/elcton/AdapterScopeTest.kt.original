package com.hcbiu.elcton

import java.io.File
import org.junit.Assert.*
import org.junit.Test

/** Guards the explicitly approved first-stage adapter scope, not SDK behavior. */
class AdapterScopeTest {
    private fun source(name:String):String {
        val roots=listOf(File("app/src/main/java/com/hcbiu/elcton"),File("src/main/java/com/hcbiu/elcton"))
        val file=roots.map{File(it,name)}.firstOrNull{it.isFile}?:error("Source not found for scope gate")
        return file.readText()
    }
    @Test fun automaticPeerWakeIsNotEnabledWithoutLifecycleAndRealDeviceEvidence(){
        assertFalse("Automatic ping/wakeup is out of the approved first-stage scope",source("WearProbe.kt").contains("p2p.ping("))
    }
    @Test fun backupFailureDoesNotExposeExceptionMessageInProductUi(){
        assertFalse("Restore exceptions may contain local paths or private content",source("MainActivity.kt").contains("恢复失败：\u0024{it.message}"))
    }
}
