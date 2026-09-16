"""Transport one bounded lineage objective through the existing local tracker."""
import json
from .kernel import fingerprint
from .lineage import ConsecutiveLineage, normalize_request

CRITERIA = ('Kernel chose every deficit and subsequent composition challenge',
            'Requested consecutive runtime extensions passed all existing gates',
            'Every extension solved its ordinary goal using the new module')


def _checked(issue, issue_id):
    if issue.get('id') != issue_id:
        raise ValueError('LINEAGE_ISSUE_MISMATCH')
    description = issue.get('description')
    if type(description) is not str or len(description.encode()) > 2048:
        raise ValueError('LINEAGE_BOUNDED_DESCRIPTION_REQUIRED')
    value = normalize_request(json.loads(description))
    texts = [r.get('text') for r in issue.get('acceptanceCriteria', [])]
    if len(texts) != len(CRITERIA) or set(texts) != set(CRITERIA):
        raise ValueError('LINEAGE_CRITERIA_REQUIRED')
    return value, {text: texts.index(text) for text in CRITERIA}


def run_issue(kernel, client, workspace_id, issue_id, output, *, progress=None):
    loop = ConsecutiveLineage(kernel)
    issue = client.call('hive_get_issue', {'id': issue_id})
    existing = [s for s in loop.snapshot().values() if
                (s['start']['workspace_id'], s['start']['issue_id']) == (workspace_id, issue_id)]
    if issue['state'] == 'cancelled':
        if existing:
            sid = existing[0]['start']['tick']
            loop.stop(sid)
            return {'status': 'CANCELLED', 'issue_id': issue_id, 'lineage_id': sid,
                    'generations': len(existing[0]['generations'])}
        return {'status': 'CANCELLED', 'issue_id': issue_id, 'generations': 0}
    try:
        value, _ = _checked(issue, issue_id)
    except (ValueError, TypeError, KeyError):
        if existing and existing[0]['status'] == 'ACTIVE':
            loop.stop(existing[0]['start']['tick'])
        raise
    if existing and existing[0]['start']['request'] != value:
        if existing[0]['status'] == 'ACTIVE':
            loop.stop(existing[0]['start']['tick'])
        raise ValueError('LINEAGE_TRACKER_OBJECTIVE_CHANGED')
    if issue['state'] == 'done' and not existing:
        raise ValueError('LINEAGE_TRACKER_DONE_WITHOUT_PROVENANCE')
    sid = loop.start(workspace_id, issue_id, value)

    class Cancelled(Exception):
        pass

    def check(row):
        current = client.call('hive_get_issue', {'id': issue_id})
        if current['state'] == 'cancelled':
            loop.stop(sid)
            raise Cancelled()
        try:
            current_request, _ = _checked(current, issue_id)
        except (ValueError, TypeError, KeyError):
            loop.stop(sid)
            raise
        if current_request != value:
            loop.stop(sid)
            raise ValueError('LINEAGE_TRACKER_OBJECTIVE_CHANGED')
        if progress:
            progress(row)

    if issue['state'] not in {'done', 'cancelled', 'in_progress'}:
        client.call('hive_set_state', {'id': issue_id, 'state': 'in_progress',
                                     'note': 'Durable lineage objective ' + str(sid)})
    try:
        result = loop.run(sid, output, progress=check)
    except Cancelled:
        return {'status': 'CANCELLED', 'issue_id': issue_id, 'lineage_id': sid,
                'generations': len(loop.snapshot()[sid]['generations'])}
    current = client.call('hive_get_issue', {'id': issue_id})
    if current['state'] == 'cancelled':
        loop.stop(sid)
        return {'status': 'CANCELLED', 'issue_id': issue_id, 'lineage_id': sid,
                'generations': len(result['generations'])}
    current_request, indices = _checked(current, issue_id)
    if current_request != value:
        raise ValueError('LINEAGE_TRACKER_OBJECTIVE_CHANGED')
    receipt = {'schema': 'yado.hivemind.consecutive-runtime-result.v1',
               'workspace_id': workspace_id, 'issue_id': issue_id, 'lineage_id': sid,
               'status': result['status'], 'reason': result['finish']['reason'],
               'generations': len(result['generations']), 'requested_generations': value['generations'],
               'identity': kernel.identity, 'implementation': result['start']['implementation'],
               'generation_events': [r['event_hash'] for r in result['generations']],
               'classification': 'BOUNDED_POLYNOMIAL_RUNTIME_CAPACITY_EXTENSIONS'}
    message = json.dumps(receipt, sort_keys=True, separators=(',', ':'))
    if not any(row.get('message') == message for row in current.get('activity', [])):
        client.call('hive_add_comment', {'id': issue_id, 'message': message})
    done = result['status'] == 'COMPLETE'
    for text in CRITERIA:
        if current['acceptanceCriteria'][indices[text]].get('done') is not done:
            client.call('hive_mark_acceptance', {'id': issue_id, 'index': indices[text], 'done': done})
    state = 'done' if done else 'in_review'
    if current['state'] != state:
        client.call('hive_set_state', {'id': issue_id, 'state': state,
                                     'note': 'Consecutive lineage receipt ' + fingerprint(receipt)})
    saved = client.call('hive_get_issue', {'id': issue_id})
    saved_request, saved_indices = _checked(saved, issue_id)
    if (saved_request != value or saved['state'] != state
            or any(saved['acceptanceCriteria'][saved_indices[text]]['done'] is not done for text in CRITERIA)
            or not any(row.get('message') == message for row in saved.get('activity', []))):
        raise ValueError('LINEAGE_TRACKER_RECEIPT_READBACK_FAILED')
    return {**receipt, 'published': True, 'tracker_state': state}
