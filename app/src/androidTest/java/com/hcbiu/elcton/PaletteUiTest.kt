package com.hcbiu.elcton

import android.content.Context
import android.content.res.Configuration
import android.graphics.BitmapFactory
import android.os.Process
import android.view.View
import android.view.WindowInsets
import android.view.inputmethod.InputMethodManager
import androidx.compose.ui.test.*
import androidx.compose.ui.test.junit4.createAndroidComposeRule
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import androidx.test.uiautomator.UiDevice
import org.json.JSONArray
import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import java.io.File
import java.io.FileInputStream
import java.security.MessageDigest
import java.util.concurrent.CountDownLatch
import java.util.concurrent.TimeUnit
import javax.xml.parsers.DocumentBuilderFactory

/** Real presentation choices, business-hash preservation and host-cold processes. Emulator-only fixture. */
@RunWith(AndroidJUnit4::class)
class PaletteUiTest {
    @get:Rule val ui = createAndroidComposeRule<MainActivity>()
    private val instrumentation get() = InstrumentationRegistry.getInstrumentation()
    private val device get() = UiDevice.getInstance(instrumentation)
    private val args get() = InstrumentationRegistry.getArguments()
    private val phase get() = args.getString("palette_phase")!!
    private val navigationMode get() = args.getString("navigation_mode")!!
    private val qaRun get() = args.getString("palette_run")!!.also { java.util.UUID.fromString(it) }
    private val directory get() = File(instrumentation.targetContext.filesDir,"qa-palette-evidence/$qaRun").apply {
        check(isDirectory || mkdirs())
    }
    private val prefs get() = instrumentation.targetContext.getSharedPreferences("ui-theme",Context.MODE_PRIVATE)
    private val palettes = listOf("PURPLE","BLUE","GREEN","TEAL","ORANGE","PINK")
    private val states = palettes.flatMap { p -> listOf(p to "LIGHT", p to "DARK") }
    private fun mode() = prefs.getString("mode","LIGHT")!!
    private fun palette() = prefs.getString("palette","PURPLE")!!
    private fun dark() = if(mode()=="SYSTEM") systemDark() else mode()=="DARK"
    private fun systemDark() = ui.activity.resources.configuration.uiMode and Configuration.UI_MODE_NIGHT_MASK == Configuration.UI_MODE_NIGHT_YES
    private fun hash(file:File) = MessageDigest.getInstance("SHA-256").digest(file.readBytes()).joinToString("") { "%02x".format(it) }
    private fun businessHashes() = JSONObject().apply {
        for(name in listOf("timetable.json","timetable-last-good.json","timetable.json.bak","timetable-last-good.json.bak")) {
            val file=File(instrumentation.targetContext.filesDir,name)
            put(name,if(file.isFile)hash(file) else "ABSENT")
        }
    }
    private fun shell(command:String) = instrumentation.uiAutomation.executeShellCommand(command).use {
        FileInputStream(it.fileDescriptor).readBytes().toString(Charsets.UTF_8).trim()
    }
    private fun bounds(tag:String, unmerged:Boolean=false):JSONArray? = ui.onAllNodesWithTag(tag,useUnmergedTree=unmerged).fetchSemanticsNodes().firstOrNull()?.boundsInWindow?.let {
        JSONArray(listOf(it.left,it.top,it.right,it.bottom))
    }
    private fun selected(tag:String):Boolean = ui.onAllNodesWithTag(tag).fetchSemanticsNodes().firstOrNull()?.config?.getOrElse(androidx.compose.ui.semantics.SemanticsProperties.Selected) { false } ?: false
    private fun currentState(scene:String):JSONObject {
        val result=JSONObject().apply {
            put("scene",scene);put("palette",palette());put("mode",mode());put("pid",Process.myPid());put("qaRun",qaRun)
            put("systemDark",systemDark());put("navigationMode",navigationMode)
            put("screenWidth",device.displayWidth);put("screenHeight",device.displayHeight)
            put("density",ui.activity.resources.displayMetrics.density)
            val nav=ui.onNodeWithTag("nav-week").fetchSemanticsNode().boundsInWindow
            put("navigationTop",nav.top);put("navigationBottom",nav.bottom)
            val options=JSONObject()
            for(p in palettes) bounds("palette-${p.lowercase()}")?.let {
                options.put(p,JSONObject().put("bounds",it).put("selected",selected("palette-${p.lowercase()}"))
                    .put("previewBounds",bounds("palette-preview-${p.lowercase()}",true)?:JSONObject.NULL)
                    .put("labelBounds",bounds("palette-label-${p.lowercase()}",true)?:JSONObject.NULL))
            }
            put("paletteOptions",options)
            val selectedModes = listOf("LIGHT","DARK","SYSTEM").filter { selected("theme-${it.lowercase()}") }
            put("modeSelected",selectedModes.singleOrNull()?:"INVALID")
            put("semesterBounds",bounds("semester-input")?:JSONObject.NULL)
            put("deleteBounds",bounds("course-delete")?:JSONObject.NULL)
            val colors=JSONObject()
            for(i in 0..7) bounds("course-color-$i")?.let { colors.put(i.toString(),it) }
            put("courseColorBounds",colors)
            put("courseColorsSelected",JSONArray((0..7).filter { selected("course-color-$it") }))
            val blocks=ui.onAllNodes(SemanticsMatcher.keyIsDefined(CourseColorIndexKey),useUnmergedTree=true).fetchSemanticsNodes()
            put("weekTimeBlock",if(blocks.size==1) JSONObject().apply {
                val node=blocks.single();val b=node.boundsInWindow
                put("bounds",JSONArray(listOf(b.left,b.top,b.right,b.bottom)))
                put("colorIndex",node.config[CourseColorIndexKey])
            } else JSONObject.NULL)
            put("businessHashes",businessHashes())
        }
        ui.runOnUiThread {
            val window=ui.activity.window;val insets=window.decorView.rootWindowInsets
            result.put("imeVisible",insets?.isVisible(WindowInsets.Type.ime())==true)
            result.put("statusBarHeight",insets?.getInsets(WindowInsets.Type.statusBars())?.top?:0)
            result.put("systemNavigationHeight",insets?.getInsets(WindowInsets.Type.navigationBars())?.bottom?:0)
            result.put("chromeArgb",window.statusBarColor);result.put("uiFlags",window.decorView.systemUiVisibility)
        }
        return result
    }
    private fun committedFrame() {
        val latch=CountDownLatch(1)
        ui.runOnUiThread {
            val view=ui.activity.window.decorView
            check(view.isHardwareAccelerated)
            view.viewTreeObserver.registerFrameCommitCallback { latch.countDown() };view.invalidate()
        }
        check(latch.await(5,TimeUnit.SECONDS)) { "No actual committed palette frame" }
    }
    private fun background():Int {
        // Independent fixed design values, not derived from the selected MaterialTheme.
        val colors=mapOf("PURPLE" to ("F9F5FF" to "0C0F15"),"BLUE" to ("F9F9FF" to "111318"),
            "GREEN" to ("F8FBF1" to "11140F"),"TEAL" to ("F4FBF9" to "0E1514"),
            "ORANGE" to ("FFF8F5" to "1A120D"),"PINK" to ("FFF8F8" to "191114"))
        val pair=colors.getValue(palette())
        return android.graphics.Color.parseColor("#"+if(dark())pair.second else pair.first)
    }
    private fun dismissKeyboard() {
        ui.runOnUiThread {
            val window=ui.activity.window
            val manager=ui.activity.getSystemService(Context.INPUT_METHOD_SERVICE) as InputMethodManager
            manager.hideSoftInputFromWindow(window.decorView.windowToken,0)
            window.insetsController?.hide(WindowInsets.Type.ime())
            ui.activity.currentFocus?.clearFocus()
        }
        ui.waitUntil(5000) {
            var visible=true
            ui.runOnUiThread { visible=ui.activity.window.decorView.rootWindowInsets?.isVisible(WindowInsets.Type.ime())==true }
            !visible
        }
    }
    private fun freshHierarchy(file:File) {
        val automation=instrumentation.uiAutomation
        // API33 has no public clearCache(); setServiceInfo clears this connection's cache.
        // Keep the same flags/service info, then fetch actual nodes instead of a stable stale tree.
        automation.serviceInfo=checkNotNull(automation.serviceInfo)
        device.dumpWindowHierarchy(file)
    }
    private fun sameBounds(node:org.w3c.dom.Element?,expected:JSONArray):Boolean {
        if(node==null)return false
        val actual=node.getAttribute("bounds").split('[',']',',').filter{it.isNotEmpty()}.map{it.toInt()}
        return actual.size==4 && (0..3).all { kotlin.math.abs(actual[it]-expected.getDouble(it))<=2 }
    }
    private fun sceneMatches(nodes:org.w3c.dom.NodeList,state:JSONObject):Boolean {
        val app=(0 until nodes.length).map { nodes.item(it) as org.w3c.dom.Element }
            .filter { it.getAttribute("package")=="com.hcbiu.elcton" }
        val text=app.map { it.getAttribute("text") }.toSet()
        when(state.getString("scene")) {
            "options" -> {
                if("配色" !in text || "删除课程" in text)return false
                for((i,p) in palettes.withIndex()) {
                    val matches=app.filter { it.getAttribute("text")==listOf("紫","蓝","绿","青","橙","粉")[i] }
                    if(matches.size!=1)return false
                    val label=matches.single();val option=state.getJSONObject("paletteOptions").getJSONObject(p)
                    val parent=label.parentNode as? org.w3c.dom.Element
                    if(!sameBounds(label,option.getJSONArray("labelBounds")) || !sameBounds(parent,option.getJSONArray("bounds")))return false
                }
            }
            "semester" -> {
                val fields=app.filter { it.getAttribute("class")=="android.widget.EditText" && sameBounds(it,state.getJSONArray("semesterBounds")) }
                if(fields.size!=1 || "学期开始日期" !in text || "保存学期" !in text)return false
            }
            "editor-bottom" -> {
                val labels=app.filter { it.getAttribute("text")=="删除课程" }
                if(labels.size!=1 || "配色" in text)return false
                val parent=labels.single().parentNode as? org.w3c.dom.Element
                if(!sameBounds(parent,state.getJSONArray("deleteBounds")))return false
            }
            "week" -> if(!text.containsAll(listOf("M3E配色验收","上一周","下一周")) || text.any { it in listOf("保存","课程名称","删除课程","配色") })return false
            else -> return false
        }
        return true
    }
    private fun ready(picture:File,xml:File,state:JSONObject):Boolean {
        val bitmap=BitmapFactory.decodeFile(picture.absolutePath)?:return false
        try {
            val expected=background()
            val nav=state.getDouble("navigationBottom").toInt()
            for(y in listOf(10,bitmap.height/3,nav-10,bitmap.height-8)) {
                if(y !in 0 until bitmap.height)return false
                for(x in listOf(1,2,bitmap.width-3,bitmap.width-2))if(bitmap.getPixel(x,y)!=expected)return false
            }
            val nodes=DocumentBuilderFactory.newInstance().newDocumentBuilder().parse(xml).getElementsByTagName("node")
            if(!sceneMatches(nodes,state))return false
            var ink=0
            for(i in 0 until nodes.length) {
                val e=nodes.item(i) as org.w3c.dom.Element
                if(e.getAttribute("package")!="com.hcbiu.elcton"||e.getAttribute("text")!="今日")continue
                val b=e.getAttribute("bounds").split('[',']',',').filter{it.isNotEmpty()}.map{it.toInt()}
                if(b.size!=4||b[0]<0||b[1]<0||b[2]>bitmap.width||b[3]>bitmap.height)return false
                for(y in b[1] until b[3] step 2)for(x in b[0] until b[2] step 2) {
                    val rgb=bitmap.getPixel(x,y)
                    val channels=listOf(android.graphics.Color.red(rgb),android.graphics.Color.green(rgb),android.graphics.Color.blue(rgb))
                    if(if(dark())channels.min()>100 else channels.max()<180)ink++
                }
            }
            return ink>=12 && !state.getBoolean("imeVisible")
        } finally { bitmap.recycle() }
    }
    private fun capture(name:String,scene:String) {
        ui.waitForIdle()
        val attempts=File(directory,"attempts").apply { mkdirs() }
        val deadline=System.nanoTime()+TimeUnit.SECONDS.toNanos(25)
        var attempt=0
        while(System.nanoTime()<deadline) {
            attempt++;committedFrame()
            val picture=File(attempts,"$name-$attempt.png")
            val xmlBefore=File(attempts,"$name-$attempt-before.xml");val xml=File(attempts,"$name-$attempt.xml")
            freshHierarchy(xmlBefore);val before=currentState(scene)
            check(device.takeScreenshot(picture));freshHierarchy(xml);val after=currentState(scene)
            val xmlStable=hash(xmlBefore)==hash(xml)
            val stable=xmlStable && before.toString()==after.toString()
            val pixelReady=stable && ready(picture,xml,after)
            val receipt=JSONObject().apply {
                put("name",name);put("phase",phase);put("qaRun",qaRun);put("attempt",attempt);put("captureId",java.util.UUID.randomUUID().toString())
                put("expectedPalette",palette());put("expectedDark",dark());put("before",before);put("after",after)
                put("stable",stable);put("xmlStable",xmlStable);put("pixelReady",pixelReady)
                put("pngSha256",hash(picture));put("xmlSha256",hash(xml));put("xmlBeforeSha256",hash(xmlBefore))
            }
            File(attempts,"$name-$attempt-state.json").writeText(receipt.toString())
            if(pixelReady) {
                picture.copyTo(File(directory,"$name.png"),true);xml.copyTo(File(directory,"$name.xml"),true)
                File(directory,"$name-state.json").writeText(receipt.toString());return
            }
            ui.waitForIdle()
        }
        error("Palette PNG/XML/state failed to converge: $name")
    }
    private fun settings() {
        dismissKeyboard();ui.onNodeWithTag("nav-today").performClick();ui.onNodeWithTag("nav-settings").performClick();ui.waitForIdle()
    }
    private fun chooseMode(value:String) {
        val before=businessHashes().toString();val oldPalette=palette()
        settings();ui.onNodeWithTag("theme-${value.lowercase()}").performScrollTo().performClick().assertIsSelected()
        ui.waitForIdle();assertEquals(value,mode());assertEquals(oldPalette,palette());assertEquals(before,businessHashes().toString())
        for(other in listOf("LIGHT","DARK","SYSTEM").filter{it!=value})ui.onNodeWithTag("theme-${other.lowercase()}").assertIsNotSelected()
    }
    private fun choosePalette(value:String) {
        val before=businessHashes().toString();val oldMode=mode()
        settings();ui.onNodeWithTag("palette-${value.lowercase()}").performScrollTo().performClick().assertIsSelected()
        ui.waitForIdle();assertEquals(value,palette());assertEquals(oldMode,mode());assertEquals(before,businessHashes().toString())
        for(other in palettes.filter{it!=value})ui.onNodeWithTag("palette-${other.lowercase()}").assertIsNotSelected()
    }
    private fun options(name:String) {
        settings();ui.onNodeWithTag("palette-pink").performScrollTo()
        val labels=listOf("紫","蓝","绿","青","橙","粉")
        for((index,p) in palettes.withIndex()) {
            ui.onNodeWithTag("palette-${p.lowercase()}").assertIsDisplayed()
                .assert(SemanticsMatcher.expectValue(androidx.compose.ui.semantics.SemanticsProperties.Role,
                    androidx.compose.ui.semantics.Role.RadioButton))
            ui.onNodeWithTag("palette-label-${p.lowercase()}",useUnmergedTree=true).assertTextEquals(labels[index])
                .assert(hasAnyAncestor(hasTestTag("palette-${p.lowercase()}")))
        }
        ui.onNodeWithTag("palette-${palette().lowercase()}").assertIsSelected()
        capture(name,"options")
    }
    private fun semester(name:String) {
        settings();ui.onNodeWithTag("semester-input").performScrollTo().assertIsDisplayed();capture(name,"semester")
    }
    private fun openFixture() {
        ui.onNodeWithTag("nav-week").performClick();ui.onNodeWithTag("week-day-6").performClick()
        ui.onNodeWithText("M3E配色验收").performClick();ui.waitForIdle()
    }
    private fun editorAndWeek(prefix:String) {
        openFixture();ui.onNodeWithTag("course-delete").performScrollTo().assertIsDisplayed()
        for(i in 0..7)ui.onNodeWithTag("course-color-$i").assertIsDisplayed()
        ui.onNodeWithTag("course-color-0").assertIsSelected()
        capture(prefix+"-editor-bottom","editor-bottom")
        ui.onNodeWithTag("nav-week").performClick();ui.onNodeWithTag("week-day-6").performClick()
        ui.onNodeWithText("M3E配色验收").assertIsDisplayed()
        ui.onNodeWithText("上一周").assertIsDisplayed()
        capture(prefix+"-week","week")
    }
    private fun createFixture() {
        assertFalse("Palette absent still defaults to purple",prefs.contains("palette"))
        assertEquals("PURPLE",palette())
        ui.onNodeWithTag("nav-week").performClick();ui.onNodeWithTag("add-course").performClick()
        ui.onNodeWithTag("course-name").performTextInput("M3E配色验收")
        ui.onNodeWithTag("course-day-6").performScrollTo().performClick()
        dismissKeyboard()
        ui.onNodeWithTag("course-save").performClick();ui.waitForIdle()
    }
    private fun setSystemDark(value:Boolean) {
        shell("cmd uimode night "+if(value)"yes" else "no")
        ui.waitUntil(15000) { runCatching { systemDark()==value && ui.onAllNodesWithTag("nav-today").fetchSemanticsNodes().isNotEmpty() }.getOrDefault(false) }
        ui.waitForIdle()
    }
    @Test fun inspectPaletteAndPersistencePhase() {
        ui.waitUntil(15000){ui.onAllNodesWithTag("nav-today").fetchSemanticsNodes().isNotEmpty()}
        assertEquals("true",args.getString("previous_force_stop"))
        File(directory,"r3-$phase-process.json").writeText(JSONObject().put("pid",Process.myPid()).put("phase",phase)
            .put("mode",mode()).put("palette",palette()).put("qaRun",qaRun).put("previousHostForceStop",true).toString())
        if(phase=="warm")createFixture()
        val before=businessHashes()
        when {
            phase=="warm" -> {
                for((p,m) in states) {
                    choosePalette(p);chooseMode(m)
                    val prefix="r3-${p.lowercase()}-${m.lowercase()}"
                    options(prefix+"-options");semester(prefix+"-semester");editorAndWeek(prefix)
                }
                choosePalette("PURPLE");chooseMode("LIGHT")
            }
            phase.startsWith("cold-") && phase!="cold-system" -> {
                val pair=states.first{phase=="cold-${it.first.lowercase()}-${it.second.lowercase()}"}
                assertEquals(pair.first,palette());assertEquals(pair.second,mode())
                options("r3-${pair.first.lowercase()}-${pair.second.lowercase()}-cold")
                val index=states.indexOf(pair)
                if(index+1<states.size) {
                    choosePalette(states[index+1].first);chooseMode(states[index+1].second)
                } else { chooseMode("SYSTEM") }
            }
            phase=="system" -> {
                assertEquals("SYSTEM",mode())
                for(p in palettes) {
                    choosePalette(p);setSystemDark(false);options("r3-${p.lowercase()}-system-light")
                    setSystemDark(true);options("r3-${p.lowercase()}-system-dark")
                }
            }
            phase=="cold-system" -> {
                assertEquals("SYSTEM",mode());assertEquals("PINK",palette());assertTrue(systemDark())
                options("r3-system-cold")
                choosePalette("PURPLE");chooseMode("DARK");options("r3-restored-purple-dark")
            }
            else -> error("Unknown palette phase: $phase")
        }
        val after=businessHashes();assertEquals(before.toString(),after.toString())
        File(directory,"r3-$phase-result.json").writeText(JSONObject().apply {
            put("passed",true);put("phase",phase);put("pid",Process.myPid());put("mode",mode());put("palette",palette())
            put("navigationMode",navigationMode);put("qaRun",qaRun);put("businessBefore",before);put("businessAfter",after)
        }.toString())
        if(phase=="cold-system") {
            // Remove only the named emulator QA course; never runs on a physical phone.
            openFixture();ui.onNodeWithTag("course-delete").performScrollTo().performClick()
            ui.onNodeWithTag("delete-confirm").performClick();ui.onAllNodesWithText("M3E配色验收").assertCountEquals(0)
        }
    }
}
