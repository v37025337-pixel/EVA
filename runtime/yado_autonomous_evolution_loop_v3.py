from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parent
OUT = REPO / 'candidates/autonomous/yado-autonomous-evolution-loop-v3.json'
GENERATIONS = 3


def sha_text(text: str) -> str:
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def run(cmd, cwd: Path, timeout: int = 240):
    cp = subprocess.run(cmd, cwd=cwd, env={**os.environ, 'PYTHONPATH': f"{cwd/'runtime'}:{cwd/'runtime/yado_rc8_v36'}"}, capture_output=True, text=True, timeout=timeout)
    if cp.returncode != 0:
        raise RuntimeError('SUBPROCESS_FAILED:' + ' '.join(map(str, cmd)) + '\n' + cp.stdout[-4000:] + '\n' + cp.stderr[-4000:])
    return cp


def load(path: Path):
    return json.loads(path.read_text(encoding='utf-8'))


def main():
    parent = REPO / 'runtime/yado_bounded_autonomous_learning_v1.py'
    if not parent.exists():
        raise RuntimeError('PARENT_RUNTIME_MISSING')
    initial_sha = sha_text(parent.read_text(encoding='utf-8'))
    rows = []

    with tempfile.TemporaryDirectory(prefix='yado-v3-evolution-') as td:
        work = Path(td) / 'repo'
        shutil.copytree(REPO, work, ignore=shutil.ignore_patterns('.git', '__pycache__', '*.pyc', '*.sqlite'))
        target = work / 'runtime/yado_bounded_autonomous_learning_v1.py'
        previous_sha = sha_text(target.read_text(encoding='utf-8'))
        previous_experience_digest = None

        for generation in range(1, GENERATIONS + 1):
            # 1) Current generation gathers fresh bounded public-web experience.
            run([sys.executable, 'runtime/yado_bounded_autonomous_learning_v1.py'], work)
            exp = load(work / 'experience/autonomous/yado-autonomous-learning-latest.json')
            if exp.get('status') != 'PASS_SHADOW_BOUNDED_AUTONOMOUS_EXTERNAL_LEARNING_V1':
                raise RuntimeError('LEARNING_PASS_REQUIRED')
            policy = exp.get('network_policy') or {}
            if policy.get('credentials_allowed') is not False or policy.get('external_writes') is not False or policy.get('downloaded_code_executed') is not False:
                raise RuntimeError('UNSAFE_NETWORK_POLICY')
            if not exp.get('sources'):
                raise RuntimeError('NO_SUCCESSFUL_LEARNING_SOURCE')

            # 2) The already-admitted V2 mechanism rewrites the CURRENT parent.
            run([sys.executable, 'runtime/yado_native_experience_to_runtime_self_rewrite_v2.py'], work)
            receipt = load(work / 'candidates/autonomous/yado-native-experience-to-runtime-self-rewrite-v2.json')
            if receipt.get('status') != 'PASS_SHADOW_NATIVE_EXPERIENCE_TO_RUNTIME_SELF_REWRITE_CANDIDATE_V2':
                raise RuntimeError('V2_REWRITE_PASS_REQUIRED')
            candidate = work / receipt['candidate_path']
            candidate_src = candidate.read_text(encoding='utf-8')
            candidate_sha = sha_text(candidate_src)
            if receipt.get('parent_sha256') != previous_sha:
                raise RuntimeError('PARENT_SHA_CHAIN_BREAK')
            if candidate_sha == previous_sha:
                raise RuntimeError('NO_SOURCE_CHANGE')

            # 3) Candidate becomes next-generation runtime inside the isolated lineage only.
            target.write_text(candidate_src, encoding='utf-8')
            run([sys.executable, '-m', 'py_compile', str(target.relative_to(work))], work)

            # 4) Execute evolved runtime again and prove prior experience affects selection.
            run([sys.executable, str(target.relative_to(work))], work)
            evolved_exp = load(work / 'experience/autonomous/yado-autonomous-learning-latest.json')
            evolved_receipt = load(work / 'candidates/autonomous/yado-bounded-autonomous-learning-v1.json')
            if evolved_receipt.get('status') != 'PASS_SHADOW_BOUNDED_AUTONOMOUS_EXTERNAL_LEARNING_V1':
                raise RuntimeError('EVOLVED_RUNTIME_EXECUTION_FAILED')
            ranking = evolved_exp.get('source_ranking') or []
            top = [x.get('id') for x in ranking[:3]]
            prior_success = receipt.get('learned_binding', {}).get('successful_source_ids') or []
            if not prior_success or not any(x in top for x in prior_success):
                raise RuntimeError('EXPERIENCE_DID_NOT_INFLUENCE_NEXT_SELECTION')

            current_exp_digest = evolved_exp.get('experience_digest')
            rows.append({
                'generation': generation,
                'parent_sha256': previous_sha,
                'candidate_sha256': candidate_sha,
                'input_experience_digest': exp.get('experience_digest'),
                'output_experience_digest': current_exp_digest,
                'prior_success_ids': prior_success,
                'top_ranked_source_ids': top,
                'successful_sources': len(evolved_exp.get('sources') or []),
                'fact_count': sum(len(x.get('facts', [])) for x in evolved_exp.get('sources', [])),
                'network_read_only': True,
                'credentials_used': False,
                'external_writes': False,
                'downloaded_code_executed': False,
            })
            previous_sha = candidate_sha
            previous_experience_digest = current_exp_digest

        # Final isolated regression after the third generation.
        run([sys.executable, '-m', 'compileall', '-q', 'runtime', 'successor'], work, timeout=300)
        run([sys.executable, '-m', 'unittest', 'discover', '-s', 'successor/tests', '-p', 'test_*.py'], work, timeout=300)
        run([sys.executable, '-m', 'unittest',
             'runtime/yado_rc8_v36/test_yado_rc8_self_audit_consistency_v1.py',
             'runtime/yado_rc8_v36/test_yado_external_runtime_contract_v1.py',
             'runtime/yado_rc8_v36/test_yado_skill_admission_runtime_v1.py',
             'runtime/yado_rc8_v36/test_yado_transfer_evaluation_runtime_v1.py'], work, timeout=300)

    out = {
        'schema': 'yado.autonomous_evolution_loop.v3',
        'status': 'PASS_SHADOW_BOUNDED_MULTI_GENERATION_AUTONOMOUS_EVOLUTION_V3',
        'generation_count': len(rows),
        'required_generations': GENERATIONS,
        'initial_parent_sha256': initial_sha,
        'final_candidate_sha256': rows[-1]['candidate_sha256'],
        'final_experience_digest': previous_experience_digest,
        'generations': rows,
        'chain_continuity': all(rows[i]['parent_sha256'] == rows[i-1]['candidate_sha256'] for i in range(1, len(rows))),
        'external_model_used_for_rewrite': False,
        'network_scope': 'PUBLIC_HTTPS_READ_ONLY_ALLOWLISTED',
        'credentials_used': False,
        'external_writes': False,
        'downloaded_code_executed': False,
        'canonical_mutation': False,
        'automatic_main_mutation': False,
        'rollback_boundary': 'ISOLATED_LINEAGE_ONLY',
        'consciousness_claimed': False,
        'next_required_capability': 'COUNTERFACTUAL_MULTI_GENERATION_ADMISSION_V4',
        'semantic_boundary': 'Three chained isolated generations of bounded external learning -> experience-conditioned runtime rewrite -> evolved execution -> regression. Host workflow/controller still provides orchestration and safety boundaries.'
    }
    if len(rows) != GENERATIONS or not out['chain_continuity']:
        raise RuntimeError('GENERATION_CHAIN_INCOMPLETE')
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2, ensure_ascii=False, sort_keys=True) + '\n', encoding='utf-8')
    print(json.dumps({
        'status': out['status'],
        'generations': out['generation_count'],
        'final_candidate_sha256': out['final_candidate_sha256'],
        'final_experience_digest': out['final_experience_digest'],
        'chain_continuity': out['chain_continuity'],
        'next': out['next_required_capability'],
    }, indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
