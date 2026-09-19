"""Admission must authorize exact records and preserve inherited capabilities."""
import copy
from dataclasses import replace
from pathlib import Path
import unittest

from yado_unified_causal_evolution_architecture_v1 import (
    CausalClaim,
    GenerationRecord,
    PromotionPolicy,
    UnifiedCausalEvolutionArchitecture,
    self_test,
)


class ArchitectureAdmissionIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.arch = UnifiedCausalEvolutionArchitecture()
        self.parent = GenerationRecord(
            generation_id='parent', parent_generation_id=None, lineage_id='lineage',
            artifact_digest='parent-artifact', capability_scores={'logic': 0.5, 'integrity': 1.0},
            protected_capabilities=('integrity',),
            hard_constraints={name: True for name in PromotionPolicy().required_constraints},
            change_set=(), evidence_ids=('parent-evidence',),
            metadata={'provenance': {'source': 'verified-parent'}},
        )
        self.arch.register_root(self.parent)
        self.candidate = replace(
            self.parent, generation_id='child', parent_generation_id='parent',
            artifact_digest='child-artifact', capability_scores={'logic': 0.6, 'integrity': 1.0},
            hard_constraints=dict(self.parent.hard_constraints),
            change_set=('logic-improvement',), evidence_ids=('fresh', 'ablation'),
            causal_claims=(CausalClaim(
                claim_id='claim', deficit_id='logic-deficit', mechanism_id='logic-improvement',
                evidence_ids=('fresh', 'ablation'), expected_effects={'logic': 0.1}, status='VERIFIED',
            ),),
            domain_experiences=('MATHEMATICS:fresh', 'PROGRAMMING:fresh'),
            metadata={'provenance': {'source': 'verified-child'}},
        )

    def test_exact_evaluated_candidate_promotes_and_legacy_self_test_passes(self):
        decision = self.arch.evaluate_candidate(self.candidate)
        self.assertEqual(decision.action, 'PROMOTE_GENERATION')
        self.arch.promote(copy.deepcopy(self.candidate), copy.deepcopy(decision))
        self.assertEqual(self.arch.developmental_head, 'child')
        self.assertEqual(self.arch.snapshot()['generation_count'], 2)
        self.assertEqual(self_test()['status'], 'PASS_UNIFIED_CAUSAL_EVOLUTION_ARCHITECTURE_V1_SELF_TEST')

    def test_same_id_substituted_artifact_cannot_use_previous_approval(self):
        decision = self.arch.evaluate_candidate(self.candidate)
        before = self.arch.snapshot()
        altered = replace(self.candidate, artifact_digest='unevaluated-artifact')
        with self.assertRaises(ValueError):
            self.arch.promote(altered, decision)
        self.assertEqual(self.arch.snapshot(), before)

    def test_nested_candidate_mutation_after_evaluation_invalidates_approval(self):
        for field in ('capability_scores', 'hard_constraints', 'causal_claims', 'metadata'):
            with self.subTest(field=field):
                candidate = copy.deepcopy(self.candidate)
                decision = self.arch.evaluate_candidate(candidate)
                if field == 'capability_scores':
                    candidate.capability_scores['integrity'] = 0.0
                elif field == 'hard_constraints':
                    candidate.hard_constraints['regression_pass'] = False
                elif field == 'causal_claims':
                    candidate.causal_claims[0].expected_effects['logic'] = -1.0
                else:
                    candidate.metadata['provenance']['source'] = 'unevaluated'
                before = self.arch.snapshot()
                with self.assertRaises(ValueError):
                    self.arch.promote(candidate, decision)
                self.assertEqual(self.arch.snapshot(), before)

    def test_decision_digest_binds_candidate_artifact_and_parent_artifact(self):
        first = self.arch.evaluate_candidate(self.candidate)
        changed_candidate = self.arch.evaluate_candidate(replace(self.candidate, artifact_digest='other-child'))
        other = UnifiedCausalEvolutionArchitecture()
        other.register_root(replace(self.parent, artifact_digest='other-parent'))
        changed_parent = other.evaluate_candidate(self.candidate)
        self.assertNotEqual(first.decision_digest, changed_candidate.decision_digest)
        self.assertNotEqual(first.decision_digest, changed_parent.decision_digest)

    def test_decision_from_other_parent_or_controller_is_not_an_approval(self):
        other = UnifiedCausalEvolutionArchitecture()
        other.register_root(replace(self.parent, artifact_digest='other-parent'))
        decision = other.evaluate_candidate(self.candidate)
        before = self.arch.snapshot()
        with self.assertRaises(ValueError):
            self.arch.promote(self.candidate, decision)
        self.assertEqual(self.arch.snapshot(), before)

    def test_mutated_decision_does_not_modify_journal_or_authorize_promotion(self):
        decision = self.arch.evaluate_candidate(self.candidate)
        before = self.arch.snapshot()
        decision.gains['logic'] = 100.0
        self.assertEqual(self.arch.snapshot(), before)
        with self.assertRaises(ValueError):
            self.arch.promote(self.candidate, decision)
        self.assertEqual(self.arch.snapshot(), before)

    def test_withheld_decision_cannot_be_relabelled_as_approved(self):
        broken = replace(self.candidate, hard_constraints={})
        decision = self.arch.evaluate_candidate(broken)
        self.assertEqual(decision.action, 'WITHHOLD_CANDIDATE')
        with self.assertRaises(ValueError):
            self.arch.promote(broken, replace(decision, action='PROMOTE_GENERATION'))
        self.assertEqual(self.arch.developmental_head, 'parent')

    def test_caller_mutation_cannot_rewrite_registered_parent(self):
        before = self.arch.snapshot()
        self.parent.capability_scores['integrity'] = 0.0
        self.parent.metadata['provenance']['source'] = 'altered'
        self.assertEqual(self.arch.snapshot(), before)

    def test_promoted_record_and_snapshot_do_not_expose_mutable_state(self):
        decision = self.arch.evaluate_candidate(self.candidate)
        self.arch.promote(self.candidate, decision)
        before = self.arch.snapshot()
        self.candidate.metadata['provenance']['source'] = 'altered-by-caller'
        self.candidate.capability_scores['integrity'] = 0.0
        returned = self.arch.snapshot()
        returned['generations'][0]['metadata']['provenance']['source'] = 'altered-through-snapshot'
        self.assertEqual(self.arch.snapshot(), before)

    def test_omitting_parent_protected_score_is_withheld(self):
        missing = replace(self.candidate, capability_scores={'logic': 0.9}, protected_capabilities=())
        decision = self.arch.evaluate_candidate(missing)
        self.assertEqual(decision.action, 'WITHHOLD_CANDIDATE')
        with self.assertRaises(ValueError):
            self.arch.promote(missing, decision)
        self.assertEqual(self.arch.developmental_head, 'parent')

    def test_removing_inherited_protection_without_dropping_score_is_withheld(self):
        unprotected = replace(self.candidate, protected_capabilities=())
        decision = self.arch.evaluate_candidate(unprotected)
        self.assertEqual(decision.action, 'WITHHOLD_CANDIDATE')
        self.assertEqual(self.arch.developmental_head, 'parent')

    def test_preserved_protection_can_expand_but_cannot_regress(self):
        expanded = replace(self.candidate, protected_capabilities=('integrity', 'logic'))
        decision = self.arch.evaluate_candidate(expanded)
        self.assertEqual(decision.action, 'PROMOTE_GENERATION')
        self.arch.promote(expanded, decision)
        regressing = replace(
            expanded, generation_id='grandchild', parent_generation_id='child',
            artifact_digest='grandchild-artifact', capability_scores={'logic': 0.8, 'integrity': 0.99},
        )
        self.assertEqual(self.arch.evaluate_candidate(regressing).action, 'WITHHOLD_CANDIDATE')
        preserved = replace(regressing, capability_scores={'logic': 0.8, 'integrity': 1.0})
        next_decision = self.arch.evaluate_candidate(preserved)
        self.assertEqual(next_decision.action, 'PROMOTE_GENERATION')
        self.arch.promote(preserved, next_decision)
        self.assertEqual(self.arch.developmental_head, 'grandchild')
        self.assertEqual(self.arch.snapshot()['generation_count'], 3)
        with self.assertRaises(ValueError):
            self.arch.promote(expanded, decision)

    def test_architecture_and_runtime_helpers_remain_identical(self):
        root = Path(__file__).resolve().parents[1]
        name = 'yado_unified_causal_evolution_architecture_v1.py'
        self.assertEqual((root / 'runtime' / name).read_bytes(), (root / 'architecture' / name).read_bytes())


if __name__ == '__main__':
    unittest.main()
