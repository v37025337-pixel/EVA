"""Maintainer-authored run harness; decisions and generators use unchanged YADO.

This experiment produces evidence and isolated candidates, not admission.
Official documentation describes public interfaces, not this assistant's weights.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "runtime"))

from yado_active_kernel_contract_v1 import active_kernel_identity
from yado_autonomous_deep_development_v1 import build_plan
from yado_bounded_autonomous_learning_v1 import digest, evidence_facts, normalized_text
from yado_cross_disciplinary_internet_learning_v1 import run as cross_run
from yado_native_experience_to_runtime_self_rewrite_v3 import synthesize_candidate
from yado_native_learning_cycle_v1 import probe_candidate
from yado_unified_core_self_directed_web_research_v1 import UnifiedYADOCoreSelfDirectedWebResearchV1

BASE = "b53c828e14990961eef67ee7a700fe3261a1019e"
DOCS = [
    ("OPENAI_TOOLS", "https://developers.openai.com/api/docs/guides/tools.md"),
    ("OPENAI_SHELL", "https://developers.openai.com/api/docs/guides/tools-shell.md"),
    ("OPENAI_EVALS", "https://developers.openai.com/api/docs/guides/evals.md"),
]


def save(out, name, value):
    path = out / (name + ".json")
    path.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n")
    # The completed log is a second transport for exact JSON evidence.
    print("YADO_EVIDENCE " + json.dumps({"name": name, "value": value}, sort_keys=True), flush=True)


def inspect_environment(identity):
    return {
        "schema": "yado.measured_execution_environment.v1",
        "probe_authorship": "MAINTAINER_AUTHORED_STDLIB_OBSERVATION",
        "os": platform.system(), "release": platform.release(),
        "machine": platform.machine(), "python": platform.python_version(),
        "cpu_count": os.cpu_count(), "free_disk_bytes": shutil.disk_usage(ROOT).free,
        "git_available": shutil.which("git") is not None,
        "execution_context": "GITHUB_ACTIONS" if os.getenv("GITHUB_ACTIONS") == "true" else "LOCAL",
        "run_id": os.getenv("GITHUB_RUN_ID", "LOCAL"),
        "tested_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "canonical_identity": identity,
        "private_environment_variables_collected": False,
        "assistant_weights_available": False,
        "assistant_private_internals_observed": False,
    }


def documentation(core):
    sources, failures = [], []
    for source_id, url in DOCS:
        try:
            page = core.public_web_fetch(url, timeout=15, max_redirects=0)
            receipt = page["receipt"]
            assert receipt["http_status"] == 200 and receipt["read_only"]
            text = normalized_text(page["content"], receipt["content_type"].split(";", 1)[0])
            found = evidence_facts(text, {"tool", "model", "environment", "eval", "shell", "agent"})
            # Preserve a short evidence excerpt; the entire page is read in memory.
            facts = [" ".join(found[0].split()[:25])] if found else []
            if not facts:
                raise ValueError("NO_RELEVANT_DOCUMENT_TEXT")
            sources.append({"source_id": source_id, "url": url, "facts": facts,
                            "fact_count": len(facts), "network": {"host": receipt["final_host"]},
                            "provenance": receipt, "document_chars_read": len(text)})
        except Exception as exc:
            failures.append({"source_id": source_id, "url": url,
                             "error": type(exc).__name__ + ":" + str(exc)[:240]})
    return {"schema": "yado.official_assistant_documentation_experiment.v1",
            "sources": sources, "failures": failures,
            "scope": "PUBLIC_OPENAI_INTERFACES_NOT_PRIVATE_MODEL_INTERNALS",
            "status": "PASS_DOCUMENT_ACQUISITION" if len(sources) == len(DOCS) else "PARTIAL_DOCUMENT_ACQUISITION"}


def native_probe(out, experience):
    parent = ROOT / "runtime/yado_bounded_autonomous_learning_v1.py"
    source, learned, safety = synthesize_candidate(parent.read_text(), experience)
    candidate = out / "native_runtime_candidate.py"
    compile(source, str(candidate), "exec")
    candidate.write_text(source)
    observed = probe_candidate(parent, candidate, learned)
    assert synthesize_candidate(source, experience)[0] == source
    return {
        "schema": "yado.documentation_conditioned_native_probe.v1",
        "status": "PASS_ISOLATED_BINDING_PROBE",
        "experience_digest": experience["experience_digest"],
        "candidate_sha256": hashlib.sha256(candidate.read_bytes()).hexdigest(),
        "effective_binding_verified": observed["effective_binding"] == learned,
        "ranking_probes": observed["ranking_probes"],
        "behavior_changed": any(r["changed"] for r in observed["ranking_probes"]),
        "safety_delta": safety, "idempotent": True,
        "full_regression_admission": False, "capability_gain_proven": False,
        "canonical_promotion": False,
        "limitation": "Ranking changes are not transfer improvement; catalog remains the admitted catalog.",
    }


def main(out):
    out.mkdir(parents=True, exist_ok=True)
    save(out, "summary", {"status": "WITHHOLD_INCOMPLETE_RUN"})
    identity = active_kernel_identity(ROOT)
    subprocess.run(["git", "merge-base", "--is-ancestor", BASE, "HEAD"], cwd=ROOT, check=True)
    environment = inspect_environment(identity)
    save(out, "environment", environment)
    core = UnifiedYADOCoreSelfDirectedWebResearchV1(ROOT)
    assert core.audit()["pass"] is True
    plan = build_plan(ROOT)
    save(out, "kernel_selected_development_plan", plan)
    docs = documentation(core)
    save(out, "official_documentation", docs)

    config = json.loads((ROOT / "architecture/yado-cross-disciplinary-internet-learning-v1.json").read_text())
    self_model = json.loads((ROOT / "architecture/developmental-self-model-overlay.json").read_text())
    cross = cross_run(config, self_model)
    save(out, "cross_disciplinary_learning", cross)

    # The initial objective is user-directed. Residual goals and research decisions
    # are produced by the admitted controller, not rewritten by this harness.
    research = core.self_directed_web_research_generations(
        "Python runtime environment network documentation data verification",
        seed_urls=["https://docs.python.org/3/library/platform.html",
                   "https://developer.mozilla.org/en-US/docs/Web/HTTP/Overview"],
        max_generations=2, max_sources_per_generation=2,
        closure_source_target=3, max_search_results=12, timeout=8,
    )
    # Shorten displayed excerpts without modifying causal memory or decisions.
    for generation in research["generations"]:
        for source in generation.get("sources", []):
            source["excerpts"] = [" ".join(" ".join(source.get("excerpts", [])).split()[:25])]
    save(out, "self_directed_research", research)
    state = core.export_self_directed_research_state()
    save(out, "research_memory", state)
    restored = UnifiedYADOCoreSelfDirectedWebResearchV1(ROOT)
    restored.restore_self_directed_research_state(state)
    assert restored.export_self_directed_research_state() == state

    # Explicitly authored adapter: factual observations -> existing native generator.
    # This is not a fabricated bounded-learner receipt and is not written to its feed.
    exp = {"schema": "yado.environment_documentation_experience.v1",
           "run_id": environment["run_id"], "execution_identity": identity,
           "environment_digest": digest(environment), "research_memory_digest": state["state_digest"],
           "cross_disciplinary_digest": cross["evidence_digest"],
           "sources": docs["sources"], "failures": docs["failures"],
           "adapter_authorship": "MAINTAINER_AUTHORED_EXPERIMENT",
           "admitted_to_canonical_learning_feed": False}
    exp["experience_digest"] = digest(exp)
    save(out, "experience", exp)
    probe = native_probe(out, exp) if exp["sources"] else {"status": "WITHHOLD_NO_DOCUMENTATION"}
    save(out, "native_probe", probe)

    assert active_kernel_identity(ROOT) == identity
    assert not subprocess.check_output(["git", "diff", "--name-only", "--", "runtime", "successor", "canonical", "architecture"], cwd=ROOT).strip()
    checks = {"official_documents_read": len(docs["sources"]) == 3,
              "internet_learning": cross["status"] == "PASS_REAL_INTERNET_CROSS_DISCIPLINARY_EXPERIENCE",
              "research_executed": bool(research["generations"]),
              "research_memory_restored": restored.export_self_directed_research_state() == state,
              "native_candidate_verified": probe.get("effective_binding_verified") is True,
              "canonical_unchanged": True}
    save(out, "summary", {"schema": "yado.environment_internet_development_run.v1",
                          "status": "PASS_BOUNDED_RUN" if all(checks.values()) else "PARTIAL_BOUNDED_RUN",
                          "checks": checks, "run_id": environment["run_id"],
                          "tested_commit": environment["tested_commit"], "execution_identity": identity,
                          "official_documents_read": len(docs["sources"]),
                          "external_sources_read": cross["acquisition"]["fetched_sources"],
                          "disciplines": cross["acquisition"]["disciplines_covered"],
                          "research_status": research["status"], "remaining_research_goal": research["remaining_goal"],
                          "candidate_behavior_changed": probe.get("behavior_changed", False),
                          "capability_gain_proven": False, "canonical_promotion": False})


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    main(parser.parse_args().output.resolve())
