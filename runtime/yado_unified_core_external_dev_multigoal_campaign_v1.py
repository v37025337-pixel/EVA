from __future__ import annotations

from yado_external_dev_multigoal_campaign_v1 import ExternalDevMultiGoalCampaignV1
from yado_unified_core_external_dev_self_development_v1 import UnifiedYADOCoreExternalDevSelfDevelopmentV1


class UnifiedYADOCoreExternalDevMultiGoalCampaignV1(UnifiedYADOCoreExternalDevSelfDevelopmentV1):
    CAMPAIGN_LAYER_ID = 'UNIFIED_YADO_CORE_EXTERNAL_DEV_MULTIGOAL_CAMPAIGN_V1'

    def __init__(self, repo_root=None, campaign_state=None, router_path=None):
        super().__init__(repo_root=repo_root)
        self.external_dev_campaign_controller = ExternalDevMultiGoalCampaignV1(router_path=router_path, state=campaign_state)

    def external_dev_campaign_advance(self, objective, *, steps=1, timeout=25.0, resolver=None, transport=None, fetch_override=None):
        out = self.external_dev_campaign_controller.advance(
            self, objective, steps=steps, timeout=timeout,
            resolver=resolver, transport=transport, fetch_override=fetch_override,
        )
        out['core_route'] = self.CAMPAIGN_LAYER_ID
        out['generation'] = self.head.get('generation_id')
        return out

    def external_dev_campaign_export_state(self):
        return self.external_dev_campaign_controller.export_state()

    def external_dev_campaign_receipt(self):
        out = self.external_dev_campaign_controller.final_receipt()
        out['core_route'] = self.CAMPAIGN_LAYER_ID
        out['generation'] = self.head.get('generation_id')
        return out

    def audit(self):
        report = super().audit()
        snap = self.external_dev_campaign_controller.snapshot()
        checks = dict(report['checks'])
        checks.update({
            'external_dev_multigoal_campaign_bound': snap.get('component_id') == 'RUNTIME-G2-EXTERNAL-DEV-MULTIGOAL-CAMPAIGN-V1',
            'external_dev_multigoal_campaign_no_third_party_execution': snap.get('third_party_code_executed') is False,
            'external_dev_multigoal_campaign_no_external_writes': snap.get('external_writes_to_third_parties') is False,
            'external_dev_multigoal_campaign_no_auto_main': snap.get('automatic_main_mutation') is False,
            'external_dev_multigoal_campaign_no_g3': snap.get('g3_genesis_performed') is False,
        })
        report['checks'] = checks
        report['pass'] = all(checks.values())
        report['external_dev_multigoal_campaign'] = snap
        return report

    def snapshot(self):
        snap = super().snapshot()
        snap['external_dev_multigoal_campaign'] = self.external_dev_campaign_controller.snapshot()
        snap['external_dev_multigoal_campaign_layer_id'] = self.CAMPAIGN_LAYER_ID
        snap['semantic_boundary'] = (
            'CANONICAL G2 PLUS A BOUNDED SHADOW FIVE-GOAL DEVELOPMENT CAMPAIGN. GOALS ARE DERIVED '
            'FROM CAMPAIGN STATE AND ROUTED BY THE ADMITTED YADO-GENERATED ROUTER; EXTERNAL ACTIONS '
            'REMAIN READ-ONLY, CREDENTIAL-FREE, NON-CANONICAL, AND DO NOT IMPLY G3 OR CONSCIOUSNESS.'
        )
        return snap


__all__ = ['UnifiedYADOCoreExternalDevMultiGoalCampaignV1']
