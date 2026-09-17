from __future__ import annotations

"""Bounded, read-only bridge for external development projects.

The bridge turns verified repository metadata into admissible observations for
YADO. It never clones, imports, executes, or writes third-party code.
"""

from dataclasses import asdict, dataclass
from typing import Any


SCHEMA = "yado.external_project_bridge.v1"
STATUS_PASS = "PASS_SHADOW_EXTERNAL_PROJECT_BRIDGE_V1"
STATUS_WITHHOLD = "WITHHOLD_EXTERNAL_PROJECT_BRIDGE_UNKNOWN_TARGET"


@dataclass(frozen=True)
class Project:
    project_id: str
    repository: str
    default_branch: str
    role: str
    license_status: str
    allowed_actions: tuple[str, ...]


PROJECTS = (
    Project(
        project_id="FREE_FOR_DEV_CATALOG",
        repository="ripienaar/free-for-dev",
        default_branch="master",
        role="READ_ONLY_RESOURCE_CATALOG",
        license_status="LICENSE_NOT_PRESENT_IN_DEFAULT_TREE",
        allowed_actions=("READ_METADATA", "EXTRACT_RESOURCE_DESCRIPTIONS"),
    ),
    Project(
        project_id="HIVEMIND_ORCHESTRATOR",
        repository="dip497/hivemind",
        default_branch="main",
        role="READ_ONLY_LOCAL_ORCHESTRATOR_REFERENCE",
        license_status="MIT",
        allowed_actions=("READ_METADATA", "DERIVE_LOCAL_ADAPTER_PLAN"),
    ),
)


def snapshot() -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": STATUS_PASS,
        "project_count": len(PROJECTS),
        "repositories": [project.repository for project in PROJECTS],
        "third_party_code_copied": False,
        "third_party_code_executed": False,
        "external_writes": False,
        "credentials_used": False,
        "automatic_main_mutation": False,
    }


def observe(repository: str, *, default_branch: str, license_status: str) -> dict[str, Any]:
    """Record only explicit metadata supplied by a read-only observer."""
    project = next((item for item in PROJECTS if item.repository == repository), None)
    if project is None:
        return {
            "status": STATUS_WITHHOLD,
            "repository": repository,
            "reason": "REPOSITORY_NOT_ADMITTED",
        }
    if default_branch != project.default_branch or license_status != project.license_status:
        return {
            "status": STATUS_WITHHOLD,
            "repository": repository,
            "reason": "ADMITTED_METADATA_DRIFT",
        }
    return {"status": STATUS_PASS, "project": asdict(project)}


def route_task(repository: str, task: str) -> dict[str, Any]:
    """Route an admitted observation without treating external text as code."""
    lowered = task.lower()
    project = next((item for item in PROJECTS if item.repository == repository), None)
    if project is None:
        return {"status": STATUS_WITHHOLD, "capability": None}
    if project.project_id == "FREE_FOR_DEV_CATALOG" and any(
        token in lowered for token in ("free", "resource", "service", "tier", "catalog")
    ):
        capability = "FREE_TIER_RESOURCE_DISCOVERY"
    elif project.project_id == "HIVEMIND_ORCHESTRATOR" and any(
        token in lowered for token in ("agent", "mcp", "worktree", "issue", "orchestrator")
    ):
        capability = "TASK_CONTRACT_AND_AGENT_SUPERVISION_PATTERN"
    else:
        return {"status": STATUS_WITHHOLD, "capability": None, "repository": repository}
    return {
        "status": STATUS_PASS,
        "capability": capability,
        "repository": repository,
        "execution": "PLAN_ONLY",
        "external_write": False,
    }
