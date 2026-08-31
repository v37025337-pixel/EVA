from __future__ import annotations
from pathlib import Path
from collections import Counter
import hashlib,json,os,random,sys

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
PKG=ROOT/'yado_rc8_v36'
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(PKG))

from yado_evolution_ledger_v2 import validate_ledger_v2,event_hash
from yado_conjunctive_rule_inducer_v1 import ConjunctiveRuleInducerV1
from yado_bounded_dnf_relation_policy_inducer_v1 import BoundedDNFRelationPolicyInducerV1
from yado_bounded_capability_router_v1 import BoundedCapabilityRouterLearnerV1
from yado_g2_typed_recurrent_capability_graph_runtime_v1 import G2TypedRecurrentCapabilityGraphRuntimeV1
from yado_g2_contextual_stream_capability_adapter_v1 import ContextualStreamCapabilityAdapterV1

HEAD=REPO/'canonical'/'yado-main-head-g2.json'
LEDGER=REPO/'architecture'/'evolution-ledger.json'
ARCH=REPO/'canonical'/'yado-g2-architecture-v1.json'
PORT=REPO/'resources'/'yado-unified-external-resource-portfolio-v1.json'
META=REPO/'candidates'/'g2-development'/'contextual-stream-capability-adapter-v1.json'
SRC=REPO/'runtime'/'yado_g2_contextual_stream_capability_adapter_v1.py'
OUT=ROOT/'yado_context_adapter_dependency_fresh_admission_v1_receipt.json'

CAP_CONJ='ALG-CONJUNCTIVE-RULE-INDUCER-V1'
CAP_REL='ALG-BOUNDED-DNF-RELATION-POLICY-INDUCER-V1'
CAP_BUD='ALG-BUDGETED-STAGE-POLICY-V1'
CAP_RES='RESOURCE-PORTFOLIO-V1'
CAPS=[CAP_CONJ,CAP_REL,CAP_BUD,CAP_RES]

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def h(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def fsha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8'))

head=load(HEAD);ledger=load(LEDGER);arch=load(ARCH);portfolio=load(PORT);meta=load(META)
validate_ledger_v2(ledger)
if ledger.get('open_deficits')!=['SHADOW_CONTEXT_ADAPTER_DEPENDENCE']:raise RuntimeError('UNEXPECTED_FRONTIER')
if meta.get('canonical_active') is not False:raise RuntimeError('ADAPTER_ALREADY_CANONICAL')
if meta.get('state')!='AUTHORIZED_FOR_G2_SHADOW_DEVELOPMENT':raise RuntimeError('ADAPTER_NOT_AUTHORIZED_SHADOW')
if ledger.get('current_head_digest')!=head.get('canonical_head_digest'):raise RuntimeError('HEAD_LEDGER_MISMATCH')

# Fresh support programs; seeds and stream IDs are distinct from historical adapter evidence.
def route_label(x):
    if x['budget_limited'] or x['quota_limited']:return CAP_BUD
    if x['external_evidence_needed']:return CAP_RES
    if x['relation_needed'] or x['disjunction_needed']:return CAP_REL
    return CAP_CONJ

def route_cases(seed,n):
    r=random.Random(seed);out=[]
    for _ in range(n):
        x={'budget_limited':r.random()<.25,'quota_limited':r.random()<.08,
           'external_evidence_needed':r.random()<.22,'relation_needed':r.random()<.25,
           'disjunction_needed':r.random()<.12,'noise':r.randrange(10**9)}
        out.append({'input':x,'expected':route_label(x)})
    return out

router=BoundedCapabilityRouterLearnerV1.synthesize(route_cases(9011,1200),route_cases(9012,500),CAP_CONJ,min_support=7)

def scalar_cases(seed,n):
    r=random.Random(seed);out=[]
    for _ in range(n):
        x={'condition_a':bool(r.getrandbits(1)),'condition_b':bool(r.getrandbits(1)),
           'condition_c':bool(r.getrandbits(1)),'noise':r.randrange(10**9)}
        out.append({'input':x,'expected':'PASS' if x['condition_a'] and x['condition_b'] and x['condition_c'] else 'HOLD'})
    return out
scalar=ConjunctiveRuleInducerV1.synthesize('CTX_FRESH_SCALAR','LOGIC',scalar_cases(9021,700),min_support=3,max_rules=12)

def relation_cases(seed,n):
    r=random.Random(seed);pool=[f'CTX_R_{i}' for i in range(32)];out=[]
    for _ in range(n):
        a=r.choice(pool);o=r.choice(pool);g=r.choice(pool);og=r.choice(pool)
        if r.random()<.4:a=o
        if r.random()<.4:og=g
        role=r.choice(['MEMBER','LEAD','GUEST']);verified=bool(r.getrandbits(1));critical=bool(r.getrandbits(1))
        x={'actor':a,'owner':o,'group':g,'object_group':og,'role':role,'verified':verified,'critical':critical}
        if a==o and verified:y='ALLOW'
        elif g==og and role=='MEMBER' and verified and critical:y='ALLOW'
        elif role=='LEAD' and verified:y='ALLOW'
        else:y='DENY'
        out.append({'input':x,'expected':y})
    return out
relation=BoundedDNFRelationPolicyInducerV1.synthesize('CTX_FRESH_REL','LOGIC',relation_cases(9031,900),min_support=4,max_clauses=12,validation_cases=relation_cases(9032,400))

route_keys=sorted(portfolio.get('routes_for_current_open_deficits',{}))
if not route_keys:raise RuntimeError('NO_RESOURCE_ROUTES')

def explicit_desc(cap):
    d={'budget_limited':False,'quota_limited':False,'external_evidence_needed':False,
       'relation_needed':False,'disjunction_needed':False,'context_ambiguous':False}
    if cap==CAP_BUD:d['budget_limited']=True
    elif cap==CAP_RES:d['external_evidence_needed']=True
    elif cap==CAP_REL:d['relation_needed']=True
    return d

def ambiguous_desc():
    return {'budget_limited':False,'quota_limited':False,'external_evidence_needed':False,
            'relation_needed':False,'disjunction_needed':False,'context_ambiguous':True}

def task_for(cap,sid,idx,amb=False):
    desc=ambiguous_desc() if amb else explicit_desc(cap)
    if cap==CAP_CONJ:
        return {'kind':'scalar','stream_id':sid,'descriptor':desc,
                'payload':{'condition_a':True,'condition_b':True,'condition_c':True,'noise':idx}}
    if cap==CAP_REL:
        return {'kind':'relation','stream_id':sid,'descriptor':desc,
                'payload':{'actor':'A','owner':'A','group':'G1','object_group':'G2','role':'GUEST','verified':True,'critical':False}}
    if cap==CAP_RES:
        return {'kind':'resource','stream_id':sid,'descriptor':desc,'route_key':route_keys[idx%len(route_keys)],'payload':{}}
    return {'kind':'budget','stream_id':sid,'descriptor':desc,'current_confidence':0.45,'target_confidence':0.78,
            'remaining_budget':10.0,'stages':[
              {'stage_id':f'{sid}_S1','cost':1.0,'expected_gain':0.10,'quota_remaining':2,'available':True,'latency':0.2,'attempted':False},
              {'stage_id':f'{sid}_S2','cost':3.0,'expected_gain':0.24,'quota_remaining':2,'available':True,'latency':0.5,'attempted':False},
              {'stage_id':f'{sid}_S3','cost':7.0,'expected_gain':0.42,'quota_remaining':1,'available':True,'latency':1.0,'attempted':False},
            ]}

def make_runtime():
    return G2TypedRecurrentCapabilityGraphRuntimeV1(arch,router,scalar,relation,portfolio)

# Interleaved fresh streams: prime all, then query all ambiguously in reverse order.
N=320
caps=[CAPS[(i*3+1)%4] for i in range(N)]
streams=[f'CTX_FRESH_{i:04d}_{h([i,9051])[:8]}' for i in range(N)]

rt_on=make_runtime();ad_on=ContextualStreamCapabilityAdapterV1(rt_on,'BOUNDED_STREAM_CONTEXT_MAP')
for i,(sid,cap) in enumerate(zip(streams,caps)):
    ad_on.run(task_for(cap,sid,i,False))
on=[]
for i in reversed(range(N)):
    out=ad_on.run(task_for(caps[i],streams[i],i,True))
    on.append(out.get('context_selected_capability')==caps[i])
adapter_score=sum(on)/len(on)

rt_off=make_runtime()
off=[]
for i in reversed(range(N)):
    t=task_for(caps[i],streams[i],i,True)
    try:selected=rt_off.router.execute(t['descriptor'])
    except Exception:selected=None
    off.append(selected==caps[i])
base_score=sum(off)/len(off)

rt_abl=make_runtime();ad_abl=ContextualStreamCapabilityAdapterV1(rt_abl,'BOUNDED_STREAM_CONTEXT_MAP')
abl=[]
for i,(sid,cap) in enumerate(zip(streams,caps)):
    ad_abl.run(task_for(cap,sid,i,False))
    ad_abl.clear_context()
    rt_abl.episodes.clear()
    out=ad_abl.run(task_for(cap,sid,i,True))
    abl.append(out.get('context_selected_capability')==cap)
ablation_score=sum(abl)/len(abl)

# Per-capability coverage and bounded memory behavior.
per_cap={}
for cap in CAPS:
    idx=[i for i,c in enumerate(caps) if c==cap]
    vals=[]
    rt=make_runtime();ad=ContextualStreamCapabilityAdapterV1(rt,'BOUNDED_STREAM_CONTEXT_MAP')
    for i in idx:
        ad.run(task_for(cap,streams[i],i,False))
    for i in reversed(idx):
        vals.append(ad.run(task_for(cap,streams[i],i,True)).get('context_selected_capability')==cap)
    per_cap[cap]=sum(vals)/len(vals) if vals else 0.0

rt_stress=make_runtime();ad_stress=ContextualStreamCapabilityAdapterV1(rt_stress,'BOUNDED_STREAM_CONTEXT_MAP')
for i in range(1100):
    cap=CAPS[i%4];sid=f'LRU_STRESS_{i:04d}'
    ad_stress.run(task_for(cap,sid,i,False))
lru_size=len(ad_stress.stream_context)
oldest_evicted='LRU_STRESS_0000' not in ad_stress.stream_context
newest_retained='LRU_STRESS_1099' in ad_stress.stream_context

checks={
 'fresh_adapter_score':adapter_score>=0.99,
 'base_router_low_on_context_ambiguity':base_score<=0.40,
 'memory_ablation_low':ablation_score<=0.40,
 'causal_context_drop':adapter_score-ablation_score>=0.55,
 'all_capabilities_fresh_pass':all(v>=0.99 for v in per_cap.values()),
 'lru_bound_respected':lru_size<=ContextualStreamCapabilityAdapterV1.MAX_STREAM_CONTEXTS,
 'oldest_evicted':oldest_evicted,
 'newest_retained':newest_retained,
 'component_digest_matches_registered_shadow':ContextualStreamCapabilityAdapterV1.component().get('component_digest')==meta.get('component',{}).get('component_digest'),
 'canonical_head_immutable':ledger.get('current_head_digest')==head.get('canonical_head_digest'),
}
passed=all(checks.values())
next_cap='SHADOW_CONTEXT_ADAPTER_CANONICAL_INTEGRATION_V1' if passed else 'SHADOW_CONTEXT_ADAPTER_SELF_EVOLUTION_V2'
run_id=str(os.getenv('GITHUB_RUN_ID') or 'LOCAL')
receipt={
 'schema':'yado.g2.context_adapter_dependency_fresh_admission.v1',
 'status':'PASS_CONTEXT_ADAPTER_DEPENDENCY_FRESH_ADMISSION_V1' if passed else 'WITHHOLD_CONTEXT_ADAPTER_DEPENDENCY_FRESH_ADMISSION_V1',
 'adapter_candidate_digest':meta.get('candidate_digest'),
 'adapter_source_sha256':fsha(SRC),
 'fresh_stream_count':N,
 'adapter_score':adapter_score,'base_score':base_score,'memory_ablation_score':ablation_score,
 'causal_drop':adapter_score-ablation_score,'per_capability':per_cap,
 'lru':{'size':lru_size,'max':ContextualStreamCapabilityAdapterV1.MAX_STREAM_CONTEXTS,
        'oldest_evicted':oldest_evicted,'newest_retained':newest_retained},
 'checks':checks,'canonical_mutation':False,'promotion_applied':False,'g3_genesis_performed':False,
 'next_required_capability':next_cap,
 'semantic_boundary':'FRESH CAUSAL ADMISSION OF BOUNDED STREAM-CONTEXT CAPABILITY ROUTING. DOES NOT ESTABLISH GENERAL MEMORY, SUBJECTIVE CONTINUITY, OR CONSCIOUSNESS.'
}
receipt['receipt_sha256']=h(receipt);OUT.write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')

e={'index':len(ledger['events']),'event_id':f"E{len(ledger['events'])+1:04d}_G2_CONTEXT_ADAPTER_DEPENDENCY_FRESH_ADMISSION",
 'event_type':'CONTEXT_ADAPTER_CAUSAL_FRESH_ADMISSION','status':'PASS_SHADOW' if passed else 'WITHHOLD',
 'generation':ledger['current_head'],'deficit':'SHADOW_CONTEXT_ADAPTER_DEPENDENCE',
 'effect':f"ADAPTER={adapter_score:.6f}; BASE={base_score:.6f}; ABLATION={ablation_score:.6f}; NEXT={next_cap}",
 'source_path':f'receipts/yado-context-adapter-dependency-fresh-admission-v1-run-{run_id}.json',
 'source_digest':receipt['receipt_sha256'],'run_id':run_id,'parent_event_hash':ledger['tail_event_hash'],
 'canonical_mutation':False,'promotion_applied':False}
e['event_hash']=event_hash(e);ledger['events'].append(e);ledger['event_count']=len(ledger['events']);ledger['tail_event_hash']=e['event_hash']
ledger['open_deficits']=[next_cap];ledger['ledger_digest']=h({k:v for k,v in ledger.items() if k!='ledger_digest'})
validate_ledger_v2(ledger);LEDGER.write_text(json.dumps(ledger,indent=2,sort_keys=True)+'\n')
print(json.dumps({'status':receipt['status'],'adapter_score':adapter_score,'base_score':base_score,
 'memory_ablation_score':ablation_score,'causal_drop':adapter_score-ablation_score,
 'per_capability':per_cap,'checks':checks,'next_required_capability':next_cap,'receipt_sha256':receipt['receipt_sha256']},indent=2,sort_keys=True))
if not passed:raise SystemExit('CONTEXT_ADAPTER_DEPENDENCY_FRESH_ADMISSION_WITHHELD')
