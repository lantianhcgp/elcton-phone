#!/usr/bin/env python3
"""Offline original PNG contact sheets for R8 visual inspection only.
No source, verifier, cloud or original-image writes; no image invention.
"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import hashlib
import json

HERE = Path(__file__).resolve().parent
ORIGINALS = HERE / 'full-artifact/artifact/product'
OUT = HERE / 'visual-tour'
OUT.mkdir(exist_ok=False)
paths = sorted(ORIGINALS.glob('*.png'))
assert len(paths) == 28, 'Real product tour 28 source images required'
font = ImageFont.truetype('/data/data/com.termux/files/usr/share/fonts/TTF/DejaVuSans.ttf', 19)
rows = []
for first in range(0, len(paths), 4):
    group = paths[first:first + 4]
    sheet = Image.new('RGB', (1728, 832), '#262626')
    draw = ImageDraw.Draw(sheet)
    for index, path in enumerate(group):
        with Image.open(path) as image:
            image.load()
            assert image.size == (1080, 1920), path.name
            full = image.convert('RGB').resize((432, 768), Image.Resampling.LANCZOS)
            sheet.paste(full, (index * 432, 50))
        draw.text((index * 432 + 8, 12), path.name, font=font, fill='white')
        rows.append({'source': str(path), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                     'original_size': [1080, 1920], 'sheet': 'tour-%02d.png' % (first // 4 + 1),
                     'full_source_preserved': True})
    target = OUT / ('tour-%02d.png' % (first // 4 + 1))
    sheet.save(target)
(OUT / 'originals.json').write_text(json.dumps(rows, ensure_ascii=False, indent=2) + '\n')
print(json.dumps({'scene_count': len(rows), 'sheets': len(list(OUT.glob('*.png'))),
                  'out': str(OUT), 'scope': 'Contact sheets only; NOT visual or gate verdict'}))
