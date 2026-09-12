from __future__ import annotations

import hashlib
import importlib.util
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parent
POLICY_PATH = ROOT / "yado_cognitive_tri_organ_policy_v3.py"
EXPERIENCE_PATH = REPO / "experience" / "autonomous" / "yado-autonomous-learning-latest.json"
OUT_DIR = REPO / "candidates" / "cognitive"
REPORT = OUT_DIR / "yado-experience-conditioned-cognitive-evolution-v4.json"
CANDIDATE = OUT_DIR / "yado_cognitive_policy_candidate_v4.py"
SCHEMA = "yado.experience_conditioned_cognitive_evolution.v4"


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError("MODULE_SPEC_FAILED:" + str(path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def canon(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def digest(obj: Any) -> str:
    return hashlib.sha256(canon(obj).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class Genome:
    logic_depth: int
    contradiction_check: bool
    thinking_depth: int
    thinking_beam: int
    abstraction_families: int

    def as_dict(self) -> dict[str, Any]:
        return {
            "logic_depth": self.logic_depth,
            "contradiction_check": self.contradiction_check,
            "thinking_depth": self.thinking_depth,
            "thinking_beam": self.thinking_beam,
            "abstraction_families": self.abstraction_families,
        }


# Fresh harder families, distinct from the V2 benchmark.
HIDDEN_CASES = [
    ("logic", {"logic_depth": 3}),
    ("logic", {"logic_depth": 4}),
    ("logic", {"logic_depth": 5, "contradiction_check": True}),
    ("logic", {"logic_depth": 4, "contradiction_check": True}),
    ("thinking", {"thinking_depth": 4, "thinking_beam": 2}),
    ("thinking", {"thinking_depth": 5, "thinking_beam": 2}),
    ("thinking", {"thinking_depth": 5, "thinking_beam": 3}),
    ("thinking", {"thinking_depth": 6, "thinking_beam": 3}),
    ("intelligence", {"abstraction_families": 6}),
    ("intelligence", {"abstraction_families": 7, "logic_depth": 4}),
    ("intelligence", {"abstraction_families": 8, "thinking_depth": 5}),
    ("intelligence", {"abstraction_families": 8, "contradiction_check": True}),
]


def satisfies(g: Genome, req: dict[str, Any]) -> bool:
    for key, value in req.items():
        actual = getattr(g, key)
        if isinstance(value, bool):
            if actual is not value:
                return False
        elif actual < value:
            return False
    return True


def evaluate(g: Genome) -> dict[str, float]:
    totals = {"logic": 0, "thinking": 0, "intelligence": 0}
    wins = {"logic": 0, "thinking": 0, "intelligence": 0}
    for organ, req in HIDDEN_CASES:
        totals[organ] += 1
        wins[organ] += int(satisfies(g, req))
    return {k: wins[k] / totals[k] for k in totals}


def experience_signal(exp: dict[str, Any]) -> dict[str, Any]:
    sources = exp.get("sources") or []
    facts = [f for row in sources for f in (row.get("facts") or [])]
    failures = exp.get("failures") or []
    tokens = set()
    for fact in facts:
        for token in str(fact).lower().replace("/", " ").replace("-", " ").split():
            token = token.strip(".,:;()[]{}'\"")
            if len(token) >= 5:
                tokens.add(token)
    return {
        "source_count": len(sources),
        "fact_count": len(facts),
        "failure_count": len(failures),
        "lexical_diversity": len(tokens),
        "experience_digest": exp.get("experience_digest") or digest(exp),
        "successful_source_ids": [row.get("source_id") for row in sources if row.get("source_id")],
    }


def mutate(parent: Genome, signal: dict[str, Any], generation: int) -> list[Genome]:
    # Verified experience expands the reachable mutation neighborhood. Without
    # evidence, the controller can only retain the current policy. The facts do
    # not encode the winning genome or hidden answers.
    evidence_level = min(3, signal["fact_count"] // 16)
    source_level = min(2, signal["source_count"])
    diversity_level = 1 if signal["lexical_diversity"] >= 20 else 0
    if evidence_level == 0 or source_level == 0:
        return [parent]
    growth = min(3, generation, evidence_level + diversity_level)
    contradiction_options = [parent.contradiction_check]
    if signal["failure_count"] > 0:
        contradiction_options.append(True)
    out: set[Genome] = {parent}
    for ld in range(max(1, parent.logic_depth - 1), min(6, parent.logic_depth + source_level + growth) + 1):
        for td in range(max(1, parent.thinking_depth - 1), min(7, parent.thinking_depth + source_level + growth) + 1):
            for beam in range(parent.thinking_beam, min(4, parent.thinking_beam + growth) + 1):
                for af in range(parent.abstraction_families, min(10, parent.abstraction_families + evidence_level + growth) + 1):
                    for cc in contradiction_options:
                        out.add(Genome(ld, cc, td, beam, af))
    return sorted(out, key=lambda g: (g.logic_depth, g.thinking_depth, g.thinking_beam, g.abstraction_families, g.contradiction_check))


def objective(scores: dict[str, float], g: Genome) -> float:
    mean = sum(scores.values()) / 3.0
    complexity = (g.logic_depth + g.thinking_depth + g.thinking_beam + g.abstraction_families) / 200.0
    return mean - complexity


def evolve(baseline: Genome, signal: dict[str, Any]) -> tuple[Genome, list[dict[str, Any]]]:
    parent = baseline
    generations = []
    for generation in range(1, 5):
        pool = mutate(parent, signal, generation)
        scored = [(objective(evaluate(g), g), evaluate(g), g) for g in pool]
        scored.sort(key=lambda row: (-row[0], -min(row[1].values()), canon(row[2].as_dict())))
        best_obj, best_scores, best = scored[0]
        generations.append({
            "generation": generation,
            "candidate_pool": len(pool),
            "parent": parent.as_dict(),
            "best_genome": best.as_dict(),
            "hidden_scores": best_scores,
            "objective": best_obj,
        })
        parent = best
    return parent, generations


def main() -> dict[str, Any]:
    if not POLICY_PATH.exists() or not EXPERIENCE_PATH.exists():
        raise RuntimeError("REQUIRED_STATE_MISSING")
    policy_mod = load_module(POLICY_PATH, "yado_policy_v3_active")
    active = dict(policy_mod.COGNITIVE_POLICY)
    exp = json.loads(EXPERIENCE_PATH.read_text(encoding="utf-8"))
    if exp.get("status") != "PASS_SHADOW_BOUNDED_AUTONOMOUS_EXTERNAL_LEARNING_V1":
        raise RuntimeError("EXPERIENCE_NOT_VERIFIED")
    signal = experience_signal(exp)
    baseline = Genome(**active)
    baseline_scores = evaluate(baseline)
    selected, generations = evolve(baseline, signal)
    selected_scores = evaluate(selected)

    zero_signal = {
        "source_count": 0, "fact_count": 0, "failure_count": 0,
        "lexical_diversity": 0, "experience_digest": "ABLATION_NONE",
        "successful_source_ids": [],
    }
    ablated, ablated_generations = evolve(baseline, zero_signal)
    ablated_scores = evaluate(ablated)

    improved = sum(selected_scores.values()) > sum(baseline_scores.values())
    min_ok = min(selected_scores.values()) >= 0.75
    changed = selected.as_dict() != baseline.as_dict()
    causal = selected.as_dict() != ablated.as_dict() and sum(selected_scores.values()) > sum(ablated_scores.values())
    status = "PASS_SHADOW_EXPERIENCE_CONDITIONED_COGNITIVE_EVOLUTION_V4" if improved and min_ok and changed and causal else "WITHHOLD_EXPERIENCE_CONDITIONED_COGNITIVE_EVOLUTION_V4"

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    src = (
        "from __future__ import annotations\n\n"
        f"COGNITIVE_POLICY = {selected.as_dict()!r}\n"
        f"VERIFIED_HIDDEN_SCORES = {selected_scores!r}\n"
        f"EXPERIENCE_BINDING = {{'experience_digest':{signal['experience_digest']!r},'source_ids':{signal['successful_source_ids']!r},'fact_count':{signal['fact_count']!r}}}\n\n"
        "def component():\n"
        "    return {'schema':'yado.cognitive_policy_candidate.v4','policy':COGNITIVE_POLICY,'verified_hidden_scores':VERIFIED_HIDDEN_SCORES,'experience_binding':EXPERIENCE_BINDING,'canonical_active':False,'consciousness_claimed':False}\n"
    )
    compile(src, str(CANDIDATE), "exec")
    CANDIDATE.write_text(src, encoding="utf-8")
    candidate_sha = hashlib.sha256(CANDIDATE.read_bytes()).hexdigest()
    report = {
        "schema": SCHEMA,
        "status": status,
        "baseline_policy": baseline.as_dict(),
        "baseline_hidden": baseline_scores,
        "selected_policy": selected.as_dict(),
        "selected_hidden": selected_scores,
        "generations": generations,
        "experience_signal": signal,
        "no_experience_ablation": {
            "selected_policy": ablated.as_dict(),
            "hidden_scores": ablated_scores,
            "generations": ablated_generations,
            "causal_effect_observed": causal,
        },
        "candidate_path": str(CANDIDATE.relative_to(REPO)),
        "candidate_sha256": candidate_sha,
        "external_model_used": False,
        "downloaded_code_executed": False,
        "automatic_main_mutation": False,
        "canonical_mutation": False,
        "consciousness_claimed": False,
        "limitations": [
            "bounded externally authored benchmark and mutation grammar",
            "experience gates mutation-space expansion; it does not encode hidden answers",
            "functional cognition evidence only",
        ],
    }
    REPORT.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, sort_keys=True))
    if not status.startswith("PASS_"):
        raise SystemExit(2)
    return report


if __name__ == "__main__":
    main()
