"""Finite, evidence-gated runtime materialization from durable failures.

The host authors the adapter grammar and gates. The kernel selects a recorded
deficit and emits a reusable module from an inherited exact fitting algorithm.
Hivemind transports the objective; it cannot supply code or a PASS receipt.
"""
from __future__ import annotations

import copy
from functools import lru_cache
import json
import os
from pathlib import Path
import random
import secrets
import subprocess
import sys

from .archive import canonical, file_sha, sha
from .kernel import ROOT, encode, fingerprint

SCHEMA = 'yado.hivemind.runtime-evolution.v1'
REQUEST = {'schema': SCHEMA, 'objective': 'repair_native_source_failures'}
PREFIX = 'native_materialized_'
COST = 4


def normalize_request(value):
    if value != REQUEST:
        raise ValueError('RUNTIME_EVOLUTION_TYPED_OBJECTIVE_REQUIRED')
    return dict(REQUEST)


def select_candidate(goals, excluded=(), parents=()):
    from .native_mechanism import build_candidate, inferred_degree, synthesize
    solved = {fingerprint(g['spec']['training']) for g in goals.values()
              if g['status'] == 'VALIDATED_ON_HOLDOUT' and g['spec']['domain'] == 'native_source'}
    options = []
    for g in goals.values():
        if (g['status'] != 'WITHHOLD' or g['mode'] != 'full'
                or g['spec']['domain'] != 'native_source'
                or 'native_evolved_v2' not in g['attempted']):
            continue
        training = g['spec']['training']
        if fingerprint(training) in solved:
            continue
        if any(synthesize(parent, training).get('source') for parent in parents):
            continue
        degree = inferred_degree(training)
        if degree is None:
            continue
        candidate = build_candidate(degree)
        if candidate['source_sha256'] in excluded:
            continue
        options.append({'goal_id': g['id'], 'training_digest': fingerprint(training),
                        'max_degree': degree, 'candidate': candidate})
    return min(options, key=lambda x: (x['max_degree'], x['goal_id'])) if options else None


def states(records):
    """Projection only; causal validation is performed by cognitive replay."""
    result = {}
    for r in records:
        if r['kind'] == 'COG_RUNTIME_PROPOSE':
            result[r['tick']] = {'proposal': r, 'evaluation': None, 'admission': None, 'revoked': False}
        elif r['kind'] in {'COG_RUNTIME_EVALUATE', 'COG_RUNTIME_ADMIT', 'COG_RUNTIME_REVOKE'}:
            item = result.get(r.get('proposal_tick'))
            if item is None:
                raise ValueError('RUNTIME_EVOLUTION_UNKNOWN_PROPOSAL')
            key = {'COG_RUNTIME_EVALUATE': 'evaluation', 'COG_RUNTIME_ADMIT': 'admission',
                   'COG_RUNTIME_REVOKE': 'revoked'}[r['kind']]
            item[key] = True if key == 'revoked' else r
    return result


def active_candidates(records):
    return {PREFIX + s['proposal']['selection']['candidate']['source_sha256'][:16]:
            s['proposal']['selection']['candidate'] for s in states(records).values()
            if s['admission'] is not None and not s['revoked']}


def strategy_candidate(records, strategy, training):
    from .native_mechanism import synthesize
    candidate = active_candidates(records).get(strategy)
    if candidate is None:
        raise ValueError('RUNTIME_MECHANISM_NOT_ADMITTED')
    result = synthesize(candidate, training)
    if not result.get('source'):
        raise ValueError('RUNTIME_MECHANISM_WITHHOLD:' + str(result.get('reason')))
    return {**result, 'runtime_mechanism_sha256': candidate['source_sha256']}


def evaluation_passed(row):
    try:
        regression, trial, memory, audit = [row[k] for k in ('regression', 'trial', 'memory', 'audit')]
        return bool(
            regression['status'] == 'PASS' and regression['returncode'] == 0
            and type(regression['tests_run']) is int and regression['tests_run'] >= 262
            and regression['tests_run'] == regression['expected_tests'] == regression['passed_tests']
            and regression['source_unchanged'] is True and not regression['failures']
            and not regression['errors'] and not regression['skipped']
            and regression['candidate_integration_test_passed'] is True
            and regression['trial_candidate_sha256'] == row['candidate_sha256']
            and trial['candidate_sha256'] == row['candidate_sha256']
            and trial['passed'] is True and trial['fresh_cases'] >= 4
            and len(trial['cases']) == trial['fresh_cases']
            and all(case['passed'] is True and case['predictions'] == case['expected']
                    and len(case['expected']) == 4 for case in trial['cases'])
            and trial['negative_cases'] >= 5 and trial['historical_retry_passed'] is True
            and len(trial['negative_rejections']) == trial['negative_cases']
            and all(value is True for value in trial['negative_rejections'])
            and trial['fresh_gain_over_parent'] >= 1
            and memory['passed'] is True and memory['goals'] > 0
            and audit['pass'] is True
            and audit['full_kernel']['status'] == 'PASS'
            and audit['full_kernel']['returncode'] == 0 and audit['full_kernel']['findings'] == []
        )
    except (KeyError, TypeError):
        return False


def replay_event(record, past, goals):
    """Reject invented selection, missing gates and activation before admission."""
    from .hivemind import _key
    from .native_mechanism import validate_candidate
    body = {k: v for k, v in record.items() if k not in {'tick', 'event_hash'}}
    current = states(past)
    if any(g['status'] == 'ACTIVE' for g in goals.values()):
        raise ValueError('RUNTIME_EVOLUTION_REQUIRES_IDLE_COGNITION')
    if body['kind'] == 'COG_RUNTIME_PROPOSE':
        required = {'kind', 'workspace_id', 'issue_id', 'request', 'implementation_identity',
                    'selection', 'parents', 'memory_digest', 'generator_authorship', 'algorithm_origin'}
        key = _key(body['workspace_id'], body['issue_id'])
        normalize_request(body['request'])
        if set(body) != required or any((s['proposal']['workspace_id'], s['proposal']['issue_id']) == key
                                        for s in current.values()):
            raise ValueError('RUNTIME_EVOLUTION_PROPOSAL_CONTRACT')
        parents = list(active_candidates(past).values())
        excluded = [x['source_sha256'] for x in parents]
        if (body['parents'] != parents or body['selection'] != select_candidate(goals, excluded, parents)
                or body['memory_digest'] != fingerprint(goals)
                or body['generator_authorship'] != 'ASSISTANT_AUTHORIZED_BY_USER'
                or body['algorithm_origin'] != 'INHERITED_FITTER_KERNEL_SELECTED_AST_MATERIALIZATION'):
            raise ValueError('RUNTIME_EVOLUTION_SELECTION_PROVENANCE')
        if body['selection']:
            validate_candidate(body['selection']['candidate'])
        return
    item = current.get(body.get('proposal_tick'))
    if item is None or item['proposal']['selection'] is None:
        raise ValueError('RUNTIME_EVOLUTION_PROPOSAL_REQUIRED')
    proposal = item['proposal']
    candidate = proposal['selection']['candidate']
    if body['kind'] == 'COG_RUNTIME_EVALUATE':
        if (item['evaluation'] is not None or item['admission'] is not None
                or set(body) != {'kind', 'proposal_tick', 'candidate_sha256', 'implementation_identity',
                                 'regression', 'trial', 'memory', 'audit', 'passed'}
                or body['candidate_sha256'] != candidate['source_sha256']
                or body['implementation_identity'] != proposal['implementation_identity']
                or body['memory']['goals_digest'] != fingerprint(goals)
                or body['memory']['goals'] != len(goals)
                or canonical(body['trial']) != _expected_trial(canonical(candidate),
                    canonical(goals[proposal['selection']['goal_id']]['spec']),
                    proposal['selection']['goal_id'], body['trial']['fresh_seed'], canonical(proposal['parents']))
                or body['passed'] is not evaluation_passed(body)):
            raise ValueError('RUNTIME_EVOLUTION_EVALUATION_CONTRACT')
    elif body['kind'] == 'COG_RUNTIME_ADMIT':
        expected = {'kind': 'COG_RUNTIME_ADMIT', 'proposal_tick': proposal['tick'],
                    'evaluation_tick': (item['evaluation'] or {}).get('tick'),
                    'implementation_identity': proposal['implementation_identity'],
                    'candidate_sha256': candidate['source_sha256'],
                    'strategy': PREFIX + candidate['source_sha256'][:16], 'cost': COST}
        if (body != expected or item['admission'] is not None
                or not evaluation_passed(item['evaluation'] or {})
                or item['evaluation']['memory']['goals_digest'] != fingerprint(goals)):
            raise ValueError('RUNTIME_EVOLUTION_ADMISSION_WITHOUT_GATES')
    elif body['kind'] == 'COG_RUNTIME_REVOKE':
        if (item['admission'] is None or item['revoked']
                or body != {'kind': 'COG_RUNTIME_REVOKE', 'proposal_tick': proposal['tick'],
                            'reason': 'EXPLICIT_ROLLBACK'}):
            raise ValueError('RUNTIME_EVOLUTION_ROLLBACK_CONTRACT')
    else:
        raise ValueError('RUNTIME_EVOLUTION_UNKNOWN_EVENT')


def verify_implementations(records, current_implementation):
    upgrades = [r for r in records if r['kind'] == 'IMPLEMENTATION_UPGRADE']
    implementation = upgrades[0]['predecessor_implementation_digest'] if upgrades else current_implementation
    for record in records:
        if record['kind'] == 'IMPLEMENTATION_UPGRADE':
            implementation = record['implementation_digest']
        elif record['kind'] in {'COG_RUNTIME_PROPOSE', 'COG_RUNTIME_EVALUATE', 'COG_RUNTIME_ADMIT'}:
            if record.get('implementation_identity') != implementation:
                raise ValueError('RUNTIME_EVOLUTION_IMPLEMENTATION_PROVENANCE')


def trial_report(kernel, proposal, seed):
    """New coefficients and held-out inputs are drawn only after module freeze."""
    from .cognitive import CognitiveLoop, replay
    old = replay(CognitiveLoop(kernel)._records())[proposal['selection']['goal_id']]
    return json.loads(_expected_trial(canonical(proposal['selection']['candidate']),
                                    canonical(old['spec']), old['id'], seed, canonical(proposal['parents'])))


@lru_cache(maxsize=32)
def _expected_trial(candidate_json, spec_json, goal_id, seed, parents_json):
    """Replay the actual finite probes once per immutable proof in each process."""
    from .native_mechanism import synthesize, validate_candidate
    from .native_binding import synthesize as parent_synthesize
    from yado_active_native_learning_v1 import execute_source
    candidate, old_spec = json.loads(candidate_json), json.loads(spec_json)
    if type(seed) is not str or len(seed) != 48 or any(c not in '0123456789abcdef' for c in seed):
        raise ValueError('RUNTIME_EVOLUTION_FRESH_SEED_CONTRACT')
    validate_candidate(candidate)
    rng = random.Random(seed)
    degree = candidate['profile']['max_degree']
    cases = []
    for d in range(degree + 1):
        for repeat in range(4 if degree == 0 else 2):
            coefficients = [rng.randint(10, 29) * rng.choice((-1, 1)) for _ in range(d + 1)]
            key = 'fresh_value_' + str(d) + str(repeat)
            def expected(x):
                return sum(c * x ** power for power, c in enumerate(coefficients))
            training = [{'input': {key: x}, 'expected': expected(x)} for x in (-3, -2, -1, 0, 1, 2, 3)]
            result = synthesize(candidate, copy.deepcopy(training))
            inputs = [{key: x} for x in (-11, -7, 8, 13)]
            answers = [expected(x[key]) for x in inputs]
            predictions = execute_source(result, inputs) if result.get('source') else []
            cases.append({'degree': d, 'coefficients': coefficients, 'training': training,
                          'program_sha256': result.get('source_sha256'), 'inputs': inputs,
                          'expected': answers, 'predictions': predictions, 'passed': predictions == answers})
    sample = [{'input': {'x': x}, 'expected': 10 - x * x} for x in range(-3, 4)]
    negatives = [sample[:2], sample + [copy.deepcopy(sample[0])],
                 [{'input': {'x': bool(x % 2)}, 'expected': 1} for x in range(7)],
                 [{'input': {'x': x, 'y': x}, 'expected': x} for x in range(7)],
                 [{'input': {'x': x}, 'expected': x * (x - 1) // 2} for x in range(7)],
                 [{'input': {'x': x}, 'expected': x ** (degree + 1) + 17} for x in range(7)]]
    rejected = [not synthesize(candidate, copy.deepcopy(rows)).get('source') for rows in negatives]
    result = synthesize(candidate, copy.deepcopy(old_spec['training']))
    validation = old_spec['validation']
    historical = bool(result.get('source')) and execute_source(
        result, [r['input'] for r in validation]) == [r['expected'] for r in validation]
    # One independent fresh case must establish a gain over the actual old route.
    target = cases[-1]
    try:
        baseline = parent_synthesize(copy.deepcopy(target['training']))
        parent_predictions = execute_source(baseline, target['inputs'])
    except (ValueError, KeyError, TypeError):
        parent_predictions = []
    active_parent_predictions = []
    for parent in json.loads(parents_json):
        previous = synthesize(parent, copy.deepcopy(target['training']))
        active_parent_predictions.append(execute_source(previous, target['inputs']) if previous.get('source') else [])
    gain = int(target['passed'] and parent_predictions != target['expected']
               and all(predictions != target['expected'] for predictions in active_parent_predictions))
    return canonical({'candidate_sha256': candidate['source_sha256'], 'fresh_seed': seed,
            'fresh_cases': len(cases), 'negative_cases': len(negatives),
            'cases': cases, 'negative_rejections': rejected,
            'historical_goal_id': goal_id, 'historical_retry_passed': bool(historical),
            'fresh_gain_over_parent': gain, 'parent_predictions': parent_predictions,
            'active_parent_predictions': active_parent_predictions,
            'passed': all(x['passed'] for x in cases) and all(rejected) and bool(historical) and bool(gain)})


class RuntimeEvolution:
    def __init__(self, kernel):
        from .cognitive import CognitiveLoop
        self.kernel, self.loop = kernel, CognitiveLoop(kernel)

    def _idle(self):
        from .cognitive import replay
        if (any(g['status'] == 'ACTIVE' for g in replay(self.loop._records()).values())
                or any(s['status'] == 'ACTIVE' for s in self.kernel.development_snapshot()['sessions'].values())
                or any(s['status'] == 'ACTIVE' for s in self.kernel.autonomy_snapshot()['sessions'].values())):
            raise ValueError('RUNTIME_EVOLUTION_REQUIRES_IDLE_SESSIONS')

    def propose(self, workspace_id, issue_id, request):
        from .cognitive import replay
        from .hivemind import _key
        key, request = _key(workspace_id, issue_id), normalize_request(request)
        def operation():
            self._idle()
            records = self.loop._records()
            existing = [s['proposal'] for s in states(records).values()
                        if (s['proposal']['workspace_id'], s['proposal']['issue_id']) == key]
            if existing:
                return existing[0]
            goals = replay(records)
            if any(g['status'] == 'ACTIVE' for g in goals.values()):
                raise ValueError('RUNTIME_EVOLUTION_REQUIRES_IDLE_COGNITION')
            parents = list(active_candidates(records).values())
            excluded = [x['source_sha256'] for x in parents]
            return self.kernel._append({'kind': 'COG_RUNTIME_PROPOSE',
                'workspace_id': workspace_id, 'issue_id': issue_id, 'request': request,
                'implementation_identity': self.kernel.implementation_identity,
                'selection': select_candidate(goals, excluded, parents), 'parents': parents,
                'memory_digest': fingerprint(goals),
                'generator_authorship': 'ASSISTANT_AUTHORIZED_BY_USER',
                'algorithm_origin': 'INHERITED_FITTER_KERNEL_SELECTED_AST_MATERIALIZATION'})
        return self.loop._transaction(operation)

    def evaluate(self, proposal_tick, output):
        """Run fixed commands locally; no imported verdict or arbitrary command."""
        from .cognitive import replay
        from .generation import retained_memory
        self.kernel.verify_state()
        self._idle()
        item = states(self.loop._records())[proposal_tick]
        if item['evaluation']:
            return item['evaluation']
        proposal = item['proposal']
        if proposal['selection'] is None:
            raise ValueError('RUNTIME_EVOLUTION_NO_CANDIDATE')
        if proposal['implementation_identity'] != self.kernel.implementation_identity:
            raise ValueError('RUNTIME_EVOLUTION_IMPLEMENTATION_CHANGED')
        output = Path(output).resolve()
        output.mkdir(parents=True, exist_ok=False)
        candidate = proposal['selection']['candidate']
        candidate_path = output / 'candidate.json'
        candidate_path.write_text(json.dumps(candidate, sort_keys=True, indent=2) + '\n')
        (output / 'candidate.py').write_text(candidate['source'])
        trial = trial_report(self.kernel, proposal, secrets.token_hex(24))
        (output / 'trial.typed.json').write_text(encode(trial) + '\n')
        birth = output / 'regression-birth'
        with (output / 'build.log').open('w') as log:
            subprocess.run([sys.executable, '-m', 'successor', 'build', '--output', str(birth)],
                           cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, check=True, timeout=300)
        env = dict(os.environ, YADO_RUNTIME_CANDIDATE=str(candidate_path),
                   YADO_RUNTIME_CANDIDATE_SHA256=candidate['source_sha256'])
        report_path = output / 'regression.json'
        with (output / 'regression-command.log').open('w') as log:
            completed = subprocess.run([sys.executable, 'runtime/yado_full_regression_v1.py',
                '--manifest', str(birth / 'manifest.json'), '--output', str(report_path)],
                cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT, timeout=1800)
        report = json.loads(report_path.read_text())
        if json.loads(candidate_path.read_text()) != candidate:
            raise ValueError('RUNTIME_EVOLUTION_TRIAL_CANDIDATE_CHANGED')
        regression = {k: report.get(k) for k in ('status', 'tested_commit', 'tests_run', 'expected_tests',
                                               'source_unchanged', 'failures', 'errors', 'skipped')}
        regression.update(returncode=completed.returncode, passed_tests=len(report.get('passed_ids', [])),
                          trial_candidate_sha256=candidate['source_sha256'], report_sha256=file_sha(report_path),
                          source_digest=sha(canonical(report.get('source_sha256', {})).encode()),
                          candidate_integration_test_passed=any(name.endswith(
                              'NativeMechanismTests.test_regression_uses_the_frozen_runtime_candidate_when_provided')
                              for name in report.get('passed_ids', [])))
        self.kernel._check_sources()
        memory = retained_memory(self.kernel)
        (output / 'memory.typed.json').write_text(encode(memory) + '\n')
        goals = replay(self.loop._records())
        memory_summary = {'passed': memory['passed'], 'goals': memory['goals'],
                          'goals_digest': fingerprint(goals), 'evidence_digest': fingerprint(memory)}
        audit = self.kernel.parent.audit()
        generated = [ROOT / 'audits/yado-full-kernel-audit-v1-report.json',
                     ROOT / 'audits/yado-full-kernel-audit-v1-summary.md']
        originals = {path: path.read_bytes() if path.exists() else None for path in generated}
        try:
            with (output / 'kernel-audit.log').open('w') as log:
                audited = subprocess.run([sys.executable, 'runtime/yado_full_kernel_audit_v1.py'],
                    cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, timeout=300)
            full_audit = json.loads(generated[0].read_text())
            (output / 'kernel-audit.json').write_bytes(generated[0].read_bytes())
            audit['full_kernel'] = {'status': full_audit['status'], 'findings': full_audit['findings'],
                                    'returncode': audited.returncode, 'report_sha256': file_sha(generated[0])}
        finally:
            for path, original in originals.items():
                if original is None:
                    path.unlink(missing_ok=True)
                else:
                    path.write_bytes(original)
        body = {'kind': 'COG_RUNTIME_EVALUATE', 'proposal_tick': proposal_tick,
                'candidate_sha256': candidate['source_sha256'],
                'implementation_identity': self.kernel.implementation_identity,
                'regression': regression, 'trial': trial, 'memory': memory_summary, 'audit': audit}
        body['passed'] = evaluation_passed(body)
        def record():
            self._idle()
            if fingerprint(replay(self.loop._records())) != memory_summary['goals_digest']:
                raise ValueError('RUNTIME_EVOLUTION_MEMORY_CHANGED_DURING_GATES')
            return self.kernel._append(body)
        return self.loop._transaction(record)

    def admit(self, proposal_tick):
        from .cognitive import replay
        def operation():
            self._idle()
            item = states(self.loop._records())[proposal_tick]
            if item['admission']:
                return item['admission']
            if not evaluation_passed(item['evaluation'] or {}):
                raise ValueError('RUNTIME_EVOLUTION_ADMISSION_WITHOUT_GATES')
            if (self.kernel.implementation_identity != item['proposal']['implementation_identity']
                    or item['evaluation']['memory']['goals_digest'] != fingerprint(replay(self.loop._records()))):
                raise ValueError('RUNTIME_EVOLUTION_STALE_GATES')
            candidate = item['proposal']['selection']['candidate']
            return self.kernel._append({'kind': 'COG_RUNTIME_ADMIT', 'proposal_tick': proposal_tick,
                'evaluation_tick': item['evaluation']['tick'], 'candidate_sha256': candidate['source_sha256'],
                'implementation_identity': self.kernel.implementation_identity,
                'strategy': PREFIX + candidate['source_sha256'][:16], 'cost': COST})
        return self.loop._transaction(operation)

    def rollback(self, proposal_tick):
        def operation():
            self._idle()
            item = states(self.loop._records())[proposal_tick]
            if item['revoked']:
                return {'status': 'ALREADY_REVOKED'}
            if not item['admission']:
                raise ValueError('RUNTIME_EVOLUTION_NOT_ACTIVE')
            return self.kernel._append({'kind': 'COG_RUNTIME_REVOKE', 'proposal_tick': proposal_tick,
                                        'reason': 'EXPLICIT_ROLLBACK'})
        return self.loop._transaction(operation)
