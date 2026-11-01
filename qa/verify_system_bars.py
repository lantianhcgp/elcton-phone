#!/usr/bin/env python3
"""Measure actual screenshot pixels, not PNG filter bytes or file sizes.

Only app-owned, non-modal scenes are compared. The keyboard and DocumentsUI
own their own system navigation bar and are deliberately not called app UI.
"""
import argparse
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import cast
from PIL import Image

BACKGROUND = (12, 15, 21)
APP_SCENES = {
    "01-today-empty", "02-week-empty", "03-editor-empty", "04-editor-invalid",
    "05-week-course", "06-editor-filled", "07-week-edited", "08-settings",
    "09-settings-invalid", "13-device", "14-device-unavailable",
    "15-editor-bottom", "17-course-deleted", "20-restored-course",
    "21-confirmed-empty-import", "22-return-today", "24-file-exported",
    "27-file-imported-course", "28-restarted-file-import", "29-keyboard-visible",
}


def inspect(image_path: Path, state_path: Path) -> dict:
    state = json.loads(state_path.read_text())
    with Image.open(image_path) as source:
        image = source.convert("RGB")
    width, height = image.size
    bottom = state.get("navigationBottom")
    assert isinstance(bottom, (int, float)) and 20 < bottom <= height, state
    assert state["screenHeight"] == height, "Screenshot/state size mismatch"
    # Sample margins outside all padded app content and system-bar icons.
    rows = {
        "status_bar": min(10, max(0, int(state.get("statusBarHeight", 24)) - 1)),
        "page": height // 3,
        "app_navigation": int(bottom) - 10,
    }
    if not state.get("imeVisible"):
        rows["system_navigation"] = height - 10
    samples = {}
    for name, y in rows.items():
        assert 0 <= y < height, (name, y)
        pixels = [image.getpixel((x, y)) for x in (1, 2, width - 3, width - 2)]
        samples[name] = {"row": y, "rgb": pixels,
                         "matches_page_background": all(tuple(p) == BACKGROUND for p in pixels)}
    # Match the rendered frame to its captured hierarchy, not only four flat margins.
    # Missing SystemUI keys once passed the old color-only gate after a nav-mode switch.
    hierarchy = ET.parse(image_path.with_suffix(".xml")).getroot()
    readiness = []
    def check_pixels(node, label, minimum=12):
        bounds = [int(n) for n in re.findall(r"\d+", node.get("bounds", ""))]
        assert len(bounds) == 4, (label, bounds)
        left, top, right, base = bounds
        assert 0 <= left < right <= width and 0 <= top < base <= height, (label, bounds)
        light = sum(min(cast(tuple[int, int, int], pixel)) > 100 for pixel in image.crop((left, top, right, base)).getdata())
        readiness.append({"component": label, "bounds": bounds,
                          "visible_pixels": light, "passed": light >= minimum})
    labels = [n for n in hierarchy.iter("node")
              if n.get("package") == "com.hcbiu.elcton" and n.get("text") == "今日"]
    assert len(labels) == 1, "App navigation label missing or ambiguous"
    check_pixels(labels[0], "app_navigation_label")
    if not state.get("imeVisible"):
        keys = [n for n in hierarchy.iter("node")
                if n.get("resource-id", "").endswith(("/back", "/home_button", "/recent_apps"))]
        if state.get("navigationMode") == "three-button" or keys:
            assert len(keys) == 3, "Incomplete system three-button hierarchy"
            for key in keys:
                check_pixels(key, key.get("resource-id"), minimum=12)
                bounds = [int(n) for n in re.findall(r"\d+", key.get("bounds", ""))]
                white = sum(min(cast(tuple[int, int, int], pixel)) > 180
                            for pixel in image.crop((bounds[0], bounds[1], bounds[2], bounds[3])).getdata())
                readiness[-1].update(visible_pixels=white, passed=white >= 12)
        else:
            # AOSP gesture handle is not an accessibility node. Read its real pixels.
            bounds = (width // 3, int(bottom), width * 2 // 3, height)
            light = sum(min(cast(tuple[int, int, int], pixel)) > 180 for pixel in image.crop(bounds).getdata())
            readiness.append({"component": "system_gesture_handle", "bounds": list(bounds),
                              "visible_pixels": light, "passed": light >= 12})
    return {"name": image_path.name, "size": [width, height],
            "expected_rgb": list(BACKGROUND), "ime_visible": bool(state.get("imeVisible")),
            "bands": samples, "capture_readiness": readiness,
            "passed": all(s["matches_page_background"] for s in samples.values())
                      and all(s["passed"] for s in readiness)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", type=Path)
    parser.add_argument("--state", type=Path)
    parser.add_argument("--product", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.image:
        if not args.state:
            parser.error("--image requires --state")
        results = [inspect(args.image, args.state)]
    else:
        if not args.product:
            parser.error("Provide --image/--state or --product")
        missing = sorted(name for name in APP_SCENES if not (args.product / (name + ".png")).is_file())
        assert not missing, "Missing app-owned UI scenes: " + str(missing)
        results = [inspect(args.product / (name + ".png"), args.product / (name + "-state.json"))
                   for name in sorted(APP_SCENES)]
    report = {"passed": all(r["passed"] for r in results), "scenes": len(results),
              "scope": "Full-screen emulator screenshots; keyboard/SAF system chrome is outside app ownership",
              "results": results}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(report, ensure_ascii=False))
    raise SystemExit(0 if report["passed"] else 1)


if __name__ == "__main__":
    main()
