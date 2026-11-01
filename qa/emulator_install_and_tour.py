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
    return subprocess.run(['adb','shell'],input=(command+'\n').encode(),capture_output=True,check=True).stdout.decode(errors='replace')
for apk in (main[0],tests[0]):subprocess.run(['adb','install','-r',str(apk)],check=True)
navigation_mode=os.environ.get('QA_NAVIGATION_MODE','three-button')
assert navigation_mode in ('three-button','gestural'),navigation_mode
overlay='com.android.internal.systemui.navbar.'+('threebutton' if navigation_mode=='three-button' else 'gestural')
shell('cmd overlay enable-exclusive --category '+overlay)
active_overlays=shell('cmd overlay list')
assert '[x] '+overlay in active_overlays,'Navigation overlay not enabled: '+active_overlays
(out/'environment.json').write_text(json.dumps({'navigation_mode':navigation_mode,'overlay':overlay,'sdk':shell('getprop ro.build.version.sdk').strip(),'overlays':active_overlays},indent=2))
shell('pm clear com.hcbiu.elcton');shell('svc power stayon true');shell('settings put system screen_off_timeout 2147483647');shell('input keyevent KEYCODE_WAKEUP');shell('wm dismiss-keyguard')
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
(out/'report.json').write_text(json.dumps({'passed':passed,'scope':'product UI/real APK in Android emulator; no physical paired watch','source_sha':sources[0].read_text().strip(),'shots':shots,'hierarchies':hierarchies,'keyboard_pixel_checks':ime_checks,'system_bar_pixels':pixels,'instrumentation':result},indent=2))
print(json.dumps({'passed':passed,'screenshots':len(shots),'pixel_scenes':pixels.get('scenes',0)}))
assert passed,'System bar pixels failed; see system-bar-pixels.json and .log'
