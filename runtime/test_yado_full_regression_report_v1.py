"""Interrupted regression attempts must invalidate a previous PASS immediately."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest


RUNNER = Path(__file__).with_name('yado_full_regression_v1.py')
LAUNCHER = r'''
import importlib.util, pathlib, subprocess, sys, time, unittest
runner_path, directory, stage = sys.argv[1:]
spec = importlib.util.spec_from_file_location('regression_runner', runner_path)
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)
root = pathlib.Path(directory)
runner.ROOT = root
runner.source_digests = lambda: {}
def block():
    (root / 'entered.txt').write_text('entered:' + stage)
    time.sleep(30)
    raise AssertionError('The parent should terminate this blocked attempt')
def commit(*args, **kwargs):
    if stage == 'git':
        block()
    if stage == 'git_error':
        raise subprocess.CalledProcessError(128, ['git', 'rev-parse', 'HEAD'])
    return 'a' * 40
runner.subprocess.check_output = commit
class Example(unittest.TestCase):
    def runTest(self):
        if stage == 'execution':
            block()
def collect():
    if stage == 'collection':
        block()
    return unittest.TestSuite([Example()]), {'fixture': 1}
runner.collect = collect
sys.argv = [str(runner_path), '--manifest', str(root / 'manifest.json'), '--output', str(root / 'report.json')]
raise SystemExit(runner.main())
'''


class FullRegressionReportTests(unittest.TestCase):
    def fixture(self, root):
        (root / 'manifest.json').write_text(json.dumps({'identity_digest': 'fixture-identity'}))
        (root / 'report.json').write_text(json.dumps({'status': 'PASS', 'tested_commit': 'old-commit'}))

    def command(self, root, stage):
        return [sys.executable, '-c', LAUNCHER, str(RUNNER), str(root), stage]

    def test_termination_before_git_collection_or_test_completion_cannot_leave_pass(self):
        for stage in ('git', 'collection', 'execution'):
            with self.subTest(stage=stage), tempfile.TemporaryDirectory(prefix='yado-interrupted-regression-') as directory:
                root = Path(directory)
                self.fixture(root)
                process = subprocess.Popen(self.command(root, stage), stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                try:
                    deadline = time.monotonic() + 10
                    while not (root / 'entered.txt').exists():
                        if process.poll() is not None:
                            stdout, stderr = process.communicate()
                            self.fail(f'Runner exited before the controlled interruption: {stdout}\n{stderr}')
                        if time.monotonic() >= deadline:
                            self.fail('Runner did not reach the controlled interruption')
                        time.sleep(0.01)
                    process.terminate()
                    process.communicate(timeout=5)
                    self.assertNotEqual(process.returncode, 0)
                    report = json.loads((root / 'report.json').read_text())
                    self.assertEqual(report['status'], 'WITHHOLD')
                    self.assertNotEqual(report.get('tested_commit'), 'old-commit')
                finally:
                    if process.poll() is None:
                        process.kill()
                        process.communicate(timeout=5)

    def test_git_identification_failure_is_saved_in_current_withhold_report(self):
        with tempfile.TemporaryDirectory(prefix='yado-regression-git-error-') as directory:
            root = Path(directory)
            self.fixture(root)
            result = subprocess.run(self.command(root, 'git_error'), capture_output=True, text=True, timeout=10)
            self.assertNotEqual(result.returncode, 0)
            report = json.loads((root / 'report.json').read_text())
            self.assertEqual(report['status'], 'WITHHOLD')
            self.assertIn('CalledProcessError', report['error'])
            self.assertNotEqual(report.get('tested_commit'), 'old-commit')

    def test_completed_successful_run_can_replace_withhold_with_pass(self):
        with tempfile.TemporaryDirectory(prefix='yado-completed-regression-') as directory:
            root = Path(directory)
            self.fixture(root)
            result = subprocess.run(self.command(root, 'complete'), capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stderr)
            report = json.loads((root / 'report.json').read_text())
            self.assertEqual(report['status'], 'PASS')
            self.assertEqual(report['tested_commit'], 'a' * 40)
            self.assertEqual(report['tests_run'], 1)
            self.assertEqual(report['tests_run'], report['expected_tests'])
            self.assertTrue(report['source_unchanged'])


if __name__ == '__main__':
    unittest.main()
