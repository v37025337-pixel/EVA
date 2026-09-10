"""Fresh native-only self-rewrite gate. Historical LLM transport is not executed."""
from __future__ import annotations
from pathlib import Path
import argparse, io, json, subprocess, sys, tempfile, unittest, uuid

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parent
sys.path[:0] = [str(ROOT), str(ROOT/'yado_rc8_v36'), str(REPO/'tests')]
from yado_g2_autonomous_self_rewrite_v1 import canonical_snapshot, fsha, load, MODE, REQUEST, TASK
from yado_g2_native_semantic_ast_backend_v1 import digest

OUT = REPO/'candidates/kernel-self-generated/g2-self-rewrite-repaired-controller-fresh-regression-gate-v1.json'
REGRESSION_MODULES = [
    'test_yado_rc8_self_audit_consistency_v1',
    'test_yado_external_runtime_contract_v1',
    'test_yado_skill_admission_runtime_v1',
    'test_yado_transfer_evaluation_runtime_v1',
    'test_yado_native_self_rewrite_v1',
]


def invoke(script, output, extra=()):
    proc = subprocess.run([sys.executable,str(ROOT/script),'--output',str(output),*extra],
                          cwd=REPO,capture_output=True,text=True,timeout=180)
    return {'exit_code':proc.returncode,'stdout':proc.stdout,'stderr':proc.stderr,
            'receipt':load(output) if output.exists() else None}


def regression():
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromNames(REGRESSION_MODULES)
    expected = suite.countTestCases()
    stream = io.StringIO()
    result = unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
    passed = (not loader.errors and result.wasSuccessful() and result.testsRun == expected
              and expected >= 36 and not result.skipped and not result.expectedFailures)
    return {'pass':passed,'tests_expected':expected,'tests_run':result.testsRun,
            'failures':len(result.failures),'errors':len(result.errors),'skipped':len(result.skipped),
            'modules':REGRESSION_MODULES,'log':stream.getvalue()}


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('--output',type=Path,default=OUT)
    args = parser.parse_args(argv)
    args.output.unlink(missing_ok=True)
    before = canonical_snapshot(REPO)
    task = load(REPO/TASK)
    run_id = uuid.uuid4().hex
    # Track the executable tree, not only the cached canonical-head object.
    code_paths = sorted((REPO/'runtime').rglob('*.py')) + sorted((REPO/'tests').rglob('*.py'))
    code_before = {str(p.relative_to(REPO)):fsha(p) for p in code_paths}
    with tempfile.TemporaryDirectory(prefix='yado-fresh-native-gate-') as td:
        td = Path(td)
        rewrite = invoke('yado_g2_autonomous_self_rewrite_v1.py',td/'rewrite.json',('--run-id',run_id))
        fresh = invoke('yado_g2_autonomous_self_improvement_task_v1.py',td/'fresh.json')
    r = rewrite['receipt'] or {}
    f = fresh['receipt'] or {}
    reg = regression()
    compiled = subprocess.run([sys.executable,'-m','compileall','-q','runtime'],cwd=REPO,
                              capture_output=True,text=True,timeout=180)
    canonical_unchanged = before == canonical_snapshot(REPO)
    code_unchanged = all(fsha(REPO/rel) == value for rel,value in code_before.items())
    expected_id = task['task']['task_id']
    expected_goal = task['task']['goal']
    priority = r.get('kernel_selected_priority') or {}
    action_result = (f.get('goal_action_binding') or {}).get('result') or {}
    fresh_intake = bool(
        f.get('kernel_selected_next_step') == expected_id
        and f.get('task') == task
        and priority.get('code') == expected_id
        and priority.get('recommended_action') == expected_goal
        and f.get('selected_action') is None
        and action_result.get('missing_capability') == expected_id
        and action_result.get('status') == 'WITHHOLD_EXTERNAL_GOAL_CAPABILITY_DEFICIT'
        and f.get('direct_priority_evidence') is False
    )
    candidate_exists = bool(r.get('candidate_path'))
    checks = {
        'rewrite_process_finished_with_report':rewrite['exit_code'] in (0,2) and bool(r),
        'fresh_goal_process_finished_with_report':fresh['exit_code'] in (0,2) and bool(f),
        'fresh_run_identity_matches':r.get('run_id') == run_id,
        'rewrite_consumed_current_request':r.get('inputs_sha256',{}).get(TASK) == fsha(REPO/TASK),
        'source_contract_is_native_only':load(REPO/REQUEST).get('source_generation') == MODE,
        'external_models_unused':r.get('external_models_used') is False,
        'fresh_goal_preserved_as_explicit_deficit':fresh_intake,
        'candidate_source_created_for_current_goal':candidate_exists,
        # Neither intake repair nor historical replay is fresh candidate evidence.
        'fresh_candidate_validation_pass':r.get('fresh_candidate_validation') == 'PASS',
        'native_admission_pass':bool(r.get('selected_skill_id')),
        'compileall_pass':compiled.returncode == 0,
        'selected_regression_suite_pass':reg['pass'],
        'canonical_and_ledger_bytes_unchanged':canonical_unchanged,
        'tested_source_bytes_unchanged':code_unchanged,
    }
    passed = all(checks.values())
    status = ('PASS_SHADOW_G2_SELF_REWRITE_REPAIRED_CONTROLLER_FRESH_REGRESSION_GATE_V1' if passed
              else 'WITHHOLD_G2_SELF_REWRITE_REPAIRED_CONTROLLER_FRESH_REGRESSION_GATE_V1')
    report = {'schema':'yado.g2.self_rewrite_repaired_controller_fresh_regression_gate.v1',
              'status':status,'run_id':run_id,'checks':checks,
              'rewrite':rewrite,'fresh_external_goal':fresh,'regression':reg,
              'compileall':{'exit_code':compiled.returncode,'stdout':compiled.stdout,'stderr':compiled.stderr},
              'tested_sources_sha256':code_before,'canonical_before_sha256':before,
              'candidate_admission':'NOT_RUN_NO_CANDIDATE' if not candidate_exists else 'WITHHOLD_MISSING_GOAL_SPECIFIC_FRESH_VALIDATION',
              'next_required_capability':r.get('next_required_capability'),
              'canonical_mutation':False,'promotion_applied':False,
              'semantic_boundary':'This gate runs the current native routing integration, not an old LLM-repaired controller artifact. Fresh task handoff and host integration tests do not establish self-authored semantic repair or canonical admission.'}
    report['receipt_sha256'] = digest(report)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'status':status,'checks':checks,'regression_tests':reg['tests_run'],
                      'next_required_capability':report['next_required_capability'],
                      'receipt_sha256':report['receipt_sha256']},indent=2))
    return 0 if passed else 2


if __name__ == '__main__':
    raise SystemExit(main())
