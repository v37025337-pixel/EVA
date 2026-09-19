from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

from yado_runtime_self_rewrite_admission_v4 import (
    ROOT, TARGET, CANDIDATE, CONTRACT, CORE, MAINTENANCE_STATE, OUT, PROMOTION,
    V4_RECEIPT, analyze, analyze_committed, run,
)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def write_json(root, relative, value, digest_field=None):
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    if digest_field:
        value[digest_field] = digest({k: v for k, v in value.items() if k != digest_field})
    path.write_text(json.dumps(value))


def fixture(root, *, maintenance=True):
    for relative in (CANDIDATE, V4_RECEIPT, PROMOTION, OUT):
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes((ROOT / relative).read_bytes())
    target = root / TARGET
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes((root / CANDIDATE).read_bytes() + (b'\n# verified maintenance fixture\n' if maintenance else b''))
    if not maintenance:
        return
    dependency = root / 'runtime/maintenance_dependency.py'
    dependency.write_text('VALUE = 1\n')
    sources = {str(TARGET): sha(target), 'runtime/maintenance_dependency.py': sha(dependency)}
    identity = 'YADO_UNIFIED_KERNEL_REPAIR_V1'
    core = {'implementation_id': identity,
            'runtime_integrity_manifest': {'sources': sources, 'manifest_digest': digest(sources)}}
    write_json(root, CORE, core, 'core_digest')
    head = {'implementation_id': identity, 'unified_core': {
        'core_digest': core['core_digest'], 'runtime_integrity_manifest_digest': digest(sources)}}
    write_json(root, 'canonical/yado-main-head-g2.json', head, 'canonical_head_digest')
    write_json(root, 'architecture/evolution-ledger.json',
               {'current_head_digest': head['canonical_head_digest']}, 'ledger_digest')
    write_json(root, CONTRACT, {'implementation_id': identity, 'execution_branch': 'main',
                               'runtime_lineage': {'generation': 'V4_MAINTENANCE_R1',
                                                   'active_sha256': sha(target),
                                                   'candidate_sha256': sha(root / CANDIDATE)}})


class RuntimeSelfRewriteAdmissionV4Tests(unittest.TestCase):
    def test_probe_handles_parent_v4_maintenance_or_unrelated_shadow_state(self):
        result = analyze()
        recognized = {'PARENT_RUNTIME_PENDING_SHADOW_APPLY',
                      'V4_CANDIDATE_APPLIED_IN_ISOLATED_WORKTREE', MAINTENANCE_STATE}
        if result['runtime_state'] in recognized:
            self.assertEqual(result['status'], 'PASS_SHADOW_RUNTIME_SELF_REWRITE_ADMISSION_V4_PROBE')
            self.assertTrue(result['checks']['runtime_state_recognized'])
            self.assertTrue(result['checks']['candidate_sha_matches_v4_receipt'])
            self.assertTrue(result['checks']['candidate_ranking_matches_v4_receipt'])
        else:
            self.assertEqual(result['runtime_state'], 'UNEXPECTED_RUNTIME_STATE')
            self.assertEqual(result['status'], 'WITHHOLD_RUNTIME_SELF_REWRITE_ADMISSION_V4_PROBE')
            self.assertFalse(result['checks']['runtime_state_recognized'])

    def test_probe_preserves_target_and_historical_admission_receipt(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            fixture(root)
            before = {path: sha(root / path) for path in (TARGET, CANDIDATE, OUT, V4_RECEIPT, PROMOTION)}
            result = run(root)
            self.assertFalse(result['checks']['probe_mutated_runtime'])
            self.assertEqual(before, {path: sha(root / path) for path in before})

    def test_historical_v4_still_requires_exact_binding(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            fixture(root, maintenance=False)
            result = analyze(root)
            self.assertEqual(result['runtime_state'], 'V4_CANDIDATE_APPLIED_IN_ISOLATED_WORKTREE')
            self.assertTrue(result['checks']['target_matches_candidate_when_shadow_applied'])
            self.assertEqual(result['next_required_capability'], 'PHYSICAL_RUNTIME_PROMOTION_V4_REQUIRES_SEPARATE_GATE')

    def test_verified_maintenance_is_recognized_without_claiming_historical_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            fixture(root)
            result = analyze(root)
            self.assertEqual(result['runtime_state'], MAINTENANCE_STATE)
            self.assertEqual(result['status'], 'PASS_SHADOW_RUNTIME_SELF_REWRITE_ADMISSION_V4_PROBE')
            self.assertNotEqual(result['target_sha256'], result['candidate_sha256'])
            self.assertEqual(result['active_kernel_identity']['controller_sha256'], sha(root / TARGET))
            self.assertEqual(result['next_required_capability'], 'NEXT_GENERATION_FROM_VERIFIED_MAINTENANCE_RUNTIME')

    def test_unknown_learner_edit_without_maintenance_contract_is_withheld(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            fixture(root, maintenance=False)
            with (root / TARGET).open('a') as stream:
                stream.write('\n# unknown edit\n')
            result = analyze(root)
            self.assertEqual(result['runtime_state'], 'UNEXPECTED_RUNTIME_STATE')
            self.assertEqual(result['status'], 'WITHHOLD_RUNTIME_SELF_REWRITE_ADMISSION_V4_PROBE')

    def test_maintenance_requires_intact_canonical_binding_and_every_manifest_source(self):
        mutations = {
            'learner': (TARGET, None),
            'other_runtime': (Path('runtime/maintenance_dependency.py'), None),
            'core': (CORE, 'implementation_id'),
            'head': (Path('canonical/yado-main-head-g2.json'), 'implementation_id'),
            'ledger': (Path('architecture/evolution-ledger.json'), 'current_head_digest'),
            'execution_branch': (CONTRACT, 'execution_branch'),
        }
        for name, (relative, key) in mutations.items():
            with self.subTest(name=name), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                fixture(root)
                if key is None:
                    with (root / relative).open('a') as stream:
                        stream.write('\n# unbound change\n')
                else:
                    value = json.loads((root / relative).read_text())
                    value[key] = 'unbound'
                    write_json(root, relative, value)
                result = analyze(root)
                self.assertEqual(result['runtime_state'], 'UNEXPECTED_RUNTIME_STATE')
                self.assertEqual(result['status'], 'WITHHOLD_RUNTIME_SELF_REWRITE_ADMISSION_V4_PROBE')

    def test_maintenance_does_not_excuse_tampered_historical_candidate_or_receipt(self):
        for relative, field in ((CANDIDATE, None), (V4_RECEIPT, 'candidate_sha256'),
                                (PROMOTION, 'candidate_sha256')):
            with self.subTest(relative=relative), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                fixture(root)
                if field is None:
                    with (root / relative).open('a') as stream:
                        stream.write('\nraise AssertionError("UNVERIFIED_CANDIDATE_EXECUTED")\n')
                else:
                    value = json.loads((root / relative).read_text())
                    value[field] = '0' * 64
                    write_json(root, relative, value)
                result = analyze(root)
                self.assertEqual(result['status'], 'WITHHOLD_RUNTIME_SELF_REWRITE_ADMISSION_V4_PROBE')

    def test_committed_probe_uses_pinned_git_data_despite_unbound_worktree_files(self):
        git_dir = subprocess.check_output(['git', 'rev-parse', '--absolute-git-dir'], cwd=ROOT, text=True).strip()
        expected = analyze_committed(ROOT)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / '.git').write_text('gitdir: ' + git_dir + '\n')
            fixture(root)
            with (root / TARGET).open('a') as stream:
                stream.write('\n# unbound worktree edit\n')
            result = analyze_committed(root)
            self.assertEqual(result['repository_view'], 'COMMITTED_HEAD')
            self.assertEqual(result['tested_commit'], expected['tested_commit'])
            self.assertEqual(result['target_sha256'], expected['target_sha256'])
            self.assertEqual(result['runtime_state'], expected['runtime_state'])
            self.assertNotEqual(result['target_sha256'], sha(root / TARGET))


if __name__ == '__main__':
    unittest.main()
