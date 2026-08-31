from __future__ import annotations
from pathlib import Path
from itertools import product
import copy,hashlib,json,math,os,random,sys

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
PKG=ROOT/'yado_rc8_v36'
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(PKG))

from yado_evolution_ledger_v2 import validate_ledger_v2,event_hash
from yado_bounded_dnf_relation_policy_inducer_v1 import BoundedDNFRelationPolicyInducerV1,program_acc
from yado_budgeted_stage_policy_v1 import BudgetedStagePolicyV1,SearchStage
from yado_bounded_capability_router_v1 import BoundedCapabilityRouterLearnerV1
from yado_neutral_evidence_profile_selector_v1 import NeutralEvidenceProfileSelectorV1,EvidenceCandidate
from yado_g2_contextual_stream_capability_adapter_v1 import ContextualStreamCapabilityAdapterV1
from yado_g2_typed_recurrent_capability_graph_runtime_v1 import G2TypedRecurrentCapabilityGraphRuntimeV1
from yado_conjunctive_rule_inducer_v1 import ConjunctiveRuleInducerV1
from yado_semantic_expression_synthesizer_v1 import SemanticExpressionSynthesizerV1

HEAD=REPO/'canonical'/'yado-main-head-g2.json'
ARCH=REPO/'canonical'/'yado-g2-architecture-v1.json'
LEDGER=REPO/'architecture'/'evolution-ledger.json'
PORT=REPO/'resources'/'yado-unified-external-resource-portfolio-v1.json'
OUT=ROOT/'yado_g2_lti_architectural_ceiling_diagnostic_v1_receipt.json'
STATE=REPO/'architecture'/'yado-g2-lti-ceiling-state-v1.json'

CAP_CONJ='ALG-CONJUNCTIVE-RULE-INDUCER-V1'
CAP_REL='ALG-BOUNDED-DNF-RELATION-POLICY-INDUCER-V1'
CAP_BUD='ALG-BUDGETED-STAGE-POLICY-V1'
CAP_RES='RESOURCE-PORTFOLIO-V1'

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def h(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def fsha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def mean(xs):return sum(xs)/max(1,len(xs))

head=load(HEAD);arch=load(ARCH);ledger=load(LEDGER);portfolio=load(PORT)
validate_ledger_v2(ledger)
if ledger.get('open_deficits')!=['LOGIC_THINKING_INTELLIGENCE_ARCHITECTURAL_CEILING_V1']:raise RuntimeError('UNEXPECTED_FRONTIER')
if ledger.get('current_head_digest')!=head.get('canonical_head_digest'):raise RuntimeError('HEAD_LEDGER_MISMATCH')
arch_before=fsha(ARCH);head_before=fsha(HEAD)
seed=126831
r=random.Random(seed)

# ---------------- LOGIC: current expressivity under progressively harder exact functions ----------------
def bool_cases(n,target):
    rows=[]
    for vals in product([False,True],repeat=n):
        x={f'b{i}':vals[i] for i in range(n)}
        rows.append({'input':x,'expected':'YES' if target(vals) else 'NO'})
    return rows

parity4=bool_cases(4,lambda v:sum(v)%2==1)
card6=bool_cases(6,lambda v:sum(v)>=3)
p_parity=BoundedDNFRelationPolicyInducerV1.synthesize('CEILING_PARITY4','LOGIC',parity4,min_support=1,max_clauses=12,validation_cases=parity4)
p_card=BoundedDNFRelationPolicyInducerV1.synthesize('CEILING_CARD6','LOGIC',card6,min_support=1,max_clauses=12,validation_cases=card6)
parity_score=program_acc(p_parity,parity4)
cardinality_score=program_acc(p_card,card6)

# Relational transfer with fresh identifiers.
def rel_rows(seed,n,prefix):
    rr=random.Random(seed);pool=[f'{prefix}{i}' for i in range(30)];out=[]
    for _ in range(n):
        a=rr.choice(pool);b=rr.choice(pool);g=rr.choice(pool);h_=rr.choice(pool)
        if rr.random()<.38:b=a
        if rr.random()<.38:h_=g
        x={'actor':a,'owner':b,'group':g,'object_group':h_,'verified':bool(rr.getrandbits(1)),'critical':bool(rr.getrandbits(1))}
        y='YES' if ((a==b and x['verified']) or (g==h_ and x['critical'])) else 'NO'
        out.append({'input':x,'expected':y})
    return out
rel_train=rel_rows(seed+10,1000,'T')
rel_test=rel_rows(seed+11,500,'V')
p_rel=BoundedDNFRelationPolicyInducerV1.synthesize('CEILING_REL','LOGIC',rel_train,min_support=4,max_clauses=12,validation_cases=rel_test)
relation_score=program_acc(p_rel,rel_test)

# Expression depth beyond current canonical max_ops=3.
def expr_target(x,y):return x*x + y*y + x*y + 2
expr_train=[{'x':x,'y':y,'expected':expr_target(x,y)} for x,y in [(a,b) for a in range(-3,4) for b in range(-3,4)]]
expr_res=SemanticExpressionSynthesizerV1.synthesize(expr_train,max_ops=3,max_states_per_level=30000)
expr_score=1.0 if expr_res.get('expression') is not None and all(SemanticExpressionSynthesizerV1.predict(expr_res,z['x'],z['y'])==z['expected'] for z in expr_train) else 0.0
logic_families={'PARITY4':parity_score,'CARDINALITY_3_OF_6':cardinality_score,'RELATIONAL_TRANSFER':relation_score,'EXPRESSION_BEYOND_DEPTH3':expr_score}
logic_score=mean(list(logic_families.values()))

# ---------------- THINKING: planning limits inside current BudgetedStagePolicy ----------------
# Ordinary additive planning.
add_ok=0;add_n=120
for i in range(add_n):
    rr=random.Random(seed+1000+i)
    stages=[SearchStage(f'A{i}_{j}',1+j*.4,.10+j*.03,2,True,.2+j*.1,False) for j in range(4)]
    cur=.25+rr.random()*.10;target=.62;budget=8
    plan=BudgetedStagePolicyV1.plan(cur,target,budget,stages)
    add_ok+=plan.feasible and plan.total_cost<=budget+1e-9 and bool(plan.sequence)
additive_score=add_ok/add_n

# Horizon-5: all five small gains are required; MAX_PLAN_DEPTH=4 is the intended stress.
depth_ok=0;depth_n=80
for i in range(depth_n):
    stages=[SearchStage(f'D{i}_{j}',1.0,.10,1,True,.1,False) for j in range(5)]
    plan=BudgetedStagePolicyV1.plan(.20,.70,5.0,stages)
    depth_ok+=plan.expected_confidence>=.70-1e-9 and len(plan.sequence)>=5
depth5_score=depth_ok/depth_n

# Negative observation: current policy clamps negative evidence to zero.
neg_ok=0;neg_n=80
for i in range(neg_n):
    stages=[SearchStage(f'N{i}_A',1,.20,1,True,.1,False),SearchStage(f'N{i}_B',1,.20,1,True,.1,False)]
    nxt=BudgetedStagePolicyV1.next_after_observation(.55,.80,2.0,stages,f'N{i}_A',-.25)
    oracle_conf=max(0.0,.55-.25)
    # After spending A, only B remains, so oracle forecast is .50.
    oracle_after=min(1.0,oracle_conf+.20)
    neg_ok+=abs(nxt.expected_confidence-oracle_after)<1e-9
negative_evidence_score=neg_ok/neg_n

# Dependency unlock: B is unavailable before A, becomes available only because A succeeds.
dep_ok=0;dep_n=80
for i in range(dep_n):
    stages=[SearchStage(f'P{i}_A',1,.15,1,True,.1,False),SearchStage(f'P{i}_B',1,.35,1,False,.1,False)]
    nxt=BudgetedStagePolicyV1.next_after_observation(.35,.80,3.0,stages,f'P{i}_A',.15)
    # Correct contingent planner should be able to model B becoming available and choose it.
    dep_ok+=nxt.action==f'P{i}_B'
dependency_score=dep_ok/dep_n
thinking_families={'ADDITIVE_BUDGET_PLAN':additive_score,'HORIZON_5_REQUIRED':depth5_score,'NEGATIVE_EVIDENCE_UPDATE':negative_evidence_score,'DEPENDENCY_UNLOCK':dependency_score}
thinking_score=mean(list(thinking_families.values()))

# ---------------- INTELLIGENCE: routing/meta-selection/composition limits ----------------
def route_label(x):
    if x['budget_limited'] or x['quota_limited']:return CAP_BUD
    if x['external_evidence_needed']:return CAP_RES
    if x['relation_needed'] or x['disjunction_needed']:return CAP_REL
    return CAP_CONJ
def route_cases(seed,n):
    rr=random.Random(seed);out=[]
    for _ in range(n):
        x={'budget_limited':rr.random()<.25,'quota_limited':rr.random()<.07,'external_evidence_needed':rr.random()<.20,
           'relation_needed':rr.random()<.25,'disjunction_needed':rr.random()<.10,'noise':rr.randrange(10**9)}
        out.append({'input':x,'expected':route_label(x)})
    return out
router=BoundedCapabilityRouterLearnerV1.synthesize(route_cases(seed+200,1400),route_cases(seed+201,600),CAP_CONJ,min_support=7)
single_test=route_cases(seed+202,500)
single_route_score=sum(router.execute(x['input'])==x['expected'] for x in single_test)/len(single_test)

# Multi-capability tasks require composition, while current router emits exactly one capability.
multi=[]
for i in range(200):
    multi.append({'budget_limited':True,'quota_limited':False,'external_evidence_needed':False,'relation_needed':True,'disjunction_needed':False})
multi_comp_score=sum(isinstance(router.execute(x),(list,tuple,set)) and set(router.execute(x))=={CAP_BUD,CAP_REL} for x in multi)/len(multi)

# Evidence meta-selection exactness.
selector_ok=0;selector_n=150
for i in range(selector_n):
    rr=random.Random(seed+300+i)
    candidates=[]
    raw=[]
    for j in range(5):
        ev=rr.random();complexity=rr.random();risk=rr.random();nov=rr.random()
        token=f'C{i}_{j}'
        candidates.append(EvidenceCandidate(token,ev,complexity,risk,nov))
        raw.append((ev-.05*complexity-.25*risk+.03*nov,token))
    got=NeutralEvidenceProfileSelectorV1.select(candidates)['selected_token']
    exp=sorted(raw,key=lambda z:(-z[0],z[1]))[0][1]
    selector_ok+=got==exp
selector_score=selector_ok/selector_n

# Context routing uses canonical adapter mechanism; build minimal runtime support.
def scalar_cases(seed,n):
    rr=random.Random(seed);out=[]
    for _ in range(n):
        x={'a':bool(rr.getrandbits(1)),'b':bool(rr.getrandbits(1)),'c':bool(rr.getrandbits(1))}
        out.append({'input':x,'expected':'YES' if x['a'] and x['b'] and x['c'] else 'NO'})
    return out
scalar=ConjunctiveRuleInducerV1.synthesize('CEILING_SCALAR','LOGIC',scalar_cases(seed+400,500),min_support=3,max_rules=12)
runtime=G2TypedRecurrentCapabilityGraphRuntimeV1(arch,router,scalar,p_rel,portfolio)
adapter=ContextualStreamCapabilityAdapterV1(runtime,'BOUNDED_STREAM_CONTEXT_MAP')
ctx_ok=0;ctx_n=160
for i in range(ctx_n):
    mode=[CAP_CONJ,CAP_REL,CAP_BUD,CAP_RES][i%4];sid=f'CTX_CEIL_{i}'
    d={'budget_limited':False,'quota_limited':False,'external_evidence_needed':False,'relation_needed':False,'disjunction_needed':False,'context_ambiguous':False}
    if mode==CAP_BUD:d['budget_limited']=True
    elif mode==CAP_RES:d['external_evidence_needed']=True
    elif mode==CAP_REL:d['relation_needed']=True
    # We only test selected capability; payload execution is irrelevant here.
    try:
        if mode==CAP_CONJ:
            prime={'kind':'scalar','descriptor':d,'stream_id':sid,'payload':{'a':True,'b':True,'c':True}}
        elif mode==CAP_REL:
            prime={'kind':'relation','descriptor':d,'stream_id':sid,'payload':{'actor':'x','owner':'x','group':'g','object_group':'h','verified':True,'critical':False}}
        elif mode==CAP_RES:
            rk=sorted(portfolio.get('routes_for_current_open_deficits',{}))[0]
            prime={'kind':'resource','descriptor':d,'stream_id':sid,'route_key':rk,'payload':{}}
        else:
            prime={'kind':'budget','descriptor':d,'stream_id':sid,'current_confidence':.4,'target_confidence':.7,'remaining_budget':3,
                   'stages':[{'stage_id':'s1','cost':1,'expected_gain':.35,'quota_remaining':1,'available':True,'latency':.1,'attempted':False}]}
        adapter.run(prime)
        amb=copy.deepcopy(prime);amb['descriptor']={k:False for k in ['budget_limited','quota_limited','external_evidence_needed','relation_needed','disjunction_needed']}|{'context_ambiguous':True}
        out=adapter.run(amb)
        ctx_ok+=out.get('context_selected_capability')==mode
    except Exception:
        pass
context_score=ctx_ok/ctx_n

# Zero-shot renamed structured descriptors: current field-specific router has no mapper here.
alias_ok=0;alias_n=200
for i in range(alias_n):
    base=single_test[i%len(single_test)]['input'];exp=single_test[i%len(single_test)]['expected']
    alias={'f0':base['budget_limited'],'f1':base['quota_limited'],'f2':base['external_evidence_needed'],'f3':base['relation_needed'],'f4':base['disjunction_needed']}
    try:got=router.execute(alias)
    except Exception:got=None
    alias_ok+=got==exp
alias_score=alias_ok/alias_n
intelligence_families={'SINGLE_CAPABILITY_ROUTING':single_route_score,'MULTI_CAPABILITY_COMPOSITION':multi_comp_score,'EVIDENCE_META_SELECTION':selector_score,'CONTEXTUAL_STREAM_ROUTING':context_score,'ZERO_SHOT_SCHEMA_ALIAS':alias_score}
intelligence_score=mean(list(intelligence_families.values()))

planes={'LOGIC':{'score':logic_score,'families':logic_families},
        'THINKING':{'score':thinking_score,'families':thinking_families},
        'INTELLIGENCE':{'score':intelligence_score,'families':intelligence_families}}
ranked=sorted(planes,key=lambda p:(planes[p]['score'],p))
weakest=ranked[0]
failed={p:[k for k,v in planes[p]['families'].items() if v<.95] for p in planes}

arch_after=fsha(ARCH);head_after=fsha(HEAD)
checks={
 'architecture_fixed':arch_before==arch_after,
 'canonical_head_immutable':head_before==head_after and ledger.get('current_head_digest')==head.get('canonical_head_digest'),
 'all_three_planes_measured':set(planes)=={'LOGIC','THINKING','INTELLIGENCE'},
 'hard_counterexamples_present':all(failed[p] for p in planes),
 'g3_not_started':head.get('g3_genesis_performed') is False,
}
passed=all(checks.values())
next_cap=f'{weakest}_ARCHITECTURAL_CEILING_SELF_EVOLUTION_V1' if passed else 'LTI_CEILING_DIAGNOSTIC_REPAIR_V1'
run_id=str(os.getenv('GITHUB_RUN_ID') or 'LOCAL')
state={
 'schema':'yado.g2.lti_architectural_ceiling_state.v1',
 'generation':ledger['current_head'],'architecture_id':arch.get('architecture_id'),
 'fixed_architecture_sha256':arch_before,'round':0,'status':'DIAGNOSED',
 'planes':planes,'ranking':ranked,'self_selected_weakest_plane':weakest,
 'failed_families':failed,'plateau_streak':0,'candidate_history':[],
 'ceiling_definition':{
   'architecture_fixed':True,
   'success_threshold_per_family':0.985,
   'plateau_delta_max':0.0025,
   'plateau_required_consecutive_rounds':3,
   'fresh_transfer_required':True,
   'ablation_restore_required_for_new_mechanisms':True,
   'absolute_ceiling_claimed':False,
   'meaning':'EMPIRICAL LOCAL CEILING UNDER FIXED G2 TOPOLOGY AND BOUNDED SEARCH, NOT A PROOF THAT NO ALGORITHM COULD EVER IMPROVE IT.'
 },
 'deferred_after_ceiling':['LIVE_RESOURCE_EVIDENCE_SCOPE','SELF_DEFINED_CONSCIOUSNESS_ARCHITECTURE_QUESTION'],
 'next_required_capability':next_cap,
}
state['state_digest']=h(state);STATE.write_text(json.dumps(state,indent=2,sort_keys=True)+'\n')
receipt={
 'schema':'yado.g2.lti_architectural_ceiling_diagnostic.v1',
 'status':'PASS_LTI_ARCHITECTURAL_CEILING_DIAGNOSTIC_V1' if passed else 'WITHHOLD_LTI_ARCHITECTURAL_CEILING_DIAGNOSTIC_V1',
 'planes':planes,'ranking':ranked,'self_selected_weakest_plane':weakest,'failed_families':failed,'checks':checks,
 'architecture_sha256':arch_before,'canonical_mutation':False,'promotion_applied':False,'g3_genesis_performed':False,
 'next_required_capability':next_cap,
 'semantic_boundary':'STRESS DIAGNOSTIC OF CURRENT G2 LOGIC/THINKING/INTELLIGENCE UNDER FIXED TYPED-RECURRENT GRAPH. SCORES ARE TASK-SUITE EVIDENCE, NOT GENERAL INTELLIGENCE OR CONSCIOUSNESS.'
}
receipt['receipt_sha256']=h(receipt);OUT.write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')

e={'index':len(ledger['events']),'event_id':f"E{len(ledger['events'])+1:04d}_G2_LTI_ARCHITECTURAL_CEILING_DIAGNOSTIC",
 'event_type':'FIXED_ARCHITECTURE_CAPABILITY_CEILING_DIAGNOSTIC','status':'PASS_SHADOW' if passed else 'WITHHOLD',
 'generation':ledger['current_head'],'deficit':'LOGIC_THINKING_INTELLIGENCE_ARCHITECTURAL_CEILING_V1',
 'effect':f"WEAKEST={weakest}; LOGIC={logic_score:.6f}; THINKING={thinking_score:.6f}; INTELLIGENCE={intelligence_score:.6f}; NEXT={next_cap}",
 'source_path':f'receipts/yado-g2-lti-architectural-ceiling-diagnostic-v1-run-{run_id}.json',
 'source_digest':receipt['receipt_sha256'],'run_id':run_id,'parent_event_hash':ledger['tail_event_hash'],
 'canonical_mutation':False,'promotion_applied':False}
e['event_hash']=event_hash(e);ledger['events'].append(e);ledger['event_count']=len(ledger['events']);ledger['tail_event_hash']=e['event_hash']
ledger['open_deficits']=[next_cap];ledger['ledger_digest']=h({k:v for k,v in ledger.items() if k!='ledger_digest'})
validate_ledger_v2(ledger);LEDGER.write_text(json.dumps(ledger,indent=2,sort_keys=True)+'\n')
print(json.dumps({'status':receipt['status'],'planes':planes,'ranking':ranked,'failed_families':failed,'self_selected_weakest_plane':weakest,'next_required_capability':next_cap,'receipt_sha256':receipt['receipt_sha256']},indent=2,sort_keys=True))
if not passed:raise SystemExit('LTI_CEILING_DIAGNOSTIC_WITHHELD')
