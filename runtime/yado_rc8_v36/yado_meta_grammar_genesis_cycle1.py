from __future__ import annotations

import hashlib
import itertools
import json
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence, Tuple

from yado_phase_a_shadow import Case, PhaseAShadowSearch
from yado_primitive_genesis_cycle1 import FailureDrivenSchemaInducer


def canonical_json(x: Any) -> str:
    return json.dumps(x, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_obj(x: Any) -> str:
    return hashlib.sha256(canonical_json(x).encode("utf-8")).hexdigest()


def freeze(x: Any) -> Any:
    if isinstance(x, list):
        return ("list", tuple(freeze(v) for v in x))
    if isinstance(x, dict):
        return ("dict", tuple(sorted((str(k), freeze(v)) for k, v in x.items())))
    return (type(x).__name__, x)


RESOURCE_EVIDENCE = {
    "microsoft/prose": {
        "lesson": "detect expressiveness failure; constrain search from examples; extend representation rather than endlessly rerank an inexpressive DSL",
        "readme_sha": "193babd7fdb7b084df6aac5b1c57d47899f555a2",
        "tutorial_sha": "0b467252e8593a92d75cd7ecb42b3f60eb5ec269",
    },
    "mlb2251/dreamcoder": {
        "lesson": "iterative program search plus abstraction/library compression; induced abstractions become reusable search structure instead of a fixed hand-authored family list",
        "readme_sha": "8499281f0b30307d768588da80af42783795312e",
    },
}


@dataclass(frozen=True)
class CoordinateProgram:
    """A low-level structural program, not a named task family.

    Each output leaf points to an input position:
      idx = outer_step*j + inner_step*k + bias + last_coeff*(len(input)-1)

    rank=1 ignores k/inner_count and emits a flat sequence until idx is invalid.
    rank=2 emits fixed-width groups until any group index is invalid.

    The host supplies this small integer coordinate algebra. It does not supply
    named operator families such as CHUNK_PAIRS, GAPPED_PAIRS, REVERSE_FROM_END,
    or final coefficients. Family signatures are compressed *after* synthesis.
    """

    rank: int
    outer_step: int
    inner_step: int
    bias: int
    last_coeff: int
    inner_count: int
    origin: str = "LOW_LEVEL_COORDINATE_SEARCH"

    @property
    def complexity(self) -> int:
        return (
            1
            + abs(self.outer_step)
            + abs(self.inner_step)
            + abs(self.bias)
            + abs(self.last_coeff)
            + self.inner_count
        )

    @property
    def digest(self) -> str:
        return sha256_obj(asdict(self))


@dataclass
class ProgramScore:
    program: CoordinateProgram
    exact: float
    mdl: float
    failures: List[str]


class LowLevelCoordinateSynthesizer:
    """Bounded search below the previous AFFINE_CONTIGUOUS_SLICE_MAP schema."""

    def __init__(self, complexity_penalty: float = 0.0015):
        self.complexity_penalty = float(complexity_penalty)

    @staticmethod
    def execute(program: CoordinateProgram, value: Any) -> Any:
        if not isinstance(value, list):
            raise TypeError("list input required")
        nlast = len(value) - 1
        if program.rank == 1:
            if program.outer_step == 0:
                raise ValueError("rank1 outer_step cannot be zero")
            out = []
            j = 0
            # hard bounded termination protects against malformed candidates
            for _ in range(len(value) + 2):
                idx = program.outer_step * j + program.bias + program.last_coeff * nlast
                if idx < 0 or idx >= len(value):
                    break
                out.append(value[idx])
                j += 1
            return out
        if program.rank == 2:
            if program.outer_step == 0 or program.inner_count < 1:
                raise ValueError("invalid rank2 coordinate program")
            out = []
            j = 0
            for _ in range(len(value) + 2):
                idxs = [
                    program.outer_step * j
                    + program.inner_step * k
                    + program.bias
                    + program.last_coeff * nlast
                    for k in range(program.inner_count)
                ]
                if not idxs or any(i < 0 or i >= len(value) for i in idxs):
                    break
                out.append([value[i] for i in idxs])
                j += 1
            return out
        raise ValueError("rank must be 1 or 2")

    @staticmethod
    def infer_rank(cases: Sequence[Case]) -> int | None:
        ranks = set()
        for c in cases:
            if not isinstance(c.expected, list):
                return None
            if not c.expected:
                continue
            nested = all(isinstance(x, list) for x in c.expected)
            flat = all(not isinstance(x, list) for x in c.expected)
            if nested:
                ranks.add(2)
            elif flat:
                ranks.add(1)
            else:
                return None
        return next(iter(ranks)) if len(ranks) == 1 else None

    @staticmethod
    def infer_inner_counts(cases: Sequence[Case], rank: int) -> List[int]:
        if rank == 1:
            return [1]
        vals = set()
        for c in cases:
            if isinstance(c.expected, list):
                for g in c.expected:
                    if isinstance(g, list) and g:
                        vals.add(len(g))
        return sorted(vals)

    def generate_candidates(self, cases: Sequence[Case]) -> Iterable[CoordinateProgram]:
        rank = self.infer_rank(cases)
        if rank is None:
            return
        counts = self.infer_inner_counts(cases, rank)
        # Generic bounded integer atom grammar. No task-family list.
        outer_steps = [x for x in range(-4, 5) if x != 0]
        inner_steps = range(-4, 5) if rank == 2 else [0]
        biases = range(-4, 5)
        last_coeffs = (-1, 0, 1)
        for inner_count, outer, inner, bias, last in itertools.product(
            counts, outer_steps, inner_steps, biases, last_coeffs
        ):
            yield CoordinateProgram(rank, outer, inner, bias, last, inner_count)

    def score(self, program: CoordinateProgram, cases: Sequence[Case]) -> ProgramScore:
        passed = 0
        failures: List[str] = []
        for c in cases:
            try:
                got = self.execute(program, c.input)
                ok = freeze(got) == freeze(c.expected)
            except Exception:
                ok = False
            if ok:
                passed += 1
            else:
                failures.append(c.case_id)
        exact = passed / max(1, len(cases))
        mdl = exact - self.complexity_penalty * program.complexity
        return ProgramScore(program, exact, mdl, failures)

    def search(self, cases: Sequence[Case]) -> Tuple[ProgramScore | None, int]:
        best = None
        n = 0
        for p in self.generate_candidates(cases) or []:
            n += 1
            s = self.score(p, cases)
            lhs = (s.exact, s.mdl, -p.complexity, p.digest)
            if best is None:
                best = s
            else:
                rhs = (best.exact, best.mdl, -best.program.complexity, best.program.digest)
                if lhs > rhs:
                    best = s
        return best, n


class AbstractionLibrary:
    """Compress discovered coordinate programs into reusable structural signatures."""

    def __init__(self):
        self.entries: Dict[str, Dict[str, Any]] = {}

    @staticmethod
    def signature(p: CoordinateProgram) -> Dict[str, Any]:
        # Bias is task-position-specific; structural family keeps coordinate law.
        return {
            "rank": p.rank,
            "outer_step": p.outer_step,
            "inner_step": p.inner_step,
            "last_coeff": p.last_coeff,
            "inner_count": p.inner_count,
        }

    def observe(self, p: CoordinateProgram, task: str) -> str:
        sig = self.signature(p)
        family_id = "FAM_" + sha256_obj(sig)[:12]
        e = self.entries.setdefault(
            family_id,
            {
                "family_id": family_id,
                "signature": sig,
                "support": 0,
                "tasks": [],
                "origin": "POST_SYNTHESIS_COMPRESSION",
            },
        )
        e["support"] += 1
        e["tasks"].append(task)
        return family_id

    def export(self) -> List[Dict[str, Any]]:
        return sorted(self.entries.values(), key=lambda x: x["family_id"])


def phase_a_baseline(cases: Sequence[Case]) -> Dict[str, Any]:
    eng = PhaseAShadowSearch(max_depth=3)
    best, n = eng.search(cases)
    return {"candidate_count": n, "exact": best.exact_score, "stages": list(best.candidate.stages)}


def old_meta_schema_baseline(cases: Sequence[Case]) -> Dict[str, Any]:
    eng = FailureDrivenSchemaInducer()
    best, n = eng.search(cases)
    return {
        "candidate_count": n,
        "exact": 0.0 if best is None else best.exact,
        "schema": None if best is None else asdict(best.schema),
    }


def run_task(name: str, train: Sequence[Case], blind: Sequence[Case], lib: AbstractionLibrary) -> Dict[str, Any]:
    primitive_base = phase_a_baseline(train)
    old_meta = old_meta_schema_baseline(train)
    syn = LowLevelCoordinateSynthesizer()
    best, count = syn.search(train)
    if best is None:
        return {"task": name, "verdict": "NO_PROGRAM", "candidate_count": count}
    frozen = CoordinateProgram(**asdict(best.program))
    train_score = syn.score(frozen, train).exact
    blind_score = syn.score(frozen, blind).exact
    # Ablation removes the learned low-level coordinate program and falls back to prior meta-schema.
    old_blind = old_meta_schema_baseline(blind)["exact"]
    restore = syn.score(frozen, blind).exact
    family_id = lib.observe(frozen, name)
    passed = train_score == 1.0 and blind_score == 1.0 and restore == 1.0 and old_blind < 1.0
    return {
        "task": name,
        "prior_fixed_phase_a": primitive_base,
        "prior_affine_slice_meta_schema": old_meta,
        "generated_low_level_programs": count,
        "selected_program": asdict(frozen),
        "selected_digest": frozen.digest,
        "induced_family_id": family_id,
        "induced_family_signature": lib.signature(frozen),
        "train_exact": train_score,
        "fresh_blind_exact": blind_score,
        "ablation_prior_meta_schema_blind_exact": old_blind,
        "restore_exact": restore,
        "verdict": "SHADOW_SUPPORTED" if passed else "SHADOW_WITHHOLD",
    }


def cases() -> List[Tuple[str, List[Case], List[Case]]]:
    return [
        (
            "flat_stride2_offset1",
            [
                Case("T1", [1,2,3,4,5,6,7], [2,4,6]),
                Case("T2", ["a","b","c","d","e","f"], ["b","d","f"]),
            ],
            [
                Case("B1", [10,11,12,13,14,15,16,17], [11,13,15,17]),
                Case("B2", ["p","q","r","s","t"], ["q","s"]),
            ],
        ),
        (
            "gapped_pairs",
            [
                Case("T1", [1,2,3,4,5], [[1,3],[2,4],[3,5]]),
                Case("T2", ["a","b","c","d"], [["a","c"],["b","d"]]),
            ],
            [
                Case("B1", [10,11,12,13,14,15], [[10,12],[11,13],[12,14],[13,15]]),
                Case("B2", ["u","v","w","x","y"], [["u","w"],["v","x"],["w","y"]]),
            ],
        ),
        (
            "reverse_gapped_pairs",
            [
                Case("T1", [1,2,3,4,5], [[3,1],[4,2],[5,3]]),
                Case("T2", ["a","b","c","d"], [["c","a"],["d","b"]]),
            ],
            [
                Case("B1", [10,11,12,13,14,15], [[12,10],[13,11],[14,12],[15,13]]),
                Case("B2", ["u","v","w","x","y"], [["w","u"],["x","v"],["y","w"]]),
            ],
        ),
        (
            "from_end_flat_reverse",
            [
                Case("T1", [1,2,3,4], [4,3,2,1]),
                Case("T2", ["a","b","c","d","e"], ["e","d","c","b","a"]),
            ],
            [
                Case("B1", [10,11,12,13,14,15], [15,14,13,12,11,10]),
                Case("B2", ["u","v","w"], ["w","v","u"]),
            ],
        ),
        (
            "gapped_triplets",
            [
                Case("T1", [1,2,3,4,5,6], [[1,3,5],[2,4,6]]),
                Case("T2", ["a","b","c","d","e"], [["a","c","e"]]),
            ],
            [
                Case("B1", [10,11,12,13,14,15,16], [[10,12,14],[11,13,15],[12,14,16]]),
                Case("B2", ["u","v","w","x","y","z"], [["u","w","y"],["v","x","z"]]),
            ],
        ),
    ]



def search_with_library(
    library: AbstractionLibrary, cases: Sequence[Case], complexity_penalty: float = 0.0015
) -> Tuple[ProgramScore | None, int, str | None]:
    syn = LowLevelCoordinateSynthesizer(complexity_penalty=complexity_penalty)
    best = None
    best_family = None
    n = 0
    for entry in library.export():
        sig = entry["signature"]
        for bias in range(-4, 5):
            p = CoordinateProgram(
                rank=int(sig["rank"]),
                outer_step=int(sig["outer_step"]),
                inner_step=int(sig["inner_step"]),
                bias=bias,
                last_coeff=int(sig["last_coeff"]),
                inner_count=int(sig["inner_count"]),
                origin="LIBRARY_INSTANTIATION",
            )
            n += 1
            sc = syn.score(p, cases)
            lhs = (sc.exact, sc.mdl, -p.complexity, p.digest)
            if best is None:
                best, best_family = sc, entry["family_id"]
            else:
                rhs = (best.exact, best.mdl, -best.program.complexity, best.program.digest)
                if lhs > rhs:
                    best, best_family = sc, entry["family_id"]
    return best, n, best_family


def library_transfer_benchmark(library: AbstractionLibrary) -> Dict[str, Any]:
    train = [
        Case("LT1", [1,2,3,4,5,6], [[2,4],[3,5],[4,6]]),
        Case("LT2", ["a","b","c","d","e"], [["b","d"],["c","e"]]),
    ]
    blind = [
        Case("LB1", [10,11,12,13,14,15,16], [[11,13],[12,14],[13,15],[14,16]]),
        Case("LB2", ["u","v","w","x","y","z"], [["v","x"],["w","y"],["x","z"]]),
    ]
    full = LowLevelCoordinateSynthesizer()
    full_best, full_n = full.search(train)
    lib_best, lib_n, family_id = search_with_library(library, train)
    if full_best is None or lib_best is None:
        return {"verdict": "NO_PROGRAM"}
    frozen = CoordinateProgram(**asdict(lib_best.program))
    blind_score = full.score(frozen, blind).exact
    old_blind = old_meta_schema_baseline(blind)["exact"]
    restore = full.score(frozen, blind).exact
    return {
        "task": "library_reuse_gapped_pairs_offset1",
        "full_low_level_search_candidates": full_n,
        "library_instantiation_candidates": lib_n,
        "search_reduction_ratio": full_n / max(1, lib_n),
        "selected_family_id": family_id,
        "selected_program": asdict(frozen),
        "train_exact": lib_best.exact,
        "fresh_blind_exact": blind_score,
        "ablation_prior_meta_schema_blind_exact": old_blind,
        "restore_exact": restore,
        "verdict": "SHADOW_SUPPORTED" if lib_best.exact == 1.0 and blind_score == 1.0 and old_blind < 1.0 else "SHADOW_WITHHOLD",
    }


def build_development_library() -> AbstractionLibrary:
    lib = AbstractionLibrary()
    syn = LowLevelCoordinateSynthesizer()
    for name, train, _blind in cases():
        best, _ = syn.search(train)
        if best is not None and best.exact == 1.0:
            lib.observe(best.program, name)
    return lib

def benchmark() -> Dict[str, Any]:
    library = AbstractionLibrary()
    results = [run_task(name, tr, bl, library) for name, tr, bl in cases()]
    supported = [r for r in results if r.get("verdict") == "SHADOW_SUPPORTED"]
    family_ids = {r.get("induced_family_id") for r in supported}
    library_transfer = library_transfer_benchmark(library)
    prior_failed = all(r.get("prior_affine_slice_meta_schema", {}).get("exact", 1.0) < 1.0 for r in supported)
    report = {
        "schema": "yado.meta_grammar_genesis.cycle1.v1",
        "profile": "YADO_META_GRAMMAR_GENESIS_SHADOW",
        "target_deficit": "HOST_SUPPLIED_AFFINE_SLICE_META_SCHEMA",
        "external_learning": RESOURCE_EVIDENCE,
        "method": {
            "search_level": "LOW_LEVEL_INTEGER_COORDINATE_ALGEBRA",
            "family_list_supplied_by_host": False,
            "named_task_operator_supplied_by_host": False,
            "family_created_after_synthesis": True,
            "compression": "structural signature extracted from successful coordinate program",
            "freeze_before_blind": True,
        },
        "tasks": results,
        "library": library.export(),
        "library_transfer": library_transfer,
        "summary": {
            "tasks": len(results),
            "supported_tasks": len(supported),
            "distinct_induced_families": len(family_ids),
            "old_affine_slice_meta_schema_failed_supported_tasks": prior_failed,
            "host_supplied_affine_slice_meta_schema_removed": True,
            "host_supplied_named_family_list": False,
            "host_supplied_low_level_coordinate_algebra": True,
            "general_mechanism_family_invention_proven": False,
            "bounded_family_induction_from_low_level_programs_supported": len(supported) == len(results) and len(family_ids) >= 4,
            "library_reuse_supported": library_transfer.get("verdict") == "SHADOW_SUPPORTED",
            "canonical_durable_mutation": False,
        },
        "verdict": (
            "SHADOW_SUPPORTED_BOUNDED_META_GRAMMAR_GENESIS"
            if len(supported) == len(results) and len(family_ids) >= 4 and prior_failed and library_transfer.get("verdict") == "SHADOW_SUPPORTED"
            else "SHADOW_WITHHOLD"
        ),
        "claim_boundary": {
            "zero_host_substrate_claimed": False,
            "coordinate_algebra_learned_from_scratch": False,
            "real_18_cfg_counterexamples_replayed": False,
            "general_operator_invention_claimed": False,
        },
        "next_frontier": "learn or expand the low-level coordinate/predicate algebra from non-coordinate failures, rather than only compress programs within a supplied coordinate algebra",
    }
    return report


if __name__ == "__main__":
    report = benchmark()
    out = Path(__file__).with_name("yado_meta_grammar_genesis_cycle1_report.json")
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
