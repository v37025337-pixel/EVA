from yado_external_project_evolution_v2 import run


def test_three_state_derived_generations_pass():
    result = run()
    assert result["status"] == "PASS_SHADOW_THREE_STATE_DERIVED_GENERATIONS_V2"
    assert [item["generation"] for item in result["generations"]] == ["G1", "G2", "G3"]
    assert result["holdout_count"] == 3
    assert result["unknown_withhold"] is True
    assert result["third_party_code_executed"] is False
    assert result["external_writes"] is False
    assert result["automatic_main_mutation"] is False
    assert len(set(result["training_digests"])) == 3


def test_each_generation_keeps_its_successor_evidence():
    result = run()
    g1, g2, g3 = result["generations"]
    assert g1["baseline_failures"] == 1
    assert all(item["pass"] for item in g2["seed_replay"])
    assert all(item["pass"] for item in g3["holdout"])
