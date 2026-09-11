from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parent
EXPERIENCE = REPO / 'experience/autonomous/yado-autonomous-learning-latest.json'
TARGET = ROOT / 'yado_bounded_autonomous_learning_v1.py'
CANDIDATE = REPO / 'candidates/autonomous/yado_bounded_autonomous_learning_runtime_candidate_v2.py'
RECEIPT = REPO / 'candidates/autonomous/yado-native-experience-to-runtime-self-rewrite-v2.json'


def canon(x):
    return json.dumps(x, sort_keys=True, separators=(',', ':'), ensure_ascii=False, default=str)


def digest(x):
    return hashlib.sha256(canon(x).encode('utf-8')).hexdigest()


def sha_text(x):
    return hashlib.sha256(x.encode('utf-8')).hexdigest()


def load(path):
    return json.loads(path.read_text(encoding='utf-8'))


def successful_source_ids(exp):
    return sorted({str(x.get('source_id')) for x in exp.get('sources', []) if x.get('source_id')})


def successful_hosts(exp):
    out = set()
    for x in exp.get('sources', []):
        host = ((x.get('network') or {}).get('host'))
        if host:
            out.add(str(host).lower())
    return sorted(out)


def prior_learning_tokens(exp):
    toks = set()
    for src in exp.get('sources', []):
        for fact in src.get('facts', []):
            for t in str(fact).lower().replace('/', ' ').replace('-', ' ').split():
                t = ''.join(ch for ch in t if ch.isalnum() or ch == '_')
                if len(t) >= 4:
                    toks.add(t)
                if len(toks) >= 96:
                    return sorted(toks)
    return sorted(toks)


def make_assignment(name, value):
    return ast.Assign(targets=[ast.Name(id=name, ctx=ast.Store())], value=ast.Constant(value=value))


def synthesize_candidate(parent_src, exp):
    tree = ast.parse(parent_src)
    evidence_digest = str(exp.get('experience_digest') or '')
    if not evidence_digest:
        raise RuntimeError('EXPERIENCE_DIGEST_MISSING')

    learned = {
        'experience_digest': evidence_digest,
        'successful_source_ids': successful_source_ids(exp),
        'successful_hosts': successful_hosts(exp),
        'fact_count': sum(len(x.get('facts', [])) for x in exp.get('sources', [])),
        'learning_tokens': prior_learning_tokens(exp),
    }

    insertion_index = 0
    for i, node in enumerate(tree.body):
        if isinstance(node, ast.ImportFrom) and node.module == '__future__':
            insertion_index = i + 1
    learned_assign = ast.Assign(
        targets=[ast.Name(id='LEARNED_EXTERNAL_EVIDENCE_V2', ctx=ast.Store())],
        value=ast.parse(repr(learned), mode='eval').body,
    )
    tree.body.insert(insertion_index, learned_assign)

    changed_rank = False
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef) or node.name != 'rank_sources':
            continue
        for idx, stmt in enumerate(node.body):
            if isinstance(stmt, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'q' for t in stmt.targets):
                augment = ast.parse("q |= set(LEARNED_EXTERNAL_EVIDENCE_V2.get('learning_tokens', []))").body[0]
                node.body.insert(idx + 1, augment)
                changed_rank = True
                break
    if not changed_rank:
        raise RuntimeError('RANK_SOURCES_ANCHOR_NOT_FOUND')

    # Add a small bonus to sources proven reachable in the previous experience.
    bonus_applied = False
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == 'rank_sources':
            for stmt in node.body:
                if isinstance(stmt, ast.For) and isinstance(stmt.target, ast.Name) and stmt.target.id == 'row':
                    for j, inner in enumerate(stmt.body):
                        if isinstance(inner, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'score' for t in inner.targets):
                            extra = ast.parse("score += 2 if row.get('id') in LEARNED_EXTERNAL_EVIDENCE_V2.get('successful_source_ids', []) else 0").body[0]
                            stmt.body.insert(j + 1, extra)
                            bonus_applied = True
                            break
    if not bonus_applied:
        raise RuntimeError('SOURCE_SCORE_ANCHOR_NOT_FOUND')

    ast.fix_missing_locations(tree)
    out = ast.unparse(tree) + '\n'
    compile(out, '<yado-native-experience-runtime-v2>', 'exec')
    if 'eval(' in out or 'exec(' in out or 'subprocess' in out:
        raise RuntimeError('UNSAFE_SOURCE_CONSTRUCT_ADDED')
    return out, learned


def main():
    exp = load(EXPERIENCE)
    if exp.get('status') != 'PASS_SHADOW_BOUNDED_AUTONOMOUS_EXTERNAL_LEARNING_V1':
        raise RuntimeError('V1_PASS_EXPERIENCE_REQUIRED')
    policy = exp.get('network_policy') or {}
    if policy.get('credentials_allowed') is not False or policy.get('external_writes') is not False:
        raise RuntimeError('UNSAFE_EXPERIENCE_POLICY')
    parent_src = TARGET.read_text(encoding='utf-8')
    parent_sha = sha_text(parent_src)
    candidate_src, learned = synthesize_candidate(parent_src, exp)
    candidate_sha = sha_text(candidate_src)
    if candidate_sha == parent_sha:
        raise RuntimeError('CANDIDATE_UNCHANGED')
    CANDIDATE.parent.mkdir(parents=True, exist_ok=True)
    CANDIDATE.write_text(candidate_src, encoding='utf-8')
    receipt = {
        'schema': 'yado.native_experience_to_runtime_self_rewrite.v2',
        'status': 'PASS_SHADOW_NATIVE_EXPERIENCE_TO_RUNTIME_SELF_REWRITE_CANDIDATE_V2',
        'target_path': str(TARGET.relative_to(REPO)),
        'parent_sha256': parent_sha,
        'candidate_path': str(CANDIDATE.relative_to(REPO)),
        'candidate_sha256': candidate_sha,
        'experience_digest': exp.get('experience_digest'),
        'learned_binding': learned,
        'native_ast_materialization': True,
        'external_model_used': False,
        'downloaded_code_executed': False,
        'credentials_used': False,
        'external_writes': False,
        'canonical_mutation': False,
        'automatic_main_mutation': False,
        'rollback_parent_sha256': parent_sha,
        'next_required_capability': 'ISOLATED_RUNTIME_EXECUTION_AND_REGRESSION_ADMISSION_V2',
        'semantic_boundary': 'BOUNDED EXPERIENCE-CONDITIONED SELF-REWRITE OF THE AUTONOMOUS LEARNING RUNTIME. SHADOW ONLY; NO MAIN MUTATION OR CLAIM OF CONSCIOUSNESS.'
    }
    receipt['receipt_sha256'] = digest(receipt)
    RECEIPT.write_text(json.dumps(receipt, indent=2, ensure_ascii=False, sort_keys=True) + '\n', encoding='utf-8')
    print(json.dumps({
        'status': receipt['status'],
        'candidate_sha256': candidate_sha,
        'experience_digest': receipt['experience_digest'],
        'fact_count': learned['fact_count'],
        'successful_source_ids': learned['successful_source_ids'],
        'next': receipt['next_required_capability'],
    }, indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
