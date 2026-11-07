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
            xml += f'<node package="com.hcbiu.elcton" text="{label}" selected="{str(selected).lower()}" bounds="[{x+44},{y+24}][{x+66},{y+46}]"/>'
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
        image.save(p);p.with_suffix('.xml').write_text('<hierarchy><node package="com.hcbiu.elcton" text="今日" bounds="[20,672][50,694]"/></hierarchy>')
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

    def test_harvest_failure_cannot_reuse_previous_run_directory(self):
        source=Path(__file__).with_name('emulator_install_and_tour.py').read_text()
        self.assertIn("assert not palette_target.exists()",source)
        self.assertIn("qa-palette-evidence/'+palette_run",source)
        self.assertIn('collected=harvest_palettes()',source)
        self.assertIn('if not phase_passed or not collected:',source)


if __name__ == '__main__':
    unittest.main(verbosity=2)
