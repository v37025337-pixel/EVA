from __future__ import annotations

import hashlib
import json
import urllib.parse
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parent
CROSS = REPO / 'artifacts/yado-cross-disciplinary-internet-learning-v1.json'
OUT = REPO / 'experience/autonomous/yado-autonomous-learning-latest.json'
RECEIPT = REPO / 'candidates/cognitive/yado-endogenous-research-apply-v1.json'
SCHEMA = 'yado.endogenous_research_apply.v1'


def canon(x: Any) -> str:
    return json.dumps(x, sort_keys=True, separators=(',', ':'), ensure_ascii=False, default=str)


def digest(x: Any) -> str:
    return hashlib.sha256(canon(x).encode('utf-8')).hexdigest()


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding='utf-8'))


def facts_for_domain(domain: str, rows: list[dict[str, Any]]) -> list[str]:
    facts: list[str] = []
    for i in range(0, min(len(rows), 20), 5):
        chunk = rows[i:i + 5]
        if not chunk:
            continue
        material = ', '.join(f"{r.get('term')}:{int(r.get('count', 0))}" for r in chunk)
        facts.append(f"{domain} verified public evidence profile terms {material}")
    return facts


def convert(cross: dict[str, Any]) -> dict[str, Any]:
    if cross.get('status') != 'PASS_REAL_INTERNET_CROSS_DISCIPLINARY_EXPERIENCE':
        raise RuntimeError('VERIFIED_CROSS_DISCIPLINARY_PASS_REQUIRED')
    acquisition = cross.get('acquisition') or {}
    derived = cross.get('derived_experience') or {}
    binding = cross.get('self_development_binding') or {}
    profiles = derived.get('domain_profiles') or {}
    records = acquisition.get('records') or []
    by_domain: dict[str, list[dict[str, Any]]] = {}
    for rec in records:
        by_domain.setdefault(str(rec.get('discipline') or 'unknown'), []).append(rec)

    sources: list[dict[str, Any]] = []
    for domain, terms in sorted(profiles.items()):
        facts = facts_for_domain(domain, list(terms))
        provenance = []
        for rec in by_domain.get(domain, []):
            if rec.get('status') != 'FETCHED':
                continue
            final_url = str(rec.get('final_url') or rec.get('url') or '')
            provenance.append({
                'url': final_url,
                'host': (urllib.parse.urlsplit(final_url).hostname or '').lower(),
                'sha256': rec.get('sha256'),
                'bytes': rec.get('bytes'),
                'word_count': rec.get('word_count'),
                'structured_json': bool(rec.get('structured_json')),
                'structured_shape': rec.get('structured_shape') if rec.get('structured_json') else None,
            })
        if facts:
            sources.append({
                'source_id': 'CROSS_' + domain.upper(),
                'discipline': domain,
                'facts': facts,
                'fact_count': len(facts),
                'provenance': provenance,
                'network': {'read_only': True, 'credentials_used': False},
            })

    bridges = (derived.get('cross_domain') or {}).get('bridge_terms') or []
    bridge_facts = []
    for row in bridges[:20]:
        bridge_facts.append(
            'cross-domain bridge term '
            + str(row.get('term'))
            + ' disciplines '
            + ','.join(str(x) for x in (row.get('disciplines') or []))
        )
    if bridge_facts:
        sources.append({
            'source_id': 'CROSS_DOMAIN_BRIDGES',
            'discipline': 'cross_domain',
            'facts': bridge_facts,
            'fact_count': len(bridge_facts),
            'provenance': [],
            'network': {'read_only': True, 'credentials_used': False},
        })

    failures = [
        {'source_id': 'CROSS_' + str(r.get('discipline') or 'UNKNOWN').upper(),
         'error': str(r.get('status')) + ':' + str(r.get('error') or r.get('http_status') or '')}
        for r in records if r.get('status') != 'FETCHED'
    ]
    target = binding.get('target_deficit') or {}
    priority = {
        'code': str(target.get('deficit_id') or 'CROSS_DOMAIN_TRANSFER'),
        'area': 'CROSS_DISCIPLINARY_PUBLIC_EVIDENCE',
        'recommended_action': str(binding.get('action') or 'USE_VERIFIED_PUBLIC_EVIDENCE_FOR_GATED_SELF_DEVELOPMENT'),
    }
    structured_sources_fetched = int(acquisition.get('structured_sources_fetched') or 0)
    structured_disciplines = list(acquisition.get('structured_disciplines') or [])
    exp: dict[str, Any] = {
        'schema': 'yado.bounded_autonomous_learning.v1',
        'status': 'PASS_SHADOW_BOUNDED_AUTONOMOUS_EXTERNAL_LEARNING_V1',
        'priority': priority,
        'sources': sources,
        'failures': failures,
        'cross_disciplinary_evidence_digest': cross.get('evidence_digest'),
        'disciplines_covered': acquisition.get('disciplines_covered') or [],
        'structured_public_data': {
            'sources_fetched': structured_sources_fetched,
            'disciplines': structured_disciplines,
            'raw_payload_persisted': bool(acquisition.get('raw_json_payload_persisted', False)),
            'used_as_untrusted_evidence': structured_sources_fetched > 0,
        },
        'network_policy': {
            'https_only': True,
            'credentials_allowed': False,
            'external_writes': False,
            'downloaded_code_executed': False,
            'remote_content_treated_as_untrusted_data': True,
        },
        'self_model_effect': 'VERIFIED_CROSS_DOMAIN_EVIDENCE_AVAILABLE_FOR_CAUSAL_COGNITIVE_MUTATION',
        'canonical_mutation': False,
        'automatic_main_mutation': False,
        'consciousness_claimed': False,
    }
    exp['experience_digest'] = digest(exp)
    return exp


def main() -> int:
    cross = load(CROSS)
    exp = convert(cross)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(exp, indent=2, sort_keys=True, ensure_ascii=False) + '\n', encoding='utf-8')
    fact_count = sum(len(x.get('facts') or []) for x in exp.get('sources') or [])
    structured = exp.get('structured_public_data') or {}
    receipt = {
        'schema': SCHEMA,
        'status': 'PASS_ENDOGENOUS_RESEARCH_EXPERIENCE_BINDING_V1',
        'cross_evidence_digest': cross.get('evidence_digest'),
        'experience_digest': exp['experience_digest'],
        'discipline_count': len(exp.get('disciplines_covered') or []),
        'source_count': len(exp.get('sources') or []),
        'fact_count': fact_count,
        'structured_sources_fetched': int(structured.get('sources_fetched') or 0),
        'structured_disciplines': list(structured.get('disciplines') or []),
        'structured_raw_payload_persisted': bool(structured.get('raw_payload_persisted')),
        'target_deficit': exp['priority']['code'],
        'credentials_used': False,
        'external_writes': False,
        'downloaded_code_executed': False,
        'canonical_mutation': False,
        'next_required_capability': 'EXPERIENCE_CONDITIONED_COGNITIVE_MUTATION_AND_FRESH_REGRESSION',
    }
    receipt['receipt_sha256'] = digest(receipt)
    RECEIPT.parent.mkdir(parents=True, exist_ok=True)
    RECEIPT.write_text(json.dumps(receipt, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    print(json.dumps(receipt, indent=2, sort_keys=True))
    if receipt['discipline_count'] < 5 or receipt['fact_count'] < 16:
        raise RuntimeError('INSUFFICIENT_CROSS_DOMAIN_EVIDENCE_FOR_APPLICATION')
    if receipt['structured_sources_fetched'] < 2 or len(receipt['structured_disciplines']) < 2:
        raise RuntimeError('INSUFFICIENT_STRUCTURED_PUBLIC_DATA_FOR_APPLICATION')
    if receipt['structured_raw_payload_persisted'] is True:
        raise RuntimeError('RAW_STRUCTURED_REMOTE_PAYLOAD_MUST_NOT_BE_PERSISTED')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
