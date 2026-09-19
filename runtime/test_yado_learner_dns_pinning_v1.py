import hashlib
import io
import os
import socket
import ssl
import unittest
from unittest.mock import patch

import yado_bounded_autonomous_learning_v1 as learner


class WireSocket:
    def __init__(self, status=200, body=b'<p>Python documentation</p>', content_type='text/html'):
        self.response = (f'HTTP/1.1 {status} Response\r\nContent-Type: {content_type}\r\n'
                         f'Content-Length: {len(body)}\r\nConnection: close\r\n\r\n').encode() + body
        self.sent = []
        self.closed = False

    def sendall(self, data):
        self.sent.append(data)

    def makefile(self, *args, **kwargs):
        return io.BytesIO(self.response)

    def setsockopt(self, *args):
        pass

    def close(self):
        self.closed = True


class LearnerDNSPinningTests(unittest.TestCase):
    URL = 'https://docs.python.org/3/library/ast.html?view=public'
    IP = '93.184.216.34'

    def request(self, wire=None, *, proxy=False):
        wire = wire or WireSocket()
        hostname_lookups, connections = [], []

        def resolve(host, port, *args, **kwargs):
            if host == 'docs.python.org':
                hostname_lookups.append(host)
                address = self.IP if len(hostname_lookups) == 1 else '127.0.0.1'
            else:
                address = host
            return [(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, '', (address, port or 443))]

        def connect(address, *args, **kwargs):
            connections.append(resolve(address[0], address[1])[0][4])
            return wire

        env = {'HTTPS_PROXY': 'http://127.0.0.1:8888'} if proxy else {}
        with patch.dict(os.environ, env, clear=True), patch('socket.getaddrinfo', side_effect=resolve), \
                patch('socket.create_connection', side_effect=connect), \
                patch.object(ssl.SSLContext, 'wrap_socket', return_value=wire) as tls:
            result = learner.fetch_public_readonly(self.URL)
        return result, wire, hostname_lookups, connections, tls

    def test_dns_change_cannot_move_the_socket_to_loopback(self):
        result, wire, lookups, connections, tls = self.request()
        self.assertEqual(connections, [(self.IP, 443)])
        self.assertEqual(lookups, ['docs.python.org'])
        self.assertEqual(result['connected_ip'], self.IP)
        self.assertEqual(result['resolved_ips'], [self.IP])
        self.assertEqual(tls.call_args.kwargs['server_hostname'], 'docs.python.org')
        request = b''.join(wire.sent)
        self.assertIn(b'Host: docs.python.org', request)
        self.assertIn(b'GET /3/library/ast.html?view=public HTTP/1.1', request)

    def test_proxy_environment_is_ignored(self):
        result, wire, lookups, connections, tls = self.request(proxy=True)
        self.assertEqual(connections, [(self.IP, 443)])
        self.assertNotIn(b'CONNECT ', b''.join(wire.sent))
        self.assertFalse(result['credentials_used'])

    def test_unicode_body_hash_and_receipt_fields_are_preserved(self):
        body = '<p>Python — проверенный текст</p>'.encode()
        result, *_ = self.request(WireSocket(body=body))
        self.assertEqual(result['url'], self.URL)
        self.assertEqual(result['body'], body.decode())
        self.assertEqual(result['sha256'], hashlib.sha256(body).hexdigest())
        self.assertEqual(result['bytes'], len(body))
        self.assertEqual(result['content_type'], 'text/html')
        self.assertTrue(result['network_executed'])
        self.assertTrue(result['read_only'])
        self.assertFalse(result['redirects_followed'])
        self.assertGreaterEqual(result['latency_ms'], 0)

    def test_http_errors_and_redirects_keep_fail_closed_errors(self):
        for status in (302, 404, 503):
            wire = WireSocket(status=status)
            with self.subTest(status=status), self.assertRaisesRegex(RuntimeError, 'HTTP_ERROR:' + str(status)):
                self.request(wire)
            self.assertTrue(wire.closed)
            self.assertEqual(b''.join(wire.sent).count(b'GET '), 1)

    def test_body_limit_and_content_type_are_enforced(self):
        with patch.object(learner, 'MAX_BYTES', 32):
            with self.assertRaisesRegex(RuntimeError, 'RESPONSE_TOO_LARGE'):
                self.request(WireSocket(body=b'x' * 33))
        with self.assertRaisesRegex(RuntimeError, 'CONTENT_TYPE_REJECTED'):
            self.request(WireSocket(content_type='application/octet-stream'))
        result, *_ = self.request(WireSocket(body=b'{}', content_type='application/ld+json'))
        self.assertEqual(result['body'], '{}')

    def test_initial_private_or_mixed_dns_is_rejected(self):
        public = (socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, '', (self.IP, 443))
        private = (socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, '', ('127.0.0.1', 443))
        for answers in ([private], [public, private]):
            with self.subTest(answers=answers), patch('socket.getaddrinfo', return_value=answers), \
                    patch('socket.create_connection') as connect:
                with self.assertRaisesRegex(RuntimeError, 'NON_PUBLIC_ADDRESS_REJECTED'):
                    learner.fetch_public_readonly(self.URL)
                connect.assert_not_called()

    def test_url_authority_restrictions_survive_transport_change(self):
        for url in ('http://docs.python.org/', 'https://user:fixture@docs.python.org/',
                    'https://docs.python.org:8443/', 'https://example.org/', 'https://docs.python.org/#fragment'):
            with self.subTest(url=url), patch('socket.create_connection') as connect:
                with self.assertRaises(RuntimeError):
                    learner.fetch_public_readonly(url)
                connect.assert_not_called()

    def test_tls_failure_cannot_become_a_success_receipt(self):
        answer = [(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, '', (self.IP, 443))]
        wire = WireSocket()
        with patch('socket.getaddrinfo', return_value=answer), patch('socket.create_connection', return_value=wire), \
                patch.object(ssl.SSLContext, 'wrap_socket', side_effect=ssl.SSLCertVerificationError('untrusted certificate')):
            with self.assertRaisesRegex(RuntimeError, 'NETWORK_ERROR:'):
                learner.fetch_public_readonly(self.URL)
        self.assertTrue(wire.closed)
        self.assertEqual(wire.sent, [])


if __name__ == '__main__':
    unittest.main()
