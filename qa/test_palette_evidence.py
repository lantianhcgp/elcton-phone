#!/usr/bin/env python3
"""Synthetic fail-closed fixture tests only; these are never advertised as actual APK evidence."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from PIL import Image, ImageDraw
from qa.verify_palette_evidence import inspect_capture, check_processes


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
            'density':1.0}
        sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
        receipt = {'name':picture.stem,'phase':'matrix','captureId':'synthetic-unit-only','stable':True,'xmlStable':True,
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
        self.assertTrue(check_processes({'a':{'pid':22},'b':{'pid':22}}, {'a':{},'b':{}}))


if __name__ == '__main__':
    unittest.main(verbosity=2)
