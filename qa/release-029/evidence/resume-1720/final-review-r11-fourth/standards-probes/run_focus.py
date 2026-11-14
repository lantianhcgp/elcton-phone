import ast, hashlib, importlib.util, io, json, os, re, subprocess, sys, tempfile, time, unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path('/data/data/com.termux/files/home/elcton-phone-release-029-20261114')
OUT=ROOT/'qa/release-029/evidence/resume-1720/final-review-r11-fourth/standards-probes'
BASE=ROOT/'qa/release-029/evidence/resume-1720'
sys.path.insert(0,str(ROOT));sys.dont_write_bytecode=True
scratch=OUT/'scratch';scratch.mkdir(exist_ok=False)
tempfile.tempdir=str(scratch);os.environ['TMPDIR']=str(scratch);os.environ['PYTHONDONTWRITEBYTECODE']='1'
sha=lambda b:hashlib.sha256(b).hexdigest()
modules=('qa.test_cloud_observer','qa.test_cloud_observer_isolation','qa.test_cloud_observer_crash_containment','qa.test_cloud_observer_crash_limits')
suite=unittest.defaultTestLoader.loadTestsFromNames(modules);assert suite.countTestCases()==25
log=io.StringIO();start=time.monotonic();result=unittest.TextTestRunner(stream=log,verbosity=2).run(suite)
text=log.getvalue();(OUT/'focused25.log').open('x').write(text)
report={'tests_run':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'skipped':len(result.skipped),'seconds':time.monotonic()-start,'log_sha256':sha(text.encode()),'success':result.wasSuccessful()}
(OUT/'focused25.json').open('x').write(json.dumps(report,indent=2)+'\n')
assert result.wasSuccessful() and result.testsRun==25 and not result.skipped
print(json.dumps(report));print(text)
def observer():
    s=importlib.util.spec_from_file_location('independent_r11_probe',ROOT/'qa/cloud_emulator_observer.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def capture(m,src,out):
    actual=m.Path
    with patch.object(m,'Path',side_effect=lambda p:src if str(p)=='/tmp/android-runner' else actual(p)):
        m.capture_crashdata(out)
rows=[]
# Missing source: swap output immediately at the final index open. Both final index and budget must use the original fd.
with tempfile.TemporaryDirectory() as directory:
    b=Path(directory);out=b/'output';out.mkdir();outside=b/'outside';outside.mkdir();saved=b/'pinned';m=observer();real=os.open;swaps=[]
    def open_swap(p,flags,*a,**kw):
        if p=='crashdata-index.json' and not swaps:
            assert kw.get('dir_fd') is not None
            out.rename(saved);out.symlink_to(outside,target_is_directory=True);swaps.append(True)
        return real(p,flags,*a,**kw)
    with patch.object(m.os,'open',side_effect=open_swap): capture(m,b/'absent',out)
    assert swaps==[True] and list(outside.iterdir())==[]
    assert json.loads((saved/'crashdata-index.json').read_bytes())==[]
    assert json.loads((saved/'crashdata-budget.json').read_bytes())['stopped_reason']=='source-absent'
    rows.append({'case':'source_absent_index_open_TOCTOU','passed':True,'outside_writes':0,'index_and_budget_pinned':True,'index_mode':oct((saved/'crashdata-index.json').stat().st_mode&0o777)})
# Real final index writer sentinel, no overwrites even if the source is absent.
with tempfile.TemporaryDirectory() as directory:
    b=Path(directory);out=b/'output';out.mkdir();target=b/'outside';target.write_bytes(b'local sentinel not secret');(out/'crashdata-index.json').symlink_to(target);m=observer();rejected=False
    try: capture(m,b/'absent',out)
    except FileExistsError: rejected=True
    assert rejected and target.read_bytes()==b'local sentinel not secret'
    rows.append({'case':'source_absent_existing_index_symlink','passed':True,'external_bytes_unchanged':True,'rejected':rejected})
# Inode/link recheck occurs on pinned source fd before read, not just old lstat. Inject one fstat nlink2 without changing actual fixture.
with tempfile.TemporaryDirectory() as directory:
    b=Path(directory);src=b/'source';src.mkdir();(src/'emu-crash-test.dmp').write_bytes(b'local payload');out=b/'output';out.mkdir();m=observer();real=os.fstat;hits=[]
    def fstat(fd):
        x=real(fd)
        if x.st_size==13 and x.st_mode & 0o170000 == 0o100000:
            v=list(x);v[3]=2;hits.append(True);return os.stat_result(v)
        return x
    rejected=False
    with patch.object(m.os,'fstat',side_effect=fstat):
        try:capture(m,src,out)
        except OSError:rejected=True
    assert hits and rejected and not (out/'emulator-crashdata/emu-crash-test.dmp').exists()
    rows.append({'case':'post_stat_source_nlink2','passed':True,'rejected':True,'scope':'synthetic fstat only; not native hardlink race'})
# Production 32768 cap with long names and nested paths; never shrink the actual bound.
with tempfile.TemporaryDirectory() as directory:
    b=Path(directory);src=b/'source';src.mkdir();out=b/'output';out.mkdir();p=src
    for n in range(8):p=p/(str(n)+'x'*120);p.mkdir()
    for n in range(50):(p/('emu-crash-'+str(n)+'y'*120+'.dmp')).write_bytes(b'')
    m=observer();capture(m,src,out);index=(out/'crashdata-index.json').read_bytes();records=json.loads(index);budget=json.loads((out/'crashdata-budget.json').read_bytes())
    assert len(index)<=32768 and budget['stopped_reason']=='index-limit' and len(records)==budget['copied_files'] and 0<len(records)<50
    rows.append({'case':'production_index32768_nested_empty','passed':True,'index_bytes':len(index),'copied':len(records),'budget':budget})
# Count only source stat/open operations: 257 ignored entries must do no more than 256 source lstats.
with tempfile.TemporaryDirectory() as directory:
    b=Path(directory);src=b/'source';src.mkdir();out=b/'output';out.mkdir()
    for n in range(257):(src/('ignored-'+str(n)+'.log')).write_bytes(b'')
    m=observer();real=os.stat;hits=[]
    def st(p,*a,**kw):
        if isinstance(p,str) and p.startswith('ignored-') and kw.get('dir_fd') is not None:hits.append(p)
        return real(p,*a,**kw)
    with patch.object(m.os,'stat',side_effect=st):capture(m,src,out)
    budget=json.loads((out/'crashdata-budget.json').read_bytes());assert len(hits)==256 and budget['scanned_entries']==256 and budget['stopped_reason']=='scan-limit'
    rows.append({'case':'lazy_source_stat256','passed':True,'actual_source_lstats':len(hits),'budget':budget})
(OUT/'extra-probes.json').open('x').write(json.dumps(rows,indent=2)+'\n');print(json.dumps(rows))
# Exact original security probe class including every assertion; ROOT relocation and final empty line only.
original=(BASE/'resume-fourth/test_crash_observer_containment.py').read_text();current=(ROOT/'qa/test_cloud_observer_crash_containment.py').read_text()
def omit_root(t):
    tree=ast.parse(t);tree.body=[n for n in tree.body if not(isinstance(n,ast.Assign) and any(isinstance(a,ast.Name) and a.id=='ROOT' for a in n.targets))];return ast.dump(tree,include_attributes=False)
assert omit_root(original)==omit_root(current)
# Entire harvest inverse after deleting only the unique diagnostic Try and its immediate added comment.
p=ROOT/'qa/emulator_install_and_tour.py';txt=p.read_text();tree=ast.parse(txt);fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='harvest_palettes');tries=[n for n in fn.body if isinstance(n,ast.Try) and any(isinstance(x,ast.Name) and x.id=='wire_target' for x in ast.walk(n))];assert len(tries)==1
lines=txt.splitlines(keepends=True);n=tries[0];a=n.lineno-1;z=n.end_lineno
assert lines[a-1].lstrip().startswith('#')
inverse=''.join(lines[:a-1]+lines[z:]).encode();archive=(BASE/'resume-third/r9/emulator_install_and_tour.py.before.original').read_bytes();assert inverse==archive
wf=(ROOT/'.github/workflows/ui-smoke.yml').read_bytes();reversed_wf=wf.replace(b'python3 -B qa/cloud_emulator_observer.py -- python3 qa/emulator_install_and_tour.py',b'python3 qa/emulator_install_and_tour.py');assert wf!=reversed_wf and reversed_wf==(BASE/'resume-third/r9/ui-smoke.yml.before.original').read_bytes()
r8=json.loads((BASE/'final-review-r8/reviewed-manifest.json').read_bytes());reviewed=json.loads((OUT.parent/'reviewed-manifest.json').read_bytes());oldtests=[p for p in r8 if p.startswith(('app/src/test/','app/src/androidTest/')) or p.startswith('qa/test_')];assert all(r8[p]==reviewed[p] and sha((ROOT/p).read_bytes())==r8[p] for p in oldtests)
checks={'security_probe_ast_identical_except_ROOT':True,'harvest_inverse_whole_file_equal':True,'workflow_inverse_whole_file_equal':True,'original_test_files_exact':len(oldtests),'extra_probe_count':len(rows),'real_adb_or_kernel_calls':0}
(OUT/'scope-checks.json').open('x').write(json.dumps(checks,indent=2)+'\n');print(json.dumps(checks))
