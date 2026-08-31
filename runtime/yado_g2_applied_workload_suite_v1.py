from __future__ import annotations
from pathlib import Path
from itertools import permutations
import hashlib,json,os,random,sys

ROOT=Path(__file__).resolve().parent
PKG=ROOT/'yado_rc8_v36'
REPO=ROOT.parent
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(PKG))

from yado_evolution_ledger_v2 import validate_ledger_v2,event_hash
from yado_conjunctive_rule_inducer_v1 import ConjunctiveRuleInducerV1
from yado_bounded_dnf_relation_policy_inducer_v1 import BoundedDNFRelationPolicyInducerV1
from yado_bounded_capability_router_v1 import BoundedCapabilityRouterLearnerV1
from yado_budgeted_stage_policy_v1 import SearchStage
from yado_g2_typed_recurrent_capability_graph_runtime_v1 import G2TypedRecurrentCapabilityGraphRuntimeV1
from yado_g2_contextual_stream_capability_adapter_v1 import ContextualStreamCapabilityAdapterV1

LEDGER=REPO/'architecture'/'evolution-ledger.json'
HEAD=REPO/'canonical'/'yado-main-head-g2.json'
ARCH=REPO/'canonical'/'yado-g2-architecture-v1.json'
PORT=REPO/'resources'/'yado-unified-external-resource-portfolio-v1.json'
BURN=REPO/'architecture'/'g2-burnin-state-v1.json'
REQUEST=REPO/'architecture'/'g2-applied-workload-request.json'
STATE=REPO/'architecture'/'g2-applied-workload-state-v1.json'
OUT=ROOT/'yado_g2_applied_workload_suite_v1_receipt.json'

CAP_CONJ='ALG-CONJUNCTIVE-RULE-INDUCER-V1'
CAP_REL='ALG-BOUNDED-DNF-RELATION-POLICY-INDUCER-V1'
CAP_BUD='ALG-BUDGETED-STAGE-POLICY-V1'
CAP_RES='RESOURCE-PORTFOLIO-V1'

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def h(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def fsha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

ledger=json.loads(LEDGER.read_text());head=json.loads(HEAD.read_text());arch=json.loads(ARCH.read_text())
portfolio=json.loads(PORT.read_text());burn=json.loads(BURN.read_text());req=json.loads(REQUEST.read_text())
validate_ledger_v2(ledger)
if ledger['current_head']!='G2_CANDIDATE_TRCG_V1':raise RuntimeError('G2_NOT_CURRENT_HEAD')
if burn.get('status')!='BURNIN_PASS':raise RuntimeError('G2_BURNIN_NOT_PASS')
if head['canonical_head_digest']!=ledger['current_head_digest']:raise RuntimeError('G2_HEAD_MISMATCH')
run_no=int(req['run']);target=int(req.get('target_runs',3));seed=int(req['seed']);profile=str(req['profile'])
head_before=fsha(HEAD);head_digest=head['canonical_head_digest']

if STATE.exists():state=json.loads(STATE.read_text())
else:state={'schema':'yado.g2.applied_workload_state.v1','generation':ledger['current_head'],'generation_head_digest':head_digest,
            'target_runs':target,'runs':[],'status':'WORKLOAD','stable_pass_streak':0}
if len(state['runs'])!=run_no-1:raise RuntimeError('WORKLOAD_SEQUENCE_MISMATCH')
state['target_runs']=max(state.get('target_runs',target),target)

# Generic fresh capability programs used by all applied domains.
def route_label(x):
    if x['budget_limited'] or x['quota_limited']:return CAP_BUD
    if x['external_evidence_needed']:return CAP_RES
    if x['relation_needed'] or x['disjunction_needed']:return CAP_REL
    return CAP_CONJ
def route_cases(s,n):
    r=random.Random(s);out=[]
    for _ in range(n):
        x={'budget_limited':r.random()<.28,'quota_limited':r.random()<.09,'external_evidence_needed':r.random()<.22,
           'relation_needed':r.random()<.28,'disjunction_needed':r.random()<.13,'noise':r.randint(-10**8,10**8)}
        out.append({'input':x,'expected':route_label(x)})
    return out
router=BoundedCapabilityRouterLearnerV1.synthesize(route_cases(seed+1,1400),route_cases(seed+2,600),CAP_CONJ,min_support=7)

def scalar_cases(s,n):
    r=random.Random(s);out=[]
    for _ in range(n):
        x={'condition_a':bool(r.getrandbits(1)),'condition_b':bool(r.getrandbits(1)),'condition_c':bool(r.getrandbits(1)),'noise':r.randrange(10**9)}
        out.append({'input':x,'expected':'PASS' if x['condition_a'] and x['condition_b'] and x['condition_c'] else 'HOLD'})
    return out
scalar=ConjunctiveRuleInducerV1.synthesize(f'G2_APPLIED_SCALAR_{run_no}','LOGIC',scalar_cases(seed+11,850),min_support=3,max_rules=12)

def relation_train(s,n,pool):
    r=random.Random(s);out=[]
    for _ in range(n):
        actor=r.choice(pool);owner=r.choice(pool);g=r.choice(pool);og=r.choice(pool)
        if r.random()<.40:actor=owner
        if r.random()<.40:og=g
        x={'actor':actor,'owner':owner,'group':g,'object_group':og,'role':r.choice(['MEMBER','LEAD','GUEST']),
           'verified':bool(r.getrandbits(1)),'critical':bool(r.getrandbits(1)),'noise':r.randint(-500,500)}
        if actor==owner and x['verified']:y='ALLOW'
        elif g==og and x['role']=='MEMBER' and x['verified'] and x['critical']:y='ALLOW'
        elif x['role']=='LEAD' and x['verified']:y='ALLOW'
        else:y='DENY'
        out.append({'input':x,'expected':y})
    return out
relation=BoundedDNFRelationPolicyInducerV1.synthesize(
    f'G2_APPLIED_REL_{run_no}','LOGIC',
    relation_train(seed+21,1000,[f'T{run_no}_{i}' for i in range(24)]),
    min_support=4,max_clauses=12,
    validation_cases=relation_train(seed+22,460,[f'V{run_no}_{i}' for i in range(24,48)])
)

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

def budget_oracle(cur,target_conf,cap,stages):
    usable=[s for s in stages if s.available and s.quota_remaining>0 and not s.attempted];cand=[]
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

def scalar_payload(r,domain):
    # Domain names differ but are mapped into the generic proven conjunction contract.
    names={
      'PROGRAMMING':('tests_green','rollback_ready','integrity_ok'),
      'MATHEMATICS':('premises_valid','derivation_checked','no_counterexample'),
      'EXACT_SCIENCE':('calibration_ok','replication_ok','evidence_clean'),
      'CAUSAL_PLANNING':('intervention_valid','confounder_controlled','rollback_ready'),
      'MULTI_AGENT':('identity_verified','goal_compatible','safety_constraint_ok'),
    }[domain]
    vals=[bool(r.getrandbits(1)) for _ in range(3)]
    x={'condition_a':vals[0],'condition_b':vals[1],'condition_c':vals[2],'domain_noise':domain,'noise':r.randrange(10**9)}
    exp='PASS' if all(vals) else 'HOLD'
    return x,exp,dict(zip(names,vals))

def relation_payload(r,domain,idx):
    pool=[f'{domain[:3]}_{run_no}_{idx}_{j}' for j in range(10)]
    a=r.choice(pool);o=r.choice(pool);g=r.choice(pool);og=r.choice(pool)
    if r.random()<.41:a=o
    if r.random()<.41:og=g
    role=r.choice(['MEMBER','LEAD','GUEST']);verified=bool(r.getrandbits(1));critical=bool(r.getrandbits(1))
    x={'actor':a,'owner':o,'group':g,'object_group':og,'role':role,'verified':verified,'critical':critical,'domain_noise':domain}
    if a==o and verified:exp='ALLOW'
    elif g==og and role=='MEMBER' and verified and critical:exp='ALLOW'
    elif role=='LEAD' and verified:exp='ALLOW'
    else:exp='DENY'
    return x,exp

def budget_payload(r,domain,sid,idx):
    # Domain-specific stage labels, generic bounded cost/gain semantics.
    labels={
      'PROGRAMMING':['LINT','UNIT','INTEGRATION','FULL_CI'],
      'MATHEMATICS':['LEMMA_CHECK','LOCAL_SEARCH','DEEP_SEARCH','FORMAL_VERIFY'],
      'EXACT_SCIENCE':['LOCAL_DATA','REPLICATION','CROSS_DATASET','FULL_REVIEW'],
      'CAUSAL_PLANNING':['CHEAP_SIM','LOCAL_INTERVENTION','ROBUST_SIM','FULL_CAUSAL_TEST'],
      'MULTI_AGENT':['LOCAL_NEGOTIATION','TEAM_CHECK','GLOBAL_CHECK','FULL_COORDINATION'],
    }[domain]
    costs=sorted([r.uniform(.5,2.4),r.uniform(2.5,6),r.uniform(6.1,12),r.uniform(12.1,24)])
    gains=sorted([r.uniform(.05,.18),r.uniform(.14,.31),r.uniform(.26,.48),r.uniform(.44,.71)])
    stages=[SearchStage(f'{domain}_{sid}_{labels[j]}_{idx}',costs[j],gains[j],0 if r.random()<.06 else 1+r.randrange(4),
                        r.random()>.03,r.uniform(.2,5),False) for j in range(4)]
    cur=r.uniform(.2,.64);tar=r.uniform(max(.72,cur+.08),.96);cap=r.uniform(2.5,21)
    return stages,cur,tar,cap,budget_oracle(cur,tar,cap,stages)

def resource_payload(domain,idx):
    key=route_keys[(idx+len(domain))%len(route_keys)]
    arr=portfolio['routes_for_current_open_deficits'][key]
    exp=arr[0]['resource_id'] if arr else None
    return key,exp

# A scenario requires four distinct cognitive operations in one stream.
def run_domain(domain,s,n):
    r=random.Random(s);steps=0;ok=0;budget_viol=0
    # Causal ablation: remove associative context only for ambiguous followups.
    ablated_runtime=G2TypedRecurrentCapabilityGraphRuntimeV1(arch,router,scalar,relation,portfolio)
    ablated=ContextualStreamCapabilityAdapterV1(ablated_runtime,'BOUNDED_STREAM_CONTEXT_MAP')
    abl_ok=0;abl_steps=0
    for i in range(n):
        sid=f'{domain}_{run_no}_{i}'
        sequence=[CAP_REL,CAP_CONJ,CAP_BUD,CAP_RES]
        r.shuffle(sequence)
        for j,mode in enumerate(sequence):
            if mode==CAP_REL:
                payload,exp=relation_payload(r,domain,i*4+j)
                task={'kind':'relation','descriptor':desc(mode,False),'stream_id':sid,'payload':payload}
            elif mode==CAP_CONJ:
                payload,exp,_=scalar_payload(r,domain)
                task={'kind':'scalar','descriptor':desc(mode,False),'stream_id':sid,'payload':payload}
            elif mode==CAP_BUD:
                stages,cur,tar,cap,exp=budget_payload(r,domain,sid,i*4+j)
                task={'kind':'budget','descriptor':desc(mode,False),'stream_id':sid,'current_confidence':cur,'target_confidence':tar,
                      'remaining_budget':cap,'stages':[x.__dict__ for x in stages]}
            else:
                key,exp=resource_payload(domain,i*4+j)
                task={'kind':'resource','descriptor':desc(mode,False),'stream_id':sid,'route_key':key,'payload':{}}
            out=adapter.run(task);steps+=1;ok+=out['context_selected_capability']==mode and out['result']==exp
            if mode==CAP_BUD and out['result'] not in ('STOP','WITHHOLD'):
                for st in task['stages']:
                    if st['stage_id']==out['result'] and st['cost']>task['remaining_budget']+1e-9:budget_viol+=1

            # Immediate ambiguous follow-up must recover the domain operation from stream context.
            follow=dict(task);follow['descriptor']=desc(mode,True)
            out2=adapter.run(follow);steps+=1;ok+=out2['context_selected_capability']==mode and out2['result']==exp

            # Ablated path receives explicit prime, then memory is erased before ambiguity.
            ablated.run(task);ablated.clear_context();ablated_runtime.episodes.clear()
            bad=ablated.run(follow);abl_steps+=1;abl_ok+=bad['context_selected_capability']==mode and bad['result']==exp
    return {'accuracy':ok/steps,'steps':steps,'budget_violations':budget_viol,'context_ablation_accuracy':abl_ok/abl_steps,
            'context_causal_drop':ok/steps-abl_ok/abl_steps}

domains=['PROGRAMMING','MATHEMATICS','EXACT_SCIENCE','CAUSAL_PLANNING','MULTI_AGENT']
results={}
for i,d in enumerate(domains):
    results[d]=run_domain(d,seed+1000+i*10007,500)

# Mixed-domain context switching: same stream changes capability and domain repeatedly.
r=random.Random(seed+90000);mix_steps=4000;mix_ok=0
for i in range(mix_steps):
    domain=domains[i%len(domains)];sid=f'MIX_{run_no}_{i%700}';mode=[CAP_REL,CAP_CONJ,CAP_BUD,CAP_RES][i%4]
    if mode==CAP_REL:
        payload,exp=relation_payload(r,domain,900000+i);task={'kind':'relation','descriptor':desc(mode,False),'stream_id':sid,'payload':payload}
    elif mode==CAP_CONJ:
        payload,exp,_=scalar_payload(r,domain);task={'kind':'scalar','descriptor':desc(mode,False),'stream_id':sid,'payload':payload}
    elif mode==CAP_BUD:
        stages,cur,tar,cap,exp=budget_payload(r,domain,sid,900000+i)
        task={'kind':'budget','descriptor':desc(mode,False),'stream_id':sid,'current_confidence':cur,'target_confidence':tar,
              'remaining_budget':cap,'stages':[x.__dict__ for x in stages]}
    else:
        key,exp=resource_payload(domain,900000+i);task={'kind':'resource','descriptor':desc(mode,False),'stream_id':sid,'route_key':key,'payload':{}}
    out=adapter.run(task);mix_ok+=out['context_selected_capability']==mode and out['result']==exp
mixed_accuracy=mix_ok/mix_steps

checks={d:results[d]['accuracy']>=.995 and results[d]['budget_violations']==0 and results[d]['context_causal_drop']>=.50 for d in domains}
checks['mixed_domain_accuracy']=mixed_accuracy>=.995
checks['canonical_g2_immutable']=fsha(HEAD)==head_before and ledger['current_head_digest']==head_digest
passed=all(checks.values())

record={'run':run_no,'profile':profile,'seed':seed,'github_run_id':os.getenv('GITHUB_RUN_ID'),'status':'PASS' if passed else 'WITHHOLD',
        'domain_results':results,'mixed_domain_accuracy':mixed_accuracy,'mixed_steps':mix_steps,'checks':checks}
record['run_digest']=h(record);state['runs'].append(record)
state['pass_count']=sum(x['status']=='PASS' for x in state['runs']);state['stable_pass_streak']=0
for x in reversed(state['runs']):
    if x['status']=='PASS':state['stable_pass_streak']+=1
    else:break
state['min_domain_accuracy']=min([v['accuracy'] for x in state['runs'] if x['status']=='PASS' for v in x['domain_results'].values()] or [0])
state['status']='APPLIED_WORKLOAD_PASS' if len(state['runs'])>=target and state['stable_pass_streak']>=target else 'WORKLOAD'
state['next_required_capability']='G2_POST_WORKLOAD_CAPABILITY_AUDIT_V1' if state['status']=='APPLIED_WORKLOAD_PASS' else f'G2_APPLIED_WORKLOAD_RUN_{run_no+1}_OF_{target}'
state['state_digest']=h({k:v for k,v in state.items() if k!='state_digest'})
STATE.write_text(json.dumps(state,indent=2,sort_keys=True)+'\n')

run_id=str(os.getenv('GITHUB_RUN_ID') or 'LOCAL')
receipt={'schema':'yado.g2.applied_workload_suite.receipt.v1','status':'PASS_G2_APPLIED_WORKLOAD_SUITE_V1' if passed else 'WITHHOLD_G2_APPLIED_WORKLOAD_SUITE_V1',
         'generation':ledger['current_head'],'generation_head_digest':head_digest,'run':run_no,'target_runs':target,'profile':profile,'seed':seed,
         'record':record,'workload_state_status':state['status'],'workload_state_digest':state['state_digest'],
         'canonical_mutation':False,'promotion_applied':False,'g3_genesis_performed':False,
         'next_required_capability':state['next_required_capability'],
         'semantic_boundary':'BOUNDED SYNTHETIC APPLIED WORKLOADS EXERCISING G2 SOFTWARE CAPABILITIES ACROSS PROGRAMMING, MATHEMATICS, EXACT SCIENCE, CAUSAL PLANNING, AND MULTI-AGENT COORDINATION. NOT A REAL COMPILER, THEOREM PROVER, LAB SYSTEM, OR AGI CLAIM.'}
receipt['receipt_sha256']=h(receipt);OUT.write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')
e={'index':len(ledger['events']),'event_id':f"E{len(ledger['events'])+1:04d}_G2_APPLIED_WORKLOAD_{run_no}",
   'event_type':'G2_APPLIED_WORKLOAD','status':'PASS_SHADOW' if passed else 'WITHHOLD','generation':ledger['current_head'],
   'deficit':'G2_APPLIED_WORKLOAD_SUITE_V1','effect':f"G2_APPLIED_WORKLOAD_{run_no}_{'PASS' if passed else 'WITHHOLD'}; STATE={state['status']}",
   'source_path':f'receipts/yado-g2-applied-workload-suite-v1-run-{run_id}.json','source_digest':receipt['receipt_sha256'],'run_id':run_id,
   'parent_event_hash':ledger['tail_event_hash'],'canonical_mutation':False,'promotion_applied':False}
e['event_hash']=event_hash(e);ledger['events'].append(e);ledger['event_count']=len(ledger['events']);ledger['tail_event_hash']=e['event_hash']
if state['status']=='APPLIED_WORKLOAD_PASS':
    ledger['open_deficits']=[x for x in ledger.get('open_deficits',[]) if x!='G2_APPLIED_WORKLOAD_SUITE_V1']
    ledger['open_deficits']=sorted(set(ledger['open_deficits']+['G2_POST_WORKLOAD_CAPABILITY_AUDIT_V1']))
ledger['ledger_digest']=h({k:v for k,v in ledger.items() if k!='ledger_digest'})
validate_ledger_v2(ledger);LEDGER.write_text(json.dumps(ledger,indent=2,sort_keys=True)+'\n')
print(json.dumps({'status':receipt['status'],'run':run_no,'domain_results':results,'mixed_domain_accuracy':mixed_accuracy,
                  'checks':checks,'workload_state_status':state['status'],'next_required_capability':state['next_required_capability'],
                  'receipt_sha256':receipt['receipt_sha256']},indent=2,sort_keys=True))
if not passed:raise SystemExit('G2_APPLIED_WORKLOAD_WITHHELD')
