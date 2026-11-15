#!/usr/bin/env python3
"""Produce main APK/report from verified actual CI receipts, never from stubs.
Non-covering phone output, exact source/run/artifact/signature/manifest SHA.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import time

ROOT = Path(__file__).resolve().parents[2]
Q = Path(__file__).resolve().parent/'r6'
PHONE = Path('/storage/emulated/0/Documents/elcton-WearEngine-真机联调-20261113-123000/phone')
CERT = 'fc08a0b474a8ffca5887bd5c88ac15e865a63a64eca81c10f344496c46d9ad94'
sha = lambda p: hashlib.file_digest(p.open('rb'),'sha256').hexdigest()
read = lambda p: json.loads(p.read_bytes())

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--source',required=True)
    p.add_argument('--build-receipt',type=Path,required=True)
    p.add_argument('--diagnostics-receipt',type=Path,required=True)
    p.add_argument('--full-receipt',type=Path,required=True)
    p.add_argument('--apk',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    a=p.parse_args()
    assert re.fullmatch('[0-9a-f]{40}',a.source)
    assert '..' not in a.out.parts, 'Output parent traversal refused'
    out=a.out.absolute()
    assert not any(path.is_symlink() for path in (out,*out.parents)), 'Output symlink refused'
    out=out.resolve();base=(Q/'ci').resolve()
    assert out!=base and out.is_relative_to(base), 'Output must be new below R6 ci'
    out.mkdir(parents=True,exist_ok=False)
    build,diag,full=map(read,[a.build_receipt,a.diagnostics_receipt,a.full_receipt])
    assert build['passed'] is True and build['source_sha']==a.source
    assert diag['passed'] is True and full['passed'] is True
    assert diag['source_sha']==a.source and full['source_sha']==a.source, 'UI receipts not current-source'
    assert diag['suite']=='diagnostics' and full['suite']=='full'
    assert str(diag['run_id'])!=str(full['run_id']), 'UI lanes not separately registered'
    apk=a.apk.absolute();assert apk.is_file()
    certcmd=['java','-jar','/data/data/com.termux/files/home/rb_build/bt/android-14/lib/apksigner.jar','verify','--verbose','--print-certs',str(apk)]
    signed=subprocess.run(certcmd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
    (out/'apksigner.raw.log').write_text(signed.stdout)
    assert signed.returncode==0 and 'Verified using v2 scheme (APK Signature Scheme v2): true' in signed.stdout
    assert 'Number of signers: 1' in signed.stdout and CERT in signed.stdout
    assert re.search(r'Signer #1 certificate SHA-256 digest: '+CERT,signed.stdout)
    manifest=subprocess.run(['aapt2','dump','badging',str(apk)],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
    (out/'badging.raw.log').write_text(manifest.stdout)
    assert manifest.returncode==0
    assert "package: name='com.hcbiu.elcton' versionCode='12' versionName='0.2.10'" in manifest.stdout
    digest=sha(apk)
    main=build['rows'][0]
    assert main['name']=='elcton-phone-probe.apk' and main['package']=='com.hcbiu.elcton'
    assert main['sha256']==digest and main['bytes']==apk.stat().st_size, 'APK differs from exact verified build artifact'
    assert main['signer_sha256']==CERT and main['versionCode']=='12' and main['versionName']=='0.2.10'
    table=read(Q/'evidence/r7-ci-identity-final/table.json')
    current=read(Q/'current-identity.json')['source_identities']
    assert table['source_identities']==current, 'Delivery identity table is not final Q1 source'
    for path,row in current.items():
        raw=subprocess.check_output(['git','show',a.source+':'+path],cwd=ROOT,timeout=30)
        assert hashlib.sha256(raw).hexdigest()==row['current_sha256'], 'Committed delivery source differs: '+path
    reviewdir=Q/'reviews/closure-q3'
    closure=read(reviewdir/'dual-closure.json')
    reviewed=read(reviewdir/'reviewed-manifest.json')
    assert closure['passed'] is True and {r['axis'] for r in closure['axes']}=={'spec','quality'}
    assert closure['manifest_sha256']==sha(reviewdir/'reviewed-manifest.json')
    for path,expected in reviewed.items():
        assert hashlib.sha256(subprocess.check_output(['git','show',a.source+':'+path],cwd=ROOT,timeout=30)).hexdigest()==expected
    for axis in closure['axes']:
        assert sha(reviewdir/(axis['axis']+'-raw.txt'))==axis['raw_sha256']
    PHONE.mkdir(parents=True,exist_ok=True)
    target=PHONE/('hc课程表-0.2.10-code12-'+a.source[:8]+'-'+digest[:8]+'-signed.apk')
    assert not target.exists(), 'Existing main APK never overwritten'
    with apk.open('rb') as src,target.open('xb') as dst:shutil.copyfileobj(src,dst,1024*1024)
    assert sha(target)==digest and target.stat().st_size==apk.stat().st_size
    table=read(Q/'evidence/r7-ci-identity-final/table.json')
    record={'delivered':True,'source_sha':a.source,'versionCode':12,'versionName':'0.2.10','package':'com.hcbiu.elcton',
            'apk_path':str(target),'apk_bytes':target.stat().st_size,'apk_sha256':digest,'signer_certificate_sha256':CERT,
            'verified_v2':True,'signers':1,'build_receipt_sha256':sha(a.build_receipt),
            'diagnostics_receipt_sha256':sha(a.diagnostics_receipt),'full_receipt_sha256':sha(a.full_receipt),
            'build':build,'diagnostics':diag,'full':full,'identity_migration':table,
            'review_closure':closure,'review_manifest_sha256':sha(reviewdir/'reviewed-manifest.json'),
            'ci_links':{'build':'https://github.com/lantianhcgp/elcton-phone/actions/runs/'+str(build['build_run']),
                        'diagnostics':'https://github.com/lantianhcgp/elcton-phone/actions/runs/'+str(diag['run_id']),
                        'full':'https://github.com/lantianhcgp/elcton-phone/actions/runs/'+str(full['run_id'])},
            'scope':'Installable diagnostic build only; no Release, no device operation, unknown handshake root cause',
            'at':time.strftime('%Y-%m-%d %H:%M:%S %z')}
    (out/'receipt.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n')
    lines=['# R6 DELIVERY — 0.2.10 诊断版实际交付','',
        '版本：12 / 0.2.10；包名 com.hcbiu.elcton。仅诊断观测，不声称真机握手已修复；根因仍 unknown。',
        '不发 Release；未安装、未操作用户设备；表端/表盘/留白/haps未动。','',
        'APK：'+str(target),'字节数：'+str(target.stat().st_size),'SHA256：'+digest,
        '源码提交：'+a.source,'同签名证书 SHA256：'+CERT,'真实 apksigner v2=true，signers=1。','',
        '## 身份迁移（完整旧→最终新SHA）','']
    for path,row in table['source_identities'].items():
        lines += [Path(path).name, '旧：'+str(row['old_sha256'] or '新增，无旧SHA'),
                 'R5：'+row['r5_sha256'],'Q2：'+row.get('previous_q2_sha256',row['current_sha256']),
                 '最终（仅编译分隔空格）：'+row['current_sha256'],'']
    lines += ['版本字面：11 / 0.2.9 → 12 / 0.2.10；行为断言零改。','',
        '## CI 与评审链索引','',
        *[name+'：'+url for name,url in record['ci_links'].items()],
        '当前真双审 manifest：'+closure['manifest_sha256'],
        *[axis['axis']+'：qa/p2p-trace-0210/r6/reviews/'+axis['json_path']+' SHA256='+axis['json_sha256'] for axis in closure['axes']],
        '历史链：r6-spec-r1 FAIL → r6-spec-r2 PASS → r6-quality-r1 FAIL(Q-R6-001) → r6-spec-q1 PASS → r6-quality-q1 FAIL(helper) → Q2双审PASS → Kotlin1.9.24编译失败 → 当前Q3纯空格增量双审（全部原件保留）。','',
        '## 真实执行证据','',
        'HOST：JVM171、Python133零skip、HTTP3784、原表445源冻结；L3 afterREADY真RED→GREEN。',
        'Q-R6-001：真实HOST barrier RED→GREEN，原失败/quota/stop race与原断言保持。',
        'Android/云端构建、UI、实际 artifact/run_attempt 和完整精确 testcase/pixel 原门禁均以以下JSON为依据，非HOST替代。','',
        '构建回执：'+str(a.build_receipt),'诊断UI回执：'+str(a.diagnostics_receipt),'完整UI回执：'+str(a.full_receipt),
        '交付JSON：'+str(out/'receipt.json'),'',
        '旧029包未覆盖；所有RED和拒绝原件保留。请发起方自行装机/真机取流水，设备验收未由本轮执行。','']
    report='\n'.join(lines)
    (out/'DELIVERY.md').write_text(report)
    (Q/'DELIVERY.md').write_text(report)
    phone_report=target.with_suffix('.DELIVERY.md')
    with phone_report.open('x') as f:f.write(report)
    assert phone_report.is_file()
    print(json.dumps({'delivered':True,'apk':str(target),'sha256':digest,'bytes':target.stat().st_size,'report':str(phone_report)},ensure_ascii=False))

if __name__=='__main__':main()
