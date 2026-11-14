#!/usr/bin/env python3
"""Read back a exact remote GitHub archive, compare every tracked file byte-for-byte.
Archive cache is outside the working tree to avoid recursively publishing downloads.
"""
import argparse,hashlib,json,subprocess,tarfile
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--sha',required=True);p.add_argument('--out',required=True);p.add_argument('--cache',required=True);a=p.parse_args()
repo='lantianhcgp/elcton-phone';out=Path(a.out);out.mkdir(parents=True,exist_ok=False);cache=Path(a.cache);cache.parent.mkdir(parents=True,exist_ok=True)
branch=json.loads(subprocess.check_output(['gh','api','repos/'+repo+'/branches/release%2F0.2.9-20261114'],text=True));assert branch['commit']['sha']==a.sha
r=subprocess.check_output(['git','ls-tree','-r','-z',a.sha]);expected={}
for line in r.split(b'\0'):
    if not line:continue
    meta,path=line.split(b'\t',1);mode,kind,oid=meta.decode().split();assert kind=='blob' and mode in ('100644','100755')
    expected[path.decode()]={'blob':oid,'mode':mode}
with cache.open('xb') as f:
    fetched=subprocess.run(['gh','api','repos/'+repo+'/tarball/'+a.sha],stdout=f,stderr=subprocess.PIPE,timeout=180)
(out/'download.stderr').write_bytes(fetched.stderr);(out/'download.exit').write_text(str(fetched.returncode)+'\n');fetched.check_returncode()
seen=set();rows={}
with tarfile.open(cache,'r|gz') as archive:
    for member in archive:
        name=Path(member.name);assert not name.is_absolute() and '..' not in name.parts
        if member.isdir():continue
        assert member.isfile() and len(name.parts)>=2
        relative=Path(*name.parts[1:]).as_posix();assert relative in expected and relative not in seen,relative
        stream=archive.extractfile(member);assert stream is not None
        remote=stream.read();local=subprocess.check_output(['git','cat-file','blob',expected[relative]['blob']]);assert remote==local and len(remote)==member.size,relative
        rows[relative]={'bytes':len(remote),'sha256':hashlib.sha256(remote).hexdigest(),'git_blob':expected[relative]['blob']};seen.add(relative)
assert seen==set(expected)
report={'passed':True,'source_sha':a.sha,'scope':'Independent exact remote tarball readback: every tracked source/test/config/raw evidence blob compared with pinned local Git blob, no omissions','files':len(rows),'tracked_bytes':sum(x['bytes'] for x in rows.values()),'remote_archive_bytes':cache.stat().st_size,'remote_archive_sha256':hashlib.sha256(cache.read_bytes()).hexdigest(),'rows':rows}
(out/'all-files-readback.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k!='rows'},ensure_ascii=False))
