#!/usr/bin/env python3
"""Bind actual independent SPEC then QUALITY raw replies to immutable inputs.
Only executed after both genuine review JSONs are present; not a review itself.
"""
from pathlib import Path
import json, hashlib, shutil, time
ROOT=Path(__file__).resolve().parents[2]
Q=Path(__file__).resolve().parent/'r6/reviews'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    import argparse
    parser=argparse.ArgumentParser()
    parser.add_argument('--manifest',type=Path,default=Q/'input-r2/reviewed-manifest.json')
    parser.add_argument('--spec',default='r6-spec-r2.json')
    parser.add_argument('--spec-raw',default='spec-r2-raw.txt')
    parser.add_argument('--quality',default='r6-quality-r1.json')
    parser.add_argument('--quality-raw',default='quality-raw.txt')
    args=parser.parse_args()
    manifest=args.manifest.absolute()
    assert '..' not in args.manifest.parts and not any(p.is_symlink() for p in (manifest,*manifest.parents))
    manifest=manifest.resolve()
    assert manifest.is_relative_to(Q.resolve()) and manifest.is_file()
    m=json.loads(manifest.read_bytes())
    assert len(m)>=32 and set(json.loads((Q/'input-r2/reviewed-manifest.json').read_bytes()))<=set(m)
    assert all(sha(ROOT/p)==h for p,h in m.items()), 'Actual reviewed input changed'
    axes=[]
    for axis,name,rawname in [('spec',args.spec,args.spec_raw),('quality',args.quality,args.quality_raw)]:
        assert '/' not in name and '/' not in rawname
        data=json.loads((Q/name).read_bytes())
        assert data['input_manifest_sha256']==sha(manifest), axis+' actual reviewed identity differs'
        assert data['passed'] is True, axis+' failed actual review'
        assert not any(data.get(k,[]) for k in ['security_concerns','logic_errors','missing','critical','important']), axis+' inconsistent open blockers'
        assert (Q/rawname).is_file() and (Q/rawname).stat().st_size>0, 'Missing actual raw '+axis
        assert data['raw_reply_sha256']==sha(Q/rawname), axis+' raw is not the actual reviewed reply'
        assert data['axis']==axis and data['input_files']==len(m), axis+' input count/axis mismatch'
        assert data['reviewed_inputs']==m, axis+' manifest mapping differs'
        axes.append({'axis':axis,'json_path':name,'json_sha256':sha(Q/name),'raw_path':rawname,'raw_sha256':sha(Q/rawname)})
    target=Q/'closure'
    target.mkdir(parents=True,exist_ok=False)
    for axis in axes:
        shutil.copyfile(Q/axis['raw_path'],target/(axis['axis']+'-raw.txt'))
    shutil.copyfile(manifest,target/'reviewed-manifest.json')
    closure={'passed':True,'axes':axes,'manifest_sha256':sha(manifest),'input_files':len(m),'at':time.strftime('%Y-%m-%d %H:%M:%S %z'),'scope':'Actual independent source-review closure ONLY; APK/run not yet verified'}
    (target/'dual-closure.json').write_text(json.dumps(closure,indent=2)+'\n')
    print(json.dumps({'passed':True,'closure':str(target),'inputs':len(m)}))

if __name__=='__main__':main()
