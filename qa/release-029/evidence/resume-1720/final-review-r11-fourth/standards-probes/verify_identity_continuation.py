import ast, hashlib, json, os, re, subprocess, sys
from pathlib import Path
ROOT = Path('/data/data/com.termux/files/home/elcton-phone-release-029-20261114')
BASE = ROOT / 'qa/release-029/evidence/resume-1720'
OUT = BASE / 'final-review-r11-fourth/standards-probes'
R = OUT.parent
sha = lambda b: hashlib.sha256(b).hexdigest()
compact = lambda x: json.dumps(x,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
def raw(p): return (ROOT / p).read_bytes()
def load(p): return json.loads(p.read_bytes())
def git(*args): return subprocess.check_output(['git', *args], cwd=ROOT)
def decode_receipt(p): return json.JSONDecoder().raw_decode(p.read_text().lstrip())[0]
def sections(b):
    chunks = re.split(rb'(?=^diff --git )', b, flags=re.M)
    return {c.split(b'\n',1)[0].decode():c for c in chunks if c}
def fresh_diff(manifest, pin):
    b=git('diff',pin,'--',*sorted(manifest))
    untracked=git('ls-files','--others','--exclude-standard').decode().splitlines()
    added=[]
    for p in untracked:
        if p in manifest:
            x=subprocess.run(['git','diff','--no-index','--','/dev/null',p],cwd=ROOT,capture_output=True)
            assert x.returncode in (0,1),p
            b+=x.stdout;added.append(p)
    return b,added
prep=load(R/'prepare.json'); reviewed=load(R/'reviewed-manifest.json'); product=load(R/'product-manifest.json')
assert git('rev-parse','HEAD').decode().strip()=='44df9d0fd36aecaa22613e9aa73c5c7d4ed94416'
assert len(reviewed)==130 and len(product)==37
assert sha(compact(reviewed))==prep['reviewed_manifest_sha256']
assert sha(compact(product))==prep['product_manifest_sha256']
assert all(sha(raw(p))==s for p,s in reviewed.items())
assert all(sha(raw(p))==s for p,s in product.items())
assert (R/'candidate-before.json').read_bytes()==(R/'candidate-after.json').read_bytes()==raw('qa/release-029/approved-release-delta.json')
assert sha((R/'candidate-before.json').read_bytes())==prep['candidate_before_sha256']
assert sha((R/'candidate-after.json').read_bytes())==prep['candidate_after_sha256']
candidate=load(R/'candidate-after.json')
assert candidate['status']=='candidate_pending_independent_review' and candidate['independent_approvals']==[]
for key in ('immutable_source_sha256','guarded_source_sha256','lineage_sha256'):
    assert all(sha(raw(p))==s for p,s in candidate[key].items()),key
for p,s in candidate['immutable_source_sha256'].items():
    assert sha(git('show',candidate['head_pin']+':'+p))==s
for p,changes in candidate['patches'].items():
    assert len(changes)==1
    x=changes[0];assert x['before'].encode()==git('show',x['before_commit']+':'+p)
    assert sha(x['before'].encode())==x['before_sha256']
    assert x['after'].encode()==raw(p) and sha(raw(p))==x['after_sha256']
generated={}
for base in ('app/src/main','app/src/test','app/src/androidTest','qa'):
    for p in (ROOT/base).rglob('*'):
        n=p.relative_to(ROOT).as_posix()
        if not p.is_file() or '__pycache__' in p.parts: continue
        if base=='qa' and (not (p.suffix in ('.py','.kt') or p.name.endswith('.kt.in')) or '/evidence/' in n): continue
        generated[n]=sha(p.read_bytes())
for p in ('app/build.gradle.kts','.github/workflows/build.yml','.github/workflows/ui-smoke.yml','.gitattributes','.gitignore','build.gradle.kts','settings.gradle.kts','gradle.properties','qa/release-029/approved-release-delta.json','qa/release-029/SPEC.md','qa/release-029/TEST-ATTRIBUTION.md','qa/release-029/ANDROID-HARNESS-ATTRIBUTION.md','qa/release-029/RESUME-CHANGES.md'):
    generated[p]=sha(raw(p))
assert generated==reviewed
b,untracked=fresh_diff(reviewed,candidate['head_pin'])
assert b==(R/'current.diff').read_bytes() and len(b)==prep['diff_bytes'] and sha(b)==prep['diff_sha256']
r8=BASE/'final-review-r8';old=load(r8/'reviewed-manifest.json');prod8=load(r8/'product-manifest.json');p8=load(r8/'prepare.json');cl8=load(r8/'dual-closure.json')
assert prod8==product and (r8/'product-manifest.json').read_bytes()==(R/'product-manifest.json').read_bytes()
assert sha(compact(old))==p8['reviewed_manifest_sha256'] and sha(compact(prod8))==p8['product_manifest_sha256']
for p,s in old.items(): assert sha(git('show','44df9d0fd36aecaa22613e9aa73c5c7d4ed94416:'+p))==s,p
for p,s in product.items(): assert sha(git('show','HEAD:'+p))==s,p
b8=git('diff',candidate['head_pin'],'44df9d0fd36aecaa22613e9aa73c5c7d4ed94416','--',*sorted(old))
assert b8==(r8/'current.diff').read_bytes() and sha(b8)==p8['diff_sha256']
r8raws={}
for axis in ('standards','spec'):
    p=r8/(axis+'-raw.txt');v=decode_receipt(p)
    assert v['axis']==axis and v['passed'] is True and not any(v[x] for x in ('security_concerns','logic_errors','missing_requirements'))
    assert v['bindings'].get('reviewed_manifest_sha256',v.get('reviewed_manifest_sha256'))==p8['reviewed_manifest_sha256']
    r8raws[axis]=sha(p.read_bytes())
assert all(s in json.dumps(cl8) for s in r8raws.values())
chain=[]
prior=decode_receipt(r8/'standards-raw.txt')['prior_coverage']
for rnd in range(4,8):
    d=BASE/('final-review-r'+str(rnd));pr=load(d/'prepare.json');rm=load(d/'reviewed-manifest.json');pm=load(d/'product-manifest.json');closure=load(d/'dual-closure.json')
    assert sha(compact(rm))==pr['reviewed_manifest_sha256']
    assert sha(compact(pm))==pr['product_manifest_sha256']
    diff=(d/'current.diff').read_bytes();assert len(diff)==pr['diff_bytes'] and sha(diff)==pr['diff_sha256']
    rr={}
    for axis in ('standards','spec'):
        p=d/(axis+'-raw.txt');v=decode_receipt(p);s=sha(p.read_bytes());rr[axis]=s
        assert s==prior['r'+str(rnd)+'_'+axis+'_raw_sha256'] and s in json.dumps(closure)
        assert v['passed'] is True and not any(v[x] for x in ('security_concerns','logic_errors','missing_requirements'))
    chain.append({'round':rnd,'raw_sha256':rr,'closure_sha256':sha((d/'dual-closure.json').read_bytes()),'canonical_manifest_verified':True,'full_diff_hash_verified':True})
s8=sections(b8);s11=sections(b)
changed=[k for k in s8 if k in s11 and s8[k]!=s11[k]];added=[k for k in s11 if k not in s8];removed=[k for k in s8 if k not in s11]
old10=load(BASE/'final-review-r10-fourth/reviewed-manifest.json')
report={'bindings':prep,'head':'44df9d0fd36aecaa22613e9aa73c5c7d4ed94416','head_pin':candidate['head_pin'],'prepare_raw_sha256':sha((R/'prepare.json').read_bytes()),'manifest_raw_sha256':{n:sha((R/n).read_bytes()) for n in ('reviewed-manifest.json','product-manifest.json')},'scope_regenerated_exact':True,'live_mismatches':[],'complete_diff_equal':True,'untracked_appended':untracked,'r8_all125_equal_pinned_commit':True,'product_exact_r8_and_HEAD':True,'r8_raw_sha256':r8raws,'r8_closure_sha256':sha((r8/'dual-closure.json').read_bytes()),'prior_chain':chain,'r8_changed':[p for p in old if p in reviewed and old[p]!=reviewed[p]],'r8_added':[p for p in reviewed if p not in old],'r8_removed':[p for p in old if p not in reviewed],'r8_unchanged':sum(old[p]==reviewed.get(p) for p in old),'r10_changed':[p for p in old10 if p in reviewed and old10[p]!=reviewed[p]],'r10_added':[p for p in reviewed if p not in old10],'cumulative_diff':{'r8_sections':len(s8),'current_sections':len(s11),'unchanged_sections':sum(s8.get(k)==v for k,v in s11.items()),'changed':changed,'added':added,'removed':removed}}
with (OUT/'identity.json').open('x') as f:json.dump(report,f,ensure_ascii=False,indent=2);f.write('\n')
with (OUT/'r8-current-semantic.diff').open('xb') as f:f.write(b''.join(s11[k] for k in changed+added))
# Actual HEAD delta is the present QA observer correction; inherited product does not need a new line audit.
head_diff,_=fresh_diff(reviewed,'HEAD')
with (OUT/'head-current.diff').open('xb') as f:f.write(head_diff)
print(json.dumps(report,ensure_ascii=False))
print('HEAD_DELTA_BEGIN\n'+head_diff.decode()+'HEAD_DELTA_END')
