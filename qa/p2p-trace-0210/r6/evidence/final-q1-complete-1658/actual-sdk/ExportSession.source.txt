package com.hcbiu.elcton

/** Import is proposed only after a bounded ASCII snapshot fully matches the declared checksum. */
class ExportSession(val id:String) {
    private var length=0
    private var digest=""
    private var chunks=0
    private val buffer=StringBuilder()
    var nextSequence=0; private set
    var sourceRevision=0L; private set
    var result:String?=null; private set
    var error:String?=null; private set
    val initialized:Boolean get() = length>0
    fun meta(peerId:String,size:Int,crc:String,count:Int,revision:Long):Boolean {
        if(peerId!=id||initialized||size !in 1..32768||count !in 1..128||!Regex("[0-9a-f]{8}").matches(crc))return false
        length=size;digest=crc;chunks=count;sourceRevision=revision;return true
    }
    fun chunk(peerId:String,seq:Int,data:String):Boolean {
        if(peerId!=id||!initialized||seq!=nextSequence||result!=null||error!=null||data.isEmpty()||data.any{it.code !in 32..126})return false
        if(buffer.length+data.length>length){error="EXPORT_TOO_LARGE";return false}
        buffer.append(data);nextSequence++
        if(nextSequence==chunks){
            val text=buffer.toString()
            if(text.length!=length||Wire.crc32(text)!=digest)error="CORRUPT_EXPORT" else result=text
        }
        return true
    }
}
