#!/usr/bin/env python3
"""Identity-only follow-up to the ten-space CI compile compatibility correction."""
import copy
import hashlib
import json
from pathlib import Path
import re
import subprocess

ROOT=Path(__file__).resolve().parents[2]
Q=Path(__file__).resolve().parent/'r6'
BEFORE='a0881bf7c1d97724ea166f0e51988902c280a5cc'
FILES={'P2pTrace':7,'SyncEngine':3}
sha=lambda b:hashlib.sha256(b).hexdigest()


def main():
    evidence=Q/'evidence/r7-ci-identity'
    assert not evidence.exists()
    current=Q/'current-identity.json'
    previous=current.read_bytes()
    assert previous==subprocess.check_output(['git','show',BEFORE+':'+str(current.relative_to(ROOT))],cwd=ROOT)
    old=json.loads(previous)
    mutation=[]
    for name,count in FILES.items():
        path='app/src/main/java/com/hcbiu/elcton/'+name+'.kt'
        before=subprocess.check_output(['git','show',BEFORE+':'+path],cwd=ROOT)
        after=(ROOT/path).read_bytes()
        # Only the exact ten offending string-else joins; string/other bytes unchanged.
        assert before.count(b'"else')==count
        expected=before.replace(b'"else',b'" else')
        assert expected==after and sha(before)==old['source_identities'][path]['current_sha256']
        mutation.append({'path':path,'added_spaces':count,'before_sha256':sha(before),'after_sha256':sha(after),'before_bytes':len(before),'after_bytes':len(after)})
    for path,row in old['source_identities'].items():
        if Path(path).stem not in FILES:
            assert sha((ROOT/path).read_bytes())==row['current_sha256']
    assert sha((ROOT/old['old_manifest']).read_bytes())==old['old_manifest_sha256']
    assert sha((ROOT/old['version_identity']['path']).read_bytes())==old['version_identity']['current_sha256']
    new=copy.deepcopy(old)
    for row in mutation:
        target=new['source_identities'][row['path']]
        target['previous_q2_sha256']=row['before_sha256']
        target['current_sha256']=row['after_sha256']
        target['current_bytes']=row['after_bytes']
    new['ci_whitespace_identity']={'source_before':BEFORE,'failed_run':43710014774,'attempt':1,
        'compiler':'1.9.24','changes':mutation,'authorization':'R7 pure-diagnostic CI completion, ten ASCII separating spaces only; behavior and original assertions unchanged'}
    raw=(json.dumps(new,ensure_ascii=False,indent=2)+'\n').encode()
    evidence.mkdir(parents=True,exist_ok=False)
    (evidence/'previous-current-identity.json.source.txt').write_bytes(previous)
    previous_table=Q/'evidence/identity-migration-q1/table.json'
    (evidence/'previous-table.json.source.txt').write_bytes(previous_table.read_bytes())
    table={'source_identities':new['source_identities'],'version_identity':new['version_identity'],
           'old_manifest_sha256':new['old_manifest_sha256'],'previous_q2_manifest_sha256':sha(previous),
           'new_manifest_sha256':sha(raw),'ci_whitespace_identity':new['ci_whitespace_identity']}
    for name in ('WearProbe','SyncEngine','DiagnosticRuntime','P2pTrace'):
        (evidence/(name+'.current.source.txt')).write_bytes((ROOT/('app/src/main/java/com/hcbiu/elcton/'+name+'.kt')).read_bytes())
    (evidence/'table.json').write_text(json.dumps(table,ensure_ascii=False,indent=2)+'\n')
    current.write_bytes(raw)
    assert current.read_bytes()==raw
    receipt={'registered':True,'spaces':10,'product_changes':mutation,'previous_manifest_sha256':sha(previous),
        'new_manifest_sha256':sha(raw),'current_table_sha256':sha((evidence/'table.json').read_bytes()),
        'old_q1_table_unchanged':(evidence/'previous-table.json.source.txt').read_bytes()==previous_table.read_bytes(),
        'other_two_product_sources_unchanged':True,'version_unchanged':True,'old_behavior_assertions_unchanged':True,
        'scope':'Current identity registration only, old evidence preserved; independent approval pending'}
    (evidence/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps(receipt))

if __name__=='__main__':
    main()
