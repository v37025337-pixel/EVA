import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('source_audit', Path(__file__).with_name('yado_current_manifest_source_audit_v1.py'))
source_audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(source_audit)


class CurrentManifestSourceAuditTests(unittest.TestCase):
    def test_current_pointer_detects_source_drift_without_changing_historical_hash(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'canonical').mkdir()
            source = root / 'module.py'
            source.write_text('value = 1\n')
            digest = hashlib.sha256(source.read_bytes()).hexdigest()
            manifest = root / 'canonical/manifest.json'
            manifest.write_text(json.dumps({'current': digest, 'historical': 'old-admission'}))
            args = (root, [('manifest.json', ('current',), 'code')], {'code': 'module.py'})
            self.assertEqual(source_audit.audit_current_sources(*args)['status'], 'PASS')
            source.write_text('value = 2\n')
            result = source_audit.audit_current_sources(*args)
            self.assertEqual(result['status'], 'FAIL_CURRENT_SOURCE_BINDINGS')
            self.assertEqual(result['errors'][0]['source'], 'module.py')
            self.assertEqual(json.loads(manifest.read_text())['historical'], 'old-admission')


if __name__ == '__main__':
    unittest.main()
