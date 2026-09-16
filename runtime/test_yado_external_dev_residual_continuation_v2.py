import json
import unittest

from test_yado_external_dev_capability_pack_v1 import fake_fetch
from yado_unified_core_external_dev_residual_continuation_v2 import (
    UnifiedYADOCoreExternalDevResidualContinuationV2,
)


OBJECTIVE = 'Improve the reliability and continuity of YADO external developer self-development without naming a preferred tool'


class ExternalDevResidualContinuationV2Tests(unittest.TestCase):
    def test_residual_goal_begins_only_after_base_five_and_uses_live_output(self):
        core = UnifiedYADOCoreExternalDevResidualContinuationV2()
        out = core.external_dev_campaign_advance(OBJECTIVE, steps=5, fetch_override=fake_fetch)
        self.assertEqual(out['goal_count'], 5)
        self.assertEqual(out['residual_goal_count'], 0)
        self.assertEqual(out['status'], 'IN_PROGRESS_EXTERNAL_DEV_RESIDUAL_CONTINUATION_V2')
        self.assertIsNotNone(out['next_goal'])
        resource_name = out['resource_candidate']['name']
        self.assertIn(resource_name.lower(), out['next_goal'].lower())
        for source_name in ('hivemind', 'hoppscotch', 'dyad', 'nexustools', 'free-for-dev'):
            self.assertNotIn(source_name, out['next_goal'].lower())

        out = core.external_dev_campaign_advance(OBJECTIVE, steps=1, fetch_override=fake_fetch)
        self.assertEqual(out['goal_count'], 6)
        self.assertEqual(out['residual_goal_count'], 1)
        self.assertEqual(out['events'][5]['selected_capability'], 'LOCAL_APP_BUILD_ADMISSION_LOOP')
        self.assertEqual(out['events'][5]['result_status'], 'PASS_RESOURCE_VALIDATION_PLAN')
        self.assertTrue(out['post_fixed_goal_derived_from_live_state'])

    def test_restart_after_base_five_continues_two_residual_goals(self):
        first = UnifiedYADOCoreExternalDevResidualContinuationV2()
        partial = first.external_dev_campaign_advance(OBJECTIVE, steps=5, fetch_override=fake_fetch)
        self.assertEqual(partial['goal_count'], 5)
        state = first.external_dev_campaign_export_state()

        second = UnifiedYADOCoreExternalDevResidualContinuationV2(campaign_state=state)
        final = second.external_dev_campaign_advance(OBJECTIVE, steps=2, fetch_override=fake_fetch)
        self.assertEqual(final['status'], 'PASS_SHADOW_EXTERNAL_DEV_RESIDUAL_CONTINUATION_V2')
        self.assertEqual(final['goal_count'], 7)
        self.assertEqual(final['base_goal_count'], 5)
        self.assertEqual(final['residual_goal_count'], 2)
        self.assertEqual(final['restart_count'], 1)
        self.assertEqual(final['chain_verification']['event_count'], 7)
        self.assertTrue(final['post_fixed_goal_derived_from_live_state'])
        self.assertEqual(final['events'][5]['selected_capability'], 'LOCAL_APP_BUILD_ADMISSION_LOOP')
        self.assertEqual(final['events'][6]['selected_capability'], 'PURE_LOCAL_DEV_UTILITY_LIBRARY')
        self.assertEqual(final['events'][6]['result_status'], 'PASS_RESIDUAL_CONTINUATION_DIGEST')
        self.assertEqual(len(final['continuation_digest']), 64)
        self.assertIsNone(final['next_goal'])
        receipt = second.external_dev_campaign_receipt()
        self.assertEqual(receipt['core_route'], 'UNIFIED_YADO_CORE_EXTERNAL_DEV_RESIDUAL_CONTINUATION_V2')
        self.assertEqual(receipt['generation'], 'G2_CANDIDATE_TRCG_V1')

    def test_tampered_state_still_fails_closed(self):
        core = UnifiedYADOCoreExternalDevResidualContinuationV2()
        core.external_dev_campaign_advance(OBJECTIVE, steps=5, fetch_override=fake_fetch)
        state = core.external_dev_campaign_export_state()
        state['artifacts']['resource_options']['results'][0]['name'] = 'tampered'
        with self.assertRaises(RuntimeError):
            UnifiedYADOCoreExternalDevResidualContinuationV2(
                campaign_state=json.loads(json.dumps(state))
            )

    def test_core_audit_preserves_boundary(self):
        core = UnifiedYADOCoreExternalDevResidualContinuationV2()
        audit = core.audit()
        self.assertTrue(audit['pass'], audit)
        snap = core.snapshot()
        self.assertEqual(
            snap['external_dev_residual_continuation']['component_id'],
            'RUNTIME-G2-EXTERNAL-DEV-RESIDUAL-CONTINUATION-V2',
        )
        self.assertFalse(
            snap['external_dev_residual_continuation']['automatic_main_mutation']
        )


if __name__ == '__main__':
    unittest.main()
