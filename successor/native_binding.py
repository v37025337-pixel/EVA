"""Explicit admission of the existing training-only V2 synthesis route."""
from pathlib import Path

from .archive import file_sha

STRATEGY = 'native_evolved_v2'
COST = 4
ROOT = Path(__file__).resolve().parents[1]
SOURCES = ('successor/native_binding.py', 'successor/evolved_kernel.py',
           'successor/evolved_kernel_v2.py', 'successor/arithmetic_source.py',
           'successor/generalized_source_v2.py', 'successor/generalized_boolean_v2.py')


def activation():
    return {'kind': 'COG_ACTIVATE_NATIVE_SYNTHESIS', 'strategy': STRATEGY, 'cost': COST,
            'sources': {name: file_sha(ROOT / name) for name in SOURCES},
            'binding_authorship': 'ASSISTANT_AUTHORIZED_BY_USER',
            'program_selection': 'KERNEL_TRAINING_ONLY', 'canonical_promotion': False}


def active(records):
    return any(r['kind'] == 'COG_ACTIVATE_NATIVE_SYNTHESIS' for r in records)


def synthesize(training):
    from .evolved_kernel_v2 import synthesize_program_v2
    candidate = synthesize_program_v2(training)
    if not candidate.get('source'):
        raise ValueError('BOUND_V2_SYNTHESIS_WITHHOLD')
    return {**candidate, 'binding_strategy': STRATEGY}
