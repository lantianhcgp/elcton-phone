from pathlib import Path
import subprocess,sys,re,json
from PIL import Image,ImageStat
out=Path('qa-evidence');out.mkdir(exist_ok=True)
main=list(Path('incoming').rglob('elcton-phone-probe.apk'))
tests=list(Path('incoming').rglob('elcton-ui-tests.apk'))
assert len(main)==1 and len(tests)==1,(main,tests)
def shell(command):
    return subprocess.run(['adb','shell'],input=(command+'\n').encode(),capture_output=True,check=True).stdout.decode(errors='replace')
for apk in (main[0],tests[0]):subprocess.run(['adb','install','-r',str(apk)],check=True)
shell('pm clear com.hcbiu.elcton');shell('svc power stayon true');shell('settings put system screen_off_timeout 2147483647');shell('input keyevent KEYCODE_WAKEUP');shell('wm dismiss-keyguard')
command='am instrument -w -r -e class com.hcbiu.elcton.ProductUiTest com.hcbiu.elcton.test/androidx.test.runner.AndroidJUnitRunner'
result=shell(command);(out/'instrumentation.txt').write_text(result)
subprocess.run(['adb','pull','/sdcard/Download/elcton-qa',str(out/'product')],check=False)
logs=shell('logcat -d -v brief');(out/'logcat.txt').write_text(logs)
shots=[]
for p in sorted((out/'product').rglob('*.png')):
    im=Image.open(p).convert('RGB');stats=ImageStat.Stat(im);entry={'name':p.name,'size':list(im.size),'mean':sum(stats.mean)/3,'stddev':sum(stats.stddev)/3}
    assert entry['mean']>10 and entry['stddev']>12,'Blank framebuffer '+str(entry)
    shots.append(entry)
passed=bool(re.search(r'OK \(1 test\)',result)) and 'FAILURES' not in result and 'INSTRUMENTATION_FAILED' not in result
(out/'report.json').write_text(json.dumps({'passed':passed,'scope':'product UI/real APK in Android emulator; no physical paired watch','shots':shots,'instrumentation':result},indent=2))
print(json.dumps({'passed':passed,'screenshots':len(shots)}));assert passed,result
assert len(shots)>=17,'Incomplete component-tour coverage'
assert not re.search(r'FATAL EXCEPTION[\s\S]{0,1000}Process: com\.hcbiu\.elcton',logs),'Application crashed'
