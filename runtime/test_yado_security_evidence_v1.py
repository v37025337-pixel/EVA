"""Security PASS requires complete source scans and bound dependency evidence."""
from copy import deepcopy
from contextlib import redirect_stdout
from datetime import datetime, timedelta, timezone
import ast
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


AUDITOR = Path(__file__).with_name('yado_security_audit_v1.py')
REQUIREMENTS = ('runtime/yado_rc8_v36/requirements-github.txt', 'successor/requirements.txt')


class SecurityEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='yado-security-evidence-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for directory in ('runtime/yado_rc8_v36', 'successor', 'canonical', '.github/workflows', 'audits'):
            (self.root / directory).mkdir(parents=True, exist_ok=True)
        shutil.copyfile(AUDITOR, self.root / 'runtime/yado_security_audit_v1.py')
        self.source = self.root / 'runtime/yado_unified_core_v1.py'
        self.source.write_text('VALUE = 1\n')
        self.write('canonical/yado-unified-core-v1.json', {'active_runtime_sources': ['runtime/yado_unified_core_v1.py']})
        self.write('.github/yado-active-workflow-allowlist-v1.json', {
            'active_workflows': ['audit.yml'], 'write_authorized_workflows': [], 'max_active_workflow_count': 1,
        })
        (self.root / '.github/workflows/audit.yml').write_text(
            'name: fixture\non:\n  workflow_dispatch:\npermissions:\n  contents: read\n'
            'jobs:\n  audit:\n    runs-on: ubuntu-latest\n    steps:\n      - run: true\n')
        (self.root / REQUIREMENTS[0]).write_text('alpha>=1,<2\nbeta>=2,<3\n')
        (self.root / REQUIREMENTS[1]).write_text('alpha==1.5\nbeta==2.5\n')
        self.git('init', '-q')
        self.git('add', 'runtime/yado_unified_core_v1.py', *REQUIREMENTS, 'canonical', '.github')
        self.git('-c', 'user.name=Audit Fixture', '-c', 'user.email=audit@example.invalid', 'commit', '-qm', 'fixture')
        self.report = {'dependencies': [
            {'name': 'alpha', 'version': '1.5', 'vulns': []},
            {'name': 'beta', 'version': '2.5', 'vulns': []},
        ]}
        now = datetime.now(timezone.utc).isoformat()
        self.proof = {
            'schema': 'yado.pip_audit_evidence.v1',
            'requirements': {p: hashlib.sha256((self.root / p).read_bytes()).hexdigest() for p in REQUIREMENTS},
            'git_commit': self.git('rev-parse', 'HEAD').strip(),
            'tool': {'name': 'pip-audit', 'version': '2.9.0'},
            'command': {'requirements': list(REQUIREMENTS), 'format': 'json'},
            'returncode': 0, 'started_at': now, 'finished_at': now,
        }

    def git(self, *args):
        return subprocess.check_output(['git', *args], cwd=self.root, text=True, stderr=subprocess.DEVNULL)

    def write(self, path, value):
        (self.root / path).write_text(json.dumps(value) + '\n')

    def audit(self, report=None, proof=None):
        self.write('audits/yado-pip-audit-v1.json', self.report if report is None else report)
        bound = deepcopy(self.proof if proof is None else proof)
        bound['report_sha256'] = hashlib.sha256((self.root / 'audits/yado-pip-audit-v1.json').read_bytes()).hexdigest()
        self.write('audits/yado-pip-audit-v1-evidence.json', bound)
        process = subprocess.run([sys.executable, 'runtime/yado_security_audit_v1.py'], cwd=self.root,
                                 capture_output=True, text=True, timeout=30)
        return process, json.loads((self.root / 'audits/yado-security-audit-v1-report.json').read_text())

    def assert_withheld(self, process, report):
        self.assertNotEqual(process.returncode, 0)
        self.assertNotEqual(report['status'], 'PASS')

    def test_complete_current_bound_evidence_passes(self):
        process, report = self.audit()
        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertEqual(report['status'], 'PASS')
        self.assertEqual(report['active_runtime_files_scanned'], 1)

    def test_invalid_dependency_reports_never_pass(self):
        cases = ({}, {'error': 'audit incomplete'}, {'dependencies': []},
                 {'dependencies': [{'name': 'unrelated', 'version': '1.0', 'vulns': []}]},
                 {'dependencies': [{'name': 'alpha', 'version': '1.5', 'vulns': [], 'skip_reason': 'unavailable'}]},
                 {'dependencies': [{'name': 'alpha', 'version': '2.5', 'vulns': []}, self.report['dependencies'][1]]},
                 {'dependencies': [{'name': 'alpha', 'version': '1.5'}, self.report['dependencies'][1]]})
        for value in cases:
            with self.subTest(report=value):
                self.assert_withheld(*self.audit(report=value))

    def test_unbound_stale_wrong_commit_failed_or_partial_proofs_never_pass(self):
        expired = (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()
        changes = ({'schema': 'unknown'}, {'git_commit': '0' * 40}, {'returncode': 2},
                   {'returncode': False}, {'requirements': {}}, {'command': {'requirements': [REQUIREMENTS[0]], 'format': 'json'}},
                   {'started_at': expired, 'finished_at': expired}, {'tool': {'name': 'other-tool', 'version': '1.0'}})
        for change in changes:
            with self.subTest(change=change):
                proof = {**self.proof, **change}
                self.assert_withheld(*self.audit(proof=proof))

    def test_changed_requirements_invalidate_previous_evidence(self):
        (self.root / REQUIREMENTS[1]).write_text('alpha==1.6\nbeta==2.5\n')
        self.assert_withheld(*self.audit())

    def test_missing_proof_and_changed_raw_report_never_pass(self):
        for missing in (True, False):
            with self.subTest(missing=missing):
                self.audit()
                path = self.root / 'audits/yado-pip-audit-v1-evidence.json'
                if missing:
                    path.unlink()
                else:
                    self.write('audits/yado-pip-audit-v1.json', {'dependencies': []})
                process = subprocess.run([sys.executable, 'runtime/yado_security_audit_v1.py'], cwd=self.root,
                                         capture_output=True, text=True, timeout=30)
                report = json.loads((self.root / 'audits/yado-security-audit-v1-report.json').read_text())
                self.assert_withheld(process, report)

    def test_missing_and_invalid_active_sources_fail_with_actual_scan_count(self):
        for value in (None, 'def invalid(:\n'):
            with self.subTest(source=value):
                if value is None:
                    self.source.unlink()
                else:
                    self.source.write_text(value)
                process, report = self.audit()
                self.assert_withheld(process, report)
                self.assertEqual(report['active_runtime_files_scanned'], 0)

    def test_git_failure_never_passes(self):
        shutil.rmtree(self.root / '.git')
        self.assert_withheld(*self.audit())

    def reviewed_exec(self):
        self.source.write_text("exec('VALUE = 1', {'__builtins__': {}})\n")
        test = self.root / 'runtime/test_fixture_boundary.py'
        test.write_text('def test_boundary():\n    assert True\n')
        node = next(node for node in ast.walk(ast.parse(self.source.read_text())) if isinstance(node, ast.Call))
        row = {
            'path': 'runtime/yado_unified_core_v1.py',
            'source_sha256': hashlib.sha256(self.source.read_bytes()).hexdigest(),
            'call': 'exec', 'call_identity': f'exec:{node.lineno}:{node.col_offset}',
            'ast_call_sha256': hashlib.sha256(ast.dump(node, include_attributes=False).encode()).hexdigest(),
            'boundary': 'Fixture executes a fixed local constant; no supplied code is accepted.',
            'test_references': ['runtime/test_fixture_boundary.py::test_boundary'],
        }
        policy = {'schema': 'yado.dynamic_execution_review.v1', 'reviews': [row]}
        self.write('.github/yado-dynamic-execution-review-v1.json', policy)
        return policy

    def test_exact_reviewed_site_passes_without_general_sandbox_claim(self):
        self.reviewed_exec()
        process, report = self.audit()
        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertEqual(report['dynamic_execution_review']['reviewed_count'], 1)
        self.assertIs(report['dynamic_execution_review']['general_python_sandbox'], False)
        self.assertTrue(any(row['call'] == 'exec' for row in report['active_runtime_risk_calls']))

    def test_changed_source_and_new_call_cannot_reuse_review(self):
        for new_call in (False, True):
            with self.subTest(new_call=new_call):
                policy = self.reviewed_exec()
                if new_call:
                    self.source.write_text(self.source.read_text() + "exec('OTHER = 2', {'__builtins__': {}})\n")
                    # Even a refreshed file hash must not authorize an additional call.
                    policy['reviews'][0]['source_sha256'] = hashlib.sha256(self.source.read_bytes()).hexdigest()
                    self.write('.github/yado-dynamic-execution-review-v1.json', policy)
                else:
                    self.source.write_text(self.source.read_text() + 'ADDED = 1\n')
                process, report = self.audit()
                self.assert_withheld(process, report)
                self.assertGreater(report['dynamic_execution_review']['unreviewed_count'], 0)

    def test_invalid_review_binding_policy_or_test_reference_fails(self):
        for field, value in (('ast_call_sha256', '0' * 64), ('call_identity', 'exec:99:0'),
                             ('boundary', ''), ('test_references', ['runtime/test_fixture_boundary.py::test_missing'])):
            with self.subTest(field=field):
                policy = self.reviewed_exec()
                policy['reviews'][0][field] = value
                self.write('.github/yado-dynamic-execution-review-v1.json', policy)
                self.assert_withheld(*self.audit())
        self.write('.github/yado-dynamic-execution-review-v1.json', {'reviews': []})
        self.assert_withheld(*self.audit())

    def test_known_vulnerability_never_passes_even_with_bound_zero_exit(self):
        report = deepcopy(self.report)
        report['dependencies'][0]['vulns'] = [{'id': 'FIXTURE-001', 'fix_versions': ['1.6']}]
        process, result = self.audit(report=report)
        self.assert_withheld(process, result)
        self.assertEqual(result['dependency_vulnerability_count'], 1)

    def test_collector_binds_both_requirements_and_preserves_tool_failure(self):
        spec = importlib.util.spec_from_file_location('security_evidence_under_test', AUDITOR)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        for exit_code in (0, 2):
            with self.subTest(exit_code=exit_code):
                raw = json.dumps(self.report).encode()
                result = subprocess.CompletedProcess([], exit_code, raw, b'')
                with patch.object(module, 'ROOT', self.root), \
                     patch.object(module, 'PIP_REPORT', self.root / 'audits/yado-pip-audit-v1.json'), \
                     patch.object(module, 'PIP_EVIDENCE', self.root / 'audits/yado-pip-audit-v1-evidence.json'), \
                     patch.object(module, 'current_commit', return_value=self.proof['git_commit']), \
                     patch.object(module.importlib.metadata, 'version', return_value='2.9.0'), \
                     patch.object(module.subprocess, 'run', return_value=result) as invoke, redirect_stdout(io.StringIO()):
                    module.collect_dependency_evidence()
                self.assertEqual(invoke.call_args.args[0], [sys.executable, '-m', 'pip_audit', '--strict',
                    '-r', REQUIREMENTS[0], '-r', REQUIREMENTS[1], '-f', 'json'])
                proof = json.loads((self.root / 'audits/yado-pip-audit-v1-evidence.json').read_text())
                self.assertEqual(proof['returncode'], exit_code)
                self.assertEqual(proof['report_sha256'], hashlib.sha256(raw).hexdigest())
                self.assertEqual(proof['requirements'], self.proof['requirements'])
                process = subprocess.run([sys.executable, 'runtime/yado_security_audit_v1.py'], cwd=self.root,
                                         capture_output=True, text=True, timeout=30)
                report = json.loads((self.root / 'audits/yado-security-audit-v1-report.json').read_text())
                if exit_code:
                    self.assert_withheld(process, report)
                else:
                    self.assertEqual(report['status'], 'PASS')


if __name__ == '__main__':
    unittest.main()
