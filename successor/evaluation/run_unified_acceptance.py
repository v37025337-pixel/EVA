"""Fresh bounded transfer tasks, with expectations kept outside the kernel."""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import random
import time

from successor.assembly import rehearse
from successor.graph import CausalGraph
from successor.kernel import SuccessorKernel, encode, equivalent, fingerprint
from successor.unified import export


def run(manifest, output):
    output = Path(output).resolve(); output.mkdir(parents=True, exist_ok=False)
    start = time.perf_counter(); checks = []
    kernel = SuccessorKernel(manifest, output / 'session.sqlite'); graph = CausalGraph(kernel)
    report = {'schema': 'yado.unified.acceptance.v1', 'seed': 20260912,
              'scope': 'BOUNDED_TASK_TRANSFER_AND_PERSISTENT_SOURCE_REUSE',
              'historical_verdicts_counted_as_tests': False, 'test_designer': 'ASSISTANT'}
    def check(label, actual, expected):
        checks.append({'label': label, 'passed': equivalent(actual, expected), 'actual': str(actual), 'expected': str(expected)})
    try:
        historical = rehearse(graph, 12); graph.run(400)
        state = graph.snapshot(); model_digest = fingerprint(state['self_model'])
        report['rehearsal'] = {'count': len(historical), 'statuses': dict(Counter(state['goals'][key]['status'] for key in historical)),
                               'self_model': state['self_model'], 'fresh_external_test': False}
        kernel.close(); kernel = SuccessorKernel(manifest, output / 'session.sqlite'); graph = CausalGraph(kernel)
        report['model_survives_restart'] = fingerprint(graph.snapshot()['self_model']) == model_digest
        rng = random.Random(20260912)
        for case in range(6):
            labels = [f'fresh-{case}-{i}' for i in range(7 + case)]
            edges = [[a, b] for a in labels for b in labels if a != b and rng.random() < .18]
            reach, todo = {labels[0]}, [labels[0]]
            while todo:
                current = todo.pop()
                for a, b in edges:
                    if a == current and b not in reach:
                        reach.add(b); todo.append(b)
            query = [{'x': x, 'y': y} for x, y in [(17, -9), (-11, 8), (23, 3), (-19, -7)]]
            rows = [{'x': x, 'y': y, 'expected': x*x+2*y+case} for x in range(-3, 4) for y in range(-2, 3)]
            key = graph.submit({'goal': f'Fresh composed task {case}', 'nodes': [
                {'id': 'reach', 'capability': 'relation', 'input': {'relation': edges, 'start': labels[0]}},
                {'id': 'events', 'capability': 'events', 'input': {'events': [['Q', ''], ['R', '']]},
                 'bindings': [{'from': 'reach', 'path': ['answer', 0], 'to': ['events', i, 1]} for i in (0, 1)]},
                {'id': 'numeric', 'capability': 'numeric', 'input': {'rows': rows, 'queries': query}}]})
            graph.run(80); nodes = graph.snapshot()['goals'][key]['nodes']
            check(f'{case}/closure', sorted(nodes['reach']['result']['answer']), sorted(reach))
            check(f'{case}/event-composition', nodes['events']['result']['answer'], True)
            check(f'{case}/causal-dependency', nodes['events']['decision']['dependencies']['reach'], nodes['reach']['terminal_tick'])
            for i, q in enumerate(query):
                check(f'{case}/unseen-numeric-{i}', nodes['numeric']['result']['predictions'][i], q['x']**2+2*q['y']+case)
        programs = []
        for case in range(2):
            formula = (lambda x, y: x*x+y) if case == 0 else (lambda x, y: x*y+3)
            rows = [{'x': x, 'y': y, 'expected': formula(x, y)} for x in range(-3, 4) for y in range(-2, 3)]
            key = graph.submit({'goal': f'Native source construction {case}', 'nodes': [{'id': 'source', 'capability': 'source_synthesis',
                        'input': {'rows': rows, 'queries': [{'x': 13, 'y': -7}]}}]})
            graph.run(30); goal = graph.snapshot()['goals'][key]
            result = goal['nodes']['source']['result']
            check(f'source-{case}/admission', goal['status'], 'VALIDATED_ON_HOLDOUT')
            programs.append((result['source_sha256'], formula))
        report['export'] = export(graph, output / 'exported')
        kernel.close(); kernel = SuccessorKernel(manifest, output / 'session.sqlite'); graph = CausalGraph(kernel)
        for case, (digest, formula) in enumerate(programs):
            queries = [{'x': rng.randint(-60, 60), 'y': rng.randint(-60, 60)} for _ in range(12)]
            key = graph.submit({'goal': f'Apply retained source {case}', 'nodes': [{'id': 'apply', 'capability': 'source_apply',
                                'input': {'capability_id': digest, 'queries': queries}}]})
            graph.run(20); result = graph.snapshot()['goals'][key]['nodes']['apply']['result']
            for i, q in enumerate(queries):
                check(f'source-{case}/unseen-{i}', result['predictions'][i], formula(q['x'], q['y']))
        state = graph.snapshot()
        (output / 'final-state.json').write_text(encode(state) + '\n')
        report.update(final_goal_statuses=dict(Counter(g['status'] for g in state['goals'].values())),
                      integrity=state['integrity'], learned_capability_ids=list(state['learned_capabilities']))
        passed = len(checks) == 68 and all(c['passed'] for c in checks) and report['model_survives_restart'] and all(g['status'] != 'ACTIVE' for g in state['goals'].values())
        report['status'] = 'PASS_BOUNDED_UNIFIED_ARCHITECTURE' if passed else 'FAIL_UNIFIED_ACCEPTANCE'
    except Exception as error:
        report.update(status='ERROR_UNIFIED_ACCEPTANCE', error_type=type(error).__name__, error=str(error))
    finally:
        kernel.close()
        report.update(checks=checks, checks_passed=sum(c['passed'] for c in checks), checks_total=len(checks), elapsed_seconds=time.perf_counter()-start)
        (output / 'acceptance.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    return report


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('--manifest', required=True); p.add_argument('--output', required=True)
    args = p.parse_args(); result = run(args.manifest, args.output)
    print(json.dumps({k: v for k, v in result.items() if k not in ('checks', 'rehearsal')}, ensure_ascii=False, indent=2))
    raise SystemExit(0 if result['status'].startswith('PASS_') else 1)
