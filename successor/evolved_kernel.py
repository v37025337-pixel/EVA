"""Deficit-driven Successor candidate built after the real coding baseline.

The inherited G2 runtime is left untouched.  This candidate adds exactly one bounded
programming family discovered as missing in the baseline: arithmetic expression
synthesis over one or two integer inputs.  It is used as a fallback only after the
existing repair engine withholds, and as an explicit program_synthesis task.

The grammar is host-authored; the concrete profile/program is selected from training
examples by the kernel.  No automatic canonical promotion is performed.
"""
from __future__ import annotations

import copy
from typing import Any

from .arithmetic_source import synthesize_candidate, synthesize_repair
from .kernel import SuccessorKernel


class EvolvedSuccessorKernelV1(SuccessorKernel):
    KERNEL_ID = "YADO_SUCCESSOR_DEFICIT_DRIVEN_PROGRAMMING_V1"
    TASK_KINDS = SuccessorKernel.TASK_KINDS + ("program_synthesis",)

    def _dispatch(self, task):
        kind, payload = task.get("kind"), task.get("payload", {})
        if kind == "program_synthesis":
            training = copy.deepcopy(payload.get("training", []))
            candidate = synthesize_candidate(training)
            return {
                **candidate,
                "status": "PASS_PROGRAM_SYNTHESIS_CANDIDATE",
                "capability": "BOUNDED_ARITHMETIC_EXPRESSION_SYNTHESIS_V1",
                "validation_labels_consumed": False,
                "automatic_canonical_promotion": False,
            }
        if kind == "repair":
            inherited = super()._dispatch(task)
            if isinstance(inherited, dict) and inherited.get("source"):
                return inherited
            examples = [(tuple(args), value) for args, value in payload.get("train_examples", [])]
            try:
                fallback = synthesize_repair(
                    str(payload["source"]), str(payload["function_name"]), examples
                )
            except Exception as exc:
                if isinstance(inherited, dict):
                    result = copy.deepcopy(inherited)
                    result["successor_fallback_attempted"] = True
                    result["successor_fallback_status"] = "WITHHOLD"
                    result["successor_fallback_error_type"] = type(exc).__name__
                    result["automatic_canonical_promotion"] = False
                    return result
                raise
            fallback["inherited_repair_status"] = (
                inherited.get("status") if isinstance(inherited, dict) else None
            )
            fallback["inherited_repair_reason"] = (
                inherited.get("reason") if isinstance(inherited, dict) else None
            )
            fallback["successor_fallback_attempted"] = True
            fallback["capability"] = "BOUNDED_ARITHMETIC_REPAIR_FALLBACK_V1"
            return fallback
        return super()._dispatch(task)

    def execute_synthesized(self, candidate: dict[str, Any], inputs: list[dict[str, int]]):
        """Execute only candidates emitted by the reviewed bounded arithmetic grammar."""
        return self.parent.execute_native_source(candidate, copy.deepcopy(inputs))

    def snapshot(self):
        snap = super().snapshot()
        snap.update({
            "kernel_id": self.KERNEL_ID,
            "predecessor_kernel_id": SuccessorKernel.KERNEL_ID,
            "deficit_driven_extension": "BOUNDED_ARITHMETIC_EXPRESSION_SYNTHESIS_V1",
            "extension_origin": "MEASURED_REAL_CODING_BASELINE_DEFICITS",
            "grammar_authorship": "HOST_BOUNDED",
            "program_selection": "KERNEL_TRAINING_ONLY",
            "automatic_canonical_promotion": False,
        })
        return snap


__all__ = ["EvolvedSuccessorKernelV1"]
