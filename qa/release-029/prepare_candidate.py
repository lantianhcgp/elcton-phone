#!/usr/bin/env python3
"""Refresh an exact CANDIDATE snapshot, never manufacture review approval.
Historical candidate/raw verdicts are kept before regeneration. Immutable source
and pinned before-texts must validate, not just be rehashed into correctness.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]

def sha(raw): return hashlib.sha256(raw).hexdigest()
def raw(path): return (ROOT / path).read_bytes()
def compact(obj): return json.dumps(obj, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()
def save_new(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as out: out.write(data)
def pinned(commit, path): return subprocess.check_output(['git', 'show', commit + ':' + path], cwd=ROOT)

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--out',required=True);args=parser.parse_args()
    out=ROOT/args.out;out.mkdir(parents=True,exist_ok=False)
    candidate=ROOT/'qa/release-029/approved-release-delta.json'
    previous=candidate.read_bytes();data=json.loads(previous)
    assert data['status']=='candidate_pending_independent_review' and data['independent_approvals']==[]
    save_new(out/'candidate-before.json',previous)
    for path,expected in data['immutable_source_sha256'].items():
        assert sha(raw(path))==expected and sha(pinned(data['head_pin'],path))==expected, 'immutable drift '+path
    for path,changes in data['patches'].items():
        assert len(changes)==1
        change=changes[0]
        assert change['before'].encode()==pinned(change['before_commit'],path), 'bad before '+path
        assert sha(change['before'].encode())==change['before_sha256']
        change['after']=raw(path).decode('utf-8');change['after_sha256']=sha(raw(path))
    # New scheduling helper is not an approved exception. It is part of the exact
    # current candidate and must receive the same independent full review.
    data['guarded_source_sha256']['app/src/main/java/com/hcbiu/elcton/MainThreadActions.kt']='pending'
    data['guarded_source_sha256']={path:sha(raw(path)) for path in data['guarded_source_sha256']}
    data['lineage_sha256']={path:sha(raw(path)) for path in data['lineage_sha256']}
    after=(json.dumps(data,ensure_ascii=False,indent=2)+'\n').encode()
    save_new(out/'candidate-after.json',after)
    # Exact additive candidate change; historical copy above remains immutable.
    candidate.write_bytes(after)
    product={p.relative_to(ROOT).as_posix():sha(p.read_bytes()) for p in (ROOT/'app/src/main').rglob('*') if p.is_file()}
    product['app/build.gradle.kts']=sha(raw('app/build.gradle.kts'))
    reviewed=dict(product)
    for base in ('app/src/test','app/src/androidTest','qa'):
        for p in (ROOT/base).rglob('*'):
            name=p.relative_to(ROOT).as_posix()
            if not p.is_file() or '__pycache__' in p.parts: continue
            if base=='qa' and (not (p.suffix in ('.py','.kt') or p.name.endswith('.kt.in')) or '/evidence/' in name): continue
            reviewed[name]=sha(p.read_bytes())
    for path in ('.github/workflows/build.yml','.github/workflows/ui-smoke.yml','.gitattributes','.gitignore','build.gradle.kts','settings.gradle.kts','gradle.properties','qa/release-029/approved-release-delta.json','qa/release-029/SPEC.md','qa/release-029/TEST-ATTRIBUTION.md','qa/release-029/ANDROID-HARNESS-ATTRIBUTION.md','qa/release-029/RESUME-CHANGES.md'):
        reviewed[path]=sha(raw(path))
    save_new(out/'product-manifest.json',(json.dumps(product,ensure_ascii=False,indent=2,sort_keys=True)+'\n').encode())
    save_new(out/'reviewed-manifest.json',(json.dumps(reviewed,ensure_ascii=False,indent=2,sort_keys=True)+'\n').encode())
    # Capture new files too; git diff HEAD alone would omit untracked implementations.
    difference=subprocess.check_output(['git','diff',data['head_pin'],'--',*sorted(reviewed)],cwd=ROOT)
    untracked=subprocess.check_output(['git','ls-files','--others','--exclude-standard'],cwd=ROOT,text=True).splitlines()
    for path in untracked:
        if path not in reviewed: continue
        result=subprocess.run(['git','diff','--no-index','--','/dev/null',path],cwd=ROOT,stdout=subprocess.PIPE,check=False)
        assert result.returncode in (0,1)
        difference+=result.stdout
    save_new(out/'current.diff',difference)
    receipt={'candidate_before_sha256':sha(previous),'candidate_after_sha256':sha(after),
             'product_files':len(product),'product_manifest_sha256':sha(compact(product)),
             'reviewed_files':len(reviewed),'reviewed_manifest_sha256':sha(compact(reviewed)),
             'diff_sha256':sha(difference),'diff_bytes':len(difference),
             'scope':'exact candidate identity only; independent approval pending'}
    save_new(out/'prepare.json',(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n').encode())
    print(json.dumps(receipt,ensure_ascii=False))

if __name__=='__main__':main()
