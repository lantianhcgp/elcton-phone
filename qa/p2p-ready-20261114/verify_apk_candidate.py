#!/usr/bin/env python3
"""CI/readback check on the binary manifest and compiled candidate BuildConfig, not source comments."""
import json, os, re, subprocess, sys
from pathlib import Path
apk=Path(sys.argv[1]);out=Path(sys.argv[2])
aapt=Path(os.environ['ANDROID_HOME'])/'build-tools/34.0.0/aapt'
r=subprocess.run([str(aapt),'dump','badging',str(apk)],text=True,capture_output=True,check=True)
m=re.search(r"package: name='([^']+)' versionCode='([^']+)' versionName='([^']+)'",r.stdout)
assert m and m.groups()==('com.hcbiu.elcton','10','0.2.8'),'Final APK binary version mismatch'
report={'passed':True,'package':m[1],'versionCode':int(m[2]),'versionName':m[3],'scope':'Binary APK manifest only; generated BuildConfig is tested separately by Android unit variant'}
out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
