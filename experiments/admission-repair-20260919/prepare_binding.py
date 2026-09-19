"""Bind the reviewed four-module repair and append a maintenance ledger event."""
import copy
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'runtime'))
from yado_evolution_ledger_v2 import event_hash, validate_ledger_v2

REPORT = 'experiments/admission-repair-20260919/observed-results.json'
REPAIR = 'YADO_OFFLINE_REPLAY_JSON_SEMANTICS_V2_REPAIR'
EXPECTED_PREVIOUS = {
    'successor/cognitive.py': '39ec723722ea405bea5c45f0107572477bd51985813c7d033be19c48d26597ce',
    'successor/compositional_binding.py': '8f5d445a98f141ad1eb2846f8615f377e101ae885a4f137f38d10fa5628b1032',
    'successor/compositional_source.py': 'd9741e99432cb1e07d56f1e2543b90b1b3b1f3b2d12b91bacca9993c4f8fcdaf',
    'successor/generation.py': '895170e691d8c637358b91dc0c7d6669998682ac206d89b5c81338062f2096f4',
}


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), default=str).encode()).hexdigest()


def seal(value, field):
    value[field] = digest({k: v for k, v in value.items() if k != field})


def main():
    paths = ['canonical/yado-unified-core-v1.json', 'canonical/yado-main-head-g2.json', 'architecture/evolution-ledger.json']
    core, head, ledger = [json.loads((ROOT / p).read_text()) for p in paths]
    observed = json.loads((ROOT / REPORT).read_text())
    assert observed['status'] == 'PASS_REPAIRED_REPLAY_JSON_AND_READMISSION'
    assert observed['readmission_passed'] and observed['inherited_event_prefixes_unchanged']
    assert observed['json_fresh_passed'] == observed['json_fresh_checks'] == 32
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
        'effect': 'BIND_REVIEWED_OFFLINE_RETENTION_AND_VERSIONED_JSON_SEMANTICS; NEXT=' + ledger['open_deficits'][0],
        'validation_required_before_main_merge': ['FULL_REGRESSION', 'FULL_KERNEL_AUDIT_V2',
            'CANONICAL_INVARIANT_GUARD', 'FRESH_COMPONENT_READMISSION_AND_NATIVE_CONTINUITY'],
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
