"""Offline storage-contract regressions, not evidence of external learning.

Only receipt-file prerequisites and external/meta boundaries use fixtures. The
canonical tri-organ implementation and the binding under test execute normally.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from yado_g2_all_experience_tri_organ_runtime_v1 import G2AllExperienceTriOrganRuntimeV1
from yado_g2_causal_external_learning_binding_v1 import G2CausalExternalLearningBindingV1

ROOT = Path(__file__).resolve().parent.parent
LEGACY_SCHEMA = 'yado.g2.causal_external_learning_binding.state.v1'
NEW_SCHEMA = 'yado.g2.causal_external_learning_binding.state.v2'


def seal_state(value):
    value.pop('state_digest', None)
    text = json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, default=str)
    value['state_digest'] = hashlib.sha256(text.encode()).hexdigest()
    return value


class CausalLearningStateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.fixture_root = Path(self.tmp.name)
        self.meta_calls = []
        for stage, relative in G2CausalExternalLearningBindingV1.RECEIPTS.items():
            path = self.fixture_root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps({'status': G2CausalExternalLearningBindingV1.EXPECTED[stage],
                                        'offline_test_fixture': True}))
        self.artifact = json.loads((ROOT / 'canonical/yado-g2-causal-external-learning-binding-v1.json').read_text())
        self.organs = G2AllExperienceTriOrganRuntimeV1(json.loads(
            (ROOT / 'canonical/yado-g2-all-experience-tri-organ-v1.json').read_text()))

    def tearDown(self):
        self.tmp.cleanup()

    def binding(self):
        def meta(evidence):
            self.meta_calls.append(deepcopy(evidence))
            return {'offline_test_fixture': True, 'decision': 'WITHHOLD'}
        return G2CausalExternalLearningBindingV1(self.fixture_root, self.artifact,
            lambda *args, **kwargs: [], self.organs.thinking, self.organs.logic,
            self.organs.intelligence, meta)

    def advance(self, binding, count=1):
        for _ in range(count):
            prepared = binding.prepare_cycle('offline storage verification')
            self.assertEqual(prepared['status'], 'PASS_CAUSAL_PREPARE')
            # The empty external receipt is invalid, and is correctly recorded as
            # failure. Failed learning attempts must survive restarts too.
            applied = binding.apply_result(prepared, {})
            self.assertEqual(applied['status'], 'WITHHOLD_G2_CAUSAL_EXTERNAL_LEARNING_BINDING_V1')
        return binding.export_state()

    def test_rollover_round_trip_preserves_128_episodes_and_monotonic_sequence(self):
        binding = self.binding()
        state = self.advance(binding, 130)
        restored = self.binding()
        restored.import_state(json.loads(json.dumps(state)))
        self.assertEqual(restored.export_state(), state)
        self.assertEqual(state['schema'], NEW_SCHEMA)
        self.assertEqual(len(state['episodes']), 128)
        self.assertEqual([r['sequence'] for r in state['episodes']], list(range(3, 131)))
        self.assertEqual(state['base_sequence'], 2)
        self.assertEqual(state['episodes'][0]['prior_event_digest'], state['base_event_digest'])
        self.assertEqual(restored.snapshot()['episode_count'], 128)
        self.assertEqual(restored.snapshot()['total_episode_count'], 130)
        next_state = self.advance(restored)
        self.assertEqual(next_state['episodes'][-1]['sequence'], 131)
        self.assertEqual(next_state['base_sequence'], 3)
        self.binding().import_state(next_state)

    def test_retained_anchor_is_actual_evicted_episode_digest(self):
        binding = self.binding()
        first = self.advance(binding)['episodes'][0]['event_digest']
        state = self.advance(binding, 128)
        self.assertEqual(state['base_sequence'], 1)
        self.assertEqual(state['base_event_digest'], first)
        self.assertEqual(state['episodes'][0]['sequence'], 2)
        self.binding().import_state(state)

    def test_stale_plan_rejected_before_meta_or_memory_change(self):
        binding = self.binding()
        first = binding.prepare_cycle('first')
        stale = binding.prepare_cycle('prepared before first result')
        binding.apply_result(first, {})
        before = binding.export_state()
        calls = len(self.meta_calls)
        with self.assertRaisesRegex(ValueError, 'CAUSAL_EXTERNAL_BINDING_STALE_PLAN'):
            binding.apply_result(stale, {})
        self.assertEqual(len(self.meta_calls), calls)
        self.assertEqual(binding.export_state(), before)

    def test_replayed_plan_rejected_after_restore_before_meta(self):
        binding = self.binding()
        prepared = binding.prepare_cycle('once')
        binding.apply_result(prepared, {})
        restored = self.binding()
        restored.import_state(binding.export_state())
        before = restored.export_state()
        calls = len(self.meta_calls)
        with self.assertRaisesRegex(ValueError, 'CAUSAL_EXTERNAL_BINDING_STALE_PLAN'):
            restored.apply_result(prepared, {})
        self.assertEqual(len(self.meta_calls), calls)
        self.assertEqual(restored.export_state(), before)

    def test_valid_full_legacy_states_import_then_export_v2(self):
        for count in (0, 1, 128):
            with self.subTest(count=count):
                original = self.binding()
                if count:
                    self.advance(original, count)
                legacy = original.export_state()
                legacy['schema'] = LEGACY_SCHEMA
                legacy.pop('base_sequence', None)
                legacy.pop('base_event_digest', None)
                seal_state(legacy)
                restored = self.binding()
                restored.import_state(legacy)
                state = restored.export_state()
                self.assertEqual(state['schema'], NEW_SCHEMA)
                self.assertEqual(state['base_sequence'], 0)
                self.assertIsNone(state['base_event_digest'])
                self.assertEqual(state['episodes'], legacy['episodes'])

    def test_truncated_legacy_rejected_without_guessing_or_mutation(self):
        state = self.advance(self.binding(), 129)
        state['schema'] = LEGACY_SCHEMA
        state.pop('base_sequence', None)
        state.pop('base_event_digest', None)
        seal_state(state)
        target = self.binding()
        before = self.advance(target)
        with self.assertRaisesRegex(ValueError, 'CAUSAL_EXTERNAL_BINDING_EVENT_CHAIN_INVALID'):
            target.import_state(state)
        self.assertEqual(target.export_state(), before)

    def test_bad_v2_anchor_rejected_atomically_even_after_rehash(self):
        original = self.advance(self.binding(), 129)
        target = self.binding()
        before = self.advance(target, 2)
        for key, value in (('base_sequence', 2), ('base_sequence', True),
                           ('base_event_digest', 'a' * 64), ('base_event_digest', None)):
            with self.subTest(key=key, value=value):
                broken = deepcopy(original)
                broken['schema'] = NEW_SCHEMA
                broken[key] = value
                seal_state(broken)
                with self.assertRaises(ValueError):
                    target.import_state(broken)
                self.assertEqual(target.export_state(), before)

    def test_corrupt_digest_and_late_chain_link_do_not_replace_memory(self):
        original = self.advance(self.binding(), 3)
        target = self.binding()
        before = self.advance(target)
        broken_digest = deepcopy(original)
        broken_digest['state_digest'] = '0' * 64
        broken_chain = deepcopy(original)
        broken_chain['episodes'][-1]['prior_event_digest'] = 'f' * 64
        seal_state(broken_chain)
        for broken in (broken_digest, broken_chain):
            with self.assertRaises(ValueError):
                target.import_state(broken)
            self.assertEqual(target.export_state(), before)


if __name__ == '__main__':
    unittest.main()
