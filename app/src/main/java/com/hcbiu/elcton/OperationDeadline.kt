package com.hcbiu.elcton

/** Based on a monotonic clock; progress never changes the original deadline. */
class OperationDeadline {
    private var end:Long?=null
    fun begin(now:Long,budget:Long){require(budget>0&&now>=0&&now<=Long.MAX_VALUE-budget);end=now+budget}
    fun expired(now:Long):Boolean=end?.let{now>=it}?:false
    fun clear(){end=null}
}
