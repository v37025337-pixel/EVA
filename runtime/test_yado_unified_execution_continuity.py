import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import yado_active_kernel_contract_v1 as contract
import yado_bounded_autonomous_learning_v1 as learner
import yado_repository_reconciliation_v1 as reconcile


class UnifiedExecutionContinuityTests(unittest.TestCase):
    def identity_fixture(self, root):
        path = root / contract.LEARNER
        path.parent.mkdir(parents=True)
        path.write_text('print("admitted learner")\n')
        source_sha = hashlib.sha256(path.read_bytes()).hexdigest()
        sources = {contract.LEARNER: source_sha}
        core = {"implementation_id": "repair", "runtime_integrity_manifest": {"sources": sources, "manifest_digest": contract.digest(sources)}}
        core["core_digest"] = contract.digest(core)
        head = {"implementation_id": "repair", "unified_core": {"core_digest": core["core_digest"], "runtime_integrity_manifest_digest": contract.digest(sources)}}
        head["canonical_head_digest"] = contract.digest(head)
        ledger = {"current_head_digest": head["canonical_head_digest"]}
        ledger["ledger_digest"] = contract.digest(ledger)
        architecture = {"implementation_id": "repair", "execution_branch": "main", "runtime_lineage": {"active_sha256": source_sha}}
        for name, value in [("canonical/yado-unified-core-v1.json", core), ("canonical/yado-main-head-g2.json", head), ("architecture/evolution-ledger.json", ledger), ("architecture/yado-unified-architecture-v2.json", architecture)]:
            p = root / name; p.parent.mkdir(parents=True, exist_ok=True); p.write_text(json.dumps(value))
        return source_sha

    def test_actual_executable_must_match_canonical(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source_sha = self.identity_fixture(root)
            self.assertEqual(contract.active_kernel_identity(root)["controller_sha256"], source_sha)
            (root / contract.LEARNER).write_text('print("old learner")\n')
            with self.assertRaisesRegex(ValueError, "IMPLEMENTATION_MISMATCH"):
                contract.active_kernel_identity(root)

    def test_empty_html_cannot_be_reported_as_learning(self):
        with tempfile.TemporaryDirectory() as temp, patch.object(learner, 'REPO', Path(temp)), patch.object(learner, 'active_kernel_identity', return_value={}), patch.object(learner, 'fetch_public_readonly', return_value={'body': '<html>OK</html>', 'content_type': 'text/html'}):
            with self.assertRaisesRegex(RuntimeError, 'NO_USEFUL_EXTERNAL_EVIDENCE'):
                learner.main()
            self.assertFalse((Path(temp) / 'candidates/autonomous/yado-bounded-autonomous-learning-v1.json').exists())

    def test_git_failure_is_unavailable_not_empty_success(self):
        with patch.object(reconcile, 'git', side_effect=RuntimeError('git unavailable')):
            result = reconcile.branch_inventory({})
        self.assertFalse(result['available'])

    def test_strict_reconciliation_rejects_unavailable_topology(self):
        with tempfile.TemporaryDirectory() as temp, patch.object(reconcile, 'OUT', Path(temp) / 'report.json'), patch.object(reconcile, 'branch_inventory', return_value={'available': False, 'blocking_ahead_branches': []}), patch('builtins.print'):
            with self.assertRaises(SystemExit):
                reconcile.run(strict=True)
            result = json.loads((Path(temp) / 'report.json').read_text())
            self.assertFalse(result['checks']['remote_branch_divergence_policy_satisfied'])

    def test_no_runtime_is_copied_to_experience_feed(self):
        from yado_persist_learning_feed_v1 import copy_verified_outputs, EXPERIENCE, RECEIPT
        with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
            source, destination = Path(a), Path(b)
            self.identity_fixture(source)
            identity = contract.active_kernel_identity(source)
            experience = {'evidence_text': 'Проверенный внешний факт', 'status': 'PASS_SHADOW_BOUNDED_AUTONOMOUS_EXTERNAL_LEARNING_V1', 'execution_identity': identity}
            experience['experience_digest'] = learner.digest(experience)
            candidate = 'candidates/autonomous/yado_learned_recall_test.py'
            p = source / candidate; p.parent.mkdir(parents=True); p.write_text('FACTS = ["evidence"]\n')
            receipt = {'status': experience['status'], 'experience_digest': experience['experience_digest'], 'generated_capability': {'path': candidate, 'fact_count': 1, 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()}}
            receipt['receipt_sha256'] = learner.digest(receipt)
            for name, value in [(EXPERIENCE, experience), (RECEIPT, receipt)]:
                p = source / name; p.parent.mkdir(parents=True, exist_ok=True); p.write_text(json.dumps(value))
            self.assertEqual(set(copy_verified_outputs(source, destination)), {EXPERIENCE, RECEIPT, candidate})
            self.assertFalse((destination / 'runtime').exists())
            receipt['generated_capability']['path'] = 'runtime/evil.py'
            (source / RECEIPT).write_text(json.dumps(receipt))
            with self.assertRaisesRegex(ValueError, 'PATH_NOT_ALLOWED'):
                copy_verified_outputs(source, destination)


if __name__ == '__main__':
    unittest.main()
