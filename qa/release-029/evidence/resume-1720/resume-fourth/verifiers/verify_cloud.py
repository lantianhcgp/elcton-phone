#!/usr/bin/env python3
"""Offline independent artifact gate. No adb/network/CI; outputs are new evidence only.

Usage: --source <literal 40hex> --run <literal digits> --suite diagnostics|full
       --incoming <fetch root containing run.json and artifact/> --out <NEW evidence dir>
JSON normalization changes tuple/list representation ONLY; no keys/errors/precision dropped.
External fetch/API/attempt/APK authenticity remains the parent's separate obligation.
"""
import argparse
import ast
import hashlib
import importlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import traceback
import xml.etree.ElementTree as ET

sys.dont_write_bytecode = True
ROOT = next(p for p in Path(__file__).resolve().parents if (p / 'qa/diag_emulator_smoke.py').is_file())
sys.path.insert(0, str(ROOT))
CRITERIA = ('diag_emulator_smoke', 'emulator_install_and_tour', 'verify_theme_evidence',
            'verify_palette_evidence', 'verify_system_bars')


def require(condition, label):
    if not condition:
        raise AssertionError(label)


def read_json(path):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            require(key not in result, 'Duplicate JSON key: ' + key)
            result[key] = value
        return result
    return json.loads(Path(path).read_bytes(), object_pairs_hook=unique,
                      parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def normalize(value):
    return json.loads(json.dumps(value, ensure_ascii=False, allow_nan=False))


def compare(actual, expected, label):
    # Entire JSON object, including errors, extra keys and unrounded values.
    a = json.dumps(normalize(actual), sort_keys=True, ensure_ascii=False, allow_nan=False)
    b = json.dumps(expected, sort_keys=True, ensure_ascii=False, allow_nan=False)
    require(a == b, label + ': COMPLETE JSON differs after serialization-only normalization')


def load_original(name):
    require(name in CRITERIA and name != 'emulator_install_and_tour', 'No executable tour import')
    return importlib.import_module('qa.' + name)


def check_run(run, source, run_id):
    require(re.fullmatch(r'[0-9a-f]{40}', source) is not None, 'Malformed --source')
    require(re.fullmatch(r'[1-9][0-9]*', run_id) is not None, 'Malformed --run')
    require(run.get('headSha') == source and str(run.get('databaseId')) == run_id,
            'run.json exact headSha/databaseId mismatch')
    require(run.get('status') == 'completed' and run.get('conclusion') == 'success',
            'run.json is not completed/success')


def check_host(host, source):
    require(host.get('passed') is True, 'Artifact report passed is not true')
    key = 'sourceSha' if 'sourceSha' in host else 'source_sha'
    require(host.get(key) == source, 'Artifact report exact source mismatch')


class Gate:
    def __init__(self, args):
        self.args = args
        self.art = args.incoming / 'artifact'
        self.out = args.out
        self.errors = []
        self.checks = []
        self.details = {}

    def check(self, name, fn):
        errors_before = len(self.errors)
        try:
            result = fn()
            self.checks.append({'name': name, 'passed': len(self.errors) == errors_before})
            if result is not None:
                self.details[name] = normalize(result)
                self.write(name + '.json', result)
            return result
        except Exception as error:
            self.checks.append({'name': name, 'passed': False})
            self.errors.append(name + ': ' + type(error).__name__ + ': ' + str(error))
            with (self.out / 'failures.log').open('a') as stream:
                stream.write(name + '\n' + traceback.format_exc() + '\n')
            return None

    def write(self, name, value):
        with (self.out / name).open('x') as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
            stream.write('\n')

    def snapshot(self):
        raw = self.out / 'raw'; raw.mkdir()
        inventory = {}
        for path in sorted(self.args.incoming.rglob('*')):
            require(not path.is_symlink(), 'Symlink input refused: ' + str(path))
            if path.is_file():
                relative = path.relative_to(self.args.incoming)
                target = raw / relative; target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(path, target)
                digest = sha(path)
                require(sha(target) == digest, 'Snapshot differs: ' + str(relative))
                inventory[str(relative)] = {'bytes': path.stat().st_size, 'sha256': digest}
        self.write('input-inventory.json', inventory)
        if (self.args.incoming / 'inventory.json').is_file():
            declared = read_json(self.args.incoming / 'inventory.json')
            require(declared['source_sha'] == self.args.source and str(declared['run']) == self.args.run,
                    'Fetch inventory exact identity mismatch')
            compare({k:v for k,v in inventory.items() if k != 'inventory.json'},
                    declared['inventory'], 'ALL fetched files')
        # Exercise only the immutable snapshot, not a concurrently changing incoming tree.
        self.art = raw / 'artifact'
        return {'raw_files': len(inventory), 'snapshot': str(raw)}

    def clients(self):
        host = read_json(self.art / 'client-jvm-selftest.log')
        require(host.get('ok') is True and host.get('mode') == 'actual-kotlin-host', 'Local real Kotlin host selftest')
        require(host.get('assertions') == 3784 and host.get('clients') == ['urllib', 'curl'], 'Local host 3784/both clients')
        require(host.get('all_raw_checks_passed') is True, 'Local host raw socket checks')
        compare(host['write_eof_transport'], {'status':'supported', 'excluded_checks':[]}, 'Local EOF transport')
        text = (self.art / 'client-jvm-regression.log').read_text()
        tests = ('content_length_post_survives_eof_closing_relay',
                 'direct_controls_with_and_without_write_eof_use_real_server',
                 'url_mode_really_runs_curl_and_urllib',
                 'url_mode_reports_unsupported_write_eof_without_dropping_other_checks')
        require(all(re.search(r'^test_' + name + r' .* \.\.\. ok$', text, re.M) for name in tests), 'ALL four real-client regressions')
        require(re.search(r'^Ran 4 tests in ', text, re.M) and re.search(r'^OK$', text, re.M)
                and not re.search(r'FAILED|FAILURES|ERROR|Traceback', text), 'Local client regression log is not green')
        return {'local_host':host, 'real_client_tests':list(tests), 'scope':'Existing local JVM raw logs, not Android/physical proof'}

    def diagnostics(self):
        d = load_original('diag_emulator_smoke'); host = read_json(self.art / 'diag-host-report.json')
        self.check('diag-report-identity', lambda: check_host(host, self.args.source))
        qa_run = host['qaRun']; sdk = host['sdk']
        require(isinstance(qa_run, str) and qa_run, 'Missing diag qaRun')
        require(isinstance(sdk, str) and re.fullmatch(r'[1-9][0-9]*', sdk), 'Invalid diag SDK')
        require(host['stage'] == 'complete' and host['navigationMode'] in ('three-button','gestural'), 'Incomplete diag stage/input')
        require(re.fullmatch(r'emulator-[0-9]+', host['serial']), 'Non-emulator capture serial')
        d.source_identity((self.art / 'checkout-head.stdout.bin').read_bytes().decode('ascii'), self.args.source)
        require((self.art / 'sdk-property.stdout.bin').read_text().removesuffix('\n') == sdk, 'Saved SDK property mismatch')
        overlay = 'com.android.internal.systemui.navbar.' + ('threebutton' if host['navigationMode'] == 'three-button' else 'gestural')
        require('[x] ' + overlay in (self.art / 'overlays.stdout.bin').read_text(), 'Saved navigation overlay mismatch')
        def pngs():
            h = d.Harness.__new__(d.Harness); h.report = {}; h.save = lambda: None
            h.verify_evidence(self.art / 'diag-product', self.args.source, qa_run)
            compare(h.report['instrumentationReceipt'], host['instrumentationReceipt'], 'Diag instrumentation report')
            compare(h.report['independentPngChecks'], host['independentPngChecks'], 'Diag ALL PNG metrics')
            for name in d.SHOTS:
                compare(read_json(self.art / 'diag-product' / (name + '.json')),
                        next(c for c in host['instrumentationReceipt']['captures'] if c['name']==name), 'Complete capture '+name)
            return h.report
        self.check('diag-original-png-xml', pngs)
        def keepalive():
            receipt = d.verify_keepalive_report(read_json(self.art / 'diag-product/keepalive-report.json'),
                                               self.args.source, qa_run, int(sdk))
            compare(receipt, host['keepaliveInstrumentationReceipt'], 'Keepalive ALL fields')
            require((self.art / 'diag-product/mcp-keepalive-on.png').stat().st_size > 0, 'Keepalive PNG missing')
            require(any(n.get('package')==d.PACKAGE for n in ET.parse(self.art / 'diag-product/mcp-keepalive-on.xml').iter('node')), 'Keepalive actual app XML')
            return receipt
        self.check('diag-original-keepalive', keepalive)
        def shared():
            receipt = read_json(self.art / 'diag-product/shared-phone-report.json'); check_host(receipt, self.args.source)
            require(receipt['qaRun']==qa_run, 'Shared fixture qaRun mismatch')
            for key in ('sharedPhoneActivityRecreated','pureMcpCoursesWriteRead','previewDoesNotWrite',
                        'confirmedWritePersisted','protectedDataUnchanged','fixtureFilesRestored'):
                require(receipt.get(key) is True, 'Missing shared fixture assertion: '+key)
            compare(receipt, host['sharedPhoneInstrumentationReceipt'], 'Shared fixture ALL fields')
            for name in ('diag','shared-phone','keepalive'):
                raw = (self.art / (name+'-instrumentation.stdout.bin')).read_bytes()
                d.verify_one_test(subprocess.CompletedProcess([],0,raw,b''), name+' saved wire')
            return receipt
        self.check('diag-shared-and-instrumentation-wire', shared)
        def http():
            recorded = read_json(self.art / 'android-http-selftest.stdout.bin')
            compare(recorded, host['normalHttpSelftest'], 'External Android HTTP complete wire report')
            require(recorded['ok'] is True and recorded['mode']=='read-only-app' and recorded['clients']==['urllib','curl'], 'Android HTTP actual clients')
            require(recorded['assertions']==3659 and recorded['all_raw_checks_passed'] is False, 'Android external URL boundary: 3659, not all 3784')
            compare(recorded['write_eof_transport'], {'status':'unsupported','reason':'EmptyHttpResponse',
                    'excluded_checks':['Truncated body rejected (requires client write EOF)'],
                    'required_validation':'direct production-host raw socket and Android direct Socket'}, 'Android EOF explicit boundary')
            for key in ('normalColdProcessPersistence','androidNioHttpRead','businessFilesUnchanged'):
                require(host.get(key) is True, 'Missing normal Android assertion: '+key)
            require(host['coldHttpAssertions']==133, 'Normal Android socket assertions 133')
            for label in ('main','tests'):
                signer = d.certificate_identity((self.art/(label+'-apksigner.stdout.bin')).read_text())
                require(signer==host['certificates'][label], 'Saved actual signer differs')
                require(re.fullmatch(r'[0-9a-f]{64}',host['apkSha256'][label]), 'Malformed saved APK hash')
            return {'external_android':recorded, 'android_socket_assertions':133,
                    'scope':'Saved Android direct Socket instrumentation + URL clients; parent verifies APK bytes/remote inputs'}
        self.check('diag-http-and-signer-wire', http)
        self.check('diag-background-notification-stop', lambda: self.background(host, d))

    def background(self, host, d):
        b = host['normalBackgroundFgs']
        for key in ('passed','defaultOn','stopDisablesChoice','stopInactive','stopAcknowledged',
                    'offPortClosed','offNotificationRemoved','businessAndTokenAndErrorsUnchanged'):
            require(b.get(key) is True, 'Background assertion false/missing: '+key)
        require(b['stopPath']=='actual-notification-action' and b['observationCount']==len(b['observations'])==3, 'Original 3-probe/notification STOP coverage')
        h = d.Harness.__new__(d.Harness)
        def playback(label, *args, **kwargs):
            # READ ONLY. Never use Harness.adb, shell, execute or finish.
            return subprocess.CompletedProcess([],0,(self.art/(label+'.stdout.bin')).read_bytes(),b'')
        h.adb = playback
        expected = (self.art/'diag-product/synthetic-expected.txt').read_text()
        previous = -1
        for number,row in enumerate(b['observations'],1):
            require(row['attempt']==number and row['elapsedSeconds']>=previous, 'Background probe ordering')
            previous=row['elapsedSeconds']; require(previous >= (0,2.5,5)[number-1], 'Background observation offsets shortened')
            require(all(row.get(k) is True for k in ('foreground','ordinaryProcess','urllibVersionAndError')), 'Background probe flags')
            prefix='normal-background-'+str(number); h.foreground_receipt(prefix,b['pid'])
            for kind in ('version','errors'):
                label=prefix+'-'+kind; raw=(self.art/(label+'-response.json')).read_bytes()
                meta=read_json(self.art/(label+'-http.json')); reply=read_json(self.art/(label+'-response.json'))
                require(meta['status']==200 and int(meta['headers']['content-length'])==len(raw), 'Background real HTTP length/status')
                require(reply.get('jsonrpc')=='2.0' and reply.get('id')==label and 'error' not in reply, 'Background RPC envelope')
                result=reply['result']; require(result['isError'] is False and len(result['content'])==1 and result['content'][0]['type']=='text', 'Background RPC success')
                data=json.loads(result['content'][0]['text']); compare(data,result['structuredContent'],'Background complete tool text/structured')
                if kind=='version': require((data['packageName'],data['versionName'],data['versionCode'])==(d.PACKAGE,'0.2.9',11),'Background version')
                else: require(len(data['errors'])==1 and data['errors'][0]['full']==expected,'Background full persisted diagnostic')
        tree=ET.parse(self.art/'normal-notification-on.xml').getroot()
        containers=[n for n in tree.iter('node') if any(c.get('text')=='MCP 保持运行' for c in n.iter('node')) and any(c.get('text') in ('停止','STOP','Stop') for c in n.iter('node'))]
        require(containers, 'Actual notification/STOP subtree missing')
        container=min(containers,key=lambda n:len(list(n.iter('node'))))
        stops=[n for n in container.iter('node') if n.get('package')=='com.android.systemui' and n.get('text') in ('停止','STOP','Stop') and n.get('enabled')=='true']
        require(len(stops)==1,'Actual unique notification STOP absent')
        before=(self.art/'normal-stop-events-before.stdout.bin').read_text(); acknowledged=False
        for path in self.art.glob('normal-stop-choice-*.stdout.bin'):
            number=path.name.removeprefix('normal-stop-choice-').removesuffix('.stdout.bin')
            choice=ET.fromstring(path.read_bytes()).find("boolean[@name='keep_running']")
            events=(self.art/('normal-stop-events-'+number+'.stdout.bin')).read_text()
            services=(self.art/('normal-stop-ack-services-'+number+'.stdout.bin')).read_text()
            acknowledged |= (choice is not None and choice.get('value')=='false' and
                             all(events.count(s)>before.count(s) for s in ('MCP notification STOP delivered','MCP stop handled; active=false; choiceSaved=true')) and
                             'McpKeepAliveService' not in services and 'isForeground=true' not in services)
        require(acknowledged,'Durable STOP acknowledgement absent')
        for i in range(3):
            binary=self.art/('normal-stop-port-'+str(i)+'.bin'); text=self.art/('normal-stop-port-'+str(i)+'.txt')
            require((binary.is_file() and binary.read_bytes()==b'') or (text.is_file() and text.read_text()=='Actual socket refused/reset/broken pipe; no HTTP response\n'), 'Listener closure raw evidence')
        stopped=(self.art/'normal-stop-services.stdout.bin').read_text()
        require('McpKeepAliveService' not in stopped and 'isForeground=true' not in stopped,'Service remains after STOP')
        require(not any(n.get('text')=='MCP 保持运行' for n in ET.parse(self.art/'normal-notification-off.xml').iter('node')),'Notification remains after STOP')
        for label, checked in (('normal-on-readback', 'true'), ('normal-off-readback', 'false')):
            paths = sorted(self.art.glob(label + '-settings-*.xml'))
            require(paths, 'Missing actual settings readback: ' + label)
            switch = None
            for path in paths:
                nodes = [n for n in ET.parse(path).iter('node') if n.get('package') == d.PACKAGE]
                switches = [n for n in nodes if n.get('resource-id') in ('mcp-keepalive-switch', d.PACKAGE + ':id/mcp-keepalive-switch')
                            or (n.get('class') == 'android.widget.Switch' and n.get('checkable') == 'true')]
                if switches:
                    require(len(switches) == 1 and any(n.get('text') == 'MCP 保持运行' for n in nodes), 'Ambiguous/missing original keepalive readback switch/label')
                    switch = switches[0]
            require(switch is not None and switch.get('checked') == checked, 'Actual on/off UI readback mismatch')
        for suffix in ('business','private-hashes'):
            require((self.art/('background-before-'+suffix+'.stdout.bin')).read_bytes()==(self.art/('background-after-'+suffix+'.stdout.bin')).read_bytes(),'Background protected data changed')
        require((self.art/'http-business-before.stdout.bin').read_bytes()==(self.art/'http-business-after.stdout.bin').read_bytes(),'Read-only HTTP business changed')
        return {'background':b,'scope':'Finite 5 seconds / 3 ordinary emulator probes, NOT 10-minute, Doze, MIUI, watch or physical acceptance'}

    def full(self):
        host=read_json(self.art/'report.json')
        self.check('full-report-identity', lambda: check_host(host,self.args.source))
        # Keep every original failure field (e.g. harvested:false), even when later gates fail.
        self.write('full-original-report.json',host)
        environment=read_json(self.art/'environment.json'); navigation=environment['navigation_mode']
        require(navigation in ('three-button','gestural'),'Full navigation input')
        for label,name in (('theme','verify_theme_evidence'),('palette','verify_palette_evidence')):
            def product(label=label,name=name):
                original=load_original(name); saved_host=read_json(self.art/(label+'-host.json'))
                self.write(label+'-original-host.json',saved_host)
                require(saved_host['source_sha']==self.args.source and saved_host['navigation_mode']==navigation,'Full '+label+' exact source/input')
                actual=original.verify_product(self.art/(label+'-product'),saved_host)
                self.write(label+'-recomputed.json',actual)
                require(saved_host['passed'] is True,'Original '+label+' host RED')
                compare(actual,read_json(self.art/(label+'-report.json')),label+' ALL scene/phase JSON')
                compare(actual,host[label+'_ui'],label+' embedded report ALL JSON')
                require(actual['passed'] is True,'Original '+label+' pixels/phases RED')
                return {'screenshots':actual['screenshots'],'passed':actual['passed']}
            self.check('full-'+label+'-original',product)
        self.check('full-tour-original-static-block',lambda:self.tour(host))
        def system_bars():
            original=load_original('verify_system_bars')
            missing=sorted(n for n in original.APP_SCENES if not (self.art/'product'/(n+'.png')).is_file())
            require(not missing,'Missing original app-owned system-bar scenes: '+str(missing))
            rows=[original.inspect(self.art/'product'/(n+'.png'),self.art/'product'/(n+'-state.json')) for n in sorted(original.APP_SCENES)]
            report={'passed':all(r['passed'] for r in rows),'scenes':len(rows),
                    'scope':'Full-screen emulator screenshots; keyboard/SAF system chrome is outside app ownership','results':rows}
            self.write('system-bars-recomputed.json',report)
            compare(report,read_json(self.art/'system-bar-pixels.json'),'System bars COMPLETE JSON')
            compare(report,host['system_bar_pixels'],'System bars embedded COMPLETE JSON')
            require(report['passed'] is True,'Original system bar pixel predicates RED')
            return {'scenes':len(rows),'passed':report['passed']}
        self.check('full-system-bars-original',system_bars)

    def tour(self, host):
        from PIL import Image,ImageStat
        # Execute ONLY the frozen pure verifier span: shots=[] through crash assertion.
        # Never import the tour module (its top level performs adb/install).
        path=ROOT/'qa/emulator_install_and_tour.py'; tree=ast.parse(path.read_text())
        def assignment_named(node, name):
            return isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == name for t in node.targets)
        start=next(i for i,n in enumerate(tree.body) if assignment_named(n, 'shots'))
        end=next(i for i in range(start,len(tree.body)) if assignment_named(tree.body[i], 'pixel_run'))
        block=ast.Module(body=tree.body[start:end],type_ignores=[])
        for node in ast.walk(block):
            require(not isinstance(node,(ast.Import,ast.ImportFrom)), 'Unexpected imports in pure verifier block')
            if isinstance(node,ast.Call) and isinstance(node.func,ast.Name):
                require(node.func.id not in ('shell','exec','eval','open','__import__'),'Unsafe tour call')
        names=set(re.findall(r'shot\("([^"]+)"\)',(ROOT/'app/src/androidTest/java/com/hcbiu/elcton/ProductUiTest.kt').read_text()))
        require(len(names)==28 and {p.stem for p in (self.art/'product').rglob('*.png')}==names,'Original 28 exact tour scene names missing/extra')
        logs=(self.art/'logcat.txt').read_text(); instrumentation=(self.art/'instrumentation.txt').read_text()
        require(re.search(r'OK \(1 test\)',instrumentation) and 'FAILURES' not in instrumentation and 'INSTRUMENTATION_FAILED' not in instrumentation,'Original full instrumentation RED')
        from typing import cast
        scope={'out':self.art,'logs':logs,'Image':Image,'ImageStat':ImageStat,'ET':ET,'json':json,'re':re,'cast':cast}
        exec(compile(block,str(path)+'#offline-pure-verifier','exec'),scope)
        for key,name in (('shots','shots'),('hierarchies','hierarchies'),('ime_checks','keyboard_pixel_checks')):
            compare(scope[key],host[name],'Full original '+name+' COMPLETE JSON')
        return {'shots':len(scope['shots']),'hierarchies':len(scope['hierarchies']),
                'states':len(names),'keyboard_pixel_checks':len(scope['ime_checks']),
                'original_block_lines':[tree.body[start].lineno,tree.body[end-1].end_lineno]}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',required=True); parser.add_argument('--run',required=True)
    parser.add_argument('--suite',choices=('diagnostics','full'),required=True)
    parser.add_argument('--incoming',type=Path,required=True); parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args(); args.incoming=args.incoming.resolve(); args.out=args.out.resolve()
    require(re.fullmatch(r'[0-9a-f]{40}',args.source),'Malformed --source')
    require(re.fullmatch(r'[1-9][0-9]*',args.run),'Malformed --run')
    require(args.out.is_relative_to(ROOT/'qa/release-029/evidence'),'Output must be inside evidence')
    require(not args.out.is_relative_to(args.incoming) and not args.incoming.is_relative_to(args.out),'Input/output overlap refused')
    args.out.mkdir(parents=True,exist_ok=False)
    gate=Gate(args)
    gate.write('execution.json',{'argv':sys.argv,'source':args.source,'run':args.run,'suite':args.suite,
                              'incoming':str(args.incoming),'out':str(args.out),'python':sys.version,
                              'tool_sha256':sha(__file__),'scope':'HOST OFFLINE ONLY: zero adb/API/CI/device actions'})
    gate.write('criteria-sha256.json',{name:sha(ROOT/'qa'/(name+'.py')) for name in CRITERIA})
    gate.check('input-snapshot-all-bytes',gate.snapshot)
    gate.check('exact-run-success',lambda:check_run(read_json(args.out/'raw/run.json'),args.source,args.run))
    gate.check('local-client-raw-logs',gate.clients)
    gate.check(args.suite+'-complete',gate.diagnostics if args.suite=='diagnostics' else gate.full)
    receipt={'passed':not gate.errors,'source_sha':args.source,'run_id':args.run,'suite':args.suite,
             'checks':gate.checks,'errors':gate.errors,'details':gate.details,
             'scope':'Offline exact original artifact verifiers, NOT new cloud execution or physical/watch proof',
             'external_binding':'Parent must verify current exact API/attempt/inputs/APK/source independently'}
    gate.write('receipt.json',receipt)
    print(json.dumps({'passed':receipt['passed'],'source_sha':args.source,'run_id':args.run,
                      'suite':args.suite,'checks':len(gate.checks),'errors':gate.errors,'receipt':str(args.out/'receipt.json')}))
    return 0 if receipt['passed'] else 1


if __name__=='__main__':
    raise SystemExit(main())
