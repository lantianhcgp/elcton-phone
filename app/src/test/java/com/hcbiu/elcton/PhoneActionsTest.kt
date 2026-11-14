package com.hcbiu.elcton

import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Test

/** Domain behavior across the actual shared engine/repository; no Android/watch claims. */
class PhoneActionsTest {
    private val raw="{\"schema\":\"elcton.schedule\",\"version\":1,\"settings\":{\"semesterStart\":\"2026-09-01\"},\"courses\":[]}"
    private val peer=SyncDevice("paired","Watch","not-a-whitelist",true,0)
    private inner class Harness {
        val sent=mutableListOf<JSONObject>();var receiver:((String)->Unit)?=null;var saves=0;var unregisters=0;var scans=0
        val repo=object:ScheduleRepository {
            var book=ScheduleBook.empty("school","2026-09-01")
            override fun load()=book
            override fun save(book:ScheduleBook){saves++;this.book=book}
            override fun restore()=book
            override fun hasBackup()=saves>0
        }
        val schedule=PhoneSchedule(repo)
        val transport=object:SyncTransport {
            override fun checkPermission(success:(Boolean)->Unit,failure:(String)->Unit){success(true)}
            override fun requestPermission(success:(Boolean)->Unit,failure:(String)->Unit)=false
            override fun scan(success:(List<SyncDevice>)->Unit,failure:(String)->Unit){scans++;success(listOf(peer))}
            override fun installed(device:SyncDevice,success:(Boolean)->Unit,failure:(String)->Unit){success(true)}
            override fun register(device:SyncDevice,message:(String)->Unit,success:()->Unit,failure:(String)->Unit){receiver=message;success()}
            override fun unregister(){unregisters++;receiver=null}
            override fun send(device:SyncDevice,text:String,result:(Int)->Unit,failure:(String)->Unit){sent.add(JSONObject(text));result(207)}
        }
        val scheduler=object:SyncScheduler {
            override fun post(block:()->Unit){block()}
            override fun after(ms:Long,block:()->Unit)=SyncCancellation {}
            override fun now()=1L
            override fun wallTime()=1000L
        }
        val baselines=object:SyncBaselines {
            override fun lastSuccess(deviceId:String)=0L
            override fun save(deviceId:String,datasetId:String,digest:String,revision:Long,at:Long){}
        }
        val sync: SyncEngine=SyncEngine(transport,scheduler,baselines,{}, {doc,revision->actions.receiveImport(doc,revision)})
        val actions: PhoneActions=PhoneActions(sync,schedule)
        fun ready(dirty:Boolean=false,dataset:String="",hasData:Boolean=false) {
            assertTrue(actions.scan());assertTrue(actions.connect(peer.id))
            receive("READY","",",\"maxBytes\":8192,\"digest\":\"00000000\",\"sourceRevision\":0,\"localDirty\":$dirty,\"hasData\":$hasData,\"datasetId\":\"$dataset\"")
            assertTrue(sync.state.ready)
        }
        fun receive(type:String,id:String,extra:String="") { receiver!!("{\"protocol\":\"elcton.sync\",\"version\":1,\"type\":\"$type\",\"transferId\":\"$id\",\"sender\":\"watch\""+extra+"}") }
        fun finishExport() {
            val id=sent.last().getString("transferId");val ascii=PhoneSnapshot.encode(raw);val chunks=ascii.chunked(600)
            receive("EXPORT_META",id,",\"length\":${ascii.length},\"digest\":\"${Wire.crc32(ascii)}\",\"chunks\":${chunks.size},\"sourceRevision\":8")
            chunks.forEachIndexed {i,chunk->receive("EXPORT_CHUNK",id,",\"seq\":$i,\"data\":${JSONObject.quote(chunk)}")}
        }
    }
    @Test fun syncConnectRequiresTheObservedPairedDevice() {
        val h=Harness();assertFalse(h.actions.connect(peer.id));assertTrue(h.sent.isEmpty())
        assertTrue(h.actions.scan());assertEquals(1,h.scans);assertTrue(h.actions.connect(peer.id))
        assertEquals("HELLO",h.sent.last().getString("type"));assertFalse(h.sync.state.ready)
        assertFalse(h.actions.connect("unknown"))
    }
    @Test fun syncDisconnectSharesTheEngineAndInvalidatesReady() {
        val h=Harness();h.ready();h.actions.disconnect()
        assertFalse(h.sync.state.ready);assertFalse(h.sync.state.busy);assertEquals("",h.sync.state.selected);assertNull(h.receiver)
        assertFalse(h.actions.publish(true));assertTrue(h.unregisters>0)
    }
    @Test fun startImportReturnsPendingAndPreviewDoesNotWriteByDefault() {
        val h=Harness();assertFalse(h.actions.startImport());h.ready();assertTrue(h.actions.startImport())
        assertEquals("EXPORT_REQUEST",h.sent.last().getString("type"));assertTrue(h.sync.state.busy);assertEquals(0,h.saves)
        h.finishExport();assertNotNull(h.schedule.state.pendingImport);assertEquals(0,h.saves)
        assertTrue(h.schedule.confirmImport());assertEquals(1,h.saves);assertNull(h.schedule.state.pendingImport)
    }
    @Test fun explicitlyConfirmedWatchImportUsesTheSameRepository() {
        val h=Harness();h.ready();assertTrue(h.actions.startImport(true));h.finishExport()
        assertEquals(1,h.saves);assertNull(h.schedule.state.pendingImport);assertEquals(9L,h.schedule.state.book.revision)
    }
    @Test fun confirmedWatchImportCannotReplaceAnEditorSaveMadeWhileWaiting() {
        val h=Harness();h.ready();assertTrue(h.actions.startImport(true))
        assertTrue(h.schedule.save(h.schedule.state.book.withSemester("2026-10-01")))
        h.finishExport()
        assertEquals("2026-10-01",h.schedule.state.book.semesterStart)
        assertEquals(1,h.saves)
        assertNotNull("A changed base must retain a new preview, not auto-confirm",h.schedule.state.pendingImport)
        assertTrue(h.schedule.confirmImport());assertEquals(2,h.saves)
    }
    @Test fun startPublishRequiresConfirmationAndConflictsRequireForce() {
        val h=Harness();h.ready(true,"other",true);assertFalse(h.actions.publish(false));assertFalse(h.actions.publish(true))
        assertEquals(listOf("HELLO"),h.sent.map{it.getString("type")})
        assertTrue(h.actions.publish(true,true));assertEquals("BEGIN",h.sent.last().getString("type"));assertTrue(h.sync.state.busy)
        assertFalse(h.actions.publish(true,true));assertEquals(0,h.saves)
    }
    @Test fun abortCancelsTransferAndAnyUnconfirmedPreviewWithoutWriting() {
        val h=Harness();h.ready();assertTrue(h.actions.importDocument(raw));assertNotNull(h.schedule.state.pendingImport)
        assertTrue(h.actions.startImport(true));val old=h.receiver!!;h.actions.abort()
        assertEquals("CANCEL",h.sent.last().getString("type"));assertNull(h.schedule.state.pendingImport);assertEquals(0,h.saves)
        old("{"+Wire.header("READY","")+",\"maxBytes\":8192,\"digest\":\"00000000\",\"sourceRevision\":0,\"localDirty\":false,\"hasData\":false,\"datasetId\":\"\"}")
        assertFalse(h.sync.state.ready);assertEquals(0,h.saves)
    }
    @Test fun coursesReadUsesTheActualSharedRepositoryAndPendingPreview() {
        val h=Harness();assertEquals(PhoneSnapshot.encode(h.schedule.state.book.wireJson()),PhoneSnapshot.encode(h.actions.coursesJson().getJSONObject("document").toString()))
        assertTrue(h.actions.importDocument(raw));assertTrue(h.actions.stateJson().getBoolean("import_pending"));assertEquals(0,h.saves)
    }
    @Test fun coursesWriteValidatesAndOnlyConfirmedWriteMutatesTheSharedRepository() {
        val h=Harness();assertFalse(h.actions.importDocument("{}",true));assertEquals(0,h.saves)
        assertTrue(h.actions.importDocument(raw,false));assertEquals(0,h.saves)
        assertTrue(h.actions.importDocument(raw,true));assertEquals(1,h.saves);assertEquals(2L,h.schedule.state.book.revision)
        h.ready();assertTrue(h.actions.startImport());assertFalse(h.actions.importDocument(raw,true));assertEquals(1,h.saves)
    }
    @Test fun pickupDocumentUsesTheVerySameSharedImportAndConfirmation() {
        val h=Harness();val response=JSONObject(raw).put("code","ok").toString()
        val pickup=PickupClient.parseResponse(response);assertTrue(h.actions.importDocument(pickup,true));assertEquals(1,h.saves)
    }
    @Test fun deviceAndPairingOutputAreObservedNotGuessedOrModelWhitelisted() {
        val h=Harness();assertEquals(0,h.actions.devicesJson().getJSONArray("devices").length());assertFalse(h.actions.devicesJson().getBoolean("observed"))
        assertTrue(h.actions.scan());val listed=h.actions.devicesJson();assertEquals(1,listed.getJSONArray("devices").length())
        assertEquals(peer.id,listed.getJSONArray("devices").getJSONObject(0).getString("device_id"));assertTrue(listed.getBoolean("observed"))
        assertTrue(h.actions.stateJson().getBoolean("permission_granted"));assertFalse(h.actions.stateJson().getBoolean("ready"))
    }
}
