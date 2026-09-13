"""Second deficit-driven Successor candidate after the frozen V2 baseline.

V1 remains intact and is always tried first.  V2 adds only bounded families that are
supported by measured deficits or fresh transfer evidence: bitwise integer source
synthesis, small one-variable integer polynomials, and generic boolean comparison
predicates when BOTH boolean classes are present in training.  The frozen not_gate
split is still intentionally not learnable because its training data contains only
one class and therefore does not identify the hidden branch.
"""
from __future__ import annotations

import copy

from .evolved_kernel import EvolvedSuccessorKernelV1
from .generalized_source_v2 import synthesize_candidate_v2, synthesize_repair_v2
from .generalized_boolean_v2 import (
    synthesize_boolean_candidate_v2,
    synthesize_boolean_repair_v2,
)


class EvolvedSuccessorKernelV2(EvolvedSuccessorKernelV1):
    KERNEL_ID = "YADO_SUCCESSOR_DEFICIT_DRIVEN_PROGRAMMING_V2"

    def _dispatch(self, task):
        kind, payload = task.get("kind"), task.get("payload", {})
        if kind == "program_synthesis":
            try:
                inherited = super()._dispatch(task)
                if isinstance(inherited, dict) and inherited.get("source"):
                    inherited = copy.deepcopy(inherited)
                    inherited["v2_fallback_attempted"] = False
                    return inherited
            except Exception as exc:
                inherited = {
                    "status": "WITHHOLD_V1_PROGRAM_SYNTHESIS",
                    "reason": type(exc).__name__,
                }

            training = copy.deepcopy(payload.get("training", []))
            generalized_error = None
            try:
                candidate = synthesize_candidate_v2(training)
            except Exception as exc:
                generalized_error = type(exc).__name__
                try:
                    candidate = synthesize_boolean_candidate_v2(training)
                except Exception as boolean_exc:
                    result = copy.deepcopy(inherited) if isinstance(inherited, dict) else {}
                    result.update({
                        "v2_fallback_attempted": True,
                        "v2_fallback_status": "WITHHOLD",
                        "v2_fallback_error_type": type(boolean_exc).__name__,
                        "v2_generalized_error_type": generalized_error,
                        "automatic_canonical_promotion": False,
                    })
                    return result
            return {
                **candidate,
                "status": "PASS_PROGRAM_SYNTHESIS_CANDIDATE_V2",
                "capability": "BOUNDED_SECOND_CYCLE_PROGRAM_SYNTHESIS_V2",
                "validation_labels_consumed": False,
                "v2_fallback_attempted": True,
                "automatic_canonical_promotion": False,
            }

        if kind == "repair":
            try:
                inherited = super()._dispatch(task)
            except Exception as exc:
                inherited = {"status": "WITHHOLD_V1_REPAIR", "reason": type(exc).__name__}
            if isinstance(inherited, dict) and inherited.get("source"):
                result = copy.deepcopy(inherited)
                result["v2_fallback_attempted"] = False
                return result
            examples = [(tuple(args), value) for args, value in payload.get("train_examples", [])]
            generalized_error = None
            try:
                fallback = synthesize_repair_v2(
                    str(payload["source"]), str(payload["function_name"]), examples
                )
            except Exception as exc:
                generalized_error = type(exc).__name__
                try:
                    fallback = synthesize_boolean_repair_v2(
                        str(payload["source"]), str(payload["function_name"]), examples
                    )
                except Exception as boolean_exc:
                    result = copy.deepcopy(inherited) if isinstance(inherited, dict) else {}
                    result.update({
                        "v2_fallback_attempted": True,
                        "v2_fallback_status": "WITHHOLD",
                        "v2_fallback_error_type": type(boolean_exc).__name__,
                        "v2_generalized_error_type": generalized_error,
                        "automatic_canonical_promotion": False,
                    })
                    return result
            fallback["inherited_repair_status"] = (
                inherited.get("status") if isinstance(inherited, dict) else None
            )
            fallback["inherited_repair_reason"] = (
                inherited.get("reason") if isinstance(inherited, dict) else None
            )
            fallback["v2_fallback_attempted"] = True
            fallback["capability"] = "BOUNDED_SECOND_CYCLE_REPAIR_FALLBACK_V2"
            return fallback

        return super()._dispatch(task)

    def snapshot(self):
        snap = super().snapshot()
        snap.update({
            "kernel_id": self.KERNEL_ID,
            "predecessor_kernel_id": EvolvedSuccessorKernelV1.KERNEL_ID,
            "second_cycle_extension": "BOUNDED_BITWISE_POLYNOMIAL_AND_IDENTIFIABLE_BOOLEAN_SYNTHESIS_V2",
            "second_cycle_origin": "FROZEN_SECOND_CYCLE_BASELINE_V2_PLUS_FRESH_TRANSFER_DEFICIT",
            "grammar_authorship": "HOST_BOUNDED",
            "program_selection": "KERNEL_TRAINING_ONLY",
            "boolean_profile_requires_both_training_classes": True,
            "ambiguous_not_gate_special_case_added": False,
            "automatic_canonical_promotion": False,
        })
        return snap


__all__ = ["EvolvedSuccessorKernelV2"]
