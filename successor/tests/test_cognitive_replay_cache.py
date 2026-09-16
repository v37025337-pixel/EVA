import copy
from fractions import Fraction
import marshal
import math
import unittest
from unittest.mock import patch

from successor import cognitive
from successor.kernel import fingerprint


def goal_records():
    spec = {'domain': 'relation', 'relation': [[0, 1]], 'start': 0}
    return [{'kind': 'COG_GOAL', 'tick': 1, 'event_hash': 'a' * 64,
             'spec': spec, 'spec_digest': fingerprint(spec), 'budget': 3, 'mode': 'full'}]


def execution_records():
    records = goal_records()
    choice = {'strategy': 'native_logic', 'cost': 1, 'probability': 0.5}
    workspace = {'goal_digest': records[0]['spec_digest'], 'remaining_budget': 3,
                 'proposals': [choice]}
    digest = fingerprint(workspace)
    records += [
        {'kind': 'COG_DECIDE', 'tick': 2, 'event_hash': 'b' * 64, 'goal_id': 1,
         'choice': choice, 'workspace': workspace, 'workspace_digest': digest},
        {'kind': 'COG_EXECUTE', 'tick': 3, 'event_hash': 'c' * 64, 'goal_id': 1,
         'decision_tick': 2, 'workspace_digest': digest,
         'result': {'predictions': [Fraction(1, 3), True, 1, 1.0, -0.0,
                                    ('fraction', 1, 3), [1, 2], (1, 2)]}},
    ]
    return records


class CognitiveReplayCacheTests(unittest.TestCase):
    def setUp(self):
        self.cache = cognitive._ReplayCache()
        self.patcher = patch.object(cognitive, '_REPLAY_CACHE', self.cache)
        self.patcher.start()
        self.addCleanup(self.patcher.stop)

    def test_equal_content_reuses_validated_projection(self):
        records = execution_records()
        with patch.object(cognitive, '_replay_uncached', wraps=cognitive._replay_uncached) as run:
            first = cognitive.replay(records)
            self.assertEqual(cognitive.replay(copy.deepcopy(records)), first)
            self.assertEqual(run.call_count, 1)
        self.assertEqual(self.cache.info()['hits'], 1)

    def test_input_mutation_with_same_claimed_hash_still_fails(self):
        records = goal_records()
        cognitive.replay(records)
        for invalid in (True, 3.0, Fraction(3, 1)):
            with self.subTest(invalid=repr(invalid)):
                records[0]['budget'] = invalid
                with self.assertRaisesRegex(ValueError, 'COGNITIVE_GOAL_CONTRACT'):
                    cognitive.replay(records)
        records[0]['budget'] = 3
        records[0]['spec']['start'] = 77
        with self.assertRaisesRegex(ValueError, 'COGNITIVE_GOAL_CONTRACT'):
            cognitive.replay(records)
        self.assertEqual(self.cache.info()['entries'], 1)
        self.assertEqual(self.cache.info()['hits'], 0)

    def test_tick_hash_and_ignored_fields_are_part_of_key(self):
        records = goal_records()
        with patch.object(cognitive, '_replay_uncached', wraps=cognitive._replay_uncached) as run:
            cognitive.replay(records)
            for field, value in (('tick', 7), ('event_hash', 'd' * 64), ('extra', {'a': 1})):
                changed = copy.deepcopy(records)
                changed[0][field] = value
                cognitive.replay(changed)
            self.assertEqual(run.call_count, 4)

    def test_numeric_and_sequence_types_have_distinct_exact_keys(self):
        values = [True, 1, 1.0, Fraction(1, 1), 0.0, -0.0,
                  ('fraction', 1, 1), [1, 2], (1, 2), None]
        keys = [marshal.dumps(cognitive._cache_normalize(v), 2) for v in values]
        self.assertEqual(len(set(keys)), len(values))
        records = execution_records()
        for _ in range(2):
            values = cognitive.replay(records)[1]['execution']['result']['predictions']
            self.assertEqual([type(v) for v in values],
                             [Fraction, bool, int, float, float, tuple, list, tuple])
            self.assertEqual(math.copysign(1, values[4]), -1)
            self.assertEqual(values[5], ('fraction', 1, 3))

    def test_alias_sharing_does_not_change_content_key(self):
        shared = ''.join(['repeated-', 'long-value'])
        aliased = [shared, shared]
        separate = [shared, ('_' + shared)[1:]]
        self.assertIsNot(separate[0], separate[1])
        self.assertEqual(marshal.dumps(cognitive._cache_normalize(aliased), 2),
                         marshal.dumps(cognitive._cache_normalize(separate), 2))

    def test_cold_and_warm_results_cannot_poison_cache_or_inputs(self):
        records = execution_records()
        original = copy.deepcopy(records)
        expected = cognitive._replay_uncached(copy.deepcopy(records))
        for _ in range(2):
            result = cognitive.replay(records)
            self.assertEqual(result, expected)
            result[1]['spec']['relation'].append([1, 9])
            result[1]['execution']['result']['predictions'].clear()
            result[1]['attempted'].append('forged')
            self.assertEqual(records, original)
        self.assertEqual(cognitive.replay(records), expected)
        self.cache.clear()
        self.assertEqual(cognitive.replay(records), expected)

    def test_cold_replay_uses_private_input_snapshot(self):
        records = goal_records()
        original = cognitive._replay_uncached

        def mutate_caller(snapshot):
            records[0]['budget'] = True
            return original(snapshot)

        with patch.object(cognitive, '_replay_uncached', side_effect=mutate_caller):
            self.assertEqual(cognitive.replay(records)[1]['budget'], 3)
        with self.assertRaisesRegex(ValueError, 'COGNITIVE_GOAL_CONTRACT'):
            cognitive.replay(records)

    def test_failures_are_revalidated_and_never_cached(self):
        records = goal_records()
        records[0]['budget'] = 0
        with patch.object(cognitive, '_replay_uncached', wraps=cognitive._replay_uncached) as run:
            for _ in range(2):
                with self.assertRaisesRegex(ValueError, 'COGNITIVE_GOAL_CONTRACT'):
                    cognitive.replay(records)
            self.assertEqual(run.call_count, 2)
        self.assertEqual(self.cache.info()['entries'], 0)

    def test_live_binding_provenance_is_rechecked_after_warmup(self):
        from successor.native_binding import activation
        body = activation()
        records = [{**body, 'tick': 1, 'event_hash': 'e' * 64}]
        self.assertEqual(cognitive.replay(records), {})
        self.assertEqual(cognitive.replay(records), {})
        changed = copy.deepcopy(body)
        changed['sources']['successor/evolved_kernel.py'] = 'f' * 64
        with patch('successor.native_binding.activation', return_value=changed):
            with self.assertRaisesRegex(ValueError, 'COGNITIVE_NATIVE_BINDING_PROVENANCE'):
                cognitive.replay(records)

    def test_lru_and_byte_limits_bound_retention(self):
        cache = cognitive._ReplayCache(max_entries=2, max_bytes=100000)
        with patch.object(cognitive, '_REPLAY_CACHE', cache):
            for tick in (1, 2, 1, 3):
                records = goal_records()
                records[0]['tick'] = tick
                cognitive.replay(records)
            self.assertEqual(cache.info()['entries'], 2)
            self.assertEqual(cache.info()['hits'], 1)
            records[0]['tick'] = 2
            cognitive.replay(records)
            self.assertEqual(cache.info()['misses'], 4)
            self.assertLessEqual(cache.info()['bytes'], cache.max_bytes)
        tiny = cognitive._ReplayCache(max_bytes=1)
        with patch.object(cognitive, '_REPLAY_CACHE', tiny):
            self.assertEqual(cognitive.replay(goal_records())[1]['budget'], 3)
            self.assertEqual(tiny.info()['entries'], 0)

    def test_large_valid_journal_has_no_new_whole_journal_node_limit(self):
        records = goal_records()
        # Ignored metadata is still in the key, but is not a replay schema gate.
        # This exceeds TypedJSON's default whole-value node limit of 250000.
        records[0]['large_metadata'] = [0] * 250001
        self.assertEqual(cognitive.replay(records)[1]['budget'], 3)
        self.assertEqual(cognitive.replay(records)[1]['budget'], 3)
        self.assertEqual(self.cache.info()['hits'], 1)

    def test_unsupported_and_deep_values_fall_back_to_original_replay(self):
        class Marker:
            pass
        for metadata in (Marker(), float('inf')):
            records = goal_records()
            records[0]['extra'] = metadata
            self.assertEqual(cognitive.replay(records)[1]['budget'], 3)
        records = goal_records()
        deep = []
        for _ in range(1200):
            deep = [deep]
        records[0]['extra'] = deep
        self.assertEqual(cognitive.replay(records)[1]['budget'], 3)
        self.assertEqual(self.cache.info()['entries'], 0)

    def test_generator_fallback_is_not_consumed_by_cache_preflight(self):
        self.assertEqual(cognitive.replay(iter(goal_records()))[1]['budget'], 3)
        self.assertEqual(self.cache.info()['entries'], 0)


if __name__ == '__main__':
    unittest.main()
