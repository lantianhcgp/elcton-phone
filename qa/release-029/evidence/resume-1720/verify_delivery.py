#!/usr/bin/env python3
"""Actual downloaded binary verification/exclusive delivery, no device actions."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
p=argparse.ArgumentParser();p.add_argument('--apk',required=True);p.add_argument('--sha',required=True);p.add_argument('--out',required=True);p.add_argument('--destination',required=True);a=p.parse_args()
apk=Path(a.apk);out=Path(a.out);out.mkdir(parents=True,exist_ok=False)
expected='fc08a0b474a8ffca5887bd5c88ac15e865a63a64eca81c10f344496c46d9ad94'
r=subprocess.run(['aapt2','dump','badging',str(apk)],capture_output=True,text=True,timeout=40)
(out/'manifest-binary.txt').write_text(r.stdout+r.stderr);(out/'manifest-binary.exit').write_text(str(r.returncode)+'\n');r.check_returncode()
m=re.search(r"package: name='([^']+)' versionCode='([^']+)' versionName='([^']+)'",r.stdout)
assert m and m.groups()==('com.hcbiu.elcton','11','0.2.9')
r=subprocess.run(['java','-Xmx256m','-jar',str(Path.home()/'rb_build/bt/android-14/lib/apksigner.jar'),'verify','--verbose','--print-certs',str(apk)],capture_output=True,text=True,timeout=60)
(out/'apk-signature.txt').write_text(r.stdout+r.stderr);(out/'apk-signature.exit').write_text(str(r.returncode)+'\n');r.check_returncode()
m=re.search(r'certificate SHA-256 digest: ([0-9a-fA-F]+)',r.stdout);assert m and m[1].lower()==expected
assert 'Verified using v2 scheme (APK Signature Scheme v2): true' in r.stdout
raw=apk.read_bytes();digest=hashlib.sha256(raw).hexdigest();dest=Path(a.destination);assert not dest.exists()
dest.parent.mkdir(parents=True,exist_ok=True)
with dest.open('xb') as f:f.write(raw)
assert dest.read_bytes()==raw and dest.stat().st_size==len(raw)
b=Path(__file__).parent
old=json.loads((b/'old-deliveries-before.json').read_text());old.append(json.loads((b/'old-watch-delivery-before.json').read_text()))
for row in old:
 p=Path(row['path']);assert p.stat().st_size==row['bytes'] and hashlib.sha256(p.read_bytes()).hexdigest()==row['sha256']
report={'passed':True,'source_sha':a.sha,'package':'com.hcbiu.elcton','versionCode':11,'versionName':'0.2.9','signer_sha256':expected,'apk_sha256':digest,'bytes':len(raw),'delivery_path':str(dest),'old_deliveries_unchanged':old,'scope':'actual CI binary manifest/signature/hash/exclusive phone storage copy; physical tests PENDING'}
(out/'delivery.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps(report,ensure_ascii=False))
