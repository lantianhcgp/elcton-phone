package com.hcbiu.elcton

import java.math.BigInteger
import java.nio.file.Files
import java.nio.file.Path
import java.nio.file.Paths
import java.security.MessageDigest
import java.security.cert.CertificateFactory
import java.security.interfaces.ECPublicKey
import java.util.Base64
import javax.xml.parsers.DocumentBuilderFactory
import org.junit.Assert.*
import org.junit.Test

/** Reads the real configuration and public certificate; no Android/Wear Engine mock. */
class WearEngineConfigTest {
    private val root: Path = generateSequence(Paths.get("").toAbsolutePath()) { it.parent }
        .first { Files.isRegularFile(it.resolve("app/src/main/AndroidManifest.xml")) }
    private val manifest = root.resolve("app/src/main/AndroidManifest.xml")
    private val probe = root.resolve("app/src/main/java/com/hcbiu/elcton/WearProbe.kt").toFile().readText(Charsets.UTF_8)
    private val certificate = Files.newInputStream(root.resolve("app/src/test/resources/watch-development-cert.pem")).use {
        CertificateFactory.getInstance("X.509").generateCertificate(it)
    }
    private val publicKey = certificate.publicKey as ECPublicKey
    private fun constant(name: String): String = Regex("private val $name\\s*=\\s*\"([^\"]+)\"")
        .find(probe)!!.groupValues[1]
    private fun coordinate(value: BigInteger): ByteArray {
        val signed = value.toByteArray()
        val magnitude = if (signed.size == 33 && signed[0] == 0.toByte()) signed.copyOfRange(1, 33) else signed
        require(magnitude.size <= 32)
        return ByteArray(32 - magnitude.size) + magnitude
    }
    // SEC1 uncompressed EC point: 0x04 || unsigned fixed-width X || unsigned fixed-width Y.
    private fun rawPoint() = byteArrayOf(4) + coordinate(publicKey.w.affineX) + coordinate(publicKey.w.affineY)
    private fun fingerprint() = constant("watchPackage") + "_" + Base64.getEncoder().encodeToString(rawPoint())
    private fun sha256(bytes: ByteArray) = MessageDigest.getInstance("SHA-256").digest(bytes)
        .joinToString("") { "%02x".format(it.toInt() and 255) }

    @Test fun scopeAuthenticationHasInternetPermission() {
        val document = DocumentBuilderFactory.newInstance().apply { isNamespaceAware = true }
            .newDocumentBuilder().parse(manifest.toFile())
        val permissions = document.getElementsByTagName("uses-permission")
        val internetCount = (0 until permissions.length).count {
            permissions.item(it).attributes.getNamedItemNS("http://schemas.android.com/apk/res/android", "name")
                ?.nodeValue == "android.permission.INTERNET"
        }
        assertEquals("Wear Engine cloud Scope authentication requires INTERNET", 1, internetCount)
    }

    @Test fun litePeerFingerprintUsesBundleAndRawPublicKey() {
        assertEquals("Lite peer identity is not certificate SHA256 or SPKI DER", fingerprint(), constant("watchFingerprint"))
        assertTrue(probe.contains("setPeerPkgName(watchPackage).setPeerFingerPrint(watchFingerprint)"))
    }

    @Test fun peerFingerprintDecodesToActualCertificateEcPoint() {
        val value = constant("watchFingerprint")
        assertTrue("Lite fingerprint must include bundle prefix", value.startsWith(constant("watchPackage") + "_"))
        assertArrayEquals(rawPoint(), Base64.getDecoder().decode(value.substringAfter('_')))
    }

    @Test fun publicCertificateAndRawPointArePinned() {
        assertEquals("8926257d1bd9ff653dcd84100d53cbbabbd39371fdda5126dfb37429e55c67be", sha256(certificate.encoded))
        assertEquals(256, publicKey.params.curve.field.fieldSize)
        assertEquals(65, rawPoint().size)
        assertEquals(4, rawPoint()[0].toInt())
        assertEquals("BOc6BPXgVZY7Ik7lETcDy6ezKw77Dqm0EDBscNFv9kHcXaW7gXBRQmA8RfLcDvcCLkOSQIsB33zj/s2IS6u5utM=", Base64.getEncoder().encodeToString(rawPoint()))
    }

    @Test fun fingerprintIsNeitherSpkiNorAsciiHexEncoding() {
        assertEquals("e57bbc00ad8f928e6f9d24d0a8453fea9edd865b6b44216e8799551610cdf742", sha256(publicKey.encoded))
        assertNotEquals(constant("watchPackage") + "_" + Base64.getEncoder().encodeToString(publicKey.encoded), constant("watchFingerprint"))
        val hex = rawPoint().joinToString("") { "%02x".format(it.toInt() and 255) }
        assertNotEquals(constant("watchPackage") + "_" + Base64.getEncoder().encodeToString(hex.toByteArray(Charsets.US_ASCII)), constant("watchFingerprint"))
        assertTrue(fingerprint().length <= 127)
    }

    @Test fun unrelatedWearEngineIntegrationIsPreserved() {
        assertEquals("watchapp.nexus.0zzip", constant("watchPackage"))
        val xml = manifest.toFile().readText(Charsets.UTF_8)
        assertTrue(xml.contains("android:value=\"appid=118599721\""))
        assertTrue(xml.contains("android:name=\"com.huawei.health\""))
        assertTrue(root.resolve("app/build.gradle.kts").toFile().readText(Charsets.UTF_8).contains("com.huawei.hms:wearengine:5.0.3.301"))
    }
}
