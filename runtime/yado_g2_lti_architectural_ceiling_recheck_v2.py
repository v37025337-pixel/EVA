from __future__ import annotations
from pathlib import Path
from itertools import product
import hashlib,json,os,random,sys

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
PKG=ROOT/'yado_rc8_v36'
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(PKG))

from yado_evolution_ledger_v2 import validate_ledger_v2,event_hash
from yado_bounded_dnf_relation_policy_inducer_v1 import BoundedDNFRelationPolicyInducerV1,program_acc
from yado_bounded_capability_router_v1 import BoundedCapabilityRouterLearnerV1
from yado_neutral_evidence_profile_selector_v1 import NeutralEvidenceProfileSelectorV1,EvidenceCandidate
from yado_semantic_expression_synthesizer_v1 import SemanticExpressionSynthesizerV1
from yado_bounded_adaptive_contingent_planner_v1 import BoundedAdaptiveContingentPlannerV1,ContingentStage

HEAD=REPO/'canonical'/'yado-main-head-g2.json'
ARCH=REPO/'canonical'/'yado-g2-architecture-v1.json'
LEDGER=REPO/'architecture'/'evolution-ledger.json'
STATE=REPO/'architecture'/'yado-g2-lti-ceiling-state-v1.json'
OUT=ROOT/'yado_g2_lti_architectural_ceiling_recheck_v2_receipt.json'

CAP_CONJ='ALG-CONJUNCTIVE-RULE-INDUCER-V1'
CAP_REL='ALG-BOUNDED-DNF-RELATION-POLICY-INDUCER-V1'
CAP_BUD='ALG-BUDGETED-STAGE-POLICY-V1'
CAP_RES='RESOURCE-PORTFOLIO-V1'

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def h(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def fsha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def avg(xs):return sum(xs)/max(1,len(xs))

head=load(HEAD);arch=load(ARCH);ledger=load(LEDGER);state=load(STATE)
validate_ledger_v2(ledger)
if ledger.get('open_deficits')!=['LTI_ARCHITECTURAL_CEILING_RECHECK_V2']:raise RuntimeError('UNEXPECTED_FRONTIER')
if ledger.get('current_head_digest')!=head.get('canonical_head_digest'):raise RuntimeError('HEAD_LEDGER_MISMATCH')
if state.get('fixed_architecture_sha256')!=fsha(ARCH):raise RuntimeError('ARCHITECTURE_DRIFT')
arch_sha=fsha(ARCH);head_sha=fsha(HEAD)

# ---------- LOGIC fresh V2 ----------
def bool_rows(n,target):
    out=[]
    for vals in product([False,True],repeat=n):
        out.append({'input':{f'q{i}':vals[i] for i in range(n)},'expected':'YES' if target(vals) else 'NO'})
    return out

parity5=bool_rows(5,lambda v:sum(v)%2==1)
card7=bool_rows(7,lambda v:sum(v)>=4)
p_parity=BoundedDNFRelationPolicyInducerV1.synthesize('CEIL_V2_PARITY5','LOGIC',parity5,min_support=1,max_clauses=12,validation_cases=parity5)
p_card=BoundedDNFRelationPolicyInducerV1.synthesize('CEIL_V2_CARD7','LOGIC',card7,min_support=1,max_clauses=12,validation_cases=card7)
parity_score=program_acc(p_parity,parity5)
cardinality_score=program_acc(p_card,card7)

def rel_rows(seed,n,prefix):
    rr=random.Random(seed);pool=[f'{prefix}{i}' for i in range(40)];rows=[]
    for _ in range(n):
        a=rr.choice(pool);b=rr.choice(pool);g=rr.choice(pool);og=rr.choice(pool)
        if rr.random()<.36:b=a
        if rr.random()<.36:og=g
        x={'subject':a,'owner':b,'team':g,'object_team':og,'verified':bool(rr.getrandbits(1)),'critical':bool(rr.getrandbits(1))}
        y='YES' if ((a==b and x['verified']) or (g==og and x['critical'])) else 'NO'
        rows.append({'input':x,'expected':y})
    return rows
rel_train=rel_rows(71201,1100,'LT');rel_test=rel_rows(71202,550,'LV')
p_rel=BoundedDNFRelationPolicyInducerV1.synthesize('CEIL_V2_REL','LOGIC',rel_train,min_support=4,max_clauses=12,validation_cases=rel_test)
relation_score=program_acc(p_rel,rel_test)

def expr_fn(x,y):return x*x + y*y + x*y + x + 3
pts=[(a,b) for a in range(-4,5) for b in range(-4,5)]
expr_rows=[{'x':x,'y':y,'expected':expr_fn(x,y)} for x,y in pts]
expr=SemanticExpressionSynthesizerV1.synthesize(expr_rows,max_ops=3,max_states_per_level=30000)
expr_score=1.0 if expr.get('expression') is not None and all(SemanticExpressionSynthesizerV1.predict(expr,z['x'],z['y'])==z['expected'] for z in expr_rows) else 0.0
logic_families={'PARITY5':parity_score,'CARDINALITY_4_OF_7':cardinality_score,'RELATIONAL_TRANSFER_V2':relation_score,'DEEP_COMPOSITION_EXPRESSION':expr_score}
logic_score=avg(list(logic_families.values()))

# ---------- THINKING fresh V2 using canonical adaptive planner ----------
P=BoundedAdaptiveContingentPlannerV1;S=ContingentStage
think={}

ok=0;n=100
for i in range(n):
    stages=[S(f'A{i}_{j}',1+.1*(j%2),.09+.01*(j%3),1,True,.1,False,()) for j in range(7)]
    p=P.plan(.22,.76,8.0,stages)
    ok+=p.feasible and p.expected_confidence>=.76-1e-9
think['LONG_HORIZON_7']=ok/n

ok=0;n=100
for i in range(n):
    a=f'N{i}A';b=f'N{i}B';c=f'N{i}C'
    stages=[S(a,1,.15,1,True,.1,False,()),S(b,1,.22,1,True,.1,False,()),S(c,1,.28,1,True,.1,False,())]
    obs=(-.12,-.23,-.31)[i%3]
    p=P.next_after_observation(.64,.84,3.0,stages,a,obs)
    base=max(0.0,.64+obs)
    gain=sum(next(s.expected_gain for s in stages if s.stage_id==sid) for sid in p.sequence)
    ok+=abs(p.expected_confidence-min(1.0,base+gain))<1e-9
think['SIGNED_NEGATIVE_V2']=ok/n

ok=0;n=100
for i in range(n):
    ids=[f'D{i}_{j}' for j in range(6)]
    stages=[S(ids[0],1,.06,1,True,.1,False,())]
    for j in range(1,6):stages.append(S(ids[j],1,.16,1,False,.1,False,(ids[j-1],)))
    p=P.next_after_observation(.20,.98,7.0,stages,ids[0],.06)
    ok+=p.action==ids[1] and p.expected_confidence>=.98-1e-9
think['DEPENDENCY_CHAIN5']=ok/n

ok=0;n=100
for i in range(n):
    stages=[S(f'W{i}_{j}',2.5,.09,1,True,.1,False,()) for j in range(4)]
    p=P.plan(.15,.9,2.0,stages)
    ok+=p.action=='WITHHOLD' and not p.feasible
think['FAIL_CLOSED_BUDGET']=ok/n

thinking_score=avg(list(think.values()))

# ---------- INTELLIGENCE fresh V2 ----------
def route_label(x):
    if x['budget_limited'] or x['quota_limited']:return CAP_BUD
    if x['external_evidence_needed']:return CAP_RES
    if x['relation_needed'] or x['disjunction_needed']:return CAP_REL
    return CAP_CONJ
def route_rows(seed,n):
    rr=random.Random(seed);rows=[]
    for _ in range(n):
        x={'budget_limited':rr.random()<.24,'quota_limited':rr.random()<.08,'external_evidence_needed':rr.random()<.21,
           'relation_needed':rr.random()<.26,'disjunction_needed':rr.random()<.11,'noise':rr.randrange(10**9)}
        rows.append({'input':x,'expected':route_label(x)})
    return rows
router=BoundedCapabilityRouterLearnerV1.synthesize(route_rows(71301,1500),route_rows(71302,650),CAP_CONJ,min_support=7)
single=route_rows(71303,600)
single_score=sum(router.execute(z['input'])==z['expected'] for z in single)/len(single)

# exact composition requirement: two simultaneous independent needs require ordered pair/set, single-output router cannot satisfy.
multi=[]
for i in range(240):
    if i%2==0:
        x={'budget_limited':True,'quota_limited':False,'external_evidence_needed':True,'relation_needed':False,'disjunction_needed':False}
        exp={CAP_BUD,CAP_RES}
    else:
        x={'budget_limited':False,'quota_limited':False,'external_evidence_needed':True,'relation_needed':True,'disjunction_needed':False}
        exp={CAP_RES,CAP_REL}
    multi.append((x,exp))
comp_ok=0
for x,exp in multi:
    got=router.execute(x)
    comp_ok+=isinstance(got,(list,tuple,set)) and set(got)==exp
composition_score=comp_ok/len(multi)

selector_ok=0;selector_n=180
for i in range(selector_n):
    rr=random.Random(71400+i);cands=[];scores=[]
    for j in range(6):
        ev=rr.random();cx=rr.random();risk=rr.random();nov=rr.random();tok=f'V2_{i}_{j}'
        cands.append(EvidenceCandidate(tok,ev,cx,risk,nov));scores.append((ev-.05*cx-.25*risk+.03*nov,tok))
    got=NeutralEvidenceProfileSelectorV1.select(cands)['selected_token']
    exp=sorted(scores,key=lambda z:(-z[0],z[1]))[0][1]
    selector_ok+=got==exp
selector_score=selector_ok/selector_n

# Fresh alias schema without calibration.
alias_ok=0;alias_n=240
for i in range(alias_n):
    z=single[i%len(single)];x=z['input']
    alias={'s0':x['budget_limited'],'s1':x['quota_limited'],'s2':x['external_evidence_needed'],'s3':x['relation_needed'],'s4':x['disjunction_needed'],'junk':x['noise']}
    try:got=router.execute(alias)
    except Exception:got=None
    alias_ok+=got==z['expected']
alias_score=alias_ok/alias_n

intelligence_families={'SINGLE_ROUTING_V2':single_score,'MULTI_CAPABILITY_COMPOSITION_V2':composition_score,'EVIDENCE_META_SELECTION_V2':selector_score,'ZERO_SHOT_SCHEMA_ALIAS_V2':alias_score}
intelligence_score=avg(list(intelligence_families.values()))

planes={
 'LOGIC':{'score':logic_score,'families':logic_families},
 'THINKING':{'score':thinking_score,'families':think},
 'INTELLIGENCE':{'score':intelligence_score,'families':intelligence_families},
}
ranking=sorted(planes,key=lambda p:(planes[p]['score'],p))
weakest=ranking[0]
threshold=float(state.get('ceiling_definition',{}).get('success_threshold_per_family',.985))
failed={p:[k for k,v in planes[p]['families'].items() if v<threshold] for p in planes}

checks={
 'architecture_fixed':fsha(ARCH)==arch_sha,
 'canonical_head_immutable':fsha(HEAD)==head_sha and ledger.get('current_head_digest')==head.get('canonical_head_digest'),
 'thinking_canonical_component_present':state.get('planes',{}).get('THINKING',{}).get('canonical_component')=='ALG-G2-BOUNDED-ADAPTIVE-CONTINGENT-PLANNER-V1',
 'all_three_planes_measured':set(planes)=={'LOGIC','THINKING','INTELLIGENCE'},
 'g3_not_started':head.get('g3_genesis_performed') is False,
}
passed=all(checks.values())
all_at_target=all(not failed[p] for p in failed)
if all_at_target:
    next_cap='LTI_ARCHITECTURAL_CEILING_PLATEAU_PROBE_V1'
else:
    next_cap=f'{weakest}_ARCHITECTURAL_CEILING_SELF_EVOLUTION_V1'

state['round']=2
state['planes']=planes
state['ranking']=ranking
state['failed_families']=failed
state['self_selected_weakest_plane']=weakest
state['status']='ALL_FAMILIES_AT_THRESHOLD' if all_at_target else 'EVOLVING_TO_CEILING'
state['next_required_capability']=next_cap
state['state_digest']=h({k:v for k,v in state.items() if k!='state_digest'})
STATE.write_text(json.dumps(state,indent=2,sort_keys=True)+'\n')

run_id=str(os.getenv('GITHUB_RUN_ID') or 'LOCAL')
receipt={'schema':'yado.g2.lti_architectural_ceiling_recheck.v2',
 'status':'PASS_LTI_ARCHITECTURAL_CEILING_RECHECK_V2' if passed else 'WITHHOLD_LTI_ARCHITECTURAL_CEILING_RECHECK_V2',
 'planes':planes,'ranking':ranking,'failed_families':failed,'self_selected_weakest_plane':weakest,
 'all_families_at_threshold':all_at_target,'threshold':threshold,'checks':checks,
 'architecture_sha256':arch_sha,'canonical_mutation':False,'promotion_applied':False,'g3_genesis_performed':False,
 'next_required_capability':next_cap,
 'semantic_boundary':'FRESH THREE-PLANE RECHECK AFTER THINKING IMPROVEMENT. SELF-SELECTS THE NEXT WEAKEST PLANE UNDER THE SAME FIXED G2 GRAPH.'
}
receipt['receipt_sha256']=h(receipt);OUT.write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')

e={'index':len(ledger['events']),'event_id':f"E{len(ledger['events'])+1:04d}_G2_LTI_CEILING_RECHECK_V2",
 'event_type':'FIXED_ARCHITECTURE_CAPABILITY_CEILING_RECHECK','status':'PASS_SHADOW' if passed else 'WITHHOLD',
 'generation':ledger['current_head'],'deficit':'LTI_ARCHITECTURAL_CEILING_RECHECK_V2',
 'effect':f"WEAKEST={weakest}; LOGIC={logic_score:.6f}; THINKING={thinking_score:.6f}; INTELLIGENCE={intelligence_score:.6f}; NEXT={next_cap}",
 'source_path':f'receipts/yado-g2-lti-architectural-ceiling-recheck-v2-run-{run_id}.json',
 'source_digest':receipt['receipt_sha256'],'run_id':run_id,'parent_event_hash':ledger['tail_event_hash'],
 'canonical_mutation':False,'promotion_applied':False}
e['event_hash']=event_hash(e);ledger['events'].append(e);ledger['event_count']=len(ledger['events']);ledger['tail_event_hash']=e['event_hash']
ledger['open_deficits']=[next_cap];ledger['ledger_digest']=h({k:v for k,v in ledger.items() if k!='ledger_digest'})
validate_ledger_v2(ledger);LEDGER.write_text(json.dumps(ledger,indent=2,sort_keys=True)+'\n')
print(json.dumps({'status':receipt['status'],'planes':planes,'ranking':ranking,'failed_families':failed,'self_selected_weakest_plane':weakest,'next_required_capability':next_cap,'receipt_sha256':receipt['receipt_sha256']},indent=2,sort_keys=True))
if not passed:raise SystemExit('LTI_CEILING_RECHECK_V2_WITHHELD')
