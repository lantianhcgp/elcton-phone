package com.hcbiu.elcton

import android.app.Activity
import android.content.Context
import android.os.Handler
import android.os.Looper
import com.huawei.wearengine.HiWear
import com.huawei.wearengine.auth.AuthCallback
import com.huawei.wearengine.auth.Permission
import com.huawei.wearengine.device.Device
import com.huawei.wearengine.p2p.Message
import com.huawei.wearengine.p2p.Receiver
import com.huawei.wearengine.p2p.SendCallback
import org.json.JSONObject

/** Actual SDK adapter. Device-reported state and APPLIED are the only success evidence. */
class WearProbe(private val activity: Activity, private val update: (State) -> Unit,
                private val importCandidate: (String,Long) -> Unit) {
    data class State(val status:String="尚未连接手表",val detail:String="通过华为运动健康配对后，查询可用设备。",
        val devices:List<Device> = emptyList(),val selected:String="",val ready:Boolean=false,val busy:Boolean=false,
        val digest:String="",val dirty:Boolean=false,val revision:Long=0,val maxBytes:Int=8192,
        val datasetId:String="",val hasData:Boolean=false,val diagnostic:String="",val lastSuccessAt:Long=0)
    private val handler=Handler(Looper.getMainLooper())
    private val p2p by lazy {HiWear.getP2pClient(activity)}
    private val baselines=activity.getSharedPreferences("device-baselines",Context.MODE_PRIVATE)
    private var state=State()
    private var receiver:Receiver?=null
    private var device:Device?=null
    private var generation=0
    private var timer:Runnable?=null
    private var session:TransferSession?=null
    private var exporting:ExportSession?=null
    private var exportRetries=0
    private var closed=false
    private var awaitingPermission=false
    private var handshakeAttempts=0
    private var awaitingReady=false
    private val sendAttempts=SendAttempts()
    private val total=OperationDeadline()
    private var totalTimer:Runnable?=null
    private fun finishTotal(){totalTimer?.let(handler::removeCallbacks);totalTimer=null;total.clear()}
    private fun beginTotal(message:String){
        finishTotal();total.begin(android.os.SystemClock.elapsedRealtime(),45000)
        val gen=generation
        val run=Runnable{if(!closed&&gen==generation&&total.expired(android.os.SystemClock.elapsedRealtime()))fail(message)}
        totalTimer=run;handler.postDelayed(run,45000)
    }
    private val watchPackage="watchapp.nexus.0zzip"
    // Lite identity: bundleName + '_' + Base64(SEC1 uncompressed certificate EC point), not a cert hash/SPKI.
    private val watchFingerprint="watchapp.nexus.0zzip_BOc6BPXgVZY7Ik7lETcDy6ezKw77Dqm0EDBscNFv9kHcXaW7gXBRQmA8RfLcDvcCLkOSQIsB33zj/s2IS6u5utM="
    private fun publish(s:State){state=s;update(s)}
    private fun main(block:()->Unit):Unit {handler.post{if(!closed&&!activity.isFinishing)block()}}
    private fun cancelTimer(){timer?.let(handler::removeCallbacks);timer=null}
    private fun deadline(ms:Long,block:()->Unit){cancelTimer();val gen=generation;val r=Runnable{if(!closed&&gen==generation)block()};timer=r;handler.postDelayed(r,ms)}
    private fun fail(message:String){
        generation++;sendAttempts.invalidate();cancelTimer();finishTotal();session=null;exporting=null;awaitingPermission=false;awaitingReady=false;unregister()
        publish(state.copy(status="操作未完成",detail=message.take(200),ready=false,busy=false))
    }
    private fun describe(e:Exception):String {
        val raw=UserFacingError.diagnostic(e)
        state=state.copy(diagnostic=raw)
        android.util.Log.w("ElctonWear",raw)
        return UserFacingError.explain(e.message.orEmpty())
    }
    fun authorizeAndScan(){
        if(state.busy)return
        unregister();val gen=++generation
        publish(state.copy(status="检查设备授权",busy=true,ready=false,diagnostic=""))
        deadline(20000){fail("授权检查超时。请打开运动健康，确认已登录并保持手表连接。")}
        try{
            HiWear.getAuthClient(activity).checkPermission(Permission.DEVICE_MANAGER).addOnSuccessListener{granted->main{
                if(gen!=generation)return@main
                if(granted)scan(gen)else{
                    awaitingPermission=true;publish(state.copy(status="等待你确认授权"))
                    deadline(90000){fail("授权未完成，没有查询或传输课表。")}
                    HiWear.getAuthClient(activity).requestPermission(object:AuthCallback{
                        override fun onOk(permissions:Array<Permission>)=main{
                            if(gen==generation){awaitingPermission=false
                                if(permissions.any{it.name==Permission.DEVICE_MANAGER.name})scan(gen) else fail("设备权限未获准，没有传输课表。")}
                        }
                        override fun onCancel()=main{if(gen==generation)fail("已取消授权，没有查询或传输课表。")}
                    },Permission.DEVICE_MANAGER).addOnFailureListener{e->main{if(gen==generation)fail(describe(e))}}
                }
            }}.addOnFailureListener{e->main{if(gen==generation)fail(describe(e))}}
        }catch(e:Exception){fail(describe(e))}
    }
    private fun scan(gen:Int){
        publish(state.copy(status="查询配对设备",busy=true))
        deadline(15000){fail("设备查询超时，请检查运动健康的连接状态。")}
        try{HiWear.getDeviceClient(activity).commonDevice.addOnSuccessListener{found->main{
            if(gen!=generation)return@main
            cancelTimer();val list=found.orEmpty()
            publish(state.copy(status=if(list.isEmpty())"未找到可用设备" else "选择要同步的手表",
                detail=if(list.isEmpty())"确认运动健康已配对且设备支持应用间通信。" else "设备按实际通信能力判断，不限定 FIT3 型号。",devices=list,busy=false))
        }}.addOnFailureListener{e->main{if(gen==generation)fail(describe(e))}}}catch(e:Exception){fail(describe(e))}
    }
    fun connect(selected:Device){
        if(state.busy)return
        if(!DevicePolicy.canAttemptSync(selected.isConnected,selected.p2pCapability,Device.DEVICE_CAPABILITY_SUPPORT,Device.DEVICE_CAPABILITY_NOT_SUPPORT)){
            fail("设备未连接，或明确不支持应用间通信。");return
        }
        unregister();val gen=++generation
        publish(state.copy(status="检查配套手表应用",selected=selected.uuid.orEmpty(),busy=true,ready=false,dirty=false,datasetId="",hasData=false))
        deadline(15000){fail("检查手表应用超时，请确认运动健康仍连接。")}
        try{
            p2p.setPeerPkgName(watchPackage).setPeerFingerPrint(watchFingerprint)
            p2p.isAppInstalled(selected,watchPackage).addOnSuccessListener{installed->main{
                if(gen!=generation)return@main
                if(!installed){fail("这台手表没有安装匹配的课程表应用。不同系统运行时需要对应安装包，不能强装 Lite 包。");return@main}
                val callback=Receiver{message->main{
                    if(gen!=generation||message.type!=Message.MESSAGE_TYPE_DATA)return@main
                    val bytes=message.data?:return@main
                    if(bytes.size<=1024 && bytes.all{it.toInt() in 32..126})onMessage(bytes.toString(Charsets.US_ASCII))
                }}
                receiver=callback;device=selected
                deadline(15000){fail("接收器注册超时，未发送课表。")}
                p2p.registerReceiver(selected,callback).addOnSuccessListener{handler.post{
                    if(closed||activity.isFinishing||gen!=generation){try{p2p.unregisterReceiver(callback)}catch(_:Exception){};return@post}
                    handshakeAttempts=0;awaitingReady=true
                    publish(state.copy(status="等待手表准备",detail="可在手表进入：周视图 → 同步 → 开始接收。手机正在尝试检测对端。"))
                    // Foreground receive page only; automatic peer wake is not yet verified.
                    hello()
                }}.addOnFailureListener{e->main{if(gen==generation)fail(describe(e))}}
            }}.addOnFailureListener{e->main{if(gen==generation)fail(describe(e))}}
        }catch(e:Exception){fail(describe(e))}
    }
    private fun hello(){
        if(device==null){fail("请先连接设备。");return}
        send("{"+Wire.header("HELLO","")+"}")
        deadline(5000){if(++handshakeAttempts<=3)hello()else fail("未收到手表准备回执。请进入手表同步页并点开始接收；还没有发送课表。")}
    }
    private fun onMessage(raw:String){
        val m=PacketIngress.watch(raw)?:return
        val type=m.optString("type")
        val export=exporting
        if(export!=null){
            if(m.optString("transferId")!=export.id)return
            if(type=="ERROR"){fail("手表导出失败：${m.optString("code")}，手机课表没有改变。");return}
            if(type=="EXPORT_META"){
                if(!export.meta(export.id,m.optInt("length"),m.optString("digest"),m.optInt("chunks"),m.optLong("sourceRevision")))return
                exportRetries=0;requestExportPacket();return
            }
            if(type=="EXPORT_CHUNK"){
                if(!export.chunk(export.id,m.optInt("seq",-1),m.optString("data")))return
                cancelTimer();exportRetries=0
                if(export.error!=null){fail("手表导出内容校验失败，手机旧课表保留。");return}
                val result=export.result
                if(result!=null){
                    val validated=try{PhoneSnapshot.encode(result)}catch(e:Exception){fail("手表导出格式无效：${UserFacingError.validation(e.message)}");return}
                    finishTotal();sendAttempts.invalidate()
                    send("{"+Wire.header("EXPORT_DONE",export.id)+"}",reportFailure=false);exporting=null
                    publish(state.copy(status="手表课表已取回",detail="请在导入预览中决定是否替换手机课表。",busy=false))
                    importCandidate(validated,export.sourceRevision)
                }else requestExportPacket()
                return
            }
            return
        }
        if(type=="READY"&&session==null&&awaitingReady){
            awaitingReady=false;sendAttempts.invalidate()
            val budget=m.optInt("maxBytes",0)
            if(budget !in 1..32768){fail("对端能力信息无效，未发送课表。");return}
            cancelTimer()
            publish(state.copy(status="手表已准备",detail="可以同步手机课表，或先导入手表已有课表。",ready=true,busy=false,
                digest=m.optString("digest"),dirty=m.optBoolean("localDirty"),revision=m.optLong("sourceRevision"),maxBytes=budget,
                datasetId=m.optString("datasetId"),hasData=m.optBoolean("hasData"),
                lastSuccessAt=baselines.getLong(state.selected+".at",0)))
            return
        }
        val current=session?:return
        if(!current.reply(type,m.optString("transferId"),m.optInt("seq",-99),m.optString("digest"),m.optLong("sourceRevision"),m.optString("code")))return
        cancelTimer();sendAttempts.invalidate()
        if(current.complete){
            finishTotal()
            session=null
            val now=System.currentTimeMillis()
            baselines.edit().putString(state.selected+".dataset",current.datasetId).putString(state.selected+".digest",current.digest)
                .putLong(state.selected+".revision",current.revision).putLong(state.selected+".at",now).apply()
            publish(state.copy(status="同步成功",detail="手表已保存并读回确认。",busy=false,digest=current.digest,dirty=false,
                revision=current.revision,datasetId=current.datasetId,hasData=true,lastSuccessAt=now))
        }else if(current.error!=null)fail("手表未确认本次提交（${current.error}）。请重新连接核对最终课表，不把取消或发送回执当作回滚证据。")else transmitCurrent()
    }
    fun publishSnapshot(text:String,force:Boolean,datasetId:String,revision:Long){
        if(!state.ready||state.busy||device==null)return
        val validated=try{PhoneSnapshot.encode(text)}catch(e:Exception){fail(UserFacingError.validation(e.message));return}
        if(validated.length>state.maxBytes){fail("课表超出当前手表的安全接收容量，未截断或发送。请查看兼容报告。");return}
        if(state.datasetId==datasetId&&!state.dirty&&state.digest==Wire.crc32(validated)){
            publish(state.copy(status="已是最新课表",detail="手表内容与手机一致，无需重复写入。"));return
        }
        try{session=TransferSession(validated,"t-"+System.currentTimeMillis().toString(36),datasetId,maxOf(1L,revision),state.digest,force)
            beginTotal("同步总时限已到。请重新连接核对手表最终版本；未把发送成功当作保存成功。")
            publish(state.copy(status="正在同步",detail="等待手表确认接收，旧课表尚未替换。",busy=true));transmitCurrent()
        }catch(e:Exception){fail(UserFacingError.validation(e.message))}
    }
    private fun transmitCurrent(){
        val current=session?:return
        publish(state.copy(status=if(current.acceptedChunks==current.chunkCount)"正在校验保存" else "正在同步",
            detail="已确认 ${current.acceptedChunks}/${current.chunkCount} 包；收到保存回执才算完成。"))
        current.currentMessage?.let{send(it)}
        deadline(5000){if(session===current){if(current.timeout())transmitCurrent()else fail("保存回执超时。重新连接可核对最终版本，未把发送成功当作保存成功。")}}
    }
    fun requestExport(){
        if(!state.ready||state.busy||device==null)return
        exporting=ExportSession("e-"+System.currentTimeMillis().toString(36));exportRetries=0
        beginTotal("回传总时限已到，手机课表未自动改变。请重新连接再取回。")
        publish(state.copy(status="从手表读取课表",detail="手机已有课表不会自动替换。",busy=true))
        requestExportPacket()
    }
    private fun requestExportPacket(){
        val export=exporting?:return
        val type=if(export.initialized)"EXPORT_NEXT" else "EXPORT_REQUEST"
        send("{"+Wire.header(type,export.id)+(if(export.initialized)",\"seq\":"+export.nextSequence else "")+"}")
        deadline(5000){if(exporting===export){if(exportRetries++<3)requestExportPacket()else fail("手表回传超时，手机课表未改变。")}}
    }
    private fun send(text:String,reportFailure:Boolean=true){
        val peer=device?:return;val gen=generation;val attempt=sendAttempts.issue()
        if(text.length>1024||text.any{it.code !in 32..126}){if(reportFailure)fail("消息超出传输上限，未发送。");return}
        fun accepts()=gen==generation&&sendAttempts.accepts(attempt)
        try{p2p.send(peer,Message.Builder().setPayload(text.toByteArray(Charsets.US_ASCII)).build(),object:SendCallback{
            override fun onSendResult(code:Int)=main{
                if(!accepts())return@main
                if(code!=207){if(reportFailure)fail("Wear Engine 发送失败（$code），没有成功保存证据。")}else session?.transportSucceeded()
            }
            override fun onSendProgress(progress:Long){}
        }).addOnFailureListener{e->main{if(reportFailure&&accepts())fail(describe(e))}}
        }catch(e:Exception){if(reportFailure&&accepts())fail(describe(e))}
    }
    fun cancel(){
        val id=session?.transferId?:exporting?.id
        if(id!=null)send("{"+Wire.header("CANCEL",id)+"}",reportFailure=false)
        generation++;sendAttempts.invalidate();cancelTimer();finishTotal();session=null;exporting=null;awaitingPermission=false;awaitingReady=false;unregister()
        publish(state.copy(status="已断开",detail="已停止等待回执；若已进入保存阶段，请重新连接核对最终课表。手机不会自动导入或合并。",busy=false,ready=false))
    }
    private fun unregister(){receiver?.let{try{p2p.unregisterReceiver(it)}catch(_:Exception){}};receiver=null;device=null}
    fun onBackground(){if(!awaitingPermission)cancel()}
    fun close(){cancel();closed=true}
}
