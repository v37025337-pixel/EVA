import io
import os
import socket
import ssl
import unittest
from unittest.mock import patch

from yado_g2_openapi_readonly_executor_v1 import G2OpenAPIReadOnlyExecutorV1


class ResponseSocket:
    def __init__(self, status=200, body=b'{}', content_type='application/json'):
        self.response = (f'HTTP/1.1 {status} Response\r\nContent-Type: {content_type}\r\n'
                         f'Content-Length: {len(body)}\r\nConnection: close\r\n\r\n').encode() + body
        self.sent = []

    def sendall(self, data):
        self.sent.append(data)

    def makefile(self, *args, **kwargs):
        return io.BytesIO(self.response)

    def setsockopt(self, *args):
        pass

    def close(self):
        pass


class OpenAPIDNSPinningTests(unittest.TestCase):
    def setUp(self):
        self.plan = {'action': 'ALLOW', 'read_only_candidate': True, 'network_execute': False,
                     'method': 'GET', 'path': '/status', 'required_slots': {'query': []}}
        self.dns = [(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, '', ('93.184.216.34', 443))]

    def request(self, wire=None, *, plan=None, proxy=False, **kwargs):
        wire = wire or ResponseSocket()
        env = {'HTTPS_PROXY': 'http://127.0.0.1:8888'} if proxy else {}
        with patch.dict(os.environ, env, clear=True), \
                patch('socket.getaddrinfo', return_value=self.dns) as dns, \
                patch('socket.create_connection', return_value=wire) as connect, \
                patch.object(ssl.SSLContext, 'wrap_socket', return_value=wire) as tls:
            result = G2OpenAPIReadOnlyExecutorV1(['approved.example'], max_bytes=1024).execute(
                plan or self.plan, 'https://approved.example', **kwargs)
        return result, wire, dns, connect, tls

    def test_socket_uses_validated_ip_and_tls_uses_original_hostname(self):
        result, wire, dns, connect, tls = self.request()
        self.assertEqual(connect.call_args.args[0], ('93.184.216.34', 443))
        self.assertEqual(tls.call_args.kwargs['server_hostname'], 'approved.example')
        self.assertEqual(result['connected_ip'], '93.184.216.34')
        self.assertEqual(result['resolved_ips'], ['93.184.216.34'])
        self.assertEqual(dns.call_count, 1)
        self.assertEqual(result['body_text'], '{}')
        self.assertIn(b'Host: approved.example', b''.join(wire.sent))

    def test_proxy_environment_cannot_redirect_the_connection(self):
        result, wire, dns, connect, tls = self.request(proxy=True)
        self.assertEqual(connect.call_args.args[0], ('93.184.216.34', 443))
        self.assertNotIn(b'CONNECT ', b''.join(wire.sent))
        self.assertTrue(result['read_only_enforced'])

    def test_private_or_mixed_dns_answers_are_rejected_before_connection(self):
        private = (socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, '', ('127.0.0.1', 443))
        for answers in ([private], self.dns + [private]):
            with self.subTest(answers=answers), patch('socket.getaddrinfo', return_value=answers), \
                    patch('socket.create_connection') as connect:
                with self.assertRaisesRegex(RuntimeError, 'NON_PUBLIC_ADDRESS_REJECTED'):
                    G2OpenAPIReadOnlyExecutorV1(['approved.example']).execute(self.plan, 'https://approved.example')
                connect.assert_not_called()

    def test_redirect_is_rejected_without_following_it(self):
        with self.assertRaisesRegex(RuntimeError, 'REDIRECT_REJECTED:302'):
            self.request(ResponseSocket(status=302))

    def test_size_and_content_type_limits_survive_transport_change(self):
        with self.assertRaisesRegex(RuntimeError, 'RESPONSE_TOO_LARGE'):
            self.request(ResponseSocket(body=b'x' * 1025))
        with self.assertRaisesRegex(RuntimeError, 'CONTENT_TYPE_REJECTED'):
            self.request(ResponseSocket(body=b'html', content_type='text/html'))

    def test_head_has_no_response_body(self):
        result, wire, *_ = self.request(plan={**self.plan, 'method': 'HEAD'})
        self.assertEqual(result['response_bytes'], 0)
        self.assertNotIn('body_text', result)
        self.assertIn(b'HEAD /status HTTP/1.1', b''.join(wire.sent))

    def test_credentials_are_rejected_before_socket_use(self):
        with patch('socket.getaddrinfo', return_value=self.dns), patch('socket.create_connection') as connect:
            with self.assertRaisesRegex(RuntimeError, 'CREDENTIAL_HEADER_REJECTED'):
                G2OpenAPIReadOnlyExecutorV1(['approved.example']).execute(
                    self.plan, 'https://approved.example', headers={'Authorization': 'fixture'})
            connect.assert_not_called()


if __name__ == '__main__':
    unittest.main()
