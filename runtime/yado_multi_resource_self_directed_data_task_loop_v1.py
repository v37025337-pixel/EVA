from __future__ import annotations

import argparse
import hashlib
import json
import math
from copy import deepcopy
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener

ROOT = Path(__file__).resolve().parent.parent
ALLOWED_HOSTS = {
    "jsonplaceholder.typicode.com",
    "earthquake.usgs.gov",
    "api.worldbank.org",
    "api.open-meteo.com",
}
MAX_BYTES = 1_500_000
USER_AGENT = "YADO-Multi-Resource-Self-Directed-Data-Task-Loop/1.0"


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def verify_history(receipts: list[dict[str, Any]]) -> dict[str, Any]:
    if len(receipts) < 2:
        raise ValueError("at least two verified receipts are required")
    resources: set[str] = set()
    runs: list[int] = []
    for receipt in receipts:
        if not str(receipt.get("status", "")).startswith("PASS_VERIFIED_"):
            raise ValueError("history contains an unverified receipt")
        regression = receipt.get("full_regression", {})
        if regression.get("status") != "PASS" or int(regression.get("tests_run", 0)) < 200:
            raise ValueError("history receipt lacks complete regression proof")
        if regression.get("failures") != [] or regression.get("errors") != []:
            raise ValueError("history receipt contains regression failures")
        audit = receipt.get("full_kernel_audit")
        audit_status = audit.get("status") if isinstance(audit, dict) else audit
        if audit_status != "PASS":
            raise ValueError("history receipt lacks full-kernel audit proof")
        if receipt.get("canonical_mutation") is not False:
            raise ValueError("history unexpectedly mutated canonical state")
        for key in ("selected_resource_id", "prior_resource_id"):
            if receipt.get(key):
                resources.add(str(receipt[key]))
        runs.append(int(receipt.get("workflow_run_id", 0)))
    return {
        "verified_receipt_count": len(receipts),
        "verified_resources": sorted(resources),
        "verified_runs": runs,
    }


def fetch_json(url: str, timeout: int = 25) -> tuple[Any, dict[str, Any]]:
    parsed = urlparse(url)
    if (parsed.scheme != "https" or parsed.hostname not in ALLOWED_HOSTS
            or parsed.username is not None or parsed.password is not None
            or parsed.port not in (None, 443)):
        raise ValueError("endpoint outside bounded public read-only allowlist")
    req = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"}, method="GET")
    with build_opener(_NoRedirect()).open(req, timeout=timeout) as response:
        raw = response.read(MAX_BYTES + 1)
        if len(raw) > MAX_BYTES:
            raise ValueError("response exceeds bounded size")
        payload = json.loads(raw.decode("utf-8"))
        return payload, {
            "url": url,
            "host": parsed.hostname,
            "http_status": int(response.status),
            "bytes": len(raw),
            "sha256": sha256_bytes(raw),
            "read_only": True,
            "credentials_used": False,
        }


def scalar(value: Any) -> Any:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, (str, int, float)) or value is None:
        return value
    return json.dumps(value, sort_keys=True, ensure_ascii=False)


def classify_and_normalize(payload: Any) -> tuple[str, list[dict[str, Any]], dict[str, Any]]:
    if isinstance(payload, dict) and payload.get("type") == "FeatureCollection" and isinstance(payload.get("features"), list):
        records: list[dict[str, Any]] = []
        for feature in payload["features"]:
            if not isinstance(feature, dict):
                continue
            props = feature.get("properties") if isinstance(feature.get("properties"), dict) else {}
            geometry = feature.get("geometry") if isinstance(feature.get("geometry"), dict) else {}
            coords = geometry.get("coordinates") if isinstance(geometry.get("coordinates"), list) else []
            if feature.get("id") is None or props.get("time") is None or len(coords) < 2:
                continue
            records.append({
                "id": str(feature["id"]),
                "time": int(props["time"]),
                "magnitude": scalar(props.get("mag")),
                "longitude": float(coords[0]),
                "latitude": float(coords[1]),
                "depth": float(coords[2]) if len(coords) > 2 and coords[2] is not None else None,
            })
        return "GEO_EVENT_STREAM", records, {
            "shape": "geojson_feature_collection",
            "fields": sorted(records[0]) if records else [],
        }

    if (
        isinstance(payload, list)
        and len(payload) >= 2
        and isinstance(payload[0], dict)
        and isinstance(payload[1], list)
        and ("page" in payload[0] or "pages" in payload[0])
    ):
        records = []
        for item in payload[1]:
            if not isinstance(item, dict):
                continue
            date, value = item.get("date"), item.get("value")
            if date is None or value is None or not isinstance(value, (int, float)):
                continue
            country = item.get("country") if isinstance(item.get("country"), dict) else {}
            indicator = item.get("indicator") if isinstance(item.get("indicator"), dict) else {}
            records.append({
                "period": str(date),
                "value": float(value),
                "country": str(item.get("countryiso3code") or country.get("id") or ""),
                "indicator": str(indicator.get("id") or ""),
            })
        return "INDICATOR_SERIES", records, {
            "shape": "world_bank_indicator_series",
            "fields": sorted(records[0]) if records else [],
        }

    if isinstance(payload, dict) and isinstance(payload.get("hourly"), dict) and isinstance(payload["hourly"].get("time"), list):
        hourly = payload["hourly"]
        times = hourly.get("time", [])
        value_key = next(
            (key for key, value in hourly.items() if key != "time" and isinstance(value, list) and len(value) == len(times)),
            None,
        )
        if value_key is None:
            return "TIME_SERIES", [], {"shape": "hourly_time_series", "fields": []}
        records = []
        for t, value in zip(times, hourly[value_key]):
            if t is None or value is None or not isinstance(value, (int, float)):
                continue
            records.append({"time": str(t), "value": float(value), "variable": str(value_key)})
        return "TIME_SERIES", records, {
            "shape": "hourly_time_series",
            "fields": sorted(records[0]) if records else [],
            "value_key": value_key,
        }

    if isinstance(payload, list) and payload and all(isinstance(item, dict) for item in payload[: min(8, len(payload))]):
        records = []
        for item in payload:
            row = {str(key): scalar(value) for key, value in item.items() if isinstance(key, str)}
            if row:
                records.append(row)
        return "RELATIONAL_RECORDS", records, {
            "shape": "array_of_objects",
            "fields": sorted(records[0]) if records else [],
        }

    raise ValueError("unsupported public data shape")


def split_train_holdout(records: list[dict[str, Any]], minimum: int = 8) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if len(records) < minimum:
        raise ValueError(f"insufficient normalized records: {len(records)}")
    cut = max(4, min(len(records) - 3, int(len(records) * 0.7)))
    train, holdout = records[:cut], records[cut:]
    if len(holdout) < 3:
        raise ValueError("insufficient held-out records")
    return train, holdout


def unique_field(rows: list[dict[str, Any]], field: str) -> bool:
    values = [row.get(field) for row in rows]
    return bool(values) and all(value is not None for value in values) and len(values) == len(set(map(str, values)))


def non_null_field(rows: list[dict[str, Any]], field: str) -> bool:
    return bool(rows) and all(row.get(field) is not None for row in rows)


def derive_task(task_class: str, rows: list[dict[str, Any]]) -> dict[str, Any]:
    if task_class == "GEO_EVENT_STREAM":
        return {
            "task_class": task_class,
            "identity_field": "id",
            "invariants": [
                {"kind": "IDENTITY_UNIQUENESS", "field": "id"},
                {"kind": "NOT_NULL", "field": "time"},
                {"kind": "NUMERIC_RANGE", "field": "longitude", "min": -180.0, "max": 180.0},
                {"kind": "NUMERIC_RANGE", "field": "latitude", "min": -90.0, "max": 90.0},
            ],
            "stressors": ["REPEAT_INGESTION", "OUT_OF_RANGE_LONGITUDE"],
            "repair_catalog": ["DEDUPLICATE_BY_ID", "REJECT_COORDINATE_OUT_OF_RANGE", "SORT_BY_TIME"],
        }
    if task_class == "INDICATOR_SERIES":
        return {
            "task_class": task_class,
            "identity_field": "period",
            "invariants": [
                {"kind": "PERIOD_UNIQUENESS", "field": "period"},
                {"kind": "NOT_NULL", "field": "value"},
                {"kind": "NUMERIC", "field": "value"},
            ],
            "stressors": ["REPEAT_PERIOD", "NULL_NUMERIC_VALUE"],
            "repair_catalog": ["UPSERT_BY_PERIOD", "REJECT_NULL_VALUE", "SORT_PERIOD"],
        }
    if task_class == "TIME_SERIES":
        return {
            "task_class": task_class,
            "identity_field": "time",
            "invariants": [
                {"kind": "TIME_UNIQUENESS", "field": "time"},
                {"kind": "TIME_MONOTONIC", "field": "time"},
                {"kind": "NOT_NULL", "field": "value"},
                {"kind": "NUMERIC", "field": "value"},
            ],
            "stressors": ["REPEAT_TIMESTAMP", "NULL_NUMERIC_VALUE", "REVERSE_ORDER"],
            "repair_catalog": ["DEDUPLICATE_BY_TIME", "REJECT_NULL_VALUE", "SORT_BY_TIME"],
        }
    if task_class == "RELATIONAL_RECORDS":
        fields = sorted({key for row in rows for key in row})
        identity = next((field for field in ("id", "source_id", "uuid") if field in fields and unique_field(rows, field)), None)
        if identity is None:
            raise ValueError("relational sample lacks a unique identity field")
        required = next((field for field in fields if field != identity and non_null_field(rows, field)), None)
        if required is None:
            raise ValueError("relational sample lacks a derived required field")
        return {
            "task_class": task_class,
            "identity_field": identity,
            "required_field": required,
            "invariants": [
                {"kind": "IDENTITY_UNIQUENESS", "field": identity},
                {"kind": "NOT_NULL", "field": required},
            ],
            "stressors": ["REPEAT_INGESTION", "NULL_REQUIRED_FIELD"],
            "repair_catalog": ["PRIMARY_KEY_AND_UPSERT", "REJECT_NULL_REQUIRED"],
        }
    raise ValueError(f"unknown task class: {task_class}")


def synthetic_identity(rows: list[dict[str, Any]], field: str) -> str:
    return f"YADO-SYNTHETIC-{len(rows)}-{str(rows[0].get(field)) if rows else 'EMPTY'}"


def corrupt(rows: list[dict[str, Any]], task: dict[str, Any]) -> list[dict[str, Any]]:
    out = [deepcopy(row) for row in rows]
    if not out:
        return out
    first = deepcopy(out[0])
    cls, identity = task["task_class"], task["identity_field"]
    out.append(deepcopy(first))
    if cls == "GEO_EVENT_STREAM":
        bad = deepcopy(first)
        bad[identity] = synthetic_identity(rows, identity)
        bad["longitude"] = 999.0
        out.append(bad)
    elif cls == "INDICATOR_SERIES":
        bad = deepcopy(first)
        bad[identity] = synthetic_identity(rows, identity)
        bad["value"] = None
        out.append(bad)
    elif cls == "TIME_SERIES":
        bad = deepcopy(first)
        bad[identity] = "9999-YADO-SYNTHETIC"
        bad["value"] = None
        out.append(bad)
        out.reverse()
    elif cls == "RELATIONAL_RECORDS":
        bad = deepcopy(first)
        bad[identity] = synthetic_identity(rows, identity)
        bad[task["required_field"]] = None
        out.append(bad)
    return out


def detect_violations(rows: list[dict[str, Any]], task: dict[str, Any]) -> list[dict[str, Any]]:
    violations: list[dict[str, Any]] = []
    cls, identity = task["task_class"], task["identity_field"]
    ids = [str(row.get(identity)) for row in rows]
    if len(ids) != len(set(ids)):
        duplicate_kind = {
            "INDICATOR_SERIES": "PERIOD_UNIQUENESS",
            "TIME_SERIES": "TIME_UNIQUENESS",
        }.get(cls, "IDENTITY_UNIQUENESS")
        violations.append({"kind": duplicate_kind, "field": identity})
    for invariant in task["invariants"]:
        kind, field = invariant["kind"], invariant["field"]
        if kind == "NOT_NULL" and any(row.get(field) is None for row in rows):
            violations.append({"kind": kind, "field": field})
        elif kind == "NUMERIC_RANGE":
            lo, hi = float(invariant["min"]), float(invariant["max"])
            if any(
                row.get(field) is None
                or not isinstance(row.get(field), (int, float))
                or not (lo <= float(row[field]) <= hi)
                for row in rows
            ):
                violations.append({"kind": kind, "field": field, "min": lo, "max": hi})
    if cls == "TIME_SERIES":
        times = [str(row.get("time")) for row in rows if row.get("time") is not None]
        if times != sorted(times):
            violations.append({"kind": "TIME_MONOTONIC", "field": "time"})
    unique: dict[str, dict[str, Any]] = {}
    for violation in violations:
        unique[json.dumps(violation, sort_keys=True)] = violation
    return list(unique.values())


def choose_repairs(task: dict[str, Any], violations: list[dict[str, Any]]) -> list[str]:
    cls = task["task_class"]
    kinds = {violation["kind"] for violation in violations}
    selected: list[str] = []
    if "IDENTITY_UNIQUENESS" in kinds:
        selected.append("DEDUPLICATE_BY_ID" if cls == "GEO_EVENT_STREAM" else "PRIMARY_KEY_AND_UPSERT")
    if "PERIOD_UNIQUENESS" in kinds:
        selected.append("UPSERT_BY_PERIOD")
    if "TIME_UNIQUENESS" in kinds:
        selected.append("DEDUPLICATE_BY_TIME")
    if "NOT_NULL" in kinds:
        selected.append("REJECT_NULL_VALUE" if cls in {"INDICATOR_SERIES", "TIME_SERIES"} else "REJECT_NULL_REQUIRED")
    if "NUMERIC_RANGE" in kinds:
        selected.append("REJECT_COORDINATE_OUT_OF_RANGE")
    if "TIME_MONOTONIC" in kinds:
        selected.append("SORT_BY_TIME")
    if cls == "GEO_EVENT_STREAM" and "SORT_BY_TIME" not in selected:
        selected.append("SORT_BY_TIME")
    return selected


def valid_under_selected_repairs(row: dict[str, Any], task: dict[str, Any], repairs: list[str]) -> bool:
    reject_null = "REJECT_NULL_VALUE" in repairs or "REJECT_NULL_REQUIRED" in repairs
    reject_range = "REJECT_COORDINATE_OUT_OF_RANGE" in repairs
    for invariant in task["invariants"]:
        kind, field = invariant["kind"], invariant["field"]
        value = row.get(field)
        if reject_null and kind == "NOT_NULL" and value is None:
            return False
        if reject_null and kind == "NUMERIC" and not isinstance(value, (int, float)):
            return False
        if reject_range and kind == "NUMERIC_RANGE":
            if not isinstance(value, (int, float)):
                return False
            if not (float(invariant["min"]) <= float(value) <= float(invariant["max"])):
                return False
    return True


def repair_rows(rows: list[dict[str, Any]], task: dict[str, Any], repairs: list[str]) -> list[dict[str, Any]]:
    identity = task["identity_field"]
    filtered = [deepcopy(row) for row in rows if valid_under_selected_repairs(row, task, repairs)]
    dedupe_enabled = any(
        repair in repairs
        for repair in ("DEDUPLICATE_BY_ID", "PRIMARY_KEY_AND_UPSERT", "UPSERT_BY_PERIOD", "DEDUPLICATE_BY_TIME")
    )
    if dedupe_enabled:
        by_id: dict[str, dict[str, Any]] = {}
        for row in filtered:
            key = row.get(identity)
            if key is not None:
                by_id[str(key)] = row
        result = list(by_id.values())
    else:
        result = filtered
    if result and ("SORT_BY_TIME" in repairs or task["task_class"] == "TIME_SERIES"):
        sort_field = "time" if "time" in result[0] else identity
        result.sort(key=lambda row: str(row.get(sort_field)))
    elif result and task["task_class"] == "INDICATOR_SERIES":
        result.sort(key=lambda row: str(row.get(identity)))
    return result


def required_violation_kinds(task: dict[str, Any]) -> set[str]:
    mapping = {
        "REPEAT_INGESTION": "IDENTITY_UNIQUENESS",
        "REPEAT_PERIOD": "PERIOD_UNIQUENESS",
        "REPEAT_TIMESTAMP": "TIME_UNIQUENESS",
        "NULL_NUMERIC_VALUE": "NOT_NULL",
        "NULL_REQUIRED_FIELD": "NOT_NULL",
        "OUT_OF_RANGE_LONGITUDE": "NUMERIC_RANGE",
        "REVERSE_ORDER": "TIME_MONOTONIC",
    }
    return {mapping[stressor] for stressor in task["stressors"] if stressor in mapping}


def verify_case(train: list[dict[str, Any]], holdout: list[dict[str, Any]], task: dict[str, Any]) -> dict[str, Any]:
    damaged_train = corrupt(train, task)
    violations = detect_violations(damaged_train, task)
    repairs = choose_repairs(task, violations)
    repaired_train = repair_rows(damaged_train, task, repairs)

    damaged_holdout = corrupt(holdout, task)
    repaired_holdout = repair_rows(damaged_holdout, task, repairs)
    identity = task["identity_field"]
    expected_holdout = {str(row[identity]) for row in holdout if row.get(identity) is not None}
    actual_holdout = {str(row[identity]) for row in repaired_holdout if row.get(identity) is not None}
    observed = {violation["kind"] for violation in violations}
    required = required_violation_kinds(task)
    post_train = detect_violations(repaired_train, task)
    post_holdout = detect_violations(repaired_holdout, task)
    passed = all([
        required <= observed,
        bool(repairs),
        post_train == [],
        post_holdout == [],
        expected_holdout == actual_holdout,
    ])
    return {
        "status": "PASS" if passed else "FAIL",
        "derived_invariants": task["invariants"],
        "derived_stressors": task["stressors"],
        "required_violation_kinds": sorted(required),
        "baseline_violations": violations,
        "selected_repairs": repairs,
        "post_repair_violations": post_train,
        "heldout_post_repair_violations": post_holdout,
        "train_input_count": len(train),
        "heldout_input_count": len(holdout),
        "heldout_expected_unique": len(expected_holdout),
        "heldout_repaired_unique": len(actual_holdout),
        "heldout_pass": expected_holdout == actual_holdout,
    }


def novelty_score(task_class: str, record_count: int, prior_resources: set[str], resource_id: str) -> float:
    task_bonus = {
        "GEO_EVENT_STREAM": 120.0,
        "INDICATOR_SERIES": 115.0,
        "TIME_SERIES": 110.0,
        "RELATIONAL_RECORDS": 30.0,
    }.get(task_class, 0.0)
    history_penalty = 80.0 if resource_id in prior_resources else 0.0
    return task_bonus + math.log2(max(record_count, 1) + 1.0) - history_penalty


def run(config_path: Path, out_path: Path) -> dict[str, Any]:
    config = load_json(config_path)
    receipts = [load_json(ROOT / path) for path in config["verified_experience_paths"]]
    history = verify_history(receipts)
    prior_resources = set(history["verified_resources"])

    viable: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    minimum_records = int(config.get("minimum_records_per_source", 8))
    for source in config["sources"]:
        try:
            payload, meta = fetch_json(source["url"])
            task_class, records, shape = classify_and_normalize(payload)
            train, holdout = split_train_holdout(records, minimum_records)
            task = derive_task(task_class, train)
            viable.append({
                "source": source,
                "meta": meta,
                "shape": shape,
                "task_class": task_class,
                "records": records,
                "train": train,
                "holdout": holdout,
                "task": task,
                "novelty_score": novelty_score(task_class, len(records), prior_resources, source["id"]),
            })
        except Exception as exc:
            failures.append({"source_id": source.get("id"), "error": f"{type(exc).__name__}: {exc}"})

    viable.sort(key=lambda item: (item["novelty_score"], item["source"]["id"]), reverse=True)
    target_cases = int(config.get("target_case_count", 3))
    selected: list[dict[str, Any]] = []
    seen_classes: set[str] = set()
    for item in viable:
        if item["task_class"] in seen_classes:
            continue
        selected.append(item)
        seen_classes.add(item["task_class"])
        if len(selected) >= target_cases:
            break
    if len(selected) < target_cases:
        for item in viable:
            if item not in selected:
                selected.append(item)
                if len(selected) >= target_cases:
                    break

    cases: list[dict[str, Any]] = []
    for item in selected:
        verification = verify_case(item["train"], item["holdout"], item["task"])
        cases.append({
            "source_id": item["source"]["id"],
            "domain": item["source"]["domain"],
            "host": item["meta"]["host"],
            "provenance_sha256": item["meta"]["sha256"],
            "task_class": item["task_class"],
            "novelty_score": item["novelty_score"],
            "shape": item["shape"],
            "normalized_record_count": len(item["records"]),
            "verification": verification,
        })

    passed = [case for case in cases if case["verification"]["status"] == "PASS"]
    task_classes = sorted({case["task_class"] for case in passed})
    domains = sorted({case["domain"] for case in passed})
    gate = all([
        len(passed) >= int(config.get("minimum_successful_cases", 3)),
        len(task_classes) >= int(config.get("minimum_task_classes", 3)),
        len(domains) >= int(config.get("minimum_domains", 3)),
        all(case["verification"]["heldout_pass"] for case in passed),
    ])
    report = {
        "schema": "yado.multi_resource_self_directed_data_task_loop.v1",
        "status": "PASS_MULTI_RESOURCE_SELF_DIRECTED_DATA_TASK_LOOP_V1" if gate else "FAIL_MULTI_RESOURCE_SELF_DIRECTED_DATA_TASK_LOOP_V1",
        "verified_history": history,
        "selection": {
            "host_preselected_resource": False,
            "host_preselected_task_class": False,
            "bounded_source_catalog_provided": True,
            "bounded_task_and_repair_catalog_provided": True,
            "selection_rule": "observed_shape_and_novelty_score",
            "available_viable_sources": [
                {
                    "source_id": item["source"]["id"],
                    "domain": item["source"]["domain"],
                    "task_class": item["task_class"],
                    "record_count": len(item["records"]),
                    "novelty_score": item["novelty_score"],
                }
                for item in viable
            ],
            "selected_source_ids": [case["source_id"] for case in cases],
        },
        "cases": cases,
        "source_failures": failures,
        "summary": {
            "successful_cases": len(passed),
            "unique_task_classes": task_classes,
            "unique_domains": domains,
            "all_heldout_pass": bool(passed) and all(case["verification"]["heldout_pass"] for case in passed),
        },
        "safety_boundary": {
            "public_read_only_sources_only": True,
            "credentials_used": False,
            "authenticated_access": False,
            "external_writes": False,
            "remote_code_execution": False,
            "downloaded_code_executed": False,
            "canonical_mutation": False,
        },
        "g3_genesis_performed": False,
        "consciousness_claimed": False,
        "next_step": "CROSS_SOURCE_EVIDENCE_FUSION_AND_DEFICIT_PRIORITIZATION_V1",
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    return report


def self_test() -> None:
    geo = {
        "type": "FeatureCollection",
        "features": [
            {
                "id": f"e{i}",
                "properties": {"time": 1000 + i, "mag": 1.2},
                "geometry": {"coordinates": [10.0 + i, 20.0, 3.0]},
            }
            for i in range(12)
        ],
    }
    cls, rows, _ = classify_and_normalize(geo)
    train, holdout = split_train_holdout(rows)
    assert cls == "GEO_EVENT_STREAM"
    assert verify_case(train, holdout, derive_task(cls, train))["status"] == "PASS"

    wb = [
        {"page": 1},
        [
            {"date": str(2000 + i), "value": 100 + i, "countryiso3code": "TST", "indicator": {"id": "X"}}
            for i in range(12)
        ],
    ]
    cls, rows, _ = classify_and_normalize(wb)
    train, holdout = split_train_holdout(rows)
    assert cls == "INDICATOR_SERIES"
    assert verify_case(train, holdout, derive_task(cls, train))["status"] == "PASS"

    meteo = {
        "hourly": {
            "time": [f"2026-01-01T{i:02d}:00" for i in range(12)],
            "temperature_2m": [float(i) for i in range(12)],
        }
    }
    cls, rows, _ = classify_and_normalize(meteo)
    train, holdout = split_train_holdout(rows)
    assert cls == "TIME_SERIES"
    assert verify_case(train, holdout, derive_task(cls, train))["status"] == "PASS"
    print("PASS_MULTI_RESOURCE_SELF_DIRECTED_DATA_TASK_LOOP_SELF_TEST")


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
        "selected": report["selection"]["selected_source_ids"],
        "successful_cases": report["summary"]["successful_cases"],
        "task_classes": report["summary"]["unique_task_classes"],
        "domains": report["summary"]["unique_domains"],
        "source_failures": report["source_failures"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
