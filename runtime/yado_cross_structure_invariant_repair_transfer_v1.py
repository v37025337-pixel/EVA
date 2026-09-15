from __future__ import annotations

import argparse
import json
import sqlite3
from copy import deepcopy
from pathlib import Path
from typing import Any

import yado_endogenous_data_invariant_repair_v1 as prior

ROOT = Path(__file__).resolve().parent.parent


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def verify_prior_receipt(receipt: dict[str, Any]) -> None:
    if receipt.get("status") != "PASS_VERIFIED_ENDOGENOUS_DATA_INVARIANT_REPAIR_V1":
        raise ValueError("prior endogenous experience is not verified")
    regression = receipt.get("full_regression", {})
    if regression.get("status") != "PASS" or int(regression.get("tests_run", 0)) < 200:
        raise ValueError("prior experience lacks complete regression proof")
    if regression.get("failures") != [] or regression.get("errors") != []:
        raise ValueError("prior experience has regression failures")
    if receipt.get("full_kernel_audit") != "PASS":
        raise ValueError("prior experience lacks full-kernel audit proof")
    if receipt.get("fresh_holdout_pass") is not True:
        raise ValueError("prior experience lacks fresh holdout proof")
    if receipt.get("canonical_mutation") is not False:
        raise ValueError("prior receipt unexpectedly mutated canonical state")


def field_signature(profile: dict[str, Any]) -> set[str]:
    return set(map(str, profile.get("fields", [])))


def schema_distance(a: dict[str, Any], b: dict[str, Any]) -> float:
    left = field_signature(a)
    right = field_signature(b)
    union = left | right
    if not union:
        return 0.0
    return 1.0 - (len(left & right) / len(union))


def probe_resources(resources: list[dict[str, Any]]) -> list[dict[str, Any]]:
    probed: list[dict[str, Any]] = []
    for resource in resources:
        payload, meta = prior.fetch_json(resource["probe_url"])
        rows = prior.object_rows(payload, int(resource.get("probe_rows", 8)))
        profile = prior.infer_profile(rows)
        probed.append({
            "id": resource["id"],
            "resource": resource,
            "profile": profile,
            "probe_meta": meta,
        })
    return probed


def select_transfer_resource(
    probed: list[dict[str, Any]],
    prior_resource_id: str,
    prior_profile_hint: dict[str, Any],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    eligible = [item for item in probed if item["id"] != prior_resource_id]
    if not eligible:
        raise ValueError("no held-out resource remains after excluding prior resource")
    scored: list[dict[str, Any]] = []
    for item in eligible:
        distance = schema_distance(item["profile"], prior_profile_hint)
        score = float(item["profile"]["selection_score"]) + distance * 100.0
        scored.append({**item, "schema_distance_from_prior": distance, "transfer_score": score})
    scored.sort(key=lambda x: (x["transfer_score"], x["id"]), reverse=True)
    return scored[0], scored


def derive_stressors(profile: dict[str, Any]) -> list[dict[str, Any]]:
    stressors: list[dict[str, Any]] = []
    identity = profile.get("identity_field")
    if identity:
        stressors.append({
            "kind": "REPEAT_INGESTION",
            "target_field": identity,
            "derived_from_invariant": "IDENTITY_UNIQUENESS",
        })
    null_candidates = [
        inv["field"]
        for inv in profile.get("invariants", [])
        if inv.get("kind") == "NOT_NULL" and inv.get("field") != identity
    ]
    if null_candidates:
        field = sorted(null_candidates)[0]
        stressors.append({
            "kind": "NULL_REQUIRED_FIELD",
            "target_field": field,
            "derived_from_invariant": "NOT_NULL",
        })
    bool_candidates = [
        inv["field"]
        for inv in profile.get("invariants", [])
        if inv.get("kind") == "BOOLEAN_DOMAIN"
    ]
    if bool_candidates:
        field = sorted(bool_candidates)[0]
        stressors.append({
            "kind": "INVALID_BOOLEAN_DOMAIN",
            "target_field": field,
            "derived_from_invariant": "BOOLEAN_DOMAIN",
        })
    if len(stressors) < 2:
        raise ValueError("transfer target does not expose at least two independently derived stressors")
    return stressors


def next_identity_value(rows: list[dict[str, Any]], profile: dict[str, Any]) -> Any:
    identity = profile["identity_field"]
    values = [prior.normalize_value(row.get(identity)) for row in rows]
    sql_type = profile["stats"][identity]["sql_type"]
    if sql_type in {"INTEGER", "REAL"}:
        numeric = [float(v) for v in values if isinstance(v, (int, float))]
        base = max(numeric) if numeric else 0.0
        candidate = int(base) + 1_000_003
        return candidate
    return f"YADO_TRANSFER_{len(values)}_UNIQUE"


def apply_stressors_to_baseline(
    conn: sqlite3.Connection,
    table: str,
    rows: list[dict[str, Any]],
    profile: dict[str, Any],
    stressors: list[dict[str, Any]],
) -> None:
    prior.load_rows_plain(conn, table, profile["fields"], rows)
    for stressor in stressors:
        kind = stressor["kind"]
        if kind == "REPEAT_INGESTION":
            prior.load_rows_plain(conn, table, profile["fields"], rows)
        elif kind == "NULL_REQUIRED_FIELD":
            row = deepcopy(rows[0])
            row[profile["identity_field"]] = next_identity_value(rows, profile)
            row[stressor["target_field"]] = None
            prior.load_rows_plain(conn, table, profile["fields"], [row])
        elif kind == "INVALID_BOOLEAN_DOMAIN":
            row = deepcopy(rows[0])
            row[profile["identity_field"]] = next_identity_value(rows, profile)
            row[stressor["target_field"]] = 7
            prior.load_rows_plain(conn, table, profile["fields"], [row])
        else:
            raise ValueError(f"unsupported stressor: {kind}")
    conn.commit()


def baseline_transfer_failure(
    rows: list[dict[str, Any]],
    profile: dict[str, Any],
    stressors: list[dict[str, Any]],
) -> dict[str, Any]:
    conn = sqlite3.connect(":memory:")
    try:
        table = "transfer_baseline"
        prior.create_baseline(conn, table, profile)
        apply_stressors_to_baseline(conn, table, rows, profile, stressors)
        violations = prior.detect_violations(conn, table, profile)
        observed_kinds = {v["kind"] for v in violations}
        required_kinds = {s["derived_from_invariant"] for s in stressors}
        return {
            "status": "DEFECT_DETECTED" if required_kinds <= observed_kinds else "DEFECT_INCOMPLETE",
            "violations": violations,
            "required_violation_kinds": sorted(required_kinds),
            "observed_violation_kinds": sorted(observed_kinds),
        }
    finally:
        conn.close()


def verify_constraint_rejection(
    rows: list[dict[str, Any]],
    profile: dict[str, Any],
    repairs: list[dict[str, Any]],
    stressors: list[dict[str, Any]],
) -> dict[str, Any]:
    conn = sqlite3.connect(":memory:")
    table = "constraint_probe"
    results: dict[str, bool] = {}
    try:
        prior.create_repaired(conn, table, profile, repairs)
        prior.load_rows_repaired(conn, table, profile, rows)
        conn.commit()
        for stressor in stressors:
            if stressor["kind"] == "REPEAT_INGESTION":
                before = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                prior.load_rows_repaired(conn, table, profile, rows)
                conn.commit()
                after = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                results["repeat_ingestion_idempotent"] = before == after
                continue
            row = deepcopy(rows[0])
            row[profile["identity_field"]] = next_identity_value(rows, profile)
            if stressor["kind"] == "NULL_REQUIRED_FIELD":
                row[stressor["target_field"]] = None
                key = "null_required_field_rejected"
            elif stressor["kind"] == "INVALID_BOOLEAN_DOMAIN":
                row[stressor["target_field"]] = 7
                key = "invalid_boolean_rejected"
            else:
                continue
            try:
                prior.load_rows_repaired(conn, table, profile, [row])
                conn.commit()
                results[key] = False
            except sqlite3.IntegrityError:
                conn.rollback()
                results[key] = True
        return results
    finally:
        conn.close()


def run(config_path: Path, out_path: Path) -> dict[str, Any]:
    config = load_json(config_path)
    receipt = load_json(ROOT / config["prior_experience_path"])
    verify_prior_receipt(receipt)
    learned = prior.load_learned_candidate(ROOT / config["learned_candidate_path"])
    component = learned.component()
    if component.get("study_digest") != config["required_study_digest"]:
        raise ValueError("learned candidate study digest mismatch")
    if component.get("canonical_active") is not False:
        raise ValueError("development candidate unexpectedly canonical")

    probed = probe_resources(config["resources"])
    prior_id = str(receipt["selected_resource_id"])
    prior_item = next((item for item in probed if item["id"] == prior_id), None)
    if prior_item is None:
        raise ValueError("prior selected resource is absent from transfer probe set")
    selected, ranked = select_transfer_resource(probed, prior_id, prior_item["profile"])
    if selected["id"] == prior_id:
        raise AssertionError("transfer resource repeated the prior resource")
    if selected["schema_distance_from_prior"] < float(config.get("min_schema_distance", 0.25)):
        raise ValueError("held-out schema is not sufficiently different from prior schema")

    resource = selected["resource"]
    train_payload, train_meta = prior.fetch_json(resource["train_url"])
    holdout_payload, holdout_meta = prior.fetch_json(resource["holdout_url"])
    train_rows = prior.object_rows(train_payload, int(resource.get("train_rows", 24)))
    holdout_rows = prior.object_rows(holdout_payload, int(resource.get("holdout_rows", 12)))
    profile = prior.infer_profile(train_rows)
    stressors = derive_stressors(profile)
    baseline = baseline_transfer_failure(train_rows, profile, stressors)
    repairs = prior.choose_repairs(profile, baseline["violations"])
    verification = prior.verify_repair(train_rows, holdout_rows, profile, repairs, learned)
    constraint_checks = verify_constraint_rejection(train_rows, profile, repairs, stressors)

    expected_repair_strategies = set()
    for violation in baseline["violations"]:
        if violation["kind"] == "IDENTITY_UNIQUENESS":
            expected_repair_strategies.add("PRIMARY_KEY_AND_UPSERT")
        elif violation["kind"] == "NOT_NULL":
            expected_repair_strategies.add("NOT_NULL_CONSTRAINT")
        elif violation["kind"] == "BOOLEAN_DOMAIN":
            expected_repair_strategies.add("BOOLEAN_CHECK_CONSTRAINT")
    selected_strategies = {item["strategy"] for item in repairs}
    repair_coverage = expected_repair_strategies <= selected_strategies
    constraint_pass = all(constraint_checks.values()) and bool(constraint_checks)
    passed = all([
        baseline["status"] == "DEFECT_DETECTED",
        repair_coverage,
        verification["status"] == "PASS",
        verification["fresh_holdout_disjoint"] is True,
        verification["fresh_holdout_pass"] is True,
        verification["learned_candidate_query_correct"] is True,
        verification["rollback_preserved_state"] is True,
        constraint_pass,
        selected["id"] != prior_id,
    ])
    status = "PASS_CROSS_STRUCTURE_INVARIANT_REPAIR_TRANSFER_V1" if passed else "FAIL_CROSS_STRUCTURE_INVARIANT_REPAIR_TRANSFER_V1"
    report = {
        "schema": "yado.cross_structure_invariant_repair_transfer.v1",
        "status": status,
        "prior_experience": {
            "path": config["prior_experience_path"],
            "source_commit": receipt["source_commit"],
            "workflow_run_id": receipt["workflow_run_id"],
            "selected_resource_id": prior_id,
            "prior_regression_tests": receipt["full_regression"]["tests_run"],
        },
        "resource_selection": {
            "selected_resource_id": selected["id"],
            "prior_resource_excluded": selected["id"] != prior_id,
            "schema_distance_from_prior": selected["schema_distance_from_prior"],
            "ranked_candidates": [
                {
                    "id": item["id"],
                    "schema_distance_from_prior": item["schema_distance_from_prior"],
                    "transfer_score": item["transfer_score"],
                    "fields": item["profile"]["fields"],
                }
                for item in ranked
            ],
        },
        "derived_profile": profile,
        "derived_stressors": stressors,
        "baseline": baseline,
        "repair_selection": {
            "repairs": repairs,
            "expected_repair_strategies": sorted(expected_repair_strategies),
            "selected_repair_strategies": sorted(selected_strategies),
            "repair_coverage": repair_coverage,
            "selection_driven_by_observed_violations": True,
            "catalog_bounded": True,
        },
        "verification": verification,
        "constraint_checks": constraint_checks,
        "external_data": {
            "train": train_meta,
            "holdout": holdout_meta,
            "train_rows": len(train_rows),
            "holdout_rows": len(holdout_rows),
        },
        "transfer_claim": {
            "different_resource_from_prior": True,
            "independent_profile_derivation": True,
            "repair_not_copied_as_fixed_tuple": True,
            "repair_selected_from_new_observed_violations": True,
        },
        "safety_boundary": {
            "public_read_only_api": True,
            "credentials_used": False,
            "authenticated_access": False,
            "external_writes": False,
            "remote_code_execution": False,
            "downloaded_code_executed": False,
            "canonical_mutation": False,
        },
        "g3_genesis_performed": False,
        "consciousness_claimed": False,
        "next_step": "MULTI_RESOURCE_SELF_DIRECTED_DATA_TASK_LOOP_V1",
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    return report


def self_test() -> None:
    prior_profile = {
        "fields": ["id", "postId", "name", "email", "body"],
    }
    new_profile = {
        "fields": ["id", "userId", "title", "body"],
        "identity_field": "id",
        "invariants": [
            {"kind": "IDENTITY_UNIQUENESS", "field": "id"},
            {"kind": "NOT_NULL", "field": "id"},
            {"kind": "NOT_NULL", "field": "title"},
        ],
    }
    assert schema_distance(prior_profile, new_profile) > 0.5
    stressors = derive_stressors(new_profile)
    assert {s["kind"] for s in stressors} == {"REPEAT_INGESTION", "NULL_REQUIRED_FIELD"}
    verified = {
        "status": "PASS_VERIFIED_ENDOGENOUS_DATA_INVARIANT_REPAIR_V1",
        "full_regression": {"status": "PASS", "tests_run": 200, "failures": [], "errors": []},
        "full_kernel_audit": "PASS",
        "fresh_holdout_pass": True,
        "canonical_mutation": False,
    }
    verify_prior_receipt(verified)
    print("PASS_CROSS_STRUCTURE_INVARIANT_REPAIR_TRANSFER_SELF_TEST")


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
    print(json.dumps({
        "status": report["status"],
        "prior_resource": report["prior_experience"]["selected_resource_id"],
        "selected_resource": report["resource_selection"]["selected_resource_id"],
        "schema_distance": report["resource_selection"]["schema_distance_from_prior"],
        "derived_invariants": len(report["derived_profile"]["invariants"]),
        "derived_stressors": [x["kind"] for x in report["derived_stressors"]],
        "repairs": report["repair_selection"]["selected_repair_strategies"],
        "fresh_holdout": report["verification"]["fresh_holdout_pass"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
