#!/usr/bin/env python3
"""Only produce final acceptance/report after all actual pinned real receipts are green."""
import argparse
import datetime
import hashlib
import json
from pathlib import Path
import subprocess

CERT = 'fc08a0b474a8ffca5887bd5c88ac15e865a63a64eca81c10f344496c46d9ad94'
REPO = 'lantianhcgp/elcton-phone'
ROOT = Path(__file__).resolve().parents[5]
EVIDENCE = ROOT / 'qa/release-029/evidence/resume-1720'


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def original(path):
    return json.loads(Path(path).read_bytes())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--pipeline', type=Path, required=True)
    parser.add_argument('--pipeline-result', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--destination-dir', type=Path, required=True)
    args = parser.parse_args()
    pipeline = args.pipeline
    result = original(args.pipeline_result)
    assert result['passed'] is True and len(result['cloud_results']) == 2
    source = result['source_sha']
    assert len(source) == 40 and all(c in '0123456789abcdef' for c in source)
    build = original(pipeline / 'build-verification/receipt.json')
    assert build['passed'] is True and build['source_sha'] == source
    assert str(build['build_run']) == str(result['build_run'])
    assert build['gradle']['tests'] == 153 and build['gradle']['skipped'] == 0
    main_apk = build['rows'][0]
    assert (main_apk['package'], main_apk['versionName'], main_apk['versionCode']) == ('com.hcbiu.elcton', '0.2.9', '11')
    assert main_apk['signer_sha256'] == CERT and main_apk['v2'] is True and main_apk['zip_crc'] is True
    assert digest(main_apk['path']) == main_apk['sha256']
    review = EVIDENCE / 'final-review-r11-fourth'
    closure = original(review / 'dual-closure.json')
    assert closure['passed'] is True and closure['reviewed_files'] == 130 and closure['product_files'] == 37
    for row in closure['axes']:
        assert digest(review / (row['axis'] + '-raw.txt')) == row['raw_sha256']
    inputs = original(review / 'reviewed-manifest.json')
    for path, expected in inputs.items():
        assert digest(ROOT / path) == expected
        assert hashlib.sha256(subprocess.check_output(['git', 'show', source + ':' + path], cwd=ROOT)).hexdigest() == expected
    local = original(EVIDENCE / 'resume-fourth/gates-r11/complete.json')
    assert local['passed'] is True and local['host_tests'] == 152 and local['python_tests'] == 133 and local['python_skipped'] == 0
    assert local['http_report']['assertions'] == 3784 and local['runtime_tests'] == 1
    old = original(EVIDENCE / 'resume-fourth/protected-inputs-at-start.json')
    assert len(old['rows']) == 3 and all(digest(row['path']) == row['sha256'] for row in old['rows'])
    assert main_apk['sha256'] not in {row['sha256'] for row in old['rows'] if row['path'].endswith('.apk')}, 'New exact candidate hash equals protected old APK'
    actual = {}
    assert {row['suite'] for row in result['cloud_results']} == {'diagnostics', 'full'}
    for row in result['cloud_results']:
        assert row['passed'] is True and row['wait_exit'] == 0 and row['verify_exit'] == 0
        receipt_path = Path(row['receipt'])
        assert digest(receipt_path) == row['receipt_sha256']
        receipt = original(receipt_path)
        assert receipt['passed'] is True and receipt['source_sha'] == source and str(receipt['run_id']) == str(row['run'])
        incoming = pipeline / (row['suite'] + '-artifact')
        run = original(incoming / 'run-api.json')
        attempt = original(incoming / 'attempt-api.json')
        assert run['head_sha'] == source and run['status'] == 'completed' and run['conclusion'] == 'success'
        assert run['run_attempt'] == attempt['run_attempt'] and attempt['conclusion'] == 'success'
        registered = original(pipeline / (row['suite'] + '-dispatch/registered.json'))
        assert registered['inputs'] == {'build_run': str(result['build_run']), 'build_sha': source,
                                       'api_level': '33', 'navigation_mode': 'three-button', 'qa_suite': row['suite']}
        assert str(registered['run']['databaseId']) == str(row['run'])
        actual[row['suite']] = {'run': str(row['run']), 'url': run['html_url'], 'attempt': run['run_attempt'],
                                'receipt_sha256': row['receipt_sha256']}
    out = args.out
    out.mkdir(parents=True, exist_ok=False)
    destination = args.destination_dir / ('hc课程表-0.2.9-code11-' + source[:7] + '-全绿合并版-signed.apk')
    args.destination_dir.mkdir(parents=True, exist_ok=True)
    assert not destination.exists(), 'Do not overwrite any candidate'
    with Path(main_apk['path']).open('rb') as incoming, destination.open('xb') as delivered:
        while True:
            block = incoming.read(1024 * 1024)
            if not block:
                break
            delivered.write(block)
    assert destination.stat().st_size == main_apk['bytes'] and digest(destination) == main_apk['sha256']
    receipt = {'passed': True, 'versionName': '0.2.9', 'versionCode': 11, 'source_sha': source,
               'created_at': datetime.datetime.now().astimezone().isoformat(),
               'build_run': str(result['build_run']), 'apk': {'path': str(destination.resolve()),
               'bytes': main_apk['bytes'], 'sha256': main_apk['sha256'], 'certificate_sha256': CERT, 'v2': True},
               'cloud': actual, 'review': {'reviewed_files': 130, 'product_files': 37, 'closure_sha256': digest(review / 'dual-closure.json')},
               'gates': {'Gradle':153, 'JVM':152, 'Python':133, 'Python_skips':0, 'HTTP_host_assertions':3784, 'Runtime':1, 'MCP_tools':15},
               'old_deliveries_unchanged':old['rows'],
               'physical_acceptance': {'pure_MCP_import_sync_readback':'pending, owner', 'background_10min_health_error_tail':'pending, owner'},
               'scope':'Exact build+both fresh cloud suites+APK only; final evidence commit/external all-byte readback must still close; NO physical/watch/WE PASS'}
    (out / 'actual-delivery.json').open('x').write(json.dumps(receipt, ensure_ascii=False, indent=2) + '\n')
    text = '\n'.join([
        '# 0.2.9 第四轮：代码/构建/两云端已全绿；真机待发起方', '',
        '- 精确源码：' + source,
        '- 版本：0.2.9 / versionCode 11；15 MCP工具（旧4+新增11）、默认保活开、127.0.0.1本地Bearer、共用UI业务层。',
        '- 最新独立双轴：SPEC/STANDARDS通过；130输入/37产品/完整549989B累计diff精确绑定。原R9/R10 false原件全保留。',
        '- 当前HOST：JVM152/152，Python133/133零skip，HTTP3784，Runtime1/1，Termux15工具HTTP200且listener关闭。',
        '- 精确构建：' + str(result['build_run']) + '，Gradle153/153零skip，主/测试APK固定fc08…ad94与v2/CRC均实际核过。',
        '- 诊断云端：' + actual['diagnostics']['url'],
        '- full云端：' + actual['full']['url'],
        '- 新APK：' + str(destination.resolve()),
        '- APK字节：' + str(main_apk['bytes']),
        '- APK SHA256：' + main_apk['sha256'],
        '- 证书 SHA256：' + CERT,
        '- 原0.2.8、9e300f9候选及1.1.15HAP三件SHA原样，未覆盖/删改。',
        '', '## 失败及因果边界',
        '- 旧full43590641863：cold-pink-dark用例OK后harvest失败；ADB RC1/console5554拒连已证。旧676原件保真，OOM/GPU等机制未证实。新runner原配置重跑通过不等于证明旧故障底层根因。',
        '- R11只修QA观察失败隔离/信号/有界收尾及crash目录安全/资源上限，产品与原断言/配置不迁就。所有旧RED/拒绝回执/原件永久保留。',
        '', '## 真机层（未执行，明确pending）',
        '- 纯MCP 导入→同步→回读：pending，归发起方。',
        '- 退后台10分钟 /health200 + error_tail：pending，归发起方。',
        '- 云端HOST/普通Home5秒采样不替代MIUI/蓝牙/真实WearEngine通信或真机十分钟。',
        '', '## 尾部提交/读回',
        '- 本报告由真实新回执生成；报告+全部尾部证据还要精确commit/push并逐字节外部读回闭合。最后读回回执会在独立收尾文件中绑定，不先冒称已完成。', ''
    ])
    (out / 'FINAL-REPORT.md').open('x').write(text)
    print(json.dumps({'passed':True, 'source_sha':source, 'apk':str(destination.resolve()), 'sha256':main_apk['sha256'],
                      'cloud':actual, 'tail_external_readback':'pending'}, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()
