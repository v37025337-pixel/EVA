"""Explicit admission of bounded training-only native synthesis routes."""
from pathlib import Path

from .archive import file_sha

STRATEGY = 'native_evolved_v2'
COST = 4
ROOT = Path(__file__).resolve().parents[1]
SOURCES = ('successor/native_binding.py', 'successor/evolved_kernel.py',
           'successor/evolved_kernel_v2.py', 'successor/arithmetic_source.py',
           'successor/generalized_source_v2.py', 'successor/generalized_boolean_v2.py',
           'successor/inductive_mechanism.py')


def activation():
    return {'kind': 'COG_ACTIVATE_NATIVE_SYNTHESIS', 'strategy': STRATEGY, 'cost': COST,
            'sources': {name: file_sha(ROOT / name) for name in SOURCES},
            'binding_authorship': 'ASSISTANT_AUTHORIZED_BY_USER',
            'program_selection': 'KERNEL_TRAINING_ONLY', 'canonical_promotion': False}


def active(records):
    return any(r['kind'] == 'COG_ACTIVATE_NATIVE_SYNTHESIS' for r in records)


def synthesize(training):
    """Try the admitted V2 route first, then a bounded typed inductive fallback.

    Both routes consume training examples only.  The inductive fallback derives a
    frozen primitive profile from behavior when the predecessor has no source;
    validation labels remain outside this binding and are consumed only by the
    cognitive verifier after source freeze.
    """
    from .evolved_kernel_v2 import synthesize_program_v2

    predecessor = synthesize_program_v2(training)
    if predecessor.get('source'):
        return {**predecessor, 'binding_strategy': STRATEGY,
                'binding_route': 'EVOLVED_V2'}

    from .inductive_mechanism import build_candidate, synthesize as synthesize_inductive
    mechanism = build_candidate(training)
    if mechanism is None:
        raise ValueError('BOUND_V2_AND_INDUCTIVE_SYNTHESIS_WITHHOLD')
    candidate = synthesize_inductive(mechanism, training)
    if not candidate.get('source'):
        raise ValueError('BOUND_V2_AND_INDUCTIVE_SYNTHESIS_WITHHOLD')
    return {
        **candidate,
        'binding_strategy': STRATEGY,
        'binding_route': 'INDUCTIVE_V1',
        'predecessor_status': predecessor.get('status'),
        'inductive_mechanism_sha256': mechanism['source_sha256'],
        'inductive_profile': mechanism['profile'],
    }
