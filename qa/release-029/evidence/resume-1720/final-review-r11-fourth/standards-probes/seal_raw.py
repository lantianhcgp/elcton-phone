import hashlib,json,re,subprocess,sys,time
from pathlib import Path
ROOT=Path('/data/data/com.termux/files/home/elcton-phone-release-029-20261114');BASE=ROOT/'qa/release-029/evidence/resume-1720';R=BASE/'final-review-r11-fourth';OUT=R/'standards-probes'
sha=lambda b:hashlib.sha256(b).hexdigest()
compact=lambda x:json.dumps(x,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
load=lambda p:json.loads(p.read_bytes())
def receipt(p):return json.JSONDecoder().raw_decode(p.read_text().lstrip())[0]
identity=load(OUT/'identity.json');focus=load(OUT/'focused25.json');extra=load(OUT/'extra-probes.json');scope=load(OUT/'scope-checks.json');prep=load(R/'prepare.json');reviewed=load(R/'reviewed-manifest.json');product=load(R/'product-manifest.json')
assert focus['success'] and focus['tests_run']==25 and not any(focus[k] for k in ('failures','errors','skipped')) and all(x['passed'] for x in extra)
assert sha((OUT/'focused25.log').read_bytes())==focus['log_sha256']
gates=BASE/'resume-fourth/gates-r11';complete=load(gates/'complete.json');inputs=load(gates/'inputs-before.json');assert len(inputs)==152 and sha(compact(inputs))==complete['inputs_manifest_sha256'];assert all(sha((ROOT/p).read_bytes())==s for p,s in inputs.items())
gate_rows={}
for n in ('host','python','http','runtime','termux'):
    ex=load(gates/(n+'.execution.json'));raw=(gates/(n+'.raw.log')).read_bytes();assert ex['exit_code']==0 and sha(raw)==ex['log_sha256']
    gate_rows[n]={'execution_sha256':sha((gates/(n+'.execution.json')).read_bytes()),'raw_sha256':sha(raw),'exit_code':0}
assert re.search(rb'Ran 133 tests .*\n\nOK\s*$',(gates/'python.raw.log').read_bytes())
assert b'OK (152 tests)' in (gates/'host/junit.log').read_bytes()
assert b'OK (1 test)' in (gates/'runtime.raw.log').read_bytes()
http=load(gates/'http.raw.log');assert http['assertions']==3784 and http['ok'] and http['all_raw_checks_passed']
term=load(gates/'termux/receipt.json');assert term['count']==15 and term['http_status']==200 and term['passed'] and term['listener_closed']
old10=load(BASE/'final-review-r10-fourth/reviewed-manifest.json');oldtest=[p for p in old10 if p.startswith(('app/src/test/','app/src/androidTest/')) or p.startswith('qa/test_')];assert len(oldtest)==54 and all(old10[p]==reviewed[p] for p in oldtest)
historical={}
for axis in ('standards','spec'):
    p=BASE/'final-review-r10-fourth'/(axis+'-raw.txt');x=receipt(p);assert x['passed'] is False and any(x[k] for k in ('security_concerns','logic_errors','missing_requirements'));historical[axis]=sha(p.read_bytes())
before=load(BASE/'resume-fourth/r11/before-manifest.json');assert all(sha((ROOT/v['original']).read_bytes())==v['sha256'] and len((ROOT/v['original']).read_bytes())==v['bytes'] for v in before.values())
red=load(BASE/'resume-fourth/crash-containment-RED.execution.json');assert red['returncode']==1 and red['observer_sha256']==before['qa/cloud_emulator_observer.py']['sha256'] and red['script_sha256']==sha((BASE/'resume-fourth/test_crash_observer_containment.py').read_bytes());red_log=(BASE/'resume-fourth/crash-containment-RED.stderr.bin').read_bytes();assert b'Ran 5 tests' in red_log and b'failures=3' in red_log
limits=load(BASE/'resume-fourth/r11/limits-first-RED.json');assert limits['exit_code']==1 and sha(Path(limits['log']).read_bytes())==limits['sha256'] and limits['test_sha256']==reviewed['qa/test_cloud_observer_crash_limits.py']
preserved={}
for p in ('resume-fourth/r11/PLAN.md','resume-fourth/crash-containment-RED.execution.json','resume-fourth/crash-containment-RED.stderr.bin','resume-fourth/r11/before-manifest.json','resume-fourth/r11/limits-first-RED.log','resume-fourth/r11/focused-after/execution.json','resume-fourth/r11/focused-opath/execution.json'):
    preserved[p]=sha((BASE/p).read_bytes())
bindings=dict(prep);bindings.update({'head':identity['head'],'current_head':identity['head'],'head_pin':identity['head_pin'],'prepare_raw_sha256':identity['prepare_raw_sha256'],'manifest_raw_sha256':identity['manifest_raw_sha256'],'product_sha256':prep['product_manifest_sha256'],'complete_diff_equal':True,'scope_regenerated_exact':True,'live_mismatches':[],'product_mismatches':[],'untracked_appended':identity['untracked_appended'],'hash_encoding':'Manifest SHA256 is sorted compact JSON sort_keys=True,separators comma/colon,ensure_ascii=False,UTF8,no newline; raw/candidate/diff hashes are exact bytes.'})
report={'axis':'standards','passed':True,'security_concerns':[],'logic_errors':[],'missing_requirements':[],'suggestions':[],
'summary':'R11 STANDARDS=true，仅当前QA观察修复审查，不是Android/云端/真机PASS。独立130/130输入、37/37产品、549989B完整累计diff及compact身份均核；R10 source/output祖先symlink及index TOCTOU真实反例已闭合。原25测试实跑零fail/error/skip，另5小范围本地探针全绿：缺源index换root与existing symlink安全、handle nlink再核、生产32768B index及256 lazy源stat边界。64 copy/depth8/32MiB per-file/64MiB total帽及预算截停已实现。完整R8双raw和R4→R7原覆盖链SHA/closure/manifest/diff继承核验，不伪称全产品逐行新审。原R10两false与RED/先期PermissionError/PYTHONPATH失败全保留；当前完整HOST原日志绿，云端/真机仍pending。',
'reviewed_manifest_sha256':prep['reviewed_manifest_sha256'],'diff_sha256':prep['diff_sha256'],'product_sha256':prep['product_manifest_sha256'],'bindings':bindings,
'coverage':{'mode':'完整当前身份/累计diff重建 + R8以来四改五新增完整语义审核 + 精确继承原R8记载范围；不是130文件或37产品逐行新审','full_read_changed':identity['r8_changed'],'full_read_added':identity['r8_added'],'r8_unchanged_inputs':identity['r8_unchanged'],'removed':identity['r8_removed'],'cumulative_diff':identity['cumulative_diff'],'product_37_exact_r8_and_HEAD':True,'old_test_54_exact_r10':True,'r8_all125_inputs_equal_HEAD44df9d0':True,'r8_raw_sha256':identity['r8_raw_sha256'],'r8_dual_closure_sha256':identity['r8_closure_sha256'],'inherited_chain':identity['prior_chain'],'inheritance_limit':'继承R8原raw明确的R7→R4和有界R3业务覆盖；R3 SPEC原false不回写、不改成全文件逐行审。','standards_sources':['mattpocock-code-review 12 smells','fail-closed-review-loops','qa/release-029/SPEC.md','qa/release-029/ANDROID-HARNESS-ATTRIBUTION.md','qa/release-029/RESUME-CHANGES.md','resume-fourth/r11/PLAN.md'],'smell_baseline_result':'小范围12 smells未见新硬阻塞；兼容旧AST单独加载的inline诊断不强制抽helper。','scope_check':scope},
'counterexample_resolution':[{'id':'R10-STANDARDS-S1','status':'closed','proof':'/ trusted O_PATH anchor，所有源/输出祖先逐组件dirfd+O_DIRECTORY|O_NOFOLLOW，最终目录pin；源存在/不存在index与budget同pin、600+O_EXCL|O_NOFOLLOW，无lexical reopen。原5安全测试含真实rename/symlink race全绿。'},{'id':'R10-STANDARDS-L1','status':'closed','proof':'lazy scandir扫描256、copy64、depth8、index32768、每file33554432/total67108864；预留index先于读取/复制。257empty与257ignored/depth20/缩小index-total负例全绿；额外生产帽nested index32662B/copy27后截停及源lstat256实测。'},{'id':'R10-STANDARDS-N1','status':'closed_for_tested_fault','proof':'fstat再次检查regular,nlink1,dev/ino；nlink2合成fstat实际拒绝，非native hardlink竞态证明。'}],
'independent_execution':{'focused25':focus,'extra_probes':extra,'probe_root':str(OUT),'real_ADB_CI_kernel_or_physical_calls':0},
'host_evidence_readback':{'scope':'只读核当前父全HOST原回执/原日志/152输入，同源；未在本轴重新编译JVM或启动业务listener','complete_raw_sha256':sha((gates/'complete.json').read_bytes()),'inputs152_compact_sha256':complete['inputs_manifest_sha256'],'host152_python133_zero_skip_http3784_runtime1_termux15':True,'execution_logs':gate_rows},
'preservation':{'r10_false_raw_sha256':historical,'red_and_plan_sha256':preserved,'security_probe_assertions_identical_except_ROOT':True,'harvest_inverse_whole_file_equal':True,'workflow_inverse_whole_file_equal':True,'all_54_old_tests_exact':True},
'acceptance_limits':{'android_pass':False,'physical_pass':False,'release_delivery_complete':False,'new_source_matched_cloud_suites':'pending','physical_pure_MCP_and_10min':'pending','old_full43590641863':'RED retained; no new emulator cause proved','signing_version_SCOPE':'no changes; product byte identity only, not fresh APK signature verification','push_CI_ADB_install_or_progress_write_performed':False,'best_effort_finalizer':'bounded join preserves child exit; index/receipt can be absent on slow capture, never proves complete observation'},
'issues_encountered':['Reviewer-only first historical pin assumption failed on R8 uncommitted candidate McpKeepAliveTest. Original script retained; read-only continuation verified all R8 candidate125 bytes and cumulative diff at committed HEAD44df9d0. Not a candidate blocker.','Independent baseline R8 oldtest count52, R10 count54 includes two observer test files; verified54 explicitly rather than rounding52.'],
'files_created_or_modified_by_this_review':[str(R/'standards-raw.txt'),str(OUT)+'/**']}
assert report['passed']==(not report['security_concerns'] and not report['logic_errors'] and not report['missing_requirements'])
# Immediate final freeze: every pretty input + compact + 130 current bytes + entire diff before exclusive raw.
assert prep==identity['bindings'] and sha((R/'prepare.json').read_bytes())==identity['prepare_raw_sha256']
for n,s in identity['manifest_raw_sha256'].items():assert sha((R/n).read_bytes())==s
assert sha(compact(reviewed))==prep['reviewed_manifest_sha256'] and sha(compact(product))==prep['product_manifest_sha256']
assert all(sha((ROOT/p).read_bytes())==s for p,s in reviewed.items())
assert (R/'candidate-before.json').read_bytes()==(R/'candidate-after.json').read_bytes()==(ROOT/'qa/release-029/approved-release-delta.json').read_bytes()
assert sha((R/'candidate-after.json').read_bytes())==prep['candidate_after_sha256']
b=subprocess.check_output(['git','diff',identity['head_pin'],'--',*sorted(reviewed)],cwd=ROOT)
u=subprocess.check_output(['git','ls-files','--others','--exclude-standard'],cwd=ROOT).decode().splitlines()
for p in u:
    if p in reviewed:
        x=subprocess.run(['git','diff','--no-index','--','/dev/null',p],cwd=ROOT,capture_output=True);assert x.returncode in (0,1);b+=x.stdout
assert b==(R/'current.diff').read_bytes() and len(b)==prep['diff_bytes'] and sha(b)==prep['diff_sha256']
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT).decode().strip()==identity['head']
bindings['freeze_rechecked_immediately_before_exclusive_write']=True
raw=(json.dumps(report,ensure_ascii=False,indent=2)+'\n').encode();target=R/'standards-raw.txt'
with target.open('xb') as f:f.write(raw)
actual=target.read_bytes();assert actual==raw;v=json.loads(actual);assert v['axis']=='standards' and v['passed'] and v['passed']==(not v['security_concerns'] and not v['logic_errors'] and not v['missing_requirements'])
print(json.dumps({'raw':str(target),'sha256':sha(actual),'passed':True,'reviewed_files':130,'diff_bytes':len(b),'focused_tests':25},ensure_ascii=False))
