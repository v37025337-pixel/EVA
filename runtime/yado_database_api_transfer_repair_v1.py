from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sqlite3
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent.parent
ALLOWED_HOSTS = {"jsonplaceholder.typicode.com"}
MAX_BYTES = 400_000
USER_AGENT = "YADO-Database-API-Transfer-Repair/1.0"


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
    if parsed.scheme != "https" or parsed.hostname not in ALLOWED_HOSTS:
        raise ValueError("endpoint outside bounded public read-only allowlist")
    req = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"}, method="GET")
    with urlopen(req, timeout=timeout) as response:
        raw = response.read(MAX_BYTES + 1)
        if len(raw) > MAX_BYTES:
            raise ValueError("response exceeds bounded size")
        payload = json.loads(raw.decode("utf-8"))
        meta = {
            "url": url,
            "host": parsed.hostname,
            "http_status": int(response.status),
            "bytes": len(raw),
            "sha256": sha256_bytes(raw),
            "read_only": True,
            "credentials_used": False,
        }
        return payload, meta


def normalize_todos(payload: Any, limit: int = 50) -> list[tuple[int, int, str, int]]:
    if not isinstance(payload, list):
        raise ValueError("expected JSON array")
    rows: list[tuple[int, int, str, int]] = []
    for item in payload[:limit]:
        if not isinstance(item, dict):
            continue
        source_id = int(item["id"])
        user_id = int(item["userId"])
        title = str(item["title"])
        completed = 1 if bool(item["completed"]) else 0
        rows.append((source_id, user_id, title, completed))
    if not rows:
        raise ValueError("no normalized rows")
    return rows


def baseline_failure(rows: list[tuple[int, int, str, int]], learned) -> dict[str, Any]:
    conn = sqlite3.connect(":memory:")
    try:
        conn.execute("CREATE TABLE todo_bad(source_id INTEGER, user_id INTEGER, title TEXT, completed INTEGER)")
        insert_sql = "INSERT INTO todo_bad(source_id,user_id,title,completed) VALUES (?,?,?,?)"
        conn.executemany(insert_sql, rows)
        conn.executemany(insert_sql, rows)
        conn.commit()
        row_count = conn.execute("SELECT COUNT(*) FROM todo_bad").fetchone()[0]
        distinct_count = conn.execute("SELECT COUNT(DISTINCT source_id) FROM todo_bad").fetchone()[0]
        duplicate_groups = conn.execute(
            "SELECT COUNT(*) FROM (SELECT source_id FROM todo_bad GROUP BY source_id HAVING COUNT(*)>1)"
        ).fetchone()[0]
        learned_query_rows = learned.select_where(conn, "todo_bad", ["source_id", "user_id"], "completed", 0)
        table_info = conn.execute("PRAGMA table_info(todo_bad)").fetchall()
        has_primary_key = any(int(col[5]) > 0 for col in table_info)
        defect = row_count != distinct_count and duplicate_groups > 0 and not has_primary_key
        return {
            "status": "DEFECT_DETECTED" if defect else "DEFECT_NOT_DETECTED",
            "defect_detected": bool(defect),
            "row_count_after_duplicate_load": int(row_count),
            "distinct_source_ids": int(distinct_count),
            "duplicate_source_id_groups": int(duplicate_groups),
            "primary_key_present": bool(has_primary_key),
            "learned_candidate_query_rows": len(learned_query_rows),
            "diagnosis": "duplicate external identities are admitted because the baseline schema lacks an identity constraint",
        }
    finally:
        conn.close()


def expected_group_counts(rows: list[tuple[int, int, str, int]]) -> list[tuple[int, int, int]]:
    counts: dict[tuple[int, int], int] = {}
    for _, user_id, _, completed in rows:
        counts[(user_id, completed)] = counts.get((user_id, completed), 0) + 1
    return sorted((u, c, n) for (u, c), n in counts.items())


def repaired_database(train_rows: list[tuple[int, int, str, int]], holdout_rows: list[tuple[int, int, str, int]], learned) -> dict[str, Any]:
    conn = sqlite3.connect(":memory:")
    try:
        conn.execute(
            "CREATE TABLE todo_fixed("
            "source_id INTEGER PRIMARY KEY,"
            "user_id INTEGER NOT NULL,"
            "title TEXT NOT NULL,"
            "completed INTEGER NOT NULL CHECK(completed IN (0,1))"
            ")"
        )
        conn.execute("CREATE INDEX idx_todo_fixed_user_completed ON todo_fixed(user_id, completed)")
        upsert_sql = (
            "INSERT INTO todo_fixed(source_id,user_id,title,completed) VALUES (?,?,?,?) "
            "ON CONFLICT(source_id) DO UPDATE SET user_id=excluded.user_id,title=excluded.title,completed=excluded.completed"
        )
        conn.executemany(upsert_sql, train_rows)
        conn.executemany(upsert_sql, train_rows)
        conn.commit()
        train_count = conn.execute("SELECT COUNT(*) FROM todo_fixed").fetchone()[0]
        unique_train = len({r[0] for r in train_rows})
        idempotent_train = train_count == unique_train

        conn.executemany(upsert_sql, holdout_rows)
        conn.commit()
        all_rows_by_id: dict[int, tuple[int, int, str, int]] = {r[0]: r for r in train_rows}
        all_rows_by_id.update({r[0]: r for r in holdout_rows})
        all_rows = list(all_rows_by_id.values())
        final_count = conn.execute("SELECT COUNT(*) FROM todo_fixed").fetchone()[0]
        groups = conn.execute(
            "SELECT user_id, completed, COUNT(*) FROM todo_fixed GROUP BY user_id, completed ORDER BY user_id, completed"
        ).fetchall()
        expected_groups = expected_group_counts(all_rows)

        sample_user = all_rows[0][1]
        sample_completed = all_rows[0][3]
        plan = conn.execute(
            "EXPLAIN QUERY PLAN SELECT source_id FROM todo_fixed WHERE user_id=? AND completed=?",
            (sample_user, sample_completed),
        ).fetchall()
        plan_text = " | ".join(str(x) for row in plan for x in row)
        index_used = "idx_todo_fixed_user_completed" in plan_text

        learned_rows = learned.select_where(conn, "todo_fixed", ["source_id", "title"], "completed", 0)
        expected_incomplete = sum(1 for row in all_rows if row[3] == 0)
        learned_query_correct = len(learned_rows) == expected_incomplete

        before_rollback = final_count
        conn.execute("BEGIN")
        conn.execute(
            "INSERT INTO todo_fixed(source_id,user_id,title,completed) VALUES (?,?,?,?)",
            (9_999_999, 999, "rollback-probe", 0),
        )
        conn.rollback()
        after_rollback = conn.execute("SELECT COUNT(*) FROM todo_fixed").fetchone()[0]
        rollback_preserved = before_rollback == after_rollback

        holdout_ids = {r[0] for r in holdout_rows}
        present_holdout = conn.execute(
            f"SELECT COUNT(*) FROM todo_fixed WHERE source_id IN ({','.join('?' for _ in holdout_ids)})",
            tuple(sorted(holdout_ids)),
        ).fetchone()[0] if holdout_ids else 0
        holdout_pass = present_holdout == len(holdout_ids)

        passed = all(
            [
                idempotent_train,
                final_count == len(all_rows_by_id),
                groups == expected_groups,
                index_used,
                learned_query_correct,
                rollback_preserved,
                holdout_pass,
            ]
        )
        return {
            "status": "PASS" if passed else "FAIL",
            "repair_strategy": [
                "PRIMARY_KEY_EXTERNAL_IDENTITY",
                "PARAMETERIZED_UPSERT",
                "COMPOSITE_QUERY_INDEX",
                "CHECK_CONSTRAINT_BOOLEAN_DOMAIN",
                "TRANSACTION_ROLLBACK_VERIFICATION",
            ],
            "train_idempotent": bool(idempotent_train),
            "train_unique_count": int(unique_train),
            "row_count_after_holdout": int(final_count),
            "expected_unique_count": len(all_rows_by_id),
            "group_counts_match_external_data": groups == expected_groups,
            "index_used_for_bounded_query": bool(index_used),
            "query_plan": plan_text,
            "learned_candidate_query_correct": bool(learned_query_correct),
            "rollback_preserved_state": bool(rollback_preserved),
            "fresh_holdout_count": len(holdout_ids),
            "fresh_holdout_present": int(present_holdout),
            "fresh_holdout_pass": bool(holdout_pass),
        }
    finally:
        conn.close()


def run(config_path: Path, out_path: Path) -> dict[str, Any]:
    config = load_json(config_path)
    candidate_path = ROOT / config["learned_candidate_path"]
    learned = load_learned_candidate(candidate_path)
    component = learned.component()
    expected_digest = config["required_study_digest"]
    if component.get("study_digest") != expected_digest:
        raise ValueError("learned candidate study digest mismatch")
    if component.get("canonical_active") is not False:
        raise ValueError("development candidate unexpectedly canonical")

    train_payload, train_meta = fetch_json(config["train_url"])
    holdout_payload, holdout_meta = fetch_json(config["holdout_url"])
    train_rows = normalize_todos(train_payload, int(config.get("max_train_rows", 30)))
    holdout_rows = normalize_todos(holdout_payload, int(config.get("max_holdout_rows", 20)))

    train_shape = learned.summarize_json_shape(train_payload)
    holdout_shape = learned.summarize_json_shape(holdout_payload)
    baseline = baseline_failure(train_rows, learned)
    repair = repaired_database(train_rows, holdout_rows, learned)

    status = "PASS_DATABASE_API_TRANSFER_REPAIR_V1" if baseline["defect_detected"] and repair["status"] == "PASS" else "FAIL_DATABASE_API_TRANSFER_REPAIR_V1"
    report = {
        "schema": "yado.database_api_transfer_repair.v1",
        "status": status,
        "used_study_digest": component["study_digest"],
        "candidate_skill_count": len(component.get("learned_skills", [])),
        "candidate_component": component,
        "external_data": {
            "train": train_meta,
            "holdout": holdout_meta,
            "train_shape": train_shape,
            "holdout_shape": holdout_shape,
            "train_rows": len(train_rows),
            "holdout_rows": len(holdout_rows),
        },
        "baseline": baseline,
        "repair": repair,
        "causal_chain": [
            "PUBLIC_API_DATA",
            "BASELINE_SCHEMA",
            "DUPLICATE_IDENTITY_FAILURE",
            "DIAGNOSIS_MISSING_IDENTITY_CONSTRAINT",
            "REPAIRED_SCHEMA_AND_UPSERT",
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
            safe = {"todo_bad", "todo_fixed", "source_id", "user_id", "title", "completed"}
            if table not in safe or where_column not in safe or any(c not in safe for c in columns):
                raise ValueError("unsafe test identifier")
            q = f"SELECT {', '.join(columns)} FROM {table} WHERE {where_column} = ?"
            return conn.execute(q, (value,)).fetchall()

    rows = [(1, 1, "a", 0), (2, 1, "b", 1), (3, 2, "c", 0)]
    holdout = [(4, 2, "d", 1), (5, 3, "e", 0)]
    baseline = baseline_failure(rows, Learned)
    repair = repaired_database(rows, holdout, Learned)
    assert baseline["defect_detected"] is True, baseline
    assert repair["status"] == "PASS", repair
    assert repair["fresh_holdout_pass"] is True, repair
    print("PASS_DATABASE_API_TRANSFER_REPAIR_SELF_TEST")


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
        "study_digest": report["used_study_digest"],
        "candidate_skill_count": report["candidate_skill_count"],
        "baseline_defect": report["baseline"]["defect_detected"],
        "repair": report["repair"]["status"],
        "fresh_holdout": report["repair"]["fresh_holdout_pass"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
