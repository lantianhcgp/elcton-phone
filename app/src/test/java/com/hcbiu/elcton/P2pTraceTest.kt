package com.hcbiu.elcton

import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Test

/** HOST only. Reflection makes the first RED an assertion, not a compiler failure. */
class P2pTraceTest {
    private fun type(): Class<*> {
        val found = runCatching { Class.forName("com.hcbiu.elcton.P2pTrace") }.getOrNull()
        assertNotNull("Missing P2pTrace schema1 observation seam", found)
        return found!!
    }
    private fun trace(wall: () -> Long = { 700L }, elapsed: () -> Long = { 9L }): Any =
        type().getConstructor(String::class.java, kotlin.jvm.functions.Function0::class.java, kotlin.jvm.functions.Function0::class.java)
            .newInstance("host-test", wall, elapsed)
    private fun emit(t: Any, stage: String, fields: Map<String, Any?> = emptyMap()) {
        type().getMethod("emit", String::class.java, String::class.java, Map::class.java).invoke(t, "engine", stage, fields)
    }
    private fun read(t: Any, after: Long = 0, limit: Int = 128) = type()
        .getMethod("read", Long::class.javaPrimitiveType, Int::class.javaPrimitiveType).invoke(t, after, limit) as JSONObject
    @Test fun schemaClockSequenceAndIndependentGenerationReferences() {
        val t=trace(); emit(t,"SEND_CALL",mapOf("generation" to 2,"nativeGeneration" to 17L,"attemptId" to 6L,"bytes" to 90))
        emit(t,"SEND_RESULT",mapOf("resultCode" to 206,"stale" to true))
        val r=read(t); val events=r.getJSONArray("events"); assertEquals(2,events.length())
        val e=events.getJSONObject(0)
        assertEquals(1,e.getInt("schema")); assertEquals("host-test",e.getString("origin")); assertEquals(1L,e.getLong("seq"))
        assertEquals(700L,e.getLong("wallMs")); assertEquals(9L,e.getLong("elapsedMs")); assertEquals(2,e.getInt("generation"))
        assertEquals(17L,e.getLong("nativeGeneration")); assertEquals(6L,e.getLong("attemptId")); assertEquals(206,events.getJSONObject(1).getInt("resultCode"))
        assertEquals(e.getString("sid"),events.getJSONObject(1).getString("sid")); assertTrue(events.getJSONObject(1).getBoolean("stale"))
    }
    @Test fun boundedTailTrueDroppedCursorAndPrivacy() {
        val t=trace(); repeat(140) { emit(t,"SEND_CALL",mapOf("name" to "PRIVATE_NAME","MAC" to "PRIVATE_MAC","data" to "PRIVATE_COURSE","token" to "PRIVATE_TOKEN","url" to "PRIVATE_URL","type" to "PRIVATE_TYPE","reason" to "PRIVATE_REASON","bytes" to it)) }
        val r=read(t); assertEquals(128,r.getInt("buffer")); assertEquals(12L,r.getLong("dropped"))
        assertEquals(13L,r.getJSONArray("events").getJSONObject(0).getLong("seq")); assertTrue(r.getBoolean("has_more"))
        val page=read(t,135,2); assertEquals(2,page.getJSONArray("events").length()); assertTrue(page.getBoolean("has_more")); assertEquals(137L,page.getLong("nextSeq"))
        assertFalse(r.toString().contains("PRIVATE_")); assertTrue(r.toString().toByteArray().size<1024*1024)
        for(i in 0 until r.getJSONArray("events").length()) {
            val e=r.getJSONArray("events").getJSONObject(i); assertTrue(e.toString().toByteArray(Charsets.UTF_8).size<=2048)
            assertTrue(e.has("truncated")); assertTrue(e.has("originalBytes"))
        }
    }
    @Test fun hostileFieldAndClocksCannotEscapeOrInventEvent() {
        val t=trace(elapsed={ throw IllegalStateException("PRIVATE_CLOCK") }); emit(t,"SEND_CALL")
        assertEquals(0,read(t).getInt("buffer")); assertEquals(1L,read(t).getLong("dropped"))
        val good=trace(); val hostile=object: java.util.AbstractMap<String,Any?>() {
            override val entries: MutableSet<MutableMap.MutableEntry<String, Any?>> get()=throw IllegalStateException("PRIVATE_GETTER")
        }
        emit(good,"SEND_CALL",hostile); assertEquals(0,read(good).getInt("buffer")); assertEquals(1L,read(good).getLong("dropped"))
    }
    @Test fun writerFailureAndStorageFullAreDiagnosticOnlyAndNoRetriesAfterFull() {
        val t=trace(); emit(t,"SEND_CALL"); var calls=0
        val persist=type().getMethod("persist",kotlin.jvm.functions.Function1::class.java)
        persist.invoke(t,{ _:String -> calls++; throw IllegalStateException("PRIVATE_WRITER") })
        assertEquals(1,calls); assertEquals("trace_write_failed",read(t).getString("storage"))
        persist.invoke(t,{ _:String -> calls++; false }); assertEquals(2,calls); assertEquals("trace_storage_full",read(t).getString("storage"))
        emit(t,"SEND_RESULT"); persist.invoke(t,{ _:String -> calls++; true }); assertEquals(2,calls)
        assertFalse(read(t).toString().contains("PRIVATE_WRITER"))
    }
    @Test fun engineKeepsFiveArgConstructorAndRequiresTraceAttachment() {
        assertEquals(1,SyncEngine::class.java.constructors.count{it.parameterCount==5})
        assertNotNull("Missing diagnostic-only attachTrace",SyncEngine::class.java.methods.firstOrNull{it.name=="attachTrace"&&it.parameterCount==1})
    }
}
