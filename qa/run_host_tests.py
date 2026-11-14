#!/usr/bin/env python3
"""Run the genuine non-Android Kotlin modules with real JSON + JUnit, no fabricated SDK.
Dependencies must be supplied via --deps. Prints real execution and writes logs if --out set.
"""
import argparse, pathlib, subprocess, sys, os
p=argparse.ArgumentParser();p.add_argument('--deps',required=True);p.add_argument('--out');p.add_argument('--classes',nargs='*');a=p.parse_args()
root=pathlib.Path(__file__).resolve().parents[1];deps=pathlib.Path(a.deps);out=pathlib.Path(a.out or deps/'host-run');out.mkdir(parents=True,exist_ok=True)
source=root/'app/src/main/java/com/hcbiu/elcton';test=root/'app/src/test/java/com/hcbiu/elcton'
names=['Wire','PhoneSnapshot','ScheduleBook','TransferSession','ExportSession','DevicePolicy','UserFacingError','PacketIngress','SendAttempts','OperationDeadline','WearErrorRecord','ErrorJournal','McpToken','DiagnosticTools','DiagnosticMcpServer']
files=[source/(n+'.kt') for n in names if (source/(n+'.kt')).exists()]+sorted(test.glob('*Test.kt'))
if (root/'qa/McpHost.kt').is_file(): files.append(root/'qa/McpHost.kt')
cp=os.pathsep.join(str(deps/(n+'.jar')) for n in ['json','junit','hamcrest']);jar=out/'host-tests.jar'
cmd=['kotlinc',*[str(f) for f in files],'-classpath',cp,'-include-runtime','-d',str(jar)]
r=subprocess.run(cmd,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT);(out/'compile.log').write_text(r.stdout);print(r.stdout)
if r.returncode:sys.exit(r.returncode)
classes=a.classes or ['com.hcbiu.elcton.'+f.stem for f in sorted(test.glob('*Test.kt'))]
r=subprocess.run(['java','-cp',str(jar)+os.pathsep+cp,'org.junit.runner.JUnitCore',*classes],text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
(out/'junit.log').write_text(r.stdout);print(r.stdout);sys.exit(r.returncode)
