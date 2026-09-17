from yado_external_project_training_v1 import (
    SOURCE_ROWS,
    STATUS_PASS,
    STATUS_WITHHOLD,
    route,
    snapshot,
    train,
    validate_rows,
)


def test_snapshot_is_bounded():
    result = snapshot()
    assert result["status"] == STATUS_PASS
    assert result["source_count"] == 2
    assert result["network_fetch"] is False
    assert result["third_party_code_executed"] is False
    assert result["external_writes"] is False


def test_training_preserves_provenance_and_builds_three_profiles():
    trained = train()
    assert trained["status"] == STATUS_PASS
    assert trained["row_count"] == len(SOURCE_ROWS)
    assert set(trained["profiles"]) == {"LOGIC", "THINKING", "INTELLIGENCE"}
    assert set(trained["source_repositories"]) == {
        "ripienaar/free-for-dev",
        "dip497/hivemind",
    }
    assert trained["training_digest"]


def test_trained_profiles_route_distinct_cognitive_tasks():
    trained = train()
    assert route("validate security criteria and review state", trained)["capability"] == "LOGIC"
    assert route("preserve context across workflow architecture events", trained)["capability"] == "THINKING"
    assert route("coordinate agents and supervise resource adaptation", trained)["capability"] == "INTELLIGENCE"


def test_unknown_task_is_withheld():
    assert route("quantum banana semantics", train())["status"] == STATUS_WITHHOLD


def test_unadmitted_source_is_rejected():
    bad = [dict(SOURCE_ROWS[0], repository="unknown/example")]
    try:
        validate_rows(bad)
    except ValueError as error:
        assert str(error) == "TRAINING_REPOSITORY_NOT_ADMITTED"
    else:
        raise AssertionError("unadmitted source was accepted")
