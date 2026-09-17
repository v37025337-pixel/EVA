from __future__ import annotations

LAYER_ORDER = (
    "MEMORY_EXPERIENCE",
    "LOGIC",
    "THINKING",
    "INTELLIGENCE",
    "SELF_MODEL",
    "GENERATION",
    "VERIFICATION",
)
STATUS_RANK = {"FAIL": 4, "WITHHOLD": 3, "PARTIAL": 2, "PASS_SHADOW": 1}
MUTATION_MAP = {
    "THINKING": "HYPOTHESIS_BRANCH_PLANNER_V1",
    "INTELLIGENCE": "EVIDENCE_GENERALIZATION_REVIEW_V1",
    "GENERATION": "NATIVE_SOURCE_EMISSION_RETRY_V1",
    "SELF_MODEL": "RUNTIME_INTROSPECTION_RECEIPT_V1",
    "MEMORY_EXPERIENCE": "EXPERIENCE_RUNTIME_REGISTRATION_V1",
    "LOGIC": "CONTRADICTION_RESOLUTION_REVIEW_V1",
    "VERIFICATION": "REPOSITORY_WORKFLOW_EVIDENCE_V1",
}

def select_deficit(layers: list[dict]) -> dict:
    if not layers:
        return {"status": "WITHHOLD", "reason": "no_layer_observations"}
    normalized = []
    for item in layers:
        name = item.get("name", "UNKNOWN")
        status = item.get("status", "WITHHOLD")
        normalized.append({
            "layer": name,
            "status": status,
            "rank": STATUS_RANK.get(status, 3),
            "deficit": item.get("deficit", "unspecified"),
        })
    normalized.sort(key=lambda item: (-item["rank"], LAYER_ORDER.index(item["layer"]) if item["layer"] in LAYER_ORDER else 99, item["layer"]))
    chosen = normalized[0]
    return {
        "status": "SELECTED",
        "layer": chosen["layer"],
        "deficit": chosen["deficit"],
        "target_capability": MUTATION_MAP.get(chosen["layer"]),
    }

def run_evolution(layers: list[dict], *, compile_pass: bool, regression_pass: bool, audit_pass: bool) -> dict:
    missing = sorted(set(LAYER_ORDER) - {item.get("name") for item in layers})
    if missing:
        return {"schema": "yado.full_layer_evolution_controller.v1", "status": "WITHHOLD", "reason": "missing_layers", "missing_layers": tuple(missing), "canonical_active": False}
    selection = select_deficit(layers)
    gates = {"compile": bool(compile_pass), "regression": bool(regression_pass), "audit": bool(audit_pass)}
    status = "SHADOW_APPLIED" if selection["status"] == "SELECTED" and all(gates.values()) else "WITHHOLD"
    return {
        "schema": "yado.full_layer_evolution_controller.v1",
        "status": status,
        "selected_deficit": selection,
        "gates": gates,
        "rollback_supported": True,
        "canonical_active": False,
        "external_code_executed": False,
    }

def component() -> dict:
    return {
        "schema": "yado.full_layer_evolution_controller.v1",
        "layer_count": len(LAYER_ORDER),
        "mutation_targets": tuple(sorted(MUTATION_MAP)),
        "canonical_active": False,
        "external_code_executed": False,
    }
