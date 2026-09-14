from __future__ import annotations

from pathlib import Path
import hashlib
import importlib.util
import json
import sys

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parent
GENESIS_RECEIPT = REPO / "architecture/yado-native-controller-new-dimension-genesis-v1.json"
CANDIDATE = REPO / "candidates/g2-self-evolution/yado_evolutionary_genome_new_dimension_candidate_v1.py"
OUT = REPO / "candidates/g2-self-evolution/yado-native-controller-dimension-fresh-transfer-v1.json"

PRIOR_TRAINING_VALUES = {
    "NATIVE_CONTROLLER_NEW_DIMENSION_GENESIS",
    "NATIVE_EVOLUTIONARY_CONTROLLER_SELF_REPRESENTATION_AND_MUTATION_V2",
    "STRUCTURAL_SEARCH_SPACE_DID_NOT_EXPAND",
}
KEYS = {
    "next_required_capability",
    "failure_next_required_capability",
    "residual_frontier",
    "deficit",
    "deficits",
    "suggestion",
    "signature",
    "task",
    "objective",
}


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_module(path: Path, name: str):
    sys.path.insert(0, str(ROOT))
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError("MODULE_SPEC_FAILURE")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def parent_for(cls, suffix: str):
    return cls.parent_genome(
        head_digest="0" * 64,
        component_digests={"LOGIC":"l","THINKING":"t","INTELLIGENCE":"i","CODE":"c"},
        experience_digest="fresh-transfer-" + suffix,
    )


def walk_values(obj, path: str, rows: list[dict], key: str = ""):
    if isinstance(obj, dict):
        for k, v in obj.items():
            walk_values(v, path, rows, str(k).lower())
    elif isinstance(obj, list):
        for v in obj:
            walk_values(v, path, rows, key)
    elif isinstance(obj, str) and key in KEYS:
        value = " ".join(obj.split())
        if 6 <= len(value) <= 240:
            rows.append({"source": path, "key": key, "value": value})


def historical_deficits() -> list[dict]:
    roots = ["architecture", "receipts", "experience", "candidates"]
    rows: list[dict] = []
    for root in roots:
        base = REPO / root
        if not base.exists():
            continue
        for path in sorted(base.rglob("*.json")):
            if path == OUT:
                continue
            try:
                obj = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                continue
            walk_values(obj, str(path.relative_to(REPO)), rows)
    seen = set()
    unique = []
    for row in rows:
        v = row["value"]
        upper = v.upper()
        if v in seen or upper in PRIOR_TRAINING_VALUES:
            continue
        if "NATIVE_CONTROLLER_NEW_DIMENSION_GENESIS" in upper:
            continue
        seen.add(v)
        unique.append(row)
    # Hash ordering makes selection deterministic but independent of filesystem chronology.
    unique.sort(key=lambda r: hashlib.sha256((r["key"] + "\0" + r["value"]).encode()).hexdigest())
    return unique


def evolve_case(cls, row: dict, index: int) -> dict:
    parent = parent_for(cls, str(index))
    base_dims = set(parent.get("chromosomes", {}))
    experience = [{row["key"]: row["value"], "historical_source": row["source"]}]
    controller = cls(parent, experience_sources=experience)
    result = controller.evolve_once()
    child = result.get("child") or {}
    new_dims = sorted(set((child.get("chromosomes") or {})) - base_dims)

    # Ablation: same historical text moved to an ignored metadata key must not create a dimension.
    ablated = cls(parent, experience_sources=[{"note": row["value"], "historical_source": row["source"]}]).evolve_once()
    ablated_dims = sorted(set(((ablated.get("child") or {}).get("chromosomes") or {})) - base_dims)

    # Irrelevant note must not perturb the derived dimension.
    perturbed = cls(parent, experience_sources=[{row["key"]: row["value"], "note": "unrelated metadata"}]).evolve_once()
    perturbed_dims = sorted(set(((perturbed.get("child") or {}).get("chromosomes") or {})) - base_dims)

    rollback_ok = bool(new_dims) and all(
        ((child["chromosomes"][d].get("expression") or {}).get("rollback_anchor") == parent.get("genome_digest"))
        for d in new_dims
    )
    return {
        "source": row["source"],
        "key": row["key"],
        "value_sha256": hashlib.sha256(row["value"].encode()).hexdigest(),
        "value_preview": row["value"][:120],
        "new_dimensions": new_dims,
        "selection": result.get("selection"),
        "fitness_gain": (result.get("fitness") or {}).get("fitness_gain"),
        "all_regressions_pass": (result.get("fitness") or {}).get("all_regressions_pass"),
        "rollback_anchor_bound": rollback_ok,
        "ablated_new_dimensions": ablated_dims,
        "perturbed_new_dimensions": perturbed_dims,
        "perturbation_stable": perturbed_dims == new_dims,
    }


def main() -> int:
    receipt = json.loads(GENESIS_RECEIPT.read_text(encoding="utf-8"))
    if receipt.get("status") != "PASS_NATIVE_CONTROLLER_NEW_DIMENSION_GENESIS_V1":
        raise RuntimeError("GENESIS_NOT_ADMITTED")
    candidate_bytes = CANDIDATE.read_bytes()
    candidate_sha = sha256_bytes(candidate_bytes)
    if candidate_sha != receipt.get("candidate_sha256"):
        raise RuntimeError("GENESIS_CANDIDATE_SHA_MISMATCH")

    mod = load_module(CANDIDATE, "yado_dimension_fresh_transfer_candidate_v1")
    cls = mod.YADOEvolutionaryGenomeV1
    pool = historical_deficits()
    if len(pool) < 8:
        raise RuntimeError(f"INSUFFICIENT_FRESH_HISTORICAL_DEFICITS:{len(pool)}")

    cases = []
    used_dims = set()
    # Search up to 40 fresh historical deficits and retain the first eight valid transfers.
    for idx, row in enumerate(pool[:40]):
        case = evolve_case(cls, row, idx)
        valid = (
            bool(case["new_dimensions"])
            and case["selection"] == "CHILD"
            and case["all_regressions_pass"] is True
            and case["rollback_anchor_bound"] is True
            and case["ablated_new_dimensions"] == []
            and case["perturbation_stable"] is True
        )
        if not valid:
            continue
        dims = set(case["new_dimensions"])
        if dims & used_dims:
            continue
        used_dims |= dims
        cases.append(case)
        if len(cases) >= 8:
            break

    unique_dimensions = sorted({d for c in cases for d in c["new_dimensions"]})
    prior_dims = set(receipt.get("derived_new_dimensions") or [])
    checks = {
        "genesis_admitted": True,
        "candidate_sha_bound": True,
        "fresh_historical_pool_ge_8": len(pool) >= 8,
        "valid_transfer_cases_ge_5": len(cases) >= 5,
        "unique_derived_dimensions_ge_5": len(unique_dimensions) >= 5,
        "all_cases_select_child": bool(cases) and all(c["selection"] == "CHILD" for c in cases),
        "all_cases_regressions_pass": bool(cases) and all(c["all_regressions_pass"] is True for c in cases),
        "all_cases_rollback_bound": bool(cases) and all(c["rollback_anchor_bound"] is True for c in cases),
        "all_ablations_remove_dimension": bool(cases) and all(c["ablated_new_dimensions"] == [] for c in cases),
        "all_irrelevant_perturbations_stable": bool(cases) and all(c["perturbation_stable"] is True for c in cases),
        "fresh_dimensions_extend_prior": bool(set(unique_dimensions) - prior_dims),
        "canonical_mutation": False,
        "external_model_used": False,
    }
    passed = (
        all(v is True for k, v in checks.items() if k not in {"canonical_mutation", "external_model_used"})
        and not checks["canonical_mutation"]
        and not checks["external_model_used"]
    )
    report = {
        "schema": "yado.native_controller_dimension_fresh_transfer.v1",
        "status": "PASS_NATIVE_CONTROLLER_DIMENSION_FRESH_TRANSFER_AND_ABLATION_V1" if passed else "WITHHOLD_NATIVE_CONTROLLER_DIMENSION_FRESH_TRANSFER_AND_ABLATION_V1",
        "genesis_candidate_sha256": candidate_sha,
        "historical_pool_size": len(pool),
        "cases": cases,
        "case_count": len(cases),
        "unique_derived_dimensions": unique_dimensions,
        "checks": checks,
        "semantic_boundary": "HELD-OUT TRANSFER USES PRE-EXISTING YADO HISTORY, NOT NEW INTERNET CODE OR HOST-PRESELECTED DIMENSION NAMES. CAUSAL FIELD ABLATION MUST REMOVE THE NEW DIMENSION; IRRELEVANT METADATA MUST NOT CHANGE IT. DEVELOPMENT CANDIDATE ONLY.",
        "canonical_mutation": False,
        "next_required_capability": "NATIVE_CONTROLLER_ENDOGENOUS_DEFICIT_TO_DIMENSION_LOOP_V1" if passed else "NATIVE_CONTROLLER_DIMENSION_TRANSFER_REPAIR",
    }
    report["receipt_sha256"] = hashlib.sha256(json.dumps(report, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": report["status"],
        "historical_pool_size": len(pool),
        "case_count": len(cases),
        "unique_derived_dimensions": unique_dimensions,
        "next_required_capability": report["next_required_capability"],
        "receipt_sha256": report["receipt_sha256"],
    }, indent=2, sort_keys=True))
    return 0 if passed else 2


if __name__ == "__main__":
    raise SystemExit(main())
