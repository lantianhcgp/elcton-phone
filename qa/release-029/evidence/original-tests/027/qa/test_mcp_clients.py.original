#!/usr/bin/env python3
"""Real Kotlin HTTP client regression, plus a SYNTHETIC EOF-closing TCP relay.

Run: python -B qa/test_mcp_clients.py --classpath <production-host.jar:real-json.jar>
Discovery: set MCP_HTTP_TEST_CLASSPATH to the same genuine classpath. No Android mocks.
The relay models one possible forwarding policy, NOT adb behavior or an Android result.
"""
import argparse
import json
import os
from pathlib import Path
import selectors
import socket
import subprocess
import sys
import tempfile
import threading
import time
import unittest

from mcp_http_selftest import CheckFailure, Suite, encode, ready_line


class EofClosingRelay:
    """Forward real production bytes; close both sides on client EOF.

    A 50ms upstream-read gate makes the EOF policy deterministic, avoiding a race
    where the real server responds before the fixture observes client shutdown.
    This is a transport fixture, never an HTTP/Android service replacement.
    """
    def __init__(self, upstream_port):
        self.upstream_port = upstream_port
        self.listener = socket.socket()
        self.listener.bind(('127.0.0.1', 0))
        self.listener.listen(32)
        self.listener.settimeout(0.1)
        self.port = self.listener.getsockname()[1]
        self.stopped = threading.Event()
        self.eof_closures = 0
        self.lock = threading.Lock()
        self.peers = set()
        self.workers = []
        self.acceptor = threading.Thread(target=self.accept, daemon=True)
        self.acceptor.start()

    def accept(self):
        while not self.stopped.is_set():
            try:
                client, _ = self.listener.accept()
            except socket.timeout:
                continue
            except OSError:
                break
            worker = threading.Thread(target=self.forward, args=(client,), daemon=True)
            self.workers.append(worker)
            worker.start()

    def forward(self, client):
        upstream = None
        try:
            upstream = socket.create_connection(('127.0.0.1', self.upstream_port), timeout=5)
            client.settimeout(5)
            with self.lock:
                self.peers.update((client, upstream))
            started = time.monotonic()
            with selectors.DefaultSelector() as sel:
                sel.register(client, selectors.EVENT_READ, upstream)
                upstream_registered = False
                while not self.stopped.is_set():
                    if not upstream_registered and time.monotonic() - started >= 0.05:
                        sel.register(upstream, selectors.EVENT_READ, client)
                        upstream_registered = True
                    for key, _ in sel.select(timeout=0.01):
                        peer = key.fileobj
                        assert isinstance(peer, socket.socket)
                        data = peer.recv(65536)
                        if not data:
                            if key.fileobj is client:
                                with self.lock:
                                    self.eof_closures += 1
                            return
                        key.data.sendall(data)
        except OSError:
            pass  # Fixture teardown can interrupt outstanding real sockets.
        finally:
            for peer in (client, upstream):
                if peer is not None:
                    with self.lock:
                        self.peers.discard(peer)
                    try:
                        peer.shutdown(socket.SHUT_RDWR)
                    except OSError:
                        pass
                    peer.close()

    def close(self):
        self.stopped.set()
        self.listener.close()
        with self.lock:
            peers = list(self.peers)
        for peer in peers:
            try:
                peer.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
        self.acceptor.join(timeout=2)
        for worker in self.workers:
            worker.join(timeout=2)
        if self.acceptor.is_alive() or any(worker.is_alive() for worker in self.workers):
            raise AssertionError('Transport fixture left a worker running')


class McpRealClientTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.classpath = os.environ.get('MCP_HTTP_TEST_CLASSPATH')
        if not cls.classpath:
            raise unittest.SkipTest('Real Kotlin dependency required: run qa/test_mcp_clients.py --classpath; NOT Android verification')
        cls.temp = tempfile.TemporaryDirectory(prefix='mcp-client-regression-')
        cls.fixture = Path(cls.temp.name)
        cls.process = subprocess.Popen(
            ['java', '-Xmx256m', '-cp', cls.classpath, 'qa.McpHostKt', str(cls.fixture)],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            cls.port = ready_line(cls.process)['port']
            cls.token = (cls.fixture / 'mcp.token').read_text('ascii')
        except Exception:
            cls.process.terminate()
            cls.process.wait(timeout=5)
            cls.temp.cleanup()
            raise

    @classmethod
    def tearDownClass(cls):
        try:
            assert cls.process.stdin is not None and cls.process.stdout is not None
            cls.process.stdin.write('stop\n')
            cls.process.stdin.flush()
            stopped = json.loads(cls.process.stdout.readline())
            if stopped != {'stopped': True, 'running': False, 'boundPort': 0}:
                raise AssertionError('Real host stop receipt differs')
            if cls.process.wait(timeout=5) != 0:
                raise AssertionError('Real host exited unsuccessfully')
            try:
                socket.create_connection(('127.0.0.1', cls.port), timeout=1).close()
            except OSError:
                pass
            else:
                raise AssertionError('Real host listener remains open')
        finally:
            if cls.process.poll() is None:
                cls.process.terminate()
                cls.process.wait(timeout=5)
            for stream in (cls.process.stdin, cls.process.stdout, cls.process.stderr):
                if stream is not None:
                    stream.close()
            cls.temp.cleanup()

    def test_direct_controls_with_and_without_write_eof_use_real_server(self):
        suite = Suite(f'http://127.0.0.1:{self.port}', self.token)
        for shutdown in (False, True):
            with self.subTest(shutdown=shutdown):
                status, _, body = suite.wire(b'GET /health HTTP/1.1\r\nHost: localhost\r\n\r\n', shutdown=shutdown)
                self.assertEqual(200, status)
                self.assertEqual({'ok': True}, json.loads(body))

    def test_content_length_post_survives_eof_closing_relay(self):
        relay = EofClosingRelay(self.port)
        try:
            suite = Suite(f'http://127.0.0.1:{relay.port}', self.token)
            try:
                status, _, body = suite.request('POST', '/mcp', {'jsonrpc': '2.0', 'id': '中文🙂', 'method': 'ping'})
            except CheckFailure as failure:
                self.fail('Normal framed POST used write EOF and lost HTTP response in SYNTHETIC relay: ' + str(failure))
            self.assertEqual(200, status)
            self.assertEqual('中文🙂', json.loads(body)['id'])
            self.assertEqual(0, relay.eof_closures, 'Normal HTTP must not signal write EOF before receiving response')
        finally:
            relay.close()

    def test_url_mode_reports_unsupported_write_eof_without_dropping_other_checks(self):
        relay = EofClosingRelay(self.port)
        try:
            result = subprocess.run(
                [sys.executable, '-B', str(Path(__file__).with_name('mcp_http_selftest.py')),
                 '--url', f'http://127.0.0.1:{relay.port}', '--token-file', str(self.fixture / 'mcp.token')],
                capture_output=True, text=True, timeout=90)
            self.assertEqual(0, result.returncode, 'SYNTHETIC forwarding regression failed: ' + result.stderr)
            report = json.loads(result.stdout)
            self.assertEqual({'urllib', 'curl'}, set(report['clients']))
            self.assertFalse(report['all_raw_checks_passed'], 'Do not mislabel unsupported EOF checks as PASS')
            self.assertEqual('unsupported', report['write_eof_transport']['status'])
            self.assertEqual(['Truncated body rejected (requires client write EOF)'], report['write_eof_transport']['excluded_checks'])
            self.assertGreaterEqual(relay.eof_closures, 1, 'Capability probe really sent client EOF')
            self.assertFalse(self.token in result.stdout + result.stderr, 'Credential leaked (REDACTED)')
        finally:
            relay.close()

    def test_url_mode_really_runs_curl_and_urllib(self):
        result = subprocess.run(
            [sys.executable, '-B', str(Path(__file__).with_name('mcp_http_selftest.py')),
             '--url', f'http://127.0.0.1:{self.port}', '--token-file', str(self.fixture / 'mcp.token')],
            capture_output=True, text=True, timeout=60)
        self.assertEqual(0, result.returncode, 'Real read-only URL selftest failed: ' + result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual({'urllib', 'curl'}, set(report.get('clients', [])), 'Real client regressions must be mandatory, not merely raw Socket/health')
        self.assertFalse(self.token in result.stdout + result.stderr, 'Credential leaked (REDACTED)')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--classpath', required=True)
    args, unittest_args = parser.parse_known_args()
    os.environ['MCP_HTTP_TEST_CLASSPATH'] = args.classpath
    print('Scope: local JVM production Kotlin + real org.json; SYNTHETIC host callbacks/relay; NOT Android or adb verification', flush=True)
    unittest.main(argv=[sys.argv[0], '-v', *unittest_args])
