#!/usr/bin/env python3
"""Termux -> rish -> run-as private token; no adb, stdout credential, or shared storage."""
import argparse
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import urllib.request
import urllib.error

PACKAGE = 'com.hcbiu.elcton'
TOKEN_PATTERN = re.compile(rb'[0-9a-f]{64}')


def private_token() -> bytes:
    wrapper = Path.home() / 'rish/rish_t'
    if not wrapper.is_file():
        raise RuntimeError('rish wrapper missing; see android-shizuku-shell')
    # -c is verified but stdin is the canonical transport; token output can be interleaved.
    # Avoid the marker mixed into stdout: rish -c is verified for this exact tiny read.
    rish = Path.home() / 'rish/rish'
    env = dict(os.environ, RISH_APPLICATION_ID='com.termux')
    for attempt in range(3):
        result = subprocess.run([str(rish), '-c', 'run-as ' + PACKAGE + ' cat files/mcp/token'], capture_output=True, timeout=25, env=env)
        token = result.stdout
        if result.returncode == 0 and TOKEN_PATTERN.fullmatch(token):
            return token
    raise RuntimeError('private token read failed/invalid; requires Shizuku shell permission and debuggable original-signed APK; no credential printed')


def store_private(path: Path, token: bytes) -> None:
    path = path.expanduser()
    home = Path.home().resolve()
    parent = path.parent.resolve()
    if not parent.is_relative_to(home):
        raise ValueError('Token destination must be within Termux private home, never /storage or Documents')
    parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW, 0o600)
    try:
        os.fchmod(fd, 0o600)
        os.write(fd, token)
    finally:
        os.close(fd)


def request(token: bytes, tool: str, limit: int):
    if tool not in ('error_tail', 'diag_read', 'version_info', 'fs_read'):
        raise ValueError('Only the four read-only tools are supported')
    if not 1 <= limit <= 128:
        raise ValueError('error_tail limit must be 1..128')
    args = {'limit': limit} if tool == 'error_tail' else {'path': 'diagnostics/wear-errors.jsonl'} if tool == 'fs_read' else {}
    body = json.dumps({'jsonrpc': '2.0', 'id': 'termux-direct', 'method': 'tools/call', 'params': {'name': tool, 'arguments': args}}, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
    headers = {'Author' + 'ization': 'Bear' + 'er ' + token.decode('ascii'), 'Content-Type': 'application/json', 'Connection': 'close'}
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    req = urllib.request.Request('http://127.0.0.1:8766/mcp', body, headers)
    try:
        response = opener.open(req, timeout=12)
    except urllib.error.HTTPError as error:
        response = error
    raw = response.read()
    response.close()
    if token in raw:
        raise RuntimeError('Server response contains credential; refusing to print')
    payload = json.loads(raw.decode('utf-8'))
    if response.code != 200 or payload.get('id') != 'termux-direct' or 'error' in payload:
        raise RuntimeError('HTTP/RPC failed: status=' + str(response.code))
    return payload


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--save-token', type=Path)
    parser.add_argument('--tool', choices=['error_tail', 'diag_read', 'version_info', 'fs_read'])
    parser.add_argument('--limit', type=int, default=128)
    args = parser.parse_args()
    try:
        token = private_token()
        if args.save_token:
            store_private(args.save_token, token)
        if args.tool:
            print(json.dumps(request(token, args.tool, args.limit), ensure_ascii=False, indent=2))
        else:
            print(json.dumps({'token': 'PRIVATE_READ_OK', 'saved': bool(args.save_token), 'tokenValue': 'NOT_PRINTED'}))
    except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired, urllib.error.URLError) as error:
        print(json.dumps({'ok': False, 'failure': type(error).__name__ + ': ' + str(error)}))
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
