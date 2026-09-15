"""Declared, bounded admission tasks; the task grammar is assistant-authored.

These measure Boolean schema transfer, constrained planning, routing and exact
polynomial source synthesis. They are not a general intelligence examination.
"""
from itertools import product
import random


ORGANS = ('LOGIC', 'THINKING', 'INTELLIGENCE', 'CODE')


def challenge(seed, *, retention=False):
    rng = random.Random(str(seed))
    width = 2 if retention else 4
    names = ['f_' + str(rng.randrange(10**9)) for _ in range(width)]
    signs = [bool(rng.getrandbits(1)) for _ in names]
    train, queries, labels = [], [], []
    for bits in product((False, True), repeat=width):
        answer = 'YES' if (sum(bits) % 2 == 0 if retention else list(bits) == signs) else 'NO'
        base = dict(zip(names, bits))
        # Holdout noise combinations are absent from training. The projected
        # truth table is observed; this checks nuisance invariance, not unseen
        # truth-table inference. Repeat for the inherited router support gate.
        for noise in (False, True):
            for _ in range(2):
                train.append({'input': {**base, 'n0': noise, 'n1': noise}, 'expected': answer})
            queries.append({**base, 'n0': noise, 'n1': not noise})
            labels.append(answer)
    logic = {'organ': 'LOGIC', 'training': train, 'queries': queries}
    route = {'organ': 'INTELLIGENCE', 'training': train, 'queries': queries, 'fallback': 'NO'}
    coefficient, offset = rng.choice((-7, -3, 2, 5)), rng.randrange(-30, 31)
    degree = 1 if retention else 4
    xs = list(range(-5, 6))
    query_x = rng.sample(list(range(-14, -6)) + list(range(7, 15)), 6)
    def value(x):
        return coefficient * x ** degree + 2 * x + offset
    code = {'organ': 'CODE', 'source': 'def solve(x):\n    return x\n', 'function': 'solve',
            'training': [[[x], value(x)] for x in xs], 'queries': [[x] for x in query_x]}
    stages = [{'stage_id': 'A_' + str(rng.randrange(10**6)), 'cost': 1, 'expected_gain': .75, 'latency': 9},
              {'stage_id': 'Z_' + str(rng.randrange(10**6)), 'cost': 1, 'expected_gain': .75, 'latency': 1}]
    if retention:
        stages[1]['cost'] = 2
    planning = {'organ': 'THINKING', 'current': .1, 'target': .8, 'budget': 2, 'stages': stages}
    cases = [(logic, labels), (route, [[x] for x in labels]),
             (planning, stages[0 if retention else 1]['stage_id']), (code, [value(x) for x in query_x])]
    if retention:
        # Real counterexamples for the historical lineage planner: source
        # availability, dependencies, quota, and an already satisfied goal.
        for forbidden in ({'available': False}, {'requires': ['MISSING']}, {'quota_remaining': 0}):
            task = {**planning, 'stages': [{**stages[0], **forbidden}, stages[1]]}
            cases.append((task, stages[1]['stage_id']))
        cases.append(({**planning, 'current': .9}, 'STOP'))
        cases.append(({**planning, 'budget': 0}, 'WITHHOLD'))
    return cases
