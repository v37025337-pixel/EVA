import importlib.util
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
import zipfile


spec = importlib.util.spec_from_file_location('file_audit', Path(__file__).with_name('yado_repository_file_audit_v1.py'))
file_audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(file_audit)


class RepositoryFileAuditTests(unittest.TestCase):
    def test_wal_mode_database_check_creates_no_sidecar_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / 'history.sqlite'
            connection = sqlite3.connect(path)
            connection.execute('PRAGMA journal_mode=WAL')
            connection.execute('CREATE TABLE history(value TEXT)')
            connection.commit()
            connection.close()
            before = {p.name: p.read_bytes() for p in root.iterdir()}
            result = file_audit.audit_files(root, ['history.sqlite'])
            self.assertEqual(result['status'], 'PASS')
            self.assertEqual({p.name: p.read_bytes() for p in root.iterdir()}, before)

    def test_broken_code_outside_runtime_is_reported_without_execution(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            files = ['successor/broken.py', 'candidates/broken.py', 'experiments/broken.py']
            for name in files:
                path = root / name
                path.parent.mkdir()
                path.write_text('def broken(:\n')
            result = file_audit.audit_files(root, files)
            self.assertEqual(result['status'], 'FAIL_FILE_INTEGRITY')
            self.assertEqual({x['path'] for x in result['errors']}, set(files))

    def test_parsing_does_not_execute_candidate(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'candidate.py').write_text('raise RuntimeError("must not execute")\n')
            result = file_audit.audit_files(root, ['candidate.py'])
            self.assertEqual(result['status'], 'PASS')
            self.assertEqual(result['counts']['PYTHON_COMPILED'], 1)

    def test_invalid_json_and_corrupt_archive_fail(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'bad.json').write_text('{')
            (root / 'bad.zip').write_bytes(b'not a zip archive')
            result = file_audit.audit_files(root, ['bad.json', 'bad.zip'])
            self.assertEqual(len(result['errors']), 2)

    def test_valid_file_and_archive_bytes_are_hashed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'manifest.json').write_text(json.dumps({'generation': 'G0'}))
            with zipfile.ZipFile(root / 'history.zip', 'w') as archive:
                archive.writestr('original.txt', 'preserved history')
            result = file_audit.audit_files(root, ['manifest.json', 'history.zip'])
            self.assertEqual(result['status'], 'PASS')
            self.assertEqual(result['file_count'], 2)
            self.assertTrue(all(len(row['sha256']) == 64 for row in result['files']))


if __name__ == '__main__':
    unittest.main()
