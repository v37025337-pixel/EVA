from __future__ import annotations
from pathlib import Path
import hashlib,itertools,json,os,random,sys

ROOT=Path(__file__).resolve().parent
PKG=ROOT/'yado_rc8_v36'
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(PKG))

from yado_core_v2_1 import RuleProgramSynthesizer,BoundedRuleSandbox
from yado_conjunctive_rule_inducer_v1 import ConjunctiveRuleInducerV1,program_acc
from yado_core_v3_0_rc8_external_cognitive import UnifiedYADOKernelV30RC8ExternalCognitive
from yado_metacognitive_control_runtime_v1 import CapabilityBoundaryProfile,CapabilityObservation

REG=ROOT.parent/'candidates'/'shadow-algorithm-bank'/'active-registry-entry.json'
STATE=PKG/'yado_canonical_state_v3_rc8_external_cognitive.json'
OUT=ROOT/'live_shadow_meta_selection_developmental_v1'
OUT.mkdir(exist_ok=True)

def canon(o): return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def sha_file(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def objdict(x): return dict(x.__dict__) if hasattr(x,'__dict__') else x

reg=json.loads(REG.read_text())
if reg.get('state')!='ACTIVE_FOR_SHADOW_META_SELECTION':
    raise RuntimeError('ACTIVE_SHADOW_META_SELECTION_REQUIRED')

GEN=['THINKING_BOUNDARY_REASONING','INTELLIGENCE_BOUNDARY_REASONING','REPRESENTATION_INVARIANCE']
CAN=['UNIFY_BOOT_AND_STATE_LINEAGE','ADD_PREIMPORT_DEPENDENCY_LOCK','HARDEN_DIRECT_EVIDENCE_FETCH',
     'PROTECT_HISTORICAL_STATE_FROM_MUTATION','CONSOLIDATE_VALIDATED_FRONTIER_PORTFOLIO_INSTANCE_LOCALLY',
     'DURABILIZE_HOST_CAPABILITY_MODEL','STRUCTURAL_FRONTIER_ROUTER']
ALL=GEN+CAN

def active(ctx):
    out=[]
    if ctx['current_generation_active']:out.extend(GEN)
    if not ctx['lineage_verified']:out.append(CAN[0])
    if not ctx['dependency_lock_verified']:out.append(CAN[1])
    if not ctx['evidence_fetch_hardened']:out.append(CAN[2])
    if not ctx['historical_state_protected']:out.append(CAN[3])
    out.extend(CAN[4:])
    return out

def cases(ctxs,seed):
    r=random.Random(seed);out=[]
    for c in ctxs:
        for role in ALL:
            out.append({'input':{'role':role,**c,'live_noise':r.randint(0,5)},'expected':'KEEP' if role in active(c) else 'DROP'})
    return out

contexts=[dict(zip(
 ['lineage_verified','dependency_lock_verified','evidence_fetch_hardened','historical_state_protected','current_generation_active'],
 vals
)) for vals in itertools.product([False,True],repeat=5)]

current_ctx={
 'lineage_verified':True,
 'dependency_lock_verified':False,
 'evidence_fetch_hardened':False,
 'historical_state_protected':False,
 'current_generation_active':True,
}
others=[c for c in contexts if c!=current_ctx]
train_ctx=others[:20]
val_ctx=others[20:]
train=cases(train_ctx,91001);val=cases(val_ctx,91002)

cands=[]
try:
    old=RuleProgramSynthesizer.synthesize('LIVE_DEVELOPMENTAL_FILTER','LOGIC',train,min_support=2)
    cands.append(('EXISTING_RULE_PROGRAM_SYNTHESIZER',old,program_acc(old,val)))
except Exception as e:
    cands.append(('EXISTING_RULE_PROGRAM_SYNTHESIZER',None,0.0))

new=ConjunctiveRuleInducerV1.synthesize('LIVE_DEVELOPMENTAL_FILTER','LOGIC',train,min_support=2,max_rules=12)
cands.append(('CONJUNCTIVE_RULE_INDUCTION',new,program_acc(new,val)))

def complexity(p):
    if p is None:return 10**9
    return len(p.rules)+sum(len(r.predicates) for r in p.rules)

cands.sort(key=lambda x:(x[2],-complexity(x[1]),x[0]=='EXISTING_RULE_PROGRAM_SYNTHESIZER'),reverse=True)
family,program,validation=cands[0]

current_priority=[]
for role in ALL:
    payload={'role':role,**current_ctx,'live_noise':99}
    if BoundedRuleSandbox.execute(program,payload)=='KEEP':
        current_priority.append(role)
expected_priority=active(current_ctx)
live_pass=current_priority==expected_priority

before=sha_file(STATE)
k=UnifiedYADOKernelV30RC8ExternalCognitive(db_path=str(OUT/'g0.sqlite'))

profile=CapabilityBoundaryProfile()
for d,s in [(0.45,True),(0.65,True),(0.75,True),(0.82,True),(0.88,True),(0.92,live_pass)]:
    profile.update(CapabilityObservation('LIVE_SHADOW_META_SELECTION',d,s))
task={
 'task_id':'G0-LIVE-SHADOW-META-001',
 'capability':'LIVE_SHADOW_META_SELECTION',
 'difficulty':0.88,
 'verbal_confidence':0.95,
 'evidence_coverage':1.0,
 'novelty':0.72,
 'framework_conflict':False,
}
decision=k.metacognitive_decide(task,profile)
d=objdict(decision)

items=[
 {
  'item_id':'SHADOW-SELECTOR',
  'source':'SHADOW_ALGORITHM_BANK',
  'source_kind':'self_model',
  'content':{'selected_family':family,'validation':validation,'registry_entry_digest':reg['registry_entry_digest']},
  'confidence':1.0,'goal_relevance':1.0,'novelty':0.8,'urgency':0.85,'epistemic_risk':0.0,
  'tags':('shadow_bank','meta_selection'),
 },
 {
  'item_id':'LIVE-PRIORITY',
  'source':'LIVE_SHADOW_DEVELOPMENTAL_FILTER',
  'source_kind':'tool_observation',
  'content':{'current_context':current_ctx,'effective_priority':current_priority,'expected_priority':expected_priority,'pass':live_pass},
  'confidence':1.0,'goal_relevance':1.0,'novelty':0.95,'urgency':0.95,'epistemic_risk':0.0,
  'tags':('developmental_priority','live_blind'),
 }
]
def consume(xs):
    return [x.content for x in xs]

observed='LIVE_SHADOW_SELECTION_ACCEPTED' if d.get('action')=='EXECUTE' and live_pass else 'LIVE_SHADOW_SELECTION_WITHHELD'
ep=k.digital_conscious_cycle(
  goal='Use the G0-authorized shadow algorithm bank to compute the current effective developmental priority without changing canonical G0.',
  items=items,consumers={'DEVELOPMENT_VIEW':consume},
  metacognitive_task=task,capability_profile=profile,
  context='LIVE_SHADOW_META_SELECTION',action='COMPUTE_EFFECTIVE_DEVELOPMENTAL_PRIORITY',
  possible_outcomes=('LIVE_SHADOW_SELECTION_ACCEPTED','LIVE_SHADOW_SELECTION_WITHHELD'),
  observed_outcome=observed,proposed_belief_ids=(),
)

after=sha_file(STATE)
report={
 'schema':'yado.live_shadow_meta_selection.developmental.v1',
 'status':'PASS_LIVE_SHADOW_META_SELECTION_DEVELOPMENTAL_V1' if live_pass and d.get('action')=='EXECUTE' and before==after else 'WITHHOLD_LIVE_SHADOW_META_SELECTION_DEVELOPMENTAL_V1',
 'github_run_id':os.getenv('GITHUB_RUN_ID'),'github_sha':os.getenv('GITHUB_SHA'),
 'selected_family':family,'validation':validation,
 'candidate_validations':[{ 'family':f,'validation':v,'complexity':complexity(p)} for f,p,v in cands],
 'current_context':current_ctx,
 'current_effective_priority':current_priority,'current_expected_priority':expected_priority,
 'live_blind_pass':live_pass,
 'g0_decision':d,'episode':objdict(ep),
 'canonical_parent_byte_identical':before==after,
 'canonical_mutation':False,'promotion_applied':False,
 'next_required_capability':'EVALUATE_SHADOW_CAPABILITY_FOR_G1_INHERITANCE_V1' if live_pass and d.get('action')=='EXECUTE' else 'REVISE_SHADOW_SELECTOR',
}
report['receipt_sha256']=hashlib.sha256(canon(report).encode()).hexdigest()
(ROOT/'yado_live_shadow_meta_selection_developmental_v1_receipt.json').write_text(json.dumps(report,indent=2,sort_keys=True,default=str)+'\n')
print(json.dumps({
 'status':report['status'],'selected_family':family,'validation':validation,
 'live_blind_pass':live_pass,'current_effective_priority':current_priority,
 'g0_decision':d,'canonical_parent_byte_identical':report['canonical_parent_byte_identical'],
 'next_required_capability':report['next_required_capability'],'receipt_sha256':report['receipt_sha256']
},indent=2,sort_keys=True,default=str))
k.close()
