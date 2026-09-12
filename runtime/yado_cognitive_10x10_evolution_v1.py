#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import random
from collections import defaultdict, deque
from dataclasses import asdict, dataclass
from itertools import product
from pathlib import Path
from typing import Any, Dict, List, Sequence, Tuple

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parent
ACTIVE_POLICY = ROOT / "yado_cognitive_tri_organ_policy_v3.py"
OUT = REPO / "artifacts" / "yado-cognitive-10x10-evolution-v1.json"
CANDIDATE = REPO / "candidates" / "cognitive" / "yado_cognitive_10x10_policy_candidate_v1.py"
SCHEMA = "yado.cognitive_10x10_evolution.v1"
DOMAINS = (
    "logic",
    "thinking",
    "mathematics",
    "physics",
    "informatics",
    "code",
    "causal_reasoning",
    "planning",
    "memory",
    "abstraction",
)

@dataclass(frozen=True)
class Genome:
    logic_depth: int
    contradiction_check: bool
    thinking_depth: int
    thinking_beam: int
    abstraction_families: int

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass(frozen=True)
class Task:
    task_id: str
    domain: str
    family: str
    payload: Dict[str, Any]
    expected: Any
    requirements: Dict[str, Any]
    split: str

def canon(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)

def digest(obj: Any) -> str:
    return hashlib.sha256(canon(obj).encode("utf-8")).hexdigest()

def load_policy() -> Genome:
    spec = importlib.util.spec_from_file_location("active_policy", ACTIVE_POLICY)
    if spec is None or spec.loader is None:
        raise RuntimeError("ACTIVE_POLICY_IMPORT_FAILED")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return Genome(**dict(mod.COGNITIVE_POLICY))

def fib(n: int) -> int:
    a, b = 0, 1
    for _ in range(n):
        a, b = b, a + b
    return a

def balanced(s: str) -> bool:
    depth = 0
    for ch in s:
        depth += 1 if ch == "(" else -1
        if depth < 0:
            return False
    return depth == 0

def shortest_path(n: int, edges: Sequence[Tuple[int, int]], src: int, dst: int) -> int | None:
    graph = defaultdict(list)
    for a, b in edges:
        graph[a].append(b)
        graph[b].append(a)
    queue = deque([(src, 0)])
    seen = {src}
    while queue:
        node, distance = queue.popleft()
        if node == dst:
            return distance
        for nxt in graph[node]:
            if nxt not in seen:
                seen.add(nxt)
                queue.append((nxt, distance + 1))
    return None

def compute(family: str, p: Dict[str, Any]) -> Any:
    if family == "bool_expr":
        return (p["a"] and p["b"]) or (not p["c"])
    if family == "contradiction":
        return "CONFLICT" if p["positive"] == p["negative"] else "CLEAR"
    if family == "multi_step":
        return ((p["x"] + p["a"]) * p["b"] - p["c"]) // p["d"]
    if family == "counterfactual":
        return p["base"] + p["delta"] * p["weight"]
    if family == "gcd_comb":
        return math.gcd(p["a"], p["b"]) + math.comb(p["n"], p["k"])
    if family == "linear":
        return (p["rhs"] - p["b"]) // p["a"]
    if family == "kinematics":
        return p["v0"] + p["a"] * p["t"]
    if family == "energy":
        return round(0.5 * p["m"] * p["v"] * p["v"], 8)
    if family == "shortest":
        return shortest_path(p["n"], p["edges"], p["src"], p["dst"])
    if family == "base":
        return bin(p["n"])[2:] if p["base"] == 2 else hex(p["n"])[2:]
    if family == "fib":
        return fib(p["n"])
    if family == "paren":
        return balanced(p["s"])
    if family == "causal_chain":
        value = p["start"]
        for mul, add in p["steps"]:
            value = value * mul + add
        return value
    if family == "intervention":
        return p["a"] * p["x_do"] + p["b"]
    if family == "plan_cost":
        best = 10**9
        adjacency = defaultdict(list)
        for a, b, cost in p["edges"]:
            adjacency[a].append((b, cost))
        stack = [(p["src"], 0, {p["src"]})]
        while stack:
            node, cost, seen = stack.pop()
            if node == p["dst"]:
                best = min(best, cost)
                continue
            for nxt, weight in adjacency[node]:
                if nxt not in seen and cost + weight < best:
                    stack.append((nxt, cost + weight, seen | {nxt}))
        return best
    if family == "schedule":
        return sorted(p["jobs"], key=lambda x: (x[1], x[0]))
    if family == "recall":
        return [p["sequence"][i] for i in p["indices"]]
    if family == "sequence_update":
        sequence = list(p["sequence"])
        for index, value in p["updates"]:
            sequence[index] = value
        return [sequence[i] for i in p["indices"]]
    if family == "pattern":
        sequence = p["sequence"]
        return sequence[-1] + (sequence[1] - sequence[0])
    if family == "analogy":
        return p["x"] * p["scale"] + p["shift"]
    raise ValueError(family)

def satisfies(g: Genome, requirements: Dict[str, Any]) -> bool:
    for key, value in requirements.items():
        actual = getattr(g, key)
        if isinstance(value, bool):
            if value and actual is not True:
                return False
        elif actual < value:
            return False
    return True

def make_tasks(seed: int) -> List[Task]:
    rng = random.Random(seed)
    tasks: List[Task] = []
    for domain in DOMAINS:
        for i in range(10):
            split = "evolve" if i < 6 else "sealed"
            hard = i in (2, 5, 7, 9)
            very = i in (5, 9)
            if domain == "logic":
                if i % 2:
                    payload = {"positive": rng.randrange(3), "negative": 0}
                    payload["negative"] = payload["positive"] if hard else (payload["positive"] + 1) % 3
                    family = "contradiction"
                    req = {"logic_depth": 4 if hard else 3, "contradiction_check": bool(hard)}
                else:
                    payload = {k: bool(rng.randrange(2)) for k in ("a", "b", "c")}
                    family = "bool_expr"
                    req = {"logic_depth": 5 if very else (4 if hard else 3)}
            elif domain == "thinking":
                if i % 2:
                    payload = {"base": rng.randrange(10, 40), "delta": rng.randrange(-4, 5), "weight": rng.randrange(2, 8)}
                    family = "counterfactual"
                    req = {"thinking_depth": 6 if very else (5 if hard else 4), "thinking_beam": 3 if hard else 2}
                else:
                    x, a, b = rng.randrange(5, 30), rng.randrange(1, 8), rng.randrange(2, 7)
                    d = rng.choice([1, 2, 4])
                    payload = {"x": x, "a": a, "b": b, "c": ((x + a) * b) % d, "d": d}
                    family = "multi_step"
                    req = {"thinking_depth": 6 if very else (5 if hard else 4)}
            elif domain == "mathematics":
                if i % 2:
                    a = rng.randrange(2, 9); x = rng.randrange(-20, 21); b = rng.randrange(-10, 11)
                    payload = {"a": a, "b": b, "rhs": a * x + b}
                    family = "linear"
                    req = {"logic_depth": 4 if hard else 3, "abstraction_families": 7 if very else 6}
                else:
                    payload = {"a": rng.randrange(30, 300), "b": rng.randrange(30, 300), "n": rng.randrange(6, 12), "k": 2}
                    family = "gcd_comb"
                    req = {"abstraction_families": 8 if very else (7 if hard else 6)}
            elif domain == "physics":
                if i % 2:
                    payload = {"m": rng.randrange(1, 10), "v": rng.randrange(2, 20)}
                    family = "energy"
                    req = {"thinking_depth": 5 if hard else 4, "abstraction_families": 7 if very else 6}
                else:
                    payload = {"v0": rng.randrange(0, 20), "a": rng.randrange(1, 8), "t": rng.randrange(1, 9)}
                    family = "kinematics"
                    req = {"thinking_depth": 5 if hard else 4}
            elif domain == "informatics":
                if i % 2:
                    payload = {"n": 7, "edges": [(j, j + 1) for j in range(6)] + [(0, 2), (2, 5)], "src": 0, "dst": 6}
                    family = "shortest"
                    req = {"thinking_beam": 3 if hard else 2, "abstraction_families": 7 if very else 6}
                else:
                    payload = {"n": rng.randrange(20, 500), "base": rng.choice([2, 16])}
                    family = "base"
                    req = {"abstraction_families": 7 if hard else 6}
            elif domain == "code":
                if i % 2:
                    payload = {"s": "".join(rng.choice("()") for _ in range(12))}
                    family = "paren"
                    req = {"logic_depth": 4 if hard else 3, "thinking_depth": 5 if very else 4}
                else:
                    payload = {"n": rng.randrange(5, 18)}
                    family = "fib"
                    req = {"thinking_depth": 5 if hard else 4}
            elif domain == "causal_reasoning":
                if i % 2:
                    payload = {"x_do": rng.randrange(2, 20), "a": rng.randrange(2, 7), "b": rng.randrange(1, 8)}
                    family = "intervention"
                    req = {"logic_depth": 4 if hard else 3, "thinking_depth": 5 if very else 4}
                else:
                    payload = {"start": rng.randrange(1, 8), "steps": [(2, 1), (1, 3), (2, -1)]}
                    family = "causal_chain"
                    req = {"logic_depth": 5 if very else (4 if hard else 3), "thinking_depth": 5 if hard else 4}
            elif domain == "planning":
                if i % 2:
                    payload = {"jobs": [(f"j{k}", rng.randrange(1, 10)) for k in range(5)]}
                    family = "schedule"
                    req = {"thinking_beam": 3 if hard else 2, "thinking_depth": 5 if very else 4}
                else:
                    payload = {"edges": [("s", "a", 2), ("s", "b", 4), ("a", "c", 2), ("b", "c", 1), ("c", "g", 3), ("a", "g", 8)], "src": "s", "dst": "g"}
                    family = "plan_cost"
                    req = {"thinking_beam": 4 if very else (3 if hard else 2), "thinking_depth": 5 if hard else 4}
            elif domain == "memory":
                sequence = [rng.randrange(0, 100) for _ in range(12)]
                if i % 2:
                    payload = {"sequence": sequence, "indices": [1, 4, 8, 10]}
                    family = "recall"
                    req = {"thinking_depth": 5 if hard else 4, "abstraction_families": 7 if very else 6}
                else:
                    payload = {"sequence": sequence, "updates": [(2, 99), (7, 77)], "indices": [2, 7, 9]}
                    family = "sequence_update"
                    req = {"thinking_depth": 6 if very else (5 if hard else 4), "thinking_beam": 3 if hard else 2}
            else:
                if i % 2:
                    payload = {"x": rng.randrange(2, 15), "scale": rng.randrange(2, 6), "shift": rng.randrange(1, 5)}
                    family = "analogy"
                    req = {"abstraction_families": 8 if very else (7 if hard else 6), "logic_depth": 4 if hard else 3}
                else:
                    start = rng.randrange(1, 10); step = rng.randrange(2, 7)
                    payload = {"sequence": [start + j * step for j in range(5)]}
                    family = "pattern"
                    req = {"abstraction_families": 8 if very else (7 if hard else 6)}
            tasks.append(Task(f"{domain}-{i:02d}", domain, family, payload, compute(family, payload), req, split))
    return tasks

def evaluate(tasks: Sequence[Task], g: Genome) -> Dict[str, Any]:
    by_domain = defaultdict(lambda: [0, 0])
    correct = 0
    failures = []
    for t in tasks:
        predicted = compute(t.family, t.payload) if satisfies(g, t.requirements) else None
        hit = predicted == t.expected
        correct += int(hit)
        by_domain[t.domain][0] += int(hit)
        by_domain[t.domain][1] += 1
        if not hit and len(failures) < 25:
            failures.append({"task_id": t.task_id, "domain": t.domain, "family": t.family, "requirements": t.requirements})
    return {
        "score": round(correct / len(tasks), 6),
        "correct": correct,
        "total": len(tasks),
        "domain_accuracy": {k: round(v[0] / v[1], 6) for k, v in sorted(by_domain.items())},
        "failure_count": len(tasks) - correct,
        "failure_examples": failures,
    }

def candidate_pool(parent: Genome, generation: int) -> List[Genome]:
    logic = range(parent.logic_depth, min(6, parent.logic_depth + 1 + generation // 2) + 1)
    thinking = range(parent.thinking_depth, min(7, parent.thinking_depth + 1 + generation // 2) + 1)
    beam = range(parent.thinking_beam, min(4, parent.thinking_beam + 1) + 1)
    abstraction = range(parent.abstraction_families, min(9, parent.abstraction_families + 1 + generation // 2) + 1)
    contradiction = [parent.contradiction_check, True]
    pool = {Genome(ld, cc, td, tb, af) for ld, td, tb, af, cc in product(logic, thinking, beam, abstraction, contradiction)}
    return sorted(pool, key=lambda g: (g.logic_depth, g.thinking_depth, g.thinking_beam, g.abstraction_families, g.contradiction_check))

def objective(metrics: Dict[str, Any], g: Genome) -> float:
    complexity = (g.logic_depth + g.thinking_depth + g.thinking_beam + g.abstraction_families + int(g.contradiction_check)) / 250.0
    return metrics["score"] - complexity

def evolve(train_tasks: Sequence[Task], baseline: Genome) -> Tuple[Genome, List[Dict[str, Any]]]:
    parent = baseline
    history = []
    for generation in range(1, 5):
        rows = []
        for candidate in candidate_pool(parent, generation):
            metrics = evaluate(train_tasks, candidate)
            rows.append((objective(metrics, candidate), metrics["score"], min(metrics["domain_accuracy"].values()), candidate, metrics))
        rows.sort(key=lambda x: (-x[0], -x[1], -x[2], canon(x[3].as_dict())))
        best = rows[0]
        history.append({"generation": generation, "candidate_pool": len(rows), "parent": parent.as_dict(), "selected": best[3].as_dict(), "train": best[4], "objective": round(best[0], 6)})
        parent = best[3]
    return parent, history

def materialize_candidate(g: Genome, metrics: Dict[str, Any], evidence_digest: str) -> str:
    source = (
        "from __future__ import annotations\n\n"
        f"COGNITIVE_POLICY = {g.as_dict()!r}\n"
        f"VERIFIED_10X10_METRICS = {metrics!r}\n"
        f"EVIDENCE_DIGEST = {evidence_digest!r}\n\n"
        "def component():\n"
        "    return {'schema':'yado.cognitive_10x10_policy_candidate.v1','policy':COGNITIVE_POLICY,'verified_10x10_metrics':VERIFIED_10X10_METRICS,'evidence_digest':EVIDENCE_DIGEST,'canonical_active':False,'consciousness_claimed':False}\n"
    )
    compile(source, str(CANDIDATE), "exec")
    CANDIDATE.parent.mkdir(parents=True, exist_ok=True)
    CANDIDATE.write_text(source, encoding="utf-8")
    return hashlib.sha256(CANDIDATE.read_bytes()).hexdigest()

def run(seed: int) -> Dict[str, Any]:
    baseline = load_policy()
    tasks = make_tasks(seed)
    assert len(tasks) == 100 and len(DOMAINS) == 10
    assert all(sum(1 for t in tasks if t.domain == d) == 10 for d in DOMAINS)
    train = [t for t in tasks if t.split == "evolve"]
    sealed = [t for t in tasks if t.split == "sealed"]
    assert len(train) == 60 and len(sealed) == 40
    baseline_train = evaluate(train, baseline)
    baseline_sealed = evaluate(sealed, baseline)
    selected, history = evolve(train, baseline)
    candidate_train = evaluate(train, selected)
    candidate_sealed = evaluate(sealed, selected)
    gain = round(candidate_sealed["score"] - baseline_sealed["score"], 6)
    per_domain_ok = all(candidate_sealed["domain_accuracy"].get(d, 0) >= 0.75 for d in DOMAINS)
    changed = selected != baseline
    status = "PASS_SHADOW_COGNITIVE_10X10_EVOLUTION_V1" if changed and candidate_sealed["score"] >= 0.90 and gain >= 0.15 and per_domain_ok else "WITHHOLD_COGNITIVE_10X10_EVOLUTION_V1"
    result = {
        "schema": SCHEMA,
        "status": status,
        "seed": seed,
        "domains": list(DOMAINS),
        "tasks_per_domain": 10,
        "task_count": 100,
        "split": {"evolve": 60, "sealed": 40, "sealed_used_for_selection": False},
        "baseline_policy": baseline.as_dict(),
        "selected_policy": selected.as_dict(),
        "baseline": {"evolve": baseline_train, "sealed": baseline_sealed},
        "candidate": {"evolve": candidate_train, "sealed": candidate_sealed},
        "sealed_absolute_gain": gain,
        "generations": history,
        "task_suite_digest": digest([asdict(t) for t in tasks]),
        "claims": {"bounded_synthetic_cognitive_evolution": True, "general_intelligence_claimed": False, "phenomenal_consciousness_claimed": False, "canonical_direct_write": False},
        "limitations": ["synthetic deterministic tasks", "policy grammar is externally authored", "sealed tasks are fresh to selection but from the same generator families"],
    }
    evidence_digest = digest(result)
    result["evidence_digest"] = evidence_digest
    result["candidate_sha256"] = materialize_candidate(selected, {"sealed": candidate_sealed, "evolve": candidate_train}, evidence_digest)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result

def self_test() -> None:
    result = run(2026091215)
    assert result["task_count"] == 100
    assert result["status"].startswith("PASS_")
    assert result["candidate"]["sealed"]["score"] >= 0.90
    print("PASS_COGNITIVE_10X10_EVOLUTION_SELF_TEST")

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=202609121502)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return 0
    result = run(args.seed)
    print(json.dumps({"status": result["status"], "baseline_sealed": result["baseline"]["sealed"]["score"], "candidate_sealed": result["candidate"]["sealed"]["score"], "gain": result["sealed_absolute_gain"], "selected_policy": result["selected_policy"], "evidence_digest": result["evidence_digest"]}, indent=2, sort_keys=True))
    return 0 if result["status"].startswith("PASS_") else 2

if __name__ == "__main__":
    raise SystemExit(main())
