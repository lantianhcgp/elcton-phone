#!/usr/bin/env python3
"""Synthetic fail-closed fixture tests only; these are never advertised as actual APK evidence."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from PIL import Image, ImageDraw
from qa.verify_palette_evidence import inspect_capture, check_processes, check_capture_provenance, mix, rgb, roles, COURSE, valid_business_snapshot


class PaletteEvidenceTest(unittest.TestCase):
    def fixture(self, directory, bad_container=False, wrong_palette=False, duplicate=False, checkmark=True):
        root = Path(directory)
        picture = root/'r3-purple-light-options.png'
        image = Image.new('RGB', (360, 800), (249, 245, 255) if not wrong_palette else (249, 249, 255))
        draw = ImageDraw.Draw(image)
        draw.rectangle((22, 674, 48, 690), fill=(98, 86, 113))
        draw.rectangle((160, 766, 200, 780), fill=(80, 80, 80))
        specs = {'PURPLE': ('紫', '6750A4'), 'BLUE': ('蓝', '3D5F90'), 'GREEN': ('绿', '3E6837'), 'TEAL': ('青', '006A65'), 'ORANGE': ('橙', '8B4F25'), 'PINK': ('粉', '8B4A62')}
        options = {}
        xml = '<hierarchy><node package="com.hcbiu.elcton" text="今日" bounds="[20,672][50,694]"/>'
        for i, (name, (label, primary)) in enumerate(specs.items()):
            x, y = 20+i%3*105, 160+i//3*80
            selected = name=='PURPLE' or (duplicate and name=='BLUE')
            options[name] = {'bounds': [x,y,x+95,y+60], 'selected': selected,
                             'previewBounds':[x+12,y+18,x+36,y+42],'labelBounds':[x+44,y+24,x+66,y+46]}
            base = (234,221,255) if selected else (240,234,247)
            draw.rectangle((x,y,x+94,y+59), fill=base)
            if selected:
                draw.rectangle((x,y,x+94,y+1), fill=(103,80,164))
            draw.ellipse((x+12,y+18,x+35,y+41), fill='#'+primary)
            if selected and checkmark:
                draw.line([(x+19,y+29),(x+23,y+33),(x+29,y+24)],fill=(255,255,255),width=3)
            draw.rectangle((x+44,y+28,x+55,y+39), fill=(33,0,93))
            # Actual API33 shape: checked semantics live on the option parent; RadioButton is decorative.
            xml += (f'<node package="com.hcbiu.elcton" class="android.view.View" checkable="true" checked="{str(selected).lower()}" selected="false" bounds="[{x},{y}][{x+95},{y+60}]">'
                    f'<node package="com.hcbiu.elcton" text="{label}" selected="false" bounds="[{x+44},{y+24}][{x+66},{y+46}]"/>'
                    f'<node package="com.hcbiu.elcton" class="android.widget.RadioButton" checkable="false" checked="false" selected="false" bounds="[{x},{y}][{x+95},{y+60}]"/></node>')
        xml += '</hierarchy>'
        if bad_container:
            draw.rectangle((24,187,27,193), fill=(12,15,21))
        image.save(picture)
        hierarchy = picture.with_suffix('.xml'); hierarchy.write_text(xml)
        state = {'mode':'LIGHT','palette':'PURPLE','systemDark':True,'pid':120,'navigationMode':'three-button',
            'screenWidth':360,'screenHeight':800,'navigationTop':640,'navigationBottom':750,
            'statusBarHeight':24,'systemNavigationHeight':50,'imeVisible':False,'chromeArgb':-395777,'uiFlags':8208,
            'paletteOptions':options,'modeSelected':'LIGHT','businessHashes':{'timetable.json':'a'*64,'timetable-last-good.json':'b'*64,'timetable.json.bak':'ABSENT','timetable-last-good.json.bak':'ABSENT'},'scene':'options',
            'density':1.0,'qaRun':'synthetic-run'}
        sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
        receipt = {'name':picture.stem,'phase':'warm','qaRun':'synthetic-run','captureId':'synthetic-unit-only','stable':True,'xmlStable':True,
            'pixelReady':True,'expectedDark':False,'expectedPalette':'PURPLE','before':state,'after':state.copy(),
            'pngSha256':sha(picture),'xmlSha256':sha(hierarchy),'xmlBeforeSha256':sha(hierarchy)}
        picture.with_name(picture.stem+'-state.json').write_text(json.dumps(receipt))
        return picture

    def test_valid_bound_options_fixture_is_accepted(self):
        with tempfile.TemporaryDirectory() as directory:
            result = inspect_capture(self.fixture(directory))
            self.assertTrue(result['passed'], result)

    def test_correct_preferences_but_wrong_framebuffer_palette_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            self.assertFalse(inspect_capture(self.fixture(directory, wrong_palette=True))['passed'])

    def test_two_selected_palettes_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            self.assertFalse(inspect_capture(self.fixture(directory, duplicate=True))['passed'])

    def test_corrupt_nested_tonal_container_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            self.assertFalse(inspect_capture(self.fixture(directory, bad_container=True))['passed'])

    def test_changed_xml_is_rejected_even_if_state_flags_are_green(self):
        with tempfile.TemporaryDirectory() as directory:
            picture = self.fixture(directory)
            picture.with_suffix('.xml').write_text('<hierarchy/>')
            self.assertFalse(inspect_capture(picture)['passed'])

    def test_missing_option_and_stale_process_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            picture = self.fixture(directory)
            path = picture.with_name(picture.stem+'-state.json')
            receipt = json.loads(path.read_text()); receipt['before']['paletteOptions'].pop('TEAL'); receipt['after']['paletteOptions'].pop('TEAL')
            path.write_text(json.dumps(receipt))
            self.assertFalse(inspect_capture(picture)['passed'])
        host={k:{'force_stop':{'target_pid_after':'','test_pid_after':''},'exit_code':0,'passed':True,'stdout':'OK (1 test)'} for k in ('a','b')}
        phases={'a':{'pid':22},'b':{'pid':23}}
        self.assertEqual([],check_processes(phases,host))
        phases['b']['pid']=22
        self.assertEqual(['Cold phases reuse an actual process'],check_processes(phases,host))

    def editor_fixture(self, directory, raw_colors=False, selected_indicator=True):
        root=Path(directory);options=self.fixture(directory)
        receipt=json.loads(options.with_name(options.stem+'-state.json').read_text())
        p=root/'r3-purple-light-editor-bottom.png'
        image=Image.new('RGB',(360,800),(249,245,255));draw=ImageDraw.Draw(image)
        draw.rectangle((22,674,48,690),fill=(98,86,113))
        color_bounds={};tokens=roles('PURPLE',False)
        for i,color in enumerate(COURSE):
            x=20+i*40;y=450
            color_bounds[str(i)]=[x,y,x+38,y+48]
            color=rgb(color) if raw_colors else mix(tokens['surfaceHighest'],rgb(color),.46)
            draw.ellipse((x+4,y+9,x+33,y+38),fill=color)
            if i==0 and selected_indicator:
                draw.ellipse((x+4,y+9,x+33,y+38),outline=tokens['primary'],width=2)
                draw.line([(x+14,y+24),(x+18,y+28),(x+25,y+19)],fill=tokens['onSurface'],width=3)
        draw.rectangle((140,530,205,545),fill=tokens['error'])
        receipt['name']=p.stem;receipt['phase']='warm'
        for key in ('before','after'):
            receipt[key].update(scene='editor-bottom',courseColorBounds=color_bounds,courseColorsSelected=[0],deleteBounds=[20,510,340,566])
        # Compose accessibility expands a narrow clickable slot to 48dp and later siblings clip overlap.
        # These are fixture inputs, not device receipts; all existing test assertions remain unchanged.
        touch_bounds={str(i):[b[0]-5,b[1],b[2]+5,b[3]] for i,b in enumerate(color_bounds.values())}
        for key in ('before','after'):
            receipt[key].update(courseColorTouchBounds=touch_bounds,courseColorLabelBounds=[20,412,128,434])
        draw.rectangle((22,416,124,430),fill=tokens['primary'])
        controls='<node package="com.hcbiu.elcton" text="课程颜色" bounds="[20,412][128,434]"/>'
        for i,b in enumerate(touch_bounds.values()):
            right=min(b[2],touch_bounds[str(i+1)][0]) if i<7 else b[2]
            controls+=(f'<node package="com.hcbiu.elcton" class="android.view.View" checkable="true" checked="{str(i==0).lower()}" '
                       f'clickable="{str(i!=0).lower()}" enabled="true" visible-to-user="true" bounds="[{b[0]},{b[1]}][{right},{b[3]}]"/>')
        image.save(p);p.with_suffix('.xml').write_text('<hierarchy><node package="com.hcbiu.elcton" text="今日" bounds="[20,672][50,694]"/><node package="com.hcbiu.elcton" class="android.view.View" bounds="[15,400][345,500]">'+controls+'</node><node package="com.hcbiu.elcton" class="android.view.View" bounds="[20,510][340,566]"><node package="com.hcbiu.elcton" text="删除课程" bounds="[140,530][205,546]"/></node></hierarchy>')
        receipt['pngSha256']=hashlib.sha256(p.read_bytes()).hexdigest()
        receipt['xmlSha256']=receipt['xmlBeforeSha256']=hashlib.sha256(p.with_suffix('.xml').read_bytes()).hexdigest()
        p.with_name(p.stem+'-state.json').write_text(json.dumps(receipt))
        return p

    def test_valid_editor_frame_and_only_raw_color_mutation_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            valid=inspect_capture(self.editor_fixture(d))
            self.assertTrue(valid['passed'],valid)
            raw=inspect_capture(self.editor_fixture(d,raw_colors=True))
            self.assertFalse(raw['passed'],raw)
            self.assertIn('Untoned or wrong business color point',str(raw['errors']))

    def test_delete_button_can_touch_but_never_cross_navigation(self):
        with tempfile.TemporaryDirectory() as d:
            p=self.editor_fixture(d); path=p.with_name(p.stem+'-state.json')
            receipt=json.loads(path.read_text())
            for key in ('before','after'):
                receipt[key]['deleteBounds'][3]=receipt[key]['navigationTop']
            xml=p.with_suffix('.xml');xml.write_text(xml.read_text().replace('[20,510][340,566]','[20,510][340,640]'))
            receipt['xmlSha256']=receipt['xmlBeforeSha256']=hashlib.sha256(xml.read_bytes()).hexdigest()
            path.write_text(json.dumps(receipt))
            touching=inspect_capture(p);self.assertTrue(touching['passed'],touching)
            for key in ('before','after'):receipt[key]['deleteBounds'][3]+=1
            path.write_text(json.dumps(receipt))
            crossing=inspect_capture(p);self.assertFalse(crossing['passed'],crossing)
            self.assertIn('Delete button crosses navigation',str(crossing['errors']))

    def test_delete_xml_cannot_be_stale_even_when_its_hashes_are_consistent(self):
        with tempfile.TemporaryDirectory() as d:
            p=self.editor_fixture(d);valid=inspect_capture(p);self.assertTrue(valid['passed'],valid)
            xml=p.with_suffix('.xml');xml.write_text(xml.read_text().replace('[20,510][340,566]','[20,500][340,556]'))
            path=p.with_name(p.stem+'-state.json');receipt=json.loads(path.read_text())
            receipt['xmlSha256']=receipt['xmlBeforeSha256']=hashlib.sha256(xml.read_bytes()).hexdigest();path.write_text(json.dumps(receipt))
            invalid=inspect_capture(p);self.assertFalse(invalid['passed'],invalid)
            self.assertIn('Delete XML/state bounds disagree',str(invalid['errors']))

    def test_filename_cannot_bypass_requested_editor_scene(self):
        with tempfile.TemporaryDirectory() as d:
            p=self.editor_fixture(d);path=p.with_name(p.stem+'-state.json')
            receipt=json.loads(path.read_text());receipt['before']['scene']=receipt['after']['scene']='week'
            path.write_text(json.dumps(receipt))
            self.assertFalse(inspect_capture(p)['passed'])

    def test_cold_capture_pid_phase_and_unique_id_are_actually_bound(self):
        snapshot={'timetable.json':'a'*64,'timetable-last-good.json':'b'*64,'timetable.json.bak':'ABSENT','timetable-last-good.json.bak':'ABSENT'}
        states={'cold-purple-light':{'pid':130,'qaRun':'synthetic-run','businessBefore':snapshot}}
        row={'name':'r3-purple-light-cold','passed':True,'metrics':{'phase':'cold-purple-light','pid':130,
             'businessHashes':{'timetable.json':'a'*64,'timetable-last-good.json':'b'*64,'timetable.json.bak':'ABSENT','timetable-last-good.json.bak':'ABSENT'},'navigationMode':'three-button','qaRun':'synthetic-run','captureId':'capture-1'}}
        self.assertEqual([],check_capture_provenance([row],states,'three-button','synthetic-run'))
        row['metrics']['pid']=120
        self.assertIn('capture PID',str(check_capture_provenance([row],states,'three-button','synthetic-run')))
        row['metrics']['pid']=130
        row['metrics']['phase']='warm'
        self.assertTrue(check_capture_provenance([row],states,'three-button','synthetic-run'))
        row['metrics']['phase']='cold-purple-light'
        self.assertIn('reused capture identity',str(check_capture_provenance([row,row],states,'three-button','synthetic-run')))
        row['metrics']['qaRun']='previous-run'
        self.assertIn('run identity differs',str(check_capture_provenance([row],states,'three-button','synthetic-run')))

    def test_verified_stop_is_independent_of_pid_reuse_test(self):
        host={'cold':{'force_stop':{'target_pid_after':'','test_pid_after':''},'exit_code':0,'passed':True,'stdout':'OK (1 test)'}}
        self.assertEqual([],check_processes({'cold':{'pid':123}},host))
        host['cold']['force_stop']['target_pid_after']='122'
        self.assertEqual(['cold: no verified force-stop'],check_processes({'cold':{'pid':123}},host))

    def test_palette_verifier_rejects_incomplete_business_hashes(self):
        with tempfile.TemporaryDirectory() as d:
            p=self.fixture(d)
            state=p.with_name(p.stem+'-state.json');r=json.loads(state.read_text())
            for key in ('before','after'):
                r[key]['businessHashes']={'timetable.json':'abc'}
            state.write_text(json.dumps(r))
            self.assertFalse(inspect_capture(p)['passed'])

    def test_options_frame_with_consistent_week_metadata_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p=self.fixture(d);r=json.loads(p.with_name(p.stem+'-state.json').read_text())
            week=p.with_name('r3-purple-light-week.png');week.write_bytes(p.read_bytes())
            week.with_suffix('.xml').write_bytes(p.with_suffix('.xml').read_bytes());r['name']=week.stem
            for key in ('before','after'):r[key]['scene']='week'
            week.with_name(week.stem+'-state.json').write_text(json.dumps(r))
            self.assertFalse(inspect_capture(week)['passed'])

    def test_editor_frame_without_selected_indicator_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            valid=inspect_capture(self.editor_fixture(d));self.assertTrue(valid['passed'],valid)
            invalid=inspect_capture(self.editor_fixture(d,selected_indicator=False))
            self.assertFalse(invalid['passed'])
            self.assertIn('Selected course outline',str(invalid['errors']))

    def week_fixture(self, directory, time_fill='tonal'):
        root=Path(directory); options=self.fixture(directory)
        receipt=json.loads(options.with_name(options.stem+'-state.json').read_text())
        picture=root/'r3-purple-light-week.png';tokens=roles('PURPLE',False)
        image=Image.new('RGB',(360,800),tokens['background']);draw=ImageDraw.Draw(image)
        block=[40,300,114,370]
        fill={'tonal':mix(tokens['surfaceHighest'],rgb(COURSE[0]),.46),
              'raw':rgb(COURSE[0]),'blank':tokens['background']}[time_fill]
        draw.rectangle(block,fill=fill)
        text_specs=[('上一周',[20,190,80,212]),('下一周',[280,190,340,212]),
                    ('M3E配色验收',[130,305,290,330]),('08:00',[48,312,90,325]),
                    ('08:45',[48,343,90,354]),('今日',[20,672,50,694])]
        xml='<hierarchy>'
        for text,b in text_specs:
            draw.rectangle((b[0]+2,b[1]+3,b[2]-2,b[3]-3),fill=(98,86,113) if text=='今日' else tokens['onSurface'])
            xml+=f'<node package="com.hcbiu.elcton" text="{text}" bounds="[{b[0]},{b[1]}][{b[2]},{b[3]}]"/>'
        xml+='</hierarchy>';picture.with_suffix('.xml').write_text(xml);image.save(picture)
        for key in ('before','after'):
            receipt[key].update(scene='week',weekTimeBlock={'bounds':block,'colorIndex':0})
        receipt['name']=picture.stem;receipt['pngSha256']=hashlib.sha256(picture.read_bytes()).hexdigest()
        receipt['xmlSha256']=receipt['xmlBeforeSha256']=hashlib.sha256(picture.with_suffix('.xml').read_bytes()).hexdigest()
        picture.with_name(picture.stem+'-state.json').write_text(json.dumps(receipt))
        return picture

    def test_actual_week_content_gate_has_valid_baseline_and_rejects_only_raw_or_blank_block(self):
        with tempfile.TemporaryDirectory() as d:
            valid=inspect_capture(self.week_fixture(d));self.assertTrue(valid['passed'],valid)
            for fill in ('raw','blank'):
                with self.subTest(fill=fill):
                    bad=inspect_capture(self.week_fixture(d,time_fill=fill))
                    self.assertFalse(bad['passed'],bad)
                    self.assertIn('CourseCard time block not tonal',str(bad['errors']))

    def test_four_file_snapshot_rejects_missing_keys_and_only_malformed_hash(self):
        valid={name:('ABSENT' if name.endswith('.bak') else 'a'*64)
               for name in ('timetable.json','timetable-last-good.json','timetable.json.bak','timetable-last-good.json.bak')}
        self.assertTrue(valid_business_snapshot(valid))
        bad=valid.copy();bad.pop('timetable.json.bak');self.assertFalse(valid_business_snapshot(bad))
        bad=valid.copy();bad['timetable.json']='not-a-hash';self.assertFalse(valid_business_snapshot(bad))
        self.assertFalse(valid_business_snapshot({'timetable.json':'abc'}))

    def test_selected_color_checkmark_and_semantics_fail_independently(self):
        with tempfile.TemporaryDirectory() as d:
            picture=self.editor_fixture(d);receipt_path=picture.with_name(picture.stem+'-state.json')
            receipt=json.loads(receipt_path.read_text());tokens=roles('PURPLE',False)
            image=Image.open(picture).convert('RGB');draw=ImageDraw.Draw(image)
            draw.rectangle((31,466,46,482),fill=mix(tokens['surfaceHighest'],rgb(COURSE[0]),.46))
            image.save(picture);receipt['pngSha256']=hashlib.sha256(picture.read_bytes()).hexdigest();receipt_path.write_text(json.dumps(receipt))
            invalid=inspect_capture(picture);self.assertFalse(invalid['passed'],invalid)
            self.assertIn('Selected course checkmark',str(invalid['errors']))
            for selected in ([],[0,1]):
                picture=self.editor_fixture(d);receipt_path=picture.with_name(picture.stem+'-state.json')
                receipt=json.loads(receipt_path.read_text())
                for key in ('before','after'):receipt[key]['courseColorsSelected']=selected
                receipt_path.write_text(json.dumps(receipt))
                invalid=inspect_capture(picture);self.assertFalse(invalid['passed'],invalid)
                self.assertIn('Exactly one selected course color',str(invalid['errors']))

    def test_selected_palette_missing_only_preview_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            picture=self.fixture(d);receipt_path=picture.with_name(picture.stem+'-state.json')
            r=json.loads(receipt_path.read_text());image=Image.open(picture).convert('RGB')
            ImageDraw.Draw(image).rectangle((31,177,57,202),fill=(234,221,255))
            image.save(picture);r['pngSha256']=hashlib.sha256(picture.read_bytes()).hexdigest();receipt_path.write_text(json.dumps(r))
            invalid=inspect_capture(picture);self.assertFalse(invalid['passed'],invalid)
            self.assertIn('Palette local preview',str(invalid['errors']))

    def test_unselected_palette_labels_cannot_swap_with_correct_preview_and_metadata(self):
        with tempfile.TemporaryDirectory() as d:
            picture=self.fixture(d);receipt_path=picture.with_name(picture.stem+'-state.json')
            r=json.loads(receipt_path.read_text());xml=picture.with_suffix('.xml')
            text=xml.read_text().replace('text="蓝"','text="TMP"').replace('text="绿"','text="蓝"').replace('text="TMP"','text="绿"')
            xml.write_text(text);r['xmlSha256']=r['xmlBeforeSha256']=hashlib.sha256(xml.read_bytes()).hexdigest();receipt_path.write_text(json.dumps(r))
            invalid=inspect_capture(picture);self.assertFalse(invalid['passed'],invalid)
            self.assertIn('Chinese label not bound',str(invalid['errors']))

    def test_selected_palette_checkmark_is_independently_required(self):
        with tempfile.TemporaryDirectory() as d:
            valid=inspect_capture(self.fixture(d));self.assertTrue(valid['passed'],valid)
            invalid=inspect_capture(self.fixture(d,checkmark=False));self.assertFalse(invalid['passed'],invalid)
            self.assertIn('Selected palette checkmark',str(invalid['errors']))

    def test_palette_timeout_preserves_partial_output_and_attempts(self):
        import ast
        import subprocess
        from unittest.mock import patch
        tree=ast.parse(Path(__file__).with_name('emulator_install_and_tour.py').read_text())
        helper=next((n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='execute_palette_phase'),None)
        self.assertIsNotNone(helper,'Palette timeout execution helper absent')
        assert helper is not None
        calls=[]
        with tempfile.TemporaryDirectory() as d:
            out=Path(d)
            timeout=subprocess.TimeoutExpired(['adb','shell'],600,output=b'partial instrument\x00\xff',stderr=b'partial stderr\xff')
            def harvest():
                calls.append('harvest');(out/'attempt.bin').write_bytes(b'preserved attempt');return True
            def shell(command):
                calls.append(command);return 'real mock logcat'
            host={'passed':False,'source_sha':'c'*40,'phases':{}}
            scope={'subprocess':subprocess,'re':__import__('re'),'json':json,'out':out,'palette_host':host,'harvest_palettes':harvest,'shell':shell}
            exec(compile(ast.Module(body=[helper],type_ignores=[]),'actual-palette-helper','exec'),scope)
            with patch.object(subprocess,'run',side_effect=timeout):
                with self.assertRaises(subprocess.TimeoutExpired):scope['execute_palette_phase']('warm','instrument command',{'target_pid_after':'','test_pid_after':''})
            self.assertEqual((out/'palette-warm-stdout.bin').read_bytes(),timeout.output)
            self.assertEqual((out/'palette-warm-stderr.bin').read_bytes(),timeout.stderr)
            self.assertEqual((out/'attempt.bin').read_bytes(),b'preserved attempt')
            self.assertEqual(calls,['harvest','logcat -d -v brief'])
            saved=json.loads((out/'palette-host.json').read_text());self.assertFalse(saved['phases']['warm']['passed']);self.assertTrue(saved['phases']['warm']['timed_out'])
            self.assertFalse(json.loads((out/'report.json').read_text())['passed'])
            self.assertEqual((out/'palette-failure-logcat.txt').read_text(),'real mock logcat')

    def test_unselected_palette_extra_outline_or_checkmark_is_rejected_from_png_alone(self):
        for marker in ('outline','checkmark'):
            with self.subTest(marker=marker), tempfile.TemporaryDirectory() as d:
                picture=self.fixture(d);self.assertTrue(inspect_capture(picture)['passed'])
                path=picture.with_name(picture.stem+'-state.json');receipt=json.loads(path.read_text())
                option=receipt['after']['paletteOptions']['BLUE']
                image=Image.open(picture).convert('RGB');draw=ImageDraw.Draw(image)
                if marker=='outline':
                    x1,y1,x2,_=option['bounds']
                    draw.rectangle((x1,y1,x2-1,y1+1),fill=roles('PURPLE',False)['primary'])
                else:
                    x1,y1,x2,y2=option['previewBounds'];cx,cy=(x1+x2)//2,(y1+y2)//2
                    draw.line([(cx-5,cy),(cx-1,cy+4),(cx+5,cy-5)],fill=(255,255,255),width=3)
                image.save(picture);receipt['pngSha256']=hashlib.sha256(picture.read_bytes()).hexdigest()
                path.write_text(json.dumps(receipt))
                invalid=inspect_capture(picture);self.assertFalse(invalid['passed'],invalid)
                self.assertIn('Unselected palette '+marker,str(invalid['errors']))

    def test_unselected_course_extra_outline_or_checkmark_is_rejected_from_png_alone(self):
        for marker in ('outline','checkmark'):
            with self.subTest(marker=marker), tempfile.TemporaryDirectory() as d:
                picture=self.editor_fixture(d);self.assertTrue(inspect_capture(picture)['passed'])
                path=picture.with_name(picture.stem+'-state.json');receipt=json.loads(path.read_text())
                x1,y1,x2,y2=receipt['after']['courseColorBounds']['1'];cx,cy=(x1+x2)//2,(y1+y2)//2
                image=Image.open(picture).convert('RGB');draw=ImageDraw.Draw(image)
                if marker=='outline':
                    draw.ellipse((cx-15,cy-15,cx+14,cy+14),outline=roles('PURPLE',False)['primary'],width=2)
                else:
                    draw.line([(cx-5,cy),(cx-1,cy+4),(cx+5,cy-5)],fill=roles('PURPLE',False)['onSurface'],width=3)
                image.save(picture);receipt['pngSha256']=hashlib.sha256(picture.read_bytes()).hexdigest()
                path.write_text(json.dumps(receipt))
                invalid=inspect_capture(picture);self.assertFalse(invalid['passed'],invalid)
                self.assertIn('Unselected course '+marker,str(invalid['errors']))

    def semester_fixture(self, directory):
        root=Path(directory);options=self.fixture(directory)
        receipt=json.loads(options.with_name(options.stem+'-state.json').read_text())
        picture=root/'r3-purple-light-semester.png';tokens=roles('PURPLE',False)
        image=Image.new('RGB',(360,800),tokens['background']);draw=ImageDraw.Draw(image)
        draw.rectangle((22,674,48,690),fill=(98,86,113))
        field=[30,300,330,356];draw.rectangle(field,fill=mix(tokens['primaryContainer'],tokens['surface'],.24))
        draw.rectangle((50,316,150,336),fill=tokens['onPrimaryContainer'])
        image.save(picture)
        picture.with_suffix('.xml').write_text('<hierarchy><node package="com.hcbiu.elcton" text="今日" bounds="[20,672][50,694]"/><node package="com.hcbiu.elcton" text="学期开始日期" bounds="[30,250][160,280]"/><node package="com.hcbiu.elcton" class="android.widget.EditText" text="2026-09-01" bounds="[30,300][330,356]"/><node package="com.hcbiu.elcton" text="保存学期" bounds="[160,380][230,402]"/></hierarchy>')
        receipt['name']=picture.stem
        for key in ('before','after'):receipt[key].update(scene='semester',semesterBounds=field)
        receipt['pngSha256']=hashlib.sha256(picture.read_bytes()).hexdigest()
        receipt['xmlSha256']=receipt['xmlBeforeSha256']=hashlib.sha256(picture.with_suffix('.xml').read_bytes()).hexdigest()
        picture.with_name(picture.stem+'-state.json').write_text(json.dumps(receipt))
        return picture

    def test_valid_semester_fixture_and_xml_only_scene_or_field_mutations(self):
        import xml.etree.ElementTree as ET
        for mutation in ('today-only','no-title','no-save','no-field','wrong-bounds','duplicate-field'):
            with self.subTest(mutation=mutation),tempfile.TemporaryDirectory() as directory:
                picture=self.semester_fixture(directory);valid=inspect_capture(picture)
                self.assertTrue(valid['passed'],valid)
                xml=picture.with_suffix('.xml');tree=ET.parse(xml);root=tree.getroot()
                field=next(n for n in root if n.get('class')=='android.widget.EditText')
                if mutation=='today-only':
                    for n in list(root):
                        if n.get('text')!='今日':root.remove(n)
                elif mutation in ('no-title','no-save'):
                    target='学期开始日期' if mutation=='no-title' else '保存学期'
                    root.remove(next(n for n in root if n.get('text')==target))
                elif mutation=='no-field':root.remove(field)
                elif mutation=='wrong-bounds':field.set('bounds','[40,300][340,356]')
                else:root.append(ET.fromstring(ET.tostring(field)))
                tree.write(xml,encoding='utf-8')
                path=picture.with_name(picture.stem+'-state.json');receipt=json.loads(path.read_text())
                receipt['xmlSha256']=receipt['xmlBeforeSha256']=hashlib.sha256(xml.read_bytes()).hexdigest()
                path.write_text(json.dumps(receipt))
                invalid=inspect_capture(picture);self.assertFalse(invalid['passed'],invalid)
                self.assertIn('semester',str(invalid['errors']).lower())

    def test_xml_only_palette_selection_must_match_live_option(self):
        import xml.etree.ElementTree as ET
        for mutation in ('previous-selection','extra-checked','none-checked','not-checkable','missing-checked','wrong-parent-bounds'):
            with self.subTest(mutation=mutation),tempfile.TemporaryDirectory() as directory:
                picture=self.fixture(directory);baseline=inspect_capture(picture)
                self.assertTrue(baseline['passed'],baseline)
                xml=picture.with_suffix('.xml');tree=ET.parse(xml)
                parents={child:parent for parent in tree.iter() for child in parent}
                controls={n.get('text'):parents[n] for n in tree.iter('node') if n.get('text') in ('紫','蓝')}
                if mutation=='previous-selection':
                    controls['紫'].set('checked','false');controls['蓝'].set('checked','true')
                elif mutation=='extra-checked':controls['蓝'].set('checked','true')
                elif mutation=='none-checked':controls['紫'].set('checked','false')
                elif mutation=='not-checkable':controls['紫'].set('checkable','false')
                elif mutation=='missing-checked':controls['紫'].attrib.pop('checked')
                else:controls['紫'].set('bounds','[30,160][125,220]')
                tree.write(xml,encoding='utf-8')
                path=picture.with_name(picture.stem+'-state.json');receipt=json.loads(path.read_text())
                receipt['xmlSha256']=receipt['xmlBeforeSha256']=hashlib.sha256(xml.read_bytes()).hexdigest()
                path.write_text(json.dumps(receipt))
                invalid=inspect_capture(picture);self.assertFalse(invalid['passed'],invalid)
                self.assertIn('Palette accessibility',str(invalid['errors']))

    def test_one_pixel_palette_checkmarks_cannot_hide_at_any_grid_offset(self):
        for dx in range(2):
            for dy in range(2):
                with self.subTest(dx=dx,dy=dy),tempfile.TemporaryDirectory() as d:
                    p=self.fixture(d);baseline=inspect_capture(p);self.assertTrue(baseline['passed'],baseline)
                    im=Image.open(p).convert('RGB');ImageDraw.Draw(im).line([(144+dx,190+dy),(148+dx,194+dy),(154+dx,188+dy)],fill=(255,255,255),width=1)
                    im.save(p);path=p.with_name(p.stem+'-state.json');receipt=json.loads(path.read_text());receipt['pngSha256']=hashlib.sha256(p.read_bytes()).hexdigest();path.write_text(json.dumps(receipt))
                    result=inspect_capture(p);self.assertFalse(result['passed'],result)
                    self.assertIn('Unselected palette checkmark is rendered',str(result['errors']))

    def test_one_pixel_course_checkmarks_cannot_hide_at_any_grid_offset(self):
        for dx in range(2):
            for dy in range(2):
                with self.subTest(dx=dx,dy=dy),tempfile.TemporaryDirectory() as d:
                    p=self.editor_fixture(d);baseline=inspect_capture(p);self.assertTrue(baseline['passed'],baseline)
                    im=Image.open(p).convert('RGB');ImageDraw.Draw(im).line([(83+dx,455+dy),(87+dx,459+dy),(93+dx,453+dy)],fill=(33,0,93),width=1)
                    im.save(p);path=p.with_name(p.stem+'-state.json');receipt=json.loads(path.read_text());receipt['pngSha256']=hashlib.sha256(p.read_bytes()).hexdigest();path.write_text(json.dumps(receipt))
                    result=inspect_capture(p);self.assertFalse(result['passed'],result)
                    self.assertIn('Unselected course checkmark is rendered',str(result['errors']))

    def test_editor_xml_color_row_requires_all_current_accessibility_controls(self):
        import xml.etree.ElementTree as ET
        for mutation in ('no-label','missing-all','one-missing','duplicate','wrong-bounds','previous-selection','extra-checked','missing-checked','not-checkable','disabled','not-visible','wrong-parent'):
            with self.subTest(mutation=mutation),tempfile.TemporaryDirectory() as d:
                picture=self.editor_fixture(d);baseline=inspect_capture(picture);self.assertTrue(baseline['passed'],baseline)
                xml=picture.with_suffix('.xml');tree=ET.parse(xml);root=tree.getroot()
                label=next(n for n in root.iter('node') if n.get('text')=='课程颜色')
                parent=next(n for n in root if label in list(n))
                controls=[n for n in parent if n.get('checkable')=='true']
                if mutation=='no-label':parent.remove(label)
                elif mutation=='missing-all':
                    for n in controls:parent.remove(n)
                elif mutation=='one-missing':parent.remove(controls[7])
                elif mutation=='duplicate':parent.append(ET.fromstring(ET.tostring(controls[1])))
                elif mutation=='wrong-bounds':controls[1].set('bounds','[65,455][105,503]')
                elif mutation=='previous-selection':controls[0].set('checked','false');controls[1].set('checked','true')
                elif mutation=='extra-checked':controls[1].set('checked','true')
                elif mutation=='missing-checked':controls[0].attrib.pop('checked')
                elif mutation=='not-checkable':controls[1].set('checkable','false')
                elif mutation=='disabled':controls[1].set('enabled','false')
                elif mutation=='not-visible':controls[1].set('visible-to-user','false')
                else:parent.remove(controls[1]);root.append(controls[1])
                tree.write(xml,encoding='utf-8')
                path=picture.with_name(picture.stem+'-state.json');receipt=json.loads(path.read_text())
                receipt['xmlSha256']=receipt['xmlBeforeSha256']=hashlib.sha256(xml.read_bytes()).hexdigest();path.write_text(json.dumps(receipt))
                self.assertEqual(receipt['pngSha256'],hashlib.sha256(picture.read_bytes()).hexdigest())
                self.assertEqual(receipt['before'],receipt['after'])
                result=inspect_capture(picture);self.assertFalse(result['passed'],result)
                self.assertIn('Course color accessibility',str(result['errors']))

    def test_course_color_label_uses_real_primary_role_in_all_twelve_schemes(self):
        from qa.verify_palette_evidence import STATES
        root=Path(__file__).resolve().parents[1]
        source=(root/'app/src/main/java/com/hcbiu/elcton/MainActivity.kt').read_text()
        theme=(root/'app/src/main/java/com/hcbiu/elcton/M3xTheme.kt').read_text()
        self.assertIn('Text("课程颜色",style=MaterialTheme.typography.labelLarge,color=M3x.Ink)',source)
        self.assertIn('val Ink: Color @Composable get() = MaterialTheme.colorScheme.primary',theme)
        for palette,mode in STATES:
            with self.subTest(palette=palette,mode=mode),tempfile.TemporaryDirectory() as d:
                picture=self.editor_fixture(d);old=roles('PURPLE',False);new=roles(palette,mode=='DARK')
                recolor={old[role]:new[role] for role in ('background','primary','onSurface','error')}
                recolor[(98,86,113)]=new['primary']
                recolor.update({mix(old['surfaceHighest'],rgb(c),.46):mix(new['surfaceHighest'],rgb(c),.30 if mode=='DARK' else .46) for c in COURSE})
                image=Image.open(picture).convert('RGB');raw=image.tobytes()
                image.putdata([recolor.get(pixel,pixel) for pixel in zip(raw[::3],raw[1::3],raw[2::3])])
                # Independent application/source contract: M3x.Ink is primary, not onSurface.
                ImageDraw.Draw(image).rectangle((22,416,124,430),fill=new['primary'])
                target=picture.with_name(f'r3-{palette.lower()}-{mode.lower()}-editor-bottom.png');image.save(target)
                target.with_suffix('.xml').write_bytes(picture.with_suffix('.xml').read_bytes())
                receipt=json.loads(picture.with_name(picture.stem+'-state.json').read_text())
                receipt.update(name=target.stem,expectedPalette=palette,expectedDark=mode=='DARK',pngSha256=hashlib.sha256(target.read_bytes()).hexdigest())
                chrome=0xFF000000|(new['background'][0]<<16)|(new['background'][1]<<8)|new['background'][2]
                for key in ('before','after'):
                    receipt[key].update(palette=palette,mode=mode,chromeArgb=chrome-(1<<32),uiFlags=0 if mode=='DARK' else 8208)
                state_path=target.with_name(target.stem+'-state.json');state_path.write_text(json.dumps(receipt))
                baseline=inspect_capture(target);self.assertTrue(baseline['passed'],baseline)
                for ink in (new['onSurface'],new['background']):
                    ImageDraw.Draw(image).rectangle((22,416,124,430),fill=ink);image.save(target)
                    receipt['pngSha256']=hashlib.sha256(target.read_bytes()).hexdigest();state_path.write_text(json.dumps(receipt))
                    result=inspect_capture(target);self.assertFalse(result['passed'],result)
                    self.assertIn('Course color accessibility label not rendered',str(result['errors']))

    def test_palette_harvest_subprocess_has_bounded_timeout_and_valid_run_archive(self):
        import ast
        import io
        import subprocess
        import tarfile
        from types import SimpleNamespace
        tree=ast.parse(Path(__file__).with_name('emulator_install_and_tour.py').read_text())
        helper=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='harvest_palettes')
        run_id='bounded-harvest-fixture';content=b'independent captured attempt'
        wire=io.BytesIO()
        with tarfile.open(fileobj=wire,mode='w') as archive:
            entry=tarfile.TarInfo('qa-palette-evidence/'+run_id+'/attempt.bin');entry.size=len(content)
            archive.addfile(entry,io.BytesIO(content))
        calls=[]
        def transport(argv,**kwargs):
            self.assertEqual(argv,['adb','shell'])
            self.assertTrue(kwargs.get('capture_output'))
            self.assertEqual(kwargs['input'],('run-as com.hcbiu.elcton tar -cf - -C files qa-palette-evidence/'+run_id+'\n').encode())
            deadline=kwargs.get('timeout')
            self.assertIsInstance(deadline,(int,float),'Real palette harvest transport is unbounded')
            self.assertGreater(deadline,0);self.assertLessEqual(deadline,60)
            calls.append(deadline)
            return subprocess.CompletedProcess(argv,0,stdout=wire.getvalue(),stderr=b'')
        with tempfile.TemporaryDirectory() as directory:
            out=Path(directory);target=out/'palette-product';target.mkdir()
            scope={'subprocess':SimpleNamespace(run=transport,TimeoutExpired=subprocess.TimeoutExpired),'io':io,'tarfile':tarfile,
                   'Path':Path,'out':out,'palette_target':target,'palette_run':run_id}
            exec(compile(ast.Module(body=[helper],type_ignores=[]),'actual-bounded-palette-harvest','exec'),scope)
            self.assertTrue(scope['harvest_palettes']())
            self.assertEqual((target/'attempt.bin').read_bytes(),content)
            self.assertEqual(len(calls),1)

    def test_palette_timeout_recovery_bounds_real_helpers_and_preserves_both_failures(self):
        import ast
        import io
        import re
        import subprocess
        import tarfile
        from types import SimpleNamespace
        tree=ast.parse(Path(__file__).with_name('emulator_install_and_tour.py').read_text())
        helpers: list[ast.stmt]=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ('shell','harvest_palettes','execute_palette_phase')]
        self.assertEqual(len(helpers),3)
        for logcat_timeout in (False,True):
            with self.subTest(logcat_timeout=logcat_timeout),tempfile.TemporaryDirectory() as directory:
                out=Path(directory);target=out/'palette-product';target.mkdir()
                original=subprocess.TimeoutExpired(['adb','shell'],600,output=b'instrument partial\x00\xff',stderr=b'instrument stderr\xff')
                harvest_error=subprocess.TimeoutExpired(['adb','shell'],60,output=b'tar partial\x00\xff',stderr=b'tar stderr\xff')
                logcat_error=subprocess.TimeoutExpired(['adb','shell'],60,output=b'logcat partial\x00\xff',stderr=b'logcat stderr\xff')
                calls=[]
                def transport(argv,**kwargs):
                    command=kwargs['input'].decode().strip();calls.append((command,kwargs.get('timeout')))
                    self.assertEqual(argv,['adb','shell'])
                    if command=='instrument command':raise original
                    if command.startswith('run-as com.hcbiu.elcton tar -cf - '):raise harvest_error
                    self.assertEqual(command,'logcat -d -v brief')
                    if logcat_timeout:raise logcat_error
                    return subprocess.CompletedProcess(argv,0,stdout=b'bounded logcat output',stderr=b'')
                host={'passed':False,'source_sha':'d'*40,'phases':{}}
                scope={'subprocess':SimpleNamespace(run=transport,TimeoutExpired=subprocess.TimeoutExpired),'io':io,'tarfile':tarfile,
                       'Path':Path,'out':out,'palette_target':target,'palette_run':'recovery-fixture','palette_host':host,'json':json,'re':re}
                exec(compile(ast.Module(body=helpers,type_ignores=[]),'actual-recovery-helpers','exec'),scope)
                with self.assertRaises(subprocess.TimeoutExpired) as raised:
                    scope['execute_palette_phase']('warm','instrument command',{'target_pid_after':'','test_pid_after':''})
                self.assertIs(raised.exception,original,'Recovery replaced the original instrumentation failure')
                self.assertEqual(len(calls),3);self.assertEqual(calls[0][1],600)
                for command,deadline in calls[1:]:
                    self.assertIsInstance(deadline,(int,float),'Recovery transport is unbounded: '+command)
                    self.assertGreater(deadline,0);self.assertLessEqual(deadline,60)
                for prefix,error in (('palette-warm',original),('palette-harvest-timeout',harvest_error)):
                    for stream,wire in (('stdout',error.stdout),('stderr',error.stderr)):
                        path=out/(prefix+'-'+stream+'.bin');self.assertTrue(path.exists(),'Timeout wire bytes lost: '+path.name)
                        self.assertEqual(path.read_bytes(),wire)
                report=json.loads((out/'report.json').read_text())
                self.assertFalse(report['passed']);self.assertTrue(report['timed_out']);self.assertFalse(report['harvested'])
                self.assertIn('TimeoutExpired',(out/'palette-harvest-error.txt').read_text())
                if logcat_timeout:
                    self.assertIn('TimeoutExpired',(out/'palette-logcat-error.txt').read_text())
                    for stream,wire in (('stdout',logcat_error.stdout),('stderr',logcat_error.stderr)):
                        path=out/('palette-logcat-timeout-'+stream+'.bin');self.assertTrue(path.exists(),'Logcat timeout bytes lost')
                        self.assertEqual(path.read_bytes(),wire)
                else:self.assertEqual((out/'palette-failure-logcat.txt').read_text(),'bounded logcat output')

    def test_harvest_failure_cannot_reuse_previous_run_directory(self):
        source=Path(__file__).with_name('emulator_install_and_tour.py').read_text()
        self.assertIn("assert not palette_target.exists()",source)
        self.assertIn("qa-palette-evidence/'+palette_run",source)
        self.assertIn('collected=harvest_palettes()',source)
        self.assertIn('if not phase_passed or not collected:',source)


if __name__ == '__main__':
    unittest.main(verbosity=2)
