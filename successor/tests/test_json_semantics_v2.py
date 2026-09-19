"""Versioned JSON equality must not reinterpret frozen V1 programs or history."""
import copy
import unittest
from unittest.mock import patch

from successor import cognitive, compositional_binding as binding
from successor import compositional_source as engine
from successor.kernel import fingerprint


V2 = 'YADO_TYPED_COMPOSITION_V2'
# Captured before the repair; each digest was checked against git HEAD bytes.
LEGACY_PINS = {
    'successor/compositional_binding.py': '8f5d445a98f141ad1eb2846f8615f377e101ae885a4f137f38d10fa5628b1032',
    'successor/compositional_source.py': 'd9741e99432cb1e07d56f1e2543b90b1b3b1f3b2d12b91bacca9993c4f8fcdaf',
    'successor/program_goals.py': '438861282ebee4ef593eafbcc3b75f69870f991731ad0612a7df15dfeae14843',
    'runtime/yado_active_native_learning_v1.py': 'a700ffd7c09d078d605e0218b48e899537f95535ae5a5f18ffd4ab748694085f',
}


def legacy_activation():
    return {'kind': binding.ACTIVATE, 'strategy': binding.STRATEGY, 'cost': 4,
            'sources': dict(LEGACY_PINS),
            'grammar_authorship': 'MAINTAINER_AUTHORIZED_BY_USER',
            'program_selection': 'KERNEL_TRAINING_ONLY',
            'memory_origin': 'VERIFIED_PRIOR_PROGRAMS', 'canonical_promotion': False}


def row(left, right, expected):
    return {'input': {'left': left, 'right': right}, 'expected': expected}


def legacy_training():
    return [row('{"a":1,"b":2}', '{ "a": 1, "b": 2 }', True),
            row('{"a":3,"b":4}', '{"a":3,"b":5}', False),
            row('[1,2]', '[1, 2]', True),
            row('{"k":[true,null]}', '{"k": [false,null]}', False)]


def comparison(name, grammar=V2):
    program = engine._call(name,
                           engine._call('json_parse', engine._node('input', key='left')),
                           engine._call('json_parse', engine._node('input', key='right')))
    source = engine._emit(program)
    return {'schema': engine.SCHEMA, 'grammar': grammar, 'program': program,
            'source': source, 'source_sha256': engine._sha(source),
            'input_signature': [['left', 'str'], ['right', 'str']],
            'training_digest': '0' * 64, 'parent_source_sha256': [],
            'synthesis_inputs': 'TRAINING_ONLY'}


def legacy_records():
    """Small real replay contract, with no kernel, SQLite, or network access."""
    records = []
    def add(body):
        event = {**body, 'tick': len(records) + 1, 'event_hash': 'a' * 64}
        records.append(event)
        return event
    add(legacy_activation())
    spec = {'schema': 'yado.native_program_goal.v1', 'domain': 'native_source',
            'training': legacy_training(),
            'validation': [row('{"x":1,"y":2}', '{"y":2,"x":1}', True),
                           row('[3,4]', '[4,3]', False)],
            'queries': [{'input': {'left': '{"c":6,"d":7}', 'right': '{"d":7,"c":6}'}}]}
    goal = add({'kind': 'COG_GOAL', 'spec': spec, 'spec_digest': fingerprint(spec),
                'mode': 'no_memory', 'budget': 4})
    choice = {'strategy': binding.STRATEGY, 'cost': 4, 'probability': 0.5}
    workspace = {'goal_digest': fingerprint(spec), 'remaining_budget': 4, 'proposals': [choice]}
    decision = add({'kind': 'COG_DECIDE', 'goal_id': goal['tick'], 'choice': choice,
                    'workspace': workspace, 'workspace_digest': fingerprint(workspace)})
    candidate = engine.synthesize(spec['training'])
    result = {**candidate, 'status': 'CANDIDATE', 'source_context': cognitive.goal_context(spec)}
    for partition, field in [('training', 'training_predictions'),
                             ('validation', 'validation_predictions'), ('queries', 'predictions')]:
        result[field] = engine.execute(candidate, [r['input'] for r in spec[partition]])
    execution = add({'kind': 'COG_EXECUTE', 'goal_id': goal['tick'], 'decision_tick': decision['tick'],
                     'workspace_digest': decision['workspace_digest'], 'result': result})
    verification = add(cognitive.CognitiveLoop(None)._verify(
        {'id': goal['tick'], 'spec': spec, 'execution': execution, 'decision': decision}))
    add({'kind': 'COG_REFLECT', 'goal_id': goal['tick'], 'verification_tick': verification['tick'],
         'success': False, 'domain': 'native_source', 'strategy': binding.STRATEGY,
         'context': cognitive.goal_context(spec), 'cost': 4, 'brier_error': 0.25,
         'workspace_digest': decision['workspace_digest']})
    add({'kind': 'COG_FINISH', 'goal_id': goal['tick'], 'status': 'WITHHOLD', 'result': None, 'spent': 4})
    return records


class JsonSemanticsV2Tests(unittest.TestCase):
    def test_nested_objects_ignore_key_order_but_arrays_preserve_order(self):
        cases = [row('{"a":{"x":1,"y":[{"m":2,"n":3}]},"b":null}',
                     '{"b":null,"a":{"y":[{"n":3,"m":2}],"x":1}}', True),
                 row('[1,{"a":2}]', '[{"a":2},1]', False),
                 row('{"v":true}', '{"v":1}', False),
                 row('{"v":false}', '{"v":0}', False),
                 row('{"v":null}', '{}', False),
                 row('"line\\n\\u00e9"', '"line\\né"', True),
                 row('"line\\n"', '"line\\\\n"', False),
                 row('null', 'null', True)]
        for name, invert in [('json_equal_v2', False), ('json_not_equal_v2', True)]:
            observed = engine.execute(comparison(name), [r['input'] for r in cases])
            self.assertEqual(observed, [r['expected'] != invert for r in cases])

    def test_v1_freeze_and_operations_remain_order_observant(self):
        left, right = {'a': 1, 'b': 2}, {'b': 2, 'a': 1}
        self.assertNotEqual(engine._freeze(left), engine._freeze(right))
        self.assertFalse(engine._primitive('equal', left, right))
        self.assertTrue(engine._primitive('not_equal', left, right))
        self.assertNotEqual(engine._primitive('json_compact', left), engine._primitive('json_compact', right))

    def test_v1_rejects_relabelled_v2_operation(self):
        with self.assertRaisesRegex(ValueError, 'COMPOSITION_CALL_SCHEMA'):
            engine.validate(comparison('json_equal_v2', grammar=engine.GRAMMAR))

    def test_v2_does_not_expand_supported_json_domain(self):
        for text in ['NaN', 'Infinity', '1.5', '"\\ud800"']:
            with self.subTest(text=text), self.assertRaises((ValueError, UnicodeError)):
                engine.execute(comparison('json_equal_v2'), [{'left': text, 'right': text}])

    def test_training_only_v2_synthesis_and_frozen_v1_candidate(self):
        # Additional labelled reorder examples belong to training, not holdout.
        training = legacy_training() + [row('{"c":3,"d":4}', '{"d":4,"c":3}', True),
                                        row('{"flag":true}', '{"flag":1}', False)]
        candidate = engine.synthesize(training, grammar=V2)
        self.assertEqual(candidate['grammar'], V2)
        self.assertIn('json_equal_v2', candidate['source'])
        self.assertEqual(engine.execute(candidate, [{'left': '{"u":[{"r":9,"s":8}],"v":null}',
                                                    'right': '{"v":null,"u":[{"s":8,"r":9}]}'}]), [True])
        old = engine.synthesize(legacy_training())
        self.assertEqual(old['source_sha256'], 'ee73b1eed5c0cae3d9648c9691964db03e786fe87d22e7143e20970bcaaa4990')
        self.assertEqual(old['training_digest'], 'f06f52d82a2df555b0212a181c4a1bcedf9c7c1db2fe0a6d7b871f98721d1454')
        self.assertEqual((old['search_states'], old['search_attempts']), (271, 864))

    def test_versioned_catalog_and_memory(self):
        self.assertNotIn('json_equal_v2', [x['name'] for x in engine.catalog()['operators']])
        self.assertIn('json_equal_v2', [x['name'] for x in engine.catalog(grammar=V2)['operators']])
        with self.assertRaisesRegex(ValueError, 'COMPOSITION_MEMORY_GRAMMAR'):
            engine.synthesize(legacy_training(), memories=[comparison('json_equal_v2')])
        old = comparison('equal', grammar=engine.GRAMMAR)
        engine.synthesize(legacy_training(), memories=[old], grammar=V2)


class HistoricalProfileTests(unittest.TestCase):
    def test_exact_legacy_activation_and_body_tampering(self):
        self.assertEqual(binding.activation_grammar(legacy_activation()), engine.GRAMMAR)
        for mutate in [lambda r: r['sources'].__setitem__('successor/compositional_source.py', 'f' * 64),
                       lambda r: r.__setitem__('canonical_promotion', True),
                       lambda r: r.__setitem__('grammar', V2),
                       lambda r: r.__setitem__('cost', True)]:
            event = legacy_activation()
            mutate(event)
            with self.assertRaisesRegex(ValueError, 'COGNITIVE_COMPOSITIONAL_BINDING_PROVENANCE'):
                binding.activation_grammar(event)

    def test_legacy_failed_goal_stays_withhold_after_explicit_v2_activation(self):
        records = legacy_records()
        before = copy.deepcopy(records)
        self.assertFalse(records[4]['passed'])
        self.assertEqual(cognitive.replay(records)[2]['status'], 'WITHHOLD')
        records.extend([{**binding.deactivation(), 'tick': 8, 'event_hash': 'b' * 64},
                        {**binding.activation(grammar=V2), 'tick': 9, 'event_hash': 'c' * 64}])
        self.assertEqual(cognitive.replay(records)[2]['status'], 'WITHHOLD')
        self.assertEqual(records[:7], before)
        self.assertEqual(binding.grammar_at(records[:7]), engine.GRAMMAR)
        self.assertEqual(binding.grammar_at(records), V2)

    def test_new_activation_requires_live_source_pins(self):
        body = binding.activation(grammar=V2)
        records = [{**body, 'tick': 1, 'event_hash': 'c' * 64}]
        cognitive.replay(records)
        with patch.object(binding, 'file_sha', return_value='f' * 64):
            with self.assertRaisesRegex(ValueError, 'COGNITIVE_COMPOSITIONAL_BINDING_PROVENANCE'):
                cognitive.replay(records)


if __name__ == '__main__':
    unittest.main()
