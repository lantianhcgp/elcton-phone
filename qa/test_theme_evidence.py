#!/usr/bin/env python3
"""Synthetic unit fixtures explicitly exercise failures; not runtime evidence."""
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from PIL import Image, ImageDraw
sys.path.insert(0, str(Path(__file__).resolve().parent))
from verify_theme_evidence import inspect_capture


class ThemeEvidenceTest(unittest.TestCase):
    def fixture(self, directory, keyboard=True, ime_top=400, mismatched=False):
        root = Path(directory)
        picture = root / 'r2-light-date-error-ime.png'
        image = Image.new('RGB', (300, 600), (249, 245, 255))
        draw = ImageDraw.Draw(image)
        draw.text((30, 70), 'error', fill=(105, 0, 5))
        draw.rectangle((28, 328, 52, 346), fill=(33, 0, 93))
        if keyboard:
            draw.rectangle((0, 400, 299, 569), fill=(238, 238, 238))
            for row in range(430, 555, 40):
                for column in range(20, 290, 25):
                    draw.rectangle((column, row, column+5, row+9), fill=(50, 50, 50))
        image.save(picture)
        ime_xml = '<node package="com.android.inputmethod.latin" text="a" bounds="[0,400][300,570]"/>'
        xml = picture.with_suffix('.xml')
        xml.write_text('<hierarchy><node package="com.hcbiu.elcton" text="今日" bounds="[25,325][55,350]"/><node package="com.hcbiu.elcton" text="请输入有效日期（YYYY-MM-DD）" bounds="[25,50][260,100]"/>'+ime_xml+'</hierarchy>')
        state = dict(mode='LIGHT', systemDark=False, pid=88, screenWidth=300, screenHeight=600,
            navigationMode='three-button', navigationTop=310, navigationBottom=380,
            dateErrorBounds=[25,50,260,100], imePackage='com.android.inputmethod.latin',
            imeBounds=[0,ime_top,300,570], imeVisible=True, imeBottom=200, statusBarHeight=24,
            systemNavigationHeight=30, chromeArgb=-395777, uiFlags=8208)
        sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
        receipt = dict(name=picture.stem, captureId='unit-fixture-only', phase='initial', attempt=1,
            expectedDark=False, requiresIme=True, before=state, after=state.copy(), stable=True,
            pixelReady=True, pngSha256=sha(picture), xmlSha256=sha(xml), xmlStable=True, xmlBeforeSha256=sha(xml))
        if mismatched:
            xml.write_text(xml.read_text().replace('text="a"', 'text="different frame"'))
        picture.with_name(picture.stem+'-state.json').write_text(json.dumps(receipt))
        return picture

    def test_state_true_without_actual_keyboard_pixels_fails(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertFalse(inspect_capture(self.fixture(d, keyboard=False))['passed'])

    def test_keyboard_bounds_outside_window_fails(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertFalse(inspect_capture(self.fixture(d, ime_top=620))['passed'])

    def test_png_xml_different_capture_hash_fails(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertFalse(inspect_capture(self.fixture(d, mismatched=True))['passed'])

    def test_visible_keyboard_error_and_bound_png_xml_are_accepted(self):
        with tempfile.TemporaryDirectory() as d:
            result = inspect_capture(self.fixture(d))
            self.assertTrue(result['passed'], result)


if __name__ == '__main__':
    unittest.main(verbosity=2)
