#!/usr/bin/env python3
"""Read-only re-execution of exact Android diagnosis verifiers, no device actions."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import subprocess

D = Path(__file__).resolve().parent.parent
ROOT = D / 'diag-44df9d0-evidence'
ART = ROOT / 'artifact'
OUT = D / 'resume-third/diag-independent-verification.json'
SOURCE = '44df9d0fd36aecaa22613e9aa73c5c7d4ed94416'
RUN = '43590599162'
report = json.loads((ART / 'diag-host-report.json').read_bytes())
run = json.loads((ROOT / 'run.json').read_bytes())
assert run['headSha'] == SOURCE and str(run['databaseId']) == RUN
assert run['status'] == 'completed' and run['conclusion'] == 'success'
assert report['passed'] is True and report['sourceSha'] == SOURCE
assert report['sdk'] == '33' and report['navigationMode'] == 'three-button'
assert re.fullmatch(r'[1-9][0-9]*', report['sdk'])
module_spec = importlib.util.spec_from_file_location('exact_diag_verifier', 'qa/diag_emulator_smoke.py')
assert module_spec is not None and module_spec.loader is not None
module = importlib.util.module_from_spec(module_spec)
module_spec.loader.exec_module(module)
harness = module.Harness.__new__(module.Harness)
harness.report = {}
harness.save = lambda: None
harness.verify_evidence(ART / 'diag-product', SOURCE, report['qaRun'])
assert json.loads(json.dumps(harness.report['independentPngChecks'])) == report['independentPngChecks']
assert harness.report['instrumentationReceipt'] == report['instrumentationReceipt']
keepalive = json.loads((ART / 'diag-product/keepalive-report.json').read_bytes())
sdk = int(report['sdk'])  # Original harness also passes int(sdk), saved JSON retains original '33'.
assert module.verify_keepalive_report(keepalive, SOURCE, report['qaRun'], sdk) == report['keepaliveInstrumentationReceipt']
negative_checks = 0
for key in ['defaultOn', 'onNotification', 'backgroundHttp', 'offPortClosed',
            'offNotificationRemoved', 'businessAndTokenAndErrorsUnchanged',
            'bindFailureUiOnAndHintRetained', 'startingNotActive', 'activeChannelDeniedStopsAndUiOn',
            'backgroundChannelDeniedEventStops', 'stopDisablesChoice', 'stopInactive',
            'permissionDeniedFailClosed', 'defaultOnNoPermissionRetainsChoice', 'noNotificationWithoutPermission']:
    bad = copy.deepcopy(keepalive)
    bad[key] = False
    try:
        module.verify_keepalive_report(bad, SOURCE, report['qaRun'], sdk)
    except AssertionError:
        negative_checks += 1
    else:
        raise AssertionError('Original keepalive verifier accepted false: ' + key)
background = report['normalBackgroundFgs']
assert background['passed'] is True and background['stopPath'] == 'actual-notification-action'
assert background['observationCount'] == len(background['observations']) == 3
assert all(all(row[k] is True for k in ('foreground', 'ordinaryProcess', 'urllibVersionAndError'))
           for row in background['observations'])
for key in ('defaultOn', 'stopDisablesChoice', 'stopInactive', 'stopAcknowledged',
            'offPortClosed', 'offNotificationRemoved', 'businessAndTokenAndErrorsUnchanged'):
    assert background[key] is True
assert report['normalHttpSelftest']['ok'] is True
assert report['normalHttpSelftest']['assertions'] == 3659
assert report['normalColdProcessPersistence'] is True and report['androidNioHttpRead'] is True
assert report['coldHttpAssertions'] == 133 and report['businessFilesUnchanged'] is True
binary = json.loads((D / 'download-44df9d0/actual-binary-verification-continuation-2/receipt.json').read_bytes())
for key, row in zip(('main', 'tests'), binary['rows']):
    assert report['apkSha256'][key] == row['sha256']
    assert report['certificates'][key] == row['signer_sha256']
inv = json.loads((ROOT / 'inventory.json').read_bytes())['inventory']
for path, item in inv.items():
    raw = (ROOT / path).read_bytes()
    assert len(raw) == item['bytes'] and hashlib.sha256(raw).hexdigest() == item['sha256']
result = {'passed': True, 'source_sha': SOURCE, 'run_id': RUN,
          'raw_files_verified': len(inv), 'independent_diagnostic_png_checks': len(module.SHOTS),
          'keepalive_original_flag_negatives_rejected': negative_checks,
          'normal_http_assertions': 3659, 'android_raw_socket_assertions': 133,
          'normal_http_write_eof_boundary': report['normalHttpSelftest']['write_eof_transport'],
          'normal_http_all_raw_checks_passed': report['normalHttpSelftest']['all_raw_checks_passed'],
          'background': background,
          'scope': 'Independent original validators on exact CI PNG/XML/reports/binary identity; NOT 10-minute MIUI/physical/watch proof',
          'physical_acceptance': 'pending-originator'}
with OUT.open('x') as file:
    json.dump(result, file, indent=2)
    file.write('\n')
print(json.dumps({k: v for k, v in result.items() if k != 'background'}))
