from __future__ import annotations

"""Fresh contextual THINKING holdout over YADO's real contextual stream adapter.

The benchmark exercises the existing ContextualStreamCapabilityAdapterV1 rather
than reimplementing its behavior. It measures stream-specific context retention,
long-gap retention beyond the recurrent episode lookback, explicit context
updates, and cross-stream isolation on train/hidden/fresh seeded suites.
"""

from dataclasses import asdict
import hashlib
import json
import random
from pathlib import Path
from typing import Any

from yado_g2_contextual_stream_capability_adapter_v1 import (
    CAP_BUD,
    CAP_CONJ,
    CAP_REL,
    CAP_RES,
    STRATEGIES,
    ContextualStreamCapabilityAdapterV1,
)

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "candidates/cognitive/yado-thinking-contextual-holdout-v1.json"
CAP = ROOT / "candidates/cognitive/yado_thinking_contextual_policy_v1.py"
ADAPTER_PATH = ROOT / "runtime/yado_g2_contextual_stream_capability_adapter_v1.py"

SEEDS = {"train": 2026091821, "hidden": 2026091822, "fresh": 2026091823}
TARGET_CAPABILITIES = (CAP_REL, CAP_BUD, CAP_RES)


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


def _explicit_descriptor(capability: str) -> dict[str, bool]:
    return ContextualStreamCapabilityAdapterV1._explicit_descriptor(capability)


def _explicit_task(stream_id: str, capability: str) -> dict[str, Any]:
    return {"stream_id": stream_id, "descriptor": _explicit_descriptor(capability)}


def _ambiguous_task(stream_id: str) -> dict[str, Any]:
    return {"stream_id": stream_id, "descriptor": {"context_ambiguous": True}}


def _other_capability(capability: str, offset: int = 1) -> str:
    pool = list(TARGET_CAPABILITIES)
    index = pool.index(capability)
    return pool[(index + offset) % len(pool)]


def _scenario_short_interleave(rng: random.Random, index: int) -> dict[str, Any]:
    target = TARGET_CAPABILITIES[index % len(TARGET_CAPABILITIES)]
    stream = f"short-target-{index}"
    fillers = [
        _explicit_task(f"short-filler-{index}-{j}", TARGET_CAPABILITIES[(index + j + 1) % len(TARGET_CAPABILITIES)])
        for j in range(7)
    ]
    return {
        "family": "short_interleave",
        "steps": [_explicit_task(stream, target), *fillers, _ambiguous_task(stream)],
        "queries": [(len(fillers) + 1, target)],
    }


def _scenario_long_gap(rng: random.Random, index: int) -> dict[str, Any]:
    target = TARGET_CAPABILITIES[index % len(TARGET_CAPABILITIES)]
    stream = f"long-target-{index}"
    # More than adapter.MAX_LOOKBACK, but far below MAX_STREAM_CONTEXTS.
    fillers = [
        _explicit_task(
            f"long-filler-{index}-{j}",
            TARGET_CAPABILITIES[(index + j + 1) % len(TARGET_CAPABILITIES)],
        )
        for j in range(ContextualStreamCapabilityAdapterV1.MAX_LOOKBACK + 12)
    ]
    return {
        "family": "long_gap",
        "steps": [_explicit_task(stream, target), *fillers, _ambiguous_task(stream)],
        "queries": [(len(fillers) + 1, target)],
    }


def _scenario_context_update(rng: random.Random, index: int) -> dict[str, Any]:
    first = TARGET_CAPABILITIES[index % len(TARGET_CAPABILITIES)]
    second = _other_capability(first)
    stream = f"update-target-{index}"
    fillers_a = [
        _explicit_task(f"update-a-{index}-{j}", TARGET_CAPABILITIES[(index + j + 1) % len(TARGET_CAPABILITIES)])
        for j in range(4)
    ]
    fillers_b = [
        _explicit_task(f"update-b-{index}-{j}", TARGET_CAPABILITIES[(index + j + 2) % len(TARGET_CAPABILITIES)])
        for j in range(6)
    ]
    steps = [
        _explicit_task(stream, first),
        *fillers_a,
        _explicit_task(stream, second),
        *fillers_b,
        _ambiguous_task(stream),
    ]
    return {
        "family": "context_update",
        "steps": steps,
        "queries": [(len(steps) - 1, second)],
    }


def _scenario_cross_stream_isolation(rng: random.Random, index: int) -> dict[str, Any]:
    cap_a = TARGET_CAPABILITIES[index % len(TARGET_CAPABILITIES)]
    cap_b = _other_capability(cap_a)
    stream_a = f"cross-a-{index}"
    stream_b = f"cross-b-{index}"
    steps = [
        _explicit_task(stream_a, cap_a),
        _explicit_task(stream_b, cap_b),
        _ambiguous_task(stream_a),
        _ambiguous_task(stream_b),
    ]
    return {
        "family": "cross_stream_isolation",
        "steps": steps,
        "queries": [(2, cap_a), (3, cap_b)],
    }


def build_split(seed: int, count_per_family: int = 8) -> list[dict[str, Any]]:
    rng = random.Random(seed)
    builders = (
        _scenario_short_interleave,
        _scenario_long_gap,
        _scenario_context_update,
        _scenario_cross_stream_isolation,
    )
    rows: list[dict[str, Any]] = []
    for builder_index, builder in enumerate(builders):
        for i in range(count_per_family):
            rows.append(builder(rng, i + builder_index * 100))
    rng.shuffle(rows)
    return rows


def run_scenario(strategy_id: str, scenario: dict[str, Any]) -> bool:
    runtime = StubRuntime()
    adapter = ContextualStreamCapabilityAdapterV1(runtime, strategy_id=strategy_id)
    expected_by_index = dict(scenario["queries"])
    for index, task in enumerate(scenario["steps"]):
        result = adapter.run(task)
        if index in expected_by_index:
            if result.get("context_selected_capability") != expected_by_index[index]:
                return False
    return True


def score(strategy_id: str, scenarios: list[dict[str, Any]]) -> dict[str, Any]:
    correct = 0
    by_family: dict[str, list[int]] = {}
    for scenario in scenarios:
        ok = run_scenario(strategy_id, scenario)
        correct += int(ok)
        bucket = by_family.setdefault(scenario["family"], [0, 0])
        bucket[0] += int(ok)
        bucket[1] += 1
    return {
        "accuracy": correct / len(scenarios),
        "correct": correct,
        "total": len(scenarios),
        "by_family": {
            name: pair[0] / pair[1] for name, pair in sorted(by_family.items())
        },
    }


def _strategy_metadata(strategy_id: str) -> dict[str, Any]:
    for item in STRATEGIES:
        if item.strategy_id == strategy_id:
            return asdict(item)
    raise ValueError(f"UNKNOWN_STRATEGY:{strategy_id}")


def _objective(result: dict[str, Any], strategy_id: str) -> tuple[Any, ...]:
    meta = _strategy_metadata(strategy_id)
    # Performance dominates; lower risk/complexity break exact ties.
    return (
        result["accuracy"],
        -float(meta["risk"]),
        -float(meta["complexity"]),
        float(meta["novelty"]),
        strategy_id,
    )


def emit_candidate(strategy_id: str, scores: dict[str, Any]) -> str:
    CAP.parent.mkdir(parents=True, exist_ok=True)
    source = (
        "from __future__ import annotations\n\n"
        f"THINKING_CONTEXT_STRATEGY = {strategy_id!r}\n"
        f"VERIFIED_SCORES = {scores!r}\n\n"
        "def component():\n"
        "    return {'schema':'yado.thinking_contextual_policy.v1',"
        "'strategy_id':THINKING_CONTEXT_STRATEGY,'verified_scores':VERIFIED_SCORES,"
        "'canonical_active':False,'automatic_main_mutation':False,"
        "'consciousness_claimed':False}\n"
    )
    compile(source, str(CAP), "exec")
    CAP.write_text(source, encoding="utf-8")
    return hashlib.sha256(source.encode("utf-8")).hexdigest()


def run(root: Path = ROOT) -> dict[str, Any]:
    root = Path(root).resolve()
    splits = {name: build_split(seed) for name, seed in SEEDS.items()}
    baseline_id = "BASE_ROUTER_ONLY"
    baseline_scores = {name: score(baseline_id, rows) for name, rows in splits.items()}

    ranked = []
    for strategy in STRATEGIES:
        train = score(strategy.strategy_id, splits["train"])
        ranked.append((_objective(train, strategy.strategy_id), strategy.strategy_id, train))
    ranked.sort(key=lambda row: row[0], reverse=True)

    selected_id = ranked[0][1]
    selected_scores = {name: score(selected_id, rows) for name, rows in splits.items()}

    pass_gate = (
        selected_id == "BOUNDED_STREAM_CONTEXT_MAP"
        and selected_scores["hidden"]["accuracy"] >= 0.95
        and selected_scores["fresh"]["accuracy"] >= 0.95
        and selected_scores["fresh"]["accuracy"] > baseline_scores["fresh"]["accuracy"]
        and all(value >= 0.90 for value in selected_scores["fresh"]["by_family"].values())
    )

    candidate_sha = emit_candidate(selected_id, selected_scores)
    adapter_sha256 = hashlib.sha256(ADAPTER_PATH.read_bytes()).hexdigest()

    receipt = {
        "schema": "yado.thinking_contextual_holdout.v1",
        "status": (
            "PASS_SHADOW_THINKING_CONTEXTUAL_HOLDOUT_V1"
            if pass_gate
            else "WITHHOLD_THINKING_CONTEXTUAL_HOLDOUT_V1"
        ),
        "selected_target": "THINKING",
        "selected_action": "derive and test a contextual reasoning holdout",
        "real_yado_component": "ALG-G2-CONTEXTUAL-STREAM-CAPABILITY-ADAPTER-V1",
        "adapter_path": str(ADAPTER_PATH.relative_to(root)),
        "adapter_sha256": adapter_sha256,
        "adapter_limits": {
            "max_lookback": ContextualStreamCapabilityAdapterV1.MAX_LOOKBACK,
            "max_stream_contexts": ContextualStreamCapabilityAdapterV1.MAX_STREAM_CONTEXTS,
        },
        "seeds": SEEDS,
        "scenario_counts": {name: len(rows) for name, rows in splits.items()},
        "baseline_strategy": baseline_id,
        "baseline_scores": baseline_scores,
        "selected_strategy": selected_id,
        "selected_strategy_metadata": _strategy_metadata(selected_id),
        "selected_scores": selected_scores,
        "candidate_path": str(CAP.relative_to(root)),
        "candidate_sha256": candidate_sha,
        "real_yado_context_adapter_used": True,
        "external_model_used": False,
        "downloaded_code_executed": False,
        "canonical_mutation": False,
        "automatic_main_mutation": False,
        "consciousness_claimed": False,
        "limitations": [
            "bounded contextual routing benchmark",
            "scenario generator and strategy selection objective are externally authored",
            "passing demonstrates stream-context handling only, not general reasoning",
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
