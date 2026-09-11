from __future__ import annotations

import ast
import hashlib
import json
import sys
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / "runtime"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runtime.yado_g2_openapi_readonly_executor_v1 import G2OpenAPIReadOnlyExecutorV1


@dataclass(frozen=True)
class Layer:
    name: str
    evidence_files: tuple[str, ...]
    capability: str


LAYERS = (
    Layer("causal_memory", ("successor/kernel.py",), "persistent causal history"),
    Layer("self_model", ("successor/cognitive.py",), "empirical self-model and prediction error"),
    Layer("workspace", ("runtime/yado_unified_core_v1.py",), "bounded cognitive workspace"),
    Layer("logic", ("runtime/yado_unified_core_v1.py",), "relational/causal logic"),
    Layer("thinking", ("runtime/yado_unified_core_v1.py",), "multi-step causal processing"),
    Layer("intelligence", ("runtime/yado_unified_core_v1.py",), "selection and transfer"),
    Layer("source_rewrite", ("runtime/yado_g2_autonomous_self_rewrite_v1.py",), "shadow source rewrite"),
    Layer("real_network", ("runtime/yado_g2_openapi_readonly_executor_v1.py",), "bounded real read-only network"),
)

SAFE_CONTRACTS = (
    {
        "id": "github_repo_metadata",
        "host": "api.github.com",
        "base": "https://api.github.com",
        "path": "/repos/v37025337-pixel/EVA",
        "keywords": {"repository", "identity", "default", "branch", "metadata"},
    },
    {
        "id": "github_main_head",
        "host": "api.github.com",
        "base": "https://api.github.com",
        "path": "/repos/v37025337-pixel/EVA/commits/main",
        "keywords": {"current", "main", "head", "commit", "canonical", "fresh"},
    },
)


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def inspect_layers() -> list[dict[str, Any]]:
    rows = []
    for layer in LAYERS:
        present = [p for p in layer.evidence_files if (ROOT / p).exists()]
        rows.append({
            **asdict(layer),
            "evidence_files": list(layer.evidence_files),
            "present_files": present,
            "available": len(present) == len(layer.evidence_files),
        })
    return rows


def derive_deficit(layers: list[dict[str, Any]]) -> dict[str, Any]:
    missing = [x["name"] for x in layers if not x["available"]]
    # A real-connect capability now exists, but a fresh external fact has not yet
    # been bound into an evolution receipt. That is the first causal gap this loop closes.
    if "real_network" not in missing:
        return {
            "code": "FRESH_EXTERNAL_EVIDENCE_NOT_BOUND_TO_EVOLUTION_STATE",
            "target_layer": "real_network",
            "need": "current fresh canonical main head commit evidence",
            "reason": "self-rewrite decisions should be grounded in fresh repository state, not stale assumptions",
        }
    return {
        "code": "LAYER_CAPABILITY_MISSING",
        "target_layer": missing[0] if missing else "unknown",
        "need": "repository identity and capability evidence",
        "reason": "required layer evidence is absent",
    }


def choose_contract(deficit: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    tokens = set(str(deficit).lower().replace("_", " ").split())
    ranked = []
    for c in SAFE_CONTRACTS:
        score = len(tokens & c["keywords"])
        ranked.append({"id": c["id"], "score": score})
    ranked.sort(key=lambda x: (-x["score"], x["id"]))
    winner_id = ranked[0]["id"]
    winner = next(c for c in SAFE_CONTRACTS if c["id"] == winner_id)
    return winner, ranked


def execute_research(contract: dict[str, Any]) -> dict[str, Any]:
    executor = G2OpenAPIReadOnlyExecutorV1(
        allowed_hosts={contract["host"]},
        max_bytes=256 * 1024,
        timeout=10.0,
    )
    plan = {
        "action": "ALLOW",
        "read_only_candidate": True,
        "method": "GET",
        "network_execute": False,
        "path": contract["path"],
        "required_slots": {"query": []},
        "contract_id": "YADO-EVOLUTION-LOOP-V1-" + contract["id"].upper(),
    }
    return executor.execute(plan, contract["base"])


def extract_fact(contract_id: str, result: dict[str, Any]) -> dict[str, Any]:
    body = json.loads(result.get("body_text") or "{}")
    if contract_id == "github_main_head":
        return {
            "kind": "repository_main_head",
            "sha": body.get("sha"),
            "message": ((body.get("commit") or {}).get("message") or "")[:300],
        }
    return {
        "kind": "repository_metadata",
        "full_name": body.get("full_name"),
        "default_branch": body.get("default_branch"),
    }


def generate_shadow_capability(deficit: dict[str, Any], fact: dict[str, Any]) -> tuple[str, str]:
    # This source is generated from the loop's selected deficit and observed fact.
    # It is intentionally a small, safe evidence-binding capability; it does not mutate main.
    payload = json.dumps({"deficit": deficit["code"], "fact": fact}, sort_keys=True)
    src = (
        "from __future__ import annotations\n\n"
        f"BOUND_EVIDENCE = {payload!r}\n\n"
        "def evidence_digest() -> str:\n"
        "    import hashlib\n"
        "    return hashlib.sha256(BOUND_EVIDENCE.encode('utf-8')).hexdigest()\n"
    )
    tree = ast.parse(src)
    forbidden = (ast.Exec,) if hasattr(ast, "Exec") else tuple()
    if forbidden and any(isinstance(n, forbidden) for n in ast.walk(tree)):
        raise RuntimeError("FORBIDDEN_AST")
    compile(tree, "<yado-evolution-shadow-candidate>", "exec")
    return src, sha256_text(src)


def main() -> int:
    layers = inspect_layers()
    deficit = derive_deficit(layers)
    contract, ranking = choose_contract(deficit)
    result = execute_research(contract)
    fact = extract_fact(contract["id"], result)

    network_ok = (
        result.get("network_executed") is True
        and result.get("read_only_enforced") is True
        and result.get("credentials_used") is False
        and result.get("status") == 200
    )
    fact_ok = bool(fact.get("sha") or fact.get("full_name"))

    candidate_src = ""
    candidate_sha = None
    candidate_path = None
    compile_ok = False
    if network_ok and fact_ok:
        candidate_src, candidate_sha = generate_shadow_capability(deficit, fact)
        candidate_path = ROOT / "candidates" / "g2-self-evolution" / "yado_evolution_bound_evidence_candidate_v1.py"
        candidate_path.parent.mkdir(parents=True, exist_ok=True)
        candidate_path.write_text(candidate_src, encoding="utf-8")
        compile(candidate_src, str(candidate_path), "exec")
        compile_ok = True

    accepted_shadow = bool(network_ok and fact_ok and compile_ok)
    status = "PASS_SHADOW_YADO_EVOLUTION_LOOP_V1" if accepted_shadow else "WITHHOLD_YADO_EVOLUTION_LOOP_V1"
    receipt = {
        "schema": "yado.evolution_loop.v1",
        "status": status,
        "causal_chain": [
            "inspect_layers",
            "derive_deficit",
            "select_safe_external_contract",
            "execute_real_read_only_research",
            "bind_observed_fact",
            "generate_shadow_capability",
            "compile_candidate",
            "accept_or_withhold",
        ],
        "layers": layers,
        "self_selected_deficit": deficit,
        "contract_ranking": ranking,
        "selected_contract": {k: v for k, v in contract.items() if k != "keywords"},
        "network": {
            "network_executed": result.get("network_executed"),
            "read_only_enforced": result.get("read_only_enforced"),
            "credentials_used": result.get("credentials_used"),
            "http_status": result.get("status"),
            "body_sha256": result.get("body_sha256"),
            "execution_digest": result.get("execution_digest"),
        },
        "observed_fact": fact,
        "shadow_candidate": {
            "path": str(candidate_path.relative_to(ROOT)) if candidate_path else None,
            "sha256": candidate_sha,
            "compile_pass": compile_ok,
        },
        "canonical_mutation": False,
        "external_coding_model_used": False,
        "limitations": [
            "deficit derivation and safe-contract inventory are bounded by this V1 scaffold",
            "generated candidate is evidence-binding code, not open-ended architecture invention",
            "PASS does not establish subjective consciousness",
        ],
    }
    out = ROOT / "receipts" / "yado-evolution-loop-v1.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0 if accepted_shadow else 1


if __name__ == "__main__":
    raise SystemExit(main())
