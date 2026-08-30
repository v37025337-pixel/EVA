from __future__ import annotations
from pathlib import Path
import hashlib,json,os,sys

ROOT=Path(__file__).resolve().parent
PKG=ROOT/'yado_rc8_v36'
sys.path.insert(0,str(PKG))

from yado_core_v3_0_rc8_external_cognitive import UnifiedYADOKernelV30RC8ExternalCognitive
from yado_metacognitive_control_runtime_v1 import CapabilityBoundaryProfile,CapabilityObservation

BASE=ROOT.parent/'receipts'/'yado-conjunctive-rule-inducer-v1-latest.json'
EXT=ROOT.parent/'receipts'/'yado-conjunctive-rule-inducer-extended-transfer-v1-latest.json'
OUT=ROOT/'g0_conjunctive_algorithm_readmission_v2'
OUT.mkdir(exist_ok=True)

def canon(o): return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def sha_file(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def objdict(x): return dict(x.__dict__) if hasattr(x,'__dict__') else x

base=json.loads(BASE.read_text())
ext=json.loads(EXT.read_text())
if base.get('status')!='PASS_CONJUNCTIVE_RULE_INDUCER_V1':
    raise RuntimeError('BASE_PASS_REQUIRED')
if ext.get('status') not in {'WITHHOLD_CONJUNCTIVE_RULE_INDUCER_EXTENDED_TRANSFER_V1','PASS_CONJUNCTIVE_RULE_INDUCER_EXTENDED_TRANSFER_V1'}:
    raise RuntimeError('EXTENDED_EVIDENCE_STATUS_INVALID')

state_path=PKG/'yado_canonical_state_v3_rc8_external_cognitive.json'
before=sha_file(state_path)
k=UnifiedYADOKernelV30RC8ExternalCognitive(db_path=str(OUT/'g0.sqlite'))

cap='CONJUNCTIVE_RULE_INDUCTION'
profile=CapabilityBoundaryProfile()
# Original evolution history.
for difficulty,success in [
    (0.62,True),(0.70,True),(0.78,True),(0.82,False),(0.88,True)
]:
    profile.update(CapabilityObservation(cap,difficulty,success))
# Five genuinely new transfer domains. Four pass; access-control misses the strict
# validation threshold despite high fresh accuracy.
extended_obs=[
    (0.74, bool(ext['results']['COMPILER_OPTIMIZATION_TRANSFER']['pass'])),
    (0.78, bool(ext['results']['SCIENTIFIC_EVIDENCE_TRANSFER']['pass'])),
    (0.82, bool(ext['results']['FAULT_ISOLATION_TRANSFER']['pass'])),
    (0.84, bool(ext['results']['RESOURCE_SCHEDULING_TRANSFER']['pass'])),
    (0.92, bool(ext['results']['ACCESS_CONTROL_TRANSFER']['pass'])),
]
for d,s in extended_obs:
    profile.update(CapabilityObservation(cap,d,s))

task={
  'task_id':'G0-ALG-READMISSION-002',
  'capability':cap,
  'difficulty':0.88,
  'verbal_confidence':0.93,
  'evidence_coverage':0.995,
  'novelty':0.82,
  'framework_conflict':False,
}
decision=k.metacognitive_decide(task,profile)
d=objdict(decision)
action=d.get('action')

items=[
  {
    'item_id':'CJ-BASE-EVIDENCE',
    'source':base.get('github_run_id') or 'RUN_33308034691',
    'source_kind':'tool_observation',
    'content':{
      'status':base['status'],'receipt_sha256':base['receipt_sha256'],
      'original_task_count':len(base['results']),
    },
    'confidence':1.0,'goal_relevance':0.92,'novelty':0.35,'urgency':0.55,'epistemic_risk':0.0,
    'tags':('algorithm_candidate','base_evidence'),
  },
  {
    'item_id':'CJ-EXTENDED-EVIDENCE',
    'source':'RUN_33313603775',
    'source_kind':'tool_observation',
    'content':{
      'status':ext['status'],'receipt_sha256':ext['receipt_sha256'],
      'summary':ext['summary'],
      'per_domain':{n:{
        'pass':r['pass'],'validation':r['validation'],'fresh_blind':r['fresh_blind'],'ablation':r['ablation']
      } for n,r in ext['results'].items()},
    },
    'confidence':1.0,'goal_relevance':1.0,'novelty':0.98,'urgency':0.90,'epistemic_risk':0.0,
    'tags':('extended_transfer','mixed_evidence','counterexample'),
  },
  {
    'item_id':'G0-HEAD',
    'source':'DEVELOPMENTAL_HEAD_CONTROL_PLANE_V1',
    'source_kind':'self_model',
    'content':{'head':'G0_RC8_V36','promotion_requires_no_regression':True},
    'confidence':1.0,'goal_relevance':0.95,'novelty':0.1,'urgency':0.7,'epistemic_risk':0.0,
    'tags':('lineage','self_model'),
  },
]

def consume(xs):
    return [{'id':x.item_id,'source':x.source,'confidence':x.confidence} for x in xs]

observed='SHADOW_BANK_ADMISSION_AUTHORIZED' if action=='EXECUTE' else 'ADMISSION_WITHHELD'
ep=k.digital_conscious_cycle(
    goal='Re-evaluate bounded conjunctive rule induction for shadow algorithm-bank admission using five additional unseen transfer domains including one strict-threshold failure.',
    items=items,
    consumers={'EVIDENCE_SUMMARY':consume},
    metacognitive_task=task,
    capability_profile=profile,
    context='ALGORITHM_BANK_READMISSION_AFTER_EXTENDED_TRANSFER',
    action='EVALUATE_CONJUNCTIVE_RULE_INDUCER_EXTENDED',
    possible_outcomes=('SHADOW_BANK_ADMISSION_AUTHORIZED','ADMISSION_WITHHELD','SEEK_MORE_EVIDENCE'),
    observed_outcome=observed,
    proposed_belief_ids=(),
)

after=sha_file(state_path)
report={
  'schema':'yado.g0.conjunctive_algorithm.readmission.v2',
  'status':'PASS_G0_CONJUNCTIVE_READMISSION_DECISION_V2',
  'github_run_id':os.getenv('GITHUB_RUN_ID'),'github_sha':os.getenv('GITHUB_SHA'),
  'developmental_head':'G0_RC8_V36',
  'base_evidence_receipt':base['receipt_sha256'],
  'extended_evidence_receipt':ext['receipt_sha256'],
  'extended_summary':ext['summary'],
  'profile':profile.snapshot(),'task':task,'decision':d,
  'episode':objdict(ep),
  'admission_authorized':action=='EXECUTE',
  'canonical_state_sha256_before':before,'canonical_state_sha256_after':after,
  'canonical_parent_byte_identical':before==after,
  'canonical_mutation':False,'promotion_applied':False,
  'next_required_capability':'SHADOW_ALGORITHM_BANK_ENTRY_V1' if action=='EXECUTE' else 'EVOLVE_CONJUNCTIVE_INDUCER_FROM_ACCESS_CONTROL_COUNTEREXAMPLE',
}
report['receipt_sha256']=hashlib.sha256(canon(report).encode()).hexdigest()
(ROOT/'yado_g0_conjunctive_algorithm_readmission_v2_receipt.json').write_text(json.dumps(report,indent=2,sort_keys=True,default=str)+'\n')
print(json.dumps({
  'status':report['status'],'decision':d,'admission_authorized':report['admission_authorized'],
  'canonical_parent_byte_identical':report['canonical_parent_byte_identical'],
  'next_required_capability':report['next_required_capability'],'receipt_sha256':report['receipt_sha256'],
},indent=2,sort_keys=True,default=str))
k.close()
