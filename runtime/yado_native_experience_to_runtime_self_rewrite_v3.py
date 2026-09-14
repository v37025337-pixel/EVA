from __future__ import annotations

import ast
import hashlib
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parent
EXPERIENCE = REPO / 'experience/autonomous/yado-autonomous-learning-latest.json'
TARGET = ROOT / 'yado_bounded_autonomous_learning_v1.py'
CANDIDATE = REPO / 'candidates/autonomous/yado_bounded_autonomous_learning_runtime_candidate_v3.py'
RECEIPT = REPO / 'candidates/autonomous/yado-native-experience-to-runtime-self-rewrite-v3.json'


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


def failed_source_ids(exp):
    return sorted({str(x.get('source_id')) for x in exp.get('failures', []) if x.get('source_id')})


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
                if len(toks) >= 128:
                    return sorted(toks)
    return sorted(toks)


def dangerous_call_counts(source):
    tree = ast.parse(source)
    names = Counter()
    attrs = Counter()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if isinstance(node.func, ast.Name):
            names[node.func.id] += 1
        elif isinstance(node.func, ast.Attribute):
            attrs[node.func.attr] += 1
    return {
        'eval': names['eval'],
        'exec': names['exec'],
        'compile': names['compile'],
        'system': attrs['system'],
        'Popen': attrs['Popen'],
        'run': attrs['run'],
        'call': attrs['call'],
        'check_call': attrs['check_call'],
        'check_output': attrs['check_output'],
    }


def assert_no_new_dangerous_constructs(parent_src, candidate_src):
    before = dangerous_call_counts(parent_src)
    after = dangerous_call_counts(candidate_src)
    added = {k: after[k] - before[k] for k in after if after[k] > before[k]}
    if added:
        raise RuntimeError('UNSAFE_SOURCE_CONSTRUCT_ADDED:' + canon(added))
    return {'parent': before, 'candidate': after, 'new_dangerous_calls': added}


def _assigns_name(node, name):
    return isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == name for t in node.targets)


def synthesize_candidate(parent_src, exp):
    tree = ast.parse(parent_src)
    evidence_digest = str(exp.get('experience_digest') or '')
    if not evidence_digest:
        raise RuntimeError('EXPERIENCE_DIGEST_MISSING')

    learned = {
        'experience_digest': evidence_digest,
        'successful_source_ids': successful_source_ids(exp),
        'failed_source_ids': failed_source_ids(exp),
        'successful_hosts': successful_hosts(exp),
        'fact_count': sum(len(x.get('facts', [])) for x in exp.get('sources', [])),
        'learning_tokens': prior_learning_tokens(exp),
    }

    learned_value = ast.parse(repr(learned), mode='eval').body
    learned_updated = False
    for i, node in enumerate(tree.body):
        if _assigns_name(node, 'LEARNED_EXTERNAL_EVIDENCE_V2'):
            tree.body[i] = ast.Assign(
                targets=[ast.Name(id='LEARNED_EXTERNAL_EVIDENCE_V2', ctx=ast.Store())],
                value=learned_value,
            )
            learned_updated = True
            break
    if not learned_updated:
        insertion_index = 0
        for i, node in enumerate(tree.body):
            if isinstance(node, ast.ImportFrom) and node.module == '__future__':
                insertion_index = i + 1
        tree.body.insert(
            insertion_index,
            ast.Assign(
                targets=[ast.Name(id='LEARNED_EXTERNAL_EVIDENCE_V2', ctx=ast.Store())],
                value=learned_value,
            ),
        )

    rank = next((n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'rank_sources'), None)
    if rank is None:
        raise RuntimeError('RANK_SOURCES_ANCHOR_NOT_FOUND')

    rank_text = '\n'.join(ast.unparse(x) for x in rank.body)
    if "LEARNED_EXTERNAL_EVIDENCE_V2.get('learning_tokens'" not in rank_text:
        for idx, stmt in enumerate(rank.body):
            if _assigns_name(stmt, 'q'):
                rank.body.insert(idx + 1, ast.parse("q |= set(LEARNED_EXTERNAL_EVIDENCE_V2.get('learning_tokens', []))").body[0])
                break
        else:
            raise RuntimeError('RANK_QUERY_ANCHOR_NOT_FOUND')

    row_loop = next((n for n in rank.body if isinstance(n, ast.For) and isinstance(n.target, ast.Name) and n.target.id == 'row'), None)
    if row_loop is None:
        raise RuntimeError('RANK_ROW_LOOP_NOT_FOUND')

    loop_text = '\n'.join(ast.unparse(x) for x in row_loop.body)
    score_idx = next((i for i, stmt in enumerate(row_loop.body) if _assigns_name(stmt, 'score')), None)
    if score_idx is None:
        raise RuntimeError('SOURCE_SCORE_ANCHOR_NOT_FOUND')

    insert_at = score_idx + 1
    if "successful_source_ids" not in loop_text:
        row_loop.body.insert(insert_at, ast.parse("score += 2 if row.get('id') in LEARNED_EXTERNAL_EVIDENCE_V2.get('successful_source_ids', []) else 0").body[0])
        insert_at += 1

    loop_text = '\n'.join(ast.unparse(x) for x in row_loop.body)
    if 'row_host' not in loop_text:
        row_loop.body.insert(insert_at, ast.parse("row_host = (urllib.parse.urlsplit(row.get('url', '')).hostname or '').lower()").body[0])
        insert_at += 1
    if "successful_hosts" not in loop_text:
        row_loop.body.insert(insert_at, ast.parse("score += 1 if row_host in LEARNED_EXTERNAL_EVIDENCE_V2.get('successful_hosts', []) else 0").body[0])
        insert_at += 1
    if "failed_source_ids" not in loop_text:
        row_loop.body.insert(insert_at, ast.parse("score -= 1 if row.get('id') in LEARNED_EXTERNAL_EVIDENCE_V2.get('failed_source_ids', []) else 0").body[0])

    ast.fix_missing_locations(tree)
    out = ast.unparse(tree) + '\n'
    compile(out, '<yado-native-experience-runtime-v3>', 'exec')
    safety_delta = assert_no_new_dangerous_constructs(parent_src, out)
    return out, learned, safety_delta


def main():
    exp = load(EXPERIENCE)
    if exp.get('status') != 'PASS_SHADOW_BOUNDED_AUTONOMOUS_EXTERNAL_LEARNING_V1':
        raise RuntimeError('V1_PASS_EXPERIENCE_REQUIRED')
    policy = exp.get('network_policy') or {}
    if policy.get('credentials_allowed') is not False or policy.get('external_writes') is not False:
        raise RuntimeError('UNSAFE_EXPERIENCE_POLICY')

    parent_src = TARGET.read_text(encoding='utf-8')
    parent_sha = sha_text(parent_src)
    candidate_src, learned, safety_delta = synthesize_candidate(parent_src, exp)
    candidate_sha = sha_text(candidate_src)
    if candidate_sha == parent_sha:
        raise RuntimeError('CANDIDATE_UNCHANGED')

    CANDIDATE.parent.mkdir(parents=True, exist_ok=True)
    CANDIDATE.write_text(candidate_src, encoding='utf-8')
    receipt = {
        'schema': 'yado.native_experience_to_runtime_self_rewrite.v3',
        'status': 'PASS_SHADOW_NATIVE_EXPERIENCE_TO_RUNTIME_SELF_REWRITE_CANDIDATE_V3',
        'target_path': str(TARGET.relative_to(REPO)),
        'parent_sha256': parent_sha,
        'candidate_path': str(CANDIDATE.relative_to(REPO)),
        'candidate_sha256': candidate_sha,
        'experience_digest': exp.get('experience_digest'),
        'learned_binding': learned,
        'strategy_changes': [
            'refresh learned evidence instead of duplicating prior mutation',
            'retain successful-source affinity',
            'add successful-host affinity',
            'penalize sources that failed in the latest bounded run',
        ],
        'safety_delta': safety_delta,
        'native_ast_materialization': True,
        'external_model_used': False,
        'downloaded_code_executed': False,
        'credentials_used': False,
        'external_writes': False,
        'canonical_mutation': False,
        'automatic_main_mutation': False,
        'rollback_parent_sha256': parent_sha,
        'next_required_capability': 'ISOLATED_RUNTIME_EXECUTION_AND_REGRESSION_ADMISSION_V3',
        'semantic_boundary': 'IDEMPOTENT EXPERIENCE-CONDITIONED SELF-REWRITE OF THE BOUNDED INTERNET LEARNING RUNTIME. DEVELOPMENT/SHADOW ONLY; NO MAIN MUTATION OR CONSCIOUSNESS CLAIM.',
    }
    receipt['receipt_sha256'] = digest(receipt)
    RECEIPT.write_text(json.dumps(receipt, indent=2, ensure_ascii=False, sort_keys=True) + '\n', encoding='utf-8')
    print(json.dumps({
        'status': receipt['status'],
        'candidate_sha256': candidate_sha,
        'experience_digest': receipt['experience_digest'],
        'fact_count': learned['fact_count'],
        'successful_source_ids': learned['successful_source_ids'],
        'failed_source_ids': learned['failed_source_ids'],
        'successful_hosts': learned['successful_hosts'],
        'next': receipt['next_required_capability'],
    }, indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
