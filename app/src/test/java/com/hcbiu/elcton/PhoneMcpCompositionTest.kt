package com.hcbiu.elcton

import org.json.JSONArray
import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Test
import java.nio.file.Files

class PhoneMcpCompositionTest {
    @Test fun originalDiagnosticSchemasAndBehaviorRemainExactAfterAppendingActions() {
        val root=Files.createTempDirectory("combined-mcp-").toFile()
        val old=DiagnosticTools(root,{JSONArray().put(JSONObject().put("limit",it))},{JSONObject().put("connected",false)},{JSONObject().put("versionName","test")})
        val combined=CombinedMcpTools(old,PhoneMcpTools {_,_->JSONObject().put("error","test-unused-action")})
        try {
            val original=old.list();val all=combined.list()
            assertEquals(4,original.length());assertEquals(15,all.length())
            for(i in 0 until original.length()) assertEquals(original.getJSONObject(i).toString(),all.getJSONObject(i).toString())
            for((name,args) in listOf("version_info" to JSONObject(),"diag_read" to JSONObject(),"error_tail" to JSONObject().put("limit",7)))
                assertEquals(old.call(name,args).toString(),combined.call(name,args).toString())
            assertEquals(old.validArguments("error_tail",JSONObject().put("limit",129)),combined.validArguments("error_tail",JSONObject().put("limit",129)))
        } finally {root.deleteRecursively()}
    }
    @Test fun duplicateOwnershipCannotSilentlyReplaceAnOldTool() {
        val root=Files.createTempDirectory("combined-duplicate-").toFile()
        val old=DiagnosticTools(root,{JSONArray()},{JSONObject()},{JSONObject()})
        try {assertThrows(IllegalStateException::class.java){CombinedMcpTools(old,old).list()}}
        finally {root.deleteRecursively()}
    }
}
