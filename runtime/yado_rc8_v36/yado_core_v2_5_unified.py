from __future__ import annotations

import hashlib
import json
import os
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence

from yado_core_v2 import HashingEmbedder, canonical_json, utc_now
from yado_core_v2_1 import BoundedRuleSandbox, RuleProgram, RuleProgramSynthesizer
from yado_core_v2_4_audited import UnifiedCognitiveSystemV24Audited
from yado_notion_training_development import ADMISSION_TRAIN
from yado_phase_a_shadow import Case
from yado_primitive_genesis_cycle1 import (
    FailureDrivenSchemaInducer,
    RESOURCE_EVIDENCE,
    baseline_score,
)

ROOT = Path(__file__).resolve().parent


@dataclass(frozen=True)
class CycleTask:
    name: str
    train: Sequence[Case]
    blind: Sequence[Case]
    live_input: Any
    expected_live: Any


@dataclass(frozen=True)
class CycleRequest:
    resource_id: str
    resource_query: str
    actions: Sequence[Mapping[str, str]]
    features: Mapping[str, float]
    task: CycleTask


class UnifiedYADOKernelV25(UnifiedCognitiveSystemV24Audited):
    """Single YADO developmental runtime for the currently proven bounded layers.

    The class deliberately chooses the YADO v2.4 audited lineage as the sole
    active runtime. Nova-Core v2.5 and older YADO lines are registered as
    historical/reference artifacts, not instantiated as competing authorities.

    Integrated causal path:
      MEMORY -> THINKING -> LOGIC -> INTELLIGENCE -> MECHANISM/EXECUTION
      -> LEARNING -> MEMORY.

    This is still a shadow developmental runtime. It does not claim AGI or a
    substrate-free self-invention mechanism.
    """

    SCHEMA_VERSION = 7
    PROFILE = "YADO_V2_5_UNIFIED_SHADOW"

    def _init_schema(self) -> None:
        super()._init_schema()
        with self.db_lock:
            self.conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS unified_models (
                    model_name TEXT PRIMARY KEY,
                    organ TEXT NOT NULL,
                    capability TEXT NOT NULL,
                    model_json TEXT NOT NULL,
                    source_path TEXT NOT NULL,
                    source_sha256 TEXT NOT NULL,
                    status TEXT NOT NULL,
                    loaded_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS unified_memory_events (
                    memory_id TEXT PRIMARY KEY,
                    cycle_id TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    payload_sha256 TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS unified_cycles (
                    cycle_id TEXT PRIMARY KEY,
                    request_json TEXT NOT NULL,
                    result_json TEXT NOT NULL,
                    trace_json TEXT NOT NULL,
                    success INTEGER NOT NULL,
                    created_at TEXT NOT NULL
                );
                """
            )
            self.conn.commit()

    def __init__(self, db_path: str = "yado_v25_unified_shadow.db"):
        # Keep the test/development runtime restart-stable without depending on
        # external secrets. This key protects only this local shadow DB.
        os.environ.setdefault("YADO_MASTER_KEY", "yado-v25-unified-local-shadow-key")
        super().__init__(db_path=db_path, embedder=HashingEmbedder(128))
        self.models: Dict[str, Any] = {}
        self.logic_program: Optional[RuleProgram] = None
        self._load_verified_developmental_models()
        self._bootstrap_logic_program()
        self._bootstrap_external_evidence()

    # ------------------------------------------------------------------
    # Registry / persistence
    # ------------------------------------------------------------------
    @staticmethod
    def _file_sha(path: Path) -> str:
        h = hashlib.sha256()
        with path.open("rb") as fh:
            for chunk in iter(lambda: fh.read(1024 * 1024), b""):
                h.update(chunk)
        return h.hexdigest()

    def _register_model(
        self,
        name: str,
        organ: str,
        capability: str,
        model: Any,
        source_path: Path,
        status: str = "SHADOW_SUPPORTED",
    ) -> None:
        digest = self._file_sha(source_path)
        self.models[name] = model
        with self.db_lock:
            self.conn.execute(
                """INSERT OR REPLACE INTO unified_models
                   (model_name,organ,capability,model_json,source_path,source_sha256,status,loaded_at)
                   VALUES(?,?,?,?,?,?,?,?)""",
                (
                    name,
                    organ,
                    capability,
                    canonical_json(model),
                    str(source_path),
                    digest,
                    status,
                    utc_now().isoformat(),
                ),
            )
            self.conn.commit()

    def _load_verified_developmental_models(self) -> None:
        cognitive_path = ROOT / "yado_cognitive_training_cycle1_report.json"
        thinking_path = ROOT / "yado_thinking_training_cycle2_report.json"
        resource_path = ROOT / "yado_resource_intelligence_cycle8_report.json"
        primitive_path = ROOT / "yado_primitive_genesis_cycle1_report.json"

        cognitive = json.loads(cognitive_path.read_text(encoding="utf-8"))
        intelligence = next(r for r in cognitive["runs"] if r["organ"] == "INTELLIGENCE")
        logic = next(r for r in cognitive["runs"] if r["organ"] == "LOGIC")
        if intelligence["verdict"] != "SHADOW_SUPPORTED" or logic["verdict"] != "SHADOW_SUPPORTED":
            raise RuntimeError("verified cognitive models are not in supported state")
        self._register_model(
            "INTELLIGENCE_STRATEGY_TREE",
            "INTELLIGENCE",
            intelligence["capability"],
            intelligence["details"]["tree"],
            cognitive_path,
        )
        self._register_model(
            "LOGIC_TRAINING_EVIDENCE",
            "LOGIC",
            logic["capability"],
            {
                "tasks": logic["details"]["tasks"],
                "host_boolean_meta_ops": logic["details"]["host_boolean_meta_ops"],
            },
            cognitive_path,
        )

        thinking = json.loads(thinking_path.read_text(encoding="utf-8"))["run"]
        if thinking["verdict"] != "SHADOW_SUPPORTED":
            raise RuntimeError("thinking model is not in supported state")
        self._register_model(
            "THINKING_PRECEDENCE_GRAPH",
            "THINKING",
            thinking["capability"],
            thinking["details"]["learned_edges"],
            thinking_path,
        )

        resource = json.loads(resource_path.read_text(encoding="utf-8"))
        if resource.get("verdict") != "SHADOW_SUPPORTED_BOUNDED":
            raise RuntimeError("resource intelligence model is not supported")
        self._register_model(
            "RESOURCE_INTELLIGENCE_CONFIG",
            "INTELLIGENCE",
            "bounded_resource_selection",
            resource["selected"],
            resource_path,
            status=resource["verdict"],
        )

        primitive = json.loads(primitive_path.read_text(encoding="utf-8"))
        if primitive.get("verdict") != "SHADOW_SUPPORTED_BOUNDED_PRIMITIVE_GENESIS":
            # Older report variants put the verdict under summary.
            pv = primitive.get("summary", {}).get("verdict")
            if pv != "SHADOW_SUPPORTED_BOUNDED_PRIMITIVE_GENESIS":
                raise RuntimeError("primitive genesis evidence is not supported")
        self._register_model(
            "PRIMITIVE_GENESIS_META_SCHEMA",
            "GENERATIVE_EXECUTIVE",
            "bounded_primitive_genesis",
            {
                "family": "AFFINE_CONTIGUOUS_SLICE_MAP",
                "host_supplied_meta_schema": True,
                "task_specific_operator_supplied": False,
            },
            primitive_path,
            status="SHADOW_SUPPORTED_BOUNDED_PRIMITIVE_GENESIS",
        )

    def _bootstrap_logic_program(self) -> None:
        # Re-synthesize the previously validated external-evidence admission
        # program from its revealed training corpus. No hand-coded status table
        # is used by the runtime executor.
        self.logic_program = RuleProgramSynthesizer.synthesize(
            target_capability="external_evidence_admission",
            target_organ="LOGIC",
            examples=ADMISSION_TRAIN,
            min_support=2,
        )
        model = {
            "program_id": self.logic_program.program_id,
            "source_digest": self.logic_program.source_digest,
            "rules": [
                {
                    "predicates": [asdict(p) for p in r.predicates],
                    "output": r.output,
                    "support": r.support,
                    "confidence": r.confidence,
                }
                for r in self.logic_program.rules
            ],
            "default_output": self.logic_program.default_output,
        }
        # The training file is the evidence source for this executable model.
        self._register_model(
            "LOGIC_EXTERNAL_EVIDENCE_ADMISSION",
            "LOGIC",
            "external_evidence_admission",
            model,
            ROOT / "yado_notion_training_development.py",
        )

    def _bootstrap_external_evidence(self) -> None:
        sources = {
            "github:microsoft/prose:tutorial": {
                "text": RESOURCE_EVIDENCE["microsoft/prose"]["summary"],
                "metadata": {
                    "provider": "github",
                    "repo": "microsoft/prose",
                    "status": "ACTIVE_VERIFIED",
                    "authority": False,
                    "tutorial_sha": RESOURCE_EVIDENCE["microsoft/prose"]["tutorial_sha"],
                },
                "tags": ["external_evidence", "program_synthesis", "dsl", "verified_source"],
            },
            "github:egraphs-good/egg": {
                "text": RESOURCE_EVIDENCE["egraphs-good/egg"]["summary"],
                "metadata": {
                    "provider": "github",
                    "repo": "egraphs-good/egg",
                    "status": "EXTERNAL_EVIDENCE",
                    "authority": False,
                },
                "tags": ["external_evidence", "egraphs", "synthesis"],
            },
            "github:emina/rosette": {
                "text": RESOURCE_EVIDENCE["emina/rosette"]["summary"],
                "metadata": {
                    "provider": "github",
                    "repo": "emina/rosette",
                    "status": "EXTERNAL_EVIDENCE",
                    "authority": False,
                },
                "tags": ["external_evidence", "solver_aided", "synthesis"],
            },
        }
        for resource_id, spec in sources.items():
            if self.get_resource(resource_id, include_text=False) is None:
                self.add_resource(resource_id, spec["text"], metadata=spec["metadata"], tags=spec["tags"])

    def remember(self, cycle_id: str, kind: str, payload: Mapping[str, Any]) -> str:
        raw = canonical_json(dict(payload))
        digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()
        memory_id = f"MEM-{digest[:16]}-{uuid.uuid4().hex[:6]}"
        with self.db_lock:
            self.conn.execute(
                """INSERT INTO unified_memory_events
                   (memory_id,cycle_id,kind,payload_json,payload_sha256,created_at)
                   VALUES(?,?,?,?,?,?)""",
                (memory_id, cycle_id, kind, raw, digest, utc_now().isoformat()),
            )
            self.conn.commit()
        return memory_id

    def memory_count(self) -> int:
        with self.db_lock:
            return int(self.conn.execute("SELECT COUNT(*) FROM unified_memory_events").fetchone()[0])

    # ------------------------------------------------------------------
    # Organs
    # ------------------------------------------------------------------
    def thinking_plan(self, actions: Sequence[Mapping[str, str]]) -> List[str]:
        edges = self.models["THINKING_PRECEDENCE_GRAPH"]
        by_role = {str(a["role"]): str(a["id"]) for a in actions}
        present = set(by_role)
        adj = {r: set() for r in present}
        indeg = {r: 0 for r in present}
        wins = {r: 0 for r in present}
        for e in edges:
            a, b = e["before"], e["after"]
            if a in present and b in present:
                if b not in adj[a]:
                    adj[a].add(b)
                    indeg[b] += 1
                wins[a] += 1
                wins[b] -= 1
        ordered: List[str] = []
        while len(ordered) < len(present):
            zeros = [r for r in present if r not in ordered and indeg[r] == 0]
            if not zeros:
                zeros = [r for r in present if r not in ordered]
            zeros.sort(key=lambda r: (-wins[r], r))
            role = zeros[0]
            ordered.append(role)
            for nxt in adj[role]:
                indeg[nxt] -= 1
        return [by_role[r] for r in ordered]

    def thinking_plan_valid(self, actions: Sequence[Mapping[str, str]], plan_ids: Sequence[str]) -> bool:
        role_by_id = {str(a["id"]): str(a["role"]) for a in actions}
        pos = {role_by_id[aid]: i for i, aid in enumerate(plan_ids) if aid in role_by_id}
        for e in self.models["THINKING_PRECEDENCE_GRAPH"]:
            a, b = e["before"], e["after"]
            if a in pos and b in pos and pos[a] >= pos[b]:
                return False
        return len(plan_ids) == len(actions) and len(set(plan_ids)) == len(actions)

    def logic_admission(self, source_status: str, ablated: bool = False) -> str:
        if self.logic_program is None:
            raise RuntimeError("logic program not loaded")
        if ablated:
            # Component removed: no positive admission certificate is available.
            return "WITHHOLD"
        return str(BoundedRuleSandbox.execute(self.logic_program, {"layer_status": source_status}))

    @staticmethod
    def _tree_predict_obj(node: Mapping[str, Any], x: Mapping[str, float]) -> str:
        cur: Mapping[str, Any] = node
        while "label" not in cur:
            feature = str(cur["feature"])
            threshold = float(cur["threshold"])
            cur = cur["left"] if float(x.get(feature, 0.0)) <= threshold else cur["right"]
        return str(cur["label"])

    def intelligence_strategy(self, features: Mapping[str, float], ablated: bool = False) -> str:
        if ablated:
            return "WITHHOLD"
        return self._tree_predict_obj(self.models["INTELLIGENCE_STRATEGY_TREE"], features)

    # ------------------------------------------------------------------
    # Causal cycle
    # ------------------------------------------------------------------
    @staticmethod
    def _serialize_case(c: Case) -> Dict[str, Any]:
        return {"case_id": c.case_id, "input": c.input, "expected": c.expected}

    @classmethod
    def _serialize_request(cls, request: CycleRequest) -> Dict[str, Any]:
        return {
            "resource_id": request.resource_id,
            "resource_query": request.resource_query,
            "actions": list(request.actions),
            "features": dict(request.features),
            "task": {
                "name": request.task.name,
                "train": [cls._serialize_case(c) for c in request.task.train],
                "blind": [cls._serialize_case(c) for c in request.task.blind],
                "live_input": request.task.live_input,
                "expected_live": request.task.expected_live,
            },
        }

    def _record_cycle(self, cycle_id: str, request: CycleRequest, result: Mapping[str, Any], trace: Sequence[Mapping[str, Any]]) -> None:
        with self.db_lock:
            self.conn.execute(
                """INSERT OR REPLACE INTO unified_cycles
                   (cycle_id,request_json,result_json,trace_json,success,created_at)
                   VALUES(?,?,?,?,?,?)""",
                (
                    cycle_id,
                    canonical_json(self._serialize_request(request)),
                    canonical_json(dict(result)),
                    canonical_json(list(trace)),
                    1 if result.get("cycle_success") else 0,
                    utc_now().isoformat(),
                ),
            )
            self.conn.commit()

    def run_causal_cycle(self, request: CycleRequest, ablate: Optional[Iterable[str]] = None) -> Dict[str, Any]:
        ablated = set(ablate or [])
        cycle_id = f"CYCLE-{uuid.uuid4().hex[:12]}"
        trace: List[Dict[str, Any]] = []
        mem_before = self.memory_count()

        # MEMORY -> source/evidence context
        source = None if "MEMORY_READ" in ablated else self.get_resource(request.resource_id, include_text=True)
        source_status = str((source or {}).get("metadata", {}).get("status", "UNKNOWN"))
        trace.append({
            "stage": "MEMORY",
            "resource_id": request.resource_id,
            "found": source is not None,
            "source_status": source_status,
            "ablated": "MEMORY_READ" in ablated,
        })

        # THINKING -> causal action ordering
        if "THINKING" in ablated:
            plan_ids = [str(a["id"]) for a in request.actions]
        else:
            plan_ids = self.thinking_plan(request.actions)
        plan_valid = self.thinking_plan_valid(request.actions, plan_ids)
        trace.append({
            "stage": "THINKING",
            "plan_ids": plan_ids,
            "plan_valid": plan_valid,
            "ablated": "THINKING" in ablated,
        })

        # DIAGNOSE uses actual old-substrate fit rather than a supplied label.
        old_train = baseline_score(request.task.train)
        expressiveness_gap = 1.0 if float(old_train["train_exact"]) < 1.0 else 0.0

        # LOGIC -> evidence admission certificate
        admission = self.logic_admission(source_status, ablated="LOGIC" in ablated)
        evidence_complete = 1.0 if admission == "ALLOW" else 0.0
        trace.append({
            "stage": "LOGIC",
            "source_status": source_status,
            "admission": admission,
            "evidence_complete": evidence_complete,
            "ablated": "LOGIC" in ablated,
        })

        # INTELLIGENCE -> developmental strategy from evidence + diagnosis.
        features = dict(request.features)
        features["evidence_complete"] = evidence_complete
        features["expressiveness_gap"] = expressiveness_gap
        strategy = self.intelligence_strategy(features, ablated="INTELLIGENCE" in ablated)
        trace.append({
            "stage": "INTELLIGENCE",
            "features": features,
            "strategy": strategy,
            "ablated": "INTELLIGENCE" in ablated,
        })

        action: Dict[str, Any] = {
            "strategy": strategy,
            "old_substrate_train_exact": float(old_train["train_exact"]),
        }
        live_output = None
        blind_score = 0.0
        ablation_score = 0.0
        restore_score = 0.0
        mechanism_digest = None

        prerequisites_ok = plan_valid and admission == "ALLOW"
        if strategy == "EXPAND_REPRESENTATION" and prerequisites_ok:
            if "MECHANISM" in ablated:
                # Remove the learned primitive-genesis layer; use old fixed substrate.
                blind_score = float(baseline_score(request.task.blind)["train_exact"])
                action.update({"mechanism": "OLD_FIXED_PHASE_A", "verdict": "NO_EXPRESSIVE_MECHANISM"})
            else:
                inducer = FailureDrivenSchemaInducer()
                best, generated = inducer.search(request.task.train)
                if best is not None:
                    frozen = best.schema
                    mechanism_digest = frozen.digest
                    blind_score = float(inducer.score(frozen, request.task.blind).exact)
                    ablation_score = float(baseline_score(request.task.blind)["train_exact"])
                    restore_score = float(inducer.score(frozen, request.task.blind).exact)
                    if best.exact == 1.0 and blind_score == 1.0 and restore_score == 1.0 and blind_score > ablation_score:
                        live_output = inducer.execute(frozen, request.task.live_input)
                        action.update({
                            "mechanism": "DERIVED_OPERATOR_SCHEMA",
                            "schema": asdict(frozen),
                            "generated_candidates": generated,
                            "train_exact": best.exact,
                            "blind_exact": blind_score,
                            "ablation_old_substrate": ablation_score,
                            "restore_exact": restore_score,
                            "verdict": "BOUNDED_EXECUTE",
                        })
                    else:
                        action.update({"mechanism": "DERIVED_OPERATOR_SCHEMA", "verdict": "WITHHOLD_VALIDATION"})
                else:
                    action.update({"mechanism": "DERIVED_OPERATOR_SCHEMA", "verdict": "NO_SCHEMA"})
        elif strategy == "SEEK_EVIDENCE":
            neighbors = [] if "MEMORY_READ" in ablated else self.find_concept_neighbors(request.resource_query, k=3)
            action.update({"mechanism": "MEMORY_RETRIEVAL", "neighbors": neighbors, "verdict": "EVIDENCE_REQUESTED"})
        else:
            action.update({"mechanism": None, "verdict": "WITHHOLD"})

        trace.append({
            "stage": "EXECUTION",
            "action": action,
            "live_output": live_output,
            "mechanism_digest": mechanism_digest,
            "ablated": "MECHANISM" in ablated,
        })

        output_correct = live_output == request.task.expected_live
        validation_ok = blind_score == 1.0 and restore_score == 1.0 and blind_score > ablation_score

        # LEARNING -> outcome back into MEMORY. Removing this stage leaves a
        # one-pass executor, so the closed-loop criterion fails even if output was computed.
        memory_id = None
        if "LEARNING" not in ablated and output_correct and validation_ok:
            memory_id = self.remember(
                cycle_id,
                "DEVELOPMENT_OUTCOME",
                {
                    "task": request.task.name,
                    "strategy": strategy,
                    "source": request.resource_id,
                    "source_status": source_status,
                    "admission": admission,
                    "mechanism_digest": mechanism_digest,
                    "blind_score": blind_score,
                    "ablation_score": ablation_score,
                    "restore_score": restore_score,
                    "live_output": live_output,
                },
            )
        mem_after = self.memory_count()
        learning_closed = memory_id is not None and mem_after == mem_before + 1
        trace.append({
            "stage": "LEARNING_MEMORY",
            "memory_id": memory_id,
            "memory_count_before": mem_before,
            "memory_count_after": mem_after,
            "closed_loop": learning_closed,
            "ablated": "LEARNING" in ablated,
        })

        cycle_success = bool(
            source is not None
            and plan_valid
            and admission == "ALLOW"
            and strategy == "EXPAND_REPRESENTATION"
            and output_correct
            and validation_ok
            and learning_closed
        )
        result = {
            "profile": self.PROFILE,
            "cycle_id": cycle_id,
            "cycle_success": cycle_success,
            "source_status": source_status,
            "plan_valid": plan_valid,
            "admission": admission,
            "strategy": strategy,
            "expressiveness_gap": expressiveness_gap,
            "old_substrate_train_exact": float(old_train["train_exact"]),
            "blind_score": blind_score,
            "ablation_score": ablation_score,
            "restore_score": restore_score,
            "live_output": live_output,
            "expected_live": request.task.expected_live,
            "output_correct": output_correct,
            "learning_closed": learning_closed,
            "mechanism_digest": mechanism_digest,
            "ablated_components": sorted(ablated),
            "canonical_durable_mutation": False,
        }
        self._record_cycle(cycle_id, request, result, trace)
        result["trace"] = trace
        return result

    def unified_snapshot(self) -> Dict[str, Any]:
        with self.db_lock:
            model_count = self.conn.execute("SELECT COUNT(*) FROM unified_models").fetchone()[0]
            cycles = self.conn.execute("SELECT COUNT(*) FROM unified_cycles").fetchone()[0]
            successes = self.conn.execute("SELECT COUNT(*) FROM unified_cycles WHERE success=1").fetchone()[0]
        return {
            "profile": self.PROFILE,
            "active_runtime_lineages": 1,
            "active_lineage": "YADO_V2_4_AUDITED -> YADO_V2_5_UNIFIED_SHADOW",
            "legacy_nova_core_active": False,
            "legacy_noesis_authority_active": False,
            "registered_models": int(model_count),
            "memory_events": self.memory_count(),
            "cycles": int(cycles),
            "successful_cycles": int(successes),
            "causal_loop": [
                "MEMORY",
                "THINKING",
                "LOGIC",
                "INTELLIGENCE",
                "MECHANISM_EXECUTION",
                "LEARNING",
                "MEMORY",
            ],
            "canonical_durable_mutation": False,
        }


__all__ = ["CycleRequest", "CycleTask", "UnifiedYADOKernelV25"]
