package com.hcbiu.elcton

import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import android.net.Uri
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.BackHandler
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.text.selection.SelectionContainer
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.res.colorResource
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import org.json.JSONObject
import java.time.LocalDate
import java.util.UUID

/** Phone is the editor; imported watch data is a proposal, never an automatic overwrite. */
class MainActivity : ComponentActivity() {
    private lateinit var store: ScheduleStore
    private lateinit var probe: WearProbe
    private var book by mutableStateOf(ScheduleBook.empty("initial", "2026-09-01"))
    private var tab by mutableIntStateOf(0)
    private var selectedDay by mutableIntStateOf(LocalDate.now().dayOfWeek.value)
    private var displayWeek by mutableIntStateOf(1)
    private var editing by mutableStateOf(false)
    private var editingCourse by mutableStateOf<Course?>(null)
    private var notice by mutableStateOf("")
    private var loadError by mutableStateOf<String?>(null)
    private var showImport by mutableStateOf(false)
    private var showExport by mutableStateOf(false)
    private var pendingImport by mutableStateOf<ScheduleBook?>(null)
    private var pendingPublish by mutableStateOf(false)
    private var confirmClear by mutableStateOf(false)
    private var confirmRestore by mutableStateOf(false)
    private var diagnostics by mutableStateOf(false)
    private var probeState by mutableStateOf(WearProbe.State())
    private val colors = listOf(Color(0xFF8FA8FF),Color(0xFFB49BFF),Color(0xFF69C9B6),Color(0xFFE7AD77),Color(0xFFDD91B9),Color(0xFF81BCD9),Color(0xFFA7C57F),Color(0xFFB5BCCA))

    private val openFile = registerForActivityResult(ActivityResultContracts.OpenDocument()) { uri ->
        if (uri != null) runCatching { contentResolver.openInputStream(uri)?.use { stream ->
            val output=java.io.ByteArrayOutputStream();val buffer=ByteArray(4096)
            while(true){val count=stream.read(buffer);if(count<0)break;require(output.size()+count<=65536){"导入文件过大"};output.write(buffer,0,count)}
            output.toString("UTF-8")
        } ?: error("无法读取文件") }.onSuccess { prepareImport(it) }.onFailure { notice="导入失败：${UserFacingError.validation(it.message)}" }
    }
    private val exportFile = registerForActivityResult(ActivityResultContracts.CreateDocument("application/json")) { uri ->
        if(uri!=null)runCatching {
            contentResolver.openOutputStream(uri)?.use { it.write(book.wireJson().toByteArray(Charsets.UTF_8)) } ?: error("无法写入文件")
        }.onSuccess { notice="课表已导出" }.onFailure { notice="导出失败：${UserFacingError.validation(it.message)}" }
    }
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        store=ScheduleStore(this)
        runCatching { store.load() }.onSuccess { book=it }.onFailure { loadError="手机课表读取失败；原文件未重置。可在设置恢复备份。" }
        displayWeek=book.weekAt(LocalDate.now())
        probe=WearProbe(this,{ probeState=it }) { raw,revision -> prepareImport(raw,revision) }
        setContent {
            M3xTheme {
                Product()
            }
        }
    }
    private fun save(next: ScheduleBook): Boolean = try {
        check(loadError==null){"请先恢复无法读取的课表"}
        store.save(next);book=next;notice="已保存在手机，尚未同步到手表";true
    } catch(e:Exception){notice=UserFacingError.validation(e.message);false}
    private fun prepareImport(raw: String, remoteRevision: Long = 0) {
        runCatching { book.importSnapshot(raw,remoteRevision) }.onSuccess { pendingImport=it;showImport=false }
            .onFailure { notice="无法导入：${UserFacingError.validation(it.message)}" }
    }
    @Composable private fun Product() {
        val titles=listOf("今日课程","周课表","设备同步","设置")
        Scaffold(
            containerColor=MaterialTheme.colorScheme.background,
            topBar={ Surface(color=MaterialTheme.colorScheme.background) {
                Row(Modifier.fillMaxWidth().padding(horizontal=20.dp,vertical=16.dp),horizontalArrangement=Arrangement.SpaceBetween) {
                    Column { Text(if(editing)"编辑课程" else titles[tab],style=MaterialTheme.typography.headlineSmall);Text("hc课程表",style=MaterialTheme.typography.labelMedium,color=MaterialTheme.colorScheme.onSurfaceVariant) }
                    Text("第${book.weekAt(LocalDate.now())}周",style=MaterialTheme.typography.labelLarge,color=MaterialTheme.colorScheme.primary,modifier=Modifier.padding(top=8.dp))
                }
            }},
            bottomBar={ NavigationBar(containerColor=MaterialTheme.colorScheme.background,tonalElevation=0.dp) {
                listOf("今日","课表","设备","设置").forEachIndexed { index,label ->
                    NavigationBarItem(selected=tab==index,modifier=Modifier.testTag(listOf("nav-today","nav-week","nav-devices","nav-settings")[index]),
                        onClick={tab=index;editing=false;editingCourse=null},icon={TabGlyph(index,tab==index)},label={Text(label)})
                }
            }},
            floatingActionButton={if(!editing&&tab<=1&&loadError==null)FloatingActionButton(onClick={editingCourse=null;editing=true},modifier=Modifier.testTag("add-course"),containerColor=MaterialTheme.colorScheme.primary) { Text("＋",style=MaterialTheme.typography.headlineMedium) }}
        ){padding->
            Box(Modifier.fillMaxSize().padding(padding)) {
                if(editing)CourseEditor(editingCourse)
                else when(tab){0->Today();1->Week();2->Devices();else->Settings()}
            }
        }
        BackHandler(editing){editing=false;editingCourse=null}
        if(showImport)ImportDialog()
        if(pendingImport!=null) {
            val proposed=pendingImport!!
            AlertDialog(onDismissRequest={pendingImport=null},title={Text("导入预览")},text={Column(verticalArrangement=Arrangement.spacedBy(12.dp)){
                Text("${proposed.courses.size} 条课程 · 学期 ${proposed.semesterStart}")
                Text("确认后替换手机的 ${book.courses.size} 条课程，并保留上一版本。不会自动发到手表。",style=MaterialTheme.typography.bodyMedium)
            }},confirmButton={TextButton(onClick={if(save(proposed))pendingImport=null},modifier=Modifier.testTag("import-confirm")){Text("确认导入")}},
                dismissButton={TextButton(onClick={pendingImport=null},modifier=Modifier.testTag("import-cancel")){Text("取消")}})
        }
        if(showExport)AlertDialog(onDismissRequest={showExport=false},title={Text("导出课表")},text={Column{
            Text("${book.courses.size} 条课程 · JSON v1",style=MaterialTheme.typography.labelLarge)
            SelectionContainer { Text(book.wireJson(),fontFamily=FontFamily.Monospace,style=MaterialTheme.typography.bodySmall,
                modifier=Modifier.heightIn(max=260.dp).verticalScroll(rememberScrollState()).padding(top=12.dp)) }
        }},confirmButton={TextButton(onClick={showExport=false;exportFile.launch("hc-course-schedule.json")}){Text("保存文件")}},
            dismissButton={Row{TextButton(onClick={(getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager).setPrimaryClip(ClipData.newPlainText("课表",book.wireJson()));notice="课表已复制"}){Text("复制")};TextButton(onClick={showExport=false}){Text("关闭")}}})
        if(pendingPublish)AlertDialog(onDismissRequest={pendingPublish=false},title={Text("确认替换手表课表")},
            text={Text("手表有已有数据或本地修改。此次用手机课表替换选中手表；手表会保留上一有效版本。也可取消并先从手表导入。")},
            confirmButton={TextButton(onClick={pendingPublish=false;probe.publishSnapshot(book.wireJson(),true,book.datasetId,maxOf(1L,book.revision))}){Text("确认替换")}},
            dismissButton={TextButton(onClick={pendingPublish=false}){Text("取消")}})
        if(confirmClear)AlertDialog(onDismissRequest={confirmClear=false},title={Text("清空手机课表？")},text={Text("清空只影响手机，保留上一版本备份；不会自动清空手表。")},confirmButton={TextButton(onClick={confirmClear=false;save(book.copy(courses=emptyList(),revision=book.revision+1))}){Text("清空")}},dismissButton={TextButton(onClick={confirmClear=false}){Text("取消")}})
        if(confirmRestore)AlertDialog(onDismissRequest={confirmRestore=false},title={Text("恢复上一版本？")},text={Text("恢复手机本地备份，不会自动同步。")},confirmButton={TextButton(onClick={confirmRestore=false;runCatching{store.restore()}.onSuccess{book=it;loadError=null;notice="已恢复上一版本"}.onFailure{notice="恢复失败：${UserFacingError.validation(it.message)}"}}){Text("恢复")}},dismissButton={TextButton(onClick={confirmRestore=false}){Text("取消")}})
        if(diagnostics)AlertDialog(onDismissRequest={diagnostics=false},title={Text("连接诊断")},text={SelectionContainer{Text(probeState.diagnostic.ifEmpty{"暂无错误记录"},style=MaterialTheme.typography.bodySmall,fontFamily=FontFamily.Monospace)}},confirmButton={TextButton(onClick={diagnostics=false}){Text("关闭")}})
    }
    @Composable private fun TabGlyph(index:Int,selected:Boolean) {
        val color=if(selected)MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.onSurfaceVariant
        val background=MaterialTheme.colorScheme.background
        Canvas(Modifier.size(22.dp)) {
            val unit=size.width/10;val stroke=unit*.65f
            when(index){
                0->{drawCircle(color,radius=unit*3.2f,center=center,style=androidx.compose.ui.graphics.drawscope.Stroke(stroke));drawLine(color,center,Offset(center.x,unit*2.4f),stroke);drawLine(color,center,Offset(unit*7.6f,center.y),stroke)}
                1->{drawRect(color,topLeft=Offset(unit,unit*1.6f),size=androidx.compose.ui.geometry.Size(unit*8,unit*7.3f),style=androidx.compose.ui.graphics.drawscope.Stroke(stroke));drawLine(color,Offset(unit,unit*4),Offset(unit*9,unit*4),stroke);drawCircle(color,unit*.55f,Offset(unit*3.2f,unit*6.4f));drawCircle(color,unit*.55f,Offset(unit*6.8f,unit*6.4f))}
                2->{drawRoundRect(color,topLeft=Offset(unit*2,unit),size=androidx.compose.ui.geometry.Size(unit*6,unit*8),cornerRadius=androidx.compose.ui.geometry.CornerRadius(unit),style=androidx.compose.ui.graphics.drawscope.Stroke(stroke));drawLine(color,Offset(unit*3.5f,unit*7),Offset(unit*6.5f,unit*7),stroke)}
                else->{for(i in 0..2){val y=unit*(2+i*3);drawLine(color,Offset(unit,y),Offset(unit*9,y),stroke);drawCircle(background,unit,Offset(unit*(if(i==1)6f else 3f),y));drawCircle(color,unit,Offset(unit*(if(i==1)6f else 3f),y),style=androidx.compose.ui.graphics.drawscope.Stroke(stroke))}}
            }
        }
    }

    @Composable private fun NoticeBlock() {
        val text=loadError?:notice
        if(text.isNotEmpty())Text(text,color=if(loadError!=null)MaterialTheme.colorScheme.error else MaterialTheme.colorScheme.onSurfaceVariant,style=MaterialTheme.typography.bodySmall,modifier=Modifier.fillMaxWidth().padding(bottom=8.dp))
    }
    @Composable private fun Today() {
        val now=LocalDate.now();val week=book.weekAt(now);val list=book.forDay(now.dayOfWeek.value,week)
        LazyColumn(Modifier.fillMaxSize(),contentPadding=PaddingValues(20.dp,0.dp,20.dp,100.dp),verticalArrangement=Arrangement.spacedBy(12.dp)) {
            item{NoticeBlock();Text("${now.monthValue}月${now.dayOfMonth}日 · ${dayLabel(now.dayOfWeek.value)}",style=MaterialTheme.typography.titleMedium)}
            if(list.isEmpty())item{EmptyMessage("今天没有课程","在手机添加课程，或在设置导入已有课表。")}
            items(list,key={it.id}){course->CourseCard(course)}
        }
    }
    @Composable private fun Week() {
        Column(Modifier.fillMaxSize()) {
            Column(Modifier.padding(horizontal=20.dp)){NoticeBlock()
                Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.SpaceBetween){TextButton(onClick={displayWeek=maxOf(1,displayWeek-1)}){Text("上一周")};Text("第${displayWeek}周 · ${if(displayWeek%2==1)"单周" else "双周"}",modifier=Modifier.padding(top=12.dp));TextButton(onClick={displayWeek++}){Text("下一周")}}
                Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.spacedBy(3.dp)){for(day in 1..7){Surface(color=if(selectedDay==day)MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.surface,shape=RoundedCornerShape(12.dp),modifier=Modifier.weight(1f).height(42.dp).testTag("week-day-$day").clickable{selectedDay=day}){Box(contentAlignment=androidx.compose.ui.Alignment.Center){Text(dayLabel(day).takeLast(1),color=if(selectedDay==day)Color(0xFF17203A) else MaterialTheme.colorScheme.onSurface)}}}}
                Spacer(Modifier.height(16.dp))
            }
            val list=book.forDay(selectedDay,displayWeek)
            LazyColumn(Modifier.fillMaxSize(),contentPadding=PaddingValues(20.dp,0.dp,20.dp,100.dp),verticalArrangement=Arrangement.spacedBy(12.dp)){
                if(list.isEmpty())item{EmptyMessage("这天没有课程","切换星期或添加新课程。")}
                items(list,key={it.id}){CourseCard(it)}
            }
        }
    }
    @Composable private fun EmptyMessage(title:String,body:String){Column(Modifier.fillMaxWidth().padding(vertical=32.dp),verticalArrangement=Arrangement.spacedBy(12.dp)){Text(title,style=MaterialTheme.typography.titleLarge);Text(body,style=MaterialTheme.typography.bodyMedium,color=MaterialTheme.colorScheme.onSurfaceVariant)}}
    @Composable private fun CourseCard(c:Course) {
        Surface(color=MaterialTheme.colorScheme.surface,shape=RoundedCornerShape(18.dp),modifier=Modifier.fillMaxWidth().clickable{editingCourse=c;editing=true}){
            Row(Modifier.padding(16.dp),horizontalArrangement=Arrangement.spacedBy(14.dp)){
                Box(Modifier.width(4.dp).height(72.dp).background(colors[c.colorIndex],RoundedCornerShape(2.dp)))
                Column(Modifier.weight(1f),verticalArrangement=Arrangement.spacedBy(6.dp)){
                    Text(c.name,style=MaterialTheme.typography.titleMedium,maxLines=2,overflow=TextOverflow.Ellipsis)
                    Text("${c.startTime}—${c.endTime} · ${c.startPeriod}—${c.endPeriod}节",style=MaterialTheme.typography.bodySmall,color=MaterialTheme.colorScheme.onSurfaceVariant)
                    val place=listOf(c.teacher,c.location).filter{it.isNotEmpty()}.joinToString(" · ")
                    if(place.isNotEmpty())Text(place,style=MaterialTheme.typography.bodySmall,color=MaterialTheme.colorScheme.onSurfaceVariant,maxLines=1,overflow=TextOverflow.Ellipsis)
                }
                Text(when(c.weekType){"odd"->"单周";"even"->"双周";else->"每周"},style=MaterialTheme.typography.labelSmall,color=MaterialTheme.colorScheme.primary)
            }
        }
    }
    @Composable private fun CourseEditor(existing:Course?) {
        val key=existing?.id?:"new"
        val id=remember(key){existing?.id?:UUID.randomUUID().toString()}
        var name by remember(key){mutableStateOf(existing?.name?:"")};var teacher by remember(key){mutableStateOf(existing?.teacher?:"")};var location by remember(key){mutableStateOf(existing?.location?:"")}
        var day by remember(key){mutableIntStateOf(existing?.dayOfWeek?:selectedDay)}
        var first by remember(key){mutableStateOf((existing?.startPeriod?:1).toString())};var last by remember(key){mutableStateOf((existing?.endPeriod?:1).toString())}
        var from by remember(key){mutableStateOf(existing?.startTime?:"08:00")};var to by remember(key){mutableStateOf(existing?.endTime?:"08:45")}
        var week by remember(key){mutableStateOf(existing?.weekType?:"all")};var color by remember(key){mutableIntStateOf(existing?.colorIndex?:0)}
        var error by remember(key){mutableStateOf("")};var delete by remember(key){mutableStateOf(false)};var overlap by remember(key){mutableStateOf<Course?>(null)}
        fun commit(c:Course){runCatching{book.put(c)}.onSuccess{if(save(it)){editing=false;editingCourse=null}}.onFailure{error=UserFacingError.validation(it.message)}}
        Column(Modifier.fillMaxSize()){
            Row(Modifier.fillMaxWidth().padding(horizontal=12.dp),horizontalArrangement=Arrangement.SpaceBetween){TextButton(onClick={editing=false}){Text("返回")};Button(onClick={
                if(name.isBlank()){error="请输入课程名称";return@Button}
                val a=first.toIntOrNull();val b=last.toIntOrNull();if(a==null||b==null){error="请填写有效节次";return@Button}
                val c=Course(id,name.trim(),location.trim(),teacher.trim(),day,a,b,from.trim(),to.trim(),week,color)
                runCatching{book.put(c)}.onFailure{error=UserFacingError.validation(it.message)}.onSuccess{if(book.overlaps(c).isNotEmpty())overlap=c else commit(c)}
            },modifier=Modifier.testTag("course-save")){Text("保存")}}
            Column(Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(20.dp),verticalArrangement=Arrangement.spacedBy(14.dp)){
                if(error.isNotEmpty())Text(error,color=MaterialTheme.colorScheme.error)
                OutlinedTextField(name,{name=it;error=""},Modifier.fillMaxWidth().testTag("course-name"),label={Text("课程名称")},singleLine=true)
                Row(horizontalArrangement=Arrangement.spacedBy(12.dp)){OutlinedTextField(teacher,{teacher=it},Modifier.weight(1f).testTag("course-teacher"),label={Text("教师")},singleLine=true);OutlinedTextField(location,{location=it},Modifier.weight(1f).testTag("course-location"),label={Text("地点")},singleLine=true)}
                Text("上课星期",style=MaterialTheme.typography.labelLarge)
                Row(horizontalArrangement=Arrangement.spacedBy(3.dp)){for(d in 1..7){Surface(color=if(day==d)MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.surface,shape=RoundedCornerShape(12.dp),modifier=Modifier.weight(1f).height(40.dp).testTag("course-day-$d").clickable{day=d}){Box(contentAlignment=androidx.compose.ui.Alignment.Center){Text(dayLabel(d).takeLast(1),color=if(day==d)Color(0xFF17203A) else MaterialTheme.colorScheme.onSurface)}}}}
                Row(horizontalArrangement=Arrangement.spacedBy(12.dp)){OutlinedTextField(first,{first=it},Modifier.weight(1f).testTag("course-first"),label={Text("开始节次")},singleLine=true,keyboardOptions=KeyboardOptions(keyboardType=KeyboardType.Number));OutlinedTextField(last,{last=it},Modifier.weight(1f).testTag("course-last"),label={Text("结束节次")},singleLine=true,keyboardOptions=KeyboardOptions(keyboardType=KeyboardType.Number))}
                Row(horizontalArrangement=Arrangement.spacedBy(12.dp)){OutlinedTextField(from,{from=it},Modifier.weight(1f).testTag("course-start"),label={Text("开始时间")},singleLine=true);OutlinedTextField(to,{to=it},Modifier.weight(1f).testTag("course-end"),label={Text("结束时间")},singleLine=true)}
                Text("周次规则",style=MaterialTheme.typography.labelLarge)
                Row(horizontalArrangement=Arrangement.spacedBy(8.dp)){listOf("all" to "每周","odd" to "单周","even" to "双周").forEach{(value,label)->FilterChip(selected=week==value,onClick={week=value},label={Text(label)},modifier=Modifier.testTag("course-week-$value"))}}
                Text("课程颜色",style=MaterialTheme.typography.labelLarge)
                Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.SpaceBetween){colors.forEachIndexed{i,c->Box(Modifier.size(30.dp).background(c,CircleShape).clickable{color=i}.testTag("course-color-$i"),contentAlignment=androidx.compose.ui.Alignment.Center){if(color==i)Text("✓",color=Color(0xFF10131B))}}}
                if(existing!=null)OutlinedButton(onClick={delete=true},modifier=Modifier.fillMaxWidth().testTag("course-delete")){Text("删除课程",color=MaterialTheme.colorScheme.error)}
                Spacer(Modifier.height(24.dp))
            }
        }
        if(delete)AlertDialog(onDismissRequest={delete=false},title={Text("删除这门课程？")},text={Text("只修改手机课表，之后主动同步才会更新手表。")},confirmButton={TextButton(onClick={if(save(book.remove(id))){editing=false;delete=false}},modifier=Modifier.testTag("delete-confirm")){Text("删除")}},dismissButton={TextButton(onClick={delete=false}){Text("取消")}})
        if(overlap!=null)AlertDialog(onDismissRequest={overlap=null},title={Text("上课时间重叠")},text={Text("与已有课程存在同星期、同周次的时间重叠。不会自动删除任何课程，是否仍保存？")},confirmButton={TextButton(onClick={val c=overlap!!;overlap=null;commit(c)}){Text("仍然保存")}},dismissButton={TextButton(onClick={overlap=null}){Text("返回修改")}})
    }
    @Composable private fun Settings(){
        var semester by remember(book.semesterStart){mutableStateOf(book.semesterStart)};var dateError by remember{mutableStateOf("")}
        Column(Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(horizontal=20.dp),verticalArrangement=Arrangement.spacedBy(14.dp)){
            NoticeBlock();Text("学期",style=MaterialTheme.typography.titleMedium)
            Text("第一周按该日期所在的周一起算。",color=MaterialTheme.colorScheme.onSurfaceVariant,style=MaterialTheme.typography.bodySmall)
            OutlinedTextField(semester,{semester=it;dateError=""},Modifier.fillMaxWidth().testTag("semester-input"),label={Text("学期开始日期")},singleLine=true)
            if(dateError.isNotEmpty())Text(dateError,color=MaterialTheme.colorScheme.error)
            Button(onClick={runCatching{book.withSemester(semester)}.onSuccess{if(save(it))displayWeek=it.weekAt(LocalDate.now())}.onFailure{dateError="请输入有效日期（YYYY-MM-DD）"}},modifier=Modifier.testTag("semester-save")){Text("保存学期")}
            HorizontalDivider(Modifier.padding(vertical=6.dp));Text("导入与备份",style=MaterialTheme.typography.titleMedium)
            OutlinedButton(onClick={showImport=true},modifier=Modifier.fillMaxWidth().testTag("import-paste")){Text("粘贴 JSON 导入")}
            OutlinedButton(onClick={openFile.launch(arrayOf("application/json","text/plain","application/octet-stream"))},modifier=Modifier.fillMaxWidth().testTag("import-file")){Text("从文件导入")}
            OutlinedButton(onClick={showExport=true},modifier=Modifier.fillMaxWidth().testTag("export-preview")){Text("预览并导出课表")}
            if(store.hasBackup())OutlinedButton(onClick={confirmRestore=true},modifier=Modifier.fillMaxWidth().testTag("restore-backup")){Text("恢复上一版本")}
            TextButton(onClick={confirmClear=true},enabled=loadError==null,modifier=Modifier.testTag("clear-book")){Text("清空手机课表",color=MaterialTheme.colorScheme.error)}
            HorizontalDivider();Text("隐私与兼容性",style=MaterialTheme.typography.titleMedium)
            Text("课表保存在两端应用本地；同步不使用自建云服务。设备能力、签名和运动健康授权决定是否可通信，不把 FIT3 作为型号白名单。",style=MaterialTheme.typography.bodySmall,color=MaterialTheme.colorScheme.onSurfaceVariant)
            Text("0.2.4 · 测试构建\nWear Engine 真实权限与其他运行时适配以验证报告为准。",style=MaterialTheme.typography.labelSmall,color=MaterialTheme.colorScheme.onSurfaceVariant)
            Spacer(Modifier.height(32.dp))
        }
    }
    @Composable private fun ImportDialog(){var raw by remember{mutableStateOf("")};var error by remember{mutableStateOf("")}
        AlertDialog(onDismissRequest={showImport=false},title={Text("粘贴课表 JSON")},text={Column(verticalArrangement=Arrangement.spacedBy(12.dp)){
            Text("使用 elcton.schedule v1。先检查内容，再确认导入。",style=MaterialTheme.typography.bodySmall)
            OutlinedTextField(raw,{raw=it},Modifier.fillMaxWidth().heightIn(min=160.dp,max=300.dp).testTag("import-input"),label={Text("JSON 内容")})
            if(error.isNotEmpty())Text(error,color=MaterialTheme.colorScheme.error)
        }},confirmButton={TextButton(onClick={runCatching{book.importSnapshot(raw)}.onSuccess{pendingImport=it;showImport=false}.onFailure{error=UserFacingError.validation(it.message)}},modifier=Modifier.testTag("import-check")){Text("检查")}},dismissButton={TextButton(onClick={showImport=false}){Text("取消")}})
    }
    @Composable private fun Devices(){
        Column(Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(horizontal=20.dp),verticalArrangement=Arrangement.spacedBy(14.dp)){
            NoticeBlock();Text(probeState.status,style=MaterialTheme.typography.titleLarge)
            Text(probeState.detail,style=MaterialTheme.typography.bodyMedium,color=MaterialTheme.colorScheme.onSurfaceVariant)
            if(probeState.busy)LinearProgressIndicator(Modifier.fillMaxWidth())
            Button(onClick={probe.authorizeAndScan()},enabled=!probeState.busy,modifier=Modifier.testTag("scan-devices")){Text("查询配对设备")}
            probeState.devices.forEach{d->OutlinedButton(onClick={probe.connect(d)},enabled=!probeState.busy,modifier=Modifier.fillMaxWidth()){
                Column(Modifier.fillMaxWidth()){Text(d.name.orEmpty(),style=MaterialTheme.typography.titleSmall);Text("${if(d.isConnected)"已连接" else "未连接"} · ${d.model.orEmpty()}",style=MaterialTheme.typography.labelSmall)}
            }}
            Surface(color=MaterialTheme.colorScheme.surface,shape=RoundedCornerShape(16.dp)){Column(Modifier.padding(16.dp),verticalArrangement=Arrangement.spacedBy(10.dp)){
                Text("手表准备",style=MaterialTheme.typography.titleSmall)
                Text("在手表进入周视图 → 同步 → 开始接收。手机保持前台，等对端准备就绪后再发布课表。",style=MaterialTheme.typography.bodySmall,color=MaterialTheme.colorScheme.onSurfaceVariant)
                Text("手机 ${book.courses.size} 条课程 · 修订 ${book.revision}",style=MaterialTheme.typography.labelMedium)
            }}
            Button(onClick={if(probeState.dirty||probeState.hasData&&probeState.datasetId!=book.datasetId)pendingPublish=true else probe.publishSnapshot(book.wireJson(),false,book.datasetId,maxOf(1L,book.revision))},enabled=probeState.ready&&!probeState.busy&&loadError==null,modifier=Modifier.fillMaxWidth().testTag("publish-book")){Text("同步到选中手表")}
            OutlinedButton(onClick={probe.requestExport()},enabled=probeState.ready&&!probeState.busy,modifier=Modifier.fillMaxWidth().testTag("import-watch")){Text("从手表导入")}
            TextButton(onClick={probe.cancel()},modifier=Modifier.testTag("disconnect")){Text("断开并停止同步")}
            if(probeState.diagnostic.isNotEmpty())TextButton(onClick={diagnostics=true},modifier=Modifier.testTag("diagnostics")){Text("查看诊断记录")}
            Text("当前提供 Lite Wearable 应用。圆屏、方屏按窗口适配；其他系统运行时需要对应应用包。连接和版本结果不等于全机型认证。",style=MaterialTheme.typography.bodySmall,color=MaterialTheme.colorScheme.onSurfaceVariant)
            Spacer(Modifier.height(28.dp))
        }
    }
    private fun dayLabel(day:Int)=listOf("周一","周二","周三","周四","周五","周六","周日")[day-1]
    override fun onStop(){if(::probe.isInitialized)probe.onBackground();super.onStop()}
    override fun onDestroy(){if(::probe.isInitialized)probe.close();super.onDestroy()}
}
