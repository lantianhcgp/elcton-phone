"""Transport regression checks; production HTTP remains exercised by mcp_http_selftest.py."""
import errno
import unittest
from unittest.mock import MagicMock, patch

from mcp_http_selftest import CheckFailure, Suite


class HttpShutdownRaceTest(unittest.TestCase):
    def reply(self, chunks, shutdown_error=None):
        peer = MagicMock()
        peer.__enter__.return_value = peer
        peer.shutdown.side_effect = shutdown_error
        peer.recv.side_effect = chunks
        suite = Suite('http://127.0.0.1:8766', 'private-fixture')
        with patch('mcp_http_selftest.socket.create_connection', return_value=peer):
            return suite.wire(b'GET /health HTTP/1.1\r\n\r\n')

    def test_complete_reply_survives_only_enotconn_at_shutdown(self):
        status, headers, body = self.reply([
            b'HTTP/1.1 200 OK\r\nContent-Length: 2\r\nConnection: close\r\n\r\n{}', b''
        ], OSError(errno.ENOTCONN, 'already closed'))
        self.assertEqual((200, b'{}'), (status, body))
        self.assertEqual('2', headers['content-length'])

    def test_empty_reply_after_enotconn_still_fails(self):
        with self.assertRaises(CheckFailure):
            self.reply([b''], OSError(errno.ENOTCONN, 'already closed'))

    def test_truncated_reply_after_enotconn_still_fails(self):
        with self.assertRaises(CheckFailure):
            self.reply([b'HTTP/1.1 200 OK\r\nContent-Length: 2\r\nConnection: close\r\n\r\n{', b''],
                       OSError(errno.ENOTCONN, 'already closed'))

    def test_receive_reset_after_enotconn_still_fails(self):
        with self.assertRaises(ConnectionResetError):
            self.reply([ConnectionResetError(errno.ECONNRESET, 'reset')],
                       OSError(errno.ENOTCONN, 'already closed'))

    def test_other_shutdown_errors_are_not_ignored(self):
        for code in (errno.EPIPE, errno.ECONNRESET, errno.EBADF):
            with self.subTest(code=code), self.assertRaises(OSError) as failure:
                self.reply([b''], OSError(code, 'failure'))
            self.assertEqual(code, failure.exception.errno)

    def test_invalid_utf8_and_token_echo_still_fail(self):
        for payload, error in ((b'\xff', UnicodeDecodeError), (b'private-fixture', CheckFailure)):
            with self.subTest(payload=payload), self.assertRaises(error):
                self.reply([b'HTTP/1.1 200 OK\r\nContent-Length: ' + str(len(payload)).encode() +
                            b'\r\nConnection: close\r\n\r\n' + payload, b''],
                           OSError(errno.ENOTCONN, 'already closed'))


if __name__ == '__main__':
    unittest.main()
