"""Append the validated audit-sidecar repair without rewriting earlier evidence."""
import copy
import json
from bind import ROOT, digest, seal, file_hash, write, event_hash, validate_ledger_v2

EVIDENCE = 'experiments/deep-audit-20260920/sqlite-readonly-validation.json'
SOURCE = 'runtime/yado_repository_file_audit_v1.py'
REPAIR = 'IMMUTABLE_SQLITE_REPOSITORY_AUDIT_V1'


def main():
    report = json.loads((ROOT / EVIDENCE).read_text())
    focused = json.loads((ROOT / 'experiments/deep-audit-20260920/focused-validation.json').read_text())
    if report['status'] != 'PASS' or report['tests_run'] != 5 or report['source_sha256'] != file_hash(SOURCE):
        raise ValueError('SQLITE_READONLY_VALIDATION_REQUIRED')
    core = json.loads((ROOT / 'canonical/yado-unified-core-v1.json').read_text())
    head = json.loads((ROOT / 'canonical/yado-main-head-g2.json').read_text())
    ledger = json.loads((ROOT / 'architecture/evolution-ledger.json').read_text())
    validate_ledger_v2(ledger)
    old_events = copy.deepcopy(ledger['events'])
    old_head = head['canonical_head_digest']
    declared = core['runtime_integrity_manifest']['sources']
    actual = {path: file_hash(path) for path in core['active_runtime_sources']}
    if ({p for p in actual if actual[p] != declared.get(p)} != {SOURCE}
            or declared[SOURCE] != focused['source_sha256'][SOURCE]):
        raise ValueError('UNEXPECTED_POST_BINDING_SOURCE_CHANGE')
    repair = {'repair': REPAIR, 'source': SOURCE, 'previous_sha256': declared[SOURCE],
              'current_sha256': actual[SOURCE], 'validation_report': EVIDENCE}
    core['runtime_integrity_manifest'].update(sources=actual, manifest_digest=digest(actual))
    for document in (core, head):
        document['maintenance'].setdefault('post_binding_repairs', []).append(copy.deepcopy(repair))
    seal(core, 'core_digest')
    head['unified_core'].update(core_digest=core['core_digest'],
        runtime_integrity_manifest_digest=core['runtime_integrity_manifest']['manifest_digest'])
    seal(head, 'canonical_head_digest')
    event = {'event_id': REPAIR, 'index': len(old_events),
        'parent_event_hash': ledger['tail_event_hash'],
        'event_type': 'USER_AUTHORIZED_MAINTENANCE_BINDING',
        'generation': head['generation_id'], 'promotion_applied': False,
        'canonical_mutation': True, 'previous_head_digest': old_head,
        'new_head_digest': head['canonical_head_digest'],
        'implementation_id': head['implementation_id'], 'capability_upgrade': REPAIR,
        'effect': 'READ_COMMITTED_SQLITE_WITHOUT_CREATING_SIDECAR_FILES',
        'source_path': EVIDENCE, 'source_digest': file_hash(EVIDENCE),
        'validation_required_before_main_merge': ['FULL_REGRESSION', 'FULL_KERNEL_AUDIT_V2',
                                                   'CANONICAL_INVARIANT_GUARD']}
    event['event_hash'] = event_hash(event)
    ledger['events'].append(event)
    ledger.update(event_count=len(ledger['events']), tail_event_hash=event['event_hash'],
                  current_head_digest=head['canonical_head_digest'])
    seal(ledger, 'ledger_digest')
    validate_ledger_v2(ledger)
    assert ledger['events'][:-1] == old_events
    for path, value in [('canonical/yado-unified-core-v1.json', core),
                        ('canonical/yado-main-head-g2.json', head),
                        ('architecture/evolution-ledger.json', ledger)]:
        write(path, value)
    print(json.dumps({'status': 'BOUND_REQUIRES_FULL_INTEGRATION_GATES',
                      'head_digest': head['canonical_head_digest']}))


if __name__ == '__main__':
    main()
