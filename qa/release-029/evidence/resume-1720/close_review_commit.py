#!/usr/bin/env python3
"""Read independent saved raw axis verdicts, rehash current manifest and commit."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
p=argparse.ArgumentParser();p.add_argument('--dir',required=True);p.add_argument('--spec',required=True);p.add_argument('--standards',required=True);p.add_argument('--message',required=True);a=p.parse_args();d=Path(a.dir);prep=json.loads((d/'prepare.json').read_bytes());rows=[]
for axis,path in [('spec',a.spec),('standards',a.standards)]:
    raw=Path(path).read_bytes();text=raw.decode();obj,end=json.JSONDecoder().raw_decode(text);tail=text[end:].strip()
    assert not tail or (tail.startswith('[steer did not land — the subagent finished before it could be delivered:') and tail.endswith(']'))
    assert obj['axis']==axis and obj['passed']==(not obj['security_concerns'] and not obj['logic_errors'] and not obj['missing_requirements']) and obj['passed'] is True
    for target,field in [('source_manifest_sha256','product_manifest_sha256'),('reviewed_manifest_sha256','reviewed_manifest_sha256'),('diff_sha256','diff_sha256')]:assert obj[target]==prep[field]
    dest=d/(axis+'-raw.txt')
    with dest.open('xb') as f:f.write(raw)
    rows.append({'axis':axis,'raw_sha256':hashlib.sha256(raw).hexdigest(),'passed':obj['passed'],'summary':obj['summary'],'suffix_present':bool(tail)})
manifest=json.loads((d/'reviewed-manifest.json').read_bytes());assert all(hashlib.sha256(Path(n).read_bytes()).hexdigest()==h for n,h in manifest.items())
closure={'passed':True,'scope':'cumulative review+current incremental exact binding; not Android execution','source_manifest_sha256':prep['product_manifest_sha256'],'reviewed_manifest_sha256':prep['reviewed_manifest_sha256'],'diff_sha256':prep['diff_sha256'],'axes':rows}
with (d/'dual-closure.json').open('x') as f:f.write(json.dumps(closure,ensure_ascii=False,indent=2)+'\n')
subprocess.run(['git','add','-A'],check=True)
assert all(hashlib.sha256(subprocess.check_output(['git','show',':'+n])).hexdigest()==h for n,h in manifest.items())
r=subprocess.run(['git','commit','-m',a.message],capture_output=True,text=True);(d/'commit.log').write_text(r.stdout+r.stderr);(d/'commit.exit').write_text(str(r.returncode)+'\n');r.check_returncode()
print(json.dumps({'passed':True,'commit':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),'axes':rows},ensure_ascii=False))
