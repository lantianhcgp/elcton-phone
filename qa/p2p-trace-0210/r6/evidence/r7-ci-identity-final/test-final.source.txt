package com.hcbiu.elcton

import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Test

/** Actual SyncEngine vs frozen baseline source compiled in a separate class; HOST only. */
class P2pTraceEngineTest {
    private fun required(name:String):Class<*> = runCatching{Class.forName("com.hcbiu.elcton.$name")}.getOrNull().also{assertNotNull("Missing $name observation/oracle seam",it)}!!
    private fun trace(clock:Clock,broken:Boolean=false):Any = required("P2pTrace").getConstructor(String::class.java,kotlin.jvm.functions.Function0::class.java,kotlin.jvm.functions.Function0::class.java)
        .newInstance("host-test",{ 700L+clock.time },{ if(broken) throw AssertionError("clock sentinel") else clock.time })
    private fun read(t:Any):JSONObject = t.javaClass.getMethod("read",Long::class.javaPrimitiveType,Int::class.javaPrimitiveType).invoke(t,0L,128) as JSONObject
    private fun stages(t:Any):List<String> { val a=read(t).getJSONArray("events");return (0 until a.length()).map{a.getJSONObject(it).getString("stage")} }
    class Clock(val calls:MutableList<String>):SyncScheduler {
        data class Task(val at:Long,val order:Int,val f:()->Unit,var cancelled:Boolean=false)
        var time=0L;var serial=0;val tasks=mutableListOf<Task>()
        override fun post(block:()->Unit){calls+="post@$time";tasks+=Task(time,++serial,block)}
        override fun after(ms:Long,block:()->Unit):SyncCancellation{calls+="after:$ms@$time";val t=Task(time+ms,++serial,block);tasks+=t;return SyncCancellation{calls+="cancel:${t.at}";t.cancelled=true}}
        override fun now():Long {calls+="now@$time";return time}
        override fun wallTime():Long{calls+="wall@$time";return 700L+time}
        fun advance(ms:Long){val end=time+ms;while(true){val t=tasks.filter{!it.cancelled&&it.at<=end}.minWithOrNull(compareBy({it.at},{it.order}))?:break;tasks.remove(t);time=t.at;t.f()};time=end}
    }
    class Transport(val calls:MutableList<String>,val clock:Clock):SyncTransport {
        val peer=SyncDevice("PRIVATE_UUID","PRIVATE_NAME","PRIVATE_MODEL",true,0)
        var installing=true;var registering=true;var throwSend=false
        var receiver:((String)->Unit)?=null;var regOk:(()->Unit)?=null;var regFail:((String)->Unit)?=null
        var result:((Int)->Unit)?=null;var sendFail:((String)->Unit)?=null
        override fun checkPermission(success:(Boolean)->Unit,failure:(String)->Unit){calls+="check";success(true)}
        override fun requestPermission(success:(Boolean)->Unit,failure:(String)->Unit):Boolean{calls+="request";return false}
        override fun scan(success:(List<SyncDevice>)->Unit,failure:(String)->Unit){calls+="scan";success(listOf(peer))}
        override fun installed(device:SyncDevice,success:(Boolean)->Unit,failure:(String)->Unit){assertSame(peer,device);calls+="installed";if(installing)success(true)}
        override fun register(device:SyncDevice,message:(String)->Unit,success:()->Unit,failure:(String)->Unit){assertSame(peer,device);calls+="register";receiver=message;regOk=success;regFail=failure;if(registering)success()}
        override fun unregister(){calls+="unregister"}
        override fun send(device:SyncDevice,text:String,result:(Int)->Unit,failure:(String)->Unit){assertSame(peer,device);calls+="send@$${clock.time}:$text";this.result=result;sendFail=failure;if(throwSend)throw IllegalStateException("same business sentinel")}
    }
    inner class Harness(name:String,observed:Boolean,broken:Boolean=false) {
        val calls=mutableListOf<String>();val clock=Clock(calls);val transport=Transport(calls,clock);val updates=mutableListOf<String>()
        val baselines=object:SyncBaselines{override fun lastSuccess(deviceId:String):Long{calls+="lastSuccess:$deviceId";return 123L};override fun save(deviceId:String,datasetId:String,digest:String,revision:Long,at:Long){calls+="save:$deviceId:$datasetId:$digest:$revision:$at"}}
        val engine=required(name).constructors.single{it.parameterCount==5}.newInstance(transport,clock,baselines,{s:Any->updates+=s.toString()},{s:String,r:Long->calls+="import:$s:$r"})
        val trace=if(observed)trace(clock,broken).also{t->engine.javaClass.methods.firstOrNull{it.name=="attachTrace"&&it.parameterCount==1}.also{assertNotNull("Missing attachTrace stage support",it)}!!.invoke(engine,t)}else null
        fun action(name:String,vararg args:Any):Any?=engine.javaClass.methods.single{it.name==name&&it.parameterCount==args.size}.invoke(engine,*args)
        fun start(){assertEquals(true,action("authorizeAndScan",false));clock.advance(0);assertEquals(true,action("connect",transport.peer.id));clock.advance(0)}
    }
    private fun compare(mode:String,broken:Boolean=false):Harness {
        val base=Harness("P2pTraceBaselineEngine",false);val seen=Harness("SyncEngine",true,broken)
        for(h in listOf(base,seen)) {
            if(mode=="install")h.transport.installing=false
            if(mode=="reg"||mode=="lateReg")h.transport.registering=false
            if(mode=="syncThrow")h.transport.throwSend=true
            h.start()
            when(mode){
                "ready"->{h.transport.receiver!!(READY);h.clock.advance(0);h.transport.result!!(206);h.transport.result!!(207);h.clock.advance(0);h.clock.advance(20000)}
                "reject"->{for(raw in listOf(READY.replace("watch","phone"),READY.replace("\"version\":1","\"version\":2"),"X".repeat(1025),"中",READY.replace("8192","0"))){h.transport.receiver!!(raw);h.clock.advance(0)};h.clock.advance(20000)}
                "resultFail"->{h.clock.advance(1000);h.transport.result!!(206);h.clock.advance(0);h.transport.result!!(207);h.transport.sendFail!!("late failure");h.clock.advance(40000)}
                "cancel"->{h.clock.advance(1000);h.action("cancel");h.transport.result!!(206);h.transport.receiver!!(READY);h.clock.advance(40000)}
                "lateReg"->{h.action("cancel");h.transport.regOk!!();h.transport.regFail!!("late registration");h.clock.advance(40000)}
                "close"->{h.action("close");h.action("close");h.transport.result!!(207);h.clock.advance(40000)}
                else->h.clock.advance(20000)
            }
        }
        assertEquals("Business calls/order/bytes differ: $mode",base.calls,seen.calls);assertEquals("Business updates differ: $mode",base.updates,seen.updates)
        return seen
    }
    @Test fun originalHelloDeadlinesAndRetryStages(){val h=compare("timeout");val a=read(h.trace!!).getJSONArray("events");val retry=(0 until a.length()).map{a.getJSONObject(it)}.filter{it.getString("stage")=="HELLO_RETRY"};assertEquals(listOf(5000L,10000L,15000L),retry.map{it.getLong("elapsedMs")});assertEquals(20000L,(0 until a.length()).map{a.getJSONObject(it)}.single{it.getString("stage")=="READY_TIMEOUT"}.getLong("elapsedMs"));assertEquals(4,h.calls.count{it.startsWith("send@")} )}
    @Test fun installAndRegistrationTimeoutAreNotReadyTimeout(){for(mode in listOf("install","reg")){val h=compare(mode);assertTrue(stages(h.trace!!).contains(if(mode=="install")"INSTALL_TIMEOUT" else "REG_TIMEOUT"));assertFalse(stages(h.trace).contains("READY_TIMEOUT"))}}
    @Test fun validReadyAcceptedExactlyOnceAndLateResultsRemainVisible(){val h=compare("ready");assertEquals(1,stages(h.trace!!).count{it=="READY_ACCEPT"});assertEquals(2,stages(h.trace).count{it=="SEND_RESULT"});assertFalse(read(h.trace).toString().contains("PRIVATE_"))}
    @Test fun originalRejectsAndEarlyFailuresCancelCloseAndLateCallbacksHaveZeroDrift(){for(mode in listOf("reject","resultFail","cancel","lateReg","close","syncThrow"))compare(mode)}
    @Test fun hostileDiagnosticClockHasZeroBusinessDrift(){compare("timeout",true);compare("ready",true);compare("syncThrow",true)}
    companion object{const val READY="{\"protocol\":\"elcton.sync\",\"version\":1,\"sender\":\"watch\",\"type\":\"READY\",\"transferId\":\"\",\"maxBytes\":8192,\"sourceRevision\":0,\"datasetId\":\"\",\"digest\":\"\",\"localDirty\":false,\"hasData\":false}"}
}
