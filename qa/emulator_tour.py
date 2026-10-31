#!/usr/bin/env python3
"""ADB-only UI smoke tour. Runs on GitHub's emulator, not the user's phone."""
import json, re, subprocess, time, xml.etree.ElementTree as ET
from pathlib import Path
out = Path('qa-evidence'); out.mkdir(exist_ok=True)

def adb(*args):
    return subprocess.run(['adb', *args], check=True, capture_output=True)

def shell(command):
    return subprocess.run(['adb','shell'], input=(command+'\n').encode(), check=True, capture_output=True).stdout.decode(errors='replace')

def nodes():
    shell('uiautomator dump /sdcard/ui.xml')
    adb('pull','/sdcard/ui.xml',str(out/'latest.xml'))
    return ET.parse(out/'latest.xml').getroot()

def wait_text(text, timeout=20):
    end=time.monotonic()+timeout
    while time.monotonic()<end:
        root=nodes()
        if any(text in (n.get('text','')+' '+n.get('content-desc','')) for n in root.iter('node')): return root
        time.sleep(.3)
    raise AssertionError('Missing UI text '+text)

def tap(text):
    root=wait_text(text)
    matches=[n for n in root.iter('node') if n.get('text')==text or n.get('content-desc')==text]
    if not matches: raise AssertionError('No exact tap target '+text)
    # Tab label is a child inside its clickable parent; center lands within the same target.
    bounds=matches[-1].get('bounds',''); nums=list(map(int,re.findall(r'\d+',bounds)))
    assert len(nums)==4 and nums[2]>nums[0] and nums[3]>nums[1], bounds
    shell(f'input tap {(nums[0]+nums[2])//2} {(nums[1]+nums[3])//2}')

def capture(name):
    shell('screencap -p /sdcard/frame.png')
    adb('pull','/sdcard/frame.png',str(out/(name+'.png')))
    root=nodes(); ET.ElementTree(root).write(out/(name+'.xml'),encoding='utf-8')
    from PIL import Image, ImageStat
    im=Image.open(out/(name+'.png')).convert('RGB'); stats=ImageStat.Stat(im)
    result={'name':name,'width':im.width,'height':im.height,'mean':sum(stats.mean)/3,'stddev':sum(stats.stddev)/3}
    (out/(name+'.check.json')).write_text(json.dumps(result))
    assert result['stddev']>12 and result['mean']>10, 'Blank framebuffer: '+str(result)
    return result

shell('input keyevent KEYCODE_WAKEUP')
shell('wm dismiss-keyguard')
shell('am start -W -n com.hcbiu.elcton/.MainActivity')
wait_text('结构化课表'); shots=[capture('01-snapshot')]
tap('校验并保存到手机'); wait_text('0 条课程'); shots.append(capture('02-saved-empty'))
tap('设备');wait_text('授权并查询设备');shots.append(capture('03-device'))
tap('授权并查询设备');wait_text('操作未完成');shots.append(capture('04-health-unavailable'))
root=nodes();text=' '.join(n.get('text','') for n in root.iter('node'))
assert '同步成功' not in text, 'False success without Health service'
tap('断开并停止同步');wait_text('已断开');shots.append(capture('05-disconnected'))
tap('课表');wait_text('结构化课表');shots.append(capture('06-return'))
logs=shell('logcat -d -v brief');(out/'logcat.txt').write_text(logs)
assert not re.search(r'FATAL EXCEPTION[\s\S]{0,1000}Process: com\.hcbiu\.elcton',logs),'Application crashed'
(out/'report.json').write_text(json.dumps({'passed':True,'steps':6,'shots':shots,'scope':'UI smoke on real APK; no real Wear Engine device attached'},indent=2))
print(json.dumps({'passed':True,'steps':6,'evidence':str(out)}))
