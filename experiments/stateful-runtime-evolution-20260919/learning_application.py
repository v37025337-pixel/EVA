"""Measure durable learning, causal reuse and fresh text transfer.

The host supplies examples and checks. Existing native synthesis creates every
program; the existing development controller chooses the memory-dependent retry.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path
import random
import secrets


def text_goal(pairs, structured):
    def row(pair):
        left, right = pair
        value = left + right
        return {"input": {"left": left, "right": right},
                "expected": {"joined": value} if structured else value}
    rows = [row(pair) for pair in pairs]
    return {"schema": "yado.native_program_goal.v1", "domain": "native_source",
            "training": rows[:3], "validation": rows[3:5],
            "queries": [{"input": r["input"]} for r in rows[5:]]}


def run_learning_application(kernel, manifest, state, output):
    from successor.cognitive import CognitiveLoop, replay
    from successor.compositional_source import execute
    from successor.generation import retained_memory
    from successor.kernel import SuccessorKernel, encode

    out = Path(output)
    out.mkdir(exist_ok=False)
    before = kernel.verify_state()
    kernel.set_compositional_synthesis(True)
    pairs = [("ab", "Z9"), ("x-", "Q"), ("K", "12"),
             ("данные", " Ω"), ('quote"', "\\line\n"), ("雪", " done")]
    target = text_goal(pairs, True)

    def goals(current=kernel):
        return replay(CognitiveLoop(current)._records())

    def solve(current, spec, *, mode="full", budget=5):
        gid = current.open_goal(spec, budget=budget, mode=mode)
        current.think(60)
        result = goals(current)[gid]
        if result["status"] == "ACTIVE":
            current.stop_goal(gid)
            raise ValueError("TEXT_APPLICATION_GOAL_DID_NOT_TERMINATE")
        return result

    def save(name, value):
        (out / (name + ".typed.json")).write_text(encode(value) + "\n")

    failed = solve(kernel, target)
    save("baseline", failed)
    if failed["status"] == "VALIDATED_ON_HOLDOUT":
        return {"status": "ALREADY_KNOWN", "new_capability_claimed": False,
                "goal_id": failed["id"], "state_before": before,
                "state_after": kernel.verify_state()}
    assert failed["status"] == "WITHHOLD"

    control_id = kernel.start_development(budget=10, max_goals=2)
    kernel.develop(100)
    control = kernel.development_snapshot()["sessions"][control_id]
    save("before-learning-development", control)
    assert not control["selections"], "RETRY_WITHOUT_NEW_KNOWLEDGE"

    learned = solve(kernel, text_goal(pairs, False))
    save("learned", learned)
    assert learned["status"] == "VALIDATED_ON_HOLDOUT"
    (out / "learned-program.py").write_text(learned["result"]["source"])

    # Re-run the same difficulty without access to learned program memory.
    # This is a real cognitive goal; its failure remains in the journal.
    ablated = solve(kernel, target, mode="no_memory")
    save("without-memory-control", ablated)
    assert ablated["status"] == "WITHHOLD", "MEMORY_CAUSAL_GAIN_NOT_ESTABLISHED"

    session_id = kernel.start_development(budget=10, max_goals=2)
    kernel.develop(100)
    session = kernel.development_snapshot()["sessions"][session_id]
    save("development", session)
    assert session["status"] == "COMPLETE"
    assert [x["parent_goal_id"] for x in session["selections"]] == [failed["id"]]
    selected = session["selections"][0]
    assert any(x.get("retry_reason") == "NEW_VERIFIED_MEMORY" for x in selected["untried"])
    child = goals()[session["outcomes"][0]["goal_id"]]
    save("composed", child)
    assert child["status"] == "VALIDATED_ON_HOLDOUT"
    assert child["result"]["parent_source_sha256"] == [learned["result"]["source_sha256"]]
    assert goals()[failed["id"]] == failed

    # Freeze the emitted program before drawing any fresh evaluation inputs.
    candidate = copy.deepcopy(child["result"])
    frozen_sha = candidate["source_sha256"]
    (out / "composed-program.py").write_text(candidate["source"])
    seed = secrets.token_hex(24)
    rng = random.Random(seed)
    alphabet = 'abCD09 -_"\\\n\tΩ雪данные'
    fresh = [("fresh" + str(i) + "_" + ''.join(rng.choices(alphabet, k=rng.randint(0, 24))),
              ''.join(rng.choices(alphabet, k=rng.randint(0, 24)))) for i in range(24)]
    inputs = [{"left": a, "right": b} for a, b in fresh]
    expected = [{"joined": a + b} for a, b in fresh]
    observed = execute(candidate, inputs)
    assert observed == expected and candidate["source_sha256"] == frozen_sha
    save("fresh-transfer", {"seed": seed, "frozen_source_sha256": frozen_sha,
                            "inputs": inputs, "expected": expected, "observed": observed,
                            "sampled_after_source_freeze": True})

    # One writer at a time: the old kernel is idle while a new instance opens
    # the persisted state and uses the learned program on fresh data.
    saved = kernel.verify_state()
    reopened = SuccessorKernel(manifest, state)
    try:
        assert reopened.verify_state() == saved and reopened.identity == kernel.identity
        recalled = solve(reopened, text_goal(fresh, True), budget=1)
        assert recalled["status"] == "VALIDATED_ON_HOLDOUT"
        assert recalled["attempted"] == ["reuse_verified_source"]
        assert recalled["result"]["source_sha256"] == frozen_sha
        assert recalled["result"]["predictions"] == expected[5:]
        save("reopened-application", recalled)
    finally:
        reopened.close()

    memory = retained_memory(kernel)
    save("retained-memory", memory)
    assert memory["passed"]
    report = {"status": "PASS_LEARNING_AND_CAUSAL_PROGRAM_APPLICATION",
              "baseline_goal_id": failed["id"], "baseline_status": failed["status"],
              "learned_goal_id": learned["id"], "without_memory_status": ablated["status"],
              "development_session_id": session_id, "kernel_selected_retry_goal_id": child["id"],
              "learned_source_sha256": learned["result"]["source_sha256"],
              "composed_source_sha256": frozen_sha, "parent_program_inlined": True,
              "new_verified_programs": 2, "fresh_cases": len(fresh),
              "fresh_cases_passed": sum(a == b for a, b in zip(observed, expected)),
              "fresh_seed": seed, "fresh_inputs_sampled_after_source_freeze": True,
              "reopened_reuse_goal_id": recalled["id"], "restart_application_passed": True,
              "memory_goals_checked": memory["goals"], "memory_preserved": memory["passed"],
              "old_failure_preserved": goals()[failed["id"]] == failed,
              "state_before": before, "state_after": kernel.verify_state(),
              "curriculum_and_oracle_authorship": "ASSISTANT",
              "program_selection_and_composition": "EXISTING_YADO_MECHANISMS"}
    (out / "summary.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    return report
