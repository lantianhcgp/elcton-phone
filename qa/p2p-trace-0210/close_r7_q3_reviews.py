#!/usr/bin/env python3
"""Close genuine Q3 delta reviews, preserve all previous closures."""
import hashlib
import json
from pathlib import Path
import shutil

ROOT=Path(__file__).resolve().parents[2]
V=Path(__file__).resolve().parent/'r6/reviews'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    manifest=V/'input-q3/reviewed-manifest.json'
    m=json.loads(manifest.read_bytes())
    assert m and all(sha(ROOT/p)==h for p,h in m.items())
    axes=[]
    for axis in ('spec','quality'):
        report=V/('r7-'+axis+'-q3.json')
        raw=V/(axis+'-q3-raw.txt')
        d=json.loads(report.read_bytes())
        assert d['axis']==axis and d['passed'] is True
        assert d['input_files']==len(m) and d['input_manifest_sha256']==sha(manifest)
        assert d['reviewed_inputs']==m and d['raw_reply_sha256']==sha(raw)
        assert raw.stat().st_size>0
        assert not any(d.get(k,[]) for k in ('security_concerns','logic_errors','missing','critical','important'))
        axes.append({'axis':axis,'json_path':report.name,'json_sha256':sha(report),'raw_path':raw.name,'raw_sha256':sha(raw)})
    target=V/'closure-q3';target.mkdir(exist_ok=False)
    for x in axes:shutil.copyfile(V/x['raw_path'],target/(x['axis']+'-raw.txt'))
    shutil.copyfile(manifest,target/'reviewed-manifest.json')
    record={'passed':True,'axes':axes,'manifest_sha256':sha(manifest),'input_files':len(m),
        'scope':'Genuine independent Q3 source delta closure, historical Q2 retained; not CI/APK acceptance'}
    (target/'dual-closure.json').write_text(json.dumps(record,indent=2)+'\n')
    print(json.dumps({'passed':True,'inputs':len(m),'closure':str(target)}))

if __name__=='__main__':main()
