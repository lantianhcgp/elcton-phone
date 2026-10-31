from pathlib import Path
from typing import cast
import subprocess,sys,re,json,io,tarfile,xml.etree.ElementTree as ET
from PIL import Image,ImageStat
out=Path('qa-evidence');out.mkdir(exist_ok=True)
main=list(Path('incoming').rglob('elcton-phone-probe.apk'))
tests=list(Path('incoming').rglob('elcton-ui-tests.apk'))
assert len(main)==1 and len(tests)==1,(main,tests)
sources=list(Path('incoming').rglob('source-sha.txt'))
assert len(sources)==1 and sources[0].read_text().strip()==subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),'APK/test/source identity mismatch'
def shell(command):
    return subprocess.run(['adb','shell'],input=(command+'\n').encode(),capture_output=True,check=True).stdout.decode(errors='replace')
for apk in (main[0],tests[0]):subprocess.run(['adb','install','-r',str(apk)],check=True)
shell('pm clear com.hcbiu.elcton');shell('svc power stayon true');shell('settings put system screen_off_timeout 2147483647');shell('input keyevent KEYCODE_WAKEUP');shell('wm dismiss-keyguard')
command='am instrument -w -r -e class com.hcbiu.elcton.ProductUiTest com.hcbiu.elcton.test/androidx.test.runner.AndroidJUnitRunner'
result=shell(command);(out/'instrumentation.txt').write_text(result)
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
        ys=[y for y in range(60,im.height-120) if max(abs(cast(tuple[int,int,int],im.getpixel((1,y)))[i]-(21,26,35)[i]) for i in range(3))<=2]
        runs=[]
        for y in ys:
            if not runs or y>runs[-1][1]+1:runs.append([y,y])
            else:runs[-1][1]=y
        candidates=[r for r in runs if r[1]-r[0]>=180];assert len(candidates)==1,('Navigation band not visible',runs)
        nav=candidates[0];assert nav[1]<im.height*.78,('Keyboard screenshot is actually a full-height app',nav)
        sample=[cast(tuple[int,int,int],im.getpixel((x,y))) for y in range(nav[1]+90,im.height-170,8) for x in range(12,im.width-12,8)]
        fraction=sum(min(rgb)>180 for rgb in sample)/len(sample);assert fraction>.45,('No rendered input-method keyboard',fraction)
        ime_checks.append({'file':p.name,'navigation':nav,'keyboard_bright_fraction':fraction,'passed':True})
passed=bool(re.search(r'OK \(1 test\)',result)) and 'FAILURES' not in result and 'INSTRUMENTATION_FAILED' not in result
(out/'report.json').write_text(json.dumps({'passed':passed,'scope':'product UI/real APK in Android emulator; no physical paired watch','source_sha':sources[0].read_text().strip(),'shots':shots,'hierarchies':hierarchies,'keyboard_pixel_checks':ime_checks,'instrumentation':result},indent=2))
print(json.dumps({'passed':passed,'screenshots':len(shots)}));assert passed,result
assert len(shots)==28 and len(hierarchies)==28 and len(ime_checks)==1,'Incomplete component-tour coverage'
assert not re.search(r'FATAL EXCEPTION[\s\S]{0,1000}Process: com\.hcbiu\.elcton',logs),'Application crashed'
