"""Entry point that enriches repair evidence without exposing hidden holdout labels."""
from __future__ import annotations

from .arithmetic_source import select_expression
from . import real_coding_self_improvement_run as proof
from .real_coding_intelligence_run import run_repair as inherited_run_repair


def audited_run_repair(kernel, task, head):
    row = inherited_run_repair(kernel, task, head)
    if row.get("repair_mode") == "SUCCESSOR_ARITHMETIC_FALLBACK_V1":
        training = []
        for args, expected in task["rows"][:10]:
            training.append({"input": dict(zip(task["args"], args)), "expected": expected})
        selected = select_expression(training)
        row["selected"] = selected["program"]
        row["profile_attempts"] = selected["attempts"]
        row["repair_profile_evidence_uses_training_only"] = True
    return row


# The proof module resolves this global when _repair_rows runs.
proof.run_repair = audited_run_repair


if __name__ == "__main__":
    raise SystemExit(proof.main())
