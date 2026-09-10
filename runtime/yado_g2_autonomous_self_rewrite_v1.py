"""Bounded native-source proposal transport; fresh admission remains mandatory."""
from __future__ import annotations
from pathlib import Path
import argparse, hashlib, json, re, sys, tempfile, uuid
from dataclasses import asdict

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parent
sys.path[:0] = [str(ROOT), str(ROOT / 'yado_rc8_v36')]
from yado_g2_goal_action_binding_v1 import YADOGoalActionBindingV1
from yado_g2_native_semantic_ast_backend_v1 import propose, digest

REQUEST = 'architecture/yado-kernel-autonomous-self-rewrite-v1-request.json'
TASK = 'architecture/yado-kernel-autonomous-self-improvement-v1-request.json'
OUTPUT = 'candidates/kernel-self-generated/g2-autonomous-self-rewrite-v1.json'
MODE = 'NATIVE_SEMANTIC_AST_ONLY'


def load(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def fsha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def latest_audit(repo):
    paths = [p for p in (repo / 'receipts').glob('yado-unified-core-deep-self-audit-v1-run-*.json')
             if re.search(r'run-(\d+)\.json$', p.name)]
    if not paths:
        raise ValueError('NO_DEEP_SELF_AUDIT')
    path = max(paths, key=lambda p: int(re.search(r'run-(\d+)\.json$', p.name).group(1)))
    data = load(path)
    if data.get('status') != 'PASS_YADO_UNIFIED_CORE_DEEP_SELF_AUDIT_V1':
        raise ValueError('LATEST_DEEP_SELF_AUDIT_NOT_PASS')
    return path, data


def canonical_snapshot(repo):
    paths = sorted((repo / 'canonical').glob('*.json')) + [repo / 'architecture/evolution-ledger.json']
    return {str(p.relative_to(repo)): fsha(p) for p in paths}


def run(repo, run_id):
    repo = Path(repo).resolve()
    if repo != REPO.resolve():
        raise ValueError('EXECUTABLE_REPOSITORY_MISMATCH')
    request, task = load(repo / REQUEST), load(repo / TASK)
    before = canonical_snapshot(repo)
    inputs = {rel: fsha(repo / rel) for rel in (REQUEST, TASK,
              'runtime/yado_g2_autonomous_self_rewrite_v1.py',
              'runtime/yado_g2_goal_action_binding_v1.py',
              'runtime/yado_g2_native_semantic_ast_backend_v1.py')}
    auth = task.get('authorization') or {}
    if request.get('source_generation') != MODE or request.get('external_model_fallback') is not False:
        raise ValueError('NATIVE_ONLY_SOURCE_CONTRACT_REQUIRED')
    if not (auth.get('self_selected_code_rewrite') is True and auth.get('repository_write') is True):
        raise ValueError('SELF_REWRITE_AUTHORIZATION_MISSING')
    if request.get('canonical_mutation') is not False or request.get('execute_untrusted_candidate') is not False:
        raise ValueError('SHADOW_ONLY_CONTRACT_REQUIRED')
    audit_path, audit = latest_audit(repo)
    inputs[str(audit_path.relative_to(repo))] = fsha(audit_path)
    intake = YADOGoalActionBindingV1.resolve_goal(task, audit)
    priority = (intake['priority'] or [None])[0]
    backend = {'status': intake['status'], 'candidate_source': None}
    if priority is not None:
        backend = propose(repo, priority)
    inputs.update(backend.get('lineage_sha256') or {})
    source = backend.pop('candidate_source', None)
    candidate_path = None
    if source is not None:
        candidate_path = 'candidates/g2-self-evolution/' + Path(backend['target_path']).stem + '_' + backend['candidate_sha256'][:16] + '_autonomous_candidate_v1.py'
        path = repo / candidate_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(source, encoding='utf-8')
    # The existing kernel owns deficit registration and skill admission. Compile
    # alone supplies no semantic/heldout score; no unmeasured PASS is submitted.
    from yado_core_v3_0_rc8_external_cognitive import UnifiedYADOKernelV30RC8ExternalCognitive
    with tempfile.TemporaryDirectory(prefix='yado-native-rewrite-') as td:
        kernel = UnifiedYADOKernelV30RC8ExternalCognitive(db_path=str(Path(td) / 'state.sqlite'))
        try:
            native_goal = None
            if priority is not None:
                goal = kernel.executive.create_goal(
                    objective=priority['recommended_action'],
                    required_capabilities={priority['code']: 1.0},
                    success_criteria={'external_contract': priority.get('success_conditions', []),
                                      'fresh_validation_required': True})
                native_goal = {'goal_id': goal.goal_id, 'objective': goal.objective,
                               'capability_registry_scope': 'TEMPORARY_PROBE',
                               'deficits': [asdict(d) for d in kernel.executive.detect_deficits(goal.goal_id)]}
            selection = kernel.select_evolution_skills(
                [], max_skills=1, min_semantic_consistency=.90, min_fit_gain=.50,
                max_heldout_drop=0, min_heldout_gain=.50)
        finally:
            kernel.close()
    after = canonical_snapshot(repo)
    unchanged_inputs = all(fsha(repo / rel) == value for rel, value in inputs.items())
    report = {
        'schema': 'yado.g2.autonomous_self_rewrite.v1',
        'status': 'WITHHOLD_G2_AUTONOMOUS_SELF_REWRITE_V1',
        'run_id': run_id, 'source_generation': MODE, 'inputs_sha256': inputs,
        'inputs_unchanged': unchanged_inputs, 'goal_intake': intake,
        'kernel_selected_priority': priority, 'native_goal': native_goal,
        'source_proposal': backend, 'kernel_selection': selection,
        'target_selection': {'selected_path': backend.get('target_path'),
                             'origin': 'EXISTING_NATIVE_SEMANTIC_LINEAGE'},
        'candidate_path': candidate_path, 'candidate_source_sha256': backend.get('candidate_sha256'),
        'candidate_executed': False, 'fresh_candidate_validation': 'NOT_RUN',
        'regression_admission': 'NOT_RUN', 'selected_skill_id': None,
        'external_models_used': False, 'external_model_proposed_candidate_source': False,
        'host_selected_target': False, 'host_wrote_candidate_source': False,
        'host_created_goal_intake_transport': True, 'host_created_backend_transport': True,
        'canonical_mutation': False, 'canonical_head_unchanged': before == after,
        'canonical_before_sha256': before, 'canonical_after_sha256': after,
        'next_required_capability': backend.get('next_required_capability', 'FRESH_SOURCE_ADMISSION_GATE'),
        'semantic_boundary': 'Host-authored routing and V18 AST placement transport. Source operands, context and target come from existing YADO artifacts. No new semantic operator is invented by this adapter. Missing fresh/heldout/regression evidence never counts as admission.'}
    report['receipt_sha256'] = digest(report)
    return report


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('--repo', type=Path, default=REPO)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--run-id', default=uuid.uuid4().hex)
    args = parser.parse_args(argv)
    output = args.output or args.repo / OUTPUT
    output.unlink(missing_ok=True)
    try:
        report = run(args.repo, args.run_id)
    except (ValueError, KeyError, OSError, RuntimeError) as exc:
        report = {'status': 'WITHHOLD_G2_AUTONOMOUS_SELF_REWRITE_V1', 'run_id': args.run_id,
                  'error': type(exc).__name__ + ':' + str(exc), 'candidate_path': None,
                  'canonical_mutation': False, 'external_models_used': False}
        report['receipt_sha256'] = digest(report)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    print(json.dumps({k: report.get(k) for k in ('status', 'run_id', 'candidate_path',
                     'kernel_selected_priority', 'next_required_capability', 'error', 'receipt_sha256')}, indent=2))
    return 2


if __name__ == '__main__':
    raise SystemExit(main())
