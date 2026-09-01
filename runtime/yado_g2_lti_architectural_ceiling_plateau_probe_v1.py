from __future__ import annotations
from pathlib import Path
from itertools import product
from fractions import Fraction
import hashlib,json,os,sys

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
sys.path.insert(0,str(ROOT))

from yado_evolution_ledger_v2 import validate_ledger_v2,event_hash
from yado_neutral_evidence_profile_selector_v1 import NeutralEvidenceProfileSelectorV1,EvidenceCandidate
from yado_bounded_compositional_logic_v1 import BoundedCompositionalLogicV1
from yado_bounded_adaptive_contingent_planner_v1 import BoundedAdaptiveContingentPlannerV1,ContingentStage
from yado_bounded_compositional_schema_router_v1 import BoundedCompositionalSchemaRouterV1

HEAD=REPO/'canonical'/'yado-main-head-g2.json'
ARCH=REPO/'canonical'/'yado-g2-architecture-v1.json'
LEDGER=REPO/'architecture'/'evolution-ledger.json'
STATE=REPO/'architecture'/'yado-g2-lti-ceiling-state-v1.json'
OUT=ROOT/'yado_g2_lti_architectural_ceiling_plateau_probe_v1_receipt.json'

CAP_CONJ='ALG-CONJUNCTIVE-RULE-INDUCER-V1'
CAP_REL='ALG-BOUNDED-DNF-RELATION-POLICY-INDUCER-V1'

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def h(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def fsha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def avg(xs):return sum(xs)/max(1,len(xs))

head=load(HEAD);ledger=load(LEDGER);state=load(STATE)
validate_ledger_v2(ledger)
if ledger.get('open_deficits')!=['LTI_ARCHITECTURAL_CEILING_PLATEAU_PROBE_V1']:raise RuntimeError('UNEXPECTED_FRONTIER')
if ledger.get('current_head_digest')!=head.get('canonical_head_digest'):raise RuntimeError('HEAD_LEDGER_MISMATCH')
arch_sha=fsha(ARCH);head_sha=fsha(HEAD)
if state.get('status')!='ALL_FAMILIES_AT_THRESHOLD':raise RuntimeError('PLATEAU_PROBE_REQUIRES_GREEN_BASELINE')

probes={}
contract_snapshot={
 'LOGIC':{
   'MAX_BOOLEAN_FIELDS':BoundedCompositionalLogicV1.MAX_BOOLEAN_FIELDS,
   'MAX_POLYNOMIAL_DEGREE':BoundedCompositionalLogicV1.MAX_POLYNOMIAL_DEGREE,
   'MAX_POLYNOMIAL_TERMS':BoundedCompositionalLogicV1.MAX_POLYNOMIAL_TERMS,
 },
 'THINKING':{
   'MAX_STAGES':BoundedAdaptiveContingentPlannerV1.MAX_STAGES,
   'MAX_PLAN_DEPTH':BoundedAdaptiveContingentPlannerV1.MAX_PLAN_DEPTH,
 },
 'INTELLIGENCE':{
   'MAX_FIELDS':BoundedCompositionalSchemaRouterV1.MAX_FIELDS,
   'MAX_OUTPUTS':BoundedCompositionalSchemaRouterV1.MAX_OUTPUTS,
   'MAX_TRIGGERS_PER_OUTPUT':BoundedCompositionalSchemaRouterV1.MAX_TRIGGERS_PER_OUTPUT,
 }
}

# ---------------- LOGIC: probes generated from its declared bounds ----------------
L=BoundedCompositionalLogicV1
n=L.MAX_BOOLEAN_FIELDS+1
rows=[{'input':{f'b{i:02d}':v[i] for i in range(n)},'expected':'YES' if sum(v)%2 else 'NO'} for v in product([False,True],repeat=n)]
try:
    m=L.learn_symmetric_boolean(rows)
    s=sum(L.predict_symmetric_boolean(m,z['input'])==z['expected'] for z in rows)/len(rows)
    reason='EXECUTED'
except Exception as exc:
    s=0.0;reason=type(exc).__name__
probes['LOGIC']={'BOOLEAN_WIDTH_PLUS_ONE':{'score':s,'bound':L.MAX_BOOLEAN_FIELDS,'probe_value':n,'reason':reason}}

d=L.MAX_POLYNOMIAL_DEGREE+1
pts=[(x,y) for x in range(-3,4) for y in range(-3,4)]
poly=[{'x':x,'y':y,'expected':x**d+y} for x,y in pts]
pm=L.fit_polynomial(poly,max_degree=d)
ps=0.0 if pm.get('kind')=='WITHHOLD' else sum(L.predict_polynomial(pm,z['x'],z['y'])==Fraction(z['expected']) for z in poly)/len(poly)
probes['LOGIC']['POLYNOMIAL_DEGREE_PLUS_ONE']={'score':ps,'bound':L.MAX_POLYNOMIAL_DEGREE,'probe_value':d,'reason':pm.get('kind')}

# ---------------- THINKING: generated from stage/depth contract ----------------
P=BoundedAdaptiveContingentPlannerV1;S=ContingentStage
stage_n=P.MAX_STAGES+1
stages=[S(f's{i}',1.0,0.1,1,True,.1,False,()) for i in range(stage_n)]
plan=P.plan(.1,1.0,float(stage_n),stages)
# A full success requires using the plus-one stage to reach target.
stage_score=1.0 if plan.expected_confidence>=1.0-1e-12 and len(plan.sequence)>=stage_n else min(1.0,plan.expected_confidence/1.0)
probes['THINKING']={'STAGE_WIDTH_PLUS_ONE':{'score':stage_score,'bound':P.MAX_STAGES,'probe_value':stage_n,'reason':plan.reason,'sequence_len':len(plan.sequence)}}

# Dependency chain with one more remaining decision than the declared plan depth.
remaining=P.MAX_PLAN_DEPTH+1
ids=[f'd{i}' for i in range(remaining+1)]
dep_stages=[S(ids[0],1,.05,1,True,.1,False,())]
for j in range(1,len(ids)):
    dep_stages.append(S(ids[j],1,.1,1,False,.1,False,(ids[j-1],)))
p2=P.next_after_observation(.05,1.0,float(len(ids)),dep_stages,ids[0],.05)
dep_score=1.0 if p2.expected_confidence>=1.0-1e-12 and len(p2.sequence)>=remaining else min(1.0,p2.expected_confidence/1.0)
probes['THINKING']['DEPENDENCY_DEPTH_PLUS_ONE']={'score':dep_score,'bound':P.MAX_PLAN_DEPTH,'probe_value':remaining,'reason':p2.reason,'sequence_len':len(p2.sequence)}

# ---------------- INTELLIGENCE: fields and interaction-order frontier ----------------
R=BoundedCompositionalSchemaRouterV1
field_n=R.MAX_FIELDS+1
fname=[f'f{i:02d}' for i in range(field_n-1)]+['zz_relevant']
train=[];test=[]
for i in range(256):
    x={f:bool((i>>(j%8))&1) for j,f in enumerate(fname)}
    # Deliberately vary the relevant field independently from the first 16 signatures.
    x['zz_relevant']=bool((i//2)%2)
    y=(CAP_REL,) if x['zz_relevant'] else (CAP_CONJ,)
    train.append({'input':x,'expected':y})
for i in range(128):
    x={f:bool(((i+37)>>(j%7))&1) for j,f in enumerate(fname)}
    x['zz_relevant']=bool((i//3)%2)
    y=(CAP_REL,) if x['zz_relevant'] else (CAP_CONJ,)
    test.append({'input':x,'expected':y})
rm=R.fit(train,CAP_CONJ)
field_score=sum(R.route(rm,z['input'])==z['expected'] for z in test)/len(test)
probes['INTELLIGENCE']={'FIELD_WIDTH_PLUS_ONE':{'score':field_score,'bound':R.MAX_FIELDS,'probe_value':field_n,'reason':'RELEVANT_FIELD_SORTS_AFTER_CURRENT_FIELD_BOUND'}}

# Interaction-order +1: current compositional router uses single-field triggers.
ix=[]
for a,b,c,d in product([False,True],repeat=4):
    out=set()
    if a and b:out.add(CAP_REL)
    if c and d:out.add('RESOURCE-PORTFOLIO-V1')
    if not out:out.add(CAP_CONJ)
    for _ in range(8):ix.append({'input':{'a':a,'b':b,'c':c,'d':d},'expected':tuple(sorted(out))})
irm=R.fit(ix,CAP_CONJ)
interaction_score=sum(R.route(irm,z['input'])==z['expected'] for z in ix)/len(ix)
probes['INTELLIGENCE']['TRIGGER_INTERACTION_ORDER_PLUS_ONE']={'score':interaction_score,'current_order':1,'probe_order':2,'reason':'PAIRWISE_CAPABILITY_TRIGGER'}

plane_scores={p:avg([v['score'] for v in fam.values()]) for p,fam in probes.items()}
deficit_severity={p:1.0-s for p,s in plane_scores.items()}

# Neutral selector sees opaque tokens; plane names are mapped only after selection.
tokens={}
candidates=[]
meta={
 'LOGIC':(.28,.05,.76),
 'THINKING':(.34,.06,.84),
 'INTELLIGENCE':(.31,.05,.88),
}
for i,p in enumerate(sorted(plane_scores)):
    tok='opaque_'+h({'plateau_probe':1,'slot':i,'head':head['canonical_head_digest']})[:18]
    tokens[tok]=p
    complexity,risk,novelty=meta[p]
    candidates.append(EvidenceCandidate(tok,deficit_severity[p],complexity,risk,novelty))
selection=NeutralEvidenceProfileSelectorV1.select(candidates)
selected_plane=tokens[selection['selected_token']]
selected_score=plane_scores[selected_plane]
threshold=float(state.get('ceiling_definition',{}).get('success_threshold_per_family',.985))
new_deficit=selected_score<threshold

if new_deficit:
    plateau_streak=0
    next_cap=f'{selected_plane}_PLATEAU_SELF_EVOLUTION_V1'
    status='FRONTIER_FOUND'
else:
    plateau_streak=int(state.get('plateau_streak',0))+1
    req=int(state.get('ceiling_definition',{}).get('plateau_required_consecutive_rounds',3))
    next_cap='LTI_ARCHITECTURAL_CEILING_PLATEAU_PROBE_V2' if plateau_streak<req else 'LTI_ARCHITECTURAL_CEILING_EMPIRICAL_PLATEAU_CONFIRMATION_V1'
    status='PLATEAU_ROUND'

checks={
 'baseline_all_green':all(not xs for xs in state.get('failed_families',{}).values()),
 'contract_snapshot_nonempty':all(contract_snapshot[p] for p in contract_snapshot),
 'three_planes_probed':set(probes)=={'LOGIC','THINKING','INTELLIGENCE'},
 'architecture_immutable':fsha(ARCH)==arch_sha,
 'canonical_head_immutable':fsha(HEAD)==head_sha and ledger.get('current_head_digest')==head.get('canonical_head_digest'),
 'g3_not_started':head.get('g3_genesis_performed') is False,
}
passed=all(checks.values())

state['round']=int(state.get('round',0))+1
state['plateau_streak']=plateau_streak
state['plateau_probe']={
 'probe_version':1,'contract_snapshot':contract_snapshot,'probes':probes,'plane_scores':plane_scores,
 'deficit_severity':deficit_severity,'neutral_selection':selection,'selected_plane':selected_plane,
 'status':status,'architecture_sha256':arch_sha
}
state['self_selected_weakest_plane']=selected_plane
state['status']='EVOLVING_TO_CEILING' if new_deficit else 'PLATEAU_SEARCH'
state['next_required_capability']=next_cap
state['state_digest']=h({k:v for k,v in state.items() if k!='state_digest'})
STATE.write_text(json.dumps(state,indent=2,sort_keys=True)+'\n')

run_id=str(os.getenv('GITHUB_RUN_ID') or 'LOCAL')
receipt={
 'schema':'yado.g2.lti_architectural_ceiling_plateau_probe.v1',
 'status':'PASS_LTI_ARCHITECTURAL_CEILING_PLATEAU_PROBE_V1' if passed else 'WITHHOLD_LTI_ARCHITECTURAL_CEILING_PLATEAU_PROBE_V1',
 'probe_status':status,'contract_snapshot':contract_snapshot,'probes':probes,'plane_scores':plane_scores,
 'deficit_severity':deficit_severity,'neutral_selection':selection,'self_selected_plane':selected_plane,
 'new_deficit_found':new_deficit,'plateau_streak':plateau_streak,'checks':checks,
 'architecture_sha256':arch_sha,'canonical_mutation':False,'promotion_applied':False,'g3_genesis_performed':False,
 'next_required_capability':next_cap,
 'semantic_boundary':'CONTRACT-DERIVED FRONTIER SEARCH. PROBES ARE GENERATED FROM ACTIVE MAX_* BOUNDS AND ONE-ORDER-BEYOND INTERACTION; NO LIMIT IS CHANGED BY THIS PROBE. A FOUND DEFICIT REOPENS SAME-G2 SELF-EVOLUTION, NOT G3.'
}
receipt['receipt_sha256']=h(receipt)
OUT.write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')

e={'index':len(ledger['events']),'event_id':f"E{len(ledger['events'])+1:04d}_G2_LTI_PLATEAU_PROBE_V1",
 'event_type':'FIXED_ARCHITECTURE_CONTRACT_DERIVED_PLATEAU_PROBE','status':'PASS_SHADOW' if passed else 'WITHHOLD',
 'generation':ledger['current_head'],'deficit':'LTI_ARCHITECTURAL_CEILING_PLATEAU_PROBE_V1',
 'effect':f"PROBE={status}; SELECTED={selected_plane}; SCORE={selected_score:.6f}; STREAK={plateau_streak}; NEXT={next_cap}",
 'source_path':f'receipts/yado-g2-lti-architectural-ceiling-plateau-probe-v1-run-{run_id}.json','source_digest':receipt['receipt_sha256'],
 'run_id':run_id,'parent_event_hash':ledger['tail_event_hash'],'canonical_mutation':False,'promotion_applied':False}
e['event_hash']=event_hash(e);ledger['events'].append(e);ledger['event_count']=len(ledger['events']);ledger['tail_event_hash']=e['event_hash']
ledger['open_deficits']=[next_cap];ledger['ledger_digest']=h({k:v for k,v in ledger.items() if k!='ledger_digest'})
validate_ledger_v2(ledger);LEDGER.write_text(json.dumps(ledger,indent=2,sort_keys=True)+'\n')
print(json.dumps({'status':receipt['status'],'probe_status':status,'plane_scores':plane_scores,'probes':probes,'self_selected_plane':selected_plane,'new_deficit_found':new_deficit,'plateau_streak':plateau_streak,'next_required_capability':next_cap,'receipt_sha256':receipt['receipt_sha256']},indent=2,sort_keys=True))
if not passed:raise SystemExit('PLATEAU_PROBE_V1_WITHHELD')
