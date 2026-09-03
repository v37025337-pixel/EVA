from __future__ import annotations

from typing import Any, Dict, Mapping

from yado_core_v2_6_cross_domain import UnifiedYADOKernelV26CrossDomain
from yado_semantic_selective_v27 import SelectiveConfig, SelectiveEvidenceRouter


class UnifiedYADOKernelV27Selective(UnifiedYADOKernelV26CrossDomain):
    SCHEMA_VERSION = 9
    PROFILE = "YADO_V2_7_SELECTIVE_EVIDENCE_SHADOW"

    def _execute_semantic(self, payload: Mapping[str, Any], ablated: bool) -> Dict[str, Any]:
        extra_docs = list(payload["extra_docs"])
        deep_evidence = dict(payload.get("deep_evidence", {}))
        cases = [(str(q), str(e)) for q, e in payload["blind_cases"]]
        live_query = str(payload["live_query"])
        expected_live = str(payload["expected_live"])

        router = SelectiveEvidenceRouter(extra_docs, deep_evidence, SelectiveConfig())
        baseline_hit = 0
        baseline_rr = 0.0
        baseline_details = []
        for q, e in cases:
            rows = router.token_only_rows(q)
            ids = [r for _, r in rows]
            rank = ids.index(e) + 1
            baseline_hit += int(rank == 1)
            baseline_rr += 1.0 / rank
            baseline_details.append({"query": q, "expected": e, "rank": rank, "top3": [{"repo": r, "score": float(s)} for s, r in rows[:3]]})
        n = max(1, len(cases))
        baseline = baseline_hit / n

        if ablated:
            live_rows = router.token_only_rows(live_query)
            live_output = live_rows[0][1] if live_rows else None
            return {
                "mechanism": "TOKEN_ONLY",
                "baseline": float(baseline),
                "candidate": float(baseline),
                "ablation": float(baseline),
                "restore": float(baseline),
                "live_output": live_output,
                "expected_live": expected_live,
                "output_correct": live_output == expected_live,
                "details": {"baseline_mrr": baseline_rr / n, "baseline_cases": baseline_details},
            }

        candidate = router.evaluate(cases)
        live = router.decide(live_query)
        restore = router.evaluate(cases)
        return {
            "mechanism": "SELECTIVE_SEMANTIC_GENERIC_DEEP_ROUTER",
            "baseline": float(baseline),
            "candidate": float(candidate["top1"]),
            "ablation": float(baseline),
            "restore": float(restore["top1"]),
            "live_output": live["winner"],
            "expected_live": expected_live,
            "output_correct": live["winner"] == expected_live,
            "details": {
                "candidate_mrr": candidate["mrr"],
                "baseline_mrr": baseline_rr / n,
                "actions": candidate["actions"],
                "candidate_cases": candidate["details"],
                "live_action": live["action"],
                "live_features": live["features"],
                "live_deep_pool_size": len(live.get("deep_pool", [])),
                "live_deep_top": live.get("deep_top", []),
                "selective_config": SelectiveConfig().__dict__,
                "config_digest": SelectiveConfig().digest,
                "host_task_specific_repo_rule_supplied": False,
                "deep_evidence_host_mediated": True,
            },
        }


__all__ = ["UnifiedYADOKernelV27Selective"]
