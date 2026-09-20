"""Validate every tracked file's bytes and parse every tracked code/data file.

Historical files are inspected without importing or executing historical code.
Passing these checks establishes syntax/container integrity, not semantic safety.
"""
from collections import Counter
import hashlib
import json
from pathlib import Path
import sqlite3
import subprocess
import zipfile


def audit_files(root: Path, paths=None):
    root = Path(root).resolve()
    if paths is None:
        raw = subprocess.check_output(['git', 'ls-files', '-z'], cwd=root)
        paths = [p for p in raw.decode('utf-8').split('\0') if p]
    rows, errors = [], []
    for name in sorted(set(paths)):
        path = root / name
        row = {'path': name, 'check': 'HASHED'}
        try:
            if not path.resolve().is_relative_to(root):
                raise ValueError('PATH_OUTSIDE_REPOSITORY')
            data = path.read_bytes()
            row.update(size=len(data), sha256=hashlib.sha256(data).hexdigest())
            suffix = path.suffix.lower()
            if suffix == '.py':
                compile(data, name, 'exec')
                row['check'] = 'PYTHON_COMPILED'
            elif suffix == '.json':
                json.loads(data)
                row['check'] = 'JSON_PARSED'
            elif suffix in {'.yml', '.yaml'}:
                import yaml
                yaml.safe_load(data)
                row['check'] = 'YAML_PARSED'
            elif suffix == '.zip':
                with zipfile.ZipFile(path) as archive:
                    bad = archive.testzip()
                    if bad is not None:
                        raise ValueError('ZIP_CRC_FAILURE:' + bad)
                row['check'] = 'ZIP_CRC_PASS'
            elif suffix == '.sqlite':
                # Inspect the committed database image without creating WAL/SHM
                # sidecars, even if its persistent journal mode is WAL.
                connection = sqlite3.connect(path.as_uri() + '?mode=ro&immutable=1', uri=True)
                try:
                    if connection.execute('PRAGMA quick_check').fetchall() != [('ok',)]:
                        raise ValueError('SQLITE_QUICK_CHECK_FAILED')
                finally:
                    connection.close()
                row['check'] = 'SQLITE_QUICK_CHECK_PASS'
        except Exception as exc:
            row['check'] = 'FAILED'
            errors.append({'path': name, 'error': type(exc).__name__ + ':' + str(exc)})
        rows.append(row)
    return {'status': 'PASS' if not errors else 'FAIL_FILE_INTEGRITY',
            'scope': 'TRACKED_REPOSITORY_FILES', 'file_count': len(rows),
            'counts': dict(Counter(row['check'] for row in rows)),
            'errors': errors, 'files': rows,
            'claim_boundary': 'BYTE_INVENTORY_AND_SYNTAX_CONTAINER_CHECKS; NOT_COMPLETE_SEMANTIC_PROOF'}
