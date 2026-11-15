#!/usr/bin/env python3
"""Register final exact lexical whitespace identities; historical identities immutable."""
import copy
import hashlib
import json
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[2]
Q=Path(__file__).resolve().parent/'r6'
BEFORE='a0881bf7c1d97724ea166f0e51988902c280a5cc'
FILES={'P2pTrace':14,'SyncEngine':5}
TEST='app/src/test/java/com/hcbiu/elcton/P2pTraceEngineTest.kt'
sha=lambda b:hashlib.sha256(b).hexdigest()

def git_bytes(path):
    return subprocess.check_output(['git','show',BEFORE+':'+path],cwd=ROOT)

def main():
    evidence=Q/'evidence/r7-ci-identity-final'
    assert not evidence.exists()
    current=Q/'current-identity.json'
    previous=current.read_bytes()
    old=json.loads(previous)
    saved=(Q/'evidence/r7-ci-identity/table.json').read_bytes()
    assert json.loads(saved)['source_identities']==old['source_identities']
    q2=json.loads((Q/'evidence/r7-ci-identity/previous-current-identity.json.source.txt').read_bytes())
    mutation=[]
    for name,count in FILES.items():
        path='app/src/main/java/com/hcbiu/elcton/'+name+'.kt'
        before=git_bytes(path);after=(ROOT/path).read_bytes()
        expected=before.replace(b'"else',b'" else').replace(b'else"',b'else "')
        assert expected==after and len(after)-len(before)==count
        assert sha(before)==q2['source_identities'][path]['current_sha256']
        mutation.append({'path':path,'total_ascii_spaces':count,'q2_sha256':sha(before),
            'first_candidate_sha256':old['source_identities'][path]['current_sha256'],
            'final_sha256':sha(after),'bytes':len(after),'exact_inverse_to_Q2':True})
    test_before=git_bytes(TEST);test_after=(ROOT/TEST).read_bytes()
    assert test_before.replace(b'"else',b'" else').replace(b'else"',b'else "')==test_after
    assert len(test_after)-len(test_before)==2
    original_tests=json.loads((Path(__file__).resolve().parent/'baseline.json').read_bytes())['old_tests']
    assert TEST not in original_tests, 'Cannot mutate original frozen test'
    for path,row in old['source_identities'].items():
        if Path(path).stem not in FILES:assert sha((ROOT/path).read_bytes())==row['current_sha256']
    assert sha((ROOT/old['old_manifest']).read_bytes())==old['old_manifest_sha256']
    assert sha((ROOT/old['version_identity']['path']).read_bytes())==old['version_identity']['current_sha256']
    new=copy.deepcopy(old)
    for row in mutation:
        target=new['source_identities'][row['path']]
        target['previous_first_whitespace_sha256']=target['current_sha256']
        target['current_sha256']=row['final_sha256'];target['current_bytes']=row['bytes']
    new['ci_whitespace_identity_final']={'source_before':BEFORE,'failed_run':43710014774,'attempt':1,
        'compiler':'1.9.24','changes':mutation,'total_spaces':21,
        'test_lexical_identity':{'path':TEST,'old_sha256':sha(test_before),'new_sha256':sha(test_after),'spaces':2,'new_diagnostic_test_only':True,'all_assertion_tokens_unchanged':True},
        'authorization':'R7 diagnostic completion, whitespace token separation only; no behavior or original test assertion changes'}
    raw=(json.dumps(new,ensure_ascii=False,indent=2)+'\n').encode()
    evidence.mkdir(parents=True,exist_ok=False)
    (evidence/'previous-first-current-identity.json.source.txt').write_bytes(previous)
    (evidence/'previous-first-table.json.source.txt').write_bytes(saved)
    (evidence/'q2-current-identity.json.source.txt').write_bytes((Q/'evidence/r7-ci-identity/previous-current-identity.json.source.txt').read_bytes())
    table={'source_identities':new['source_identities'],'version_identity':new['version_identity'],'old_manifest_sha256':new['old_manifest_sha256'],
        'previous_first_manifest_sha256':sha(previous),'new_manifest_sha256':sha(raw),'ci_whitespace_identity_final':new['ci_whitespace_identity_final']}
    for name in ('WearProbe','SyncEngine','DiagnosticRuntime','P2pTrace'):
        (evidence/(name+'.final.source.txt')).write_bytes((ROOT/('app/src/main/java/com/hcbiu/elcton/'+name+'.kt')).read_bytes())
    (evidence/'test-before.source.txt').write_bytes(test_before)
    (evidence/'test-final.source.txt').write_bytes(test_after)
    (evidence/'table.json').write_text(json.dumps(table,ensure_ascii=False,indent=2)+'\n')
    current.write_bytes(raw)
    assert current.read_bytes()==raw
    receipt={'registered':True,'total_spaces':21,'rows':mutation,'test_spaces':2,
        'previous_first_manifest_sha256':sha(previous),'new_manifest_sha256':sha(raw),
        'old_first_table_unchanged':(Q/'evidence/r7-ci-identity/table.json').read_bytes()==saved,
        'table_sha256':sha((evidence/'table.json').read_bytes()),'old_test_assertions_changed':False,'version_unchanged':True,
        'scope':'Final identity-only registration, all prior attempts retained; independent source review pending'}
    (evidence/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps(receipt))

if __name__=='__main__':main()
