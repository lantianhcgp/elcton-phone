#!/usr/bin/env python3
"""Real HTTP integration checks. Host mode starts production Kotlin, never a Python mock.

Host: python qa/mcp_http_selftest.py --classpath <jar:json.jar>
App:  python qa/mcp_http_selftest.py --url http://127.0.0.1:8766 --token-file <private-file>
App:  python qa/mcp_http_selftest.py --url http://127.0.0.1:8766 --adb-token com.hcbiu.elcton
      (--adb-token uses adb exec-out run-as PACKAGE cat files/mcp/token; --adb-token-path overrides)
Only host fixtures are mutated. --url mode is read-only and does not stop the app.
"""
import argparse
import errno
import http.client
import json
import os
from pathlib import Path
import re
import selectors
import socket
import subprocess
import sys
import tempfile
import time
from typing import Any
from urllib.parse import urlsplit


class CheckFailure(Exception):
    pass


def require(condition, label):
    if not condition:
        raise CheckFailure(label)


def encode(value):
    return json.dumps(value, ensure_ascii=False, separators=(',', ':')).encode('utf-8')


class Suite:
    def __init__(self, url, token, fixture=None):
        parts = urlsplit(url)
        require(parts.scheme == 'http' and not parts.query and not parts.fragment and parts.path in ('', '/', '/mcp'), 'URL must be an HTTP endpoint without credentials or query')
        require(not parts.username and not parts.password, 'URL credentials are not allowed')
        self.host, self.port = parts.hostname, parts.port or 8766
        self.token, self.fixture, self.count = token, fixture, 0

    def check(self, condition, label):
        require(condition, label)
        self.count += 1

    def wire(self, wire, shutdown=True):
        with socket.create_connection((self.host, self.port), timeout=6) as connection:
            connection.settimeout(6)
            connection.sendall(wire)
            if shutdown:
                try:
                    connection.shutdown(socket.SHUT_WR)
                except OSError as failure:
                    # The one-shot server may have already sent a complete response and closed.
                    # Still read and validate the full HTTP reply; all other errors are failures.
                    if failure.errno != errno.ENOTCONN:
                        raise
            chunks = []
            while True:
                chunk = connection.recv(65536)
                if not chunk:
                    break
                chunks.append(chunk)
        raw = b''.join(chunks)
        self.check(b'\r\n\r\n' in raw, 'HTTP framing')
        head, body = raw.split(b'\r\n\r\n', 1)
        lines = head.decode('ascii').split('\r\n')
        status = int(lines[0].split()[1])
        headers = {line.split(':', 1)[0].lower(): line.split(':', 1)[1].strip() for line in lines[1:]}
        self.check(int(headers['content-length']) == len(body), 'UTF8 byte Content-Length')
        self.check(headers.get('connection') == 'close', 'Connection is closed')
        self.check(self.token.encode('ascii') not in raw, 'Credential is never echoed')
        body.decode('utf-8', errors='strict')
        return status, headers, body

    def request(self, method, path, body: Any = b'', auth: bool | str = True, extra=None):
        if not isinstance(body, bytes):
            body = encode(body)
        headers = {'Host': 'localhost', 'Content-Type': 'application/json', 'Content-Length': str(len(body))}
        if auth is True:
            headers['Authorization'] = 'Bearer ' + self.token
        elif isinstance(auth, str):
            headers['Authorization'] = auth
        if extra:
            headers.update(extra)
        start = f'{method} {path} HTTP/1.1\r\n'
        start += ''.join(f'{key}: {value}\r\n' for key, value in headers.items()) + '\r\n'
        return self.wire(start.encode('ascii') + body)

    def rpc(self, method, params=None, ident=1):
        value = {'jsonrpc': '2.0', 'id': ident, 'method': method}
        if params is not None:
            value['params'] = params
        status, _, body = self.request('POST', '/mcp', value)
        self.check(status == 200, 'RPC HTTP 200')
        reply = json.loads(body)
        self.check(reply.get('jsonrpc') == '2.0' and reply.get('id') == ident, 'RPC id preservation')
        return reply

    def call(self, name, args=None):
        reply = self.rpc('tools/call', {'name': name, 'arguments': {} if args is None else args})
        self.check('result' in reply, 'Tool result exists')
        result = reply['result']
        self.check(isinstance(result.get('isError'), bool), 'Tool isError is boolean')
        content = result['content']
        self.check(len(content) == 1 and content[0]['type'] == 'text', 'MCP text content')
        data = json.loads(content[0]['text'])
        if 'structuredContent' in result:
            self.check(result['structuredContent'] == data, 'Structured content is actual text JSON')
        return result['isError'], data

    def error(self, body, code):
        status, _, raw = self.request('POST', '/mcp', body)
        self.check(status == 200 and json.loads(raw).get('error', {}).get('code') == code, 'JSON-RPC error code ' + str(code))
        self.check(b'private-secret' not in raw, 'Errors never echo request')

    def run(self):
        status, _, body = self.request('GET', '/health', auth=False)
        self.check(status == 200 and json.loads(body) == {'ok': True}, 'Anonymous minimal health')
        methods = ['initialize', 'ping', 'tools/list', 'tools/call', 'notifications/initialized']
        wrong_case = self.token.swapcase()
        if wrong_case == self.token:
            wrong_case = ('a' if self.token[0] != 'a' else 'b') + self.token[1:]
        for method in methods:
            req: dict[str, Any] = {'jsonrpc': '2.0', 'method': method}
            if method != 'notifications/initialized':
                req['id'] = 1
            for auth in [False, 'Bearer', 'Bearer ', 'Bearer wrong', 'Bearer ' + wrong_case, 'Basic ' + self.token]:
                status, _, _ = self.request('POST', '/mcp', req, auth=auth)
                self.check(status == 401, 'Every MCP method requires exact Bearer token')
        status, _, _ = self.request('POST', '/mcp', {'jsonrpc': '2.0', 'id': 1, 'method': 'ping'}, auth='bEaReR ' + self.token)
        self.check(status == 200, 'Scheme is case-insensitive')
        ping = encode({'jsonrpc': '2.0', 'id': 1, 'method': 'ping'})
        header = f'POST /mcp HTTP/1.1\r\naUtHoRiZaTiOn: bEaReR {self.token}\r\nContent-Length: {len(ping)}\r\n\r\n'.encode('ascii')
        self.check(self.wire(header + ping)[0] == 200, 'Header name is case-insensitive')
        for path in ['/mcp?token=' + self.token, '/mcp/extra', '/mcpx', '/mcp/', '/%6dcp', '/health?x=1']:
            self.check(self.request('POST', path, ping, auth=False)[0] == 404, 'Exact endpoint and no URL-token bypass')
        self.check(self.request('GET', '/mcp', auth=False)[0] == 405, 'POST only MCP')
        initialized = self.rpc('initialize', {'protocolVersion': '2025-03-26', 'capabilities': {}, 'clientInfo': {'name': 'selftest', 'version': '1'}})['result']
        self.check(initialized['protocolVersion'] == '2025-03-26' and 'tools' in initialized['capabilities'], 'MCP initialize negotiation')
        listed = self.rpc('tools/list')['result']['tools']
        self.check(len(listed) == 4 and {t['name'] for t in listed} == {'error_tail', 'diag_read', 'version_info', 'fs_read'}, 'Exactly four read-only tools')
        for tool in listed:
            schema = tool['inputSchema']
            self.check(schema['type'] == 'object' and schema['additionalProperties'] is False and 'required' in schema, 'Schemas enforce object fields')
            self.check(tool['annotations']['readOnlyHint'] is True, 'Read-only annotations')
        failed, version = self.call('version_info')
        self.check(not failed and isinstance(version, dict), 'Real version callback')
        failed, diag = self.call('diag_read')
        self.check(not failed and isinstance(diag, dict), 'Real diag callback')
        if self.fixture:
            self.check(version.get('versionName') == 'host-fixture' and diag.get('label') == '离线🙂', 'Host callbacks are real fixtures')
        for limit in [None, 1, 128]:
            failed, data = self.call('error_tail', {} if limit is None else {'limit': limit})
            self.check(not failed and isinstance(data.get('errors'), list), 'Actual error_tail list')
            self.check(len(data['errors']) <= (20 if limit is None else limit), 'error_tail limit respected')
            if self.fixture and limit is None:
                self.check(len(data['errors']) == 2 and data['errors'][0]['message'] == 'synthetic 一', 'Two real fixture error rows')
        for path in ['diagnostics/state.json', 'diagnostics/wear-errors.jsonl']:
            failed, data = self.call('fs_read', {'path': path})
            if self.fixture:
                self.check(not failed and data['text'] == (self.fixture / path).read_text(), 'Actual whitelist file bytes')
            else:
                self.check(isinstance(data, dict), 'Real app file read or explicit isError if absent')
        for path in ['../diagnostics/state.json', '/data/private-secret', 'diagnostics/../diagnostics/state.json', './diagnostics/state.json', 'diagnostics//state.json', 'mcp.token', 'schedule.json', 'shared_prefs/prefs.xml', 'diagnostics', 'diagnostics/state.json\x00']:
            failed, data = self.call('fs_read', {'path': path})
            self.check(failed and path not in json.dumps(data), 'Whitelist rejects sensitive/path traversal reads')
        for ident in ['中文🙂', 17, 9223372036854775807, 1.5, None]:
            self.check(self.rpc('ping', ident=ident)['result'] == {}, 'String/number/null id preserved')
        # Raw request bytes and lexical parse hooks: never compare rounded Python floats.
        numeric_ids = ['9223372036854775809', '-9223372036854775809', '1e999', '-1E+999',
                       '1.2300e+004', '-0', '0.00', '0e0', '1e-999',
                       '123456789012345678901234567890.1234567890']
        class NumericToken(str):
            pass
        def reject_constant(_):
            raise CheckFailure('Reply contains a non-JSON number')
        for ident in numeric_ids:
            for fields, expected in [
                ('"jsonrpc":"2.0","method":"ping"', None),
                ('"jsonrpc":"1.0","method":"ping"', -32600),
                ('"jsonrpc":"2.0","method":false', -32600),
                ('"jsonrpc":"2.0","method":"unknown"', -32601),
                ('"jsonrpc":"2.0","method":"ping","params":[]', -32602)]:
                request = ('{' + fields + ',"id":' + ident + '}').encode('ascii')
                status, _, raw = self.request('POST', '/mcp', request)
                reply = json.loads(raw, parse_int=NumericToken, parse_float=NumericToken, parse_constant=reject_constant)
                self.check(status == 200, 'Raw numeric id HTTP 200')
                self.check(type(reply.get('id')) is NumericToken and reply['id'] == ident, 'Exact raw numeric id token preserved')
                self.check(reply.get('result') == {} if expected is None else reply.get('error', {}).get('code') == str(expected), 'Numeric id RPC result/error')
        status, _, raw = self.request('POST', '/mcp', rb'{"params":{"clientInfo":{"id":7}},"i\u0064":1.00E+009,"method":"initialize","jsonrpc":"2.0"}')
        reply = json.loads(raw, parse_int=NumericToken, parse_float=NumericToken, parse_constant=reject_constant)
        self.check(status == 200 and type(reply.get('id')) is NumericToken and reply['id'] == '1.00E+009' and 'result' in reply, 'Escaped top-level id ignores nested ids')
        for method in ['notifications/initialized', 'ping', 'tools/list', 'unknown']:
            status, _, body = self.request('POST', '/mcp', {'jsonrpc': '2.0', 'method': method})
            self.check(status == 202 and body == b'', 'Notification 202 empty body')
        for body in [b'', b'{', b'{"a":1,"a":2}', b'{"jsonrpc":"2.0"} trailing', b"{'jsonrpc':'2.0'}", b'{"x":NaN}', b'{"x":1,}', b'{"x":01}']:
            self.error(body, -32700)
        for body in [b'[]', b'42', b'null', b'{}', encode({'jsonrpc': '1.0', 'method': 'ping', 'id': 1}), encode({'jsonrpc': '2.0', 'method': 'ping', 'id': True}), encode({'jsonrpc': '2.0', 'method': 'ping', 'id': {}})]:
            self.error(body, -32600)
        self.error({'jsonrpc': '2.0', 'id': 1, 'method': 'private-secret'}, -32601)
        invalid_params = [[], None, {'name': 'diag_read', 'arguments': []}, {'name': 'diag_read', 'arguments': {'private-secret': True}}, {'name': 'fs_read', 'arguments': {}}, {'name': 'fs_read', 'arguments': {'path': 1}}, {'name': 'diag_read', 'surprise': 1}]
        invalid_params.extend({'name': 'error_tail', 'arguments': {'limit': x}} for x in [0, 129, -1, 1.5, 1.0, '20', True, None])
        for params in invalid_params:
            self.error({'jsonrpc': '2.0', 'id': 7, 'method': 'tools/call', 'params': params}, -32602)
        failed, data = self.call('private-secret')
        self.check(failed and 'private-secret' not in json.dumps(data), 'Unknown tool isError sanitized')
        base = f'POST /mcp HTTP/1.1\r\nAuthorization: Bearer {self.token}\r\n'
        for framing in ['Content-Length: -1', 'Content-Length: abc', 'Content-Length: 1\r\nContent-Length: 1', 'Content-Length: 0\r\nTransfer-Encoding: chunked', 'Content-Length: 0\r\nAuthorization: Bearer ' + self.token, 'Content-Length: 0\r\n folded: value']:
            self.check(self.wire((base + framing + '\r\n\r\n').encode('ascii'))[0] == 400, 'Malformed/ambiguous framing rejected')
        self.check(self.wire((base + '\r\n').encode('ascii'))[0] == 411, 'Content-Length required')
        self.check(self.wire((base + 'Content-Length: 9\r\n\r\n{}').encode('ascii'))[0] == 400, 'Truncated body rejected')
        self.check(self.wire((base + 'Content-Length: 65537\r\n\r\n').encode('ascii'))[0] == 413, 'Body size bounded')
        self.check(self.wire((base + 'X-Large: ' + 'x' * 17000 + '\r\n\r\n').encode('ascii'))[0] == 431, 'Header size bounded')
        self.check(self.wire((base + 'Content-Length: 2\r\n\r\n').encode('ascii') + b'\xc3\x28')[0] == 400, 'Strict body UTF8')
        started = time.monotonic()
        self.check(self.wire((base + 'Content-Length: 9\r\n\r\n{').encode('ascii'), shutdown=False)[0] == 408, 'Partial body finite read timeout')
        self.check(time.monotonic() - started < 5, 'Read timeout bounded')
        if self.fixture:
            failure_marker = self.fixture / 'fail.diag'
            failure_marker.touch()
            try:
                failed, data = self.call('diag_read')
                self.check(failed and 'private-secret' not in json.dumps(data), 'Provider exceptions are actual sanitized isError')
            finally:
                failure_marker.unlink()
            state = self.fixture / 'diagnostics/state.json'
            original = state.read_bytes()
            try:
                state.write_bytes(b'a' * (256 * 1024))
                failed, data = self.call('fs_read', {'path': 'diagnostics/state.json'})
                self.check(not failed and len(data['text']) == 256 * 1024, '256KiB file boundary allowed')
                state.write_bytes(b'a' * (256 * 1024 + 1))
                failed, data = self.call('fs_read', {'path': 'diagnostics/state.json'})
                self.check(failed and data['error'] == 'file_too_large' and 'text' not in data, 'Oversized files explicitly fail without truncation')
                state.write_bytes(b'\xc3\x28')
                self.check(self.call('fs_read', {'path': 'diagnostics/state.json'})[0], 'Strict file UTF8')
                state.unlink(); state.mkdir()
                self.check(self.call('fs_read', {'path': 'diagnostics/state.json'})[0], 'Directories rejected')
                state.rmdir()
                outside = self.fixture / 'private-secret'
                outside.write_text('private-secret')
                state.symlink_to(outside)
                self.check(self.call('fs_read', {'path': 'diagnostics/state.json'})[0], 'File symlinks rejected')
                state.unlink()
            finally:
                if state.is_symlink():
                    state.unlink()
                state.write_bytes(original)
            diagnostics = self.fixture / 'diagnostics'
            retained = self.fixture / 'retained-diagnostics'
            diagnostics.rename(retained)
            diagnostics.symlink_to(retained, target_is_directory=True)
            try:
                self.check(self.call('fs_read', {'path': 'diagnostics/state.json'})[0], 'Symbolic parent directory rejected')
            finally:
                diagnostics.unlink()
                retained.rename(diagnostics)
            other = socket.socket()
            try:
                other.bind(('127.0.0.2', self.port))
                self.check(True, 'Production listener binds only 127.0.0.1')
            finally:
                other.close()
            stalled = [socket.create_connection((self.host, self.port), timeout=3) for _ in range(20)]
            try:
                stalled[-1].settimeout(4)
                response = stalled[-1].recv(1024)
                self.check(response.startswith(b'HTTP/1.1 503'), 'Bounded worker pool rejects overload')
            finally:
                # Drain every accepted/rejected socket before the independent stop test.
                # Merely close() leaves queue cleanup racing with the next client (503).
                for connection in stalled:
                    connection.settimeout(4)
                    try:
                        connection.shutdown(socket.SHUT_WR)
                    except OSError:
                        pass
                for connection in stalled:
                    try:
                        while connection.recv(4096):
                            pass
                    except ConnectionResetError:
                        pass
                    finally:
                        connection.close()
        return self.count


def ready_line(process):
    with selectors.DefaultSelector() as sel:
        sel.register(process.stdout, selectors.EVENT_READ)
        require(bool(sel.select(timeout=12)), 'Kotlin host ready timeout')
        line = process.stdout.readline()
    require(bool(line), 'Kotlin host ended before ready')
    data = json.loads(line)
    require(data.get('ready') is True and isinstance(data.get('port'), int), 'Kotlin host ready record')
    return data


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument('--classpath')
    source.add_argument('--url')
    auth = parser.add_mutually_exclusive_group()
    auth.add_argument('--token-file', type=Path)
    auth.add_argument('--adb-token', metavar='PACKAGE')
    parser.add_argument('--adb-token-path', default='files/mcp/token')
    parser.add_argument('--adb-serial')
    args = parser.parse_args()
    if args.url and not (args.token_file or args.adb_token):
        parser.error('--url requires --token-file or --adb-token')
    process = None
    with tempfile.TemporaryDirectory(prefix='mcp-real-http-') as temp:
        fixture = Path(temp) if args.classpath else None
        try:
            if args.classpath:
                assert fixture is not None
                process = subprocess.Popen(['java', '-Xmx256m', '-cp', args.classpath, 'qa.McpHostKt', str(fixture)], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                ready = ready_line(process)
                url = f'http://127.0.0.1:{ready["port"]}'
                token = (fixture / 'mcp.token').read_text('ascii')
                require((fixture / 'mcp.token').stat().st_mode & 0o777 == 0o600, 'Host token private mode')
            else:
                url = args.url
                if args.token_file:
                    token = args.token_file.read_text('ascii')
                else:
                    require(re.fullmatch(r'[A-Za-z0-9_]+(?:\.[A-Za-z0-9_]+)+', args.adb_token), 'Literal Android package format')
                    require(re.fullmatch(r'files/[A-Za-z0-9._/-]+', args.adb_token_path) and '..' not in args.adb_token_path.split('/'), 'Literal token file path')
                    command = ['adb'] + (['-s', args.adb_serial] if args.adb_serial else [])
                    result = subprocess.run(command + ['exec-out', 'run-as', args.adb_token, 'cat', args.adb_token_path], capture_output=True, timeout=10)
                    require(result.returncode == 0, 'ADB private token read failed')
                    token = result.stdout.decode('ascii')
            require(re.fullmatch(r'[0-9a-f]{64}', token), 'Credential file must contain exactly 64 lowercase hex bytes')
            suite = Suite(url, token, fixture)
            count = suite.run()
            if process:
                assert process.stdin is not None and process.stdout is not None
                # Close an in-flight client by stopping the actual server, then prove the port is gone.
                active = socket.create_connection((suite.host, suite.port), timeout=3)
                active.settimeout(3)
                active.sendall(b'POST /mcp HTTP/1.1\r\n')
                process.stdin.write('stop\n'); process.stdin.flush()
                stopped = json.loads(process.stdout.readline())
                suite.check(stopped == {'stopped': True, 'running': False, 'boundPort': 0}, 'Actual Kotlin stop state')
                try:
                    first_byte = active.recv(1)
                    closed = first_byte == b''
                    if not closed:
                        remaining = active.recv(255)
                        first_line = (first_byte + remaining).split(b'\r\n', 1)[0]
                        raise CheckFailure('Stop client already received HTTP status ' + (first_line.split()[1].decode('ascii') if first_line.startswith(b'HTTP/1.1 ') else 'non-HTTP'))
                except ConnectionResetError:
                    closed = True
                active.close()
                suite.check(closed, 'stop closes active sockets')
                try:
                    socket.create_connection((suite.host, suite.port), timeout=1).close()
                    raise CheckFailure('Stopped port remains open')
                except OSError:
                    suite.check(True, 'Stopped listener closed')
                require(process.wait(timeout=5) == 0, 'Kotlin host clean shutdown')
                count = suite.count
            print(json.dumps({'ok': True, 'mode': 'actual-kotlin-host' if fixture else 'read-only-app', 'assertions': count, 'token': 'REDACTED'}, ensure_ascii=False))
        finally:
            if process and process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    process.kill(); process.wait()


if __name__ == '__main__':
    try:
        main()
    except CheckFailure as failure:
        print(json.dumps({'ok': False, 'failure': str(failure), 'token': 'REDACTED'}), file=sys.stderr)
        sys.exit(1)
    except Exception as failure:
        # Never print request/response bytes, paths, auth arguments, or subprocess stderr.
        import traceback
        last = traceback.extract_tb(failure.__traceback__)[-1]
        print(json.dumps({'ok': False, 'failure': type(failure).__name__, 'errno': getattr(failure, 'errno', None), 'at': last.name + ':' + str(last.lineno), 'token': 'REDACTED'}), file=sys.stderr)
        sys.exit(1)
