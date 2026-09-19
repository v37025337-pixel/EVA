"""Run existing YADO mechanisms on live sources and a verified prior checkpoint.

The assistant authors this experiment, transport and acceptance checks. YADO
selects the concrete native goals and emits the repository-router source using
its inherited grammar. Reading documents does not prove general understanding.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / "runtime")]
OVERLAY = (
    "runtime/yado_bounded_autonomous_learning_v1.py",
    "runtime/yado_cognitive_tri_organ_policy_v3.py",
    "candidates/cognitive/yado_cognitive_tri_organ_policy_v3.py",
    "audits/yado-native-learning-cycle-v1/runtime_candidate.py",
    "audits/yado-native-learning-cycle-v1/receipt.json",
)
HIVE_SHA = "32a9f345f1bb69f0bda237449bbd28b8fb6262f1e1b7a13efff7dafe9d5c764d"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(out, name, value):
    (out / (name + ".json")).write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"stage": name, "status": value.get("status", "RECORDED")}), flush=True)


def restore(checkpoint, out, expected_run):
    receipt = json.loads((checkpoint / "continuation-receipt.json").read_text())
    if (receipt["status"] != "PASS_SHADOW_STATEFUL_RESTART_CONTINUATION_V1"
            or receipt["source_run_id"] != expected_run):
        raise ValueError("UNVERIFIED_PREDECESSOR_CHECKPOINT")
    for relative, expected in receipt["checkpoint_files_sha256"].items():
        path = (checkpoint / relative).resolve()
        if not path.is_relative_to(checkpoint.resolve()) or sha(path) != expected:
            raise ValueError("PREDECESSOR_FILE_MISMATCH:" + relative)
    required = {"kernel.sqlite", "birth/manifest.json"} | {"source-overlay/" + p for p in OVERLAY}
    if not required.issubset(receipt["checkpoint_files_sha256"]):
        raise ValueError("PREDECESSOR_FILES_NOT_PINNED")
    for relative in OVERLAY:
        destination = ROOT / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(checkpoint / "source-overlay" / relative, destination)
    shutil.copytree(checkpoint / "birth", out / "birth")
    with sqlite3.connect((checkpoint / "kernel.sqlite").resolve().as_uri() + "?mode=ro", uri=True) as source:
        with sqlite3.connect(out / "kernel.sqlite") as target:
            source.backup(target)
    return receipt


def external_learning(out):
    from yado_unified_core_self_directed_web_research_v1 import UnifiedYADOCoreSelfDirectedWebResearchV1
    from yado_unified_core_peer_systems_learning_v1 import UnifiedYADOCorePeerSystemsLearningV1
    from yado_unified_core_external_dev_self_development_v1 import UnifiedYADOCoreExternalDevSelfDevelopmentV1
    from yado_external_dev_self_development_v1 import ExternalDevSelfDevelopmentV1

    results = {}
    errors = {}
    # Preserve partial evidence if an independent public service is unavailable.
    for stage in ("ghidra", "repositories", "peers"):
        try:
            if stage == "ghidra":
                core = UnifiedYADOCoreSelfDirectedWebResearchV1(ROOT)
                assert core.audit()["pass"]
                request = json.loads((ROOT / "architecture/yado-ghidra-information-genetics-v1.json").read_text())
                result = core.self_directed_web_research_generations(
                    request["objective"], seed_urls=request["seed_urls"],
                    max_generations=request["max_generations"],
                    max_sources_per_generation=request["max_sources_per_generation"],
                    closure_source_target=request["closure_source_target"],
                    max_search_results=request["max_search_results"], timeout=15)
                state = core.export_self_directed_research_state()
                save(out, "web-memory", state)
                restarted = UnifiedYADOCoreSelfDirectedWebResearchV1(ROOT)
                restarted.restore_self_directed_research_state(state)
                assert restarted.export_self_directed_research_state() == state
                result["memory_roundtrip_verified"] = True
                results[stage] = result
                save(out, stage, result)
                assert result["status"].startswith("PASS_")
            elif stage == "repositories":
                core = UnifiedYADOCoreExternalDevSelfDevelopmentV1(ROOT)
                assert core.audit()["pass"]
                candidate = out / "repository-router.py"
                result = core.external_dev_self_develop(
                    "Learn reusable development patterns from the connected repositories and improve routing from observed deficits",
                    candidate_path=candidate, receipt_path=out / "repository-router-receipt.json", timeout=15)
                results[stage] = result
                save(out, stage, result)
                assert result["status"] == "PASS_SHADOW_EXTERNAL_DEV_SELF_DEVELOPMENT_V1"
                before = ExternalDevSelfDevelopmentV1.evaluate_router_source(
                    (ROOT / "candidates/autonomous/yado_external_dev_capability_router_candidate_v1.py").read_text())
                after = ExternalDevSelfDevelopmentV1.evaluate_router_source(candidate.read_text())
                save(out, "router-comparison", {
                    "status": after["status"], "before_accuracy": before["accuracy"],
                    "after_accuracy": after["accuracy"], "gain": after["accuracy"] - before["accuracy"],
                    "source_sha256": sha(candidate),
                    "benchmark": "EXISTING_FIVE_CASE_ROUTING_BENCHMARK_NOT_NEW_BLIND_TASKS",
                    "general_capability_gain_proven": False,
                })
            else:
                core = UnifiedYADOCorePeerSystemsLearningV1(ROOT)
                assert core.audit()["pass"]
                result = core.study_peer_systems(timeout=15)
                results[stage] = result
                save(out, stage, result)
                assert result["status"] == "PASS_SHADOW_PEER_SYSTEMS_LEARNING_V1"
        except Exception as exc:
            errors[stage] = type(exc).__name__ + ":" + str(exc)[:1000]
            save(out, stage + "-error", {"status": "WITHHOLD", "error": errors[stage]})
    return results, errors


def main(args):
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    save(out, "summary", {"status": "WITHHOLD_INCOMPLETE"})
    predecessor = restore(args.checkpoint, out, args.source_run)
    # Imports happen after restoring the exact sources pinned by the predecessor.
    from successor.kernel import SuccessorKernel
    from successor.endogenous_run import propose_endogenous_goal, run_endogenous_cycles
    from successor.hivemind import CRITERIA, run_issue
    from successor.hivemind_client import HivemindClient

    manifest, state = out / "birth/manifest.json", out / "kernel.sqlite"
    kernel = SuccessorKernel(manifest, state)
    try:
        before = kernel.verify_state()
        assert before == predecessor["state_after"]
        assert kernel.identity == predecessor["identity_digest"]
        prefix = [tuple(row) for row in kernel.db.execute("SELECT * FROM events ORDER BY tick")]
        identity = kernel.identity
    finally:
        kernel.close()
    results, errors = external_learning(out)

    try:
        if sha(args.hive) != HIVE_SHA:
            raise ValueError("HIVEMIND_BINARY_DIGEST_MISMATCH")
        workspace = out / "hivemind-workspace"
        workspace.mkdir()
        env = dict(os.environ, XDG_CONFIG_HOME=str(out / "hivemind-config"))
        subprocess.run([str(args.hive), "init", "--prefix", "YADO", "--no-agentic", "--json"],
                       cwd=workspace, env=env, check=True, timeout=60, capture_output=True, text=True)
        kernel = SuccessorKernel(manifest, state)
        try:
            proposal = propose_endogenous_goal(kernel)
            save(out, "hivemind-kernel-proposal", proposal)
            with HivemindClient([str(args.hive), "mcp-stdio"], workspace / ".hivemind", env=env) as client:
                issue = client.call("hive_create_issue", {
                    "title": "YADO state-derived continuation",
                    "description": json.dumps({"schema": "yado.hivemind.goal.v1", "spec": proposal["spec"],
                                               "budget": 3, "mode": "full"}),
                    "acceptance_criteria": list(CRITERIA), "state": "todo"})
                result = run_issue(kernel, client, "yado-repository-learning-20260919", issue["id"])
                save(out, "hivemind", result)
                assert result["passed"] and result["tracker_state"] == "done"
                tick = kernel.verify_state()["tick"]
                retry = run_issue(kernel, client, "yado-repository-learning-20260919", issue["id"])
                assert retry["goal_id"] == result["goal_id"] and kernel.verify_state()["tick"] == tick
                save(out, "hivemind-retry", {"status": "PASS", "same_goal": True, "no_duplicate_events": True})
                results["hivemind"] = result
        finally:
            kernel.close()
    except Exception as exc:
        errors["hivemind"] = type(exc).__name__ + ":" + str(exc)[:1000]
        save(out, "hivemind-error", {"status": "WITHHOLD", "error": errors["hivemind"]})

    kernel = SuccessorKernel(manifest, state)
    try:
        continuation = run_endogenous_cycles(kernel, cycles=args.cycles, budget=3)
        save(out, "continuation", continuation)
        after = kernel.verify_state()
        events = [tuple(row) for row in kernel.db.execute("SELECT * FROM events ORDER BY tick")]
        assert kernel.identity == identity and events[:len(prefix)] == prefix
        assert after["tick"] > before["tick"]
        assert continuation["cycles_verified"] == args.cycles
        assert all(row["proposal_tick"] > before["tick"] for row in continuation["results"])
    finally:
        kernel.close()
    # Include exact runtime dependencies, not just a SQLite file that cannot reopen.
    for relative in OVERLAY:
        target = out / "source-overlay" / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / relative, target)
    save(out, "continuation-receipt", {
        "status": "PASS_SHADOW_STATEFUL_RESTART_CONTINUATION_V1",
        "source_run_id": int(os.environ.get("GITHUB_RUN_ID", "0")),
        "predecessor_run_id": args.source_run, "identity_digest": identity,
        "state_before": before, "state_after": after,
        "cross_workflow_state_restored": True, "prior_events_preserved_exactly": True,
        "checkpoint_files_sha256": {str(p.relative_to(out)): sha(p) for p in sorted(out.rglob("*"))
                                     if p.is_file() and p.name not in {"summary.json", "continuation-receipt.json"}},
    })
    summary = {
        "status": "PASS_REPOSITORY_LEARNING_AND_STATEFUL_CONTINUATION" if not errors else "WITHHOLD_PARTIAL_CAMPAIGN",
        "tested_commit": os.environ.get("GITHUB_SHA"), "predecessor_run_id": args.source_run,
        "identity_digest": identity, "cross_workflow_state_restored": True,
        "prior_events_preserved_exactly": True, "new_cycles_verified": continuation["cycles_verified"],
        "host_goals_in_continuation": continuation["host_goal_count"],
        "ghidra_research_generations": results.get("ghidra", {}).get("generation_count", 0),
        "repository_sources": results.get("repositories", {}).get("used_source_patterns", []),
        "peer_sources_verified": results.get("peers", {}).get("verified_source_count", 0),
        "hivemind_real_transport_passed": results.get("hivemind", {}).get("passed", False),
        "errors": errors, "state_before": before, "state_after": after,
        "transport_and_experiment_authorship": "ASSISTANT",
        "goal_selection_and_router_emission": "EXISTING_YADO_MECHANISMS",
        "third_party_repository_patches": 0,
        "general_intelligence_established": False, "consciousness_established": False,
        "background_process_running_after_completion": False,
    }
    save(out, "summary", summary)
    print(json.dumps(summary, sort_keys=True), flush=True)
    return 0 if not errors else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--source-run", type=int, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--hive", type=Path, required=True)
    parser.add_argument("--cycles", type=int, default=20)
    raise SystemExit(main(parser.parse_args()))
