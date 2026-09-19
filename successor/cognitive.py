"""Event-sourced, bounded metacognition over real inherited YADO solvers.

The controller is assistant-authored. Its empirical self-model is learned from
checked executions. Nothing here measures or asserts phenomenal consciousness.
"""
from __future__ import annotations

import copy
from collections import OrderedDict
from fractions import Fraction
import marshal
import math
import sys
from threading import RLock
import time

from .archive import canonical, sha
from .kernel import decode, encode, equivalent, fingerprint
from yado_active_native_learning_v1 import validate_source_goal, source_sha

MODES = ('full', 'no_memory', 'no_self_model', 'no_consolidation', 'fixed_max')
STRATEGIES = {
    'numeric': (('polynomial_1', 1), ('polynomial_2', 2), ('polynomial_3', 3)),
    'relation': (('native_logic', 1), ('native_router', 2)),
    'events': (('native_thinking', 1), ('native_router', 2)),
    'native_source': (('reuse_verified_source', 1), ('native_v2', 1), ('native_v3', 2), ('native_v4', 3)),
    'library_discovery': (('catalog_v6', 4),),
}
RECENT_OBSERVATIONS = 16
WORKSPACE_CAPACITY = 2
SOURCE_MEMORY_CAPACITY = 16


class _UncacheableReplay(Exception):
    pass


def _cache_normalize(value):
    """Snapshot exact supported types, without TypedJSON's whole-value node cap.

    Every input tuple is tagged, so its contents cannot impersonate Fraction's
    tag. marshal is used only to encode these builtins, never to load code/data.
    """
    kind = type(value)
    if value is None or kind in (str, int, bool):
        return value
    if kind is float:
        if not math.isfinite(value):
            raise _UncacheableReplay
        return value
    if kind is Fraction:
        return ('fraction', value.numerator, value.denominator)
    if kind is tuple:
        return ('tuple', tuple(_cache_normalize(v) for v in value))
    if kind is list:
        return [_cache_normalize(v) for v in value]
    if kind is dict:
        return {_cache_normalize(k): _cache_normalize(v) for k, v in value.items()}
    raise _UncacheableReplay


def _cache_restore(value):
    if type(value) is list:
        return [_cache_restore(v) for v in value]
    if type(value) is dict:
        return {_cache_restore(k): _cache_restore(v) for k, v in value.items()}
    if type(value) is tuple:
        if value[0] == 'fraction':
            return Fraction(value[1], value[2])
        return tuple(_cache_restore(v) for v in value[1])
    return value


def _replay_context(snapshot):
    records = snapshot[1] if type(snapshot) is tuple else snapshot
    if any(type(r) is not dict or type(r.get('kind')) is not str for r in records):
        raise _UncacheableReplay
    kinds = {r['kind'] for r in records}
    context = [MODES, STRATEGIES, WORKSPACE_CAPACITY, SOURCE_MEMORY_CAPACITY]
    # replay's two filesystem-dependent proofs must remain live on cache hits.
    if 'COG_ACTIVATE_NATIVE_SYNTHESIS' in kinds:
        from .native_binding import activation
        context.append(activation())
    if any(kind.startswith('COG_RUNTIME_') for kind in kinds):
        from .archive import file_sha
        from .native_mechanism import ROOT, DONOR_PATH
        context.append(file_sha(ROOT / DONOR_PATH))
    return _cache_normalize(context)


def _retained_size(value):
    """Conservative retained object size; shared objects count once per entry."""
    pending, seen, total = [value], set(), 0
    while pending:
        item = pending.pop()
        if id(item) in seen:
            continue
        seen.add(id(item))
        total += sys.getsizeof(item)
        if type(item) is dict:
            pending.extend(item.keys())
            pending.extend(item.values())
        elif type(item) in (list, tuple):
            pending.extend(item)
        elif type(item) is Fraction:
            pending.extend((item.numerator, item.denominator))
    return total


class _ReplayCache:
    """Disposable, process-local LRU; never an admission or persistence source."""
    def __init__(self, max_entries=128, max_bytes=256 * 1024 * 1024):
        self.max_entries, self.max_bytes = max_entries, max_bytes
        self.enabled = True
        self._lock = RLock()
        self.clear()

    def clear(self):
        with self._lock:
            self._entries = OrderedDict()
            self._bytes = self.hits = self.misses = 0

    def get(self, key):
        with self._lock:
            entry = self._entries.get(key)
            if entry is None:
                self.misses += 1
                return None
            self._entries.move_to_end(key)
            self.hits += 1
            return entry[0]

    def put(self, key, value):
        size = sys.getsizeof(key) + _retained_size(value) + 512
        if self.max_entries < 1 or size > self.max_bytes:
            return
        with self._lock:
            previous = self._entries.pop(key, None)
            if previous is not None:
                self._bytes -= previous[1]
            while self._entries and (len(self._entries) >= self.max_entries
                                     or self._bytes + size > self.max_bytes):
                _, (_, removed_size) = self._entries.popitem(last=False)
                self._bytes -= removed_size
            self._entries[key] = (value, size)
            self._bytes += size

    def info(self):
        with self._lock:
            return {'entries': len(self._entries), 'bytes': self._bytes,
                    'hits': self.hits, 'misses': self.misses,
                    'max_entries': self.max_entries, 'max_bytes': self.max_bytes}


_REPLAY_CACHE = _ReplayCache()


def _integer(value, bound):
    return type(value) is int and abs(value) <= bound


def validate_goal(spec):
    if not isinstance(spec, dict) or spec.get('domain') not in STRATEGIES:
        raise ValueError('SUPPORTED_GOAL_DOMAINS: ' + ', '.join(STRATEGIES))
    spec = copy.deepcopy(spec)
    domain = spec['domain']
    if domain == 'native_source':
        return validate_source_goal(spec)
    if domain == 'library_discovery':
        if spec != {'domain': 'library_discovery', 'objective': 'html_xml_parser'}:
            raise ValueError('LIBRARY_GOAL_SUPPORTS_HTML_XML_PARSER_ONLY')
        return spec
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
    key = observation.get('context', observation['domain']) + '/' + observation['strategy']
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


def goal_context(spec):
    if spec['domain'] != 'native_source':
        return spec['domain']
    row = spec['training'][0]
    signature = [[k, type(v).__name__] for k, v in sorted(row['input'].items())]
    return 'native_source:' + fingerprint([signature, type(row['expected']).__name__])


def learned_source(records, goal):
    """Legacy newest-source rule, retained for existing journal provenance."""
    return next(iter(learned_sources(records, goal, limit=1)), None)


def learned_sources(records, goal, limit=SOURCE_MEMORY_CAPACITY):
    """Bounded, newest-first distinct programs admitted in this type context."""
    if goal['mode'] == 'no_memory' or goal['spec']['domain'] != 'native_source':
        return []
    context = goal_context(goal['spec'])
    sources, seen = [], set()
    for record in reversed(records):
        result = record.get('result') or {}
        if (record['kind'] == 'COG_FINISH' and record['status'] == 'VALIDATED_ON_HOLDOUT'
                and result.get('source_context') == context and 'source' in result
                and result['source_sha256'] not in seen):
            sources.append(record)
            seen.add(result['source_sha256'])
            if len(sources) == limit:
                break
    return sources


def _fits_training(predictions, training):
    return (isinstance(predictions, list) and len(predictions) == len(training)
            and all(equivalent(value, row['expected']) for value, row in zip(predictions, training)))


def recall_source(sources, training, execute):
    """Select on training only; neither holdout rows nor query inputs enter here.

    One strategy unit permits at most SOURCE_MEMORY_CAPACITY program probes.
    Probe evidence records the actual search work separately from that unit.
    """
    if not sources:
        raise ValueError('NO_ADMITTED_SOURCE_MEMORY')
    evidence = {'version': 2, 'selection_inputs': 'TRAINING_ONLY',
                'training_digest': fingerprint(training), 'candidate_limit': SOURCE_MEMORY_CAPACITY,
                'probes': []}
    for prior in sources:
        probe = {'finish_tick': prior['tick'], 'source_sha256': prior['result']['source_sha256']}
        try:
            probe['predictions'] = execute(prior['result'], [row['input'] for row in training])
        except Exception as error:
            probe['error_type'] = type(error).__name__
        evidence['probes'].append(probe)
        if _fits_training(probe.get('predictions'), training):
            return prior, evidence
    # Preserve the previous failed-reuse path so the loop can reflect on the
    # failure and try a grammar extension within its remaining budget.
    return sources[0], evidence


def replay_recalled_source(records, goal, result):
    evidence = result.get('memory_retrieval')
    if evidence is None:
        return learned_source(records, goal)
    invalid = 'COGNITIVE_NATIVE_SOURCE_REUSE_PROVENANCE'
    if (not isinstance(evidence, dict) or type(evidence.get('version')) is not int
            or evidence['version'] != 2 or evidence.get('selection_inputs') != 'TRAINING_ONLY'
            or evidence.get('training_digest') != fingerprint(goal['spec']['training'])
            or evidence.get('candidate_limit') != SOURCE_MEMORY_CAPACITY):
        raise ValueError(invalid)
    sources, probes = learned_sources(records, goal), evidence.get('probes')
    if not isinstance(probes, list) or not 1 <= len(probes) <= len(sources):
        raise ValueError(invalid)
    for index, probe in enumerate(probes):
        prior = sources[index]
        if (not isinstance(probe, dict) or probe.get('finish_tick') != prior['tick']
                or probe.get('source_sha256') != prior['result']['source_sha256']
                or set(probe) not in ({'finish_tick', 'source_sha256', 'predictions'},
                                      {'finish_tick', 'source_sha256', 'error_type'})
                or 'error_type' in probe and not isinstance(probe['error_type'], str)):
            raise ValueError(invalid)
        if _fits_training(probe.get('predictions'), goal['spec']['training']):
            if index != len(probes) - 1:
                raise ValueError(invalid)
            return prior
    if len(probes) != len(sources):
        raise ValueError(invalid)
    return sources[0]


def available_strategies(goal, records):
    from .native_binding import STRATEGY, COST, active
    from .runtime_evolution import active_candidates, COST as runtime_cost
    strategies = STRATEGIES[goal['spec']['domain']]
    if goal['spec']['domain'] == 'native_source' and active(records):
        strategies += ((STRATEGY, COST),)
    if goal['spec']['domain'] == 'native_source':
        row = goal['spec']['training'][0]
        if len(row['input']) == 1 and type(next(iter(row['input'].values()))) is int and type(row['expected']) is int:
            strategies += tuple((name, runtime_cost) for name in active_candidates(records))
    return [(s, c) for s, c in strategies
            if s != 'reuse_verified_source' or learned_source(records, goal) is not None]


def replay(records):
    """Memoize successful replay by a complete typed, immutable content key.

    Claimed event hashes are only fields in that key, never a substitute for
    bodies. Unsupported, cyclic or oversized values use the original validator.
    """
    if not _REPLAY_CACHE.enabled or type(records) not in (list, tuple):
        return _replay_uncached(records)
    try:
        snapshot = _cache_normalize(records)
        context = _replay_context(snapshot)
        # Version 2 has no object-reference memoization: equal content has equal
        # bytes regardless of alias sharing between separately decoded records.
        key = marshal.dumps((snapshot, context), 2)
        if len(key) > _REPLAY_CACHE.max_bytes:
            return _replay_uncached(records)
        cached = _REPLAY_CACHE.get(key)
        if cached is not None:
            return copy.deepcopy(cached)
        private_records = _cache_restore(snapshot)
    except (_UncacheableReplay, RecursionError, ValueError, OSError):
        return _replay_uncached(records)
    # Failures propagate and are never cached. The private snapshot also keeps
    # subsequent caller mutations out of both the proof and its stored result.
    result = _replay_uncached(private_records)
    try:
        unchanged = marshal.dumps(_replay_context(snapshot), 2) == marshal.dumps(context, 2)
    except (_UncacheableReplay, RecursionError, ValueError, OSError):
        unchanged = False
    if unchanged:
        _REPLAY_CACHE.put(key, result)
    return copy.deepcopy(result)


def _replay_uncached(records):
    """Validate cross-event causal links while rebuilding disposable projections."""
    goals, past = {}, []
    for r in records:
        kind = r['kind']
        if kind.startswith('COG_RUNTIME_'):
            from .runtime_evolution import replay_event
            replay_event(r, past, goals)
        elif kind == 'COG_ACTIVATE_NATIVE_SYNTHESIS':
            from .native_binding import activation, active
            body = {k: v for k, v in r.items() if k not in {'tick', 'event_hash'}}
            if (body != activation() or active(past)
                    or any(g['status'] == 'ACTIVE' for g in goals.values())):
                raise ValueError('COGNITIVE_NATIVE_BINDING_PROVENANCE')
        elif kind == 'COG_GOAL':
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
                allowed = dict(available_strategies(g, past))
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
                result = r['result']
                if g['spec']['domain'] == 'native_source' and result['status'] == 'CANDIDATE':
                    if (source_sha(result['source']) != result['source_sha256']
                            or result['source_context'] != goal_context(g['spec'])):
                        raise ValueError('COGNITIVE_NATIVE_SOURCE_INTEGRITY')
                    strategy = g['decision']['choice']['strategy']
                    if strategy in {'native_v2', 'native_v3', 'native_v4', 'native_evolved_v2'}:
                        # Journal hashes and stored prediction labels cannot
                        # attest executable provenance. Re-emit from the original
                        # training partition before admitting source to memory.
                        try:
                            if strategy == 'native_evolved_v2':
                                from .native_binding import synthesize
                                generated = synthesize(g['spec']['training'])
                            else:
                                from yado_active_native_learning_v1 import synthesize_source
                                generated = synthesize_source(g['spec']['training'], strategy)
                        except Exception as error:
                            raise ValueError('COGNITIVE_NATIVE_SOURCE_EMISSION_PROVENANCE') from error
                        if result['source'] != generated.get('source'):
                            raise ValueError('COGNITIVE_NATIVE_SOURCE_EMISSION_PROVENANCE')
                    if g['decision']['choice']['strategy'].startswith('native_materialized_'):
                        from .runtime_evolution import strategy_candidate
                        generated = strategy_candidate(past, g['decision']['choice']['strategy'], g['spec']['training'])
                        if (result['source'] != generated['source'] or result.get('runtime_mechanism_sha256')
                                != generated['runtime_mechanism_sha256']):
                            raise ValueError('COGNITIVE_RUNTIME_MECHANISM_EXECUTION_PROVENANCE')
                    if g['decision']['choice']['strategy'] == 'reuse_verified_source':
                        prior = replay_recalled_source(past, g, result)
                        if (prior is None or result.get('reused_finish_tick') != prior['tick']
                                or result['source_sha256'] != prior['result']['source_sha256']):
                            raise ValueError('COGNITIVE_NATIVE_SOURCE_REUSE_PROVENANCE')
                g['remaining'] -= g['decision']['choice']['cost']
                g['attempted'].append(g['decision']['choice']['strategy'])
                g.update(phase='VERIFY', execution=r)
            elif kind == 'COG_VERIFY':
                if (g['phase'] != 'VERIFY' or r['execution_tick'] != g['execution']['tick']
                        or type(r['passed']) is not bool
                        or r['workspace_digest'] != g['decision']['workspace_digest']):
                    raise ValueError('COGNITIVE_VERIFICATION_CAUSAL_LINK')
                # A valid chain proves stored bytes, not the truth of a PASS.
                # Recheck local oracles; replay external proof bindings offline.
                try:
                    expected = CognitiveLoop(None)._verify(g, recorded_verification=r)
                    fields = ('passed', 'checks', 'scope', 'evidence')
                    if fingerprint({k: r[k] for k in fields}) != fingerprint({k: expected[k] for k in fields}):
                        raise ValueError('mismatched verification')
                except (KeyError, TypeError, ValueError, OverflowError) as error:
                    raise ValueError('COGNITIVE_VERIFICATION_RESULT_MISMATCH') from error
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
                if r.get('context', r['domain']) != goal_context(g['spec']):
                    raise ValueError('COGNITIVE_REFLECTION_CONTEXT')
                g['phase'] = 'FINISH' if r['success'] else 'SELECT'
            elif kind == 'COG_FINISH':
                if g['phase'] not in {'FINISH', 'SELECT'}:
                    raise ValueError('COGNITIVE_PREMATURE_FINISH')
                if g['phase'] == 'FINISH':
                    expected_status = 'VALIDATED_ON_HOLDOUT' if g['spec']['domain'] in {'numeric', 'native_source'} else 'VERIFIED'
                else:
                    affordable = [(s, c) for s, c in available_strategies(g, past)
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


def _stored_library_verification(candidate, record):
    """Check persisted proof consistency; never repeat an external observation.

    A frozen HTTP receipt cannot prove that PyPI is still unchanged. Replay binds
    its filename/hash to the frozen bundle and preserves that historical scope.
    Recorded network failures remain failures, without requiring a live network.
    """
    from yado_autonomous_external_library_discovery_v5 import sha_json
    evidence = record['evidence']
    if record['scope'] == 'LIBRARY_VALIDATION_ERROR':
        if (set(evidence) != {'error_type', 'error'}
                or not all(type(evidence[k]) is str for k in evidence)):
            raise ValueError('LIBRARY_FAILURE_PROOF_CONTRACT')
        return False, 0, 'LIBRARY_VALIDATION_ERROR', evidence
    bundle, proof = candidate['bundle'], evidence['proof']
    if (sha_json(bundle) != candidate['bundle_sha256']
            or proof['filename'] != bundle['filename'] or proof['sha256'] != bundle['artifact_sha256']
            or type(proof['matched']) is not bool or proof['selection_data_used'] is not False
            or not isinstance(proof['source'], dict)):
        raise ValueError('LIBRARY_FROZEN_PROOF_MISMATCH')
    passed = proof['matched'] and bundle['artifact_sha256'] == candidate['artifact']['expected_sha256']
    if (evidence['passed'] is not passed or type(evidence['checks']) is not int or evidence['checks'] != 1
            or evidence['scope'] != 'SEPARATE_PYPI_SIMPLE_AFTER_BUNDLE_FREEZE'):
        raise ValueError('LIBRARY_VERIFICATION_PROOF_MISMATCH')
    return passed, 1, 'SEPARATE_PYPI_SIMPLE_AFTER_BUNDLE_FREEZE', evidence


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

    def activate_native_synthesis(self):
        from .native_binding import activation
        def admit():
            records = self._records()
            previous = next((r for r in records if r['kind'] == 'COG_ACTIVATE_NATIVE_SYNTHESIS'), None)
            if previous is not None:
                return previous
            if (any(g['status'] == 'ACTIVE' for g in replay(records).values())
                    or any(s['status'] == 'ACTIVE' for s in self.kernel.development_snapshot()['sessions'].values())
                    or any(s['status'] == 'ACTIVE' for s in self.kernel.autonomy_snapshot()['sessions'].values())):
                raise ValueError('NATIVE_BINDING_REQUIRES_IDLE_KERNEL')
            return self.kernel._append(activation())
        return self._transaction(admit)

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
        for strategy, cost in available_strategies(g, records):
            if strategy in g['attempted'] or cost > g['remaining']:
                continue
            item = stats.get(goal_context(g['spec']) + '/' + strategy, {})
            n = item.get('successes', 0) + item.get('failures', 0)
            probability = (item.get('successes', 0) + 1) / (n + 2)
            uncertainty = math.sqrt(probability * (1 - probability) / (n + 3))
            score = probability + .1 * uncertainty - .04 * cost
            if strategy == 'reuse_verified_source':
                # Reusing an admitted program avoids regeneration, but it must
                # still pass this goal's independent examples before acceptance.
                score += .15
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
            if spec['domain'] == 'native_source':
                if choice['strategy'] == 'reuse_verified_source':
                    prior, retrieval = recall_source(learned_sources(self._records(), g),
                                                     spec['training'], parent.execute_native_source)
                    candidate = copy.deepcopy(prior['result'])
                    candidate['reused_finish_tick'] = prior['tick']
                    candidate['memory_retrieval'] = retrieval
                elif choice['strategy'] == 'native_evolved_v2':
                    from .native_binding import synthesize
                    candidate = synthesize(spec['training'])
                elif choice['strategy'].startswith('native_materialized_'):
                    from .runtime_evolution import strategy_candidate
                    # Historical retention replays the mechanism available at
                    # this decision, including after an explicit rollback.
                    history = [r for r in self._records() if r['tick'] < g['decision']['tick']]
                    candidate = strategy_candidate(history, choice['strategy'], spec['training'])
                else:
                    candidate = parent.native_source_candidate(spec['training'], choice['strategy'])
                def predict(rows):
                    return parent.execute_native_source(candidate, [r['input'] for r in rows])
                result = {**candidate, 'status': 'CANDIDATE', 'source_context': goal_context(spec),
                          'training_predictions': predict(spec['training']),
                          'validation_predictions': predict(spec['validation']),
                          'predictions': predict(spec['queries'])}
            elif spec['domain'] == 'library_discovery':
                result = {**parent.native_library_candidate(), 'status': 'CANDIDATE'}
            elif spec['domain'] == 'numeric':
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

    def _verify(self, g, *, recorded_verification=None):
        spec, result = g['spec'], g['execution']['result']
        passed, checks, scope = False, 0, 'NO_CANDIDATE'
        evidence = {}
        if result['status'] == 'CANDIDATE':
            if spec['domain'] == 'native_source':
                checks = len(spec['validation'])
                scope = 'INDEPENDENT_VALIDATION_LABELS_AFTER_SOURCE_FREEZE'
                passed = source_sha(result['source']) == result['source_sha256']
                for name in ('training', 'validation'):
                    predictions = result[name + '_predictions']
                    passed = passed and len(predictions) == len(spec[name]) and all(
                        equivalent(a, row['expected']) for a, row in zip(predictions, spec[name]))
                evidence = {'source_sha256': result['source_sha256']}
            elif spec['domain'] == 'library_discovery':
                if recorded_verification is not None:
                    passed, checks, scope, evidence = _stored_library_verification(result, recorded_verification)
                else:
                    try:
                        evidence = self.kernel.parent.verify_native_library(result)
                        passed, checks, scope = evidence['passed'], evidence['checks'], evidence['scope']
                    except Exception as error:
                        evidence = {'error_type': type(error).__name__, 'error': str(error)}
                        scope = 'LIBRARY_VALIDATION_ERROR'
            elif spec['domain'] == 'numeric':
                _, holdout = split_examples(spec['rows'])
                answers = result['holdout_predictions']
                checks, scope = len(holdout), 'INDEPENDENT_HELD_OUT_LABELS'
                passed = len(answers) == checks and all(not isinstance(a, bool) and Fraction(a) == Fraction(r['expected'])
                                                       for a, r in zip(answers, holdout))
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
                passed = (isinstance(answer, (list, tuple, set)) and all(type(n) in (int, str) for n in answer)
                          and set(answer) == expected and len(answer) == len(expected))
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
                'checks': checks, 'scope': scope, 'evidence': evidence}

    def _reflect(self, g):
        choice, success = g['decision']['choice'], g['verification']['passed']
        error = int(success) - choice['probability']
        return {'kind': 'COG_REFLECT', 'goal_id': g['id'], 'verification_tick': g['verification']['tick'],
                'workspace_digest': g['decision']['workspace_digest'], 'domain': g['spec']['domain'],
                'strategy': choice['strategy'], 'success': success, 'cost': choice['cost'],
                'context': goal_context(g['spec']),
                'predicted_success': choice['probability'], 'prediction_error': error, 'brier_error': error ** 2,
                'update_basis': 'CHECKED_EXECUTION', 'next_phase': 'FINISH' if success else 'SELECT'}

    @staticmethod
    def _finish(g, success):
        status = ('VALIDATED_ON_HOLDOUT' if g['spec']['domain'] in {'numeric', 'native_source'} else 'VERIFIED') if success else 'WITHHOLD'
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
