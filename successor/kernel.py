"""A restartable task kernel around the actual, pinned YADO G2 runtime."""
from __future__ import annotations

import copy
import json
from pathlib import Path
import sqlite3
import sys

from .archive import ExperienceArchive, canonical, file_sha, sha

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "runtime"))
sys.path.insert(0, str(ROOT / "runtime" / "yado_rc8_v36"))


def encode(obj):
    from yado_g2_unified_execution_fabric_v5 import _TypedJSONV2
    return canonical(_TypedJSONV2.encode(obj))


def decode(text):
    from yado_g2_unified_execution_fabric_v5 import _TypedJSONV2
    return _TypedJSONV2.decode(json.loads(text))


def fingerprint(obj):
    from yado_g2_unified_execution_fabric_v5 import _TypedJSONV2
    def stable(node):
        if isinstance(node, list):
            return [stable(x) for x in node]
        if isinstance(node, dict):
            out = {k: stable(v) for k, v in node.items()}
            if out.get("t") == "dict":
                out["v"].sort(key=lambda pair: canonical(pair[0]))
            return out
        return node
    return sha(canonical(stable(_TypedJSONV2.encode(obj))).encode())


def equivalent(a, b):
    if isinstance(a, (tuple, list)) and isinstance(b, (tuple, list)):
        return len(a) == len(b) and all(equivalent(x, y) for x, y in zip(a, b))
    if isinstance(a, dict) and isinstance(b, dict):
        return a.keys() == b.keys() and all(equivalent(a[k], b[k]) for k in a)
    if isinstance(a, bool) != isinstance(b, bool):
        return False
    return a == b


class SuccessorKernel:
    KERNEL_ID = "YADO_SUCCESSOR_CAUSAL_METACOGNITION_V2"
    TASK_KINDS = ("logic", "thinking", "intelligence", "plan", "science", "cognitive",
                  "represent", "repair", "experience", "audit")

    def __init__(self, manifest, state, *, repo=ROOT):
        self.repo = Path(repo).resolve()
        if self.repo != ROOT:
            raise ValueError("RUNTIME_AND_DATA_ROOT_MUST_MATCH; run the package in its own checkout")
        self.manifest_path = Path(manifest).resolve()
        self.manifest = json.loads(self.manifest_path.read_text())
        identity = dict(self.manifest)
        claimed = identity.pop("identity_digest")
        if sha(canonical(identity).encode()) != claimed:
            raise ValueError("SUCCESSOR_MANIFEST_DIGEST_MISMATCH")
        self.identity = claimed
        self._check_sources()
        archive_path = (self.manifest_path.parent / self.manifest["archive_file"]).resolve()
        if not archive_path.is_relative_to(self.manifest_path.parent):
            raise ValueError("ARCHIVE_OUTSIDE_BIRTH")
        for name in ("source_catalog", "rehearsal_goals"):
            if name in self.manifest:
                binding = self.manifest[name]
                artifact = (self.manifest_path.parent / binding["file"]).resolve()
                if not artifact.is_relative_to(self.manifest_path.parent) or file_sha(artifact) != binding["sha256"]:
                    raise ValueError("BIRTH_ARTIFACT_INTEGRITY:" + name)
        if file_sha(archive_path) != self.manifest["archive_sha256"]:
            raise ValueError("SUCCESSOR_ARCHIVE_DIGEST_MISMATCH")
        self.archive = ExperienceArchive(archive_path)
        from yado_unified_core_v1 import UnifiedYADOCoreV1
        self.parent = UnifiedYADOCoreV1(self.repo)
        self.parent_audit = self.parent.audit()
        if not self.parent_audit["pass"]:
            self.archive.close()
            raise ValueError("INHERITED_CORE_AUDIT_FAILED")
        state = Path(state).resolve()
        state.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(state, timeout=30, isolation_level=None)
        self.db.row_factory = sqlite3.Row
        self.db.executescript("""
        PRAGMA foreign_keys=ON;
        PRAGMA journal_mode=WAL;
        PRAGMA synchronous=FULL;
        CREATE TABLE IF NOT EXISTS identity(id INTEGER PRIMARY KEY CHECK(id=1), digest TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS events(tick INTEGER PRIMARY KEY, previous_hash TEXT NOT NULL,
            body TEXT NOT NULL, event_hash TEXT NOT NULL UNIQUE);
        CREATE TABLE IF NOT EXISTS jobs(id INTEGER PRIMARY KEY, goal TEXT NOT NULL, task TEXT NOT NULL,
            state TEXT NOT NULL DEFAULT 'PENDING', result_tick INTEGER REFERENCES events(tick));
        """)
        try:
            self.db.execute("BEGIN IMMEDIATE")
            self.db.execute("INSERT OR IGNORE INTO identity VALUES(1,?)", (self.identity,))
            if self.db.execute("SELECT digest FROM identity WHERE id=1").fetchone()[0] != self.identity:
                raise ValueError("STATE_BELONGS_TO_DIFFERENT_SUCCESSOR")
            self.verify_state()
            self.db.execute("COMMIT")
        except BaseException:
            self.db.execute("ROLLBACK")
            self.close()
            raise

    def _check_sources(self):
        changed = []
        pinned = self.manifest["inherited_files"] | self.manifest["assembly_sources"]
        for relative, expected in pinned.items():
            path = (self.repo / relative).resolve()
            if not path.is_relative_to(self.repo) or not path.is_file() or file_sha(path) != expected:
                changed.append(relative)
        if changed:
            raise ValueError("INHERITED_SOURCE_DRIFT:" + ",".join(changed[:8]))

    def close(self):
        self.db.close()
        self.archive.close()

    def verify_state(self):
        previous, tick = "0" * 64, 0
        submissions, completions, cognitive_records, graph_records = [], {}, [], []
        for row in self.db.execute("SELECT * FROM events ORDER BY tick"):
            tick += 1
            digest = sha((previous + "\n" + str(tick) + "\n" + row["body"]).encode())
            if row["tick"] != tick or row["previous_hash"] != previous or row["event_hash"] != digest:
                raise ValueError("CAUSAL_HISTORY_INTEGRITY_FAILURE")
            body = decode(row["body"])
            if str(body.get("kind", "")).startswith("COG_"):
                cognitive_records.append({**body, "tick": tick, "event_hash": digest})
            if str(body.get("kind", "")).startswith("GRAPH_"):
                graph_records.append({**body, "tick": tick, "event_hash": digest})
            if body.get("kind") == "GOAL_SUBMITTED":
                submissions.append(body)
            if body.get("job_id") is not None:
                if body["job_id"] in completions:
                    raise ValueError("DUPLICATE_JOB_COMPLETION")
                completions[body["job_id"]] = (tick, body)
            previous = digest
        registered = set()
        for submission in submissions:
            tasks = []
            for job_id in submission["job_ids"]:
                row = self.db.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
                if row is None or row["goal"] != submission["goal"] or job_id in registered:
                    raise ValueError("GOAL_QUEUE_INTEGRITY_FAILURE")
                registered.add(job_id)
                tasks.append(row["task"])
                completion = completions.get(job_id)
                if completion:
                    result_tick, body = completion
                    if (row["result_tick"] != result_tick or row["state"] != body["status"]
                            or encode(body["task"]) != row["task"]):
                        raise ValueError("JOB_RESULT_INTEGRITY_FAILURE")
                elif row["state"] != "PENDING" or row["result_tick"] is not None:
                    raise ValueError("JOB_STATE_WITHOUT_RESULT")
            if sha(canonical(tasks).encode()) != submission["tasks_digest"]:
                raise ValueError("GOAL_TASK_CONTENT_INTEGRITY_FAILURE")
        if len(registered) != self.db.execute("SELECT count(*) FROM jobs").fetchone()[0]:
            raise ValueError("UNREGISTERED_QUEUE_JOB")
        if self.db.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise ValueError("STATE_SQLITE_INTEGRITY_FAILURE")
        if self.db.execute("PRAGMA foreign_key_check").fetchone() is not None:
            raise ValueError("STATE_REFERENCE_INTEGRITY_FAILURE")
        if cognitive_records:
            from .cognitive import replay
            replay(cognitive_records)
        if graph_records:
            from .graph import replay as replay_graph
            replay_graph(graph_records)
        return {"status": "PASS", "tick": tick, "event_hash": previous}

    def _append(self, body):
        last = self.db.execute("SELECT tick,event_hash FROM events ORDER BY tick DESC LIMIT 1").fetchone()
        tick, previous = (last["tick"] + 1, last["event_hash"]) if last else (1, "0" * 64)
        text = encode(body)
        digest = sha((previous + "\n" + str(tick) + "\n" + text).encode())
        self.db.execute("INSERT INTO events VALUES(?,?,?,?)", (tick, previous, text, digest))
        return {"tick": tick, "event_hash": digest, **body}

    def recent(self, limit=5):
        rows = self.db.execute("SELECT tick,event_hash,body FROM events ORDER BY tick DESC LIMIT ?",
                               (max(1, min(int(limit), 100)),))
        return [{"tick": r["tick"], "event_hash": r["event_hash"], **decode(r["body"])} for r in rows]

    def _last_attempt(self, signature):
        for row in self.db.execute("SELECT tick,body FROM events ORDER BY tick DESC"):
            body = decode(row["body"])
            if body.get("task_signature") == signature and body.get("execution_attempted"):
                return row["tick"], body
        return None

    def _dispatch(self, task):
        kind, p = task.get("kind"), task.get("payload", {})
        if kind == "logic":
            return self.parent.all_experience_logic(p["relation"], p["start"])
        if kind == "thinking":
            if len(p["events"]) > 10_000:
                raise ValueError("EVENT_BUDGET_EXCEEDED")
            return self.parent.all_experience_thinking(p["events"])
        if kind == "intelligence":
            return self.parent.all_experience_intelligence(p)
        if kind == "plan":
            return self.parent.plan_contingent(p["current_confidence"], p["target_confidence"],
                                               p["remaining_budget"], p["stages"], p.get("completed", ()))
        if kind == "science":
            if len(p["rows"]) > 10_000:
                raise ValueError("SCIENCE_ROW_BUDGET_EXCEEDED")
            return self.parent.analyze_science_data(p["rows"])
        if kind == "cognitive":
            return self.parent.cognitive_experience_decide(p["organ"], p.get("input", {}))
        if kind == "represent":
            return self.parent.represent_raw_task(p["text"])
        if kind == "repair":
            budget = min(max(int(p.get("max_candidates", 1000)), 1), 4000)
            examples = [(tuple(args), value) for args, value in p["train_examples"]]
            return self.parent.repair_program(p["source"], p["function_name"], examples, budget)
        if kind == "experience":
            return {"sources": self.archive.search(p["query"], p.get("limit", 6))}
        if kind == "audit":
            result = self.parent.audit()
            result["scope"] = "PARENT_REGISTERED_INVENTORY"
            result["archived_remote_branch_count"] = self.archive.summary["counts"]["remote_branches"]
            result["parent_registry_covers_archived_branch_count"] = (
                result["branch_count"] == result["archived_remote_branch_count"])
            return result
        return {"status": "WITHHOLD_UNSUPPORTED_TASK", "supported": list(self.TASK_KINDS)}

    def _execute_in_transaction(self, task, *, job_id=None, retry=False):
        task = copy.deepcopy(task)
        if not isinstance(task, dict) or not isinstance(task.get("payload", {}), dict):
            raise ValueError("TASK_AND_PAYLOAD_MUST_BE_OBJECTS")
        signature = sha((self.identity + fingerprint(task)).encode())
        previous = self._last_attempt(signature)
        history = self.archive.search(task.get("history_query") or task.get("kind", ""), 4)
        prior_failed = previous is not None and previous[1]["status"] in {"FAIL", "ERROR", "WITHHOLD"}
        body = {"task": task, "task_signature": signature, "job_id": job_id,
                "historical_sources": history, "execution_attempted": False,
                "prior_attempt_tick": previous[0] if previous else None,
                "automatic_canonical_promotion": False}
        body["historical_meta_advice"] = []
        for source in history:
            if source["reported_outcome"] == "UNKNOWN":
                continue
            try:
                artifact = json.loads(self.archive.read(source["digest"]))
                advice = self.parent.global_experience_meta_decide_evidence({
                    "outcome": "PASS" if source["reported_outcome"] == "PASS" else "WITHHOLD",
                    "next_required_capability": source["next_capability"] or None,
                    "source_class": "RECEIPT" if "receipts/" in source["path"] else "EXPERIENCE",
                    "artifact": artifact})
                body["historical_meta_advice"].append({"source_digest": source["digest"],
                                                       "advice": advice})
            except Exception as exc:
                body["historical_meta_advice"].append({"source_digest": source["digest"],
                                                       "uninterpreted": type(exc).__name__})
        if prior_failed and not retry:
            body.update(status="WITHHOLD", reason="UNCHANGED_FAILED_ATTEMPT",
                        next_action="REVISE_INPUT_OR_REQUEST_EXPLICIT_RETRY")
            return self._append(body)
        body["execution_attempted"] = True
        try:
            result = self._dispatch(task)
            body["result"] = result
            status = str(result.get("status", "")) if isinstance(result, dict) else ""
            if status.startswith(("WITHHOLD", "BLOCK", "REJECT")):
                body.update(status="WITHHOLD", verification="NOT_RUN")
            elif status.startswith(("FAIL", "ERROR")):
                body.update(status="FAIL", verification="NATIVE_FAILURE")
            elif "expect" in task:
                expected = task["expect"]
                value = result
                for key in expected.get("path", []):
                    value = value[key]
                passed = equivalent(value, expected["equals"])
                body.update(status="VERIFIED" if passed else "FAIL",
                            verification="EXPECTED_VALUE_MATCH" if passed else "EXPECTED_VALUE_MISMATCH")
            else:
                body.update(status="EXECUTED_UNVERIFIED", verification="NO_INDEPENDENT_EXPECTATION")
            encode(result)
        except Exception as exc:
            body.pop("result", None)
            body.update(status="ERROR", error_type=type(exc).__name__, error=str(exc),
                        verification="EXECUTION_ERROR")
        adverse = body["status"] in {"FAIL", "ERROR", "WITHHOLD"}
        body["next_action"] = "REVISE" if adverse else ("CONTINUE" if body["status"] == "VERIFIED" else "SEEK_EVIDENCE")
        evidence = {"outcome": "PASS" if body["status"] == "VERIFIED" else "WITHHOLD",
                    "source_class": "RECEIPT", "domain": str(task.get("kind", "")).upper(),
                    "next_required_capability": "REVISE_TASK" if adverse else (
                        None if body["status"] == "VERIFIED" else "VERIFY_TASK"),
                    "artifact": {"status": body["status"], "canonical_mutation": False}}
        try:
            body["inherited_meta_advice"] = self.parent.global_experience_meta_decide_evidence(evidence)
        except Exception as exc:
            body["inherited_meta_advice"] = {"decision": "WITHHOLD", "error": str(exc)}
        return self._append(body)

    def execute(self, task, *, retry=False):
        self._check_sources()
        self.db.execute("BEGIN IMMEDIATE")
        try:
            self.verify_state()
            event = self._execute_in_transaction(task, retry=retry)
            self.db.execute("COMMIT")
            return event
        except BaseException:
            self.db.execute("ROLLBACK")
            raise

    def submit(self, goal, tasks):
        tasks = list(tasks)
        if not tasks or len(tasks) > 1000:
            raise ValueError("GOAL_REQUIRES_1_TO_1000_TASKS")
        encoded = [encode(task) for task in tasks]
        self.db.execute("BEGIN IMMEDIATE")
        try:
            ids = [self.db.execute("INSERT INTO jobs(goal,task) VALUES(?,?)", (str(goal), task)).lastrowid for task in encoded]
            self._append({"kind": "GOAL_SUBMITTED", "goal": str(goal), "job_ids": ids,
                          "tasks_digest": sha(canonical(encoded).encode())})
            self.db.execute("COMMIT")
            return ids
        except BaseException:
            self.db.execute("ROLLBACK")
            raise

    def resume(self, max_steps=20):
        if not 1 <= int(max_steps) <= 1000:
            raise ValueError("STEP_BUDGET_OUT_OF_RANGE")
        outputs = []
        self._check_sources()
        for _ in range(int(max_steps)):
            self.db.execute("BEGIN IMMEDIATE")
            try:
                self.verify_state()
                row = self.db.execute("SELECT * FROM jobs WHERE state='PENDING' ORDER BY id LIMIT 1").fetchone()
                if row is None:
                    self.db.execute("COMMIT")
                    break
                event = self._execute_in_transaction(decode(row["task"]), job_id=row["id"])
                self.db.execute("UPDATE jobs SET state=?,result_tick=? WHERE id=?",
                                (event["status"], event["tick"], row["id"]))
                self.db.execute("COMMIT")
                outputs.append(event)
            except BaseException:
                self.db.execute("ROLLBACK")
                raise
        return outputs

    def snapshot(self):
        last = self.recent(1)
        return {"kernel_id": self.KERNEL_ID, "identity_digest": self.identity,
                "parent_generation": self.parent.head["generation_id"],
                "inherited_capabilities": len(self.parent.head["active_capabilities"]),
                "task_kinds": list(self.TASK_KINDS), "archive": self.archive.summary["counts"],
                "state_integrity": self.verify_state(),
                "jobs": dict(self.db.execute("SELECT state,count(*) FROM jobs GROUP BY state")),
                "last_result": {k: last[0].get(k) for k in ("tick", "status", "next_action")} if last else None,
                "consciousness_established": False, "g3_genesis_performed": False}

    def open_goal(self, spec, *, budget=6, mode="full"):
        from .cognitive import CognitiveLoop
        return CognitiveLoop(self).open_goal(spec, budget, mode)

    def think(self, max_steps=20):
        from .cognitive import CognitiveLoop
        return CognitiveLoop(self).run(max_steps)

    def cognitive_snapshot(self):
        from .cognitive import CognitiveLoop
        return CognitiveLoop(self).snapshot()

    def stop_goal(self, goal_id):
        from .cognitive import CognitiveLoop
        return CognitiveLoop(self).stop(goal_id)
