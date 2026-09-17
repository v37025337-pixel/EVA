from __future__ import annotations

EXPERIENCE = {
    "schema": "yado.multidomain_learning_cycle.v1",
    "domains": ("programming_ast", "web_protocols", "repository_api", "web_architecture"),
    "records": (
        {
            "source_id": "PYTHON_AST",
            "domain": "programming_ast",
            "tags": ("source", "ast", "parse", "compile", "fields", "code"),
            "claims": ("parse source into AST", "compile AST into code object", "validate fields before compile"),
        },
        {
            "source_id": "MDN_HTTP",
            "domain": "web_protocols",
            "tags": ("http", "request", "response", "resource", "protocol", "web"),
            "claims": ("fetch resources", "request response interaction", "web communication constraints"),
        },
        {
            "source_id": "GITHUB_REST",
            "domain": "repository_api",
            "tags": ("api", "repository", "endpoint", "resource", "operation", "provenance"),
            "claims": ("explicit resource endpoints", "repository metadata", "operation traceability"),
        },
        {
            "source_id": "W3C_WEBARCH",
            "domain": "web_architecture",
            "tags": ("web", "resource", "identity", "interaction", "interoperability", "architecture"),
            "claims": ("resource identification", "resource interaction", "interoperability constraints"),
        },
    ),
}

def _tokens(value: str) -> frozenset[str]:
    return frozenset(token for token in str(value).lower().replace("-", " ").split() if token)

def rank_evidence(query: str, limit: int = 8) -> list[dict]:
    wanted = _tokens(query)
    ranked = []
    for record in EXPERIENCE["records"]:
        searchable = _tokens(" ".join(record["tags"] + record["claims"]))
        score = len(wanted & searchable)
        if score:
            ranked.append((score, record["domain"], record["source_id"], record))
    ranked.sort(key=lambda item: (-item[0], item[1], item[2]))
    bounded = max(1, min(int(limit), len(ranked) or 1))
    return [
        {"score": score, "source_id": source_id, "domain": domain, "claims": record["claims"]}
        for score, domain, source_id, record in ranked[:bounded]
    ]

def cross_domain_bridges() -> list[dict]:
    bridges = []
    records = EXPERIENCE["records"]
    for index, left in enumerate(records):
        for right in records[index + 1:]:
            overlap = sorted(set(left["tags"]) & set(right["tags"]))
            if overlap:
                bridges.append({
                    "left": left["source_id"],
                    "right": right["source_id"],
                    "shared_tags": tuple(overlap),
                })
    return sorted(bridges, key=lambda item: (item["left"], item["right"]))

def component() -> dict:
    return {
        "schema": "yado.multidomain_evidence_triage.v1",
        "domain_count": len(EXPERIENCE["domains"]),
        "source_count": len(EXPERIENCE["records"]),
        "cross_domain_bridge_count": len(cross_domain_bridges()),
        "external_code_executed": False,
        "canonical_active": False,
    }
