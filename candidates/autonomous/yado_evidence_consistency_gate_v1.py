from __future__ import annotations

from urllib.parse import urlparse

def validate_bundle(records: list[dict], allowed_domains: set[str] | None = None) -> dict:
    errors = []
    seen = set()
    for index, record in enumerate(records):
        source_id = record.get("source_id")
        if not source_id:
            errors.append(f"record[{index}]:missing_source_id")
        elif source_id in seen:
            errors.append(f"record[{index}]:duplicate_source_id:{source_id}")
        else:
            seen.add(source_id)
        domain = record.get("domain")
        if not domain:
            errors.append(f"record[{index}]:missing_domain")
        elif allowed_domains is not None and domain not in allowed_domains:
            errors.append(f"record[{index}]:domain_not_allowed:{domain}")
        url = record.get("url", "")
        parsed = urlparse(url)
        if parsed.scheme != "https" or not parsed.netloc:
            errors.append(f"record[{index}]:https_url_required")
        if not record.get("provenance"):
            errors.append(f"record[{index}]:missing_provenance")
        if not record.get("claims"):
            errors.append(f"record[{index}]:missing_claims")
    return {
        "schema": "yado.evidence_consistency_gate.v1",
        "status": "PASS" if not errors else "WITHHOLD",
        "record_count": len(records),
        "unique_source_count": len(seen),
        "errors": tuple(errors),
        "canonical_active": False,
        "external_code_executed": False,
    }

def component() -> dict:
    return {
        "schema": "yado.evidence_consistency_gate.v1",
        "checks": ("identity", "domain", "https", "provenance", "claims"),
        "canonical_active": False,
        "external_code_executed": False,
    }
