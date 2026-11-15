package com.hcbiu.elcton

/** One immutable publication, stop-and-wait. Only a matching application-level APPLIED completes it. */
class TransferSession(
    val text: String,
    val transferId: String,
    val datasetId: String,
    val revision: Long,
    val baseDigest: String,
    val force: Boolean
) {
    private val chunks = Wire.chunks(text, transferId)
    private var position = 0
    private var retries = 0
    var complete = false
        private set
    var error: String? = null
        private set
    val digest = Wire.crc32(text)
    val acceptedChunks: Int get() = maxOf(0, minOf(position - 1, chunks.size))
    val chunkCount: Int get() = chunks.size

    init {
        require(Regex("[A-Za-z0-9_-]{1,64}").matches(datasetId))
        require(revision > 0 && text.isNotEmpty() && text.length <= 32768)
    }
    val currentMessage: String?
        get() {
            if (complete || error != null) return null
            if (position == 0) return "{" + Wire.header("BEGIN", transferId) +
                ",\"datasetId\":" + Wire.quote(datasetId) + ",\"sourceRevision\":" + revision +
                ",\"baseDigest\":" + Wire.quote(baseDigest) + ",\"force\":" + force +
                ",\"length\":" + text.length + ",\"digest\":" + Wire.quote(digest) + ",\"chunks\":" + chunks.size + "}"
            if (position <= chunks.size) return chunks[position - 1].message
            return "{" + Wire.header("END", transferId) + "}"
        }
    fun transportSucceeded() { /* transport delivery is not application persistence */ }
    fun reply(type: String, id: String, seq: Int, receivedDigest: String, sourceRevision: Long, code: String): Boolean {
        if (id != transferId || complete || error != null) return false
        if (type == "ERROR") { error = code.ifEmpty { "REMOTE_ERROR" }; return true }
        if (type == "ACK" && position <= chunks.size && seq == position - 1) {
            position++; retries = 0; return true
        }
        if (type == "APPLIED" && position == chunks.size + 1 && receivedDigest == digest && sourceRevision == revision) {
            complete = true; return true
        }
        return false
    }
    fun timeout(): Boolean {
        if (complete || error != null) return false
        if (retries < 3) { retries++; return true }
        error = "TIMEOUT"; return false
    }
}
