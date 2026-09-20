"""Bind reviewed maintenance to current manifests without rewriting history."""
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'runtime'))
from yado_evolution_ledger_v2 import event_hash, validate_ledger_v2
from yado_current_manifest_source_audit_v1 import SOURCES, SPECIFICATIONS, audit_current_sources

REPAIR = 'YADO_G0_TO_CURRENT_DEEP_AUDIT_REPAIR_V1'
BASELINE = '93b28c15fde045efc6cdec5a0b9d6f2bf374380f'
EVIDENCE = 'experiments/deep-audit-20260920/focused-validation.json'


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), default=str).encode()).hexdigest()


def seal(value, field):
    value[field] = digest({k: v for k, v in value.items() if k != field})


def file_hash(name):
    return hashlib.sha256((ROOT / name).read_bytes()).hexdigest()


def write(name, value):
    path = ROOT / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + '\n')


def main():
    observed = json.loads((ROOT / EVIDENCE).read_text())
    if observed['status'] != 'PASS' or observed['failures'] or observed['errors'] or observed['skipped']:
        raise ValueError('FOCUSED_VALIDATION_REQUIRED')
    for path, expected in observed['source_sha256'].items():
        if file_hash(path) != expected:
            raise ValueError('SOURCE_CHANGED_AFTER_FOCUSED_VALIDATION:' + path)
    documents = {p.name: json.loads(p.read_text()) for p in (ROOT / 'canonical').glob('*.json')}
    core, head, prov = (documents[name] for name in (
        'yado-unified-core-v1.json', 'yado-main-head-g2.json', 'yado-algorithm-provenance-registry-v1.json'))
    if core.get('maintenance', {}).get('capability_upgrade') == REPAIR:
        raise ValueError('MAINTENANCE_ALREADY_BOUND')
    originals = copy.deepcopy(documents)
    ledger = json.loads((ROOT / 'architecture/evolution-ledger.json').read_text())
    validate_ledger_v2(ledger)
    original_events = copy.deepcopy(ledger['events'])
    previous_head = head['canonical_head_digest']
    hashes = {key: file_hash(path) for key, path in SOURCES.items()}
    touched = set()
    for name, keys, key in SPECIFICATIONS:
        target = documents[name]
        for field in keys[:-1]:
            target = target[field]
        target[keys[-1]] = hashes[key]
        touched.add(name)

    leaf_fields = {
        'yado-active-native-loop-v1.json': 'binding_digest',
        'yado-g2-cognitive-temporal-kernel-v1.json': 'canonical_component_digest',
        'yado-g2-evolutionary-genome-v1.json': 'canonical_component_digest',
        'yado-g2-experience-conditioned-cognitive-layer-v4.json': 'canonical_component_digest',
        'yado-g2-active-patch-registry-v1.json': 'registry_digest',
    }
    patch = documents['yado-g2-active-patch-registry-v1.json']
    for row in patch['patches']:
        actual = file_hash(row['source'])
        if row['source_sha256'] != actual or row['expected_source_sha256'] != actual:
            row.setdefault('source_binding_history', []).append({
                'source_sha256': row['source_sha256'],
                'expected_source_sha256': row['expected_source_sha256'],
                'evidence_scope': 'ORIGINAL_ADMISSION_IMPLEMENTATION'})
            row.update(source_sha256=actual, expected_source_sha256=actual,
                       source_hash_ok=True, maintenance_evidence=EVIDENCE)
    for name, field in leaf_fields.items():
        leaf = documents[name]
        leaf.setdefault('maintenance_history', []).append({
            'previous_digest': originals[name][field], 'repair': REPAIR,
            'original_gate_evidence_scope': 'HISTORICAL_ADMISSION_ONLY',
            'validation_report': EVIDENCE,
            'full_integration_gates_required_before_main': True})
        seal(leaf, field)
        touched.add(name)

    binding = prov['current_g2_binding']
    native = documents['yado-active-native-loop-v1.json']
    for target in (core['active_native_loop_v1'], head['active_native_loop_v1'], binding['active_native_loop_v1']):
        target.update(binding_digest=native['binding_digest'], runtime_sha256=hashes['native'])
    for row in prov['mechanisms']:
        if row.get('adapter_source') == SOURCES['native']:
            row['adapter_source_sha256'] = hashes['native']
    for obj in (core, head):
        obj['active_patch_registry']['registry_digest'] = patch['registry_digest']
        for key, name in (
            ('evolutionary_genome_v1', 'yado-g2-evolutionary-genome-v1.json'),
            ('experience_conditioned_cognitive_layer_v4', 'yado-g2-experience-conditioned-cognitive-layer-v4.json'),
            ('cognitive_temporal_kernel_v1', 'yado-g2-cognitive-temporal-kernel-v1.json')):
            obj[key]['canonical_component_digest'] = documents[name]['canonical_component_digest']
        obj['cognitive_temporal_kernel_v1']['artifact'] = 'canonical/yado-g2-cognitive-temporal-kernel-v1.json'
    binding['active_patch_registry_digest'] = patch['registry_digest']
    binding['experience_conditioned_cognitive_layer_digest'] = documents['yado-g2-experience-conditioned-cognitive-layer-v4.json']['canonical_component_digest']
    seal(prov, 'registry_digest')
    core['algorithm_provenance_registry_digest'] = prov['registry_digest']
    head['algorithm_provenance_registry']['registry_digest'] = prov['registry_digest']
    head['unified_core']['algorithm_provenance_registry_digest'] = prov['registry_digest']

    lineage = {
        'schema': 'yado.formal_generation_lineage.v1',
        'active_formal_generation': head['generation_id'],
        'current_head_manifest': 'canonical/yado-main-head-g2.json',
        'runtime_version_axis': 'architecture/yado-unified-architecture-v2.json',
        'g3_genesis_performed': False,
        'stages': [
            {'generation': 'G0_RC8_V36', 'role': 'HISTORICAL_VERIFIED_ROOT',
             'manifest': 'architecture/developmental-head-manifest.json',
             'state_digest': '7ecfd384d48bfd5c39312fa4c54a8feb49f4473b171902c8190a6b276beda9d1',
             'ledger_event': 'E0001_G0_VERIFIED_ROOT', 'run_id': '33266617685'},
            {'generation': 'G1_CANDIDATE_S2', 'role': 'HISTORICAL_ADMITTED_PARENT',
             'manifest': 'canonical/yado-main-head-g1-s2.json',
             'head_digest': documents['yado-main-head-g1-s2.json']['canonical_head_digest'],
             'parent_digest': documents['yado-main-head-g1-s2.json']['parent_artifact_digest'],
             'promotion_run_id': '33347635985'},
            {'generation': head['generation_id'], 'role': 'CURRENT_FORMAL_ARCHITECTURE',
             'manifest': 'canonical/yado-main-head-g2.json',
             'parent_digest': documents['yado-main-head-g1-s2.json']['canonical_head_digest'],
             'promotion_run_id': '33357100322'}],
        'claim_boundary': 'SOFTWARE_LINEAGE; MAINTENANCE_AND_RUNTIME_VERSIONS_DO_NOT_IMPLY_NEW_FORMAL_GENERATIONS'}
    seal(lineage, 'artifact_digest')
    write('canonical/yado-generation-lineage-v1.json', lineage)
    extra_sources = ['runtime/yado_repository_file_audit_v1.py',
                     'runtime/yado_current_manifest_source_audit_v1.py',
                     'runtime/yado_legacy_planning_boundary_v1.py',
                     'runtime/yado_g2_remote_branch_inventory_reconcile_v2.py',
                     'runtime/yado_branch_lifecycle_audit_v1.py']
    core['active_runtime_sources'] = sorted(set(core['active_runtime_sources'] + extra_sources))
    sources = {path: file_hash(path) for path in core['active_runtime_sources']}
    core['runtime_integrity_manifest'].update(sources=sources, manifest_digest=digest(sources))
    core['historical_recovery_api'] = {
        'source': 'runtime/yado_legacy_data_boundary_v1.py',
        'source_sha256': file_hash('runtime/yado_legacy_data_boundary_v1.py'),
        'role': 'EXPLICIT_CHECKED_RECOVERY_API_NOT_AN_ACTIVE_COGNITIVE_ORGAN',
        'original_archives_unchanged': True, 'validation_report': EVIDENCE}
    for obj in (core, head):
        obj.setdefault('maintenance_history', []).append(copy.deepcopy(obj.get('maintenance', {})))
        obj['maintenance'] = {**obj.get('maintenance', {}), 'capability_upgrade': REPAIR,
            'authorship': 'ASSISTANT_USER_AUTHORIZED_REPAIR', 'validation_report': EVIDENCE,
            'parent_main_commit': BASELINE, 'native_capability_gain_claimed': False,
            'formal_generation_changed': False, 'full_integration_gates_required_before_main': True}
        obj['formal_generation_lineage'] = {'artifact': 'canonical/yado-generation-lineage-v1.json',
                                          'artifact_digest': lineage['artifact_digest']}
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
        'effect': 'BIND_REVIEWED_RUNTIME_REPAIRS_AND_COMPLETE_SOURCE_AUDIT; NEXT=' + ledger['open_deficits'][0],
        'validation_required_before_main_merge': ['FULL_REGRESSION', 'FULL_KERNEL_AUDIT_V2', 'CANONICAL_INVARIANT_GUARD'],
        'source_path': EVIDENCE, 'source_digest': file_hash(EVIDENCE)}
    event['event_hash'] = event_hash(event)
    ledger['events'].append(event)
    ledger.update(event_count=len(ledger['events']), tail_event_hash=event['event_hash'],
                  current_head_digest=head['canonical_head_digest'])
    seal(ledger, 'ledger_digest')
    validate_ledger_v2(ledger)
    assert ledger['events'][:-1] == original_events
    for name in touched | {'yado-g2-active-patch-registry-v1.json'}:
        write('canonical/' + name, documents[name])
    write('architecture/evolution-ledger.json', ledger)
    result = audit_current_sources(ROOT)
    if result['errors']:
        raise ValueError('CURRENT_SOURCE_BINDING_FAILED:' + str(result['errors']))
    print(json.dumps({'status': 'BOUND_REQUIRES_FULL_INTEGRATION_GATES',
        'active_runtime_sources': len(sources), 'source_pointer_checks': len(result['checks']),
        'head_digest': head['canonical_head_digest'], 'ledger_event_index': index}))


if __name__ == '__main__':
    main()
