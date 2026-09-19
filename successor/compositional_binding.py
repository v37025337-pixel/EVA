"""Versioned activation and causal memory for compositional native programs.

The maintainer supplies the operator grammar. The kernel selects programs from
training examples and can compose programs retained after independent checks.
"""
from .archive import file_sha
from .kernel import ROOT

STRATEGY = 'native_compositional_v1'
COST = 4
ACTIVATE = 'COG_ACTIVATE_COMPOSITIONAL_SYNTHESIS'
DEACTIVATE = 'COG_DEACTIVATE_COMPOSITIONAL_SYNTHESIS'
SOURCES = ('successor/compositional_binding.py', 'successor/compositional_source.py',
           'successor/program_goals.py',
           'runtime/yado_active_native_learning_v1.py')
MEMORY_LIMIT = 16


def activation():
    return {'kind': ACTIVATE, 'strategy': STRATEGY, 'cost': COST,
            'sources': {name: file_sha(ROOT / name) for name in SOURCES},
            'grammar_authorship': 'MAINTAINER_AUTHORIZED_BY_USER',
            'program_selection': 'KERNEL_TRAINING_ONLY',
            'memory_origin': 'VERIFIED_PRIOR_PROGRAMS', 'canonical_promotion': False}


def deactivation():
    return {'kind': DEACTIVATE, 'strategy': STRATEGY, 'reason': 'EXPLICIT_ROLLBACK'}


def active(records):
    return next((r['kind'] == ACTIVATE for r in reversed(records)
                 if r['kind'] in {ACTIVATE, DEACTIVATE}), False)


def memories(records):
    from .compositional_source import SCHEMA
    values, seen = [], set()
    for r in reversed(records):
        result = r.get('result') or {}
        if (r['kind'] == 'COG_FINISH' and r['status'] == 'VALIDATED_ON_HOLDOUT'
                and result.get('schema') == SCHEMA and result['source_sha256'] not in seen):
            values.append(result)
            seen.add(result['source_sha256'])
            if len(values) == MEMORY_LIMIT:
                break
    return values


def synthesize(training, records, *, use_memory=True):
    from .compositional_source import synthesize as generate
    candidate = generate(training, memories=memories(records) if use_memory else ())
    if not candidate.get('source'):
        raise ValueError('COMPOSITIONAL_SYNTHESIS_WITHHOLD:' + str(candidate.get('reason')))
    return candidate


def verify_execution(result, spec):
    """Recompute frozen-program outputs; stored labels cannot manufacture PASS."""
    from .compositional_source import execute
    for partition, field in (('training', 'training_predictions'),
                             ('validation', 'validation_predictions'), ('queries', 'predictions')):
        from .kernel import fingerprint
        observed = execute(result, [row['input'] for row in spec[partition]])
        if field not in result or fingerprint(result[field]) != fingerprint(observed):
            raise ValueError('COMPOSITIONAL_EXECUTION_PROVENANCE:' + partition)
