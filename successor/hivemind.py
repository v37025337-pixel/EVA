"""Run typed Hivemind issues through the native cognitive loop.

The tracker transports goals and receipts. It neither supplies a solver nor
decides whether the kernel's independent validation passed.
"""
import argparse
import copy
import json
import re

from .cognitive import CognitiveLoop, MODES, replay, validate_goal
from .kernel import SuccessorKernel, decode, fingerprint
from .hivemind_client import HivemindClient

SCHEMA = 'yado.hivemind.goal.v1'
CRITERIA = ('Native kernel validation passed', 'Result is recorded in the durable kernel journal')
ACCEPTED = {'VERIFIED', 'VALIDATED_ON_HOLDOUT'}


def request(description):
    if not isinstance(description, str) or len(description.encode('utf-8')) > 65536:
        raise ValueError('HIVEMIND_BOUNDED_JSON_DESCRIPTION_REQUIRED')
    return normalize_request(json.loads(description))


def normalize_request(value):
    if (not isinstance(value, dict) or value.get('schema') != SCHEMA
            or not {'schema', 'spec'} <= set(value)
            or set(value) - {'schema', 'spec', 'budget', 'mode'}):
        raise ValueError('HIVEMIND_TYPED_GOAL_REQUIRED')
    budget, mode = value.get('budget', 10), value.get('mode', 'full')
    if type(budget) is not int or not 1 <= budget <= 30 or mode not in MODES:
        raise ValueError('HIVEMIND_GOAL_BUDGET_OR_MODE')
    return {'schema': SCHEMA, 'spec': validate_goal(value['spec']), 'budget': budget, 'mode': mode}


def _key(workspace, issue):
    if (not isinstance(workspace, str) or not re.fullmatch(r'[A-Za-z0-9_.-]{1,128}', workspace)
            or not isinstance(issue, str) or not re.fullmatch(r'[A-Z][A-Z0-9]{1,9}-\d+(\.\d+)*', issue)):
        raise ValueError('HIVEMIND_STABLE_WORKSPACE_AND_ISSUE_IDS_REQUIRED')
    return workspace, issue


def verify_links(records):
    by_tick, seen, links = {}, set(), {}
    for record in records:
        if record.get('kind') == 'HIVEMIND_INTAKE':
            body = {k: v for k, v in record.items() if k not in {'tick', 'event_hash'}}
            if set(body) != {'kind', 'workspace_id', 'issue_id', 'goal_id', 'request_digest'}:
                raise ValueError('HIVEMIND_INTAKE_CONTRACT')
            key = _key(body['workspace_id'], body['issue_id'])
            goal = by_tick.get(body['goal_id'])
            if (key in seen or goal is None or goal.get('kind') != 'COG_GOAL'
                    or body['goal_id'] != record['tick'] - 1):
                raise ValueError('HIVEMIND_GOAL_LINK')
            expected = {'schema': SCHEMA, 'spec': goal['spec'], 'budget': goal['budget'], 'mode': goal['mode']}
            if body['request_digest'] != fingerprint(expected):
                raise ValueError('HIVEMIND_REQUEST_DIGEST')
            seen.add(key)
            links[key] = record
        by_tick[record['tick']] = record
    return links


def _records(kernel):
    return [{**decode(raw), 'tick': tick, 'event_hash': digest}
            for tick, raw, digest in kernel.db.execute('SELECT tick,body,event_hash FROM events ORDER BY tick')]


def execution_implementation(kernel, tick):
    if tick is None:
        return None
    upgrades = [r for r in _records(kernel) if r.get('kind') == 'IMPLEMENTATION_UPGRADE']
    implementation = upgrades[0]['predecessor_implementation_digest'] if upgrades else kernel.implementation_identity
    for event in upgrades:
        if event['tick'] > tick:
            break
        implementation = event['implementation_digest']
    return implementation


def _goal(kernel, goal_id):
    # The public summary intentionally omits execution and verification records.
    return replay(CognitiveLoop(kernel)._records())[goal_id]


def bind_goal(kernel, workspace, issue, value):
    key = _key(workspace, issue)
    value = normalize_request(value)
    loop = CognitiveLoop(kernel)
    def bind():
        links = verify_links(_records(kernel))
        previous = links.get(key)
        if previous is not None:
            if previous['request_digest'] != fingerprint(value):
                raise ValueError('HIVEMIND_REQUEST_CHANGED_AFTER_INTAKE')
            return previous['goal_id']
        if sum(g['status'] == 'ACTIVE' for g in replay(loop._records()).values()) >= 64:
            raise ValueError('ACTIVE_GOAL_BUDGET')
        goal = kernel._append({'kind': 'COG_GOAL', 'spec': copy.deepcopy(value['spec']),
                               'budget': value['budget'], 'mode': value['mode'],
                               'spec_digest': fingerprint(value['spec'])})
        kernel._append({'kind': 'HIVEMIND_INTAKE', 'workspace_id': workspace, 'issue_id': issue,
                        'goal_id': goal['tick'], 'request_digest': fingerprint(value)})
        return goal['tick']
    return loop._transaction(bind)


def _criteria(issue):
    criteria = issue.get('acceptanceCriteria', [])
    texts = [c.get('text') for c in criteria]
    if len(texts) != len(CRITERIA) or set(texts) != set(CRITERIA):
        raise ValueError('HIVEMIND_NATIVE_VALIDATION_CRITERIA_REQUIRED')
    return {text: texts.index(text) for text in CRITERIA}


def run_issue(kernel, client, workspace_id, issue_id, *, max_steps=40):
    key = _key(workspace_id, issue_id)
    if type(max_steps) is not int or not 1 <= max_steps <= 1000:
        raise ValueError('HIVEMIND_FINITE_STEP_BUDGET_REQUIRED')
    issue = client.call('hive_get_issue', {'id': issue_id})
    if issue.get('id') != issue_id:
        raise ValueError('HIVEMIND_ISSUE_RESPONSE_MISMATCH')
    link = verify_links(_records(kernel)).get(key)
    if issue['state'] == 'cancelled':
        if link is not None:
            kernel.stop_goal(link['goal_id'])
        return {'status': 'CANCELLED', 'issue_id': issue_id, 'goal_id': link['goal_id'] if link else None}
    indices = _criteria(issue)
    value = request(issue.get('description'))
    if link is not None and link['request_digest'] != fingerprint(value):
        raise ValueError('HIVEMIND_REQUEST_CHANGED_AFTER_INTAKE')
    if issue['state'] == 'done' and link is None:
        raise ValueError('HIVEMIND_DONE_WITHOUT_KERNEL_PROVENANCE')
    goal_id = bind_goal(kernel, workspace_id, issue_id, value)
    goal = _goal(kernel, goal_id)
    if goal['status'] == 'ACTIVE':
        client.call('hive_set_state', {'id': issue_id, 'state': 'in_progress',
                                     'note': f'YADO durable goal {goal_id}; finite step budget {max_steps}'})
        kernel.think(max_steps)
        goal = _goal(kernel, goal_id)
    kernel.verify_state()
    current = client.call('hive_get_issue', {'id': issue_id})
    if current['state'] == 'cancelled':
        kernel.stop_goal(goal_id)
        return {'status': 'CANCELLED', 'issue_id': issue_id, 'goal_id': goal_id}
    indices = _criteria(current)
    if request(current.get('description')) != value:
        raise ValueError('HIVEMIND_REQUEST_CHANGED_DURING_EXECUTION')
    passed = goal['status'] in ACCEPTED and bool((goal['verification'] or {}).get('passed'))
    execution_tick = (goal['execution'] or {}).get('tick')
    recorded_result = goal['result'] if goal['result'] is not None else (goal['execution'] or {}).get('result')
    receipt = {'schema': 'yado.hivemind.result.v1', 'workspace_id': workspace_id, 'issue_id': issue_id,
               'goal_id': goal_id, 'request_digest': fingerprint(value), 'status': goal['status'],
               'kernel_identity': kernel.identity,
               'execution_implementation_identity': execution_implementation(kernel, execution_tick),
               'publisher_implementation_identity': kernel.implementation_identity,
               'execution_tick': execution_tick, 'result_recorded': execution_tick is not None,
               'verification_tick': (goal['verification'] or {}).get('tick'),
               'verification_scope': (goal['verification'] or {}).get('scope'),
               'checks': (goal['verification'] or {}).get('checks', 0),
               'result_digest': fingerprint(recorded_result),
               'source_sha256': (recorded_result or {}).get('source_sha256'),
               'selected_strategies': goal['attempted'], 'passed': passed}
    comment = json.dumps(receipt, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
    if not any(row.get('message') == comment for row in current.get('activity', [])):
        client.call('hive_add_comment', {'id': issue_id, 'message': comment})
    expected = {CRITERIA[0]: passed, CRITERIA[1]: execution_tick is not None}
    for text, checked in expected.items():
        index = indices[text]
        if current['acceptanceCriteria'][index].get('done') is not checked:
            client.call('hive_mark_acceptance', {'id': issue_id, 'index': index, 'done': checked})
    tracker_state = 'done' if passed else 'in_progress' if goal['status'] == 'ACTIVE' else 'in_review'
    if current['state'] != tracker_state:
        client.call('hive_set_state', {'id': issue_id, 'state': tracker_state,
                                     'note': f'YADO goal {goal_id}: {goal["status"]}; receipt {fingerprint(receipt)}'})
    saved = client.call('hive_get_issue', {'id': issue_id})
    saved_indices = _criteria(saved)
    if (saved['state'] != tracker_state or request(saved['description']) != value
            or not any(row.get('message') == comment for row in saved.get('activity', []))
            or any(saved['acceptanceCriteria'][saved_indices[text]]['done'] is not checked
                   for text, checked in expected.items())):
        raise ValueError('HIVEMIND_RECEIPT_READBACK_FAILED')
    return {**receipt, 'tracker_state': tracker_state, 'published': True}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--manifest', required=True)
    p.add_argument('--state', required=True)
    p.add_argument('--tracker-root', required=True, help='The actual .hivemind directory')
    p.add_argument('--workspace-id', required=True, help='Stable ID retained when the tracker is moved')
    p.add_argument('--issue', required=True)
    p.add_argument('--hive', required=True, help='Path to the pinned hive executable')
    p.add_argument('--max-steps', type=int, default=40)
    a = p.parse_args()
    kernel = SuccessorKernel(a.manifest, a.state)
    kernel.db.execute('PRAGMA journal_mode=DELETE')
    try:
        with HivemindClient([a.hive, 'mcp-stdio'], a.tracker_root) as client:
            result = run_issue(kernel, client, a.workspace_id, a.issue, max_steps=a.max_steps)
            print(json.dumps(result, ensure_ascii=False, indent=2))
    finally:
        kernel.close()


if __name__ == '__main__':
    main()
