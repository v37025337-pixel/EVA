from __future__ import annotations

from yado_external_dev_residual_continuation_v2 import ExternalDevResidualContinuationV2
from yado_unified_core_external_dev_multigoal_campaign_v1 import UnifiedYADOCoreExternalDevMultiGoalCampaignV1
from yado_unified_core_external_dev_self_development_v1 import UnifiedYADOCoreExternalDevSelfDevelopmentV1


class UnifiedYADOCoreExternalDevResidualContinuationV2(UnifiedYADOCoreExternalDevMultiGoalCampaignV1):
    CAMPAIGN_LAYER_ID = 'UNIFIED_YADO_CORE_EXTERNAL_DEV_RESIDUAL_CONTINUATION_V2'

    def __init__(self, repo_root=None, campaign_state=None, router_path=None):
        UnifiedYADOCoreExternalDevSelfDevelopmentV1.__init__(self, repo_root=repo_root)
        self.external_dev_campaign_controller = ExternalDevResidualContinuationV2(
            router_path=router_path,
            state=campaign_state,
        )

    def audit(self):
        report = UnifiedYADOCoreExternalDevSelfDevelopmentV1.audit(self)
        snap = self.external_dev_campaign_controller.snapshot()
        checks = dict(report['checks'])
        checks.update({
            'external_dev_residual_continuation_bound': (
                snap.get('component_id') == 'RUNTIME-G2-EXTERNAL-DEV-RESIDUAL-CONTINUATION-V2'
            ),
            'external_dev_residual_goal_state_binding_available': (
                snap.get('post_fixed_goal_derived_from_live_state') in (False, True)
            ),
            'external_dev_residual_continuation_no_third_party_execution': (
                snap.get('third_party_code_executed') is False
            ),
            'external_dev_residual_continuation_no_external_writes': (
                snap.get('external_writes_to_third_parties') is False
            ),
            'external_dev_residual_continuation_no_auto_main': (
                snap.get('automatic_main_mutation') is False
            ),
            'external_dev_residual_continuation_no_g3': (
                snap.get('g3_genesis_performed') is False
            ),
        })
        report['checks'] = checks
        report['pass'] = all(checks.values())
        report['external_dev_residual_continuation'] = snap
        return report

    def snapshot(self):
        snap = UnifiedYADOCoreExternalDevSelfDevelopmentV1.snapshot(self)
        snap['external_dev_residual_continuation'] = self.external_dev_campaign_controller.snapshot()
        snap['external_dev_residual_continuation_layer_id'] = self.CAMPAIGN_LAYER_ID
        snap['semantic_boundary'] = (
            'CANONICAL G2 PLUS A BOUNDED SHADOW RESIDUAL-GOAL CONTINUATION LAYER. THE FIRST FIVE '
            'GOALS REMAIN THE ADMITTED V1 CAMPAIGN; AFTERWARD THE NEXT GOAL IS DERIVED FROM THE '
            'ACTUAL RETAINED RESOURCE-DISCOVERY RESULT AND ROUTED BY THE ADMITTED YADO-GENERATED '
            'ROUTER. NO THIRD-PARTY CODE EXECUTION, CREDENTIAL USE, EXTERNAL WRITE, AUTOMATIC MAIN '
            'MUTATION, G3 CLAIM, OR CONSCIOUSNESS CLAIM IS MADE.'
        )
        return snap


__all__ = ['UnifiedYADOCoreExternalDevResidualContinuationV2']
