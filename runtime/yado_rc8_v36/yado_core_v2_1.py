from __future__ import annotations

import hashlib
import json
import re
import uuid
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from yado_core_v2 import (
    CausalExecutive,
    GoalState,
    UnifiedCognitiveSystem,
    canonical_json,
    utc_now,
)


# ---------------------------------------------------------------------------
# Permanent organs + evolving state labels
# ---------------------------------------------------------------------------
@dataclass
class OrganState:
    organ_id: str
    name: str
    state_label: str
    revision: int
    mechanisms: List[str] = field(default_factory=list)
    updated_at: str = field(default_factory=lambda: utc_now().isoformat())


@dataclass
class RulePredicate:
    op: str
    field: str
    value: Any


@dataclass
class RuleSpec:
    predicates: List[RulePredicate]
    output: Any
    support: int
    confidence: float


@dataclass
class RuleProgram:
    program_id: str
    target_capability: str
    target_organ: str
    rules: List[RuleSpec]
    default_output: Any
    source_digest: str
    training_count: int
    status: str = "SHADOW"
    created_at: str = field(default_factory=lambda: utc_now().isoformat())

    def digest(self) -> str:
        payload = {
            "program_id": self.program_id,
            "target_capability": self.target_capability,
            "target_organ": self.target_organ,
            "rules": [
                {
                    "predicates": [asdict(p) for p in rule.predicates],
                    "output": rule.output,
                    "support": rule.support,
                    "confidence": rule.confidence,
                }
                for rule in self.rules
            ],
            "default_output": self.default_output,
            "source_digest": self.source_digest,
            "training_count": self.training_count,
        }
        return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()


@dataclass
class DevelopmentReceipt:
    experiment_id: str
    program_id: str
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
    created_at: str = field(default_factory=lambda: utc_now().isoformat())


class BoundedRuleSandbox:
    """Pure-data executor. No eval/exec, filesystem, subprocess, imports, or network."""

    ALLOWED_OPS = {"EQ", "EXISTS", "TRUTHY", "FALSY", "CONTAINS", "TEXT_HAS_TOKEN"}
    MAX_RULES = 12
    MAX_PREDICATES_PER_RULE = 4
    MAX_TEXT_LENGTH = 16_000

    @staticmethod
    def _tokenize(text: str) -> List[str]:
        return re.findall(r"[^\W_]+", text.lower(), flags=re.UNICODE)

    @classmethod
    def _match(cls, predicate: RulePredicate, payload: Mapping[str, Any]) -> bool:
        if predicate.op not in cls.ALLOWED_OPS:
            raise ValueError(f"unsupported predicate op: {predicate.op}")
        if predicate.op == "EXISTS":
            return predicate.field in payload
        value = payload.get(predicate.field)
        if predicate.op == "EQ":
            return value == predicate.value
        if predicate.op == "TRUTHY":
            return bool(value)
        if predicate.op == "FALSY":
            return not bool(value)
        if predicate.op == "CONTAINS":
            try:
                return predicate.value in value
            except TypeError:
                return False
        if predicate.op == "TEXT_HAS_TOKEN":
            if not isinstance(value, str) or len(value) > cls.MAX_TEXT_LENGTH:
                return False
            return str(predicate.value).lower() in cls._tokenize(value)
        return False

    @classmethod
    def validate(cls, program: RuleProgram) -> None:
        if len(program.rules) > cls.MAX_RULES:
            raise ValueError("program exceeds MAX_RULES")
        for rule in program.rules:
            if not rule.predicates or len(rule.predicates) > cls.MAX_PREDICATES_PER_RULE:
                raise ValueError("invalid predicate count")
            for predicate in rule.predicates:
                if predicate.op not in cls.ALLOWED_OPS:
                    raise ValueError(f"unsupported predicate op: {predicate.op}")

    @classmethod
    def execute(cls, program: RuleProgram, payload: Mapping[str, Any], ablated: bool = False) -> Any:
        cls.validate(program)
        if ablated:
            return program.default_output
        for rule in program.rules:
            if all(cls._match(predicate, payload) for predicate in rule.predicates):
                return rule.output
        return program.default_output


class RuleProgramSynthesizer:
    """
    Small symbolic learner for bounded programs.

    It derives rules from labeled examples; it does not contain domain rules such
    as "and means conjunction". Supported candidates are exact scalar equality
    and token-presence rules for text fields. Rules must be pure on training data
    and meet minimum support, which rejects one-off memorization by default.
    """

    @staticmethod
    def _freeze(value: Any) -> str:
        return canonical_json(value)

    @classmethod
    def synthesize(
        cls,
        target_capability: str,
        target_organ: str,
        examples: Sequence[Mapping[str, Any]],
        min_support: int = 2,
        max_rules: int = 12,
    ) -> RuleProgram:
        if len(examples) < 3:
            raise ValueError("at least 3 training examples are required")
        if min_support < 2:
            raise ValueError("min_support must be >= 2 to reject one-shot memorization")

        normalized: List[Tuple[Mapping[str, Any], Any]] = []
        for example in examples:
            payload = example.get("input")
            if not isinstance(payload, Mapping) or "expected" not in example:
                raise ValueError("each example must contain mapping input and expected")
            normalized.append((payload, example["expected"]))

        outputs = [cls._freeze(expected) for _, expected in normalized]
        default_key, _ = Counter(outputs).most_common(1)[0]
        output_values = {cls._freeze(expected): expected for _, expected in normalized}
        default_output = output_values[default_key]

        feature_hits: Dict[Tuple[str, str, str], List[int]] = defaultdict(list)
        feature_values: Dict[Tuple[str, str, str], Any] = {}

        for idx, (payload, _) in enumerate(normalized):
            for field, value in payload.items():
                if isinstance(value, (str, int, float, bool)) or value is None:
                    key = ("EQ", str(field), cls._freeze(value))
                    feature_hits[key].append(idx)
                    feature_values[key] = value
                if isinstance(value, str) and len(value) <= BoundedRuleSandbox.MAX_TEXT_LENGTH:
                    for token in sorted(set(BoundedRuleSandbox._tokenize(value))):
                        if len(token) < 2:
                            continue
                        key = ("TEXT_HAS_TOKEN", str(field), token)
                        feature_hits[key].append(idx)
                        feature_values[key] = token

        candidates: List[Tuple[int, float, str, RuleSpec]] = []
        for (op, field, frozen_value), indexes in feature_hits.items():
            support = len(indexes)
            if support < min_support:
                continue
            labels = [outputs[i] for i in indexes]
            label_key, count = Counter(labels).most_common(1)[0]
            confidence = count / support
            if confidence < 1.0:
                continue
            output = output_values[label_key]
            # A rule that only predicts the default output adds no capability.
            if cls._freeze(output) == default_key:
                continue
            predicate = RulePredicate(op=op, field=field, value=feature_values[(op, field, frozen_value)])
            rule = RuleSpec(predicates=[predicate], output=output, support=support, confidence=confidence)
            # Higher support first; prefer scalar EQ over text token when equally strong.
            op_priority = 1.0 if op == "EQ" else 0.5
            candidates.append((support, op_priority, canonical_json(asdict(rule)), rule))

        candidates.sort(key=lambda item: (-item[0], -item[1], item[2]))
        selected: List[RuleSpec] = []
        covered_signatures = set()
        for _, _, _, rule in candidates:
            signature = (cls._freeze(rule.output), canonical_json([asdict(p) for p in rule.predicates]))
            if signature in covered_signatures:
                continue
            selected.append(rule)
            covered_signatures.add(signature)
            if len(selected) >= min(max_rules, BoundedRuleSandbox.MAX_RULES):
                break

        if not selected:
            raise ValueError("no stable bounded rule could be synthesized from the examples")

        source_digest = hashlib.sha256(canonical_json(list(examples)).encode("utf-8")).hexdigest()
        program = RuleProgram(
            program_id=f"P-{uuid.uuid4().hex[:12]}",
            target_capability=target_capability,
            target_organ=target_organ,
            rules=selected,
            default_output=default_output,
            source_digest=source_digest,
            training_count=len(examples),
        )
        BoundedRuleSandbox.validate(program)
        return program


class DevelopmentalExecutive(CausalExecutive):
    DEFAULT_ORGANS = (
        ("ORG-PERCEPTION", "PERCEPTION"),
        ("ORG-MEMORY", "MEMORY"),
        ("ORG-LOGIC", "LOGIC"),
        ("ORG-THINKING", "THINKING"),
        ("ORG-INTELLIGENCE", "INTELLIGENCE"),
        ("ORG-SELF-MODEL", "SELF_MODEL"),
        ("ORG-WORKSPACE", "CONSCIOUS_WORKSPACE"),
        ("ORG-GOALS", "MOTIVE_GOALS"),
        ("ORG-EXECUTIVE", "GENERATIVE_EXECUTIVE"),
        ("ORG-LEARNING", "LEARNING"),
    )

    def __init__(self, system: "UnifiedCognitiveSystemV21"):
        self.organs: Dict[str, OrganState] = {}
        self.programs: Dict[str, RuleProgram] = {}
        self.active_program_by_capability: Dict[str, str] = {}
        super().__init__(system)
        self._restore_development_state()
        self._ensure_organs()

    def _ensure_organs(self) -> None:
        for organ_id, name in self.DEFAULT_ORGANS:
            if name in self.organs:
                continue
            state = OrganState(organ_id=organ_id, name=name, state_label="S0", revision=0)
            self.organs[name] = state
            self._persist_organ(state)

    def _persist_organ(self, organ: OrganState) -> None:
        with self.system.db_lock:
            self.system.conn.execute(
                """
                INSERT OR REPLACE INTO organs(organ_id, name, state_label, revision, mechanisms, updated_at)
                VALUES(?,?,?,?,?,?)
                """,
                (
                    organ.organ_id,
                    organ.name,
                    organ.state_label,
                    organ.revision,
                    canonical_json(organ.mechanisms),
                    organ.updated_at,
                ),
            )
            self.system.conn.commit()

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
            for row in rows:
                program = self._program_from_json(json.loads(row["program_json"]))
                program.status = row["status"]
                self.programs[program.program_id] = program
                self.active_program_by_capability[program.target_capability] = program.program_id

    @staticmethod
    def _program_from_json(data: Mapping[str, Any]) -> RuleProgram:
        rules = []
        for raw_rule in data["rules"]:
            predicates = [RulePredicate(**p) for p in raw_rule["predicates"]]
            rules.append(
                RuleSpec(
                    predicates=predicates,
                    output=raw_rule["output"],
                    support=int(raw_rule["support"]),
                    confidence=float(raw_rule["confidence"]),
                )
            )
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

    def synthesize_program(
        self,
        deficit_id: str,
        target_organ: str,
        training_examples: Sequence[Mapping[str, Any]],
        min_support: int = 2,
    ) -> RuleProgram:
        if deficit_id not in self.deficits:
            raise KeyError("unknown deficit")
        if target_organ not in self.organs:
            raise KeyError("unknown target organ")
        deficit = self.deficits[deficit_id]
        program = RuleProgramSynthesizer.synthesize(
            target_capability=deficit.target,
            target_organ=target_organ,
            examples=training_examples,
            min_support=min_support,
        )
        self.programs[program.program_id] = program
        self._persist_program(program)
        return program

    def _persist_program(self, program: RuleProgram) -> None:
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
                    canonical_json(asdict(program)),
                    program.digest(),
                    program.status,
                    program.created_at,
                ),
            )
            self.system.conn.commit()

    @staticmethod
    def _score(program: RuleProgram, cases: Sequence[Mapping[str, Any]], ablated: bool = False) -> float:
        if not cases:
            raise ValueError("evaluation cases must not be empty")
        correct = 0
        for case in cases:
            payload = case.get("input")
            if not isinstance(payload, Mapping) or "expected" not in case:
                raise ValueError("each evaluation case must contain mapping input and expected")
            predicted = BoundedRuleSandbox.execute(program, payload, ablated=ablated)
            if canonical_json(predicted) == canonical_json(case["expected"]):
                correct += 1
        return correct / len(cases)

    def evaluate_program(
        self,
        program_id: str,
        blind_cases: Sequence[Mapping[str, Any]],
        min_score: Optional[float] = None,
        min_ablation_drop: float = 0.20,
    ) -> DevelopmentReceipt:
        if program_id not in self.programs:
            raise KeyError("unknown program")
        program = self.programs[program_id]
        matching_deficits = [d for d in self.deficits.values() if d.target == program.target_capability and d.status == "OPEN"]
        if not matching_deficits:
            raise ValueError("no open deficit for target capability")
        deficit = max(matching_deficits, key=lambda d: d.required - d.observed)
        required_score = float(deficit.required if min_score is None else min_score)

        candidate_score = self._score(program, blind_cases, ablated=False)
        ablation_score = self._score(program, blind_cases, ablated=True)
        restore_score = self._score(program, blind_cases, ablated=False)
        ablation_drop = candidate_score - ablation_score

        pass_score = candidate_score >= required_score
        pass_causal = ablation_drop >= min_ablation_drop
        pass_restore = abs(restore_score - candidate_score) <= 1e-12
        committed = pass_score and pass_causal and pass_restore

        if committed:
            verdict = "COMMIT"
            reason = "blind target passed; ablation removed the gain; restore reproduced the gain"
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
            self.register_capability(
                program.target_capability,
                candidate_score,
                [
                    f"program:{program.program_id}",
                    f"program_digest:{program.digest()}",
                    f"blind_score:{candidate_score:.6f}",
                    f"ablation_drop:{ablation_drop:.6f}",
                    f"organ:{program.target_organ}:{organ.state_label}",
                ],
            )
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
        receipt = DevelopmentReceipt(
            experiment_id=f"DEV-{uuid.uuid4().hex[:12]}",
            program_id=program.program_id,
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
            program_digest=program.digest(),
        )
        with self.system.db_lock:
            self.system.conn.execute(
                "INSERT INTO developmental_experiments(experiment_id, program_id, receipt_json, created_at) VALUES(?,?,?,?)",
                (receipt.experiment_id, program.program_id, canonical_json(asdict(receipt)), receipt.created_at),
            )
            self.system.conn.commit()
        return receipt

    def execute_capability(self, capability: str, payload: Mapping[str, Any]) -> Any:
        program_id = self.active_program_by_capability.get(capability)
        if not program_id:
            raise KeyError(f"no committed executable mechanism for capability: {capability}")
        program = self.programs[program_id]
        if program.status != "COMMITTED":
            raise RuntimeError("active mechanism is not committed")
        return BoundedRuleSandbox.execute(program, payload)

    def developmental_snapshot(self) -> Dict[str, Any]:
        return {
            "organs": {name: asdict(state) for name, state in sorted(self.organs.items())},
            "active_programs": dict(sorted(self.active_program_by_capability.items())),
            "capabilities": {name: asdict(state) for name, state in sorted(self.capabilities.items())},
        }


class UnifiedCognitiveSystemV21(UnifiedCognitiveSystem):
    SCHEMA_VERSION = 3

    def _init_schema(self) -> None:
        super()._init_schema()
        with self.db_lock:
            self.conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS organs (
                    organ_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL UNIQUE,
                    state_label TEXT NOT NULL,
                    revision INTEGER NOT NULL,
                    mechanisms TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS mechanisms (
                    program_id TEXT PRIMARY KEY,
                    target_capability TEXT NOT NULL,
                    target_organ TEXT NOT NULL,
                    program_json TEXT NOT NULL,
                    program_digest TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS developmental_experiments (
                    experiment_id TEXT PRIMARY KEY,
                    program_id TEXT NOT NULL,
                    receipt_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                """
            )
            self.conn.commit()

    def __init__(self, db_path: str = "cognitive_system_v2_1.db", embedder=None):
        super().__init__(db_path=db_path, embedder=embedder)
        # Replace v2 metric-only executive with the v2.1 executable developmental executive.
        self.executive = DevelopmentalExecutive(self)


__all__ = [
    "BoundedRuleSandbox",
    "DevelopmentReceipt",
    "DevelopmentalExecutive",
    "OrganState",
    "RuleProgram",
    "RuleProgramSynthesizer",
    "UnifiedCognitiveSystemV21",
]
