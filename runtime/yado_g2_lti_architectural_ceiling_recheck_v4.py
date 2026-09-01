from __future__ import annotations
from pathlib import Path
from itertools import product
from fractions import Fraction
import hashlib,json,os,sys

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
PKG=ROOT/'yado_rc8_v36'
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(PKG))

from yado_evolution_ledger_v2 import validate_ledger_v2,event_hash
from yado_bounded_compositional_logic_v1 import BoundedCompositionalLogicV1
from yado_bounded_dnf_relation_policy_inducer_v1 import BoundedDNFRelationPolicyInducerV1,program_acc
from yado_bounded_adaptive_contingent_planner_v1 import BoundedAdaptiveContingentPlannerV1,ContingentStage
from yado_bounded_compositional_schema_router_v1 import BoundedCompositionalSchemaRouterV1
from yado_neutral_evidence_profile_selector_v1 import NeutralEvidenceProfileSelectorV1,EvidenceCandidate
from yado_g2_typed_recurrent_capability_graph_runtime_v1 import G2TypedRecurrentCapabilityGraphRuntimeV1

HEAD=REPO/'canonical'/'yado-main-head-g2.json'
CORE=REPO/'canonical'/'yado-unified-core-v1.json'
ARCH=REPO/'canonical'/'yado-g2-architecture-v1.json'
LEDGER=REPO/'architecture'/'evolution-ledger.json'
STATE=REPO/'architecture'/'yado-g2-lti-ceiling-state-v1.json'
PORT=REPO/'resources'/'yado-unified-external-resource-portfolio-v1.json'
OUT=ROOT/'yado_g2_lti_architectural_ceiling_recheck_v4_receipt.json'

CAP_CONJ='ALG-CONJUNCTIVE-RULE-INDUCER-V1'
CAP_REL='ALG-BOUNDED-DNF-RELATION-POLICY-INDUCER-V1'
CAP_BUD='ALG-BUDGETED-STAGE-POLICY-V1'
CAP_RES='RESOURCE-PORTFOLIO-V1'

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def h(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def fsha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def avg(xs):return sum(xs)/max(1,len(xs))

head=load(HEAD);core=load(CORE);arch=load(ARCH);ledger=load(LEDGER);state=load(STATE);portfolio=load(PORT)
validate_ledger_v2(ledger)
if ledger.get('open_deficits')!=['LTI_ARCHITECTURAL_CEILING_RECHECK_V4']:raise RuntimeError('UNEXPECTED_FRONTIER')
if ledger.get('current_head_digest')!=head.get('canonical_head_digest'):raise RuntimeError('HEAD_LEDGER_MISMATCH')
arch_sha=fsha(ARCH);head_sha=fsha(HEAD)
if state.get('fixed_architecture_sha256')!=arch_sha:raise RuntimeError('ARCHITECTURE_DRIFT')

active=set()
for p in core.get('planes',[]):active.update(p.get('active_components',[]))
required=[
 'ALG-G2-BOUNDED-COMPOSITIONAL-LOGIC-V1',
 'ALG-G2-BOUNDED-ADAPTIVE-CONTINGENT-PLANNER-V1',
 'ALG-G2-BOUNDED-COMPOSITIONAL-SCHEMA-ROUTER-V1',
]
if not all(x in active for x in required):raise RuntimeError('CANONICAL_LTI_COMPONENT_MISSING')

# ---------- LOGIC fresh V4 ----------
L=BoundedCompositionalLogicV1
def br(n,fn,p):
    return [{'input':{f'{p}{i}':v[i] for i in range(n)},'expected':'YES' if fn(v) else 'NO'} for v in product([False,True],repeat=n)]
lf={}
for name,rows in [
 ('PARITY12',br(12,lambda v:sum(v)%2==1,'p')),
 ('EXACT6OF12',br(12,lambda v:sum(v)==6,'e')),
]:
    m=L.learn_symmetric_boolean(rows)
    lf[name]=sum(L.predict_symmetric_boolean(m,z['input'])==z['expected'] for z in rows)/len(rows)
pts=[(x,y) for x in range(-5,6) for y in range(-5,6)]
poly=[{'x':x,'y':y,'expected':-2*x**3+3*x*y*y+y**3-4*x+7} for x,y in pts]
pm=L.fit_polynomial(poly,max_degree=3)
lf['CUBIC_TRANSFER_V4']=sum(L.predict_polynomial(pm,z['x'],z['y'])==Fraction(z['expected']) for z in poly)/len(poly)
quartic=[{'x':x,'y':y,'expected':x**4+2*y} for x,y in pts]
qm=L.fit_polynomial(quartic,max_degree=3)
lf['OUT_OF_SCOPE_QUARTIC_WITHHOLD']=1.0 if qm.get('kind')=='WITHHOLD' else 0.0
ns=br(6,lambda v:(v[0] and v[1]) or (v[2] and not v[3]) or (v[4] and v[5]),'n')
dp=BoundedDNFRelationPolicyInducerV1.synthesize('V4_NONSYM','LOGIC',ns,min_support=1,max_clauses=12,validation_cases=ns)
lf['NONSYMMETRIC_REGRESSION']=program_acc(dp,ns)
logic_score=avg(list(lf.values()))

# ---------- THINKING fresh V4 ----------
P=BoundedAdaptiveContingentPlannerV1;S=ContingentStage
tf={}
ok=0;n=120
for i in range(n):
    stages=[S(f'H{i}_{j}',1,.08,1,True,.1,False,()) for j in range(8)]
    p=P.plan(.18,.82,8,stages)
    ok+=p.feasible and p.expected_confidence>=.82-1e-9 and len(p.sequence)>=8
tf['FULL_HORIZON8']=ok/n
ok=0
for i in range(n):
    ids=[f'D{i}_{j}' for j in range(8)]
    stages=[S(ids[0],1,.05,1,True,.1,False,())]+[S(ids[j],1,.12,1,False,.1,False,(ids[j-1],)) for j in range(1,8)]
    p=P.next_after_observation(.12,.98,8,stages,ids[0],.05)
    ok+=p.action==ids[1] and p.expected_confidence>=.98-1e-9 and len(p.sequence)>=7
tf['DEPENDENCY_CHAIN7']=ok/n
ok=0
for i in range(n):
    a=f'A{i}';b=f'B{i}';c=f'C{i}'
    ss=[S(a,1,.1,1,True,.1,False,()),S(b,1,.3,1,True,.1,False,()),S(c,1,.3,1,True,.1,False,())]
    obs=(-.18,-.32)[i%2]
    p=P.next_after_observation(.72,.86,3,ss,a,obs)
    base=max(0,.72+obs);gain=sum(next(s.expected_gain for s in ss if s.stage_id==sid) for sid in p.sequence)
    ok+=abs(p.expected_confidence-min(1,base+gain))<1e-9
tf['SIGNED_EVIDENCE_V4']=ok/n
thinking_score=avg(list(tf.values()))

# ---------- INTELLIGENCE fresh V4 ----------
R=BoundedCompositionalSchemaRouterV1
def expected(x):
    s=set()
    if x['budget_limited'] or x['quota_limited']:s.add(CAP_BUD)
    if x['external_evidence_needed']:s.add(CAP_RES)
    if x['relation_needed'] or x['disjunction_needed']:s.add(CAP_REL)
    if not s:s.add(CAP_CONJ)
    return tuple(sorted(s))
train=[];test=[]
for mask in range(32):
    x={'budget_limited':bool(mask&1),'quota_limited':bool(mask&2),'external_evidence_needed':bool(mask&4),'relation_needed':bool(mask&8),'disjunction_needed':bool(mask&16)}
    for _ in range(6):train.append({'input':dict(x),'expected':expected(x)})
    test.append({'input':dict(x),'expected':expected(x)})
rm=R.fit(train,CAP_CONJ)
inf={}
inf['CAPABILITY_SET_EXACT']=sum(R.route(rm,z['input'])==z['expected'] for z in test)/len(test)

aliases={'budget_limited':'A17','quota_limited':'B29','external_evidence_needed':'C43','relation_needed':'D59','disjunction_needed':'E71'}
fields=list(aliases);refs=[];als=[]
for i in range(32):
    ref={f:bool((i>>j)&1) for j,f in enumerate(fields)}
    ali={aliases[f]:ref[f] for f in reversed(fields)}
    refs.append(ref);als.append(ali)
al=R.fit_schema_alignment(refs,als)
ali_test=[{'input':{aliases[k]:v for k,v in reversed(list(z['input'].items()))},'expected':z['expected']} for z in test]
inf['OPAQUE_SCHEMA_TRANSFER_V4']=sum(R.route_aligned(rm,al,z['input'])==z['expected'] for z in ali_test)/len(ali_test)

amb_ref=[{'a':bool(i%2),'b':bool(i%2),'c':bool((i//2)%2)} for i in range(20)]
amb_alias=[{'u':z['a'],'v':z['b'],'w':z['c']} for z in amb_ref]
inf['AMBIGUITY_WITHHOLD_V4']=1.0 if R.fit_schema_alignment(amb_ref,amb_alias).get('kind')=='WITHHOLD' else 0.0

# Evidence meta-selection remains regression.
sel_ok=0
for i in range(120):
    xs=[
      EvidenceCandidate(f'T{i}_{j}',evidence=(j+1)/10,complexity=(j%3)/10,risk=(j%2)/10,novelty=(j%4)/10)
      for j in range(5)
    ]
    got=NeutralEvidenceProfileSelectorV1.select(xs)
    scored=[(x.evidence-.05*x.complexity-.25*x.risk+.03*x.novelty,x.token) for x in xs]
    exp=sorted(scored,key=lambda z:(-z[0],z[1]))[0][1]
    sel_ok+=got['selected_token']==exp
inf['EVIDENCE_META_SELECTION_V4']=sel_ok/120

# Critical coevolution test: can the canonical typed runtime execute a capability SET?
multi_case=next(z for z in test if set(z['expected'])=={CAP_BUD,CAP_REL})
class SetRouter:
    fallback_output=CAP_CONJ
    def execute(self,x):return multi_case['expected']
class DummyScalar:
    def execute(self,x):return 'SCALAR'
class DummyRelation:
    def execute(self,x):return 'REL'
runtime=G2TypedRecurrentCapabilityGraphRuntimeV1(arch,SetRouter(),DummyScalar(),DummyRelation(),portfolio)
dispatch_ok=False
try:
    runtime.run({
      'kind':'multi','stream_id':'V4_MULTI','descriptor':multi_case['input'],'payload':{},
      'current_confidence':.3,'target_confidence':.7,'remaining_budget':3,
      'stages':[{'stage_id':'s1','cost':1,'expected_gain':.5,'quota_remaining':1,'available':True}],
    })
    dispatch_ok=True
except Exception:
    dispatch_ok=False
inf['CANONICAL_MULTI_CAPABILITY_RUNTIME_DISPATCH']=1.0 if dispatch_ok else 0.0

intelligence_score=avg(list(inf.values()))
planes={'LOGIC':{'score':logic_score,'families':lf},'THINKING':{'score':thinking_score,'families':tf},'INTELLIGENCE':{'score':intelligence_score,'families':inf}}
ranking=sorted(planes,key=lambda p:(planes[p]['score'],p));weakest=ranking[0]
threshold=float(state.get('ceiling_definition',{}).get('success_threshold_per_family',.985))
failed={p:[k for k,v in planes[p]['families'].items() if v<threshold] for p in planes}
all_at_target=all(not failed[p] for p in failed)
checks={
 'architecture_fixed':fsha(ARCH)==arch_sha,
 'canonical_head_immutable':fsha(HEAD)==head_sha and ledger.get('current_head_digest')==head.get('canonical_head_digest'),
 'all_three_ceiling_components_canonical':all(x in active for x in required),
 'all_three_planes_measured':set(planes)=={'LOGIC','THINKING','INTELLIGENCE'},
 'g3_not_started':head.get('g3_genesis_performed') is False,
}
passed=all(checks.values())
next_cap='LTI_ARCHITECTURAL_CEILING_PLATEAU_PROBE_V1' if all_at_target else f'{weakest}_ARCHITECTURAL_CEILING_SELF_EVOLUTION_V2'
state['round']=4;state['planes']=planes;state['ranking']=ranking;state['failed_families']=failed;state['self_selected_weakest_plane']=weakest
state['status']='ALL_FAMILIES_AT_THRESHOLD' if all_at_target else 'EVOLVING_TO_CEILING';state['next_required_capability']=next_cap
state['state_digest']=h({k:v for k,v in state.items() if k!='state_digest'});STATE.write_text(json.dumps(state,indent=2,sort_keys=True)+'\n')

run_id=str(os.getenv('GITHUB_RUN_ID') or 'LOCAL')
receipt={'schema':'yado.g2.lti_architectural_ceiling_recheck.v4','status':'PASS_LTI_ARCHITECTURAL_CEILING_RECHECK_V4' if passed else 'WITHHOLD_LTI_ARCHITECTURAL_CEILING_RECHECK_V4',
 'planes':planes,'ranking':ranking,'failed_families':failed,'self_selected_weakest_plane':weakest,'all_families_at_threshold':all_at_target,'threshold':threshold,'checks':checks,
 'architecture_sha256':arch_sha,'canonical_mutation':False,'promotion_applied':False,'g3_genesis_performed':False,'next_required_capability':next_cap,
 'semantic_boundary':'COEVOLUTION RECHECK OF CANONICAL LOGIC/THINKING/INTELLIGENCE. INCLUDES WHETHER MULTI-CAPABILITY INTELLIGENCE OUTPUT IS EXECUTABLE BY THE EXISTING TYPED RUNTIME.'
}
receipt['receipt_sha256']=h(receipt);OUT.write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')
e={'index':len(ledger['events']),'event_id':f"E{len(ledger['events'])+1:04d}_G2_LTI_CEILING_RECHECK_V4",
 'event_type':'FIXED_ARCHITECTURE_COEVOLUTION_CEILING_RECHECK','status':'PASS_SHADOW' if passed else 'WITHHOLD','generation':ledger['current_head'],'deficit':'LTI_ARCHITECTURAL_CEILING_RECHECK_V4',
 'effect':f"WEAKEST={weakest}; LOGIC={logic_score:.6f}; THINKING={thinking_score:.6f}; INTELLIGENCE={intelligence_score:.6f}; NEXT={next_cap}",
 'source_path':f'receipts/yado-g2-lti-architectural-ceiling-recheck-v4-run-{run_id}.json','source_digest':receipt['receipt_sha256'],'run_id':run_id,'parent_event_hash':ledger['tail_event_hash'],
 'canonical_mutation':False,'promotion_applied':False}
e['event_hash']=event_hash(e);ledger['events'].append(e);ledger['event_count']=len(ledger['events']);ledger['tail_event_hash']=e['event_hash'];ledger['open_deficits']=[next_cap]
ledger['ledger_digest']=h({k:v for k,v in ledger.items() if k!='ledger_digest'});validate_ledger_v2(ledger);LEDGER.write_text(json.dumps(ledger,indent=2,sort_keys=True)+'\n')
print(json.dumps({'status':receipt['status'],'planes':planes,'ranking':ranking,'failed_families':failed,'self_selected_weakest_plane':weakest,'next_required_capability':next_cap,'receipt_sha256':receipt['receipt_sha256']},indent=2,sort_keys=True))
if not passed:raise SystemExit('LTI_CEILING_RECHECK_V4_WITHHELD')
