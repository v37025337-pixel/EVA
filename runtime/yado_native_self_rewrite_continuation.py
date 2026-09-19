"""Continue evidence-binding rewrites from the verified active controller.

This is a pre-admission diagnostic, not a capability or promotion gate. The
historical V4 reproduction stays immutable. Every attempt has a new directory.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
from pathlib import Path
import subprocess
import sys

from yado_active_kernel_contract_v1 import active_kernel_identity
from yado_native_experience_to_runtime_self_rewrite_v3 import digest, synthesize_candidate
from yado_native_self_rewrite_v4_fresh_experience import (
    ROOT, TARGET, EXPERIENCE, _binding_from_source, _normalized_ast_digest,
)


def _save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + '\n')


def _sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _literal(source, name):
    assignments = [n for n in ast.parse(source).body if isinstance(n, ast.Assign)
                   and any(isinstance(t, ast.Name) and t.id == name for t in n.targets)]
    if len(assignments) != 1 or len(assignments[0].targets) != 1:
        raise ValueError('UNIQUE_LITERAL_REQUIRED:' + name)
    return ast.literal_eval(assignments[0].value)


def _validate_experience(exp, identity, catalog):
    if not isinstance(exp, dict) or exp.get('status') != 'PASS_SHADOW_BOUNDED_AUTONOMOUS_EXTERNAL_LEARNING_V1':
        raise ValueError('EXPERIENCE_NOT_VERIFIED')
    if exp.get('experience_digest') != digest({k: v for k, v in exp.items() if k != 'experience_digest'}):
        raise ValueError('EXPERIENCE_CONTENT_DIGEST_MISMATCH')
    policy = exp.get('network_policy') or {}
    if (policy.get('credentials_allowed') is not False or policy.get('external_writes') is not False
            or policy.get('downloaded_code_executed') is not False):
        raise ValueError('UNSAFE_EXPERIENCE_POLICY')
    origin = exp.get('execution_identity') or {}
    if any(origin.get(k) != identity[k] for k in ('controller_sha256', 'implementation_id')):
        raise ValueError('EXPERIENCE_PARENT_MISMATCH')
    sources, failures = exp.get('sources'), exp.get('failures')
    if not isinstance(sources, list) or not sources or not isinstance(failures, list):
        raise ValueError('EXPERIENCE_ROWS_REQUIRED')
    success_ids = [row['source_id'] for row in sources]
    failed_ids = [row['source_id'] for row in failures]
    if (len(set(success_ids)) != len(success_ids) or len(set(failed_ids)) != len(failed_ids)
            or set(success_ids) & set(failed_ids)):
        raise ValueError('AMBIGUOUS_SOURCE_OUTCOMES')
    known = {row['id'] for row in catalog}
    if not set(success_ids + failed_ids) <= known:
        raise ValueError('UNKNOWN_EXPERIENCE_SOURCE')
    if not all(isinstance(row.get('facts'), list) and all(isinstance(f, str) for f in row['facts'])
               for row in sources) or not any(row['facts'] for row in sources):
        raise ValueError('EXPERIENCE_FACTS_REQUIRED')


def _diagnose(root, output, priorities):
    observations = {}
    for variant in ('parent', 'candidate', 'ablated'):
        request = {'runtime_directory': str(root / 'runtime'),
                   'source': str(output / (variant + '.py')),
                   'sha256': _sha(output / (variant + '.py')), 'priorities': priorities}
        cp = subprocess.run(
            [sys.executable, '-I', '-B', str(Path(__file__).with_name('yado_rewrite_ranking_probe.py'))],
            input=json.dumps(request), capture_output=True, text=True, cwd=output, timeout=45,
        )
        if cp.returncode:
            raise ValueError('ISOLATED_RANKING_FAILED:' + variant + ':' + cp.stderr[-1000:])
        observations[variant] = json.loads(cp.stdout)
    _save(output / 'ranking-observations.json', observations)
    before, after, ablated = [observations[k]['rankings'] for k in ('parent', 'candidate', 'ablated')]
    if not (len(before) == len(after) == len(ablated) == len(priorities)):
        raise ValueError('INCOMPLETE_RANKING_OBSERVATIONS')
    limit = observations['parent']['selection_limit']
    if observations['candidate']['selection_limit'] != limit or observations['ablated']['selection_limit'] != limit:
        raise ValueError('SELECTION_BUDGET_CHANGED')
    selections = lambda rows: [r['id'] for r in rows[:limit]]
    return {'priority_count': len(priorities),
            'selection_changes': sum(selections(a) != selections(b) for a, b in zip(before, after)),
            'score_changes': sum(a != b for a, b in zip(before, after)),
            'ablation_restores_parent': before == ablated,
            'processes': [observations[k]['pid'] for k in ('parent', 'candidate', 'ablated')],
            'classification': 'CATALOG_DERIVED_DIAGNOSTIC_NOT_BLIND_TRANSFER'}


def continue_from_active(root: Path, output: Path, experience_path: Path | None = None):
    root, output = Path(root).resolve(), Path(output).resolve()
    for directory in ('runtime', 'successor', 'canonical', 'architecture', 'resources'):
        if output.is_relative_to(root / directory):
            raise ValueError('OUTPUT_MUST_NOT_OVERLAY_ACTIVE_SOURCES')
    output.mkdir(parents=True, exist_ok=False)
    result = {'schema': 'yado.current_parent_rewrite_attempt.v1', 'status': 'WITHHOLD',
              'active_admission_performed': False, 'runtime_mutation_applied': False,
              'capability_gain_claimed': False, 'g3_genesis_performed': False,
              'blind_evaluation_performed': False, 'full_candidate_regression_performed': False,
              'checks': {}, 'next_required_capability': 'REPAIR_OR_OBTAIN_EFFECTIVE_EXPERIENCE'}
    try:
        identity = active_kernel_identity(root)
        result['parent_identity'] = identity
        result['checks']['parent_verified'] = True
        target = root / TARGET
        parent = target.read_text(encoding='utf-8')
        if hashlib.sha256(parent.encode()).hexdigest() != identity['controller_sha256']:
            raise ValueError('PARENT_CHANGED_DURING_READ')
        catalog = _literal(parent, 'SOURCE_CATALOG')
        parent_binding = _literal(parent, 'LEARNED_EXTERNAL_EVIDENCE_V2')
        exp = json.loads(Path(experience_path or root / EXPERIENCE).read_text(encoding='utf-8'))
        _validate_experience(exp, identity, catalog)
        result['checks']['experience_content_verified'] = True
        result['experience_digest'] = exp['experience_digest']
        result['parent_experience_digest'] = parent_binding.get('experience_digest')
        if result['experience_digest'] == result['parent_experience_digest']:
            raise ValueError('NO_FRESH_EXPERIENCE')
        candidate, learned, safety = synthesize_candidate(parent, exp)
        if _normalized_ast_digest(parent) != _normalized_ast_digest(candidate):
            raise ValueError('UNSUPPORTED_STRUCTURAL_REWRITE')
        result['checks']['only_learned_binding_changed'] = True
        if _literal(candidate, 'LEARNED_EXTERNAL_EVIDENCE_V2') != learned:
            raise ValueError('CANDIDATE_BINDING_MISMATCH')
        # Restore the binding in the emitted program, then execute it as its own
        # process. A changed hash or a swapped in-process global is not evidence.
        tree = ast.parse(candidate)
        for node in tree.body:
            if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name)
                    and t.id == 'LEARNED_EXTERNAL_EVIDENCE_V2' for t in node.targets):
                node.value = ast.parse(repr(parent_binding), mode='eval').body
        ablated = ast.unparse(ast.fix_missing_locations(tree)) + '\n'
        for name, source in (('parent', parent), ('candidate', candidate), ('ablated', ablated)):
            compile(source, name, 'exec')
            (output / (name + '.py')).write_text(source, encoding='utf-8')
        _save(output / 'experience.json', exp)
        result.update(parent_runtime_sha256=identity['controller_sha256'],
                      candidate_sha256=_sha(output / 'candidate.py'), safety_delta=safety)
        priorities = [exp['priority']] + [
            {'code': row['id'], 'area': 'SOURCE_CATALOG_DIAGNOSTIC',
             'recommended_action': ' '.join(row['tags'])} for row in catalog]
        _save(output / 'diagnostic-priorities.json', priorities)
        diagnostic = _diagnose(root, output, priorities)
        result['diagnostic'] = diagnostic
        result['checks']['ablation_restores_parent'] = diagnostic['ablation_restores_parent']
        result['checks']['parent_unchanged'] = active_kernel_identity(root) == identity
        if not result['checks']['parent_unchanged']:
            raise ValueError('ACTIVE_PARENT_CHANGED_DURING_ATTEMPT')
        if not diagnostic['ablation_restores_parent']:
            raise ValueError('ABLATION_DID_NOT_RESTORE_PARENT')
        if not diagnostic['selection_changes']:
            raise ValueError('NO_OBSERVABLE_SELECTION_CHANGE')
        result.update(status='READY_FOR_INDEPENDENT_EVALUATION', reason='SELECTION_CHANGE_OBSERVED',
                      next_required_capability='FRESH_BLIND_UTILITY_AND_NEGATIVE_TRANSFER_THEN_FULL_REGRESSION')
    except (ValueError, RuntimeError, KeyError, TypeError, OSError, SyntaxError, subprocess.SubprocessError) as exc:
        result['reason'] = str(exc)
        result['error_type'] = type(exc).__name__
    _save(output / 'receipt.json', result)
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--experience', type=Path)
    args = parser.parse_args(argv)
    result = continue_from_active(args.root, args.output, args.experience)
    print(json.dumps(result, sort_keys=True))
    return 0 if result['status'] == 'READY_FOR_INDEPENDENT_EVALUATION' else 2


if __name__ == '__main__':
    raise SystemExit(main())
