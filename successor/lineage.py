"""Durable consecutive capacity extensions in a disclosed polynomial grammar.

The host authors this controller and the finite composition grammar. The kernel
chooses an existing deficit, emits/gates a module, uses it through normal
cognition, and constructs the next challenge from its actual successful program.
This is not an architectural generation or open-ended algorithm invention.
"""
from __future__ import annotations

import copy
from fractions import Fraction
from functools import lru_cache
import json
from pathlib import Path
import secrets

from .archive import canonical
from .kernel import decode, encode, fingerprint

SCHEMA = 'yado.consecutive-runtime-lineage.v1'
POLICY = 'polynomial_composition_from_verified_program_v1'
BUDGET = 30
REQUEST = {'schema': SCHEMA, 'objective': 'consecutive_verified_capacity_extensions',
           'generations': 3}


def normalize_request(value):
    if (type(value) is not dict or set(value) != set(REQUEST)
            or value.get('schema') != SCHEMA or value.get('objective') != REQUEST['objective']
            or type(value.get('generations')) is not int or not 3 <= value['generations'] <= 5):
        raise ValueError('LINEAGE_TYPED_BOUNDED_OBJECTIVE_REQUIRED')
    return dict(value)


def records(kernel):
    return [{**decode(row['body']), 'tick': row['tick'], 'event_hash': row['event_hash']}
            for row in kernel.db.execute('SELECT tick,event_hash,body FROM events ORDER BY tick')]


def ref(record):
    return {'tick': record['tick'], 'event_hash': record['event_hash']}


def body(record):
    return {k: v for k, v in record.items() if k not in {'tick', 'event_hash'}}


@lru_cache(maxsize=24)
def _goals(encoded):
    from .cognitive import replay as cognitive_replay
    return cognitive_replay(decode(encoded))


def goals_at(past):
    # Cache by actual bytes, never by an unverified claimed digest alone.
    return _goals(encode([r for r in past if r.get('kind', '').startswith('COG_')]))


@lru_cache(maxsize=8)
def _sessions_idle(encoded, identity):
    from .development import replay as development_replay
    from .autonomy import replay as autonomy_replay
    past = decode(encoded)
    development = development_replay([r for r in past if r.get('kind', '').startswith(('COG_', 'DEV_'))])
    autonomy = autonomy_replay(past, identity)
    return not any(s['status'] == 'ACTIVE' for s in [*development.values(), *autonomy.values()])


def selection(past):
    from .runtime_evolution import active_candidates, select_candidate, SELECTION_POLICY
    parents = list(active_candidates(past).values())
    return select_candidate(goals_at(past), [p['source_sha256'] for p in parents],
                            parents, policy=SELECTION_POLICY)


def polynomial_values(training, inputs):
    """Independent exact Lagrange oracle, without the inherited fitter/emitter."""
    key = next(iter(training[0]['input']))
    points = [(row['input'][key], row['expected']) for row in training]
    if len({x for x, _ in points}) != len(points):
        raise ValueError('LINEAGE_ORACLE_DUPLICATE_INPUT')
    answer = []
    for row in inputs:
        x, value = row[key], Fraction(0)
        for i, (xi, yi) in enumerate(points):
            term = Fraction(yi)
            for j, (xj, _) in enumerate(points):
                if i != j:
                    term *= Fraction(x - xj, xi - xj)
            value += term
        if value.denominator != 1:
            raise ValueError('LINEAGE_ORACLE_NONINTEGER')
        answer.append(int(value))
    return answer


def sealed_queries(spec):
    validation = spec['validation']
    if polynomial_values(spec['training'], [r['input'] for r in validation]) != [
            r['expected'] for r in validation]:
        raise ValueError('LINEAGE_ORACLE_VALIDATION_MISMATCH')
    return polynomial_values(spec['training'], [r['input'] for r in spec['queries']])


def initial_plan(past, session):
    selected = selection(past)
    if selected is None:
        return None
    spec = copy.deepcopy(goals_at(past)[selected['goal_id']]['spec'])
    return {'kind': 'LINEAGE_PLAN', 'lineage_id': session['start']['tick'],
            'source_goal_id': selected['goal_id'], 'spec': spec,
            'query_oracle': sealed_queries(spec), 'oracle_basis': 'EXACT_INTERPOLATION_AND_SEALED_VALIDATION',
            'selection_digest': fingerprint(selected)}


@lru_cache(maxsize=24)
def _challenge(encoded_finish, encoded_spec):
    from .cognitive import validate_goal
    from yado_active_native_learning_v1 import execute_source
    finish, parent_spec = decode(encoded_finish), decode(encoded_spec)
    result = finish['result']
    digest = finish['event_hash']
    a, b = int(digest[:2], 16) % 5 - 2, int(digest[2:4], 16) % 7 - 3
    key = 'lineage_' + digest[:8]
    old_key = next(iter(parent_spec['training'][0]['input']))
    xs = [-3, -2, -1, 0, 1, 2, 3, -6, -4, 4, 6, -9, 11]
    old_inputs = [{old_key: x} for x in xs]
    actual = execute_source(result, old_inputs)
    if actual != polynomial_values(parent_spec['training'], old_inputs):
        raise ValueError('LINEAGE_PARENT_PROGRAM_ORACLE_MISMATCH')
    values = [x * y + a * x + b for x, y in zip(xs, actual)]
    rows = [{'input': {key: x}, 'expected': y} for x, y in zip(xs, values)]
    spec = validate_goal({'domain': 'native_source', 'training': rows[:7],
                          'validation': rows[7:11],
                          'queries': [{'input': r['input']} for r in rows[11:]]})
    return {'spec': spec, 'query_oracle': values[11:],
            'recipe': {'operation': 'x_times_parent_plus_ax_plus_b', 'a': a, 'b': b,
                       'seed_event': ref(finish), 'parent_source_sha256': result['source_sha256'],
                       'parent_input_key': old_key},
            'oracle_basis': 'EXECUTED_PARENT_CROSS_CHECKED_BY_EXACT_INTERPOLATION',
            'data_origin': 'ENDOGENOUS_COMPOSITION_OF_PRECEDING_VERIFIED_PROGRAM'}


def next_challenge(session):
    return {'kind': 'LINEAGE_CHALLENGE', 'lineage_id': session['start']['tick'],
            'parent_generation': ref(session['generations'][-1]),
            **copy.deepcopy(_challenge(encode(session['retry_finish']), encode(session['spec'])))}


def _check_control(session, past):
    from .cognitive import available_strategies
    goal = goals_at(past)[session['control_goal']['tick']]
    prior = [r for r in past if r['tick'] < session['control_goal']['tick']
             and r.get('kind', '').startswith('COG_')]
    routes = available_strategies(goal, prior)
    if (goal['status'] != 'WITHHOLD' or sum(cost for _, cost in routes) > BUDGET
            or set(goal['attempted']) != {name for name, _ in routes}):
        raise ValueError('LINEAGE_CONTROL_DID_NOT_EXHAUST_ALL_ROUTES')


@lru_cache(maxsize=24)
def _query_check(encoded_result, encoded_spec, encoded_expected):
    from yado_active_native_learning_v1 import execute_source
    result, spec, expected = decode(encoded_result), decode(encoded_spec), decode(encoded_expected)
    rows = spec['training'] + spec['validation']
    if execute_source(result, [r['input'] for r in rows]) != [r['expected'] for r in rows]:
        raise ValueError('LINEAGE_PROGRAM_FAILED_LABELLED_REEXECUTION')
    predictions = execute_source(result, [r['input'] for r in spec['queries']])
    if predictions != expected:
        raise ValueError('LINEAGE_PROGRAM_FAILED_SEALED_QUERIES')
    return tuple(predictions)


def generation_body(session, past):
    from .runtime_evolution import active_candidates, evaluation_passed
    proposal, evaluation, admission = [session[k] for k in ('proposal', 'evaluation', 'admission')]
    finish, control = session['retry_finish'], session['control_finish']
    candidate = proposal['selection']['candidate']
    digest = candidate['source_sha256']
    result = finish.get('result') or {}
    goal = goals_at(past)[session['retry_goal']['tick']]
    if (finish['status'] != 'VALIDATED_ON_HOLDOUT'
            or result.get('runtime_mechanism_sha256') != digest
            or goal['decision']['choice']['strategy'] != admission['strategy']
            or active_candidates(past).get(admission['strategy']) != candidate
            or not evaluation_passed(evaluation)):
        raise ValueError('LINEAGE_GENERATION_REQUIRES_ACTUAL_CHILD_USE')
    predictions = list(_query_check(encode(result), encode(session['spec']), encode(session['query_oracle'])))
    return {'kind': 'LINEAGE_GENERATION', 'lineage_id': session['start']['tick'],
            'ordinal': len(session['generations']) + 1,
            'parent_generation': ref(session['generations'][-1]) if session['generations'] else None,
            'control_finish': ref(control), 'proposal': ref(proposal), 'gate_attempt': ref(session['gate']),
            'evaluation': ref(evaluation), 'admission': ref(admission), 'retry_finish': ref(finish),
            'candidate_sha256': digest, 'program_sha256': result['source_sha256'],
            'query_predictions': predictions, 'query_expected': session['query_oracle'],
            'memory_digest_before_gates': proposal['memory_digest'],
            'classification': 'BOUNDED_POLYNOMIAL_RUNTIME_CAPACITY_EXTENSION'}


def replay(all_records, identity=None, implementation=None):
    """Validate the full phase order, every parent and ordinary cognitive child."""
    sessions, active, past = {}, None, []
    current_impl = next((r['predecessor_implementation_digest'] for r in all_records
                         if r.get('kind') == 'IMPLEMENTATION_UPGRADE'), implementation)
    for r in all_records:
        kind, value = r.get('kind', ''), body(r)
        if kind == 'IMPLEMENTATION_UPGRADE':
            current_impl = r['implementation_digest']
        if kind == 'LINEAGE_START':
            from .hivemind import _key
            from .runtime_evolution import active_candidates
            _key(r['workspace_id'], r['issue_id'])
            request = normalize_request(r['request'])
            if (active is not None or any(s['start']['workspace_id'] == r['workspace_id']
                    and s['start']['issue_id'] == r['issue_id'] for s in sessions.values())
                    or any(g['status'] == 'ACTIVE' for g in goals_at(past).values())
                    or not _sessions_idle(encode(past), identity or r['identity'])):
                raise ValueError('LINEAGE_REQUIRES_IDLE_UNIQUE_SESSION')
            expected = {'kind': kind, 'workspace_id': r['workspace_id'], 'issue_id': r['issue_id'],
                        'request': request, 'policy': POLICY, 'identity': identity or r['identity'],
                        'implementation': current_impl or r['implementation'],
                        'predecessor': ref(past[-1]) if past else {'tick': 0, 'event_hash': '0' * 64},
                        'memory_digest': fingerprint(goals_at(past)),
                        'parents_digest': fingerprint(active_candidates(past)), 'task_budget': BUDGET,
                        'gate_attempts_per_generation': 1}
            if value != expected:
                raise ValueError('LINEAGE_START_PROVENANCE')
            active = {'start': r, 'status': 'ACTIVE', 'phase': 'READY', 'generations': []}
            sessions[r['tick']] = active
        elif active is None:
            if kind.startswith('LINEAGE_') or 'lineage_id' in r:
                raise ValueError('LINEAGE_ORPHAN_EVENT')
        else:
            s, phase = active, active['phase']
            if kind.startswith('LINEAGE_') and r.get('lineage_id') != s['start']['tick']:
                raise ValueError('LINEAGE_SESSION_LINK')
            if kind == 'LINEAGE_PLAN' and phase == 'READY':
                if value != initial_plan(past, s):
                    raise ValueError('LINEAGE_SELECTION_PROVENANCE')
                s.update(spec=r['spec'], query_oracle=r['query_oracle'], phase='CONTROL_OPEN')
            elif kind == 'LINEAGE_CHALLENGE' and phase == 'NEXT':
                if len(s['generations']) >= s['start']['request']['generations'] or value != next_challenge(s):
                    raise ValueError('LINEAGE_CHALLENGE_PROVENANCE')
                s.update(spec=r['spec'], query_oracle=r['query_oracle'], phase='CONTROL_OPEN')
            elif kind == 'COG_GOAL' and phase in {'CONTROL_OPEN', 'RETRY_OPEN'}:
                expected = {'kind': kind, 'spec': s['spec'], 'spec_digest': fingerprint(s['spec']),
                            'mode': 'full', 'budget': BUDGET}
                if value != expected:
                    raise ValueError('LINEAGE_OWNED_GOAL_CONTRACT')
                target = 'control' if phase == 'CONTROL_OPEN' else 'retry'
                s[target + '_goal'] = r
                s['phase'] = target.upper()
            elif phase in {'CONTROL', 'RETRY'} and kind in {
                    'COG_DECIDE', 'COG_EXECUTE', 'COG_VERIFY', 'COG_REFLECT', 'COG_FINISH', 'COG_STOP'}:
                target = phase.lower()
                if r.get('goal_id') != s[target + '_goal']['tick'] or 'lineage_id' in r:
                    raise ValueError('LINEAGE_FOREIGN_GOAL')
                if kind in {'COG_FINISH', 'COG_STOP'}:
                    s[target + '_finish'] = r
                    s['phase'] = phase + '_DONE'
            elif kind == 'COG_CONSOLIDATE' and phase in {'CONTROL_DONE', 'RETRY_DONE'}:
                pass
            elif kind == 'COG_RUNTIME_PROPOSE' and phase == 'CONTROL_DONE':
                _check_control(s, past)
                chosen = selection(past)
                issue = s['start']['issue_id'] + '.' + str(s['start']['tick']) + '.' + str(len(s['generations']) + 1)
                if (r['workspace_id'] != s['start']['workspace_id'] or r['issue_id'] != issue
                        or chosen is None or r['selection'] != chosen
                        or goals_at(past)[chosen['goal_id']]['spec'] != s['spec']
                        or r['implementation_identity'] != s['start']['implementation']):
                    raise ValueError('LINEAGE_PROPOSAL_PROVENANCE')
                s.update(proposal=r, phase='PROPOSED')
            elif kind == 'LINEAGE_GATE_ATTEMPT' and phase == 'PROPOSED':
                from .runtime_evolution import _checked_trial_seed
                _checked_trial_seed(r['seed'])
                if value != {'kind': kind, 'lineage_id': s['start']['tick'],
                             'proposal': ref(s['proposal']), 'seed': r['seed'], 'attempt': 1,
                             'predecessor': ref(past[-1])}:
                    raise ValueError('LINEAGE_GATE_ATTEMPT_CONTRACT')
                s.update(gate=r, phase='GATING')
            elif kind == 'COG_RUNTIME_EVALUATE' and phase == 'GATING':
                if (r['proposal_tick'] != s['proposal']['tick']
                        or r['trial']['fresh_seed'] != s['gate']['seed']
                        or ref(past[-1]) != ref(s['gate'])):
                    raise ValueError('LINEAGE_GATE_SEED_OR_PREFIX_CHANGED')
                s.update(evaluation=r, phase='EVALUATED')
            elif kind == 'COG_RUNTIME_ADMIT' and phase == 'EVALUATED':
                from .runtime_evolution import evaluation_passed
                if r['proposal_tick'] != s['proposal']['tick'] or not evaluation_passed(s['evaluation']):
                    raise ValueError('LINEAGE_ADMISSION_CONTRACT')
                s.update(admission=r, phase='RETRY_OPEN')
            elif kind == 'LINEAGE_GENERATION' and phase == 'RETRY_DONE':
                if value != generation_body(s, past):
                    raise ValueError('LINEAGE_GENERATION_PROVENANCE')
                s['generations'].append(r)
                s['phase'] = 'NEXT'
            elif kind == 'LINEAGE_FINISH':
                count = len(s['generations'])
                complete = phase == 'NEXT' and count == s['start']['request']['generations']
                reasons = {'USER_STOP'}
                if complete:
                    reasons.add('TARGET_REACHED')
                if phase == 'READY' and selection(past) is None:
                    reasons.add('NO_SUPPORTED_DEFICIT')
                if phase == 'CONTROL_DONE':
                    finish = s['control_finish']
                    if finish.get('status') != 'WITHHOLD':
                        reasons.add('NO_FAILED_CONTROL')
                    elif selection(past) is None:
                        reasons.add('GRAMMAR_EXHAUSTED')
                if phase == 'EVALUATED' and not s['evaluation']['passed']:
                    reasons.add('GATES_FAILED')
                if phase == 'RETRY_DONE' and s['retry_finish'].get('status') != 'VALIDATED_ON_HOLDOUT':
                    reasons.add('RETRY_FAILED')
                if phase == 'GATING':
                    reasons.add('INTERRUPTED_GATES')
                if phase in {'CONTROL', 'RETRY'} or r.get('reason') not in reasons:
                    raise ValueError('LINEAGE_FINISH_REASON')
                expected = {'kind': kind, 'lineage_id': s['start']['tick'], 'reason': r['reason'],
                            'generations': count,
                            'status': 'COMPLETE' if r['reason'] == 'TARGET_REACHED' else 'WITHHOLD'}
                if value != expected:
                    raise ValueError('LINEAGE_FINISH_CONTRACT')
                s.update(status=r['status'], finish=r, phase='DONE')
                active = None
            else:
                raise ValueError('LINEAGE_UNRELATED_OR_OUT_OF_ORDER_EVENT:' + kind + ':' + phase)
        past.append(r)
    return sessions


class ConsecutiveLineage:
    def __init__(self, kernel):
        from .cognitive import CognitiveLoop
        self.kernel, self.loop = kernel, CognitiveLoop(kernel)

    def snapshot(self):
        self.kernel.verify_state()
        return replay(records(self.kernel), self.kernel.identity, self.kernel.implementation_identity)

    def start(self, workspace_id, issue_id, request):
        from .runtime_evolution import RuntimeEvolution, active_candidates
        from .hivemind import _key
        _key(workspace_id, issue_id)
        request = normalize_request(request)
        def operation():
            prior = records(self.kernel)
            sessions = replay(prior, self.kernel.identity, self.kernel.implementation_identity)
            for session in sessions.values():
                start = session['start']
                if (start['workspace_id'], start['issue_id']) == (workspace_id, issue_id):
                    if start['request'] != request:
                        raise ValueError('LINEAGE_OBJECTIVE_CHANGED')
                    return start['tick']
            RuntimeEvolution(self.kernel)._idle()
            return self.kernel._append({'kind': 'LINEAGE_START', 'workspace_id': workspace_id,
                'issue_id': issue_id, 'request': request, 'policy': POLICY,
                'identity': self.kernel.identity, 'implementation': self.kernel.implementation_identity,
                'predecessor': ref(prior[-1]) if prior else {'tick': 0, 'event_hash': '0' * 64},
                'memory_digest': fingerprint(goals_at(prior)),
                'parents_digest': fingerprint(active_candidates(prior)), 'task_budget': BUDGET,
                'gate_attempts_per_generation': 1})['tick']
        return self.loop._transaction(operation)

    def _append(self, value):
        return self.loop._transaction(lambda: self.kernel._append(value))

    def finish(self, session_id, reason):
        def operation():
            s = replay(records(self.kernel), self.kernel.identity, self.kernel.implementation_identity)[session_id]
            if s['status'] != 'ACTIVE':
                return s['finish']
            return self.kernel._append({'kind': 'LINEAGE_FINISH', 'lineage_id': session_id,
                'reason': reason, 'generations': len(s['generations']),
                'status': 'COMPLETE' if reason == 'TARGET_REACHED' else 'WITHHOLD'})
        return self.loop._transaction(operation)

    def stop(self, session_id):
        s = self.snapshot()[session_id]
        if s['status'] == 'ACTIVE' and s['phase'] in {'CONTROL', 'RETRY'}:
            self.loop.stop(s[s['phase'].lower() + '_goal']['tick'])
        return self.finish(session_id, 'USER_STOP')

    def run(self, session_id, output, *, progress=None):
        """One bounded objective, no per-generation observer choices.

        An interrupted gate attempt is preserved and terminal: resume cannot
        silently reroll a trial or replace a failed full regression.
        """
        import fcntl
        from .runtime_evolution import RuntimeEvolution, REQUEST as EVOLVE_REQUEST
        state_path = self.kernel.db.execute('PRAGMA database_list').fetchone()[2]
        output = Path(output).resolve()
        output.mkdir(parents=True, exist_ok=True)
        with open(state_path + '.lineage.lock', 'a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            for _ in range(80):
                s = self.snapshot()[session_id]
                if progress:
                    progress({'phase': s['phase'], 'generations': len(s['generations']), 'status': s['status']})
                if s['status'] != 'ACTIVE':
                    return s
                phase, evolution = s['phase'], RuntimeEvolution(self.kernel)
                if phase == 'READY':
                    plan = initial_plan(records(self.kernel), s)
                    if plan is None:
                        self.finish(session_id, 'NO_SUPPORTED_DEFICIT')
                    else:
                        self._append(plan)
                elif phase in {'CONTROL_OPEN', 'RETRY_OPEN'}:
                    self.loop.open_goal(s['spec'], budget=BUDGET, mode='full')
                elif phase in {'CONTROL', 'RETRY'}:
                    self.loop.run(100)
                elif phase == 'CONTROL_DONE':
                    if s['control_finish'].get('status') != 'WITHHOLD':
                        self.finish(session_id, 'NO_FAILED_CONTROL')
                    elif selection(records(self.kernel)) is None:
                        self.finish(session_id, 'GRAMMAR_EXHAUSTED')
                    else:
                        issue = s['start']['issue_id'] + '.' + str(session_id) + '.' + str(len(s['generations']) + 1)
                        evolution.propose(s['start']['workspace_id'], issue, EVOLVE_REQUEST)
                elif phase == 'PROPOSED':
                    gate = self._append({'kind': 'LINEAGE_GATE_ATTEMPT', 'lineage_id': session_id,
                        'proposal': ref(s['proposal']), 'seed': secrets.token_hex(24), 'attempt': 1,
                        'predecessor': ref(records(self.kernel)[-1])})
                    destination = output / ('generation-' + str(len(s['generations']) + 1))
                    evolution.evaluate(s['proposal']['tick'], destination, trial_seed=gate['seed'])
                elif phase == 'GATING':
                    self.finish(session_id, 'INTERRUPTED_GATES')
                elif phase == 'EVALUATED':
                    if s['evaluation']['passed']:
                        evolution.admit(s['proposal']['tick'])
                    else:
                        self.finish(session_id, 'GATES_FAILED')
                elif phase == 'RETRY_DONE':
                    if s['retry_finish'].get('status') != 'VALIDATED_ON_HOLDOUT':
                        self.finish(session_id, 'RETRY_FAILED')
                    else:
                        self._append(generation_body(s, records(self.kernel)))
                elif phase == 'NEXT':
                    if len(s['generations']) == s['start']['request']['generations']:
                        self.finish(session_id, 'TARGET_REACHED')
                    else:
                        self._append(next_challenge(s))
                else:
                    raise ValueError('LINEAGE_UNKNOWN_PHASE')
            raise ValueError('LINEAGE_DRIVER_BOUND_EXCEEDED')


def main():
    import argparse
    from .kernel import SuccessorKernel
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('manifest', 'state', 'workspace-id', 'issue-id', 'output'):
        parser.add_argument('--' + name, required=True)
    parser.add_argument('--generations', type=int, default=3)
    args = parser.parse_args()
    kernel = SuccessorKernel(args.manifest, args.state)
    try:
        loop = ConsecutiveLineage(kernel)
        sid = loop.start(args.workspace_id, args.issue_id, {**REQUEST, 'generations': args.generations})
        result = loop.run(sid, args.output, progress=lambda row: print(json.dumps(row), flush=True))
        (Path(args.output) / 'lineage.typed.json').write_text(encode(result) + '\n')
        print(json.dumps({'status': result['status'], 'generations': len(result['generations'])}), flush=True)
    finally:
        kernel.close()


if __name__ == '__main__':
    main()
