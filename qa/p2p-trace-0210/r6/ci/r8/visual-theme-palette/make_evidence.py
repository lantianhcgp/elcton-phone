from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import hashlib, json, datetime
from collections import Counter
BASE=Path('/data/data/com.termux/files/home/elcton-phone-diagnostics-0210-20261115/qa/p2p-trace-0210/r6/ci/r8')
SRC=BASE/'full-artifact/artifact'
OUT=BASE/'visual-theme-palette'
(OUT/'sheets').mkdir(parents=True, exist_ok=True)
(OUT/'crops').mkdir(parents=True, exist_ok=True)
font=ImageFont.load_default(size=15)
manifest={'generated_at':datetime.datetime.now().astimezone().isoformat(),'source_commit':'b3eb5568','build_run':'43715446826','ui_run':'43720799962','platform':'API33 three-button','scope':'Root PNGs only, excludes attempts; static screenshot inspection only; numeric gates not rerun; real handshake not covered','images':{},'sheets':{}}
for folder in ('theme-product','palette-product'):
 for p in sorted((SRC/folder).glob('*.png')):
  key=str(p.relative_to(SRC)); im=Image.open(p)
  manifest['images'][key]={'source_absolute':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'width':im.width,'height':im.height,'visual_status':'unviewed','overview_sheets':[],'component_sheets':[],'crops':[]}
assert sum(k.startswith('theme-product/') for k in manifest['images'])==23
assert sum(k.startswith('palette-product/') for k in manifest['images'])==74

def sheet(name, keys, width=360, crop=None, role='overview'):
 tiles=[]; cells=[]
 for key in keys:
  im=Image.open(SRC/key).convert('RGB'); rect=crop or (0,0,im.width,im.height)
  c=im.crop(rect)
  if crop:
   cp=OUT/'crops'/(Path(key).stem+'--'+name+'.png')
   c.save(cp,compress_level=2)
   manifest['images'][key]['crops'].append({'path':str(cp),'source_rectangle_xyxy':list(rect),'sha256':hashlib.sha256(cp.read_bytes()).hexdigest()})
  c=c.resize((width,round(c.height*width/c.width)),Image.Resampling.LANCZOS)
  tile=Image.new('RGB',(width,c.height+34),'#e7e7e7'); d=ImageDraw.Draw(tile)
  d.text((6,4),Path(key).stem,fill='#000000',font=font)
  tile.paste(c,(0,34)); tiles.append(tile)
 cols=min(3,len(tiles)); th=max(t.height for t in tiles); rows=(len(tiles)+cols-1)//cols
 canvas=Image.new('RGB',(cols*width,rows*th),'#adb0b5')
 for i,(tile,key) in enumerate(zip(tiles,keys)):
  x=(i%cols)*width; y=(i//cols)*th; canvas.paste(tile,(x,y))
  cells.append({'source':key,'tile_xyxy':[x,y,x+tile.width,y+tile.height],'source_rectangle_xyxy':list(crop or (0,0,1080,1920))})
  manifest['images'][key][role+'_sheets' if role=='overview' else 'component_sheets'].append(name)
 dest=OUT/'sheets'/(name+'.png');canvas.save(dest,compress_level=2)
 manifest['sheets'][name]={'path':str(dest),'sha256':hashlib.sha256(dest.read_bytes()).hexdigest(),'role':role,'size':list(canvas.size),'cells':cells,'personally_viewed':False}

colours=['purple','blue','green','teal','orange','pink']
for state in ['light-options','dark-options','light-week','dark-week','light-semester','dark-semester','light-editor-bottom','dark-editor-bottom','light-cold','dark-cold','system-light','system-dark']:
 keys=['palette-product/r3-'+colour+'-'+state+'.png' for colour in colours]
 sheet('palette-'+state,keys)
 if state.endswith('options'):
  sheet('component-'+state,keys,540,(80,590,1000,1590),'component')
 elif state.endswith('week'):
  sheet('component-'+state,keys,540,(45,80,1035,1270),'component')
 elif state.endswith('semester'):
  sheet('component-'+state,keys,540,(45,310,1035,1300),'component')
 elif state.endswith('editor-bottom'):
  sheet('component-'+state,keys,540,(45,790,1035,1588),'component')

extra=['palette-product/r3-restored-purple-dark.png','palette-product/r3-system-cold.png']
sheet('palette-restored-system-cold',extra,width=540)
sheet('component-restored-state',extra,width=540,crop=(45,590,1035,1590),role='component')
tkeys=[k for k in manifest['images'] if k.startswith('theme-product/')]
for i in range(0,len(tkeys),6):sheet('theme-overview-'+str(i//6+1),tkeys[i:i+6])
# Native-resolution named component crops for targeted personal vision.
representatives=[('palette-product/r3-purple-light-options.png','native-light-options',(80,590,1000,1590)),('palette-product/r3-purple-dark-options.png','native-dark-options',(80,590,1000,1590)),('palette-product/r3-purple-light-week.png','native-light-week',(45,80,1035,1270)),('palette-product/r3-purple-dark-week.png','native-dark-week',(45,80,1035,1270)),('palette-product/r3-purple-light-semester.png','native-light-semester',(45,310,1035,1300)),('palette-product/r3-purple-dark-semester.png','native-dark-semester',(45,310,1035,1300)),('palette-product/r3-purple-light-editor-bottom.png','native-light-editor-bottom',(45,790,1035,1588)),('palette-product/r3-purple-dark-editor-bottom.png','native-dark-editor-bottom',(45,790,1035,1588)),('palette-product/r3-restored-purple-dark.png','native-restored-state',(0,0,1080,1920)),('theme-product/r2-light-date-error-ime.png','native-light-ime-bottom',(0,1050,1080,1920)),('theme-product/r2-dark-date-error-ime.png','native-dark-ime-bottom',(0,1050,1080,1920))]
for key,name,rect in representatives:
 im=Image.open(SRC/key).crop(rect); dest=OUT/'crops'/(name+'.png');im.save(dest,compress_level=2)
 manifest['images'][key]['crops'].append({'path':str(dest),'source_rectangle_xyxy':list(rect),'sha256':hashlib.sha256(dest.read_bytes()).hexdigest(),'personally_viewed':False})
# Combined status/dock/system bars preserve original pixels before sheet resampling.
for mode in ['light','dark']:
 keys=['palette-product/r3-'+c+'-'+mode+'-cold.png' for c in colours]
 tiles=[]
 for key in keys:
  im=Image.open(SRC/key).convert('RGB'); c=Image.new('RGB',(1080,400));c.paste(im.crop((0,0,1080,80)),(0,0));c.paste(im.crop((0,1600,1080,1920)),(0,80))
  cp=OUT/'crops'/(Path(key).stem+'--bars.png');c.save(cp,compress_level=2)
  manifest['images'][key]['crops'].append({'path':str(cp),'source_rectangles_xyxy':[[0,0,1080,80],[0,1600,1080,1920]],'sha256':hashlib.sha256(cp.read_bytes()).hexdigest()})
  c=c.resize((540,200),Image.Resampling.LANCZOS);t=Image.new('RGB',(540,234),'#e7e7e7');ImageDraw.Draw(t).text((6,4),Path(key).stem,fill='black',font=font);t.paste(c,(0,34));tiles.append(t)
 can=Image.new('RGB',(1620,468),'#adb0b5')
 for i,t in enumerate(tiles):can.paste(t,((i%3)*540,(i//3)*234))
 name='component-'+mode+'-bars';dest=OUT/'sheets'/(name+'.png');can.save(dest,compress_level=2)
 manifest['sheets'][name]={'path':str(dest),'sha256':hashlib.sha256(dest.read_bytes()).hexdigest(),'role':'component','size':list(can.size),'cells':[{'source':k,'source_rectangles_xyxy':[[0,0,1080,80],[0,1600,1080,1920]]} for k in keys],'personally_viewed':False}
 for key in keys:manifest['images'][key]['component_sheets'].append(name)
(OUT/'image-mapping.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2))
print(json.dumps({'originals':len(manifest['images']),'sheets':len(manifest['sheets']),'crops':sum(len(i['crops']) for i in manifest['images'].values()),'output':str(OUT),'sheets_paths':[str(OUT/'sheets'/(n+'.png')) for n in manifest['sheets']]},indent=2))
