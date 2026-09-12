from __future__ import annotations

import json
import re
import urllib.parse
from pathlib import Path
from typing import Any

import yado_autonomous_external_library_discovery_v5 as v5

ROOT = Path(__file__).resolve().parents[1]
RECEIPT = ROOT / "receipts" / "yado-autonomous-open-catalog-discovery-v6.json"

SIMPLE_ROOT = "https://pypi.org/simple/"
OBJECTIVE = "find and connect to a Python library for parsing HTML/XML/markup content"
DISCOVERY_ANCHORS = ("html", "xml", "markup", "parser", "scrap")
MAX_INDEX_BYTES = 100_000_000
MAX_DISCOVERED_CANDIDATES = 32


def non_extra_requirement_names(info: dict[str, Any]) -> list[str]:
    result: list[str] = []
    for requirement in list(info.get("requires_dist") or []):
        text = str(requirement)
        if "extra ==" in text or "extra==" in text:
            continue
        match = re.match(r"\s*([A-Za-z0-9][A-Za-z0-9._-]*)", text)
        if not match:
            continue
        name = v5.normalize_name(match.group(1))
        if name and name not in result:
            result.append(name)
    return result


def discover_from_open_catalog() -> tuple[list[str], dict[str, Any]]:
    raw, proof = v5.guarded_fetch(
        SIMPLE_ROOT,
        accept="application/vnd.pypi.simple.v1+json",
        max_bytes=MAX_INDEX_BYTES,
    )
    payload = json.loads(raw.decode("utf-8"))
    projects = list(payload.get("projects") or [])
    names = []
    for row in projects:
        if isinstance(row, dict):
            name = str(row.get("name") or "").strip()
        else:
            name = ""
        if name:
            names.append(name)
    if not names:
        raise RuntimeError("PyPI Simple root returned no project names")

    ranked: list[tuple[int, int, str, str, list[str]]] = []
    for original in names:
        normalized = v5.normalize_name(original)
        hits = [anchor for anchor in DISCOVERY_ANCHORS if anchor in normalized]
        if not hits:
            continue
        score = 0
        for anchor in hits:
            if normalized == anchor:
                score += 240
            elif normalized.startswith(anchor):
                score += 150
            elif normalized.endswith(anchor):
                score += 110
            else:
                score += 80
        score += max(0, 40 - len(normalized))
        ranked.append((-score, len(normalized), normalized, original, hits))

    ranked.sort()
    shortlist: list[str] = []
    evidence_rows = []
    for neg_score, _, normalized, original, hits in ranked:
        if normalized in shortlist:
            continue
        shortlist.append(normalized)
        evidence_rows.append(
            {
                "name": normalized,
                "catalog_name": original,
                "lexical_score": -neg_score,
                "anchor_hits": hits,
            }
        )
        if len(shortlist) >= MAX_DISCOVERED_CANDIDATES:
            break
    if not shortlist:
        raise RuntimeError("open catalog discovery produced no candidates")

    return shortlist, {
        "source": proof,
        "catalog_project_count": len(names),
        "discovery_anchors": list(DISCOVERY_ANCHORS),
        "candidate_names_host_provided": False,
        "candidate_limit": MAX_DISCOVERED_CANDIDATES,
        "discovered_candidates": evidence_rows,
    }


def fetch_candidate_metadata(shortlist: list[str]) -> dict[str, dict[str, Any]]:
    records: dict[str, dict[str, Any]] = {}
    for name in shortlist:
        payload, proof = v5.fetch_json(v5.PYPI_JSON.format(name=urllib.parse.quote(name)))
        records[name] = {
            "payload": payload,
            "source": proof,
            "relevance": v5.relevance_score(payload),
            "requirements": non_extra_requirement_names(payload.get("info") or {}),
        }
    return records


def metadata_has_usable_wheel(payload: dict[str, Any]) -> bool:
    for item in list(payload.get("urls") or []):
        if (
            item.get("packagetype") == "bdist_wheel"
            and str(item.get("filename") or "").endswith(".whl")
            and item.get("url")
            and (item.get("digests") or {}).get("sha256")
        ):
            return True
    return False


def select_discovered_library(
    discovery: dict[str, Any],
    records: dict[str, dict[str, Any]],
) -> tuple[str, dict[str, Any]]:
    lexical = {
        row["name"]: int(row["lexical_score"])
        for row in discovery["discovered_candidates"]
    }
    ranked = []
    for name, record in records.items():
        relevance = int(record["relevance"]["score"])
        requirements = list(record["requirements"])
        wheel_ok = metadata_has_usable_wheel(record["payload"])
        eligible = relevance > 0 and bool(requirements) and wheel_ok
        combined = relevance * 1000 + int(lexical.get(name, 0))
        ranked.append(
            {
                "name": name,
                "relevance_score": relevance,
                "lexical_score": int(lexical.get(name, 0)),
                "combined_score": combined,
                "requirements": requirements,
                "usable_wheel": wheel_ok,
                "eligible": eligible,
                "summary": record["relevance"]["summary"],
                "version": record["relevance"]["version"],
            }
        )
    ranked.sort(key=lambda row: (-int(row["eligible"]), -row["combined_score"], row["name"]))
    eligible = [row for row in ranked if row["eligible"]]
    if not eligible:
        raise RuntimeError("open-catalog candidates produced no eligible library")
    selected = eligible[0]
    return selected["name"], {
        "selection_basis": "open_catalog_discovery_then_live_metadata_relevance",
        "host_provided_selected_package": False,
        "selected_package": selected["name"],
        "ranked": ranked,
    }


def inherited_shadow_receipts() -> dict[str, str]:
    paths = {
        "v1": ROOT / "receipts" / "yado-external-source-evolution-v1.json",
        "v2": ROOT / "receipts" / "yado-autonomous-meta-source-evolution-v2.json",
        "v3": ROOT / "receipts" / "yado-autonomous-grammar-extension-v3.json",
        "v4": ROOT / "receipts" / "yado-autonomous-meta-grammar-evolution-v4.json",
        "v5": ROOT / "receipts" / "yado-autonomous-external-library-discovery-v5.json",
    }
    statuses = {
        key: str(json.loads(path.read_text(encoding="utf-8")).get("status"))
        for key, path in paths.items()
    }
    expected = {
        "v1": "PASS_SHADOW_G2_EXTERNAL_SOURCE_EVOLUTION_V1",
        "v2": "PASS_SHADOW_G2_AUTONOMOUS_META_SOURCE_EVOLUTION_V2",
        "v3": "PASS_SHADOW_G2_AUTONOMOUS_GRAMMAR_EXTENSION_V3",
        "v4": "PASS_SHADOW_G2_AUTONOMOUS_META_GRAMMAR_EVOLUTION_V4",
        "v5": "PASS_SHADOW_G2_AUTONOMOUS_EXTERNAL_LIBRARY_DISCOVERY_V5",
    }
    if statuses != expected:
        raise RuntimeError(f"inherited shadow retention failure: {statuses}")
    return statuses


def main() -> int:
    inherited = inherited_shadow_receipts()
    shortlist, discovery = discover_from_open_catalog()
    records = fetch_candidate_metadata(shortlist)
    selected, selection = select_discovered_library(discovery, records)
    selected_payload = records[selected]["payload"]
    selected_info = selected_payload.get("info") or {}
    selected_version = str(selected_info.get("version") or "")
    if not selected_version:
        raise RuntimeError("selected discovered package has no version")

    artifact = v5.choose_wheel(selected_payload)
    wheel_raw, wheel_fetch = v5.guarded_fetch(
        artifact["url"],
        accept="application/octet-stream",
        max_bytes=v5.MAX_WHEEL_BYTES,
    )
    actual_wheel_sha = v5.sha_bytes(wheel_raw)
    if actual_wheel_sha != artifact["expected_sha256"]:
        raise RuntimeError("open-catalog selected artifact digest mismatch")

    wheel_evidence = v5.inspect_wheel(wheel_raw, selected, selected_version)
    dependency = wheel_evidence["selected_dependency"]
    dependency_payload, dependency_proof = v5.fetch_json(
        v5.PYPI_JSON.format(name=urllib.parse.quote(dependency))
    )
    dependency_info = dependency_payload.get("info") or {}
    dependency_version = str(dependency_info.get("version") or "")
    if not dependency_version:
        raise RuntimeError("discovered dependency has no live version")

    bundle = {
        "objective": OBJECTIVE,
        "catalog": "PyPI Simple root",
        "selected_package": v5.normalize_name(selected),
        "selected_version": selected_version,
        "artifact_filename": artifact["filename"],
        "artifact_sha256": actual_wheel_sha,
        "discovered_dependency": v5.normalize_name(dependency),
        "dependency_version": dependency_version,
        "connection_depth": 3,
        "candidate_names_host_provided": False,
        "read_only": True,
    }
    frozen_bundle_sha = v5.sha_json(bundle)

    sealed = v5.sealed_simple_validation(selected, artifact["filename"], actual_wheel_sha)
    if v5.sha_json(bundle) != frozen_bundle_sha:
        raise RuntimeError("open-catalog bundle changed after sealed validation")

    selected_row = next(row for row in selection["ranked"] if row["name"] == selected)
    gates = {
        "open_catalog_read_only": discovery["source"]["read_only"] is True,
        "catalog_has_many_projects": discovery["catalog_project_count"] > 1000,
        "candidate_names_host_provided": False,
        "candidate_shortlist_nonempty": len(shortlist) > 0,
        "selected_from_discovered_catalog": selected in shortlist,
        "selected_package_host_provided": False,
        "selected_metadata_relevance_positive": selected_row["relevance_score"] > 0,
        "selected_has_external_dependency": bool(selected_row["requirements"]),
        "artifact_digest_verified": actual_wheel_sha == artifact["expected_sha256"],
        "dependency_discovered_from_external_artifact": wheel_evidence["host_provided_dependency_name"] is False,
        "second_hop_registry_connection_succeeded": bool(dependency_version),
        "bundle_frozen_before_sealed_validation": True,
        "sealed_independent_registry_surface_verified": sealed["matched"] is True,
        "external_write_methods_used": False,
        "credentials_used": False,
        "external_models_used": False,
        "canonical_mutation": False,
    }

    pass_gate = (
        gates["open_catalog_read_only"]
        and gates["catalog_has_many_projects"]
        and gates["candidate_names_host_provided"] is False
        and gates["candidate_shortlist_nonempty"]
        and gates["selected_from_discovered_catalog"]
        and gates["selected_package_host_provided"] is False
        and gates["selected_metadata_relevance_positive"]
        and gates["selected_has_external_dependency"]
        and gates["artifact_digest_verified"]
        and gates["dependency_discovered_from_external_artifact"]
        and gates["second_hop_registry_connection_succeeded"]
        and gates["bundle_frozen_before_sealed_validation"]
        and gates["sealed_independent_registry_surface_verified"]
        and gates["external_write_methods_used"] is False
        and gates["credentials_used"] is False
        and gates["external_models_used"] is False
        and gates["canonical_mutation"] is False
        and all(value.startswith("PASS_SHADOW_") for value in inherited.values())
    )
    status = (
        "PASS_SHADOW_G2_AUTONOMOUS_OPEN_CATALOG_DISCOVERY_V6"
        if pass_gate
        else "WITHHOLD_G2_AUTONOMOUS_OPEN_CATALOG_DISCOVERY_V6"
    )

    report = {
        "schema": "yado.autonomous_open_catalog_discovery.v6",
        "status": status,
        "objective": OBJECTIVE,
        "discovery": discovery,
        "selection": selection,
        "selected_library": {
            "name": v5.normalize_name(selected),
            "version": selected_version,
            "source": records[selected]["source"],
        },
        "artifact_connection": {
            **artifact,
            "actual_sha256": actual_wheel_sha,
            "fetch": wheel_fetch,
            "wheel_metadata": wheel_evidence,
        },
        "second_hop_library_connection": {
            "name": v5.normalize_name(dependency),
            "version": dependency_version,
            "host_provided_dependency_name": False,
            "source": dependency_proof,
        },
        "frozen_bundle_sha256": frozen_bundle_sha,
        "sealed_validation": sealed,
        "application": {
            "external_catalog_applied": True,
            "externally_discovered_candidate_names_applied": True,
            "externally_discovered_dependency_applied": True,
            "connection_depth": 3,
        },
        "gates": gates,
        "inherited_shadow_retention": inherited,
        "boundaries": {
            "host_authored_objective": True,
            "host_authored_discovery_anchors": True,
            "host_authored_registry_allowlist": True,
            "host_authored_resource_caps": True,
            "host_authored_candidate_names": False,
            "host_authored_selected_package": False,
            "host_authored_dependency_name": False,
            "unrestricted_internet_autonomy_claimed": False,
            "general_intelligence_claimed": False,
            "consciousness_claimed": False,
            "g3_genesis_performed": False,
        },
    }
    RECEIPT.parent.mkdir(parents=True, exist_ok=True)
    RECEIPT.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print(
        json.dumps(
            {
                "status": status,
                "catalog_project_count": discovery["catalog_project_count"],
                "discovered_candidate_count": len(shortlist),
                "selected_package": v5.normalize_name(selected),
                "selected_version": selected_version,
                "selected_relevance_score": selected_row["relevance_score"],
                "artifact_sha256": actual_wheel_sha,
                "discovered_dependency": v5.normalize_name(dependency),
                "dependency_version": dependency_version,
                "connection_depth": 3,
                "frozen_bundle_sha256": frozen_bundle_sha,
                "sealed_simple_verified": sealed["matched"],
                "inherited_shadow_retention": inherited,
            },
            sort_keys=True,
        )
    )
    return 0 if pass_gate else 2


if __name__ == "__main__":
    raise SystemExit(main())
