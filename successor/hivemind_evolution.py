"""Run one runtime-evolution objective through the real Hivemind MCP tracker."""
import argparse
import json
from pathlib import Path
import secrets

from .cognitive import CognitiveLoop
from .hivemind import _key
from .hivemind_client import HivemindClient
from .kernel import SuccessorKernel, fingerprint
from .runtime_evolution import REQUEST, RuntimeEvolution, normalize_request, states

CRITERIA = ('Kernel emitted a reusable runtime mechanism',
            'Fresh transfer, memory retention and complete regression passed',
            'Mechanism admitted to durable native cognition')


def request(description):
    if not isinstance(description, str) or len(description.encode()) > 2048:
        raise ValueError('RUNTIME_EVOLUTION_BOUNDED_DESCRIPTION_REQUIRED')
    return normalize_request(json.loads(description))


def criteria(issue):
    values = issue.get('acceptanceCriteria', [])
    texts = [x.get('text') for x in values]
    if len(texts) != len(CRITERIA) or set(texts) != set(CRITERIA):
        raise ValueError('RUNTIME_EVOLUTION_CRITERIA_REQUIRED')
    return {text: texts.index(text) for text in CRITERIA}


def run_issue(kernel, client, workspace_id, issue_id, output):
    _key(workspace_id, issue_id)
    current = client.call('hive_get_issue', {'id': issue_id})
    if current.get('id') != issue_id:
        raise ValueError('RUNTIME_EVOLUTION_ISSUE_MISMATCH')
    if current['state'] == 'cancelled':
        return {'status': 'CANCELLED', 'issue_id': issue_id}
    criteria(current)
    value = request(current.get('description'))
    existing = [s for s in states(CognitiveLoop(kernel)._records()).values()
                if (s['proposal']['workspace_id'], s['proposal']['issue_id']) == (workspace_id, issue_id)]
    if current['state'] == 'done' and not existing:
        raise ValueError('RUNTIME_EVOLUTION_DONE_WITHOUT_PROVENANCE')
    evolution = RuntimeEvolution(kernel)
    proposal = evolution.propose(workspace_id, issue_id, value)
    item = states(CognitiveLoop(kernel)._records())[proposal['tick']]
    if proposal['selection'] and item['evaluation'] is None:
        client.call('hive_set_state', {'id': issue_id, 'state': 'in_progress',
                                     'note': f'Runtime proposal {proposal["tick"]}; testing frozen module'})
        evolution.evaluate(proposal['tick'], Path(output) / ('attempt-' + secrets.token_hex(8)))
    current = client.call('hive_get_issue', {'id': issue_id})
    if current['state'] == 'cancelled':
        return {'status': 'CANCELLED', 'issue_id': issue_id, 'proposal_tick': proposal['tick']}
    indices = criteria(current)
    if request(current.get('description')) != value:
        raise ValueError('RUNTIME_EVOLUTION_REQUEST_CHANGED')
    item = states(CognitiveLoop(kernel)._records())[proposal['tick']]
    if item['evaluation'] and item['evaluation']['passed'] and not item['revoked']:
        evolution.admit(proposal['tick'])
        item = states(CognitiveLoop(kernel)._records())[proposal['tick']]
    kernel.verify_state()
    emitted = proposal['selection'] is not None
    passed = bool(item['evaluation'] and item['evaluation']['passed'])
    admitted = bool(item['admission'] and not item['revoked'])
    receipt = {'schema': 'yado.hivemind.runtime-evolution-result.v1',
               'workspace_id': workspace_id, 'issue_id': issue_id, 'proposal_tick': proposal['tick'],
               'evaluation_tick': (item['evaluation'] or {}).get('tick'),
               'admission_tick': (item['admission'] or {}).get('tick'),
               'status': 'ADMITTED' if admitted else 'ROLLED_BACK' if item['revoked'] else 'WITHHOLD',
               'kernel_identity': kernel.identity,
               'execution_implementation_identity': proposal['implementation_identity'],
               'publisher_implementation_identity': kernel.implementation_identity,
               'candidate_sha256': proposal['selection']['candidate']['source_sha256'] if emitted else None,
               'strategy': (item['admission'] or {}).get('strategy'),
               'source_goal_id': proposal['selection']['goal_id'] if emitted else None,
               'emitted': emitted, 'gates_passed': passed, 'admitted': admitted}
    message = json.dumps(receipt, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
    if not any(x.get('message') == message for x in current.get('activity', [])):
        client.call('hive_add_comment', {'id': issue_id, 'message': message})
    expected = dict(zip(CRITERIA, (emitted, passed, admitted)))
    for text, done in expected.items():
        if current['acceptanceCriteria'][indices[text]].get('done') is not done:
            client.call('hive_mark_acceptance', {'id': issue_id, 'index': indices[text], 'done': done})
    state = 'done' if admitted else 'in_review'
    if current['state'] != state:
        client.call('hive_set_state', {'id': issue_id, 'state': state,
                                     'note': 'Runtime evolution receipt ' + fingerprint(receipt)})
    saved = client.call('hive_get_issue', {'id': issue_id})
    saved_indices = criteria(saved)
    if (saved['state'] != state or request(saved.get('description')) != value
            or not any(x.get('message') == message for x in saved.get('activity', []))
            or any(saved['acceptanceCriteria'][saved_indices[text]]['done'] is not done
                   for text, done in expected.items())):
        raise ValueError('RUNTIME_EVOLUTION_RECEIPT_READBACK_FAILED')
    return {**receipt, 'tracker_state': state, 'published': True}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('manifest', 'state', 'tracker-root', 'workspace-id', 'issue', 'hive', 'output'):
        p.add_argument('--' + name, required=True)
    a = p.parse_args()
    kernel = SuccessorKernel(a.manifest, a.state)
    kernel.db.execute('PRAGMA journal_mode=DELETE')
    try:
        with HivemindClient([a.hive, 'mcp-stdio'], a.tracker_root) as client:
            result = run_issue(kernel, client, a.workspace_id, a.issue, a.output)
            print(json.dumps(result, ensure_ascii=False, indent=2))
    finally:
        kernel.close()


if __name__ == '__main__':
    main()
