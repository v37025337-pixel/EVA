"""RC7 native transition-program runtime.

This is a fresh, bounded implementation of the public transition-program contract
used by YADO V2.9. It is validated against the preserved compatibility runtime but
is not claimed to be the lost historical original.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from typing import Any, Iterable, Mapping, Sequence

PROVENANCE = {
    "status": "RC7_NATIVE_REDERIVATION_V1",
    "source": "PUBLIC_RUNTIME_CONTRACT_PLUS_FRESH_DIFFERENTIAL_VALIDATION",
    "scope": "V2_9_TRANSITION_PROGRAM_RUNTIME",
    "lost_original_recovered": False,
}


def _canonical(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


@dataclass(frozen=True)
class TransitionProgram:
    output_mode: str
    guard: object
    emit_expr: object
    state_update: object
    initial_state: object = 0
    origin: str = "RC7_NATIVE_REDERIVATION_V1"

    @property
    def digest(self) -> str:
        return hashlib.sha256(_canonical(asdict(self)).encode("utf-8")).hexdigest()


def _eval(expr: Any, item: Any, state: Any) -> Any:
    if not isinstance(expr, (list, tuple)) or not expr:
        return expr
    op = expr[0]
    if op == "ITEM":
        return item
    if op == "STATE":
        return state
    if op == "CONST":
        return expr[1]
    if op == "TRUE":
        return True
    if op == "FALSE":
        return False
    if op == "ITE":
        return _eval(expr[2], item, state) if bool(_eval(expr[1], item, state)) else _eval(expr[3], item, state)

    left = _eval(expr[1], item, state)
    right = _eval(expr[2], item, state)
    if op == "ADD":
        return left + right
    if op == "SUB":
        return left - right
    if op == "MUL":
        return left * right
    if op == "MOD":
        return left % right
    if op == "EQ":
        return left == right
    if op == "NEQ":
        return left != right
    if op == "LT":
        return left < right
    if op == "GT":
        return left > right
    raise ValueError(f"unsupported native expr op {op}")


class AtomicTransitionSynthesizer:
    def execute(self, program: TransitionProgram, inp: Sequence[Any]) -> Any:
        state = program.initial_state
        emitted = []
        for item in inp:
            if bool(_eval(program.guard, item, state)):
                emitted.append(_eval(program.emit_expr, item, state))
            state = _eval(program.state_update, item, state)
        return state if program.output_mode == "STATE" else emitted

    def score(self, program: TransitionProgram, cases: Sequence[tuple[Sequence[Any], Any]]) -> dict[str, float]:
        if not cases:
            return {"exact": 0.0}
        hits = sum(self.execute(program, x) == y for x, y in cases)
        return {"exact": hits / len(cases)}

    @staticmethod
    def _constants(train: Sequence[tuple[Sequence[Any], Any]]) -> list[Any]:
        values = []
        for x, y in train:
            candidates = list(x) + (list(y) if isinstance(y, list) else [y])
            values.extend(z for z in candidates if isinstance(z, (int, float)))
            if isinstance(y, list) and len(x) == len(y):
                values.extend(
                    b - a for a, b in zip(x, y)
                    if isinstance(a, (int, float)) and isinstance(b, (int, float))
                )
        return sorted(set(values + [0, 1, -1]))[:24]

    @staticmethod
    def _candidate_family(c: Any) -> Iterable[TransitionProgram]:
        divisor = c if c != 0 else 1
        yield TransitionProgram(
            "LIST",
            ["EQ", ["MOD", ["ITEM"], ["CONST", divisor]], ["CONST", 0]],
            ["ITEM"],
            ["STATE"],
            0,
        )
        yield TransitionProgram(
            "LIST",
            ["TRUE"],
            ["ITE", ["LT", ["ITEM"], ["CONST", 0]], ["ADD", ["ITEM"], ["CONST", c]], ["ITEM"]],
            ["STATE"],
            0,
        )
        yield TransitionProgram(
            "STATE",
            ["TRUE"],
            ["ITEM"],
            ["ITE", ["GT", ["ITEM"], ["CONST", c]], ["ADD", ["STATE"], ["ITEM"]], ["STATE"]],
            0,
        )

    def search(self, train: Sequence[tuple[Sequence[Any], Any]]):
        candidates = [p for c in self._constants(train) for p in self._candidate_family(c)]
        best = max(candidates, key=lambda p: self.score(p, train)["exact"]) if candidates else None
        return best, len(candidates), {"native_runtime": True, "provenance": PROVENANCE["status"]}


def load_skill_library_from_report(path: str):
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
    return list(data.get("skill_library") or [])


def _program_from_dict(data: Mapping[str, Any]) -> TransitionProgram:
    return TransitionProgram(
        output_mode=data["output_mode"],
        guard=data["guard"],
        emit_expr=data["emit_expr"],
        state_update=data["state_update"],
        initial_state=data.get("initial_state", 0),
        origin=data.get("origin", "RC7_NATIVE_REDERIVED_SKILL"),
    )


def _replace_constants(expr: Any, value: Any) -> Any:
    if isinstance(expr, list):
        if expr and expr[0] == "CONST":
            return ["CONST", value]
        return [_replace_constants(part, value) for part in expr]
    return expr


def search_with_skill_library(library, train):
    synth = AtomicTransitionSynthesizer()
    numeric = sorted({
        z
        for x, y in train
        for z in (list(x) + (list(y) if isinstance(y, list) else [y]))
        if isinstance(z, (int, float))
    })[:16]
    candidates = []
    for skill in library or []:
        for example in skill.get("examples", []):
            candidates.append(_program_from_dict(example))
            for n in numeric:
                variant = dict(example)
                variant["guard"] = _replace_constants(example.get("guard"), n)
                variant["emit_expr"] = _replace_constants(example.get("emit_expr"), n)
                variant["state_update"] = _replace_constants(example.get("state_update"), n)
                candidates.append(_program_from_dict(variant))
    best = max(candidates, key=lambda p: synth.score(p, train)["exact"]) if candidates else None
    return best, len(candidates), {"native_runtime": True, "provenance": PROVENANCE["status"]}


__all__ = [
    "PROVENANCE",
    "TransitionProgram",
    "AtomicTransitionSynthesizer",
    "load_skill_library_from_report",
    "search_with_skill_library",
]
