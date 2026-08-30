from __future__ import annotations
from pathlib import Path
import hashlib,json,os,sys

ROOT=Path(__file__).resolve().parent
PKG=ROOT/'yado_rc8_v36'
sys.path.insert(0,str(PKG))

from yado_core_v3_0_rc8_external_cognitive import UnifiedYADOKernelV30RC8ExternalCognitive
from yado_metacognitive_control_runtime_v1 import CapabilityBoundaryProfile,CapabilityObservation

META=ROOT.parent/'receipts'/'yado-fresh-meta-selection-conjunctive-vs-existing-v1-latest.json'
READMIT=ROOT.parent/'receipts'/'yado-g0-conjunctive-algorithm-readmission-v2-latest.json'
ENTRY=ROOT.parent/'candidates'/'shadow-algorithm-bank'/'conjunctive-rule-inducer-v1.json'
OUT=ROOT/'g0_meta_selection_admission_decision_v1'
OUT.mkdir(exist_ok=True)

def canon(o): return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def sha_file(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def objdict(x): return dict(x.__dict__) if hasattr(x,'__dict__') else x

meta=json.loads(META.read_text())
readmit=json.loads(READMIT.read_text())
entry=json.loads(ENTRY.read_text())

if meta.get('status')!='PASS_FRESH_META_SELECTION_CONJUNCTIVE_VS_EXISTING_V1':
    raise RuntimeError('META_SELECTION_PASS_REQUIRED')
if readmit.get('decision',{}).get('action')!='EXECUTE':
    raise RuntimeError('G0_READMISSION_EXECUTE_REQUIRED')
if entry.get('scope')!='SHADOW_ONLY' or entry.get('canonical_active') is not False:
    raise RuntimeError('SHADOW_ENTRY_CONTRACT_INVALID')

state=PKG/'yado_canonical_state_v3_rc8_external_cognitive.json'
before=sha_file(state)
k=UnifiedYADOKernelV30RC8ExternalCognitive(db_path=str(OUT/'g0.sqlite'))

cap='META_SELECT_CONJUNCTIVE_VS_EXISTING_BANK'
profile=CapabilityBoundaryProfile()
# Selection evidence: simple task preserves old algorithm, five harder fresh tasks select
# the new algorithm, all with blind success.
obs=[
  (0.45, meta['results']['UNARY_SANITY']['selected_family']=='EXISTING_RULE_PROGRAM_SYNTHESIZER' and meta['results']['UNARY_SANITY']['fresh_blind']==1.0),
  (0.68, meta['results']['ARTIFACT_INTEGRITY']['fresh_blind']==1.0),
  (0.74, meta['results']['INSTRUMENT_CALIBRATION']['fresh_blind']==1.0),
  (0.80, meta['results']['DATA_PROVENANCE']['fresh_blind']==1.0),
  (0.84, meta['results']['DISTRIBUTED_COMMIT']['fresh_blind']==1.0),
  (0.88, meta['results']['DEPLOYMENT_POLICY']['fresh_blind']==1.0),
]
for d,s in obs:
    profile.update(CapabilityObservation(cap,d,bool(s)))

task={
  'task_id':'G0-META-SELECT-ADMISSION-001',
  'capability':cap,
  'difficulty':0.82,
  'verbal_confidence':0.96,
  'evidence_coverage':1.0,
  'novelty':0.66,
  'framework_conflict':False,
}
decision=k.metacognitive_decide(task,profile)
d=objdict(decision)
action=d.get('action')

items=[
  {
    'item_id':'META-SELECTION-EVIDENCE',
    'source':'RUN_33313898337',
    'source_kind':'tool_observation',
    'content':{
      'status':meta['status'],
      'receipt_sha256':meta['receipt_sha256'],
      'selected_counts':meta['selected_counts'],
      'all_selected_fresh_blind_ge_0_97':meta['all_selected_fresh_blind_ge_0_97'],
      'selection_rule':meta['selection_rule'],
    },
    'confidence':1.0,'goal_relevance':1.0,'novelty':0.95,'urgency':0.88,'epistemic_risk':0.0,
    'tags':('meta_selection','fresh_blind','algorithm_bank'),
  },
  {
    'item_id':'READMISSION-EVIDENCE',
    'source':'RUN_33313727864',
    'source_kind':'tool_observation',
    'content':{
      'decision':readmit['decision'],
      'admission_authorized':readmit['admission_authorized'],
      'receipt_sha256':readmit['receipt_sha256'],
    },
    'confidence':1.0,'goal_relevance':0.92,'novelty':0.55,'urgency':0.75,'epistemic_risk':0.0,
    'tags':('g0_authority','readmission'),
  },
  {
    'item_id':'SHADOW-BANK-ENTRY',
    'source':'SHADOW_ALGORITHM_BANK',
    'source_kind':'self_model',
    'content':{
      'entry_id':entry['entry_id'],'entry_digest':entry['entry_digest'],
      'scope':entry['scope'],'canonical_active':entry['canonical_active'],
    },
    'confidence':1.0,'goal_relevance':0.9,'novelty':0.25,'urgency':0.6,'epistemic_risk':0.0,
    'tags':('shadow_bank','self_model'),
  }
]

def consume(xs):
    return [{'id':x.item_id,'source':x.source,'confidence':x.confidence} for x in xs]

observed='ENABLE_SHADOW_META_SELECTION' if action=='EXECUTE' else 'WITHHOLD_SHADOW_META_SELECTION'
ep=k.digital_conscious_cycle(
    goal='Decide whether the G0-authorized conjunctive rule inducer may become actively selectable in the shadow algorithm bank after fresh comparison against the existing bank.',
    items=items,
    consumers={'EVIDENCE_SUMMARY':consume},
    metacognitive_task=task,
    capability_profile=profile,
    context='SHADOW_ALGORITHM_META_SELECTION_ADMISSION',
    action='EVALUATE_SHADOW_META_SELECTION_ACTIVATION',
    possible_outcomes=('ENABLE_SHADOW_META_SELECTION','WITHHOLD_SHADOW_META_SELECTION','SEEK_MORE_EVIDENCE'),
    observed_outcome=observed,
    proposed_belief_ids=(),
)

registry_entry=None
if action=='EXECUTE':
    registry_entry={
      'schema':'yado.shadow_algorithm_bank.registry_entry.v1',
      'entry_id':entry['entry_id'],
      'family':entry['family'],
      'organ':entry['organ'],
      'component_digest':entry['component_digest'],
      'entry_digest':entry['entry_digest'],
      'state':'ACTIVE_FOR_SHADOW_META_SELECTION',
      'canonical_active':False,
      'selection_policy':'VALIDATION_THEN_COMPLEXITY_THEN_EXISTING_ON_EXACT_TIE',
      'activation_authority':'G0_METACOGNITIVE_EXECUTE',
      'activation_decision':d,
      'activation_evidence_receipt':meta['receipt_sha256'],
      'canonical_promotion_required_for_live_replacement':True,
    }
    registry_entry['registry_entry_digest']=hashlib.sha256(canon(registry_entry).encode()).hexdigest()
    (OUT/'registry_entry.json').write_text(json.dumps(registry_entry,indent=2,sort_keys=True,default=str)+'\n')

after=sha_file(state)
report={
  'schema':'yado.g0.meta_selection_admission_decision.v1',
  'status':'PASS_G0_META_SELECTION_ADMISSION_DECISION_V1',
  'github_run_id':os.getenv('GITHUB_RUN_ID'),'github_sha':os.getenv('GITHUB_SHA'),
  'developmental_head':'G0_RC8_V36',
  'decision':d,'shadow_meta_selection_enabled':action=='EXECUTE',
  'registry_entry':registry_entry,
  'canonical_parent_sha256_before':before,'canonical_parent_sha256_after':after,
  'canonical_parent_byte_identical':before==after,
  'canonical_mutation':False,'promotion_applied':False,
  'next_required_capability':'RUN_SHADOW_META_SELECTION_IN_LIVE_DEVELOPMENTAL_TASKS_V1' if action=='EXECUTE' else 'SEEK_MORE_META_SELECTION_EVIDENCE',
}
report['receipt_sha256']=hashlib.sha256(canon(report).encode()).hexdigest()
(ROOT/'yado_g0_meta_selection_admission_decision_v1_receipt.json').write_text(json.dumps(report,indent=2,sort_keys=True,default=str)+'\n')
print(json.dumps({
  'status':report['status'],'decision':d,
  'shadow_meta_selection_enabled':report['shadow_meta_selection_enabled'],
  'canonical_parent_byte_identical':report['canonical_parent_byte_identical'],
  'next_required_capability':report['next_required_capability'],
  'receipt_sha256':report['receipt_sha256'],
},indent=2,sort_keys=True,default=str))
k.close()
