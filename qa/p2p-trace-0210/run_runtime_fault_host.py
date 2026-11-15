#!/usr/bin/env python3
"""R5 S2 HOST fault lane: exact current Runtime/trace, independent new tests, no Android claim."""
import argparse, hashlib, json, os, pathlib, subprocess, sys, tempfile
p=argparse.ArgumentParser();p.add_argument('--deps',required=True);p.add_argument('--out',required=True);a=p.parse_args()
root=pathlib.Path(__file__).resolve().parents[2];out=pathlib.Path(a.out).resolve();out.mkdir(parents=True,exist_ok=False)
s=root/'app/src/main/java/com/hcbiu/elcton';d=pathlib.Path(a.deps)
files=[s/(n+'.kt') for n in ['DiagnosticRuntime','P2pTrace','PacketIngress','PhoneSnapshot','Wire','WearErrorRecord','ErrorJournal','McpToken','McpToolProvider','DiagnosticTools','DiagnosticMcpServer']]
inputs=[root/'qa/runtime_revision_host'/n for n in ['HostBuildConfig.kt.in','HostLog.kt.in','DiagnosticRuntimeRevisionTest.kt.in']]+list((root/'qa/p2p-trace-0210/runtime-fault-host').glob('*.kt.in'))
scratch=pathlib.Path(tempfile.mkdtemp(prefix='p2p-r1-runtime-host-'))
for f in inputs:
    target=scratch/f.name.removesuffix('.in');target.write_bytes(f.read_bytes());files.append(target)
    (out/(target.name+'.source.txt')).write_bytes(target.read_bytes())
cp=os.pathsep.join(str(d/(n+'.jar')) for n in ['json','junit','hamcrest']);jar=out/'runtime-fault-host.jar'
receipt={'origin':'host-test','files':{str(f):hashlib.sha256(f.read_bytes()).hexdigest() for f in files},'templates':{str(f):hashlib.sha256(f.read_bytes()).hexdigest() for f in inputs},'commands':[]}
for name,cmd in [('compile',['kotlinc',*map(str,files),'-classpath',cp,'-include-runtime','-d',str(jar)]),('junit',['java','-Ddiag.evidence='+str(out),'-Ddiag.work='+str(out),'-cp',str(jar)+os.pathsep+cp,'org.junit.runner.JUnitCore','com.hcbiu.elcton.P2pRuntimeFaultTest','com.hcbiu.elcton.DiagnosticRuntimeRevisionTest'])]:
    r=subprocess.run(cmd,cwd=root,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    (out/(name+'.log')).write_text(r.stdout);(out/(name+'.exit')).write_text(str(r.returncode)+'\n')
    receipt['commands'].append({'name':name,'argv':cmd,'exit':r.returncode});(out/'receipt.json').write_text(json.dumps(receipt,indent=2));print(r.stdout,flush=True)
    if r.returncode:sys.exit(r.returncode)
