"""Observe native attempts on prerequisites of the three recorded user deficits.

The maintainer supplies acceptance examples, never candidate solution source.
These finite tests do not establish live agent dialogue or repository editing.
"""
from __future__ import annotations

import argparse
import ast
import difflib
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'runtime'))
sys.path.insert(0, str(ROOT))
from yado_active_kernel_contract_v1 import active_kernel_identity
from yado_active_native_learning_v1 import validate_source_goal
from successor.kernel import SuccessorKernel, decode
from successor.cognitive import replay
from successor.runtime_evolution import REQUEST, RuntimeEvolution


def save(out, name, value):
    (out / (name + '.json')).write_text(json.dumps(value, sort_keys=True, indent=2) + '\n')
    print('YADO_EVIDENCE ' + json.dumps({'name': name, 'value': value}, sort_keys=True), flush=True)


def fixtures():
    # Reference oracles are used only to construct labelled acceptance examples.
    # No oracle, source, or query answer is passed to a native synthesis call.
    def message(row):
        return json.dumps({'jsonrpc': '2.0', 'id': 1, 'method': 'tools/call',
                           'params': {'name': 'hive_add_comment',
                                      'arguments': {'id': 'YADO-1', 'message': row['message']}}},
                          separators=(',', ':'), ensure_ascii=False)

    def patch(row):
        return ''.join(difflib.unified_diff(row['before'].splitlines(keepends=True),
                       row['after'].splitlines(keepends=True),
                       fromfile='a/target.py', tofile='b/target.py'))

    def function_change(row):
        def functions(source):
            return [ast.dump(node, include_attributes=False) for node in ast.parse(source).body
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))]
        return functions(row['before']) != functions(row['after'])

    messages = [{'message': x} for x in ['ready', 'quoted "value"', 'line\nnext',
                'back\\slash', 'данные', 'tab\there', 'done: "ok"\nещё']]
    patches = [
        {'before': 'x = 1\n', 'after': 'x = 2\n'},
        {'before': 'def f(x):\n    return x\n', 'after': 'def f(x):\n    return x + 1\n'},
        {'before': 'a = 3\nb = 4\n', 'after': 'a = 3\n'},
        {'before': 'flag = False\n', 'after': 'flag = True\n'},
        {'before': 'name = "старое"\n', 'after': 'name = "новое"\n'},
        {'before': 'a = 9\n', 'after': 'a = 9\nb = 10\n'},
        {'before': 'def f(x):\n    return x * 2\n', 'after': 'def f(x):\n    return x * 3\n'},
    ]
    def code(digest, expression):
        return 'PACK_DIGEST = ' + repr(digest) + '\ndef route(x):\n    return ' + expression + '\n'
    pairs = [('a', 'b', 'x', 'x'), ('c', 'c', 'x + 1', 'x + 2'),
             ('d', 'e', 'x * 2', 'x * 2'), ('f', 'g', 'x - 1', 'x - 2'),
             ('h', 'i', 'x == 2', 'x == 2'), ('j', 'k', 'x + 3', 'x + 4'),
             ('l', 'm', 'x % 2', 'x % 2')]
    changes = [{'before': code(a, x), 'after': code(b, y)} for a, b, x, y in pairs]
    tasks = []
    for name, deficit, inputs, oracle in [
        ('mcp_comment_serialization', 'LIVE_AGENT_COMMUNICATION_ADAPTER', messages, message),
        ('unified_patch_emission', 'REPOSITORY_EDIT_EXECUTE_ADAPTER', patches, patch),
        ('function_ast_change_detection', 'NATIVE_ALGORITHM_NOVELTY', changes, function_change),
    ]:
        spec = {'domain': 'native_source',
                'training': [{'input': row, 'expected': oracle(row)} for row in inputs[:3]],
                'validation': [{'input': row, 'expected': oracle(row)} for row in inputs[3:5]],
                'queries': [{'input': row} for row in inputs[5:]]}
        validate_source_goal(spec)
        tasks.append({'name': name, 'parent_deficit': deficit, 'spec': spec,
                      'observer_query_expected': [oracle(row) for row in inputs[5:]],
                      'task_scope': 'NECESSARY_COMPONENT_PROBE_NOT_COMPLETE_CAPABILITY',
                      'acceptance_examples_authorship': 'MAINTAINER',
                      'solution_source_supplied': False})
    return tasks


def journal(kernel):
    return [dict(row) for row in kernel.db.execute(
        'SELECT tick,previous_hash,body,event_hash FROM events ORDER BY tick')]


def goal_summary(kernel):
    goals = kernel.cognitive_snapshot()['goals']
    return {str(key): {k: g[k] for k in ('id', 'status', 'attempted', 'budget', 'remaining', 'result')}
            for key, g in goals.items()}


def main(out, preflight=False):
    tasks = fixtures()
    if preflight:
        print(json.dumps({'fixture_contract': 'PASS', 'task_count': len(tasks)}))
        return
    out.mkdir(parents=True, exist_ok=False)
    save(out, 'summary', {'status': 'WITHHOLD_INCOMPLETE_RUN'})
    identity = active_kernel_identity(ROOT)
    previous = ROOT / 'experience/development/20260919-native-repositories/unresolved_development_request.json'
    save(out, 'request', {'previous_request': json.loads(previous.read_text()),
                        'previous_request_sha256': hashlib.sha256(previous.read_bytes()).hexdigest(),
                        'tasks': tasks, 'run_id': os.getenv('GITHUB_RUN_ID', 'LOCAL'),
                        'tested_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
                        'prior_binary_state_restored': False,
                        'prior_deficit_observations_imported': True,
                        'candidate_implementation_authored_by_assistant': False})
    birth = out / 'birth'
    subprocess.run([sys.executable, '-m', 'successor', 'build', '--output', str(birth)],
                   cwd=ROOT, check=True, timeout=300)
    state = out / 'state.sqlite'
    kernel = SuccessorKernel(birth / 'manifest.json', state)
    task_goals = {}
    try:
        for task in tasks:
            goal_id = kernel.open_goal(task['spec'], budget=7, mode='full')
            task_goals[task['name']] = goal_id
            kernel.think(max_steps=80)
        save(out, 'initial_attempts', {'task_goals': task_goals, 'goals': goal_summary(kernel)})
        # Activate an existing admitted route. This is not a new implementation.
        save(out, 'existing_route_activation', kernel.activate_native_synthesis())
        for index in range(2):
            session_id = kernel.start_development(budget=30, max_goals=3)
            kernel.develop(max_steps=200)
            save(out, 'development_' + str(index + 1), kernel.development_snapshot())
        proposal = RuntimeEvolution(kernel).propose('native-gap-repair-20260919', 'YADO-1', REQUEST)
        admitted = False
        save(out, 'runtime_evolution_proposal', proposal)
        if proposal['selection'] is not None:
            evolution = RuntimeEvolution(kernel)
            evaluation = evolution.evaluate(proposal['tick'], out / 'candidate-evaluation')
            save(out, 'runtime_evaluation', evaluation)
            # Admission remains the kernel's fixed evidence-gated operation.
            if evaluation['passed']:
                save(out, 'runtime_admission', evolution.admit(proposal['tick']))
                admitted = True
        before = kernel.verify_state()
        before_journal = journal(kernel)
        save(out, 'kernel_journal', {'identity': kernel.identity,
                                    'implementation_identity': kernel.implementation_identity,
                                    'rows': before_journal})
        save(out, 'final_goals', goal_summary(kernel))
        save(out, 'updated_self_model', kernel.cognitive_snapshot()['all_observations'])
        attempts = []
        for row in before_journal:
            event = decode(row['body'])
            if event.get('kind') == 'COG_EXECUTE':
                attempts.append({'tick': row['tick'], **event})
        save(out, 'native_execution_attempts', attempts)
    finally:
        kernel.close()
    restored = SuccessorKernel(birth / 'manifest.json', state)
    try:
        after = restored.verify_state()
        assert before == after and before_journal == journal(restored)
        save(out, 'restart_verification', {'before': before, 'after': after,
                                          'journal_bytes_preserved': True})
        goals = replay([{**decode(row['body']), 'tick': row['tick'], 'event_hash': row['event_hash']}
                        for row in journal(restored) if decode(row['body']).get('kind', '').startswith('COG_')])
        outcomes = []
        for task in tasks:
            relevant = [g for g in goals.values() if g['spec'] == task['spec']]
            accepted = [g for g in relevant if g['status'] == 'VALIDATED_ON_HOLDOUT']
            queries_pass = any((g['result'] or {}).get('predictions') == task['observer_query_expected']
                               for g in accepted)
            outcomes.append({'task': task['name'], 'parent_deficit': task['parent_deficit'],
                             'goal_ids': [g['id'] for g in relevant],
                             'holdout_passed': bool(accepted), 'fresh_queries_passed': queries_pass,
                             'attempted_strategies': sorted({s for g in relevant for s in g['attempted']})})
        assert active_kernel_identity(ROOT) == identity
        assert not subprocess.check_output(['git', 'diff', '--name-only', '--',
                    'runtime', 'successor', 'canonical', 'architecture'], cwd=ROOT).strip()
        save(out, 'summary', {'status': 'COMPLETED_BOUNDED_NATIVE_ATTEMPT', 'outcomes': outcomes,
                              'component_probes_passed': sum(x['fresh_queries_passed'] for x in outcomes),
                              'component_probes_total': len(outcomes),
                              'runtime_candidate_selected': proposal['selection'] is not None,
                              'new_runtime_strategy_admitted': admitted,
                              'runtime_source_updated': False,
                              'canonical_unchanged': True, 'restart_verified': True,
                              'durable_failure_experience_retained': True,
                              'agent_conversation_performed': False,
                              'repository_patch_performed': False,
                              'background_process_running': False,
                              'original_deficits_resolved': False,
                              'kernel_identity': identity})
    finally:
        restored.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--preflight', action='store_true')
    args = parser.parse_args()
    main(args.output.resolve(), args.preflight)
