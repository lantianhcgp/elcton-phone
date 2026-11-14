from pathlib import Path
from typing import cast
import subprocess,sys,re,json,io,tarfile,os,xml.etree.ElementTree as ET
from PIL import Image,ImageStat
out=Path('qa-evidence');out.mkdir(exist_ok=True)

def preserve_failure(result):
    (out/'report.json').write_text(json.dumps({'passed':False,'stage':'instrumentation',
        'source_sha':sources[0].read_text().strip(),'exit_code':result.returncode,
        'instrumentation':result.stdout.decode(errors='replace'),
        'stderr':result.stderr.decode(errors='replace')},indent=2))
main=list(Path('incoming').rglob('elcton-phone-probe.apk'))
tests=list(Path('incoming').rglob('elcton-ui-tests.apk'))
assert len(main)==1 and len(tests)==1,(main,tests)
sources=list(Path('incoming').rglob('source-sha.txt'))
assert len(sources)==1 and sources[0].read_text().strip()==subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),'APK/test/source identity mismatch'
def shell(command):
    return subprocess.run(['adb','shell'],input=(command+'\n').encode(),capture_output=True,check=True,timeout=60).stdout.decode(errors='replace')
for apk in (main[0],tests[0]):subprocess.run(['adb','install','-r',str(apk)],check=True)
navigation_mode=os.environ.get('QA_NAVIGATION_MODE','three-button')
assert navigation_mode in ('three-button','gestural'),navigation_mode
overlay='com.android.internal.systemui.navbar.'+('threebutton' if navigation_mode=='three-button' else 'gestural')
shell('cmd overlay enable-exclusive --category '+overlay)
active_overlays=shell('cmd overlay list')
assert '[x] '+overlay in active_overlays,'Navigation overlay not enabled: '+active_overlays
(out/'environment.json').write_text(json.dumps({'navigation_mode':navigation_mode,'overlay':overlay,'sdk':shell('getprop ro.build.version.sdk').strip(),'overlays':active_overlays},indent=2))
shell('pm clear com.hcbiu.elcton');shell('svc power stayon true');shell('settings put system screen_off_timeout 2147483647');shell('input keyevent KEYCODE_WAKEUP');shell('wm dismiss-keyguard')

def prepare_ui_notifications():
    # Appearance/persistence fixtures must not be blocked by the new default-on
    # API33 permission dialog. Permission-denied behavior has separate diagnostics tests.
    sdk = int(shell('getprop ro.build.version.sdk').strip())
    if sdk < 33:
        return {'sdk': sdk, 'notification_fixture': 'not-required'}
    shell('pm grant com.hcbiu.elcton android.permission.POST_NOTIFICATIONS')
    permissions = shell('dumpsys package com.hcbiu.elcton')
    assert 'android.permission.POST_NOTIFICATIONS: granted=true' in permissions, 'Notification permission grant did not read back'
    return {'sdk': sdk, 'notification_fixture': 'pregranted-ui-only', 'granted': True}

(out/'notification-fixture.json').write_text(json.dumps(prepare_ui_notifications(), indent=2)+'\n')
def harvest_theme():
    archive=subprocess.run(['adb','shell'],input=b'run-as com.hcbiu.elcton tar -cf - -C files qa-theme-evidence\n',capture_output=True)
    if archive.returncode or not archive.stdout:
        (out/'theme-harvest-error.txt').write_text(archive.stderr.decode(errors='replace'))
        return False
    target=out/'theme-product';target.mkdir(exist_ok=True)
    try:
        with tarfile.open(fileobj=io.BytesIO(archive.stdout),mode='r:') as captured:
            for member in captured.getmembers():
                if not member.isfile():continue
                relative=Path(member.name)
                assert relative.parts[0]=='qa-theme-evidence' and '..' not in relative.parts,member.name
                destination=target.joinpath(*relative.parts[1:])
                destination.parent.mkdir(parents=True,exist_ok=True)
                contents=captured.extractfile(member);assert contents is not None
                destination.write_bytes(contents.read())
        return True
    except (tarfile.TarError,AssertionError) as error:
        (out/'theme-harvest-error.txt').write_text(str(error))
        return False

# New theme suite uses real UI selections; frozen legacy dark assertions remain untouched.
from verify_theme_evidence import PHASES,verify_product
host={'passed':False,'source_sha':sources[0].read_text().strip(),'navigation_mode':navigation_mode,'phases':{}}
shell('cmd uimode night no')
for phase in PHASES:
    shell('am force-stop com.hcbiu.elcton');shell('am force-stop com.hcbiu.elcton.test')
    stop={'target_pid_after':shell('pidof com.hcbiu.elcton; test "$?" -le 1').strip(),'test_pid_after':shell('pidof com.hcbiu.elcton.test; test "$?" -le 1').strip()}
    assert stop['target_pid_after']=='' and stop['test_pid_after']=='','Theme phase did not get a fresh process'
    if phase=='cold-system-dark':shell('cmd uimode night yes')
    command=('am instrument -w -r -e navigation_mode '+navigation_mode+' -e theme_phase '+phase+
        ' -e previous_force_stop true -e class com.hcbiu.elcton.ThemeUiTest com.hcbiu.elcton.test/androidx.test.runner.AndroidJUnitRunner')
    executed=subprocess.run(['adb','shell'],input=(command+'\n').encode(),capture_output=True,timeout=420)
    result=executed.stdout.decode(errors='replace')
    phase_passed=executed.returncode==0 and bool(re.search(r'OK \(1 test\)',result)) and 'FAILURES' not in result and 'INSTRUMENTATION_FAILED' not in result
    host['phases'][phase]={'passed':phase_passed,'exit_code':executed.returncode,'force_stop':stop,'stdout':result,'stderr':executed.stderr.decode(errors='replace')}
    (out/f'theme-{phase}-instrumentation.txt').write_text(result+executed.stderr.decode(errors='replace'))
    (out/'theme-host.json').write_text(json.dumps(host,indent=2)+'\n')
    harvest_theme()
    if not phase_passed:
        (out/'report.json').write_text(json.dumps({'passed':False,'stage':'theme-'+phase,'source_sha':host['source_sha'],'instrumentation':result},indent=2))
        (out/'theme-failure-logcat.txt').write_text(shell('logcat -d -v brief'))
        raise AssertionError('Theme UI phase failed: '+phase+'; see raw instrumentation and capture attempts')
host['passed']=True
(out/'theme-host.json').write_text(json.dumps(host,indent=2)+'\n')
theme_report=verify_product(out/'theme-product',host)
(out/'theme-report.json').write_text(json.dumps(theme_report,indent=2)+'\n')
assert theme_report['passed'],'PNG/XML/state theme gate failed: '+str(theme_report['errors'])
# Independent palette suite: real user choices, explicit light/dark + system, host-cold processes.
from verify_palette_evidence import PHASES as PALETTE_PHASES, verify_product as verify_palettes
import uuid
palette_run=str(uuid.uuid4())
palette_target=out/'palette-product'
assert not palette_target.exists(),'Palette harvest requires a new run-specific destination'
palette_target.mkdir()

def harvest_palettes():
    try:
        archive=subprocess.run(['adb','shell'],input=('run-as com.hcbiu.elcton tar -cf - -C files qa-palette-evidence/'+palette_run+'\n').encode(),capture_output=True,timeout=60)
    except subprocess.TimeoutExpired as error:
        (out/'palette-harvest-timeout-stdout.bin').write_bytes(error.stdout or b'')
        (out/'palette-harvest-timeout-stderr.bin').write_bytes(error.stderr or b'')
        raise
    if archive.returncode or not archive.stdout:
        (out/'palette-harvest-error.txt').write_text(archive.stderr.decode(errors='replace'))
        return False
    target=palette_target
    try:
        with tarfile.open(fileobj=io.BytesIO(archive.stdout),mode='r:') as captured:
            for member in captured.getmembers():
                if not member.isfile():continue
                relative=Path(member.name)
                assert relative.parts[:2]==('qa-palette-evidence',palette_run) and '..' not in relative.parts,member.name
                destination=target.joinpath(*relative.parts[2:]);destination.parent.mkdir(parents=True,exist_ok=True)
                content=captured.extractfile(member);assert content is not None
                destination.write_bytes(content.read())
        return True
    except (tarfile.TarError,AssertionError) as error:
        (out/'palette-harvest-error.txt').write_text(str(error))
        return False

def execute_palette_phase(phase,command,stop):
    timeout_error=None
    try:
        executed=subprocess.run(['adb','shell'],input=(command+'\n').encode(),capture_output=True,timeout=600)
        stdout,stderr,exit_code=executed.stdout,executed.stderr,executed.returncode
    except subprocess.TimeoutExpired as error:
        timeout_error=error
        stdout,stderr,exit_code=error.stdout or b'',error.stderr or b'',None
    # Preserve the exact wire bytes as well as readable output before any fallible harvest/logcat.
    (out/f'palette-{phase}-stdout.bin').write_bytes(stdout)
    (out/f'palette-{phase}-stderr.bin').write_bytes(stderr)
    result=stdout.decode(errors='replace');errors=stderr.decode(errors='replace')
    phase_passed=timeout_error is None and exit_code==0 and bool(re.search(r'OK \(1 test\)',result)) and 'FAILURES' not in result and 'INSTRUMENTATION_FAILED' not in result
    palette_host['phases'][phase]={'passed':phase_passed,'exit_code':exit_code,'timed_out':timeout_error is not None,'force_stop':stop,'stdout':result,'stderr':errors}
    (out/f'palette-{phase}-instrumentation.txt').write_text(result+errors)
    (out/'palette-host.json').write_text(json.dumps(palette_host,indent=2)+'\n')
    if not phase_passed:
        (out/'report.json').write_text(json.dumps({'passed':False,'stage':'palette-'+phase,'source_sha':palette_host['source_sha'],'instrumentation':result,'stderr':errors,'timed_out':timeout_error is not None},indent=2))
    try:
        collected=harvest_palettes()
    except Exception as error:
        collected=False
        (out/'palette-harvest-error.txt').write_text(type(error).__name__+': '+str(error))
    if not phase_passed or not collected:
        (out/'report.json').write_text(json.dumps({'passed':False,'stage':'palette-'+phase,'source_sha':palette_host['source_sha'],'instrumentation':result,'stderr':errors,'timed_out':timeout_error is not None,'harvested':collected},indent=2))
        try: (out/'palette-failure-logcat.txt').write_text(shell('logcat -d -v brief'))
        except Exception as error:
            if isinstance(error,subprocess.TimeoutExpired):
                (out/'palette-logcat-timeout-stdout.bin').write_bytes(error.stdout or b'')
                (out/'palette-logcat-timeout-stderr.bin').write_bytes(error.stderr or b'')
            (out/'palette-logcat-error.txt').write_text(type(error).__name__+': '+str(error))
        if timeout_error is not None: raise timeout_error
        raise AssertionError('Palette phase failed: '+phase+'; preserve raw output/attempts')

palette_host={'passed':False,'qa_run':palette_run,'source_sha':sources[0].read_text().strip(),'navigation_mode':navigation_mode,'phases':{}}
for phase in PALETTE_PHASES:
    shell('am force-stop com.hcbiu.elcton');shell('am force-stop com.hcbiu.elcton.test')
    stop={'target_pid_after':shell('pidof com.hcbiu.elcton; test "$?" -le 1').strip(),'test_pid_after':shell('pidof com.hcbiu.elcton.test; test "$?" -le 1').strip()}
    assert stop['target_pid_after']==stop['test_pid_after']=='','Palette process not cold'
    if phase=='warm':shell('cmd uimode night no')
    # Keep explicit modes under the opposite real system night state.
    if phase.startswith('cold-') and phase!='cold-system':shell('cmd uimode night '+('yes' if phase.endswith('-light') else 'no'))
    command=('am instrument -w -r -e navigation_mode '+navigation_mode+' -e palette_phase '+phase+' -e palette_run '+palette_run+
        ' -e previous_force_stop true -e class com.hcbiu.elcton.PaletteUiTest com.hcbiu.elcton.test/androidx.test.runner.AndroidJUnitRunner')
    execute_palette_phase(phase,command,stop)
palette_host['passed']=True
(out/'palette-host.json').write_text(json.dumps(palette_host,indent=2)+'\n')
palette_report=verify_palettes(out/'palette-product',palette_host)
(out/'palette-report.json').write_text(json.dumps(palette_report,indent=2)+'\n')
assert palette_report['passed'],'Independent palette pixel/cold gate failed: '+str(palette_report['errors'])
# Both added suites really end in PURPLE+DARK through UI; legacy tests remain frozen.
shell('am force-stop com.hcbiu.elcton');shell('cmd uimode night no')
assert 'name="mode">DARK<' in shell('run-as com.hcbiu.elcton cat shared_prefs/ui-theme.xml'),'Legacy test requires an actual stored dark selection'
command='am instrument -w -r -e navigation_mode '+navigation_mode+' -e class com.hcbiu.elcton.ProductUiTest com.hcbiu.elcton.test/androidx.test.runner.AndroidJUnitRunner'
# Preserve a live host-side log even if the emulator/ADB dies during instrumentation.
with (out/'logcat-live.txt').open('wb') as log:
    live=subprocess.Popen(['adb','logcat','-v','brief'],stdout=log,stderr=subprocess.STDOUT)
    try:
        executed=subprocess.run(['adb','shell'],input=(command+'\n').encode(),capture_output=True,timeout=420)
    finally:
        live.terminate()
        try:live.wait(timeout=10)
        except subprocess.TimeoutExpired:live.kill();live.wait()
(out/'instrumentation.txt').write_text(executed.stdout.decode(errors='replace'))
(out/'instrumentation-stderr.txt').write_text(executed.stderr.decode(errors='replace'))
result=executed.stdout.decode(errors='replace')
if executed.returncode:
    preserve_failure(executed)
    raise RuntimeError('Instrumentation or emulator disconnected; preserved output and live logcat')
archive=subprocess.run(['adb','shell'],input=b'run-as com.hcbiu.elcton tar -cf - -C files qa-evidence\n',capture_output=True,check=True)
product=out/'product';product.mkdir(exist_ok=True)
with tarfile.open(fileobj=io.BytesIO(archive.stdout),mode='r:') as captured:
    for member in captured.getmembers():
        if not member.isfile():continue
        name=Path(member.name).name
        assert member.name in ('qa-evidence/'+name,'qa-evidence/./'+name),member.name
        contents=captured.extractfile(member)
        assert contents is not None
        (product/name).write_bytes(contents.read())
logs=shell('logcat -d -v brief');(out/'logcat.txt').write_text(logs)
passed=bool(re.search(r'OK \(1 test\)',result)) and 'FAILURES' not in result and 'INSTRUMENTATION_FAILED' not in result
if not passed:
    (out/'report.json').write_text(json.dumps({'passed':False,'source_sha':sources[0].read_text().strip(),'instrumentation':result},indent=2))
    raise AssertionError(result)
# Keep a fail-closed report until every gate (including screenshot pixels) passes.
(out/'report.json').write_text(json.dumps({'passed':False,'stage':'verification-pending','source_sha':sources[0].read_text().strip(),'instrumentation':result},indent=2))
shots=[];hierarchies=[];ime_checks=[]
for p in sorted((out/'product').rglob('*.png')):
    im=Image.open(p).convert('RGB');stats=ImageStat.Stat(im);entry={'name':p.name,'size':list(im.size),'mean':sum(stats.mean)/3,'stddev':sum(stats.stddev)/3}
    assert entry['mean']>10 and entry['stddev']>12,'Blank framebuffer '+str(entry)
    shots.append(entry)
    xml=p.with_suffix('.xml');assert xml.is_file() and xml.stat().st_size>100,'Missing hierarchy '+p.name
    root=ET.parse(xml).getroot();packages=sorted({value for node in root.iter('node') if (value:=node.get('package'))})
    assert packages,'Hierarchy has no windows '+p.name
    hierarchies.append({'name':xml.name,'packages':packages})
    state=json.loads(p.with_name(p.stem+'-state.json').read_text())
    if p.stem=='29-keyboard-visible':
        bottom=state['navigationBottom'];assert state['imeVisible'] and isinstance(bottom,(int,float)) and bottom<im.height*.78,'Keyboard did not resize the app viewport'
        nav=[int(state['navigationTop']),int(bottom)-1]
        assert nav[1]-nav[0]>=180 and nav[1]<im.height*.78,('Navigation is not visible above keyboard',nav)
        for y in (nav[0]+10,nav[1]-10):
            assert im.getpixel((1,y))==(12,15,21),('Navigation color mismatch',y,im.getpixel((1,y)))
        sample=[cast(tuple[int,int,int],im.getpixel((x,y))) for y in range(nav[1]+90,im.height-170,8) for x in range(12,im.width-12,8)]
        fraction=sum(min(rgb)>180 for rgb in sample)/len(sample);assert fraction>.45,('No rendered input-method keyboard',fraction)
        ime_checks.append({'file':p.name,'navigation':nav,'keyboard_bright_fraction':fraction,'passed':True})
assert len(shots)==28 and len(hierarchies)==28 and len(ime_checks)==1,'Incomplete component-tour coverage'
assert not re.search(r'FATAL EXCEPTION[\s\S]{0,1000}Process: com\.hcbiu\.elcton',logs),'Application crashed'
pixel_run=subprocess.run([sys.executable,'qa/verify_system_bars.py','--product',str(product),'--out',str(out/'system-bar-pixels.json')],capture_output=True,text=True)
(out/'system-bar-pixels.log').write_text(pixel_run.stdout+pixel_run.stderr)
pixels=json.loads((out/'system-bar-pixels.json').read_text()) if (out/'system-bar-pixels.json').is_file() else {'passed':False}
passed=pixel_run.returncode==0 and pixels.get('passed') is True
(out/'report.json').write_text(json.dumps({'passed':passed,'scope':'product UI/real APK in Android emulator; no physical paired watch','source_sha':sources[0].read_text().strip(),'shots':shots,'hierarchies':hierarchies,'keyboard_pixel_checks':ime_checks,'system_bar_pixels':pixels,'theme_ui':theme_report,'palette_ui':palette_report,'instrumentation':result},indent=2))
print(json.dumps({'passed':passed,'screenshots':len(shots),'pixel_scenes':pixels.get('scenes',0)}))
assert passed,'System bar pixels failed; see system-bar-pixels.json and .log'
