"""Runtime adapters for the admitted, bounded V1--V6 mechanisms.

The adapter is assistant-authored. YADO selects programs from the existing
host-authored grammar. Only scalar examples enter synthesis; no supplied code
or downloaded package is executed. This is not a general Python sandbox.
"""
from __future__ import annotations

import copy
import hashlib
import json
import re
import urllib.parse

import yado_external_source_evolution_v1 as v1
import yado_autonomous_meta_source_evolution_v2 as v2
import yado_autonomous_grammar_extension_v3 as v3
import yado_autonomous_meta_grammar_evolution_v4 as v4
import yado_autonomous_external_library_discovery_v5 as v5
import yado_autonomous_open_catalog_discovery_v6 as v6


def source_sha(source):
    return hashlib.sha256(source.encode('utf-8')).hexdigest()


def validate_source_goal(spec):
    if set(spec) != {'domain', 'training', 'validation', 'queries'}:
        raise ValueError('SOURCE_GOAL_REQUIRES_TRAINING_VALIDATION_AND_UNLABELLED_QUERIES')
    for name, lower, upper in (('training', 3, 64), ('validation', 2, 32), ('queries', 1, 32)):
        if not isinstance(spec[name], list) or not lower <= len(spec[name]) <= upper:
            raise ValueError('SOURCE_EXAMPLE_BUDGET:' + name)
    seen, signature, output_kind = set(), None, None
    def scalar(value):
        return (type(value) is bool or type(value) is int and abs(value) <= 10**6
                or type(value) is str and len(value) <= 256)
    for partition in ('training', 'validation', 'queries'):
        for row in spec[partition]:
            required = {'input'} if partition == 'queries' else {'input', 'expected'}
            if not isinstance(row, dict) or set(row) != required:
                raise ValueError('SOURCE_EXAMPLE_SCHEMA')
            inputs = row['input']
            if (not isinstance(inputs, dict) or not 1 <= len(inputs) <= 2
                    or any(type(k) is not str or not re.fullmatch(r'[A-Za-z][A-Za-z0-9_]{0,31}', k)
                           or not scalar(v) for k, v in inputs.items())):
                raise ValueError('BOUNDED_SCALAR_INPUTS_REQUIRED')
            current = [(k, type(inputs[k]).__name__) for k in sorted(inputs)]
            signature = current if signature is None else signature
            if current != signature:
                raise ValueError('SOURCE_INPUT_SIGNATURE_DRIFT')
            marker = json.dumps(inputs, sort_keys=True)
            if marker in seen:
                raise ValueError('SOURCE_PARTITIONS_MUST_HAVE_DISTINCT_INPUTS')
            seen.add(marker)
            if partition != 'queries':
                if not scalar(row['expected']):
                    raise ValueError('BOUNDED_SCALAR_OUTPUT_REQUIRED')
                kind = type(row['expected']).__name__
                output_kind = kind if output_kind is None else output_kind
                if kind != output_kind:
                    raise ValueError('SOURCE_OUTPUT_SIGNATURE_DRIFT')
    return copy.deepcopy(spec)


def synthesize_source(training, strategy):
    """No validation labels or query answers are accepted by this seam."""
    cases = copy.deepcopy(training)
    if strategy not in {'native_v2', 'native_v3', 'native_v4'}:
        raise ValueError('UNKNOWN_NATIVE_STRATEGY')
    signature, output_kind, keys = v2.infer_signature(cases)
    route = (signature, output_kind)
    stage = 'V2'
    if route == (('str',), 'str') and strategy in {'native_v3', 'native_v4'}:
        namespace = {'score_program': v2.score_program}
        exec(compile(v3.extension_function_source(), '<admitted-v3-grammar>', 'exec'), namespace)
        selected = namespace['synth_str_to_str'](cases, keys)
        stage = 'V3'
    elif route == (('int',), 'bool') and strategy == 'native_v4':
        namespace = {'score_program': v2.score_program}
        exec(compile(v4.meta_strategy_extension_source(), '<admitted-v4-meta-grammar>', 'exec'), namespace)
        rule = namespace['derive_missing_route_rule'](cases)
        exec(compile(rule['synth_function_source'], '<native-derived-operator>', 'exec'), namespace)
        selected = namespace[rule['synth_function_name']](cases, keys)
        stage = 'V4'
    else:
        selected = v2.synthesize_generic(cases)
    source, ast_evidence = v2.inject_generated_helpers(v1.seed_source(), {'learned': selected})
    # The V1 seed has no annotations; its future import is unnecessary for the
    # isolated function namespace and is removed before compilation and freeze.
    source = source.removeprefix('from __future__ import annotations\n')
    compile(source, '<native-candidate>', 'exec')
    return {'source': source, 'source_sha256': source_sha(source), 'compiled': True,
            'selected': selected, 'ast_evidence': ast_evidence, 'grammar_stage': stage,
            'training_digest': v5.sha_json(training), 'synthesis_inputs': 'TRAINING_ONLY',
            'origin': 'YADO_SELECTION_FROM_ADMITTED_HOST_GRAMMAR'}


def execute_source(candidate, inputs):
    source = candidate['source']
    if source_sha(source) != candidate['source_sha256']:
        raise ValueError('NATIVE_SOURCE_DIGEST_MISMATCH')
    # Only reviewed grammar emission is a caller of this function. Restrict
    # builtins as defense in depth; never advertise this as an untrusted-code API.
    namespace = {'__builtins__': {'str': str, 'int': int, 'len': len, 'set': set,
                 'sum': sum, 'zip': zip, 'abs': abs, 'range': range, 'KeyError': KeyError}}
    exec(compile(source, '<native-candidate>', 'exec'), namespace)
    return [namespace['solve']('learned', 'learned', copy.deepcopy(row)) for row in inputs]


def connect_library():
    """Live V6 discovery and V5 artifact inspection; validation is a later event."""
    shortlist, discovery = v6.discover_from_open_catalog()
    records = v6.fetch_candidate_metadata(shortlist)
    selected, selection = v6.select_discovered_library(discovery, records)
    payload = records[selected]['payload']
    version = str(payload['info']['version'])
    artifact = v5.choose_wheel(payload)
    raw, fetch = v5.guarded_fetch(artifact['url'], accept='application/octet-stream', max_bytes=v5.MAX_WHEEL_BYTES)
    actual = v5.sha_bytes(raw)
    if actual != artifact['expected_sha256']:
        raise ValueError('NATIVE_LIBRARY_ARTIFACT_DIGEST_MISMATCH')
    metadata = v5.inspect_wheel(raw, selected, version)
    dependency = metadata['selected_dependency']
    dep_payload, dep_proof = v5.fetch_json(v5.PYPI_JSON.format(name=urllib.parse.quote(dependency)))
    dep_version = str((dep_payload.get('info') or {}).get('version') or '')
    if not version or not dep_version:
        raise ValueError('NATIVE_LIBRARY_VERSION_MISSING')
    bundle = {'objective': 'html_xml_parser', 'package': v5.normalize_name(selected),
              'version': version, 'filename': artifact['filename'], 'artifact_sha256': actual,
              'dependency': v5.normalize_name(dependency), 'dependency_version': dep_version}
    return {'bundle': bundle, 'bundle_sha256': v5.sha_json(bundle), 'discovery': discovery,
            'selection': selection, 'artifact': artifact, 'artifact_fetch': fetch,
            'wheel_metadata': metadata, 'dependency_source': dep_proof,
            'read_only': True, 'package_executed': False, 'package_installed': False}


def verify_library(candidate):
    bundle = candidate['bundle']
    if v5.sha_json(bundle) != candidate['bundle_sha256']:
        raise ValueError('NATIVE_LIBRARY_BUNDLE_DIGEST_MISMATCH')
    proof = v5.sealed_simple_validation(bundle['package'], bundle['filename'], bundle['artifact_sha256'])
    passed = (proof['matched'] is True and v5.sha_json(bundle) == candidate['bundle_sha256']
              and bundle['artifact_sha256'] == candidate['artifact']['expected_sha256'])
    return {'passed': passed, 'scope': 'SEPARATE_PYPI_SIMPLE_AFTER_BUNDLE_FREEZE',
            'checks': 1, 'proof': proof}
