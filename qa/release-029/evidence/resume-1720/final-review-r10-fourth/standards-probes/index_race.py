import hashlib,importlib.util,json,tempfile
from pathlib import Path
from unittest.mock import patch
R=Path('/data/data/com.termux/files/home/elcton-phone-release-029-20261114');P=R/'qa/release-029/evidence/resume-1720/final-review-r10-fourth/standards-probes';T=P/'index-race-scratch';T.mkdir(exist_ok=False)
s=importlib.util.spec_from_file_location('o',R/'qa/cloud_emulator_observer.py');assert s and s.loader;o=importlib.util.module_from_spec(s);s.loader.exec_module(o)
with tempfile.TemporaryDirectory(dir=T) as td:
 base=Path(td);source=base/'source';source.mkdir();(source/'safe.dmp').write_bytes(b'synthetic emulator fixture');output=base/'output';output.mkdir();outside=base/'outside';outside.mkdir();saved=base/'pinned-original-output';oldpath=o.Path;oldopen=Path.open;swapped=[]
 def redirect(v):return source if str(v)=='/tmp/android-runner' else oldpath(v)
 def race(path,*args,**kwargs):
  if path==output/'crashdata-index.json' and not swapped:
   output.rename(saved);output.symlink_to(outside);swapped.append(True)
  return oldopen(path,*args,**kwargs)
 with patch.object(o,'Path',redirect),patch.object(Path,'open',race):o.capture_crashdata(output)
 index=outside/'crashdata-index.json';raw=index.read_bytes()
 result={'scope':'exact output root replacement at index-open boundary via in-memory Path.open wrapper; implementation unchanged; synthetic local dirs only','pinned_copy_retained_under_original':(saved/'emulator-crashdata/safe.dmp').is_file(),'new_output_root_is_symlink':output.is_symlink(),'index_created_outside_pinned_output':index.is_file(),'index_bytes':len(raw),'index_sha256':hashlib.sha256(raw).hexdigest(),'index_records':len(json.loads(raw)),'actual_adb_or_kernel_calls':0}
with (P/'index-race.json').open('x') as f:json.dump(result,f,indent=2);f.write('\n')
print(json.dumps(result))
