#!/usr/bin/env python3
"""Refresh immutable post-Q1 independent review inputs, preserving all old inputs.
No approval itself. Explicit current field map and exact permitted runtime delta.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
QA = Path(__file__).resolve().parent
Q = QA/'r6'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--runtime-final',type=Path,required=True)
    parser.add_argument('--regression-final',type=Path,required=True)
    args=parser.parse_args()
    args.runtime_final=args.runtime_final.absolute()
    args.regression_final=args.regression_final.absolute()
    assert args.runtime_final.is_relative_to(ROOT) and args.regression_final.is_relative_to(ROOT)
    assert args.runtime_final.is_file() and args.regression_final.is_file()
    assert json.loads(args.regression_final.read_bytes())['passed'] is True
    prior_path=Q/'reviews/input-r2/reviewed-manifest.json'
    prior=json.loads(prior_path.read_bytes())
    changed=[p for p,h in prior.items() if sha(ROOT/p)!=h]
    allowed=['app/src/main/java/com/hcbiu/elcton/DiagnosticRuntime.kt','qa/p2p-trace-0210/r6/current-identity.json','qa/p2p-trace-0210/check_r6_scope.py']
    assert set(changed)==set(allowed), 'Unexpected prior input change: '+str(changed)
    dest=Q/'reviews/input-q1'
    dest.mkdir(parents=True,exist_ok=True)
    assert not (dest/'reviewed-manifest.json').exists(), 'Completed review input never overwritten'
    rows={p:sha(ROOT/p) for p in prior}
    for folder in [Q/'runtime-wakeup-host']:
        assert folder.is_dir()
        for p in sorted(folder.iterdir()):
            if p.is_file() and p.name.endswith(('.kt.in','.java.in','.py','.md')):
                rows[str(p.relative_to(ROOT))]=sha(p)
    extras=[QA/'run_r6_final_regressions.py',QA/'migrate_r6_quality_identity.py',Q/'QUALITY-R1-REPAIR-SCOPE.md',
            Q/'evidence/identity-migration-q1/table.json',args.runtime_final,args.regression_final]
    for p in extras:rows[str(p.relative_to(ROOT))]=sha(p)
    (dest/'reviewed-manifest.json').write_text(json.dumps(rows,indent=2)+'\n')
    old=(ROOT/'app/src/main/java/com/hcbiu/elcton/DiagnosticRuntime.kt').read_bytes()
    original=(Q/'evidence/identity-migration/DiagnosticRuntime.kt.current.source.txt').read_bytes()
    # Historical baseline is retained; current migration snapshot may be updated.
    import difflib
    delta=''.join(difflib.unified_diff(original.decode().splitlines(True),old.decode().splitlines(True),fromfile='Runtime-before-Q1',tofile='Runtime-current'))
    (dest/'runtime-q1.diff').write_text(delta)
    (dest/'whole-current.diff').write_bytes(subprocess.check_output(['git','diff','HEAD','--binary','--',*list(prior)],cwd=ROOT))
    (dest/'receipt.json').write_text(json.dumps({'previous_manifest_sha256':sha(prior_path), 'manifest_sha256':sha(dest/'reviewed-manifest.json'),
        'changed_prior_paths':changed,'input_files':len(rows),'q1_report_sha256':sha(args.runtime_final),
        'final_regression_sha256':sha(args.regression_final),'scope':'Current identity/readback only; not independent approval'},indent=2)+'\n')
    print(json.dumps({'inputs':len(rows),'manifest':str(dest/'reviewed-manifest.json'),'actual_prior_changed':changed}))

if __name__=='__main__':main()
