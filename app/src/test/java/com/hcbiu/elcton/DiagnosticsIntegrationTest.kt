package com.hcbiu.elcton

import java.io.File
import org.junit.Assert.*
import org.junit.Test

/** Scope/integration audit, not a claim that hardware SDK calls succeed. */
class DiagnosticsIntegrationTest {
    private fun root(): File = generateSequence(File("").absoluteFile) { it.parentFile }
        .first { File(it, "app/src/main/AndroidManifest.xml").isFile }
    private fun source(name: String) = File(root(), "app/src/main/java/com/hcbiu/elcton/$name").readText(Charsets.UTF_8)

    @Test fun diagnosticHttpUsesRawSocketWithoutRelaxingProductionCleartextPolicy() {
        val test = File(root(), "app/src/androidTest/java/com/hcbiu/elcton/DiagnosticsUiTest.kt").readText()
        assertFalse("target34 HttpURLConnection blocks declared cleartext=false", test.contains("HttpURLConnection"))
        assertTrue(test.contains("Socket().use"))
        assertTrue(File(root(), "app/src/main/AndroidManifest.xml").readText().contains("android:usesCleartextTraffic=\"false\""))
    }

    @Test fun versionCapsuleUsesActualBuildConfigAndCodeEight() {
        val main = source("MainActivity.kt")
        val gradle = File(root(), "app/build.gradle.kts").readText(Charsets.UTF_8)
        assertTrue("Version capsule must use the installed build version", main.contains("BuildConfig.VERSION_NAME"))
        assertFalse(main.contains("0.2.4 · 测试构建"))
        assertTrue(gradle.contains("versionCode = 8"))
        assertTrue(gradle.contains("versionName = \"0.2.6\""))
        assertTrue(gradle.contains("buildConfig = true"))
    }

    @Test fun sdkErrorOutletRecordsFullMessageCodeAndExactFailurePhase() {
        val probe = source("WearProbe.kt")
        assertTrue("SDK errorCode/message must survive the describe outlet", probe.contains("WearErrorRecord.capture"))
        assertTrue(probe.contains("WearEngineException"))
        assertTrue(probe.contains(".errorCode"))
        assertTrue(probe.contains("android.util.Log.w(\"ElctonWear\",raw)"))
        assertTrue(probe.contains("diagnostics?.record(record)"))
        for (phase in listOf("checkPermission", "requestPermission", "getCommonDevice", "registerReceiver", "isAppInstalled", "p2p.send")) {
            assertTrue("Exact SDK phase is missing: $phase", probe.contains("describe(e,\"$phase\")"))
        }
        assertFalse(probe.contains("UserFacingError.diagnostic(e)"))
        assertTrue(probe.contains("WearErrorRecord.captureWithMessage"))
        assertTrue(probe.contains("val message=e.message"))
        assertTrue("Observation construction must not interrupt the original failure return", probe.contains("catch(observationError:Exception)"))
        assertTrue(probe.contains("return UserFacingError.explain(message.orEmpty())"))
    }

    @Test fun fullDiagnosisIsScrollableAndOnlyApplicationStartsPassiveMcp() {
        val main = source("MainActivity.kt")
        assertTrue(main.contains("testTag(\"diagnostics-scroll\")"))
        assertTrue(main.contains("testTag(\"diagnostics-details\")"))
        assertTrue(main.contains("heightIn(max=300.dp)"))
        val manifest = File(root(), "app/src/main/AndroidManifest.xml").readText(Charsets.UTF_8)
        assertTrue(manifest.contains("android:name=\".ElctonApplication\""))
        assertFalse(manifest.contains("<service"))
        assertFalse(manifest.contains("FOREGROUND_SERVICE"))
        assertTrue(source("ElctonApplication.kt").contains("diagnostics.start()"))
    }
}
