"""Persistent verified causal dataflow on the successor's single event journal.

The journal is authoritative. Projections, routing statistics and the generated
source registry are rebuilt and causally checked after every restart.
"""
from __future__ import annotations

import copy
import re

from . import capabilities as caps
from .kernel import decode, encode, equivalent, fingerprint

KERNEL_ID = 'YADO_UNIFIED_CAUSAL_GRAPH_V1'
RELEASE = {'VERIFIED', 'VALIDATED_ON_HOLDOUT'}
TERMINAL = RELEASE | {'WITHHOLD', 'BLOCKED', 'EXECUTED_UNVERIFIED'}


def valid_path(path):
    return (isinstance(path, list) and 1 <= len(path) <= 12
            and all(type(x) is str and 0 < len(x) <= 80 or type(x) is int and 0 <= x <= 2048 for x in path))


def validate_spec(spec):
    if not isinstance(spec, dict) or set(spec) - {'goal', 'origin', 'priority', 'mode', 'nodes', 'provenance'}:
        raise ValueError('GRAPH_SPEC_SCHEMA')
    spec = copy.deepcopy(spec)
    spec.setdefault('origin', 'user'); spec.setdefault('priority', 0); spec.setdefault('mode', 'full')
    spec.setdefault('provenance', {})
    if (not isinstance(spec.get('goal'), str) or not 1 <= len(spec['goal']) <= 500
            or spec['origin'] not in ('user', 'experience', 'internal') or spec['mode'] not in ('full', 'no_memory')
            or type(spec['priority']) is not int or not -100 <= spec['priority'] <= 100
            or not isinstance(spec.get('nodes'), list) or not 1 <= len(spec['nodes']) <= 32
            or not isinstance(spec['provenance'], dict) or len(encode(spec).encode()) > 1024 * 1024):
        raise ValueError('GRAPH_BOUNDS_OR_SCHEMA')
    ids = set()
    for n in spec['nodes']:
        if (not isinstance(n, dict) or set(n) - {'id', 'capability', 'input', 'budget', 'needs', 'bindings', 'expect'}
                or not isinstance(n.get('id'), str) or not re.fullmatch('[a-zA-Z][a-zA-Z0-9_-]{0,63}', n['id'])
                or n['id'] in ids or n.get('capability') not in caps.STRATEGIES or not isinstance(n.get('input'), dict)):
            raise ValueError('GRAPH_NODE_SCHEMA')
        ids.add(n['id'])
        n.setdefault('budget', 6); n.setdefault('needs', []); n.setdefault('bindings', []); n.setdefault('expect', None)
        if (type(n['budget']) is not int or not 1 <= n['budget'] <= 30 or not isinstance(n['needs'], list)
                or any(type(x) is not str for x in n['needs']) or not isinstance(n['bindings'], list)
                or len(n['bindings']) > 32 or len(n['needs']) > 32):
            raise ValueError('GRAPH_NODE_BUDGET_OR_DEPENDENCIES')
        targets = []
        for b in n['bindings']:
            if (not isinstance(b, dict) or set(b) != {'from', 'path', 'to'} or type(b['from']) is not str
                    or not valid_path(b['path']) or not valid_path(b['to'])):
                raise ValueError('GRAPH_BINDING_SCHEMA')
            try:
                caps.at(n['input'], b['to'])
            except (KeyError, IndexError, TypeError, ValueError) as e:
                raise ValueError('GRAPH_BINDING_TARGET_MISSING') from e
            target = tuple(b['to'])
            if any(target[:len(p)] == p or p[:len(target)] == target for p in targets):
                raise ValueError('GRAPH_OVERLAPPING_BINDINGS')
            targets.append(target)
            n['needs'].append(b['from'])
        n['needs'] = sorted(set(n['needs']))
        if n['expect'] is not None and (not isinstance(n['expect'], dict)
                or set(n['expect']) != {'path', 'equals'} or not valid_path(n['expect']['path'])):
            raise ValueError('GRAPH_EXPECTATION_SCHEMA')
        if not n['bindings']:
            caps.validate_input(n['capability'], n['input'])
    pending = {n['id']: set(n['needs']) for n in spec['nodes']}
    if any(not deps <= ids for deps in pending.values()):
        raise ValueError('GRAPH_UNKNOWN_DEPENDENCY')
    done = set()
    while pending:
        ready = {key for key, deps in pending.items() if deps <= done}
        if not ready:
            raise ValueError('GRAPH_CYCLE')
        done |= ready
        pending = {key: deps for key, deps in pending.items() if key not in ready}
    return spec


def resolved_input(g, n):
    value = copy.deepcopy(n['spec']['input'])
    dependencies = {}
    for name in n['spec']['needs']:
        parent = g['nodes'][name]
        if parent['status'] not in RELEASE:
            raise ValueError('GRAPH_DEPENDENCY_NOT_VERIFIED')
        dependencies[name] = parent['terminal_tick']
    for b in n['spec']['bindings']:
        result = copy.deepcopy(caps.at(g['nodes'][b['from']]['result'], b['path']))
        target = value if len(b['to']) == 1 else caps.at(value, b['to'][:-1])
        target[b['to'][-1]] = result
    return caps.validate_input(n['spec']['capability'], value), dependencies


def proposals(g, n, stats):
    model = {} if g['spec']['mode'] == 'no_memory' else stats
    items = []
    for strategy, cost in caps.STRATEGIES[n['spec']['capability']]:
        if strategy in n['attempted'] or cost > n['remaining']:
            continue
        item = model.get(n['spec']['capability'] + '/' + strategy, {})
        count = item.get('successes', 0) + item.get('failures', 0)
        probability = (item.get('successes', 0) + 1) / (count + 2)
        items.append({'strategy': strategy, 'cost': cost, 'observations': count,
                      'probability': probability, 'score': probability - .04 * cost})
    items.sort(key=lambda p: (-p['score'], p['cost'], p['strategy']))
    return items[:3], fingerprint(model)


def observation(n):
    key = n['spec']['capability'] + '/' + n['decision']['choice']['strategy']
    return key, key + ':' + fingerprint({'input': n['decision']['input'], 'expect': n['spec']['expect']})


def next_node(g):
    for n in g['nodes'].values():
        if n['status'] not in TERMINAL and n['phase'] != 'SELECT':
            return n
    for n in g['nodes'].values():
        if n['status'] in TERMINAL:
            continue
        dependencies = [g['nodes'][key]['status'] for key in n['spec']['needs']]
        if any(s in TERMINAL - RELEASE for s in dependencies) or all(s in RELEASE for s in dependencies):
            return n
    return None


def finish_status(g):
    statuses = {n['status'] for n in g['nodes'].values()}
    if not statuses <= TERMINAL:
        raise ValueError('GRAPH_PREMATURE_FINISH')
    if statuses & {'WITHHOLD', 'BLOCKED'}:
        return 'WITHHOLD'
    if 'EXECUTED_UNVERIFIED' in statuses:
        return 'EXECUTED_UNVERIFIED'
    return 'VALIDATED_ON_HOLDOUT' if 'VALIDATED_ON_HOLDOUT' in statuses else 'VERIFIED'


def block_reason(g, n, stats):
    blocked = [key for key in n['spec']['needs'] if g['nodes'][key]['status'] in TERMINAL - RELEASE]
    if blocked:
        return {'status': 'BLOCKED', 'reason': 'DEPENDENCY_WITHOUT_VERIFIED_RESULT', 'blocked_by': blocked}
    try:
        resolved_input(g, n)
    except (ValueError, TypeError, KeyError, IndexError):
        return {'status': 'BLOCKED', 'reason': 'BOUND_INPUT_CONTRACT', 'blocked_by': []}
    if not proposals(g, n, stats)[0]:
        return {'status': 'WITHHOLD', 'reason': 'BUDGET_OR_STRATEGIES_EXHAUSTED', 'blocked_by': []}
    return None


def replay(records):
    goals, stats, seen, registry = {}, {}, set(), {}
    for r in records:
        kind = r['kind']
        if kind == 'GRAPH_OPEN':
            spec = validate_spec(r['spec'])
            if r['tick'] in goals or r['spec_digest'] != fingerprint(spec):
                raise ValueError('GRAPH_OPEN_INTEGRITY')
            goals[r['tick']] = {'id': r['tick'], 'spec': spec, 'status': 'ACTIVE', 'nodes': {
                n['id']: {'spec': n, 'status': 'PENDING', 'phase': 'SELECT', 'remaining': n['budget'],
                          'attempted': [], 'decision': None, 'execution': None, 'verification': None,
                          'result': None, 'terminal_tick': None} for n in spec['nodes']}}
            continue
        g = goals.get(r.get('graph_id'))
        if g is None or g['status'] != 'ACTIVE':
            raise ValueError('GRAPH_CAUSAL_LINK')
        if kind == 'GRAPH_STOP':
            g['status'] = 'STOPPED'
            continue
        if kind == 'GRAPH_FINISH':
            if r['status'] != finish_status(g):
                raise ValueError('GRAPH_FINISH_STATUS')
            g['status'] = r['status']
            continue
        n = g['nodes'].get(r.get('node_id'))
        if n is None or n['status'] in TERMINAL or next_node(g) is not n:
            raise ValueError('GRAPH_NODE_CAUSAL_LINK')
        if kind == 'GRAPH_BLOCK':
            expected = block_reason(g, n, stats)
            if n['phase'] != 'SELECT' or expected is None or any(r[k] != v for k, v in expected.items()):
                raise ValueError('GRAPH_BLOCK_CONTRACT')
            n.update(status=r['status'], phase='DONE', terminal_tick=r['tick'])
        elif kind == 'GRAPH_SELECT':
            value, dependencies = resolved_input(g, n)
            choices, model_digest = proposals(g, n, stats)
            if (n['phase'] != 'SELECT' or not choices or r['choice'] != choices[0] or r['proposals'] != choices
                    or r['self_model_digest'] != model_digest or not equivalent(r['input'], value)
                    or r['input_digest'] != fingerprint(value) or r['dependencies'] != dependencies):
                raise ValueError('GRAPH_SELECTION_INTEGRITY')
            n.update(phase='EXECUTE', decision=r, execution=None, verification=None)
        elif kind == 'GRAPH_EXECUTE':
            if (n['phase'] != 'EXECUTE' or r['decision_tick'] != n['decision']['tick']
                    or r['result_digest'] != fingerprint(r['result'])):
                raise ValueError('GRAPH_EXECUTION_INTEGRITY')
            n['remaining'] -= n['decision']['choice']['cost']
            n['attempted'].append(n['decision']['choice']['strategy'])
            n.update(phase='VERIFY', execution=r)
        elif kind == 'GRAPH_VERIFY':
            if n['phase'] != 'VERIFY' or r['execution_tick'] != n['execution']['tick']:
                raise ValueError('GRAPH_VERIFICATION_CAUSAL_LINK')
            expected = caps.verify(n['spec']['capability'], n['decision']['input'], n['execution']['result'], n['spec']['expect'], registry)
            if not equivalent(r['verification'], expected):
                raise ValueError('GRAPH_VERIFICATION_INTEGRITY')
            n.update(phase='REFLECT', verification=r)
        elif kind == 'GRAPH_REFLECT':
            if n['phase'] != 'REFLECT' or r['verification_tick'] != n['verification']['tick']:
                raise ValueError('GRAPH_REFLECTION_CAUSAL_LINK')
            key, oid = observation(n)
            passed = n['verification']['verification']['passed']
            counted = passed is not None and oid not in seen
            if r['observation_id'] != oid or r['counted'] is not counted:
                raise ValueError('GRAPH_OBSERVATION_INTEGRITY')
            if counted:
                seen.add(oid)
                item = stats.setdefault(key, {'successes': 0, 'failures': 0, 'cost': 0})
                item['successes' if passed else 'failures'] += 1
                item['cost'] += n['decision']['choice']['cost']
            if passed is not False:
                cap = n['spec']['capability']
                status = ('VALIDATED_ON_HOLDOUT' if cap in ('numeric', 'source_synthesis') else 'VERIFIED') if passed else 'EXECUTED_UNVERIFIED'
                n.update(status=status, phase='DONE', result=n['execution']['result'], terminal_tick=r['tick'])
                if cap == 'source_synthesis' and passed:
                    result = n['result']
                    registry.setdefault(result['source_sha256'], {'source': result['source'], 'admission_tick': r['tick'],
                        'origin_graph': g['id'], 'verification_scope': n['verification']['verification']['scope']})
            else:
                n.update(phase='SELECT')
        else:
            raise ValueError('UNKNOWN_GRAPH_EVENT')
    return {'goals': goals, 'self_model': stats, 'observations': seen, 'learned_capabilities': registry}


class CausalGraph:
    def __init__(self, kernel):
        self.kernel = kernel

    def _records(self):
        records = []
        for row in self.kernel.db.execute('SELECT tick,event_hash,body FROM events ORDER BY tick'):
            body = decode(row['body'])
            if str(body.get('kind', '')).startswith('GRAPH_'):
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

    def submit(self, spec):
        spec = validate_spec(spec)
        def append():
            if sum(g['status'] == 'ACTIVE' for g in replay(self._records())['goals'].values()) >= 64:
                raise ValueError('ACTIVE_GRAPH_BUDGET')
            return self.kernel._append({'kind': 'GRAPH_OPEN', 'spec': spec, 'spec_digest': fingerprint(spec)})['tick']
        return self._transaction(append)

    def stop(self, graph_id):
        def append():
            g = replay(self._records())['goals'].get(graph_id)
            if g is None:
                raise ValueError('UNKNOWN_GRAPH')
            if g['status'] != 'ACTIVE':
                return {'graph_id': graph_id, 'status': g['status']}
            return self.kernel._append({'kind': 'GRAPH_STOP', 'graph_id': graph_id, 'reason': 'USER_STOP'})
        return self._transaction(append)

    def _execute(self, n, registry):
        try:
            result = caps.execute(self.kernel, n['spec']['capability'], n['decision']['input'], n['decision']['choice']['strategy'], registry)
            encode(result)
            return result
        except Exception as error:
            return {'status': 'ERROR', 'error_type': type(error).__name__, 'error': str(error)}

    def _step(self):
        state = replay(self._records())
        active = [g for g in state['goals'].values() if g['status'] == 'ACTIVE']
        active.sort(key=lambda g: ({'user': 0, 'experience': 1, 'internal': 2}[g['spec']['origin']], -g['spec']['priority'], g['id']))
        if not active:
            return None
        g = active[0]
        n = next_node(g)
        if n is None:
            event = {'kind': 'GRAPH_FINISH', 'graph_id': g['id'], 'status': finish_status(g)}
        else:
            event = {'graph_id': g['id'], 'node_id': n['spec']['id']}
            if n['phase'] == 'SELECT':
                blocked = block_reason(g, n, state['self_model'])
                if blocked:
                    event.update(kind='GRAPH_BLOCK', **blocked)
                else:
                    value, dependencies = resolved_input(g, n)
                    choices, digest = proposals(g, n, state['self_model'])
                    event.update(kind='GRAPH_SELECT', input=value, input_digest=fingerprint(value), dependencies=dependencies,
                                 choice=choices[0], proposals=choices, self_model_digest=digest,
                                 historical_sources=self.kernel.archive.search(n['spec']['capability'], 3))
            elif n['phase'] == 'EXECUTE':
                result = self._execute(n, state['learned_capabilities'])
                event.update(kind='GRAPH_EXECUTE', decision_tick=n['decision']['tick'], result=result, result_digest=fingerprint(result))
            elif n['phase'] == 'VERIFY':
                event.update(kind='GRAPH_VERIFY', execution_tick=n['execution']['tick'], verification=caps.verify(
                    n['spec']['capability'], n['decision']['input'], n['execution']['result'], n['spec']['expect'], state['learned_capabilities']))
            else:
                _, oid = observation(n)
                passed = n['verification']['verification']['passed']
                event.update(kind='GRAPH_REFLECT', verification_tick=n['verification']['tick'], observation_id=oid,
                             counted=passed is not None and oid not in state['observations'])
        return self.kernel._append(event)

    def run(self, max_steps=20):
        if type(max_steps) is not int or not 1 <= max_steps <= 1000:
            raise ValueError('GRAPH_STEP_BUDGET')
        events = []
        for _ in range(max_steps):
            event = self._transaction(self._step)
            if event is None:
                break
            events.append(event)
        return events

    def snapshot(self):
        integrity = self.kernel.verify_state()
        state = replay(self._records())
        state['observation_count'] = len(state.pop('observations'))
        return {**state, 'kernel_id': KERNEL_ID, 'integrity': integrity,
                'supported_capabilities': list(caps.STRATEGIES), 'controller_authorship': 'ASSISTANT',
                'self_model_origin': 'DEDUPLICATED_CHECKED_LOCAL_EXECUTIONS',
                'background_process_running': False, 'consciousness_established': False}
