package com.hcbiu.elcton

/** SDK callbacks belong to an individual attempt, not merely a publication object. */
class SendAttempts {
    private var serial=0L
    fun issue():Long=++serial
    fun accepts(attempt:Long):Boolean=attempt==serial
    fun invalidate(){serial++}
}
