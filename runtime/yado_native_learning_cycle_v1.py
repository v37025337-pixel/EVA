"""Verify fresh learning, refresh one shadow candidate and measure its effect.

This is a bounded orchestration/probe written by the maintainer. Candidate
materialization uses the existing native AST generator. No admission is implied.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
from pathlib import Path
import subprocess
import sys

from yado_active_kernel_contract_v1 import active_kernel_identity
from yado_native_experience_to_runtime_self_rewrite_v3 import synthesize_candidate
from yado_persist_learning_feed_v1 import verified_learning_outputs

ROOT = Path(__file__).resolve().parents[1]
TARGET = "runtime/yado_bounded_autonomous_learning_v1.py"

PROBE = r'''
import ast, importlib.util, json, math, sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.argv[1]).parent))
def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
parent = load('parent_learner', sys.argv[1])
child = load('candidate_learner', sys.argv[2])
expected = json.loads(sys.stdin.read())
assignments = [n for n in ast.parse(Path(sys.argv[2]).read_text()).body
               if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name)
               and t.id == 'LEARNED_EXTERNAL_EVIDENCE_V2' for t in n.targets)]
assert len(assignments) == 1, 'DUPLICATE_LEARNED_BINDING'
assert child.LEARNED_EXTERNAL_EVIDENCE_V2 == expected, 'EFFECTIVE_BINDING_MISMATCH'
rows = []
for code in ('MEMORY_AND_EXPERIENCE', 'CODE_REPAIR', 'NETWORK_EVIDENCE'):
    priority = {'code': code, 'area': code, 'recommended_action': 'learn code network tests'}
    before, after = parent.rank_sources(priority), child.rank_sources(priority)
    assert len(after) == len(child.SOURCE_CATALOG)
    assert {row['id'] for row in after} == {row['id'] for row in child.SOURCE_CATALOG}
    assert all(math.isfinite(row['score']) for row in after)
    assert after == sorted(after, key=lambda row: (-row['score'], row['id']))
    rows.append({'priority': code, 'parent': before, 'candidate': after, 'changed': before != after})
print(json.dumps({'effective_binding': child.LEARNED_EXTERNAL_EVIDENCE_V2,
                  'parent_binding': parent.LEARNED_EXTERNAL_EVIDENCE_V2,
                  'ranking_probes': rows}))
'''


def probe_candidate(parent: Path, candidate: Path, learned: dict) -> dict:
    process = subprocess.run(
        [sys.executable, "-c", PROBE, str(parent.resolve()), str(candidate.resolve())],
        input=json.dumps(learned), capture_output=True, text=True, timeout=30,
    )
    if process.returncode:
        raise ValueError("CANDIDATE_PROBE_FAILED:" + process.stderr[-2000:])
    return json.loads(process.stdout)


def _facts(experience: dict) -> set[tuple[str, str]]:
    return {(row["source_id"], text) for row in experience.get("sources", [])
            for text in row.get("facts", [])}


def run(experience_root: Path, output: Path, root: Path = ROOT) -> dict:
    root, output = Path(root).resolve(), Path(output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    report_path = output / "receipt.json"
    # A failed attempt must replace a stale positive receipt.
    report_path.write_text(json.dumps({"status": "WITHHOLD_UNVERIFIED_LEARNING_CYCLE"}) + "\n")
    identity = active_kernel_identity(root)
    experience, learning_receipt, _ = verified_learning_outputs(experience_root, identity)
    parent = root / TARGET
    parent_source = parent.read_text(encoding="utf-8")
    parent_sha = hashlib.sha256(parent_source.encode()).hexdigest()
    source, learned, safety = synthesize_candidate(parent_source, experience)
    candidate = output / "runtime_candidate.py"
    compile(source, str(candidate), "exec")
    candidate.write_text(source, encoding="utf-8")
    observed = probe_candidate(parent, candidate, learned)
    if synthesize_candidate(source, experience)[0] != source:
        raise ValueError("NON_IDEMPOTENT_CANDIDATE_REFRESH")
    if hashlib.sha256(parent.read_bytes()).hexdigest() != parent_sha:
        raise ValueError("CANONICAL_PARENT_CHANGED_DURING_PROBE")
    # The learner may have just overwritten latest.json in this worktree.
    # Compare against the committed predecessor, never against that new output.
    baseline = json.loads(subprocess.check_output(
        ["git", "show", "HEAD:experience/autonomous/yado-autonomous-learning-latest.json"],
        cwd=root, text=True, timeout=30,
    ))
    old_facts, new_facts = _facts(baseline), _facts(experience)
    behavioral_change = any(row["changed"] for row in observed["ranking_probes"])
    old_binding = {k: v for k, v in observed["parent_binding"].items() if k != "experience_digest"}
    new_binding = {k: v for k, v in learned.items() if k != "experience_digest"}
    if old_binding == new_binding and behavioral_change:
        raise ValueError("RANKING_CHANGED_WITHOUT_NEW_LEARNED_CONTENT")
    report = {
        "schema": "yado.native_learning_cycle.v1",
        "status": "PASS_SHADOW_BINDING_PROBE" if behavioral_change else "NO_MEASURED_BEHAVIOR_GAIN",
        "learning_run_id": experience.get("run_id"),
        "experience_digest": experience["experience_digest"],
        "learning_receipt_sha256": learning_receipt["receipt_sha256"],
        "execution_identity": identity,
        "baseline_experience_digest": baseline.get("experience_digest"),
        "baseline_view": "COMMITTED_HEAD",
        "fact_count": len(new_facts), "novel_fact_count": len(new_facts - old_facts),
        "repeated_fact_count": len(new_facts & old_facts),
        "parent_sha256": parent_sha,
        "candidate_sha256": hashlib.sha256(source.encode()).hexdigest(),
        "candidate_changed": source != parent_source,
        "effective_binding_verified": True, "repeated_generation_idempotent": True,
        "ranking_probes": observed["ranking_probes"],
        "behavior_changed": behavioral_change, "safety_delta": safety,
        "candidate_full_regression_admission": False, "canonical_runtime_mutated": False,
        "capability_gain_proven": False, "automatic_canonical_promotion": False,
        "next_required_capability": "INDEPENDENT_TRANSFER_GAIN_AND_FULL_CANDIDATE_ADMISSION",
    }
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--experience-root", type=Path, default=ROOT)
    parser.add_argument("--output", type=Path, default=ROOT / "audits/yado-native-learning-cycle-v1")
    args = parser.parse_args()
    result = run(args.experience_root, args.output)
    print(json.dumps({k: v for k, v in result.items() if k not in {"ranking_probes", "safety_delta"}}, sort_keys=True))
