"""Versioned activation and causal memory for compositional native programs.

The maintainer supplies the operator grammar. The kernel selects programs from
training examples and can compose programs retained after independent checks.
"""
from .archive import file_sha
from .kernel import ROOT
from .compositional_source import GRAMMAR, GRAMMAR_V2, GRAMMARS

STRATEGY = 'native_compositional_v1'
COST = 4
ACTIVATE = 'COG_ACTIVATE_COMPOSITIONAL_SYNTHESIS'
DEACTIVATE = 'COG_DEACTIVATE_COMPOSITIONAL_SYNTHESIS'
SOURCES = ('successor/compositional_binding.py', 'successor/compositional_source.py',
           'successor/program_goals.py',
           'runtime/yado_active_native_learning_v1.py')
MEMORY_LIMIT = 16

# Approved predecessor bytes, captured before the V2 change and checked against
# git HEAD. This exact allowlist is implementation-owned, never journal-derived.
# Historical programs are re-synthesized with V1; these pins do not attest the
# current implementation or authorize arbitrary historical source bundles.
_LEGACY_V1_SOURCES = {
    'successor/compositional_binding.py': '8f5d445a98f141ad1eb2846f8615f377e101ae885a4f137f38d10fa5628b1032',
    'successor/compositional_source.py': 'd9741e99432cb1e07d56f1e2543b90b1b3b1f3b2d12b91bacca9993c4f8fcdaf',
    'successor/program_goals.py': '438861282ebee4ef593eafbcc3b75f69870f991731ad0612a7df15dfeae14843',
    'runtime/yado_active_native_learning_v1.py': 'a700ffd7c09d078d605e0218b48e899537f95535ae5a5f18ffd4ab748694085f',
}


def _activation(sources, grammar):
    if grammar not in GRAMMARS:
        raise ValueError('COMPOSITION_GRAMMAR_VERSION')
    body = {'kind': ACTIVATE, 'strategy': STRATEGY, 'cost': COST,
            'sources': dict(sources),
            'grammar_authorship': 'MAINTAINER_AUTHORIZED_BY_USER',
            'program_selection': 'KERNEL_TRAINING_ONLY',
            'memory_origin': 'VERIFIED_PRIOR_PROGRAMS', 'canonical_promotion': False}
    if grammar != GRAMMAR:
        body['grammar'] = grammar
    return body


def activation(*, grammar=GRAMMAR):
    return _activation({name: file_sha(ROOT / name) for name in SOURCES}, grammar)


def activation_grammar(body):
    """Verify the whole activation against live pins or one approved V1 body."""
    from .kernel import fingerprint
    if type(body) is dict:
        grammar = body.get('grammar', GRAMMAR)
        if grammar in GRAMMARS:
            if fingerprint(body) == fingerprint(activation(grammar=grammar)):
                return grammar
            if fingerprint(body) == fingerprint(_activation(_LEGACY_V1_SOURCES, GRAMMAR)):
                return GRAMMAR
    raise ValueError('COGNITIVE_COMPOSITIONAL_BINDING_PROVENANCE')


def deactivation():
    return {'kind': DEACTIVATE, 'strategy': STRATEGY, 'reason': 'EXPLICIT_ROLLBACK'}


def active(records):
    return next((r['kind'] == ACTIVATE for r in reversed(records)
                 if r['kind'] in {ACTIVATE, DEACTIVATE}), False)


def grammar_at(records):
    """Resolve the activation at this historical prefix, never today's profile."""
    for record in reversed(records):
        if record['kind'] == DEACTIVATE:
            break
        if record['kind'] == ACTIVATE:
            return activation_grammar({k: v for k, v in record.items() if k not in {'tick', 'event_hash'}})
    return GRAMMAR


def memories(records, *, grammar=GRAMMAR):
    from .compositional_source import SCHEMA
    values, seen = [], set()
    for r in reversed(records):
        result = r.get('result') or {}
        if (r['kind'] == 'COG_FINISH' and r['status'] == 'VALIDATED_ON_HOLDOUT'
                and result.get('schema') == SCHEMA and result['source_sha256'] not in seen
                and (grammar == GRAMMAR_V2 or result.get('grammar') == GRAMMAR)):
            values.append(result)
            seen.add(result['source_sha256'])
            if len(values) == MEMORY_LIMIT:
                break
    return values


def synthesize(training, records, *, use_memory=True):
    from .compositional_source import synthesize as generate
    grammar = grammar_at(records)
    candidate = generate(training, memories=memories(records, grammar=grammar) if use_memory else (), grammar=grammar)
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
