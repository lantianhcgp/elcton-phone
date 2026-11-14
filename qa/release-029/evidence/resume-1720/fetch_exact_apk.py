#!/usr/bin/env python3
"""Download only artifacts of one already-readback exact source run."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
p=argparse.ArgumentParser();p.add_argument('--run',required=True);p.add_argument('--sha',required=True);p.add_argument('--out',required=True);a=p.parse_args()
repo='lantianhcgp/elcton-phone';out=Path(a.out);out.mkdir(parents=True,exist_ok=False)
r=subprocess.run(['gh','run','view',a.run,'--repo',repo,'--json','databaseId,headSha,status,conclusion,url,jobs,event,workflowName,headBranch'],capture_output=True,text=True,check=True,timeout=45)
run=json.loads(r.stdout);assert run['headSha']==a.sha and run['status']=='completed' and run['conclusion']=='success'
(out/'run-exact.json').write_text(json.dumps(run,indent=2)+'\n')
r=subprocess.run(['gh','api','repos/'+repo+'/actions/runs/'+a.run+'/artifacts'],capture_output=True,text=True,check=True,timeout=45)
arts=json.loads(r.stdout);assert not any(x['expired'] for x in arts['artifacts']);assert len(arts['artifacts'])==arts['total_count']
(out/'artifacts.json').write_text(json.dumps(arts,indent=2)+'\n')
name='android-probe-'+a.sha;assert sum(x['name']==name for x in arts['artifacts'])==1
r=subprocess.run(['gh','run','download',a.run,'--repo',repo,'--dir',str(out/'artifact'),'--name',name],capture_output=True,text=True,timeout=150)
(out/'download.stdout').write_text(r.stdout);(out/'download.stderr').write_text(r.stderr);(out/'download.exit').write_text(str(r.returncode)+'\n');r.check_returncode()
main=list((out/'artifact').rglob('elcton-phone-probe.apk'));tests=list((out/'artifact').rglob('elcton-ui-tests.apk'));pins=list((out/'artifact').rglob('source-sha.txt'))
assert len(main)==len(tests)==len(pins)==1 and pins[0].read_text().strip()==a.sha
inventory={str(p.relative_to(out)): {'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in out.rglob('*') if p.is_file()}
(out/'download-file-inventory.json').write_text(json.dumps(inventory,indent=2)+'\n')
print(json.dumps({'passed':True,'scope':'exact successful GitHub source/run/artifact readback only','sha':a.sha,'run':a.run,'main_apk':str(main[0]),'test_apk':str(tests[0]),'files':len(inventory),'url':run['url']}))
