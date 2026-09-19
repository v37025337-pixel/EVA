"""Bind the reviewed public grammar-profile repair and append a maintenance ledger event."""
import copy
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'runtime'))
from yado_evolution_ledger_v2 import event_hash, validate_ledger_v2

REPORT = 'experiments/profile-continuation-20260919/profile-tests.json'
REPAIR = 'YADO_PUBLIC_V2_PROFILE_CONTINUITY_REPAIR'
EXPECTED_PREVIOUS = {'successor/cognitive.py': 'e7c3f077b95bec6b272ec6ad103e528538df09236d823dd817366638483b2648', 'successor/kernel.py': '1718ed31d116ee0c01943eb88950141c181177399b550e2c7f9d0f76d39fe4d1'}


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), default=str).encode()).hexdigest()


def seal(value, field):
    value[field] = digest({k: v for k, v in value.items() if k != field})


def main():
    paths = ['canonical/yado-unified-core-v1.json', 'canonical/yado-main-head-g2.json', 'architecture/evolution-ledger.json']
    core, head, ledger = [json.loads((ROOT / p).read_text()) for p in paths]
    observed = json.loads((ROOT / REPORT).read_text())
    assert observed['status'] == 'PASS_PUBLIC_V2_PROFILE_REGRESSION'
    assert observed['tests_run'] == 3 and observed['failures'] == observed['errors'] == observed['skips'] == 0
    assert validate_ledger_v2(ledger)['valid']
    actual = {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in core['active_runtime_sources']}
    prior = core['runtime_integrity_manifest']['sources']
    changed = {p: h for p, h in prior.items() if actual.get(p) != h}
    assert changed == EXPECTED_PREVIOUS, changed
    previous_head = head['canonical_head_digest']
    for document in (core, head):
        document['maintenance_history'].append(copy.deepcopy(document['maintenance']))
        document['maintenance'] = {**document['maintenance'], 'capability_upgrade': REPAIR,
            'authorship': 'ASSISTANT_USER_AUTHORIZED_REPAIR', 'validation_report': REPORT,
            'parent_main_commit': '05488e8dddc4629c5c1d9cf38b0c21cf3931df74',
            'native_capability_gain_claimed': False, 'formal_generation_changed': False}
    core['runtime_integrity_manifest'].update(sources=actual, manifest_digest=digest(actual))
    seal(core, 'core_digest')
    head['unified_core'].update(core_digest=core['core_digest'],
        runtime_integrity_manifest_digest=core['runtime_integrity_manifest']['manifest_digest'])
    seal(head, 'canonical_head_digest')
    index = len(ledger['events'])
    event = {'event_id': REPAIR + '_MAINTENANCE_' + str(index), 'index': index,
        'parent_event_hash': ledger['tail_event_hash'], 'event_type': 'USER_AUTHORIZED_MAINTENANCE_BINDING',
        'generation': head['generation_id'], 'promotion_applied': False, 'canonical_mutation': True,
        'previous_head_digest': previous_head, 'new_head_digest': head['canonical_head_digest'],
        'implementation_id': head['implementation_id'], 'capability_upgrade': REPAIR,
        'effect': 'BIND_PUBLIC_ACTIVE_GRAMMAR_AND_MEMORY_STATUS_REPAIR; NEXT=' + ledger['open_deficits'][0],
        'validation_required_before_main_merge': ['FULL_REGRESSION', 'FULL_KERNEL_AUDIT_V2',
            'CANONICAL_INVARIANT_GUARD', 'PRESERVED_COMPONENT_ADMISSION_AND_NATIVE_CONTINUITY'],
        'source_path': REPORT, 'source_digest': hashlib.sha256((ROOT / REPORT).read_bytes()).hexdigest()}
    event['event_hash'] = event_hash(event)
    ledger['events'].append(event)
    ledger.update(event_count=len(ledger['events']), tail_event_hash=event['event_hash'],
                  current_head_digest=head['canonical_head_digest'])
    seal(ledger, 'ledger_digest')
    assert validate_ledger_v2(ledger)['valid']
    for path, value in zip(paths, [core, head, ledger]):
        (ROOT / path).write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + '\n')
    print(json.dumps({'sources_rebound': sorted(changed), 'ledger_event_index': index,
                      'head_digest': head['canonical_head_digest']}))


if __name__ == '__main__':
    main()
