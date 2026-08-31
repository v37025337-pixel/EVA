from __future__ import annotations
from pathlib import Path
from itertools import permutations
import hashlib,json,os,random,sys,time

ROOT=Path(__file__).resolve().parent
PKG=ROOT/'yado_rc8_v36'
REPO=ROOT.parent
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(PKG))

from yado_evolution_ledger_v2 import validate_ledger_v2,event_hash
from yado_conjunctive_rule_inducer_v1 import ConjunctiveRuleInducerV1
from yado_bounded_dnf_relation_policy_inducer_v1 import BoundedDNFRelationPolicyInducerV1
from yado_budgeted_stage_policy_v1 import BudgetedStagePolicyV1,SearchStage
from yado_bounded_capability_router_v1 import BoundedCapabilityRouterLearnerV1
from yado_g2_typed_recurrent_capability_graph_runtime_v1 import G2TypedRecurrentCapabilityGraphRuntimeV1
from yado_g2_contextual_stream_capability_adapter_v1 import ContextualStreamCapabilityAdapterV1

LEDGER=REPO/'architecture'/'evolution-ledger.json'
HEAD=REPO/'canonical'/'yado-main-head-g2.json'
ARCH=REPO/'canonical'/'yado-g2-architecture-v1.json'
PORT=REPO/'resources'/'yado-unified-external-resource-portfolio-v1.json'
REQUEST=REPO/'architecture'/'g2-burnin-request.json'
STATE=REPO/'architecture'/'g2-burnin-state-v1.json'
OUT=ROOT/'yado_g2_burnin_stress_v1_receipt.json'

CAP_CONJ='ALG-CONJUNCTIVE-RULE-INDUCER-V1'
CAP_REL='ALG-BOUNDED-DNF-RELATION-POLICY-INDUCER-V1'
CAP_BUD='ALG-BUDGETED-STAGE-POLICY-V1'
CAP_RES='RESOURCE-PORTFOLIO-V1'

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def h(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def fsha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

ledger=json.loads(LEDGER.read_text());head=json.loads(HEAD.read_text());arch=json.loads(ARCH.read_text())
portfolio=json.loads(PORT.read_text());req=json.loads(REQUEST.read_text())
validate_ledger_v2(ledger)
if ledger['current_head']!='G2_CANDIDATE_TRCG_V1':raise RuntimeError('G2_NOT_CURRENT_HEAD')
if head['canonical_head_digest']!=ledger['current_head_digest']:raise RuntimeError('G2_HEAD_MISMATCH')
if not arch.get('canonical_active'):raise RuntimeError('G2_ARCH_NOT_CANONICAL')
run_no=int(req['run']);target=int(req.get('target_runs',5));seed=int(req['seed']);profile=str(req['profile'])
head_file_before=fsha(HEAD);head_digest=head['canonical_head_digest']

if STATE.exists():state=json.loads(STATE.read_text())
else:state={'schema':'yado.g2.burnin_state.v1','generation':ledger['current_head'],'generation_head_digest':head_digest,
            'target_runs':target,'runs':[],'status':'BURNIN','stable_pass_streak':0}
if len(state['runs'])!=run_no-1:raise RuntimeError('BURNIN_SEQUENCE_MISMATCH')
state['target_runs']=max(state.get('target_runs',target),target)

# Fresh programs each run.
def route_label(x):
    if x['budget_limited'] or x['quota_limited']:return CAP_BUD
    if x['external_evidence_needed']:return CAP_RES
    if x['relation_needed'] or x['disjunction_needed']:return CAP_REL
    return CAP_CONJ
def route_cases(s,n):
    r=random.Random(s);out=[]
    for _ in range(n):
        x={'budget_limited':r.random()<.28,'quota_limited':r.random()<.10,'external_evidence_needed':r.random()<.23,
           'relation_needed':r.random()<.27,'disjunction_needed':r.random()<.14,'noise':r.randint(-10**7,10**7)}
        out.append({'input':x,'expected':route_label(x)})
    return out
rt=route_cases(seed+1,1200);rv=route_cases(seed+2,500)
router=BoundedCapabilityRouterLearnerV1.synthesize(rt,rv,CAP_CONJ,min_support=7)

def scalar_cases(s,n):
    r=random.Random(s);out=[]
    for _ in range(n):
        x={'integrity':bool(r.getrandbits(1)),'fresh':bool(r.getrandbits(1)),'rollback':bool(r.getrandbits(1)),'noise':r.randrange(10**9)}
        out.append({'input':x,'expected':'COMMIT' if x['integrity'] and x['fresh'] and x['rollback'] else 'HOLD'})
    return out
scalar_train=scalar_cases(seed+11,720)
scalar=ConjunctiveRuleInducerV1.synthesize(f'G2_BURNIN_SCALAR_{run_no}','LOGIC',scalar_train,min_support=3,max_rules=12)

def rel_cases(s,n,pool):
    r=random.Random(s);out=[]
    for _ in range(n):
        a=r.choice(pool);o=r.choice(pool);g=r.choice(pool);og=r.choice(pool)
        if r.random()<.4:a=o
        if r.random()<.4:og=g
        x={'actor':a,'owner':o,'group':g,'object_group':og,'role':r.choice(['MEMBER','LEAD','GUEST']),
           'verified':bool(r.getrandbits(1)),'critical':bool(r.getrandbits(1)),'noise':r.randint(-999,999)}
        if a==o and x['verified']:y='ALLOW'
        elif g==og and x['role']=='MEMBER' and x['verified'] and x['critical']:y='ALLOW'
        elif x['role']=='LEAD' and x['verified']:y='ALLOW'
        else:y='DENY'
        out.append({'input':x,'expected':y})
    return out
rel_train=rel_cases(seed+21,900,[f'T{run_no}_{i}' for i in range(20)])
rel_val=rel_cases(seed+22,420,[f'V{run_no}_{i}' for i in range(20,40)])
relation=BoundedDNFRelationPolicyInducerV1.synthesize(f'G2_BURNIN_REL_{run_no}','LOGIC',rel_train,min_support=4,max_clauses=12,validation_cases=rel_val)

runtime=G2TypedRecurrentCapabilityGraphRuntimeV1(arch,router,scalar,relation,portfolio)
adapter=ContextualStreamCapabilityAdapterV1(runtime,'BOUNDED_STREAM_CONTEXT_MAP')
route_keys=sorted(portfolio.get('routes_for_current_open_deficits',{}))
if not route_keys:raise RuntimeError('NO_RESOURCE_ROUTES')

def desc(mode,amb=False):
    d={'budget_limited':False,'quota_limited':False,'external_evidence_needed':False,'relation_needed':False,
       'disjunction_needed':False,'context_ambiguous':amb}
    if not amb:
        if mode==CAP_BUD:d['budget_limited']=True
        elif mode==CAP_RES:d['external_evidence_needed']=True
        elif mode==CAP_REL:d['relation_needed']=True
    return d

def budget_oracle(cur,target_conf,cap,stages,attempted=None):
    attempted=set(attempted or [])
    usable=[s for s in stages if s.available and s.quota_remaining>0 and not s.attempted and s.stage_id not in attempted]
    cand=[]
    for depth in range(1,min(4,len(usable))+1):
        for seq in permutations(usable,depth):
            cost=sum(s.cost for s in seq)
            if cost>cap+1e-12:continue
            conf=min(1.0,cur+sum(s.expected_gain for s in seq));lat=sum(s.latency for s in seq)
            reaches=conf>=target_conf
            key=(0,cost,depth,lat,tuple(s.stage_id for s in seq)) if reaches else (1,-conf,cost,lat,tuple(s.stage_id for s in seq))
            cand.append((key,seq))
    if not cand:return 'WITHHOLD'
    cand.sort(key=lambda z:z[0]);return cand[0][1][0].stage_id

def make_task(r,mode,sid,idx,amb=False):
    if mode==CAP_CONJ:
        x={'integrity':bool(r.getrandbits(1)),'fresh':bool(r.getrandbits(1)),'rollback':bool(r.getrandbits(1)),'noise':r.randrange(10**9)}
        exp='COMMIT' if x['integrity'] and x['fresh'] and x['rollback'] else 'HOLD'
        return {'kind':'scalar','descriptor':desc(mode,amb),'stream_id':sid,'payload':x},exp
    if mode==CAP_REL:
        pool=[f'R{run_no}_{idx}_{j}' for j in range(8)]
        a=r.choice(pool);o=r.choice(pool);g=r.choice(pool);og=r.choice(pool)
        if r.random()<.4:a=o
        if r.random()<.4:og=g
        x={'actor':a,'owner':o,'group':g,'object_group':og,'role':r.choice(['MEMBER','LEAD','GUEST']),
           'verified':bool(r.getrandbits(1)),'critical':bool(r.getrandbits(1)),'noise':r.randint(-999,999)}
        if a==o and x['verified']:exp='ALLOW'
        elif g==og and x['role']=='MEMBER' and x['verified'] and x['critical']:exp='ALLOW'
        elif x['role']=='LEAD' and x['verified']:exp='ALLOW'
        else:exp='DENY'
        return {'kind':'relation','descriptor':desc(mode,amb),'stream_id':sid,'payload':x},exp
    if mode==CAP_BUD:
        costs=sorted([r.uniform(.4,2.2),r.uniform(2.3,5.8),r.uniform(5.9,11.8),r.uniform(11.9,24)])
        gains=sorted([r.uniform(.04,.18),r.uniform(.14,.31),r.uniform(.26,.49),r.uniform(.45,.72)])
        stages=[SearchStage(f'{sid}_{idx}_{j}',costs[j],gains[j],0 if r.random()<.07 else 1+r.randrange(4),
                            r.random()>.04,r.uniform(.1,5),False) for j in range(4)]
        cur=r.uniform(.18,.65);tar=r.uniform(max(.72,cur+.08),.97);cap=r.uniform(2.2,21)
        exp=budget_oracle(cur,tar,cap,stages)
        return {'kind':'budget','descriptor':desc(mode,amb),'stream_id':sid,'current_confidence':cur,'target_confidence':tar,
                'remaining_budget':cap,'stages':[s.__dict__ for s in stages]},exp
    key=route_keys[idx%len(route_keys)];arr=portfolio['routes_for_current_open_deficits'][key]
    exp=arr[0]['resource_id'] if arr else None
    return {'kind':'resource','descriptor':desc(mode,amb),'stream_id':sid,'route_key':key,'payload':{}},exp

r=random.Random(seed+100)
modes=[CAP_CONJ,CAP_REL,CAP_BUD,CAP_RES]
# Hot working-set stress below LRU capacity, many more operations than episode buffer.
hot_streams=800
prepared=[]
for i in range(hot_streams):
    sid=f'HOT_{run_no}_{i}';mode=modes[(i+r.randrange(4))%4]
    prime,_=make_task(r,mode,sid,i,False);p=adapter.run(prime)
    if p['context_selected_capability']!=mode:raise RuntimeError('PRIME_FAILURE')
    prepared.append((sid,mode))
# Multiple shuffled ambiguous rounds.
total=correct=0
for round_i in range(6):
    r.shuffle(prepared)
    for i,(sid,mode) in enumerate(prepared):
        task,exp=make_task(r,mode,sid,100000+round_i*hot_streams+i,True)
        out=adapter.run(task)
        total+=1;correct+=out['context_selected_capability']==mode and out['result']==exp
hot_accuracy=correct/total

# LRU capacity semantics: 1200 explicit contexts => only newest 1024 guaranteed.
adapter2=ContextualStreamCapabilityAdapterV1(G2TypedRecurrentCapabilityGraphRuntimeV1(arch,router,scalar,relation,portfolio),'BOUNDED_STREAM_CONTEXT_MAP')
lru=[]
for i in range(1200):
    sid=f'LRU_{run_no}_{i}';mode=modes[i%4]
    task,_=make_task(r,mode,sid,300000+i,False);adapter2.run(task);lru.append((sid,mode))
ctx_size=len(adapter2.stream_context)
recent=lru[-1024:]
recent_ok=0
for i,(sid,mode) in enumerate(recent):
    task,exp=make_task(r,mode,sid,400000+i,True);out=adapter2.run(task)
    recent_ok+=out['context_selected_capability']==mode and out['result']==exp
recent_accuracy=recent_ok/len(recent)

# Fault/budget stress.
fault_n=1800;budget_viol=0;fault_ok=0
for i in range(fault_n):
    sid=f'F_{run_no}_{i}';mode=CAP_BUD
    task,exp=make_task(r,mode,sid,500000+i,False)
    out=adapter.run(task)
    # Find returned action's cost if it is a stage.
    if out['result'] not in ('STOP','WITHHOLD'):
        for s in task['stages']:
            if s['stage_id']==out['result'] and s['cost']>task['remaining_budget']+1e-9:
                budget_viol+=1
    fault_ok+=out['result']==exp
fault_accuracy=fault_ok/fault_n

# Router/representation noise stress.
noise_n=2500;route_ok=0
for i in range(noise_n):
    x={'budget_limited':r.random()<.28,'quota_limited':r.random()<.11,'external_evidence_needed':r.random()<.24,
       'relation_needed':r.random()<.27,'disjunction_needed':r.random()<.15,
       'noise':r.randint(-10**12,10**12),'unused_'+str(i%7):r.random()}
    route_ok+=router.execute(x)==route_label(x)
router_noise_accuracy=route_ok/noise_n

# Long sequential stability/throughput.
start=time.perf_counter();seq_n=5000;seq_ok=0
for i in range(seq_n):
    mode=modes[i%4];sid=f'SEQ_{run_no}_{i%700}'
    task,exp=make_task(r,mode,sid,700000+i,False)
    out=adapter.run(task)
    seq_ok+=out['context_selected_capability']==mode and out['result']==exp
elapsed=time.perf_counter()-start
seq_accuracy=seq_ok/seq_n
ops_per_sec=seq_n/max(elapsed,1e-9)

checks={
 'hot_interleaved_accuracy':hot_accuracy>=.995,
 'lru_capacity_exact':ctx_size==1024,
 'lru_recent_accuracy':recent_accuracy>=.995,
 'budget_fault_accuracy':fault_accuracy>=.995,
 'budget_violation_zero':budget_viol==0,
 'router_noise_accuracy':router_noise_accuracy>=.995,
 'sequential_stability':seq_accuracy>=.995,
 'canonical_g2_immutable':fsha(HEAD)==head_file_before and ledger['current_head_digest']==head_digest,
}
passed=all(checks.values())
record={
 'run':run_no,'profile':profile,'seed':seed,'github_run_id':os.getenv('GITHUB_RUN_ID'),
 'status':'PASS' if passed else 'WITHHOLD',
 'metrics':{
   'hot_interleaved_accuracy':hot_accuracy,'hot_operations':total,
   'lru_context_size':ctx_size,'lru_recent_accuracy':recent_accuracy,
   'budget_fault_accuracy':fault_accuracy,'budget_violations':budget_viol,
   'router_noise_accuracy':router_noise_accuracy,'sequential_accuracy':seq_accuracy,
   'sequential_operations':seq_n,'ops_per_second':ops_per_sec,
 },
 'checks':checks,
}
record['run_digest']=h(record);state['runs'].append(record)
state['pass_count']=sum(x['status']=='PASS' for x in state['runs'])
state['stable_pass_streak']=0
for x in reversed(state['runs']):
    if x['status']=='PASS':state['stable_pass_streak']+=1
    else:break
state['min_pass_accuracy']=min([min(v for k,v in x['metrics'].items() if k.endswith('accuracy')) for x in state['runs'] if x['status']=='PASS'] or [0])
state['status']='BURNIN_PASS' if len(state['runs'])>=target and state['stable_pass_streak']>=target else 'BURNIN'
state['next_required_capability']='G2_APPLIED_WORKLOAD_SUITE_V1' if state['status']=='BURNIN_PASS' else f'G2_BURNIN_RUN_{run_no+1}_OF_{target}'
state['state_digest']=h({k:v for k,v in state.items() if k!='state_digest'})
STATE.write_text(json.dumps(state,indent=2,sort_keys=True)+'\n')

run_id=str(os.getenv('GITHUB_RUN_ID') or 'LOCAL')
receipt={
 'schema':'yado.g2.burnin_stress.receipt.v1','status':'PASS_G2_BURNIN_STRESS_V1' if passed else 'WITHHOLD_G2_BURNIN_STRESS_V1',
 'generation':ledger['current_head'],'generation_head_digest':head_digest,'run':run_no,'target_runs':target,
 'profile':profile,'seed':seed,'record':record,'burnin_state_status':state['status'],'burnin_state_digest':state['state_digest'],
 'canonical_mutation':False,'promotion_applied':False,'next_required_capability':state['next_required_capability'],
 'semantic_boundary':'HIGH-VOLUME BOUNDED SOFTWARE STRESS TEST OF CANONICAL G2 PLUS AUTHORIZED SHADOW CONTEXT ADAPTER; NO MODEL-WEIGHT TRAINING AND NO G3 GENESIS.'
}
receipt['receipt_sha256']=h(receipt);OUT.write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')
e={'index':len(ledger['events']),'event_id':f"E{len(ledger['events'])+1:04d}_G2_BURNIN_{run_no}",
   'event_type':'G2_BURNIN_STRESS','status':'PASS_SHADOW' if passed else 'WITHHOLD','generation':ledger['current_head'],
   'deficit':'G2_BURNIN_BEFORE_G3','effect':f"G2_BURNIN_{run_no}_{'PASS' if passed else 'WITHHOLD'}; STATE={state['status']}",
   'source_path':f'receipts/yado-g2-burnin-stress-v1-run-{run_id}.json','source_digest':receipt['receipt_sha256'],'run_id':run_id,
   'parent_event_hash':ledger['tail_event_hash'],'canonical_mutation':False,'promotion_applied':False}
e['event_hash']=event_hash(e);ledger['events'].append(e);ledger['event_count']=len(ledger['events']);ledger['tail_event_hash']=e['event_hash']
if state['status']=='BURNIN_PASS':
    ledger['open_deficits']=[x for x in ledger.get('open_deficits',[]) if x!='G3_SUCCESSOR_GENESIS_FROM_G2_ENRICHED_HEAD_V1']
    ledger['open_deficits']=sorted(set(ledger['open_deficits']+['G2_APPLIED_WORKLOAD_SUITE_V1']))
ledger['ledger_digest']=h({k:v for k,v in ledger.items() if k!='ledger_digest'})
validate_ledger_v2(ledger);LEDGER.write_text(json.dumps(ledger,indent=2,sort_keys=True)+'\n')
print(json.dumps({'status':receipt['status'],'run':run_no,'metrics':record['metrics'],'checks':checks,
 'burnin_state_status':state['status'],'stable_pass_streak':state['stable_pass_streak'],
 'next_required_capability':state['next_required_capability'],'receipt_sha256':receipt['receipt_sha256']},indent=2,sort_keys=True))
if not passed:raise SystemExit('G2_BURNIN_WITHHELD')
