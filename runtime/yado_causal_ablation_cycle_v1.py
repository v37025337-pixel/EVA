from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parent.parent
DEFAULT_GOAL = REPO / "candidates/autonomous/yado-endogenous-goal-genesis-v1.json"
DEFAULT_HISTORY = REPO / "receipts/yado-g2-raw-representation-v5-canonical-admission-v1-run-33900049280.json"
DEFAULT_RUNTIME = REPO / "runtime/yado_rc8_v36"
DEFAULT_OUT = REPO / "candidates/autonomous/yado-causal-ablation-cycle-v1.json"
EXPECTED_GOAL = "KERNEL_G2_RAW_REPRESENTATION_V4_ROBUSTNESS_SELF_EVOLUTION_V2"
EXPECTED_ACTION = "CAUSAL_ABLATION_OF_CANDIDATE_IMPROVEMENT"
HISTORICAL_CANDIDATE_SHA256 = "caca65d80ed4289ea4a2f8490a3296586163283975840897478954219016bce1"


def canon(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)


def digest(value: Any) -> str:
    return hashlib.sha256(canon(value).encode("utf-8")).hexdigest()


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def run(cmd: list[str], cwd: Path, timeout: int = 900) -> dict[str, Any]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(cwd) + os.pathsep + env.get("PYTHONPATH", "")
    cp = subprocess.run(cmd, cwd=cwd, env=env, text=True, capture_output=True, timeout=timeout)
    return {
        "cmd": cmd,
        "returncode": cp.returncode,
        "stdout_tail": cp.stdout[-12000:],
        "stderr_tail": cp.stderr[-12000:],
    }


def locate_runtime_source(root: Path) -> Path:
    candidates = sorted(root.rglob("runtime.py"))
    scored: list[tuple[int, Path]] = []
    for path in candidates:
        try:
            text = path.read_text(encoding="utf-8")
        except Exception:
            continue
        score = 0
        if "raw_representation_consumers" in text:
            score += 100
        if "raw_processor" in text:
            score += 10
        if "router" in text:
            score += 5
        if "/yado/core/" in path.as_posix():
            score += 20
        scored.append((score, path))
    if not scored or scored[-1][0] < 100:
        raise RuntimeError("RAW_REPRESENTATION_RUNTIME_SOURCE_NOT_FOUND")
    return sorted(scored, key=lambda x: (x[0], x[1].as_posix()))[-1][1]


def read_consumers(source: str) -> list[str]:
    m = re.search(r"self\.raw_representation_consumers\s*=\s*\[([^\]]*)\]", source)
    if not m:
        raise RuntimeError("RAW_REPRESENTATION_CONSUMERS_ASSIGNMENT_NOT_FOUND")
    return re.findall(r"['\"]([^'\"]+)['\"]", m.group(1))


def apply_historical_v5_candidate(source: str) -> tuple[str, int]:
    # Historical V5's one semantic mutation: add router as a canonical raw consumer.
    pattern = re.compile(
        r"self\.raw_representation_consumers\s*=\s*\[\s*(['\"])raw_processor\1\s*\]"
    )

    def repl(match: re.Match[str]) -> str:
        q = match.group(1)
        return f"self.raw_representation_consumers = [{q}raw_processor{q}, {q}router{q}]"

    return pattern.subn(repl, source, count=1)


def pytest_suite(root: Path) -> dict[str, Any]:
    tests = root / "tests"
    if not tests.exists():
        return {"available": False, "returncode": None, "reason": "NO_RUNTIME_TEST_DIRECTORY"}
    result = run([sys.executable, "-m", "pytest", "-q", "tests"], cwd=root)
    result["available"] = True
    return result


def generate(goal: dict[str, Any], historical: dict[str, Any], runtime_root: Path) -> dict[str, Any]:
    if goal.get("selected_goal") != EXPECTED_GOAL:
        raise RuntimeError(f"UNEXPECTED_ENDOGENOUS_GOAL:{goal.get('selected_goal')}")
    selected_action = (goal.get("selected_action") or {}).get("action")
    if selected_action != EXPECTED_ACTION:
        raise RuntimeError(f"UNEXPECTED_ENDOGENOUS_ACTION:{selected_action}")
    if goal.get("host_supplied_goal") is not False or goal.get("host_selected_goal") is not False:
        raise RuntimeError("GOAL_NOT_ENDOGENOUS")
    if (goal.get("trigger") or {}).get("repair_queue_empty") is not True:
        raise RuntimeError("REPAIR_QUEUE_NOT_EMPTY")
    contract = goal.get("execution_contract") or {}
    if contract.get("canonical_direct_write") is not False or contract.get("automatic_main_mutation") is not False:
        raise RuntimeError("CANONICAL_WRITE_NOT_FORBIDDEN")

    hist_text = canon(historical)
    if "WITHHOLD" not in hist_text:
        raise RuntimeError("HISTORICAL_V5_WITHHOLD_NOT_PROVEN")
    if HISTORICAL_CANDIDATE_SHA256 not in hist_text:
        raise RuntimeError("HISTORICAL_V5_CANDIDATE_DIGEST_NOT_PROVEN")

    source_path = locate_runtime_source(runtime_root)
    rel_source = source_path.relative_to(runtime_root)
    original = source_path.read_text(encoding="utf-8")
    control_consumers = read_consumers(original)
    if control_consumers != ["raw_processor"]:
        raise RuntimeError(f"CANONICAL_V4_CONSUMER_INVARIANT_CHANGED:{control_consumers}")

    with tempfile.TemporaryDirectory(prefix="yado-ablation-") as td:
        td_path = Path(td)
        control = td_path / "control"
        treatment = td_path / "treatment"
        shutil.copytree(runtime_root, control)
        shutil.copytree(runtime_root, treatment)

        treatment_source = treatment / rel_source
        treatment_text, changed = apply_historical_v5_candidate(treatment_source.read_text(encoding="utf-8"))
        if changed != 1:
            raise RuntimeError(f"HISTORICAL_V5_TREATMENT_PATCH_COUNT:{changed}")
        treatment_source.write_text(treatment_text, encoding="utf-8")

        control_source_text = (control / rel_source).read_text(encoding="utf-8")
        treatment_source_text = treatment_source.read_text(encoding="utf-8")
        control_consumers_after = read_consumers(control_source_text)
        treatment_consumers = read_consumers(treatment_source_text)

        control_compile = run([sys.executable, "-m", "compileall", "-q", "."], cwd=control)
        treatment_compile = run([sys.executable, "-m", "compileall", "-q", "."], cwd=treatment)
        control_tests = pytest_suite(control)
        treatment_tests = pytest_suite(treatment)

    compile_ok = control_compile["returncode"] == 0 and treatment_compile["returncode"] == 0
    control_invariant_ok = control_consumers_after == ["raw_processor"]
    treatment_preserves_invariant = treatment_consumers == ["raw_processor"]
    fresh_regression_signal = (
        bool(control_tests.get("available"))
        and control_tests.get("returncode") == 0
        and treatment_tests.get("returncode") not in (0, None)
    )

    historical_target_gain = {
        "source": str(DEFAULT_HISTORY.relative_to(REPO)),
        "candidate_sha256": HISTORICAL_CANDIDATE_SHA256,
        "historical_verdict": historical.get("verdict") or historical.get("status") or "WITHHOLD",
        "positive_lanes_reported": [
            "HOLDOUT_BLOCK/ROUTER",
            "DISCOURSE_CHAT/ROUTER",
            "ROI_BBOX/ROUTER",
            "AUTO_ENABLE_FOR_NONZERO_CAMERA_INDEX/ROUTER",
        ],
        "negative_lane_reported": "NO_RAW_KEEP_CHAT/CHAT",
        "note": "Historical receipt is prior evidence only; the fresh experiment below independently replays the candidate against the current reconstructed canonical runtime.",
    }

    # The treatment intentionally replays the rejected candidate. A coupling violation is itself
    # a fresh causal counterexample; a failing treatment test suite strengthens but is not required
    # for the rejection because the canonical consumer invariant is explicit and machine-checked.
    if not compile_ok or not control_invariant_ok:
        verdict = "INVALID_EXPERIMENT"
        next_action = "REPAIR_EXPERIMENT_HARNESS_AND_REPEAT_IDENTICAL_ABLATION"
    elif treatment_preserves_invariant:
        verdict = "HISTORICAL_CANDIDATE_NOT_REPRODUCED"
        next_action = "REINSPECT_CANDIDATE_PROVENANCE_BEFORE_REVALIDATION"
    else:
        verdict = "REJECT_AND_REVISE_CANDIDATE"
        next_action = "EXPERIENCE_GUIDED_SHADOW_REDERIVATION_PRESERVE_CANONICAL_COUPLING"

    report: dict[str, Any] = {
        "schema": "yado.causal_ablation_cycle.v1",
        "status": "PASS_SHADOW_CAUSAL_ABLATION_CYCLE_V1" if verdict == "REJECT_AND_REVISE_CANDIDATE" else verdict,
        "canonical_mutation": False,
        "architecture_mutation": False,
        "g3_genesis_performed": False,
        "consciousness_claimed": False,
        "goal_provenance": {
            "goal": goal.get("selected_goal"),
            "action": selected_action,
            "goal_source": goal.get("goal_source"),
            "host_supplied_goal": goal.get("host_supplied_goal"),
            "host_selected_goal": goal.get("host_selected_goal"),
            "goal_receipt_sha256": goal.get("receipt_sha256"),
        },
        "candidate_provenance": historical_target_gain,
        "experiment": {
            "design": "PAIRED_CONTROL_TREATMENT_REPLAY_OF_HISTORICAL_V5_CANDIDATE_ON_CURRENT_RECONSTRUCTED_RUNTIME",
            "runtime_source": rel_source.as_posix(),
            "control": {
                "raw_representation_consumers": control_consumers_after,
                "compile": control_compile,
                "tests": control_tests,
            },
            "treatment": {
                "mutation": "ADD_ROUTER_TO_RAW_REPRESENTATION_CONSUMERS",
                "raw_representation_consumers": treatment_consumers,
                "compile": treatment_compile,
                "tests": treatment_tests,
            },
            "causal_delta": {
                "consumer_set_added": sorted(set(treatment_consumers) - set(control_consumers_after)),
                "canonical_consumer_invariant_preserved": treatment_preserves_invariant,
                "fresh_test_regression_signal": fresh_regression_signal,
                "compile_ok": compile_ok,
            },
        },
        "causal_evaluation": {
            "verdict": verdict,
            "reason": (
                "Historical V5 had useful routing gains, but replaying its defining mutation adds router to the canonical raw consumer set. "
                "That violates the current V4 coupling invariant; therefore the useful effect must be re-derived without changing raw_representation_consumers."
                if verdict == "REJECT_AND_REVISE_CANDIDATE"
                else "Experiment did not satisfy the preregistered causal decision rule."
            ),
            "admit_candidate": False,
            "automatic_main_mutation": False,
        },
        "self_selected_next_action": next_action,
        "next_action_constraints": {
            "preserve_raw_representation_consumers": ["raw_processor"],
            "preserve_no_raw_chat_semantics": True,
            "preserve_recorder_activation_semantics": True,
            "fresh_counterexample_required": True,
            "full_regression_required_before_admission": True,
            "full_kernel_audit_required_before_admission": True,
            "canonical_direct_write": False,
        },
        "semantic_boundary": "This is a bounded causal experiment binding an endogenous developmental goal to action and evaluation. It does not establish consciousness, general agency, or permission for canonical self-modification.",
    }
    report["receipt_sha256"] = digest(report)
    return report


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--goal", default=str(DEFAULT_GOAL))
    ap.add_argument("--history", default=str(DEFAULT_HISTORY))
    ap.add_argument("--runtime", default=str(DEFAULT_RUNTIME))
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    args = ap.parse_args()
    report = generate(load(Path(args.goal)), load(Path(args.history)), Path(args.runtime))
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": report["status"],
        "goal": report["goal_provenance"]["goal"],
        "action": report["goal_provenance"]["action"],
        "causal_verdict": report["causal_evaluation"]["verdict"],
        "fresh_test_regression_signal": report["experiment"]["causal_delta"]["fresh_test_regression_signal"],
        "next_action": report["self_selected_next_action"],
        "canonical_mutation": report["canonical_mutation"],
        "receipt_sha256": report["receipt_sha256"],
    }, indent=2, sort_keys=True))
    return 0 if report["causal_evaluation"]["verdict"] == "REJECT_AND_REVISE_CANDIDATE" else 2


if __name__ == "__main__":
    raise SystemExit(main())
