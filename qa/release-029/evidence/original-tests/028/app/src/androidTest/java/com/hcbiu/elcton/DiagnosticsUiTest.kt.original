package com.hcbiu.elcton

import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.graphics.Color
import android.graphics.Rect
import android.system.Os
import androidx.compose.ui.semantics.SemanticsActions
import androidx.compose.ui.semantics.SemanticsProperties
import androidx.compose.ui.test.*
import androidx.compose.ui.test.junit4.createAndroidComposeRule
import androidx.compose.ui.text.TextLayoutResult
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import androidx.test.uiautomator.By
import androidx.test.uiautomator.UiDevice
import org.json.JSONArray
import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import java.io.File
import java.net.InetSocketAddress
import java.net.Socket
import java.security.MessageDigest
import java.util.concurrent.CountDownLatch
import java.util.concurrent.TimeUnit
import kotlin.math.ceil
import kotlin.math.floor
import kotlin.math.sqrt

/** CI emulator only. Every injected error is explicitly SYNTHETIC; no WearEngine action is invoked. */
@RunWith(AndroidJUnit4::class)
class DiagnosticsUiTest {
    @get:Rule val ui = createAndroidComposeRule<MainActivity>()
    private val instrumentation get() = InstrumentationRegistry.getInstrumentation()
    private val device get() = UiDevice.getInstance(instrumentation)
    private val root get() = instrumentation.targetContext.filesDir
    private val directory get() = File(root, "qa-diag-evidence").apply { check(isDirectory || mkdirs()) }
    private val captures = JSONArray()
    private fun hash(file: File) = MessageDigest.getInstance("SHA-256").digest(file.readBytes()).joinToString("") { "%02x".format(it) }
    private fun rect(value: androidx.compose.ui.geometry.Rect) = Rect(floor(value.left).toInt(), floor(value.top).toInt(), ceil(value.right).toInt(), ceil(value.bottom).toInt())
    private fun box(value: Rect) = JSONArray(listOf(value.left, value.top, value.right, value.bottom))
    private fun businessFiles(): Map<String, String?> = listOf("timetable.json", "timetable-last-good.json", "timetable.json.bak", "timetable-last-good.json.bak").associateWith {
        val file = File(root, it)
        if (file.exists()) hash(file) else null
    }
    private fun rpc(token: String, method: String, params: JSONObject? = null): JSONObject {
        val request = JSONObject().put("jsonrpc", "2.0").put("id", 26).put("method", method)
        params?.let { request.put("params", it) }
        val bytes = request.toString().toByteArray(Charsets.UTF_8)
        // Real loopback HTTP without changing the production network-security policy.
        return Socket().use { socket ->
            socket.connect(InetSocketAddress("127.0.0.1", 8766), 5000)
            socket.soTimeout = 5000
            val header = "POST /mcp HTTP/1.1\r\nHost: 127.0.0.1:8766\r\n" +
                "Author" + "ization: " + "Bear" + "er " + token + "\r\n" +
                "Content-Type: application/json\r\nContent-Length: ${bytes.size}\r\nConnection: close\r\n\r\n"
            socket.getOutputStream().apply { write(header.toByteArray(Charsets.US_ASCII)); write(bytes); flush() }
            val reply = socket.getInputStream().readBytes()
            val boundary = "\r\n\r\n".toByteArray(Charsets.US_ASCII)
            val split = (0..reply.size - boundary.size).firstOrNull { index ->
                boundary.indices.all { reply[index + it] == boundary[it] }
            } ?: error("Actual HTTP response has no header/body boundary")
            val headers = reply.copyOfRange(0, split).toString(Charsets.US_ASCII).split("\r\n")
            assertTrue("real Android HTTP status", headers.first().startsWith("HTTP/1.1 200 "))
            val lengths = headers.drop(1).filter { it.substringBefore(":").equals("Content-Length", true) }
            assertEquals("one actual length header", 1, lengths.size)
            val body = reply.copyOfRange(split + boundary.size, reply.size)
            assertEquals("complete actual HTTP body", lengths.single().substringAfter(":").trim().toInt(), body.size)
            val text = body.toString(Charsets.UTF_8)
            assertFalse("no token in HTTP response", text.contains(token))
            val response = JSONObject(text)
            assertEquals("2.0", response.getString("jsonrpc")); assertEquals(26, response.getInt("id"))
            assertFalse("no RPC error", response.has("error"))
            response.getJSONObject("result")
        }
    }
    private fun call(token: String, name: String, arguments: JSONObject = JSONObject()): JSONObject {
        val result = rpc(token, "tools/call", JSONObject().put("name", name).put("arguments", arguments))
        assertFalse("real tool $name succeeds (including Android NIO fs_read)", result.getBoolean("isError"))
        return JSONObject(result.getJSONArray("content").getJSONObject(0).getString("text"))
    }
    private fun pixels(bitmap: Bitmap, area: Rect, step: Int): JSONObject {
        check(!area.isEmpty && area.left >= 0 && area.top >= 0 && area.right <= bitmap.width && area.bottom <= bitmap.height)
        var sum = 0.0; var squared = 0.0; var count = 0; var low = 255.0; var high = 0.0
        for (y in area.top until area.bottom step step) for (x in area.left until area.right step step) {
            val color = bitmap.getPixel(x, y)
            val value = (Color.red(color) + Color.green(color) + Color.blue(color)) / 3.0
            sum += value; squared += value * value; count++; low = minOf(low, value); high = maxOf(high, value)
        }
        val mean = sum / count
        return JSONObject().put("samples", count).put("mean", mean).put("stddev", sqrt(maxOf(0.0, squared / count - mean * mean)))
            .put("minimum", low).put("maximum", high).put("step", step)
    }
    private fun capture(name: String, target: Rect, targetText: String, extra: JSONObject = JSONObject()) {
        ui.waitForIdle()
        val frame = CountDownLatch(1)
        ui.runOnUiThread {
            val decor = ui.activity.window.decorView
            check(decor.isHardwareAccelerated) { "Evidence requires real HWUI" }
            decor.viewTreeObserver.registerFrameCommitCallback { frame.countDown() }; decor.invalidate()
        }
        check(frame.await(5, TimeUnit.SECONDS)) { "No committed screenshot frame: $name" }
        val attempts = File(directory, "attempts").apply { mkdirs() }
        var ready = false
        for (attempt in 1..3) {
            val png = File(attempts, "$name-$attempt.png")
            check(device.takeScreenshot(png)) { "Actual emulator screenshot failed" }
            val bitmap = BitmapFactory.decodeFile(png.absolutePath) ?: error("Invalid screenshot PNG")
            val receipt: JSONObject
            try {
                val full = pixels(bitmap, Rect(0, 0, bitmap.width, bitmap.height), 3)
                val local = pixels(bitmap, target, 1)
                ready = bitmap.width == device.displayWidth && bitmap.height == device.displayHeight &&
                    full.getDouble("mean") > 10.0 && full.getDouble("stddev") > 12.0 &&
                    local.getDouble("stddev") > 8.0 && local.getDouble("maximum") - local.getDouble("minimum") > 45.0
                receipt = JSONObject().put("name", name).put("attempt", attempt).put("pixelReady", ready)
                    .put("targetText", targetText).put("targetBounds", box(target)).put("extra", extra)
                    .put("screenWidth", bitmap.width).put("screenHeight", bitmap.height).put("fullPixels", full)
                    .put("targetPixels", local).put("pngSha256", hash(png))
            } finally { bitmap.recycle() }
            File(attempts, "$name-$attempt.json").writeText(receipt.toString(), Charsets.UTF_8)
            if (ready) {
                png.copyTo(File(directory, "$name.png"), overwrite = true)
                device.dumpWindowHierarchy(File(directory, "$name.xml"))
                File(directory, "$name.json").writeText(receipt.toString(), Charsets.UTF_8)
                captures.put(receipt); break
            }
            ui.waitForIdle()
        }
        assertTrue("semantic target has actual rendered pixels, not a blank frame: $name", ready)
    }
    private fun markerBounds(full: String, marker: String, layout: TextLayoutResult): Rect {
        val node = ui.onNodeWithTag("diagnostics-details", useUnmergedTree = true).fetchSemanticsNode()
        val line = layout.getLineForOffset(full.indexOf(marker).also { check(it >= 0) })
        val position = node.positionInWindow
        val area = rect(androidx.compose.ui.geometry.Rect(position.x + layout.getLineLeft(line), position.y + layout.getLineTop(line),
            position.x + layout.getLineRight(line), position.y + layout.getLineBottom(line)))
        val viewport = rect(ui.onNodeWithTag("diagnostics-scroll", useUnmergedTree = true).fetchSemanticsNode().boundsInWindow)
        assertTrue("complete $marker line inside real scroll viewport", viewport.contains(area))
        // Dialog semantics use dialog-window coordinates, while screencap uses display pixels.
        // Anchor the window offset to the real accessibility title, never a guessed screen center.
        val title = rect(ui.onNodeWithText("连接诊断").fetchSemanticsNode().boundsInWindow)
        val screenTitle = device.findObject(By.pkg("com.hcbiu.elcton").text("连接诊断"))?.visibleBounds
            ?: error("Actual diagnostic dialog title is not visible")
        area.offset(screenTitle.left - title.left, screenTitle.top - title.top)
        return area
    }
    @Test fun passiveRuntimePersistsAndShowsCompleteSyntheticError() {
        val args = InstrumentationRegistry.getArguments()
        check(args.getString("diag_emulator") == "true") { "Only the CI emulator harness may run this suite" }
        val source = args.getString("diag_source_sha") ?: error("Missing exact checkout SHA")
        check(source.matches(Regex("[0-9a-f]{40}")))
        val report = JSONObject().put("passed", false).put("sourceSha", source).put("qaRun", args.getString("diag_run"))
            .put("scope", "real Android emulator; SYNTHETIC errors; no paired watch or WearEngine actions").put("captures", captures)
        val reportFile = File(directory, "report.json")
        reportFile.writeText(report.toString(), Charsets.UTF_8)
        try {
            ui.waitUntil(15000) { ui.onAllNodesWithTag("nav-settings").fetchSemanticsNodes().isNotEmpty() }
            @Suppress("DEPRECATION") val installed = instrumentation.targetContext.packageManager.getPackageInfo("com.hcbiu.elcton", 0)
            assertEquals("0.2.6", installed.versionName); assertEquals(8L, installed.longVersionCode)
            assertEquals(installed.versionName, BuildConfig.VERSION_NAME); assertEquals(installed.longVersionCode, BuildConfig.VERSION_CODE.toLong())
            val runtime = (ui.activity.application as ElctonApplication).diagnostics
            ui.waitUntil(10000) { runtime.read().getJSONObject("mcp").getBoolean("running") }
            val mcp = runtime.read().getJSONObject("mcp")
            assertEquals("127.0.0.1", mcp.getString("host")); assertEquals(8766, mcp.getInt("port")); assertTrue(mcp.getBoolean("readOnly"))
            assertTrue("no startup error", mcp.isNull("startupError"))
            val tokenFile = File(root, "mcp/token")
            val token = tokenFile.readText(Charsets.US_ASCII)
            assertTrue(token.matches(Regex("[0-9a-f]{64}"))); assertEquals(64L, tokenFile.length())
            assertEquals("actual Android token mode 0600", 0x180, Os.stat(tokenFile.absolutePath).st_mode and 0x1ff)
            report.put("packageVersion", installed.versionName).put("packageCode", installed.longVersionCode)
                .put("passiveMcp", mcp).put("tokenBytes", tokenFile.length()).put("tokenMode", "0600").put("token", "REDACTED")
            val before = businessFiles()
            ui.onNodeWithTag("nav-settings").performClick()
            ui.onNodeWithTag("version-capsule").performScrollTo().assertIsDisplayed()
            val versionLabel = "${installed.versionName} · 测试构建"
            ui.onNodeWithText(versionLabel).assertIsDisplayed()
            capture("settings-version", rect(ui.onNodeWithText(versionLabel).fetchSemanticsNode().boundsInWindow), versionLabel)

            val message = "SYNTHETIC-BEGIN\n" + (1..48).joinToString("\n") { "SYNTHETIC line $it: full diagnostic text, no real device result." }
            val error = IllegalStateException(message, IllegalArgumentException("SYNTHETIC-CAUSE\nSYNTHETIC-END"))
            val record = WearErrorRecord.capture(error, "qa.synthetic.instrumentation", System.currentTimeMillis()) { 860026 }
            runtime.record(record)
            val full = record.full
            File(directory, "synthetic-expected.txt").writeText(full, Charsets.UTF_8)
            assertEquals(full, runtime.latestFull())
            assertEquals(full, runtime.errorTail(1).getJSONObject(0).getString("full"))
            ui.waitUntil(10000) {
                runCatching { JSONObject(File(root, "diagnostics/state.json").readText(Charsets.UTF_8)).getJSONObject("latestError").getString("full") == full }.getOrDefault(false)
            }
            val journal = File(root, "diagnostics/wear-errors.jsonl").readLines(Charsets.UTF_8).filter { it.isNotBlank() }
            assertEquals(full, JSONObject(journal.last()).getString("full"))
            assertEquals(2, JSONObject(journal.last()).getJSONArray("causes").length())
            // Recreate the actual Activity. No injection-only product API or reflection into UI state.
            ui.activityRule.scenario.recreate()
            ui.waitUntil(15000) { ui.onAllNodesWithTag("nav-devices").fetchSemanticsNodes().isNotEmpty() }
            assertSame("Application runtime survives Activity recreate", runtime, (ui.activity.application as ElctonApplication).diagnostics)
            ui.onNodeWithTag("nav-devices").performClick()
            ui.onNodeWithTag("diagnostics").performScrollTo().assertIsDisplayed().performClick()
            ui.onNodeWithText("连接诊断").assertIsDisplayed(); ui.onNodeWithText("关闭").assertIsDisplayed()
            val details = ui.onNodeWithTag("diagnostics-details", useUnmergedTree = true)
            assertEquals("full persisted text in real Compose semantics", full, details.fetchSemanticsNode().config[SemanticsProperties.Text].joinToString("") { it.text })
            val layouts = mutableListOf<TextLayoutResult>()
            details.performSemanticsAction(SemanticsActions.GetTextLayoutResult) { assertTrue(it(layouts)) }
            val layout = layouts.single()
            assertEquals(full, layout.layoutInput.text.text)
            assertTrue("long diagnostic has many actual layout lines", layout.lineCount > 48)
            for (line in 0 until layout.lineCount) assertFalse("no ellipsis at line $line", layout.isLineEllipsized(line))
            val scroll = ui.onNodeWithTag("diagnostics-scroll", useUnmergedTree = true)
            val range = scroll.fetchSemanticsNode().config[SemanticsProperties.VerticalScrollAxisRange]
            assertTrue("real diagnostic is scrollable", range.maxValue() > 0f)
            assertEquals(0f, range.value(), 1f)
            capture("diagnostics-head", markerBounds(full, "SYNTHETIC-BEGIN", layout), "SYNTHETIC-BEGIN", JSONObject().put("scroll", range.value()).put("scrollMax", range.maxValue()))
            scroll.performSemanticsAction(SemanticsActions.ScrollBy) { assertTrue(it(0f, range.maxValue())) }
            ui.waitUntil(10000) { val current = scroll.fetchSemanticsNode().config[SemanticsProperties.VerticalScrollAxisRange]; current.value() >= current.maxValue() - 1f }
            val end = scroll.fetchSemanticsNode().config[SemanticsProperties.VerticalScrollAxisRange]
            capture("diagnostics-tail", markerBounds(full, "SYNTHETIC-END", layout), "SYNTHETIC-END", JSONObject().put("scroll", end.value()).put("scrollMax", end.maxValue()))
            ui.onNodeWithText("关闭").assertIsDisplayed().performClick()
            ui.onNodeWithTag("diagnostics-scroll", useUnmergedTree = true).assertDoesNotExist()

            val listed = rpc(token, "tools/list").getJSONArray("tools")
            assertEquals(setOf("error_tail", "diag_read", "version_info", "fs_read"), (0 until listed.length()).map { listed.getJSONObject(it).getString("name") }.toSet())
            val version = call(token, "version_info")
            assertEquals("0.2.6", version.getString("versionName")); assertEquals(8, version.getInt("versionCode"))
            assertEquals("com.hcbiu.elcton", version.getString("packageName"))
            assertEquals(full, call(token, "diag_read").getJSONObject("latestError").getString("full"))
            assertEquals(full, call(token, "error_tail", JSONObject().put("limit", 1)).getJSONArray("errors").getJSONObject(0).getString("full"))
            val stateRead = call(token, "fs_read", JSONObject().put("path", "diagnostics/state.json"))
            val journalRead = call(token, "fs_read", JSONObject().put("path", "diagnostics/wear-errors.jsonl"))
            assertEquals(stateRead.getString("text").toByteArray(Charsets.UTF_8).size, stateRead.getInt("bytes"))
            assertEquals(full, JSONObject(stateRead.getString("text")).getJSONObject("latestError").getString("full"))
            assertEquals(File(root, "diagnostics/wear-errors.jsonl").readText(Charsets.UTF_8), journalRead.getString("text"))
            assertEquals("diagnostics/UI/HTTP must not modify timetable", before, businessFiles())
            report.put("syntheticFullSha256", hash(File(directory, "synthetic-expected.txt"))).put("syntheticChars", full.length)
                .put("causeCount", 2).put("activityRecreated", true).put("fullTextUntruncated", true).put("closeVisibleAndWorks", true)
                .put("androidNioHttpRead", true).put("httpTools", JSONArray(listOf("error_tail", "diag_read", "version_info", "fs_read")))
                .put("businessFilesUnchanged", true).put("passed", true)
        } catch (error: Throwable) {
            report.put("failure", error.javaClass.name + ": " + error.message)
            throw error
        } finally { reportFile.writeText(report.toString(), Charsets.UTF_8) }
    }
}
