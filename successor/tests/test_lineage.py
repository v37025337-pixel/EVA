import copy
import json
import os
from pathlib import Path
import tempfile
import unittest
import sys
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'runtime/yado_rc8_v36'))

from successor.kernel import SuccessorKernel, encode
from successor.lineage import (BUDGET, REQUEST, ConsecutiveLineage, _challenge,
                               _query_check, initial_plan, next_challenge,
                               normalize_request, polynomial_values, records, replay)


def spec(power=3):
    row = lambda x: {'input': {'x': x}, 'expected': 17 * x ** power - 2 * x - 5}
    return {'domain': 'native_source', 'training': [row(x) for x in range(-3, 4)],
            'validation': [row(-6), row(7)], 'queries': [{'input': {'x': -9}}, {'input': {'x': 11}}]}


class LineageContractTests(unittest.TestCase):
    def test_only_a_bounded_high_level_objective_is_accepted(self):
        self.assertEqual(normalize_request(REQUEST), REQUEST)
        for field in ('source', 'degree', 'goal_id', 'passed', 'command', 'oracle'):
            with self.assertRaises(ValueError):
                normalize_request({**REQUEST, field: 'observer supplied'})
        for count in (True, 0, 2, 6, 3.0, '3'):
            with self.assertRaises(ValueError):
                normalize_request({**REQUEST, 'generations': count})

    def test_orphan_tags_and_lineage_events_are_rejected(self):
        for kind in ('COG_GOAL', 'LINEAGE_GENERATION', 'unrelated'):
            with self.assertRaisesRegex(ValueError, 'ORPHAN'):
                replay([{'kind': kind, 'lineage_id': 1, 'tick': 1, 'event_hash': 'a' * 64}])

    def test_exact_oracle_does_not_use_the_materialized_fitter(self):
        task = spec(5)
        xs = [-19, 23]
        with patch('successor.native_mechanism.synthesize', side_effect=AssertionError('fitter called')):
            self.assertEqual(polynomial_values(task['training'], [{'x': x} for x in xs]),
                             [17 * x ** 5 - 2 * x - 5 for x in xs])

    def test_next_goal_is_derived_from_actual_parent_and_immutable_finish(self):
        from successor.native_mechanism import build_candidate, synthesize
        task = spec()
        program = synthesize(build_candidate(3), task['training'])
        finish = {'tick': 42, 'event_hash': '12ab' + '7' * 60, 'result': program}
        challenge = _challenge(encode(finish), encode(task))
        key = next(iter(challenge['spec']['training'][0]['input']))
        a, b = challenge['recipe']['a'], challenge['recipe']['b']
        for row in challenge['spec']['training'] + challenge['spec']['validation']:
            x = row['input'][key]
            self.assertEqual(row['expected'], x * (17 * x ** 3 - 2 * x - 5) + a * x + b)
        mutated = copy.deepcopy(finish)
        mutated['result']['source'] = "def solve(component_id, program_id, inputs):\n    return 17\n"
        import hashlib
        mutated['result']['source_sha256'] = hashlib.sha256(mutated['result']['source'].encode()).hexdigest()
        with self.assertRaises(ValueError):
            _challenge(encode(mutated), encode(task))

    def test_success_flag_cannot_substitute_for_program_reexecution(self):
        from successor.native_mechanism import build_candidate, synthesize
        task = spec()
        program = synthesize(build_candidate(3), task['training'])
        expected = [-17 * 9 ** 3 + 18 - 5, 17 * 11 ** 3 - 22 - 5]
        self.assertEqual(_query_check(encode(program), encode(task), encode(expected)), tuple(expected))
        with self.assertRaisesRegex(ValueError, 'SEALED_QUERIES'):
            _query_check(encode(program), encode(task), encode([0, 0]))


ROOT = Path(__file__).resolve().parents[2]
MANIFEST = Path(os.environ.get('YADO_SUCCESSOR_TEST_MANIFEST', ROOT / 'successor/state/birth-v2/manifest.json'))


class LineageIntegrationTests(unittest.TestCase):
    def setUp(self):
        if not MANIFEST.exists():
            self.skipTest('Build the pinned successor before integration tests')
        self.tmp = tempfile.TemporaryDirectory()
        self.state = Path(self.tmp.name) / 'kernel.sqlite'
        self.kernel = SuccessorKernel(MANIFEST, self.state)
        self.loop = ConsecutiveLineage(self.kernel)

    def tearDown(self):
        if hasattr(self, 'kernel'):
            self.kernel.close()
            self.tmp.cleanup()

    def deficit(self):
        self.kernel.activate_native_synthesis()
        self.kernel.open_goal(spec(), budget=BUDGET)
        self.kernel.think(100)
        sid = self.loop.start('lineage-test', 'YADO-1', REQUEST)
        return sid

    def test_no_deficit_stops_durably_with_zero_generations_and_reopens(self):
        sid = self.loop.start('lineage-test', 'YADO-1', REQUEST)
        result = self.loop.run(sid, Path(self.tmp.name) / 'gates')
        self.assertEqual(result['status'], 'WITHHOLD')
        self.assertEqual(result['generations'], [])
        self.assertEqual(result['finish']['reason'], 'NO_SUPPORTED_DEFICIT')
        before = self.kernel.verify_state()
        self.assertEqual(self.loop.start('lineage-test', 'YADO-1', REQUEST), sid)
        self.loop.run(sid, Path(self.tmp.name) / 'gates')
        self.assertEqual(self.kernel.verify_state(), before)
        self.kernel.close()
        self.kernel = SuccessorKernel(MANIFEST, self.state)
        self.assertEqual(self.kernel.verify_state(), before)

    def test_foreign_work_and_changed_owned_goal_rejected_before_insert(self):
        sid = self.deficit()
        before = self.kernel.verify_state()
        with self.assertRaisesRegex(ValueError, 'UNRELATED'):
            self.kernel.open_goal({'domain': 'relation', 'relation': [[1, 2]], 'start': 1})
        self.assertEqual(self.kernel.verify_state(), before)
        s = self.loop.snapshot()[sid]
        self.loop._append(initial_plan(records(self.kernel), s))
        before = self.kernel.verify_state()
        with self.assertRaisesRegex(ValueError, 'OWNED_GOAL_CONTRACT'):
            self.kernel.open_goal(spec(), budget=1)
        self.assertEqual(self.kernel.verify_state(), before)
        self.loop.stop(sid)
        self.assertEqual(self.loop.snapshot()[sid]['status'], 'WITHHOLD')

    def test_interrupted_gate_cannot_reroll_or_count_a_generation(self):
        sid = self.deficit()
        out = Path(self.tmp.name) / 'gates'
        with patch('successor.runtime_evolution.RuntimeEvolution.evaluate',
                   side_effect=InterruptedError('power loss')) as evaluate:
            with self.assertRaisesRegex(InterruptedError, 'power loss'):
                self.loop.run(sid, out)
            self.assertEqual(evaluate.call_count, 1)
        s = self.loop.snapshot()[sid]
        self.assertEqual(s['phase'], 'GATING')
        self.assertEqual(s['control_finish']['status'], 'WITHHOLD')
        self.assertEqual(s['gate']['seed'], evaluate.call_args.kwargs['trial_seed'])
        before = self.kernel.verify_state()
        forged = {'kind': 'LINEAGE_GENERATION', 'lineage_id': sid, 'ordinal': 1}
        with self.assertRaisesRegex(ValueError, 'UNRELATED_OR_OUT_OF_ORDER'):
            self.loop._append(forged)
        self.assertEqual(self.kernel.verify_state(), before)
        self.kernel.close()
        self.kernel = SuccessorKernel(MANIFEST, self.state)
        self.loop = ConsecutiveLineage(self.kernel)
        with patch('successor.runtime_evolution.RuntimeEvolution.evaluate',
                   side_effect=AssertionError('a second gate attempt is forbidden')):
            result = self.loop.run(sid, out)
        self.assertEqual(result['finish']['reason'], 'INTERRUPTED_GATES')
        self.assertEqual(result['generations'], [])

    def test_upgrade_cannot_cross_an_active_lineage(self):
        from successor.continuity import prepare_upgrade
        self.loop.start('lineage-test', 'YADO-1', REQUEST)
        with self.assertRaisesRegex(ValueError, 'IDLE_PREDECESSOR'):
            prepare_upgrade(MANIFEST, self.state, Path(self.tmp.name) / 'upgrade')

    def test_valid_legacy_execution_history_is_retained(self):
        from successor.runtime_evolution import active_candidates
        self.kernel._append({'task': {'kind': 'audit'}, 'status': 'PASS', 'execution_attempted': True})
        sid = self.loop.start('lineage-test', 'YADO-1', REQUEST)
        self.assertEqual(active_candidates(records(self.kernel)), {})
        result = self.loop.run(sid, Path(self.tmp.name) / 'gates')
        self.assertEqual(result['finish']['reason'], 'NO_SUPPORTED_DEFICIT')
        self.assertEqual(self.kernel.verify_state()['status'], 'PASS')

    def test_tracker_publishes_withhold_and_does_not_claim_generations(self):
        from successor.hivemind_lineage import CRITERIA, run_issue
        from successor.tests.test_hivemind import Tracker
        tracker = Tracker({})
        tracker.issue['description'] = json.dumps(REQUEST)
        tracker.issue['acceptanceCriteria'] = [{'text': text, 'done': False} for text in CRITERIA]
        result = run_issue(self.kernel, tracker, 'lineage-test', tracker.issue['id'],
                           Path(self.tmp.name) / 'gates')
        self.assertEqual(result['status'], 'WITHHOLD')
        self.assertEqual(result['generations'], 0)
        self.assertEqual(tracker.issue['state'], 'in_review')
        self.assertFalse(any(row['done'] for row in tracker.issue['acceptanceCriteria']))
        before = self.kernel.verify_state()
        self.assertEqual(run_issue(self.kernel, tracker, 'lineage-test', tracker.issue['id'],
                                  Path(self.tmp.name) / 'gates'), result)
        self.assertEqual(self.kernel.verify_state(), before)

    def test_wrong_cognitive_phase_cannot_poison_owned_goal_history(self):
        sid = self.deficit()
        plan = initial_plan(records(self.kernel), self.loop.snapshot()[sid])
        self.loop._append(plan)
        gid = self.kernel.open_goal(plan['spec'], budget=BUDGET)
        before = self.kernel.verify_state()
        with self.assertRaises(ValueError):
            self.kernel._append({'kind': 'COG_VERIFY', 'goal_id': gid, 'execution_tick': gid,
                                 'passed': True, 'workspace_digest': 'forged'})
        self.assertEqual(self.kernel.verify_state(), before)
        self.loop.stop(sid)

    def test_mutating_returned_plan_does_not_poison_inherited_memory(self):
        sid = self.deficit()
        before = self.kernel.verify_state()
        plan = initial_plan(records(self.kernel), self.loop.snapshot()[sid])
        plan['spec']['training'][0]['expected'] += 1
        with self.assertRaisesRegex(ValueError, 'SELECTION_PROVENANCE'):
            self.loop._append(plan)
        self.assertEqual(self.kernel.verify_state(), before)
        self.loop.stop(sid)

    def test_tracker_cancellation_after_run_is_not_overwritten(self):
        from successor.hivemind_lineage import CRITERIA, run_issue
        from successor.tests.test_hivemind import Tracker
        tracker = Tracker({})
        tracker.issue['description'] = json.dumps(REQUEST)
        tracker.issue['acceptanceCriteria'] = [{'text': text, 'done': False} for text in CRITERIA]
        original_call, calls = tracker.call, []
        def racing_call(name, arguments):
            calls.append(name)
            if name == 'hive_get_issue' and calls.count(name) == 4:
                tracker.issue['state'] = 'cancelled'
            return original_call(name, arguments)
        tracker.call = racing_call
        result = run_issue(self.kernel, tracker, 'lineage-test', tracker.issue['id'],
                           Path(self.tmp.name) / 'gates')
        self.assertEqual(result['status'], 'CANCELLED')
        self.assertEqual(tracker.issue['state'], 'cancelled')
        self.assertNotIn('hive_add_comment', calls)
        self.assertEqual(self.loop.snapshot()[result['lineage_id']]['generations'], [])

    def test_invalid_edited_tracker_objective_durably_stops_session(self):
        from successor.hivemind_lineage import CRITERIA, run_issue
        from successor.tests.test_hivemind import Tracker
        tracker = Tracker({})
        tracker.issue['description'] = json.dumps(REQUEST)
        tracker.issue['acceptanceCriteria'] = [{'text': text, 'done': False} for text in CRITERIA]
        sid = self.loop.start('lineage-test', tracker.issue['id'], REQUEST)
        tracker.issue['description'] = '{invalid JSON'
        with self.assertRaises(ValueError):
            run_issue(self.kernel, tracker, 'lineage-test', tracker.issue['id'],
                       Path(self.tmp.name) / 'gates')
        result = self.loop.snapshot()[sid]
        self.assertEqual(result['status'], 'WITHHOLD')
        self.assertEqual(result['finish']['reason'], 'USER_STOP')

    def test_valid_but_changed_tracker_objective_stops_original_session(self):
        from successor.hivemind_lineage import CRITERIA, run_issue
        from successor.tests.test_hivemind import Tracker
        tracker = Tracker({})
        tracker.issue['description'] = json.dumps({**REQUEST, 'generations': 4})
        tracker.issue['acceptanceCriteria'] = [{'text': text, 'done': False} for text in CRITERIA]
        sid = self.loop.start('lineage-test', tracker.issue['id'], REQUEST)
        with self.assertRaisesRegex(ValueError, 'OBJECTIVE_CHANGED'):
            run_issue(self.kernel, tracker, 'lineage-test', tracker.issue['id'],
                       Path(self.tmp.name) / 'gates')
        self.assertEqual(self.loop.snapshot()[sid]['finish']['reason'], 'USER_STOP')


if __name__ == '__main__':
    unittest.main()
