import copy
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


API_SOURCE = Path(__file__).resolve().parents[1] / 'api/index.py'


def digest(value):
    raw = json.dumps(value, sort_keys=True, separators=(',', ':')).encode()
    return hashlib.sha256(raw).hexdigest()


def sealed(value, key):
    return {**value, key: digest(value)}


class APIReadinessTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        spec = importlib.util.spec_from_file_location('isolated_readiness_api', API_SOURCE)
        self.api = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.api)
        self.api.ROOT = self.root
        self.api.CANONICAL = self.root / 'canonical/yado-unified-core-v1.json'
        self.api.AUDIT = self.root / 'audits/yado-full-kernel-audit-v1-report.json'
        self.write('api/index.py', API_SOURCE.read_bytes())
        self.write('runtime/example.py', b'VALUE = 1\n')
        self.sources = {'runtime/example.py': hashlib.sha256(b'VALUE = 1\n').hexdigest()}
        self.core = sealed({'canonical_active': True, 'generation': 'G2',
                            'active_runtime_sources': ['runtime/example.py'],
                            'runtime_integrity_manifest': {'algorithm': 'sha256', 'sources': self.sources,
                                                           'manifest_digest': digest(self.sources)}}, 'core_digest')
        self.head = sealed({'generation_id': 'G2'}, 'canonical_head_digest')
        self.ledger = {'current_head': 'G2', 'current_head_digest': self.head['canonical_head_digest']}
        self.write_json('canonical/yado-unified-core-v1.json', self.core)
        self.write_json('canonical/yado-main-head-g2.json', self.head)
        self.write_json('architecture/evolution-ledger.json', self.ledger)
        self.report = {'schema': 'yado.full_kernel_audit.v1', 'status': 'PASS', 'findings': [],
                       'audited_commit': 'a' * 40, 'canonical': {'head_digest': self.head['canonical_head_digest']},
                       'source_sha256': {p.relative_to(self.root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                                         for p in self.root.rglob('*') if p.is_file()}}
        self.write_report()

    def write(self, relative, data):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)

    def write_json(self, relative, data):
        self.write(relative, (json.dumps(data, sort_keys=True) + '\n').encode())

    def write_report(self):
        self.write_json('audits/yado-full-kernel-audit-v1-report.json', self.report)

    def assert_not_ready(self):
        result = self.api._load_status()
        self.assertEqual(result['status'], 'not_ready')
        self.assertFalse(result['full_kernel_audit_pass'])
        return result

    def test_current_verified_bytes_are_ready_without_git_metadata(self):
        result = self.api._load_status()
        self.assertEqual(result['status'], 'ok')
        self.assertTrue(result['full_kernel_audit_pass'])
        self.assertEqual(result['audit_freshness'], 'SOURCE_SHA256_MATCH')
        self.assertEqual(result['generation'], 'G2')
        self.assertFalse((self.root / '.git').exists())

    def test_missing_corrupt_or_inactive_canonical_is_not_ready(self):
        for content in (None, b'{', b'[]'):
            with self.subTest(content=content):
                if content is None:
                    self.api.CANONICAL.unlink(missing_ok=True)
                else:
                    self.api.CANONICAL.write_bytes(content)
                self.assert_not_ready()
        inactive = {k: v for k, v in self.core.items() if k != 'core_digest'}
        inactive['canonical_active'] = False
        self.write_json('canonical/yado-unified-core-v1.json', sealed(inactive, 'core_digest'))
        self.assert_not_ready()

    def test_core_head_and_source_digest_drift_are_not_ready(self):
        originals = {p: (self.root / p).read_bytes() for p in (
            'canonical/yado-unified-core-v1.json', 'canonical/yado-main-head-g2.json', 'runtime/example.py')}
        mutations = [('canonical/yado-unified-core-v1.json', {**self.core, 'generation': 'G3'}),
                     ('canonical/yado-main-head-g2.json', {**self.head, 'generation_id': 'G3'}),
                     ('runtime/example.py', None)]
        for path, value in mutations:
            with self.subTest(path=path):
                if value is None:
                    self.write(path, b'VALUE = 2\n')
                else:
                    self.write_json(path, value)
                self.assert_not_ready()
                self.write(path, originals[path])

    def test_head_and_ledger_must_agree(self):
        self.write_json('architecture/evolution-ledger.json', {**self.ledger, 'current_head_digest': '0' * 64})
        self.assert_not_ready()

    def test_old_summary_cannot_supply_a_pass(self):
        self.api.AUDIT.unlink()
        self.write('audits/yado-full-kernel-audit-v1-summary.md', b'Status: **PASS**\n')
        self.assert_not_ready()

    def test_audit_requires_success_and_current_complete_source_binding(self):
        for field, value in (('status', 'FAIL_AUDIT'), ('source_sha256', {}), ('source_sha256', None),
                             ('canonical', {'head_digest': '0' * 64})):
            with self.subTest(field=field, value=value):
                original = copy.deepcopy(self.report)
                self.report[field] = value
                self.write_report()
                self.assert_not_ready()
                self.report = original
        self.report['source_sha256'].pop('api/index.py')
        self.write_report()
        self.assert_not_ready()

    def test_changed_api_or_additional_audited_source_makes_report_stale(self):
        self.write('api/index.py', b'# changed API\n')
        self.assert_not_ready()
        self.write('api/index.py', API_SOURCE.read_bytes())
        self.write('successor/example.py', b'VALUE = 1\n')
        self.report['source_sha256']['successor/example.py'] = hashlib.sha256(b'VALUE = 1\n').hexdigest()
        self.write_report()
        self.assertEqual(self.api._load_status()['status'], 'ok')
        self.write('successor/example.py', b'VALUE = 2\n')
        self.assert_not_ready()

    def test_manifest_and_report_paths_cannot_escape_root(self):
        for field in ('manifest', 'report'):
            with self.subTest(field=field):
                if field == 'manifest':
                    value = {k: v for k, v in self.core.items() if k != 'core_digest'}
                    sources = {'../outside.py': '0' * 64}
                    value['runtime_integrity_manifest'] = {'sources': sources, 'manifest_digest': digest(sources)}
                    self.write_json('canonical/yado-unified-core-v1.json', sealed(value, 'core_digest'))
                else:
                    self.write_json('canonical/yado-unified-core-v1.json', self.core)
                    self.report['source_sha256']['../outside.py'] = '0' * 64
                    self.write_report()
                self.assert_not_ready()

    def test_http_readiness_returns_503_and_positive_returns_200(self):
        handler = object.__new__(self.api.handler)
        handler.path = '/health'
        for expected in (200, 503):
            with self.subTest(expected=expected):
                if expected == 503:
                    self.api.CANONICAL.unlink()
                handler.wfile = io.BytesIO()
                with patch.object(handler, 'send_response') as response, \
                        patch.object(handler, 'send_header'), patch.object(handler, 'end_headers'):
                    handler.do_GET()
                response.assert_called_once_with(expected)
                self.assertEqual(json.loads(handler.wfile.getvalue())['status'],
                                 'ok' if expected == 200 else 'not_ready')


if __name__ == '__main__':
    unittest.main()
