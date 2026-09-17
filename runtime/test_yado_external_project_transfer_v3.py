from yado_external_project_transfer_v3 import run


def test_g4_transfer_and_ambiguity_guard_pass():
    result = run()
    assert result["status"] == "PASS_SHADOW_G4_TRANSFER_AND_AMBIGUITY_GUARD_V3"
    assert result["parent_status"] == "PASS_SHADOW_THREE_STATE_DERIVED_GENERATIONS_V2"
    assert result["transfer_count"] == 3
    assert all(item["pass"] for item in result["transfer"])
    assert result["baseline_ambiguous_selected"] is not None
    assert result["guarded_ambiguous_status"].startswith("WITHHOLD")
    assert result["unknown_withhold"] is True
    assert result["third_party_code_executed"] is False
    assert result["external_writes"] is False
    assert result["automatic_main_mutation"] is False
