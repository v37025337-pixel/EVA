import json
import unittest

from test_yado_external_dev_capability_pack_v1 import fake_fetch
from yado_unified_core_external_dev_multigoal_campaign_v1 import UnifiedYADOCoreExternalDevMultiGoalCampaignV1


OBJECTIVE = 'Improve the reliability and continuity of YADO external developer self-development without naming a preferred tool'


class ExternalDevMultiGoalCampaignTests(unittest.TestCase):
    def test_five_state_derived_goals_select_five_capabilities(self):
        core = UnifiedYADOCoreExternalDevMultiGoalCampaignV1()
        out = core.external_dev_campaign_advance(OBJECTIVE, steps=5, fetch_override=fake_fetch)
        self.assertEqual(out['status'], 'PASS_SHADOW_EXTERNAL_DEV_MULTIGOAL_CAMPAIGN_V1')
        self.assertEqual(out['goal_count'], 5)
        self.assertEqual(out['distinct_capability_count'], 5)
        self.assertTrue(out['unknown_withhold'])
        self.assertTrue(all(row['goal_derived_from_state'] for row in out['events']))
        joined = ' '.join(row['goal'].lower() for row in out['events'])
        for name in ('hivemind', 'hoppscotch', 'dyad', 'nexustools', 'free-for-dev'):
            self.assertNotIn(name, joined)

    def test_campaign_survives_restart_after_three_goals(self):
        first = UnifiedYADOCoreExternalDevMultiGoalCampaignV1()
        partial = first.external_dev_campaign_advance(OBJECTIVE, steps=3, fetch_override=fake_fetch)
        self.assertEqual(partial['goal_count'], 3)
        state = first.external_dev_campaign_export_state()
        second = UnifiedYADOCoreExternalDevMultiGoalCampaignV1(campaign_state=state)
        final = second.external_dev_campaign_advance(OBJECTIVE, steps=2, fetch_override=fake_fetch)
        self.assertEqual(final['status'], 'PASS_SHADOW_EXTERNAL_DEV_MULTIGOAL_CAMPAIGN_V1')
        self.assertEqual(final['restart_count'], 1)
        self.assertEqual(final['chain_verification']['event_count'], 5)
        self.assertEqual(second.external_dev_campaign_receipt()['generation'], 'G2_CANDIDATE_TRCG_V1')

    def test_tampered_state_fails_closed(self):
        core = UnifiedYADOCoreExternalDevMultiGoalCampaignV1()
        core.external_dev_campaign_advance(OBJECTIVE, steps=2, fetch_override=fake_fetch)
        state = core.external_dev_campaign_export_state()
        state['events'][0]['goal'] += ' tampered'
        with self.assertRaises(RuntimeError):
            UnifiedYADOCoreExternalDevMultiGoalCampaignV1(campaign_state=json.loads(json.dumps(state)))

    def test_core_audit_preserves_boundary(self):
        audit = UnifiedYADOCoreExternalDevMultiGoalCampaignV1().audit()
        self.assertTrue(audit['pass'], audit)
        self.assertEqual(UnifiedYADOCoreExternalDevMultiGoalCampaignV1().snapshot()['generation'], 'G2_CANDIDATE_TRCG_V1')


if __name__ == '__main__':
    unittest.main()
