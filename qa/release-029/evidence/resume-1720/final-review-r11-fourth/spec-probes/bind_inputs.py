import ast
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path('/data/data/com.termux/files/home/elcton-phone-release-029-20261114')
BASE = ROOT / 'qa/release-029/evidence/resume-1720'
OUT = BASE / 'final-review-r11-fourth'
PROBES = OUT / 'spec-probes'
def sha(b): return hashlib.sha256(b).hexdigest()
def compact(o): return json.dumps(o, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()
def load(p): return json.loads(p.read_bytes())
def first_json(p): return json.JSONDecoder().raw_decode(p.read_text())[0]
def git(*args): return subprocess.check_output(['git', *args], cwd=ROOT)
def save(name, value):
    with (PROBES/name).open('xb') as f: f.write((json.dumps(value,ensure_ascii=False,indent=2)+'\n').encode())
def sections(raw):
    blocks = raw.split(b'diff --git ')
    assert blocks[0] == b''
    return {b.split(b'\n',1)[0].split(b' b/',1)[1].decode():b'diff --git '+b for b in blocks[1:]}

def current():
    prep = load(OUT/'prepare.json')
    reviewed = load(OUT/'reviewed-manifest.json')
    product = load(OUT/'product-manifest.json')
    assert len(reviewed)==prep['reviewed_files']==130
    assert len(product)==prep['product_files']==37
    assert sha(compact(reviewed))==prep['reviewed_manifest_sha256']=='856a6c8f94f63a47ec8fdf0192015d01ccc59d138c14bbcafd5cd58279d74534'
    assert sha(compact(product))==prep['product_manifest_sha256']=='72a773083cecfef06f9fdf43f423f38b8948c0108e2e3235bf078056b3651138'
    for p,h in reviewed.items(): assert sha((ROOT/p).read_bytes())==h, 'live drift '+p
    for p,h in product.items(): assert sha((ROOT/p).read_bytes())==h, 'product drift '+p
    before=(OUT/'candidate-before.json').read_bytes(); after=(OUT/'candidate-after.json').read_bytes()
    assert before==after==(ROOT/'qa/release-029/approved-release-delta.json').read_bytes()
    assert sha(before)==prep['candidate_before_sha256']==prep['candidate_after_sha256']
    candidate=json.loads(after)
    checks={}
    for kind in ('guarded_source_sha256','immutable_source_sha256','lineage_sha256'):
        for p,h in candidate[kind].items(): assert sha((ROOT/p).read_bytes())==h,kind+' '+p
        checks[kind]=len(candidate[kind])
    for p,rows in candidate['patches'].items():
        for row in rows:
            assert row['before'].encode()==git('show',row['before_commit']+':'+p)
            assert sha(row['before'].encode())==row['before_sha256']
            assert row['after'].encode()==(ROOT/p).read_bytes()
            assert sha(row['after'].encode())==row['after_sha256']
    rebuilt=git('diff','--no-ext-diff',candidate['head_pin'],'--',*sorted(reviewed))
    appended=[]
    for p in git('ls-files','--others','--exclude-standard').decode().splitlines():
        if p not in reviewed: continue
        child=subprocess.run(['git','diff','--no-ext-diff','--no-index','--','/dev/null',p],cwd=ROOT,stdout=subprocess.PIPE)
        assert child.returncode in (0,1)
        rebuilt+=child.stdout;appended.append(p)
    assert rebuilt==(OUT/'current.diff').read_bytes(), 'full diff bytes mismatch'
    assert sha(rebuilt)==prep['diff_sha256']=='0173d7ecf6e7bc92cfe2d359e0cb6f8630e5641cb68a9b6ea0079e06648ddd14'
    assert len(rebuilt)==prep['diff_bytes']==549989
    actual=git('rev-parse','HEAD').decode().strip()
    assert actual=='44df9d0fd36aecaa22613e9aa73c5c7d4ed94416'
    snapshots={p.name:{'bytes':len(p.read_bytes()),'sha256':sha(p.read_bytes())} for p in [OUT/x for x in ('prepare.json','candidate-before.json','candidate-after.json','reviewed-manifest.json','product-manifest.json','current.diff')]}
    return {'prepare':prep,'snapshot_files':snapshots,'candidate_checks':checks,'actual_head':actual,'head_pin':candidate['head_pin'],'live_reviewed_exact':130,'live_product_exact':37,'complete_diff_bytes_equal':True,'untracked_appended':appended}

if __name__=='__main__':
    report=current()
    r8=BASE/'final-review-r8'; closure=load(r8/'dual-closure.json'); pp=load(r8/'prepare.json'); pm=load(r8/'product-manifest.json'); rm=load(r8/'reviewed-manifest.json')
    assert pm==load(OUT/'product-manifest.json') and (r8/'product-manifest.json').read_bytes()==(OUT/'product-manifest.json').read_bytes()
    assert sha(compact(rm))==pp['reviewed_manifest_sha256'] and sha(compact(pm))==pp['product_manifest_sha256']
    assert sha((r8/'current.diff').read_bytes())==pp['diff_sha256']
    axes={}
    for row in closure['axes']:
        p=r8/(row['axis']+'-raw.txt'); raw=first_json(p)
        assert sha(p.read_bytes())==row['raw_sha256']
        assert raw['passed'] and not any(raw[k] for k in ('security_concerns','logic_errors','missing_requirements'))
        binding = raw.get('bindings', {})
        assert raw.get('reviewed_manifest_sha256', binding.get('reviewed_manifest_sha256'))==pp['reviewed_manifest_sha256']
        assert raw.get('diff_sha256', binding.get('diff_sha256'))==pp['diff_sha256']
        axes[row['axis']]={'sha256':sha(p.read_bytes()),'passed':raw['passed'],'summary':raw['summary'],'coverage':raw.get('coverage',{}),'source_manifest_sha256':raw.get('source_manifest_sha256')}
    for p,h in pm.items(): assert sha(git('show',report['actual_head']+':'+p))==h,'HEAD product '+p
    earlier=[]
    for n,commit in [(3,'b9ce4787b7f286cadfc6632d772a1bb5b57ce337'),(4,'b9ce4787b7f286cadfc6632d772a1bb5b57ce337'),(5,'9d3b87308c2428e8a89a0c1dd506052dc13da341'),(6,'17443ebd617272e41d87f28da57f662b12fd1561'),(7,'17443ebd617272e41d87f28da57f662b12fd1561')]:
        d=BASE/('final-review-r'+str(n)); prep=load(d/'prepare.json'); products=load(d/'product-manifest.json'); reviewed=load(d/'reviewed-manifest.json')
        assert sha(compact(products))==prep['product_manifest_sha256']
        assert sha(compact(reviewed))==prep['reviewed_manifest_sha256']
        assert sha((d/'current.diff').read_bytes())==prep['diff_sha256'] and len((d/'current.diff').read_bytes())==prep['diff_bytes']
        assert len(products)==37
        for p,h in products.items(): assert sha(git('show',commit+':'+p))==h, 'history product '+str(n)+' '+p
        item={'round':n,'product_git_commit':commit,'product_files':37,'all_product_git_blobs_match':True,'raws':{}}
        c=load(d/'dual-closure.json') if (d/'dual-closure.json').exists() else None
        for axis in ('spec','standards'):
            p=d/(axis+'-raw.txt'); raw=first_json(p); h=sha(p.read_bytes())
            assert raw['reviewed_manifest_sha256']==prep['reviewed_manifest_sha256'] and raw['diff_sha256']==prep['diff_sha256']
            if c:
                matching=[r for r in c['axes'] if r['axis']==axis]; assert len(matching)==1 and matching[0]['raw_sha256']==h
            item['raws'][axis]={'sha256':h,'passed':raw['passed'],'closure_hash_verified':c is not None}
        earlier.append(item)
    r10=BASE/'final-review-r10-fourth'; old=load(r10/'reviewed-manifest.json'); now=load(OUT/'reviewed-manifest.json')
    r8sections=sections((r8/'current.diff').read_bytes()); nowsections=sections((OUT/'current.diff').read_bytes())
    changed=[p for p in nowsections if r8sections.get(p)!=nowsections[p]]
    with (PROBES/'changed-since-r8.diff').open('xb') as f: f.write(b''.join(nowsections[p] for p in changed))
    oldtests=[p for p in old if (p.startswith('app/src/test/') or p.startswith('app/src/androidTest/') or p.startswith('qa/test_'))]
    assert all(now[p]==old[p] for p in oldtests)
    oldraws={}
    for axis in ('spec','standards'):
        p=r10/(axis+'-raw.txt'); v=first_json(p); assert v['passed'] is False
        oldraws[axis]={'sha256':sha(p.read_bytes()),'passed':False,'security_concerns':v['security_concerns'],'logic_errors':v['logic_errors']}
    bm=load(BASE/'resume-fourth/r11/before-manifest.json')
    for p,row in bm.items():
        data=(ROOT/row['original']).read_bytes();assert len(data)==row['bytes'] and sha(data)==row['sha256'];assert row['sha256']==old[p]
    gate=BASE/'resume-fourth/gates-r11'; complete=load(gate/'complete.json');inputs=load(gate/'inputs-before.json')
    print('GATE_INPUT_SHAPE',type(inputs).__name__,list(inputs)[:4])
    if 'files' in inputs: im=inputs['files']
    else: im=inputs
    for p,row in im.items():
        if isinstance(row,str): assert sha((ROOT/p).read_bytes())==row,'gate input '+p
        else: assert sha((ROOT/p).read_bytes())==row['sha256'],'gate input '+p
    gate_logs={}
    for key in ('host','python','http','runtime','termux'):
        execution=load(gate/(key+'.execution.json')); log=(gate/(key+'.raw.log')).read_bytes()
        assert execution.get('exit_code',execution.get('returncode'))==0,'gate exit '+key
        gate_logs[key]={'execution':execution,'log_sha256':sha(log),'log_bytes':len(log),'tail':log.decode(errors='replace')[-1600:]}
    report.update({'r8_original_axes':axes,'r8_closure_sha256':sha((r8/'dual-closure.json').read_bytes()),'r3_r7_chain':earlier,'all_37_product_full_manifest_bytes_equal_r8':True,'r8_unchanged_entries':sum(now.get(p)==h for p,h in rm.items()),'r8_changed_entries':[p for p,h in rm.items() if now.get(p)!=h],'r8_added_entries':sorted(set(now)-set(rm)),'r8_removed_entries':sorted(set(rm)-set(now)),'changed_cumulative_sections':changed,'changed_sections_file_sha256':sha((PROBES/'changed-since-r8.diff').read_bytes()),'r10_delta_changed':[p for p,h in old.items() if now.get(p)!=h],'r10_delta_added':sorted(set(now)-set(old)),'r10_old_test_files_exact':len(oldtests),'r10_original_false_raws':oldraws,'before_originals_verified':True,'gates_complete':complete,'gate_inputs_verified':len(im),'gate_logs':gate_logs})
    save('binding-initial.json',report)
    print(json.dumps({k:v for k,v in report.items() if k not in ('r8_original_axes','gate_logs','r10_original_false_raws')},ensure_ascii=False,indent=2))
    print('GATE_LOGS',json.dumps(gate_logs,ensure_ascii=False))
