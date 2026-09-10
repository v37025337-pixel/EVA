"""Event-sourced, bounded metacognition over real inherited YADO solvers.

The controller is assistant-authored. Its empirical self-model is learned from
checked executions. Nothing here measures or asserts phenomenal consciousness.
"""
from __future__ import annotations

import copy
from fractions import Fraction
import math
import time

from .archive import canonical, sha
from .kernel import decode, encode, equivalent, fingerprint

MODES = ('full', 'no_memory', 'no_self_model', 'no_consolidation', 'fixed_max')
STRATEGIES = {
    'numeric': (('polynomial_1', 1), ('polynomial_2', 2), ('polynomial_3', 3)),
    'relation': (('native_logic', 1), ('native_router', 2)),
    'events': (('native_thinking', 1), ('native_router', 2)),
}
RECENT_OBSERVATIONS = 16
WORKSPACE_CAPACITY = 2


def _integer(value, bound):
    return type(value) is int and abs(value) <= bound


def validate_goal(spec):
    if not isinstance(spec, dict) or spec.get('domain') not in STRATEGIES:
        raise ValueError('SUPPORTED_GOAL_DOMAINS: numeric, relation, events')
    spec = copy.deepcopy(spec)
    domain = spec['domain']
    if domain == 'numeric':
        if set(spec) != {'domain', 'rows', 'queries'}:
            raise ValueError('NUMERIC_GOAL_REQUIRES_ROWS_AND_UNLABELLED_QUERIES')
        rows, queries = spec['rows'], spec['queries']
        if not isinstance(rows, list) or not 16 <= len(rows) <= 64:
            raise ValueError('NUMERIC_ROWS_REQUIRE_16_TO_64_UNIQUE_EXAMPLES')
        if not isinstance(queries, list) or not 1 <= len(queries) <= 32:
            raise ValueError('QUERY_BUDGET_EXCEEDED')
        for row in rows + queries:
            if (not isinstance(row, dict) or not _integer(row.get('x'), 1000)
                    or not _integer(row.get('y'), 1000)):
                raise ValueError('BOUNDED_INTEGER_COORDINATES_REQUIRED')
        if any(set(r) != {'x', 'y', 'expected'} or not _integer(r['expected'], 10**12) for r in rows):
            raise ValueError('INVALID_LABELLED_EXAMPLE')
        if any(set(q) != {'x', 'y'} for q in queries):
            raise ValueError('QUERY_ANSWERS_MUST_NOT_BE_SUPPLIED')
        if len({(r['x'], r['y']) for r in rows}) != len(rows):
            raise ValueError('DUPLICATE_COORDINATES_LEAK_ACROSS_HOLDOUT')
    elif domain == 'relation':
        if set(spec) != {'domain', 'relation', 'start'} or not isinstance(spec['relation'], list):
            raise ValueError('RELATION_SCHEMA')
        edges = spec['relation']
        if len(edges) > 1024 or any(not isinstance(e, (list, tuple)) or len(e) != 2 for e in edges):
            raise ValueError('RELATION_EDGE_BUDGET_OR_ARITY')
        nodes = [spec['start']] + [n for e in edges for n in e]
        if any(not (_integer(n, 10**9) or type(n) is str and len(n) <= 80) for n in nodes):
            raise ValueError('INVALID_NODE')
        if len(set(nodes)) > 128:
            raise ValueError('RELATION_NODE_BUDGET')
    else:
        if set(spec) != {'domain', 'events'} or not isinstance(spec['events'], list):
            raise ValueError('EVENT_SCHEMA')
        if len(spec['events']) > 2048:
            raise ValueError('EVENT_BUDGET')
        for event in spec['events']:
            if (not isinstance(event, (list, tuple)) or len(event) != 2
                    or not all(type(x) is str and len(x) <= 80 for x in event)):
                raise ValueError('EVENT_REQUIRES_TWO_SHORT_STRINGS')
    return spec


def split_examples(rows):
    # Neither labels nor query answers influence this fixed partition.
    ordered = sorted(rows, key=lambda r: sha(canonical([r['x'], r['y']]).encode()))
    count = max(4, len(ordered) // 4)
    return copy.deepcopy(ordered[count:]), copy.deepcopy(ordered[:count])


def _update(stats, observation):
    key = observation['domain'] + '/' + observation['strategy']
    item = stats.setdefault(key, {'successes': 0, 'failures': 0, 'cost': 0, 'squared_error': 0.0})
    item['successes' if observation['success'] else 'failures'] += 1
    item['cost'] += observation['cost']
    item['squared_error'] += observation['brier_error']


def consolidated_stats(records):
    stats = {}
    for r in records:
        if r['kind'] == 'COG_REFLECT':
            _update(stats, r)
    return stats


def replay(records):
    """Validate cross-event causal links while rebuilding disposable projections."""
    goals, past = {}, []
    for r in records:
        kind = r['kind']
        if kind == 'COG_GOAL':
            validate_goal(r['spec'])
            if (r['mode'] not in MODES or type(r['budget']) is not int or not 1 <= r['budget'] <= 30
                    or r['spec_digest'] != fingerprint(r['spec'])):
                raise ValueError('COGNITIVE_GOAL_CONTRACT')
            goals[r['tick']] = {'id': r['tick'], 'spec': r['spec'], 'mode': r['mode'],
                'budget': r['budget'], 'remaining': r['budget'], 'status': 'ACTIVE',
                'phase': 'SELECT', 'attempted': [], 'decision': None, 'execution': None,
                'verification': None, 'result': None}
        elif kind == 'COG_CONSOLIDATE':
            expected = consolidated_stats(past)
            observed = [x['tick'] for x in past if x['kind'] == 'COG_REFLECT']
            if (r['stats'] != expected or r['through_tick'] != max(observed, default=0)
                    or r['model_digest'] != fingerprint(expected)):
                raise ValueError('COGNITIVE_CONSOLIDATION_INTEGRITY')
        else:
            g = goals.get(r.get('goal_id'))
            if g is None or g['status'] != 'ACTIVE':
                raise ValueError('COGNITIVE_GOAL_CAUSAL_LINK')
            if kind == 'COG_DECIDE':
                choice = r['choice']
                allowed = dict(STRATEGIES[g['spec']['domain']])
                if (g['phase'] != 'SELECT' or choice['strategy'] in g['attempted']
                        or allowed.get(choice['strategy']) != choice['cost']
                        or choice['cost'] > g['remaining']
                        or r['workspace_digest'] != fingerprint(r['workspace'])
                        or r['workspace']['goal_digest'] != fingerprint(g['spec'])
                        or r['workspace']['remaining_budget'] != g['remaining']
                        or not 1 <= len(r['workspace']['proposals']) <= WORKSPACE_CAPACITY
                        or r['workspace']['proposals'][0] != choice):
                    raise ValueError('COGNITIVE_DECISION_CONTRACT')
                g.update(phase='EXECUTE', decision=r, execution=None, verification=None)
            elif kind == 'COG_EXECUTE':
                if (g['phase'] != 'EXECUTE' or r['decision_tick'] != g['decision']['tick']
                        or r['workspace_digest'] != g['decision']['workspace_digest']):
                    raise ValueError('COGNITIVE_EXECUTION_CAUSAL_LINK')
                g['remaining'] -= g['decision']['choice']['cost']
                g['attempted'].append(g['decision']['choice']['strategy'])
                g.update(phase='VERIFY', execution=r)
            elif kind == 'COG_VERIFY':
                if (g['phase'] != 'VERIFY' or r['execution_tick'] != g['execution']['tick']
                        or type(r['passed']) is not bool
                        or r['workspace_digest'] != g['decision']['workspace_digest']):
                    raise ValueError('COGNITIVE_VERIFICATION_CAUSAL_LINK')
                g.update(phase='REFLECT', verification=r)
            elif kind == 'COG_REFLECT':
                choice = g['decision']['choice']
                if (g['phase'] != 'REFLECT' or r['verification_tick'] != g['verification']['tick']
                        or r['success'] is not g['verification']['passed']
                        or r['domain'] != g['spec']['domain'] or r['strategy'] != choice['strategy']
                        or r['cost'] != choice['cost']
                        or r['brier_error'] != (int(r['success']) - choice['probability']) ** 2
                        or r['workspace_digest'] != g['decision']['workspace_digest']):
                    raise ValueError('COGNITIVE_REFLECTION_CAUSAL_LINK')
                g['phase'] = 'FINISH' if r['success'] else 'SELECT'
            elif kind == 'COG_FINISH':
                if g['phase'] not in {'FINISH', 'SELECT'}:
                    raise ValueError('COGNITIVE_PREMATURE_FINISH')
                if g['phase'] == 'FINISH':
                    expected_status = 'VALIDATED_ON_HOLDOUT' if g['spec']['domain'] == 'numeric' else 'VERIFIED'
                else:
                    affordable = [(s, c) for s, c in STRATEGIES[g['spec']['domain']]
                                  if s not in g['attempted'] and c <= g['remaining']]
                    if affordable:
                        raise ValueError('COGNITIVE_FINISH_WITH_AVAILABLE_ACTION')
                    expected_status = 'WITHHOLD'
                if r['status'] != expected_status:
                    raise ValueError('COGNITIVE_FINISH_STATUS')
                expected_result = g['execution']['result'] if g['phase'] == 'FINISH' else None
                if r['result'] != expected_result or r['spent'] != g['budget'] - g['remaining']:
                    raise ValueError('COGNITIVE_FINISH_RESULT')
                g.update(status=r['status'], result=r['result'], phase='DONE')
            elif kind == 'COG_STOP':
                g.update(status='STOPPED', phase='DONE')
            else:
                raise ValueError('UNKNOWN_COGNITIVE_EVENT')
        past.append(r)
    return goals


def empirical_model(records, goal):
    if goal['mode'] == 'no_memory':
        records = [r for r in records if r.get('goal_id') == goal['id']]
    stats, through, source = {}, 0, None
    if goal['mode'] not in {'no_memory', 'no_consolidation'}:
        for r in records:
            if r['kind'] == 'COG_CONSOLIDATE':
                stats, through, source = copy.deepcopy(r['stats']), r['through_tick'], r['tick']
    recent = [r for r in records if r['kind'] == 'COG_REFLECT' and r['tick'] > through]
    for r in recent[-RECENT_OBSERVATIONS:]:
        _update(stats, r)
    return stats, {'consolidation_tick': source, 'recent_reflection_ticks': [r['tick'] for r in recent[-RECENT_OBSERVATIONS:]]}


class CognitiveLoop:
    def __init__(self, kernel):
        self.kernel = kernel

    def _records(self):
        records = []
        for row in self.kernel.db.execute('SELECT tick,event_hash,body FROM events ORDER BY tick'):
            body = decode(row['body'])
            if str(body.get('kind', '')).startswith('COG_'):
                records.append({**body, 'tick': row['tick'], 'event_hash': row['event_hash']})
        return records

    def _transaction(self, operation):
        self.kernel._check_sources()
        self.kernel.db.execute('BEGIN IMMEDIATE')
        try:
            self.kernel.verify_state()
            result = operation()
            self.kernel.db.execute('COMMIT')
            return result
        except BaseException:
            self.kernel.db.execute('ROLLBACK')
            raise

    def open_goal(self, spec, budget=6, mode='full'):
        spec = validate_goal(spec)
        if type(budget) is not int or not 1 <= budget <= 30 or mode not in MODES:
            raise ValueError('INVALID_COGNITIVE_BUDGET_OR_MODE')
        def submit():
            if sum(g['status'] == 'ACTIVE' for g in replay(self._records()).values()) >= 64:
                raise ValueError('ACTIVE_GOAL_BUDGET')
            return self.kernel._append({'kind': 'COG_GOAL', 'spec': spec, 'budget': budget,
                                        'mode': mode, 'spec_digest': fingerprint(spec)})['tick']
        return self._transaction(submit)

    def stop(self, goal_id):
        def stop_goal():
            g = replay(self._records()).get(int(goal_id))
            if g is None:
                raise ValueError('UNKNOWN_GOAL')
            if g['status'] != 'ACTIVE':
                return {'status': g['status'], 'goal_id': g['id']}
            return self.kernel._append({'kind': 'COG_STOP', 'goal_id': g['id'], 'reason': 'USER_STOP'})
        return self._transaction(stop_goal)

    def _select(self, g, records):
        stats, evidence = empirical_model(records, g)
        proposals = []
        for strategy, cost in STRATEGIES[g['spec']['domain']]:
            if strategy in g['attempted'] or cost > g['remaining']:
                continue
            item = stats.get(g['spec']['domain'] + '/' + strategy, {})
            n = item.get('successes', 0) + item.get('failures', 0)
            probability = (item.get('successes', 0) + 1) / (n + 2)
            uncertainty = math.sqrt(probability * (1 - probability) / (n + 3))
            score = probability + .1 * uncertainty - .04 * cost
            if g['mode'] == 'no_self_model':
                score = -cost
            elif g['mode'] == 'fixed_max':
                score = cost
            proposals.append({'strategy': strategy, 'cost': cost, 'probability': probability,
                              'uncertainty': uncertainty, 'observations': n, 'score': score})
        proposals.sort(key=lambda p: (-p['score'], p['cost'], p['strategy']))
        if not proposals:
            return self._finish(g, False)
        workspace = {'goal_id': g['id'], 'goal_digest': fingerprint(g['spec']),
                     'remaining_budget': g['remaining'], 'proposals': proposals[:WORKSPACE_CAPACITY],
                     'self_model_digest': fingerprint(stats), 'evidence': evidence}
        return {'kind': 'COG_DECIDE', 'goal_id': g['id'], 'choice': proposals[0],
                'workspace': workspace, 'workspace_digest': fingerprint(workspace),
                'broadcast_consumers': ['executor', 'verifier', 'self_model'],
                'selection_basis': {'no_self_model': 'COST_ONLY_ABLATION', 'fixed_max': 'FIXED_MAXIMUM_CAPACITY_BASELINE'}.get(
                    g['mode'], 'EMPIRICAL_SUCCESS_UNCERTAINTY_AND_COST'),
                'candidate_count': len(proposals)}

    def _execute(self, g):
        spec, choice = g['spec'], g['decision']['choice']
        parent = self.kernel.parent
        start = time.perf_counter()
        try:
            if spec['domain'] == 'numeric':
                train, holdout = split_examples(spec['rows'])
                model = parent.fit_polynomial_logic(train, max_degree=int(choice['strategy'][-1]))
                if model.get('kind') == 'WITHHOLD':
                    result = {'status': 'WITHHOLD', 'reason': model.get('reason')}
                else:
                    def predict(rows):
                        return [parent.predict_polynomial_logic(model, row['x'], row['y']) for row in rows]
                    result = {'status': 'CANDIDATE', 'model': model, 'predictions': predict(spec['queries']),
                              'holdout_predictions': predict(holdout), 'train_count': len(train),
                              'holdout_count': len(holdout)}
            elif spec['domain'] == 'relation':
                if choice['strategy'] == 'native_logic':
                    native = parent.all_experience_logic(spec['relation'], spec['start'])
                else:
                    native = parent.all_experience_intelligence({'input_contract': 'RELATION_START_TO_STATE',
                        'relation': spec['relation'], 'start': spec['start']})
                result = {'status': 'CANDIDATE', 'answer': native['result'], 'native': native}
            else:
                if choice['strategy'] == 'native_thinking':
                    native = parent.all_experience_thinking(spec['events'])
                else:
                    native = parent.all_experience_intelligence({'input_contract': 'EVENT_SEQUENCE_TO_BOOLEAN',
                                                                 'events': spec['events']})
                result = {'status': 'CANDIDATE', 'answer': native['result'], 'native': native}
            encode(result)
        except Exception as error:
            result = {'status': 'ERROR', 'error_type': type(error).__name__, 'error': str(error)}
        return {'kind': 'COG_EXECUTE', 'goal_id': g['id'], 'decision_tick': g['decision']['tick'],
                'workspace_digest': g['decision']['workspace_digest'], 'result': result,
                'elapsed_ms': (time.perf_counter() - start) * 1000}

    def _verify(self, g):
        spec, result = g['spec'], g['execution']['result']
        passed, checks, scope = False, 0, 'NO_CANDIDATE'
        if result['status'] == 'CANDIDATE':
            if spec['domain'] == 'numeric':
                _, holdout = split_examples(spec['rows'])
                answers = result['holdout_predictions']
                checks, scope = len(holdout), 'INDEPENDENT_HELD_OUT_LABELS'
                passed = len(answers) == checks and all(Fraction(a) == Fraction(r['expected']) for a, r in zip(answers, holdout))
            elif spec['domain'] == 'relation':
                edges = spec['relation']
                reach = {n: {n} for n in [spec['start']] + [x for e in edges for x in e]}
                for a, b in edges:
                    reach[a].add(b)
                for middle in tuple(reach):
                    for node in reach:
                        if middle in reach[node]:
                            reach[node].update(reach[middle])
                expected = reach[spec['start']]
                answer = result['answer']
                passed = isinstance(answer, (list, tuple, set)) and set(answer) == expected and len(answer) == len(expected)
                checks, scope = 1, 'INDEPENDENT_TRANSITIVE_CLOSURE'
            else:
                opened, valid = [], True
                for code, key in spec['events']:
                    if code == 'Q':
                        opened.append(key)
                    elif code == 'R' and opened and opened[-1] == key:
                        opened.pop()
                    else:
                        valid = False
                expected = valid and not opened
                passed = equivalent(result['answer'], expected)
                checks, scope = 1, 'INDEPENDENT_Q_R_NESTING_CONTRACT'
        return {'kind': 'COG_VERIFY', 'goal_id': g['id'], 'execution_tick': g['execution']['tick'],
                'workspace_digest': g['decision']['workspace_digest'], 'passed': bool(passed),
                'checks': checks, 'scope': scope}

    def _reflect(self, g):
        choice, success = g['decision']['choice'], g['verification']['passed']
        error = int(success) - choice['probability']
        return {'kind': 'COG_REFLECT', 'goal_id': g['id'], 'verification_tick': g['verification']['tick'],
                'workspace_digest': g['decision']['workspace_digest'], 'domain': g['spec']['domain'],
                'strategy': choice['strategy'], 'success': success, 'cost': choice['cost'],
                'predicted_success': choice['probability'], 'prediction_error': error, 'brier_error': error ** 2,
                'update_basis': 'CHECKED_EXECUTION', 'next_phase': 'FINISH' if success else 'SELECT'}

    @staticmethod
    def _finish(g, success):
        status = ('VALIDATED_ON_HOLDOUT' if g['spec']['domain'] == 'numeric' else 'VERIFIED') if success else 'WITHHOLD'
        result = copy.deepcopy(g['execution']['result']) if success else None
        return {'kind': 'COG_FINISH', 'goal_id': g['id'], 'status': status, 'result': result,
                'reason': 'CHECK_PASSED' if success else 'BUDGET_OR_STRATEGIES_EXHAUSTED',
                'spent': g['budget'] - g['remaining']}

    def _step(self):
        records = self._records()
        goals = replay(records)
        g = next((g for g in goals.values() if g['status'] == 'ACTIVE'), None)
        if g is None:
            observations = [r for r in records if r['kind'] == 'COG_REFLECT']
            checkpoints = [r for r in records if r['kind'] == 'COG_CONSOLIDATE']
            latest = next(reversed(goals.values()), None) if goals else None
            if (not observations or latest['mode'] in {'no_memory', 'no_consolidation'}
                    or checkpoints and checkpoints[-1]['through_tick'] >= observations[-1]['tick']):
                return None
            stats = consolidated_stats(records)
            event = {'kind': 'COG_CONSOLIDATE', 'through_tick': observations[-1]['tick'], 'stats': stats,
                     'model_digest': fingerprint(stats), 'raw_evidence_preserved': True}
        elif g['phase'] == 'SELECT':
            event = self._select(g, records)
        elif g['phase'] == 'EXECUTE':
            event = self._execute(g)
        elif g['phase'] == 'VERIFY':
            event = self._verify(g)
        elif g['phase'] == 'REFLECT':
            event = self._reflect(g)
        else:
            event = self._finish(g, True)
        return self.kernel._append(event)

    def run(self, max_steps=20):
        if type(max_steps) is not int or not 1 <= max_steps <= 1000:
            raise ValueError('COGNITIVE_STEP_BUDGET')
        events = []
        for _ in range(max_steps):
            result = self._transaction(self._step)
            if result is None:
                break
            events.append(result)
        return events

    def snapshot(self):
        self.kernel.verify_state()
        records = self._records()
        goals = replay(records)
        stats = consolidated_stats(records)
        return {'schema': 'yado.causal_metacognition.v2',
                'goals': {str(k): {key: value for key, value in g.items()
                                  if key not in {'spec', 'decision', 'execution', 'verification'}} for k, g in goals.items()},
                'all_observations': stats, 'workspace_capacity': WORKSPACE_CAPACITY,
                'recent_observation_capacity': RECENT_OBSERVATIONS,
                'consciousness_assessment': 'NOT_ESTABLISHED', 'controller_authorship': 'ASSISTANT',
                'self_model_origin': 'VERIFIED_EXECUTION_OUTCOMES', 'background_process_running': False}
