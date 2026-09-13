"""Supervised 20-goal acceptance run. The curriculum is host-authored.

Each goal is pursued by CognitiveLoop without a supplied sequence of actions.
Public benchmark holdouts establish bounded transfer, not unseen-benchmark
performance, general intelligence, or consciousness.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path

from .kernel import SuccessorKernel, equivalent
from .archive import file_sha, git
import yado_autonomous_meta_source_evolution_v2 as v2

ROOT = Path(__file__).resolve().parents[1]


def external_goal(name):
    payload, proof = v2.fetch_json(f'{v2.BASE}/{name}/canonical-data.json')
    rows, seen = [], set()
    for case in v2.flatten_cases(payload):
        if name == 'run-length-encoding' and case['property'] != 'encode':
            continue
        if type(case.get('expected')) not in {int, str, bool} or case.get('scenarios'):
            continue
        inputs = case['input']
        if any(type(x) not in {int, str, bool} for x in inputs.values()):
            continue
        if name == 'hamming' and len(inputs['strand1']) != len(inputs['strand2']):
            continue
        if any(type(x) is int and abs(x) > 10**6 for x in inputs.values()):
            continue
        marker = json.dumps(inputs, sort_keys=True)
        if marker not in seen:
            rows.append({'input': inputs, 'expected': case['expected']})
            seen.add(marker)
    if name == 'hamming' and len(rows) == 5:
        # This pinned corpus has only five supported numeric examples. Keep
        # both external holdouts and use a separately authored unlabelled query.
        spec = {'domain': 'native_source', 'training': rows[:3], 'validation': rows[3:],
                'queries': [{'input': {'strand1': 'ACGTAC', 'strand2': 'AGGTTC'}}]}
        return {'name': name, 'spec': spec, 'expected_queries': [2], 'external_source': proof,
                'query_origin': 'HOST_AUTHORED_TRANSFER_CASE'}
    if not 6 <= len(rows) <= 67:
        raise ValueError('EXTERNAL_CASE_COUNT:' + name + ':' + str(len(rows)))
    spec = {'domain': 'native_source', 'training': rows[:-3], 'validation': rows[-3:-1],
            'queries': [{'input': rows[-1]['input']}]}
    return {'name': name, 'spec': spec, 'expected_queries': [rows[-1]['expected']], 'external_source': proof}


def curriculum():
    names = ['hamming', 'isogram', 'raindrops', 'run-length-encoding', 'armstrong-numbers']
    with ThreadPoolExecutor(max_workers=4) as pool:
        tasks = list(pool.map(external_goal, names))
    # Two genuinely different local inputs use the external run-length contract.
    key = next(iter(tasks[3]['spec']['training'][0]['input']))
    for index, letter in enumerate(('W', 'Z')):
        tasks.append({'name': f'restart-source-transfer-{index}', 'spec': {
            'domain': 'native_source',
            'training': [{'input': {key: letter * n}, 'expected': str(n) + letter} for n in (7, 8, 9)],
            'validation': [{'input': {key: letter * n}, 'expected': str(n) + letter} for n in (10, 11)],
            'queries': [{'input': {key: letter * 12}}]}, 'expected_queries': ['12' + letter]})
    for index, degree in enumerate((1, 2, 3, 2)):
        tasks.append({'name': f'numeric-{index}', 'spec': {'domain': 'numeric',
            'rows': [{'x': x, 'y': y, 'expected': x**degree + 2*y + index}
                     for x in range(-3, 4) for y in range(-2, 3)],
            'queries': [{'x': 9, 'y': -4}, {'x': -8, 'y': 3}]},
            'expected_queries': [9**degree - 8 + index, (-8)**degree + 6 + index]})
    for index in range(4):
        tasks.append({'name': f'relation-{index}', 'spec': {'domain': 'relation',
            'relation': [[index, index+1], [index+1, index+2], [index+2, index], [99, 100]],
            'start': index}})
    for index, events in enumerate(([], [('Q', 'a'), ('R', 'a')],
                                    [('Q', 'a'), ('R', 'b')], [('Q', 'a')])):
        tasks.append({'name': f'events-{index}', 'spec': {'domain': 'events', 'events': events}})
    tasks.append({'name': 'live-library-discovery', 'spec': {'domain': 'library_discovery',
                                                           'objective': 'html_xml_parser'}})
    assert len(tasks) == 20
    return tasks


def run(manifest, output):
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    tasks = curriculum()
    (output / 'goals.json').write_text(json.dumps(tasks, ensure_ascii=False, indent=2) + '\n')
    state = output / 'kernel.sqlite'
    kernel = SuccessorKernel(manifest, state)
    results = []
    try:
        for index, task in enumerate(tasks):
            if index == 5:
                kernel.close()
                kernel = SuccessorKernel(manifest, state)
            goal_id = kernel.open_goal(task['spec'], budget=10)
            kernel.think(40)
            goal = kernel.cognitive_snapshot()['goals'][str(goal_id)]
            correct = goal['status'] in {'VERIFIED', 'VALIDATED_ON_HOLDOUT'}
            if 'expected_queries' in task:
                correct = correct and equivalent((goal['result'] or {}).get('predictions'), task['expected_queries'])
            row = {'name': task['name'], 'goal_id': goal_id, 'status': goal['status'],
                   'attempted': goal['attempted'], 'spent': goal['budget'] - goal['remaining'],
                   'independent_query_check': correct, 'result': goal['result']}
            results.append(row)
            print(json.dumps({k: v for k, v in row.items() if k != 'result'}), flush=True)
        snapshot = kernel.cognitive_snapshot()
        verification = kernel.verify_state()
        events = [dict(row) for row in kernel.db.execute('SELECT * FROM events ORDER BY tick')]
        (output / 'events.json').write_text(json.dumps(events, ensure_ascii=False, indent=2) + '\n')
        (output / 'sources').mkdir()
        for row in results:
            result = row['result'] or {}
            if result.get('source'):
                (output / 'sources' / (result['source_sha256'] + '.py')).write_text(result['source'])
        report = {'schema': 'yado.active_native_loop.acceptance.v1',
                  'status': 'PASS_BOUNDED_ACTIVE_LOOP' if all(r['independent_query_check'] for r in results) else 'WITHHOLD',
                  'tested_commit': git(ROOT, 'rev-parse', 'HEAD').decode().strip(),
                  'working_tree_dirty': bool(git(ROOT, 'status', '--porcelain').strip()),
                  'identity_digest': kernel.identity, 'goals_run': len(results),
                  'goals_passed': sum(r['independent_query_check'] for r in results),
                  'restart_after_goal': 5, 'results': results, 'snapshot': snapshot,
                  'state_verification': verification,
                  'external_sources': [t['external_source'] for t in tasks if 'external_source' in t],
                  'authorship': {'curriculum': 'ASSISTANT', 'adapter': 'ASSISTANT',
                                'selection_and_source_composition': 'YADO_USING_HOST_AUTHORED_GRAMMAR'},
                  'consciousness_established': False, 'general_intelligence_established': False}
    finally:
        kernel.close()
    report['state_sha256'] = file_sha(state)
    (output / 'receipt.json').write_text(json.dumps(report, ensure_ascii=False, indent=2, default=str) + '\n')
    print(json.dumps({k: report[k] for k in ('status', 'goals_run', 'goals_passed', 'identity_digest')}), flush=True)
    return 0 if report['status'] == 'PASS_BOUNDED_ACTIVE_LOOP' else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    return run(args.manifest, args.output)


if __name__ == '__main__':
    raise SystemExit(main())
