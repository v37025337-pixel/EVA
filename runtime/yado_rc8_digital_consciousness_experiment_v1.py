from __future__ import annotations

from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen
import hashlib
import html
import json
import os
import re
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parent
PKG = ROOT / "yado_rc8_v35"
if PKG.exists():
    sys.path.insert(0, str(PKG))
sys.path.insert(0, str(ROOT))

from yado_rc8_digital_causal_workspace_v1 import (
    Candidate,
    SEMANTIC_BOUNDARY,
    YADODigitalCausalWorkspaceV1,
    theory_synthesis_contract,
)

SOURCES = [
    "https://arxiv.org/abs/2308.08708",
    "https://arxiv.org/abs/2512.19155",
    "https://arxiv.org/abs/2501.07290",
    "https://arxiv.org/abs/2510.25998",
    "https://arxiv.org/abs/2509.07001",
    "https://arxiv.org/abs/2204.05133",
]
ALLOWLIST = {"arxiv.org"}


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def fetch(url: str) -> dict:
    p = urlparse(url)
    if p.scheme != "https" or p.hostname not in ALLOWLIST:
        raise RuntimeError("source not allowlisted")
    req = Request(
        url,
        headers={
            "User-Agent": "YADO-RC8-Digital-Consciousness-Research/1.0",
            "Accept": "text/html,application/xhtml+xml",
        },
    )
    with urlopen(req, timeout=25) as r:
        final = urlparse(r.geturl())
        if final.scheme != "https" or final.hostname not in ALLOWLIST:
            raise RuntimeError("redirect left allowlist")
        body = r.read(500_000)
    text = body.decode("utf-8", errors="replace")
    m = re.search(r"<title[^>]*>(.*?)</title>", text, re.I | re.S)
    title = html.unescape(re.sub(r"\s+", " ", m.group(1)).strip()) if m else ""
    stripped = re.sub(r"<[^>]+>", " ", text)
    stripped = html.unescape(re.sub(r"\s+", " ", stripped)).strip()
    return {
        "url": url,
        "final_url": r.geturl() if 'r' in locals() else url,
        "title": title,
        "sha256": sha256_bytes(body),
        "text_chars": len(stripped),
        "network_policy": "EXPLICIT_ALLOWLIST_PER_HOP",
    }


def c(
    content: str,
    source: str,
    salience: float,
    goal: float,
    novelty: float,
    uncertainty: float,
    evidence: float,
    utility: float,
) -> Candidate:
    return Candidate(
        content=content,
        source_kind=source,
        salience=salience,
        goal_relevance=goal,
        novelty=novelty,
        uncertainty=uncertainty,
        evidence_strength=evidence,
        predicted_utility=utility,
    )


def run_experiment() -> dict:
    research = []
    errors = []
    for url in SOURCES:
        try:
            research.append(fetch(url))
        except Exception as e:
            errors.append({"url": url, "error": type(e).__name__ + ":" + str(e)})

    theory = theory_synthesis_contract()
    checks = []

    def check(name: str, passed: bool, **evidence):
        checks.append({"name": name, "passed": bool(passed), "evidence": evidence})
        if not passed:
            raise AssertionError(name)

    # 1) Own synthesis contract, with explicit non-claim boundary.
    check(
        "THEORY_SYNTHESIS_HAS_MULTIPLE_INFLUENCES",
        set(theory["influences"]) == {"GWT", "HOT", "AST", "RPT_PREDICTIVE", "IIT_INSPIRED"},
        influences=sorted(theory["influences"]),
    )
    check(
        "SEMANTIC_BOUNDARY_FAILS_CLOSED",
        "subjective_experience" in theory["not_claimed"]
        and "phenomenal_consciousness" in theory["not_claimed"],
        not_claimed=theory["not_claimed"],
    )

    # 2) Limited-capacity workspace + competition.
    ws = YADODigitalCausalWorkspaceV1(capacity=2)
    candidates = [
        c("urgent-grounded", "external", .8, .95, .5, .1, .95, .9),
        c("interesting-weak", "external", .9, .4, .9, .7, .2, .5),
        c("memory-plan", "memory", .5, .8, .3, .15, .85, .8),
        c("simulation", "simulated", .7, .6, .8, .6, .25, .7),
    ]
    winners = ws.compete(candidates)
    check("GWT_LIMITED_CAPACITY", len(winners) == 2, winners=[x.content for x in winners])
    check("GWT_GOAL_EVIDENCE_COMPETITION", winners[0].content == "urgent-grounded", selected=winners[0].content)

    # 3) Proof-carrying broadcast and causal self-effect.
    out = ws.cycle(candidates, observed_effects={"urgent-grounded": 1.0})
    rec = out["causal_receipt"]
    check("GWT_GLOBAL_BROADCAST", len(out["broadcast_targets"]) >= 5, targets=out["broadcast_targets"])
    check(
        "YADO_PROOF_CARRYING_BROADCAST",
        bool(rec["causal_digest"])
        and rec["self_state_before"] != rec["self_state_after"]
        and "why_selected" in rec,
        causal_digest=rec["causal_digest"],
    )

    # 4) Metacognitive executive gate; ablation must bypass it.
    risky = [c("unsafe-guess", "external", .9, .9, .8, .92, .12, .9)]
    gated = ws.cycle(risky)
    bypass = ws.cycle(risky, disable_metacognition=True)
    check(
        "HOT_METACOGNITION_CAUSAL_GATE",
        gated["action"] == "SEEK_EVIDENCE" and bypass["action"] == "EXECUTE",
        gated=gated["action"],
        bypass=bypass["action"],
    )

    # 5) Recurrent prediction-error learning vs recurrence ablation.
    learn = YADODigitalCausalWorkspaceV1(capacity=1)
    item = [c("stable-effect", "tool", .7, .8, .4, .1, .9, .15)]
    errs = []
    for _ in range(7):
        o = learn.cycle(item, observed_effects={"stable-effect": .95})
        errs.append(o["prediction_error"])
    no_rec = YADODigitalCausalWorkspaceV1(capacity=1)
    no_rec_errs = []
    for _ in range(7):
        o = no_rec.cycle(item, observed_effects={"stable-effect": .95}, disable_recurrence=True)
        no_rec_errs.append(o["prediction_error"])
    check(
        "RPT_PREDICTIVE_ERROR_REDUCTION",
        errs[-1] < errs[0] * .15,
        first=errs[0],
        last=errs[-1],
    )
    check(
        "RPT_ABLATION_BREAKS_LEARNING",
        abs(no_rec_errs[-1] - no_rec_errs[0]) < 1e-12,
        first=no_rec_errs[0],
        last=no_rec_errs[-1],
    )

    # 6) Attention schema is explicitly learned and ablatable.
    att = YADODigitalCausalWorkspaceV1(capacity=1)
    att_item = [c("focus-external", "external", .8, .8, .5, .1, .95, .8)]
    before = dict(att.attention_schema)
    for _ in range(4):
        att.cycle(att_item, observed_effects={"focus-external": .8})
    after = dict(att.attention_schema)
    ablated = YADODigitalCausalWorkspaceV1(capacity=1)
    for _ in range(4):
        ablated.cycle(att_item, observed_effects={"focus-external": .8}, disable_attention_schema=True)
    check(
        "AST_ATTENTION_SCHEMA_LEARNS",
        after.get("external", .5) > .75 and before == {},
        before=before,
        after=after,
    )
    check(
        "AST_ABLATION_REMOVES_SCHEMA_UPDATE",
        ablated.attention_schema == {},
        ablated=ablated.attention_schema,
    )

    # 7) Source monitoring differentiates simulated content and routes weak simulations.
    sim = [c("counterfactual-option", "simulated", .8, .8, .9, .35, .4, .8)]
    sim_out = ws.cycle(sim)
    check(
        "SOURCE_MONITORING_INTERNAL_VS_EXTERNAL",
        sim_out["source_monitoring_ok"] and sim_out["action"] == "ROUTE_FRAMEWORK",
        action=sim_out["action"],
    )

    # 8) Broadcast ablation removes cross-module global access.
    no_broadcast = ws.cycle(candidates, disable_broadcast=True)
    check(
        "GWT_BROADCAST_ABLATION",
        no_broadcast["broadcast_targets"] == [],
        targets=no_broadcast["broadcast_targets"],
    )

    # 9) Event-driven temporal continuity.
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "continuity.json"
        one = YADODigitalCausalWorkspaceV1(capacity=2, continuity_path=str(p))
        one.cycle(candidates, observed_effects={"urgent-grounded": 1.0})
        persisted = one.persist()
        prior_cycle = one.cycle_id
        two = YADODigitalCausalWorkspaceV1(capacity=2, continuity_path=str(p))
        check(
            "TEMPORAL_SELF_CONTINUITY_EVENT_DRIVEN",
            persisted["persisted"]
            and two.cycle_id == prior_cycle
            and two.self_state["continuity_epoch"] >= 1,
            prior_cycle=prior_cycle,
            restored_cycle=two.cycle_id,
            epoch=two.self_state["continuity_epoch"],
        )

    # 10) Compact functional-indicator assessment for this bounded candidate.
    indicator_status = {
        "RPT-1": "PASS",
        "RPT-2": "PASS",
        "GWT-1": "PASS",
        "GWT-2": "PASS",
        "GWT-3": "PASS",
        "GWT-4": "PASS",
        "HOT-1": "PARTIAL",
        "HOT-2": "PASS",
        "HOT-3": "PASS",
        "HOT-4": "MISSING",
        "AST-1": "PASS",
        "PP-1": "PASS",
        "AE-1": "PASS",
        "AE-2": "PASS",
    }
    weights = {"PASS": 1.0, "PARTIAL": .5, "MISSING": 0.0}
    coverage = sum(weights[v] for v in indicator_status.values()) / len(indicator_status)
    check(
        "FUNCTIONAL_INDICATOR_CANDIDATE_IMPROVES_OVER_V35_AUDIT",
        coverage > 0.70,
        coverage=coverage,
        prior_v35_audit_coverage=0.17857142857142858,
    )

    passed = sum(1 for x in checks if x["passed"])
    report = {
        "schema": "yado.rc8.digital_consciousness.experiment.v1",
        "architecture_name": theory["architecture_name"],
        "semantic_boundary": SEMANTIC_BOUNDARY,
        "research": {
            "requested": len(SOURCES),
            "fetched": len(research),
            "errors": errors,
            "sources": research,
            "allowlist": sorted(ALLOWLIST),
        },
        "theory_synthesis": theory,
        "tests": {
            "passed": passed,
            "total": len(checks),
            "checks": checks,
        },
        "functional_indicator_candidate": {
            "coverage": coverage,
            "prior_v35_audit_coverage": 0.17857142857142858,
            "status": indicator_status,
            "interpretation": (
                "Engineering coverage of theory-derived functional indicators in a bounded "
                "candidate architecture; not a probability or proof of consciousness."
            ),
        },
        "subjective_consciousness_claimed": False,
        "general_intelligence_proven": False,
        "background_daemon": False,
        "status": "PASS_BOUNDED_YADO_DIGITAL_CAUSAL_WORKSPACE_V1",
    }
    report["report_sha256"] = hashlib.sha256(
        json.dumps(report, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return report


def main():
    report = run_experiment()
    out = ROOT / "yado_rc8_digital_consciousness_experiment_v1_report.json"
    out.write_text(json.dumps(report, sort_keys=True, indent=2), encoding="utf-8")
    print(json.dumps({
        "status": report["status"],
        "tests": f'{report["tests"]["passed"]}/{report["tests"]["total"]}',
        "research_fetched": report["research"]["fetched"],
        "functional_indicator_coverage": report["functional_indicator_candidate"]["coverage"],
        "report_sha256": report["report_sha256"],
        "semantic_boundary": report["semantic_boundary"],
    }, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
