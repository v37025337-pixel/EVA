from __future__ import annotations

from fractions import Fraction
from pathlib import Path
from unittest import TestCase,mock
import copy,json,subprocess,sys,tempfile,textwrap

ROOT=Path(__file__).resolve().parents[1]
RUNTIME=ROOT/'runtime'
PKG=RUNTIME/'yado_rc8_v36'
sys.path[:0]=[str(RUNTIME),str(PKG)]

from yado_g2_typed_recurrent_capability_graph_runtime_v1 import G2TypedRecurrentCapabilityGraphRuntimeV1
from yado_g2_unified_execution_fabric_v1 import CAP_LOGIC_V2,CAP_THINK_V2,CAP_INTEL_V3,CAP_BUD
from yado_g2_unified_execution_fabric_v4 import G2UnifiedExecutionFabricV4,_digest_v4
from yado_g2_unified_execution_fabric_v5 import G2UnifiedExecutionFabricV5
from yado_coverage_pruned_compositional_schema_router_v3 import CoveragePrunedCompositionalSchemaRouterV3

ARCH=json.loads((ROOT/'canonical/yado-g2-architecture-v1.json').read_text(encoding='utf-8'))

class _Router:
    fallback_output='ALG-CONJUNCTIVE-RULE-INDUCER-V1'
    def execute(self,descriptor):return self.fallback_output

class _Scalar:
    def execute(self,x):return 'SCALAR'

class _Relation:
    def execute(self,x):return 'REL'

def make_base():
    return G2TypedRecurrentCapabilityGraphRuntimeV1(ARCH,_Router(),_Scalar(),_Relation(),{})

def symmetric_rows():
    return [
      {'input':{'a':False,'b':False},'expected':'OTHER'},
      {'input':{'a':False,'b':True},'expected':'OTHER'},
      {'input':{'a':True,'b':False},'expected':'OTHER'},
      {'input':{'a':True,'b':True},'expected':'ALL'},
    ]

def intelligence_model():
    cases=[]
    for i in range(4):
        cases.append({'input':{'mode':'yes','nonce':i},'expected':'A'})
        cases.append({'input':{'mode':'no','nonce':i},'expected':'BASE'})
    return CoveragePrunedCompositionalSchemaRouterV3.fit(cases,'BASE')

class TestG2ContinuityFileIntegrity(TestCase):
    def setUp(self):
        self.td=tempfile.TemporaryDirectory(prefix='yado-file-integrity-')
        self.dir=Path(self.td.name)
        self.path=self.dir/'checkpoint.json'

    def tearDown(self):
        self.td.cleanup()

    def _new(self):
        return G2UnifiedExecutionFabricV5(make_base(),api_state={},checkpoint_path=self.path)

    def test_real_logic_integer_keys_survive_restart(self):
        f=self._new()
        learned=f.execute_capability(CAP_LOGIC_V2,{
          'operation':'learn_symmetric','rows':symmetric_rows(),'stream_id':'LOGIC'
        })
        model=learned['result']
        self.assertTrue(all(isinstance(k,int) for k in model['count_to_output']))
        before=f.execute_capability(CAP_LOGIC_V2,{
          'operation':'predict_symmetric','model':model,'payload':{'a':True,'b':True},'stream_id':'LOGIC'
        })['result']
        self.assertEqual(before,'ALL')
        del f
        f2=self._new()
        restored=next(
          e['result'] for e in reversed(f2.base.episodes)
          if e.get('kind')=='FABRIC_EPISODE' and isinstance(e.get('result'),dict)
          and e['result'].get('kind')=='SYMMETRIC_COUNT_MAP_V2'
        )
        self.assertTrue(all(isinstance(k,int) for k in restored['count_to_output']))
        after=f2.execute_capability(CAP_LOGIC_V2,{
          'operation':'predict_symmetric','model':restored,'payload':{'a':True,'b':True},'stream_id':'LOGIC'
        })['result']
        self.assertEqual((before,after),('ALL','ALL'))

    def test_real_logic_fraction_and_tuple_model_survives_restart(self):
        f=self._new()
        rows=[
          {'x':0,'y':0,'expected':Fraction(0)},
          {'x':1,'y':0,'expected':Fraction(1,2)},
          {'x':0,'y':1,'expected':Fraction(1,3)},
        ]
        model=f.execute_capability(CAP_LOGIC_V2,{
          'operation':'fit_polynomial','rows':rows,'max_degree':1,'stream_id':'POLY'
        })['result']
        self.assertTrue(all(isinstance(x,tuple) for x in model['basis']))
        self.assertTrue(all(isinstance(x,Fraction) for x in model['coeff']))
        del f
        f2=self._new()
        restored=next(
          e['result'] for e in reversed(f2.base.episodes)
          if e.get('kind')=='FABRIC_EPISODE' and isinstance(e.get('result'),dict)
          and e['result'].get('kind')=='EXACT_BOUNDED_POLYNOMIAL_V2'
        )
        self.assertTrue(all(isinstance(x,tuple) for x in restored['basis']))
        self.assertTrue(all(isinstance(x,Fraction) for x in restored['coeff']))
        got=f2.execute_capability(CAP_LOGIC_V2,{
          'operation':'predict_polynomial','model':restored,'x':1,'y':1,'stream_id':'POLY'
        })['result']
        self.assertEqual(got,Fraction(5,6))

    def test_real_intelligence_tuple_output_survives_restart(self):
        f=self._new()
        model=intelligence_model()
        got=f.execute_capability(CAP_INTEL_V3,{
          'operation':'route','model':model,'payload':{'mode':'yes','nonce':99},'stream_id':'INTEL'
        })['result']
        self.assertEqual(got,('A',))
        del f
        f2=self._new()
        restored=next(
          e['result'] for e in reversed(f2.base.episodes)
          if e.get('kind')=='FABRIC_EPISODE' and e.get('selected_capability')==CAP_INTEL_V3
        )
        self.assertIsInstance(restored,tuple)
        self.assertEqual(restored,('A',))

    def test_real_thinking_feedback_survives_restart(self):
        f=self._new()
        f.record_outcome('THINK','FAILED_A',0.0)
        stages=[
          {'stage_id':'FAILED_A','cost':1,'expected_gain':.5,'quota_remaining':1},
          {'stage_id':'NEXT_B','cost':2,'expected_gain':.6,'quota_remaining':1},
        ]
        before=f.execute_capability(CAP_THINK_V2,{
          'operation':'auto_feedback_plan','stream_id':'THINK',
          'current_confidence':.2,'target_confidence':.7,'remaining_budget':4,
          'stages':stages,'completed':()
        })
        self.assertTrue(before['meta']['memory_feedback_used'])
        self.assertEqual(before['result']['action'],'NEXT_B')
        del f
        f2=self._new()
        after=f2.execute_capability(CAP_THINK_V2,{
          'operation':'auto_feedback_plan','stream_id':'THINK',
          'current_confidence':.2,'target_confidence':.7,'remaining_budget':4,
          'stages':stages,'completed':()
        })
        self.assertTrue(after['meta']['memory_feedback_used'])
        self.assertEqual(after['result']['action'],'NEXT_B')

    def test_separate_python_process_restores_types_and_behavior(self):
        f=self._new()
        model=f.execute_capability(CAP_LOGIC_V2,{
          'operation':'learn_symmetric','rows':symmetric_rows(),'stream_id':'PROC'
        })['result']
        self.assertEqual(model['count_to_output'][2],'ALL')
        im=intelligence_model()
        self.assertEqual(f.execute_capability(CAP_INTEL_V3,{
          'operation':'route','model':im,'payload':{'mode':'yes'},'stream_id':'PROC'
        })['result'],('A',))
        del f
        code=textwrap.dedent(r'''
            from pathlib import Path
            import json,sys
            root=Path(sys.argv[2]);runtime=root/'runtime';pkg=runtime/'yado_rc8_v36'
            sys.path[:0]=[str(runtime),str(pkg)]
            from yado_g2_typed_recurrent_capability_graph_runtime_v1 import G2TypedRecurrentCapabilityGraphRuntimeV1
            from yado_g2_unified_execution_fabric_v1 import CAP_LOGIC_V2,CAP_INTEL_V3
            from yado_g2_unified_execution_fabric_v5 import G2UnifiedExecutionFabricV5
            arch=json.loads((root/'canonical/yado-g2-architecture-v1.json').read_text())
            class R:
                fallback_output='ALG-CONJUNCTIVE-RULE-INDUCER-V1'
                def execute(self,d):return self.fallback_output
            class S:
                def execute(self,x):return 'S'
            class Q:
                def execute(self,x):return 'Q'
            base=G2TypedRecurrentCapabilityGraphRuntimeV1(arch,R(),S(),Q(),{})
            f=G2UnifiedExecutionFabricV5(base,api_state={},checkpoint_path=Path(sys.argv[1]))
            m=next(e['result'] for e in reversed(f.base.episodes)
                   if isinstance(e.get('result'),dict) and e['result'].get('kind')=='SYMMETRIC_COUNT_MAP_V2')
            intel=next(e['result'] for e in reversed(f.base.episodes)
                       if e.get('selected_capability')==CAP_INTEL_V3)
            out=f.execute_capability(CAP_LOGIC_V2,{'operation':'predict_symmetric','model':m,
                'payload':{'a':True,'b':True},'stream_id':'CHILD'})['result']
            print(json.dumps({'answer':out,'int_keys':all(isinstance(k,int) for k in m['count_to_output']),
                              'intel_tuple':isinstance(intel,tuple)}))
        ''')
        p=subprocess.run([sys.executable,'-c',code,str(self.path),str(ROOT)],capture_output=True,text=True,timeout=60)
        self.assertEqual(p.returncode,0,p.stderr)
        row=json.loads(p.stdout.strip().splitlines()[-1])
        self.assertEqual(row,{'answer':'ALL','int_keys':True,'intel_tuple':True})

    def test_legacy_plain_json_v1_is_accepted_when_valid(self):
        legacy=self.dir/'legacy-v1.json'
        f=G2UnifiedExecutionFabricV4(make_base(),api_state={},checkpoint_path=legacy)
        f.record_outcome('LEGACY','A',0.0)
        self.assertEqual(json.loads(legacy.read_text())['schema'],f.CHECKPOINT_SCHEMA)
        del f
        f2=G2UnifiedExecutionFabricV5(make_base(),api_state={},checkpoint_path=legacy)
        self.assertIn('A',f2.base.stream_attempts['LEGACY'])

    def test_bounded_memory_survives_file_roundtrip(self):
        f=self._new()
        for i in range(160):
            f.base._remember({'kind':'BOUND','i':i})
        f.save_continuity_checkpoint()
        self.assertLessEqual(len(f.base.episodes),f.base.MAX_EPISODES)
        del f
        f2=self._new()
        self.assertEqual(len(f2.base.episodes),f2.base.MAX_EPISODES)

    def test_stall_continuity_survives_restart(self):
        f=self._new()
        task={
          'kind':'budget','descriptor':{'budget_limited':True},'stream_id':'STALL',
          'current_confidence':.1,'target_confidence':.9,'remaining_budget':2,
          'stages':[{'stage_id':'A','cost':1,'expected_gain':.2,'quota_remaining':1}],
          'progress_token':'UNCHANGED','deficit_id':'STALL-DEFICIT'
        }
        for _ in range(21):
            f.execute_capability(CAP_BUD,task)
        before=f.temporal_stream_state('STALL')
        self.assertTrue(before['mechanism_change_required'])
        self.assertGreaterEqual(before['no_progress_ticks'],20)
        del f
        f2=self._new()
        after=f2.temporal_stream_state('STALL')
        self.assertEqual(after['no_progress_ticks'],before['no_progress_ticks'])
        self.assertEqual(after['mechanism_change_required'],before['mechanism_change_required'])

    def test_corruption_and_cross_layer_forgery_fail_before_base_mutation(self):
        f=self._new()
        f.record_outcome('SAFE','FAILED',0.0)
        del f
        doc=json.loads(self.path.read_text())
        doc['typed_checkpoint']['t']='list'
        self.path.write_text(json.dumps(doc),encoding='utf-8')
        base=make_base()
        with self.assertRaises(ValueError):
            G2UnifiedExecutionFabricV5(base,api_state={},checkpoint_path=self.path)
        self.assertEqual(base.sequence,0)
        self.assertEqual(len(base.episodes),0)

        # Recreate a valid file, then forge an internally re-digested cross-layer link.
        f=self._new();f.record_outcome('SAFE2','FAILED2',0.0);state=f.export_continuity_state();del f
        changed=False
        for e in reversed(state['recurrent_memory_state']['episodes']):
            if e.get('kind')=='TEMPORAL_TRANSITION':
                e['tick_digest']='0'*64
                e['episode_digest']=_digest_v4({k:v for k,v in e.items() if k!='episode_digest'})
                changed=True;break
        self.assertTrue(changed)
        rm=state['recurrent_memory_state']
        rm['memory_state_digest']=_digest_v4({k:v for k,v in rm.items() if k!='memory_state_digest'})
        state['checkpoint_digest']=_digest_v4({k:v for k,v in state.items() if k!='checkpoint_digest'})
        env=G2UnifiedExecutionFabricV5._file_envelope(state)
        self.path.write_text(json.dumps(env),encoding='utf-8')
        base2=make_base()
        with self.assertRaises(ValueError):
            G2UnifiedExecutionFabricV5(base2,api_state={},checkpoint_path=self.path)
        self.assertEqual(base2.sequence,0)
        self.assertEqual(len(base2.episodes),0)

    def test_failed_replace_keeps_previous_checkpoint_and_cleans_temp(self):
        f=self._new()
        f.record_outcome('WRITE','A',0.0)
        old=self.path.read_bytes()
        f.base._remember({'kind':'NEW_STATE','value':1})
        with mock.patch('yado_g2_unified_execution_fabric_v5.os.replace',side_effect=OSError('replace failed')):
            with self.assertRaises(OSError):
                f.save_continuity_checkpoint()
        self.assertEqual(self.path.read_bytes(),old)
        self.assertEqual(list(self.dir.glob(self.path.name+'.*.tmp')),[])

    def test_unsupported_objects_and_nonfinite_numbers_fail_closed(self):
        f=self._new()
        f.base._remember({'kind':'BAD_OBJECT','value':object()})
        with self.assertRaises(TypeError):
            f.save_continuity_checkpoint()

        f2=G2UnifiedExecutionFabricV5(make_base(),api_state={},checkpoint_path=self.dir/'nan.json')
        f2.base._remember({'kind':'BAD_FLOAT','value':float('nan')})
        with self.assertRaises(ValueError):
            f2.save_continuity_checkpoint()

    def test_raw_file_envelope_is_not_accepted_as_continuity_state(self):
        f=self._new();f.record_outcome('RAW','A',0.0);del f
        raw=json.loads(self.path.read_text())
        self.assertEqual(raw['schema'],G2UnifiedExecutionFabricV5.FILE_SCHEMA)
        with self.assertRaisesRegex(ValueError,'FILE_ENVELOPE_MUST_BE_LOADED'):
            G2UnifiedExecutionFabricV5(make_base(),api_state={},continuity_state=raw)

    def test_file_size_limit(self):
        huge=self.dir/'huge.json'
        huge.write_bytes(b'{' + b'x'*(G2UnifiedExecutionFabricV5.MAX_CHECKPOINT_FILE_BYTES+1))
        with self.assertRaisesRegex(ValueError,'SIZE_LIMIT'):
            G2UnifiedExecutionFabricV5.load_continuity_checkpoint(huge)

if __name__=='__main__':
    import unittest
    unittest.main()
