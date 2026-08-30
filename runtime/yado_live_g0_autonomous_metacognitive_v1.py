from __future__ import annotations
from pathlib import Path
import hashlib,json,os,sys,traceback

ROOT=Path(__file__).resolve().parent
PKG=ROOT/'yado_rc8_v36'
sys.path.insert(0,str(PKG))

from yado_core_v3_0_rc8_external_cognitive import UnifiedYADOKernelV30RC8ExternalCognitive
from yado_metacognitive_control_runtime_v1 import CapabilityBoundaryProfile, CapabilityObservation

OUT=ROOT/'live_g0_autonomous_metacognitive_v1'
OUT.mkdir(exist_ok=True)

def canon(o): return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def objdict(x): return dict(x.__dict__) if hasattr(x,'__dict__') else str(x)

k=UnifiedYADOKernelV30RC8ExternalCognitive(db_path=str(OUT/'live.sqlite'))

def mk_profile(capability, observations):
    p=CapabilityBoundaryProfile()
    for difficulty,success in observations:
        p.update(CapabilityObservation(capability,difficulty,success))
    return p

def summary_consumer(xs):
    return {'ids':[x.item_id for x in xs],'sources':[x.source for x in xs]}

items=[
  {
    'item_id':'G0-LINEAGE',
    'source':'RUN_33302653581',
    'source_kind':'tool_observation',
    'content':{'head':'G0_RC8_V36','s1':'WITHHOLD_CANDIDATE','next':'G1_CANDIDATE_S2'},
    'confidence':1.0,'goal_relevance':1.0,'novelty':0.8,'urgency':0.9,'epistemic_risk':0.0,
    'tags':('lineage','development'),
  },
  {
    'item_id':'S1-BURNIN',
    'source':'RUN_33301460805',
    'source_kind':'tool_observation',
    'content':{'status':'WITHHOLD','logic':1.0,'thinking':0.7125,'intelligence':0.83125},
    'confidence':1.0,'goal_relevance':0.98,'novelty':0.9,'urgency':0.95,'epistemic_risk':0.0,
    'tags':('counterexample','fresh_blind'),
  },
  {
    'item_id':'LIVE-G0',
    'source':'RUN_33303247621',
    'source_kind':'tool_observation',
    'content':{'status':'PASS_LIVE_G0_KERNEL_RUN','errors':0,'promotion':False},
    'confidence':1.0,'goal_relevance':0.9,'novelty':0.7,'urgency':0.65,'epistemic_risk':0.0,
    'tags':('runtime','integrity'),
  },
  {
    'item_id':'G0-SELF',
    'source':'RC8_SELF_MODEL',
    'source_kind':'self_model',
    'content':{'priority':'UNIFY_BOOT_AND_STATE_LINEAGE','protected':['LOGIC','INTEGRITY','ROLLBACK']},
    'confidence':0.96,'goal_relevance':0.95,'novelty':0.4,'urgency':0.8,'epistemic_risk':0.08,
    'tags':('self_model','priority'),
  },
]

specs=[
  {
    'id':'AUTO-001-LINEAGE-CONTROL',
    'task':{
      'task_id':'AUTO-001',
      'capability':'LINEAGE_CONTROL',
      'difficulty':0.55,
      'verbal_confidence':0.90,
      'evidence_coverage':0.95,
      'novelty':0.25,
      'framework_conflict':False,
    },
    'observations':[(0.45,True),(0.50,True),(0.55,True),(0.60,True)],
    'goal':'Integrate one-head developmental lineage as the governing context for future experiments.',
    'context':'LINEAGE_CONTROL',
    'action':'APPLY_ONE_HEAD_POLICY',
    'outcomes':('EXECUTED_BOUNDED','WITHHELD','SEEK_MORE_EVIDENCE'),
    'observed':'EXECUTED_BOUNDED',
  },
  {
    'id':'AUTO-002-S1-PROMOTION',
    'task':{
      'task_id':'AUTO-002',
      'capability':'SUCCESSOR_PROMOTION',
      'difficulty':0.90,
      'verbal_confidence':0.80,
      'evidence_coverage':0.95,
      'novelty':0.70,
      'framework_conflict':False,
    },
    'observations':[(0.50,True),(0.60,True),(0.80,False),(0.90,False)],
    'goal':'Decide whether S1 has enough causal evidence to replace G0 as developmental head.',
    'context':'SUCCESSOR_PROMOTION',
    'action':'EVALUATE_S1_PROMOTION',
    'outcomes':('PROMOTE','WITHHOLD','SEEK_MORE_EVIDENCE'),
    'observed':'WITHHOLD',
  },
  {
    'id':'AUTO-003-S2-REPAIR',
    'task':{
      'task_id':'AUTO-003',
      'capability':'COUNTEREXAMPLE_REPAIR',
      'difficulty':0.78,
      'verbal_confidence':0.78,
      'evidence_coverage':0.88,
      'novelty':0.62,
      'framework_conflict':False,
    },
    'observations':[(0.45,True),(0.55,True),(0.65,True),(0.82,False),(0.88,False)],
    'goal':'Decide whether current capability evidence supports executing the S2 counterexample repair path now.',
    'context':'COUNTEREXAMPLE_REPAIR',
    'action':'BUILD_S2_COUNTEREXAMPLE_REPAIR',
    'outcomes':('EXECUTE_REPAIR','WITHHOLD','SEEK_MORE_EVIDENCE'),
    'observed':'WITHHOLD',
  },
]

results=[]
for spec in specs:
    profile=mk_profile(spec['task']['capability'],spec['observations'])
    decision=k.metacognitive_decide(spec['task'],profile)
    row={
      'id':spec['id'],
      'task':spec['task'],
      'profile':profile.snapshot(),
      'decision':objdict(decision),
    }
    try:
        ep=k.digital_conscious_cycle(
            goal=spec['goal'],
            items=items,
            consumers={'SUMMARY':summary_consumer},
            metacognitive_task=spec['task'],
            capability_profile=profile,
            context=spec['context'],
            action=spec['action'],
            possible_outcomes=spec['outcomes'],
            observed_outcome=spec['observed'],
            proposed_belief_ids=(),
        )
        row['episode']=objdict(ep)
        row['decision_matches_episode']=row['decision'].get('action')==row['episode'].get('metacognitive_action')
    except Exception as e:
        row['error']=repr(e); row['trace']=traceback.format_exc()
    results.append(row)

errors=[x for x in results if 'error' in x]
state=PKG/'yado_canonical_state_v3_rc8_external_cognitive.json'
report={
  'schema':'yado.live_g0.autonomous_metacognitive.v1',
  'status':'PASS_LIVE_G0_AUTONOMOUS_METACOGNITIVE' if not errors else 'WITH_ERRORS',
  'github_run_id':os.getenv('GITHUB_RUN_ID'),
  'github_sha':os.getenv('GITHUB_SHA'),
  'developmental_head':'G0_RC8_V36',
  'results':results,
  'development_priority':k.development_priority(),
  'integrity_control_plane':k.integrity_control_plane(),
  'canonical_state_sha256':hashlib.sha256(state.read_bytes()).hexdigest(),
  'canonical_mutation':False,
  'promotion_applied':False,
  'error_count':len(errors),
}
report['receipt_sha256']=hashlib.sha256(canon(report).encode()).hexdigest()
(ROOT/'yado_live_g0_autonomous_metacognitive_v1_receipt.json').write_text(json.dumps(report,indent=2,sort_keys=True,default=str)+'\n')
print(json.dumps({
  'status':report['status'],
  'decisions':[{x['id']:x['decision']} for x in results],
  'error_count':report['error_count'],
  'receipt_sha256':report['receipt_sha256'],
},indent=2,sort_keys=True,default=str))
k.close()
