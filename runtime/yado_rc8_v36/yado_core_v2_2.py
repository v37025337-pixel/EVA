from __future__ import annotations

import hashlib
import itertools
import json
import re
import uuid
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple, Union

from yado_core_v2 import UnifiedCognitiveSystem, canonical_json, utc_now
from yado_core_v2_1 import (
    BoundedRuleSandbox,
    DevelopmentalExecutive,
    OrganState,
    RulePredicate,
    RuleProgram,
    RuleProgramSynthesizer,
    RuleSpec,
    UnifiedCognitiveSystemV21,
)


# ---------------------------------------------------------------------------
# v2.2: multiple bounded executable mechanism classes
# ---------------------------------------------------------------------------
@dataclass
class FieldMapOp:
    target_field: str
    op: str  # COPY | CONST
    source_field: Optional[str] = None
    value: Any = None


@dataclass
class FieldMapperProgram:
    program_id: str
    target_capability: str
    target_organ: str
    operations: List[FieldMapOp]
    source_digest: str
    training_count: int
    status: str = "SHADOW"
    created_at: str = field(default_factory=lambda: utc_now().isoformat())
    kind: str = "FIELD_MAPPER"

    def digest(self) -> str:
        return _mechanism_digest(self)


@dataclass
class PlannerRule:
    action: str
    order: float
    predicate: Optional[RulePredicate]
    support: int
    confidence: float


@dataclass
class SequencePlannerProgram:
    program_id: str
    target_capability: str
    target_organ: str
    rules: List[PlannerRule]
    source_digest: str
    training_count: int
    status: str = "SHADOW"
    created_at: str = field(default_factory=lambda: utc_now().isoformat())
    kind: str = "SEQUENCE_PLANNER"

    def digest(self) -> str:
        return _mechanism_digest(self)


@dataclass
class PipelineProgram:
    program_id: str
    target_capability: str
    target_organ: str
    stage_program_ids: List[str]
    source_digest: str
    training_count: int
    status: str = "SHADOW"
    created_at: str = field(default_factory=lambda: utc_now().isoformat())
    kind: str = "PIPELINE"

    def digest(self) -> str:
        return _mechanism_digest(self)


Mechanism = Union[RuleProgram, FieldMapperProgram, SequencePlannerProgram, PipelineProgram]


@dataclass
class SelectionCandidate:
    program_id: str
    kind: str
    training_score: float
    complexity: int
    selected: bool = False
    reason: str = ""


@dataclass
class MechanismSelectionReceipt:
    selection_id: str
    deficit_id: str
    target_capability: str
    target_organ: str
    candidates: List[SelectionCandidate]
    selected_program_id: str
    selected_kind: str
    source_digest: str
    created_at: str = field(default_factory=lambda: utc_now().isoformat())


@dataclass
class MechanismDevelopmentReceipt:
    experiment_id: str
    program_id: str
    mechanism_kind: str
    target_capability: str
    target_organ: str
    train_cases: int
    blind_cases: int
    candidate_score: float
    ablation_score: float
    restore_score: float
    min_score: float
    min_ablation_drop: float
    verdict: str
    state_committed: bool
    reason: str
    program_digest: str
    stage_ablation_scores: Dict[str, float] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: utc_now().isoformat())


def _mechanism_kind(program: Mechanism) -> str:
    if isinstance(program, RuleProgram):
        return "RULE_PROGRAM"
    return program.kind


def _mechanism_payload(program: Mechanism) -> Dict[str, Any]:
    data = asdict(program)
    data["kind"] = _mechanism_kind(program)
    return data


def _mechanism_digest(program: Mechanism) -> str:
    payload = _mechanism_payload(program)
    # Runtime status is not part of executable identity.
    payload.pop("status", None)
    return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()


class FieldMapperSandbox:
    MAX_OPS = 24

    @classmethod
    def validate(cls, program: FieldMapperProgram) -> None:
        if not program.operations or len(program.operations) > cls.MAX_OPS:
            raise ValueError("invalid mapper operation count")
        targets = set()
        for op in program.operations:
            if op.target_field in targets:
                raise ValueError("duplicate mapper target field")
            targets.add(op.target_field)
            if op.op not in {"COPY", "CONST"}:
                raise ValueError(f"unsupported mapper op: {op.op}")
            if op.op == "COPY" and not op.source_field:
                raise ValueError("COPY requires source_field")

    @classmethod
    def execute(cls, program: FieldMapperProgram, payload: Mapping[str, Any], ablated: bool = False) -> Dict[str, Any]:
        cls.validate(program)
        if ablated:
            return {}
        out: Dict[str, Any] = {}
        for op in program.operations:
            if op.op == "COPY":
                if op.source_field not in payload:
                    # Missing source is explicit rather than silently hallucinating a value.
                    continue
                out[op.target_field] = payload[op.source_field]
            else:
                out[op.target_field] = op.value
        return out


class FieldMapperSynthesizer:
    """Derive copy/constant structural mappings from examples without field-name rules."""

    @classmethod
    def synthesize(
        cls,
        target_capability: str,
        target_organ: str,
        examples: Sequence[Mapping[str, Any]],
    ) -> FieldMapperProgram:
        if len(examples) < 3:
            raise ValueError("at least 3 examples are required")
        normalized: List[Tuple[Mapping[str, Any], Mapping[str, Any]]] = []
        for example in examples:
            inp = example.get("input")
            expected = example.get("expected")
            if not isinstance(inp, Mapping) or not isinstance(expected, Mapping):
                raise ValueError("field mapper requires mapping input and mapping expected output")
            normalized.append((inp, expected))

        output_fields = set(normalized[0][1].keys())
        if not output_fields:
            raise ValueError("expected mappings must not be empty")
        if any(set(expected.keys()) != output_fields for _, expected in normalized):
            raise ValueError("field mapper requires stable output schema")

        input_fields = sorted(set.intersection(*(set(inp.keys()) for inp, _ in normalized))) if normalized else []
        operations: List[FieldMapOp] = []
        for out_field in sorted(output_fields):
            matching_sources = [
                in_field
                for in_field in input_fields
                if all(canonical_json(inp[in_field]) == canonical_json(expected[out_field]) for inp, expected in normalized)
            ]
            if matching_sources:
                # Deterministic minimal source choice; no semantic field-name assumptions.
                operations.append(FieldMapOp(target_field=out_field, op="COPY", source_field=matching_sources[0]))
                continue
            frozen = [canonical_json(expected[out_field]) for _, expected in normalized]
            if len(set(frozen)) == 1:
                operations.append(FieldMapOp(target_field=out_field, op="CONST", value=normalized[0][1][out_field]))
                continue
            raise ValueError(f"no bounded structural mapping for output field: {out_field}")

        program = FieldMapperProgram(
            program_id=f"M-{uuid.uuid4().hex[:12]}",
            target_capability=target_capability,
            target_organ=target_organ,
            operations=operations,
            source_digest=hashlib.sha256(canonical_json(list(examples)).encode("utf-8")).hexdigest(),
            training_count=len(examples),
        )
        FieldMapperSandbox.validate(program)
        return program


class SequencePlannerSandbox:
    MAX_RULES = 24

    @classmethod
    def validate(cls, program: SequencePlannerProgram) -> None:
        if not program.rules or len(program.rules) > cls.MAX_RULES:
            raise ValueError("invalid planner rule count")
        seen = set()
        for rule in program.rules:
            if not isinstance(rule.action, str) or not rule.action:
                raise ValueError("planner actions must be non-empty strings")
            if rule.action in seen:
                raise ValueError("duplicate planner action")
            seen.add(rule.action)
            if rule.predicate is not None and rule.predicate.op not in BoundedRuleSandbox.ALLOWED_OPS:
                raise ValueError("unsupported planner predicate")

    @classmethod
    def execute(cls, program: SequencePlannerProgram, payload: Mapping[str, Any], ablated: bool = False) -> List[str]:
        cls.validate(program)
        if ablated:
            return []
        selected = []
        for rule in sorted(program.rules, key=lambda r: (r.order, r.action)):
            if rule.predicate is None or BoundedRuleSandbox._match(rule.predicate, payload):
                selected.append(rule.action)
        return selected


class SequencePlannerSynthesizer:
    """Learn an ordered action policy from examples using stable action prerequisites."""

    @staticmethod
    def _feature_candidates(payload: Mapping[str, Any]) -> List[RulePredicate]:
        features: List[RulePredicate] = []
        for field, value in payload.items():
            if isinstance(value, (str, int, float, bool)) or value is None:
                features.append(RulePredicate("EQ", str(field), value))
            if isinstance(value, str) and len(value) <= BoundedRuleSandbox.MAX_TEXT_LENGTH:
                for token in sorted(set(re.findall(r"[^\W_]+", value.lower(), flags=re.UNICODE))):
                    if len(token) >= 2:
                        features.append(RulePredicate("TEXT_HAS_TOKEN", str(field), token))
        return features

    @classmethod
    def synthesize(
        cls,
        target_capability: str,
        target_organ: str,
        examples: Sequence[Mapping[str, Any]],
        min_support: int = 2,
    ) -> SequencePlannerProgram:
        if len(examples) < 4:
            raise ValueError("sequence planner requires at least 4 examples")
        if min_support < 2:
            raise ValueError("min_support must be >= 2")

        normalized: List[Tuple[Mapping[str, Any], List[str]]] = []
        for example in examples:
            inp = example.get("input")
            expected = example.get("expected")
            if not isinstance(inp, Mapping) or not isinstance(expected, list) or not all(isinstance(x, str) for x in expected):
                raise ValueError("planner requires mapping input and list[str] expected")
            if len(expected) != len(set(expected)):
                raise ValueError("planner example contains duplicate actions")
            normalized.append((inp, expected))

        all_actions = sorted(set(itertools.chain.from_iterable(plan for _, plan in normalized)))
        if not all_actions:
            raise ValueError("plans must contain actions")

        rules: List[PlannerRule] = []
        for action in all_actions:
            positives = [i for i, (_, plan) in enumerate(normalized) if action in plan]
            negatives = [i for i, (_, plan) in enumerate(normalized) if action not in plan]
            if len(positives) == len(normalized):
                predicate = None
                support = len(positives)
            else:
                if len(positives) < min_support:
                    raise ValueError(f"action lacks support: {action}")
                # Candidate must cover every positive case and no negative case.
                candidate_map: Dict[str, RulePredicate] = {}
                for idx in positives:
                    for feature in cls._feature_candidates(normalized[idx][0]):
                        candidate_map[canonical_json(asdict(feature))] = feature
                valid: List[RulePredicate] = []
                for feature in candidate_map.values():
                    pos_match = all(BoundedRuleSandbox._match(feature, normalized[i][0]) for i in positives)
                    neg_match = any(BoundedRuleSandbox._match(feature, normalized[i][0]) for i in negatives)
                    if pos_match and not neg_match:
                        valid.append(feature)
                if not valid:
                    raise ValueError(f"no stable prerequisite for action: {action}")
                valid.sort(key=lambda p: (0 if p.op == "EQ" else 1, p.field, canonical_json(p.value)))
                predicate = valid[0]
                support = len(positives)

            order_values = [plan.index(action) for _, plan in normalized if action in plan]
            rules.append(
                PlannerRule(
                    action=action,
                    order=sum(order_values) / len(order_values),
                    predicate=predicate,
                    support=support,
                    confidence=1.0,
                )
            )

        # Reject training corpora with inconsistent relative action ordering.
        learned_order = [r.action for r in sorted(rules, key=lambda r: (r.order, r.action))]
        position = {action: i for i, action in enumerate(learned_order)}
        for _, plan in normalized:
            if plan != sorted(plan, key=lambda action: position[action]):
                raise ValueError("inconsistent action ordering cannot be represented by bounded planner")

        program = SequencePlannerProgram(
            program_id=f"PL-{uuid.uuid4().hex[:12]}",
            target_capability=target_capability,
            target_organ=target_organ,
            rules=rules,
            source_digest=hashlib.sha256(canonical_json(list(examples)).encode("utf-8")).hexdigest(),
            training_count=len(examples),
        )
        SequencePlannerSandbox.validate(program)
        return program


class MechanismSelector:
    """
    Data-driven selector.

    It does not route on capability names. It attempts mechanism families whose
    input/output contracts fit the examples, measures training fit, then prefers
    the simplest compositional family on exact-score ties. Blind cases are never
    used for selection.
    """

    KIND_TIEBREAK = {"FIELD_MAPPER": 0, "SEQUENCE_PLANNER": 1, "RULE_PROGRAM": 2}

    @staticmethod
    def complexity(program: Mechanism) -> int:
        if isinstance(program, FieldMapperProgram):
            return len(program.operations)
        if isinstance(program, SequencePlannerProgram):
            return sum(1 + (1 if r.predicate else 0) for r in program.rules)
        if isinstance(program, RuleProgram):
            return sum(len(r.predicates) + 1 for r in program.rules) + 1
        if isinstance(program, PipelineProgram):
            return len(program.stage_program_ids) * 2
        raise TypeError("unknown mechanism")

    @classmethod
    def synthesize_candidates(
        cls,
        target_capability: str,
        target_organ: str,
        examples: Sequence[Mapping[str, Any]],
        min_support: int = 2,
    ) -> List[Mechanism]:
        candidates: List[Mechanism] = []
        expected = [e.get("expected") for e in examples]

        if expected and all(isinstance(x, Mapping) for x in expected):
            try:
                candidates.append(FieldMapperSynthesizer.synthesize(target_capability, target_organ, examples))
            except ValueError:
                pass

        if expected and all(isinstance(x, list) and all(isinstance(a, str) for a in x) for x in expected):
            try:
                candidates.append(SequencePlannerSynthesizer.synthesize(target_capability, target_organ, examples, min_support))
            except ValueError:
                pass

        try:
            candidates.append(
                RuleProgramSynthesizer.synthesize(
                    target_capability=target_capability,
                    target_organ=target_organ,
                    examples=examples,
                    min_support=min_support,
                )
            )
        except ValueError:
            pass

        if not candidates:
            raise ValueError("no supported bounded mechanism family fits the training evidence")
        return candidates


class DevelopmentalExecutiveV22(DevelopmentalExecutive):
    def __init__(self, system: "UnifiedCognitiveSystemV22"):
        self.selection_receipts: Dict[str, MechanismSelectionReceipt] = {}
        super().__init__(system)

    # Override v2.1 restoration because v2.2 persists polymorphic mechanisms.
    def _restore_development_state(self) -> None:
        with self.system.db_lock:
            rows = self.system.conn.execute("SELECT * FROM organs").fetchall()
            for row in rows:
                state = OrganState(
                    organ_id=row["organ_id"],
                    name=row["name"],
                    state_label=row["state_label"],
                    revision=int(row["revision"]),
                    mechanisms=json.loads(row["mechanisms"]),
                    updated_at=row["updated_at"],
                )
                self.organs[state.name] = state

            rows = self.system.conn.execute("SELECT * FROM mechanisms WHERE status='COMMITTED'").fetchall()
            # Load non-pipelines first so pipeline references resolve deterministically.
            decoded = [(row, json.loads(row["program_json"])) for row in rows]
            decoded.sort(key=lambda item: 1 if item[1].get("kind") == "PIPELINE" else 0)
            for row, data in decoded:
                program = self._mechanism_from_json(data)
                program.status = row["status"]
                self.programs[program.program_id] = program
                self.active_program_by_capability[program.target_capability] = program.program_id

            rows = self.system.conn.execute("SELECT receipt_json FROM mechanism_selections").fetchall()
            for row in rows:
                raw = json.loads(row["receipt_json"])
                raw["candidates"] = [SelectionCandidate(**c) for c in raw["candidates"]]
                receipt = MechanismSelectionReceipt(**raw)
                self.selection_receipts[receipt.selection_id] = receipt

    @staticmethod
    def _mechanism_from_json(data: Mapping[str, Any]) -> Mechanism:
        kind = data.get("kind", "RULE_PROGRAM")
        if kind == "RULE_PROGRAM":
            # v2.1 compatibility: rule programs had no explicit kind.
            rules = []
            for raw_rule in data["rules"]:
                predicates = [RulePredicate(**p) for p in raw_rule["predicates"]]
                rules.append(RuleSpec(predicates, raw_rule["output"], int(raw_rule["support"]), float(raw_rule["confidence"])))
            return RuleProgram(
                program_id=data["program_id"],
                target_capability=data["target_capability"],
                target_organ=data["target_organ"],
                rules=rules,
                default_output=data["default_output"],
                source_digest=data["source_digest"],
                training_count=int(data.get("training_count", 0)),
                status=data.get("status", "SHADOW"),
                created_at=data.get("created_at", utc_now().isoformat()),
            )
        if kind == "FIELD_MAPPER":
            return FieldMapperProgram(
                program_id=data["program_id"], target_capability=data["target_capability"], target_organ=data["target_organ"],
                operations=[FieldMapOp(**op) for op in data["operations"]], source_digest=data["source_digest"],
                training_count=int(data.get("training_count", 0)), status=data.get("status", "SHADOW"),
                created_at=data.get("created_at", utc_now().isoformat()),
            )
        if kind == "SEQUENCE_PLANNER":
            rules = []
            for raw in data["rules"]:
                predicate = RulePredicate(**raw["predicate"]) if raw.get("predicate") else None
                rules.append(PlannerRule(raw["action"], float(raw["order"]), predicate, int(raw["support"]), float(raw["confidence"])))
            return SequencePlannerProgram(
                program_id=data["program_id"], target_capability=data["target_capability"], target_organ=data["target_organ"],
                rules=rules, source_digest=data["source_digest"], training_count=int(data.get("training_count", 0)),
                status=data.get("status", "SHADOW"), created_at=data.get("created_at", utc_now().isoformat()),
            )
        if kind == "PIPELINE":
            return PipelineProgram(
                program_id=data["program_id"], target_capability=data["target_capability"], target_organ=data["target_organ"],
                stage_program_ids=list(data["stage_program_ids"]), source_digest=data["source_digest"],
                training_count=int(data.get("training_count", 0)), status=data.get("status", "SHADOW"),
                created_at=data.get("created_at", utc_now().isoformat()),
            )
        raise ValueError(f"unknown mechanism kind: {kind}")

    def _persist_program(self, program: Mechanism) -> None:
        with self.system.db_lock:
            self.system.conn.execute(
                """
                INSERT OR REPLACE INTO mechanisms
                (program_id, target_capability, target_organ, program_json, program_digest, status, created_at)
                VALUES(?,?,?,?,?,?,?)
                """,
                (
                    program.program_id,
                    program.target_capability,
                    program.target_organ,
                    canonical_json(_mechanism_payload(program)),
                    _mechanism_digest(program),
                    program.status,
                    program.created_at,
                ),
            )
            self.system.conn.commit()

    def _execute_mechanism(
        self,
        program: Mechanism,
        payload: Mapping[str, Any],
        ablated: bool = False,
        ablate_stage: Optional[str] = None,
    ) -> Any:
        if isinstance(program, RuleProgram):
            return BoundedRuleSandbox.execute(program, payload, ablated=ablated)
        if isinstance(program, FieldMapperProgram):
            return FieldMapperSandbox.execute(program, payload, ablated=ablated)
        if isinstance(program, SequencePlannerProgram):
            return SequencePlannerSandbox.execute(program, payload, ablated=ablated)
        if isinstance(program, PipelineProgram):
            current: Any = dict(payload)
            for stage_id in program.stage_program_ids:
                if not isinstance(current, Mapping):
                    raise ValueError("pipeline stage input must be a mapping")
                if ablated and ablate_stage is None:
                    return dict(payload)
                if stage_id == ablate_stage:
                    # Stage ablation = identity at this seam.
                    continue
                stage = self.programs.get(stage_id)
                if stage is None or stage.status != "COMMITTED":
                    raise RuntimeError(f"pipeline stage is unavailable or uncommitted: {stage_id}")
                current = self._execute_mechanism(stage, current)
            return current
        raise TypeError("unsupported mechanism")

    def _score_mechanism(
        self,
        program: Mechanism,
        cases: Sequence[Mapping[str, Any]],
        ablated: bool = False,
        ablate_stage: Optional[str] = None,
    ) -> float:
        if not cases:
            raise ValueError("evaluation cases must not be empty")
        correct = 0
        for case in cases:
            payload = case.get("input")
            if not isinstance(payload, Mapping) or "expected" not in case:
                raise ValueError("each evaluation case must contain mapping input and expected")
            predicted = self._execute_mechanism(program, payload, ablated=ablated, ablate_stage=ablate_stage)
            if canonical_json(predicted) == canonical_json(case["expected"]):
                correct += 1
        return correct / len(cases)

    def synthesize_best_mechanism(
        self,
        deficit_id: str,
        target_organ: str,
        training_examples: Sequence[Mapping[str, Any]],
        min_support: int = 2,
    ) -> Tuple[Mechanism, MechanismSelectionReceipt]:
        if deficit_id not in self.deficits:
            raise KeyError("unknown deficit")
        if target_organ not in self.organs:
            raise KeyError("unknown target organ")
        deficit = self.deficits[deficit_id]
        candidates = MechanismSelector.synthesize_candidates(
            deficit.target, target_organ, training_examples, min_support=min_support
        )

        scored: List[Tuple[float, int, int, str, Mechanism]] = []
        receipt_candidates: List[SelectionCandidate] = []
        for program in candidates:
            score = self._score_mechanism(program, training_examples)
            kind = _mechanism_kind(program)
            complexity = MechanismSelector.complexity(program)
            tiebreak = MechanismSelector.KIND_TIEBREAK.get(kind, 99)
            scored.append((-score, tiebreak, complexity, program.program_id, program))
            receipt_candidates.append(SelectionCandidate(program.program_id, kind, score, complexity))

        scored.sort(key=lambda item: item[:4])
        selected = scored[0][4]
        for candidate in receipt_candidates:
            if candidate.program_id == selected.program_id:
                candidate.selected = True
                candidate.reason = "best training fit, then contract-specific structural family, then minimum bounded complexity"
            else:
                candidate.reason = "not selected by bounded selector"

        self.programs[selected.program_id] = selected
        self._persist_program(selected)
        source_digest = hashlib.sha256(canonical_json(list(training_examples)).encode("utf-8")).hexdigest()
        receipt = MechanismSelectionReceipt(
            selection_id=f"SEL-{uuid.uuid4().hex[:12]}",
            deficit_id=deficit_id,
            target_capability=deficit.target,
            target_organ=target_organ,
            candidates=receipt_candidates,
            selected_program_id=selected.program_id,
            selected_kind=_mechanism_kind(selected),
            source_digest=source_digest,
        )
        self.selection_receipts[receipt.selection_id] = receipt
        with self.system.db_lock:
            self.system.conn.execute(
                "INSERT INTO mechanism_selections(selection_id, deficit_id, receipt_json, created_at) VALUES(?,?,?,?)",
                (receipt.selection_id, deficit_id, canonical_json(asdict(receipt)), receipt.created_at),
            )
            self.system.conn.commit()
        return selected, receipt

    def discover_pipeline(
        self,
        deficit_id: str,
        target_organ: str,
        training_examples: Sequence[Mapping[str, Any]],
        max_stages: int = 2,
    ) -> PipelineProgram:
        """Search compositions of already committed mechanisms; no capability-name routing."""
        if max_stages != 2:
            raise ValueError("v2.2 bounds pipeline discovery to exactly two stages")
        if deficit_id not in self.deficits:
            raise KeyError("unknown deficit")
        if target_organ not in self.organs:
            raise KeyError("unknown target organ")
        deficit = self.deficits[deficit_id]
        active_ids = sorted(set(self.active_program_by_capability.values()))
        if len(active_ids) < 2:
            raise ValueError("at least two committed mechanisms are required for pipeline discovery")

        viable: List[Tuple[int, str, List[str]]] = []
        for stage_ids in itertools.permutations(active_ids, 2):
            probe = PipelineProgram(
                program_id="PROBE",
                target_capability=deficit.target,
                target_organ=target_organ,
                stage_program_ids=list(stage_ids),
                source_digest="probe",
                training_count=len(training_examples),
            )
            try:
                score = self._score_mechanism(probe, training_examples)
            except (ValueError, RuntimeError, TypeError):
                continue
            if score == 1.0:
                # Deterministic tie break by stage IDs.
                viable.append((len(stage_ids), canonical_json(stage_ids), list(stage_ids)))
        if not viable:
            raise ValueError("no committed mechanism composition exactly fits the training evidence")
        viable.sort()
        stage_ids = viable[0][2]
        program = PipelineProgram(
            program_id=f"PIPE-{uuid.uuid4().hex[:12]}",
            target_capability=deficit.target,
            target_organ=target_organ,
            stage_program_ids=stage_ids,
            source_digest=hashlib.sha256(canonical_json(list(training_examples)).encode("utf-8")).hexdigest(),
            training_count=len(training_examples),
        )
        self.programs[program.program_id] = program
        self._persist_program(program)
        return program

    def evaluate_mechanism(
        self,
        program_id: str,
        blind_cases: Sequence[Mapping[str, Any]],
        min_score: Optional[float] = None,
        min_ablation_drop: float = 0.20,
    ) -> MechanismDevelopmentReceipt:
        if program_id not in self.programs:
            raise KeyError("unknown program")
        program = self.programs[program_id]
        matching_deficits = [d for d in self.deficits.values() if d.target == program.target_capability and d.status == "OPEN"]
        if not matching_deficits:
            raise ValueError("no open deficit for target capability")
        deficit = max(matching_deficits, key=lambda d: d.required - d.observed)
        required_score = float(deficit.required if min_score is None else min_score)

        candidate_score = self._score_mechanism(program, blind_cases)
        restore_score = self._score_mechanism(program, blind_cases)
        stage_ablation_scores: Dict[str, float] = {}
        if isinstance(program, PipelineProgram):
            for stage_id in program.stage_program_ids:
                stage_ablation_scores[stage_id] = self._score_mechanism(program, blind_cases, ablate_stage=stage_id)
            ablation_score = max(stage_ablation_scores.values()) if stage_ablation_scores else candidate_score
            pass_causal = bool(stage_ablation_scores) and all(
                candidate_score - score >= min_ablation_drop for score in stage_ablation_scores.values()
            )
        else:
            ablation_score = self._score_mechanism(program, blind_cases, ablated=True)
            pass_causal = candidate_score - ablation_score >= min_ablation_drop

        pass_score = candidate_score >= required_score
        pass_restore = abs(restore_score - candidate_score) <= 1e-12
        committed = pass_score and pass_causal and pass_restore

        if committed:
            verdict = "COMMIT"
            reason = "blind target passed; causal ablation passed; restore reproduced the gain"
            program.status = "COMMITTED"
            deficit.status = "RESOLVED"
            self.active_program_by_capability[program.target_capability] = program.program_id
            organ = self.organs[program.target_organ]
            if program.program_id not in organ.mechanisms:
                organ.mechanisms.append(program.program_id)
            organ.revision += 1
            organ.state_label = f"S{organ.revision}"
            organ.updated_at = utc_now().isoformat()
            self._persist_organ(organ)
            evidence = [
                f"mechanism:{program.program_id}",
                f"kind:{_mechanism_kind(program)}",
                f"program_digest:{_mechanism_digest(program)}",
                f"blind_score:{candidate_score:.6f}",
                f"organ:{program.target_organ}:{organ.state_label}",
            ]
            if stage_ablation_scores:
                evidence.extend(f"stage_ablation:{sid}:{score:.6f}" for sid, score in sorted(stage_ablation_scores.items()))
            else:
                evidence.append(f"ablation_drop:{candidate_score - ablation_score:.6f}")
            self.register_capability(program.target_capability, candidate_score, evidence)
        else:
            verdict = "ROLLBACK"
            reasons = []
            if not pass_score:
                reasons.append("blind_target_not_reached")
            if not pass_causal:
                reasons.append("ablation_not_causal")
            if not pass_restore:
                reasons.append("restore_not_reproducible")
            reason = ",".join(reasons)
            program.status = "ROLLED_BACK"

        self._persist_program(program)
        receipt = MechanismDevelopmentReceipt(
            experiment_id=f"DEV22-{uuid.uuid4().hex[:12]}",
            program_id=program.program_id,
            mechanism_kind=_mechanism_kind(program),
            target_capability=program.target_capability,
            target_organ=program.target_organ,
            train_cases=program.training_count,
            blind_cases=len(blind_cases),
            candidate_score=candidate_score,
            ablation_score=ablation_score,
            restore_score=restore_score,
            min_score=required_score,
            min_ablation_drop=min_ablation_drop,
            verdict=verdict,
            state_committed=committed,
            reason=reason,
            program_digest=_mechanism_digest(program),
            stage_ablation_scores=stage_ablation_scores,
        )
        with self.system.db_lock:
            self.system.conn.execute(
                "INSERT INTO developmental_experiments(experiment_id, program_id, receipt_json, created_at) VALUES(?,?,?,?)",
                (receipt.experiment_id, program.program_id, canonical_json(asdict(receipt)), receipt.created_at),
            )
            self.system.conn.commit()
        return receipt

    # v2.1 public name remains usable, now delegates to polymorphic evaluator.
    def evaluate_program(self, program_id: str, blind_cases: Sequence[Mapping[str, Any]], min_score: Optional[float] = None,
                         min_ablation_drop: float = 0.20) -> MechanismDevelopmentReceipt:
        return self.evaluate_mechanism(program_id, blind_cases, min_score, min_ablation_drop)

    def execute_capability(self, capability: str, payload: Mapping[str, Any]) -> Any:
        program_id = self.active_program_by_capability.get(capability)
        if not program_id:
            raise KeyError(f"no committed executable mechanism for capability: {capability}")
        program = self.programs[program_id]
        if program.status != "COMMITTED":
            raise RuntimeError("active mechanism is not committed")
        return self._execute_mechanism(program, payload)

    def developmental_snapshot(self) -> Dict[str, Any]:
        base = super().developmental_snapshot()
        base["mechanism_kinds"] = {
            capability: _mechanism_kind(self.programs[program_id])
            for capability, program_id in sorted(self.active_program_by_capability.items())
        }
        base["selections"] = {sid: asdict(r) for sid, r in sorted(self.selection_receipts.items())}
        return base


class UnifiedCognitiveSystemV22(UnifiedCognitiveSystemV21):
    SCHEMA_VERSION = 4

    def _init_schema(self) -> None:
        super()._init_schema()
        with self.db_lock:
            self.conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS mechanism_selections (
                    selection_id TEXT PRIMARY KEY,
                    deficit_id TEXT NOT NULL,
                    receipt_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                """
            )
            self.conn.commit()

    def __init__(self, db_path: str = "cognitive_system_v2_2.db", embedder=None):
        # Skip the v2.1 constructor's temporary DevelopmentalExecutive: on restart it
        # cannot decode v2.2 polymorphic mechanisms. The v2 base only restores common
        # state, then we install the v2.2 executive once. Dynamic _init_schema still
        # creates all v2.1/v2.2 tables before executive restoration.
        UnifiedCognitiveSystem.__init__(self, db_path=db_path, embedder=embedder)
        self.executive = DevelopmentalExecutiveV22(self)


__all__ = [
    "DevelopmentalExecutiveV22",
    "FieldMapOp",
    "FieldMapperProgram",
    "FieldMapperSynthesizer",
    "MechanismDevelopmentReceipt",
    "MechanismSelectionReceipt",
    "MechanismSelector",
    "PipelineProgram",
    "PlannerRule",
    "SequencePlannerProgram",
    "SequencePlannerSynthesizer",
    "UnifiedCognitiveSystemV22",
]
