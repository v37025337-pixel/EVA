"""Selection versioning and actual bounded parent/candidate transfer probes."""
import copy
import json
import unittest

from successor.archive import canonical
from successor.kernel import fingerprint
from successor.native_mechanism import build_candidate
from successor.runtime_evolution import REQUEST, _checked_trial_seed, _expected_trial, replay_event, select_candidate


POLICY = 'bounded_polynomial_degree5_v2'


def failed_goal(degree):
    row = lambda x: {'input': {'x': x}, 'expected': x ** degree - 2 * x + 7}
    return {'id': degree, 'status': 'WITHHOLD', 'mode': 'full',
            'spec': {'domain': 'native_source', 'training': [row(x) for x in range(-3, 4)],
                     'validation': [row(-8), row(9)], 'queries': [{'input': {'x': 11}}]},
            'attempted': ['native_evolved_v2']}


def proposal(goals):
    return {'kind': 'COG_RUNTIME_PROPOSE', 'tick': 10, 'workspace_id': 'policy-test',
            'issue_id': 'YADO-1', 'request': REQUEST, 'implementation_identity': 'test-implementation',
            'selection': None, 'parents': [], 'memory_digest': fingerprint(goals),
            'generator_authorship': 'ASSISTANT_AUTHORIZED_BY_USER',
            'algorithm_origin': 'INHERITED_FITTER_KERNEL_SELECTED_AST_MATERIALIZATION'}


class RuntimeSelectionPolicyTests(unittest.TestCase):
    def test_persisted_trial_seed_has_an_exact_bounded_format(self):
        self.assertEqual(_checked_trial_seed('0123456789abcdef' * 3), '0123456789abcdef' * 3)
        for seed in (None, 123, '', 'a' * 47, 'a' * 49, 'A' * 48, 'g' * 48):
            with self.subTest(seed=seed), self.assertRaisesRegex(ValueError, 'FRESH_SEED_CONTRACT'):
                _checked_trial_seed(seed)

    def test_legacy_no_candidate_proposal_remains_unchanged(self):
        goals = {4: failed_goal(4)}
        self.assertIsNone(select_candidate(goals))
        historical = proposal(goals)
        before = copy.deepcopy(historical)
        replay_event(historical, [], goals)
        self.assertEqual(historical, before)
        updated = {**historical, 'selection_policy': POLICY,
                   'selection': select_candidate(goals, policy=POLICY)}
        self.assertEqual(updated['selection']['max_degree'], 4)
        replay_event(updated, [], goals)
        updated.pop('selection_policy')
        with self.assertRaisesRegex(ValueError, 'SELECTION_PROVENANCE'):
            replay_event(updated, [], goals)

    def test_new_policy_selects_four_then_five_against_actual_parent_modules(self):
        goals = {4: failed_goal(4), 5: failed_goal(5)}
        parents = [build_candidate(3)]
        selected = select_candidate(goals, parents=parents, policy=POLICY)
        self.assertEqual(selected['goal_id'], 4)
        parents.append(selected['candidate'])
        selected = select_candidate(goals, parents=parents, policy=POLICY)
        self.assertEqual(selected['goal_id'], 5)
        parents.append(selected['candidate'])
        self.assertIsNone(select_candidate(goals, parents=parents, policy=POLICY))

    def test_unknown_or_null_recorded_selection_policy_is_rejected(self):
        for policy in ('unknown', 5, True, {}, []):
            with self.subTest(policy=policy), self.assertRaisesRegex(ValueError, 'SELECTION_POLICY'):
                select_candidate({}, policy=policy)
        for policy in ('unknown', None, 5, True, {}, []):
            with self.subTest(recorded_policy=policy), self.assertRaisesRegex(ValueError, 'SELECTION_POLICY'):
                replay_event({**proposal({}), 'selection_policy': policy}, [], {})

    def test_fresh_transfer_really_executes_higher_degree_candidates_and_all_parents(self):
        for degree in (4, 5):
            with self.subTest(degree=degree):
                candidate = build_candidate(degree)
                parents = [build_candidate(d) for d in range(degree)]
                report = json.loads(_expected_trial(canonical(candidate),
                    canonical(failed_goal(degree)['spec']), degree, 'a' * 48, canonical(parents)))
                self.assertTrue(report['passed'])
                self.assertEqual(report['fresh_cases'], 2 * (degree + 1))
                self.assertTrue(all(len(case['training']) >= case['degree'] + 2 for case in report['cases']))
                self.assertEqual(len(report['active_parent_predictions']), len(parents))
                self.assertEqual(report['fresh_gain_over_parent'], 1)
                self.assertTrue(all(report['negative_rejections']))
                # A parent that can solve the target eliminates the measured gain,
                # even when every other parent remains unable to solve it.
                parents.append(build_candidate(5))
                no_gain = json.loads(_expected_trial(canonical(candidate),
                    canonical(failed_goal(degree)['spec']), degree, 'a' * 48, canonical(parents)))
                self.assertEqual(no_gain['fresh_gain_over_parent'], 0)
                self.assertFalse(no_gain['passed'])


if __name__ == '__main__':
    unittest.main()
