from __future__ import annotations

"""Bounded controller for autonomous deep development across YADO layers.

V2 selection keeps the existing admission surface but chooses cognitive deficits
from measured evidence when available instead of using file counts as a proxy
for capability quality.
"""

import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "candidates/kernel-self-generated/yado-autonomous-deep-development-v1.json"

LAYER_RULES = {
    "CODE": lambda rel: rel.suffix == ".py" and rel.parts[0] in {"runtime", "successor"},
    "LAYERS": lambda rel: rel.suffix == ".json" and rel.parts[0] in {"architecture", "canonical"},
    "MODULES": lambda rel: rel.suffix == ".py" and rel.parts[0] in {"runtime", "successor", "candidates"},
    "MEMORY_EXPERIENCE": lambda rel: rel.parts[0] in {"experience", "receipts"} and rel.suffix == ".json",
    "LOGIC": lambda rel: any(token in rel.name.lower() for token in ("logic", "causal", "invariant", "reason", "proof")),
    "THINKING": lambda rel: any(token in rel.name.lower() for token in ("thinking", "cognitive", "context", "workspace", "reflect")),
    "INTELLIGENCE": lambda rel: any(token in rel.name.lower() for token in ("intelligence", "external", "capability", "evolution", "agent", "successor")),
}

COGNITIVE_TARGETS = ("LOGIC", "THINKING", "INTELLIGENCE", "MEMORY_EXPERIENCE")
TARGET_ORDER = {name: index for index, name in enumerate(COGNITIVE_TARGETS)}

ACTION_BY_TARGET = {
    "INTEGRITY": "reconcile canonical identity, ancestry, and layer bindings",
    "VERIFICATION": "re-run fresh compile, regression, audit, and counterfactual gates",
    "CODE": "generate and execute a bounded native source candidate",
    "LAYERS": "repair cross-layer bindings and re-check architecture receipts",
    "MODULES": "test module connectivity and isolate duplicate or orphan behavior",
    "MEMORY_EXPERIENCE": "derive and test a fresh memory/provenance recall holdout",
    "LOGIC": "derive and test a new relational/causal logic holdout",
    "THINKING": "derive and test a contextual reasoning holdout",
    "INTELLIGENCE": "derive and test a capability-transfer holdout",
    "COGNITIVE_INTEGRATION": "derive and test a cross-cognitive integration holdout",
}

SEQUENCE = (
    ("CODE", "native candidate -> compile -> isolated execution"),
    ("LAYERS", "architecture binding -> canonical guard -> audit"),
    ("MODULES", "module inventory -> connectivity -> regression"),
    ("MEMORY_EXPERIENCE", "verified receipt -> provenance -> replay"),
    ("LOGIC", "logic holdout -> contradiction/causal check"),
    ("THINKING", "context holdout -> bounded reasoning check"),
    ("INTELLIGENCE", "transfer holdout -> ambiguity guard"),
)

LOGIC_HOLDOUT = "candidates/cognitive/yado-relational-causal-logic-holdout-v1.json"
TRI_ORGAN = "candidates/cognitive/yado-cognitive-tri-organ-evolution-v2.json"
THINKING_HOLDOUT = "candidates/cognitive/yado-thinking-contextual-holdout-v1.json"
INTELLIGENCE_HOLDOUT = "candidates/cognitive/yado-intelligence-transfer-holdout-v1.json"
MEMORY_HOLDOUT = "candidates/cognitive/yado-memory-experience-holdout-v1.json"
MEMORY_INDEX = "experience/branch-lifecycle/yado-branch-memory-index-v1.json"


def _digest(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _read_json(root: Path, relative: str) -> dict[str, Any] | None:
    path = root / relative
    if not path.exists():
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def _load_status(root: Path, relative: str) -> dict[str, Any]:
    value = _read_json(root, relative)
    if value is None:
        return {"status": "MISSING", "path": relative}
    return {
        "status": value.get("status", "UNKNOWN"),
        "path": relative,
        "findings": len(value.get("findings", [])),
        "failures": len(value.get("failures", [])),
    }


def _files(root: Path) -> list[Path]:
    excluded = {".git", "__pycache__", ".pytest_cache"}
    return sorted(
        path.relative_to(root)
        for path in root.rglob("*")
        if path.is_file() and not any(part in excluded for part in path.parts)
    )


def _layer_snapshot(root: Path) -> dict[str, dict[str, Any]]:
    files = _files(root)
    snapshot: dict[str, dict[str, Any]] = {}
    for layer, predicate in LAYER_RULES.items():
        selected = [path.as_posix() for path in files if predicate(path)]
        snapshot[layer] = {
            "file_count": len(selected),
            "sample": selected[:8],
            "evidence_digest": _digest(selected),
        }
    return snapshot


def _number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        out = float(value)
        if 0.0 <= out <= 1.0:
            return out
    return None


def _cognitive_evidence(root: Path) -> dict[str, dict[str, Any]]:
    evidence: dict[str, dict[str, Any]] = {
        name: {
            "score": None,
            "evidence_level": 0,
            "evidence_kind": "UNMEASURED",
            "source": None,
            "status": "MISSING_MEASURED_EVIDENCE",
        }
        for name in COGNITIVE_TARGETS
    }

    logic = _read_json(root, LOGIC_HOLDOUT)
    if logic and str(logic.get("status", "")).startswith("PASS_"):
        score = _number(((logic.get("selected_scores") or {}).get("fresh") or {}).get("accuracy"))
        if score is not None:
            evidence["LOGIC"] = {
                "score": score,
                "evidence_level": 3,
                "evidence_kind": "FRESH_HOLDOUT",
                "source": LOGIC_HOLDOUT,
                "status": logic.get("status"),
            }

    tri = _read_json(root, TRI_ORGAN)
    if tri and str(tri.get("status", "")).startswith("PASS_"):
        hidden = tri.get("selected_hidden") or {}
        for target, key in (("THINKING", "thinking"), ("INTELLIGENCE", "intelligence")):
            score = _number(hidden.get(key))
            if score is not None:
                evidence[target] = {
                    "score": score,
                    "evidence_level": 2,
                    "evidence_kind": "HIDDEN_HOLDOUT",
                    "source": TRI_ORGAN,
                    "status": tri.get("status"),
                }

    thinking = _read_json(root, THINKING_HOLDOUT)
    if thinking and str(thinking.get("status", "")).startswith("PASS_"):
        score = _number(((thinking.get("selected_scores") or {}).get("fresh") or {}).get("accuracy"))
        if score is not None:
            evidence["THINKING"] = {
                "score": score,
                "evidence_level": 3,
                "evidence_kind": "FRESH_HOLDOUT",
                "source": THINKING_HOLDOUT,
                "status": thinking.get("status"),
            }

    intelligence = _read_json(root, INTELLIGENCE_HOLDOUT)
    if intelligence and str(intelligence.get("status", "")).startswith("PASS_"):
        score = _number(((intelligence.get("selected_scores") or {}).get("fresh") or {}).get("accuracy"))
        if score is not None:
            evidence["INTELLIGENCE"] = {
                "score": score,
                "evidence_level": 3,
                "evidence_kind": "FRESH_HOLDOUT",
                "source": INTELLIGENCE_HOLDOUT,
                "status": intelligence.get("status"),
            }

    memory = _read_json(root, MEMORY_HOLDOUT)
    if memory and str(memory.get("status", "")).startswith("PASS_"):
        score = _number(((memory.get("selected_scores") or {}).get("fresh") or {}).get("accuracy"))
        if score is not None:
            evidence["MEMORY_EXPERIENCE"] = {
                "score": score,
                "evidence_level": 3,
                "evidence_kind": "FRESH_HOLDOUT",
                "source": MEMORY_HOLDOUT,
                "status": memory.get("status"),
            }
    else:
        memory_index = _read_json(root, MEMORY_INDEX)
        if memory_index and str(memory_index.get("status", "")).startswith("PASS_"):
            evidence["MEMORY_EXPERIENCE"] = {
                "score": None,
                "evidence_level": 1,
                "evidence_kind": "STRUCTURAL_ONLY",
                "source": MEMORY_INDEX,
                "status": memory_index.get("status"),
                "memory_ref_count": memory_index.get("memory_ref_count"),
            }

    return evidence


def _priority(
    snapshot: dict[str, dict[str, Any]],
    audit: dict[str, Any],
    regression: dict[str, Any],
    evidence: dict[str, dict[str, Any]],
) -> tuple[str, str]:
    if audit["status"] != "PASS" or (audit.get("findings") or 0):
        return "INTEGRITY", "canonical audit is not clean"
    if regression["status"] != "PASS" or (regression.get("failures") or 0):
        return "VERIFICATION", "regression evidence is not clean"

    missing = [name for name, row in snapshot.items() if row["file_count"] == 0]
    if missing:
        return missing[0], "layer coverage is incomplete"

    unmeasured = [name for name in COGNITIVE_TARGETS if evidence[name]["score"] is None]
    if unmeasured:
        target = min(
            unmeasured,
            key=lambda name: (evidence[name]["evidence_level"], TARGET_ORDER[name]),
        )
        return target, "cognitive target lacks measured holdout evidence"

    fresh_saturated = all(
        evidence[name]["score"] is not None
        and evidence[name]["evidence_level"] >= 3
        and float(evidence[name]["score"]) >= 0.99
        for name in COGNITIVE_TARGETS
    )
    if fresh_saturated:
        return (
            "COGNITIVE_INTEGRATION",
            "all core cognitive targets have fresh holdout score >=0.99; move to cross-cognitive integration",
        )

    target = min(
        COGNITIVE_TARGETS,
        key=lambda name: (
            evidence[name]["score"],
            evidence[name]["evidence_level"],
            TARGET_ORDER[name],
        ),
    )
    return (
        target,
        f"lowest measured cognitive evidence score={evidence[target]['score']:.6f}; "
        f"kind={evidence[target]['evidence_kind']}",
    )


def build_plan(root: Path = ROOT) -> dict[str, Any]:
    root = Path(root).resolve()
    snapshot = _layer_snapshot(root)
    audit = _load_status(root, "audits/yado-full-kernel-audit-v1-report.json")
    regression = _load_status(root, "audits/yado-full-regression-v1-report.json")
    evidence = _cognitive_evidence(root)
    selected_target, selection_reason = _priority(snapshot, audit, regression, evidence)
    all_layer_coverage = all(row["file_count"] > 0 for row in snapshot.values())

    stages = [
        {
            "stage": index,
            "layer": layer,
            "action": action,
            "gate": (
                "compile" if layer == "CODE" else
                "canonical_guard" if layer == "LAYERS" else
                "full_regression" if layer == "MODULES" else
                "provenance_replay" if layer == "MEMORY_EXPERIENCE" else
                "fresh_holdout"
            ),
        }
        for index, (layer, action) in enumerate(SEQUENCE, start=1)
    ]

    return {
        "schema": "yado.autonomous_deep_development.v1",
        "selector_version": "EVIDENCE_AWARE_DEFICIT_SELECTOR_V2",
        "status": (
            "PASS_SHADOW_AUTONOMOUS_DEEP_DEVELOPMENT_PLAN_V1"
            if all_layer_coverage else
            "WITHHOLD_AUTONOMOUS_DEEP_DEVELOPMENT_LAYER_COVERAGE_V1"
        ),
        "mode": "EVENT_DRIVEN_SHADOW",
        "selected_target": selected_target,
        "selected_action": ACTION_BY_TARGET[selected_target],
        "selection_reason": selection_reason,
        "development_sequence": stages,
        "layers": snapshot,
        "cognitive_evidence": evidence,
        "preexisting_evidence": {
            "full_kernel_audit": audit,
            "full_regression": regression,
        },
        "boundaries": {
            "canonical_mutation": False,
            "automatic_main_mutation": False,
            "external_writes": False,
            "credentials_used": False,
            "downloaded_code_executed": False,
            "self_weight_update": False,
            "consciousness_claimed": False,
        },
        "next_gate": "native candidate -> compile -> isolated execution -> full audit -> successor regression -> 20 endogenous cycles",
    }


def main() -> int:
    plan = build_plan()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(plan, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(plan, indent=2, sort_keys=True))
    return 0 if plan["status"].startswith("PASS_") else 1


if __name__ == "__main__":
    raise SystemExit(main())
