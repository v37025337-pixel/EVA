"""Frozen execution evidence must agree with the program that actually ran."""
import copy
from fractions import Fraction
from pathlib import Path
import tempfile
import unittest

from successor.cognitive import goal_context, replay, split_examples
from successor.tests.test_native_source_replay_boundary import source_records
from successor.tests.test_state_semantics import candidate_records, kernel_connection
from yado_active_native_learning_v1 import synthesize_source


def numeric_records():
    # Independent exact model of x + y, including the training partition size.
    spec = {'domain': 'numeric',
            'rows': [{'x': x, 'y': y, 'expected': x + y}
                     for x in range(4) for y in range(4)],
            'queries': [{'x': 9, 'y': 9}]}
    training, holdout = split_examples(spec['rows'])
    model = {'kind': 'EXACT_BOUNDED_POLYNOMIAL_V2', 'degree': 1,
             'basis': [(0, 0), (0, 1), (1, 0)],
             'coeff': [Fraction(0), Fraction(1), Fraction(1)],
             'term_count': 3, 'row_count': len(training)}
    result = {'status': 'CANDIDATE', 'model': model,
              'train_count': len(training), 'holdout_count': len(holdout),
              'holdout_predictions': [Fraction(r['x'] + r['y']) for r in holdout],
              'predictions': [Fraction(18)]}
    verification = {'passed': True, 'checks': len(holdout),
                    'scope': 'INDEPENDENT_HELD_OUT_LABELS', 'evidence': {}}
    return candidate_records(spec, 'polynomial_1', 1, result, verification)


def native_records(strategy):
    if strategy in {'native_v3', 'native_v4'}:
        return source_records(strategy)
    if strategy == 'native_evolved_v2':
        key, values, answers = 'x', [1, 2, 3, 4, 5, 6], [2, 4, 6, 8, 10, 12]
    else:
        key, values, answers = 'text', ['abc', 'aba', 'def', 'ghi', 'gjg', 'jkl'], [True, False, True, True, False, True]
    spec = {'domain': 'native_source',
            'training': [{'input': {key: x}, 'expected': y} for x, y in zip(values[:3], answers[:3])],
            'validation': [{'input': {key: x}, 'expected': y} for x, y in zip(values[3:5], answers[3:5])],
            'queries': [{'input': {key: values[5]}}]}
    if strategy == 'native_evolved_v2':
        from successor.native_binding import synthesize
        candidate, cost = synthesize(spec['training']), 4
    else:
        candidate, cost = synthesize_source(spec['training'], strategy), 1
    result = {**candidate, 'status': 'CANDIDATE', 'source_context': goal_context(spec),
              'training_predictions': answers[:3],
              'validation_predictions': answers[3:5], 'predictions': answers[5:]}
    verification = {'passed': True, 'checks': 2,
                    'scope': 'INDEPENDENT_VALIDATION_LABELS_AFTER_SOURCE_FREEZE',
                    'evidence': {'source_sha256': candidate['source_sha256']}}
    records = candidate_records(spec, strategy, cost, result, verification)
    if strategy == 'native_evolved_v2':
        from successor.native_binding import activation
        for record in records:
            for field in ('tick', 'goal_id', 'decision_tick', 'execution_tick', 'verification_tick'):
                if field in record:
                    record[field] += 1
        records.insert(0, {**activation(), 'tick': 1, 'event_hash': 'a' * 64})
    return records


def replace_result(records, result):
    next(r for r in records if r['kind'] == 'COG_EXECUTE')['result'] = result
    next(r for r in records if r['kind'] == 'COG_FINISH')['result'] = copy.deepcopy(result)


class ExecutionReplayIntegrityTests(unittest.TestCase):
    def test_legacy_native_routes_recompute_query_outputs(self):
        for strategy in ('native_v2', 'native_v3', 'native_v4', 'native_evolved_v2'):
            with self.subTest(strategy=strategy):
                records = native_records(strategy)
                self.assertTrue(all(g['status'] == 'VALIDATED_ON_HOLDOUT'
                                    for g in replay(records).values()))
                result = copy.deepcopy(next(r['result'] for r in records if r['kind'] == 'COG_EXECUTE'))
                result['predictions'] = ['invented query output']
                replace_result(records, result)
                with self.assertRaisesRegex(ValueError, 'NATIVE_EXECUTION_PROVENANCE'):
                    replay(records)

    def test_native_matching_stored_labels_do_not_prove_the_source_passes_holdout(self):
        records = source_records()
        spec, result = copy.deepcopy(records[0]['spec']), copy.deepcopy(records[2]['result'])
        spec['validation'][0]['expected'] = 'unsupported answer'
        result['validation_predictions'][0] = 'unsupported answer'
        verification = {key: records[3][key] for key in ('passed', 'checks', 'scope', 'evidence')}
        forged = candidate_records(spec, 'native_v3', 2, result, verification)
        with self.assertRaisesRegex(ValueError, 'NATIVE_EXECUTION_PROVENANCE'):
            replay(forged)

    def test_reused_legacy_source_still_needs_real_query_outputs(self):
        records = source_records()
        result = copy.deepcopy(records[2]['result'])
        result['reused_finish_tick'] = records[-1]['tick']
        verification = {key: records[3][key] for key in ('passed', 'checks', 'scope', 'evidence')}
        recalled = candidate_records(records[0]['spec'], 'reuse_verified_source', 1, result, verification)
        for record in recalled:
            for field in ('tick', 'goal_id', 'decision_tick', 'execution_tick', 'verification_tick'):
                if field in record:
                    record[field] += len(records)
        self.assertEqual(replay(records + recalled)[7]['result']['predictions'], result['predictions'])
        result['predictions'] = ['invented recalled output']
        replace_result(recalled, result)
        with self.assertRaisesRegex(ValueError, 'NATIVE_EXECUTION_PROVENANCE'):
            replay(records + recalled)

    def test_numeric_model_and_query_outputs_are_recomputed(self):
        records = numeric_records()
        self.assertEqual(replay(records)[1]['result']['predictions'], [18])
        for mutate in (lambda r: r.update(predictions=[Fraction(999)]),
                       lambda r: r['model']['coeff'].__setitem__(0, Fraction(7)),
                       lambda r: r.pop('model')):
            with self.subTest(mutation=mutate):
                damaged = copy.deepcopy(records)
                result = copy.deepcopy(damaged[2]['result'])
                mutate(result)
                replace_result(damaged, result)
                with self.assertRaisesRegex(ValueError, 'NUMERIC_.*PROVENANCE'):
                    replay(damaged)

    def test_numeric_matching_holdout_labels_cannot_hide_wrong_execution(self):
        records = numeric_records()
        spec, result = copy.deepcopy(records[0]['spec']), copy.deepcopy(records[2]['result'])
        _, holdout = split_examples(spec['rows'])
        point = (holdout[0]['x'], holdout[0]['y'])
        next(r for r in spec['rows'] if (r['x'], r['y']) == point)['expected'] = 999
        result['holdout_predictions'][0] = Fraction(999)
        verification = {key: records[3][key] for key in ('passed', 'checks', 'scope', 'evidence')}
        forged = candidate_records(spec, 'polynomial_1', 1, result, verification)
        with self.assertRaisesRegex(ValueError, 'NUMERIC_EXECUTION_PROVENANCE'):
            replay(forged)

    def test_honest_historical_withhold_stays_withhold(self):
        for records, domain in ((source_records(), 'native_source'), (numeric_records(), 'numeric')):
            with self.subTest(domain=domain):
                spec = copy.deepcopy(records[0]['spec'])
                if domain == 'native_source':
                    spec['validation'][0]['expected'] = 'wrong requirement'
                else:
                    point = split_examples(spec['rows'])[1][0]
                    next(r for r in spec['rows'] if r == point)['expected'] = 999
                verification = {key: records[3][key] for key in ('passed', 'checks', 'scope', 'evidence')}
                verification['passed'] = False
                failed = candidate_records(spec, records[1]['choice']['strategy'],
                                           records[1]['choice']['cost'], records[2]['result'], verification)
                self.assertEqual(replay(failed)[1]['status'], 'WITHHOLD')

    def test_hash_consistent_sqlite_cannot_restore_false_query_outputs(self):
        for records in (source_records(), numeric_records()):
            with self.subTest(domain=records[0]['spec']['domain']), tempfile.TemporaryDirectory() as directory:
                kernel = kernel_connection(Path(directory) / 'state.sqlite')
                try:
                    result = copy.deepcopy(records[2]['result'])
                    result['predictions'] = ['unexecuted answer']
                    replace_result(records, result)
                    for record in records:
                        kernel._append({key: value for key, value in record.items()
                                        if key not in {'tick', 'event_hash'}})
                    with self.assertRaisesRegex(ValueError, 'EXECUTION_PROVENANCE'):
                        kernel.verify_state()
                finally:
                    kernel.db.close()


if __name__ == '__main__':
    unittest.main()
