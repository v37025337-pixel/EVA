from __future__ import annotations
from pathlib import Path
from itertools import permutations
import copy,hashlib,json,os,random,sys

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
sys.path.insert(0,str(ROOT))

from yado_evolution_ledger_v2 import validate_ledger_v2,event_hash
from yado_conjunctive_rule_inducer_v1 import ConjunctiveRuleInducerV1,program_acc as conjunctive_acc
from yado_bounded_dnf_relation_policy_inducer_v1 import BoundedDNFRelationPolicyInducerV1,program_acc as relation_acc
from yado_budgeted_stage_policy_v1 import BudgetedStagePolicyV1,SearchStage
from yado_neutral_evidence_profile_selector_v1 import NeutralEvidenceProfileSelectorV1,EvidenceCandidate

LEDGER=REPO/'architecture'/'evolution-ledger.json'
HEAD=REPO/'canonical'/'yado-main-head-g1-s2.json'
REGISTRY=REPO/'architecture'/'g1-developmental-capability-registry-v1.json'
PORTFOLIO=REPO/'resources'/'yado-unified-external-resource-portfolio-v1.json'
REQUEST=REPO/'architecture'/'g1-training-request.json'
STATE=REPO/'architecture'/'g1-training-state-v1.json'
POST=REPO/'receipts'/'yado-g1-post-resource-assisted-development-regression-admission-v1-run-33355904404.json'

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def h(o):return hashlib.sha256(canon(o).encode()).hexdigest()

ledger=json.loads(LEDGER.read_text());head=json.loads(HEAD.read_text())
registry=json.loads(REGISTRY.read_text());portfolio=json.loads(PORTFOLIO.read_text())
request=json.loads(REQUEST.read_text());post=json.loads(POST.read_text())
validate_ledger_v2(ledger)

if ledger['current_head']!='G1_CANDIDATE_S2':raise RuntimeError('G1_NOT_CURRENT_HEAD')
if head.get('canonical_head_digest')!=ledger.get('current_head_digest'):raise RuntimeError('HEAD_DIGEST_MISMATCH')
if registry.get('state')!='ACTIVE_FOR_G1_DEVELOPMENTAL_META_SELECTION':raise RuntimeError('G1_REGISTRY_NOT_ACTIVE')
if post.get('status')!='PASS_G1_POST_RESOURCE_ASSISTED_DEVELOPMENT_REGRESSION_AND_ADMISSION_V1':raise RuntimeError('POST_ADMISSION_NOT_PASS')

epoch=int(request['epoch']);seed=int(request['seed']);curriculum=str(request['curriculum'])
target_rounds=int(request.get('target_rounds',5))
if epoch<1 or epoch>target_rounds:raise RuntimeError('BAD_EPOCH')

if STATE.exists():
    state=json.loads(STATE.read_text())
else:
    state={
      'schema':'yado.g1.multiround_training_state.v1',
      'generation':ledger['current_head'],
      'generation_head_digest':ledger['current_head_digest'],
      'target_rounds':target_rounds,
      'rounds':[],
      'status':'TRAINING',
      'new_capabilities':[],
    }
if state['generation_head_digest']!=ledger['current_head_digest']:raise RuntimeError('TRAINING_STATE_HEAD_DRIFT')
if len(state['rounds'])!=epoch-1:raise RuntimeError(f'ROUND_SEQUENCE_MISMATCH expected={epoch-1} actual={len(state["rounds"])}')

# ----- 1. Learn a capability router from examples -----
CAP_CONJ='ALG-CONJUNCTIVE-RULE-INDUCER-V1'
CAP_REL='ALG-BOUNDED-DNF-RELATION-POLICY-INDUCER-V1'
CAP_BUD='ALG-BUDGETED-STAGE-POLICY-V1'
CAP_RES='RESOURCE-PORTFOLIO-V1'

def router_label(x):
    if x['budget_limited'] or x['quota_limited']:return CAP_BUD
    if x['external_evidence_needed']:return CAP_RES
    if x['relation_needed'] or x['disjunction_needed']:return CAP_REL
    return CAP_CONJ

def router_cases(s,n):
    r=random.Random(s);out=[]
    for _ in range(n):
        x={
          'budget_limited':bool(r.getrandbits(1)),
          'quota_limited':bool(r.getrandbits(1)) if r.random()<.35 else False,
          'external_evidence_needed':bool(r.getrandbits(1)) if r.random()<.45 else False,
          'relation_needed':bool(r.getrandbits(1)) if r.random()<.45 else False,
          'disjunction_needed':bool(r.getrandbits(1)) if r.random()<.30 else False,
          'uncertainty_high':bool(r.getrandbits(1)),
          'opaque_noise':r.randint(-100,100),
        }
        out.append({'input':x,'expected':router_label(x)})
    return out
rt=router_cases(seed+11,900);rv=router_cases(seed+12,420);rb=router_cases(seed+13,900)
router=BoundedDNFRelationPolicyInducerV1.synthesize(
    f'G1_ROUTER_EPOCH_{epoch}','INTELLIGENCE',rt,min_support=5,max_clauses=12,validation_cases=rv
)
router_metrics={
  'validation':relation_acc(router,rv),
  'fresh_blind':relation_acc(router,rb),
  'ablation':relation_acc(router,rb,ablated=True),
  'restore':relation_acc(router,rb),
  'clause_count':len(router.clauses),
}

# ----- 2. Fresh scalar rule induction -----
def scalar_cases(s,n):
    r=random.Random(s);out=[]
    for _ in range(n):
        x={
          'evidence_clean':bool(r.getrandbits(1)),
          'rollback_ready':bool(r.getrandbits(1)),
          'transfer_ok':bool(r.getrandbits(1)),
          'noise':r.randint(0,10000),
        }
        y='COMMIT' if x['evidence_clean'] and x['rollback_ready'] and x['transfer_ok'] else 'WITHHOLD'
        out.append({'input':x,'expected':y})
    return out
ct=scalar_cases(seed+21,520);cv=scalar_cases(seed+22,260);cb=scalar_cases(seed+23,780)
cp=ConjunctiveRuleInducerV1.synthesize(f'G1_SCALAR_EPOCH_{epoch}','LOGIC',ct,min_support=3,max_rules=12)
conj_metrics={'validation':conjunctive_acc(cp,cv),'fresh_blind':conjunctive_acc(cp,cb),'ablation':conjunctive_acc(cp,cb,ablated=True)}

# ----- 3. Fresh relational transfer with disjoint identities -----
def relation_cases(s,n,pool):
    r=random.Random(s);out=[]
    roles=['MEMBER','LEAD','GUEST'];levels=['LOW','MEDIUM','HIGH']
    for _ in range(n):
        owner=r.choice(pool);actor=r.choice(pool);team=r.choice(pool);rteam=r.choice(pool)
        if r.random()<.42:actor=owner
        if r.random()<.42:rteam=team
        x={'actor':actor,'owner':owner,'actor_team':team,'resource_team':rteam,
           'role':r.choice(roles),'verified':bool(r.getrandbits(1)),'level':r.choice(levels),'noise':r.randint(-50,50)}
        if x['actor']==x['owner'] and x['verified']:y='ALLOW'
        elif x['actor_team']==x['resource_team'] and x['role']=='MEMBER' and x['verified'] and x['level']=='HIGH':y='ALLOW'
        elif x['role']=='LEAD' and x['verified']:y='ALLOW'
        else:y='DENY'
        out.append({'input':x,'expected':y})
    return out
rel_t=relation_cases(seed+31,760,[f'T{epoch}_{i}' for i in range(12)])
rel_v=relation_cases(seed+32,360,[f'V{epoch}_{i}' for i in range(12,24)])
rel_b=relation_cases(seed+33,920,[f'B{epoch}_{i}' for i in range(24,48)])
rp=BoundedDNFRelationPolicyInducerV1.synthesize(
    f'G1_REL_EPOCH_{epoch}','LOGIC',rel_t,min_support=4,max_clauses=12,validation_cases=rel_v
)
def relation_ablated(p,cases):
    ok=0
    for e in cases:
        out=p.default_output
        for cl in p.clauses:
            if any(a.op.startswith('FIELD_') for a in cl.atoms):continue
            if cl.match(e['input']):out=cl.output;break
        ok+=out==e['expected']
    return ok/len(cases)
rel_metrics={
 'validation':relation_acc(rp,rel_v),'fresh_blind':relation_acc(rp,rel_b),
 'relation_ablation':relation_ablated(rp,rel_b),'restore':relation_acc(rp,rel_b),
 'clause_count':len(rp.clauses),
}

# ----- 4. Budgeted planning under fresh cost distributions -----
def budget_oracle(current,target,cap,stages):
    if current>=target:return 'STOP'
    usable=[s for s in stages if s.available and s.quota_remaining>0 and not s.attempted]
    cand=[]
    for depth in range(1,min(4,len(usable))+1):
        for seq in permutations(usable,depth):
            cost=sum(s.cost for s in seq)
            if cost>cap+1e-12:continue
            conf=min(1.0,current+sum(s.expected_gain for s in seq))
            lat=sum(s.latency for s in seq)
            reaches=conf>=target
            key=(0,cost,depth,lat,tuple(s.stage_id for s in seq)) if reaches else (1,-conf,cost,lat,tuple(s.stage_id for s in seq))
            cand.append((key,seq))
    if not cand:return 'WITHHOLD'
    cand.sort(key=lambda z:z[0]);return cand[0][1][0].stage_id

r=random.Random(seed+41);n=620;bok=babl=bscale=bviol=0
for i in range(n):
    costs=sorted([r.uniform(.4,2.2),r.uniform(2.3,5.5),r.uniform(5.6,11.5),r.uniform(11.6,24)])
    gains=sorted([r.uniform(.04,.17),r.uniform(.13,.30),r.uniform(.25,.48),r.uniform(.45,.72)])
    stages=[SearchStage(f'E{epoch}_{i}_{j}',costs[j],gains[j],0 if r.random()<.08 else r.randint(1,4),r.random()>.04,r.uniform(.2,5),False) for j in range(4)]
    current=r.uniform(.2,.66);target=r.uniform(max(.72,current+.08),.96);cap=r.uniform(2.3,20)
    exp=budget_oracle(current,target,cap,stages)
    p=BudgetedStagePolicyV1.plan(current,target,cap,stages);bok+=p.action==exp
    if p.feasible and p.total_cost>cap+1e-9:bviol+=1
    bad=BudgetedStagePolicyV1.plan(current,target,cap,stages,ignore_budget=True);babl+=bad.action==exp
    factor=3.7+epoch
    scaled=[SearchStage(s.stage_id,s.cost*factor,s.expected_gain,s.quota_remaining,s.available,s.latency,s.attempted) for s in stages]
    bscale+=BudgetedStagePolicyV1.plan(current,target,cap*factor,scaled).action==exp
budget_metrics={
 'fresh_exact':bok/n,'budget_ablation_exact':babl/n,'budget_violation_rate':bviol/n,'cost_scale_invariance':bscale/n
}

# ----- 5. Architecture-neutral selection on opaque candidate tokens -----
def oracle_select(xs,cp=.05,rp=.25,nb=.03):
    scored=[(x.evidence-cp*x.complexity-rp*x.risk+nb*x.novelty,x.token) for x in xs]
    scored.sort(key=lambda z:(-z[0],z[1]));return scored[0][1]
r=random.Random(seed+51);m=800;sel_ok=0;perm_ok=0
for i in range(m):
    count=r.randint(4,12)
    xs=[EvidenceCandidate(
      token=f'opaque_{epoch}_{i}_{j}_{r.randrange(10**9)}',
      evidence=r.random(),complexity=r.random(),risk=r.random(),novelty=r.random()
    ) for j in range(count)]
    exp=oracle_select(xs)
    got=NeutralEvidenceProfileSelectorV1.select(xs)['selected_token'];sel_ok+=got==exp
    ys=list(reversed(xs))
    perm_ok+=NeutralEvidenceProfileSelectorV1.select(ys)['selected_token']==exp
selector_metrics={'fresh_exact':sel_ok/m,'permutation_invariance':perm_ok/m,'architecture_names_hardcoded':False}

# ----- 6. Resource routing invariants -----
routes=portfolio.get('routes_for_current_open_deficits',{})
route_rows=[x for arr in routes.values() for x in arr]
portfolio_metrics={
 'resource_count':portfolio.get('resource_count',0),
 'excluded_selected':sum(str(x.get('policy','')).startswith('EXCLUDED') for x in route_rows),
 'all_routes_local_first':all((not arr) or arr[0].get('kind')=='local_evidence' for arr in routes.values()),
 'digest':portfolio.get('portfolio_digest'),
}

checks={
 'router':router_metrics['validation']>=.99 and router_metrics['fresh_blind']>=.99 and router_metrics['fresh_blind']-router_metrics['ablation']>=.05,
 'conjunctive':conj_metrics['validation']>=.99 and conj_metrics['fresh_blind']>=.99 and conj_metrics['fresh_blind']-conj_metrics['ablation']>=.05,
 'relation':rel_metrics['validation']>=.99 and rel_metrics['fresh_blind']>=.99 and rel_metrics['fresh_blind']-rel_metrics['relation_ablation']>=.08,
 'budget':budget_metrics['fresh_exact']>=.99 and budget_metrics['budget_violation_rate']==0 and budget_metrics['cost_scale_invariance']>=.99 and budget_metrics['fresh_exact']-budget_metrics['budget_ablation_exact']>=.10,
 'neutral_selector':selector_metrics['fresh_exact']>=.999 and selector_metrics['permutation_invariance']>=.999,
 'portfolio':portfolio_metrics['resource_count']>=70 and portfolio_metrics['excluded_selected']==0 and portfolio_metrics['all_routes_local_first'],
 'canonical_head_unchanged':ledger['current_head_digest']==head['canonical_head_digest'],
}
passed=all(checks.values())

round_score=min(
 router_metrics['fresh_blind'],conj_metrics['fresh_blind'],rel_metrics['fresh_blind'],
 budget_metrics['fresh_exact'],selector_metrics['fresh_exact']
)
round_record={
 'epoch':epoch,'curriculum':curriculum,'seed':seed,'github_run_id':os.getenv('GITHUB_RUN_ID'),
 'status':'PASS' if passed else 'WITHHOLD','round_score':round_score,
 'checks':checks,'router_metrics':router_metrics,'conjunctive_metrics':conj_metrics,
 'relation_metrics':rel_metrics,'budget_metrics':budget_metrics,'selector_metrics':selector_metrics,
 'portfolio_metrics':portfolio_metrics,
}
round_record['round_digest']=h(round_record)
state['rounds'].append(round_record)
state['new_capabilities']=sorted(set(state.get('new_capabilities',[])+['ALG-NEUTRAL-EVIDENCE-PROFILE-SELECTOR-V1']))
state['pass_count']=sum(x['status']=='PASS' for x in state['rounds'])
state['stable_pass_streak']=0
for x in reversed(state['rounds']):
    if x['status']=='PASS':state['stable_pass_streak']+=1
    else:break
state['min_round_score']=min(x['round_score'] for x in state['rounds'])
state['status']='READY_FOR_G2_GENESIS' if len(state['rounds'])>=target_rounds and state['pass_count']==target_rounds and state['min_round_score']>=.99 else 'TRAINING'
state['next_required_capability']='G2_SUCCESSOR_GENESIS_FROM_G1_ENRICHED_HEAD_V1' if state['status']=='READY_FOR_G2_GENESIS' else f'G1_TRAINING_ROUND_{epoch+1}_OF_{target_rounds}'
state['state_digest']=h({k:v for k,v in state.items() if k!='state_digest'})
STATE.write_text(json.dumps(state,indent=2,sort_keys=True)+'\n')

run_id=str(os.getenv('GITHUB_RUN_ID') or 'LOCAL')
receipt={
 'schema':'yado.g1.multiround_training.receipt.v1',
 'status':'PASS_G1_DEVELOPMENT_TRAINING_ROUND' if passed else 'WITHHOLD_G1_DEVELOPMENT_TRAINING_ROUND',
 'generation':ledger['current_head'],'generation_head_digest':ledger['current_head_digest'],
 'epoch':epoch,'target_rounds':target_rounds,'curriculum':curriculum,'seed':seed,
 'round_record':round_record,'training_state_digest':state['state_digest'],
 'training_state_status':state['status'],
 'neutral_selector_component':NeutralEvidenceProfileSelectorV1.component(),
 'canonical_mutation':False,'promotion_applied':False,
 'next_required_capability':state['next_required_capability'],
 'semantic_boundary':'BOUNDED G1 DEVELOPMENTAL TRAINING/VALIDATION ON FRESH SYNTHETIC TASKS; UPDATES DEVELOPMENTAL STATE AND COUNTEREXAMPLE EXPERIENCE, NOT MODEL WEIGHTS OR CANONICAL G1 HEAD',
}
receipt['receipt_sha256']=h(receipt)
(ROOT/'yado_g1_multiround_training_v1_receipt.json').write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')

e={
 'index':len(ledger['events']),
 'event_id':f"E{len(ledger['events'])+1:04d}_G1_TRAINING_ROUND_{epoch}",
 'event_type':'G1_DEVELOPMENTAL_TRAINING_ROUND',
 'status':'PASS_SHADOW' if passed else 'WITHHOLD',
 'generation':ledger['current_head'],
 'deficit':'G2_SUCCESSOR_GENESIS_FROM_G1_ENRICHED_HEAD_V1',
 'effect':f"G1_TRAINING_ROUND_{epoch}_{'PASS' if passed else 'WITHHOLD'}; STATE={state['status']}",
 'source_path':f'receipts/yado-g1-multiround-training-v1-run-{run_id}.json',
 'source_digest':receipt['receipt_sha256'],'run_id':run_id,
 'parent_event_hash':ledger['tail_event_hash'],'canonical_mutation':False,'promotion_applied':False,
}
e['event_hash']=event_hash(e);ledger['events'].append(e);ledger['event_count']=len(ledger['events']);ledger['tail_event_hash']=e['event_hash']
if state['status']=='READY_FOR_G2_GENESIS':
    ledger['open_deficits']=sorted(set(ledger.get('open_deficits',[])+['G2_SUCCESSOR_GENESIS_FROM_G1_ENRICHED_HEAD_V1']))
ledger['ledger_digest']=h({k:v for k,v in ledger.items() if k!='ledger_digest'})
validate_ledger_v2(ledger);LEDGER.write_text(json.dumps(ledger,indent=2,sort_keys=True)+'\n')

print(json.dumps({
 'status':receipt['status'],'epoch':epoch,'curriculum':curriculum,'round_score':round_score,
 'checks':checks,'training_state_status':state['status'],'pass_count':state['pass_count'],
 'stable_pass_streak':state['stable_pass_streak'],'min_round_score':state['min_round_score'],
 'next_required_capability':state['next_required_capability'],'receipt_sha256':receipt['receipt_sha256']
},indent=2,sort_keys=True))
if not passed:raise SystemExit('G1_TRAINING_ROUND_WITHHELD')
