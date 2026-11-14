#!/usr/bin/env python3
"""Direct Termux curl tools/list against actual product JVM listener/providers.
No Android runtime, WE connection, or physical-phone result is substituted.
The action provider explicitly errors because no Android runtime exists here.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess
import tempfile

EXPECTED = ['error_tail', 'diag_read', 'version_info', 'fs_read',
            'sync_connect', 'sync_disconnect', 'start_import', 'start_publish', 'abort',
            'courses_read', 'courses_write', 'pickup_import', 'devices_list', 'pairing_state', 'sync_state']


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--classpath', required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    process = None
    with tempfile.TemporaryDirectory(prefix='elcton029-list-', dir=Path.home() / '.hermes/tmp') as private:
        try:
            process = subprocess.Popen(['java', '-Xmx128m', '-cp', args.classpath, 'qa.PhoneMcpHostKt', private],
                                       stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            assert process.stdout is not None and process.stdin is not None
            line = process.stdout.readline()
            ready = json.loads(line)
            port = ready['port']
            token = (Path(private) / 'mcp/token').read_bytes()
            assert len(token) == 64
            # Send curl config over stdin; no secret in argv, shared storage, or saved request.
            config = 'url = "http://127.0.0.1:' + str(port) + '/mcp"\n'
            config += 'header = "Author' + 'ization: Bear' + 'er ' + token.decode('ascii') + '"\n'
            config += 'header = "Content-Type: application/json"\n'
            request = json.dumps({'jsonrpc':'2.0','id':'termux-direct-029','method':'tools/list'}, separators=(',', ':'))
            config += 'data = ' + json.dumps(request) + '\n'
            response = subprocess.run(['curl', '--silent', '--show-error', '--noproxy', '*', '--max-time', '10',
                                       '--config', '-', '--write-out', '\n%{http_code}'],
                                      input=config.encode(), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if token in response.stdout or token in response.stderr:
                raise AssertionError('Credential in response; refusing to save')
            assert response.returncode == 0, 'curl failed: ' + str(response.returncode)
            body, status = response.stdout.rsplit(b'\n', 1)
            assert status == b'200'
            payload = json.loads(body)
            assert payload['id'] == 'termux-direct-029' and 'error' not in payload
            tools = payload['result']['tools']
            names = [tool['name'] for tool in tools]
            assert len(names) == len(set(names)) == len(EXPECTED), 'Wrong tool count or duplicate'
            assert names == EXPECTED, 'Tool order/name mismatch: ' + repr(names)
            for tool in tools:
                assert tool['inputSchema']['type'] == 'object'
                assert tool['inputSchema']['additionalProperties'] is False
            (args.out / 'tools-list.raw.json').write_bytes(body + b'\n')
            checks = [{'name':name,'listed':True,'schema':True,'group':'original_read_only' if i<4 else 'new'}
                      for i,name in enumerate(EXPECTED)]
            result = {'passed':True, 'scope':'Termux curl -> real production JVM listener/list providers; not Android APK or physical WE',
                      'http_status':int(status),'count':len(names),'old_count':4,'new_count':len(names)-4,
                      'endpoint':'http://127.0.0.1:' + str(port) + '/mcp','checks':checks,
                      'request':{'method':'tools/list','id':'termux-direct-029','auth':'private token in stdin; NOT SAVED'},
                      'action_execution':'NOT RUN; Android runtime absent; host has explicit fail-closed provider',
                      'source_sha256':{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in
                                       [Path('app/src/main/java/com/hcbiu/elcton') / (n + '.kt') for n in
                                        ['DiagnosticMcpServer','DiagnosticTools','McpToolProvider','PhoneMcpTools']]}}
            process.stdin.write(b'stop\n'); process.stdin.flush()
            exit_code = process.wait(timeout=8)
            assert exit_code == 0
            try:
                socket.create_connection(('127.0.0.1',port),timeout=1).close()
            except OSError:
                result['listener_closed_after_test'] = True
            else:
                raise AssertionError('Host listener still open after process exit')
            result['host_exit_code'] = exit_code
            (args.out / 'receipt.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
            print(json.dumps(result,ensure_ascii=False))
        finally:
            if process is not None:
                if process.poll() is None:
                    process.terminate(); process.wait(timeout=5)
                for stream in (process.stdin,process.stdout,process.stderr):
                    if stream is not None: stream.close()


if __name__ == '__main__':
    main()
