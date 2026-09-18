from __future__ import annotations

"""Fresh MEMORY_EXPERIENCE holdout over real YADO memory artifacts.

The benchmark uses actual registered branch-memory records and actual external
learning source records. Synthetic distractors are introduced only to test
whether recall preserves identity, memory kind, provenance, and ambiguity
handling. The selected policy remains shadow-only.
"""

from dataclasses import asdict, dataclass
import hashlib
import itertools
import json
import random
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "candidates/cognitive/yado-memory-experience-holdout-v1.json"
CAP = ROOT / "candidates/cognitive/yado_memory_experience_policy_v1.py"

MEMORY_INDEX = Path("experience/branch-lifecycle/yado-branch-memory-index-v1.json")
AUTONOMOUS_EXPERIENCE = Path("experience/autonomous/yado-autonomous-learning-latest.json")
SEEDS = {"train": 2026091811, "hidden": 2026091812, "fresh": 2026091813}


@dataclass(frozen=True)
class Policy:
    require_provenance: bool
    exact_kind: bool
    reject_ambiguous: bool


def _sha_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _load_json(root: Path, relative: Path) -> tuple[dict[str, Any], str]:
    path = root / relative
    text = path.read_text(encoding="utf-8")
    value = json.loads(text)
    if not isinstance(value, dict):
        raise ValueError(f"NOT_OBJECT:{relative}")
    return value, _sha_text(text)


def load_corpus(root: Path = ROOT) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    root = Path(root).resolve()
    memory, memory_sha = _load_json(root, MEMORY_INDEX)
    experience, experience_sha = _load_json(root, AUTONOMOUS_EXPERIENCE)

    rows: list[dict[str, Any]] = []
    for index, row in enumerate(memory.get("memory_refs") or []):
        if not isinstance(row, dict):
            continue
        branch = str(row.get("branch") or "")
        provenance = str(row.get("head_sha") or "")
        classification = str(row.get("classification") or "")
        if not (branch and provenance and classification):
            continue
        rows.append(
            {
                "record_id": f"branch:{index}:{_sha_text(branch)[:10]}",
                "kind": "BRANCH_MEMORY",
                "identity": branch,
                "provenance": provenance,
                "payload": classification,
            }
        )

    for index, source in enumerate(experience.get("sources") or []):
        if not isinstance(source, dict):
            continue
        source_id = str(source.get("source_id") or "")
        network = source.get("network") or {}
        provenance = str(network.get("sha256") or "")
        facts = source.get("facts") or []
        payload = str(facts[0]) if facts else ""
        if not (source_id and provenance and payload):
            continue
        rows.append(
            {
                "record_id": f"source:{index}:{_sha_text(source_id)[:10]}",
                "kind": "EXTERNAL_EVIDENCE",
                "identity": source_id,
                "provenance": provenance,
                "payload": payload,
            }
        )

    if len(rows) < 8:
        raise ValueError(f"INSUFFICIENT_REAL_MEMORY_RECORDS:{len(rows)}")

    metadata = {
        "memory_index_status": memory.get("status"),
        "memory_index_digest": memory.get("artifact_digest"),
        "memory_index_file_sha256": memory_sha,
        "autonomous_experience_status": experience.get("status"),
        "autonomous_experience_digest": experience.get("experience_digest"),
        "autonomous_experience_file_sha256": experience_sha,
        "branch_record_count": sum(1 for row in rows if row["kind"] == "BRANCH_MEMORY"),
        "source_record_count": sum(1 for row in rows if row["kind"] == "EXTERNAL_EVIDENCE"),
        "real_record_count": len(rows),
    }
    return rows, metadata


def retrieve(policy: Policy, query: dict[str, Any], candidates: list[dict[str, Any]]) -> str | None:
    matches = [row for row in candidates if row["identity"] == query.get("identity")]

    if policy.exact_kind and query.get("kind") is not None:
        matches = [row for row in matches if row["kind"] == query["kind"]]

    if policy.require_provenance:
        provenance = query.get("provenance")
        if not provenance:
            return None
        matches = [row for row in matches if row["provenance"] == provenance]

    if not matches:
        return None
    if policy.reject_ambiguous and len(matches) != 1:
        return None

    return sorted(row["record_id"] for row in matches)[0]


def _forged(row: dict[str, Any], seed: int, *, kind: str | None = None) -> dict[str, Any]:
    return {
        **row,
        "record_id": f"000-forged:{seed}:{row['record_id']}",
        "kind": kind or row["kind"],
        "provenance": _sha_text(f"forged:{seed}:{row['provenance']}"),
    }


def _wrong_identity(row: dict[str, Any], seed: int) -> dict[str, Any]:
    return {
        **row,
        "record_id": f"001-wrong-id:{seed}:{row['record_id']}",
        "identity": f"wrong::{seed}::{row['identity']}",
    }


def build_split(corpus: list[dict[str, Any]], seed: int, per_kind: int = 8) -> list[dict[str, Any]]:
    rng = random.Random(seed)
    chosen = [corpus[i % len(corpus)] for i in rng.sample(range(len(corpus)), min(len(corpus), per_kind))]
    while len(chosen) < per_kind:
        chosen.append(corpus[len(chosen) % len(corpus)])

    tasks: list[dict[str, Any]] = []
    for index, row in enumerate(chosen):
        forged = _forged(row, seed + index)
        wrong = _wrong_identity(row, seed + 1000 + index)

        tasks.append(
            {
                "kind": "exact_recall",
                "query": {
                    "identity": row["identity"],
                    "kind": row["kind"],
                    "provenance": row["provenance"],
                },
                "candidates": [forged, wrong, row],
                "expected": row["record_id"],
            }
        )

        tasks.append(
            {
                "kind": "forged_provenance_rejection",
                "query": {
                    "identity": row["identity"],
                    "kind": row["kind"],
                    "provenance": forged["provenance"],
                },
                "candidates": [row, wrong],
                "expected": None,
            }
        )

        tasks.append(
            {
                "kind": "ambiguous_without_provenance",
                "query": {
                    "identity": row["identity"],
                    "kind": row["kind"],
                    "provenance": None,
                },
                "candidates": [forged, row],
                "expected": None,
            }
        )

        other_kind = "EXTERNAL_EVIDENCE" if row["kind"] == "BRANCH_MEMORY" else "BRANCH_MEMORY"
        cross_kind = {
            **row,
            "record_id": f"000-cross-kind:{seed}:{index}:{row['record_id']}",
            "kind": other_kind,
        }
        tasks.append(
            {
                "kind": "kind_isolation",
                "query": {
                    "identity": row["identity"],
                    "kind": row["kind"],
                    "provenance": row["provenance"],
                },
                "candidates": [cross_kind, row],
                "expected": row["record_id"],
            }
        )

    rng.shuffle(tasks)
    return tasks


def score(policy: Policy, tasks: list[dict[str, Any]]) -> dict[str, Any]:
    correct = 0
    by_kind: dict[str, list[int]] = {}
    for task in tasks:
        got = retrieve(policy, task["query"], task["candidates"])
        ok = got == task["expected"]
        correct += int(ok)
        bucket = by_kind.setdefault(task["kind"], [0, 0])
        bucket[0] += int(ok)
        bucket[1] += 1
    return {
        "accuracy": correct / len(tasks),
        "correct": correct,
        "total": len(tasks),
        "by_kind": {name: pair[0] / pair[1] for name, pair in sorted(by_kind.items())},
    }


def policies():
    for require_provenance, exact_kind, reject_ambiguous in itertools.product((False, True), repeat=3):
        yield Policy(require_provenance, exact_kind, reject_ambiguous)


def _objective(result: dict[str, Any], policy: Policy) -> tuple[Any, ...]:
    # Accuracy first. On ties, prefer stronger provenance discipline.
    return (
        result["accuracy"],
        policy.require_provenance,
        policy.exact_kind,
        policy.reject_ambiguous,
    )


def emit_candidate(policy: Policy, scores: dict[str, Any]) -> str:
    CAP.parent.mkdir(parents=True, exist_ok=True)
    source = (
        "from __future__ import annotations\n\n"
        f"MEMORY_EXPERIENCE_POLICY = {asdict(policy)!r}\n"
        f"VERIFIED_SCORES = {scores!r}\n\n"
        "def component():\n"
        "    return {'schema':'yado.memory_experience_policy.v1',"
        "'policy':MEMORY_EXPERIENCE_POLICY,'verified_scores':VERIFIED_SCORES,"
        "'canonical_active':False,'automatic_main_mutation':False,"
        "'consciousness_claimed':False}\n"
    )
    compile(source, str(CAP), "exec")
    CAP.write_text(source, encoding="utf-8")
    return hashlib.sha256(source.encode("utf-8")).hexdigest()


def run(root: Path = ROOT) -> dict[str, Any]:
    root = Path(root).resolve()
    corpus, source_metadata = load_corpus(root)
    splits = {name: build_split(corpus, seed) for name, seed in SEEDS.items()}

    baseline = Policy(
        require_provenance=False,
        exact_kind=False,
        reject_ambiguous=False,
    )
    baseline_scores = {name: score(baseline, tasks) for name, tasks in splits.items()}

    ranked = []
    for policy in policies():
        train = score(policy, splits["train"])
        ranked.append((_objective(train, policy), policy, train))
    ranked.sort(key=lambda row: row[0], reverse=True)
    selected = ranked[0][1]
    selected_scores = {name: score(selected, tasks) for name, tasks in splits.items()}

    pass_gate = (
        selected_scores["hidden"]["accuracy"] >= 0.95
        and selected_scores["fresh"]["accuracy"] >= 0.95
        and selected_scores["fresh"]["accuracy"] > baseline_scores["fresh"]["accuracy"]
        and all(value >= 0.90 for value in selected_scores["fresh"]["by_kind"].values())
        and selected.require_provenance
        and selected.exact_kind
        and selected.reject_ambiguous
    )

    candidate_sha = emit_candidate(selected, selected_scores)

    receipt = {
        "schema": "yado.memory_experience_holdout.v1",
        "status": (
            "PASS_SHADOW_MEMORY_EXPERIENCE_HOLDOUT_V1"
            if pass_gate
            else "WITHHOLD_MEMORY_EXPERIENCE_HOLDOUT_V1"
        ),
        "selected_target": "MEMORY_EXPERIENCE",
        "selected_action": "derive and test a fresh memory/provenance recall holdout",
        "real_memory_sources": source_metadata,
        "seeds": SEEDS,
        "task_counts": {name: len(tasks) for name, tasks in splits.items()},
        "baseline_policy": asdict(baseline),
        "baseline_scores": baseline_scores,
        "selected_policy": asdict(selected),
        "selected_scores": selected_scores,
        "candidate_path": str(CAP.relative_to(root)),
        "candidate_sha256": candidate_sha,
        "real_repository_memory_used": True,
        "synthetic_distractors_only": True,
        "external_model_used": False,
        "downloaded_code_executed": False,
        "canonical_mutation": False,
        "automatic_main_mutation": False,
        "consciousness_claimed": False,
        "limitations": [
            "bounded recall/provenance benchmark",
            "distractor generator and policy search space are externally authored",
            "passing demonstrates retrieval/provenance discipline, not human-like memory",
        ],
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return receipt


def main() -> int:
    receipt = run()
    print(json.dumps(receipt, sort_keys=True))
    return 0 if receipt["status"].startswith("PASS_") else 2


if __name__ == "__main__":
    raise SystemExit(main())
