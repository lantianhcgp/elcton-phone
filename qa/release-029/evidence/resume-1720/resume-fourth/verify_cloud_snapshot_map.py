#!/usr/bin/env python3
"""Original artifact gates on an exact logical snapshot map, not another 600MB copy.
Complete copied artifact files from the first stopped snapshot must independently hash
identically to all original fetched bytes. Metadata and ZIP bind their complete original
files. All bytes rechecked before/after; original acceptance code objects untouched.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import stat
import sys

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('original_exact_cloud_criteria', HERE / 'verifiers/verify_cloud.py')
assert spec and spec.loader
M = importlib.util.module_from_spec(spec)
spec.loader.exec_module(M)


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def inventory(directory):
    rows = {}
    for path in sorted(directory.rglob('*')):
        M.require(not path.is_symlink(), 'Symlink input refused')
        if path.is_file():
            M.require(stat.S_ISREG(path.stat().st_mode), 'Nonregular input')
            rows[path.relative_to(directory).as_posix()] = {'bytes':path.stat().st_size,'sha256':digest(path)}
    return rows


def mapped_inventory(mapping):
    rows = {}
    for name, path in mapping.items():
        path = Path(path)
        M.require(path.is_file() and not path.is_symlink() and stat.S_ISREG(path.stat().st_mode), 'Missing/nonregular mapped snapshot')
        rows[name] = {'bytes':path.stat().st_size,'sha256':digest(path)}
    return rows


class MappedGate(M.Gate):
    def snapshot(self):
        before = inventory(self.args.incoming)
        declared = M.read_json(self.args.incoming / 'inventory.json')
        M.require(declared['source_sha'] == self.args.source and str(declared['run']) == self.args.run, 'Fetch inventory identity')
        M.compare({k:v for k,v in before.items() if k != 'inventory.json'},declared['inventory'],'ALL original fetched files')
        snapshot = self.args.snapshot_artifact
        actual_snapshot = inventory(snapshot)
        wanted_snapshot = {k.removeprefix('artifact/'):v for k,v in before.items() if k.startswith('artifact/')}
        M.compare(actual_snapshot,wanted_snapshot,'ALL copied artifact snapshot files')
        mapping = {name:str(snapshot / name.removeprefix('artifact/')) if name.startswith('artifact/')
                   else str(self.args.incoming / name) for name in before}
        M.compare(mapped_inventory(mapping),before,'ALL logical snapshot rows exact')
        self.mapping = mapping; self.before = before
        self.art = snapshot
        self.write('input-inventory.json',before)
        self.write('snapshot-map.json',{'passed':True,'rows':mapping,
                   'scope':'Every exact fetched key bound to an actual SHA/size-matching file; complete old copied artifact tree + complete original metadata/ZIP, no omissions or partial original ZIP use'})
        return {'raw_files':len(mapping),'artifact_files':len(actual_snapshot),
                'snapshot_artifact':str(snapshot),'metadata':str(self.args.incoming),
                'scope':'Exact all-byte logical snapshot; no symlinks/hardlinks/copy omissions; original files never modified'}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source',required=True); parser.add_argument('--run',required=True)
    parser.add_argument('--suite',choices=('diagnostics','full'),required=True)
    parser.add_argument('--incoming',type=Path,required=True)
    parser.add_argument('--snapshot-artifact',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    args = parser.parse_args()
    for name in ('incoming','snapshot_artifact','out'):
        setattr(args,name,getattr(args,name).resolve())
    M.require(len(args.source)==40 and all(c in '0123456789abcdef' for c in args.source),'Invalid source')
    M.require(args.run.isdecimal() and not args.run.startswith('0'),'Invalid run')
    M.require(args.out.is_relative_to(M.ROOT/'qa/release-029/evidence'),'Output outside evidence')
    for other in (args.incoming,args.snapshot_artifact):
        M.require(not args.out.is_relative_to(other) and not other.is_relative_to(args.out),'Snapshot/output overlaps')
    args.out.mkdir(parents=True,exist_ok=False)
    gate = MappedGate(args)
    gate.write('execution.json',{'argv':sys.argv,'source':args.source,'run':args.run,'suite':args.suite,
                    'incoming':str(args.incoming),'snapshot_artifact':str(args.snapshot_artifact),
                    'original_tool_sha256':digest(HERE/'verifiers/verify_cloud.py'),
                    'snapshot_tool_sha256':digest(__file__),'scope':'HOST ONLY, exact byte sources; no ADB/CI/network/device'})
    methods = ('clients','diagnostics','background','full','tour','check','write')
    M.require(all(getattr(MappedGate,name).__code__ is getattr(M.Gate,name).__code__ for name in methods),'Original criteria code changed')
    gate.write('original-method-identity.json',{'passed':True,'identical_code_objects':list(methods),'original_full_json_compare_unchanged':True})
    gate.write('criteria-sha256.json',{name:digest(M.ROOT/'qa'/(name+'.py')) for name in M.CRITERIA})
    gate.check('input-snapshot-all-bytes',gate.snapshot)
    gate.check('exact-run-success',lambda:M.check_run(M.read_json(args.incoming/'run.json'),args.source,args.run))
    gate.check('local-client-raw-logs',gate.clients)
    gate.check(args.suite+'-complete',gate.diagnostics if args.suite=='diagnostics' else gate.full)
    def after():
        M.compare(mapped_inventory(gate.mapping),gate.before,'ALL logical snapshot bytes after')
        M.compare(inventory(args.incoming),gate.before,'ALL original incoming bytes after')
        return {'files':len(gate.before),'same_exact_bytes_before_and_after':True}
    gate.check('snapshot-inputs-unchanged-after-original-gates',after)
    receipt={'passed':not gate.errors,'source_sha':args.source,'run_id':args.run,'suite':args.suite,
             'checks':gate.checks,'errors':gate.errors,'details':gate.details,
             'scope':'All ORIGINAL criteria/full JSON on exact complete logical byte snapshot; old failed copy/link adapter raws remain false and immutable',
             'external_binding':'Parent verifies API/current attempt/build/suite/API/navigation/APK separately'}
    gate.write('receipt.json',receipt)
    print(json.dumps({k:v for k,v in receipt.items() if k!='details'},ensure_ascii=False),flush=True)
    return 0 if receipt['passed'] else 1


if __name__=='__main__':
    raise SystemExit(main())
