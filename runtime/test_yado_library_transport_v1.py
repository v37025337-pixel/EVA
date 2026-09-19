import hashlib
import io
import os
import socket
import ssl
import unittest
from unittest.mock import patch

import yado_autonomous_external_library_discovery_v5 as library


class ResponseSocket:
    def __init__(self, status=200, body=b'{}', headers=None):
        fields = {'Content-Type': 'application/octet-stream', 'Content-Length': str(len(body)),
                  'Connection': 'close', **(headers or {})}
        self.response = (f'HTTP/1.1 {status} Response\r\n' +
                         ''.join(f'{key}: {value}\r\n' for key, value in fields.items()) + '\r\n').encode() + body
        self.sent = []
        self.closed = False

    def sendall(self, data):
        self.sent.append(data)

    def makefile(self, *args, **kwargs):
        if len(self.sent) > 1:
            return io.BytesIO(b'HTTP/1.1 200 OK\r\nContent-Length: 2\r\nConnection: close\r\n\r\n{}')
        return io.BytesIO(self.response)

    def setsockopt(self, *args):
        pass

    def close(self):
        self.closed = True


class LibraryTransportTests(unittest.TestCase):
    IP = '93.184.216.34'

    def request(self, *, wire=None, url='https://pypi.org/pypi/networkx/json', limit=1000, proxy=False, catalog=False):
        wire = wire or ResponseSocket()
        connections, lookups = [], []

        def resolve(host, port, *args, **kwargs):
            if host in ('pypi.org', 'files.pythonhosted.org'):
                lookups.append(host)
                address = self.IP if len(lookups) == 1 else '127.0.0.1'
            else:
                address = host
            return [(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, '', (address, port or 443))]

        def connect(address, *args, **kwargs):
            connections.append(resolve(address[0], address[1])[0][4])
            return wire

        with patch.dict(os.environ, {'HTTPS_PROXY': 'http://127.0.0.1:8888'} if proxy else {}, clear=True), \
                patch('socket.getaddrinfo', side_effect=resolve), \
                patch('socket.create_connection', side_effect=connect), \
                patch.object(ssl.SSLContext, 'wrap_socket', return_value=wire) as tls:
            if catalog:
                from yado_autonomous_open_catalog_discovery_v6 import discover_from_open_catalog
                result = discover_from_open_catalog()
            else:
                result = library.guarded_fetch(url, accept='application/octet-stream', max_bytes=limit)
        return result, connections, lookups, tls

    def test_redirect_is_rejected_before_any_second_request(self):
        wire = ResponseSocket(status=302, headers={'Location': 'https://outside.invalid/unexpected'})
        with self.assertRaises(RuntimeError):
            self.request(wire=wire)
        self.assertEqual(b''.join(wire.sent).count(b'GET '), 1)
        self.assertTrue(wire.closed)

    def test_validated_ip_is_pinned_while_tls_retains_hostname(self):
        (raw, proof), connections, lookups, tls = self.request()
        self.assertEqual(connections, [(self.IP, 443)])
        self.assertEqual(lookups, ['pypi.org'])
        self.assertEqual(tls.call_args.kwargs['server_hostname'], 'pypi.org')
        self.assertEqual(proof['connected_ip'], self.IP)
        self.assertEqual(raw, b'{}')

    def test_environment_proxy_cannot_change_peer(self):
        (_, proof), connections, *_ = self.request(proxy=True)
        self.assertEqual(connections, [(self.IP, 443)])
        self.assertFalse(proof['proxy_used'])

    def test_binary_wheel_proof_and_hash_are_preserved(self):
        body = b'PK\x03\x04\xff\x00wheel'
        url = 'https://files.pythonhosted.org/packages/example.whl'
        (raw, proof), *_ = self.request(wire=ResponseSocket(body=body), url=url)
        self.assertEqual(raw, body)
        self.assertEqual(proof['requested_url'], url)
        self.assertEqual(proof['final_url'], url)
        self.assertEqual(proof['host'], 'files.pythonhosted.org')
        self.assertEqual(proof['sha256'], hashlib.sha256(body).hexdigest())
        self.assertEqual(proof['bytes'], len(body))
        self.assertEqual(proof['http_status'], 200)
        self.assertTrue(proof['read_only'])

    def test_initial_private_dns_and_unsafe_authority_fail_before_connect(self):
        private = [(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, '', ('127.0.0.1', 443))]
        with patch('socket.getaddrinfo', return_value=private), patch('socket.create_connection') as connect:
            for url in ('https://pypi.org/', 'https://pypi.org:8443/', 'http://pypi.org/',
                        'https://user:fixture@pypi.org/', 'https://outside.invalid/'):
                with self.subTest(url=url), self.assertRaises((RuntimeError, ValueError)):
                    library.guarded_fetch(url, accept='application/json', max_bytes=100)
            connect.assert_not_called()

    def test_body_budget_and_non_200_status_fail_closed(self):
        with self.assertRaisesRegex(RuntimeError, 'payload exceeds cap'):
            self.request(wire=ResponseSocket(body=b'a' * 33), limit=32)
        with self.assertRaisesRegex(RuntimeError, 'HTTP 404'):
            self.request(wire=ResponseSocket(status=404))
        for limit in (0, -1, 1.5, True, library.MAX_WHEEL_BYTES + 1):
            with self.subTest(limit=limit), patch('socket.create_connection') as connect:
                with self.assertRaisesRegex(ValueError, 'BYTE_BUDGET'):
                    library.guarded_fetch('https://pypi.org/', accept='application/json', max_bytes=limit)
                connect.assert_not_called()

    def test_v6_catalog_budget_reaches_the_pinned_transport_without_widening_package_budget(self):
        (names, evidence), connections, *_ = self.request(
            wire=ResponseSocket(body=b'{"projects":[{"name":"html"}]}'), catalog=True)
        self.assertEqual(names, ['html'])
        self.assertEqual(connections, [(self.IP, 443)])
        self.assertEqual(evidence['source']['requested_url'], 'https://pypi.org/simple/')
        self.assertFalse(evidence['source']['redirects_followed'])
        with patch('socket.create_connection') as connect:
            for url, accept, limit in (
                ('https://pypi.org/simple/', 'application/vnd.pypi.simple.v1+json', 100_000_001),
                ('https://pypi.org/simple/networkx/', 'application/vnd.pypi.simple.v1+json', 100_000_000),
                ('https://pypi.org/simple/', 'application/octet-stream', 100_000_000),
                ('https://files.pythonhosted.org/packages/test.whl', 'application/octet-stream', 100_000_000),
            ):
                with self.subTest(url=url, accept=accept, limit=limit), self.assertRaisesRegex(ValueError, 'BYTE_BUDGET'):
                    library.guarded_fetch(url, accept=accept, max_bytes=limit)
            connect.assert_not_called()


if __name__ == '__main__':
    unittest.main()
