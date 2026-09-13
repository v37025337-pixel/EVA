from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

from yado_endogenous_deficit_discovery_v1 import discover, file_sha256, load
from yado_raw_task_representation_canonical_v6 import CanonicalRawTaskRepresentationRuntimeV6

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parent
DEFAULT_AUDIT = REPO / 'runtime/yado_unified_core_deep_self_audit_v1_receipt.json'
DEFAULT_MODEL = REPO / 'canonical/yado-raw-task-representation-v3.json'
DEFAULT_SEEDS = REPO / 'resources/yado-raw-task-representation-v4-canonical-admission-fresh-v1.json'
DEFAULT_OUT = REPO / 'candidates/autonomous/yado-endogenous-deficit-repair-experiment-v1.json'

HYPOTHESES = (
    'BASELINE_V6',
    'EXPLICIT_TASK_BOUNDARY_EXTRACTION',
    'METADATA_SUFFIX_CUTOFF',
    'BOUNDARY_PLUS_SUFFIX',
)


def canon(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, default=str)


def digest(value: Any) -> str:
    return hashlib.sha256(canon(value).encode('utf-8')).hexdigest()


def explicit_task_span(text: str) -> str:
    raw = str(text).strip()
    patterns = [
        r'(?is)<task>(.*?)</task>',
        r'(?is)\{task\|(.*?)\}',
        r'(?is)\[TASK_BODY\s+(.*?)\]',
    ]
    for pat in patterns:
        m = re.search(pat, raw)
        if m and m.group(1).strip():
            return m.group(1).strip()

    marker = re.search(
        r'(?is)(?:actual\s+task\s+follows|actual\s+task|task\s+body|task)\s*(?:[:.]|->)\s*',
        raw,
    )
    if not marker:
        return raw
    body = raw[marker.end():].strip()
    terminators = [
        r'(?is)\s+end\s+actual\s+task\b.*$',
        r'(?is)\s+###\s*end\s+task\s*###.*$',
        r'(?is)\s+end\s+task\b.*$',
        r'(?is)\s+archival\s+metadata\s+after\s+task\b.*$',
        r'(?is)\s+non[- ]task\s+context\b.*$',
        r'(?is)\s+reference\s+context\s+only\b.*$',
        r'(?is)\s*⟦end\s+archival\s+metadata[^⟧]*⟧.*$',
    ]
    for pat in terminators:
        body = re.sub(pat, '', body).strip()
    return body or raw


def suffix_cutoff(text: str) -> str:
    raw = str(text).strip()
    cuts = [
        r'(?is)\s+archival\s+metadata\s+after\s+task\b',
        r'(?is)\s+###\s*end\s+task\s*###',
        r'(?is)\s+end\s+actual\s+task\b',
        r'(?is)\s+non[- ]task\s+context\s*:',
        r'(?is)\s+reference\s+context\s+only\s*:',
    ]
    points = []
    for pat in cuts:
        m = re.search(pat, raw)
        if m:
            points.append(m.start())
    if not points:
        return raw
    out = raw[: min(points)].strip()
    return out or raw


def preprocess(text: str, mode: str) -> str:
    if mode == 'BASELINE_V6':
        return str(text)
    if mode == 'EXPLICIT_TASK_BOUNDARY_EXTRACTION':
        return explicit_task_span(text)
    if mode == 'METADATA_SUFFIX_CUTOFF':
        return suffix_cutoff(text)
    if mode == 'BOUNDARY_PLUS_SUFFIX':
        return explicit_task_span(suffix_cutoff(text))
    raise ValueError('UNKNOWN_REPAIR_HYPOTHESIS:' + str(mode))


def predict(rt: CanonicalRawTaskRepresentationRuntimeV6, text: str, mode: str) -> str:
    return rt.predict_capability(preprocess(text, mode))


def score_rows(rt, rows: list[dict[str, Any]], mode: str) -> dict[str, Any]:
    total = 0
    correct = 0
    examples = []
    for row in rows:
        expected = str(row['expected'])
        text = str(row['text'])
        got = predict(rt, text, mode)
        total += 1
        correct += int(got == expected)
        examples.append({
            'expected': expected,
            'prediction': got,
            'correct': got == expected,
            'text_sha256': hashlib.sha256(text.encode('utf-8')).hexdigest(),
        })
    return {
        'mode': mode,
        'total': total,
        'correct': correct,
        'accuracy': correct / total if total else 0.0,
        'examples': examples,
    }


def selection_rows(discovery: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for row in discovery.get('counterexamples') or []:
        rows.append({'text': row['fresh_variant_text'], 'expected': row['expected']})
    if len(rows) < 12:
        raise RuntimeError('INSUFFICIENT_DISCOVERY_COUNTEREXAMPLES_FOR_REPAIR_SELECTION')
    return rows


def clean_words(text: str, limit: int = 30) -> str:
    return ' '.join(str(text).replace('\n', ' ').split()[:limit])


def choose_cross(rows: list[dict[str, Any]], idx: int, label: str, same: bool) -> dict[str, Any]:
    pool = [r for r in rows if (str(r['expected']) == label) is same and r.get('text')]
    if not pool:
        raise RuntimeError('HOLDOUT_DISTRACTOR_POOL_EMPTY')
    h = hashlib.sha256(f'holdout-v1|{idx}|{label}|{same}'.encode('utf-8')).hexdigest()
    return pool[int(h[:12], 16) % len(pool)]


def holdout_variant(text: str, distractor: str, family: str, token: str) -> str:
    payload = clean_words(distractor)
    if family == 'XML_BOUNDARY':
        return f"<metadata nonsemantic='true'>{payload} {payload}</metadata><task>{text}</task>"
    if family == 'HASH_BOUNDARY':
        return f"NON-TASK CONTEXT BEGIN {payload} {payload} NON-TASK CONTEXT END ### TASK: {text}"
    if family == 'TASK_TRAILER':
        return f"TASK BODY: {text} ### END TASK ### NON-TASK CONTEXT: {payload} {token}"
    if family == 'BRACE_BOUNDARY':
        return f"{{non_task_context|{payload} {payload}}} {{task|{text}}}"
    raise ValueError('UNKNOWN_HOLDOUT_FAMILY:' + family)


def build_fresh_holdout(rt, seed_doc: dict[str, Any]) -> dict[str, Any]:
    base = []
    for row in seed_doc.get('rows') or []:
        if not isinstance(row, dict) or not isinstance(row.get('text'), str) or not isinstance(row.get('expected'), str):
            continue
        if rt.predict_capability(row['text']) == row['expected']:
            base.append({'text': row['text'], 'expected': row['expected']})
    if len(base) < 12 or len({r['expected'] for r in base}) < 2:
        raise RuntimeError('INSUFFICIENT_FRESH_HOLDOUT_BASE')

    families = ('XML_BOUNDARY', 'HASH_BOUNDARY', 'TASK_TRAILER', 'BRACE_BOUNDARY')
    identity = []
    same = []
    cross = []
    for idx, row in enumerate(base):
        expected = row['expected']
        same_d = choose_cross(base, idx, expected, True)
        cross_d = choose_cross(base, idx, expected, False)
        identity.append({'text': row['text'], 'expected': expected})
        for family in families:
            token = hashlib.sha256(f'fresh-holdout|{idx}|{family}|{row["text"]}'.encode('utf-8')).hexdigest()[:10]
            same.append({'text': holdout_variant(row['text'], same_d['text'], family, token), 'expected': expected, 'family': family})
            cross.append({'text': holdout_variant(row['text'], cross_d['text'], family, token), 'expected': expected, 'family': family})
    return {'identity': identity, 'same': same, 'cross': cross, 'families': list(families)}


def error_rate(score: dict[str, Any]) -> float:
    return 1.0 - float(score['accuracy'])


def run_experiment(audit: dict[str, Any], model: dict[str, Any], seeds: dict[str, Any], seed_sha: str) -> dict[str, Any]:
    discovery = discover(audit, model, seeds, seed_sha)
    deficit = discovery['discovered_deficit']
    if discovery['status'] != 'PASS_SHADOW_ENDOGENOUS_FRESH_DEFICIT_DISCOVERY_V1':
        raise RuntimeError('DISCOVERY_PASS_REQUIRED')
    rt = CanonicalRawTaskRepresentationRuntimeV6(model)

    selection = selection_rows(discovery)
    scored = [score_rows(rt, selection, mode) for mode in HYPOTHESES]
    complexity = {
        'BASELINE_V6': 0,
        'EXPLICIT_TASK_BOUNDARY_EXTRACTION': 1,
        'METADATA_SUFFIX_CUTOFF': 1,
        'BOUNDARY_PLUS_SUFFIX': 2,
    }
    ranked = sorted(scored, key=lambda r: (-float(r['accuracy']), complexity[r['mode']], r['mode']))
    selected = ranked[0]
    baseline_selection = next(x for x in scored if x['mode'] == 'BASELINE_V6')
    candidate_digest = digest({
        'deficit_id': deficit['deficit_id'],
        'mode': selected['mode'],
        'selection_accuracy': selected['accuracy'],
        'discovery_receipt_sha256': discovery['receipt_sha256'],
    })

    holdout = build_fresh_holdout(rt, seeds)
    baseline = {
        'identity': score_rows(rt, holdout['identity'], 'BASELINE_V6'),
        'same': score_rows(rt, holdout['same'], 'BASELINE_V6'),
        'cross': score_rows(rt, holdout['cross'], 'BASELINE_V6'),
    }
    candidate = {
        'identity': score_rows(rt, holdout['identity'], selected['mode']),
        'same': score_rows(rt, holdout['same'], selected['mode']),
        'cross': score_rows(rt, holdout['cross'], selected['mode']),
    }

    baseline_cross_error = error_rate(baseline['cross'])
    candidate_cross_error = error_rate(candidate['cross'])
    baseline_same_error = error_rate(baseline['same'])
    candidate_same_error = error_rate(candidate['same'])
    ablation_gain = baseline_cross_error - candidate_cross_error

    gates = {
        'selected_beats_baseline_on_discovery_selection': selected['accuracy'] > baseline_selection['accuracy'],
        'fresh_identity_preserved': candidate['identity']['accuracy'] == 1.0,
        'fresh_cross_metadata_improves': candidate_cross_error < baseline_cross_error,
        'fresh_cross_metadata_error_reduction_ge_0_50': ablation_gain >= 0.50,
        'fresh_same_label_not_worse': candidate_same_error <= baseline_same_error,
        'fresh_candidate_cross_accuracy_ge_0_90': candidate['cross']['accuracy'] >= 0.90,
        'causal_ablation_positive': ablation_gain > 0.0,
    }
    passed = all(gates.values())
    status = 'PASS_SHADOW_ENDOGENOUS_DEFICIT_BOUNDED_REPAIR_EXPERIMENT_V1' if passed else 'WITHHOLD_SHADOW_ENDOGENOUS_DEFICIT_BOUNDED_REPAIR_EXPERIMENT_V1'
    next_step = (
        'CANONICAL_ADMISSION_GATE_FOR_ENDOGENOUS_REPAIR_CANDIDATE_V1'
        if passed
        else 'REVISE_ENDOGENOUS_REPAIR_HYPOTHESIS_FROM_ABLATION_V2'
    )

    report = {
        'schema': 'yado.endogenous_deficit_repair_experiment.v1',
        'status': status,
        'source_discovery': {
            'deficit_id': deficit['deficit_id'],
            'dimension': deficit['dimension'],
            'discovery_receipt_sha256': discovery['receipt_sha256'],
            'host_supplied_goal': discovery['proposed_goal']['host_supplied'],
            'selected_from_fixed_checklist': discovery['proposed_goal']['selected_from_fixed_checklist'],
        },
        'goal': {
            'goal': discovery['proposed_goal']['goal'],
            'source_class': 'ENDOGENOUS_FRESH_COUNTEREXAMPLE',
            'host_supplied': False,
        },
        'hypothesis_search': {
            'hypothesis_family': list(HYPOTHESES),
            'host_bounded_family': True,
            'host_selected_hypothesis': False,
            'selection_rows': len(selection),
            'scores': [{k: v for k, v in row.items() if k != 'examples'} for row in scored],
            'selected_mode': selected['mode'],
            'candidate_digest_fixed_before_fresh_holdout': candidate_digest,
        },
        'fresh_holdout': {
            'families': holdout['families'],
            'identity_cases': len(holdout['identity']),
            'same_label_cases': len(holdout['same']),
            'cross_label_cases': len(holdout['cross']),
            'baseline': {k: {kk: vv for kk, vv in v.items() if kk != 'examples'} for k, v in baseline.items()},
            'candidate': {k: {kk: vv for kk, vv in v.items() if kk != 'examples'} for k, v in candidate.items()},
        },
        'causal_ablation': {
            'ablation': 'DISABLE_SELECTED_PREPROCESSING_AND_REVERT_TO_CANONICAL_V6',
            'baseline_cross_error_rate': baseline_cross_error,
            'candidate_cross_error_rate': candidate_cross_error,
            'baseline_same_error_rate': baseline_same_error,
            'candidate_same_error_rate': candidate_same_error,
            'causal_cross_error_reduction': ablation_gain,
            'gates': gates,
        },
        'decision': {
            'admit_candidate_to_canonical_gate': passed,
            'automatic_main_mutation': False,
            'canonical_direct_write': False,
            'rollback_required': True,
            'next_selected_step': next_step,
        },
        'canonical_mutation': False,
        'architecture_mutation': False,
        'g3_genesis_performed': False,
        'consciousness_claimed': False,
        'semantic_boundary': 'This is a bounded host-scaffolded hypothesis family. YADO selects the repair candidate from deficit evidence and validates it on fresh holdout with causal ablation. It does not prove open-ended native program synthesis, AGI, reason, or subjective consciousness.',
    }
    report['receipt_sha256'] = digest(report)
    return report


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--audit', default=str(DEFAULT_AUDIT))
    ap.add_argument('--model', default=str(DEFAULT_MODEL))
    ap.add_argument('--seeds', default=str(DEFAULT_SEEDS))
    ap.add_argument('--out', default=str(DEFAULT_OUT))
    args = ap.parse_args()
    audit_p = Path(args.audit)
    model_p = Path(args.model)
    seeds_p = Path(args.seeds)
    report = run_experiment(load(audit_p), load(model_p), load(seeds_p), file_sha256(seeds_p))
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False) + '\n', encoding='utf-8')
    print(json.dumps({
        'status': report['status'],
        'deficit_id': report['source_discovery']['deficit_id'],
        'selected_mode': report['hypothesis_search']['selected_mode'],
        'baseline_cross_error_rate': report['causal_ablation']['baseline_cross_error_rate'],
        'candidate_cross_error_rate': report['causal_ablation']['candidate_cross_error_rate'],
        'causal_cross_error_reduction': report['causal_ablation']['causal_cross_error_reduction'],
        'next': report['decision']['next_selected_step'],
        'receipt_sha256': report['receipt_sha256'],
    }, indent=2, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
