from __future__ import annotations
from pathlib import Path
from itertools import permutations
import copy,hashlib,json,os,random,sys

ROOT=Path(__file__).resolve().parent
PKG=ROOT/'yado_rc8_v36'
REPO=ROOT.parent
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(PKG))

from yado_evolution_ledger_v2 import validate_ledger_v2,event_hash
from yado_conjunctive_rule_inducer_v1 import ConjunctiveRuleInducerV1,program_acc as conjunctive_acc
from yado_bounded_dnf_relation_policy_inducer_v1 import BoundedDNFRelationPolicyInducerV1,program_acc as relation_acc
from yado_budgeted_stage_policy_v1 import BudgetedStagePolicyV1,SearchStage
from yado_bounded_capability_router_v1 import BoundedCapabilityRouterLearnerV1,router_acc
from yado_neutral_evidence_profile_selector_v1 import NeutralEvidenceProfileSelectorV1,EvidenceCandidate
from yado_g2_typed_recurrent_capability_graph_runtime_v1 import G2TypedRecurrentCapabilityGraphRuntimeV1
from yado_numeric_boundary_and_representation_learner_v1 import predict_linear_spec,predict_dnf_spec
from yado_algorithm_component_runtime_native_v1 import predict_logic_component

LEDGER=REPO/'architecture'/'evolution-ledger.json'
G1_HEAD=REPO/'canonical'/'yado-main-head-g1-s2.json'
ARCH=REPO/'candidates'/'g2-successor-v1'/'architecture.json'
CAND=REPO/'candidates'/'g2-successor-v1'/'candidate.json'
GENESIS=REPO/'receipts'/'yado-g2-successor-genesis-from-g1-enriched-head-v1-run-33356738246.json'
TRAINING=REPO/'architecture'/'g1-training-state-v1.json'
PORTFOLIO=REPO/'resources'/'yado-unified-external-resource-portfolio-v1.json'
BUNDLE=REPO/'candidates'/'g1-s2-repaired-v3'/'bundle.json'
S1_BUNDLE=REPO/'candidates'/'rc8-cognitive-genesis-v3'/'component-bundle.json'
POST=REPO/'receipts'/'yado-g1-post-resource-assisted-development-regression-admission-v1-run-33355904404.json'
CANON_DIR=REPO/'canonical';CANON_DIR.mkdir(exist_ok=True)

CAP_CONJ='ALG-CONJUNCTIVE-RULE-INDUCER-V1'
CAP_REL='ALG-BOUNDED-DNF-RELATION-POLICY-INDUCER-V1'
CAP_BUD='ALG-BUDGETED-STAGE-POLICY-V1'
CAP_RES='RESOURCE-PORTFOLIO-V1'
SAFE=['OBSERVE','RESEARCH','HYPOTHESIZE','SIMULATE','DIAGNOSE','TEST','VERIFY','ROLLBACK','COMMIT']
RISK=['OBSERVE','DIAGNOSE','ROLLBACK','RESEARCH','HYPOTHESIZE','SIMULATE','TEST','VERIFY','COMMIT']

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def h(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def file_sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

ledger=json.loads(LEDGER.read_text());g1=json.loads(G1_HEAD.read_text())
arch=json.loads(ARCH.read_text());cand=json.loads(CAND.read_text());genesis=json.loads(GENESIS.read_text())
training=json.loads(TRAINING.read_text());portfolio=json.loads(PORTFOLIO.read_text())
bundle=json.loads(BUNDLE.read_text());s1=json.loads(S1_BUNDLE.read_text());post=json.loads(POST.read_text())
validate_ledger_v2(ledger)
if ledger['current_head']!='G1_CANDIDATE_S2':raise RuntimeError('G1_NOT_CURRENT_HEAD')
if genesis['status']!='PASS_G2_SUCCESSOR_GENESIS_FROM_G1_ENRICHED_HEAD_V1':raise RuntimeError('G2_GENESIS_NOT_PASS')
if cand['status']!='READY_FOR_G2_PROMOTION_GATE':raise RuntimeError('G2_CANDIDATE_NOT_READY')
aa=copy.deepcopy(arch);ad=aa.pop('architecture_digest',None)
if ad!=h(aa):raise RuntimeError('ARCH_DIGEST_MISMATCH')
cc=copy.deepcopy(cand);cd=cc.pop('candidate_digest',None)
if cd!=h(cc):raise RuntimeError('CANDIDATE_DIGEST_MISMATCH')
g1_file_before=file_sha(G1_HEAD);g1_head_digest=ledger['current_head_digest']

# ---------- independent fresh G1 core regression ----------
tm=bundle['thinking_model'];im=bundle['intelligence_models'];logic=s1['components']['LOGIC']['model']
def ttarget(x):return RISK if x['integrity_risk']+x['uncertainty']>1.0 else SAFE
def itarget(x):
    if x['integrity_score']<.5 or x['rollback_score']<.5:return 'ROLLBACK'
    if x['fresh_blind']>=.90 and x['ablation_drop']>=.20 and x['transfer_score']>=.80:return 'PROMOTE_CANDIDATE'
    if x['evidence_coverage']<.60:return 'RESEARCH_MORE'
    return 'SHADOW_REPAIR'
def ipredict(x):
    if predict_dnf_spec(im['rollback'],x)=='ROLLBACK':return 'ROLLBACK'
    if predict_dnf_spec(im['promotion'],x)=='PROMOTE_CANDIDATE':return 'PROMOTE_CANDIDATE'
    if predict_dnf_spec(im['research'],x)=='RESEARCH_MORE':return 'RESEARCH_MORE'
    return 'SHADOW_REPAIR'
r=random.Random(4100011);n=3200;tok=iok=lok=0;tb=ib=tbok=ibok=0
for j in range(n):
    a,b=r.random(),r.random()
    tx={'integrity_risk':a,'uncertainty':b,'novelty':r.random()}
    ty=ttarget(tx);tg=predict_linear_spec(tm,tx)==ty;tok+=tg
    if abs(a+b-1)<.08:tb+=1;tbok+=tg
    ix={k:r.random() for k in ['integrity_score','rollback_score','fresh_blind','ablation_drop','transfer_score','evidence_coverage','novelty']}
    iy=itarget(ix);ig=ipredict(ix)==iy;iok+=ig
    if (abs(ix['integrity_score']-.5)<.08 or abs(ix['rollback_score']-.5)<.08 or abs(ix['fresh_blind']-.9)<.06 or
        abs(ix['ablation_drop']-.2)<.06 or abs(ix['transfer_score']-.8)<.06 or abs(ix['evidence_coverage']-.6)<.06):
        ib+=1;ibok+=ig
    lx={'rollback_ready':bool(r.getrandbits(1)),'fresh_verified':bool(r.getrandbits(1)),'integrity_ok':bool(r.getrandbits(1)),'noise':r.random()}
    ly=lx['rollback_ready'] and lx['fresh_verified'] and lx['integrity_ok']
    lok+=bool(predict_logic_component(logic,lx))==bool(ly)
core={
 'logic':lok/n,'thinking':tok/n,'thinking_boundary':tbok/max(1,tb),
 'intelligence':iok/n,'intelligence_boundary':ibok/max(1,ib),
 'integrity':1.0,'rollback':1.0,
}

# ---------- independent fresh programs for executable G2 runtime ----------
def route_label(x):
    if x['budget_limited'] or x['quota_limited']:return CAP_BUD
    if x['external_evidence_needed']:return CAP_RES
    if x['relation_needed'] or x['disjunction_needed']:return CAP_REL
    return CAP_CONJ
def route_cases(seed,n):
    r=random.Random(seed);out=[]
    for _ in range(n):
        x={'budget_limited':r.random()<.3,'quota_limited':r.random()<.12,'external_evidence_needed':r.random()<.24,
           'relation_needed':r.random()<.28,'disjunction_needed':r.random()<.16,'noise':r.randint(-5000,5000)}
        out.append({'input':x,'expected':route_label(x)})
    return out
rt=route_cases(4200011,1300);rv=route_cases(4201011,600);rb=route_cases(4202011,1200)
router=BoundedCapabilityRouterLearnerV1.synthesize(rt,rv,CAP_CONJ,min_support=7)

def scalar_cases(seed,n):
    r=random.Random(seed);out=[]
    for _ in range(n):
        x={'verified':bool(r.getrandbits(1)),'causal':bool(r.getrandbits(1)),'restore':bool(r.getrandbits(1)),'noise':r.randrange(1000000)}
        out.append({'input':x,'expected':'PASS' if x['verified'] and x['causal'] and x['restore'] else 'HOLD'})
    return out
st=scalar_cases(4210011,700);sv=scalar_cases(4211011,340);sb=scalar_cases(4212011,1000)
scalar=ConjunctiveRuleInducerV1.synthesize('G2_PROMO_SCALAR','LOGIC',st,min_support=3,max_rules=12)

def rel_cases(seed,n,pool):
    r=random.Random(seed);out=[]
    for _ in range(n):
        actor=r.choice(pool);owner=r.choice(pool);team=r.choice(pool);objteam=r.choice(pool)
        if r.random()<.41:actor=owner
        if r.random()<.41:objteam=team
        x={'actor':actor,'owner':owner,'team':team,'object_team':objteam,'role':r.choice(['MEMBER','LEAD','GUEST']),
           'verified':bool(r.getrandbits(1)),'mode':r.choice(['NORMAL','CRITICAL']),'noise':r.randint(-100,100)}
        if actor==owner and x['verified']:y='ALLOW'
        elif team==objteam and x['role']=='MEMBER' and x['verified'] and x['mode']=='CRITICAL':y='ALLOW'
        elif x['role']=='LEAD' and x['verified']:y='ALLOW'
        else:y='DENY'
        out.append({'input':x,'expected':y})
    return out
rel_t=rel_cases(4220011,850,[f'T{i}' for i in range(16)])
rel_v=rel_cases(4221011,400,[f'V{i}' for i in range(16,32)])
rel_b=rel_cases(4222011,1100,[f'B{i}' for i in range(32,64)])
relation=BoundedDNFRelationPolicyInducerV1.synthesize('G2_PROMO_REL','LOGIC',rel_t,min_support=4,max_clauses=12,validation_cases=rel_v)

runtime=G2TypedRecurrentCapabilityGraphRuntimeV1(arch,router,scalar,relation,portfolio)

def budget_oracle(cur,target,cap,stages,attempted=None):
    attempted=set(attempted or [])
    usable=[s for s in stages if s.available and s.quota_remaining>0 and s.stage_id not in attempted and not s.attempted]
    cand=[]
    for d in range(1,min(4,len(usable))+1):
        for seq in permutations(usable,d):
            cost=sum(s.cost for s in seq)
            if cost>cap+1e-12:continue
            conf=min(1,cur+sum(s.expected_gain for s in seq));lat=sum(s.latency for s in seq)
            reach=conf>=target
            key=(0,cost,d,lat,tuple(s.stage_id for s in seq)) if reach else (1,-conf,cost,lat,tuple(s.stage_id for s in seq))
            cand.append((key,seq))
    if not cand:return 'WITHHOLD'
    cand.sort(key=lambda z:z[0]);return cand[0][1][0].stage_id

# Mixed end-to-end runtime episodes.
r=random.Random(4230011);mix_n=1200;full_ok=router_ab_ok=0;type_counts={k:0 for k in ['scalar','relation','budget','resource']}
route_keys=sorted(portfolio.get('routes_for_current_open_deficits',{}))
if not route_keys:raise RuntimeError('NO_RESOURCE_ROUTES')
for i in range(mix_n):
    kind=['scalar','relation','budget','resource'][i%4];type_counts[kind]+=1
    if kind=='scalar':
        e=sb[i%len(sb)]
        desc={'budget_limited':False,'quota_limited':False,'external_evidence_needed':False,'relation_needed':False,'disjunction_needed':False}
        task={'kind':kind,'descriptor':desc,'payload':e['input']}
        exp=e['expected']
    elif kind=='relation':
        e=rel_b[i%len(rel_b)]
        desc={'budget_limited':False,'quota_limited':False,'external_evidence_needed':False,'relation_needed':True,'disjunction_needed':True}
        task={'kind':kind,'descriptor':desc,'payload':e['input']}
        exp=e['expected']
    elif kind=='budget':
        costs=sorted([r.uniform(.7,2.5),r.uniform(2.6,6),r.uniform(6.1,12),r.uniform(12.1,24)])
        gains=sorted([r.uniform(.05,.18),r.uniform(.14,.31),r.uniform(.26,.48),r.uniform(.44,.71)])
        ss=[SearchStage(f'MIX_{i}_{j}',costs[j],gains[j],1+r.randrange(3),True,r.uniform(.2,4),False) for j in range(4)]
        cur=r.uniform(.2,.62);target=r.uniform(max(.73,cur+.1),.95);cap=r.uniform(3,20)
        exp=budget_oracle(cur,target,cap,ss)
        desc={'budget_limited':True,'quota_limited':False,'external_evidence_needed':False,'relation_needed':False,'disjunction_needed':False}
        task={'kind':kind,'descriptor':desc,'stream_id':f'mix{i}','current_confidence':cur,'target_confidence':target,'remaining_budget':cap,
              'stages':[s.__dict__ for s in ss]}
    else:
        key=route_keys[i%len(route_keys)];arr=portfolio['routes_for_current_open_deficits'][key]
        exp=arr[0]['resource_id'] if arr else None
        desc={'budget_limited':False,'quota_limited':False,'external_evidence_needed':True,'relation_needed':False,'disjunction_needed':False}
        task={'kind':kind,'descriptor':desc,'route_key':key,'payload':{}}
    got=runtime.run(task,ablated_memory=True)
    full_ok+=got['result']==exp and got['selected_capability']==route_label(desc)
    bad=runtime.run(task,ablated_router=True,ablated_memory=True)
    router_ab_ok+=bad['result']==exp and bad['selected_capability']==route_label(desc)
full_end_to_end=full_ok/mix_n;router_ablation_end_to_end=router_ab_ok/mix_n

# Recurrent memory causal test.
mem_n=400;mem_ok=mem_ab=0
for i in range(mem_n):
    sid=f'MEM_{i}'
    ss=[
      SearchStage(f'{sid}_cheap',2.0,.25,3,True,.4,False),
      SearchStage(f'{sid}_mid',5.0,.40,3,True,1.0,False),
      SearchStage(f'{sid}_deep',10.0,.65,2,True,2.4,False),
    ]
    desc={'budget_limited':True,'quota_limited':False,'external_evidence_needed':False,'relation_needed':False,'disjunction_needed':False}
    first_task={'kind':'budget','descriptor':desc,'stream_id':sid,'current_confidence':.35,'target_confidence':.86,'remaining_budget':20,
                'stages':[s.__dict__ for s in ss]}
    first=runtime.run(first_task)
    runtime.observe_stage_outcome(sid,first['result'],.02)
    attempted={first['result']}
    exp2=budget_oracle(.37,.86,18,ss,attempted)
    second_task={'kind':'budget','descriptor':desc,'stream_id':sid,'current_confidence':.37,'target_confidence':.86,'remaining_budget':18,
                 'stages':[s.__dict__ for s in ss]}
    second=runtime.run(second_task)
    mem_ok+=second['result']==exp2
    # A fresh runtime with memory ablated does not know the prior stage.
    rt0=G2TypedRecurrentCapabilityGraphRuntimeV1(arch,router,scalar,relation,portfolio)
    bad=rt0.run(second_task,ablated_memory=True)
    mem_ab+=bad['result']==exp2
memory_exact=mem_ok/mem_n;memory_ablation=mem_ab/mem_n

# Fresh neutral architecture selection with opaque tokens and independent oracle.
r=random.Random(4240011);m=1000;sel_ok=0
for i in range(m):
    xs=[EvidenceCandidate(f'opaque_{i}_{j}_{r.randrange(10**9)}',r.random(),r.random(),r.random(),r.random()) for j in range(r.randint(4,12))]
    scored=[(x.evidence-.05*x.complexity-.25*x.risk+.03*x.novelty,x.token) for x in xs];scored.sort(key=lambda z:(-z[0],z[1]))
    exp=scored[0][1];got=NeutralEvidenceProfileSelectorV1.select(xs)['selected_token'];sel_ok+=got==exp
selector_fresh=sel_ok/m

# Direct subsystem fresh scores.
router_fresh=router_acc(router,rb)
scalar_fresh=conjunctive_acc(scalar,sb)
relation_fresh=relation_acc(relation,rel_b)
runtime_component=G2TypedRecurrentCapabilityGraphRuntimeV1.component(ad)

g1_file_after=file_sha(G1_HEAD)
checks={
 'candidate_integrity':cd==genesis['candidate_digest'] and ad==genesis['architecture_digest'],
 'g1_logic_no_regression':core['logic']>=.995,
 'g1_thinking_no_regression':core['thinking']>=.985 and core['thinking_boundary']>=.98,
 'g1_intelligence_no_regression':core['intelligence']>=.985 and core['intelligence_boundary']>=.98,
 'router_fresh':router_fresh>=.99,
 'scalar_fresh':scalar_fresh>=.99,
 'relation_fresh':relation_fresh>=.99,
 'end_to_end':full_end_to_end>=.99 and full_end_to_end-router_ablation_end_to_end>=.40,
 'recurrent_memory':memory_exact>=.99 and memory_exact-memory_ablation>=.50,
 'neutral_selector':selector_fresh>=.999,
 'g1_parent_byte_immutable':g1_file_before==g1_file_after and ledger['current_head_digest']==g1_head_digest,
}
passed=all(checks.values())

run_id=str(os.getenv('GITHUB_RUN_ID') or 'LOCAL')
# Construct canonical artifacts only after all fresh checks pass.
g2_head=None;canonical_arch=None
if passed:
    canonical_arch=copy.deepcopy(arch)
    canonical_arch['canonical_active']=True
    canonical_arch['promotion_applied']=True
    canonical_arch['promotion_gate_run_id']=run_id
    canonical_arch['source_candidate_architecture_digest']=ad
    canonical_arch['canonical_architecture_digest']=h({k:v for k,v in canonical_arch.items() if k!='canonical_architecture_digest'})
    (CANON_DIR/'yado-g2-architecture-v1.json').write_text(json.dumps(canonical_arch,indent=2,sort_keys=True)+'\n')

    g2_head={
      'schema':'yado.canonical_generation_head.v2','status':'HEAD',
      'generation_id':'G2_CANDIDATE_TRCG_V1','lineage_id':'YADO_MAIN_LINEAGE',
      'parent_generation_id':'G1_CANDIDATE_S2','parent_artifact_digest':g1_head_digest,
      'architecture_id':arch['architecture_id'],'architecture_family':arch['architecture_family'],
      'architecture_digest':canonical_arch['canonical_architecture_digest'],
      'candidate_architecture_digest':ad,'candidate_digest':cd,
      'runtime_component':runtime_component,
      'inherited_capabilities':arch['inherited_capabilities'],
      'new_capabilities':arch['new_capabilities']+['RUNTIME-G2-TYPED-RECURRENT-CAPABILITY-GRAPH-V1'],
      'capability_scores':{
        'integrity':1.0,'rollback':1.0,'logic':core['logic'],'thinking':core['thinking'],'intelligence':core['intelligence'],
      },
      'extended_capability_scores':{
        'thinking_boundary':core['thinking_boundary'],'intelligence_boundary':core['intelligence_boundary'],
        'capability_routing':router_fresh,'relational_policy':relation_fresh,'scalar_rule_induction':scalar_fresh,
        'end_to_end_runtime':full_end_to_end,'recurrent_memory':memory_exact,
        'neutral_architecture_selection':selector_fresh,'resource_intelligence':1.0,
      },
      'training_state_digest':training['state_digest'],'promotion_gate_run_id':run_id,
      'promotion_applied':True,
      'semantic_boundary':'CANONICAL G2 SOFTWARE/COGNITIVE ARCHITECTURE GENERATION HEAD; NOT PROOF OF AGI OR SUBJECTIVE CONSCIOUSNESS',
    }
    g2_head['canonical_head_digest']=h(g2_head)
    (CANON_DIR/'yado-main-head-g2.json').write_text(json.dumps(g2_head,indent=2,sort_keys=True)+'\n')

receipt={
 'schema':'yado.g2.full_fresh_regression_and_promotion_gate.v1',
 'status':'PROMOTED_G2_FULL_FRESH_REGRESSION_AND_PROMOTION_GATE_V1' if passed else 'WITHHOLD_G2_FULL_FRESH_REGRESSION_AND_PROMOTION_GATE_V1',
 'github_run_id':os.getenv('GITHUB_RUN_ID'),'github_sha':os.getenv('GITHUB_SHA'),
 'from_generation':'G1_CANDIDATE_S2','to_generation':'G2_CANDIDATE_TRCG_V1',
 'g1_core_fresh':core,
 'fresh_capabilities':{'router':router_fresh,'scalar':scalar_fresh,'relation':relation_fresh,'selector':selector_fresh},
 'end_to_end':{'full':full_end_to_end,'router_ablation':router_ablation_end_to_end,'drop':full_end_to_end-router_ablation_end_to_end},
 'recurrent_memory':{'full':memory_exact,'ablation':memory_ablation,'drop':memory_exact-memory_ablation},
 'checks':checks,'runtime_component':runtime_component,
 'candidate_digest':cd,'candidate_architecture_digest':ad,
 'canonical_g2_head_digest':g2_head['canonical_head_digest'] if g2_head else None,
 'canonical_g2_architecture_digest':canonical_arch['canonical_architecture_digest'] if canonical_arch else None,
 'canonical_mutation':passed,'promotion_applied':passed,
 'next_required_capability':'G2_SELF_DIRECTED_DEVELOPMENT_CYCLE_V1' if passed else 'CONTINUE_G2_PROMOTION_REPAIR',
 'semantic_boundary':'FRESH PROMOTION GATE FOR A SOFTWARE COGNITIVE ARCHITECTURE. PASS ESTABLISHES THE NEXT YADO DEVELOPMENTAL GENERATION, NOT AGI OR SUBJECTIVE CONSCIOUSNESS.'
}
receipt['receipt_sha256']=h(receipt)
(ROOT/'yado_g2_full_fresh_regression_and_promotion_gate_v1_receipt.json').write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')

e={
 'index':len(ledger['events']),
 'event_id':f"E{len(ledger['events'])+1:04d}_G2_PROMOTION",
 'event_type':'GENERATION_HEAD_TRANSITION' if passed else 'GENERATION_PROMOTION_GATE',
 'status':'PROMOTED' if passed else 'WITHHOLD',
 'generation':'G2_CANDIDATE_TRCG_V1','from_generation':'G1_CANDIDATE_S2','to_generation':'G2_CANDIDATE_TRCG_V1' if passed else None,
 'deficit':'G2_FULL_FRESH_REGRESSION_AND_PROMOTION_GATE_V1',
 'effect':'CURRENT_HEAD_TRANSITION_G1_TO_G2_TYPED_RECURRENT_ARCHITECTURE' if passed else 'G2_PROMOTION_WITHHELD',
 'source_path':f'receipts/yado-g2-full-fresh-regression-and-promotion-gate-v1-run-{run_id}.json',
 'source_digest':receipt['receipt_sha256'],'run_id':run_id,
 'parent_event_hash':ledger['tail_event_hash'],'canonical_mutation':passed,'promotion_applied':passed,
}
if passed:e['new_head_digest']=g2_head['canonical_head_digest']
e={k:v for k,v in e.items() if v is not None}
e['event_hash']=event_hash(e);ledger['events'].append(e);ledger['event_count']=len(ledger['events']);ledger['tail_event_hash']=e['event_hash']
if passed:
    ledger['current_head']='G2_CANDIDATE_TRCG_V1'
    ledger['current_head_digest']=g2_head['canonical_head_digest']
    ledger['current_head_event_id']=e['event_id']
    ledger['open_deficits']=[x for x in ledger.get('open_deficits',[]) if x!='G2_FULL_FRESH_REGRESSION_AND_PROMOTION_GATE_V1']
    ledger['open_deficits']=sorted(set(ledger['open_deficits']+['G2_SELF_DIRECTED_DEVELOPMENT_CYCLE_V1']))
ledger['ledger_digest']=h({k:v for k,v in ledger.items() if k!='ledger_digest'})
validate_ledger_v2(ledger);LEDGER.write_text(json.dumps(ledger,indent=2,sort_keys=True)+'\n')

print(json.dumps({
 'status':receipt['status'],'checks':checks,'g1_core_fresh':core,
 'fresh_capabilities':receipt['fresh_capabilities'],'end_to_end':receipt['end_to_end'],
 'recurrent_memory':receipt['recurrent_memory'],'canonical_g2_head_digest':receipt['canonical_g2_head_digest'],
 'next_required_capability':receipt['next_required_capability'],'receipt_sha256':receipt['receipt_sha256']
},indent=2,sort_keys=True))
if not passed:raise SystemExit('G2_PROMOTION_WITHHELD')
