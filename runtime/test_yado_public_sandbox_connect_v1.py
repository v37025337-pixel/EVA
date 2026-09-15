import json
import unittest
from unittest.mock import patch

import yado_public_sandbox_connect_v1 as m


class PublicSandboxTests(unittest.TestCase):
    def test_allowlist_rejects_other_hosts(self):
        with self.assertRaises(ValueError):
            m._request('https://example.com/execute')

    def test_runlet_success(self):
        def fake(url, **kwargs):
            if url.endswith('/health'):
                return {'status': 'healthy'}
            if url.endswith('/runtimes'):
                return [{'language_name': 'Python', 'language_version': '3.13'}]
            if url.endswith('/execute'):
                return {'status': 'OK', 'stdout': 'YADO_SANDBOX_OK 140\n', 'stderr': ''}
            raise AssertionError(url)
        with patch.object(m, '_request', side_effect=fake):
            r = m.probe_runlet()
        self.assertTrue(r.connected)
        self.assertTrue(r.executed)
        self.assertEqual(r.status, 'PASS_PUBLIC_SANDBOX_EXECUTION')

    def test_judge0_success(self):
        calls = []
        def fake(url, **kwargs):
            calls.append(url)
            if url.endswith('/languages'):
                return [{'id': 71, 'name': 'Python (3.8.1)'}]
            if '/submissions/?' in url:
                return {'token': 'abc'}
            if '/submissions/abc?' in url:
                return {'stdout': 'YADO_SANDBOX_OK 140\n', 'stderr': None, 'status': {'id': 3, 'description': 'Accepted'}}
            raise AssertionError(url)
        with patch.object(m, '_request', side_effect=fake):
            r = m.probe_judge0(polls=1, poll_delay=0)
        self.assertTrue(r.executed)
        self.assertEqual(r.provider, 'judge0')

    def test_fallback_to_runlet(self):
        with patch.object(m, 'probe_judge0', return_value=m.ProbeResult('judge0', m.JUDGE0, False, False, 'UNAVAILABLE')):
            with patch.object(m, 'probe_runlet', return_value=m.ProbeResult('runlet', m.RUNLET, True, True, 'PASS_PUBLIC_SANDBOX_EXECUTION')):
                report = m.run_fallback_order()
        self.assertEqual(report['status'], 'PASS_REAL_EXTERNAL_CODE_EXECUTION')
        self.assertEqual(report['selected_provider'], 'runlet')
        self.assertTrue(report['provider_fallback_used'])
        self.assertFalse(report['credentials_used'])

    def test_no_provider_is_blocked(self):
        bad1 = m.ProbeResult('judge0', m.JUDGE0, False, False, 'UNAVAILABLE')
        bad2 = m.ProbeResult('runlet', m.RUNLET, False, False, 'UNAVAILABLE')
        with patch.object(m, 'probe_judge0', return_value=bad1), patch.object(m, 'probe_runlet', return_value=bad2):
            report = m.run_fallback_order()
        self.assertEqual(report['status'], 'BLOCKED_NO_PUBLIC_SANDBOX_AVAILABLE')
        self.assertIsNone(report['selected_provider'])


if __name__ == '__main__':
    unittest.main()
