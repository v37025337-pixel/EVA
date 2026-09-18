from __future__ import annotations

"""Aggregate already-admitted external tool integrations behind one evidence gate.

This layer does not reimplement Exa, Hivemind, free-for-dev, or Ghidra support.
It verifies that the existing YADO components are present and bounded, refreshes
public provenance for the four repositories, and emits one shared decision
surface for later deficit-to-capability selection.
"""

import hashlib
import json
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from yado_exa_mcp_web_research_v1 import ALLOWED_TOOLS, ExaMCPConfig
from yado_external_project_bridge_v1 import (
    PROJECTS,
    STATUS_PASS as EXTERNAL_PROJECT_BRIDGE_PASS,
    route_task,
    snapshot as external_project_snapshot,
)

SCHEMA = "yado.external_tool_ecosystem_aggregation.v1"
COMPONENT_ID = "RUNTIME-G2-EXTERNAL-TOOL-ECOSYSTEM-AGGREGATION-V1"

SOURCES = {
    "exa_mcp": {
        "source_id": "EXA_MCP_SERVER",
        "repo": "exa-labs/exa-mcp-server",
        "branch": "main",
        "domain": "web_research",
        "markers": ["web search", "content fetching", "multi-step research"],
        "min_marker_hits": 2,
        "binding": "runtime/yado_exa_mcp_web_research_v1.py",
    },
    "hivemind": {
        "source_id": "HIVEMIND",
        "repo": "dip497/hivemind",
        "branch": "main",
        "domain": "agent_orchestration",
        "markers": ["worktree", "control plane", "human review", "mcp"],
        "min_marker_hits": 2,
        "binding": "runtime/yado_external_project_bridge_v1.py",
    },
    "free_for_dev": {
        "source_id": "FREE_FOR_DEV",
        "repo": "ripienaar/free-for-dev",
        "branch": "master",
        "domain": "resource_discovery",
        "markers": ["major cloud providers", "web hosting", "search", "free"],
        "min_marker_hits": 2,
        "binding": "runtime/yado_external_project_bridge_v1.py",
    },
    "ghidra": {
        "source_id": "GHIDRA",
        "repo": "NationalSecurityAgency/ghidra",
        "branch": "master",
        "domain": "static_analysis",
        "markers": ["reverse engineering", "headless", "decompilation", "scripting"],
        "min_marker_hits": 2,
        "binding": "candidates/kernel-self-generated/yado-ghidra-information-genetics-v1.json",
    },
}

ALLOWED_DOMAINS = {spec["domain"] for spec in SOURCES.values()}


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _safe(result: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    if not isinstance(result, dict) or not isinstance(result.get("content"), str):
        raise ValueError("EXTERNAL_TOOL_FETCH_INVALID")
    receipt = dict(result.get("receipt") or {})
    if not (
        receipt.get("read_only") is True
        and receipt.get("credentials_used") is False
        and receipt.get("external_write") is False
        and receipt.get("private_network_access") is False
        and receipt.get("downloaded_code_executed") is False
    ):
        raise ValueError("EXTERNAL_TOOL_FETCH_SAFETY_MISMATCH")
    return result["content"], receipt


def validate_evidence_records(records: list[dict[str, Any]]) -> dict[str, Any]:
    errors: list[str] = []
    seen: set[str] = set()
    for index, record in enumerate(records):
        source_id = str(record.get("source_id") or "")
        if not source_id:
            errors.append(f"record[{index}]:missing_source_id")
        elif source_id in seen:
            errors.append(f"record[{index}]:duplicate_source_id:{source_id}")
        else:
            seen.add(source_id)

        domain = str(record.get("domain") or "")
        if not domain:
            errors.append(f"record[{index}]:missing_domain")
        elif domain not in ALLOWED_DOMAINS:
            errors.append(f"record[{index}]:domain_not_allowed:{domain}")

        url = str(record.get("url") or "")
        parsed = urlparse(url)
        if parsed.scheme != "https" or not parsed.netloc:
            errors.append(f"record[{index}]:https_url_required")

        if not record.get("provenance"):
            errors.append(f"record[{index}]:missing_provenance")
        if not record.get("claims"):
            errors.append(f"record[{index}]:missing_claims")

    return {
        "schema": "yado.external_tool_ecosystem_shared_gate.v1",
        "status": "PASS" if not errors else "WITHHOLD",
        "record_count": len(records),
        "unique_source_count": len(seen),
        "errors": tuple(errors),
        "canonical_active": False,
        "external_code_executed": False,
    }


def existing_component_bindings(repo_root: str | Path | None = None) -> dict[str, Any]:
    root = Path(repo_root or ".").resolve()

    exa = ExaMCPConfig().validated()
    exa_ok = (
        exa.endpoint == "https://mcp.exa.ai/mcp"
        and {"web_search_exa", "web_fetch_exa"}.issubset(ALLOWED_TOOLS)
    )

    bridge = external_project_snapshot()
    projects = {project.repository: project for project in PROJECTS}
    hive_route = route_task("dip497/hivemind", "use MCP worktree agent orchestrator")
    free_route = route_task("ripienaar/free-for-dev", "find free resource tier")
    bridge_ok = (
        bridge.get("status") == EXTERNAL_PROJECT_BRIDGE_PASS
        and "dip497/hivemind" in projects
        and "ripienaar/free-for-dev" in projects
        and hive_route.get("capability") == "TASK_CONTRACT_AND_AGENT_SUPERVISION_PATTERN"
        and free_route.get("capability") == "FREE_TIER_RESOURCE_DISCOVERY"
        and hive_route.get("execution") == "PLAN_ONLY"
        and free_route.get("execution") == "PLAN_ONLY"
    )

    ghidra_arch_path = root / "architecture" / "yado-ghidra-information-genetics-v1.json"
    ghidra_candidate_path = (
        root
        / "candidates"
        / "kernel-self-generated"
        / "yado-ghidra-information-genetics-v1.json"
    )
    ghidra_arch = json.loads(ghidra_arch_path.read_text(encoding="utf-8"))
    ghidra_candidate = json.loads(ghidra_candidate_path.read_text(encoding="utf-8"))
    ghidra_boundary = dict(ghidra_candidate.get("safe_boundary") or {})
    ghidra_ok = (
        ghidra_arch.get("mode") == "READ_ONLY_PUBLIC_WEB_RESEARCH"
        and ghidra_arch.get("binary_execution") is False
        and ghidra_arch.get("automatic_canonical_mutation") is False
        and ghidra_candidate.get("status") == "SHADOW_CANDIDATE"
        and ghidra_candidate.get("source_project") == "NationalSecurityAgency/ghidra"
        and ghidra_boundary.get("binary_execution") is False
        and ghidra_boundary.get("canonical_mutation") is False
    )

    bindings = {
        "exa_mcp": {
            "status": "BOUND" if exa_ok else "WITHHOLD",
            "component": "runtime/yado_exa_mcp_web_research_v1.py",
            "endpoint": exa.endpoint,
            "tools": sorted(ALLOWED_TOOLS),
            "capabilities": ["WEB_SEARCH_AND_FETCH_TRANSPORT"],
        },
        "hivemind": {
            "status": "BOUND" if bridge_ok else "WITHHOLD",
            "component": "runtime/yado_external_project_bridge_v1.py",
            "capability": hive_route.get("capability"),
            "execution": hive_route.get("execution"),
        },
        "free_for_dev": {
            "status": "BOUND" if bridge_ok else "WITHHOLD",
            "component": "runtime/yado_external_project_bridge_v1.py",
            "capability": free_route.get("capability"),
            "execution": free_route.get("execution"),
        },
        "ghidra": {
            "status": "BOUND" if ghidra_ok else "WITHHOLD",
            "component": str(
                Path("candidates")
                / "kernel-self-generated"
                / "yado-ghidra-information-genetics-v1.json"
            ),
            "capabilities": list(ghidra_candidate.get("proposed_capabilities") or []),
            "candidate_admission": ghidra_arch.get("candidate_admission"),
        },
    }
    return {
        "status": "PASS" if all(item["status"] == "BOUND" for item in bindings.values()) else "WITHHOLD",
        "bindings": bindings,
        "reused_component_count": 4,
        "new_third_party_adapter_count": 0,
    }


class ExternalToolEcosystemLearningV1:
    def __init__(self):
        self._last: dict[str, Any] | None = None

    def snapshot(self) -> dict[str, Any]:
        return {
            "schema": SCHEMA,
            "component_id": COMPONENT_ID,
            "status": "BOUND" if self._last else "BOUND_UNREFRESHED",
            "source_count": len(SOURCES),
            "reuses_existing_components": True,
            "new_third_party_adapter_count": 0,
            "read_only_external": True,
            "third_party_code_executed": False,
            "third_party_code_copied": False,
            "automatic_install": False,
            "automatic_canonical_mutation": False,
            "last_digest": (self._last or {}).get("study_digest"),
        }

    def study(self, fetch, *, repo_root: str | Path | None = None) -> dict[str, Any]:
        component_bindings = existing_component_bindings(repo_root)
        rows: list[dict[str, Any]] = []
        evidence_records: list[dict[str, Any]] = []
        withheld: list[str] = []

        for key, spec in SOURCES.items():
            metadata_url = f"https://api.github.com/repos/{spec['repo']}"
            readme_url = (
                f"https://raw.githubusercontent.com/"
                f"{spec['repo']}/{spec['branch']}/README.md"
            )
            try:
                metadata_text, metadata_receipt = _safe(fetch(metadata_url))
                readme_text, readme_receipt = _safe(fetch(readme_url))
                metadata = json.loads(metadata_text)
                full_name = str(metadata.get("full_name") or "")
                if full_name.lower() != spec["repo"].lower():
                    raise ValueError("EXTERNAL_TOOL_REPO_IDENTITY_MISMATCH")

                lower = readme_text.lower()
                hits = [marker for marker in spec["markers"] if marker in lower]
                binding = component_bindings["bindings"][key]
                enough_markers = len(hits) >= int(spec["min_marker_hits"])
                status = (
                    "VERIFIED"
                    if enough_markers and binding["status"] == "BOUND"
                    else "WITHHOLD_SOURCE_OR_BINDING"
                )

                claims = (
                    list(binding.get("capabilities") or [])
                    or [str(binding.get("capability") or "")]
                )
                claims = [claim for claim in claims if claim]
                provenance = {
                    "repository": full_name,
                    "branch": spec["branch"],
                    "binding": spec["binding"],
                    "metadata_sha256": _sha(metadata_text),
                    "readme_sha256": _sha(readme_text),
                    "metadata_receipt_sha256": metadata_receipt.get("sha256"),
                    "readme_receipt_sha256": readme_receipt.get("sha256"),
                }
                evidence_records.append(
                    {
                        "source_id": spec["source_id"],
                        "domain": spec["domain"],
                        "url": readme_url,
                        "provenance": provenance,
                        "claims": claims,
                    }
                )
                rows.append(
                    {
                        "key": key,
                        "source_id": spec["source_id"],
                        "repo": full_name,
                        "default_branch": metadata.get("default_branch"),
                        "domain": spec["domain"],
                        "binding": spec["binding"],
                        "binding_status": binding["status"],
                        "status": status,
                        "claims": claims,
                        "marker_hits": hits,
                        "read_only": True,
                        "code_copy_performed": False,
                        "code_execution_performed": False,
                    }
                )
                if status != "VERIFIED":
                    withheld.append(key)
            except Exception as exc:
                withheld.append(key)
                rows.append(
                    {
                        "key": key,
                        "source_id": spec["source_id"],
                        "repo": spec["repo"],
                        "domain": spec["domain"],
                        "binding": spec["binding"],
                        "status": "WITHHOLD_SOURCE_UNVERIFIED",
                        "reason": f"{type(exc).__name__}:{str(exc)[:160]}",
                        "read_only": True,
                        "code_copy_performed": False,
                        "code_execution_performed": False,
                    }
                )

        verified = [row for row in rows if row["status"] == "VERIFIED"]
        gate = validate_evidence_records(evidence_records)
        pass_all = (
            component_bindings["status"] == "PASS"
            and len(verified) == len(SOURCES)
            and gate["status"] == "PASS"
        )

        body = {
            "schema": SCHEMA,
            "component_id": COMPONENT_ID,
            "status": (
                "PASS_SHADOW_EXTERNAL_TOOL_ECOSYSTEM_AGGREGATION_V1"
                if pass_all
                else "WITHHOLD_EXTERNAL_TOOL_ECOSYSTEM_AGGREGATION_V1"
            ),
            "component_bindings": component_bindings,
            "sources": rows,
            "evidence_records": evidence_records,
            "evidence_gate": gate,
            "verified_source_count": len(verified),
            "withheld_sources": withheld,
            "next": (
                "MEASURE_WHETHER_SHARED_GATED_OUTPUT_CHANGES_DOWNSTREAM_YADO_"
                "DECISIONS_BEFORE_ANY_NEW_CANONICAL_ADMISSION"
            ),
            "reuses_existing_components": True,
            "new_third_party_adapter_count": 0,
            "read_only_external": True,
            "third_party_code_executed": False,
            "third_party_code_copied": False,
            "credentials_used": False,
            "external_writes": False,
            "automatic_install": False,
            "automatic_canonical_mutation": False,
            "g3_genesis_performed": False,
        }
        body["study_digest"] = _sha(
            json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        )
        self._last = json.loads(json.dumps(body))
        return json.loads(json.dumps(body))


__all__ = [
    "ExternalToolEcosystemLearningV1",
    "SOURCES",
    "existing_component_bindings",
    "validate_evidence_records",
]
