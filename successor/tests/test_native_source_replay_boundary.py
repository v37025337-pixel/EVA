"""Restored journal source must originate from its recorded trusted grammar."""
import copy
import unittest

from successor.cognitive import goal_context, learned_sources, recall_source, replay
from successor.tests.test_state_semantics import candidate_records
from yado_active_native_learning_v1 import execute_source, source_sha, synthesize_source, validate_source_goal


def source_records(strategy='native_v3'):
    if strategy == 'native_v4':
        values, function, key = (2, 3, 12, 11, 100, 101, 998), lambda x: x % 2 == 0, 'number'
    else:
        values, function, key = ('abc', 'def', 'gh', 'ij', 'klm', 'nop'), lambda x: x[::-1], 'text'
    training = values[:-3]
    spec = {'domain': 'native_source',
            'training': [{'input': {key: x}, 'expected': function(x)} for x in training],
            'validation': [{'input': {key: x}, 'expected': function(x)} for x in values[-3:-1]],
            'queries': [{'input': {key: values[-1]}}]}
    candidate = synthesize_source(spec['training'], strategy)
    result = {**candidate, 'status': 'CANDIDATE', 'source_context': goal_context(spec),
              'training_predictions': [function(x) for x in training],
              'validation_predictions': [function(x) for x in values[-3:-1]],
              'predictions': [function(values[-1])]}
    verification = {'passed': True, 'checks': 2,
                    'scope': 'INDEPENDENT_VALIDATION_LABELS_AFTER_SOURCE_FREEZE',
                    'evidence': {'source_sha256': candidate['source_sha256']}}
    return candidate_records(spec, strategy, 3 if strategy == 'native_v4' else 2, result, verification)


def replace_source(records, source):
    result = records[2]['result']
    result.update(source=source, source_sha256=source_sha(source))
    records[3]['evidence']['source_sha256'] = result['source_sha256']
    records[5]['result'] = copy.deepcopy(result)


class NativeSourceReplayBoundaryTests(unittest.TestCase):
    def test_source_goal_rejects_code_fields_and_non_scalar_inputs(self):
        spec = source_records()[0]['spec']
        invalid = copy.deepcopy(spec)
        invalid['source'] = 'raise AssertionError()'
        with self.assertRaisesRegex(ValueError, 'SOURCE_GOAL_REQUIRES'):
            validate_source_goal(invalid)
        for inputs in ({'text': object()}, {"x']; raise AssertionError(); #": 'data'}):
            invalid = copy.deepcopy(spec)
            invalid['training'][0]['input'] = inputs
            with self.assertRaisesRegex(ValueError, 'BOUNDED_SCALAR_INPUTS_REQUIRED'):
                validate_source_goal(invalid)

    def test_rehashed_source_cannot_enter_executable_memory(self):
        records = source_records()
        replace_source(records, "raise KeyError('UNTRUSTED_JOURNAL_SOURCE')\n" + records[2]['result']['source'])
        with self.assertRaisesRegex(ValueError, 'NATIVE_SOURCE_EMISSION_PROVENANCE'):
            replay(records)

    def test_correct_stored_predictions_do_not_attest_wrong_source(self):
        records = source_records()
        replace_source(records, "def solve(component_id, program_id, inputs):\n    return 'wrong'\n")
        with self.assertRaisesRegex(ValueError, 'NATIVE_SOURCE_EMISSION_PROVENANCE'):
            replay(records)

    def test_valid_v3_and_v4_sources_remain_replayable_and_reusable(self):
        for strategy in ('native_v3', 'native_v4'):
            with self.subTest(strategy=strategy):
                records = source_records(strategy)
                self.assertEqual(replay(records)[1]['status'], 'VALIDATED_ON_HOLDOUT')
                spec = records[0]['spec']
                prior, proof = recall_source(learned_sources(records, {'mode': 'full', 'spec': spec}),
                                            spec['training'], execute_source)
                self.assertEqual(prior['result']['source'], records[2]['result']['source'])
                self.assertEqual(proof['probes'][0]['predictions'], [row['expected'] for row in spec['training']])

    def test_successful_replay_cache_does_not_hide_source_replacement(self):
        records = source_records()
        replay(records)
        replace_source(records, "def solve(component_id, program_id, inputs):\n    return 'changed'\n")
        with self.assertRaisesRegex(ValueError, 'NATIVE_SOURCE_EMISSION_PROVENANCE'):
            replay(records)

    def test_evolved_route_rechecks_emission_after_recorded_activation(self):
        from successor.native_binding import activation, synthesize
        spec = {'domain': 'native_source',
                'training': [{'input': {'x': x}, 'expected': x * 2} for x in (1, 2, 3)],
                'validation': [{'input': {'x': x}, 'expected': x * 2} for x in (4, 5)],
                'queries': [{'input': {'x': 6}}]}
        candidate = synthesize(spec['training'])
        result = {**candidate, 'status': 'CANDIDATE', 'source_context': goal_context(spec),
                  'training_predictions': [2, 4, 6], 'validation_predictions': [8, 10], 'predictions': [12]}
        verification = {'passed': True, 'checks': 2,
                        'scope': 'INDEPENDENT_VALIDATION_LABELS_AFTER_SOURCE_FREEZE',
                        'evidence': {'source_sha256': candidate['source_sha256']}}
        for tamper in (False, True):
            with self.subTest(tamper=tamper):
                records = candidate_records(spec, 'native_evolved_v2', 4, copy.deepcopy(result), copy.deepcopy(verification))
                if tamper:
                    replace_source(records, "raise KeyError('UNTRUSTED_EVOLVED_SOURCE')\n" + candidate['source'])
                for record in records:
                    for field in ('tick', 'goal_id', 'decision_tick', 'execution_tick', 'verification_tick'):
                        if field in record:
                            record[field] += 1
                records.insert(0, {**activation(), 'tick': 1, 'event_hash': 'a' * 64})
                if tamper:
                    with self.assertRaisesRegex(ValueError, 'NATIVE_SOURCE_EMISSION_PROVENANCE'):
                        replay(records)
                else:
                    self.assertEqual(replay(records)[2]['status'], 'VALIDATED_ON_HOLDOUT')


if __name__ == '__main__':
    unittest.main()
