#!/usr/bin/env python3
"""R5 actual old/new WearProbe source on labelled fake Android/Huawei API.
This executes SDK-seam call/getter/identity oracles, NOT real Huawei/Android/BLE.
Outputs are exclusive. Baseline only renames the class, never edits its business bytes.
Generated *.kt and jars are not placed in tracked QA (qa is a recursive Gradle sourceSet).
"""
import argparse, hashlib, json, pathlib, subprocess, tempfile, time, os, sys
p=argparse.ArgumentParser();p.add_argument('--deps',required=True);p.add_argument('--out',required=True)
p.add_argument('--source-snapshot');p.add_argument('--skip-junit',action='store_true');p.add_argument('--actual-sdk',action='store_true')
a=p.parse_args();root=pathlib.Path(__file__).resolve().parents[2]
out=pathlib.Path(a.out).resolve();out.mkdir(parents=True,exist_ok=False)
source=root/'app/src/main/java/com/hcbiu/elcton';templates=root/'qa/p2p-trace-0210/native-host'
names=['WearProbe','P2pTrace','SyncEngine','PacketIngress','SendAttempts','DevicePolicy','Wire','PhoneSnapshot','TransferSession','ExportSession','UserFacingError','WearErrorRecord','OperationDeadline']
base='bb26c64b67e1cfa7903cd709c2aac482f6490e6b'
d=pathlib.Path(a.deps);libs=['json','junit','hamcrest']+(['wearengine','tasks'] if a.actual_sdk else [])
cp=os.pathsep.join(str(d/(n+'.jar')) for n in libs)
if a.actual_sdk and not a.skip_junit:p.error('--actual-sdk requires --skip-junit (type resolution only, no native SDK execution)')
row={'scope':('actual Huawei jars type-check, HOST Android type shell/diagnostics; NOT native Android execution' if a.actual_sdk else 'host-test fake Android/Huawei boundary; actual WearProbe source; NOT native Android or network validation'),'base':base,'files':{},'steps':[], 'actual_sdk':a.actual_sdk}
with tempfile.TemporaryDirectory(prefix='r5-native-host-') as temp:
    temp=pathlib.Path(temp);files=[]
    for name in names:
        f=source/(name+'.kt');b=f.read_bytes()
        if a.source_snapshot:
            snap=pathlib.Path(a.source_snapshot)/(name+'.source.txt')
            if snap.is_file():b=snap.read_bytes()
        generated=temp/(name+'.kt');generated.write_bytes(b);files.append(generated)
        (out/(name+'.source.txt')).write_bytes(b)
        row['files'][f.relative_to(root).as_posix()]=hashlib.sha256(b).hexdigest()
    raw=subprocess.check_output(['git','show',base+':app/src/main/java/com/hcbiu/elcton/WearProbe.kt'],cwd=root)
    baseline=raw.replace(b'class WearProbe(',b'class P2pTraceBaselineProbe(',1)
    f=temp/'P2pTraceBaselineProbe.kt';f.write_bytes(baseline);files.append(f)
    (out/'P2pTraceBaselineProbe.source.txt').write_bytes(baseline)
    row['baseline_original_sha256']=hashlib.sha256(raw).hexdigest();row['baseline_renamed_sha256']=hashlib.sha256(baseline).hexdigest()
    for t in sorted(templates.glob('*.kt.in')):
        if a.skip_junit and t.name.endswith('Test.kt.in'):continue
        if a.actual_sdk and t.name.startswith('Huawei'):continue
        b=t.read_bytes();f=temp/t.name.removesuffix('.in');f.write_bytes(b);files.append(f)
        row['files'][t.relative_to(root).as_posix()]=hashlib.sha256(b).hexdigest()
        (out/(t.name+'.source.txt')).write_bytes(b)
    commands=[('compile',['kotlinc',*map(str,files),'-classpath',cp,'-include-runtime','-d',str(out/'native-host.jar')])]
    if not a.skip_junit:commands += [('junit',['java','-cp',str(out/'native-host.jar')+os.pathsep+cp,'org.junit.runner.JUnitCore','com.hcbiu.elcton.NativeAdapterOracleTest','com.hcbiu.elcton.NativeAfterReadyAdapterTest'])]
    for name,cmd in commands:
        t=time.monotonic();r=subprocess.run(cmd,cwd=root,capture_output=True,text=True,timeout=240)
        raw=r.stdout+r.stderr;(out/(name+'.log')).write_text(raw);(out/(name+'.exit')).write_text(str(r.returncode))
        row['steps'].append({'name':name,'argv':cmd,'exit':r.returncode,'seconds':time.monotonic()-t,'sha256':hashlib.sha256(raw.encode()).hexdigest()})
        (out/'receipt.json').write_text(json.dumps(row,indent=2)+'\n')
        print(json.dumps({'name':name,'exit':r.returncode,'seconds':row['steps'][-1]['seconds']}),flush=True);print(raw[-4500:],flush=True)
        if r.returncode:sys.exit(r.returncode)
