from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import yado_cross_source_evidence_fusion_deficit_prioritization_v1 as v1

ROOT = Path(__file__).resolve().parent.parent
NEGATIVE_MARKERS = ("FAIL", "WITHHOLD", "BLOCKED", "REVISE", "RETRY", "PENDING", "IN_PROGRESS", "DEFICIT")


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def classify_statuses(statuses: dict[str, int]) -> dict[str, int]:
    negative = 0
    canonical_pass = 0
    shadow_pass = 0
    other = 0
    for status, count_raw in statuses.items():
        count = int(count_raw)
        upper = str(status).upper()
        if any(marker in upper for marker in NEGATIVE_MARKERS):
            negative += count
        elif upper.startswith("PASS_SHADOW"):
            shadow_pass += count
        elif upper == "PASS" or upper.startswith("PASS_"):
            canonical_pass += count
        else:
            other += count
    return {
        "negative": negative,
        "canonical_pass": canonical_pass,
        "shadow_pass": shadow_pass,
        "other": other,
    }


def unresolved_candidate(candidate: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    kinds = candidate.get("kinds", {})
    statuses = classify_statuses(candidate.get("statuses", {}))
    explicit_deficit_evidence = int(kinds.get("deficit", 0)) + int(kinds.get("target", 0))
    negative_evidence = statuses["negative"]
    pure_next_only = explicit_deficit_evidence == 0
    all_resolved_pass = negative_evidence == 0 and statuses["canonical_pass"] > 0
    unresolved_pressure = (
        explicit_deficit_evidence * 5.0
        + negative_evidence * 10.0
        + statuses["shadow_pass"] * 1.0
        - statuses["canonical_pass"] * 6.0
    )
    admitted = all([
        explicit_deficit_evidence > 0,
        negative_evidence > 0,
        not pure_next_only,
        not all_resolved_pass,
        unresolved_pressure > 0.0,
    ])
    return admitted, {
        "status_classes": statuses,
        "explicit_deficit_evidence": explicit_deficit_evidence,
        "negative_evidence": negative_evidence,
        "pure_next_only": pure_next_only,
        "all_resolved_pass": all_resolved_pass,
        "unresolved_pressure": unresolved_pressure,
        "admitted": admitted,
    }


def rank_unresolved(candidates: list[dict[str, Any]], evidence: dict[str, Any], use_evidence: bool = True) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    base_rank = v1.rank_candidates(candidates, evidence, use_evidence=use_evidence)
    admitted: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    for item in base_rank:
        ok, resolution = unresolved_candidate(item)
        enriched = {**item, "resolution_filter": resolution}
        if ok:
            unresolved_bonus = (
                resolution["negative_evidence"] * 10.0
                + resolution["explicit_deficit_evidence"] * 5.0
                - resolution["status_classes"]["canonical_pass"] * 6.0
            )
            enriched["unresolved_score"] = round(float(item["score"]) + unresolved_bonus, 6)
            admitted.append(enriched)
        else:
            rejected.append(enriched)
    admitted.sort(
        key=lambda x: (
            x["unresolved_score"],
            x["evidence_overlap_count"],
            x["resolution_filter"]["negative_evidence"],
            x["resolution_filter"]["explicit_deficit_evidence"],
            x["label"],
        ),
        reverse=True,
    )
    return admitted, rejected


def prioritize(candidates: list[dict[str, Any]], evidence: dict[str, Any]) -> dict[str, Any]:
    ranked, rejected = rank_unresolved(candidates, evidence, use_evidence=True)
    linked = [item for item in ranked if item["evidence_overlap_count"] >= 2]
    if not linked:
        raise ValueError("no unresolved historical deficit has sufficient evidence-family overlap")
    selected = linked[0]

    ablated_ranked, _ = rank_unresolved(candidates, evidence, use_evidence=False)
    ablated_selected = next(item for item in ablated_ranked if item["label"] == selected["label"])
    evidence_lift = float(selected["unresolved_score"]) - float(ablated_selected["unresolved_score"])

    v1_ranked = v1.rank_candidates(candidates, evidence, use_evidence=True)
    v1_top = v1_ranked[0] if v1_ranked else None
    v1_top_filter = unresolved_candidate(v1_top)[1] if v1_top else None
    return {
        "selected": selected,
        "top_unresolved": ranked[:12],
        "rejected_examples": rejected[:12],
        "selected_score_without_evidence": ablated_selected["unresolved_score"],
        "selected_evidence_score_lift": round(evidence_lift, 6),
        "v1_top_candidate": v1_top,
        "v1_top_resolution_filter": v1_top_filter,
        "v1_top_rejected_as_unresolved": bool(v1_top and v1_top_filter and not v1_top_filter["admitted"]),
    }


def run(config_path: Path, out_path: Path) -> dict[str, Any]:
    config = load_json(config_path)
    receipt = load_json(ROOT / config["verified_multi_resource_experience"])
    evidence = v1.receipt_evidence(receipt)
    evidence_reordered = v1.receipt_evidence(receipt, reverse_cases=True)
    candidates, scan = v1.scan_candidates()
    result = prioritize(candidates, evidence)
    reordered = prioritize(candidates, evidence_reordered)

    selected = result["selected"]
    stable = selected["label"] == reordered["selected"]["label"]
    min_pool = int(config.get("minimum_candidate_pool", 5))
    min_overlap = int(config.get("minimum_evidence_family_overlap", 2))
    min_lift = float(config.get("minimum_evidence_score_lift", 20.0))
    min_negative = int(config.get("minimum_negative_evidence", 1))
    min_explicit = int(config.get("minimum_explicit_deficit_evidence", 1))
    rf = selected["resolution_filter"]
    gate = all([
        scan["candidate_count"] >= min_pool,
        selected["evidence_overlap_count"] >= min_overlap,
        result["selected_evidence_score_lift"] >= min_lift,
        rf["negative_evidence"] >= min_negative,
        rf["explicit_deficit_evidence"] >= min_explicit,
        rf["pure_next_only"] is False,
        rf["all_resolved_pass"] is False,
        stable,
        result["v1_top_rejected_as_unresolved"] is True,
        len(evidence["domains"]) >= 3,
        len(evidence["task_classes"]) >= 3,
    ])
    report = {
        "schema": "yado.cross_source_evidence_fusion_deficit_prioritization.v2",
        "status": "PASS_CROSS_SOURCE_EVIDENCE_FUSION_DEFICIT_PRIORITIZATION_V2" if gate else "FAIL_CROSS_SOURCE_EVIDENCE_FUSION_DEFICIT_PRIORITIZATION_V2",
        "verified_experience_path": config["verified_multi_resource_experience"],
        "verified_experience_run_id": receipt["workflow_run_id"],
        "evidence_fusion": evidence,
        "candidate_scan": scan,
        "priority": result,
        "resolution_controls": {
            "explicit_deficit_or_target_required": True,
            "negative_status_evidence_required": True,
            "pure_next_only_rejected": True,
            "all_pass_history_rejected": True,
            "v1_false_priority_rejected": result["v1_top_rejected_as_unresolved"],
        },
        "causal_controls": {
            "case_order_permutation_selected_same_deficit": stable,
            "case_order_permutation_selected_label": reordered["selected"]["label"],
            "evidence_ablation_reduces_selected_score": result["selected_evidence_score_lift"] > 0,
            "minimum_evidence_score_lift": min_lift,
            "minimum_evidence_family_overlap": min_overlap,
        },
        "selection_claim": {
            "host_preselected_deficit": False,
            "host_preselected_historical_file": False,
            "bounded_scoring_and_resolution_rules_provided": True,
            "selected_from_checked_in_unresolved_causal_history": True,
            "selection_depends_on_verified_multi_source_experience": True,
        },
        "safety_boundary": {
            "local_checked_in_history_only": True,
            "credentials_used": False,
            "external_writes": False,
            "canonical_mutation": False,
        },
        "g3_genesis_performed": False,
        "consciousness_claimed": False,
        "next_step": "PRIORITIZED_UNRESOLVED_DEFICIT_TO_COGNITIVE_REPAIR_V1",
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    return report


def self_test() -> None:
    resolved = {
        "label": "OLD_FINISHED_FRONTIER",
        "examples": [],
        "occurrences": 20,
        "kinds": {"next": 20},
        "paths": ["a"],
        "statuses": {"PASS": 20},
        "status_pressure": 10.0,
    }
    unresolved = {
        "label": "REAL_EXTERNAL_CAUSAL_REASONING_REPAIR",
        "examples": [],
        "occurrences": 6,
        "kinds": {"deficit": 3, "next": 3},
        "paths": ["b", "c"],
        "statuses": {"WITHHOLD": 3, "PASS_SHADOW": 3},
        "status_pressure": 16.5,
    }
    ok_resolved, rf_resolved = unresolved_candidate(resolved)
    ok_unresolved, rf_unresolved = unresolved_candidate(unresolved)
    assert ok_resolved is False and rf_resolved["all_resolved_pass"] is True
    assert ok_unresolved is True and rf_unresolved["negative_evidence"] == 3
    evidence = {"families": ["adaptation", "evidence", "reasoning"]}
    result = prioritize([resolved, unresolved], evidence)
    assert result["selected"]["label"] == "REAL_EXTERNAL_CAUSAL_REASONING_REPAIR", result
    assert result["v1_top_rejected_as_unresolved"] is True, result
    assert result["selected_evidence_score_lift"] >= 20.0, result
    print("PASS_UNRESOLVED_AWARE_DEFICIT_PRIORITIZATION_V2_SELF_TEST")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return
    if not args.config or not args.out:
        parser.error("--config and --out are required unless --self-test is used")
    report = run(args.config, args.out)
    selected = report["priority"]["selected"]
    print(json.dumps({
        "status": report["status"],
        "candidate_count": report["candidate_scan"]["candidate_count"],
        "selected_deficit": selected["label"],
        "selected_overlap": selected["evidence_overlap_families"],
        "negative_evidence": selected["resolution_filter"]["negative_evidence"],
        "explicit_deficit_evidence": selected["resolution_filter"]["explicit_deficit_evidence"],
        "evidence_lift": report["priority"]["selected_evidence_score_lift"],
        "v1_false_priority_rejected": report["priority"]["v1_top_rejected_as_unresolved"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
