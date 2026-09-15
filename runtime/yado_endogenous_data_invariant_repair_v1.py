from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
import sqlite3
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener

ROOT = Path(__file__).resolve().parent.parent
ALLOWED_HOSTS = {"jsonplaceholder.typicode.com"}
MAX_BYTES = 500_000
USER_AGENT = "YADO-Endogenous-Data-Invariant-Repair/1.0"
_SAFE_IDENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def safe_ident(value: str) -> str:
    if not _SAFE_IDENT.fullmatch(value):
        raise ValueError(f"unsafe identifier: {value!r}")
    return value


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_learned_candidate(path: Path):
    spec = importlib.util.spec_from_file_location("yado_database_web_usage_candidate_v1", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("candidate import spec unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def fetch_json(url: str, timeout: int = 20) -> tuple[Any, dict[str, Any]]:
    parsed = urlparse(url)
    if (parsed.scheme != "https" or parsed.hostname not in ALLOWED_HOSTS
            or parsed.username is not None or parsed.password is not None
            or parsed.port not in (None, 443)):
        raise ValueError("endpoint outside bounded public read-only allowlist")
    request = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"}, method="GET")
    with build_opener(_NoRedirect()).open(request, timeout=timeout) as response:
        raw = response.read(MAX_BYTES + 1)
        if len(raw) > MAX_BYTES:
            raise ValueError("response exceeds bounded size")
        final = urlparse(response.geturl())
        if final.scheme != "https" or final.hostname not in ALLOWED_HOSTS:
            raise ValueError("redirect escaped bounded public read-only allowlist")
        return json.loads(raw.decode("utf-8")), {
            "url": url,
            "final_url": response.geturl(),
            "host": final.hostname,
            "http_status": int(response.status),
            "bytes": len(raw),
            "sha256": sha256_bytes(raw),
            "read_only": True,
            "credentials_used": False,
        }


def object_rows(payload: Any, limit: int) -> list[dict[str, Any]]:
    if not isinstance(payload, list):
        raise ValueError("expected a JSON array")
    rows = [item for item in payload[:limit] if isinstance(item, dict)]
    if len(rows) < 4:
        raise ValueError("insufficient object rows")
    return rows


def scalar_kind(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, int) and not isinstance(value, bool):
        return "int"
    if isinstance(value, float):
        return "float"
    if isinstance(value, str):
        return "str"
    if isinstance(value, (dict, list)):
        return "json"
    return type(value).__name__


def normalize_value(value: Any) -> Any:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, (dict, list)):
        return json.dumps(value, sort_keys=True, separators=(",", ":"))
    return value


def infer_sql_type(values: list[Any]) -> str:
    kinds = {scalar_kind(v) for v in values if v is not None}
    if not kinds:
        return "TEXT"
    if kinds <= {"bool", "int"}:
        return "INTEGER"
    if kinds <= {"bool", "int", "float"}:
        return "REAL"
    return "TEXT"


def infer_profile(rows: list[dict[str, Any]]) -> dict[str, Any]:
    fields = sorted({str(key) for row in rows for key in row})
    safe_fields = [field for field in fields if _SAFE_IDENT.fullmatch(field)]
    if not safe_fields:
        raise ValueError("no safe fields discovered")
    stats: dict[str, Any] = {}
    for field in safe_fields:
        values = [row.get(field) for row in rows]
        non_null = [v for v in values if v is not None]
        normalized = [normalize_value(v) for v in non_null]
        unique = len(set(map(repr, normalized))) == len(non_null) and len(non_null) == len(rows)
        stats[field] = {
            "sql_type": infer_sql_type(values),
            "kinds": sorted({scalar_kind(v) for v in values}),
            "required_observed": all(field in row and row.get(field) is not None for row in rows),
            "unique_observed": bool(unique),
        }
    identity_candidates = [field for field in safe_fields if stats[field]["unique_observed"]]
    identity_field = None
    if "id" in identity_candidates:
        identity_field = "id"
    elif identity_candidates:
        identity_field = sorted(identity_candidates, key=lambda f: (not f.lower().endswith("id"), f))[0]
    if identity_field is None:
        raise ValueError("no observed unique identity field")
    relation_candidates = [
        field for field in safe_fields
        if field != identity_field and field.lower().endswith("id") and stats[field]["sql_type"] in {"INTEGER", "REAL"}
    ]
    group_field = relation_candidates[0] if relation_candidates else None
    invariants: list[dict[str, Any]] = [{
        "kind": "IDENTITY_UNIQUENESS",
        "field": identity_field,
        "evidence": "all sampled values are non-null and unique",
    }]
    for field in safe_fields:
        if stats[field]["required_observed"]:
            invariants.append({"kind": "NOT_NULL", "field": field, "evidence": "no sampled value is missing/null"})
        if stats[field]["kinds"] == ["bool"]:
            invariants.append({"kind": "BOOLEAN_DOMAIN", "field": field, "evidence": "all sampled values are boolean"})
    type_diversity = len({stats[field]["sql_type"] for field in safe_fields})
    nested_fields = sum("json" in stats[field]["kinds"] for field in safe_fields)
    score = len(safe_fields) * 10 + len(relation_candidates) * 7 + type_diversity * 3 + nested_fields
    return {
        "fields": safe_fields,
        "stats": stats,
        "identity_field": identity_field,
        "group_field": group_field,
        "invariants": invariants,
        "selection_score": score,
    }


def choose_resource(resources: list[dict[str, Any]]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    candidates: list[dict[str, Any]] = []
    for resource in resources:
        payload, meta = fetch_json(resource["probe_url"])
        rows = object_rows(payload, int(resource.get("probe_rows", 8)))
        profile = infer_profile(rows)
        candidates.append({"id": resource["id"], "profile": profile, "probe_meta": meta, "resource": resource})
    candidates.sort(
        key=lambda item: (item["profile"]["selection_score"], len(item["profile"]["invariants"]), item["id"]),
        reverse=True,
    )
    return candidates[0], candidates


def create_baseline(conn: sqlite3.Connection, table: str, profile: dict[str, Any]) -> None:
    columns = [f"{safe_ident(field)} {profile['stats'][field]['sql_type']}" for field in profile["fields"]]
    conn.execute(f"CREATE TABLE {safe_ident(table)}({', '.join(columns)})")


def row_tuple(row: dict[str, Any], fields: list[str]) -> tuple[Any, ...]:
    return tuple(normalize_value(row.get(field)) for field in fields)


def load_rows_plain(conn: sqlite3.Connection, table: str, fields: list[str], rows: list[dict[str, Any]]) -> None:
    placeholders = ",".join("?" for _ in fields)
    columns = ",".join(safe_ident(field) for field in fields)
    sql = f"INSERT INTO {safe_ident(table)}({columns}) VALUES ({placeholders})"
    conn.executemany(sql, [row_tuple(row, fields) for row in rows])


def detect_violations(conn: sqlite3.Connection, table: str, profile: dict[str, Any]) -> list[dict[str, Any]]:
    violations: list[dict[str, Any]] = []
    table_name = safe_ident(table)
    for invariant in profile["invariants"]:
        field = safe_ident(invariant["field"])
        if invariant["kind"] == "IDENTITY_UNIQUENESS":
            total = conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
            distinct = conn.execute(f"SELECT COUNT(DISTINCT {field}) FROM {table_name}").fetchone()[0]
            if total != distinct:
                violations.append({"kind": invariant["kind"], "field": field, "total": int(total), "distinct": int(distinct)})
        elif invariant["kind"] == "NOT_NULL":
            nulls = conn.execute(f"SELECT COUNT(*) FROM {table_name} WHERE {field} IS NULL").fetchone()[0]
            if nulls:
                violations.append({"kind": invariant["kind"], "field": field, "null_count": int(nulls)})
        elif invariant["kind"] == "BOOLEAN_DOMAIN":
            invalid = conn.execute(f"SELECT COUNT(*) FROM {table_name} WHERE {field} NOT IN (0,1) OR {field} IS NULL").fetchone()[0]
            if invalid:
                violations.append({"kind": invariant["kind"], "field": field, "invalid_count": int(invalid)})
    return violations


def choose_repairs(profile: dict[str, Any], violations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    repairs: list[dict[str, Any]] = []
    seen = set()
    for violation in violations:
        key = (violation["kind"], violation["field"])
        if key in seen:
            continue
        seen.add(key)
        if violation["kind"] == "IDENTITY_UNIQUENESS":
            repairs.append({
                "strategy": "PRIMARY_KEY_AND_UPSERT",
                "field": violation["field"],
                "reason": "observed identity invariant was violated by repeat ingestion",
            })
        elif violation["kind"] == "NOT_NULL":
            repairs.append({
                "strategy": "NOT_NULL_CONSTRAINT",
                "field": violation["field"],
                "reason": "observed required-field invariant was violated",
            })
        elif violation["kind"] == "BOOLEAN_DOMAIN":
            repairs.append({
                "strategy": "BOOLEAN_CHECK_CONSTRAINT",
                "field": violation["field"],
                "reason": "observed boolean-domain invariant was violated",
            })
    if profile.get("group_field"):
        repairs.append({
            "strategy": "QUERY_INDEX",
            "field": profile["group_field"],
            "reason": "discovered relational/grouping field supports bounded lookup",
        })
    return repairs


def create_repaired(conn: sqlite3.Connection, table: str, profile: dict[str, Any], repairs: list[dict[str, Any]]) -> None:
    identity = profile["identity_field"]
    columns = []
    repair_map = {(r["strategy"], r["field"]) for r in repairs}
    for field in profile["fields"]:
        constraints = []
        if ("PRIMARY_KEY_AND_UPSERT", field) in repair_map:
            constraints.append("PRIMARY KEY")
        if ("NOT_NULL_CONSTRAINT", field) in repair_map:
            constraints.append("NOT NULL")
        if ("BOOLEAN_CHECK_CONSTRAINT", field) in repair_map:
            constraints.append(f"CHECK({safe_ident(field)} IN (0,1))")
        suffix = " " + " ".join(constraints) if constraints else ""
        columns.append(f"{safe_ident(field)} {profile['stats'][field]['sql_type']}{suffix}")
    conn.execute(f"CREATE TABLE {safe_ident(table)}({', '.join(columns)})")
    if any(r["strategy"] == "QUERY_INDEX" for r in repairs):
        group_field = safe_ident(profile["group_field"])
        index_name = safe_ident(f"idx_{table}_{group_field}")
        conn.execute(f"CREATE INDEX {index_name} ON {safe_ident(table)}({group_field})")
    if not any(r["strategy"] == "PRIMARY_KEY_AND_UPSERT" and r["field"] == identity for r in repairs):
        raise RuntimeError("repair selection did not address identity invariant")


def load_rows_repaired(conn: sqlite3.Connection, table: str, profile: dict[str, Any], rows: list[dict[str, Any]]) -> None:
    fields = profile["fields"]
    identity = safe_ident(profile["identity_field"])
    placeholders = ",".join("?" for _ in fields)
    columns = ",".join(safe_ident(field) for field in fields)
    update_fields = [field for field in fields if field != profile["identity_field"]]
    assignments = ",".join(f"{safe_ident(field)}=excluded.{safe_ident(field)}" for field in update_fields)
    sql = (
        f"INSERT INTO {safe_ident(table)}({columns}) VALUES ({placeholders}) "
        f"ON CONFLICT({identity}) DO UPDATE SET {assignments}"
    )
    conn.executemany(sql, [row_tuple(row, fields) for row in rows])


def verify_repair(
    train_rows: list[dict[str, Any]],
    holdout_rows: list[dict[str, Any]],
    profile: dict[str, Any],
    repairs: list[dict[str, Any]],
    learned,
) -> dict[str, Any]:
    conn = sqlite3.connect(":memory:")
    table = "adaptive_fixed"
    try:
        create_repaired(conn, table, profile, repairs)
        load_rows_repaired(conn, table, profile, train_rows)
        load_rows_repaired(conn, table, profile, train_rows)
        conn.commit()
        post_repeat_violations = detect_violations(conn, table, profile)
        identity = profile["identity_field"]
        train_unique = len({normalize_value(row.get(identity)) for row in train_rows})
        train_count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        train_idempotent = train_count == train_unique
        holdout_ids = {normalize_value(row.get(identity)) for row in holdout_rows}
        train_ids = {normalize_value(row.get(identity)) for row in train_rows}
        holdout_disjoint = train_ids.isdisjoint(holdout_ids)
        load_rows_repaired(conn, table, profile, holdout_rows)
        conn.commit()
        final_violations = detect_violations(conn, table, profile)
        present_holdout = 0
        if holdout_ids:
            placeholders = ",".join("?" for _ in holdout_ids)
            present_holdout = conn.execute(
                f"SELECT COUNT(*) FROM {table} WHERE {safe_ident(identity)} IN ({placeholders})",
                tuple(sorted(holdout_ids, key=repr)),
            ).fetchone()[0]
        holdout_pass = holdout_disjoint and present_holdout == len(holdout_ids)
        learned_query_pass = True
        index_used = None
        query_plan = None
        if profile.get("group_field"):
            group_field = profile["group_field"]
            sample_value = normalize_value(train_rows[0].get(group_field))
            selected = learned.select_where(conn, table, [identity, group_field], group_field, sample_value)
            expected = conn.execute(
                f"SELECT COUNT(*) FROM {table} WHERE {safe_ident(group_field)}=?",
                (sample_value,),
            ).fetchone()[0]
            learned_query_pass = len(selected) == expected
            plan = conn.execute(
                f"EXPLAIN QUERY PLAN SELECT {safe_ident(identity)} FROM {table} WHERE {safe_ident(group_field)}=?",
                (sample_value,),
            ).fetchall()
            query_plan = " | ".join(str(x) for row in plan for x in row)
            index_used = f"idx_{table}_{group_field}" in query_plan
        before = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        conn.execute("BEGIN")
        probe = dict(train_rows[0])
        probe[identity] = 9_999_999
        load_rows_repaired(conn, table, profile, [probe])
        conn.rollback()
        after = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        rollback_preserved = before == after
        passed = all([
            not post_repeat_violations,
            train_idempotent,
            not final_violations,
            holdout_pass,
            learned_query_pass,
            rollback_preserved,
            index_used is not False,
        ])
        return {
            "status": "PASS" if passed else "FAIL",
            "post_repeat_violations": post_repeat_violations,
            "final_violations": final_violations,
            "train_idempotent": bool(train_idempotent),
            "fresh_holdout_disjoint": bool(holdout_disjoint),
            "fresh_holdout_count": len(holdout_ids),
            "fresh_holdout_present": int(present_holdout),
            "fresh_holdout_pass": bool(holdout_pass),
            "learned_candidate_query_correct": bool(learned_query_pass),
            "index_used_for_discovered_query": index_used,
            "query_plan": query_plan,
            "rollback_preserved_state": bool(rollback_preserved),
        }
    finally:
        conn.close()


def run(config_path: Path, out_path: Path) -> dict[str, Any]:
    config = load_json(config_path)
    learned = load_learned_candidate(ROOT / config["learned_candidate_path"])
    component = learned.component()
    if component.get("study_digest") != config["required_study_digest"]:
        raise ValueError("learned candidate study digest mismatch")
    if component.get("canonical_active") is not False:
        raise ValueError("development candidate unexpectedly canonical")
    selected, probes = choose_resource(config["resources"])
    resource = selected["resource"]
    train_payload, train_meta = fetch_json(resource["train_url"])
    holdout_payload, holdout_meta = fetch_json(resource["holdout_url"])
    train_rows = object_rows(train_payload, int(resource.get("max_train_rows", 24)))
    holdout_rows = object_rows(holdout_payload, int(resource.get("max_holdout_rows", 12)))
    profile = infer_profile(train_rows)
    conn = sqlite3.connect(":memory:")
    try:
        create_baseline(conn, "adaptive_baseline", profile)
        load_rows_plain(conn, "adaptive_baseline", profile["fields"], train_rows)
        load_rows_plain(conn, "adaptive_baseline", profile["fields"], train_rows)
        conn.commit()
        violations = detect_violations(conn, "adaptive_baseline", profile)
    finally:
        conn.close()
    repairs = choose_repairs(profile, violations)
    verification = verify_repair(train_rows, holdout_rows, profile, repairs, learned)
    identity_violation = any(v["kind"] == "IDENTITY_UNIQUENESS" for v in violations)
    status = (
        "PASS_ENDOGENOUS_DATA_INVARIANT_REPAIR_V1"
        if identity_violation and repairs and verification["status"] == "PASS"
        else "FAIL_ENDOGENOUS_DATA_INVARIANT_REPAIR_V1"
    )
    report = {
        "schema": "yado.endogenous_data_invariant_repair.v1",
        "status": status,
        "used_study_digest": component["study_digest"],
        "candidate_skill_count": len(component.get("learned_skills", [])),
        "resource_selection": {
            "selected_resource_id": resource["id"],
            "selected_score": profile["selection_score"],
            "probes": [{
                "id": item["id"],
                "score": item["profile"]["selection_score"],
                "field_count": len(item["profile"]["fields"]),
                "identity_field": item["profile"]["identity_field"],
                "group_field": item["profile"]["group_field"],
                "probe_meta": item["probe_meta"],
            } for item in probes],
        },
        "derived_profile": profile,
        "baseline": {"repeat_ingestion_cycles": 2, "violations": violations, "defect_detected": bool(violations)},
        "repair_selection": {
            "catalog_bounded": True,
            "selected_repairs": repairs,
            "selection_driven_by_observed_violations": True,
        },
        "verification": verification,
        "external_data": {
            "train": train_meta,
            "holdout": holdout_meta,
            "train_rows": len(train_rows),
            "holdout_rows": len(holdout_rows),
        },
        "causal_chain": [
            "MULTIPLE_PUBLIC_DATA_CANDIDATES",
            "SHAPE_PROBING",
            "ENDOGENOUS_RESOURCE_SELECTION",
            "INVARIANT_DERIVATION_FROM_OBSERVATIONS",
            "REPEAT_INGESTION",
            "INVARIANT_VIOLATION_DETECTION",
            "BOUNDED_REPAIR_SELECTION",
            "SCHEMA_AND_INGESTION_REPAIR",
            "FRESH_HOLDOUT",
            "VERIFIED_TRANSFER",
        ],
        "safety_boundary": {
            "public_read_only_api": True,
            "credentials_used": False,
            "authenticated_access": False,
            "external_writes": False,
            "remote_code_execution": False,
            "downloaded_code_executed": False,
            "canonical_mutation": False,
        },
        "consciousness_claimed": False,
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    return report


def self_test() -> None:
    class Learned:
        @staticmethod
        def select_where(conn, table, columns, where_column, value):
            for name in [table, where_column, *columns]:
                safe_ident(name)
            sql = f"SELECT {', '.join(columns)} FROM {table} WHERE {where_column} = ?"
            return conn.execute(sql, (value,)).fetchall()
    rows = [
        {"ownerId": 1, "id": 1, "title": "a", "active": True},
        {"ownerId": 1, "id": 2, "title": "b", "active": False},
        {"ownerId": 2, "id": 3, "title": "c", "active": True},
        {"ownerId": 2, "id": 4, "title": "d", "active": False},
    ]
    holdout = [
        {"ownerId": 3, "id": 5, "title": "e", "active": True},
        {"ownerId": 3, "id": 6, "title": "f", "active": False},
        {"ownerId": 4, "id": 7, "title": "g", "active": True},
        {"ownerId": 4, "id": 8, "title": "h", "active": False},
    ]
    profile = infer_profile(rows)
    assert profile["identity_field"] == "id", profile
    assert profile["group_field"] == "ownerId", profile
    conn = sqlite3.connect(":memory:")
    try:
        create_baseline(conn, "baseline", profile)
        load_rows_plain(conn, "baseline", profile["fields"], rows)
        load_rows_plain(conn, "baseline", profile["fields"], rows)
        conn.commit()
        violations = detect_violations(conn, "baseline", profile)
    finally:
        conn.close()
    assert any(v["kind"] == "IDENTITY_UNIQUENESS" for v in violations), violations
    repairs = choose_repairs(profile, violations)
    assert any(r["strategy"] == "PRIMARY_KEY_AND_UPSERT" for r in repairs), repairs
    verification = verify_repair(rows, holdout, profile, repairs, Learned)
    assert verification["status"] == "PASS", verification
    assert verification["fresh_holdout_pass"] is True, verification
    print("PASS_ENDOGENOUS_DATA_INVARIANT_REPAIR_SELF_TEST")


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
        "selected_resource": report["resource_selection"]["selected_resource_id"],
        "derived_invariants": len(report["derived_profile"]["invariants"]),
        "violations": len(report["baseline"]["violations"]),
        "repairs": len(report["repair_selection"]["selected_repairs"]),
        "fresh_holdout": report["verification"]["fresh_holdout_pass"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
