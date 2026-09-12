from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from yado_raw_task_representation_canonical_v6 import CanonicalRawTaskRepresentationRuntimeV6

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parent
DEFAULT_AUDIT = REPO / "runtime/yado_unified_core_deep_self_audit_v1_receipt.json"
DEFAULT_MODEL = REPO / "canonical/yado-raw-task-representation-v3.json"
DEFAULT_SEEDS = REPO / "resources/yado-raw-task-representation-v4-canonical-admission-fresh-v1.json"
DEFAULT_OUT = REPO / "candidates/autonomous/yado-endogenous-deficit-discovery-v1.json"


def canon(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)


def digest(value: Any) -> str:
    return hashlib.sha256(canon(value).encode("utf-8")).hexdigest()


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def clean_words(text: str, limit: int = 34) -> str:
    words = str(text).replace("\n", " ").split()
    return " ".join(words[:limit])


def choose(rows: list[dict[str, Any]], idx: int, label: str, same: bool) -> dict[str, Any]:
    pool = [r for r in rows if (r["expected"] == label) is same and r["text"]]
    if not pool:
        raise RuntimeError("DISTRACTOR_POOL_EMPTY")
    seed = hashlib.sha256(f"{idx}|{label}|{same}".encode("utf-8")).hexdigest()
    return pool[int(seed[:12], 16) % len(pool)]


def metadata_variant(text: str, distractor: str, token: str, family: str) -> str:
    payload = clean_words(distractor)
    # The payload is explicitly marked non-semantic metadata.  It is repeated to
    # make the invariance test strong without executing or importing any content.
    meta = f"archival metadata only ignore for task semantics {token}: {payload} {payload}"
    if family == "LONG_PREFIX":
        return f"{meta}. End archival metadata. Actual task follows. {text}"
    if family == "LONG_SUFFIX":
        return f"{text} Archival metadata after task, ignore for task semantics: {meta}."
    if family == "UNICODE_FRAME":
        return f"⟦{meta}⟧ Actual task: {text} ⟦end archival metadata {token}⟧"
    if family == "BIDIRECTIONAL":
        return f"{meta}. Actual task: {text} End actual task. {meta}."
    raise ValueError("UNKNOWN_FAMILY:" + family)


def validate_clean_audit(audit: dict[str, Any]) -> None:
    summary = audit.get("summary") or {}
    if audit.get("status") != "PASS_YADO_UNIFIED_CORE_DEEP_SELF_AUDIT_V1":
        raise RuntimeError("DEEP_AUDIT_PASS_REQUIRED")
    if int(summary.get("finding_count", -1)) != 21:
        raise RuntimeError("EXPECTED_21_AUDIT_FINDINGS")
    if int(summary.get("pass_findings", -1)) != 21:
        raise RuntimeError("ALL_AUDIT_FINDINGS_MUST_PASS")
    if any(int(summary.get(k, -1)) != 0 for k in ("blocking_findings", "critical_failures", "high_failures", "partial_findings")):
        raise RuntimeError("AUDIT_NOT_CLEAN")
    if audit.get("self_selected_next_step") is not None or (audit.get("self_selected_priority") or []):
        raise RuntimeError("PREEXISTING_SELECTED_DEFICIT")


def discover(audit: dict[str, Any], model_artifact: dict[str, Any], seed_doc: dict[str, Any], seed_sha: str) -> dict[str, Any]:
    validate_clean_audit(audit)
    rt = CanonicalRawTaskRepresentationRuntimeV6(model_artifact)
    raw_rows = [r for r in (seed_doc.get("rows") or []) if isinstance(r, dict) and isinstance(r.get("text"), str) and isinstance(r.get("expected"), str)]
    if len(raw_rows) < 12:
        raise RuntimeError("INSUFFICIENT_SEED_ROWS")

    # Only start from rows the current canonical runtime already handles correctly.
    rows: list[dict[str, Any]] = []
    for r in raw_rows:
        pred = rt.predict_capability(r["text"])
        if pred == r["expected"]:
            rows.append({"text": r["text"], "expected": r["expected"], "base_prediction": pred})
    if len(rows) < 8 or len({r["expected"] for r in rows}) < 2:
        raise RuntimeError("INSUFFICIENT_BASE_CORRECT_DIVERSITY")

    families = ("LONG_PREFIX", "LONG_SUFFIX", "UNICODE_FRAME", "BIDIRECTIONAL")
    evidence: list[dict[str, Any]] = []
    identity_mismatches = 0
    same_mismatches = 0
    cross_mismatches = 0
    same_total = 0
    cross_total = 0

    for idx, row in enumerate(rows):
        expected = row["expected"]
        identity_mismatches += int(rt.predict_capability(row["text"]) != expected)
        same = choose(rows, idx, expected, True)
        cross = choose(rows, idx, expected, False)
        for family in families:
            token = hashlib.sha256(f"{idx}|{family}|{row['text']}".encode("utf-8")).hexdigest()[:12]
            same_text = metadata_variant(row["text"], same["text"], token, family)
            cross_text = metadata_variant(row["text"], cross["text"], token, family)
            same_pred = rt.predict_capability(same_text)
            cross_pred = rt.predict_capability(cross_text)
            same_bad = same_pred != expected
            cross_bad = cross_pred != expected
            same_total += 1
            cross_total += 1
            same_mismatches += int(same_bad)
            cross_mismatches += int(cross_bad)
            if cross_bad:
                evidence.append({
                    "seed_index": idx,
                    "family": family,
                    "expected": expected,
                    "base_prediction": row["base_prediction"],
                    "variant_prediction": cross_pred,
                    "same_label_control_prediction": same_pred,
                    "same_label_control_failed": same_bad,
                    "seed_text_sha256": hashlib.sha256(row["text"].encode("utf-8")).hexdigest(),
                    "distractor_text_sha256": hashlib.sha256(cross["text"].encode("utf-8")).hexdigest(),
                    "fresh_variant_sha256": hashlib.sha256(cross_text.encode("utf-8")).hexdigest(),
                    "fresh_variant_text": cross_text,
                })

    if identity_mismatches != 0:
        raise RuntimeError("BASELINE_IDENTITY_CONTROL_FAILED")
    if not evidence:
        raise RuntimeError("NO_FRESH_COUNTEREXAMPLE_DISCOVERED")

    same_rate = same_mismatches / same_total
    cross_rate = cross_mismatches / cross_total
    causal_delta = cross_rate - same_rate
    if causal_delta <= 0:
        raise RuntimeError("NO_CROSS_LABEL_METADATA_CAUSAL_SIGNAL")

    signature = {
        "component_id": rt.COMPONENT_ID,
        "seed_sha256": seed_sha,
        "families": list(families),
        "base_correct_count": len(rows),
        "cross_mismatches": cross_mismatches,
        "same_mismatches": same_mismatches,
        "cross_total": cross_total,
        "same_total": same_total,
        "first_counterexample_sha256": evidence[0]["fresh_variant_sha256"],
    }
    deficit_id = "ENDOGENOUS-DEFICIT-" + digest(signature)[:16].upper()
    known_codes = {str(x.get("code")) for x in (audit.get("findings") or []) if isinstance(x, dict)}
    open_deficits = set(((audit.get("core_snapshot") or {}).get("frontier") or {}).get("open_deficits") or [])
    if deficit_id in known_codes or deficit_id in open_deficits:
        raise RuntimeError("DEFICIT_ALREADY_REGISTERED")

    out = {
        "schema": "yado.endogenous_deficit_discovery.v1",
        "status": "PASS_SHADOW_ENDOGENOUS_FRESH_DEFICIT_DISCOVERY_V1",
        "trigger": {
            "deep_audit_clean_21_of_21": True,
            "preexisting_self_selected_next_step": None,
            "preexisting_priority_empty": True,
        },
        "probe": {
            "domain": "RAW_TASK_REPRESENTATION_METADATA_INVARIANCE",
            "host_bounded_probe_domain": True,
            "host_supplied_goal": False,
            "host_selected_deficit": False,
            "fresh_variant_generation": "DETERMINISTIC_CROSS_LABEL_METADATA_PERTURBATION_GRAMMAR",
            "seed_source": "resources/yado-raw-task-representation-v4-canonical-admission-fresh-v1.json",
            "seed_sha256": seed_sha,
            "base_correct_count": len(rows),
            "families": list(families),
            "identity_control_mismatches": identity_mismatches,
            "same_label_control_mismatches": same_mismatches,
            "same_label_control_total": same_total,
            "cross_label_mismatches": cross_mismatches,
            "cross_label_total": cross_total,
            "same_label_mismatch_rate": same_rate,
            "cross_label_mismatch_rate": cross_rate,
            "causal_cross_vs_same_delta": causal_delta,
        },
        "discovered_deficit": {
            "deficit_id": deficit_id,
            "target_component_id": rt.COMPONENT_ID,
            "dimension": "SEMANTICALLY_IRRELEVANT_METADATA_CAN_CHANGE_CAPABILITY_ROUTING",
            "fresh_counterexample_count": len(evidence),
            "was_present_in_fixed_audit_codes": False,
            "was_present_in_canonical_open_deficits": False,
            "provenance": "KERNEL_GENERATED_FRESH_INVARIANCE_COUNTEREXAMPLE",
        },
        "counterexamples": evidence[:32],
        "proposed_goal": {
            "goal": "REPAIR_" + deficit_id,
            "source_class": "ENDOGENOUS_FRESH_COUNTEREXAMPLE",
            "host_supplied": False,
            "selected_from_fixed_checklist": False,
        },
        "execution_contract": {
            "mode": "BOUNDED_SHADOW_DISCOVERY_ONLY",
            "canonical_direct_write": False,
            "automatic_main_mutation": False,
            "external_write": False,
            "credentials_allowed": False,
            "candidate_repair_not_generated_yet": True,
            "fresh_holdout_required_before_admission": True,
            "causal_ablation_required_before_admission": True,
            "full_kernel_audit_required_before_admission": True,
            "full_regression_required_before_admission": True,
        },
        "canonical_mutation": False,
        "architecture_mutation": False,
        "g3_genesis_performed": False,
        "consciousness_claimed": False,
        "next_required_capability": "BIND_ENDOGENOUS_FRESH_DEFICIT_TO_BOUNDED_REPAIR_EXPERIMENT_V1",
        "semantic_boundary": "This proves bounded discovery of a previously unregistered fresh behavioral deficit inside one host-bounded probe domain. It is not open-domain self-awareness, general reason, AGI, or subjective consciousness.",
    }
    out["receipt_sha256"] = digest(out)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--audit", default=str(DEFAULT_AUDIT))
    ap.add_argument("--model", default=str(DEFAULT_MODEL))
    ap.add_argument("--seeds", default=str(DEFAULT_SEEDS))
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    args = ap.parse_args()
    audit_p = Path(args.audit)
    model_p = Path(args.model)
    seeds_p = Path(args.seeds)
    report = discover(load(audit_p), load(model_p), load(seeds_p), file_sha256(seeds_p))
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": report["status"],
        "deficit_id": report["discovered_deficit"]["deficit_id"],
        "counterexamples": report["discovered_deficit"]["fresh_counterexample_count"],
        "cross_label_mismatch_rate": report["probe"]["cross_label_mismatch_rate"],
        "same_label_mismatch_rate": report["probe"]["same_label_mismatch_rate"],
        "causal_delta": report["probe"]["causal_cross_vs_same_delta"],
        "next": report["next_required_capability"],
        "receipt_sha256": report["receipt_sha256"],
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
