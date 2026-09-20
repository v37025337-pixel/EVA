"""Git topology errors must never become successful history classification."""
import importlib.util
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch


def module(name):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(name + '.py'))
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


inventory = module('yado_g2_remote_branch_inventory_reconcile_v2')
lifecycle = module('yado_branch_lifecycle_audit_v1')


class BranchInventoryIntegrityTests(unittest.TestCase):
    def test_merged_branch_classification_uses_ancestry_across_namespaces(self):
        with patch.object(inventory, 'is_ancestor', return_value=True):
            for name in ('codex/repair', 'yado-repair', 'feature/fix'):
                with self.subTest(branch=name):
                    kind, _ = inventory.classify(name, 'tip', 'main', set())
                    self.assertEqual(kind, 'ABSORBED_CANONICAL_HISTORY_REF')

    def test_unmerged_codex_branch_remains_a_candidate(self):
        with patch.object(inventory, 'is_ancestor', return_value=False):
            kind, _ = inventory.classify('codex/new-mechanism', 'tip', 'main', set())
        self.assertEqual(kind, 'EXPERIENCE_CANDIDATE_REF')

    def test_unknown_divergent_namespace_remains_unclassified(self):
        with patch.object(inventory, 'is_ancestor', return_value=False):
            kind, _ = inventory.classify('unknown/new', 'tip', 'main', set())
        self.assertEqual(kind, 'UNCLASSIFIED_REF')

    def test_missing_git_object_cannot_masquerade_as_divergence(self):
        failure = subprocess.CompletedProcess([], 128, '', 'missing object')
        with patch.object(inventory, 'run', return_value=failure):
            with self.assertRaisesRegex(RuntimeError, 'ANCESTRY_CHECK_FAILED'):
                inventory.is_ancestor('missing', 'main')

    def test_failed_git_diff_cannot_hide_cognitive_changes(self):
        failure = subprocess.CompletedProcess([], 128, '', 'bad revision')
        with patch.object(lifecycle.subprocess, 'run', return_value=failure):
            with self.assertRaisesRegex(RuntimeError, 'BRANCH_DIFF_FAILED'):
                lifecycle._changed_paths('main', 'missing')


if __name__ == '__main__':
    unittest.main()
