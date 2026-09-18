from __future__ import annotations

"""Bounded relational/causal LOGIC holdout selected by YADO's development controller.

The benchmark separates directed causal evidence from merely associative links,
adds distractors and feedback contradictions, and uses train/hidden/fresh splits.
The selected policy is shadow-only and cannot mutate canonical automatically.
"""

from dataclasses import asdict, dataclass
import hashlib
import itertools
import json
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "candidates/cognitive/yado-relational-causal-logic-holdout-v1.json"
CAP = ROOT / "candidates/cognitive/yado_relational_causal_logic_policy_v1.py"
SEEDS = {"train": 2026091801, "hidden": 2026091802, "fresh": 2026091803}


@dataclass(frozen=True)
class Policy:
    max_depth: int
    causal_only: bool
    reject_feedback_cycles: bool


def _reach(edges: list[tuple[str, str]], source: str, max_depth: int) -> set[str]:
    frontier = {source}
    seen = {source}
    reached: set[str] = set()
    for _ in range(max_depth):
        nxt: set[str] = set()
        for node in frontier:
            for a, b in edges:
                if a == node and b not in seen:
                    reached.add(b)
                    nxt.add(b)
                    seen.add(b)
        frontier = nxt
        if not frontier:
            break
    return reached


def infer(policy: Policy, task: dict) -> bool:
    typed = list(task["edges"])
    usable = [(a, b) for a, b, kind in typed if (kind == "CAUSE" or not policy.causal_only)]
    source, target = task["query"]
    forward = target in _reach(usable, source, policy.max_depth)
    if policy.reject_feedback_cycles and forward:
        reverse = source in _reach(usable, target, policy.max_depth)
        if reverse:
            return False
    return forward


def _positive_case(rng: random.Random, index: int) -> dict:
    depth = 2 + (index % 5)
    chain = [f"n{index}_{j}" for j in range(depth + 1)]
    edges = [(chain[j], chain[j + 1], "CAUSE") for j in range(depth)]
    # Association distractors should not create causal conclusions.
    for j in range(3):
        edges.append((chain[0], f"a{index}_{j}", "ASSOCIATION"))
    rng.shuffle(edges)
    return {"edges": edges, "query": (chain[0], chain[-1]), "expected": True, "kind": "causal_chain"}


def _association_only_case(rng: random.Random, index: int) -> dict:
    s, m, t = f"s{index}", f"m{index}", f"t{index}"
    edges = [(s, m, "ASSOCIATION"), (m, t, "ASSOCIATION")]
    edges += [(s, f"d{index}_{j}", "CAUSE") for j in range(2)]
    rng.shuffle(edges)
    return {"edges": edges, "query": (s, t), "expected": False, "kind": "association_not_cause"}


def _feedback_case(rng: random.Random, index: int) -> dict:
    s, m, t = f"fs{index}", f"fm{index}", f"ft{index}"
    edges = [(s, m, "CAUSE"), (m, t, "CAUSE"), (t, s, "CAUSE")]
    edges.append((s, f"fa{index}", "ASSOCIATION"))
    rng.shuffle(edges)
    return {"edges": edges, "query": (s, t), "expected": False, "kind": "feedback_contradiction"}


def _negative_direction_case(rng: random.Random, index: int) -> dict:
    s, m, t = f"rs{index}", f"rm{index}", f"rt{index}"
    edges = [(t, m, "CAUSE"), (m, s, "CAUSE"), (s, t, "ASSOCIATION")]
    rng.shuffle(edges)
    return {"edges": edges, "query": (s, t), "expected": False, "kind": "wrong_direction"}


def build_split(seed: int, count_each: int = 10) -> list[dict]:
    rng = random.Random(seed)
    rows: list[dict] = []
    builders = (_positive_case, _association_only_case, _feedback_case, _negative_direction_case)
    for builder in builders:
        for i in range(count_each):
            rows.append(builder(rng, i + 100 * builders.index(builder)))
    rng.shuffle(rows)
    return rows


def score(policy: Policy, tasks: list[dict]) -> dict:
    correct = 0
    by_kind: dict[str, list[int]] = {}
    for row in tasks:
        ok = infer(policy, row) == row["expected"]
        correct += int(ok)
        bucket = by_kind.setdefault(row["kind"], [0, 0])
        bucket[0] += int(ok)
        bucket[1] += 1
    return {
        "accuracy": correct / len(tasks),
        "correct": correct,
        "total": len(tasks),
        "by_kind": {k: v[0] / v[1] for k, v in sorted(by_kind.items())},
    }


def policies():
    for depth, causal_only, reject_cycles in itertools.product(range(1, 9), (False, True), (False, True)):
        yield Policy(depth, causal_only, reject_cycles)


def _objective(result: dict, policy: Policy) -> tuple:
    # Accuracy first, then prefer shallower policies when equally correct.
    return (result["accuracy"], -policy.max_depth, policy.causal_only, policy.reject_feedback_cycles)


def emit_candidate(policy: Policy, scores: dict) -> str:
    CAP.parent.mkdir(parents=True, exist_ok=True)
    source = (
        "from __future__ import annotations\n\n"
        f"RELATIONAL_CAUSAL_LOGIC_POLICY = {asdict(policy)!r}\n"
        f"VERIFIED_SCORES = {scores!r}\n\n"
        "def component():\n"
        "    return {'schema':'yado.relational_causal_logic_policy.v1',"
        "'policy':RELATIONAL_CAUSAL_LOGIC_POLICY,'verified_scores':VERIFIED_SCORES,"
        "'canonical_active':False,'automatic_main_mutation':False,"
        "'consciousness_claimed':False}\n"
    )
    compile(source, str(CAP), "exec")
    CAP.write_text(source, encoding="utf-8")
    return hashlib.sha256(source.encode("utf-8")).hexdigest()


def run() -> dict:
    splits = {name: build_split(seed) for name, seed in SEEDS.items()}
    baseline = Policy(max_depth=1, causal_only=False, reject_feedback_cycles=False)
    baseline_scores = {name: score(baseline, rows) for name, rows in splits.items()}

    ranked = []
    for policy in policies():
        train = score(policy, splits["train"])
        ranked.append((_objective(train, policy), policy, train))
    ranked.sort(key=lambda row: row[0], reverse=True)
    selected = ranked[0][1]
    selected_scores = {name: score(selected, rows) for name, rows in splits.items()}

    pass_gate = (
        selected_scores["hidden"]["accuracy"] >= 0.95
        and selected_scores["fresh"]["accuracy"] >= 0.95
        and selected_scores["fresh"]["accuracy"] > baseline_scores["fresh"]["accuracy"]
        and all(v >= 0.90 for v in selected_scores["fresh"]["by_kind"].values())
    )
    candidate_sha = emit_candidate(selected, selected_scores)

    receipt = {
        "schema": "yado.relational_causal_logic_holdout.v1",
        "status": "PASS_SHADOW_RELATIONAL_CAUSAL_LOGIC_HOLDOUT_V1" if pass_gate else "WITHHOLD_RELATIONAL_CAUSAL_LOGIC_HOLDOUT_V1",
        "selected_target": "LOGIC",
        "selected_action": "derive and test a new relational/causal logic holdout",
        "seeds": SEEDS,
        "task_counts": {name: len(rows) for name, rows in splits.items()},
        "baseline_policy": asdict(baseline),
        "baseline_scores": baseline_scores,
        "selected_policy": asdict(selected),
        "selected_scores": selected_scores,
        "candidate_path": str(CAP.relative_to(ROOT)),
        "candidate_sha256": candidate_sha,
        "external_model_used": False,
        "downloaded_code_executed": False,
        "canonical_mutation": False,
        "automatic_main_mutation": False,
        "consciousness_claimed": False,
        "limitations": [
            "synthetic bounded relational/causal tasks",
            "task generator and policy search space are externally authored",
            "passing demonstrates functional holdout improvement, not general intelligence",
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
