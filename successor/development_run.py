"""Reproducible, offline development and fresh-input transfer experiment.

The host supplies two initial experiences and a held-out transfer curriculum.
The kernel chooses retry goals from its own failures without a supplied goal ID.
The contracts and all expected answers are host-authored, not novel discoveries.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sqlite3

from .archive import file_sha, git
from .kernel import SuccessorKernel, decode, equivalent

ROOT = Path(__file__).resolve().parents[1]


def tasks(transfer=False):
    strings = ([('AAA', '3A'), ('BBCC', '2B2C'), ('D', 'D')], [('EEEE', '4E'), ('FFG', '2FG')])
    numbers = ([(2, True), (3, False), (12, True), (11, False)], [(100, True), (101, False)])
    if transfer:
        strings = ([('HHH', '3H'), ('IIJJ', '2I2J'), ('K', 'K')], [('LLLL', '4L'), ('MMN', '2MN')])
        numbers = ([(20, True), (21, False), (32, True), (33, False)], [(200, True), (201, False)])
    return [
        {'name': 'run-length-encoding', 'spec': {'domain': 'native_source',
         'training': [{'input': {'text': a}, 'expected': b} for a, b in strings[0]],
         'validation': [{'input': {'text': a}, 'expected': b} for a, b in strings[1]],
         'queries': [{'input': {'text': 'OOOPP' if transfer else 'AABBBBB'}}]},
         'expected_queries': ['3O2P' if transfer else '2A5B']},
        {'name': 'integer-parity', 'spec': {'domain': 'native_source',
         'training': [{'input': {'number': a}, 'expected': b} for a, b in numbers[0]],
         'validation': [{'input': {'number': a}, 'expected': b} for a, b in numbers[1]],
         'queries': [{'input': {'number': n}} for n in ((888, 889) if transfer else (998, 999))]},
         'expected_queries': [True, False]},
    ]


def solve(kernel, task, mode='full'):
    goal_id = kernel.open_goal(task['spec'], budget=1, mode=mode)
    kernel.think(40)
    result = kernel.cognitive_snapshot()['goals'][str(goal_id)]
    return {'name': task['name'], 'goal_id': goal_id, 'status': result['status'],
            'attempted': result['attempted'], 'spent': result['budget'] - result['remaining'],
            'correct': result['status'] == 'VALIDATED_ON_HOLDOUT' and equivalent(
                (result['result'] or {}).get('predictions'), task['expected_queries']),
            'result': result['result']}


def backup(kernel, path):
    with sqlite3.connect(path) as destination:
        kernel.db.backup(destination)


def records(kernel):
    return [{**decode(r['body']), 'tick': r['tick'], 'event_hash': r['event_hash']}
            for r in kernel.db.execute('SELECT * FROM events ORDER BY tick')]


def run(manifest, output):
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    seed, transfer = tasks(), tasks(True)
    (output / 'curriculum.json').write_text(json.dumps({'seed': seed, 'transfer': transfer}, indent=2) + '\n')
    state = output / 'kernel.sqlite'
    kernel = SuccessorKernel(manifest, state)
    try:
        initial = [solve(kernel, t) for t in seed]
        backup(kernel, output / 'before-development.sqlite')
        development_id = kernel.start_development(budget=12, max_goals=2)
        prefix = kernel.develop(3)
        frozen = prefix[-1]
        restart_tick = kernel.verify_state()['tick']
        kernel.close()
        kernel = SuccessorKernel(manifest, state)
        suffix = kernel.develop(100)
        development = kernel.development_snapshot()
        session = development['sessions'][development_id]
        backup(kernel, output / 'without-memory.sqlite')
        kernel.close()
        kernel = SuccessorKernel(manifest, state)
        retained = [solve(kernel, t) for t in transfer]
        final_events = records(kernel)
        verification = kernel.verify_state()
        identity = kernel.identity
    finally:
        kernel.close()
    controls = {}
    for name, filename, mode in [('before_development', 'before-development.sqlite', 'full'),
                                  ('without_memory', 'without-memory.sqlite', 'no_memory')]:
        control = SuccessorKernel(manifest, output / filename)
        try:
            controls[name] = [solve(control, t, mode) for t in transfer]
            control.verify_state()
        finally:
            control.close()
    checked = {
        'initial_failures_observed': all(r['status'] == 'WITHHOLD' for r in initial),
        'selected_goals_from_own_failures': {s['parent_goal_id'] for s in session['selections']} == {
            r['goal_id'] for r in initial},
        'two_verified_development_outcomes': len(session['outcomes']) == 2 and all(
            r['status'] == 'VALIDATED_ON_HOLDOUT' for r in session['outcomes']),
        'restart_between_freeze_and_verification': frozen['kind'] == 'COG_EXECUTE' and suffix[0]['kind'] == 'COG_VERIFY'
            and frozen['result'].get('source_sha256') == suffix[0]['evidence'].get('source_sha256'),
        'bounded_complete': session['status'] == 'COMPLETE' and sum(
            s['budget'] for s in session['selections']) <= 12,
        'fresh_transfer_uses_learned_sources': all(r['correct'] and r['attempted'] == ['reuse_verified_source'] for r in retained),
        'same_budget_controls_fail': all(r['status'] == 'WITHHOLD' and not r['correct']
            for rows in controls.values() for r in rows),
        'causal_journal_valid': verification['status'] == 'PASS',
    }
    report = {'schema': 'yado.experience_development.acceptance.v1',
              'status': 'PASS_BOUNDED_EXPERIENCE_DEVELOPMENT' if all(checked.values()) else 'WITHHOLD',
              'checks': checked, 'tested_commit': git(ROOT, 'rev-parse', 'HEAD').decode().strip(),
              'working_tree_dirty': bool(git(ROOT, 'status', '--porcelain').strip()),
              'identity_digest': identity, 'initial': initial, 'development': development,
              'restart_tick': restart_tick, 'fresh_transfer': retained, 'controls': controls,
              'state_verification': verification, 'state_sha256': file_sha(state),
              'authorship': {'objective_controller_and_curriculum': 'ASSISTANT',
                            'retry_goal_selection_and_source_composition': 'YADO_RUNTIME'},
              'limits': ['TWO_HOST_AUTHORED_CONTRACTS', 'HOST_AUTHORED_GRAMMAR',
                         'RETRY_OF_PAST_TASK_NOT_NEW_OPEN_DOMAIN_OBJECTIVE',
                         'DEVELOPMENT_REUSES_OLD_HOLDOUT; TRANSFER_USES_DISTINCT_HOST_AUTHORED_INPUTS'],
              'background_process_running': False, 'consciousness_established': False,
              'general_intelligence_established': False, 'g3_genesis_performed': False}
    (output / 'events.json').write_text(json.dumps(final_events, indent=2, default=str) + '\n')
    (output / 'sources').mkdir()
    for r in retained:
        result = r['result'] or {}
        if 'source' in result:
            (output / 'sources' / (result['source_sha256'] + '.py')).write_text(result['source'])
    (output / 'receipt.json').write_text(json.dumps(report, indent=2, default=str) + '\n')
    print(json.dumps({'status': report['status'], 'checks': checked, 'identity_digest': identity}, indent=2), flush=True)
    return 0 if all(checked.values()) else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    return run(args.manifest, args.output)


if __name__ == '__main__':
    raise SystemExit(main())
