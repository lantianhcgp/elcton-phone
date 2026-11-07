#!/usr/bin/env python3
"""Independent bound PNG/XML/state palette gate. No success from preference flags alone."""
import argparse
import hashlib
import json
import re
from pathlib import Path
import xml.etree.ElementTree as ET
from PIL import Image
try:
    from qa.verify_theme_evidence import box, inside, count_ink
except ModuleNotFoundError:
    from verify_theme_evidence import box, inside, count_ink

PALETTES = ('PURPLE', 'BLUE', 'GREEN', 'TEAL', 'ORANGE', 'PINK')
LABELS = dict(zip(PALETTES, ('紫','蓝','绿','青','橙','粉')))
# Independently pinned design roles from MCU SchemeTonalSpot/reference; never read from runtime state.
TOKENS = {
 'PURPLE': {'light': 'F9F5FF FFFBFF 6750A4 EADDFF 21005D F0EAF7 E8DEF8 21005D BA1A1A', 'dark': '0C0F15 1D192B D0BCFF 4F378B EADDFF 292338 342D42 F3EDF7 FFB4AB'},
 'BLUE': {'light': 'F9F9FF F9F9FF 3D5F90 D5E3FF 234776 E7E8EE E1E2E9 191C20 BA1A1A', 'dark': '111318 111318 A6C8FF 234776 D5E3FF 282A2F 32353A E1E2E9 FFB4AB'},
 'GREEN': {'light': 'F8FBF1 F8FBF1 3E6837 BFF0B1 275022 E6E9E0 E0E4DA 191D17 BA1A1A', 'dark': '11140F 11140F A3D397 275022 BFF0B1 272B25 323630 E0E4DA FFB4AB'},
 'TEAL': {'light': 'F4FBF9 F4FBF9 006A65 9DF2EA 00504C E3E9E8 DDE4E2 161D1C BA1A1A', 'dark': '0E1514 0E1514 81D5CE 00504C 9DF2EA 252B2A 2F3635 DDE4E2 FFB4AB'},
 'ORANGE': {'light': 'FFF8F5 FFF8F5 8B4F25 FFDBC8 6F3810 F6E5DC F0DFD7 221A15 BA1A1A', 'dark': '1A120D 1A120D FFB689 6F3810 FFDBC8 312823 3D332D F0DFD7 FFB4AB'},
 'PINK': {'light': 'FFF8F8 FFF8F8 8B4A62 FFD9E3 6F334A F4E4E7 EFDFE2 22191C BA1A1A', 'dark': '191114 191114 FFB0CA 6F334A FFD9E3 31282A 3C3235 EFDFE2 FFB4AB'},
}
ROLE_NAMES = ('background','surface','primary','primaryContainer','onPrimaryContainer','surfaceHigh','surfaceHighest','onSurface','error')
COURSE = ('8FA8FF','B49BFF','69C9B6','E7AD77','DD91B9','81BCD9','A7C57F','B5BCCA')
STATES = tuple((p,m) for p in PALETTES for m in ('LIGHT','DARK'))
PHASES = ('warm',) + tuple('cold-'+p.lower()+'-'+m.lower() for p,m in STATES) + ('system', 'cold-system')


def rgb(value):
    return tuple(int(value[i:i+2],16) for i in (0,2,4))


def roles(palette, dark):
    return dict(zip(ROLE_NAMES, map(rgb, TOKENS[palette]['dark' if dark else 'light'].split())))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def mix(base, overlay, alpha):
    return tuple(round(x*(1-alpha)+y*alpha) for x,y in zip(base,overlay))


def close(a,b,tolerance=3):
    return max(abs(x-y) for x,y in zip(a,b)) <= tolerance


def pixels(image, rect, color, tolerance=3):
    return sum(close(image.getpixel((x,y)),color,tolerance)
               for y in range(rect[1],rect[3],2) for x in range(rect[0],rect[2],2))


def required():
    names = []
    for p,m in STATES:
        key=p.lower()+'-'+m.lower()
        names.extend('r3-'+key+'-'+scene for scene in ('options','semester','editor-bottom','week','cold'))
    names.extend('r3-'+p.lower()+'-system-'+m for p in PALETTES for m in ('light','dark'))
    names.extend(('r3-system-cold','r3-restored-purple-dark'))
    return tuple(names)


def inspect_capture(picture):
    picture=Path(picture)
    result={'name':picture.stem,'passed':False,'errors':[]}
    try:
        receipt=json.loads(picture.with_name(picture.stem+'-state.json').read_text())
        xml=picture.with_suffix('.xml')
        assert receipt['pngSha256']==sha(picture) and receipt['xmlSha256']==sha(xml), 'PNG/XML capture hash mismatch'
        assert receipt['xmlStable'] is True and receipt['xmlBeforeSha256']==receipt['xmlSha256'], 'XML changed across screenshot'
        assert receipt['stable'] is True and receipt['before']==receipt['after'] and receipt['pixelReady'] is True, 'Unstable/uncommitted frame'
        assert receipt['captureId'] and receipt['name']==picture.stem, 'Unbound scene'
        state=receipt['after']; palette=state['palette']; dark=receipt['expectedDark']
        assert palette in PALETTES and palette==receipt['expectedPalette'] and type(dark) is bool
        assert state['mode'] in ('LIGHT','DARK','SYSTEM')
        if state['scene']=='options': assert state['modeSelected']==state['mode'], 'Mode control is not selected'
        assert dark==(state['systemDark'] if state['mode']=='SYSTEM' else state['mode']=='DARK'), 'Mode/palette not orthogonal'
        expected=roles(palette,dark)
        argb=0xFF000000 | (expected['background'][0]<<16) | (expected['background'][1]<<8) | expected['background'][2]
        assert state['chromeArgb']==argb-(1<<32), 'System chrome did not follow full scheme'
        assert state['uiFlags']&8208==(0 if dark else 8208), 'System icon polarity'
        assert state['imeVisible'] is False, 'Unexpected keyboard in palette evidence'
        image=Image.open(picture).convert('RGB'); width,height=image.size
        assert (width,height)==(state['screenWidth'],state['screenHeight'])
        nav_top,nav_bottom=int(state['navigationTop']),int(state['navigationBottom'])
        assert state['statusBarHeight']<nav_top<nav_bottom<=height
        for y in (10,height//3,nav_bottom-10,height-8):
            for x in (1,2,width-3,width-2):
                assert image.getpixel((x,y))==expected['background'], 'Framebuffer palette differs from persisted selection'
        app=[n for n in ET.parse(xml).getroot().iter('node') if n.get('package')=='com.hcbiu.elcton']
        assert app, 'No actual App hierarchy'
        today=[n for n in app if n.get('text')=='今日']; assert today, 'Navigation label missing'
        label=box(today[0].get('bounds')); assert inside(label,width,height)
        assert count_ink(image,label,dark)>=12, 'Navigation glyphs not composed'
        scene=state['scene']; metrics={'palette':palette,'theme':state['mode'],'dark':dark,'pid':state['pid'],'scene':scene,'captureId':receipt['captureId']}
        density=state['density']; assert isinstance(density,(int,float)) and 0<density<=5
        if scene=='options':
            opts=state['paletteOptions']; assert set(opts)==set(PALETTES), 'Six palette bounds required'
            assert [p for p in PALETTES if opts[p]['selected']]==[palette], 'Exactly one palette must be selected'
            for p in PALETTES:
                r=box(opts[p]['bounds']); assert inside(r,width,height) and r[1]>=state['statusBarHeight'] and r[3]<=nav_top+3, 'Palette control clipped/under navigation'
                assert r[3]-r[1]>=48*density-3, 'Palette touch area smaller than 48dp'
                base=expected['primaryContainer'] if p==palette else expected['surfaceHigh']
                padding=max(4,round(density*5))
                probes=[(r[0]+padding,(r[1]+r[3])//2+offset) for offset in (0,1,2)]
                assert all(close(image.getpixel(point),base) for point in probes), 'Palette option has foreign/contrasting tonal container'
                assert pixels(image,r,roles(p,dark)['primary'])>=20, 'Palette round preview is absent or not scheme-bound'
                label_nodes=[n for n in app if n.get('text')==LABELS[p]]; assert len(label_nodes)==1, 'Chinese palette label missing/duplicated'
                label_box=box(label_nodes[0].get('bounds')); assert inside(label_box,width,height)
                assert pixels(image,label_box,expected['onPrimaryContainer'] if p==palette else expected['onSurface'])>=4, 'Palette label ink not composed'
                if p==palette:
                    strip=(r[0]+r[2])//2
                    assert any(close(image.getpixel((strip,y)),expected['primary']) for y in range(r[1],r[1]+max(3,round(3*density)))), 'Selection outline not rendered'
            metrics['palette_options']=6
        elif scene=='semester':
            r=box(state['semesterBounds']); assert inside(r,width,height) and r[3]<nav_top, 'Date field clipped'
            inset=max(3,round(8*density)); point=(r[0]+inset,r[1]+(r[3]-r[1])//2)
            assert close(image.getpixel(point),mix(expected['primaryContainer'],expected['surface'],.24)), 'Date field jumps out of its tonal parent'
            assert pixels(image,r,expected['onPrimaryContainer'])>=12, 'Date field content not rendered'
            metrics['nested_field_sample']=image.getpixel(point)
        elif scene=='editor-bottom':
            opts=state['courseColorBounds']; assert set(opts)==set(str(i) for i in range(8)), 'Eight business colors missing'
            for i,raw in enumerate(COURSE):
                r=box(opts[str(i)]); assert inside(r,width,height) and r[3]<nav_top, 'Business color point clipped'
                assert pixels(image,r,mix(expected['surfaceHighest'],rgb(raw),.30 if dark else .46))>=12, 'Untoned or wrong business color point'
            r=box(state['deleteBounds']); assert inside(r,width,height) and r[3]<nav_top
            assert pixels(image,r,expected['error'])>=12, 'Delete semantic ink missing'
            center=((r[0]+r[2])//2,r[1]+max(5,round(6*density)))
            assert close(image.getpixel(center),expected['background']), 'Deletion competes as filled primary action'
            metrics['business_colors']=8
        elif scene!='week':
            raise AssertionError('Unsupported scene')
        assert isinstance(state['businessHashes'],dict) and state['businessHashes'], 'No business preservation snapshot'
        result.update(passed=True,metrics=metrics)
    except (AssertionError,OSError,ValueError,TypeError,KeyError,ET.ParseError) as error:
        result['errors'].append(str(error))
    return result


def check_processes(processes,host_phases):
    errors=[]
    if len(set(p.get('pid') for p in processes.values()))!=len(processes):
        errors.append('Cold phases reuse an actual process')
    for phase in processes:
        h=host_phases.get(phase,{})
        stop=h.get('force_stop',{})
        if stop.get('target_pid_after')!='' or stop.get('test_pid_after')!='':
            errors.append(phase+': no verified force-stop')
        if h.get('exit_code')!=0 or h.get('passed') is not True or 'OK (1 test)' not in h.get('stdout',''):
            errors.append(phase+': instrumentation not passed')
    return errors


def verify_product(product,host):
    product=Path(product); reports=[inspect_capture(product/(name+'.png')) for name in required()]
    errors=[r['name']+': '+str(r['errors']) for r in reports if not r['passed']]
    processes={}
    for phase in PHASES:
        try:
            r=json.loads((product/('r3-'+phase+'-result.json')).read_text())
            assert r['passed'] is True and r['phase']==phase and r['navigationMode']==host['navigation_mode']
            assert r['businessBefore']==r['businessAfter'], 'Palette choices changed business files'
            processes[phase]=r
        except (AssertionError,OSError,ValueError,KeyError) as error:
            errors.append(phase+': '+str(error))
    errors.extend(check_processes(processes,host.get('phases',{})))
    lookup={r['name']:r.get('metrics',{}) for r in reports}
    for p,m in STATES:
        key='r3-'+p.lower()+'-'+m.lower()
        for suffix in ('options','semester','editor-bottom','week','cold'):
            row=lookup[key+'-'+suffix]
            if (row.get('palette'),row.get('theme'),row.get('dark'))!=(p,m,m=='DARK'):
                errors.append(key+'-'+suffix+': missing requested combination')
        for mode in ('light','dark'):
            row=lookup['r3-'+p.lower()+'-system-'+mode]
            if (row.get('palette'),row.get('theme'),row.get('dark'))!=(p,'SYSTEM',mode=='dark'):
                errors.append(p+': SYSTEM combination missing')
    return {'passed':not errors,'source_sha':host['source_sha'],'navigation_mode':host['navigation_mode'],
            'screenshots':len(reports),'phase_process_ids':{k:v['pid'] for k,v in processes.items()},'scenes':reports,
            'errors':errors,'scope':'Actual emulator signed APK, independent pixels + cold processes; not physical/watch acceptance'}


def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--product',type=Path,required=True); parser.add_argument('--host',type=Path,required=True); parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args(); report=verify_product(args.product,json.loads(args.host.read_text()))
    args.out.write_text(json.dumps(report,indent=2)+'\n'); print(json.dumps({k:report[k] for k in ('passed','screenshots','errors')}))
    raise SystemExit(0 if report['passed'] else 1)


if __name__=='__main__':
    main()
