#!/usr/bin/env python3
"""Register a cloud-only Android run with explicit source/build/API/suite inputs."""
import argparse
import json
from pathlib import Path
import subprocess
import time
p=argparse.ArgumentParser();p.add_argument('--sha',required=True);p.add_argument('--build',required=True);p.add_argument('--suite',choices=('diagnostics','full'),required=True);p.add_argument('--api',choices=('33','34'),default='33');p.add_argument('--out',required=True);a=p.parse_args()
repo='lantianhcgp/elcton-phone';branch='release/0.2.9-20261114';out=Path(a.out);out.mkdir(parents=True,exist_ok=False)
def runs():
 r=subprocess.run(['gh','run','list','--repo',repo,'--workflow','ui-smoke.yml','--commit',a.sha,'--limit','50','--json','databaseId,headSha,status,conclusion,url,event,createdAt'],capture_output=True,text=True,check=True,timeout=45)
 return json.loads(r.stdout)
before={r['databaseId'] for r in runs()}
inputs={'build_run':a.build,'build_sha':a.sha,'api_level':a.api,'navigation_mode':'three-button','qa_suite':a.suite}
(out/'dispatch-inputs.json').write_text(json.dumps(inputs,indent=2)+'\n')
cmd=['gh','workflow','run','ui-smoke.yml','--repo',repo,'--ref',branch]
for k,v in inputs.items():cmd+=['-f',k+'='+v]
r=subprocess.run(cmd,capture_output=True,text=True,timeout=45)
(out/'dispatch.stdout').write_text(r.stdout);(out/'dispatch.stderr').write_text(r.stderr);(out/'dispatch.exit').write_text(str(r.returncode)+'\n');r.check_returncode()
end=time.monotonic()+90
while True:
 rs=[r for r in runs() if r['databaseId'] not in before]
 if len(rs)>1:raise RuntimeError('Ambiguous new runs: do not re-dispatch or choose latest')
 if rs:
  x=rs[0];assert x['headSha']==a.sha and x['event']=='workflow_dispatch'
  (out/'registered.json').write_text(json.dumps({'run':x,'inputs':inputs,'scope':'registered exact cloud workflow; execution not PASS'},indent=2)+'\n')
  print(json.dumps({'run_id':x['databaseId'],'sha':a.sha,'inputs':inputs,'url':x['url']}));break
 if time.monotonic()>end:raise RuntimeError('Run registration timeout; no execution result claimed')
 time.sleep(3)
