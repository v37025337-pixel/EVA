from __future__ import annotations

import statistics

FUSION_POLICY = {'provenance_crosscheck': True, 'numeric_summary': True, 'contradiction_scan': True, 'min_independent_sources': 3}
EXPERIENCE_BINDING = {'experience_digest': 'e65749b52803e1b1aa88e461063751d5a14dd5681ce3fee0188216eabbdfeaf4', 'structured_sources_fetched': 3, 'structured_disciplines': ['economics_demography', 'geophysics', 'weather_systems'], 'structured_provenance_hosts': ['api.open-meteo.com', 'api.worldbank.org', 'earthquake.usgs.gov'], 'numeric_structured_sources': 3}

def fuse(records, tolerance=0.0):
    valid = [r for r in records if isinstance(r, dict) and isinstance(r.get("value"), (int, float)) and not isinstance(r.get("value"), bool)]
    hosts = {str(r.get("host") or "").lower() for r in valid if r.get("host")}
    independent = len(hosts)
    supported = FUSION_POLICY["provenance_crosscheck"] and FUSION_POLICY["numeric_summary"] and independent >= FUSION_POLICY["min_independent_sources"] and len(valid) >= FUSION_POLICY["min_independent_sources"]
    if not supported:
        return {"status": "WITHHOLD_INSUFFICIENT_FUSION_CAPABILITY", "independent_sources": independent}
    values = [float(r["value"]) for r in valid]
    median = statistics.median(values)
    mean = sum(values) / len(values)
    divergent = []
    if FUSION_POLICY["contradiction_scan"]:
        divergent = sorted(str(r.get("source_id") or r.get("host") or "unknown") for r in valid if abs(float(r["value"]) - median) > float(tolerance))
    return {"status": "FUSED", "independent_sources": independent, "count": len(values), "mean": round(mean, 6), "median": round(float(median), 6), "minimum": min(values), "maximum": max(values), "range": max(values) - min(values), "divergent_sources": divergent}

def component():
    return {"schema": "yado.structured_evidence_fusion.v1-development-candidate", "policy": FUSION_POLICY, "experience_binding": EXPERIENCE_BINDING, "canonical_active": False, "development_candidate": True, "consciousness_claimed": False}
