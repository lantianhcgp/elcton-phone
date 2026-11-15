#!/usr/bin/env python3
"""Same HOST171 sources under actual CI Kotlin1.9.24; no Android/device claim."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
Q = HERE.parent
BEFORE = 'a0881bf7c1d97724ea166f0e51988902c280a5cc'
DEPS = Path.home() / '.hermes/tmp/elcton-jvm-test'
COMPILER = Path.home() / '.hermes/tmp/elcton-kotlin-1.9.24'
NAMES = ['Wire','PhoneSnapshot','ScheduleBook','TransferSession','ExportSession','DevicePolicy','UserFacingError','PacketIngress','SendAttempts','OperationDeadline','WearErrorRecord','ErrorJournal','McpToken','McpToolProvider','DiagnosticTools','DiagnosticMcpServer','PhoneSchedule','PhoneActions','PhoneMcpTools','PickupClient','SyncEngine','McpKeepAlivePolicy','MainThreadActions','P2pTrace']
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()

p = argparse.ArgumentParser()
p.add_argument('--phase', choices=('red','green'), required=True)
p.add_argument('--out', type=Path, required=True)
a = p.parse_args()
assert '..' not in a.out.parts
out = a.out.absolute()
assert not any(x.is_symlink() for x in (out,*out.parents))
assert out.resolve().is_relative_to((Q/'evidence').resolve()) and not out.exists()
out.mkdir(parents=True, exist_ok=False)
c = json.loads((COMPILER/'download-receipt.json').read_bytes())
for row in c['downloaded']:
    assert sha(COMPILER/row['file']) == row['sha256']
assert 'kotlinc-jvm 1.9.24' in (COMPILER/'compiler-version.log').read_text()
cp = os.pathsep.join([str(DEPS/(n+'.jar')) for n in ('json','junit','hamcrest')] + [str(COMPILER/row['file']) for row in c['downloaded'] if row['file'].startswith(('kotlin-stdlib','annotations-'))])
source = ROOT/'app/src/main/java/com/hcbiu/elcton'
tests = sorted((ROOT/'app/src/test/java/com/hcbiu/elcton').glob('*Test.kt'))
files = [source/(n+'.kt') for n in NAMES] + tests + [ROOT/'qa/PhoneMcpHost.kt',ROOT/'qa/McpHost.kt']
inputs = {str(f.relative_to(ROOT)):sha(f) for f in files}
row = {'phase':a.phase,'compiler':'1.9.24','source_before':BEFORE,'input_sha256':inputs,'commands':[],'scope':'Actual Kotlin1.9.24 HOST compile and tests, not Android build or device'}
with tempfile.TemporaryDirectory(prefix='r7-kotlin19-') as tmp:
    tmp=Path(tmp)
    if a.phase=='red':
        for name in ('SyncEngine','P2pTrace'):
            original=source/(name+'.kt')
            raw=subprocess.check_output(['git','show',BEFORE+':'+str(original.relative_to(ROOT))],cwd=ROOT)
            replacement=tmp/(name+'.kt');replacement.write_bytes(raw)
            files=[replacement if f==original else f for f in files]
            (out/(name+'.before.source.txt')).write_bytes(raw)
    baseline=subprocess.check_output(['git','show','bb26c64b67e1cfa7903cd709c2aac482f6490e6b:app/src/main/java/com/hcbiu/elcton/SyncEngine.kt'],cwd=ROOT).decode()
    raw='package com.hcbiu.elcton\n\n'+baseline[baseline.index('class SyncEngine('):].replace('class SyncEngine(', 'class P2pTraceBaselineEngine(',1)
    generated=tmp/'P2pTraceBaselineEngine.kt';generated.write_text(raw);files.append(generated)
    jar=out/'kotlin19-host.jar'
    argv=['java','-Xmx512m','-cp',c['classpath'],'org.jetbrains.kotlin.cli.jvm.K2JVMCompiler','-no-stdlib','-no-reflect','-jvm-target','17',*map(str,files),'-classpath',cp,'-d',str(jar)]
    start=time.monotonic();r=subprocess.run(['nice','-n','10',*argv],cwd=ROOT,capture_output=True,text=True,timeout=300)
    log=r.stdout+r.stderr;(out/'compile.raw.log').write_text(log);(out/'compile.exit').write_text(str(r.returncode)+'\n')
    row['commands'].append({'name':'compile','exit':r.returncode,'seconds':time.monotonic()-start,'argv':argv,'log_sha256':sha(out/'compile.raw.log')})
    (out/'receipt.json').write_text(json.dumps(row,indent=2)+'\n')
    if a.phase=='red':
        assert r.returncode!=0 and 'literal prefixes and suffixes' in log, 'RED must be the real CI compiler syntax rejection'
        row['validated']=True;row['literal_errors']=log.count('literal prefixes and suffixes')
    else:
        assert r.returncode==0, 'Kotlin1.9.24 compile failed, original log retained'
        run=['java','-Xmx256m','-cp',str(jar)+os.pathsep+cp,'org.junit.runner.JUnitCore',*['com.hcbiu.elcton.'+f.stem for f in tests]]
        r=subprocess.run(run,cwd=ROOT,capture_output=True,text=True,timeout=120)
        log=r.stdout+r.stderr;(out/'junit.raw.log').write_text(log);(out/'junit.exit').write_text(str(r.returncode)+'\n')
        row['commands'].append({'name':'junit','exit':r.returncode,'argv':run,'log_sha256':sha(out/'junit.raw.log')})
        assert r.returncode==0 and 'OK (171 tests)' in log, 'Actual Kotlin1.9.24 HOST171 tests failed'
        row['validated']=True;row['tests']=171;row['jar_sha256']=sha(jar)
assert all(sha(ROOT/f)==h for f,h in inputs.items()), 'Actual source changed during compiler execution'
row['source_unchanged']=True
(out/'receipt.json').write_text(json.dumps(row,indent=2)+'\n')
print(json.dumps({'phase':a.phase,'validated':True,'compiler':'1.9.24','compile_exit':row['commands'][0]['exit'],'tests':row.get('tests'),'literal_errors':row.get('literal_errors'),'receipt':str(out/'receipt.json')}))
