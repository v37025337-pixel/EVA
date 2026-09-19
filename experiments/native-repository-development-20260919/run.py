"""Observe existing YADO-native code generation and repository task selection.

No candidate implementation or policy is supplied by this run harness.
The inherited generators remain bounded, maintainer-designed mechanisms.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'runtime'))
sys.path.insert(0, str(ROOT))
from yado_active_kernel_contract_v1 import active_kernel_identity
from yado_external_dev_self_development_v1 import ExternalDevSelfDevelopmentV1
from yado_unified_core_external_dev_residual_continuation_v2 import UnifiedYADOCoreExternalDevResidualContinuationV2
from successor.hivemind_client import ISSUE_TOOLS


def save(out, name, value):
    (out / (name + '.json')).write_text(json.dumps(value, sort_keys=True, indent=2) + '\n')
    print('YADO_EVIDENCE ' + json.dumps({'name': name, 'value': value}, sort_keys=True), flush=True)


def main(out):
    out.mkdir(parents=True, exist_ok=True)
    save(out, 'summary', {'status': 'WITHHOLD_INCOMPLETE_RUN'})
    identity = active_kernel_identity(ROOT)
    core = UnifiedYADOCoreExternalDevResidualContinuationV2(ROOT)
    assert core.audit()['pass'] is True
    capabilities = {
        'kernel_identity': identity, 'hive_executable_available': shutil.which('hive') is not None,
        'hivemind_client_tools': sorted(ISSUE_TOOLS),
        'agent_conversation_channel': 'NOT_IMPLEMENTED_BY_CURRENT_HIVEMIND_CLIENT',
        'repository_write_channel': 'NOT_IMPLEMENTED_BY_CURRENT_EXTERNAL_DEV_PACK',
        'request': 'YADO itself studies its connected repositories, generates code, derives subsequent goals, and develops its layers and access adapters; the assistant observes.',
        'unfulfilled_objectives': ['GENERAL_NEW_ALGORITHM_INVENTION', 'EXTERNAL_AGENT_DIALOGUE', 'AUTONOMOUS_REPOSITORY_PATCH_EXECUTION'],
        'helper_authorship': 'MAINTAINER_RUN_HARNESS_ONLY',
    }
    save(out, 'observed_access_capabilities', capabilities)
    objective = 'Develop reusable source from verified repository experience, select tasks from measured deficits, and continue from retained state.'
    candidate = out / 'yado_generated_repository_router.py'
    try:
        development = core.external_dev_self_develop(
            objective, candidate_path=candidate, receipt_path=out / 'kernel_receipt.json', timeout=15)
        save(out, 'repository_self_development', development)
        assert development['status'] == 'PASS_SHADOW_EXTERNAL_DEV_SELF_DEVELOPMENT_V1', development
        source = candidate.read_text()
        original = ROOT / 'candidates/autonomous/yado_external_dev_capability_router_candidate_v1.py'
        before = ExternalDevSelfDevelopmentV1.evaluate_router_source(original.read_text())
        after = ExternalDevSelfDevelopmentV1.evaluate_router_source(source)
        comparison = {'existing_candidate_score': before['accuracy'], 'new_candidate_score': after['accuracy'],
                      'gain_over_existing_candidate': after['accuracy'] - before['accuracy'],
                      'source_changed': source != original.read_text(),
                      'candidate_sha256': hashlib.sha256(candidate.read_bytes()).hexdigest(),
                      'test_origin': 'EXISTING_FIVE_CASE_ROUTING_BENCHMARK_NOT_NEW_BLIND_TASKS',
                      'new_algorithm_invention_proven': False, 'general_capability_gain_proven': False}
        save(out, 'comparison_with_existing_candidate', comparison)
        print('YADO_GENERATED_SOURCE ' + json.dumps({'name': candidate.name, 'source': source}), flush=True)

        # Use precisely the bytes emitted by YADO, then restart over retained state.
        live = UnifiedYADOCoreExternalDevResidualContinuationV2(ROOT, router_path=candidate)
        controller = live.external_dev_campaign_controller
        controller.advance(live, objective, steps=3, timeout=15)
        state = controller.export_state()
        save(out, 'campaign_checkpoint', state)
        restarted = UnifiedYADOCoreExternalDevResidualContinuationV2(ROOT, router_path=candidate, campaign_state=state)
        final = restarted.external_dev_campaign_controller.advance(restarted, objective, steps=4, timeout=15)
        save(out, 'campaign_result', final)
        save(out, 'campaign_memory', restarted.external_dev_campaign_controller.export_state())
        assert final['status'] == 'PASS_SHADOW_EXTERNAL_DEV_RESIDUAL_CONTINUATION_V2', final
        assert final['goal_count'] == 7 and final['residual_goal_count'] == 2
        assert final['chain_verification']['status'] == 'PASS'
        assert active_kernel_identity(ROOT) == identity
        assert not subprocess.check_output(['git', 'diff', '--name-only', '--', 'runtime', 'successor', 'canonical', 'architecture'], cwd=ROOT).strip()
        save(out, 'summary', {'status': 'PASS_BOUNDED_NATIVE_REPOSITORY_CAMPAIGN',
                              'sources': development['used_source_patterns'], 'goals_completed': final['goal_count'],
                              'state_derived_residual_goals': final['residual_goal_count'],
                              'candidate_sha256': comparison['candidate_sha256'],
                              'gain_over_existing_candidate': comparison['gain_over_existing_candidate'],
                              'candidate_implementation_authored_this_run_by_assistant': False,
                              'generator_origin': 'INHERITED_BOUNDED_YADO_GENERATOR',
                              'canonical_unchanged': True, 'agent_conversation_performed': False,
                              'third_party_repository_patch_performed': False,
                              'unfulfilled_objectives': capabilities['unfulfilled_objectives']})
    except Exception as exc:
        save(out, 'summary', {'status': 'WITHHOLD_NATIVE_REPOSITORY_CAMPAIGN',
                             'error': type(exc).__name__ + ':' + str(exc)[:1500],
                             'canonical_identity_after': active_kernel_identity(ROOT)})
        raise


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--output', type=Path, required=True)
    main(p.parse_args().output.resolve())
