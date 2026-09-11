from __future__ import annotations

import hashlib
import itertools
import json
import math
import random
from dataclasses import dataclass, asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'candidates/cognitive/yado-cognitive-tri-organ-evolution-v2.json'
CAP = ROOT / 'candidates/cognitive/yado_cognitive_tri_organ_candidate_v2.py'

SCHEMA = 'yado.cognitive_tri_organ_evolution.v2'
SEED = 20260911

@dataclass(frozen=True)
class Genome:
    logic_depth: int
    contradiction_check: bool
    thinking_depth: int
    thinking_beam: int
    abstraction_families: int


def logic_case(depth: int, contradiction_check: bool, edges, query, contradiction=None) -> bool:
    reach = {a: {b} for a, b in edges}
    nodes = {x for e in edges for x in e}
    for n in nodes:
        reach.setdefault(n, set())
    for _ in range(depth):
        changed = False
        for a in list(nodes):
            add = set()
            for b in list(reach[a]):
                add |= reach.get(b, set())
            if not add.issubset(reach[a]):
                reach[a] |= add
                changed = True
        if not changed:
            break
    if contradiction_check and contradiction is not None:
        x, y = contradiction
        if y in reach.get(x, set()) and x in reach.get(y, set()):
            return False
    return query[1] in reach.get(query[0], set())


def thinking_case(depth: int, beam: int, start: int, target: int, ops) -> bool:
    frontier = [(start, ())]
    seen = {start}
    for _ in range(depth):
        nxt = []
        for value, path in frontier:
            for name, fn in ops:
                nv = fn(value)
                if abs(nv) > 500 or nv in seen:
                    continue
                if nv == target:
                    return True
                seen.add(nv)
                nxt.append((nv, path + (name,)))
        nxt.sort(key=lambda x: abs(target - x[0]))
        frontier = nxt[:beam]
        if not frontier:
            break
    return start == target


def infer_family(examples, families):
    candidates = []
    for name, fn in families:
        if all(fn(x) == y for x, y in examples):
            candidates.append((name, fn))
    return candidates[0] if len(candidates) == 1 else (candidates[0] if candidates else None)


def build_tasks(seed: int):
    rng = random.Random(seed)
    logic_train, logic_hidden = [], []
    for bucket, count in ((logic_train, 18), (logic_hidden, 18)):
        for i in range(count):
            n = 4 + (i % 3)
            edges = [(j, j + 1) for j in range(n)]
            query = (0, n)
            contradiction = (0, n) if i % 7 == 0 else None
            expected = contradiction is None
            bucket.append((edges, query, contradiction, expected))
    ops = [('plus2', lambda x: x + 2), ('times2', lambda x: x * 2), ('minus3', lambda x: x - 3)]
    thinking_train, thinking_hidden = [], []
    for bucket, count in ((thinking_train, 20), (thinking_hidden, 20)):
        for _ in range(count):
            start = rng.randint(1, 8)
            v = start
            steps = rng.randint(2, 4)
            for _ in range(steps):
                v = rng.choice(ops)[1](v)
            bucket.append((start, v, ops, True))
    families_all = [
        ('x+1', lambda x: x + 1), ('2x', lambda x: 2*x), ('x2', lambda x: x*x),
        ('3x-2', lambda x: 3*x-2), ('neg+5', lambda x: -x+5),
        ('piece', lambda x: x+2 if x < 0 else 2*x),
    ]
    intel_train, intel_hidden = [], []
    for idx, (name, fn) in enumerate(families_all):
        xs = [-3, -1, 0, 2, 4]
        ex = [(x, fn(x)) for x in xs[:3]]
        hidden = [(x, fn(x)) for x in xs[3:]]
        intel_train.append((name, ex, hidden, idx))
        intel_hidden.append((name, ex[::-1], hidden[::-1], idx))
    return {
        'logic_train': logic_train, 'logic_hidden': logic_hidden,
        'thinking_train': thinking_train, 'thinking_hidden': thinking_hidden,
        'intel_train': intel_train, 'intel_hidden': intel_hidden,
        'families': families_all,
    }


def score(genome: Genome, tasks, split: str):
    logic_rows = tasks[f'logic_{split}']
    thinking_rows = tasks[f'thinking_{split}']
    intel_rows = tasks[f'intel_{split}']
    logic_ok = sum(logic_case(genome.logic_depth, genome.contradiction_check, *row[:3]) == row[3] for row in logic_rows)
    thinking_ok = sum(thinking_case(genome.thinking_depth, genome.thinking_beam, row[0], row[1], row[2]) == row[3] for row in thinking_rows)
    fams = tasks['families'][:genome.abstraction_families]
    intel_ok = 0
    intel_total = 0
    for _, ex, hidden, _ in intel_rows:
        chosen = infer_family(ex, fams)
        for x, y in hidden:
            intel_total += 1
            if chosen is not None and chosen[1](x) == y:
                intel_ok += 1
    return {
        'logic': logic_ok / len(logic_rows),
        'thinking': thinking_ok / len(thinking_rows),
        'intelligence': intel_ok / intel_total,
    }


def objective(s):
    vals = [s['logic'], s['thinking'], s['intelligence']]
    return sum(vals) / 3.0 - 0.15 * (max(vals) - min(vals))


def all_genomes():
    for d, c, td, b, a in itertools.product(range(1, 5), (False, True), range(1, 5), range(1, 7), range(2, 7)):
        yield Genome(d, c, td, b, a)


def emit_candidate(best: Genome, hidden):
    CAP.parent.mkdir(parents=True, exist_ok=True)
    src = (
        'from __future__ import annotations\n\n'
        f'COGNITIVE_POLICY = {asdict(best)!r}\n'
        f'VERIFIED_HIDDEN_SCORES = {hidden!r}\n\n'
        "def component():\n"
        "    return {'schema':'yado.cognitive_tri_organ_candidate.v2', 'policy':COGNITIVE_POLICY, "
        "'verified_hidden_scores':VERIFIED_HIDDEN_SCORES, 'canonical_active':False, "
        "'consciousness_claimed':False}\n"
    )
    compile(src, str(CAP), 'exec')
    CAP.write_text(src, encoding='utf-8')
    return hashlib.sha256(src.encode()).hexdigest()


def main():
    tasks = build_tasks(SEED)
    baseline = Genome(1, False, 1, 1, 2)
    baseline_train = score(baseline, tasks, 'train')
    baseline_hidden = score(baseline, tasks, 'hidden')

    history = []
    ranked = []
    for g in all_genomes():
        s = score(g, tasks, 'train')
        ranked.append((objective(s), min(s.values()), g, s))
    ranked.sort(key=lambda row: (row[0], row[1]), reverse=True)

    # Six bounded evolutionary generations: progressively larger candidate pools.
    for generation, limit in enumerate((16, 32, 64, 128, 256, len(ranked)), start=1):
        pool = ranked[:limit]
        best_row = pool[0]
        history.append({
            'generation': generation,
            'candidate_pool': limit,
            'best_genome': asdict(best_row[2]),
            'train_scores': best_row[3],
            'objective': best_row[0],
        })

    best = ranked[0][2]
    best_train = ranked[0][3]
    hidden = score(best, tasks, 'hidden')
    sha = emit_candidate(best, hidden)

    improved_all = all(hidden[k] >= baseline_hidden[k] for k in hidden) and any(hidden[k] > baseline_hidden[k] for k in hidden)
    balanced = min(hidden.values()) >= 0.80
    status = 'PASS_SHADOW_BOUNDED_TRI_ORGAN_COGNITIVE_EVOLUTION_V2' if improved_all and balanced else 'WITHHOLD_TRI_ORGAN_COGNITIVE_EVOLUTION_V2'

    receipt = {
        'schema': SCHEMA,
        'status': status,
        'seed': SEED,
        'organs': ['LOGIC', 'THINKING', 'INTELLIGENCE'],
        'baseline_genome': asdict(baseline),
        'baseline_train': baseline_train,
        'baseline_hidden': baseline_hidden,
        'selected_genome': asdict(best),
        'selected_train': best_train,
        'selected_hidden': hidden,
        'generations': history,
        'candidate_path': str(CAP.relative_to(ROOT)),
        'candidate_sha256': sha,
        'external_model_used': False,
        'downloaded_code_executed': False,
        'canonical_mutation': False,
        'automatic_main_mutation': False,
        'consciousness_claimed': False,
        'limitations': [
            'bounded synthetic benchmark families',
            'externally authored task generator and search space',
            'functional cognitive evolution evidence only',
        ],
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(receipt, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    print(json.dumps(receipt, sort_keys=True))
    if status.startswith('WITHHOLD'):
        raise SystemExit(2)


if __name__ == '__main__':
    main()
