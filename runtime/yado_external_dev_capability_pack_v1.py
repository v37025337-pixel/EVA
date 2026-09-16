from __future__ import annotations

"""Bounded intake and use of user-selected public developer repositories.

The pack reads current public documentation through YADO's already-admitted
read-only HTTPS channel and turns it into bounded capabilities. It never clones,
installs, executes, or copies third-party code automatically.
"""

import base64
import hashlib
import json
import re
from urllib.parse import quote, unquote, urlsplit

COMPONENT_ID = "RUNTIME-G2-EXTERNAL-DEV-CAPABILITY-PACK-V1"
SCHEMA = "yado.external_dev_capability_pack.v1"
MAX_CATALOG_RESULTS = 20

SOURCES = {
    "hivemind": {
        "repo": "dip497/hivemind",
        "branch": "main",
        "readme": "https://raw.githubusercontent.com/dip497/hivemind/main/README.md",
        "license": "https://raw.githubusercontent.com/dip497/hivemind/main/LICENSE",
        "metadata": "https://api.github.com/repos/dip497/hivemind",
        "license_mode": "MIT_REFERENCE_AND_DERIVATION_ALLOWED_WITH_ATTRIBUTION",
        "restricted_paths": [],
        "markers": ["agent", "worktree", "acceptance", "mcp"],
        "capability": "TASK_CONTRACT_AND_AGENT_SUPERVISION_PATTERN",
    },
    "hoppscotch": {
        "repo": "hoppscotch/hoppscotch",
        "branch": "main",
        "readme": "https://raw.githubusercontent.com/hoppscotch/hoppscotch/main/README.md",
        "license": "https://raw.githubusercontent.com/hoppscotch/hoppscotch/main/LICENSE",
        "metadata": "https://api.github.com/repos/hoppscotch/hoppscotch",
        "license_mode": "MIT_REFERENCE_AND_DERIVATION_ALLOWED_WITH_ATTRIBUTION",
        "restricted_paths": [],
        "markers": ["graphql", "websocket", "collections", "post-request"],
        "capability": "READ_ONLY_API_ASSERTION_WORKBENCH",
    },
    "dyad": {
        "repo": "dyad-sh/dyad",
        "branch": "main",
        "readme": "https://raw.githubusercontent.com/dyad-sh/dyad/main/README.md",
        "license": "https://raw.githubusercontent.com/dyad-sh/dyad/main/LICENSE",
        "metadata": "https://api.github.com/repos/dyad-sh/dyad",
        "license_mode": "APACHE_2_CORE_ONLY; SRC_PRO_EXCLUDED_FSL_1_1",
        "restricted_paths": ["src/pro"],
        "markers": ["local", "open-source", "app builder", "bring your own keys"],
        "capability": "LOCAL_APP_BUILD_ADMISSION_LOOP",
    },
    "nexustools": {
        "repo": "nexustools-dev/nexus-tools",
        "branch": "main",
        "readme": "https://raw.githubusercontent.com/nexustools-dev/nexus-tools/main/README.md",
        "license": "https://raw.githubusercontent.com/nexustools-dev/nexus-tools/main/LICENSE",
        "metadata": "https://api.github.com/repos/nexustools-dev/nexus-tools",
        "license_mode": "MIT_REFERENCE_AND_DERIVATION_ALLOWED_WITH_ATTRIBUTION",
        "restricted_paths": [],
        "markers": ["client-side", "json formatter", "jwt decoder", "diff checker"],
        "capability": "PURE_LOCAL_DEV_UTILITY_LIBRARY",
    },
    "free_for_dev": {
        "repo": "ripienaar/free-for-dev",
        "branch": "master",
        "readme": "https://raw.githubusercontent.com/ripienaar/free-for-dev/master/README.md",
        "license": None,
        "metadata": "https://api.github.com/repos/ripienaar/free-for-dev",
        "license_mode": "CATALOG_REFERENCE_ONLY; NO_CODE_COPY",
        "restricted_paths": ["ALL_SOURCE_COPY"],
        "markers": ["free tier", "major cloud providers", "ci and cd", "web hosting"],
        "capability": "FREE_TIER_RESOURCE_DISCOVERY",
    },
}

CAPABILITIES = tuple(x["capability"] for x in SOURCES.values())


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _safe_result(result: dict) -> tuple[str, dict]:
    if not isinstance(result, dict) or not isinstance(result.get("content"), str):
        raise ValueError("EXTERNAL_DEV_FETCH_INVALID")
    receipt = dict(result.get("receipt") or {})
    if not (
        receipt.get("read_only") is True
        and receipt.get("credentials_used") is False
        and receipt.get("external_write") is False
        and receipt.get("private_network_access") is False
    ):
        raise ValueError("EXTERNAL_DEV_FETCH_SAFETY_MISMATCH")
    return result["content"], receipt


def _repo_name(metadata: dict) -> str | None:
    value = metadata.get("full_name")
    return str(value) if isinstance(value, str) else None


class ExternalDevCapabilityPackV1:
    def __init__(self):
        self._last_refresh = None

    def snapshot(self) -> dict:
        return {
            "schema": SCHEMA,
            "component_id": COMPONENT_ID,
            "status": "BOUND" if self._last_refresh is not None else "BOUND_UNREFRESHED",
            "source_count": len(SOURCES),
            "capabilities": list(CAPABILITIES),
            "read_only_external": True,
            "third_party_code_execution": False,
            "third_party_code_copy": False,
            "credentials_allowed": False,
            "private_network_access": False,
            "external_writes": False,
            "automatic_canonical_mutation": False,
            "g3_genesis_performed": False,
            "last_refresh_digest": (self._last_refresh or {}).get("pack_digest"),
        }

    def refresh(self, fetch) -> dict:
        rows = []
        for key, spec in SOURCES.items():
            meta_text, meta_receipt = _safe_result(fetch(spec["metadata"]))
            readme_text, readme_receipt = _safe_result(fetch(spec["readme"]))
            try:
                metadata = json.loads(meta_text)
            except json.JSONDecodeError as exc:
                raise ValueError("EXTERNAL_DEV_METADATA_INVALID:" + key) from exc
            if _repo_name(metadata) != spec["repo"]:
                raise ValueError("EXTERNAL_DEV_REPO_IDENTITY_MISMATCH:" + key)
            lower = readme_text.lower()
            hits = [marker for marker in spec["markers"] if marker in lower]
            if len(hits) < max(2, len(spec["markers"]) - 1):
                raise ValueError("EXTERNAL_DEV_CAPABILITY_EVIDENCE_WEAK:" + key)
            license_receipt = None
            license_sha256 = None
            if spec["license"]:
                license_text, license_receipt = _safe_result(fetch(spec["license"]))
                license_sha256 = _sha(license_text)
            rows.append({
                "key": key,
                "repo": spec["repo"],
                "default_branch": metadata.get("default_branch"),
                "repo_visibility": metadata.get("visibility", "public"),
                "capability": spec["capability"],
                "feature_markers_verified": hits,
                "license_mode": spec["license_mode"],
                "restricted_paths": list(spec["restricted_paths"]),
                "metadata_sha256": _sha(meta_text),
                "readme_sha256": _sha(readme_text),
                "license_sha256": license_sha256,
                "metadata_receipt_sha256": meta_receipt.get("sha256"),
                "readme_receipt_sha256": readme_receipt.get("sha256"),
                "license_receipt_sha256": (license_receipt or {}).get("sha256"),
                "read_only": True,
                "code_copy_performed": False,
                "code_execution_performed": False,
            })
        body = {
            "schema": SCHEMA,
            "component_id": COMPONENT_ID,
            "status": "PASS_EXTERNAL_DEV_CAPABILITY_PACK_V1",
            "sources": rows,
            "source_count": len(rows),
            "capabilities": list(CAPABILITIES),
            "read_only_external": True,
            "code_copy_performed": False,
            "third_party_code_executed": False,
            "automatic_canonical_mutation": False,
            "g3_genesis_performed": False,
        }
        body["pack_digest"] = _sha(json.dumps(body, sort_keys=True, separators=(",", ":"), default=str))
        self._last_refresh = body
        return json.loads(json.dumps(body))

    @staticmethod
    def task_contract(objective: str, acceptance_criteria: list[str]) -> dict:
        goal = " ".join(str(objective or "").split()).strip()
        criteria = [" ".join(str(x).split()).strip() for x in acceptance_criteria if str(x).strip()]
        if not goal or not 1 <= len(criteria) <= 12:
            raise ValueError("TASK_CONTRACT_OBJECTIVE_OR_CRITERIA_INVALID")
        return {
            "schema": "yado.external_dev.task_contract.v1",
            "source_pattern": "dip497/hivemind",
            "objective": goal,
            "acceptance_criteria": criteria,
            "states": ["BACKLOG", "TODO", "IN_PROGRESS", "IN_REVIEW", "DONE", "WITHHOLD"],
            "isolation_preference": "BRANCH_OR_WORKTREE",
            "human_review_supported": True,
            "automatic_external_agent_spawn": False,
        }

    @staticmethod
    def api_probe(fetch, url: str, *, must_contain: str | None = None) -> dict:
        if urlsplit(str(url)).scheme.lower() != "https":
            raise ValueError("API_PROBE_HTTPS_REQUIRED")
        content, receipt = _safe_result(fetch(url))
        ok = True if must_contain is None else str(must_contain).lower() in content.lower()
        return {
            "schema": "yado.external_dev.api_probe.v1",
            "source_pattern": "hoppscotch/hoppscotch",
            "status": "PASS_READ_ONLY_API_ASSERTION" if ok else "WITHHOLD_API_ASSERTION",
            "url": receipt.get("final_url", url),
            "http_status": receipt.get("http_status"),
            "content_type": receipt.get("content_type"),
            "sha256": receipt.get("sha256"),
            "assertion_pass": ok,
            "read_only": True,
        }

    @staticmethod
    def app_build_plan(objective: str, stack: str, tests: list[str]) -> dict:
        goal = " ".join(str(objective or "").split()).strip()
        stack_name = " ".join(str(stack or "").split()).strip()
        checks = [" ".join(str(x).split()).strip() for x in tests if str(x).strip()]
        if not goal or not stack_name or not checks:
            raise ValueError("APP_BUILD_PLAN_INVALID")
        return {
            "schema": "yado.external_dev.local_app_build_plan.v1",
            "source_pattern": "dyad-sh/dyad",
            "objective": goal,
            "stack": stack_name,
            "phases": ["SPEC", "CANDIDATE", "BUILD", "LOCAL_PREVIEW", "TEST", "REGRESSION", "ADMISSION"],
            "required_tests": checks,
            "local_first": True,
            "restricted_reference_paths": ["src/pro"],
            "automatic_deploy": False,
            "automatic_canonical_mutation": False,
        }

    @staticmethod
    def utility(name: str, value: str) -> dict:
        op = str(name).strip().lower()
        raw = str(value)
        if op == "json_format":
            output = json.dumps(json.loads(raw), indent=2, sort_keys=True, ensure_ascii=False)
        elif op == "json_minify":
            output = json.dumps(json.loads(raw), separators=(",", ":"), ensure_ascii=False)
        elif op == "base64_encode":
            output = base64.b64encode(raw.encode()).decode()
        elif op == "base64_decode":
            output = base64.b64decode(raw.encode(), validate=True).decode()
        elif op == "url_encode":
            output = quote(raw, safe="")
        elif op == "url_decode":
            output = unquote(raw)
        elif op == "sha256":
            output = _sha(raw)
        else:
            raise ValueError("LOCAL_DEV_UTILITY_UNSUPPORTED")
        return {
            "schema": "yado.external_dev.local_utility.v1",
            "source_pattern": "nexustools-dev/nexus-tools",
            "operation": op,
            "output": output,
            "local_only": True,
            "network_used": False,
        }

    @staticmethod
    def _catalog_entries(markdown: str):
        pattern = re.compile(r"^\s*[*-]\s+\[([^\]]+)\]\((https://[^)]+)\)\s*(?:[-–—:]\s*)?(.*)$")
        for line in str(markdown).splitlines():
            match = pattern.match(line)
            if match:
                yield match.group(1).strip(), match.group(2).strip(), match.group(3).strip()

    def free_resource_candidates(self, fetch, keywords: list[str], *, limit: int = 10) -> dict:
        wanted = [str(x).lower().strip() for x in keywords if str(x).strip()]
        if not wanted or not 1 <= int(limit) <= MAX_CATALOG_RESULTS:
            raise ValueError("FREE_RESOURCE_DISCOVERY_INPUT_INVALID")
        content, receipt = _safe_result(fetch(SOURCES["free_for_dev"]["readme"]))
        ranked = []
        for name, url, description in self._catalog_entries(content):
            haystack = f"{name} {description}".lower()
            score = sum(1 for token in wanted if token in haystack)
            if score:
                ranked.append((-score, name.lower(), {"name": name, "url": url, "description": description[:500], "score": score}))
        ranked.sort()
        results = [row[2] for row in ranked[: int(limit)]]
        return {
            "schema": "yado.external_dev.free_resource_discovery.v1",
            "source_pattern": "ripienaar/free-for-dev",
            "status": "PASS_FREE_TIER_RESOURCE_DISCOVERY" if results else "WITHHOLD_NO_MATCH",
            "keywords": wanted,
            "results": results,
            "result_count": len(results),
            "catalog_sha256": receipt.get("sha256"),
            "catalog_reference_only": True,
            "credentials_used": False,
            "external_write": False,
        }


__all__ = ["ExternalDevCapabilityPackV1", "SOURCES", "CAPABILITIES"]
