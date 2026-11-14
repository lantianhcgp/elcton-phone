package com.hcbiu.elcton

import java.io.File
import java.nio.ByteBuffer
import java.nio.channels.FileChannel
import java.nio.file.FileAlreadyExistsException
import java.nio.file.Files
import java.nio.file.LinkOption
import java.nio.file.StandardOpenOption
import java.nio.file.attribute.PosixFilePermissions
import java.security.SecureRandom

/** Persistent private credential. Invalid existing files fail closed, never rotate silently. */
object McpToken {
    @JvmStatic @Synchronized
    fun loadOrCreate(file: File): String {
        try {
            val path = file.toPath()
            val parent = path.toAbsolutePath().parent ?: throw IllegalStateException()
            Files.createDirectories(parent)
            if (Files.isSymbolicLink(path)) throw IllegalStateException()
            val privatePermissions = PosixFilePermissions.fromString("rw-------")
            if (!Files.exists(path, LinkOption.NOFOLLOW_LINKS)) {
                val bytes = ByteArray(32).also { SecureRandom().nextBytes(it) }
                val hex = "0123456789abcdef"
                val token = buildString(64) {
                    bytes.forEach { b ->
                        val n = b.toInt() and 255
                        append(hex[n ushr 4]); append(hex[n and 15])
                    }
                }
                try {
                    FileChannel.open(path, setOf(StandardOpenOption.CREATE_NEW, StandardOpenOption.WRITE, LinkOption.NOFOLLOW_LINKS),
                        PosixFilePermissions.asFileAttribute(privatePermissions)).use { channel ->
                        val buffer = ByteBuffer.wrap(token.toByteArray(Charsets.US_ASCII))
                        while (buffer.hasRemaining()) channel.write(buffer)
                        channel.force(true)
                    }
                } catch (_: FileAlreadyExistsException) { /* Another creator won; validate their file. */ }
            }
            if (!Files.isRegularFile(path, LinkOption.NOFOLLOW_LINKS)) throw IllegalStateException()
            Files.setPosixFilePermissions(path, privatePermissions)
            val buffer = ByteBuffer.allocate(65)
            FileChannel.open(path, StandardOpenOption.READ, LinkOption.NOFOLLOW_LINKS).use { channel ->
                while (buffer.hasRemaining() && channel.read(buffer) != -1) { }
            }
            if (buffer.position() != 64) throw IllegalStateException()
            val token = String(buffer.array(), 0, 64, Charsets.US_ASCII)
            if (!token.matches(Regex("[0-9a-f]{64}"))) throw IllegalStateException()
            return token
        } catch (_: Exception) {
            // File names, file contents and credential values must not reach diagnostic output.
            throw IllegalStateException("MCP credential unavailable")
        }
    }
}
