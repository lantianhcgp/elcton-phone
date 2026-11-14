#!/usr/bin/env python3
"""Fetch an exact Android QA run with either conclusion; failures never become PASS."""
import argparse,hashlib,json,subprocess
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--run',required=True);p.add_argument('--sha',required=True);p.add_argument('--out',required=True);a=p.parse_args()
repo='lantianhcgp/elcton-phone';out=Path(a.out);out.mkdir(parents=True,exist_ok=False)
r=subprocess.run(['gh','run','view',a.run,'--repo',repo,'--json','databaseId,headSha,status,conclusion,jobs,url'],capture_output=True,text=True,check=True,timeout=45)
x=json.loads(r.stdout);assert x['headSha']==a.sha and x['status']=='completed';(out/'run.json').write_text(json.dumps(x,indent=2)+'\n')
r=subprocess.run(['gh','api','repos/'+repo+'/actions/runs/'+a.run+'/artifacts'],capture_output=True,text=True,check=True,timeout=45)
art=json.loads(r.stdout);assert len(art['artifacts'])==art['total_count'];(out/'artifacts.json').write_text(json.dumps(art,indent=2)+'\n')
name='android-ui-'+a.sha;assert sum(z['name']==name and not z['expired'] for z in art['artifacts'])==1
r=subprocess.run(['gh','run','download',a.run,'--repo',repo,'--name',name,'--dir',str(out/'artifact')],capture_output=True,text=True,timeout=150)
(out/'download.log').write_text(r.stdout+r.stderr);(out/'download.exit').write_text(str(r.returncode)+'\n');r.check_returncode()
report={'fetched':True,'run':a.run,'source_sha':a.sha,'conclusion':x['conclusion'],'inventory':{str(p.relative_to(out)):{'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in out.rglob('*') if p.is_file()}}
(out/'inventory.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'fetched':True,'run':a.run,'source_sha':a.sha,'conclusion':x['conclusion'],'files':len(report['inventory']),'artifact_dir':str(out/'artifact')}))
