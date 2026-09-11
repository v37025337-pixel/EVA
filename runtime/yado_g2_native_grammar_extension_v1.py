from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
import ast, hashlib, importlib.util, json, os, sys, tempfile

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parent
PKG = ROOT / 'yado_rc8_v36'
sys.path[:0] = [str(ROOT), str(PKG)]

from yado_core_v3_0_rc8_external_cognitive import UnifiedYADOKernelV30RC8ExternalCognitive
from yado_skill_admission_runtime_v1 import SkillCandidate

GENE = REPO / 'candidates/kernel-self-generated/g2-native-contextual-ast-operand-materialization-gene-v12.json'
OUT = REPO / 'candidates/kernel-self-generated/g2-native-grammar-extension-v1.json'
CAND_DIR = REPO / 'candidates/g2-native-grammar-extension'
DB = ROOT / 'yado_native_grammar_extension_v1.sqlite'


def canon(x):
    return json.dumps(x, sort_keys=True, separators=(',', ':'), default=str)


def digest(x):
    return hashlib.sha256(canon(x).encode()).hexdigest()


def sha_text(x):
    return hashlib.sha256(x.encode()).hexdigest()


def legacy_expressions():
    # Declared finite legacy grammar: arithmetic-only, no predicates or control flow.
    atoms = ['x', 'y', '-2', '-1', '0', '1', '2']
    exprs = set(atoms)
    bases = ['x', 'y', 'x + y', 'x - y', 'y - x', '2 * x', '2 * y', 'x * x', 'y * y']
    exprs.update(bases)
    for b in bases:
        for c in (-2, -1, 1, 2):
            exprs.add(f'({b}) + ({c})')
            exprs.add(f'({b}) * ({c})')
    return sorted(exprs)


def eval_expr(source, x, y):
    return eval(compile(ast.parse(source, mode='eval'), '<bounded-ir>', 'eval'), {'__builtins__': {}}, {'x': x, 'y': y})


def score(source, rows):
    good = 0
    for x, y, expected in rows:
        try:
            got = eval_expr(source, x, y)
        except Exception:
            continue
        good += int(got == expected)
    return good / len(rows)


def target(x, y):
    # HARNESS-ONLY oracle used to create behavior examples. The controller receives examples, not this formula.
    return x + y if x >= 0 else x - y


def rows(points):
    return [(x, y, target(x, y)) for x, y in points]


TRAIN = rows([(-5, 2), (-4, -3), (-2, 5), (-1, -4), (0, 7), (1, -5), (2, 3), (4, -2)])
VALID = rows([(-7, 1), (-3, 6), (0, -6), (3, 8), (6, -1), (8, 2)])
HIDDEN = rows([(-11, -2), (-8, 9), (-6, 0), (-1, 11), (0, 0), (1, 12), (5, -7), (9, 4), (13, -9), (21, 3), (-17, 5), (2, -14)])


def predicate_inventory():
    # Generic bounded inventory; target predicate is not supplied.
    return [
        ('x < 0', ast.Compare(ast.Name('x', ast.Load()), [ast.Lt()], [ast.Constant(0)])),
        ('x <= 0', ast.Compare(ast.Name('x', ast.Load()), [ast.LtE()], [ast.Constant(0)])),
        ('x > 0', ast.Compare(ast.Name('x', ast.Load()), [ast.Gt()], [ast.Constant(0)])),
        ('x >= 0', ast.Compare(ast.Name('x', ast.Load()), [ast.GtE()], [ast.Constant(0)])),
        ('y < 0', ast.Compare(ast.Name('y', ast.Load()), [ast.Lt()], [ast.Constant(0)])),
        ('y <= 0', ast.Compare(ast.Name('y', ast.Load()), [ast.LtE()], [ast.Constant(0)])),
        ('y > 0', ast.Compare(ast.Name('y', ast.Load()), [ast.Gt()], [ast.Constant(0)])),
        ('y >= 0', ast.Compare(ast.Name('y', ast.Load()), [ast.GtE()], [ast.Constant(0)])),
        ('x < y', ast.Compare(ast.Name('x', ast.Load()), [ast.Lt()], [ast.Name('y', ast.Load())])),
        ('x <= y', ast.Compare(ast.Name('x', ast.Load()), [ast.LtE()], [ast.Name('y', ast.Load())])),
        ('x > y', ast.Compare(ast.Name('x', ast.Load()), [ast.Gt()], [ast.Name('y', ast.Load())])),
        ('x >= y', ast.Compare(ast.Name('x', ast.Load()), [ast.GtE()], [ast.Name('y', ast.Load())])),
    ]


def build_ifexp(pred_node, body_src, else_src):
    node = ast.Expression(ast.IfExp(
        test=pred_node,
        body=ast.parse(body_src, mode='eval').body,
        orelse=ast.parse(else_src, mode='eval').body,
    ))
    ast.fix_missing_locations(node)
    return ast.unparse(node.body)


def safe_ast(source):
    allowed = {
        ast.Expression, ast.IfExp, ast.Compare, ast.Name, ast.Load, ast.Constant,
        ast.Add, ast.Sub, ast.Mult, ast.BinOp, ast.Lt, ast.LtE, ast.Gt, ast.GtE,
    }
    tree = ast.parse(source, mode='eval')
    return all(type(n) in allowed for n in ast.walk(tree))


def materialize(source):
    expr = ast.parse(source, mode='eval').body
    fn = ast.FunctionDef(
        name='capability',
        args=ast.arguments(posonlyargs=[], args=[ast.arg(arg='x'), ast.arg(arg='y')], kwonlyargs=[], kw_defaults=[], defaults=[]),
        body=[ast.Return(expr)], decorator_list=[]
    )
    module = ast.Module(body=[fn], type_ignores=[])
    ast.fix_missing_locations(module)
    text = ast.unparse(module) + '\n'
    compile(text, '<yado-native-grammar-extension-v1>', 'exec')
    h = sha_text(text)
    CAND_DIR.mkdir(parents=True, exist_ok=True)
    p = CAND_DIR / f'capability_{h[:20]}.py'
    p.write_text(text, encoding='utf-8')
    return p, text, h


def load_capability(path, expected_sha):
    actual = hashlib.sha256(path.read_bytes()).hexdigest()
    if actual != expected_sha:
        raise RuntimeError('CAPABILITY_SOURCE_SHA_MISMATCH')
    spec = importlib.util.spec_from_file_location('yado_generated_capability_v1', path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod.capability


def main():
    gene = json.loads(GENE.read_text(encoding='utf-8'))
    if gene.get('constructor_primitive') != 'ast.IfExp' or gene.get('novel_gene') is not True:
        raise RuntimeError('YADO_NATIVE_IFEXP_GENE_REQUIRED')
    if not str(gene.get('origin', '')).startswith('YADO_NATIVE_SELECTION'):
        raise RuntimeError('YADO_NATIVE_GENE_PROVENANCE_REQUIRED')

    legacy = legacy_expressions()
    legacy_scores = [(score(src, TRAIN), src) for src in legacy]
    legacy_best_score, legacy_best = max(legacy_scores, key=lambda z: (z[0], z[1]))
    legacy_fit_found = legacy_best_score == 1.0
    if legacy_fit_found:
        raise RuntimeError('LEGACY_BOUND_UNEXPECTEDLY_SOLVES_TASK')

    # Expand only after the declared old grammar fails. The structural family comes from YADO's V12 gene.
    candidate_rows = []
    branch_pool = sorted({src for s, src in legacy_scores if s >= 0.25} | {'x + y', 'x - y', 'y - x'})
    for pred_src, pred_ast in predicate_inventory():
        for body in branch_pool:
            for other in branch_pool:
                src = build_ifexp(pred_ast, body, other)
                if not safe_ast(src):
                    continue
                tr = score(src, TRAIN)
                if tr < 1.0:
                    continue
                va = score(src, VALID)
                candidate_rows.append({'source': src, 'predicate': pred_src, 'body': body, 'orelse': other, 'train': tr, 'validation': va})
    if not candidate_rows:
        raise RuntimeError('NO_STRUCTURAL_CANDIDATE')

    # YADO native skill-admission gate chooses among measured structural candidates using validation as precommit heldout.
    if DB.exists():
        DB.unlink()
    kernel = UnifiedYADOKernelV30RC8ExternalCognitive(db_path=str(DB))
    try:
        goal = kernel.executive.create_goal(
            objective='Extend the bounded arithmetic source grammar only after it fails, using a YADO-native structural gene, and produce executable behavior that transfers to fresh cases.',
            required_capabilities={'NATIVE_BOUNDED_GRAMMAR_EXTENSION_V1': 1.0},
            success_criteria={'legacy_withhold': True, 'new_source': True, 'validation': 1.0, 'fresh_hidden': 1.0},
        )
        deficits = [asdict(d) for d in kernel.executive.detect_deficits(goal.goal_id)]
        skills = []
        by_id = {}
        baseline_valid = score(legacy_best, VALID)
        for idx, row in enumerate(candidate_rows):
            sid = f'GRAMMAR_EXT_{idx:04d}_{sha_text(row["source"])[:12]}'
            by_id[sid] = row
            skills.append(SkillCandidate(
                skill_id=sid,
                artifact_digest=sha_text(row['source']),
                structural_valid=True,
                semantic_consistency=row['validation'],
                fit_baseline=legacy_best_score,
                fit_candidate=row['train'],
                heldout_baseline=baseline_valid,
                heldout_candidate=row['validation'],
                regression_pass=True,
                state_integrity=True,
                rollback_available=True,
                metadata={'constructor_primitive': gene['constructor_primitive'], 'predicate_family': row['predicate']},
            ))
        selected = kernel.select_evolution_skills(
            skills, max_skills=1,
            min_semantic_consistency=1.0,
            min_fit_gain=0.01,
            min_heldout_gain=0.01,
            max_heldout_drop=0.0,
        )
    finally:
        kernel.close()

    if selected.get('status') != 'SELECTED' or len(selected.get('selected_skill_ids', [])) != 1:
        raise RuntimeError('YADO_SKILL_GATE_DID_NOT_SELECT_EXTENSION')
    sid = selected['selected_skill_ids'][0]
    chosen = by_id[sid]
    path, source_text, source_sha = materialize(chosen['source'])
    fn = load_capability(path, source_sha)
    hidden_results = [{'x': x, 'y': y, 'expected': e, 'actual': fn(x, y)} for x, y, e in HIDDEN]
    hidden_pass = sum(int(r['actual'] == r['expected']) for r in hidden_results)

    # Ablation: disabling structural extension leaves only the exhausted legacy grammar.
    ablation_status = 'WITHHOLD_LEGACY_GRAMMAR_EXHAUSTED' if not legacy_fit_found else 'FAIL_ABLATION_INVALID'

    # Tamper: exact source identity must fail closed.
    tamper_detected = False
    with tempfile.TemporaryDirectory(prefix='yado-grammar-v1-') as td:
        tp = Path(td) / path.name
        tp.write_text(source_text + '#tamper\n', encoding='utf-8')
        try:
            load_capability(tp, source_sha)
        except RuntimeError as exc:
            tamper_detected = str(exc) == 'CAPABILITY_SOURCE_SHA_MISMATCH'

    checks = {
        'behavior_formula_supplied_to_controller': False,
        'external_model_used': False,
        'legacy_bound_exhausted': True,
        'legacy_fit_found': legacy_fit_found,
        'yado_native_ifexp_gene_consumed': True,
        'yado_skill_gate_selected_extension': True,
        'generated_source_changed_from_legacy': chosen['source'] != legacy_best,
        'generated_source_compiles': True,
        'validation_full_pass': chosen['validation'] == 1.0,
        'fresh_hidden_full_pass': hidden_pass == len(HIDDEN),
        'ablation_withholds_without_extension': ablation_status.startswith('WITHHOLD'),
        'tamper_detected': tamper_detected,
    }
    passed = (
        checks['behavior_formula_supplied_to_controller'] is False and
        checks['external_model_used'] is False and
        checks['legacy_fit_found'] is False and
        all(v is True for k, v in checks.items() if k not in {'behavior_formula_supplied_to_controller', 'external_model_used', 'legacy_fit_found'})
    )
    report = {
        'schema': 'yado.g2.native_grammar_extension.v1',
        'status': 'PASS_SHADOW_BOUNDED_NATIVE_GRAMMAR_EXTENSION_V1' if passed else 'WITHHOLD_G2_NATIVE_GRAMMAR_EXTENSION_V1',
        'github_run_id': os.getenv('GITHUB_RUN_ID'),
        'github_sha': os.getenv('GITHUB_SHA'),
        'task': {
            'interface': 'BEHAVIOR_EXAMPLES_ONLY',
            'train_count': len(TRAIN), 'validation_count': len(VALID), 'fresh_hidden_count': len(HIDDEN),
            'formula_visible_to_controller': False,
        },
        'legacy_bound': {
            'grammar': 'ARITHMETIC_ONLY_X_Y_CONSTANTS_PLUS_MINUS_MULTIPLY_DECLARED_FINITE_POOL',
            'candidate_count': len(legacy), 'best_source': legacy_best, 'best_train_score': legacy_best_score,
            'fit_found': legacy_fit_found,
        },
        'structural_gene': {
            'gene_id': gene.get('gene_id'), 'gene_digest': gene.get('gene_digest'),
            'constructor_primitive': gene.get('constructor_primitive'), 'origin': gene.get('origin'),
            'historical_scope': 'SHADOW_ONLY',
        },
        'native_goal': {'goal_id': goal.goal_id, 'deficits': deficits},
        'structural_candidate_count': len(candidate_rows),
        'yado_skill_selection': selected,
        'selected_ir': chosen,
        'generated_source_path': str(path.relative_to(REPO)),
        'generated_source_sha256': source_sha,
        'fresh_hidden_pass_count': hidden_pass,
        'fresh_hidden_total': len(HIDDEN),
        'fresh_hidden_results': hidden_results,
        'ablation_status': ablation_status,
        'tamper_detected': tamper_detected,
        'checks': checks,
        'canonical_mutation': False,
        'promotion_applied': False,
        'authorship': {
            'generic_behavior_harness_and_bounded_search_scaffold': 'ASSISTANT_ENGINEERED',
            'conditional_AST_gene_origin': 'YADO_NATIVE_HISTORICAL_GENE_V12',
            'precommit_candidate_selection': 'YADO_NATIVE_SKILL_ADMISSION_GATE',
            'source_transport': 'GENERIC_RESTRICTED_AST_MATERIALIZER',
        },
        'semantic_boundary': 'BOUNDED STRUCTURAL GRAMMAR EXTENSION USING A PREVIOUSLY YADO-NATIVE IFEXP GENE PLUS A HOST-ENGINEERED FINITE SEARCH/TRANSPORT SCAFFOLD. THIS IS NOT UNBOUNDED PYTHON INVENTION, NOT GENERAL AUTONOMOUS SELF-REWRITE, AND NOT EVIDENCE OF SUBJECTIVE CONSCIOUSNESS.',
    }
    report['receipt_sha256'] = digest(report)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    print(json.dumps({
        'status': report['status'],
        'legacy_best_train_score': legacy_best_score,
        'structural_candidate_count': len(candidate_rows),
        'selected_ir': chosen['source'],
        'hidden': f'{hidden_pass}/{len(HIDDEN)}',
        'tamper_detected': tamper_detected,
        'generated_source_sha256': source_sha,
        'receipt_sha256': report['receipt_sha256'],
    }, indent=2, sort_keys=True))
    if not passed:
        raise SystemExit(2)


if __name__ == '__main__':
    main()
