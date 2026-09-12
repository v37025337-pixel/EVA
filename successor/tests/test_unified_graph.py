import copy
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from successor.graph import CausalGraph
from successor.kernel import SuccessorKernel

MANIFEST = os.environ.get('YADO_SUCCESSOR_TEST_MANIFEST')


def numeric(offset=0):
    return {'rows': [{'x': x, 'y': y, 'expected': x*x+y+offset} for x in range(-3, 4) for y in range(-2, 3)],
            'queries': [{'x': 11, 'y': -3}]}


def node(capability='relation', value=None, **kw):
    return {'id': 'a', 'capability': capability, 'input': value if value is not None else {'relation': [['a', 'b'], ['b', 'c']], 'start': 'a'}, **kw}


@unittest.skipUnless(MANIFEST, 'Requires a real inherited birth via YADO_SUCCESSOR_TEST_MANIFEST')
class UnifiedGraphIntegration(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.state = Path(self.tmp.name) / 'session.sqlite'
        self.kernel = SuccessorKernel(MANIFEST, self.state)
        self.graph = CausalGraph(self.kernel)

    def tearDown(self):
        self.kernel.close(); self.tmp.cleanup()

    def restart(self):
        self.kernel.close()
        self.kernel = SuccessorKernel(MANIFEST, self.state)
        self.graph = CausalGraph(self.kernel)

    def submit(self, nodes=None, **kw):
        return self.graph.submit({'goal': 'integration', 'nodes': nodes or [node()], **kw})

    def goal(self, key):
        return self.graph.snapshot()['goals'][key]

    def test_verified_dependency_binds_real_output(self):
        other = {'id': 'b', 'capability': 'events', 'input': {'events': [['Q', ''], ['R', '']]},
                 'bindings': [{'from': 'a', 'path': ['answer', 1], 'to': ['events', i, 1]} for i in (0, 1)]}
        key = self.submit([node(), other]); self.graph.run(30)
        g = self.goal(key)
        self.assertEqual(g['status'], 'VERIFIED'); self.assertIs(g['nodes']['b']['result']['answer'], True)
        self.assertEqual(g['nodes']['b']['decision']['dependencies']['a'], g['nodes']['a']['terminal_tick'])
        self.assertEqual(g['nodes']['b']['decision']['input']['events'][0][1], 'b')

    def test_user_priority_preempts_internal(self):
        internal = self.submit(origin='internal'); self.graph.run(1)
        user = self.submit(); event = self.graph.run(1)[0]
        self.assertEqual(event['graph_id'], user); self.assertEqual(self.goal(internal)['nodes']['a']['phase'], 'EXECUTE')

    def test_memory_changes_choice_and_survives_restart(self):
        key = self.submit([node('numeric', numeric())]); self.graph.run(30)
        self.assertEqual(self.goal(key)['nodes']['a']['attempted'], ['polynomial_1', 'polynomial_2'])
        self.restart(); key = self.submit([node('numeric', numeric(2))]); self.graph.run(20)
        n = self.goal(key)['nodes']['a']
        self.assertEqual(n['attempted'], ['polynomial_2']); self.assertEqual(n['result']['predictions'], [120])
        key = self.submit([node('numeric', numeric(4))], mode='no_memory'); self.graph.run(1)
        self.assertEqual(self.goal(key)['nodes']['a']['decision']['choice']['strategy'], 'polynomial_1')

    def test_unverified_result_does_not_release_dependency(self):
        child = node(); child.update(id='b', needs=['a'])
        key = self.submit([node('native:audit', {}), child]); self.graph.run(30)
        g = self.goal(key)
        self.assertEqual(g['nodes']['a']['status'], 'EXECUTED_UNVERIFIED')
        self.assertEqual(g['nodes']['b']['status'], 'BLOCKED'); self.assertIsNone(g['nodes']['b']['execution'])

    def test_bad_graph_is_rejected_without_journal_mutation(self):
        cases = [[node(needs=['missing'])], [node(needs=['a'])], [node(bindings=[{'from': 'a', 'path': ['answer'], 'to': ['absent']}])]]
        for nodes in cases:
            with self.assertRaises(ValueError): self.submit(nodes)
        self.assertEqual(self.kernel.verify_state()['tick'], 0)

    def test_interrupted_step_rolls_back_and_can_resume(self):
        key = self.submit(); self.graph.run(1)
        before = self.kernel.verify_state(); original = self.graph._execute
        def interrupt(*args): raise KeyboardInterrupt()
        self.graph._execute = interrupt
        with self.assertRaises(KeyboardInterrupt): self.graph.run(1)
        self.assertEqual(self.kernel.verify_state(), before)
        self.graph._execute = original; self.graph.run(20)
        self.assertEqual(self.goal(key)['status'], 'VERIFIED')
        self.assertEqual(sum(r['kind'] == 'GRAPH_EXECUTE' for r in self.graph._records()), 1)

    def test_resume_in_separate_process(self):
        key = self.submit(); self.graph.run(2)
        subprocess.run([sys.executable, '-m', 'successor.unified', 'run', '--manifest', MANIFEST,
                        '--state', str(self.state), '--max-steps', '20'], check=True, stdout=subprocess.DEVNULL)
        self.assertEqual(self.goal(key)['status'], 'VERIFIED')

    def test_generated_source_reused_after_restart(self):
        key = self.submit([node('source_synthesis', numeric())]); self.graph.run(20)
        self.assertEqual(self.goal(key)['status'], 'VALIDATED_ON_HOLDOUT')
        digest = self.goal(key)['nodes']['a']['result']['source_sha256']
        self.restart()
        key = self.submit([node('source_apply', {'capability_id': digest, 'queries': [{'x': -13, 'y': 7}, {'x': 19, 'y': -8}]})])
        self.graph.run(20)
        self.assertEqual(self.goal(key)['nodes']['a']['result']['predictions'], [176, 353])

    def test_stop_is_durable(self):
        key = self.submit(); self.graph.run(1); self.graph.stop(key); before = self.kernel.verify_state()
        self.restart(); self.assertEqual(self.goal(key)['status'], 'STOPPED')
        self.assertEqual(self.graph.run(10), []); self.assertEqual(self.kernel.verify_state(), before)

    def test_identical_observation_not_counted_twice(self):
        for _ in range(2): self.submit(); self.graph.run(20)
        self.assertEqual(self.graph.snapshot()['self_model']['relation/native_logic']['successes'], 1)
