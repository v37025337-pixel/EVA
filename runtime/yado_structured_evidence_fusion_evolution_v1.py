from __future__ import annotations

import hashlib
import importlib.util
import json
import statistics
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parent
EXPERIENCE_PATH = REPO / "experience" / "autonomous" / "yado-autonomous-learning-latest.json"
OUT_DIR = REPO / "candidates" / "cognitive"
REPORT = OUT_DIR / "yado-structured-evidence-fusion-evolution-v1.json"
CANDIDATE = OUT_DIR / "yado_structured_evidence_fusion_candidate_v1.py"
SCHEMA = "yado.structured_evidence_fusion_evolution.v1"


@dataclass(frozen=True)
class FusionPolicy:
    provenance_crosscheck: bool
    numeric_summary: bool
    contradiction_scan: bool
    min_independent_sources: int

    def as_dict(self) -> dict[str, Any]:
        return {
            "provenance_crosscheck": self.provenance_crosscheck,
            "numeric_summary": self.numeric_summary,
            "contradiction_scan": self.contradiction_scan,
            "min_independent_sources": self.min_independent_sources,
        }


def canon(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def digest(value: Any) -> str:
    return hashlib.sha256(canon(value).encode("utf-8")).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def structured_signal(exp: dict[str, Any]) -> dict[str, Any]:
    structured = exp.get("structured_public_data") or {}
    hosts: set[str] = set()
    numeric_sources = 0
    shapes = []
    for source in exp.get("sources") or []:
        for row in source.get("provenance") or []:
            if not row.get("structured_json"):
                continue
            host = str(row.get("host") or "").strip().lower()
            if host:
                hosts.add(host)
            shape = row.get("structured_shape") or {}
            if int(shape.get("numeric_count") or 0) > 0:
                numeric_sources += 1
            shapes.append({
                "numeric_count": int(shape.get("numeric_count") or 0),
                "string_count": int(shape.get("string_count") or 0),
                "object_count": int(shape.get("object_count") or 0),
                "array_count": int(shape.get("array_count") or 0),
                "max_depth": int(shape.get("max_depth") or 0),
            })
    return {
        "structured_sources_fetched": int(structured.get("sources_fetched") or 0),
        "structured_disciplines": sorted(set(structured.get("disciplines") or [])),
        "structured_provenance_hosts": sorted(hosts),
        "structured_provenance_host_count": len(hosts),
        "numeric_structured_sources": numeric_sources,
        "raw_payload_persisted": bool(structured.get("raw_payload_persisted")),
        "shapes": shapes,
        "experience_digest": exp.get("experience_digest") or digest(exp),
    }


def reachable_policy(signal: dict[str, Any]) -> tuple[FusionPolicy, str]:
    baseline = FusionPolicy(False, False, False, 1)
    enough = (
        signal["structured_sources_fetched"] >= 3
        and len(signal["structured_disciplines"]) >= 3
        and signal["structured_provenance_host_count"] >= 3
        and signal["numeric_structured_sources"] >= 2
        and signal["raw_payload_persisted"] is False
    )
    if not enough:
        return baseline, "INSUFFICIENT_VERIFIED_STRUCTURED_EVIDENCE"
    return FusionPolicy(True, True, True, 3), "VERIFIED_MULTI_SOURCE_STRUCTURED_EVIDENCE"


def fuse(policy: FusionPolicy, records: list[dict[str, Any]], tolerance: float = 0.0) -> dict[str, Any]:
    valid = [r for r in records if isinstance(r, dict) and isinstance(r.get("value"), (int, float)) and not isinstance(r.get("value"), bool)]
    hosts = {str(r.get("host") or "").lower() for r in valid if r.get("host")}
    independent = len(hosts)
    supported = (
        policy.provenance_crosscheck
        and policy.numeric_summary
        and independent >= policy.min_independent_sources
        and len(valid) >= policy.min_independent_sources
    )
    if not supported:
        return {"status": "WITHHOLD_INSUFFICIENT_FUSION_CAPABILITY", "independent_sources": independent}
    values = [float(r["value"]) for r in valid]
    median = statistics.median(values)
    mean = sum(values) / len(values)
    divergent = []
    if policy.contradiction_scan:
        divergent = sorted(
            str(r.get("source_id") or r.get("host") or "unknown")
            for r in valid
            if abs(float(r["value"]) - median) > float(tolerance)
        )
    return {
        "status": "FUSED",
        "independent_sources": independent,
        "count": len(values),
        "mean": round(mean, 6),
        "median": round(float(median), 6),
        "minimum": min(values),
        "maximum": max(values),
        "range": max(values) - min(values),
        "divergent_sources": divergent,
    }


# The held-out cases are assistant-authored and independent of the live API
# payloads. The live evidence only controls whether the new fusion capability is
# reachable; it never supplies these expected answers.
HELD_OUT = [
    {
        "records": [
            {"source_id": "a", "host": "alpha.test", "value": 10},
            {"source_id": "b", "host": "beta.test", "value": 12},
            {"source_id": "c", "host": "gamma.test", "value": 11},
        ],
        "tolerance": 2.0,
        "expect": {"status": "FUSED", "mean": 11.0, "median": 11.0, "range": 2.0, "divergent_sources": []},
    },
    {
        "records": [
            {"source_id": "stable-1", "host": "one.test", "value": 20},
            {"source_id": "stable-2", "host": "two.test", "value": 21},
            {"source_id": "outlier", "host": "three.test", "value": 35},
        ],
        "tolerance": 5.0,
        "expect": {"status": "FUSED", "median": 21.0, "divergent_sources": ["outlier"]},
    },
    {
        "records": [
            {"source_id": "x1", "host": "dup.test", "value": 5},
            {"source_id": "x2", "host": "dup.test", "value": 5},
            {"source_id": "y", "host": "other.test", "value": 5},
        ],
        "tolerance": 0.0,
        "expect": {"status": "WITHHOLD_INSUFFICIENT_FUSION_CAPABILITY", "independent_sources": 2},
    },
    {
        "records": [
            {"source_id": "p", "host": "p.test", "value": -2.0},
            {"source_id": "q", "host": "q.test", "value": 0.0},
            {"source_id": "r", "host": "r.test", "value": 2.0},
            {"source_id": "ignored", "host": "s.test", "value": "missing"},
        ],
        "tolerance": 2.5,
        "expect": {"status": "FUSED", "mean": 0.0, "median": 0.0, "minimum": -2.0, "maximum": 2.0, "count": 3},
    },
]


def evaluate(policy: FusionPolicy) -> dict[str, Any]:
    passed = 0
    details = []
    for case in HELD_OUT:
        got = fuse(policy, case["records"], case["tolerance"])
        checks = {key: got.get(key) == value for key, value in case["expect"].items()}
        ok = all(checks.values())
        passed += int(ok)
        details.append({"passed": ok, "checks": checks, "result": got})
    return {"passed": passed, "total": len(HELD_OUT), "score": passed / len(HELD_OUT), "details": details}


def candidate_source(policy: FusionPolicy, signal: dict[str, Any]) -> str:
    return f'''from __future__ import annotations\n\nimport statistics\n\nFUSION_POLICY = {policy.as_dict()!r}\nEXPERIENCE_BINDING = {{'experience_digest': {signal['experience_digest']!r}, 'structured_sources_fetched': {signal['structured_sources_fetched']!r}, 'structured_disciplines': {signal['structured_disciplines']!r}, 'structured_provenance_hosts': {signal['structured_provenance_hosts']!r}, 'numeric_structured_sources': {signal['numeric_structured_sources']!r}}}\n\ndef fuse(records, tolerance=0.0):\n    valid = [r for r in records if isinstance(r, dict) and isinstance(r.get("value"), (int, float)) and not isinstance(r.get("value"), bool)]\n    hosts = {{str(r.get("host") or "").lower() for r in valid if r.get("host")}}\n    independent = len(hosts)\n    supported = FUSION_POLICY["provenance_crosscheck"] and FUSION_POLICY["numeric_summary"] and independent >= FUSION_POLICY["min_independent_sources"] and len(valid) >= FUSION_POLICY["min_independent_sources"]\n    if not supported:\n        return {{"status": "WITHHOLD_INSUFFICIENT_FUSION_CAPABILITY", "independent_sources": independent}}\n    values = [float(r["value"]) for r in valid]\n    median = statistics.median(values)\n    mean = sum(values) / len(values)\n    divergent = []\n    if FUSION_POLICY["contradiction_scan"]:\n        divergent = sorted(str(r.get("source_id") or r.get("host") or "unknown") for r in valid if abs(float(r["value"]) - median) > float(tolerance))\n    return {{"status": "FUSED", "independent_sources": independent, "count": len(values), "mean": round(mean, 6), "median": round(float(median), 6), "minimum": min(values), "maximum": max(values), "range": max(values) - min(values), "divergent_sources": divergent}}\n\ndef component():\n    return {{"schema": "yado.structured_evidence_fusion.v1-development-candidate", "policy": FUSION_POLICY, "experience_binding": EXPERIENCE_BINDING, "canonical_active": False, "development_candidate": True, "consciousness_claimed": False}}\n'''


def main() -> dict[str, Any]:
    exp = load_json(EXPERIENCE_PATH)
    if exp.get("status") != "PASS_SHADOW_BOUNDED_AUTONOMOUS_EXTERNAL_LEARNING_V1":
        raise RuntimeError("VERIFIED_EXTERNAL_EXPERIENCE_REQUIRED")
    signal = structured_signal(exp)
    selected, reason = reachable_policy(signal)
    baseline = FusionPolicy(False, False, False, 1)
    baseline_eval = evaluate(baseline)
    selected_eval = evaluate(selected)

    zero = dict(signal)
    zero.update({
        "structured_sources_fetched": 0,
        "structured_disciplines": [],
        "structured_provenance_hosts": [],
        "structured_provenance_host_count": 0,
        "numeric_structured_sources": 0,
        "experience_digest": "ABLATION_NONE",
    })
    ablated, ablation_reason = reachable_policy(zero)
    ablated_eval = evaluate(ablated)

    changed = selected.as_dict() != baseline.as_dict()
    improved = selected_eval["score"] > baseline_eval["score"]
    causal = selected.as_dict() != ablated.as_dict() and selected_eval["score"] > ablated_eval["score"]
    held_out_pass = selected_eval["score"] == 1.0
    safe_input = signal["raw_payload_persisted"] is False
    status = (
        "PASS_SHADOW_STRUCTURED_EVIDENCE_FUSION_EVOLUTION_V1"
        if changed and improved and causal and held_out_pass and safe_input
        else "WITHHOLD_STRUCTURED_EVIDENCE_FUSION_EVOLUTION_V1"
    )

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    source = candidate_source(selected, signal)
    compile(source, str(CANDIDATE), "exec")
    CANDIDATE.write_text(source, encoding="utf-8")
    candidate_sha = hashlib.sha256(CANDIDATE.read_bytes()).hexdigest()

    report = {
        "schema": SCHEMA,
        "status": status,
        "experience_signal": signal,
        "baseline_policy": baseline.as_dict(),
        "baseline_held_out": baseline_eval,
        "selected_policy": selected.as_dict(),
        "selected_held_out": selected_eval,
        "mutation_reason": reason,
        "no_experience_ablation": {
            "policy": ablated.as_dict(),
            "held_out": ablated_eval,
            "reason": ablation_reason,
            "causal_effect_observed": causal,
        },
        "new_capability": "MULTI_SOURCE_STRUCTURED_EVIDENCE_FUSION_V1",
        "candidate_path": str(CANDIDATE.relative_to(REPO)),
        "candidate_sha256": candidate_sha,
        "remote_payload_executed": False,
        "raw_remote_payload_persisted": signal["raw_payload_persisted"],
        "external_model_used": False,
        "canonical_mutation": False,
        "automatic_main_mutation": False,
        "consciousness_claimed": False,
        "limitations": [
            "assistant-authored bounded mutation grammar and held-out fusion benchmark",
            "live public API evidence gates capability genesis but does not supply held-out answers",
            "development candidate only until full runtime regression and kernel audit pass",
        ],
    }
    REPORT.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": status,
        "new_capability": report["new_capability"],
        "selected_policy": selected.as_dict(),
        "baseline_score": baseline_eval["score"],
        "selected_score": selected_eval["score"],
        "ablation_score": ablated_eval["score"],
        "candidate_sha256": candidate_sha,
        "structured_sources_fetched": signal["structured_sources_fetched"],
        "structured_disciplines": signal["structured_disciplines"],
    }, indent=2, sort_keys=True))
    if not status.startswith("PASS_"):
        raise SystemExit(2)
    return report


if __name__ == "__main__":
    main()
