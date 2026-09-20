"""Check current source pointers independently from the aggregate manifest.

Historical receipts and original admission hashes deliberately retain old bytes.
"""
import hashlib
import json
from pathlib import Path


SOURCES = {
    'repair': 'runtime/yado_ambiguity_aware_program_repair_v11.py',
    'planner': 'runtime/yado_work_budget_adaptive_contingent_planner_v2.py',
    'clock': 'runtime/yado_g2_cognitive_clock_v1.py',
    'genome': 'runtime/yado_evolutionary_genome_v1.py',
    'layer': 'runtime/yado_g2_experience_conditioned_cognitive_layer_v4.py',
    'native': 'runtime/yado_active_native_learning_v1.py',
    'cognitive': 'successor/cognitive.py',
}
SPECIFICATIONS = [
    ('yado-unified-core-v1.json', ('program_execution', 'source_sha256'), 'repair'),
    ('yado-main-head-g2.json', ('unified_core', 'bounded_program_repair_source_sha256'), 'repair'),
    ('yado-unified-core-v1.json', ('thinking_plateau_v2', 'source_sha256'), 'planner'),
    ('yado-main-head-g2.json', ('unified_core', 'thinking_ceiling_source_sha256'), 'planner'),
    ('yado-g2-cognitive-temporal-kernel-v1.json', ('clock_runtime_sha256',), 'clock'),
    ('yado-unified-core-v1.json', ('cognitive_temporal_kernel_v1', 'runtime_sha256'), 'clock'),
    ('yado-algorithm-provenance-registry-v1.json', ('current_g2_binding', 'cognitive_temporal_kernel_source_sha256'), 'clock'),
    ('yado-g2-evolutionary-genome-v1.json', ('runtime_sha256',), 'genome'),
    ('yado-unified-core-v1.json', ('evolutionary_genome_v1', 'runtime_sha256'), 'genome'),
    ('yado-algorithm-provenance-registry-v1.json', ('current_g2_binding', 'evolutionary_genome_source_sha256'), 'genome'),
    ('yado-g2-experience-conditioned-cognitive-layer-v4.json', ('runtime_sha256',), 'layer'),
    ('yado-unified-core-v1.json', ('experience_conditioned_cognitive_layer_v4', 'runtime_sha256'), 'layer'),
    ('yado-algorithm-provenance-registry-v1.json', ('current_g2_binding', 'experience_conditioned_cognitive_layer_source_sha256'), 'layer'),
    ('yado-active-native-loop-v1.json', ('controller_source_sha256',), 'cognitive'),
    ('yado-active-native-loop-v1.json', ('runtime_sha256',), 'native'),
    ('yado-unified-core-v1.json', ('active_native_loop_v1', 'runtime_sha256'), 'native'),
    ('yado-main-head-g2.json', ('active_native_loop_v1', 'runtime_sha256'), 'native'),
    ('yado-algorithm-provenance-registry-v1.json', ('current_g2_binding', 'active_native_loop_v1', 'runtime_sha256'), 'native'),
]


def audit_current_sources(root, specifications=None, sources=None):
    root = Path(root).resolve()
    complete = specifications is None and sources is None
    specifications = SPECIFICATIONS if specifications is None else specifications
    sources = SOURCES if sources is None else sources
    documents, results = {}, []
    for name, keys, source_key in specifications:
        result = {'manifest': 'canonical/' + name, 'field': '.'.join(keys),
                  'source': sources[source_key]}
        try:
            if name not in documents:
                documents[name] = json.loads((root / 'canonical' / name).read_text())
            value = documents[name]
            for key in keys:
                value = value[key]
            actual = hashlib.sha256((root / sources[source_key]).read_bytes()).hexdigest()
            result.update(declared=value, actual=actual, valid=value == actual)
        except (OSError, ValueError, KeyError, TypeError) as exc:
            result.update(valid=False, error=type(exc).__name__ + ':' + str(exc))
        results.append(result)
    if complete:
        try:
            patch_name = 'yado-g2-active-patch-registry-v1.json'
            patches = json.loads((root / 'canonical' / patch_name).read_text())
            for row in patches['patches']:
                actual = hashlib.sha256((root / row['source']).read_bytes()).hexdigest()
                for field in ('source_sha256', 'expected_source_sha256'):
                    results.append({'manifest': 'canonical/' + patch_name,
                                    'field': row['patch_id'] + '.' + field, 'source': row['source'],
                                    'declared': row[field], 'actual': actual, 'valid': row[field] == actual})
            prov = documents['yado-algorithm-provenance-registry-v1.json']
            for row in prov['mechanisms']:
                if row.get('adapter_source'):
                    actual = hashlib.sha256((root / row['adapter_source']).read_bytes()).hexdigest()
                    results.append({'manifest': 'canonical/yado-algorithm-provenance-registry-v1.json',
                                    'field': row['mechanism_id'] + '.adapter_source_sha256',
                                    'source': row['adapter_source'], 'actual': actual,
                                    'declared': row['adapter_source_sha256'],
                                    'valid': row['adapter_source_sha256'] == actual})
        except (OSError, ValueError, KeyError, TypeError) as exc:
            results.append({'manifest': 'current patch and provenance bindings', 'valid': False,
                            'error': type(exc).__name__ + ':' + str(exc)})
    return {'status': 'PASS' if all(row['valid'] for row in results) else 'FAIL_CURRENT_SOURCE_BINDINGS',
            'checks': results, 'errors': [row for row in results if not row['valid']]}
