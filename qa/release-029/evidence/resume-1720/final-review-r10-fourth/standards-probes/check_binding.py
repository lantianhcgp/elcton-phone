import ast, hashlib, json, re, subprocess, sys, time
from pathlib import Path
R = Path('/data/data/com.termux/files/home/elcton-phone-release-029-20261114')
F = R/'qa/release-029/evidence/resume-1720/final-review-r10-fourth'
P = F/'standards-probes'
PIN = 'e034de2f924dd6d96e31caa8e5a62e52474de718'
def sha(b): return hashlib.sha256(b).hexdigest()
def canon(x): return sha(json.dumps(x, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode())
def git(*args):
 p=subprocess.run(['git', *args], cwd=R, capture_output=True)
 if p.returncode not in (0,1): raise RuntimeError(p.stderr.decode())
 return p
m=json.loads((F/'reviewed-manifest.json').read_bytes()); prod=json.loads((F/'product-manifest.json').read_bytes()); prep=json.loads((F/'prepare.json').read_bytes())
head=git('rev-parse','HEAD').stdout.decode().strip()
mis=[p for p,s in m.items() if not (R/p).is_file() or sha((R/p).read_bytes()) != s]
pmis=[p for p,s in prod.items() if sha((R/p).read_bytes()) != s]
tracked=set(git('ls-files','-z').stdout.decode().split('\0')); untracked=sorted(set(m)-tracked)
diff=git('diff','--no-ext-diff',PIN,'--',*sorted(m)).stdout
for p in untracked:
 result=git('diff','--no-ext-diff','--no-index','--','/dev/null',p)
 if result.returncode!=1: raise RuntimeError('Untracked diff error '+p)
 diff+=result.stdout
out={'head':head,'head_pin':PIN,'reviewed_files':len(m),'product_files':len(prod),'reviewed_manifest_sha256':canon(m),'product_sha256':canon(prod),'diff_sha256':sha(diff),'diff_bytes':len(diff),'complete_diff_equal':diff==(F/'current.diff').read_bytes(),'untracked_appended':untracked,'live_mismatches':mis,'product_mismatches':pmis,'prepare_raw_sha256':sha((F/'prepare.json').read_bytes()),'candidate_before_sha256':sha((F/'candidate-before.json').read_bytes()),'candidate_after_sha256':sha((F/'candidate-after.json').read_bytes()),'candidate_live_equal':(F/'candidate-before.json').read_bytes()==(F/'candidate-after.json').read_bytes()==(R/'qa/release-029/approved-release-delta.json').read_bytes()}
for name in ['reviewed_manifest_sha256','diff_sha256','diff_bytes','candidate_before_sha256','candidate_after_sha256']:
 if out[name]!=prep[name]: out.setdefault('prepare_mismatches',[]).append(name)
if out['product_sha256']!=prep['product_manifest_sha256']:out.setdefault('prepare_mismatches',[]).append('product_sha256')
old=R/'qa/release-029/evidence/resume-1720/final-review-r8'; m8=json.loads((old/'reviewed-manifest.json').read_bytes())
out['r8_changed']=[p for p in m8 if m.get(p)!=m8[p]];out['r8_added']=sorted(set(m)-set(m8));out['r8_removed']=sorted(set(m8)-set(m));out['r8_unchanged']=sum(m.get(p)==s for p,s in m8.items())
out['product_exact_r8']=prod==json.loads((old/'product-manifest.json').read_bytes())
out['all_r8_inputs_match_head']=all(sha(git('show',head+':'+p).stdout)==s for p,s in m8.items())
out['product_exact_head']=all(sha(git('show',head+':'+p).stdout)==s for p,s in prod.items())
out['app_test_resource_inputs_exact_head']=sum(p.startswith(('app/src/test/','app/src/androidTest/')) and sha(git('show',head+':'+p).stdout)==s for p,s in m.items())
def sections(b):
 chunks=re.split(rb'(?m)(?=^diff --git )',b)
 return {c.splitlines()[0].decode():c for c in chunks if c}
s8=sections((old/'current.diff').read_bytes()); sc=sections(diff)
out['cumulative_sections']={'r8':len(s8),'current':len(sc),'unchanged':sum(sc.get(k)==v for k,v in s8.items()),'changed':[k for k,v in s8.items() if sc.get(k)!=v],'added':sorted(set(sc)-set(s8))}
# Every changed section is retained whole for exact semantic delta review.
delta=b''.join(v for k,v in sc.items() if s8.get(k)!=v)
name=sys.argv[1] if len(sys.argv)>1 else 'initial'
with (P/(name+'-binding.json')).open('x') as f: json.dump(out,f,ensure_ascii=False,indent=2);f.write('\n')
with (P/(name+'-changed-sections.diff')).open('xb') as f:f.write(delta)
print(json.dumps(out,ensure_ascii=False))
if mis or pmis or out.get('prepare_mismatches') or not out['complete_diff_equal'] or not out['candidate_live_equal'] or head!='44df9d0fd36aecaa22613e9aa73c5c7d4ed94416':sys.exit(1)
