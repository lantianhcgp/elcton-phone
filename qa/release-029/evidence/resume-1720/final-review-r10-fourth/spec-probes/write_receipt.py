#!/usr/bin/env python3
"""Exclusive SPEC receipt, with one last fresh binding immediately before writing."""
import datetime
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

ROOT=Path('/data/data/com.termux/files/home/elcton-phone-release-029-20261114')
F=ROOT/'qa/release-029/evidence/resume-1720/final-review-r10-fourth'
P=F/'spec-probes'
s=importlib.util.spec_from_file_location('spec_final_binding',P/'verify_candidate.py')
assert s and s.loader
v=importlib.util.module_from_spec(s);s.loader.exec_module(v)
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
a=json.loads((P/'independent-execution.json').read_bytes())
b=json.loads((P/'continuation-execution.json').read_bytes())
g=json.loads((P/'parent-gates-verified.json').read_bytes())
security=[{
 'id':'R10-SPEC-SEC-01','severity':'blocking','path':'qa/cloud_emulator_observer.py',
 'lines':[108,112,159,160],
 'requirement':'R9-STANDARDS-S1要求源与输出边界/TOCTOU fail-closed；ANDROID-HARNESS-ATTRIBUTION.md:42承诺every ancestor/leaf pinned+NOFOLLOW且RESUME-CHANGES.md:18仅修观测安全边界。',
 'finding':'源和复制目标的dirfd/叶NOFOLLOW确实修复直接源符号链接，但输出边界仍不完整：os.open(output,O_DIRECTORY|O_NOFOLLOW)只拒绝最后一个路径组件的符号链接，祖先仍跟随；最终crashdata-index.json又用词法Path.open，而不是固定output_fd。真实隔离反例中输出祖先链接穿透，及输出目录在固定fd后被换成链接后，索引写入允许词法输出之外。不能称every ancestor/leaf或输出TOCTOU已修。',
 'counterexamples':b['security_counterexamples'],
 'evidence_path':str(P/'continuation-execution.json'),
 'evidence_sha256':sha(P/'continuation-execution.json'),
 'required_resolution':'从可信根逐组件NOFOLLOW取得输出目录，所有新增输出包括index使用同一固定dirfd及O_EXCL|O_NOFOLLOW；保持诊断失败隔离、不改child或原harvest/断言。保留本RED并在新精确候选上复验两反例。',
 'limits':'仅合成目录和fixture，无真实凭据/设备读取；实证是输出越界/TOCTOU，未冒称已经泄漏真实secret。'
}]
logic=[];missing=[]
closed=[
 {'prior_ids':['R9-SPEC-01','R9-STANDARDS-L1'],'status':'closed_in_tested_scope','evidence':'独立6例：同一原归档成功/失败，分别仅wire open/close/mkdir抛错；R8原helper与R10真实helper返回、解包bytes、原error文本一致，subprocess mock每次恰1调用。原15测试另核正常成功/失败/空归档及全AST/execute_palette_phase。'},
 {'prior_ids':['R9-SPEC-02','R9-STANDARDS-L2'],'status':'closed_in_tested_scope','evidence':'独立真实包装进程8例：receipt open失败、receipt close失败、Thread.start失败、output mkdir失败，分别原child exit0/7；实际进程均0/7且每个once marker恰X，无retry；原15测试补正常收尾。'},
 {'prior_ids':['R9-SPEC-03','R9-STANDARDS-L3'],'status':'closed_in_tested_scope','evidence':'原测试direct-vs-wrapped native比较SIGTERM/SIGPIPE/SIGKILL；独立真实包装3例native -15/-13/-9，不再241/243。'},
 {'prior_ids':['R9-STANDARDS-L4'],'status':'closed_in_tested_scope','evidence':'原15中有blocked Event采样回归；另独立真实OS包装sample和finalizer永久阻塞各1例，不释放Event，进程仍exit7且实际约1.15s。daemon加有界join不会由非daemon挂住解释器。'},
 {'prior_ids':['R9-STANDARDS-S1'],'status':'partially_fixed_still_blocking','evidence':'正常crash exact bytes已复制；source leaf/dir/root及output leaf/root/nested dir symlink拒绝、unapproved log不复制；output ancestor及固定fd后的index词法重开仍真实越界。hardlink实跑因本机os.link缺失及libc EACCES未完成，不冒称该项动态绿。'},
 {'prior_ids':['R9-STANDARDS-N1','R9-SPEC suggestion unclosed files'],'status':'addressed_in_current_source','evidence':'新增wire/kernel/index/receipt均with管理；独立15日志无原unclosed ResourceWarning；wire/receipt close-only故障也不污染原结果。'}
]
coverage={
 'mode':'全128身份绑定+完整R8以来7新改文件/精确累计diff变化语义审；经原R8 raw/closure核验继承其有界产品覆盖，不称本轮128全文件逐行重新审。',
 'fully_read_requirements':['qa/release-029/SPEC.md','qa/release-029/ANDROID-HARNESS-ATTRIBUTION.md','qa/release-029/RESUME-CHANGES.md'],
 'fully_read_changed_and_new':['.github/workflows/ui-smoke.yml','qa/emulator_install_and_tour.py','qa/cloud_emulator_observer.py','qa/test_cloud_observer.py','qa/test_cloud_observer_isolation.py','qa/release-029/ANDROID-HARNESS-ATTRIBUTION.md','qa/release-029/RESUME-CHANGES.md'],
 'full_cumulative_changed_sections_read':{'path':str(P/'r8-r10-cumulative-changed-sections.diff'),'bytes':(P/'r8-r10-cumulative-changed-sections.diff').stat().st_size,'sha256':sha(P/'r8-r10-cumulative-changed-sections.diff')},
 'R8_chain_limit':'原R8记录继承R7至R4/bounded R3共享业务runtime、15 tools/确认、epoch/revision、STOP与拒绝、原4诊断、课表/取件/协议覆盖；原R3 false不回改，不重新审大历史。',
 'requirements_status':{'single_shared_business_runtime':'37产品与R8/HEAD同bytes，按已核R8有界链继承','old4_plus_new11':'父Termux真实原receipt逐名/15项核验；原产品同bytes','loopback_private_Bearer':'父原HTTP3784/Termux15及R8链；本轴无新联网或设备验收','default_keepalive_on_and_STOP':'原产品/35 app test同bytes，R8链继承；真机10min pending','cloud_original_assertions':'全文件去诊断新增try精确逆恢复r9 before.original，workflow只一次child wrapper替换，原产品判据/SDK/GPU/RAM/heap未更改'},
 'R9_counterexample_disposition':closed,
 'actual_full_state':'43590641863仍原RED；已读resume-fourth/FULL-43590641863-RECHECK.md及原report，未用旧diagnostics绿代R10 full。'
}
full=ROOT/'qa/release-029/evidence/resume-1720/full-44df9d0-evidence/artifact/report.json'
full_raw=json.loads(full.read_bytes())
assert full_raw['passed'] is False
assert a['observer15']['tests_run']==15 and a['observer15']['passed']
assert len(a['wire_io'])==6 and len(a['child_io'])==8 and len(a['native_signals'])==3
assert len(b['daemon'])==2 and all(d['native_exit']==7 for d in b['daemon'])
# Red counterexample is itself an asserted requirement violation, not a success label.
assert b['security_counterexamples'][0]['copy_through_symlink']
assert b['security_counterexamples'][1]['outside_index_written']
# Final live/diff check is intentionally immediately adjacent to receipt creation.
fresh,diff,delta=v.check()
with (P/'binding-immediate-before-raw.json').open('x') as f:json.dump(fresh,f,ensure_ascii=False,indent=2);f.write('\n')
if not fresh['passed']:
    missing.append({'id':'R10-FREEZE-DRIFT','severity':'blocking','mismatches':fresh['mismatches'],'finding':'最终现场漂移，当前review不可采用；父须重新freeze。'})
bindings={k:fresh[k] for k in ('actual_head','head_pin','reviewed_files','product_files','reviewed_manifest_sha256','diff_sha256','diff_bytes','prepare_raw_sha256','canonical_encoding','manifested_untracked_append','complete_live_diff_rebuilt_equal','candidates','candidate_checks','candidate_full_patch_checks','r9_original_raw_sha256')}
bindings.update({'product_manifest_sha256':fresh['product_sha256'],'product_sha256':fresh['product_sha256'],
 'candidate_before_sha256':fresh['candidates']['candidate-before.json']['sha256'],'candidate_after_sha256':fresh['candidates']['candidate-after.json']['sha256'],
 'all_128_live_SHA_match':not fresh['mismatches'],'all_37_live_SHA_match':fresh['r8_all_37_product_HEAD_match'],
 'final_live_mismatches':fresh['mismatches'],'freeze_rechecked_immediately_before_exclusive_write':True,
 'complete_live_diff_command':'git diff --no-ext-diff e034de2f924dd6d96e31caa8e5a62e52474de718 -- <all 128 sorted manifest paths>; append manifested untracked git diff --no-index /dev/null path',
 'final_binding_evidence_path':str(P/'binding-immediate-before-raw.json'),'final_binding_evidence_sha256':sha(P/'binding-immediate-before-raw.json')})
coverage.update({'r8_unchanged':fresh['r8_unchanged_count'],'r8_changed':fresh['r8_changed'],'r8_added':fresh['r8_added'],'r8_removed':fresh['r8_removed'],
 'cumulative_sections':fresh['cumulative_sections'],'all_37_product_exact_R8_HEAD':fresh['r8_all_37_product_HEAD_match'],'all_35_existing_app_test_inputs_exact_R8_HEAD':not fresh['old_app_test_drift'] and not fresh['HEAD_app_test_drift'] and fresh['old_app_test_files']==35,
 'preservation':fresh['preservation'],'r8_chain':fresh['r8_chain']})
raw={'axis':'spec','passed':not(security or logic or missing),'security_concerns':security,'logic_errors':logic,'missing_requirements':missing,
 'suggestions':[{'severity':'nonblocking','finding':'best-effort observer/finalizer允许缺少收尾receipt；缺失只能标unknown/pending，不能用observer child exit0或旧diag绿替代新full acceptance。'}],
 'summary':'R10 SPEC=false：R9三逻辑及STD四逻辑反例在实测范围已修；15新observer测试零skip全绿，128/37与533891B完整累计diff最终fresh精确绑定。安全门仍有1阻塞/2实证：输出祖先symlink穿透，固定output_fd后最终index仍Path.open造成TOCTOU根外写。产品/35 app tests同bytes、原判据/workflow逆恢复成立；full43590641863仍RED，新精确CI/两云端/真机MCP10min均pending。本review只增spec证据，不改产品/测试/配置、不push/dispatch/adb。',
 'reviewed_manifest_sha256':fresh['reviewed_manifest_sha256'],'diff_sha256':fresh['diff_sha256'],'product_sha256':fresh['product_sha256'],
 'bindings':bindings,'coverage':coverage,
 'independent_execution':{'scope':'HOST逻辑及真实OS child，不是Android/cloud/真机','observer15':a['observer15'],'observer15_log_path':str(P/'observer15.log'),'observer15_log_sha256':sha(P/'observer15.log'),
 'wire_io':a['wire_io'],'actual_child_io':a['child_io'],'native_signals':a['native_signals'],'permanently_blocked_daemon':b['daemon'],
 'crash_controls':b['crash'],'security_RED':b['security_counterexamples'],'cloud_guard':a['cloud_guard'],'actual_adb_calls':0,
 'execution_path':str(P/'independent-execution.json'),'execution_sha256':sha(P/'independent-execution.json'),
 'continuation_path':str(P/'continuation-execution.json'),'continuation_sha256':sha(P/'continuation-execution.json'),
 'hardlink_not_exercised':b['issues'],'first_probe_exit1_preserved':True,'first_continuation_exit1_preserved':True},
 'parent_gate_evidence_verified':{'path':str(P/'parent-gates-verified.json'),'sha256':sha(P/'parent-gates-verified.json'),'passed':g['passed'],'scope':g['scope'],
 'JVM152':True,'Python123_skip0':True,'HTTP3784':True,'Runtime1':True,'Termux15_HTTP200_portclosed':True,'complete_sha256':g['complete_sha256'],'termux_receipt_sha256':g['termux_receipt_sha256']},
 'acceptance_limits':{'new_SPEC_code_gate_pass':False,'new_full_cloud_pass':False,'old_full_43590641863':'RED retained','full_report_sha256':sha(full),'full_report_passed':full_raw['passed'],
 'both_new_exact_source_cloud_suites':'pending','release_delivery':'pending','physical_MCP_Bluetooth_MIUI_ten_minutes':'pending owned by parent','actual_ADB_device_push_dispatch_actions':0,'manifested_source_test_config_bytes_unchanged':fresh['passed'],'old_APK_HAP_not_written':True},
 'issues_encountered':b['issues']+[{'type':'reviewer_environment_only','finding':'首probe os.link不可用与续probe libc link EACCES均原样保留；仅新增recovery完成后段，不修改原测试/失败或硬链接返回。'}],
 'files_created_or_modified_by_this_review':[str(F/'spec-raw.txt'),str(P)+'/** (exclusive reviewer scripts/fixtures/logs/JSON only)'],
 'written_at':datetime.datetime.now().astimezone().isoformat()}
assert raw['passed']==(not raw['security_concerns'] and not raw['logic_errors'] and not raw['missing_requirements'])
encoded=(json.dumps(raw,ensure_ascii=False,indent=2)+'\n').encode('utf-8')
assert json.loads(encoded)['bindings']['product_manifest_sha256']==fresh['product_sha256']
with (F/'spec-raw.txt').open('xb') as file:file.write(encoded)
print(json.dumps({'axis':'spec','passed':raw['passed'],'raw_path':str(F/'spec-raw.txt'),'raw_sha256':hashlib.sha256(encoded).hexdigest(),
 'reviewed_manifest_sha256':raw['reviewed_manifest_sha256'],'diff_sha256':raw['diff_sha256'],'product_sha256':raw['product_sha256'],
 'summary':'15测试及R9逻辑反例已绿；仍1安全阻塞（2真实输出边界反例），SPEC=false。128/37完整533891B绑定无漂移；新full与真机仍pending。',
 'blockers':[{'id':'R10-SPEC-SEC-01','path':'qa/cloud_emulator_observer.py:108,112,159-160','finding':'输出祖先symlink可穿透；固定dirfd后index仍词法Path.open导致根外写。'}]},ensure_ascii=False))
