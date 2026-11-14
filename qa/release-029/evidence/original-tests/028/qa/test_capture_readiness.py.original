#!/usr/bin/env python3
"""Synthetic unit fixtures for screenshot readiness; real CI frames are separate."""
import json
import tempfile
import unittest
from pathlib import Path
from PIL import Image, ImageDraw
from verify_system_bars import inspect


class CaptureReadinessTest(unittest.TestCase):
    def sample(self, rendered):
        directory = Path(self.tmp.name)
        picture = directory / "01-today-empty.png"
        state = directory / "01-today-empty-state.json"
        state.write_text(json.dumps({"screenHeight": 600, "statusBarHeight": 24,
            "imeVisible": False, "navigationTop": 480, "navigationBottom": 550}))
        # Explicit artificial unit fixture, not a replacement for a CI screenshot.
        image = Image.new("RGB", (300, 600), (12, 15, 21))
        draw = ImageDraw.Draw(image)
        draw.rectangle((20, 517, 35, 531), fill=(237, 240, 247))
        if rendered:
            for x in (58, 141, 224):
                draw.rectangle((x, 570, x + 12, 582), fill=(237, 240, 247))
        image.save(picture)
        picture.with_suffix(".xml").write_text('''<hierarchy><node package="com.hcbiu.elcton" text="今日" bounds="[20,515][40,535]"/><node resource-id="com.android.systemui:id/back" bounds="[45,550][90,600]"/><node resource-id="com.android.systemui:id/home_button" bounds="[120,550][180,600]"/><node resource-id="com.android.systemui:id/recent_apps" bounds="[210,550][265,600]"/></hierarchy>''')
        return inspect(picture, state)

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.tmp.cleanup()

    def test_same_background_without_rendered_system_keys_is_not_a_pass(self):
        self.assertFalse(self.sample(False)["passed"], "flat background hid missing navigation keys")

    def test_aligned_label_and_rendered_keys_are_accepted(self):
        self.assertTrue(self.sample(True)["passed"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
