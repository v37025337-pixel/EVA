from __future__ import annotations

REQUIRED_LINKS = ("observation", "deficit", "hypothesis", "mutation", "verification")

def validate_chain(chain: dict) -> dict:
    errors = []
    for link in REQUIRED_LINKS:
        if not chain.get(link):
            errors.append(f"missing:{link}")
    if chain.get("verification") and "WITHHOLD" not in chain["verification"] and "PASS" not in chain["verification"]:
        errors.append("verification_outcome_missing")
    if chain.get("mutation") and chain.get("deficit") and chain["mutation"].startswith("UNRELATED_"):
        errors.append("mutation_not_linked_to_deficit")
    return {
        "schema": "yado.causal_learning_chain.v1",
        "status": "PASS" if not errors else "WITHHOLD",
        "errors": tuple(errors),
        "link_count": sum(bool(chain.get(link)) for link in REQUIRED_LINKS),
        "canonical_active": False,
        "external_code_executed": False,
    }

def component() -> dict:
    return {
        "schema": "yado.causal_learning_chain.v1",
        "required_links": REQUIRED_LINKS,
        "canonical_active": False,
        "external_code_executed": False,
    }
