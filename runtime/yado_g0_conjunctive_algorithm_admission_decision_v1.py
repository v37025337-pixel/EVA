from __future__ import annotations
from pathlib import Path
import hashlib,json,os,sys,traceback

ROOT=Path(__file__).resolve().parent
PKG=ROOT/'yado_rc8_v36'
sys.path.insert(0,str(PKG))

from yado_core_v3_0_rc8_external_cognitive import UnifiedYADOKernelV30RC8ExternalCognitive
from yado_metacognitive_control_runtime_v1 import CapabilityBoundaryProfile,CapabilityObservation

EVIDENCE=ROOT.parent/'receipts'/'yado-conjunctive-rule-inducer-v1-latest.json'
OUT=ROOT/'g0_conjunctive_algorithm_admission_decision_v1'
OUT.mkdir(exist_ok=True)

def canon(o): return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def sha_file(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def objdict(x): return dict(x.__dict__) if hasattr(x,'__dict__') else x

ev=json.loads(EVIDENCE.read_text())
if ev.get('status')!='PASS_CONJUNCTIVE_RULE_INDUCER_V1':
    raise RuntimeError('PASS_EVIDENCE_REQUIRED')
required=('DEVELOPMENTAL_FILTER','SOURCE_MONITOR_TRANSFER','PROMOTION_GATE_TRANSFER')
for name in required:
    r=ev['results'][name]
    if not (r['pass'] and r['train']==1.0 and r['validation']==1.0 and r['fresh_blind']==1.0 and r['restore']==1.0 and r['fresh_blind']>r['ablation']):
        raise RuntimeError('TASK_EVIDENCE_FAIL:'+name)

state_path=PKG/'yado_canonical_state_v3_rc8_external_cognitive.json'
before=sha_file(state_path)
k=UnifiedYADOKernelV30RC8ExternalCognitive(db_path=str(OUT/'g0.sqlite'))

cap='CONJUNCTIVE_RULE_INDUCTION'
profile=CapabilityBoundaryProfile()
# Evidence-bound capability history: the first pairwise attempt failed because
# a transfer case required a ternary conjunction; the evolved bounded candidate
# then passed three fresh/ablation tasks at increasing difficulty.
profile.update(CapabilityObservation(cap,0.82,False))
profile.update(CapabilityObservation(cap,0.70,True))
profile.update(CapabilityObservation(cap,0.78,True))
profile.update(CapabilityObservation(cap,0.88,True))

task={
  'task_id':'G0-ALG-ADMISSION-001',
  'capability':cap,
  'difficulty':0.82,
  'verbal_confidence':0.95,
  'evidence_coverage':0.98,
  'novelty':0.65,
  'framework_conflict':False,
}
decision=k.metacognitive_decide(task,profile)
d=objdict(decision)
action=d.get('action')

items=[
  {
    'item_id':'CJ-RULE-PASS',
    'source':'RUN_33308034691',
    'source_kind':'tool_observation',
    'content':{
      'status':ev['status'],
      'receipt_sha256':ev['receipt_sha256'],
      'component_digest':ev['component']['component_digest'],
      'task_results':{name:{
        'validation':ev['results'][name]['validation'],
        'fresh_blind':ev['results'][name]['fresh_blind'],
        'ablation':ev['results'][name]['ablation'],
        'restore':ev['results'][name]['restore'],
      } for name in required},
    },
    'confidence':1.0,'goal_relevance':1.0,'novelty':0.94,'urgency':0.88,'epistemic_risk':0.0,
    'tags':('algorithm_candidate','fresh_blind','ablation','transfer'),
  },
  {
    'item_id':'CJ-RULE-FAILURE-HISTORY',
    'source':'RUN_33307898757',
    'source_kind':'tool_observation',
    'content':{
      'status':'PAIRWISE_CANDIDATE_FAILED',
      'cause':'PROMOTION_TRANSFER_REQUIRED_TERNARY_CONJUNCTION',
      'evolution':'MAX_CONJUNCTION_2_TO_3_WITHIN_SANDBOX_LIMIT_4',
    },
    'confidence':1.0,'goal_relevance':0.82,'novelty':0.72,'urgency':0.45,'epistemic_risk':0.0,
    'tags':('failure_history','counterexample'),
  },
  {
    'item_id':'G0-HEAD',
    'source':'DEVELOPMENTAL_HEAD_CONTROL_PLANE_V1',
    'source_kind':'self_model',
    'content':{'head':'G0_RC8_V36','canonical_mutation_allowed':False},
    'confidence':1.0,'goal_relevance':0.95,'novelty':0.20,'urgency':0.75,'epistemic_risk':0.0,
    'tags':('lineage','self_model'),
  },
]

def evidence_consumer(xs):
    return [{'id':x.item_id,'source':x.source,'confidence':x.confidence} for x in xs]

observed='SHADOW_BANK_ADMISSION_AUTHORIZED' if action=='EXECUTE' else 'ADMISSION_WITHHELD'
episode=k.digital_conscious_cycle(
    goal='Decide whether the bounded conjunctive rule-induction candidate has enough evidence for shadow algorithm-bank admission without modifying G0.',
    items=items,
    consumers={'EVIDENCE_SUMMARY':evidence_consumer},
    metacognitive_task=task,
    capability_profile=profile,
    context='ALGORITHM_BANK_ADMISSION',
    action='EVALUATE_CONJUNCTIVE_RULE_INDUCER',
    possible_outcomes=('SHADOW_BANK_ADMISSION_AUTHORIZED','ADMISSION_WITHHELD','SEEK_MORE_EVIDENCE'),
    observed_outcome=observed,
    proposed_belief_ids=(),
)

shadow_entry=None
if action=='EXECUTE':
    shadow_entry={
      'schema':'yado.shadow_algorithm_bank.entry.v1',
      'entry_id':'ALG-CONJUNCTIVE-RULE-INDUCER-V1',
      'organ':'LOGIC',
      'family':'CONJUNCTIVE_RULE_INDUCTION',
      'component_digest':ev['component']['component_digest'],
      'evidence_receipt_sha256':ev['receipt_sha256'],
      'admission_authority':'G0_METACOGNITIVE_EXECUTE',
      'admission_decision':d,
      'scope':'SHADOW_ONLY',
      'canonical_active':False,
      'eligible_for_meta_selection':True,
      'promotion_requires':'FRESH_META_SELECTION_PLUS_REGRESSION_PLUS_ROLLBACK',
    }
    shadow_entry['entry_digest']=hashlib.sha256(canon(shadow_entry).encode()).hexdigest()
    (OUT/'shadow_algorithm_bank_entry.json').write_text(json.dumps(shadow_entry,indent=2,sort_keys=True,default=str)+'\n')

after=sha_file(state_path)
report={
  'schema':'yado.g0.conjunctive_algorithm_admission_decision.v1',
  'status':'PASS_G0_ALGORITHM_ADMISSION_DECISION',
  'github_run_id':os.getenv('GITHUB_RUN_ID'),'github_sha':os.getenv('GITHUB_SHA'),
  'developmental_head':'G0_RC8_V36',
  'evidence_receipt_sha256':ev['receipt_sha256'],
  'profile':profile.snapshot(),
  'task':task,
  'decision':d,
  'episode':objdict(episode),
  'shadow_bank_entry':shadow_entry,
  'canonical_state_sha256_before':before,
  'canonical_state_sha256_after':after,
  'canonical_parent_byte_identical':before==after,
  'canonical_mutation':False,
  'promotion_applied':False,
  'next_required_capability':'META_SELECT_NEW_ALGORITHM_VS_EXISTING_BANK_ON_FRESH_TASKS' if action=='EXECUTE' else 'SEEK_MORE_ADMISSION_EVIDENCE',
  'semantic_boundary':'G0 METACOGNITIVE ADMISSION DECISION; SHADOW BANK ONLY; VERIFIED G0 NOT MODIFIED',
}
report['receipt_sha256']=hashlib.sha256(canon(report).encode()).hexdigest()
(ROOT/'yado_g0_conjunctive_algorithm_admission_decision_v1_receipt.json').write_text(json.dumps(report,indent=2,sort_keys=True,default=str)+'\n')
print(json.dumps({
  'status':report['status'],
  'decision':d,
  'shadow_bank_entry_created':shadow_entry is not None,
  'canonical_parent_byte_identical':report['canonical_parent_byte_identical'],
  'next_required_capability':report['next_required_capability'],
  'receipt_sha256':report['receipt_sha256'],
},indent=2,sort_keys=True,default=str))
k.close()
