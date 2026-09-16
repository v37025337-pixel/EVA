from __future__ import annotations

from yado_external_dev_multigoal_campaign_v1 import (
    ExternalDevMultiGoalCampaignV1,
    canon,
    clone,
    digest,
)

COMPONENT_ID = 'RUNTIME-G2-EXTERNAL-DEV-RESIDUAL-CONTINUATION-V2'
SCHEMA = 'yado.external_dev_residual_continuation.v2'


class ExternalDevResidualContinuationV2(ExternalDevMultiGoalCampaignV1):
    """Extend the admitted five-goal campaign with state-derived residual goals.

    The first five goals remain byte-for-byte governed by V1. Only after V1 has
    completed does this layer inspect its retained artifacts and derive a new
    deficit from the actual resource-discovery output. The follow-up route is
    still selected by the admitted YADO-generated capability router.
    """

    def __init__(self, router_path=None, state=None):
        super().__init__(router_path=router_path, state=state)
        existing_schema = self.state.get('continuation_schema')
        if existing_schema not in (None, SCHEMA):
            raise RuntimeError('RESIDUAL_CONTINUATION_SCHEMA_MISMATCH')
        existing_component = self.state.get('continuation_component_id')
        if existing_component not in (None, COMPONENT_ID):
            raise RuntimeError('RESIDUAL_CONTINUATION_COMPONENT_MISMATCH')
        self.state['continuation_schema'] = SCHEMA
        self.state['continuation_component_id'] = COMPONENT_ID

    def _first_resource(self):
        resource_options = self.state.get('artifacts', {}).get('resource_options') or {}
        results = resource_options.get('results') or []
        if not results:
            return None
        row = results[0]
        if not isinstance(row, dict):
            return None
        return {
            'name': ' '.join(str(row.get('name') or 'unnamed candidate').split()),
            'url': str(row.get('url') or ''),
            'description': ' '.join(str(row.get('description') or '').split())[:500],
            'score': row.get('score'),
        }

    def derive_next_goal(self):
        inherited = super().derive_next_goal()
        if inherited is not None:
            return inherited

        artifacts = self.state['artifacts']
        first = self._first_resource()
        if first is None:
            raise RuntimeError('RESIDUAL_CONTINUATION_RESOURCE_EVIDENCE_MISSING')

        if 'resource_validation_plan' not in artifacts:
            count = int((artifacts.get('resource_options') or {}).get('result_count') or 0)
            return (
                f"The completed discovery produced {count} free compute candidates and the leading "
                f"candidate is '{first['name']}'. Before any deployment, build a local candidate "
                "validation plan with compile, test, regression, rollback and admission checks using "
                "only the evidence already collected."
            )

        if 'continuation_digest' not in artifacts:
            phases = len((artifacts['resource_validation_plan'] or {}).get('phases') or [])
            return (
                f"The state-derived validation plan contains {phases} phases; freeze an offline digest "
                "and hash of its continuation evidence so a later restart can detect drift before execution."
            )

        return None

    def _execute_selected(
        self,
        core,
        capability,
        goal,
        *,
        timeout=25.0,
        resolver=None,
        transport=None,
        fetch_override=None,
    ):
        artifacts = self.state['artifacts']
        first = self._first_resource()

        if (
            capability == 'LOCAL_APP_BUILD_ADMISSION_LOOP'
            and first is not None
            and 'resource_options' in artifacts
            and 'resource_validation_plan' not in artifacts
        ):
            out = core.external_dev_app_build_plan(
                f"Validate discovered free compute candidate {first['name']} without deploying or creating an account",
                'Python stdlib + current YADO G2 core + retained read-only evidence',
                [
                    'compile',
                    'offline-config-validation',
                    'public-doc-recheck',
                    'regression',
                    'rollback',
                    'admission',
                ],
            )
            out = clone(out)
            out['candidate'] = first
            out['derived_from_resource_discovery'] = True
            artifacts['resource_validation_plan'] = out
            return 'PASS_RESOURCE_VALIDATION_PLAN', {
                'candidate_name': first['name'],
                'candidate_url': first['url'],
                'phases': len(out.get('phases') or []),
            }

        if (
            capability == 'PURE_LOCAL_DEV_UTILITY_LIBRARY'
            and first is not None
            and 'resource_validation_plan' in artifacts
            and 'continuation_digest' not in artifacts
        ):
            frozen = {
                'objective': self.state.get('objective'),
                'resource_candidate': first,
                'resource_validation_plan': artifacts['resource_validation_plan'],
                'previous_event_sha256': (
                    self.state['events'][-1]['event_sha256'] if self.state.get('events') else None
                ),
            }
            out = core.external_dev_utility('sha256', canon(frozen))
            if out.get('network_used') is not False or len(out.get('output', '')) != 64:
                raise RuntimeError('RESIDUAL_CONTINUATION_DIGEST_FAILED')
            artifacts['continuation_digest'] = out
            return 'PASS_RESIDUAL_CONTINUATION_DIGEST', {'digest': out['output']}

        return super()._execute_selected(
            core,
            capability,
            goal,
            timeout=timeout,
            resolver=resolver,
            transport=transport,
            fetch_override=fetch_override,
        )

    def snapshot(self):
        events = self.state.get('events') or []
        selected = [row.get('selected_capability') for row in events]
        unknown = self.route('evaluate an unclassified quantum biology hypothesis')
        artifacts = self.state.get('artifacts') or {}
        chain = self.verify_chain()
        residual_goal_count = max(0, len(events) - 5)
        complete = (
            len(events) == 7
            and residual_goal_count == 2
            and 'resource_validation_plan' in artifacts
            and 'continuation_digest' in artifacts
            and self.derive_next_goal() is None
            and chain.get('status') == 'PASS'
        )
        pass_gate = complete and unknown.get('status') == 'WITHHOLD_ROUTER_NO_MATCH'
        dynamic_source_bound = False
        first = self._first_resource()
        if len(events) >= 6 and first is not None:
            dynamic_source_bound = first['name'].lower() in str(events[5].get('goal', '')).lower()

        return {
            'schema': SCHEMA,
            'component_id': COMPONENT_ID,
            'status': (
                'PASS_SHADOW_EXTERNAL_DEV_RESIDUAL_CONTINUATION_V2'
                if pass_gate
                else 'IN_PROGRESS_EXTERNAL_DEV_RESIDUAL_CONTINUATION_V2'
            ),
            'objective': self.state.get('objective'),
            'goal_count': len(events),
            'base_goal_count': min(5, len(events)),
            'residual_goal_count': residual_goal_count,
            'selected_capabilities': selected,
            'distinct_capability_count': len(set(selected)),
            'events': clone(events),
            'restart_count': self.state.get('restart_count', 0),
            'chain_verification': chain,
            'router_source_sha256': self.router_source_sha256,
            'router_policy_sha256': self.state.get('router_policy_sha256'),
            'unknown_withhold': unknown.get('status') == 'WITHHOLD_ROUTER_NO_MATCH',
            'post_fixed_goal_derived_from_live_state': dynamic_source_bound,
            'resource_candidate': first,
            'continuation_digest': (artifacts.get('continuation_digest') or {}).get('output'),
            'third_party_code_executed': False,
            'third_party_code_copied': False,
            'credentials_used': False,
            'private_network_access': False,
            'external_writes_to_third_parties': False,
            'automatic_main_mutation': False,
            'g3_genesis_performed': False,
            'next_goal': self.derive_next_goal(),
        }

    def final_receipt(self):
        out = self.snapshot()
        out['state_sha256'] = self.export_state()['state_sha256']
        out['receipt_sha256'] = digest(out)
        return out


__all__ = ['ExternalDevResidualContinuationV2']
