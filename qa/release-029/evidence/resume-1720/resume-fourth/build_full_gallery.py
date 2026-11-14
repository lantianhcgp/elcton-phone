#!/usr/bin/env python3
"""Original screenshot index/contact sheets only after real full gate and all snapshot hashes match."""
import argparse
import hashlib
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

parser = argparse.ArgumentParser()
parser.add_argument('--pipeline', type=Path, required=True)
parser.add_argument('--full-receipt', type=Path, required=True)
parser.add_argument('--out', type=Path, required=True)
args = parser.parse_args()
pipeline = args.pipeline
report = json.loads(args.full_receipt.read_bytes())
assert report['passed'] is True and not report['errors']
source = report['source_sha']
raw = pipeline / 'full-artifact/artifact'
original = json.loads((pipeline / 'full-artifact/inventory.json').read_bytes())
assert original['source_sha'] == source
def with_digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()

assert all(with_digest(pipeline / 'full-artifact' / name) == row['sha256']
           for name, row in original['inventory'].items())
out = args.out
out.mkdir(parents=True, exist_ok=False)
font_path = Path('/system/fonts/Roboto-Regular.ttf')
font = ImageFont.truetype(str(font_path), 23) if font_path.is_file() else ImageFont.load_default()
items = {}
for group in ('product', 'theme-product', 'palette-product'):
    paths = sorted((raw / group).glob('*.png'))
    assert paths, 'No original images in ' + group
    rows = []
    for path in paths:
        image = Image.open(path); image.load()
        rows.append({'name': path.name, 'path': str(path.resolve()), 'size': list(image.size),
                     'sha256': hashlib.sha256(path.read_bytes()).hexdigest()})
    items[group] = rows
    # Each panel represents actual original image; label separate from image with no overpaint.
    for number, start in enumerate(range(0, len(rows), 6), 1):
        selected = rows[start:start + 6]
        sheet = Image.new('RGB', (1536, 1984), '#25262b')
        draw = ImageDraw.Draw(sheet)
        for i, row in enumerate(selected):
            column, line = i % 3, i // 3
            ox, oy = column * 512, line * 992
            draw.text((ox + 8, oy + 8), row['name'], fill='white', font=font)
            image = Image.open(row['path']).convert('RGB')
            image.thumbnail((500, 922), Image.Resampling.LANCZOS)
            sheet.paste(image, (ox + (512 - image.width) // 2, oy + 60))
        sheet.save(out / (group + '-page-' + str(number) + '.png'))
manifest = {'source_sha': source, 'run_id': report['run_id'],
            'original_sha_manifest_checked': True, 'original_file_count': len(original['inventory']),
            'groups': items, 'scope': 'Derived visual contact sheets and exact original image index; no source edits/new acceptance'}
(out / 'image-index.json').open('x').write(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
print(json.dumps({'source': source, 'run': report['run_id'], 'original_images':{k:len(v) for k,v in items.items()},
                  'sheets':[str(p.resolve()) for p in sorted(out.glob('*.png'))]}, ensure_ascii=False), flush=True)
