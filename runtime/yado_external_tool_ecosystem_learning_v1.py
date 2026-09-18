from __future__ import annotations

"""Read-only learning layer for external developer tool ecosystems.

The layer treats third-party repositories as untrusted evidence. It reads only
public metadata and README text, verifies provenance and source identity, and
produces bounded clean-room capability cards. It never installs or executes
third-party code and never mutates canonical state.
"""

import hashlib
import json
from typing import Any
from urllib.parse import urlparse

SCHEMA = "yado.external_tool_ecosystem_learning.v1"
COMPONENT_ID = "RUNTIME-G2-EXTERNAL-TOOL-ECOSYSTEM-LEARNING-V1"

SOURCES = {
    "exa_mcp": {
        "source_id": "EXA_MCP_SERVER",
        "repo": "exa-labs/exa-mcp-server",
        "branch": "main",
        "domain": "web_research",
        "license_mode": "MIT_REFERENCE",
        "markers": ["web search", "content fetching", "multi-step research"],
        "min_marker_hits": 2,
        "focus": [
            "WEB_SEARCH_AND_FETCH_TRANSPORT",
            "MCP_TOOL_BOUNDARY",
            "SEARCH_THEN_FETCH_RESEARCH_LOOP",
        ],
    },
    "hivemind": {
        "source_id": "HIVEMIND",
        "repo": "dip497/hivemind",
        "branch": "main",
        "domain": "agent_orchestration",
        "license_mode": "MIT_REFERENCE",
        "markers": ["worktree", "control plane", "human review", "mcp"],
        "min_marker_hits": 2,
        "focus": [
            "MULTI_AGENT_TASK_ISOLATION",
            "WORKTREE_BRANCH_ISOLATION",
            "SUPERVISED_TOOL_APPROVAL",
            "PERSISTENT_TASK_STATE",
        ],
    },
    "free_for_dev": {
        "source_id": "FREE_FOR_DEV",
        "repo": "ripienaar/free-for-dev",
        "branch": "master",
        "domain": "resource_discovery",
        "license_mode": "REFERENCE_ONLY",
        "markers": ["major cloud providers", "web hosting", "search", "free"],
        "min_marker_hits": 2,
        "focus": [
            "RESOURCE_CANDIDATE_DISCOVERY",
            "COST_AWARE_CAPABILITY_DISCOVERY",
            "FREE_TIER_REVALIDATION",
        ],
    },
    "ghidra": {
        "source_id": "GHIDRA",
        "repo": "NationalSecurityAgency/ghidra",
        "branch": "master",
        "domain": "static_analysis",
        "license_mode": "APACHE_2_REFERENCE",
        "markers": ["reverse engineering", "headless", "decompilation", "scripting"],
        "min_marker_hits": 2,
        "focus": [
            "HEADLESS_STATIC_ANALYSIS",
            "PROGRAM_STRUCTURE_RECOVERY",
            "NON_EXECUTING_CODE_INSPECTION",
        ],
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
        "schema": "yado.external_tool_evidence_gate.v1",
        "status": "PASS" if not errors else "WITHHOLD",
        "record_count": len(records),
        "unique_source_count": len(seen),
        "errors": tuple(errors),
        "canonical_active": False,
        "external_code_executed": False,
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
            "read_only_external": True,
            "third_party_code_executed": False,
            "third_party_code_copied": False,
            "automatic_install": False,
            "automatic_canonical_mutation": False,
            "last_digest": (self._last or {}).get("study_digest"),
        }

    def study(self, fetch) -> dict[str, Any]:
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
                enough_markers = len(hits) >= int(spec["min_marker_hits"])
                status = "VERIFIED" if enough_markers else "WITHHOLD_WEAK_MECHANISM_EVIDENCE"

                provenance = {
                    "repository": full_name,
                    "branch": spec["branch"],
                    "metadata_sha256": _sha(metadata_text),
                    "readme_sha256": _sha(readme_text),
                    "metadata_receipt_sha256": metadata_receipt.get("sha256"),
                    "readme_receipt_sha256": readme_receipt.get("sha256"),
                }
                claims = list(spec["focus"])
                evidence_record = {
                    "source_id": spec["source_id"],
                    "domain": spec["domain"],
                    "url": readme_url,
                    "provenance": provenance,
                    "claims": claims,
                }
                evidence_records.append(evidence_record)

                row = {
                    "key": key,
                    "source_id": spec["source_id"],
                    "repo": full_name,
                    "default_branch": metadata.get("default_branch"),
                    "license_spdx": (metadata.get("license") or {}).get("spdx_id"),
                    "license_mode": spec["license_mode"],
                    "domain": spec["domain"],
                    "status": status,
                    "focus": claims,
                    "marker_hits": hits,
                    "metadata_sha256": provenance["metadata_sha256"],
                    "readme_sha256": provenance["readme_sha256"],
                    "read_only": True,
                    "code_copy_performed": False,
                    "code_execution_performed": False,
                }
                rows.append(row)
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
                        "status": "WITHHOLD_SOURCE_UNVERIFIED",
                        "reason": f"{type(exc).__name__}:{str(exc)[:160]}",
                        "focus": list(spec["focus"]),
                        "read_only": True,
                        "code_copy_performed": False,
                        "code_execution_performed": False,
                    }
                )

        verified = [row for row in rows if row["status"] == "VERIFIED"]
        gate = validate_evidence_records(evidence_records)

        capability_cards: list[dict[str, Any]] = []
        for row in verified:
            for mechanism in row["focus"]:
                capability_cards.append(
                    {
                        "mechanism": mechanism,
                        "evidence_source_id": row["source_id"],
                        "domain": row["domain"],
                        "mode": "SHADOW_CLEAN_ROOM",
                        "requires_fresh_regression": True,
                        "canonical_active": False,
                    }
                )

        pass_all = len(verified) == len(SOURCES) and gate["status"] == "PASS"
        body = {
            "schema": SCHEMA,
            "component_id": COMPONENT_ID,
            "status": (
                "PASS_SHADOW_EXTERNAL_TOOL_ECOSYSTEM_LEARNING_V1"
                if pass_all
                else "WITHHOLD_EXTERNAL_TOOL_ECOSYSTEM_LEARNING_V1"
            ),
            "sources": rows,
            "evidence_records": evidence_records,
            "evidence_gate": gate,
            "verified_source_count": len(verified),
            "withheld_sources": withheld,
            "capability_cards": capability_cards,
            "next": (
                "BUILD_AND_TEST_CLEAN_ROOM_SHADOW_ADAPTERS_FOR_WEB_RESEARCH_"
                "MULTI_AGENT_ORCHESTRATION_RESOURCE_DISCOVERY_AND_STATIC_ANALYSIS"
            ),
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
    "validate_evidence_records",
]
