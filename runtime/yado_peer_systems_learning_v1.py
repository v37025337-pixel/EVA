from __future__ import annotations

"""Bounded comparative learning from public peer agent/self-evolution systems.

Third-party repositories are read as untrusted evidence. This module never clones,
installs, executes, or bulk-copies third-party code and never mutates canonical.
"""

import hashlib
import json
from typing import Any

SCHEMA = "yado.peer_systems_learning.v1"
COMPONENT_ID = "RUNTIME-G2-PEER-SYSTEMS-LEARNING-V1"

SOURCES = {
    "dgm": {
        "repo": "jennyzzt/dgm", "branch": "main", "license_mode": "APACHE_2_REFERENCE",
        "markers": ["self-improving", "archive", "benchmark", "code"],
        "focus": ["OPEN_ENDED_ARCHIVE_SELECTION", "SELF_MODIFICATION_SELECTION", "ATTEMPT_HISTORY"],
    },
    "adas": {
        "repo": "ShengranHu/ADAS", "branch": "main", "license_mode": "APACHE_2_REFERENCE",
        "markers": ["meta agent search", "agentic systems", "code", "benchmark"],
        "focus": ["AUTOMATED_AGENT_DESIGN_SEARCH", "POPULATION_FEEDBACK"],
    },
    "rsiagent": {
        "repo": "AetherLabsAI/RSIAgent", "branch": "main", "license_mode": "APACHE_2_REFERENCE",
        "markers": ["recursive self-improvement", "broad", "deep", "memory"],
        "focus": ["BROAD_DEEP_CAUSAL_EXPLORATION", "CAUSAL_MEMORY", "CURRICULUM_ACTOR_VERIFIER"],
    },
    "agent_libos": {
        "repo": "yingqi-z20/Agent-libOS", "branch": "main", "license_mode": "APACHE_2_REFERENCE",
        "markers": ["capability", "runtime", "agentprocess", "checkpoint"],
        "focus": ["CAPABILITY_AUTHORITY_RUNTIME_BOUNDARY", "CHECKPOINT_LINEAGE", "PROCESS_IDENTITY"],
    },
    "aider": {
        "repo": "Aider-AI/aider", "branch": "main", "license_mode": "APACHE_2_REFERENCE",
        "markers": ["git", "repository", "test", "code"],
        "focus": ["REPOSITORY_EDIT_TEST_CONTEXT_LOOP", "GIT_NATIVE_WORKFLOW"],
    },
    "openhands_sdk": {
        "repo": "OpenHands/software-agent-sdk", "branch": "main", "license_mode": "MIT_REFERENCE",
        "markers": ["agent", "event", "tool", "sandbox"],
        "focus": ["AGENT_RUNTIME_ABSTRACTIONS", "EVENT_STREAM", "SANDBOX_BOUNDARY"],
    },
    "voyager": {
        "repo": "MineDojo/Voyager", "branch": "main", "license_mode": "MIT_REFERENCE",
        "markers": ["curriculum", "skill library", "self-verification", "minecraft"],
        "focus": ["AUTOMATIC_CURRICULUM", "SKILL_LIBRARY", "ITERATIVE_SELF_VERIFICATION"],
    },
    "generic_agent": {
        "repo": "lsdefine/GenericAgent", "branch": "main", "license_mode": "MIT_REFERENCE",
        "markers": ["self-evolving", "memory", "skill", "context"],
        "focus": ["HIERARCHICAL_MEMORY_AND_CONTEXT_COMPACTION", "SKILL_SOP_EXTRACTION"],
    },
    "reflexion": {
        "repo": "noahshinn/reflexion", "branch": "main", "license_mode": "MIT_REFERENCE",
        "markers": ["reflexion", "verbal", "attempt", "feedback"],
        "focus": ["REFLECTION_TO_POLICY_UPDATE", "FAILURE_TO_FUTURE_POLICY"],
    },
    "dspy": {
        "repo": "stanfordnlp/dspy", "branch": "main", "license_mode": "MIT_REFERENCE",
        "markers": ["programming", "optimizing", "modules", "metrics"],
        "focus": ["METRIC_DRIVEN_WORKFLOW_OPTIMIZATION", "PROGRAM_LEVEL_COMPILATION"],
    },
    "textgrad": {
        "repo": "zou-group/textgrad", "branch": "main", "license_mode": "MIT_REFERENCE",
        "markers": ["textgrad", "gradient", "optimization", "feedback"],
        "focus": ["TEXTUAL_FEEDBACK_CREDIT_ASSIGNMENT", "ITERATIVE_OPTIMIZATION"],
    },
    "claude_code": {
        "repo": "anthropics/claude-code", "branch": "main", "license_mode": "REFERENCE_ONLY",
        "markers": ["agentic coding", "terminal", "git workflows", "plugins"],
        "focus": ["CODEBASE_NAVIGATION", "TOOL_LOOP", "CONTEXT_MANAGEMENT"],
    },
}

def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def _safe(result: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    if not isinstance(result, dict) or not isinstance(result.get("content"), str):
        raise ValueError("PEER_FETCH_INVALID")
    receipt = dict(result.get("receipt") or {})
    if not (
        receipt.get("read_only") is True
        and receipt.get("credentials_used") is False
        and receipt.get("external_write") is False
        and receipt.get("private_network_access") is False
        and receipt.get("downloaded_code_executed") is False
    ):
        raise ValueError("PEER_FETCH_SAFETY_MISMATCH")
    return result["content"], receipt

class PeerSystemsLearningV1:
    def __init__(self):
        self._last = None

    def snapshot(self) -> dict[str, Any]:
        return {
            "schema": SCHEMA,
            "component_id": COMPONENT_ID,
            "status": "BOUND" if self._last else "BOUND_UNREFRESHED",
            "source_count": len(SOURCES),
            "read_only_external": True,
            "third_party_code_executed": False,
            "third_party_code_copied": False,
            "automatic_canonical_mutation": False,
            "last_digest": (self._last or {}).get("study_digest"),
        }

    def study(self, fetch) -> dict[str, Any]:
        rows = []
        withheld = []
        for key, spec in SOURCES.items():
            meta_url = f"https://api.github.com/repos/{spec['repo']}"
            readme_url = f"https://raw.githubusercontent.com/{spec['repo']}/{spec['branch']}/README.md"
            try:
                meta_text, meta_receipt = _safe(fetch(meta_url))
                readme_text, readme_receipt = _safe(fetch(readme_url))
                metadata = json.loads(meta_text)
                full_name = str(metadata.get("full_name") or "")
                if full_name.lower() != spec["repo"].lower():
                    raise ValueError("PEER_REPO_IDENTITY_MISMATCH")
                lower = readme_text.lower()
                hits = [m for m in spec["markers"] if m in lower]
                status = "VERIFIED" if hits else "WITHHOLD_WEAK_MECHANISM_EVIDENCE"
                row = {
                    "key": key,
                    "repo": full_name,
                    "default_branch": metadata.get("default_branch"),
                    "license_spdx": (metadata.get("license") or {}).get("spdx_id"),
                    "license_mode": spec["license_mode"],
                    "status": status,
                    "focus": list(spec["focus"]),
                    "marker_hits": hits,
                    "metadata_sha256": _sha(meta_text),
                    "readme_sha256": _sha(readme_text),
                    "metadata_receipt_sha256": meta_receipt.get("sha256"),
                    "readme_receipt_sha256": readme_receipt.get("sha256"),
                    "read_only": True,
                    "code_copy_performed": False,
                    "code_execution_performed": False,
                }
                rows.append(row)
                if status.startswith("WITHHOLD"):
                    withheld.append(key)
            except Exception as exc:
                withheld.append(key)
                rows.append({
                    "key": key,
                    "repo": spec["repo"],
                    "status": "WITHHOLD_SOURCE_UNVERIFIED",
                    "reason": f"{type(exc).__name__}:{str(exc)[:160]}",
                    "focus": list(spec["focus"]),
                    "read_only": True,
                    "code_copy_performed": False,
                    "code_execution_performed": False,
                })

        verified = [x for x in rows if x["status"] == "VERIFIED"]
        mechanism_counts: dict[str, int] = {}
        for row in verified:
            for mechanism in row["focus"]:
                mechanism_counts[mechanism] = mechanism_counts.get(mechanism, 0) + 1
        ranked = sorted(
            ({"mechanism": k, "independent_peer_count": v} for k, v in mechanism_counts.items()),
            key=lambda x: (-x["independent_peer_count"], x["mechanism"]),
        )
        body = {
            "schema": SCHEMA,
            "component_id": COMPONENT_ID,
            "status": "PASS_SHADOW_PEER_SYSTEMS_LEARNING_V1" if len(verified) >= 8 else "WITHHOLD_PEER_SYSTEMS_LEARNING_V1",
            "sources": rows,
            "verified_source_count": len(verified),
            "withheld_sources": withheld,
            "mechanism_cards": ranked,
            "next": "MAP_VERIFIED_MECHANISMS_TO_MEASURED_YADO_DEFICITS_AND_BUILD_MAX_THREE_CLEAN_ROOM_SHADOW_CANDIDATES",
            "read_only_external": True,
            "third_party_code_executed": False,
            "third_party_code_copied": False,
            "credentials_used": False,
            "external_writes": False,
            "automatic_canonical_mutation": False,
            "g3_genesis_performed": False,
        }
        body["study_digest"] = _sha(json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False))
        self._last = json.loads(json.dumps(body))
        return json.loads(json.dumps(body))

__all__ = ["PeerSystemsLearningV1", "SOURCES"]
