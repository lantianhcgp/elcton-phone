#!/usr/bin/env python3
"""Bounded GitHub CI poller. Requires exact workflow/ref/source, never picks latest."""
import argparse
import json
from pathlib import Path
import subprocess
import time

p=argparse.ArgumentParser();p.add_argument('--repo',required=True);p.add_argument('--sha',required=True);p.add_argument('--workflow',default='build.yml');p.add_argument('--out',required=True);p.add_argument('--run');p.add_argument('--seconds',type=int,default=1320);a=p.parse_args()
out=Path(a.out);out.mkdir(parents=True,exist_ok=False)
def gh(*args):
 r=subprocess.run(['gh',*args],capture_output=True,text=True,timeout=45)
 if r.returncode:raise RuntimeError('GitHub read failed: '+r.stderr[:700])
 return json.loads(r.stdout)
end=time.monotonic()+a.seconds;rid=a.run;last=None
while True:
 if rid is None:
  rs=gh('run','list','--repo',a.repo,'--workflow',a.workflow,'--commit',a.sha,'--limit','30','--json','databaseId,headSha,status,conclusion,url,createdAt')
  assert all(r['headSha']==a.sha for r in rs)
  if len(rs)>1:raise RuntimeError('Ambiguous exact-source workflow runs; require --run. No blind latest selection.')
  if rs:rid=str(rs[0]['databaseId'])
 if rid:
  r=gh('run','view',rid,'--repo',a.repo,'--json','databaseId,headSha,status,conclusion,url,jobs,event,workflowName,headBranch')
  assert r['headSha']==a.sha
  (out/'latest.json').write_text(json.dumps(r,indent=2)+'\n')
  state=(r['status'],r['conclusion'])
  if state!=last:print(json.dumps({'run':rid,'sha':a.sha,'status':state,'url':r['url']}),flush=True);last=state
  if r['status']=='completed':
   with (out/'completed.json').open('x') as f:json.dump(r,f,indent=2);f.write('\n')
   print('CI_COMPLETED '+json.dumps({'run':rid,'sha':a.sha,'conclusion':r['conclusion'],'url':r['url']}),flush=True)
   raise SystemExit(0 if r['conclusion']=='success' else 1)
 if time.monotonic()>end:raise RuntimeError('CI deadline exceeded; final status retained; not PASS')
 time.sleep(15)
