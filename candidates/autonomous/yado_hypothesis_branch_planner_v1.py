from __future__ import annotations

HYPOTHESIS_TEMPLATES = (
    {
        "id": "REUSE_VERIFIED_PATTERN",
        "risk": 1,
        "required_evidence": ("prior_success", "same_layer"),
        "action": "adapt a previously verified mechanism without changing its safety boundary",
    },
    {
        "id": "CONTROLLED_NEW_EXPERIMENT",
        "risk": 2,
        "required_evidence": ("fresh_test", "rollback"),
        "action": "create a narrow candidate and compare it against a regression baseline",
    },
    {
        "id": "DEFER_AND_COLLECT_DATA",
        "risk": 0,
        "required_evidence": ("missing_evidence",),
        "action": "withhold mutation and collect the missing evidence",
    },
)

def generate_hypotheses(deficit: str, evidence: set[str]) -> list[dict]:
    if not str(deficit).strip():
        return []
    result = []
    for template in HYPOTHESIS_TEMPLATES:
        covered = sorted(set(template["required_evidence"]) & set(evidence))
        result.append({
            "id": template["id"],
            "deficit": str(deficit),
            "action": template["action"],
            "risk": template["risk"],
            "required_evidence": template["required_evidence"],
            "covered_evidence": tuple(covered),
            "coverage": len(covered),
        })
    return result

def select_hypothesis(hypotheses: list[dict]) -> dict:
    ranked = []
    for item in hypotheses:
        score = item["coverage"] * 10 - item["risk"]
        ranked.append((score, item["coverage"], -item["risk"], item["id"], item))
    ranked.sort(key=lambda row: (-row[0], -row[1], -row[2], row[3]))
    if not ranked or ranked[0][1] == 0:
        return {"status": "WITHHOLD", "reason": "no_evidence_covered"}
    selected = dict(ranked[0][4])
    selected.update({"status": "SELECTED", "score": ranked[0][0]})
    return selected

def plan(deficit: str, evidence: set[str]) -> dict:
    hypotheses = generate_hypotheses(deficit, evidence)
    selected = select_hypothesis(hypotheses)
    return {
        "schema": "yado.hypothesis_branch_planner.v1",
        "status": "PASS_SHADOW" if selected["status"] == "SELECTED" else "WITHHOLD",
        "hypothesis_count": len(hypotheses),
        "selected": selected,
        "canonical_active": False,
        "external_code_executed": False,
    }

def component() -> dict:
    return {
        "schema": "yado.hypothesis_branch_planner.v1",
        "template_count": len(HYPOTHESIS_TEMPLATES),
        "canonical_active": False,
        "external_code_executed": False,
    }
