"""Re-execute existing bounded cognition gates; distinguish repeats from gains."""
import hashlib
import importlib
import json
from pathlib import Path
import sys
import shutil

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "runtime"), str(ROOT / "runtime/yado_rc8_v36")]
MODULES = (
    "yado_relational_causal_logic_holdout_v1",
    "yado_thinking_contextual_holdout_v1",
    "yado_intelligence_transfer_holdout_v1",
    "yado_memory_experience_holdout_v1",
    "yado_cognitive_integration_holdout_v1",
)


def main():
    rows = []
    originals = {}
    results_dir = Path(__file__).parent / "cognitive-results"
    results_dir.mkdir(exist_ok=True)
    try:
        for name in MODULES:
            module = importlib.import_module(name)
            originals[module.OUT] = module.OUT.read_bytes()
            originals[module.CAP] = module.CAP.read_bytes()
            previous = json.loads(module.OUT.read_text())
            previous_source = hashlib.sha256(module.CAP.read_bytes()).hexdigest()
            result = module.run()
            if not result["status"].startswith("PASS_"):
                raise ValueError("COGNITIVE_GATE_FAILED:" + name)
            for path in (module.OUT, module.CAP):
                shutil.copy2(path, results_dir / path.name)
            rows.append({
                "generated_receipt": (results_dir / module.OUT.name).relative_to(ROOT).as_posix(),
                "generated_candidate": (results_dir / module.CAP.name).relative_to(ROOT).as_posix(),
                "module": name, "status": result["status"],
                "receipt": module.OUT.relative_to(ROOT).as_posix(),
                "receipt_sha256": hashlib.sha256(module.OUT.read_bytes()).hexdigest(),
                "candidate_sha256": hashlib.sha256(module.CAP.read_bytes()).hexdigest(),
                "candidate_source_changed": previous_source != hashlib.sha256(module.CAP.read_bytes()).hexdigest(),
                "previous_selected_scores": previous.get("selected_scores"),
                "selected_scores": result.get("selected_scores"),
                "fresh_ablation_drops": result.get("fresh_ablation_drops"),
            })
            print(json.dumps({"module": name, "status": result["status"]}), flush=True)
    finally:
        for path, content in originals.items():
            path.write_bytes(content)
    report = {
        "status": "PASS_EXISTING_COGNITIVE_GATES_REEXECUTED",
        "evaluations": rows,
        "benchmark_scope": "REPEATED_EXISTING_FIXED_SEEDS_NOT_NEW_BLIND_TASKS",
        "general_capability_gain_proven": False,
        "scope": "Shadow component and integration validation; no automatic capability promotion.",
    }
    (Path(__file__).parent / "cognitive-verification.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
