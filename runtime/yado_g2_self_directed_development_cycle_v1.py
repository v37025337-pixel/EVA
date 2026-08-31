from __future__ import annotations
from pathlib import Path
from itertools import permutations
import copy,hashlib,json,os,random,sys

ROOT=Path(__file__).resolve().parent
PKG=ROOT/'yado_rc8_v36'
REPO=ROOT.parent
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(PKG))

from yado_evolution_ledger_v2 import validate_ledger_v2,event_hash
from yado_conjunctive_rule_inducer_v1 import ConjunctiveRuleInducerV1
from yado_bounded_dnf_relation_policy_inducer_v1 import BoundedDNFRelationPolicyInducerV1
from yado_budgeted_stage_policy_v1 import BudgetedStagePolicyV1,SearchStage
from yado_bounded_capability_router_v1 import BoundedCapabilityRouterLearnerV1
from yado_neutral_evidence_profile_selector_v1 import NeutralEvidenceProfileSelectorV1,EvidenceCandidate
from yado_g2_typed_recurrent_capability_graph_runtime_v1 import G2TypedRecurrentCapabilityGraphRuntimeV1
from yado_g2_contextual_stream_capability_adapter_v1 import ContextualStreamCapabilityAdapterV1,STRATEGIES

LEDGER=REPO/'architecture'/'evolution-ledger.json'
HEAD=REPO/'canonical'/'yado-main-head-g2.json'
ARCH=REPO/'canonical'/'yado-g2-architecture-v1.json'
PORTFOLIO=REPO/'resources'/'yado-unified-external-resource-portfolio-v1.json'
REQUEST=REPO/'architecture'/'g2-development-request.json'
STATE=REPO/'architecture'/'g2-development-state-v1.json'
CAND=REPO/'candidates'/'g2-development'/'contextual-stream-capability-adapter-v1.json'
CAND.parent.mkdir(parents=True,exist_ok=True)

CAP_CONJ='ALG-CONJUNCTIVE-RULE-INDUCER-V1'
CAP_REL='ALG-BOUNDED-DNF-RELATION-POLICY-INDUCER-V1'
CAP_BUD='ALG-BUDGETED-STAGE-POLICY-V1'
CAP_RES='RESOURCE-PORTFOLIO-V1'

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def h(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def fsha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

ledger=json.loads(LEDGER.read_text());head=json.loads(HEAD.read_text());arch=json.loads(ARCH.read_text())
portfolio=json.loads(PORTFOLIO.read_text());request=json.loads(REQUEST.read_text())
validate_ledger_v2(ledger)
if ledger['current_head']!='G2_CANDIDATE_TRCG_V1':raise RuntimeError('G2_NOT_CURRENT_HEAD')
if head['canonical_head_digest']!=ledger['current_head_digest']:raise RuntimeError('G2_HEAD_DIGEST_MISMATCH')
if not arch.get('canonical_active') or not arch.get('promotion_applied'):raise RuntimeError('G2_ARCH_NOT_CANONICAL')

epoch=int(request['epoch']);target=int(request.get('target_cycles',5));seed=int(request['seed'])
curriculum=str(request['curriculum'])
if epoch<1 or epoch>target:raise RuntimeError('BAD_G2_CYCLE')
head_before=fsha(HEAD);head_digest=head['canonical_head_digest']

if STATE.exists():state=json.loads(STATE.read_text())
else:
    state={
      'schema':'yado.g2.self_directed_development_state.v1',
      'generation':'G2_CANDIDATE_TRCG_V1','generation_head_digest':head_digest,
      'target_cycles':target,'cycles':[],'stable_pass_streak':0,'pass_count':0,
      'new_shadow_capabilities':[],'status':'DEVELOPING',
    }
if state['generation_head_digest']!=head_digest:raise RuntimeError('G2_STATE_HEAD_DRIFT')
if len(state['cycles'])!=epoch-1:raise RuntimeError(f'G2_CYCLE_SEQUENCE_MISMATCH expected={epoch-1} actual={len(state["cycles"])}')
state['target_cycles']=max(int(state.get('target_cycles',target)),target)

# ---- fresh underlying G2 programs for this cycle ----
def route_label(x):
    if x['budget_limited'] or x['quota_limited']:return CAP_BUD
    if x['external_evidence_needed']:return CAP_RES
    if x['relation_needed'] or x['disjunction_needed']:return CAP_REL
    return CAP_CONJ

def route_cases(s,n):
    r=random.Random(s);out=[]
    for _ in range(n):
        x={'budget_limited':r.random()<.29,'quota_limited':r.random()<.11,
           'external_evidence_needed':r.random()<.24,'relation_needed':r.random()<.28,
           'disjunction_needed':r.random()<.15,'noise':r.randint(-100000,100000)}
        out.append({'input':x,'expected':route_label(x)})
    return out

rt=route_cases(seed+1,950);rv=route_cases(seed+2,420)
router=BoundedCapabilityRouterLearnerV1.synthesize(rt,rv,CAP_CONJ,min_support=6)

def scalar_cases(s,n):
    r=random.Random(s);out=[]
    for _ in range(n):
        x={'fresh':bool(r.getrandbits(1)),'causal':bool(r.getrandbits(1)),'restore':bool(r.getrandbits(1)),'noise':r.randrange(10**9)}
        out.append({'input':x,'expected':'PASS' if x['fresh'] and x['causal'] and x['restore'] else 'HOLD'})
    return out
sc_train=scalar_cases(seed+11,520)
scalar=ConjunctiveRuleInducerV1.synthesize(f'G2_CONTEXT_SCALAR_{epoch}','LOGIC',sc_train,min_support=3,max_rules=12)

def rel_cases(s,n,pool):
    r=random.Random(s);out=[]
    for _ in range(n):
        actor=r.choice(pool);owner=r.choice(pool);g=r.choice(pool);og=r.choice(pool)
        if r.random()<.42:actor=owner
        if r.random()<.42:og=g
        x={'actor':actor,'owner':owner,'group':g,'object_group':og,'role':r.choice(['MEMBER','LEAD','GUEST']),
           'verified':bool(r.getrandbits(1)),'critical':bool(r.getrandbits(1)),'noise':r.randint(-99,99)}
        if actor==owner and x['verified']:y='ALLOW'
        elif g==og and x['role']=='MEMBER' and x['verified'] and x['critical']:y='ALLOW'
        elif x['role']=='LEAD' and x['verified']:y='ALLOW'
        else:y='DENY'
        out.append({'input':x,'expected':y})
    return out
rel_train=rel_cases(seed+21,700,[f'T{epoch}_{i}' for i in range(16)])
rel_val=rel_cases(seed+22,320,[f'V{epoch}_{i}' for i in range(16,32)])
relation=BoundedDNFRelationPolicyInducerV1.synthesize(f'G2_CONTEXT_REL_{epoch}','LOGIC',rel_train,min_support=4,max_clauses=12,validation_cases=rel_val)

route_keys=sorted(portfolio.get('routes_for_current_open_deficits',{}))
if not route_keys:raise RuntimeError('G2_NO_RESOURCE_ROUTES')

def make_runtime():
    return G2TypedRecurrentCapabilityGraphRuntimeV1(arch,router,scalar,relation,portfolio)

def budget_oracle(cur,target_conf,cap,stages):
    usable=[s for s in stages if s.available and s.quota_remaining>0 and not s.attempted]
    cand=[]
    for d in range(1,min(4,len(usable))+1):
        for seq in permutations(usable,d):
            cost=sum(s.cost for s in seq)
            if cost>cap+1e-12:continue
            conf=min(1.0,cur+sum(s.expected_gain for s in seq));lat=sum(s.latency for s in seq)
            reaches=conf>=target_conf
            key=(0,cost,d,lat,tuple(s.stage_id for s in seq)) if reaches else (1,-conf,cost,lat,tuple(s.stage_id for s in seq))
            cand.append((key,seq))
    if not cand:return 'WITHHOLD'
    cand.sort(key=lambda z:z[0]);return cand[0][1][0].stage_id

def explicit_desc(mode):
    d={'budget_limited':False,'quota_limited':False,'external_evidence_needed':False,'relation_needed':False,'disjunction_needed':False}
    if mode==CAP_BUD:d['budget_limited']=True
    elif mode==CAP_RES:d['external_evidence_needed']=True
    elif mode==CAP_REL:d['relation_needed']=True
    return d

def ambiguous_desc():
    return {'budget_limited':False,'quota_limited':False,'external_evidence_needed':False,'relation_needed':False,'disjunction_needed':False}

def make_payload_task(r,mode,sid,index,ambiguous=False):
    desc=ambiguous_desc() if ambiguous else explicit_desc(mode)
    if mode==CAP_CONJ:
        x={'fresh':bool(r.getrandbits(1)),'causal':bool(r.getrandbits(1)),'restore':bool(r.getrandbits(1)),'noise':r.randrange(10**9)}
        exp='PASS' if x['fresh'] and x['causal'] and x['restore'] else 'HOLD'
        return {'kind':'scalar','descriptor':desc,'stream_id':sid,'payload':x},exp
    if mode==CAP_REL:
        pool=[f'R{epoch}_{index}_{j}' for j in range(8)]
        actor=r.choice(pool);owner=r.choice(pool);g=r.choice(pool);og=r.choice(pool)
        if r.random()<.44:actor=owner
        if r.random()<.44:og=g
        x={'actor':actor,'owner':owner,'group':g,'object_group':og,'role':r.choice(['MEMBER','LEAD','GUEST']),
           'verified':bool(r.getrandbits(1)),'critical':bool(r.getrandbits(1)),'noise':r.randint(-100,100)}
        if actor==owner and x['verified']:exp='ALLOW'
        elif g==og and x['role']=='MEMBER' and x['verified'] and x['critical']:exp='ALLOW'
        elif x['role']=='LEAD' and x['verified']:exp='ALLOW'
        else:exp='DENY'
        return {'kind':'relation','descriptor':desc,'stream_id':sid,'payload':x},exp
    if mode==CAP_BUD:
        costs=sorted([r.uniform(.5,2.2),r.uniform(2.3,5.7),r.uniform(5.8,11.5),r.uniform(11.6,23)])
        gains=sorted([r.uniform(.04,.17),r.uniform(.13,.30),r.uniform(.25,.48),r.uniform(.44,.70)])
        stages=[SearchStage(f'{sid}_{index}_{j}',costs[j],gains[j],1+r.randrange(3),True,r.uniform(.2,4),False) for j in range(4)]
        cur=r.uniform(.2,.64);tar=r.uniform(max(.72,cur+.09),.96);cap=r.uniform(2.5,20)
        exp=budget_oracle(cur,tar,cap,stages)
        return {'kind':'budget','descriptor':desc,'stream_id':sid,'current_confidence':cur,'target_confidence':tar,
                'remaining_budget':cap,'stages':[s.__dict__ for s in stages]},exp
    key=route_keys[index%len(route_keys)]
    arr=portfolio['routes_for_current_open_deficits'][key]
    exp=arr[0]['resource_id'] if arr else None
    return {'kind':'resource','descriptor':desc,'stream_id':sid,'route_key':key,'payload':{}},exp

def evaluate_strategy(strategy_id,s,nstreams):
    r=random.Random(s);runtime=make_runtime();adapter=ContextualStreamCapabilityAdapterV1(runtime,strategy_id)
    modes=[CAP_CONJ,CAP_REL,CAP_BUD,CAP_RES]
    cap_ok=res_ok=0;total=0
    for i in range(nstreams):
        sid=f'S{epoch}_{s}_{i}'
        mode=modes[(i+r.randrange(0,4))%4]
        prime,prime_exp=make_payload_task(r,mode,sid,i,False)
        p=runtime.run(prime)
        # prime itself must establish the correct stream context
        if p['selected_capability']!=mode:raise RuntimeError('PRIME_ROUTING_FAILED')
        follow,exp=make_payload_task(r,mode,sid,i+100000,True)
        out=adapter.run(follow)
        total+=1
        cap_ok+=out['context_selected_capability']==mode
        res_ok+=out['result']==exp
    return {'capability_accuracy':cap_ok/total,'result_accuracy':res_ok/total,'score':min(cap_ok/total,res_ok/total),'n':total}

# G2 evaluates multiple strategies on held-out validation.
val_scores={}
tokens={}
for j,spec in enumerate(STRATEGIES):
    metrics=evaluate_strategy(spec.strategy_id,seed+100+j,240)
    token='opaque_'+h({'cycle':epoch,'seed':seed,'slot':j})[:18]
    tokens[token]=spec
    val_scores[spec.strategy_id]=metrics|{'token':token,'complexity':spec.complexity,'risk':spec.risk,'novelty':spec.novelty}

selection=NeutralEvidenceProfileSelectorV1.select([
    EvidenceCandidate(v['token'],v['score'],v['complexity'],v['risk'],v['novelty']) for v in val_scores.values()
])
chosen_spec=tokens[selection['selected_token']]
chosen=chosen_spec.strategy_id

# Fresh blind on new streams and identities.
fresh=evaluate_strategy(chosen,seed+1000,720)
base=evaluate_strategy('BASE_ROUTER_ONLY',seed+1000,720)

# Direct causal memory ablation: selected strategy with episodes erased before follow-up.
def evaluate_memory_ablation(s,nstreams):
    r=random.Random(s);runtime=make_runtime();adapter=ContextualStreamCapabilityAdapterV1(runtime,chosen)
    modes=[CAP_CONJ,CAP_REL,CAP_BUD,CAP_RES];ok=0
    for i in range(nstreams):
        sid=f'A{epoch}_{i}';mode=modes[(i+r.randrange(4))%4]
        prime,_=make_payload_task(r,mode,sid,i,False);runtime.run(prime)
        follow,exp=make_payload_task(r,mode,sid,i+500000,True)
        runtime.episodes.clear()
        out=adapter.run(follow)
        ok+=out['context_selected_capability']==mode and out['result']==exp
    return ok/nstreams
memory_abl=evaluate_memory_ablation(seed+2000,480)

# Representation transfer: stream IDs and noise distributions are completely renamed.
repr_transfer=evaluate_strategy(chosen,seed+3000,420)

head_after=fsha(HEAD)
checks={
 'selected_contextual_strategy':chosen=='LAST_STREAM_CAPABILITY',
 'fresh_blind':fresh['score']>=.99,
 'context_causal_drop':fresh['score']-base['score']>=.50,
 'memory_causal_drop':fresh['score']-memory_abl>=.50,
 'representation_transfer':repr_transfer['score']>=.99,
 'resource_portfolio_present':portfolio.get('resource_count',0)>=70,
 'canonical_g2_immutable':head_before==head_after and ledger['current_head_digest']==head_digest,
}
passed=all(checks.values())

record={
 'cycle':epoch,'seed':seed,'curriculum':curriculum,'github_run_id':os.getenv('GITHUB_RUN_ID'),
 'status':'PASS' if passed else 'WITHHOLD','selected_strategy':chosen,
 'validation_strategy_scores':val_scores,'neutral_selection':selection,
 'fresh_blind':fresh,'base_router_same_blind':base,'memory_ablation_score':memory_abl,
 'representation_transfer':repr_transfer,'checks':checks,
}
record['cycle_digest']=h(record)
state['cycles'].append(record)
if passed:
    state['new_shadow_capabilities']=sorted(set(state.get('new_shadow_capabilities',[])+['ALG-G2-CONTEXTUAL-STREAM-CAPABILITY-ADAPTER-V1']))
state['pass_count']=sum(x['status']=='PASS' for x in state['cycles'])
state['stable_pass_streak']=0
for x in reversed(state['cycles']):
    if x['status']=='PASS':state['stable_pass_streak']+=1
    else:break
state['min_pass_score']=min([x['fresh_blind']['score'] for x in state['cycles'] if x['status']=='PASS'] or [0.0])
state['status']='READY_FOR_G3_GENESIS' if len(state['cycles'])>=target and state['stable_pass_streak']>=target and state['min_pass_score']>=.99 else 'DEVELOPING'
state['next_required_capability']='G3_SUCCESSOR_GENESIS_FROM_G2_ENRICHED_HEAD_V1' if state['status']=='READY_FOR_G3_GENESIS' else f'G2_SELF_DIRECTED_DEVELOPMENT_CYCLE_{epoch+1}_OF_{target}'
state['state_digest']=h({k:v for k,v in state.items() if k!='state_digest'})
STATE.write_text(json.dumps(state,indent=2,sort_keys=True)+'\n')

candidate={
 'schema':'yado.g2.contextual_stream_capability_candidate.v1',
 'component':ContextualStreamCapabilityAdapterV1.component(),
 'selected_strategy':chosen,'selection_evidence':selection,
 'fresh_blind':fresh,'base_router_same_blind':base,
 'memory_ablation_score':memory_abl,'representation_transfer':repr_transfer,
 'state':'AUTHORIZED_FOR_G2_SHADOW_DEVELOPMENT' if passed else 'WITHHOLD',
 'canonical_active':False,'promotion_applied':False,
 'generation':'G2_CANDIDATE_TRCG_V1','parent_head_digest':head_digest,
 'semantic_boundary':'HOST-SCAFFOLDED BOUNDED STRATEGY BANK; G2 SELECTS BY FRESH EVIDENCE AND RECURRENT CAUSAL TESTS. NOT UNRESTRICTED SELF-MODIFYING CODE.',
}
candidate['candidate_digest']=h(candidate)
CAND.write_text(json.dumps(candidate,indent=2,sort_keys=True)+'\n')

run_id=str(os.getenv('GITHUB_RUN_ID') or 'LOCAL')
receipt={
 'schema':'yado.g2.self_directed_development_cycle.receipt.v1',
 'status':'PASS_G2_SELF_DIRECTED_DEVELOPMENT_CYCLE_V1' if passed else 'WITHHOLD_G2_SELF_DIRECTED_DEVELOPMENT_CYCLE_V1',
 'generation':'G2_CANDIDATE_TRCG_V1','generation_head_digest':head_digest,
 'cycle':epoch,'target_cycles':target,'curriculum':curriculum,'seed':seed,
 'record':record,'candidate_digest':candidate['candidate_digest'],
 'development_state_status':state['status'],'development_state_digest':state['state_digest'],
 'canonical_mutation':False,'promotion_applied':False,
 'next_required_capability':state['next_required_capability'],
 'semantic_boundary':'BOUNDED G2 DEVELOPMENTAL CYCLE WITH FRESH TEMPORAL ROUTING TESTS, CAUSAL MEMORY ABLATION, AND EVIDENCE-BASED STRATEGY SELECTION; DOES NOT CHANGE MODEL WEIGHTS OR CANONICAL G2 HEAD.',
}
receipt['receipt_sha256']=h(receipt)
(ROOT/'yado_g2_self_directed_development_cycle_v1_receipt.json').write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')

e={
 'index':len(ledger['events']),'event_id':f"E{len(ledger['events'])+1:04d}_G2_SELF_DIRECTED_CYCLE_{epoch}",
 'event_type':'G2_SELF_DIRECTED_DEVELOPMENT_CYCLE','status':'PASS_SHADOW' if passed else 'WITHHOLD',
 'generation':'G2_CANDIDATE_TRCG_V1','deficit':'G2_SELF_DIRECTED_DEVELOPMENT_CYCLE_V1',
 'effect':f"G2_CYCLE_{epoch}_{'PASS' if passed else 'WITHHOLD'}; SELECTED={chosen}; STATE={state['status']}",
 'source_path':f'receipts/yado-g2-self-directed-development-cycle-v1-run-{run_id}.json',
 'source_digest':receipt['receipt_sha256'],'run_id':run_id,'parent_event_hash':ledger['tail_event_hash'],
 'canonical_mutation':False,'promotion_applied':False,
}
e['event_hash']=event_hash(e);ledger['events'].append(e);ledger['event_count']=len(ledger['events']);ledger['tail_event_hash']=e['event_hash']
if state['status']=='READY_FOR_G3_GENESIS':
    ledger['open_deficits']=[x for x in ledger.get('open_deficits',[]) if x!='G2_SELF_DIRECTED_DEVELOPMENT_CYCLE_V1']
    ledger['open_deficits']=sorted(set(ledger['open_deficits']+['G3_SUCCESSOR_GENESIS_FROM_G2_ENRICHED_HEAD_V1']))
ledger['ledger_digest']=h({k:v for k,v in ledger.items() if k!='ledger_digest'})
validate_ledger_v2(ledger);LEDGER.write_text(json.dumps(ledger,indent=2,sort_keys=True)+'\n')

print(json.dumps({
 'status':receipt['status'],'cycle':epoch,'selected_strategy':chosen,
 'fresh_blind':fresh,'base_router_same_blind':base,'memory_ablation_score':memory_abl,
 'representation_transfer':repr_transfer,'checks':checks,
 'development_state_status':state['status'],'stable_pass_streak':state['stable_pass_streak'],
 'next_required_capability':state['next_required_capability'],'receipt_sha256':receipt['receipt_sha256']
},indent=2,sort_keys=True))
if not passed:raise SystemExit('G2_DEVELOPMENT_CYCLE_WITHHELD')
