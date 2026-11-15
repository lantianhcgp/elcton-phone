#!/usr/bin/env python3
"""R5 HOST runner: unchanged old source/test bytes plus the new trace source.
No Android/Huawei API simulation is compiled in this lane. Logs are exclusive.
"""
import argparse, hashlib, json, os, pathlib, subprocess, sys
p=argparse.ArgumentParser(); p.add_argument('--deps',required=True); p.add_argument('--out',required=True); p.add_argument('--classes',nargs='*'); a=p.parse_args()
root=pathlib.Path(__file__).resolve().parents[2]; deps=pathlib.Path(a.deps); out=pathlib.Path(a.out).resolve()
out.mkdir(parents=True,exist_ok=False)
source=root/'app/src/main/java/com/hcbiu/elcton'; test=root/'app/src/test/java/com/hcbiu/elcton'
names=['Wire','PhoneSnapshot','ScheduleBook','TransferSession','ExportSession','DevicePolicy','UserFacingError','PacketIngress','SendAttempts','OperationDeadline','WearErrorRecord','ErrorJournal','McpToken','McpToolProvider','DiagnosticTools','DiagnosticMcpServer','PhoneSchedule','PhoneActions','PhoneMcpTools','PickupClient','SyncEngine','McpKeepAlivePolicy','MainThreadActions','P2pTrace']
files=[source/(n+'.kt') for n in names if (source/(n+'.kt')).exists()]+sorted(test.glob('*Test.kt'))
files += [root/'qa'/n for n in ['PhoneMcpHost.kt','McpHost.kt'] if (root/'qa'/n).is_file()]
baseline=subprocess.check_output(['git','show','bb26c64b67e1cfa7903cd709c2aac482f6490e6b:app/src/main/java/com/hcbiu/elcton/SyncEngine.kt'],cwd=root,text=True)
import tempfile
scratch=pathlib.Path(tempfile.mkdtemp(prefix='p2p-trace-host-'))
baseline_file=scratch/'P2pTraceBaselineEngine.kt'
baseline_file.write_text('package com.hcbiu.elcton\n\n'+baseline[baseline.index('class SyncEngine('):].replace('class SyncEngine(', 'class P2pTraceBaselineEngine('))
(out/'P2pTraceBaselineEngine.source.txt').write_bytes(baseline_file.read_bytes())
files.append(baseline_file)
cp=os.pathsep.join(str(deps/(n+'.jar')) for n in ['json','junit','hamcrest']); jar=out/'host-tests.jar'
receipt={'source':'host-test','files':{str(f.relative_to(root) if f.is_relative_to(root) else f):hashlib.sha256(f.read_bytes()).hexdigest() for f in files},'commands':[]}
commands=[['kotlinc',*[str(f) for f in files],'-classpath',cp,'-include-runtime','-d',str(jar)],['java','-cp',str(jar)+os.pathsep+cp,'org.junit.runner.JUnitCore',*(a.classes or ['com.hcbiu.elcton.'+f.stem for f in sorted(test.glob('*Test.kt'))])]]
for label,cmd in zip(['compile','junit'],commands):
    r=subprocess.run(cmd,cwd=root,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    (out/(label+'.log')).write_text(r.stdout); (out/(label+'.exit')).write_text(str(r.returncode)+'\n')
    receipt['commands'].append({'name':label,'argv':cmd,'exit':r.returncode})
    (out/'receipt.json').write_text(json.dumps(receipt,indent=2))
    print(r.stdout,flush=True)
    if r.returncode: sys.exit(r.returncode)
