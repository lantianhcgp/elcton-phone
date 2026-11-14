#!/usr/bin/env python3
"""Mandatory exact lossless tail publishing and ALL remote readback; original large files remain local.
Partitions are a GitHub blob-size representation only, never truncated evidence.
"""
import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[5]
os.chdir(ROOT)
BASE=ROOT/'qa/release-029/evidence/resume-1720/resume-fourth/r11'
OUT=BASE/'tail-final'
OUT.mkdir(exist_ok=False)
REP=BASE/'lossless-large-originals'
REP.mkdir(exist_ok=False)
SOURCE='84a6c406099348f75b436a8e9467c34487766859'
review=ROOT/'qa/release-029/evidence/resume-1720/final-review-r11-fourth'
manifest=json.loads((review/'reviewed-manifest.json').read_bytes())
closure=json.loads((review/'dual-closure.json').read_bytes())
assert closure['passed'] is True
for p,h in manifest.items():
    assert hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h
    assert hashlib.sha256(subprocess.check_output(['git','show',SOURCE+':'+p])).hexdigest()==h
for row in closure['axes']:
    assert hashlib.sha256((review/(row['axis']+'-raw.txt')).read_bytes()).hexdigest()==row['raw_sha256']
new=subprocess.check_output(['git','ls-files','--others','--exclude-standard','-z']).split(b'\0')
large=[]
for raw in new:
    if not raw:continue
    p=ROOT/os.fsdecode(raw)
    if p.is_file() and not p.is_symlink() and p.stat().st_size>80*1024*1024:
        assert p.is_relative_to(ROOT/'qa/release-029/evidence')
        full=hashlib.sha256();parts=[];count=0
        with p.open('rb') as stream:
            while True:
                block=stream.read(32*1024*1024)
                if not block:break
                full.update(block);q=REP/(hashlib.sha256(raw).hexdigest()[:16]+'-'+str(count).zfill(4)+'.part')
                q.open('xb').write(block)
                parts.append({'path':str(q.relative_to(ROOT)),'bytes':len(block),'sha256':hashlib.sha256(block).hexdigest()})
                count+=1
        rebuilt=hashlib.sha256();size=0
        for part in parts:
            b=(ROOT/part['path']).read_bytes();assert hashlib.sha256(b).hexdigest()==part['sha256'];rebuilt.update(b);size+=len(b)
        assert rebuilt.hexdigest()==full.hexdigest() and size==p.stat().st_size
        large.append({'original':str(p.relative_to(ROOT)),'bytes':size,'sha256':full.hexdigest(),'parts':parts,'local_original_preserved':True})
(REP/'lossless-map.json').open('x').write(json.dumps({'passed':True,'scope':'Lossless partition of oversized original GitHub blobs; original local file untouched; parts concatenate exact bytes','rows':large},indent=2)+'\n')
# Exact credential scan before staging; no values printed.
command=[sys.executable,'-B','qa/release-029/evidence/resume-1720/resume-fourth/scan_git_payloads.py','--out',str(OUT/'pre-push-scan.json')]
with (OUT/'scan.log').open('xb') as log:
    run=subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,timeout=420)
assert run.returncode==0
allnames=(subprocess.check_output(['git','ls-files','-z'])+subprocess.check_output(['git','ls-files','--others','--exclude-standard','-z'])).split(b'\0')
skips={row['original'] for row in large}
paths=sorted({raw for raw in allnames if raw and os.fsdecode(raw).startswith('qa/release-029/evidence/') and os.fsdecode(raw) not in skips})
subprocess.run(['git','add','--pathspec-from-file=-','--pathspec-file-nul'],input=b'\0'.join(paths)+b'\0',check=True,timeout=300)
changed=subprocess.check_output(['git','diff','--cached','--name-only','-z']).split(b'\0')
assert all(not p or os.fsdecode(p).startswith('qa/release-029/evidence/') for p in changed)
with (OUT/'commit.log').open('xb') as log:
    p=subprocess.run(['git','commit','-m','docs(qa): seal 0.2.9 exact green cloud acceptance and lossless original evidence [skip ci]'],stdout=log,stderr=subprocess.STDOUT,timeout=300)
(OUT/'commit.exit').open('x').write(str(p.returncode)+'\n');p.check_returncode()
sha=subprocess.check_output(['git','rev-parse','HEAD']).decode().strip()
for name,expected in manifest.items():
    assert hashlib.sha256(subprocess.check_output(['git','show',sha+':'+name])).hexdigest()==expected
with (OUT/'push.log').open('xb') as log:
    p=subprocess.run(['git','push','origin','HEAD:release/0.2.9-20261114'],stdout=log,stderr=subprocess.STDOUT,timeout=900)
(OUT/'push.exit').open('x').write(str(p.returncode)+'\n');p.check_returncode()
remote=json.loads(subprocess.check_output(['gh','api','repos/lantianhcgp/elcton-phone/branches/release%2F0.2.9-20261114']))['commit']['sha'];assert remote==sha
command=[sys.executable,'-B','qa/release-029/evidence/resume-1720/resume-fourth/remote_readback_stream.py','--sha',sha,'--out',str(OUT/'remote-readback')]
with (OUT/'readback.log').open('xb') as log:
    p=subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,timeout=900)
(OUT/'readback.exit').open('x').write(str(p.returncode)+'\n');p.check_returncode()
readback=json.loads((OUT/'remote-readback/all-files-readback.json').read_bytes());assert readback['passed'] and readback['source_sha']==sha
# The complete external parts already match exact local Git blobs; recompose each original map again.
for item in large:
    dig=hashlib.sha256();size=0
    for part in item['parts']:
        row=readback['rows'][part['path']];assert row['bytes']==part['bytes'] and row['sha256']==part['sha256']
        b=(ROOT/part['path']).read_bytes();dig.update(b);size+=len(b)
    assert size==item['bytes'] and dig.hexdigest()==item['sha256']
receipt={'passed':True,'build_source_sha':SOURCE,'evidence_sha':sha,'remote_sha':remote,'external_git_files':readback['files'],'lossless_oversized_originals':len(large),'reviewed130_unchanged':True,'report_and_all_tail_evidence_external_byte_readback':True,'physical_acceptance':'pending owner','completed_at':datetime.datetime.now().astimezone().isoformat()}
(OUT/'FINAL-CLOSURE.json').open('x').write(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n')
progress=Path('/storage/emulated/0/Documents/elcton-WearEngine-真机联调-20261113-123000/进度.md')
with progress.open('a') as stream:
    stream.write('\n## 第四轮尾部闭合实际完成\n- 精确尾证提交'+sha+'已push与external全部'+str(readback['files'])+'Git文件/大原件无损分块逐字读回通过；源码130项同84a6c40，报告+全部尾证SHA闭合。最终回执='+str(OUT/'FINAL-CLOSURE.json')+'。真机纯MCP全链与退后台10分钟仍pending归发起方。\n')
print(json.dumps(receipt,ensure_ascii=False),flush=True)
