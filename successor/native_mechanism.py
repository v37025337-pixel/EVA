"""Emit a reusable native strategy from a pinned inherited polynomial fitter.

The fitter is inherited unchanged apart from its name and classmethod binding.
The bounded adapter is host-authored. The kernel emits their recombination;
each call selects its own polynomial using training examples only. Emission is
not admission, and neither the profile nor the module contains observed labels.
"""
from __future__ import annotations

import ast
import hashlib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCHEMA = 'yado.native_mechanism.v1'
GRAMMAR_VERSION = 'YADO_EXACT_POLYNOMIAL_NATIVE_MECHANISM_V1'
GRAMMAR_VERSION_V2 = 'YADO_EXACT_POLYNOMIAL_NATIVE_MECHANISM_V2'
DONOR_PATH = 'runtime/yado_evolutionary_multigeneration_lineage_v1.py'
DONOR_SHA256 = 'a471c4a4c53044db94f482ad7d6f2c4758bad3f9d60c68f2252b88759b7a1cc3'


# This is a reviewed emitter template, not supplied source. _fit is transplanted
# from the pinned donor AST; only _MAX_DEGREE varies between emitted modules.
_ADAPTER_SOURCE = '''
from fractions import Fraction
import hashlib
import json
import re

_MAX_DEGREE = 0

def _withhold(reason):
    return {'status': 'WITHHOLD', 'reason': reason, 'source': None,
            'compiled': False, 'synthesis_inputs': 'TRAINING_ONLY',
            'automatic_canonical_promotion': False}

def _training(training):
    if type(training) is not list or not 3 <= len(training) <= 64:
        raise ValueError('MECHANISM_TRAINING_BUDGET')
    clean, seen, key = [], set(), None
    for row in training:
        if type(row) is not dict or set(row) != {'input', 'expected'}:
            raise ValueError('MECHANISM_TRAINING_SCHEMA')
        inputs = row['input']
        if type(inputs) is not dict or len(inputs) != 1:
            raise ValueError('MECHANISM_UNIVARIATE_INPUT_REQUIRED')
        current = next(iter(inputs))
        if type(current) is not str or not re.fullmatch(r'[A-Za-z][A-Za-z0-9_]{0,31}', current):
            raise ValueError('MECHANISM_INPUT_KEY')
        key = current if key is None else key
        if current != key:
            raise ValueError('MECHANISM_INPUT_SIGNATURE_DRIFT')
        x, y = inputs[key], row['expected']
        if type(x) is not int or abs(x) > 10 ** 6:
            raise ValueError('MECHANISM_BOUNDED_INTEGER_INPUT_REQUIRED')
        if type(y) is not int or abs(y) > 10 ** 6:
            raise ValueError('MECHANISM_BOUNDED_INTEGER_OUTPUT_REQUIRED')
        if x in seen:
            raise ValueError('MECHANISM_DUPLICATE_INPUT')
        seen.add(x)
        clean.append({'input': {key: x}, 'expected': y})
    return clean, key

def synthesize(training):
    try:
        rows, key = _training(training)
    except ValueError as exc:
        return _withhold(str(exc))
    examples = [((row['input'][key],), row['expected']) for row in rows]
    model = _fit(examples, _MAX_DEGREE)
    if model.get('kind') == 'WITHHOLD':
        return _withhold('MECHANISM_DEGREE_BUDGET')
    degree = model['degree']
    if len(rows) < degree + 2:
        return _withhold('MECHANISM_INSUFFICIENT_DISTINCT_TRAINING')
    if any(coefficient.denominator != 1 for coefficient in model['coeff']):
        return _withhold('MECHANISM_NONINTEGRAL_COEFFICIENT')
    coefficients = [int(coefficient) for coefficient in model['coeff']]
    expression = str(coefficients[-1])
    for coefficient in reversed(coefficients[:-1]):
        expression = '(' + expression + ' * inputs[' + repr(key) + '] + ' + str(coefficient) + ')'
    source = 'def solve(component_id, program_id, inputs):\\n    return ' + expression + '\\n'
    namespace = {'__builtins__': {}}
    exec(compile(source, '<emitted-native-polynomial>', 'exec'), namespace)
    for row in rows:
        value = namespace['solve']('learned', 'learned', row['input'])
        if type(value) is not int or value != row['expected']:
            return _withhold('MECHANISM_EXPRESSION_TRAINING_MISMATCH')
    training_json = json.dumps(rows, sort_keys=True, separators=(',', ':'), ensure_ascii=True)
    return {
        'status': 'SOURCE_CANDIDATE',
        'source': source,
        'source_sha256': hashlib.sha256(source.encode('utf-8')).hexdigest(),
        'compiled': True,
        'selected': {'profile': 'EXACT_INTEGER_POLYNOMIAL', 'degree': degree,
                     'coefficients': coefficients, 'key': key, 'expression': expression},
        'grammar_stage': 'EMITTED_EXACT_POLYNOMIAL_NATIVE_MECHANISM_V1',
        'training_digest': hashlib.sha256(training_json.encode('utf-8')).hexdigest(),
        'synthesis_inputs': 'TRAINING_ONLY',
        'origin': 'KERNEL_EMITTED_RECOMBINATION_OF_INHERITED_FITTER_AND_HOST_ADAPTER',
        'automatic_canonical_promotion': False,
    }
'''


def _read_donor() -> bytes:
    raw = (ROOT / DONOR_PATH).read_bytes()
    if hashlib.sha256(raw).hexdigest() != DONOR_SHA256:
        raise ValueError('NATIVE_MECHANISM_DONOR_DIGEST_MISMATCH')
    return raw


def profile(max_degree: int) -> dict:
    """Describe a bounded emitter; no task examples are accepted here."""
    if type(max_degree) is not int or not 0 <= max_degree <= 5:
        raise ValueError('NATIVE_MECHANISM_MAX_DEGREE')
    _read_donor()
    return {'grammar_version': GRAMMAR_VERSION if max_degree <= 3 else GRAMMAR_VERSION_V2,
            'donor': {'path': DONOR_PATH, 'sha256': DONOR_SHA256},
            'max_degree': max_degree}


def _checked_profile(value: dict) -> dict:
    if type(value) is not dict or set(value) != {'grammar_version', 'donor', 'max_degree'}:
        raise ValueError('NATIVE_MECHANISM_PROFILE_SCHEMA')
    degree = value['max_degree']
    expected = profile(degree)
    donor = value['donor']
    if (type(value['grammar_version']) is not str or type(donor) is not dict
            or set(donor) != {'path', 'sha256'}
            or any(type(donor[key]) is not str for key in ('path', 'sha256'))
            or value != expected):
        raise ValueError('NATIVE_MECHANISM_PROFILE_MISMATCH')
    return expected


def _donor_fit() -> ast.FunctionDef:
    tree = ast.parse(_read_donor().decode('utf-8'))
    cls = next(node for node in tree.body
               if isinstance(node, ast.ClassDef) and node.name == 'PolynomialCodeLineageGene')
    fit = next(node for node in cls.body
               if isinstance(node, ast.FunctionDef) and node.name == 'fit')
    if [arg.arg for arg in fit.args.args] != ['cls', 'examples', 'max_degree']:
        raise ValueError('NATIVE_MECHANISM_DONOR_INTERFACE')
    fit.name = '_fit'
    fit.decorator_list = []
    fit.args.args = fit.args.args[1:]
    return fit


def emit(candidate_profile: dict) -> str:
    """Return the exact reusable module for the supported, pinned profile."""
    checked = _checked_profile(candidate_profile)
    # Preserve the original module byte-for-byte for every V1 degree. V2
    # expands the bound within the same inherited polynomial fitting family.
    adapter = _ADAPTER_SOURCE
    if checked['grammar_version'] == GRAMMAR_VERSION_V2:
        adapter = adapter.replace('EMITTED_EXACT_POLYNOMIAL_NATIVE_MECHANISM_V1',
                                  'EMITTED_EXACT_POLYNOMIAL_NATIVE_MECHANISM_V2')
    tree = ast.parse(adapter)
    for node in tree.body:
        if (isinstance(node, ast.Assign) and len(node.targets) == 1
                and isinstance(node.targets[0], ast.Name) and node.targets[0].id == '_MAX_DEGREE'):
            node.value = ast.Constant(checked['max_degree'])
    tree.body.insert(0, ast.Expr(ast.Constant(
        'Reusable polynomial synthesizer; inherited fitter plus host-authored bounded adapter. '
        + DONOR_PATH + ' @ ' + DONOR_SHA256)))
    tree.body.append(_donor_fit())
    ast.fix_missing_locations(tree)
    return ast.unparse(tree) + '\n'


def build_candidate(max_degree: int) -> dict:
    candidate_profile = profile(max_degree)
    source = emit(candidate_profile)
    return {'schema': SCHEMA, 'profile': candidate_profile, 'source': source,
            'source_sha256': hashlib.sha256(source.encode('utf-8')).hexdigest()}


def _validated_source(candidate: dict) -> str:
    if type(candidate) is not dict or set(candidate) != {'schema', 'profile', 'source', 'source_sha256'}:
        raise ValueError('NATIVE_MECHANISM_CANDIDATE_SCHEMA')
    # Keep the immutable string checked below for execution. A caller changing
    # its dictionary later cannot replace the source after validation.
    schema, source, digest = candidate['schema'], candidate['source'], candidate['source_sha256']
    if (type(schema) is not str or schema != SCHEMA
            or type(source) is not str or type(digest) is not str):
        raise ValueError('NATIVE_MECHANISM_CANDIDATE_SCHEMA')
    expected = emit(candidate['profile'])
    if source != expected or hashlib.sha256(source.encode('utf-8')).hexdigest() != digest:
        raise ValueError('NATIVE_MECHANISM_SOURCE_MISMATCH')
    return source


def validate_candidate(candidate: dict) -> None:
    """Reject any supplied code that differs from the trusted emitter's bytes."""
    _validated_source(candidate)


def synthesize(candidate: dict, training: list) -> dict:
    """Execute only re-emitted code; unsupported training returns WITHHOLD."""
    source = _validated_source(candidate)
    namespace: dict = {}
    exec(compile(source, '<validated-native-mechanism>', 'exec'), namespace)
    result = namespace['synthesize'](training)
    return {**result, 'mechanism_source_sha256': hashlib.sha256(source.encode('utf-8')).hexdigest()}


def inferred_degree(training: list, max_degree: int = 3) -> int | None:
    """Find the smallest supported degree using training only, or no proposal."""
    result = synthesize(build_candidate(max_degree), training)
    if not result.get('source'):
        return None
    return result['selected']['degree']


__all__ = ['profile', 'emit', 'build_candidate', 'validate_candidate', 'synthesize', 'inferred_degree']
