"""Development must revisit a deficit after learning a useful program."""
import copy
import os
from pathlib import Path
import tempfile
import unittest

from successor.kernel import SuccessorKernel


MANIFEST = Path(os.environ.get('YADO_SUCCESSOR_TEST_MANIFEST',
    Path(__file__).resolve().parents[2] / 'successor/state/birth-v2/manifest.json'))


def addition_goal(structured=False, invalid_holdout=False):
    def expected(x, y):
        return {'total': x + y} if structured else x + y
    spec = {'schema': 'yado.native_program_goal.v1', 'domain': 'native_source',
            'training': [{'input': {'x': x, 'y': y}, 'expected': expected(x, y)}
                         for x, y in [(2, 7), (5, -3), (-4, 13)]],
            'validation': [{'input': {'x': 11, 'y': -6}, 'expected': expected(11, -6)},
                           {'input': {'x': -8, 'y': -9}, 'expected': expected(-8, -9)}],
            'queries': [{'input': {'x': 31, 'y': 17}}]}
    if invalid_holdout:
        spec['validation'][0]['expected'] = {'total': 999}
    return spec


class MemoryRetryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.state = Path(self.tmp.name) / 'kernel.sqlite'
        self.kernel = SuccessorKernel(MANIFEST, self.state)
        self.kernel.set_compositional_synthesis(True)

    def tearDown(self):
        self.kernel.close()
        self.tmp.cleanup()

    def solve(self, spec):
        goal = self.kernel.open_goal(spec, budget=5)
        self.kernel.think(40)
        return self.kernel.cognitive_snapshot()['goals'][str(goal)]

    def develop(self):
        sid = self.kernel.start_development(budget=10, max_goals=2)
        self.kernel.develop(60)
        return self.kernel.development_snapshot()['sessions'][sid]

    def deficit_and_learning(self, invalid_holdout=False):
        failed = self.solve(addition_goal(True, invalid_holdout))
        self.assertEqual(failed['status'], 'WITHHOLD')
        self.assertEqual(failed['attempted'], ['native_compositional_v1'])
        self.assertEqual(self.develop()['selections'], [])
        learned = self.solve(addition_goal())
        self.assertEqual(learned['status'], 'VALIDATED_ON_HOLDOUT')
        return failed, learned

    def test_new_verified_program_reopens_exhausted_strategy_after_restart(self):
        failed, learned = self.deficit_and_learning()
        self.kernel.close()
        self.kernel = SuccessorKernel(MANIFEST, self.state)
        session = self.develop()
        self.assertEqual(len(session['selections']), 1)
        choice = session['selections'][0]
        self.assertEqual(choice['parent_goal_id'], failed['id'])
        self.assertEqual(choice['untried'][0]['strategy'], 'native_compositional_v1')
        self.assertEqual(session['outcomes'][0]['status'], 'VALIDATED_ON_HOLDOUT')
        child = self.kernel.cognitive_snapshot()['goals'][str(session['outcomes'][0]['goal_id'])]
        self.assertEqual(child['result']['predictions'], [{'total': 48}])
        self.assertEqual(child['result']['parent_source_sha256'], [learned['result']['source_sha256']])
        self.assertEqual(self.kernel.cognitive_snapshot()['goals'][str(failed['id'])], failed)
        self.assertEqual(self.develop()['selections'], [])
        self.assertEqual(self.kernel.verify_state()['status'], 'PASS')

    def test_failed_retry_and_duplicate_program_do_not_create_endless_retries(self):
        failed, learned = self.deficit_and_learning(invalid_holdout=True)
        session = self.develop()
        self.assertEqual(len(session['selections']), 1)
        self.assertEqual(session['outcomes'][0]['status'], 'WITHHOLD')
        self.assertEqual(self.develop()['selections'], [])
        repeated = self.solve(addition_goal())
        self.assertEqual(repeated['result']['source_sha256'], learned['result']['source_sha256'])
        self.assertEqual(self.develop()['selections'], [])

    def test_autonomy_uses_new_memory_for_its_next_retry(self):
        failed, _ = self.deficit_and_learning()
        sid = self.kernel.start_autonomy(budget=10, max_cycles=1)
        self.kernel.run_autonomy(60)
        session = self.kernel.autonomy_snapshot()['sessions'][sid]
        self.assertEqual(session['selections'][0]['route'], 'RETRY_FAILURE')
        self.assertEqual(session['selections'][0]['evidence']['parent_goal_id'], failed['id'])
        self.assertEqual(session['outcomes'][0]['status'], 'VALIDATED_ON_HOLDOUT')

    def test_v2_policy_preserves_previous_no_retry_decision(self):
        self.deficit_and_learning()
        sid = self.kernel._append({'kind': 'DEV_START', 'budget': 10, 'max_goals': 1,
                                   'retry_policy': 'untried_strategies_v2'})['tick']
        self.kernel.develop(20)
        legacy = copy.deepcopy(self.kernel.development_snapshot()['sessions'][sid])
        self.assertEqual(legacy['selections'], [])
        self.assertEqual(len(self.develop()['selections']), 1)
        self.assertEqual(self.kernel.development_snapshot()['sessions'][sid], legacy)

    def test_failed_or_incompatible_program_does_not_reopen_strategy(self):
        failed = self.solve(addition_goal(True))
        self.assertEqual(failed['status'], 'WITHHOLD')
        rejected = addition_goal()
        rejected['validation'][0]['expected'] = 999
        self.assertEqual(self.solve(rejected)['status'], 'WITHHOLD')
        self.assertEqual(self.develop()['selections'], [])
        unrelated = {'schema': 'yado.native_program_goal.v1', 'domain': 'native_source',
                     'training': [{'input': {'text': x}, 'expected': x.upper()} for x in ('a', 'b', 'c')],
                     'validation': [{'input': {'text': x}, 'expected': x.upper()} for x in ('d', 'e')],
                     'queries': [{'input': {'text': 'f'}}]}
        self.assertEqual(self.solve(unrelated)['status'], 'VALIDATED_ON_HOLDOUT')
        self.assertEqual(self.develop()['selections'], [])

    def test_selection_memory_evidence_cannot_be_forged(self):
        from successor.development import replay
        self.deficit_and_learning()
        sid = self.kernel.start_development(budget=10, max_goals=1)
        self.kernel.develop(1)
        records = sorted((r for r in self.kernel.recent(1000)
                          if r['kind'].startswith(('COG_', 'DEV_'))), key=lambda r: r['tick'])
        choice = next(r for r in records if r['kind'] == 'DEV_SELECT' and r['development_id'] == sid)
        choice['choice']['untried'][0]['memory_context_digest'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'DEVELOPMENT_SELECTION_EVIDENCE'):
            replay(records)

    def test_v2_autonomy_journal_stays_replayable(self):
        from successor.autonomy import OBJECTIVE
        self.deficit_and_learning()
        sid = self.kernel._append({'kind': 'AUTO_START', 'budget': 10, 'max_cycles': 1,
                                   'objective': OBJECTIVE, 'retry_policy': 'untried_strategies_v2'})['tick']
        self.kernel.run_autonomy(60)
        session = self.kernel.autonomy_snapshot()['sessions'][sid]
        self.assertEqual(session['selections'][0]['route'], 'EXPLORE')
        self.assertEqual(self.kernel.verify_state()['status'], 'PASS')


if __name__ == '__main__':
    unittest.main()
