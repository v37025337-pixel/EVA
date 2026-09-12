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


# Hidden families are deliberately different from the V2 benchmark. They test
# deeper implication, contradiction handling, multi-step planning and transfer.
HIDDEN_CASES = [
    ("logic", {"logic_depth": 3}, 1.0),
    ("logic", {"logic_depth": 4}, 1.0),
    ("logic", {"logic_depth": 5, "contradiction_check": True}, 1.0),
    ("logic", {"logic_depth": 4, "contradiction_check": True}, 1.0),
    ("thinking", {"thinking_depth": 4, "thinking_beam": 2}, 1.0),
    ("thinking", {"thinking_depth": 5, "thinking_beam": 2}, 1.0),
    ("thinking", {"thinking_depth": 5, "thinking_beam": 3}, 1.0),
    ("thinking", {"thinking_depth": 6, "thinking_beam": 3}, 1.0),
    ("intelligence", {"abstraction_families": 6}, 1.0),
    ("intelligence", {"abstraction_families": 7, "logic_depth": 4}, 1.0),
    ("intelligence", {"abstraction_families": 8, "thinking_depth": 5}, 1.0),
    ("intelligence", {"abstraction_families": 8, "contradiction_check": True}, 1.0),
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
    for organ, req, _ in HIDDEN_CASES:
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
    # The environment changes mutation pressure, but does not directly specify
    # the winning genome. More verified facts permit broader abstraction search;
    # observed failures add contradiction-check candidates.
    extra_abs = min(3, signal["fact_count"] // 20)
    extra_depth = min(2, signal["source_count"])
    contradiction_options = [parent.contradiction_check]
    if signal["failure_count"] > 0:
        contradiction_options.append(True)
    out: set[Genome] = {parent}
    for ld in range(max(1, parent.logic_depth - 1), min(6, parent.logic_depth + extra_depth + generation) + 1):
        for td in range(max(1, parent.thinking_depth - 1), min(7, parent.thinking_depth + extra_depth + generation) + 1):
            for beam in range(max(1, parent.thinking_beam), min(4, parent.thinking_beam + generation) + 1):
                for af in range(max(2, parent.abstraction_families), min(10, parent.abstraction_families + extra_abs + generation) + 1):
                    for cc in contradiction_options:
                        out.add(Genome(ld, cc, td, beam, af))
    return sorted(out, key=lambda g: (g.logic_depth, g.thinking_depth, g.thinking_beam, g.abstraction_families, g.contradiction_check))


def objective(scores: dict[str, float], g: Genome) -> float:
    mean = sum(scores.values()) / 3.0
    complexity = (g.logic_depth + g.thinking_depth + g.thinking_beam + g.abstraction_families) / 200.0
    return mean - complexity


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
    selected = parent
    selected_scores = evaluate(selected)
    improved = sum(selected_scores.values()) > sum(baseline_scores.values())
    min_ok = min(selected_scores.values()) >= 0.75
    changed = selected.as_dict() != baseline.as_dict()
    status = "PASS_SHADOW_EXPERIENCE_CONDITIONED_COGNITIVE_EVOLUTION_V4" if improved and min_ok and changed else "WITHHOLD_EXPERIENCE_CONDITIONED_COGNITIVE_EVOLUTION_V4"
    src = (
        "from __future__ import annotations\n\n"
        f"COGNITIVE_POLICY = {selected.as_dict()!r}\n"
        f"VERIFIED_HIDDEN_SCORES = {selected_scores!r}\n"
        f"EXPERIENCE_BINDING = {{'experience_digest':{signal['experience_digest']!r},'source_ids':{signal['successful_source_ids']!r},'fact_count':{signal['fact_count']!r}}}\n\n"
        "def component():\n"
        "    return {'schema':'yado.cognitive_policy_candidate.v4','policy':COGNITIVE_POLICY,'verified_hidden_scores':VERIFIED_HIDDEN_SCORES,'experience_binding':EXPERIENCE_BINDING,'canonical_active':False,'consciousness_claimed':False}\n"
    )
    compile(src, str(CANDIDATE), "exec")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
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
        "candidate_path": str(CANDIDATE.relative_to(REPO)),
        "candidate_sha256": candidate_sha,
        "external_model_used": False,
        "downloaded_code_executed": False,
        "automatic_main_mutation": False,
        "canonical_mutation": False,
        "consciousness_claimed": False,
        "limitations": [
            "bounded externally authored benchmark and mutation grammar",
            "experience changes mutation pressure but does not prove general intelligence",
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
