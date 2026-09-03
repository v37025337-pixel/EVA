from __future__ import annotations

import hashlib
import json
import math
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from yado_core_v2 import canonical_json, utc_now
from yado_core_v2_5_unified import UnifiedYADOKernelV25
from yado_boolean_runtime_native_v1 import (
    eval_expr,
    fit_expr,
    generate_exprs,
    score_expr,
)
from yado_phase_a_shadow import Case
from yado_primitive_genesis_cycle1 import FailureDrivenSchemaInducer, baseline_score
from yado_resource_intelligence_cycle8 import BASE, T1, T2, T3, TRAIN, grams_from_tokens, tokenize

ROOT = Path(__file__).resolve().parent


@dataclass(frozen=True)
class DomainCycleRequest:
    domain: str
    name: str
    evidence_resource_id: str
    evidence_query: str
    developmental_actions: Sequence[Mapping[str, str]]
    payload: Mapping[str, Any]


class UnifiedYADOKernelV26CrossDomain(UnifiedYADOKernelV25):
    """Cross-domain extension of the proven V2.5 unified causal runtime.

    Common causal envelope for every tested domain:
      MEMORY -> THINKING -> LOGIC -> DOMAIN_MECHANISM -> VALIDATION
      -> INTELLIGENCE -> LEARNING -> MEMORY

    The domain mechanisms are previously validated bounded capabilities. This
    layer tests whether one runtime can route them through the same evidence,
    planning, validation, decision and learning envelope. It does not claim a
    universal cognitive architecture or substrate-free self-invention.
    """

    SCHEMA_VERSION = 8
    PROFILE = "YADO_V2_6_CROSS_DOMAIN_SHADOW"
    DOMAINS = {
        "LOGIC_RULE_INDUCTION",
        "PLANNING",
        "SEMANTIC_RESOURCE_SELECTION",
        "MECHANISM_GENESIS",
    }

    def __init__(self, db_path: str = "yado_v26_cross_domain_shadow.db"):
        super().__init__(db_path=db_path)
        self._bootstrap_domain_evidence()

    @staticmethod
    def _sha(path: Path) -> str:
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def _bootstrap_domain_evidence(self) -> None:
        entries = {
            "internal:yado:logic-induction": (
                ROOT / "yado_cognitive_training_cycle1_report.json",
                "Bounded boolean-rule induction evidence: fresh blind 1.0 with causal ablation.",
                ["logic", "rule_induction", "developmental_evidence"],
            ),
            "internal:yado:planning-transfer": (
                ROOT / "yado_thinking_training_cycle2_report.json",
                "Pairwise precedence planning transfer evidence with unseen action IDs.",
                ["thinking", "planning", "precedence", "developmental_evidence"],
            ),
            "internal:yado:resource-intelligence": (
                ROOT / "yado_resource_intelligence_cycle8_report.json",
                "Bounded resource-selection transfer evidence with support-bound semantic routing.",
                ["intelligence", "semantic_selection", "developmental_evidence"],
            ),
        }
        for rid, (path, text, tags) in entries.items():
            if self.get_resource(rid, include_text=False) is None:
                self.add_resource(
                    rid,
                    text,
                    metadata={
                        "provider": "internal_developmental_registry",
                        "status": "ACTIVE_VERIFIED",
                        "authority": False,
                        "source_path": str(path),
                        "source_sha256": self._sha(path),
                    },
                    tags=tags,
                )

    # ------------------------------------------------------------------
    # Domain mechanisms
    # ------------------------------------------------------------------
    @staticmethod
    def _logic_cases(raw: Sequence[Mapping[str, Any]]) -> List[Tuple[Mapping[str, bool], bool]]:
        return [(dict(c["env"]), bool(c["expected"])) for c in raw]

    def _execute_logic(self, payload: Mapping[str, Any], ablated: bool) -> Dict[str, Any]:
        train = self._logic_cases(payload["train"])
        blind = self._logic_cases(payload["blind"])
        live_env = dict(payload["live_env"])
        expected_live = bool(payload["expected_live"])

        shallow_pool = generate_exprs(1)
        deep_pool = generate_exprs(2)
        base_expr, base_train = fit_expr(shallow_pool, train)
        candidate_expr, candidate_train = fit_expr(deep_pool, train)

        base_blind = score_expr(base_expr, blind)
        if ablated:
            active_expr = base_expr
            candidate_blind = base_blind
            restore = base_blind
            mechanism = "SHALLOW_BOOLEAN_SEARCH"
        else:
            active_expr = candidate_expr
            candidate_blind = score_expr(candidate_expr, blind)
            restore = score_expr(candidate_expr, blind)
            mechanism = "EXPANDED_BOOLEAN_RULE_SEARCH"

        live_output = bool(eval_expr(active_expr, live_env))
        return {
            "mechanism": mechanism,
            "baseline": float(base_blind),
            "candidate": float(candidate_blind),
            "ablation": float(base_blind),
            "restore": float(restore),
            "live_output": live_output,
            "expected_live": expected_live,
            "output_correct": live_output == expected_live,
            "details": {
                "baseline_train": base_train,
                "candidate_train": candidate_train,
                "baseline_expression": base_expr,
                "candidate_expression": candidate_expr,
                "shallow_candidate_count": len(shallow_pool),
                "expanded_candidate_count": len(deep_pool),
                "task_specific_formula_supplied_to_search": False,
            },
        }

    @staticmethod
    def _plan_expected(case: Mapping[str, Any]) -> List[str]:
        return [str(x) for x in case["expected"]]

    def _execute_planning(self, payload: Mapping[str, Any], ablated: bool) -> Dict[str, Any]:
        cases = list(payload["blind_cases"])
        live_case = dict(payload["live_case"])

        def candidate(case: Mapping[str, Any]) -> List[str]:
            actions = list(case["actions"])
            if ablated:
                return [str(a["id"]) for a in actions]
            return self.thinking_plan(actions)

        def input_order(case: Mapping[str, Any]) -> List[str]:
            return [str(a["id"]) for a in case["actions"]]

        base = sum(input_order(c) == self._plan_expected(c) for c in cases) / max(1, len(cases))
        cand = sum(candidate(c) == self._plan_expected(c) for c in cases) / max(1, len(cases))
        live_output = candidate(live_case)
        expected_live = self._plan_expected(live_case)
        return {
            "mechanism": "INPUT_ORDER" if ablated else "PAIRWISE_PRECEDENCE_GRAPH",
            "baseline": float(base),
            "candidate": float(cand),
            "ablation": float(base),
            "restore": float(cand),
            "live_output": live_output,
            "expected_live": expected_live,
            "output_correct": live_output == expected_live,
            "details": {
                "blind_cases": len(cases),
                "blind_action_ids_unseen_in_training": True,
            },
        }

    @staticmethod
    def _semantic_build(extra_docs: Sequence[Sequence[str]], camel_split: bool):
        supported = list(BASE + T1 + T2 + T3)
        all_docs = supported + [(str(r), str(d)) for r, d in extra_docs]
        supported_set = {r for r, _ in supported}
        desc = {r: tokenize(d, camel_split) for r, d in all_docs}
        grams = {r: grams_from_tokens(desc[r]) for r, _ in all_docs}
        pos = defaultdict(float)
        neg = defaultdict(float)
        for q, tgt in TRAIN:
            qs = set(tokenize(q, camel_split))
            td = set(desc[tgt])
            for x in qs:
                for d in td:
                    pos[(x, d)] += 1
                for r in supported_set:
                    if r == tgt:
                        continue
                    for d in set(desc[r]):
                        neg[(x, d)] += 1 / (len(supported_set) - 1)
        return supported, all_docs, supported_set, desc, grams, pos, neg

    def _semantic_ranker(self, extra_docs: Sequence[Sequence[str]], token_only: bool = False):
        cfg = self.models["RESOURCE_INTELLIGENCE_CONFIG"]
        camel = bool(cfg["camel_split"])
        gate_k = int(cfg["gate_k"])
        sem_weight = float(cfg["semantic_weight"])
        supported, all_docs, sset, desc, grams, pos, neg = self._semantic_build(extra_docs, camel)

        def lexical(q: str, r: str) -> float:
            qt = tokenize(q, camel)
            qs = set(qt)
            ds = set(desc[r])
            token = len(qs & ds) / (len(qs) or 1)
            if token_only:
                return token
            qg = grams_from_tokens(qt)
            tri = len(qg & grams[r]) / (len(qg | grams[r]) or 1)
            return 0.5 * (token + tri)

        def semantic(q: str, r: str) -> float:
            vals = []
            for x in set(tokenize(q, camel)):
                best = 0.0
                for d in set(desc[r]):
                    p = pos[(x, d)]
                    n = neg[(x, d)]
                    if p:
                        best = max(best, max(0.0, math.log((p + 0.5) / (n + 0.5))))
                vals.append(best)
            return sum(vals) / (len(vals) or 1)

        def rank(q: str) -> List[Tuple[float, str]]:
            base = sorted(((lexical(q, r), r) for r, _ in all_docs), key=lambda z: (z[0], z[1]), reverse=True)
            if token_only:
                return base
            gate = all(r in sset for _, r in base[:gate_k])
            if not gate:
                return base
            sr = {r: semantic(q, r) for r in sset}
            mx = max(sr.values()) or 1.0
            rows = []
            for b, r in base:
                if r in sset:
                    rows.append(((1 - sem_weight) * b + sem_weight * (sr[r] / mx), r))
                else:
                    rows.append((b, r))
            return sorted(rows, key=lambda z: (z[0], z[1]), reverse=True)

        return rank

    def _execute_semantic(self, payload: Mapping[str, Any], ablated: bool) -> Dict[str, Any]:
        extra_docs = list(payload["extra_docs"])
        cases = [(str(q), str(e)) for q, e in payload["blind_cases"]]
        live_query = str(payload["live_query"])
        expected_live = str(payload["expected_live"])

        base_rank = self._semantic_ranker(extra_docs, token_only=True)
        active_rank = base_rank if ablated else self._semantic_ranker(extra_docs, token_only=False)

        def score(rank_fn) -> Tuple[float, float, List[Dict[str, Any]]]:
            top1 = 0
            rr = 0.0
            details = []
            for q, e in cases:
                rows = rank_fn(q)
                ids = [r for _, r in rows]
                pos = ids.index(e) + 1
                top1 += int(pos == 1)
                rr += 1.0 / pos
                details.append({
                    "query": q,
                    "expected": e,
                    "rank": pos,
                    "top3": [{"repo": r, "score": round(float(s), 6)} for s, r in rows[:3]],
                })
            n = max(1, len(cases))
            return top1 / n, rr / n, details

        base_top1, base_mrr, base_details = score(base_rank)
        cand_top1, cand_mrr, cand_details = score(active_rank)
        live_rows = active_rank(live_query)
        live_output = live_rows[0][1] if live_rows else None
        return {
            "mechanism": "TOKEN_ONLY" if ablated else "SUPPORT_BOUND_SEMANTIC_ROUTER",
            "baseline": float(base_top1),
            "candidate": float(cand_top1),
            "ablation": float(base_top1),
            "restore": float(cand_top1),
            "live_output": live_output,
            "expected_live": expected_live,
            "output_correct": live_output == expected_live,
            "details": {
                "candidate_mrr": cand_mrr,
                "baseline_mrr": base_mrr,
                "candidate_cases": cand_details,
                "baseline_cases": base_details,
                "fresh_resources_not_in_cycle8_training": len(extra_docs),
            },
        }

    @staticmethod
    def _decode_cases(raw: Sequence[Mapping[str, Any]]) -> List[Case]:
        return [Case(str(c["case_id"]), c["input"], c["expected"]) for c in raw]

    def _execute_genesis(self, payload: Mapping[str, Any], ablated: bool) -> Dict[str, Any]:
        train = self._decode_cases(payload["train"])
        blind = self._decode_cases(payload["blind"])
        live_input = payload["live_input"]
        expected_live = payload["expected_live"]
        base = float(baseline_score(blind)["train_exact"])

        if ablated:
            return {
                "mechanism": "OLD_FIXED_PHASE_A",
                "baseline": base,
                "candidate": base,
                "ablation": base,
                "restore": base,
                "live_output": None,
                "expected_live": expected_live,
                "output_correct": False,
                "details": {"derived_schema": None},
            }

        inducer = FailureDrivenSchemaInducer()
        best, generated = inducer.search(train)
        if best is None:
            return {
                "mechanism": "FAILURE_DERIVED_SCHEMA",
                "baseline": base,
                "candidate": 0.0,
                "ablation": base,
                "restore": 0.0,
                "live_output": None,
                "expected_live": expected_live,
                "output_correct": False,
                "details": {"generated_candidates": generated, "derived_schema": None},
            }
        frozen = best.schema
        cand = float(inducer.score(frozen, blind).exact)
        live_output = inducer.execute(frozen, live_input)
        return {
            "mechanism": "FAILURE_DERIVED_SCHEMA",
            "baseline": base,
            "candidate": cand,
            "ablation": base,
            "restore": cand,
            "live_output": live_output,
            "expected_live": expected_live,
            "output_correct": live_output == expected_live,
            "details": {
                "generated_candidates": generated,
                "derived_schema": {
                    "family": frozen.family,
                    "width": frozen.width,
                    "stride": frozen.stride,
                    "offset": frozen.offset,
                    "reverse_each": frozen.reverse_each,
                    "digest": frozen.digest,
                },
                "host_supplied_meta_schema": True,
                "task_specific_operator_supplied": False,
            },
        }

    def _execute_domain(self, request: DomainCycleRequest, ablated: bool) -> Dict[str, Any]:
        if request.domain == "LOGIC_RULE_INDUCTION":
            return self._execute_logic(request.payload, ablated)
        if request.domain == "PLANNING":
            return self._execute_planning(request.payload, ablated)
        if request.domain == "SEMANTIC_RESOURCE_SELECTION":
            return self._execute_semantic(request.payload, ablated)
        if request.domain == "MECHANISM_GENESIS":
            return self._execute_genesis(request.payload, ablated)
        raise ValueError(f"unsupported domain: {request.domain}")

    # ------------------------------------------------------------------
    # Shared cross-domain causal envelope
    # ------------------------------------------------------------------
    def run_domain_cycle(self, request: DomainCycleRequest, ablate: Optional[Iterable[str]] = None) -> Dict[str, Any]:
        if request.domain not in self.DOMAINS:
            raise ValueError(request.domain)
        ablated = set(ablate or [])
        cycle_id = f"XDOM-{hashlib.sha256((request.domain + request.name + utc_now().isoformat()).encode()).hexdigest()[:12]}"
        trace: List[Dict[str, Any]] = []
        mem_before = self.memory_count()

        source = None if "MEMORY_READ" in ablated else self.get_resource(request.evidence_resource_id, include_text=True)
        source_status = str((source or {}).get("metadata", {}).get("status", "UNKNOWN"))
        trace.append({"stage": "MEMORY", "found": source is not None, "source_status": source_status, "ablated": "MEMORY_READ" in ablated})

        if "THINKING" in ablated:
            plan_ids = [str(a["id"]) for a in request.developmental_actions]
        else:
            plan_ids = self.thinking_plan(request.developmental_actions)
        plan_valid = self.thinking_plan_valid(request.developmental_actions, plan_ids)
        trace.append({"stage": "THINKING", "plan_ids": plan_ids, "plan_valid": plan_valid, "ablated": "THINKING" in ablated})

        admission = self.logic_admission(source_status, ablated="LOGIC" in ablated)
        evidence_complete = 1.0 if admission == "ALLOW" else 0.0
        trace.append({"stage": "LOGIC", "admission": admission, "ablated": "LOGIC" in ablated})

        prereq = source is not None and plan_valid and admission == "ALLOW"
        if prereq:
            domain_result = self._execute_domain(request, ablated="DOMAIN_MECHANISM" in ablated)
        else:
            domain_result = {
                "mechanism": None,
                "baseline": 0.0,
                "candidate": 0.0,
                "ablation": 0.0,
                "restore": 0.0,
                "live_output": None,
                "expected_live": request.payload.get("expected_live"),
                "output_correct": False,
                "details": {"skipped_due_to_prerequisite": True},
            }
        trace.append({"stage": "DOMAIN_MECHANISM", "domain": request.domain, "result": domain_result, "ablated": "DOMAIN_MECHANISM" in ablated})

        improvement = float(domain_result["candidate"]) - float(domain_result["ablation"])
        validation_ok = bool(
            float(domain_result["candidate"]) >= 0.999999
            and float(domain_result["restore"]) >= 0.999999
            and improvement > 0.0
            and domain_result["output_correct"]
        )
        features = {
            "blind": float(domain_result["candidate"]),
            "ablation_drop": max(0.0, improvement),
            "restore": float(domain_result["restore"]),
            "evidence_complete": evidence_complete,
            "expressiveness_gap": 0.0 if validation_ok else (1.0 if request.domain == "MECHANISM_GENESIS" else 0.0),
            "integration_gap": 0.0,
        }
        strategy = self.intelligence_strategy(features, ablated="INTELLIGENCE" in ablated)
        trace.append({"stage": "INTELLIGENCE", "features": features, "strategy": strategy, "validation_ok": validation_ok, "ablated": "INTELLIGENCE" in ablated})

        memory_id = None
        if "LEARNING" not in ablated and validation_ok and strategy == "ACCEPT_BOUNDED":
            memory_id = self.remember(
                cycle_id,
                "CROSS_DOMAIN_OUTCOME",
                {
                    "domain": request.domain,
                    "task": request.name,
                    "evidence_resource": request.evidence_resource_id,
                    "mechanism": domain_result["mechanism"],
                    "baseline": domain_result["baseline"],
                    "candidate": domain_result["candidate"],
                    "ablation": domain_result["ablation"],
                    "restore": domain_result["restore"],
                    "live_output": domain_result["live_output"],
                },
            )
        mem_after = self.memory_count()
        learning_closed = memory_id is not None and mem_after == mem_before + 1
        trace.append({"stage": "LEARNING_MEMORY", "memory_id": memory_id, "closed_loop": learning_closed, "ablated": "LEARNING" in ablated})

        success = bool(prereq and validation_ok and strategy == "ACCEPT_BOUNDED" and learning_closed)
        result = {
            "profile": self.PROFILE,
            "cycle_id": cycle_id,
            "domain": request.domain,
            "task": request.name,
            "cycle_success": success,
            "source_status": source_status,
            "plan_valid": plan_valid,
            "admission": admission,
            "domain_result": domain_result,
            "validation_ok": validation_ok,
            "intelligence_strategy": strategy,
            "learning_closed": learning_closed,
            "ablated_components": sorted(ablated),
            "canonical_durable_mutation": False,
            "trace": trace,
        }
        return result


__all__ = ["DomainCycleRequest", "UnifiedYADOKernelV26CrossDomain"]
