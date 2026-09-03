from __future__ import annotations

import hashlib
import itertools
import json
from dataclasses import asdict, dataclass, field
from typing import Any, Callable, Dict, Iterable, List, Mapping, Sequence, Tuple


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def _freeze(value: Any) -> Any:
    if isinstance(value, dict):
        return ("dict", tuple(sorted((str(k), _freeze(v)) for k, v in value.items())))
    if isinstance(value, (list, tuple)):
        return ("seq", tuple(_freeze(v) for v in value))
    return (type(value).__name__, value)


def _dedupe(seq: Any) -> Any:
    if not isinstance(seq, list):
        raise TypeError("DEDUPE requires list")
    out, seen = [], set()
    for item in seq:
        key = _freeze(item)
        if key not in seen:
            seen.add(key)
            out.append(item)
    return out


def _sort(seq: Any) -> Any:
    if not isinstance(seq, list):
        raise TypeError("SORT requires list")
    return sorted(seq, key=canonical_json)


def _reverse(seq: Any) -> Any:
    if not isinstance(seq, list):
        raise TypeError("REVERSE requires list")
    return list(reversed(seq))


def _adjacent_pairs(seq: Any) -> Any:
    if not isinstance(seq, list):
        raise TypeError("ADJACENT_PAIRS requires list")
    return [[seq[i], seq[i + 1]] for i in range(max(0, len(seq) - 1))]


def _enumerate(seq: Any) -> Any:
    if not isinstance(seq, list):
        raise TypeError("ENUMERATE requires list")
    return [[i, item] for i, item in enumerate(seq)]


def _flatten_one(seq: Any) -> Any:
    if not isinstance(seq, list):
        raise TypeError("FLATTEN_ONE requires list")
    out: List[Any] = []
    for item in seq:
        if isinstance(item, list):
            out.extend(item)
        else:
            out.append(item)
    return out


def _values(obj: Any) -> Any:
    if not isinstance(obj, dict):
        raise TypeError("VALUES requires dict")
    return [obj[k] for k in sorted(obj)]


def _keys(obj: Any) -> Any:
    if not isinstance(obj, dict):
        raise TypeError("KEYS requires dict")
    return sorted(obj)


def _identity(value: Any) -> Any:
    return value


PrimitiveFn = Callable[[Any], Any]


@dataclass(frozen=True)
class Primitive:
    name: str
    fn: PrimitiveFn = field(compare=False, repr=False)


@dataclass(frozen=True)
class Candidate:
    stages: Tuple[str, ...]
    origin: str = "SEARCH_GENERATED"

    @property
    def complexity(self) -> int:
        return len(self.stages)

    def fingerprint(self) -> str:
        return digest({"stages": self.stages, "origin": self.origin})


@dataclass
class Case:
    case_id: str
    input: Any
    expected: Any


@dataclass
class CandidateScore:
    candidate: Candidate
    exact_score: float
    mdl_score: float
    failures: List[str]


@dataclass
class ShadowReceipt:
    schema: str
    train_count: int
    blind_count: int
    primitive_names: List[str]
    candidate_count: int
    selected_stages: List[str]
    selected_digest: str
    train_exact: float
    blind_exact: float
    ablation_exact: float
    restore_exact: float
    verdict: str
    derived_macro: str | None
    provenance: Dict[str, Any]


class PhaseAShadowSearch:
    """Bounded, domain-neutral representation search.

    The host supplies only a small pure-data primitive substrate and the scoring
    contract.  It does not supply a task-specific candidate or branch/opcode
    rule.  Candidate programs are enumerated and selected from evidence.
    """

    DEFAULT_PRIMITIVES: Tuple[Primitive, ...] = (
        Primitive("IDENTITY", _identity),
        Primitive("DEDUPE", _dedupe),
        Primitive("SORT", _sort),
        Primitive("REVERSE", _reverse),
        Primitive("ADJACENT_PAIRS", _adjacent_pairs),
        Primitive("ENUMERATE", _enumerate),
        Primitive("FLATTEN_ONE", _flatten_one),
        Primitive("VALUES", _values),
        Primitive("KEYS", _keys),
    )

    def __init__(self, max_depth: int = 3, complexity_penalty: float = 0.01):
        if max_depth < 1 or max_depth > 5:
            raise ValueError("max_depth must be in [1,5]")
        self.max_depth = max_depth
        self.complexity_penalty = float(complexity_penalty)
        self.primitives: Dict[str, Primitive] = {p.name: p for p in self.DEFAULT_PRIMITIVES}
        self.derived_macros: Dict[str, Candidate] = {}

    def execute(self, candidate: Candidate, value: Any, *, skip_stage: int | None = None) -> Any:
        current = value
        for idx, name in enumerate(candidate.stages):
            if skip_stage is not None and idx == skip_stage:
                continue
            if name in self.primitives:
                current = self.primitives[name].fn(current)
            elif name in self.derived_macros:
                current = self.execute(self.derived_macros[name], current)
            else:
                raise KeyError(name)
        return current

    def generate_candidates(self) -> Iterable[Candidate]:
        names = tuple(sorted(self.primitives))
        # No task-specific candidate list is supplied; programs are generated by
        # bounded composition over the primitive substrate.
        for depth in range(1, self.max_depth + 1):
            for stages in itertools.product(names, repeat=depth):
                yield Candidate(stages=stages)

    def score(self, candidate: Candidate, cases: Sequence[Case]) -> CandidateScore:
        if not cases:
            raise ValueError("cases required")
        passed = 0
        failures: List[str] = []
        for case in cases:
            try:
                got = self.execute(candidate, case.input)
                ok = _freeze(got) == _freeze(case.expected)
            except Exception:
                ok = False
            if ok:
                passed += 1
            else:
                failures.append(case.case_id)
        exact = passed / len(cases)
        mdl = exact - self.complexity_penalty * candidate.complexity
        return CandidateScore(candidate, exact, mdl, failures)

    def search(self, train_cases: Sequence[Case]) -> Tuple[CandidateScore, int]:
        best: CandidateScore | None = None
        count = 0
        for candidate in self.generate_candidates():
            count += 1
            score = self.score(candidate, train_cases)
            if best is None:
                best = score
                continue
            # Prefer exact fit, then lower complexity, then deterministic lexical tie-break.
            lhs = (score.exact_score, score.mdl_score, -score.candidate.complexity, tuple(score.candidate.stages))
            rhs = (best.exact_score, best.mdl_score, -best.candidate.complexity, tuple(best.candidate.stages))
            if lhs > rhs:
                best = score
        assert best is not None
        return best, count

    def _ablation_score(self, candidate: Candidate, cases: Sequence[Case]) -> float:
        if len(candidate.stages) <= 1:
            # Removing the only stage is the identity baseline.
            baseline = Candidate(("IDENTITY",), origin="ABLATION")
            return self.score(baseline, cases).exact_score
        scores = []
        for idx in range(len(candidate.stages)):
            passed = 0
            for case in cases:
                try:
                    got = self.execute(candidate, case.input, skip_stage=idx)
                    passed += int(_freeze(got) == _freeze(case.expected))
                except Exception:
                    pass
            scores.append(passed / len(cases))
        # Conservative: weakest causal evidence = best-performing ablation.
        return max(scores)

    def run_shadow(
        self,
        train_cases: Sequence[Case],
        blind_cases: Sequence[Case],
        *,
        min_train: float = 1.0,
        min_blind: float = 1.0,
        min_ablation_drop: float = 0.20,
    ) -> ShadowReceipt:
        winner, candidate_count = self.search(train_cases)
        frozen = Candidate(tuple(winner.candidate.stages), origin="SEARCH_GENERATED_FROZEN")
        frozen_digest = frozen.fingerprint()
        blind = self.score(frozen, blind_cases).exact_score
        ablation = self._ablation_score(frozen, blind_cases)
        restore = self.score(frozen, blind_cases).exact_score
        causal_drop = blind - ablation

        passed = (
            winner.exact_score >= min_train
            and blind >= min_blind
            and restore == blind
            and causal_drop >= min_ablation_drop
        )
        verdict = "SHADOW_SUPPORTED" if passed else "SHADOW_REJECTED"

        macro_name = None
        if passed and len(frozen.stages) > 1:
            macro_name = "M_" + frozen_digest[:12]
            self.derived_macros[macro_name] = frozen

        return ShadowReceipt(
            schema="yado.phase_a.shadow_search.v1",
            train_count=len(train_cases),
            blind_count=len(blind_cases),
            primitive_names=sorted(self.primitives),
            candidate_count=candidate_count,
            selected_stages=list(frozen.stages),
            selected_digest=frozen_digest,
            train_exact=winner.exact_score,
            blind_exact=blind,
            ablation_exact=ablation,
            restore_exact=restore,
            verdict=verdict,
            derived_macro=macro_name,
            provenance={
                "host_task_specific_rule_supplied": False,
                "host_candidate_code_supplied": False,
                "host_supplied_primitive_substrate": True,
                "candidate_generated_by_search": True,
                "candidate_frozen_before_blind": True,
                "durable_mutation": False,
                "shadow_only": True,
                "no_opcode_semantics_hardcoded": True,
            },
        )


def synthetic_self_test() -> ShadowReceipt:
    # The target transformation is intentionally not named in the search call.
    # Search must discover it from examples.
    train = [
        Case("T1", ["b", "a", "a", "c"], [["b", "a"], ["a", "c"]]),
        Case("T2", ["x", "x", "y", "z"], [["x", "y"], ["y", "z"]]),
        Case("T3", [1, 1, 2, 3], [[1, 2], [2, 3]]),
    ]
    blind = [
        Case("B1", ["p", "q", "q", "r"], [["p", "q"], ["q", "r"]]),
        Case("B2", [4, 4, 5, 6], [[4, 5], [5, 6]]),
    ]
    return PhaseAShadowSearch(max_depth=3).run_shadow(train, blind)


if __name__ == "__main__":
    print(json.dumps(asdict(synthetic_self_test()), ensure_ascii=False, indent=2))
