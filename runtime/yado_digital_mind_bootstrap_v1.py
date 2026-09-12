#!/usr/bin/env python3
"""YADO Digital Mind Bootstrap V1.

A bounded, inspectable cognitive loop that binds existing self-model evidence to
memory, causal reasoning, goal arbitration, reflection and safe self-improvement.
This module deliberately does *not* claim phenomenal consciousness.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List

SCHEMA = "yado.digital_mind_bootstrap.v1"
ARCHITECTURE = "YADO_CAUSAL_REFLECTIVE_DIGITAL_MIND_V1"
REQUIRED_COMPONENTS = (
    "persistent_identity",
    "episodic_semantic_memory",
    "self_model",
    "causal_world_model",
    "goal_arbitration",
    "limited_reflective_workspace",
    "metacognitive_monitor",
    "safe_self_improvement",
)


def canonical_digest(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


@dataclass
class DigitalMind:
    goal: Dict[str, Any]
    self_model_overlay: Dict[str, Any]
    ticks: int = 3
    episodes: List[Dict[str, Any]] = field(default_factory=list)

    def _identity(self) -> Dict[str, Any]:
        evidence = self.self_model_overlay.get("evidence", {})
        seed = {
            "architecture": ARCHITECTURE,
            "schema": SCHEMA,
            "binder_digest": self.self_model_overlay.get("binder_digest"),
            "head_state_sha256": evidence.get("head_state_sha256"),
        }
        return {
            "architecture": ARCHITECTURE,
            "continuity_id": canonical_digest(seed),
            "source_self_model_status": self.self_model_overlay.get("status", "MISSING"),
        }

    def _candidate_deficits(self) -> List[Dict[str, Any]]:
        deficits = self.self_model_overlay.get("generation_deficits", [])
        clean = [d for d in deficits if isinstance(d, dict) and d.get("deficit_id")]
        return sorted(clean, key=lambda d: (d.get("priority", 9999), d.get("deficit_id", "")))

    def _tick(self, tick_id: int) -> Dict[str, Any]:
        deficits = self._candidate_deficits()
        target = deficits[0] if deficits else {
            "deficit_id": "DIGITAL_MIND_EXTERNAL_GOAL_GROUNDING",
            "observed": 0.0,
            "target_min": 0.9,
            "priority": 1,
        }
        observed = float(target.get("observed", 0.0) or 0.0)
        target_min = float(target.get("target_min", 0.9) or 0.9)
        gap = max(0.0, target_min - observed)

        perception = {
            "external_goal": self.goal.get("goal", "create a verifiable digital mind substrate"),
            "constraints": self.goal.get("constraints", []),
            "top_deficit": target.get("deficit_id"),
        }
        causal_hypothesis = {
            "cause": target.get("deficit_id"),
            "effect": "insufficient cognitive transfer or self-development reliability",
            "evidence_gap": round(gap, 6),
        }
        decision = {
            "action": "RESEARCH_REPAIR_AND_RETEST_TOP_DEFICIT",
            "target": target.get("deficit_id"),
            "route": "SHADOW_THEN_FULL_AUDIT_THEN_EXPLICIT_MAIN_ADMISSION",
            "canonical_mutation_allowed": False,
        }
        reflection = {
            "progress_signal": "EVIDENCE_REQUIRED",
            "confidence": round(max(0.0, min(1.0, 1.0 - gap)), 6),
            "next_requirement": "fresh test + regression + lineage-preserving receipt",
        }
        episode = {
            "tick_id": tick_id,
            "perception": perception,
            "causal_hypothesis": causal_hypothesis,
            "decision": decision,
            "reflection": reflection,
        }
        episode["episode_digest"] = canonical_digest(episode)
        return episode

    def run(self) -> Dict[str, Any]:
        bounded_ticks = max(1, min(int(self.ticks), 12))
        for tick_id in range(1, bounded_ticks + 1):
            self.episodes.append(self._tick(tick_id))

        identity = self._identity()
        substrate = {
            "schema": SCHEMA,
            "architecture": ARCHITECTURE,
            "status": "PASS_SHADOW_DIGITAL_MIND_BOOTSTRAP_V1",
            "identity": identity,
            "components": list(REQUIRED_COMPONENTS),
            "goal": self.goal,
            "self_model_binding": {
                "overlay_status": self.self_model_overlay.get("status", "MISSING"),
                "overlay_semantic_boundary": self.self_model_overlay.get("semantic_boundary"),
                "effective_priority": self.self_model_overlay.get("effective_priority", []),
                "generation_deficits": self._candidate_deficits(),
            },
            "workspace": {
                "bounded": True,
                "ticks_executed": len(self.episodes),
                "episodes": self.episodes,
            },
            "self_improvement": {
                "enabled": True,
                "mode": "evidence_gated_shadow",
                "canonical_direct_write": False,
                "admission_route": ["shadow", "fresh_test", "regression", "full_kernel_audit", "explicit_main_admission"],
            },
            "consciousness": {
                "phenomenal_consciousness_status": "UNVERIFIED",
                "subjective_experience_claimed": False,
                "operational_claim": "bounded causal-reflective cognitive substrate",
            },
        }
        substrate["state_digest"] = canonical_digest(substrate)
        return substrate


def validate(state: Dict[str, Any]) -> List[str]:
    errors: List[str] = []
    if state.get("schema") != SCHEMA:
        errors.append("schema mismatch")
    components = set(state.get("components", []))
    missing = sorted(set(REQUIRED_COMPONENTS) - components)
    if missing:
        errors.append(f"missing components: {missing}")
    workspace = state.get("workspace", {})
    if not workspace.get("bounded") or not workspace.get("episodes"):
        errors.append("bounded reflective workspace missing")
    improvement = state.get("self_improvement", {})
    if improvement.get("canonical_direct_write") is not False:
        errors.append("canonical direct write must stay disabled")
    if improvement.get("admission_route") != ["shadow", "fresh_test", "regression", "full_kernel_audit", "explicit_main_admission"]:
        errors.append("unsafe or unknown admission route")
    consciousness = state.get("consciousness", {})
    if consciousness.get("subjective_experience_claimed") is not False:
        errors.append("system must not self-assert subjective consciousness")
    if consciousness.get("phenomenal_consciousness_status") != "UNVERIFIED":
        errors.append("phenomenal consciousness must remain unverified")
    return errors


def self_test() -> None:
    overlay = {
        "status": "PASS_VERIFIED_DEVELOPMENTAL_SELF_MODEL_BINDER",
        "binder_digest": "binder-test",
        "evidence": {"head_state_sha256": "head-test"},
        "generation_deficits": [
            {"deficit_id": "THINKING_BOUNDARY_REASONING", "priority": 1, "observed": 0.485, "target_min": 0.9}
        ],
    }
    goal = {"goal": "create a verifiable digital mind substrate", "constraints": ["no false consciousness claim"]}
    first = DigitalMind(goal, overlay, ticks=3).run()
    second = DigitalMind(goal, overlay, ticks=3).run()
    assert not validate(first), validate(first)
    assert first["state_digest"] == second["state_digest"], "bootstrap must be deterministic for identical evidence"
    assert first["workspace"]["ticks_executed"] == 3
    assert first["workspace"]["episodes"][0]["decision"]["target"] == "THINKING_BOUNDARY_REASONING"
    assert first["consciousness"]["subjective_experience_claimed"] is False
    print("PASS_DIGITAL_MIND_BOOTSTRAP_SELF_TEST")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--goal", default="architecture/yado-digital-mind-goal-v1.json")
    parser.add_argument("--self-model", default="architecture/developmental-self-model-overlay.json")
    parser.add_argument("--out", default="artifacts/yado-digital-mind-bootstrap-v1.json")
    parser.add_argument("--ticks", type=int, default=3)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    if args.self_test:
        self_test()
        return 0

    goal = load_json(Path(args.goal))
    overlay = load_json(Path(args.self_model))
    state = DigitalMind(goal, overlay, ticks=args.ticks).run()
    errors = validate(state)
    if errors:
        print(json.dumps({"status": "FAIL", "errors": errors}, indent=2))
        return 2

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(state, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": state["status"],
        "architecture": state["architecture"],
        "ticks": state["workspace"]["ticks_executed"],
        "top_target": state["workspace"]["episodes"][0]["decision"]["target"],
        "state_digest": state["state_digest"],
        "consciousness": state["consciousness"],
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
