#!/usr/bin/env python3
"""Receipt closure from real successful fresh cloud runs; never overwrite first failed pipeline."""
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[5]
base = ROOT / 'qa/release-029/evidence/resume-1720/resume-fourth/r11/exact-cloud-pipeline'
source = '84a6c406099348f75b436a8e9467c34487766859'
reg = json.loads((base / 'cloud-registered.json').read_bytes())
assert reg['source_sha'] == source and reg['build_run'] == '43600711386'
build = json.loads((base / 'build-verification/receipt.json').read_bytes())
assert build['passed'] is True and build['source_sha'] == source and build['gradle']['tests'] == 153
rows = []
for suite, filename, execution_name in (('diagnostics', 'diagnostics-verification/receipt.json', 'diagnostics-verify.execution.json'),
                                        ('full', 'full-verification-snapshot-map/receipt.json', 'full-map.execution.json')):
    path = base / filename
    receipt = json.loads(path.read_bytes())
    execution = json.loads((base / execution_name).read_bytes())
    wait = json.loads((base / (suite + '-wait/completed.json')).read_bytes())
    assert receipt['passed'] is True and not receipt['errors'] and all(c['passed'] for c in receipt['checks'])
    assert receipt['source_sha'] == source and str(receipt['run_id']) == reg['runs'][suite]
    assert execution['exit_code'] == 0 and wait['conclusion'] == 'success' and wait['headSha'] == source
    run = json.loads(subprocess.check_output(['gh', 'api', 'repos/lantianhcgp/elcton-phone/actions/runs/' + reg['runs'][suite]]))
    assert run['head_sha'] == source and run['conclusion'] == 'success' and run['status'] == 'completed' and run['run_attempt'] == 1
    rows.append({'suite':suite,'run':reg['runs'][suite],'passed':True,'wait_exit':0,'verify_exit':0,
                 'receipt':str(path.resolve()),'receipt_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
                 'real_execution':str((base / execution_name).resolve()), 'url':run['html_url']})
closure={'passed':True,'source_sha':source,'build_run':reg['build_run'],'cloud_results':rows,
         'first_pipeline_execution':'original failure exit1 retained; missing full receipt not rewritten',
         'physical_device_status':'pending owner validation; no device actions',
         'scope':'Actual exact build and both successful fresh cloud runs plus all ORIGINAL independent artifact gates and full-byte before/after snapshot-map checks'}
(base / 'pipeline-result-continuation.json').open('x').write(json.dumps(closure,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(closure,ensure_ascii=False),flush=True)
