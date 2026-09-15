"""Durable bounded selection, repair, verification and exploration.

The objective, policy and three goal grammars are assistant-authored. Concrete
goals and retry choices are derived from checked local experience. This module
does not claim unrestricted invention, external agency or consciousness.
"""
from __future__ import annotations

import copy

from .cognitive import CognitiveLoop, consolidated_stats, replay as cognitive_replay
from .development import RETRY_POLICY, candidates as retry_candidates, replay as development_replay
from .endogenous_run import _events_spec, _pressure, _relation_spec
from .kernel import decode, fingerprint

OBJECTIVE = 'BOUNDED_LEARN_REPAIR_AND_EXPLORE_V1'
DOMAINS = ('numeric', 'relation', 'events')
EXPLORATION_BUDGET = 3


def limits(budget, max_cycles):
    if (type(budget) is not int or not 1 <= budget <= 512
            or type(max_cycles) is not int or not 1 <= max_cycles <= 64):
        raise ValueError('AUTONOMY_LIMITS')


def _cognitive(records):
    return [r for r in records if str(r.get('kind', '')).startswith('COG_')]


def _development(records):
    relevant = [r for r in records if str(r.get('kind', '')).startswith(('COG_', 'DEV_'))]
    return development_replay(relevant) if any(r['kind'].startswith('DEV_') for r in relevant) else {}


def _numeric_spec(seed):
    raw = bytes.fromhex(seed)
    a, b, c, offset = 1 + raw[0] % 7, raw[1] % 11 - 5, raw[2] % 13 - 6, raw[3] - 128
    return {'domain': 'numeric',
            'rows': [{'x': x, 'y': y, 'expected': a * x ** 3 + b * x * y + c * y + offset}
                     for x in range(-3, 4) for y in range(-2, 3)],
            'queries': [{'x': 8 + raw[4] % 8, 'y': -2}, {'x': -8 - raw[5] % 8, 'y': 2}]}


def choose(records, sessions, session, identity):
    """Prefer an eligible failed task; otherwise explore by measured pressure."""
    if len(session['selections']) >= session['max_cycles']:
        return None
    cognitive = _cognitive(records)
    development = _development(records)
    goals = cognitive_replay(cognitive)
    if (any(g['status'] == 'ACTIVE' for g in goals.values())
            or any(s['status'] == 'ACTIVE' for s in development.values())):
        raise ValueError('AUTONOMY_SELECTION_REQUIRES_IDLE')
    used = {**development, 'autonomy': {'selections': [
        {'spec_digest': c['spec_digest']} for s in sessions.values() for c in s['selections']
        if c['route'] == 'RETRY_FAILURE']}}
    retry_session = {'id': records[-1]['tick'] + 1, 'remaining': session['remaining']}
    if 'retry_policy' in session:
        retry_session['retry_policy'] = session['retry_policy']
    proposals = retry_candidates(cognitive, used, retry_session)
    if proposals:
        choice = proposals[0]
        return {'route': 'RETRY_FAILURE', 'budget': choice['budget'],
                'spec': copy.deepcopy(goals[choice['parent_goal_id']]['spec']),
                'spec_digest': choice['spec_digest'], 'evidence': choice}
    if session['remaining'] < EXPLORATION_BUDGET:
        return None
    stats = consolidated_stats(cognitive)
    visits = {domain: sum(c['route'] == 'EXPLORE' and c['spec']['domain'] == domain
                         for c in session['selections']) for domain in DOMAINS}
    pressures = {domain: _pressure({'all_observations': stats}, domain) / (1 + visits[domain])
                 for domain in DOMAINS}
    seed = fingerprint({'identity': identity, 'source_event_hash': records[-1]['event_hash'],
                        'session': session['id'], 'cycle': len(session['selections'])})
    tied = [domain for domain in DOMAINS if pressures[domain] == max(pressures.values())]
    domain = tied[int(seed[:8], 16) % len(tied)]
    spec = {'numeric': _numeric_spec, 'relation': _relation_spec, 'events': _events_spec}[domain](seed)
    return {'route': 'EXPLORE', 'budget': EXPLORATION_BUDGET, 'spec': spec,
            'spec_digest': fingerprint(spec), 'evidence': {'seed': seed, 'pressures': pressures,
            'session_domain_visits': visits, 'self_model_digest': fingerprint(stats),
            'source_event_hash': records[-1]['event_hash'], 'goal_instance_authorship': 'YADO_STATE_DERIVED',
            'goal_grammar_authorship': 'ASSISTANT_AUTHORED_BOUNDED_GRAMMAR'}}


def outcome(session, records):
    cognitive = _cognitive(records)
    goal = cognitive_replay(cognitive)[session['child_goal_id']]
    terminal = next(r for r in reversed(cognitive) if r.get('goal_id') == goal['id']
                    and r['kind'] in {'COG_FINISH', 'COG_STOP'})
    return {'kind': 'AUTO_OUTCOME', 'autonomy_id': session['id'], 'goal_id': goal['id'],
            'terminal_tick': terminal['tick'], 'status': goal['status'],
            'spent': goal['budget'] - goal['remaining'], 'result_digest': fingerprint(goal['result']),
            'source_sha256': (goal['result'] or {}).get('source_sha256')}


def replay(records, identity):
    """Recompute choices and causal links; a valid hash chain alone is insufficient."""
    sessions, past = {}, []
    for record in records:
        r = {k: v for k, v in record.items() if k not in {'tick', 'event_hash'}}
        kind, tick = str(r.get('kind', '')), record['tick']
        pending = next((s for s in sessions.values() if s['awaiting_goal']), None)
        if pending and not (kind == 'COG_GOAL' and r.get('autonomy_id') == pending['id']):
            raise ValueError('AUTONOMY_MISSING_GOAL')
        if kind == 'COG_GOAL' and 'autonomy_id' in r:
            s = sessions.get(r['autonomy_id'])
            if s is None or not s['awaiting_goal'] or s['status'] != 'ACTIVE':
                raise ValueError('AUTONOMY_GOAL_PROVENANCE')
            choice = s['selections'][-1]
            if (r != {'kind': kind, 'autonomy_id': s['id'], 'selection_tick': s['selection_tick'],
                      'spec': choice['spec'], 'spec_digest': choice['spec_digest'],
                      'budget': choice['budget'], 'mode': 'full'} or tick != s['selection_tick'] + 1):
                raise ValueError('AUTONOMY_GOAL_PROVENANCE')
            s.update(awaiting_goal=False, child_goal_id=tick)
        elif kind == 'AUTO_START':
            limits(r['budget'], r['max_cycles'])
            expected = {'kind': kind, 'budget': r['budget'], 'max_cycles': r['max_cycles'], 'objective': OBJECTIVE}
            if 'retry_policy' in r:
                expected['retry_policy'] = RETRY_POLICY
            if (r != expected
                    or any(s['status'] == 'ACTIVE' for s in sessions.values())
                    or any(g['status'] == 'ACTIVE' for g in cognitive_replay(_cognitive(past)).values())
                    or any(s['status'] == 'ACTIVE' for s in _development(past).values())):
                raise ValueError('AUTONOMY_START_CONTRACT')
            sessions[tick] = {'id': tick, 'status': 'ACTIVE', 'budget': r['budget'],
                              'remaining': r['budget'], 'max_cycles': r['max_cycles'],
                              'selections': [], 'outcomes': [], 'awaiting_goal': False,
                              'selection_tick': None, 'child_goal_id': None}
            if 'retry_policy' in r:
                sessions[tick]['retry_policy'] = r['retry_policy']
        elif kind.startswith('AUTO_'):
            s = sessions.get(r.get('autonomy_id'))
            if s is None or s['status'] != 'ACTIVE':
                raise ValueError('AUTONOMY_SESSION_CAUSAL_LINK')
            if kind == 'AUTO_SELECT':
                expected = choose(past, sessions, s, identity)
                if (s['child_goal_id'] is not None or expected is None
                        or r != {'kind': kind, 'autonomy_id': s['id'], 'choice': expected}):
                    raise ValueError('AUTONOMY_SELECTION_EVIDENCE')
                s['selections'].append(r['choice'])
                s['remaining'] -= r['choice']['budget']
                s.update(awaiting_goal=True, selection_tick=tick)
            elif kind == 'AUTO_OUTCOME':
                goals = cognitive_replay(_cognitive(past))
                if (s['child_goal_id'] is None or goals[s['child_goal_id']]['status'] == 'ACTIVE'
                        or r != outcome(s, past)):
                    raise ValueError('AUTONOMY_OUTCOME_PROVENANCE')
                s['outcomes'].append({**r, 'tick': tick})
                s['child_goal_id'] = None
            elif kind in {'AUTO_FINISH', 'AUTO_STOP'}:
                reason = ('USER_STOP' if kind == 'AUTO_STOP' else
                          'CYCLE_LIMIT_REACHED' if len(s['selections']) >= s['max_cycles'] else 'BUDGET_EXHAUSTED')
                if (s['child_goal_id'] is not None or kind == 'AUTO_FINISH' and choose(past, sessions, s, identity) is not None
                        or r != {'kind': kind, 'autonomy_id': s['id'], 'reason': reason}):
                    raise ValueError('AUTONOMY_FINISH_CONTRACT')
                s.update(status='STOPPED' if kind == 'AUTO_STOP' else 'COMPLETE', reason=reason)
            else:
                raise ValueError('UNKNOWN_AUTONOMY_EVENT')
        past.append(record)
    if any(s['awaiting_goal'] for s in sessions.values()):
        raise ValueError('AUTONOMY_MISSING_GOAL')
    return sessions


class AutonomousLoop:
    def __init__(self, kernel):
        self.kernel = kernel
        self.cognitive = CognitiveLoop(kernel)

    def _records(self):
        return [{**decode(r['body']), 'tick': r['tick'], 'event_hash': r['event_hash']}
                for r in self.kernel.db.execute('SELECT tick,event_hash,body FROM events ORDER BY tick')]

    def start(self, budget=120, max_cycles=20):
        limits(budget, max_cycles)
        def begin():
            records = self._records()
            if (any(s['status'] == 'ACTIVE' for s in replay(records, self.kernel.identity).values())
                    or any(g['status'] == 'ACTIVE' for g in cognitive_replay(_cognitive(records)).values())
                    or any(s['status'] == 'ACTIVE' for s in _development(records).values())):
                raise ValueError('AUTONOMY_REQUIRES_IDLE_KERNEL')
            return self.kernel._append({'kind': 'AUTO_START', 'budget': budget,
                                        'max_cycles': max_cycles, 'objective': OBJECTIVE,
                                        'retry_policy': RETRY_POLICY})['tick']
        return self.cognitive._transaction(begin)

    def _step(self):
        records = self._records()
        sessions = replay(records, self.kernel.identity)
        s = next((s for s in sessions.values() if s['status'] == 'ACTIVE'), None)
        if s is None:
            return []
        goals = cognitive_replay(_cognitive(records))
        if (any(g['status'] == 'ACTIVE' and g['id'] != s['child_goal_id'] for g in goals.values())
                or any(d['status'] == 'ACTIVE' for d in _development(records).values())):
            return []
        if s['child_goal_id'] is not None:
            if goals[s['child_goal_id']]['status'] == 'ACTIVE':
                return [self.cognitive._step()]
            return [self.kernel._append(outcome(s, records))]
        # Make learned observations durable beyond the recent-attention window.
        consolidation = self.cognitive._step()
        if consolidation is not None:
            return [consolidation]
        choice = choose(records, sessions, s, self.kernel.identity)
        if choice is None:
            reason = 'CYCLE_LIMIT_REACHED' if len(s['selections']) >= s['max_cycles'] else 'BUDGET_EXHAUSTED'
            return [self.kernel._append({'kind': 'AUTO_FINISH', 'autonomy_id': s['id'], 'reason': reason})]
        selection = self.kernel._append({'kind': 'AUTO_SELECT', 'autonomy_id': s['id'], 'choice': choice})
        goal = self.kernel._append({'kind': 'COG_GOAL', 'autonomy_id': s['id'],
            'selection_tick': selection['tick'], 'spec': copy.deepcopy(choice['spec']),
            'spec_digest': choice['spec_digest'], 'budget': choice['budget'], 'mode': 'full'})
        return [selection, goal]

    def run(self, max_steps=200):
        if type(max_steps) is not int or not 1 <= max_steps <= 1000:
            raise ValueError('AUTONOMY_STEP_BUDGET')
        events = []
        for _ in range(max_steps):
            result = self.cognitive._transaction(self._step)
            if not result:
                break
            events.extend(result)
        return events

    def stop(self, session_id):
        def end():
            records = self._records()
            s = replay(records, self.kernel.identity).get(int(session_id))
            if s is None:
                raise ValueError('UNKNOWN_AUTONOMY_SESSION')
            if s['status'] != 'ACTIVE':
                return {'status': s['status'], 'autonomy_id': s['id']}
            if s['child_goal_id'] is not None:
                child = cognitive_replay(_cognitive(records))[s['child_goal_id']]
                if child['status'] == 'ACTIVE':
                    records.append(self.kernel._append({'kind': 'COG_STOP', 'goal_id': child['id'], 'reason': 'USER_STOP'}))
                self.kernel._append(outcome(s, records))
            return self.kernel._append({'kind': 'AUTO_STOP', 'autonomy_id': s['id'], 'reason': 'USER_STOP'})
        return self.cognitive._transaction(end)

    def snapshot(self):
        self.kernel.verify_state()
        return {'schema': 'yado.bounded_autonomy.v1', 'sessions': replay(self._records(), self.kernel.identity),
                'objective': OBJECTIVE, 'goal_grammars': list(DOMAINS),
                'controller_authorship': 'ASSISTANT', 'external_actions_enabled': False,
                'general_intelligence_established': False, 'consciousness_established': False}
