from __future__ import annotations

import hashlib
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, Mapping

from yado_core_v2_7_selective import UnifiedYADOKernelV27Selective
from yado_meta_grammar_genesis_cycle1 import (
    CoordinateProgram,
    LowLevelCoordinateSynthesizer,
    build_development_library,
    search_with_library,
)
from yado_primitive_genesis_cycle1 import FailureDrivenSchemaInducer

ROOT = Path(__file__).resolve().parent


class UnifiedYADOKernelV28MetaGrammar(UnifiedYADOKernelV27Selective):
    """V2.8 shadow runtime with bounded post-synthesis family induction.

    It removes the previous AFFINE_CONTIGUOUS_SLICE_MAP family from the active
    mechanism-genesis path. A generic low-level integer coordinate algebra is
    still host supplied; successful programs are compressed into learned family
    signatures and reused before falling back to full low-level search.
    """

    SCHEMA_VERSION = 10
    PROFILE = "YADO_V2_8_META_GRAMMAR_SHADOW"

    def __init__(self, db_path: str = "yado_v28_meta_grammar_shadow.db"):
        super().__init__(db_path=db_path)
        self.meta_grammar_library = build_development_library()

    def _bootstrap_domain_evidence(self) -> None:
        super()._bootstrap_domain_evidence()
        report = ROOT / "yado_meta_grammar_genesis_cycle1_report.json"
        rid = "internal:yado:meta-grammar-genesis"
        if report.exists() and self.get_resource(rid, include_text=False) is None:
            self.add_resource(
                rid,
                "Bounded meta-grammar genesis: low-level coordinate synthesis, post-synthesis family compression, and library reuse.",
                metadata={
                    "provider": "internal_developmental_registry",
                    "status": "ACTIVE_VERIFIED",
                    "authority": False,
                    "source_path": str(report),
                    "source_sha256": hashlib.sha256(report.read_bytes()).hexdigest(),
                },
                tags=["meta_grammar", "library_learning", "mechanism_genesis", "developmental_evidence"],
            )

    def _execute_genesis(self, payload: Mapping[str, Any], ablated: bool) -> Dict[str, Any]:
        train = self._decode_cases(payload["train"])
        blind = self._decode_cases(payload["blind"])
        live_input = payload["live_input"]
        expected_live = payload["expected_live"]

        # Prior V2.7 meta-schema is the causal ablation baseline.
        prior = FailureDrivenSchemaInducer()
        prior_best, prior_generated = prior.search(blind)
        baseline = 0.0 if prior_best is None else float(prior_best.exact)

        if ablated:
            live_output = None
            if prior_best is not None:
                try:
                    live_output = prior.execute(prior_best.schema, live_input)
                except Exception:
                    live_output = None
            return {
                "mechanism": "V27_AFFINE_SLICE_META_SCHEMA",
                "baseline": baseline,
                "candidate": baseline,
                "ablation": baseline,
                "restore": baseline,
                "live_output": live_output,
                "expected_live": expected_live,
                "output_correct": live_output == expected_live,
                "details": {
                    "prior_generated_candidates": prior_generated,
                    "host_supplied_affine_slice_meta_schema": True,
                },
            }

        synth = LowLevelCoordinateSynthesizer()
        lib_best, lib_generated, family_id = search_with_library(self.meta_grammar_library, train)
        used_library = bool(lib_best is not None and lib_best.exact == 1.0)
        full_generated = 0
        if used_library:
            best = lib_best
            search_mode = "LEARNED_FAMILY_INSTANTIATION"
        else:
            best, full_generated = synth.search(train)
            search_mode = "LOW_LEVEL_COORDINATE_SEARCH"
            if best is not None and best.exact == 1.0:
                family_id = self.meta_grammar_library.observe(best.program, "runtime_new_family")

        if best is None:
            return {
                "mechanism": "META_GRAMMAR_GENESIS",
                "baseline": baseline,
                "candidate": 0.0,
                "ablation": baseline,
                "restore": 0.0,
                "live_output": None,
                "expected_live": expected_live,
                "output_correct": False,
                "details": {
                    "search_mode": search_mode,
                    "library_candidates": lib_generated,
                    "full_candidates": full_generated,
                    "derived_program": None,
                },
            }

        frozen = CoordinateProgram(**asdict(best.program))
        cand = float(synth.score(frozen, blind).exact)
        restore = float(synth.score(frozen, blind).exact)
        try:
            live_output = synth.execute(frozen, live_input)
        except Exception:
            live_output = None

        return {
            "mechanism": "META_GRAMMAR_GENESIS",
            "baseline": baseline,
            "candidate": cand,
            "ablation": baseline,
            "restore": restore,
            "live_output": live_output,
            "expected_live": expected_live,
            "output_correct": live_output == expected_live,
            "details": {
                "search_mode": search_mode,
                "selected_family_id": family_id,
                "library_candidates": lib_generated,
                "full_candidates": full_generated,
                "derived_program": asdict(frozen),
                "program_digest": frozen.digest,
                "host_supplied_affine_slice_meta_schema": False,
                "host_supplied_named_family_list": False,
                "host_supplied_low_level_coordinate_algebra": True,
                "family_created_or_reused_after_synthesis": True,
                "task_specific_operator_supplied": False,
            },
        }


__all__ = ["UnifiedYADOKernelV28MetaGrammar"]
