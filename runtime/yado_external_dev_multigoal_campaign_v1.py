from __future__ import annotations

import hashlib
import json
from pathlib import Path

from yado_external_dev_capability_pack_v1 import SOURCES
from yado_external_dev_self_development_v1 import ExternalDevSelfDevelopmentV1

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ROUTER = ROOT / 'candidates/autonomous/yado_external_dev_capability_router_candidate_v1.py'
COMPONENT_ID = 'RUNTIME-G2-EXTERNAL-DEV-MULTIGOAL-CAMPAIGN-V1'
SCHEMA = 'yado.external_dev_multigoal_campaign.v1'
FORBIDDEN_GOAL_NAMES = ('hivemind', 'hoppscotch', 'dyad', 'nexustools', 'free-for-dev')


def canon(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, default=str)


def digest(value):
    payload = value if isinstance(value, str) else canon(value)
    return hashlib.sha256(payload.encode('utf-8')).hexdigest()


def clone(value):
    return json.loads(json.dumps(value, ensure_ascii=False, default=str))


class ExternalDevMultiGoalCampaignV1:
    def __init__(self, router_path=None, state=None):
        self.router_path = Path(router_path or DEFAULT_ROUTER)
        source = self.router_path.read_text(encoding='utf-8')
        self.router_source_sha256 = digest(source)
        self.route, self.router_snapshot_fn = ExternalDevSelfDevelopmentV1.load_router(source)
        router_snapshot = self.router_snapshot_fn()
        if router_snapshot.get('capability_count') != 5:
            raise RuntimeError('CAMPAIGN_ROUTER_CAPABILITY_COUNT_MISMATCH')
        if state is None:
            self.state = {
                'schema': SCHEMA,
                'component_id': COMPONENT_ID,
                'objective': None,
                'router_source_sha256': self.router_source_sha256,
                'router_policy_sha256': router_snapshot.get('policy_sha256'),
                'artifacts': {},
                'events': [],
                'restart_count': 0,
            }
        else:
            self.state = self.restore_state(state)

    @staticmethod
    def _goal_names_absent(text):
        low = str(text).lower()
        return all(name not in low for name in FORBIDDEN_GOAL_NAMES)

    def _event_digest(self, event):
        return digest(event)

    def verify_chain(self, state=None):
        current = state or self.state
        prev = None
        for index, row in enumerate(current.get('events') or [], start=1):
            if row.get('cycle') != index:
                raise RuntimeError('CAMPAIGN_EVENT_CYCLE_DISCONTINUITY')
            if row.get('previous_event_sha256') != prev:
                raise RuntimeError('CAMPAIGN_EVENT_CHAIN_BROKEN')
            base = dict(row)
            recorded = base.pop('event_sha256', None)
            if recorded != self._event_digest(base):
                raise RuntimeError('CAMPAIGN_EVENT_DIGEST_MISMATCH')
            prev = recorded
        return {'status': 'PASS', 'event_count': len(current.get('events') or []), 'head_event_sha256': prev}

    def export_state(self):
        self.verify_chain()
        body = clone(self.state)
        body['state_sha256'] = digest(body)
        return body

    def restore_state(self, value):
        body = clone(value)
        recorded = body.pop('state_sha256', None)
        if recorded is not None and recorded != digest(body):
            raise RuntimeError('CAMPAIGN_STATE_DIGEST_MISMATCH')
        if body.get('router_source_sha256') != self.router_source_sha256:
            raise RuntimeError('CAMPAIGN_ROUTER_SOURCE_DRIFT')
        if body.get('schema') != SCHEMA:
            raise RuntimeError('CAMPAIGN_STATE_SCHEMA_MISMATCH')
        self.verify_chain(body)
        body['restart_count'] = int(body.get('restart_count', 0)) + 1
        return body

    def derive_next_goal(self):
        objective = self.state.get('objective') or ''
        a = self.state['artifacts']
        if 'task_contract' not in a:
            return f"Turn the broad development objective '{objective}' into an isolated work plan with explicit review criteria before any change."
        if 'api_probe' not in a:
            count = len(a['task_contract'].get('acceptance_criteria') or [])
            return f"The work plan now has {count} acceptance checks, but current upstream repository identity has not been independently confirmed through a public endpoint response."
        if 'build_plan' not in a:
            status = a['api_probe'].get('status')
            return f"Upstream evidence returned {status}; prepare a local candidate preview with compile, tests, regression and an admission gate before any integration."
        if 'evidence_digest' not in a:
            phases = len(a['build_plan'].get('phases') or [])
            return f"The candidate plan contains {phases} phases; canonicalize the campaign evidence and freeze an offline digest so continuation can detect drift."
        if 'resource_options' not in a:
            prefix = str(a['evidence_digest'].get('output') or '')[:12]
            return f"Evidence identity {prefix} is frozen; find a free serverless or compute option for a disposable future validation run without creating an account or changing an external service."
        return None

    def _execute_selected(self, core, capability, goal, *, timeout=25.0, resolver=None, transport=None, fetch_override=None):
        a = self.state['artifacts']
        if capability == 'TASK_CONTRACT_AND_AGENT_SUPERVISION_PATTERN':
            out = core.external_dev_task_contract(self.state['objective'], [
                'router selects from deficit text without a host tool name',
                'campaign state survives a process restart',
                'all external access remains read-only and credential-free',
                'five causally chained goals complete before admission',
            ])
            a['task_contract'] = out
            return 'PASS_TASK_CONTRACT', {'criteria': len(out.get('acceptance_criteria') or [])}
        if capability == 'READ_ONLY_API_ASSERTION_WORKBENCH':
            out = core.external_dev_api_probe(
                SOURCES['hivemind']['metadata'], must_contain='dip497/hivemind', timeout=timeout,
                resolver=resolver, transport=transport, fetch_override=fetch_override,
            )
            if out.get('status') != 'PASS_READ_ONLY_API_ASSERTION' or out.get('read_only') is not True:
                raise RuntimeError('CAMPAIGN_API_PROBE_FAILED')
            a['api_probe'] = out
            return out['status'], {'http_status': out.get('http_status'), 'sha256': out.get('sha256')}
        if capability == 'LOCAL_APP_BUILD_ADMISSION_LOOP':
            out = core.external_dev_app_build_plan(
                'Bind the admitted router into a restartable five-goal development campaign',
                'Python stdlib + current YADO G2 core',
                ['compile', 'fresh-router-selection', 'restart-continuity', 'full-regression'],
            )
            a['build_plan'] = out
            return 'PASS_BUILD_PLAN', {'phases': len(out.get('phases') or [])}
        if capability == 'PURE_LOCAL_DEV_UTILITY_LIBRARY':
            frozen = {'objective': self.state['objective'], 'events': self.state['events'], 'artifact_keys': sorted(a)}
            out = core.external_dev_utility('sha256', canon(frozen))
            if out.get('network_used') is not False or len(out.get('output', '')) != 64:
                raise RuntimeError('CAMPAIGN_LOCAL_DIGEST_FAILED')
            a['evidence_digest'] = out
            return 'PASS_LOCAL_EVIDENCE_DIGEST', {'digest': out['output']}
        if capability == 'FREE_TIER_RESOURCE_DISCOVERY':
            out = core.external_dev_free_resource_candidates(
                ['serverless', 'compute', 'ci'], limit=8, timeout=timeout,
                resolver=resolver, transport=transport, fetch_override=fetch_override,
            )
            if out.get('status') != 'PASS_FREE_TIER_RESOURCE_DISCOVERY' or int(out.get('result_count', 0)) < 1:
                raise RuntimeError('CAMPAIGN_FREE_RESOURCE_DISCOVERY_FAILED')
            if out.get('credentials_used') is not False or out.get('external_write') is not False:
                raise RuntimeError('CAMPAIGN_RESOURCE_DISCOVERY_SAFETY_MISMATCH')
            a['resource_options'] = out
            return out['status'], {'result_count': out.get('result_count'), 'catalog_sha256': out.get('catalog_sha256')}
        raise RuntimeError('CAMPAIGN_UNSUPPORTED_ROUTED_CAPABILITY:' + str(capability))

    def advance(self, core, objective, *, steps=1, timeout=25.0, resolver=None, transport=None, fetch_override=None):
        objective = ' '.join(str(objective or '').split()).strip()
        if not objective:
            raise ValueError('CAMPAIGN_OBJECTIVE_REQUIRED')
        if self.state.get('objective') is None:
            self.state['objective'] = objective
        elif self.state['objective'] != objective:
            raise RuntimeError('CAMPAIGN_OBJECTIVE_DRIFT')
        for _ in range(int(steps)):
            goal = self.derive_next_goal()
            if goal is None:
                break
            if not self._goal_names_absent(goal):
                raise RuntimeError('CAMPAIGN_GOAL_LEAKS_SOURCE_NAME')
            routed = self.route(goal)
            if routed.get('status') != 'PASS_ROUTER_SELECTION' or not routed.get('capability'):
                raise RuntimeError('CAMPAIGN_ROUTER_WITHHOLD_ON_REQUIRED_GOAL')
            status, result = self._execute_selected(
                core, routed['capability'], goal, timeout=timeout,
                resolver=resolver, transport=transport, fetch_override=fetch_override,
            )
            previous = self.state['events'][-1]['event_sha256'] if self.state['events'] else None
            event = {
                'cycle': len(self.state['events']) + 1,
                'goal': goal,
                'goal_derived_from_state': True,
                'selected_capability': routed['capability'],
                'matched': list(routed.get('matched') or []),
                'router_score': routed.get('score'),
                'result_status': status,
                'result_summary': result,
                'previous_event_sha256': previous,
            }
            event['event_sha256'] = self._event_digest(event)
            self.state['events'].append(event)
            self.verify_chain()
        return self.snapshot()

    def snapshot(self):
        events = self.state.get('events') or []
        selected = [x.get('selected_capability') for x in events]
        unknown = self.route('evaluate an unclassified quantum biology hypothesis')
        complete = len(events) == 5 and self.derive_next_goal() is None
        pass_gate = complete and len(set(selected)) == 5 and unknown.get('status') == 'WITHHOLD_ROUTER_NO_MATCH'
        return {
            'schema': SCHEMA,
            'component_id': COMPONENT_ID,
            'status': 'PASS_SHADOW_EXTERNAL_DEV_MULTIGOAL_CAMPAIGN_V1' if pass_gate else 'IN_PROGRESS_EXTERNAL_DEV_MULTIGOAL_CAMPAIGN_V1',
            'objective': self.state.get('objective'),
            'goal_count': len(events),
            'selected_capabilities': selected,
            'distinct_capability_count': len(set(selected)),
            'events': clone(events),
            'restart_count': self.state.get('restart_count', 0),
            'chain_verification': self.verify_chain(),
            'router_source_sha256': self.router_source_sha256,
            'router_policy_sha256': self.state.get('router_policy_sha256'),
            'unknown_withhold': unknown.get('status') == 'WITHHOLD_ROUTER_NO_MATCH',
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


__all__ = ['ExternalDevMultiGoalCampaignV1']
