#!/usr/bin/env python3
"""Read back exact target ref and Git tree blob identities of a staged whitelist.
Network GET only; no push, credential outputs, branch mutation or device access.
"""
import argparse, hashlib, json, subprocess
from pathlib import Path
from urllib.parse import quote
ROOT=Path(__file__).resolve().parents[2]
REPO='lantianhcgp/elcton-phone'
BRANCH='diag/p2p-trace-0.2.10-20261115'

def api(endpoint):
    p=subprocess.run(['gh','api','repos/'+REPO+endpoint],cwd=ROOT,capture_output=True,timeout=90)
    assert p.returncode==0, 'Readback GET failed; no credential-bearing URL printed'
    return json.loads(p.stdout)

def main():
    p=argparse.ArgumentParser();p.add_argument('--sha',required=True);p.add_argument('--manifest',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    assert len(a.sha)==40 and all(x in '0123456789abcdef' for x in a.sha), 'Source token must be literal lowercase40hex'
    m=json.loads(a.manifest.read_bytes());rows=m['paths']
    remote=api('/branches/'+quote(BRANCH,safe=''))
    assert remote['commit']['sha']==a.sha,'Exact branch moved; do not use latest'
    commit=api('/git/commits/'+a.sha)
    tree=api('/git/trees/'+commit['tree']['sha']+'?recursive=1')
    assert not tree.get('truncated'), 'Remote tree incomplete'
    entries={r['path']:r for r in tree['tree']}
    checked={}
    for path,row in rows.items():
        raw=subprocess.check_output(['git','show',a.sha+':'+path],cwd=ROOT,timeout=30)
        blob=hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
        assert len(raw)==row['bytes'] and hashlib.sha256(raw).hexdigest()==row['sha256'] and blob==row['blob'],'Exact committed whitelist differs: '+path
        target=entries[path]
        assert target['type']=='blob' and target['sha']==blob and target['size']==len(raw),'Exact remote blob differs: '+path
        checked[path]={'blob':blob,'bytes':len(raw),'sha256':row['sha256']}
    a.out.mkdir(parents=True,exist_ok=False)
    report={'passed':True,'branch':BRANCH,'sha':a.sha,'tree':commit['tree']['sha'],'files':len(checked),'bytes':sum(x['bytes'] for x in checked.values()),'scope':'Actual remote target ref + COMPLETE Git tree blob/size identity readback; not each raw HTTP fetch','rows':checked}
    (a.out/'receipt.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k!='rows'}))

if __name__=='__main__':main()
