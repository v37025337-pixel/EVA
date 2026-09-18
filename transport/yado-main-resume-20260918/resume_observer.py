"""Observer transport: restore JSON state and invoke unchanged main-core methods.
No repair implementation, mutation rule, or corrected source is supplied here.
"""
from pathlib import Path
import copy
import datetime as dt
import hashlib
import json
import lzma
import os
import subprocess
import sys

BASE = "68aed88a9238f7a36a99019b3b2cb63ce68ff120"
PACKED_SHA = "00609402bd2f7f61f28871e0a63c4bc6a13bf44cfa3d352e4c1b3d9a3f924c15"
PARENT_DIGEST = "d3f420ed403a1a527afe8e4a3f5fe98f75e12305c59915bd414e91ebb9c12eb5"
ROOT = Path.cwd()
OUT = Path(os.environ["RUNNER_TEMP"]) / "yado-main-resume"
OUT.mkdir(parents=True, exist_ok=True)
sys.dont_write_bytecode = True
sys.path[:0] = [str(ROOT / "runtime"), str(ROOT / "runtime/yado_rc8_v36")]

def sha(value):
    return hashlib.sha256(value).hexdigest()

def digest(value):
    return sha(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode())

def save(name, value):
    (OUT / name).write_text(json.dumps(value, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")

def signature(genome):
    return {name: {"gene_id": gene.get("gene_id"), "expression": gene.get("expression")}
            for name, gene in genome.get("chromosomes", {}).items()}

# Check every pre-existing file: only transport additions may differ from BASE.
changes = subprocess.check_output(["git", "diff", "--name-only", BASE, "HEAD"], text=True).splitlines()
allowed = {".github/workflows/yado-main-checkpoint-resume-v1.yml",
           "transport/yado-main-resume-20260918/resume_observer.py",
           "transport/yado-main-resume-20260918/checkpoint.part0",
           "transport/yado-main-resume-20260918/checkpoint.part1"}
assert set(changes) <= allowed, ("NON_TRANSPORT_CHANGE", changes)
head = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
tracked = subprocess.check_output(["git", "ls-files", "-z", "runtime", "successor", "canonical", "architecture"]).decode().split("\0")
before = {p: sha(Path(p).read_bytes()) for p in tracked if p and Path(p).is_file()}
packed = b"".join((ROOT / "transport/yado-main-resume-20260918" / ("checkpoint.part" + str(i))).read_bytes() for i in range(2))
assert sha(packed) == PACKED_SHA, "CHECKPOINT_TRANSPORT_HASH_MISMATCH"
parent = json.loads(lzma.decompress(packed))
assert parent["genome_digest"] == PARENT_DIGEST
assert digest({k: v for k, v in parent.items() if k != "genome_digest"}) == PARENT_DIGEST
experience = copy.deepcopy(parent["experience_sources"])
research_state = next(row["native_research_state"] for row in reversed(experience) if "native_research_state" in row)
assert research_state["state_digest"] == "11cee4c7b6fa5bf3e64df0077d8958ac3c85767c43f043489b70508b05605a0f"

from yado_unified_core_peer_systems_learning_v1 import UnifiedYADOCorePeerSystemsLearningV1
core = UnifiedYADOCorePeerSystemsLearningV1(repo_root=ROOT)
audit_before = core.audit()
assert audit_before["pass"] is True, audit_before
restore = core.restore_self_directed_research_state(copy.deepcopy(research_state))
assert core.export_self_directed_research_state() == research_state, "RESEARCH_RESTORE_MISMATCH"
save("input-checkpoint.json", parent)
save("core-before.json", core.snapshot())
save("restore-receipt.json", {"source_base": BASE, "launch_sha": head,
     "input_checkpoint_digest": PARENT_DIGEST, "packed_sha256": PACKED_SHA,
     "resumed_iteration": 10, "restored_research_episodes": len(research_state["episodes"]),
     "restore": restore, "research_state_exact": True,
     "scope": "Genome plus research state restored; canonical registries loaded from main. Not a complete process-memory image."})
print("RESTORED_EXACT_CHECKPOINT", PARENT_DIGEST, len(research_state["episodes"]), flush=True)

# Deny mutation of core files and process spawning during native calls. The existing
# YADO public HTTPS transport retains its own DNS, method, and authority checks.
def guard(event, args):
    if event in {"subprocess.Popen", "os.system", "os.posix_spawn", "os.fork"}:
        raise RuntimeError("NATIVE_PROCESS_SPAWN_DENIED")
    if event == "open":
        path, mode, flags = args
        writing = ((isinstance(mode, str) and any(c in mode for c in "wax+")) or
                   (isinstance(flags, int) and bool(flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND))))
        if writing and not isinstance(path, int) and not Path(path).resolve().is_relative_to(OUT):
            raise RuntimeError("NATIVE_SOURCE_WRITE_DENIED")
sys.addaudithook(guard)
last = research_state["episodes"][-1]
query = last.get("next_goal")
reads = []

def fetch(url):
    if len(reads) >= 8:
        raise RuntimeError("OBSERVER_NETWORK_REQUEST_BUDGET")
    row = {"url": url}
    reads.append(row)
    try:
        page = core.public_web_fetch(url, timeout=5)
        row["receipt"] = page.get("receipt")
        return page
    except Exception as exc:
        row["error"] = type(exc).__name__ + ":" + str(exc)
        raise

research = None
if query:
    research = core.self_directed_research_controller.research(
        query, root_objective=last["root_objective"], fetch=fetch,
        use_search=True, max_sources=2, max_search_results=4, closure_source_target=3)
next_research = core.export_self_directed_research_state()
save("native-search-result.json", research)
save("native-search-transport.json", reads)
save("next-research-state.json", next_research)
control = core.evolutionary_genome_cls(copy.deepcopy(parent), experience_sources=copy.deepcopy(experience)).evolve_once()
feedback = {"role": "GITHUB_MAIN_NATIVE_SEARCH_CONTINUATION", "native_research_state": next_research,
            "native_research_result": research, "transport_receipts": reads,
            "solution_source_supplied": False}
experience.append(feedback)
result = core.evolutionary_genome_cls(copy.deepcopy(parent), experience_sources=experience).evolve_once()
assert digest({k: v for k, v in result.items() if k != "run_digest"}) == result["run_digest"]
child = result["child"]
assert child["parent_genome_digest"] == PARENT_DIGEST
assert digest({k: v for k, v in child.items() if k != "genome_digest"}) == child["genome_digest"]
selected = child if result["selection"] == "CHILD" else result["parent"]
save("native-control.json", control)
save("native-iteration-11.json", result)
save("next-checkpoint.json", selected)
save("next-invocation-experience.json", experience)
new_core = UnifiedYADOCorePeerSystemsLearningV1(repo_root=ROOT)
new_core.restore_self_directed_research_state(copy.deepcopy(next_research))
assert new_core.export_self_directed_research_state() == next_research
assert new_core.audit()["pass"] is True
assert json.loads((OUT / "next-checkpoint.json").read_text()) == selected
unchanged = all(Path(p).is_file() and sha(Path(p).read_bytes()) == h for p, h in before.items())
assert unchanged, "CORE_FILE_CHANGED_DURING_NATIVE_CONTINUATION"
candidates = []
for owner in (result, child):
    for key in ("source", "candidate_source", "generated_source"):
        value = owner.get(key)
        if isinstance(value, str) and value not in candidates:
            candidates.append(value)
for i, value in enumerate(candidates):
    (OUT / ("unverified-native-source-" + str(i) + ".py")).write_text(value, encoding="utf-8")
changed = signature(parent) != signature(child)
summary = {
    "schema": "yado.observer.github_main_checkpoint_continuation.v1",
    "execution_status": "COMPLETED", "source_base_sha": BASE, "launch_sha": head,
    "github_run_id": os.environ.get("GITHUB_RUN_ID"), "github_run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT"),
    "runtime_entrypoint": type(core).__name__, "canonical_core_id": core.CORE_ID,
    "resumed_iteration": 10, "completed_iteration": 11,
    "input_genome_digest": PARENT_DIGEST, "output_genome_digest": selected["genome_digest"],
    "research_episodes_before": len(research_state["episodes"]),
    "research_episodes_after": len(next_research["episodes"]),
    "native_search_query": query, "native_search_status": (research or {}).get("status"),
    "next_native_query": (research or {}).get("next_goal"), "network_requests": len(reads),
    "network_successful_reads": sum("receipt" in row for row in reads),
    "native_selection": result["selection"], "declared_mutation_count": child.get("mutation_count"),
    "declared_fitness_gain": result.get("fitness", {}).get("fitness_gain"),
    "gene_or_expression_changed": changed,
    "same_gene_expression_as_control": signature(child) == signature(control["child"]),
    "native_emitted_source_count": len(candidates), "feedback_retained": feedback in child.get("experience_sources", []),
    "checkpoint_roundtrip_verified": True, "research_roundtrip_verified": True,
    "tracked_core_files_verified_unchanged": len(before), "core_source_unchanged": unchanged,
    "canonical_admission": False, "repair_94_or_96_verified": False,
    "observer_authored_repair": False, "new_third_party_implementation_added": False,
    "continuation_verdict": "NEW_OUTPUT_REQUIRES_INDEPENDENT_VERIFICATION" if changed or candidates else "REPLAY_NO_NEW_REPAIR",
    "regression_scope": "Separate full regression checks unchanged main runtime, not proof of a new repair.",
    "checkpoint_scope": "Saved genome/experience/research plus main canonical registries, not all ephemeral state of every module.",
    "finished_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
}
save("result.json", summary)
save("core-after.json", core.snapshot())
save("core-audits.json", {"before": audit_before, "after": new_core.audit()})
print("NATIVE_CONTINUATION_RESULT", json.dumps(summary, ensure_ascii=False, sort_keys=True), flush=True)
