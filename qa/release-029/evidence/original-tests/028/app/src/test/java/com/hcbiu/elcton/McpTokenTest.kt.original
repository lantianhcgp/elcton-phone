package com.hcbiu.elcton

import org.junit.Assert.*
import org.junit.Test
import java.io.File
import java.lang.reflect.InvocationTargetException
import java.nio.file.Files
import java.nio.file.attribute.PosixFilePermissions

class McpTokenTest {
    private fun load(file: File): String {
        val type = try { Class.forName("com.hcbiu.elcton.McpToken") }
        catch (_: ClassNotFoundException) { throw AssertionError("McpToken implementation missing") }
        return try { type.getMethod("loadOrCreate", File::class.java).invoke(null, file) as String }
        catch (e: InvocationTargetException) { throw e.targetException }
    }

    private fun withDir(block: (File) -> Unit) {
        val dir = Files.createTempDirectory("mcp-token-test-").toFile()
        try { block(dir) } finally { dir.deleteRecursively() }
    }

    @Test fun firstRunCreatesRandomStablePrivateToken() = withDir { dir ->
        val file = File(dir, "mcp.token")
        val value = load(file)
        assertTrue("Expected 32-byte hex token", value.matches(Regex("[0-9a-f]{64}")))
        assertEquals(value, file.readText(Charsets.US_ASCII))
        assertEquals(value, load(file))
        assertEquals(PosixFilePermissions.fromString("rw-------"), Files.getPosixFilePermissions(file.toPath()))
        assertNotEquals(value, load(File(dir, "other.token")))
    }

    @Test fun existingTokenPermissionsAreHardened() = withDir { dir ->
        val file = File(dir, "mcp.token")
        file.writeText("ab".repeat(32))
        Files.setPosixFilePermissions(file.toPath(), PosixFilePermissions.fromString("rw-r--r--"))
        assertEquals("ab".repeat(32), load(file))
        assertEquals(PosixFilePermissions.fromString("rw-------"), Files.getPosixFilePermissions(file.toPath()))
    }

    @Test fun emptyMalformedAndOversizedTokensFailClosed() = withDir { dir ->
        for (bad in listOf("", " ", "ab".repeat(31), "AB".repeat(32), "ab".repeat(32) + "\n", "x".repeat(100000))) {
            val file = File(dir, "mcp.token")
            file.writeText(bad)
            try { load(file); fail("Invalid stored token must not become anonymous authentication") }
            catch (e: Exception) { assertFalse(e.message.orEmpty().contains("mcp.token")) }
            assertEquals(bad, file.readText())
        }
    }

    @Test fun symbolicTokenAndDirectoryAreRejected() = withDir { dir ->
        val other = File(dir, "other").apply { writeText("ab".repeat(32)) }
        val link = File(dir, "mcp.token")
        Files.createSymbolicLink(link.toPath(), other.toPath())
        try { load(link); fail("Token symlink must be rejected") } catch (_: Exception) { }
        assertTrue(link.delete())
        assertTrue(link.mkdir())
        try { load(link); fail("Token directory must be rejected") } catch (_: Exception) { }
    }
}
