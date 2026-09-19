"""Focused offline checks: declared branch scopes and actual Git persistence."""
import os
import re
from pathlib import Path
import subprocess
import tempfile
import unittest
import yaml

REPO = Path(__file__).resolve().parents[2]
WORKFLOWS = REPO / '.github/workflows'
SCOPES = {
    'yado-experience-router-self-repair-v2': 'codex/yado-experience-router-self-repair-v2-20260917',
    'yado-external-dev-multigoal-campaign-v1': 'codex/yado-self-directed-dev-campaign-v1-20260916',
    'yado-external-dev-self-development-v1': 'codex/yado-external-dev-self-development-v1-20260916',
    'yado-residual-goal-continuation-v2': 'codex/yado-residual-goal-continuation-v2-20260916',
}
BRANCH = 'yado-native-self-rewrite-v4-fresh-experience-20260918'


def read(name):
    return yaml.safe_load((WORKFLOWS / (name + '.yml')).read_text())


class WriteScopeTests(unittest.TestCase):
    def test_main_enabled_report_writers_do_not_rebase_unverified_sources(self):
        for path in WORKFLOWS.glob('*.y*ml'):
            workflow = yaml.safe_load(path.read_text())
            trigger = workflow.get('on', workflow.get(True, {}))
            branches = (trigger.get('push') or {}).get('branches', [])
            for job in workflow['jobs'].values():
                for step in job.get('steps', []):
                    run = step.get('run', '')
                    reachable = 'HEAD:main' in run or ('GITHUB_REF_NAME' in run and ('main' in branches or 'workflow_dispatch' in trigger))
                    if 'git push' in run and reachable:
                        with self.subTest(workflow=path.name):
                            self.assertIsNone(re.search(r'git\s+(?:pull[^\n]*--rebase|rebase)\b', run))
        workflow = read('yado-g2-post-module-full-integrity-v1')
        job = next(iter(workflow['jobs'].values()))
        run = next(s['run'] for s in job['steps'] if 'git push' in s.get('run', ''))
        self.assertIn('test "$(git rev-parse HEAD)" = "$GITHUB_SHA"', run)
        self.assertIn('test "$(git rev-parse FETCH_HEAD)" = "$GITHUB_SHA"', run)

    def test_four_shadow_writers_allow_declared_branch_and_deny_main_dispatch(self):
        for name, branch in SCOPES.items():
            with self.subTest(name=name):
                workflow = read(name)
                job = next(iter(workflow['jobs'].values()))
                step = next(s for s in job['steps'] if 'git push' in s.get('run', ''))
                self.assertEqual(step['if'], "github.ref == 'refs/heads/" + branch + "'")
                self.assertNotEqual('refs/heads/main', 'refs/heads/' + branch)
                self.assertIn('git push origin HEAD:' + branch, step['run'])
                self.assertNotIn('GITHUB_REF_NAME', step['run'])
                self.assertIn('workflow_dispatch', workflow.get('on', workflow.get(True)))
                self.assertTrue(any('upload-artifact' in s.get('uses', '') for s in job['steps']))

    def test_v4_needs_exact_checked_sha_and_keeps_readonly_verifier(self):
        workflow = read('yado-native-self-rewrite-v4-fresh-experience')
        self.assertEqual(workflow['permissions']['contents'], 'read')
        job = workflow['jobs']['persist-v4-evidence']
        self.assertEqual(job['needs'], 'native-self-rewrite-v4')
        checkout = next(s for s in job['steps'] if s.get('uses', '').startswith('actions/checkout'))
        self.assertEqual(checkout['with']['ref'], '${{ github.sha }}')
        run = next(s['run'] for s in job['steps'] if 'git push' in s.get('run', ''))
        self.assertNotIn('--force', run)
        self.assertNotIn('rebase', run)

    def test_v4_actual_persistence_accepts_unchanged_branch_and_rejects_moved_branch(self):
        job = read('yado-native-self-rewrite-v4-fresh-experience')['jobs']['persist-v4-evidence']
        run = next(s['run'] for s in job['steps'] if 'git push' in s.get('run', ''))
        for moved in (False, True):
            with self.subTest(moved=moved), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                def git(*args, cwd=None):
                    return subprocess.check_output(['git', *args], cwd=cwd or root, stderr=subprocess.DEVNULL, text=True).strip()
                git('init', '--bare', str(root / 'remote.git'))
                git('init', str(root / 'work'))
                work = root / 'work'
                git('config', 'user.name', 'Audit', cwd=work)
                git('config', 'user.email', 'audit@example.invalid', cwd=work)
                git('checkout', '-b', BRANCH, cwd=work)
                candidate = work / 'candidates/autonomous'
                candidate.mkdir(parents=True)
                receipt = candidate / 'yado-native-self-rewrite-v4-fresh-experience.json'
                source = candidate / 'yado_bounded_autonomous_learning_runtime_candidate_v4.py'
                receipt.write_text('{}\n')
                source.write_text('value = 1\n')
                git('add', '.', cwd=work)
                git('commit', '-m', 'tested', cwd=work)
                tested = git('rev-parse', 'HEAD', cwd=work)
                git('remote', 'add', 'origin', str(root / 'remote.git'), cwd=work)
                git('push', 'origin', 'HEAD:' + BRANCH, cwd=work)
                if moved:
                    (work / 'other.txt').write_text('new untested revision\n')
                    git('add', 'other.txt', cwd=work)
                    git('commit', '-m', 'moved', cwd=work)
                    git('push', 'origin', 'HEAD:' + BRANCH, cwd=work)
                    git('checkout', '--detach', tested, cwd=work)
                receipt.write_text('{"regenerated": true}\n')
                result = subprocess.run(['bash', '-e', '-c', run], cwd=work,
                                        env={**os.environ, 'GITHUB_SHA': tested}, capture_output=True, text=True)
                remote = git('--git-dir=' + str(root / 'remote.git'), 'rev-parse', 'refs/heads/' + BRANCH)
                if moved:
                    self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
                    self.assertEqual(git('rev-parse', 'HEAD', cwd=work), tested)
                    self.assertNotEqual(remote, tested)
                else:
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                    self.assertEqual(git('rev-parse', 'HEAD^', cwd=work), tested)
                    self.assertEqual(remote, git('rev-parse', 'HEAD', cwd=work))


if __name__ == '__main__':
    unittest.main(verbosity=2)
