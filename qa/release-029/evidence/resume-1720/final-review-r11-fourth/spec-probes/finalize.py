import datetime
import hashlib
import json
import re
from pathlib import Path
from bind_inputs import current, compact, sha, load, save, ROOT, BASE, OUT, PROBES

initial=load(PROBES/'binding-initial.json')
focused=load(PROBES/'focused-execution.json')
assert focused['passed']
results=focused['original_test_results']
assert sum(r['count'] for r in results[:4])==25
assert results[4]['count']==5
assert all(r['passed'] and r['errors']==r['failures']==r['skips']==0 for r in results)
for i,row in enumerate(results):
    assert sha(Path(row['path']).read_bytes())==row['source_sha256']
    assert sha((PROBES/('tests-'+str(i)+'.log')).read_bytes())==row['log_sha256']
gate=BASE/'resume-fourth/gates-r11'
complete=load(gate/'complete.json');inputs=load(gate/'inputs-before.json')
assert sha((gate/'inputs-before.json').read_bytes())==complete['inputs_manifest_sha256']
assert complete==initial['gates_complete']
for kind,count in [('host',152),('python',133),('runtime',1)]:
    execution=load(gate/(kind+'.execution.json')); log=(gate/(kind+'.raw.log')).read_bytes()
    assert sha(log)==execution['log_sha256']==initial['gate_logs'][kind]['log_sha256']
    assert execution['exit_code']==0
    text=log.decode()
    match=re.search(r'Ran (\d+) tests',text) if kind=='python' else re.search(r'OK \((\d+) tests?\)',text)
    assert match and int(match.group(1))==count
    if kind=='python':assert not re.search(r'\.\.\. skipped|\bskipped=|^FAILED',text,re.M)
for kind in ('http','termux'):
    execution=load(gate/(kind+'.execution.json'));log=(gate/(kind+'.raw.log')).read_bytes()
    assert sha(log)==execution['log_sha256']==initial['gate_logs'][kind]['log_sha256'] and execution['exit_code']==0
http=load(gate/'http.raw.log');termux=load(gate/'termux.raw.log')
assert http['ok'] and http['assertions']==3784 and http['all_raw_checks_passed']
assert termux['host_exit_code']==0 and termux['listener_closed_after_test']
assert complete['termux']['count']==15

red_path=BASE/'resume-fourth/crash-containment-RED.execution.json';red=load(red_path)
assert red['returncode']==1 and red['script_sha256']==results[4]['source_sha256']
assert red['observer_sha256']==load(BASE/'final-review-r10-fourth/reviewed-manifest.json')['qa/cloud_emulator_observer.py']
red_stderr=BASE/'resume-fourth/crash-containment-RED.stderr.bin'
red_text=red_stderr.read_bytes().decode(errors='replace')
assert 'Ran 5 tests' in red_text and 'failures=3' in red_text
limit_red=load(BASE/'resume-fourth/r11/limits-first-RED.json')
assert limit_red['exit_code']==1 and sha(Path(limit_red['log']).read_bytes())==limit_red['sha256']
assert limit_red['test_sha256']==results[3]['source_sha256']
for namespace in ('focused-after','focused-opath'):
    execution=load(BASE/('resume-fourth/r11/'+namespace+'/execution.json'))
    for i,row in enumerate(execution):
        assert sha((BASE/('resume-fourth/r11/'+namespace+'/'+str(i)+'.log')).read_bytes())==row['log_sha256']
    if namespace=='focused-opath':assert all(row['exit_code']==0 for row in execution)

reviewed=load(OUT/'reviewed-manifest.json')
regenerated={p.relative_to(ROOT).as_posix():sha(p.read_bytes()) for p in (ROOT/'app/src/main').rglob('*') if p.is_file()}
regenerated['app/build.gradle.kts']=sha((ROOT/'app/build.gradle.kts').read_bytes())
products=dict(regenerated)
for base in ('app/src/test','app/src/androidTest','qa'):
    for p in (ROOT/base).rglob('*'):
        name=p.relative_to(ROOT).as_posix()
        if not p.is_file() or '__pycache__' in p.parts:continue
        if base=='qa' and (not (p.suffix in ('.py','.kt') or p.name.endswith('.kt.in')) or '/evidence/' in name):continue
        regenerated[name]=sha(p.read_bytes())
for path in ('.github/workflows/build.yml','.github/workflows/ui-smoke.yml','.gitattributes','.gitignore','build.gradle.kts','settings.gradle.kts','gradle.properties','qa/release-029/approved-release-delta.json','qa/release-029/SPEC.md','qa/release-029/TEST-ATTRIBUTION.md','qa/release-029/ANDROID-HARNESS-ATTRIBUTION.md','qa/release-029/RESUME-CHANGES.md'):
    regenerated[path]=sha((ROOT/path).read_bytes())
assert regenerated==reviewed and products==load(OUT/'product-manifest.json')
final=current()
assert final=={k:initial[k] for k in final}, 'Exact candidate drift during review'
for axis,row in initial['r10_original_false_raws'].items():
    assert sha((BASE/'final-review-r10-fourth'/(axis+'-raw.txt')).read_bytes())==row['sha256']
for axis,row in initial['r8_original_axes'].items():
    assert sha((BASE/'final-review-r8'/(axis+'-raw.txt')).read_bytes())==row['sha256']
final['inventory_independently_regenerated_exact']=True
final['frozen_input_files_same_bytes_as_initial']=True
final['timestamp']=datetime.datetime.now(datetime.timezone.utc).isoformat()
save('binding-immediate-before-raw.json',final)
raw={
 'axis':'spec','passed':True,'security_concerns':[],'logic_errors':[],'missing_requirements':[],
 'suggestions':[{'severity':'nonblocking','finding':'观测及finalizer仍是best-effort；1秒daemon join不保证内核采集/receipt完整。缺件只可unknown/pending，不能用child exit0、旧diagnostics绿或HOST绿替代新full及真机验收。'}],
 'summary':'R11 SPEC=true：R10真实祖先symlink与index TOCTOU拒绝项已在原未改安全5例和当前安全5例中闭合；5资源帽例及15原observer隔离例全绿，原25候选例零skip，另原安全5例/两索引分支通过。独立核130/130、37/37与549989B完整累计diff逐字节一致，R10仅observer改动+两新增测试，54旧测试与全部产品同bytes。经原R8双raw/closure及R3-R7产品字节链继承有界业务覆盖，不伪称全产品逐行重审。原R10两false/首RED全部不改；新CI/两云端/真机10min仍pending，本结论不是Android或交付PASS。',
 'reviewed_manifest_sha256':final['prepare']['reviewed_manifest_sha256'],
 'diff_sha256':final['prepare']['diff_sha256'],
 'product_sha256':final['prepare']['product_manifest_sha256'],
 'bindings':{**final['prepare'], 'actual_head':final['actual_head'],'head_pin':final['head_pin'],
     'canonical_encoding':'sha256(json.dumps(map,sort_keys=True,separators=(comma,colon),ensure_ascii=False).encode UTF-8), no newline; compact != pretty file SHA',
     'prepare_file_sha256':final['snapshot_files']['prepare.json']['sha256'],
     'snapshot_file_hashes':final['snapshot_files'],
     'candidate_full_before_after_git_checks':True,'candidate_guards_verified':final['candidate_checks'],
     'inventory_independently_regenerated_exact':True,'all_130_live_hashes_match':True,'all_37_live_hashes_match':True,
     'complete_live_diff_rebuilt_bytes_equal':True,'manifested_untracked_append':final['untracked_appended'],
     'complete_diff_command':'git diff --no-ext-diff e034de2f924dd6d96e31caa8e5a62e52474de718 -- <all 130 sorted reviewed paths>; append each manifested untracked git diff --no-ext-diff --no-index -- /dev/null path in git ls-files order',
     'freeze_rechecked_immediately_before_exclusive_write':True,
     'final_binding_evidence_path':str(PROBES/'binding-immediate-before-raw.json'),
     'final_binding_evidence_sha256':sha((PROBES/'binding-immediate-before-raw.json').read_bytes())},
 'coverage':{
     'mode':'R8原raw完整覆盖链继承 + 完整R8以来九个QA新改section语义审 + 全130输入身份绑定；不是130文件/37产品全逐行重新审。',
     'requirements_read':['qa/release-029/SPEC.md全文','qa/release-029/ANDROID-HARNESS-ATTRIBUTION.md全文','qa/release-029/RESUME-CHANGES.md全文','qa/release-029/evidence/resume-1720/resume-fourth/r11/PLAN.md全文'],
     'fully_read_changed_and_new':initial['changed_cumulative_sections'],
     'full_changed_sections':{'path':str(PROBES/'changed-since-r8.diff'),'bytes':(PROBES/'changed-since-r8.diff').stat().st_size,'sha256':initial['changed_sections_file_sha256']},
     'r8_original_axes':{axis:{'path':str(BASE/'final-review-r8'/(axis+'-raw.txt')),'sha256':row['sha256'],'passed':row['passed'],'summary':row['summary']} for axis,row in initial['r8_original_axes'].items()},
     'r8_dual_closure_sha256':initial['r8_closure_sha256'],'r3_r7_product_raw_binding_chain':initial['r3_r7_chain'],
     'inherited_semantic_limit':'R3原有界共享PhoneRuntime/15工具确认、revision/epoch/陈旧回调、STOP/拒绝、原4诊断、课表/取件/协议；R3 SPEC原false保留，R4闭合QA两项，R5/R6产品精确小修，R7/R8 QA修。不得把hash检查等同本轮全产品逐行审。',
     'r8_unchanged_entries':initial['r8_unchanged_entries'],'r8_changed_entries':initial['r8_changed_entries'],'r8_added_entries':initial['r8_added_entries'],'r8_removed_entries':initial['r8_removed_entries'],
     'all_37_product_manifest_full_bytes_equal_r8':True,'all_37_product_bytes_equal_HEAD':True,
     'r10_delta_changed':initial['r10_delta_changed'],'r10_delta_added':initial['r10_delta_added'],'old_test_files_byte_identical':54,
     'harvest_whole_file_inverse_exact':True,'workflow_single_wrapper_inverse_exact':True,'security_original_methods_and_assertions_ast_identical':True},
 'r10_findings_closed':[
     {'ids':['R10-SPEC-SEC-01','R10-STANDARDS-S1'],'status':'closed_in_precise_tested_scope','source':'qa/cloud_emulator_observer.py:102-126,129-136,149-156,232-239','evidence':'逐组件O_PATH/O_DIRECTORY/O_NOFOLLOW可信根打开source/output；原5未改测试真实实跑通过，包含source/output祖先symlink、output固定fd后rename+symlink、index叶symlink、正常exact payload。所有index包括source-absent和budget经pinned output fd O_CREAT|O_EXCL|O_NOFOLLOW 0600；另source-absent同race及既有index不覆盖实跑通过。'},
     {'ids':['R10-STANDARDS-L1'],'status':'closed_in_precise_tested_scope','source':'qa/cloud_emulator_observer.py:21-26,158-229','evidence':'scan256/copy64/depth8/index32768B/file32MiB/total64MiB；lazy scandir，budget跨递归聚合，any overflow返回True向外传播停止；索引预留在源read和复制之前。5资源真实文件例：257empty、257ignored+poison listdir、20层深度、缩帽500 index、缩帽12 total全部绿。64MiB/32MiB为静态常量及有界读取核验，未冒称新写64MiB压力文件。'},
     {'ids':['R10-STANDARDS-N1'],'status':'addressed_static','evidence':'叶prestat及fstat均nlink==1，同时REG/dev/ino校验；未声称native hardlink竞态动态复现。'}],
 'execution':{'focused_evidence_path':str(PROBES/'focused-execution.json'),'focused_evidence_sha256':sha((PROBES/'focused-execution.json').read_bytes()),'original_tests':results,'extra_indices':focused['extra_local_fake_filesystem'],'parent_complete_current_host':complete,'parent_gate_log_sha256':{k:v['log_sha256'] for k,v in initial['gate_logs'].items()},'gate_inputs_live_verified':len(inputs),'parent_gate_totals_independently_parsed':True},
 'failure_preservation':{'r10_original_false_raws':{axis:{'sha256':row['sha256'],'passed':False} for axis,row in initial['r10_original_false_raws'].items()},'before_manifest_originals_verified':True,'first_security_red':{**red,'stderr_sha256':sha(red_stderr.read_bytes()),'actual_tests':5,'actual_failures':3},'limits_first_red':limit_red,'focused_after_real_PermissionError_and_import_error_retained':True,'focused_opath_all_five_original_receipts_and_log_hashes_verified':True},
 'acceptance_limits':{'code_spec_gate_only':True,'android_pass':False,'release_acceptance':False,'fresh_exact_build_and_both_cloud_suites':'pending','physical_MCP_Bluetooth_MIUI_ten_minutes':'pending','original_full_43590641863':'RED retained; old diagnostics GREEN cannot replace it','version':'0.2.9/code11 product bytes unchanged','certificate_sha256':'fc08a0b474a8ffca5887bd5c88ac15e865a63a64eca81c10f344496c46d9ad94; no signing/build/package changes or new signing verification in this axis','push_allowed_by_this_axis_alone':False},
 'issues_encountered':['独占本轴绑定reader两次历史JSON位置KeyError，未触产品/候选；按R8原SPEC顶层及STANDARDS bindings真实schema修本轴reader，原失败另存，随后完整绑定exit0。历史R4首JSON+原尾注全raw SHA保持，未改原raw。','首security RED回执文件实际名crash-containment-RED.execution.json；首次猜名读取缺失，已找到并核真实回执/原stderr，未凭缺失判旧RED不存在。'],
 'files_created_or_modified_by_this_review':[str(OUT/'spec-raw.txt'),str(PROBES)+'/**'],
 'forbidden_actions_performed':{'implementation_or_original_tests_or_config_or_progress_modified':False,'commit':False,'push':False,'CI':False,'ADB':False,'phone_or_watch_actions':False},
 'completed_at':datetime.datetime.now(datetime.timezone.utc).isoformat()
}
assert raw['passed']==(not raw['security_concerns'] and not raw['logic_errors'] and not raw['missing_requirements'])
assert all(raw['bindings'][k]==v for k,v in final['prepare'].items())
# Final current() immediately precedes the exclusive raw publication; no source writes.
check=current();assert check['snapshot_files']==final['snapshot_files'] and check['prepare']==final['prepare']
wire=(json.dumps(raw,ensure_ascii=False,indent=2)+'\n').encode()
with (OUT/'spec-raw.txt').open('xb') as f:f.write(wire)
print(json.dumps({'axis':'spec','passed':True,'raw_absolute_path':str(OUT/'spec-raw.txt'),'raw_sha256':sha(wire),'raw_bytes':len(wire),'completed_at':raw['completed_at'],'verified_current_candidate':check['prepare'],'original_candidate_tests':25,'original_archived_security_tests':5,'additional_index_branch_probes':2},ensure_ascii=False,indent=2))
