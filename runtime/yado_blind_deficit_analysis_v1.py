"""State-derived deficit analysis for repeated blind benchmark receipts."""
from __future__ import annotations
import json
import sys
from pathlib import Path

PASS = "PASS_KERNEL_DERIVED_BLIND_DEFICIT_ANALYSIS_V1"

def analyze(data: dict) -> dict:
    runs = data.get("source_runs", [])
    if not runs:
        raise ValueError("NO_SOURCE_RUNS")
    domains = sorted(runs[0]["per_benchmark"])
    rows = []
    for domain in domains:
        samples = [run["per_benchmark"][domain] for run in runs]
        total = sum(int(s["total"]) for s in samples)
        correct = sum(int(s["correct"]) for s in samples)
        unresolved = sum(int(s["unresolved"]) for s in samples)
        accuracy = correct / total
        unresolved_rate = unresolved / total
        scores = [float(s["accuracy"]) for s in samples]
        rows.append({
            "domain": domain,
            "runs": len(samples),
            "correct": correct,
            "total": total,
            "unresolved": unresolved,
            "accuracy": accuracy,
            "unresolved_rate": unresolved_rate,
            "deficit_score": (1.0 - accuracy) + unresolved_rate,
            "repeat_consistent": len(set(scores)) == 1,
        })
    rows.sort(key=lambda row: (-row["deficit_score"], row["domain"]))
    selected = rows[0]
    names = {
        "gsm8k": ("MATHEMATICAL_REASONING_AND_NUMERIC_GENERALIZATION",
                  "derive, test and retain arithmetic decomposition and multi-step reasoning"),
        "humaneval": ("CODE_GENERATION_AND_EXECUTION_ADAPTER_COVERAGE",
                      "expand source-generation families, compile, execute and repair on holdouts"),
        "openbookqa": ("EVIDENCE_RETRIEVAL_AND_SEMANTIC_GROUNDING",
                       "improve fact retrieval, disambiguation and answer selection"),
    }
    deficit, action = names[selected["domain"]]
    return {
        "schema": "yado.blind_deficit_analysis.v1",
        "status": PASS,
        "source_run_ids": [run["run_id"] for run in runs],
        "source_response_digests": sorted({run["response_digest"] for run in runs}),
        "source_ground_truth_digests": sorted({run["sealed_ground_truth_digest"] for run in runs}),
        "repeat_consistency": all(row["repeat_consistent"] for row in rows),
        "selected_deficit": deficit,
        "selected_domain": selected["domain"],
        "selected_action": action,
        "ranking": rows,
        "limitations": [
            "bounded benchmark families",
            "externally authored benchmark contracts",
            "functional deficit evidence, not general intelligence or consciousness",
        ],
        "boundaries": data["boundaries"],
    }

def main() -> int:
    source = Path(sys.argv[1])
    target = Path(sys.argv[2])
    report = analyze(json.loads(source.read_text()))
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({
        "status": report["status"],
        "selected_deficit": report["selected_deficit"],
        "selected_domain": report["selected_domain"],
        "repeat_consistency": report["repeat_consistency"],
    }, ensure_ascii=False))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
