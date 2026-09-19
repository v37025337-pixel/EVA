"""Continue a verified checkpoint through one measured runtime evolution cycle.

The assistant supplies orchestration and a numeric-to-code observation bridge.
The existing kernel selects a failed goal, emits a reusable module, and runs
its unchanged fresh-transfer, retained-memory and full-regression gates.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / "runtime")]
loader = importlib.util.spec_from_file_location(
    "repository_resume", ROOT / "experiments/repository-learning-resume-20260919/run.py")
resume = importlib.util.module_from_spec(loader)
loader.loader.exec_module(resume)


def observe_numeric_memory(kernel, out):
    """Disclosed host bridge: y=0 slices, then the inherited composition grammar.

    These initial observations are derived from existing experience. They are
    not counted as fresh transfer; RuntimeEvolution draws its own later trials.
    """
    from successor.cognitive import CognitiveLoop, replay
    from successor.kernel import encode
    from successor.lineage import _challenge, polynomial_values, records, selection

    original = replay(CognitiveLoop(kernel)._records())
    kernel.activate_native_synthesis()
    observations = []

    def measure(spec, origin):
        goal_id = kernel.open_goal(spec, budget=30)
        kernel.think(100)
        goal = replay(CognitiveLoop(kernel)._records())[goal_id]
        if goal["status"] == "ACTIVE":
            kernel.stop_goal(goal_id)
            raise ValueError("OBSERVATION_DID_NOT_TERMINATE")
        observations.append({"goal_id": goal_id, "origin": origin, "spec": spec,
                             "status": goal["status"], "attempted": sorted(goal["attempted"])})
        resume.save(out, "observations", {"status": "RECORDED", "rows": observations})

    # A fixed order, independent of validation outcomes. No task answer or
    # module body is supplied to the runtime-evolution selector.
    for old in sorted(original.values(), key=lambda g: -g["id"]):
        if old["spec"]["domain"] != "numeric" or old["status"] != "VALIDATED_ON_HOLDOUT":
            continue
        training = [{"input": {"x": r["x"]}, "expected": r["expected"]}
                    for r in old["spec"]["rows"] if r["y"] == 0]
        if len(training) < 3:
            continue
        inputs = [{"x": x} for x in (-6, 7, -9, 11)]
        answers = polynomial_values(training, inputs)
        measure({"domain": "native_source", "training": training,
                 "validation": [{"input": x, "expected": y} for x, y in zip(inputs[:2], answers[:2])],
                 "queries": [{"input": x} for x in inputs[2:]]},
                {"kind": "HOST_NUMERIC_MEMORY_PROJECTION", "parent_goal_id": old["id"]})
        if selection(records(kernel)):
            return observations

    for _ in range(3):
        goals = replay(CognitiveLoop(kernel)._records())
        eligible = [r for r in records(kernel) if r.get("kind") == "COG_FINISH"
                    and r.get("status") == "VALIDATED_ON_HOLDOUT"
                    and any(o["goal_id"] == r["goal_id"] for o in observations)]
        if not eligible:
            break
        finish = eligible[-1]
        challenge = _challenge(encode(finish), encode(goals[finish["goal_id"]]["spec"]))
        measure(challenge["spec"], {"kind": "INHERITED_KERNEL_COMPOSITION_GRAMMAR",
                                   "recipe": challenge["recipe"]})
        if selection(records(kernel)):
            break
        if observations[-1]["status"] != "VALIDATED_ON_HOLDOUT":
            break
    return observations


def main(args):
    from successor.cognitive import CognitiveLoop, replay
    from successor.kernel import SuccessorKernel, encode
    from successor.runtime_evolution import REQUEST, RuntimeEvolution
    from successor.generation import retained_memory

    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    receipt = resume.restore(args.checkpoint, out, args.source_run)
    upgrade = resume.upgrade_research_sources(out, args.source_updates)
    if "web-memory.json" in receipt["checkpoint_files_sha256"]:
        shutil.copy2(args.checkpoint / "web-memory.json", out / "web-memory.json")
    manifest, state = out / "birth/manifest.json", out / "kernel.sqlite"
    kernel = SuccessorKernel(manifest, state)
    verified = kernel.verify_state()
    before = receipt["state_after"]
    assert verified["tick"] == before["tick"] + int(upgrade is not None)
    assert kernel.identity == receipt["identity_digest"]
    if upgrade is None:
        assert verified == before
    prefix = [tuple(r) for r in kernel.db.execute(
        "SELECT * FROM events WHERE tick<=? ORDER BY tick", (before["tick"],))]
    assert prefix[-1][3] == before["event_hash"]
    identity = kernel.identity
    report = {"status": "WITHHOLD", "predecessor_run_id": args.source_run,
              "tested_commit": os.environ.get("GITHUB_SHA"), "identity_digest": identity,
              "state_before": before, "orchestration_and_observation_bridge_authorship": "ASSISTANT",
              "implementation_upgraded": upgrade is not None,
              "candidate_selection_and_emission": "EXISTING_KERNEL_MECHANISMS",
              "algorithm_origin": "INHERITED_EXACT_POLYNOMIAL_FITTER",
              "general_intelligence_established": False, "consciousness_established": False,
              "background_process_running_after_completion": False}
    error = None
    try:
        evolution = RuntimeEvolution(kernel)
        workspace_id = "stateful-evolution-" + before["event_hash"]
        initial = evolution.propose(workspace_id, "YADO-1", REQUEST)
        resume.save(out, "initial-proposal", initial)
        if initial["selection"] is None:
            observe_numeric_memory(kernel, out)
            proposal = evolution.propose(workspace_id, "YADO-2", REQUEST)
        else:
            proposal = initial
        resume.save(out, "proposal", proposal)
        if proposal["selection"] is None:
            report["reason"] = "NO_SUPPORTED_DEFICIT"
        else:
            selected = proposal["selection"]
            report.update(selected_goal_id=selected["goal_id"], selected_degree=selected["max_degree"],
                          candidate_sha256=selected["candidate"]["source_sha256"])
            print(json.dumps({"stage": "gates_started", "degree": selected["max_degree"]}), flush=True)
            evaluation = evolution.evaluate(proposal["tick"], out / "gates")
            (out / "evaluation.typed.json").write_text(encode(evaluation) + "\n")
            report.update(gates_passed=evaluation["passed"], regression=evaluation["regression"],
                          fresh_cases=evaluation["trial"]["fresh_cases"],
                          fresh_gain_over_parent=evaluation["trial"]["fresh_gain_over_parent"],
                          memory=evaluation["memory"])
            if evaluation["passed"]:
                admission = evolution.admit(proposal["tick"])
                resume.save(out, "admission", admission)
                old = replay(CognitiveLoop(kernel)._records())[selected["goal_id"]]
                retry_id = kernel.open_goal(old["spec"], budget=30)
                kernel.think(100)
                retry = replay(CognitiveLoop(kernel)._records())[retry_id]
                memory = retained_memory(kernel)
                (out / "post-admission-memory.typed.json").write_text(encode(memory) + "\n")
                assert retry["status"] == "VALIDATED_ON_HOLDOUT" and memory["passed"]
                assert admission["strategy"] in retry["attempted"]
                report.update(status="PASS_STATEFUL_RUNTIME_EVOLUTION", retry_goal_id=retry_id,
                              retry_status=retry["status"], admitted_strategy=admission["strategy"],
                              old_failure_preserved=old["status"] == "WITHHOLD")
            else:
                report["reason"] = "GATES_FAILED"
    except Exception as exc:
        error = exc
        report.update(status="WITHHOLD", error=type(exc).__name__ + ":" + str(exc)[:1000])
    finally:
        after = kernel.verify_state()
        current = [tuple(r) for r in kernel.db.execute("SELECT * FROM events ORDER BY tick")]
        assert kernel.identity == identity and current[:len(prefix)] == prefix
        kernel.close()
        restarted = SuccessorKernel(manifest, state)
        try:
            assert restarted.verify_state() == after
        finally:
            restarted.close()
        for relative in resume.OVERLAY:
            destination = out / "source-overlay" / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / relative, destination)
        report.update(state_after=after, prior_events_preserved_exactly=True, restart_verified=True)
        resume.save(out, "summary", report)
        resume.save(out, "continuation-receipt", {
            "status": "PASS_SHADOW_STATEFUL_RESTART_CONTINUATION_V1",
            "source_run_id": int(os.environ.get("GITHUB_RUN_ID", "0")),
            "predecessor_run_id": args.source_run, "identity_digest": identity,
            "state_before": before, "state_after": after, "prior_events_preserved_exactly": True,
            "checkpoint_files_sha256": {str(p.relative_to(out)): resume.sha(p)
                for p in sorted(out.rglob("*")) if p.is_file()
                and p.name not in {"summary.json", "continuation-receipt.json"}}})
    print(json.dumps(report, sort_keys=True), flush=True)
    if error:
        raise error
    return 0 if report["status"].startswith("PASS_") else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--source-run", type=int, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--source-updates", type=Path)
    raise SystemExit(main(parser.parse_args()))
