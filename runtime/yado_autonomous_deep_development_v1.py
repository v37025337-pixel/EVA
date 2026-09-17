from __future__ import annotations

"""Bounded controller for autonomous deep development across YADO layers."""

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
ACTION_BY_TARGET = {
    "INTEGRITY": "reconcile canonical identity, ancestry, and layer bindings",
    "VERIFICATION": "re-run fresh compile, regression, audit, and counterfactual gates",
    "CODE": "generate and execute a bounded native source candidate",
    "LAYERS": "repair cross-layer bindings and re-check architecture receipts",
    "MODULES": "test module connectivity and isolate duplicate or orphan behavior",
    "MEMORY_EXPERIENCE": "consolidate verified experience and preserve provenance",
    "LOGIC": "derive and test a new relational/causal logic holdout",
    "THINKING": "derive and test a contextual reasoning holdout",
    "INTELLIGENCE": "derive and test a capability-transfer holdout",
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


def _digest(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _load_status(root: Path, relative: str) -> dict[str, Any]:
    path = root / relative
    if not path.exists():
        return {"status": "MISSING", "path": relative}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {"status": "UNREADABLE", "path": relative, "error": type(exc).__name__}
    return {
        "status": value.get("status", "UNKNOWN"),
        "path": relative,
        "findings": len(value.get("findings", [])) if isinstance(value, dict) else None,
        "failures": len(value.get("failures", [])) if isinstance(value, dict) else None,
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


def _priority(snapshot: dict[str, dict[str, Any]], audit: dict[str, Any],
              regression: dict[str, Any]) -> tuple[str, str]:
    if audit["status"] != "PASS" or (audit.get("findings") or 0):
        return "INTEGRITY", "canonical audit is not clean"
    if regression["status"] != "PASS" or (regression.get("failures") or 0):
        return "VERIFICATION", "regression evidence is not clean"
    missing = [name for name, row in snapshot.items() if row["file_count"] == 0]
    if missing:
        return missing[0], "layer coverage is incomplete"
    weakest = min(COGNITIVE_TARGETS, key=lambda name: (snapshot[name]["file_count"], name))
    return weakest, "weakest covered cognitive layer selected for the next holdout"


def build_plan(root: Path = ROOT) -> dict[str, Any]:
    root = Path(root).resolve()
    snapshot = _layer_snapshot(root)
    audit = _load_status(root, "audits/yado-full-kernel-audit-v1-report.json")
    regression = _load_status(root, "audits/yado-full-regression-v1-report.json")
    selected_target, selection_reason = _priority(snapshot, audit, regression)
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
