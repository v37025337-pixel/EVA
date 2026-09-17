from yado_external_project_bridge_v1 import (
    STATUS_PASS,
    STATUS_WITHHOLD,
    observe,
    route_task,
    snapshot,
)


def test_snapshot_is_bounded():
    result = snapshot()
    assert result["status"] == STATUS_PASS
    assert result["project_count"] == 2
    assert result["third_party_code_copied"] is False
    assert result["third_party_code_executed"] is False
    assert result["external_writes"] is False


def test_observation_accepts_verified_metadata_only():
    result = observe(
        "dip497/hivemind",
        default_branch="main",
        license_status="MIT",
    )
    assert result["status"] == STATUS_PASS
    assert result["project"]["role"] == "READ_ONLY_LOCAL_ORCHESTRATOR_REFERENCE"


def test_routes_admitted_external_goals():
    catalog = route_task("ripienaar/free-for-dev", "find a free resource tier")
    hive = route_task("dip497/hivemind", "use the MCP agent worktree orchestrator")
    assert catalog["capability"] == "FREE_TIER_RESOURCE_DISCOVERY"
    assert hive["capability"] == "TASK_CONTRACT_AND_AGENT_SUPERVISION_PATTERN"
    assert catalog["execution"] == "PLAN_ONLY"


def test_unknown_target_is_withheld():
    result = route_task("unknown/example", "run arbitrary code")
    assert result["status"] == STATUS_WITHHOLD
    assert result["capability"] is None
