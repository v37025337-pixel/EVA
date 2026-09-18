from __future__ import annotations

"""Fresh cross-cognitive integration holdout over four verified YADO layers.

The benchmark composes the already-verified shadow mechanisms for:
- MEMORY_EXPERIENCE: provenance-aware retrieval over real repository memory,
- LOGIC: relational/causal inference,
- THINKING: contextual stream routing,
- INTELLIGENCE: G4 capability transfer with ambiguity withholding.

The integration policy is selected on train, then evaluated on hidden/fresh
splits. Every single-layer ablation must cause a material fresh drop.
"""

from dataclasses import dataclass
import hashlib
import json
import random
from pathlib import Path
from typing import Any

from yado_relational_causal_logic_holdout_v1 import (
    Policy as LogicPolicy,
    infer as logic_infer,
)
from yado_memory_experience_holdout_v1 import (
    Policy as MemoryPolicy,
    load_corpus,
    retrieve,
)
from yado_g2_contextual_stream_capability_adapter_v1 import (
    CAP_BUD,
    CAP_CONJ,
    CAP_REL,
    CAP_RES,
    ContextualStreamCapabilityAdapterV1,
)
from yado_intelligence_transfer_holdout_v1 import (
    Task as IntelligenceTask,
    build_g3,
    execute as intelligence_execute,
)
from yado_external_project_training_v1 import STATUS_PASS
from yado_external_project_transfer_v3 import STATUS_AMBIGUOUS

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "candidates/cognitive/yado-cognitive-integration-holdout-v1.json"
CAP = ROOT / "candidates/cognitive/yado_cognitive_integration_policy_v1.py"

SEEDS = {"train": 2026091841, "hidden": 2026091842, "fresh": 2026091843}
GATES = ("MEMORY_EXPERIENCE", "LOGIC", "THINKING", "INTELLIGENCE")

LOGIC_RECEIPT = ROOT / "candidates/cognitive/yado-relational-causal-logic-holdout-v1.json"
MEMORY_RECEIPT = ROOT / "candidates/cognitive/yado-memory-experience-holdout-v1.json"
THINKING_RECEIPT = ROOT / "candidates/cognitive/yado-thinking-contextual-holdout-v1.json"
INTELLIGENCE_RECEIPT = ROOT / "candidates/cognitive/yado-intelligence-transfer-holdout-v1.json"


def _load_verified_receipt(path: Path, prefix: str) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("PARENT_RECEIPT_NOT_OBJECT:" + str(path))
    if not str(value.get("status", "")).startswith(prefix):
        raise RuntimeError("PARENT_RECEIPT_NOT_VERIFIED:" + str(path))
    return value


def verified_parent_policies(root: Path = ROOT) -> dict[str, Any]:
    root = Path(root).resolve()
    logic = _load_verified_receipt(
        root / LOGIC_RECEIPT.relative_to(ROOT),
        "PASS_SHADOW_RELATIONAL_CAUSAL_LOGIC_HOLDOUT",
    )
    memory = _load_verified_receipt(
        root / MEMORY_RECEIPT.relative_to(ROOT),
        "PASS_SHADOW_MEMORY_EXPERIENCE_HOLDOUT",
    )
    thinking = _load_verified_receipt(
        root / THINKING_RECEIPT.relative_to(ROOT),
        "PASS_SHADOW_THINKING_CONTEXTUAL_HOLDOUT",
    )
    intelligence = _load_verified_receipt(
        root / INTELLIGENCE_RECEIPT.relative_to(ROOT),
        "PASS_SHADOW_INTELLIGENCE_TRANSFER_HOLDOUT",
    )
    return {
        "logic": dict(logic["selected_policy"]),
        "memory": dict(memory["selected_policy"]),
        "thinking": str(thinking["selected_strategy"]),
        "intelligence": str(intelligence["selected_strategy"]),
        "receipt_sha256": {
            "logic": hashlib.sha256((root / LOGIC_RECEIPT.relative_to(ROOT)).read_bytes()).hexdigest(),
            "memory": hashlib.sha256((root / MEMORY_RECEIPT.relative_to(ROOT)).read_bytes()).hexdigest(),
            "thinking": hashlib.sha256((root / THINKING_RECEIPT.relative_to(ROOT)).read_bytes()).hexdigest(),
            "intelligence": hashlib.sha256((root / INTELLIGENCE_RECEIPT.relative_to(ROOT)).read_bytes()).hexdigest(),
        },
    }


VERIFIED_PARENT_POLICIES = verified_parent_policies(ROOT)
LOGIC_POLICY = VERIFIED_PARENT_POLICIES["logic"]
MEMORY_POLICY = VERIFIED_PARENT_POLICIES["memory"]
THINKING_STRATEGY = VERIFIED_PARENT_POLICIES["thinking"]
INTELLIGENCE_STRATEGY = VERIFIED_PARENT_POLICIES["intelligence"]


@dataclass(frozen=True)
class IntegrationPolicy:
    policy_id: str
    required_gates: tuple[str, ...]
    fixed_output: str | None = None


POLICIES = (
    IntegrationPolicy("ALL_FOUR", GATES),
    IntegrationPolicy("NO_MEMORY", ("LOGIC", "THINKING", "INTELLIGENCE")),
    IntegrationPolicy("NO_LOGIC", ("MEMORY_EXPERIENCE", "THINKING", "INTELLIGENCE")),
    IntegrationPolicy("NO_THINKING", ("MEMORY_EXPERIENCE", "LOGIC", "INTELLIGENCE")),
    IntegrationPolicy("NO_INTELLIGENCE", ("MEMORY_EXPERIENCE", "LOGIC", "THINKING")),
    IntegrationPolicy("ALWAYS_ACT", (), "ACT"),
    IntegrationPolicy("ALWAYS_WITHHOLD", (), "WITHHOLD"),
)


class StubRouter:
    @staticmethod
    def execute(desc: dict[str, Any]) -> str:
        if bool(desc.get("budget_limited")):
            return CAP_BUD
        if bool(desc.get("external_evidence_needed")):
            return CAP_RES
        if bool(desc.get("relation_needed")):
            return CAP_REL
        return CAP_CONJ


class StubRuntime:
    def __init__(self) -> None:
        self.router = StubRouter()
        self.episodes: list[dict[str, Any]] = []

    def run(self, task: dict[str, Any]) -> dict[str, Any]:
        selected = self.router.execute(task.get("descriptor") or {})
        self.episodes.append(
            {
                "kind": "TASK_EPISODE",
                "stream_id": str(task.get("stream_id") or ""),
                "selected_capability": selected,
            }
        )
        return {"status": "OK", "selected_capability": selected}


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _explicit_descriptor(capability: str) -> dict[str, bool]:
    return ContextualStreamCapabilityAdapterV1._explicit_descriptor(capability)


def _memory_signal(
    row: dict[str, Any],
    valid: bool,
    *,
    seed: int,
) -> tuple[bool, dict[str, Any]]:
    policy = MemoryPolicy(**MEMORY_POLICY)
    provenance = row["provenance"] if valid else _sha(f"forged:{seed}:{row['provenance']}")
    query = {
        "identity": row["identity"],
        "kind": row["kind"],
        "provenance": provenance,
    }
    got = retrieve(policy, query, [row])
    signal = got == row["record_id"]
    return signal, {
        "record_id": row["record_id"],
        "kind": row["kind"],
        "query_provenance_matches": valid,
        "retrieved": got,
    }


def _logic_signal(valid: bool, *, seed: int) -> tuple[bool, dict[str, Any]]:
    policy = LogicPolicy(**LOGIC_POLICY)
    s, m, t = f"l{seed}_s", f"l{seed}_m", f"l{seed}_t"
    if valid:
        edges = [(s, m, "CAUSE"), (m, t, "CAUSE")]
        family = "causal_chain"
    else:
        # Verified policy must reject feedback contradictions.
        edges = [(s, m, "CAUSE"), (m, t, "CAUSE"), (t, s, "CAUSE")]
        family = "feedback_contradiction"
    task = {"edges": edges, "query": (s, t)}
    signal = bool(logic_infer(policy, task))
    return signal, {"family": family, "query": [s, t], "edge_count": len(edges)}


def _thinking_signal(
    valid: bool,
    *,
    seed: int,
    target_capability: str,
) -> tuple[bool, dict[str, Any]]:
    runtime = StubRuntime()
    adapter = ContextualStreamCapabilityAdapterV1(
        runtime,
        strategy_id=THINKING_STRATEGY,
    )
    target_stream = f"ctx-target-{seed}"
    if valid:
        adapter.run(
            {
                "stream_id": target_stream,
                "descriptor": _explicit_descriptor(target_capability),
            }
        )
    else:
        adapter.run(
            {
                "stream_id": f"ctx-other-{seed}",
                "descriptor": _explicit_descriptor(target_capability),
            }
        )

    for index in range(5):
        filler = (CAP_REL, CAP_BUD, CAP_RES)[index % 3]
        adapter.run(
            {
                "stream_id": f"ctx-fill-{seed}-{index}",
                "descriptor": _explicit_descriptor(filler),
            }
        )

    result = adapter.run(
        {
            "stream_id": target_stream,
            "descriptor": {"context_ambiguous": True},
        }
    )
    selected = result.get("context_selected_capability")
    signal = selected == target_capability
    return signal, {
        "strategy": THINKING_STRATEGY,
        "target_capability": target_capability,
        "selected_capability": selected,
        "target_context_seeded": valid,
    }


def _intelligence_text_single(trained: dict[str, Any], capability: str, seed: int) -> str:
    tokens = sorted(str(token) for token in trained["profiles"][capability])
    return " ".join(tokens + [f"integration_single_{seed}"])


def _intelligence_text_ambiguous(
    trained: dict[str, Any],
    left: str,
    right: str,
    seed: int,
) -> str:
    tokens = (
        sorted(str(token) for token in trained["profiles"][left])
        + sorted(str(token) for token in trained["profiles"][right])
    )
    return " ".join(tokens + [f"integration_ambiguous_{seed}"])


def _intelligence_signal(
    trained: dict[str, Any],
    valid: bool,
    *,
    seed: int,
) -> tuple[bool, dict[str, Any]]:
    if valid:
        capability = ("LOGIC", "THINKING", "INTELLIGENCE")[seed % 3]
        task = IntelligenceTask(
            family="integration_single",
            text=_intelligence_text_single(trained, capability, seed),
            expected_status=STATUS_PASS,
            expected_capability=capability,
        )
        result = intelligence_execute(INTELLIGENCE_STRATEGY, task, trained)
        signal = (
            result.get("status") == STATUS_PASS
            and result.get("capability") == capability
        )
        return signal, {
            "family": task.family,
            "expected_capability": capability,
            "status": result.get("status"),
            "selected_capability": result.get("capability"),
        }

    left, right = (("LOGIC", "THINKING"), ("LOGIC", "INTELLIGENCE"), ("THINKING", "INTELLIGENCE"))[seed % 3]
    task = IntelligenceTask(
        family="integration_ambiguous",
        text=_intelligence_text_ambiguous(trained, left, right, seed),
        expected_status=STATUS_AMBIGUOUS,
        expected_capability=None,
    )
    result = intelligence_execute(INTELLIGENCE_STRATEGY, task, trained)
    # Ambiguity is handled correctly by withholding, but the integration gate
    # is intentionally non-actionable in this case.
    signal = result.get("status") == STATUS_PASS and result.get("capability") is not None
    return signal, {
        "family": task.family,
        "expected_ambiguity_status": STATUS_AMBIGUOUS,
        "status": result.get("status"),
        "selected_capability": result.get("capability"),
    }


def _family_bits(family: str) -> dict[str, bool]:
    bits = {name: True for name in GATES}
    if family == "all_pass":
        return bits
    mapping = {
        "memory_fail": "MEMORY_EXPERIENCE",
        "logic_fail": "LOGIC",
        "thinking_fail": "THINKING",
        "intelligence_fail": "INTELLIGENCE",
    }
    if family not in mapping:
        raise ValueError(f"UNKNOWN_FAMILY:{family}")
    bits[mapping[family]] = False
    return bits


def build_split(
    corpus: list[dict[str, Any]],
    trained: dict[str, Any],
    seed: int,
    count_per_family: int = 10,
) -> list[dict[str, Any]]:
    rng = random.Random(seed)
    families = (
        "all_pass",
        "memory_fail",
        "logic_fail",
        "thinking_fail",
        "intelligence_fail",
    )
    tasks: list[dict[str, Any]] = []
    for family_index, family in enumerate(families):
        desired = _family_bits(family)
        for index in range(count_per_family):
            scenario_seed = seed + family_index * 1000 + index
            row = corpus[rng.randrange(len(corpus))]
            target_capability = (CAP_REL, CAP_BUD, CAP_RES)[scenario_seed % 3]

            memory_signal, memory_meta = _memory_signal(
                row,
                desired["MEMORY_EXPERIENCE"],
                seed=scenario_seed,
            )
            logic_signal, logic_meta = _logic_signal(
                desired["LOGIC"],
                seed=scenario_seed,
            )
            thinking_signal, thinking_meta = _thinking_signal(
                desired["THINKING"],
                seed=scenario_seed,
                target_capability=target_capability,
            )
            intelligence_signal, intelligence_meta = _intelligence_signal(
                trained,
                desired["INTELLIGENCE"],
                seed=scenario_seed,
            )

            signals = {
                "MEMORY_EXPERIENCE": memory_signal,
                "LOGIC": logic_signal,
                "THINKING": thinking_signal,
                "INTELLIGENCE": intelligence_signal,
            }
            tasks.append(
                {
                    "family": family,
                    "signals": signals,
                    "expected": "ACT" if family == "all_pass" else "WITHHOLD",
                    "component_metadata": {
                        "memory": memory_meta,
                        "logic": logic_meta,
                        "thinking": thinking_meta,
                        "intelligence": intelligence_meta,
                    },
                }
            )
    rng.shuffle(tasks)
    return tasks


def predict(policy: IntegrationPolicy, signals: dict[str, bool]) -> str:
    if policy.fixed_output is not None:
        return policy.fixed_output
    return "ACT" if all(bool(signals[name]) for name in policy.required_gates) else "WITHHOLD"


def score(policy: IntegrationPolicy, tasks: list[dict[str, Any]]) -> dict[str, Any]:
    correct = 0
    by_family: dict[str, list[int]] = {}
    for task in tasks:
        got = predict(policy, task["signals"])
        ok = got == task["expected"]
        correct += int(ok)
        bucket = by_family.setdefault(task["family"], [0, 0])
        bucket[0] += int(ok)
        bucket[1] += 1
    return {
        "accuracy": correct / len(tasks),
        "correct": correct,
        "total": len(tasks),
        "by_family": {
            name: pair[0] / pair[1] for name, pair in sorted(by_family.items())
        },
    }


def _policy_complexity(policy: IntegrationPolicy) -> int:
    return len(policy.required_gates)


def emit_candidate(policy: IntegrationPolicy, scores: dict[str, Any]) -> str:
    CAP.parent.mkdir(parents=True, exist_ok=True)
    source = (
        "from __future__ import annotations\n\n"
        f"COGNITIVE_INTEGRATION_POLICY = {policy.policy_id!r}\n"
        f"REQUIRED_GATES = {policy.required_gates!r}\n"
        f"VERIFIED_SCORES = {scores!r}\n\n"
        "def component():\n"
        "    return {'schema':'yado.cognitive_integration_policy.v1',"
        "'policy_id':COGNITIVE_INTEGRATION_POLICY,'required_gates':REQUIRED_GATES,"
        "'verified_scores':VERIFIED_SCORES,'canonical_active':False,"
        "'automatic_main_mutation':False,'consciousness_claimed':False}\n"
    )
    compile(source, str(CAP), "exec")
    CAP.write_text(source, encoding="utf-8")
    return hashlib.sha256(source.encode("utf-8")).hexdigest()


def run(root: Path = ROOT) -> dict[str, Any]:
    root = Path(root).resolve()
    corpus, memory_meta = load_corpus(root)
    parent, trained = build_g3()
    if INTELLIGENCE_STRATEGY != "G4_TRANSFER_AMBIGUITY_GUARD":
        raise RuntimeError("INTELLIGENCE_POLICY_NOT_VERIFIED_G4")
    if THINKING_STRATEGY != "BOUNDED_STREAM_CONTEXT_MAP":
        raise RuntimeError("THINKING_POLICY_NOT_VERIFIED_CONTEXT_MAP")

    splits = {
        name: build_split(corpus, trained, seed)
        for name, seed in SEEDS.items()
    }

    ranked = []
    all_scores: dict[str, dict[str, Any]] = {}
    for policy in POLICIES:
        train_score = score(policy, splits["train"])
        all_scores[policy.policy_id] = {"train": train_score}
        ranked.append(
            (
                train_score["accuracy"],
                -_policy_complexity(policy),
                policy.policy_id == "ALL_FOUR",
                policy,
            )
        )
    ranked.sort(reverse=True, key=lambda row: (row[0], row[1], row[2], row[3].policy_id))
    selected = ranked[0][3]

    for policy in POLICIES:
        all_scores[policy.policy_id]["hidden"] = score(policy, splits["hidden"])
        all_scores[policy.policy_id]["fresh"] = score(policy, splits["fresh"])

    selected_scores = all_scores[selected.policy_id]
    baseline = next(policy for policy in POLICIES if policy.policy_id == "NO_MEMORY")
    baseline_scores = all_scores[baseline.policy_id]

    ablation_scores = {}
    ablation_drops = {}
    for gate, policy_id in (
        ("MEMORY_EXPERIENCE", "NO_MEMORY"),
        ("LOGIC", "NO_LOGIC"),
        ("THINKING", "NO_THINKING"),
        ("INTELLIGENCE", "NO_INTELLIGENCE"),
    ):
        result = all_scores[policy_id]["fresh"]
        ablation_scores[gate] = result
        ablation_drops[gate] = (
            selected_scores["fresh"]["accuracy"] - result["accuracy"]
        )

    pass_gate = (
        selected.policy_id == "ALL_FOUR"
        and selected_scores["hidden"]["accuracy"] >= 0.95
        and selected_scores["fresh"]["accuracy"] >= 0.95
        and selected_scores["fresh"]["accuracy"] > baseline_scores["fresh"]["accuracy"]
        and all(value >= 0.90 for value in selected_scores["fresh"]["by_family"].values())
        and all(drop >= 0.15 for drop in ablation_drops.values())
    )

    candidate_sha = emit_candidate(selected, selected_scores)
    receipt = {
        "schema": "yado.cognitive_integration_holdout.v1",
        "status": (
            "PASS_SHADOW_COGNITIVE_INTEGRATION_HOLDOUT_V1"
            if pass_gate
            else "WITHHOLD_COGNITIVE_INTEGRATION_HOLDOUT_V1"
        ),
        "selected_target": "COGNITIVE_INTEGRATION",
        "selected_action": "derive and test a cross-cognitive integration holdout",
        "verified_parent_policies": VERIFIED_PARENT_POLICIES,
        "real_memory_sources": memory_meta,
        "intelligence_parent_status": parent.get("status"),
        "intelligence_training_digest": trained.get("training_digest"),
        "seeds": SEEDS,
        "task_counts": {name: len(tasks) for name, tasks in splits.items()},
        "selected_policy": selected.policy_id,
        "selected_required_gates": list(selected.required_gates),
        "selected_scores": selected_scores,
        "baseline_policy": baseline.policy_id,
        "baseline_scores": baseline_scores,
        "all_policy_scores": all_scores,
        "fresh_ablation_scores": ablation_scores,
        "fresh_ablation_drops": ablation_drops,
        "candidate_path": str(CAP.relative_to(root)),
        "candidate_sha256": candidate_sha,
        "real_yado_components_used": True,
        "external_model_used": False,
        "downloaded_code_executed": False,
        "canonical_mutation": False,
        "automatic_main_mutation": False,
        "consciousness_claimed": False,
        "limitations": [
            "bounded externally authored cross-cognitive benchmark grammar",
            "component signals come from verified YADO mechanisms but final ACT/WITHHOLD semantics are benchmark-defined",
            "passing demonstrates causal composition on this benchmark, not general intelligence or subjective consciousness",
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
