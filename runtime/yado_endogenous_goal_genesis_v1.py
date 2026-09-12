from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parent
DEFAULT_AUDIT = REPO / 'runtime/yado_unified_core_deep_self_audit_v1_receipt.json'
DEFAULT_LEDGER = REPO / 'architecture/evolution-ledger.json'
DEFAULT_OUT = REPO / 'candidates/autonomous/yado-endogenous-goal-genesis-v1.json'


def canon(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, default=str)


def digest(value: Any) -> str:
    return hashlib.sha256(canon(value).encode('utf-8')).hexdigest()


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding='utf-8'))


def normalize_goal(value: Any) -> str | None:
    text = str(value or '').strip()
    if not text or text.lower() in {'none', 'null'}:
        return None
    return text


def build_candidates(audit: dict[str, Any], ledger: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    frontier = ((audit.get('core_snapshot') or {}).get('frontier') or {})
    for raw in frontier.get('open_deficits') or []:
        goal = normalize_goal(raw)
        if goal:
            rows.append({
                'goal': goal,
                'source_class': 'CANONICAL_DEVELOPMENTAL_FRONTIER',
                'source_path': 'runtime/yado_unified_core_deep_self_audit_v1_receipt.json:core_snapshot.frontier.open_deficits',
                'evidence_rank': 1.0,
                'developmental': True,
                'repair': False,
            })

    # Advisory audit priorities are retained as lower-ranked alternatives, not silently erased.
    for row in ledger.get('audit_priority') or []:
        code = normalize_goal(row.get('code')) if isinstance(row, dict) else None
        if code:
            rows.append({
                'goal': code,
                'source_class': 'CANONICAL_AUDIT_ADVISORY',
                'source_path': 'architecture/evolution-ledger.json:audit_priority',
                'evidence_rank': 0.55,
                'developmental': False,
                'repair': True,
                'recommended_action': row.get('recommended_action'),
            })

    dedup: dict[str, dict[str, Any]] = {}
    for row in rows:
        old = dedup.get(row['goal'])
        if old is None or row['evidence_rank'] > old['evidence_rank']:
            dedup[row['goal']] = row
    return sorted(dedup.values(), key=lambda r: (-float(r['evidence_rank']), r['goal']))


def action_hypotheses(goal: str, audit: dict[str, Any]) -> list[dict[str, Any]]:
    recommended = (((audit.get('core_snapshot') or {}).get('frontier') or {}).get('recommended_experience') or [])
    tags = sorted({str(tag).lower() for row in recommended if isinstance(row, dict) for tag in (row.get('tags') or [])})
    hypotheses = [
        {
            'action': 'FRESH_COUNTEREXAMPLE_STRESS_AND_RETEST',
            'information_gain': 1.0 if {'transfer', 'withhold', 'representation'} & set(tags) else 0.8,
            'reversibility': 1.0,
            'testability': 1.0,
            'canonical_write': False,
        },
        {
            'action': 'CAUSAL_ABLATION_OF_CANDIDATE_IMPROVEMENT',
            'information_gain': 1.0 if 'ablation' in tags else 0.75,
            'reversibility': 1.0,
            'testability': 1.0,
            'canonical_write': False,
        },
        {
            'action': 'EXPERIENCE_GUIDED_SHADOW_REDERIVATION',
            'information_gain': 0.85 if recommended else 0.6,
            'reversibility': 1.0,
            'testability': 0.9,
            'canonical_write': False,
        },
    ]
    for row in hypotheses:
        row['score'] = round((row['information_gain'] * 0.45) + (row['testability'] * 0.35) + (row['reversibility'] * 0.20), 6)
    return sorted(hypotheses, key=lambda r: (-r['score'], r['action']))


def generate(audit: dict[str, Any], ledger: dict[str, Any]) -> dict[str, Any]:
    findings = audit.get('findings') or []
    non_pass = [x for x in findings if isinstance(x, dict) and x.get('status') != 'PASS']
    blocking = [x for x in findings if isinstance(x, dict) and x.get('blocking')]
    repair_next = audit.get('self_selected_next_step') or (audit.get('audit_frontier_binding') or {}).get('proposed_next_step')

    if non_pass or blocking or repair_next:
        raise RuntimeError('REPAIR_QUEUE_NOT_EMPTY')

    candidates = build_candidates(audit, ledger)
    developmental = [x for x in candidates if x.get('developmental')]
    if not developmental:
        raise RuntimeError('NO_CANONICAL_DEVELOPMENTAL_FRONTIER')

    selected = developmental[0]
    hypotheses = action_hypotheses(selected['goal'], audit)
    action = hypotheses[0]
    frontier = ((audit.get('core_snapshot') or {}).get('frontier') or {})

    report = {
        'schema': 'yado.endogenous_goal_genesis.v1',
        'status': 'PASS_SHADOW_ENDOGENOUS_DEVELOPMENTAL_GOAL_GENESIS_V1',
        'trigger': {
            'repair_queue_empty': True,
            'all_current_audit_findings_pass': True,
            'self_selected_repair_step': None,
            'canonical_developmental_frontier_nonempty': True,
        },
        'host_supplied_goal': False,
        'host_selected_goal': False,
        'goal_source': 'CANONICAL_SELF_MODEL_DEVELOPMENTAL_FRONTIER',
        'candidate_goals': candidates,
        'selected_goal': selected['goal'],
        'selected_goal_provenance': selected,
        'frontier_source': frontier.get('frontier_source'),
        'action_hypotheses': hypotheses,
        'selected_action': action,
        'execution_contract': {
            'mode': 'BOUNDED_SHADOW_ONLY',
            'canonical_direct_write': False,
            'automatic_main_mutation': False,
            'external_write': False,
            'credentials_allowed': False,
            'rollback_required': True,
            'fresh_counterexample_required': True,
            'causal_ablation_required_before_admission': True,
            'full_regression_required_before_admission': True,
            'full_kernel_audit_required_before_admission': True,
        },
        'canonical_mutation': False,
        'architecture_mutation': False,
        'g3_genesis_performed': False,
        'consciousness_claimed': False,
        'next_required_capability': 'BIND_ENDOGENOUS_DEVELOPMENTAL_GOAL_TO_BOUNDED_EXPERIMENT_V1',
        'semantic_boundary': 'A clean repair audit does not imply completion or consciousness. This mechanism derives one developmental goal from the canonical self-model frontier and selects only a reversible shadow experiment route; it does not execute or canonically admit a rewrite.',
    }
    report['receipt_sha256'] = digest(report)
    return report


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--audit', default=str(DEFAULT_AUDIT))
    ap.add_argument('--ledger', default=str(DEFAULT_LEDGER))
    ap.add_argument('--out', default=str(DEFAULT_OUT))
    args = ap.parse_args()
    report = generate(load(Path(args.audit)), load(Path(args.ledger)))
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False) + '\n', encoding='utf-8')
    print(json.dumps({
        'status': report['status'],
        'selected_goal': report['selected_goal'],
        'selected_action': report['selected_action']['action'],
        'candidate_goal_count': len(report['candidate_goals']),
        'host_supplied_goal': report['host_supplied_goal'],
        'canonical_mutation': report['canonical_mutation'],
        'next_required_capability': report['next_required_capability'],
        'receipt_sha256': report['receipt_sha256'],
    }, indent=2, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
