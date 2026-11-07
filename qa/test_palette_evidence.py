#!/usr/bin/env python3
"""Synthetic fail-closed fixture tests only; these are never advertised as actual APK evidence."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from PIL import Image, ImageDraw
from qa.verify_palette_evidence import inspect_capture, check_processes, check_capture_provenance, mix, rgb, roles, COURSE


class PaletteEvidenceTest(unittest.TestCase):
    def fixture(self, directory, bad_container=False, wrong_palette=False, duplicate=False):
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
            options[name] = {'bounds': [x,y,x+95,y+60], 'selected': selected}
            base = (234,221,255) if selected else (240,234,247)
            draw.rectangle((x,y,x+94,y+59), fill=base)
            if selected:
                draw.rectangle((x,y,x+94,y+1), fill=(103,80,164))
            draw.ellipse((x+12,y+18,x+35,y+41), fill='#'+primary)
            draw.rectangle((x+44,y+28,x+55,y+39), fill=(33,0,93))
            xml += f'<node package="com.hcbiu.elcton" text="{label}" selected="{str(selected).lower()}" bounds="[{x},{y}][{x+95},{y+60}]"/>'
        xml += '</hierarchy>'
        if bad_container:
            draw.rectangle((24,187,27,193), fill=(12,15,21))
        image.save(picture)
        hierarchy = picture.with_suffix('.xml'); hierarchy.write_text(xml)
        state = {'mode':'LIGHT','palette':'PURPLE','systemDark':True,'pid':120,'navigationMode':'three-button',
            'screenWidth':360,'screenHeight':800,'navigationTop':640,'navigationBottom':750,
            'statusBarHeight':24,'systemNavigationHeight':50,'imeVisible':False,'chromeArgb':-395777,'uiFlags':8208,
            'paletteOptions':options,'modeSelected':'LIGHT','businessHashes':{'timetable.json':'abc'},'scene':'options',
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

    def editor_fixture(self, directory, raw_colors=False):
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
        draw.rectangle((140,530,205,545),fill=tokens['error'])
        receipt['name']=p.stem;receipt['phase']='warm'
        for key in ('before','after'):
            receipt[key].update(scene='editor-bottom',courseColorBounds=color_bounds,deleteBounds=[20,510,340,566])
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
        states={'cold-purple-light':{'pid':130,'qaRun':'synthetic-run','businessBefore':{'timetable.json':'abc'}}}
        row={'name':'r3-purple-light-cold','passed':True,'metrics':{'phase':'cold-purple-light','pid':130,
             'businessHashes':{'timetable.json':'abc'},'navigationMode':'three-button','qaRun':'synthetic-run','captureId':'capture-1'}}
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

    def test_harvest_failure_cannot_reuse_previous_run_directory(self):
        source=Path(__file__).with_name('emulator_install_and_tour.py').read_text()
        self.assertIn("assert not palette_target.exists()",source)
        self.assertIn("qa-palette-evidence/'+palette_run",source)
        self.assertIn('collected=harvest_palettes()',source)
        self.assertIn('if not phase_passed or not collected:',source)


if __name__ == '__main__':
    unittest.main(verbosity=2)
