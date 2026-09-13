"""Bounded, experience-driven retry goals over the admitted cognitive loop.

The controller and its objective are host-authored. The kernel selects a past
failure and the retry budget from checked events; it does not invent an open
domain objective. Historical validation examples remain historical examples.
Only numeric and native-source work can be scheduled here.
"""
from __future__ import annotations

import copy

from .cognitive import (CognitiveLoop, available_strategies, consolidated_stats,
                        goal_context, replay as cognitive_replay)
from .kernel import decode, fingerprint


def limits(budget, max_goals):
    if (type(budget) is not int or not 1 <= budget <= 30
            or type(max_goals) is not int or not 1 <= max_goals <= 8):
        raise ValueError('DEVELOPMENT_LIMITS')


def candidates(cognitive, sessions, session):
    goals = cognitive_replay(cognitive)
    used = {choice['spec_digest'] for s in sessions.values() for choice in s['selections']}
    solved = {fingerprint(g['spec']) for g in goals.values()
              if g['status'] == 'VALIDATED_ON_HOLDOUT'}
    generated = {r['tick'] for r in cognitive
                 if r['kind'] == 'COG_GOAL' and 'development_id' in r}
    stats, proposals = consolidated_stats(cognitive), []
    for g in goals.values():
        spec_digest = fingerprint(g['spec'])
        if (g['id'] >= session['id'] or g['id'] in generated or g['status'] != 'WITHHOLD'
                or g['mode'] != 'full' or g['spec']['domain'] not in {'native_source', 'numeric'}
                or spec_digest in used or spec_digest in solved):
            continue
        allowed = available_strategies(g, cognitive)
        untried = [(s, c) for s, c in allowed if s not in g['attempted']]
        budget = sum(c for _, c in allowed)
        failures = [r['tick'] for r in cognitive if r['kind'] == 'COG_VERIFY'
                    and r['goal_id'] == g['id'] and not r['passed']]
        if not failures or not untried or not g['budget'] < budget <= session['remaining']:
            continue
        estimates = []
        for strategy, cost in untried:
            evidence = stats.get(goal_context(g['spec']) + '/' + strategy, {})
            observations = evidence.get('successes', 0) + evidence.get('failures', 0)
            probability = (evidence.get('successes', 0) + 1) / (observations + 2)
            estimates.append({'strategy': strategy, 'cost': cost, 'observations': observations,
                              'estimated_success': probability})
        finish = next(r for r in reversed(cognitive)
                      if r['kind'] == 'COG_FINISH' and r['goal_id'] == g['id'])
        proposals.append({'parent_goal_id': g['id'], 'parent_finish_tick': finish['tick'],
                          'failure_verification_ticks': failures, 'spec_digest': spec_digest,
                          'budget': budget, 'untried': estimates,
                          'priority': max(x['estimated_success'] / x['cost'] for x in estimates),
                          'self_model_digest': fingerprint(stats)})
    return sorted(proposals, key=lambda p: (-p['priority'], p['budget'], p['parent_goal_id']))


def outcome(session, cognitive):
    goal_id = session['child_goal_id']
    g = cognitive_replay(cognitive)[goal_id]
    terminal = next(r for r in reversed(cognitive)
                    if r.get('goal_id') == goal_id and r['kind'] in {'COG_FINISH', 'COG_STOP'})
    return {'kind': 'DEV_OUTCOME', 'development_id': session['id'], 'goal_id': goal_id,
            'terminal_tick': terminal['tick'], 'status': g['status'],
            'spent': g['budget'] - g['remaining'],
            'source_sha256': (g['result'] or {}).get('source_sha256')}


def finish_reason(session, cognitive, sessions):
    if len(session['selections']) >= session['max_goals']:
        return 'GOAL_LIMIT_REACHED'
    if session['remaining'] == 0:
        return 'BUDGET_RESERVED'
    if not candidates(cognitive, sessions, session):
        return 'NO_ELIGIBLE_EXPERIENCE_WITHIN_BUDGET'
    return None


def replay(records):
    """Verify selection, budget, subgoal origin and outcome beyond hash integrity."""
    sessions, cognitive = {}, []
    for record in records:
        r = {k: v for k, v in record.items() if k not in {'tick', 'event_hash'}}
        kind, tick = r['kind'], record['tick']
        pending = next((s for s in sessions.values() if s['awaiting_goal']), None)
        if pending and not (kind == 'COG_GOAL' and r.get('development_id') == pending['id']):
            raise ValueError('DEVELOPMENT_MISSING_SUBGOAL')
        if kind.startswith('COG_'):
            if kind == 'COG_GOAL' and 'development_id' in r:
                s = sessions.get(r['development_id'])
                if s is None or not s['awaiting_goal']:
                    raise ValueError('DEVELOPMENT_SUBGOAL_PROVENANCE')
                choice = s['selections'][-1]
                parent = cognitive_replay(cognitive)[choice['parent_goal_id']]
                expected = {'kind': 'COG_GOAL', 'spec': parent['spec'], 'budget': choice['budget'],
                            'mode': 'full', 'spec_digest': choice['spec_digest'],
                            'development_id': s['id'], 'selection_tick': s['selection_tick']}
                if r != expected or tick != s['selection_tick'] + 1:
                    raise ValueError('DEVELOPMENT_SUBGOAL_PROVENANCE')
                s.update(awaiting_goal=False, child_goal_id=tick)
            cognitive.append(record)
            continue
        if kind == 'DEV_START':
            limits(r['budget'], r['max_goals'])
            if (set(r) != {'kind', 'budget', 'max_goals'}
                    or any(s['status'] == 'ACTIVE' for s in sessions.values())
                    or any(g['status'] == 'ACTIVE' for g in cognitive_replay(cognitive).values())):
                raise ValueError('DEVELOPMENT_START_CONTRACT')
            sessions[tick] = {'id': tick, 'status': 'ACTIVE', 'budget': r['budget'],
                              'remaining': r['budget'], 'max_goals': r['max_goals'],
                              'selections': [], 'outcomes': [], 'child_goal_id': None,
                              'awaiting_goal': False, 'selection_tick': None}
            continue
        s = sessions.get(r.get('development_id'))
        if s is None or s['status'] != 'ACTIVE':
            raise ValueError('DEVELOPMENT_SESSION_CAUSAL_LINK')
        if kind == 'DEV_SELECT':
            proposals = candidates(cognitive, sessions, s)
            if (s['child_goal_id'] is not None or len(s['selections']) >= s['max_goals']
                    or any(g['status'] == 'ACTIVE' for g in cognitive_replay(cognitive).values())
                    or not proposals or r != {'kind': kind, 'development_id': s['id'],
                                               'choice': proposals[0]}):
                raise ValueError('DEVELOPMENT_SELECTION_EVIDENCE')
            s['selections'].append(r['choice'])
            s['remaining'] -= r['choice']['budget']
            s.update(awaiting_goal=True, selection_tick=tick)
        elif kind == 'DEV_OUTCOME':
            goals = cognitive_replay(cognitive)
            if (s['child_goal_id'] is None or goals[s['child_goal_id']]['status'] == 'ACTIVE'
                    or r != outcome(s, cognitive)):
                raise ValueError('DEVELOPMENT_OUTCOME_PROVENANCE')
            s['outcomes'].append({**r, 'tick': tick})
            s['child_goal_id'] = None
        elif kind in {'DEV_FINISH', 'DEV_STOP'}:
            reason = 'USER_STOP' if kind == 'DEV_STOP' else finish_reason(s, cognitive, sessions)
            if (s['child_goal_id'] is not None or reason is None
                    or r != {'kind': kind, 'development_id': s['id'], 'reason': reason}):
                raise ValueError('DEVELOPMENT_FINISH_CONTRACT')
            s.update(status='STOPPED' if kind == 'DEV_STOP' else 'COMPLETE', reason=reason)
        else:
            raise ValueError('UNKNOWN_DEVELOPMENT_EVENT')
    if any(s['awaiting_goal'] for s in sessions.values()):
        raise ValueError('DEVELOPMENT_MISSING_SUBGOAL')
    return sessions


class DevelopmentLoop:
    def __init__(self, kernel):
        self.kernel = kernel
        self.cognitive = CognitiveLoop(kernel)

    def _records(self):
        records = []
        for row in self.kernel.db.execute('SELECT tick,event_hash,body FROM events ORDER BY tick'):
            body = decode(row['body'])
            if str(body.get('kind', '')).startswith(('COG_', 'DEV_')):
                records.append({**body, 'tick': row['tick'], 'event_hash': row['event_hash']})
        return records

    def start(self, budget=12, max_goals=2):
        limits(budget, max_goals)
        def begin():
            records = self._records()
            if (any(s['status'] == 'ACTIVE' for s in replay(records).values())
                    or any(g['status'] == 'ACTIVE' for g in cognitive_replay(
                        [r for r in records if r['kind'].startswith('COG_')]).values())):
                raise ValueError('DEVELOPMENT_REQUIRES_IDLE_KERNEL')
            return self.kernel._append({'kind': 'DEV_START', 'budget': budget, 'max_goals': max_goals})['tick']
        return self.cognitive._transaction(begin)

    def _step(self):
        records = self._records()
        sessions = replay(records)
        s = next((s for s in sessions.values() if s['status'] == 'ACTIVE'), None)
        if s is None:
            return []
        cognitive = [r for r in records if r['kind'].startswith('COG_')]
        goals = cognitive_replay(cognitive)
        child = goals.get(s['child_goal_id'])
        if child and child['status'] != 'ACTIVE':
            return [self.kernel._append(outcome(s, cognitive))]
        if any(g['status'] == 'ACTIVE' and g['id'] != s['child_goal_id'] for g in goals.values()):
            return []  # Resume after the externally submitted work is handled.
        if child:
            return [self.cognitive._step()]
        reason = finish_reason(s, cognitive, sessions)
        if reason:
            return [self.kernel._append({'kind': 'DEV_FINISH', 'development_id': s['id'], 'reason': reason})]
        choice = candidates(cognitive, sessions, s)[0]
        selected = self.kernel._append({'kind': 'DEV_SELECT', 'development_id': s['id'], 'choice': choice})
        goal = self.kernel._append({'kind': 'COG_GOAL', 'spec': copy.deepcopy(goals[choice['parent_goal_id']]['spec']),
                                   'budget': choice['budget'], 'mode': 'full',
                                   'spec_digest': choice['spec_digest'], 'development_id': s['id'],
                                   'selection_tick': selected['tick']})
        return [selected, goal]

    def run(self, max_steps=20):
        if type(max_steps) is not int or not 1 <= max_steps <= 1000:
            raise ValueError('DEVELOPMENT_STEP_BUDGET')
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
            s = replay(records).get(int(session_id))
            if s is None:
                raise ValueError('UNKNOWN_DEVELOPMENT_SESSION')
            if s['status'] != 'ACTIVE':
                return {'status': s['status'], 'development_id': s['id']}
            cognitive = [r for r in records if r['kind'].startswith('COG_')]
            if s['child_goal_id'] is not None:
                g = cognitive_replay(cognitive)[s['child_goal_id']]
                if g['status'] == 'ACTIVE':
                    cognitive.append(self.kernel._append({'kind': 'COG_STOP', 'goal_id': g['id'], 'reason': 'USER_STOP'}))
                self.kernel._append(outcome(s, cognitive))
            return self.kernel._append({'kind': 'DEV_STOP', 'development_id': s['id'], 'reason': 'USER_STOP'})
        return self.cognitive._transaction(end)

    def snapshot(self):
        self.kernel.verify_state()
        return {'schema': 'yado.experience_development.v1', 'sessions': replay(self._records()),
                'goal_origin': 'RETRY_SELECTED_FROM_CHECKED_FAILURES',
                'objective_and_controller_authorship': 'ASSISTANT',
                'validation_scope': 'REUSED_TASK_HOLDOUT; FRESH_TRANSFER_REQUIRES_SEPARATE_CHECK',
                'background_process_running': False, 'consciousness_established': False}
