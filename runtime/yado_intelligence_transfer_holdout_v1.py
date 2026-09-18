from __future__ import annotations

"""Fresh INTELLIGENCE capability-transfer holdout over YADO's real G4 router.

The benchmark reuses the existing three-generation external-project training
profiles and the G4 ambiguity-aware transfer router. Fresh splits contain new
combinations of learned capability tokens, explicit multi-capability ambiguity,
and unknown-domain probes. No third-party code is executed.
"""

from dataclasses import dataclass
import hashlib
import itertools
import json
import random
from pathlib import Path
from typing import Any

from yado_external_project_training_v1 import (
    SOURCE_ROWS,
    STATUS_PASS,
    STATUS_WITHHOLD,
    route,
)
from yado_external_project_evolution_v2 import (
    ADAPTATION_TASKS,
    SEED_TASKS,
    _rows,
    _train,
    run as run_three_generations,
)
from yado_external_project_transfer_v3 import (
    STATUS_AMBIGUOUS,
    route_transfer,
)

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "candidates/cognitive/yado-intelligence-transfer-holdout-v1.json"
CAP = ROOT / "candidates/cognitive/yado_intelligence_transfer_policy_v1.py"
TRANSFER_COMPONENT = ROOT / "runtime/yado_external_project_transfer_v3.py"

SEEDS = {"train": 2026091831, "hidden": 2026091832, "fresh": 2026091833}
CAPABILITIES = ("LOGIC", "THINKING", "INTELLIGENCE")
STRATEGIES = ("BASE_ROUTE", "G4_TRANSFER_AMBIGUITY_GUARD", "ALWAYS_WITHHOLD")


@dataclass(frozen=True)
class Task:
    family: str
    text: str
    expected_status: str
    expected_capability: str | None


def _digest(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def build_g3() -> tuple[dict[str, Any], dict[str, Any]]:
    parent = run_three_generations()
    if parent.get("status") != "PASS_SHADOW_THREE_STATE_DERIVED_GENERATIONS_V2":
        raise RuntimeError("G3_PARENT_NOT_PASS")
    trained = _train(tuple(SOURCE_ROWS) + _rows(SEED_TASKS) + _rows(ADAPTATION_TASKS))
    return parent, trained


def _noise(seed: int, index: int) -> str:
    return f"novel_{seed}_{index} neutral_{(seed + index) % 997}"


def build_split(trained: dict[str, Any], seed: int, per_family: int = 8) -> list[Task]:
    rng = random.Random(seed)
    profiles = {
        capability: sorted(str(token) for token in trained["profiles"][capability])
        for capability in CAPABILITIES
    }
    if any(not tokens for tokens in profiles.values()):
        raise ValueError("EMPTY_CAPABILITY_PROFILE")

    tasks: list[Task] = []

    # Fresh single-capability compositions: sample different subsets of the
    # actual learned G3 profile tokens and add unrelated surface noise.
    for capability in CAPABILITIES:
        tokens = profiles[capability]
        take = min(3, len(tokens))
        for index in range(per_family):
            chosen = rng.sample(tokens, take)
            rng.shuffle(chosen)
            text = " ".join(chosen + [_noise(seed, index + 100 * CAPABILITIES.index(capability))])
            tasks.append(
                Task(
                    family=f"single_{capability.lower()}",
                    text=text,
                    expected_status=STATUS_PASS,
                    expected_capability=capability,
                )
            )

    # Multi-capability tasks contain every learned token for both profiles.
    # Each active profile therefore has normalized score 1.0, making the
    # ambiguity independent of profile token frequency.
    for pair_index, (left, right) in enumerate(itertools.combinations(CAPABILITIES, 2)):
        pair_tokens = profiles[left] + profiles[right]
        for index in range(per_family):
            tokens = list(pair_tokens)
            rng.shuffle(tokens)
            text = " ".join(tokens + [_noise(seed, 500 + pair_index * 100 + index)])
            tasks.append(
                Task(
                    family=f"ambiguous_{left.lower()}_{right.lower()}",
                    text=text,
                    expected_status=STATUS_AMBIGUOUS,
                    expected_capability=None,
                )
            )

    for index in range(per_family):
        tasks.append(
            Task(
                family="unknown_domain",
                text=f"quasar_{seed}_{index} zephyr_{seed + index} unmapped_semantics_{index}",
                expected_status=STATUS_WITHHOLD,
                expected_capability=None,
            )
        )

    rng.shuffle(tasks)
    return tasks


def execute(strategy: str, task: Task, trained: dict[str, Any]) -> dict[str, Any]:
    if strategy == "BASE_ROUTE":
        return route(task.text, trained)
    if strategy == "G4_TRANSFER_AMBIGUITY_GUARD":
        return route_transfer(task.text, trained)
    if strategy == "ALWAYS_WITHHOLD":
        return {"status": STATUS_WITHHOLD, "capability": None}
    raise ValueError(f"UNKNOWN_STRATEGY:{strategy}")


def score(strategy: str, tasks: list[Task], trained: dict[str, Any]) -> dict[str, Any]:
    correct = 0
    by_family: dict[str, list[int]] = {}
    for task in tasks:
        result = execute(strategy, task, trained)
        ok = (
            result.get("status") == task.expected_status
            and result.get("capability") == task.expected_capability
        )
        correct += int(ok)
        bucket = by_family.setdefault(task.family, [0, 0])
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


def _strategy_cost(strategy: str) -> int:
    return {
        "BASE_ROUTE": 1,
        "G4_TRANSFER_AMBIGUITY_GUARD": 2,
        "ALWAYS_WITHHOLD": 0,
    }[strategy]


def emit_candidate(strategy: str, scores: dict[str, Any]) -> str:
    CAP.parent.mkdir(parents=True, exist_ok=True)
    source = (
        "from __future__ import annotations\n\n"
        f"INTELLIGENCE_TRANSFER_STRATEGY = {strategy!r}\n"
        f"VERIFIED_SCORES = {scores!r}\n\n"
        "def component():\n"
        "    return {'schema':'yado.intelligence_transfer_policy.v1',"
        "'strategy_id':INTELLIGENCE_TRANSFER_STRATEGY,'verified_scores':VERIFIED_SCORES,"
        "'canonical_active':False,'automatic_main_mutation':False,"
        "'consciousness_claimed':False}\n"
    )
    compile(source, str(CAP), "exec")
    CAP.write_text(source, encoding="utf-8")
    return hashlib.sha256(source.encode("utf-8")).hexdigest()


def run(root: Path = ROOT) -> dict[str, Any]:
    root = Path(root).resolve()
    parent, trained = build_g3()
    splits = {name: build_split(trained, seed) for name, seed in SEEDS.items()}

    all_scores: dict[str, dict[str, Any]] = {}
    ranked = []
    for strategy in STRATEGIES:
        train_score = score(strategy, splits["train"], trained)
        all_scores[strategy] = {"train": train_score}
        ranked.append(
            (
                train_score["accuracy"],
                -_strategy_cost(strategy),
                strategy == "G4_TRANSFER_AMBIGUITY_GUARD",
                strategy,
            )
        )
    ranked.sort(reverse=True)
    selected = ranked[0][3]

    for strategy in STRATEGIES:
        all_scores[strategy]["hidden"] = score(strategy, splits["hidden"], trained)
        all_scores[strategy]["fresh"] = score(strategy, splits["fresh"], trained)

    baseline_scores = all_scores["BASE_ROUTE"]
    selected_scores = all_scores[selected]
    fresh_gain = selected_scores["fresh"]["accuracy"] - baseline_scores["fresh"]["accuracy"]

    pass_gate = (
        selected == "G4_TRANSFER_AMBIGUITY_GUARD"
        and selected_scores["hidden"]["accuracy"] >= 0.95
        and selected_scores["fresh"]["accuracy"] >= 0.95
        and fresh_gain >= 0.20
        and all(value >= 0.90 for value in selected_scores["fresh"]["by_family"].values())
    )

    candidate_sha = emit_candidate(selected, selected_scores)
    component_sha = hashlib.sha256(TRANSFER_COMPONENT.read_bytes()).hexdigest()

    receipt = {
        "schema": "yado.intelligence_transfer_holdout.v1",
        "status": (
            "PASS_SHADOW_INTELLIGENCE_TRANSFER_HOLDOUT_V1"
            if pass_gate
            else "WITHHOLD_INTELLIGENCE_TRANSFER_HOLDOUT_V1"
        ),
        "selected_target": "INTELLIGENCE",
        "selected_action": "derive and test a capability-transfer holdout",
        "real_yado_component": "yado.external_project_transfer.v3",
        "component_path": str(TRANSFER_COMPONENT.relative_to(root)),
        "component_sha256": component_sha,
        "parent_status": parent.get("status"),
        "training_digest": trained.get("training_digest"),
        "profile_digest": _digest(trained.get("profiles")),
        "profile_tokens": {
            capability: sorted(trained["profiles"][capability])
            for capability in CAPABILITIES
        },
        "source_repositories": trained.get("source_repositories"),
        "seeds": SEEDS,
        "task_counts": {name: len(tasks) for name, tasks in splits.items()},
        "baseline_strategy": "BASE_ROUTE",
        "baseline_scores": baseline_scores,
        "selected_strategy": selected,
        "selected_scores": selected_scores,
        "all_strategy_scores": all_scores,
        "fresh_absolute_gain": fresh_gain,
        "candidate_path": str(CAP.relative_to(root)),
        "candidate_sha256": candidate_sha,
        "real_yado_transfer_router_used": True,
        "third_party_code_executed": False,
        "external_writes": False,
        "external_model_used": False,
        "canonical_mutation": False,
        "automatic_main_mutation": False,
        "consciousness_claimed": False,
        "limitations": [
            "bounded learned-vocabulary transfer benchmark",
            "fresh splits use new token combinations and surface noise, not unseen semantic vocabulary",
            "task generator and candidate strategy set are externally authored",
            "passing demonstrates capability routing/ambiguity discipline, not general intelligence",
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
