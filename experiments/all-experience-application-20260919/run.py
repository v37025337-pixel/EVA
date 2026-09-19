"""Apply available historical components and durable experience with fresh checks.

The assistant supplies this campaign. Existing kernel selectors choose components
and native retries; historical verdicts never replace present measurements.
"""
from __future__ import annotations

import argparse
from collections import Counter
import importlib.util
import json
import os
from pathlib import Path
import secrets
import shutil
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / "runtime"), str(ROOT / "runtime/yado_rc8_v36")]
loader = importlib.util.spec_from_file_location(
    "repository_resume", ROOT / "experiments/repository-learning-resume-20260919/run.py")
resume = importlib.util.module_from_spec(loader)
loader.loader.exec_module(resume)


def main(args):
    from successor.archive import build_archive, ExperienceArchive
    from successor.cognitive import CognitiveLoop, consolidated_stats, replay
    from successor.generation import GenerationKernel, retained_memory
    from successor.generation_tasks import challenge
    from successor.kernel import SuccessorKernel, encode, equivalent, fingerprint
    from successor.runtime_evolution import active_candidates

    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    resume.save(out, "summary", {"status": "WITHHOLD_INCOMPLETE"})
    receipt = resume.restore(args.checkpoint, out, args.source_run)
    for name in ("web-memory.json",):
        if name in receipt["checkpoint_files_sha256"]:
            shutil.copy2(args.checkpoint / name, out / name)
    # Preserve an existing component executor across later invocations. Its
    # frozen archive cannot be replaced underneath an admitted profile.
    component = out / "component-evolution"
    old_component = args.checkpoint / "component-evolution"
    continued = "component-evolution/state.sqlite" in receipt["checkpoint_files_sha256"]
    if continued:
        shutil.copytree(old_component, component)
    else:
        component.mkdir()
    manifest, state = out / "birth/manifest.json", out / "kernel.sqlite"
    kernel = SuccessorKernel(manifest, state)
    before = kernel.verify_state()
    assert before == receipt["state_after"] and kernel.identity == receipt["identity_digest"]
    prefix = [tuple(r) for r in kernel.db.execute("SELECT * FROM events ORDER BY tick")]
    identity = kernel.identity
    report = {"status": "WITHHOLD", "tested_commit": os.environ.get("GITHUB_SHA"),
              "predecessor_run_id": args.source_run, "identity_digest": identity,
              "state_before": before, "campaign_authorship": "ASSISTANT",
              "selection_and_execution": "EXISTING_YADO_MECHANISMS",
              "background_process_running_after_completion": False}
    generation = None
    error = None

    def save_typed(name, value):
        (out / (name + ".typed.json")).write_text(encode(value) + "\n")

    try:
        records = CognitiveLoop(kernel)._records()
        goals = replay(records)
        old_programs = kernel.native_program_status()["verified_programs"]
        old_active = active_candidates(records)
        # Freeze every reachable Git object from all fetched refs, including
        # deleted file history. Keep the inherited birth archive separately.
        archive_path = out / "available-history.sqlite"
        archive_summary = build_archive(ROOT, archive_path)
        archive = ExperienceArchive(archive_path)
        try:
            verification = archive.verify()
            outcomes = dict(archive.db.execute(
                "SELECT reported_outcome,count(*) FROM documents GROUP BY reported_outcome"))
        finally:
            archive.close()
        coverage = {"status": "PASS_AVAILABLE_EXPERIENCE_INTEGRITY",
                    "archive": archive_summary, "archive_verification": verification,
                    "historical_reported_outcomes": outcomes,
                    "native_goals": len(goals),
                    "native_statuses": dict(Counter(g["status"] for g in goals.values())),
                    "native_programs": old_programs, "active_runtime_strategies": sorted(old_active),
                    "self_model": consolidated_stats(records),
                    "self_model_digest": fingerprint(consolidated_stats(records)),
                    "all_archived_documents_semantically_applied": False,
                    "component_adapter_scope": ["LOGIC", "THINKING", "INTELLIGENCE", "CODE"],
                    "historical_claims_used_as_admission_verdicts": False}
        resume.save(out, "experience-coverage", coverage)
        if not continued:
            # Store the new archive once, at the component executor's stable path.
            archive_path.rename(component / "experience.sqlite")
        generation = GenerationKernel(kernel, component / "experience.sqlite", component / "state.sqlite")
        if not continued:
            proposal = generation.propose()
            save_typed("component-proposal", proposal)
            resume.save(out, "selection-summary", {
                "status": "FROZEN_BEFORE_FRESH_EVALUATION", "options": len(proposal["options"]),
                "profile_digest": proposal["profile_digest"],
                "regressing_options_rejected": sum(bool(x["regressions"]) for x in proposal["selection_evidence"])})
            admission = generation.admit()
            save_typed("component-admission", admission)
            assert admission["passed"], "COMPONENT_ADMISSION_WITHHELD"
        else:
            admission = next(r for r in generation.records() if r["kind"] == "ADMISSION")
        selected = generation.snapshot()
        assert selected["component_generation"] == 1
        save_typed("component-active", selected)
        generation.close()
        generation = GenerationKernel(kernel, component / "experience.sqlite", component / "state.sqlite")
        assert generation.snapshot() == selected
        # Five independently drawn batches after freeze and restart. Execute
        # through the active persistent profile, not evaluate(profile, ...).
        executions = []
        for _ in range(5):
            seed = secrets.token_hex(24)
            for task, expected in challenge(seed):
                result = generation.execute(task)
                passed = equivalent(result["result"]["answer"], expected)
                executions.append({"seed": seed, "task": task, "expected": expected,
                                   "execution": result, "passed": passed})
                save_typed("component-application", executions)
                assert passed and result["generation"] == 1
        profile_after = generation.snapshot()
        save_typed("component-after-application", profile_after)
        generation.close()
        generation = None
        resume.save(out, "application-summary", {"status": "PASS_ACTIVE_COMPONENT_APPLICATION",
                    "fresh_tasks": len(executions), "fresh_passed": sum(x["passed"] for x in executions),
                    "profile_digest": selected["profile_digest"], "restart_verified": True})
        # Existing development uses all native observations and verified source
        # memory. No fabricated failed goal or candidate is injected here.
        development = kernel.develop_native_programs(rounds=3)
        save_typed("native-development", development)
        assert all(s["status"] == "COMPLETE" for s in development["sessions"])
        sid = kernel.start_autonomy(budget=120, max_cycles=args.cycles)
        kernel.run_autonomy(max_steps=1000)
        autonomy = kernel.autonomy_snapshot()["sessions"][sid]
        save_typed("native-autonomy", autonomy)
        assert autonomy["status"] == "COMPLETE" and len(autonomy["outcomes"]) == args.cycles
        memory = retained_memory(kernel)
        save_typed("retained-memory", memory)
        assert memory["passed"]
        current = CognitiveLoop(kernel)._records()
        final_programs = kernel.native_program_status()["verified_programs"]
        prior_sources = {x["source_sha256"] for x in old_programs}
        current_sources = {x["source_sha256"] for x in final_programs}
        assert prior_sources <= current_sources
        assert active_candidates(current) == old_active
        report.update(status="PASS_ALL_AVAILABLE_EXPERIENCE_APPLICATION",
                      component_profile_newly_activated=not continued,
                      profile_digest=selected["profile_digest"],
                      fresh_admission_parent_scores=admission["parent"]["scores"],
                      fresh_admission_child_scores=admission["child"]["scores"],
                      active_component_tasks=len(executions), active_component_tasks_passed=len(executions),
                      component_restart_verified=True,
                      native_development_selections=sum(len(s["selections"]) for s in development["sessions"]),
                      native_new_programs=sorted(current_sources - prior_sources),
                      native_cycles=len(autonomy["outcomes"]),
                      native_outcomes=dict(Counter(x["status"] for x in autonomy["outcomes"])),
                      retained_goals=memory["goals"], retained_memory_passed=memory["passed"],
                      active_runtime_strategies_preserved=True,
                      archived_counts=archive_summary["counts"],
                      component_generation_state={k: v for k, v in profile_after.items() if k != "profile"},
                      all_archived_documents_semantically_applied=False)
    except Exception as exc:
        error = exc
        report.update(status="WITHHOLD", error=type(exc).__name__ + ":" + str(exc)[:1000])
    finally:
        if generation is not None:
            generation.close()
        after = kernel.verify_state()
        rows = [tuple(r) for r in kernel.db.execute("SELECT * FROM events ORDER BY tick")]
        assert kernel.identity == identity and rows[:len(prefix)] == prefix
        kernel.close()
        reopened = SuccessorKernel(manifest, state)
        try:
            assert reopened.verify_state() == after
        finally:
            reopened.close()
        for relative in resume.OVERLAY:
            dest = out / "source-overlay" / relative
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / relative, dest)
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
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--source-run", type=int, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--cycles", type=int, choices=range(1, 21), default=10)
    raise SystemExit(main(parser.parse_args()))
