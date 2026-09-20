"""Behavioral regressions found by the full runtime audit."""
import unittest

from yado_ambiguity_aware_program_repair_v11 import AmbiguityAwareProgramRepairV11
from yado_g2_cognitive_clock_v1 import G2CognitiveClockV1
from yado_work_budget_adaptive_contingent_planner_v2 import (
    ContingentStage,
    WorkBudgetAdaptiveContingentPlannerV2,
)


class DeepAuditRuntimeRegressions(unittest.TestCase):
    def test_completed_dependencies_do_not_make_an_offline_stage_available(self):
        unavailable = ContingentStage(
            'OFFLINE', 1, 1, available=False, requires=('READY',)
        )
        plan = WorkBudgetAdaptiveContingentPlannerV2.plan(
            0, 1, 10, [unavailable], completed=('READY',)
        )
        self.assertFalse(plan.feasible)
        self.assertEqual(plan.action, 'WITHHOLD')
        self.assertEqual(plan.sequence, [])

    def test_available_stage_still_waits_for_its_dependencies(self):
        stage = ContingentStage('ONLINE', 1, 1, requires=('READY',))
        waiting = WorkBudgetAdaptiveContingentPlannerV2.plan(0, 1, 10, [stage])
        ready = WorkBudgetAdaptiveContingentPlannerV2.plan(
            0, 1, 10, [stage], completed=('READY',)
        )
        self.assertFalse(waiting.feasible)
        self.assertEqual(ready.action, 'ONLINE')
        self.assertTrue(ready.feasible)

    def test_ambiguity_targets_the_variable_comparison_after_an_expression(self):
        source = (
            'def f(x):\n'
            '    return (1 if x + 1 <= 5 else 2) + (10 if x <= 10 else 20)\n'
        )
        examples = [((0,), 11), ((5,), 12), ((15,), 22)]
        alternative = source.replace('x <= 10', 'x <= 11')
        repairer = AmbiguityAwareProgramRepairV11
        for args, expected in examples:
            self.assertEqual(repairer.execute(source, 'f', args), expected)
            self.assertEqual(repairer.execute(alternative, 'f', args), expected)
        self.assertEqual(repairer.execute(source, 'f', (11,)), 22)
        self.assertEqual(repairer.execute(alternative, 'f', (11,)), 12)
        result = repairer.repair(source, 'f', examples, max_candidates=10)
        self.assertIsNone(result.get('source'))
        self.assertEqual(result['reason'], 'AMBIGUOUS_UNSEEN_THRESHOLD')

    def test_full_clock_evicts_an_unstarted_stream_without_losing_active_state(self):
        clock = G2CognitiveClockV1()
        clock.stream_state('UNSTARTED')
        for index in range(clock.MAX_STREAMS - 1):
            tick = clock.begin_tick('ACTIVE-' + str(index), 'OBSERVE')
            clock.finish_tick(tick['tick_id'], observed_result='DONE')
        previous_tick = clock.tick_id
        tick = clock.begin_tick('NEW', 'OBSERVE')
        clock.finish_tick(tick['tick_id'], observed_result='DONE')
        self.assertEqual(tick['tick_id'], previous_tick + 1)
        state = clock.export_state()
        self.assertEqual(len(state['streams']), clock.MAX_STREAMS)
        self.assertNotIn('UNSTARTED', state['streams'])
        self.assertIn('ACTIVE-0', state['streams'])
        self.assertEqual(clock.snapshot()['open_tick_count'], 0)


if __name__ == '__main__':
    unittest.main()
