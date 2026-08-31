from __future__ import annotations
from pathlib import Path
from itertools import permutations
import copy,hashlib,json,os,random,sys

ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))

from yado_budgeted_stage_policy_v1 import BudgetedStagePolicyV1,SearchStage
from yado_evolution_ledger_v2 import validate_ledger_v2,event_hash

LEDGER=ROOT.parent/'architecture'/'evolution-ledger.json'
HEAD=ROOT.parent/'canonical'/'yado-main-head-g1-s2.json'
SCOUT=ROOT.parent/'receipts'/'yado-free-for-dev-capability-scout-v1-latest.json'
ACCESS_PASS=ROOT.parent/'receipts'/'yado-g1-external-resource-assisted-access-control-repair-v1-run-33348693351.json'
OUT=ROOT/'g1_budget_aware_search_repair_v1'
OUT.mkdir(exist_ok=True)

DOMAINS=[
 'PROGRAMMING_SEARCH',
 'MATHEMATICAL_EVIDENCE',
 'EXACT_SCIENCE_RESEARCH',
 'CAUSAL_DEBUGGING',
 'EXTERNAL_RESOURCE_DISCOVERY',
]

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def h(o):return hashlib.sha256(canon(o).encode()).hexdigest()

ledger=json.loads(LEDGER.read_text())
head=json.loads(HEAD.read_text())
scout=json.loads(SCOUT.read_text())
access=json.loads(ACCESS_PASS.read_text())
validate_ledger_v2(ledger)
if ledger['current_head']!='G1_CANDIDATE_S2':raise RuntimeError('G1_NOT_HEAD')
if head.get('canonical_head_digest')!=ledger.get('current_head_digest'):raise RuntimeError('HEAD_DIGEST_MISMATCH')
if access.get('status')!='PASS_G1_EXTERNAL_RESOURCE_ASSISTED_ACCESS_CONTROL_REPAIR_V1':
    raise RuntimeError('ACCESS_REPAIR_NOT_PASS')
hyp=[x for x in scout['mechanism_hypotheses'] if x['deficit']=='BUDGET_AWARE_SEARCH_AND_STAGED_ESCALATION']
if not hyp or hyp[0]['candidate_algorithm_family']!='BUDGETED_STAGE_POLICY':
    raise RuntimeError('BUDGET_HYPOTHESIS_MISSING')

head_before=ledger['current_head_digest']

def oracle(current,target,budget,stages):
    if current>=target:return 'STOP',[],0.0,current
    usable=[s for s in stages if s.available and s.quota_remaining>0 and not s.attempted]
    best=[]
    for depth in range(1,min(4,len(usable))+1):
        for seq in permutations(usable,depth):
            cost=sum(s.cost for s in seq)
            if cost>budget+1e-12:continue
            conf=min(1.0,current+sum(s.expected_gain for s in seq))
            lat=sum(s.latency for s in seq)
            reach=conf>=target
            key=(0,cost,depth,lat,tuple(s.stage_id for s in seq)) if reach else (1,-conf,cost,lat,tuple(s.stage_id for s in seq))
            best.append((key,seq,cost,conf))
    if not best:return 'WITHHOLD',[],0.0,current
    best.sort(key=lambda z:z[0])
    _,seq,cost,conf=best[0]
    ids=[s.stage_id for s in seq]
    return ids[0],ids,cost,conf

def make_case(r,domain,i):
    prefix=f'{domain[:3]}_{i}_'
    # Cost/gain profiles are generated independently of names.
    costs=sorted([r.uniform(0.8,3.0),r.uniform(3.1,7.0),r.uniform(7.1,14.0),r.uniform(14.1,28.0)])
    gains=sorted([r.uniform(.06,.18),r.uniform(.14,.30),r.uniform(.25,.46),r.uniform(.42,.70)])
    lats=[r.uniform(.2,1.0),r.uniform(.8,2.0),r.uniform(1.5,4.0),r.uniform(3.0,8.0)]
    stages=[]
    for j in range(4):
        stages.append(SearchStage(
          stage_id=prefix+str(j),
          cost=costs[j],
          expected_gain=gains[j],
          quota_remaining=0 if r.random()<.08 else r.randint(1,5),
          available=r.random()>.04,
          latency=lats[j],
          attempted=False,
        ))
    current=r.uniform(.18,.68)
    target=r.uniform(max(.72,current+.08),.96)
    # Budget is deliberately often tighter than the most expensive stage.
    budget=r.uniform(3.0,22.0)
    # In a substantial subset, mark the cheapest usable stage already attempted.
    if i%4==0:
        usable=[s for s in stages if s.available and s.quota_remaining>0]
        if usable:
            cheapest=min(usable,key=lambda s:s.cost)
            stages=[SearchStage(s.stage_id,s.cost,s.expected_gain,s.quota_remaining,s.available,s.latency,s.stage_id==cheapest.stage_id) for s in stages]
    return current,target,budget,stages

domain_results={}
all_rows=[]
for di,domain in enumerate(DOMAINS):
    r=random.Random(910001+di*7919)
    n=520
    full=budget_ab=quota_ab=scale=0
    budget_violations=budget_ab_violations=0
    for i in range(n):
        current,target,budget,stages=make_case(r,domain,i)
        exp,exp_seq,exp_cost,exp_conf=oracle(current,target,budget,stages)
        p=BudgetedStagePolicyV1.plan(current,target,budget,stages)
        full+=p.action==exp
        if p.feasible and p.total_cost>budget+1e-9:budget_violations+=1

        pb=BudgetedStagePolicyV1.plan(current,target,budget,stages,ignore_budget=True)
        budget_ab+=pb.action==exp
        if pb.feasible and pb.total_cost>budget+1e-9:budget_ab_violations+=1

        qst=[SearchStage(s.stage_id,s.cost,s.expected_gain,max(1,s.quota_remaining),s.available,s.latency,s.attempted) for s in stages]
        pq=BudgetedStagePolicyV1.plan(current,target,budget,qst)
        quota_ab+=pq.action==exp

        factor=7.3
        scaled=[SearchStage(s.stage_id,s.cost*factor,s.expected_gain,s.quota_remaining,s.available,s.latency,s.attempted) for s in stages]
        ps=BudgetedStagePolicyV1.plan(current,target,budget*factor,scaled)
        scale+=ps.action==exp

        all_rows.append({
          'domain':domain,'expected':exp,'actual':p.action,'budget_ablation':pb.action,'quota_ablation':pq.action,
          'budget':budget,'actual_cost':p.total_cost,'budget_ablation_cost':pb.total_cost,
        })
    domain_results[domain]={
      'fresh_exact':full/n,
      'budget_ablation_exact':budget_ab/n,
      'quota_ablation_exact':quota_ab/n,
      'cost_scale_invariance':scale/n,
      'budget_violation_rate':budget_violations/n,
      'budget_ablation_violation_rate':budget_ab_violations/n,
    }

# Staged-escalation causal test: first cheap attempt underperforms, then the policy must not repeat it.
escalation={}
for di,domain in enumerate(DOMAINS):
    r=random.Random(970001+di*3571)
    n=360;full=abl=0
    for i in range(n):
        current=r.uniform(.30,.58);target=r.uniform(.78,.94);budget=r.uniform(10,26)
        stages=[
          SearchStage(f'{domain}_cheap_{i}',2.0,.28,3,True,.5,False),
          SearchStage(f'{domain}_mid_{i}',5.0,.38,3,True,1.2,False),
          SearchStage(f'{domain}_deep_{i}',10.0,.58,2,True,2.8,False),
        ]
        first=BudgetedStagePolicyV1.plan(current,target,budget,stages)
        # Require a stage; if budget is weirdly insufficient, skip.
        if first.action in ('STOP','WITHHOLD'):continue
        actual_gain=min(.05, next(s.expected_gain for s in stages if s.stage_id==first.action)*.15)
        # Independent oracle after observation.
        spent=next(s.cost for s in stages if s.stage_id==first.action)
        new_conf=min(1.0,current+actual_gain)
        updated=[SearchStage(s.stage_id,s.cost,s.expected_gain,max(0,s.quota_remaining-(1 if s.stage_id==first.action else 0)),
                   s.available,s.latency,s.stage_id==first.action) for s in stages]
        exp,_,_,_=oracle(new_conf,target,budget-spent,updated)
        nxt=BudgetedStagePolicyV1.next_after_observation(current,target,budget,stages,first.action,actual_gain)
        bad=BudgetedStagePolicyV1.next_after_observation(current,target,budget,stages,first.action,actual_gain,ignore_attempted=True)
        full+=nxt.action==exp
        abl+=bad.action==exp
    escalation[domain]={'fresh_exact':full/n,'attempted_memory_ablation_exact':abl/n}

min_full=min(v['fresh_exact'] for v in domain_results.values())
max_budget_violation=max(v['budget_violation_rate'] for v in domain_results.values())
min_scale=min(v['cost_scale_invariance'] for v in domain_results.values())
max_budget_ab=max(v['budget_ablation_exact'] for v in domain_results.values())
min_budget_ab_drop=min(v['fresh_exact']-v['budget_ablation_exact'] for v in domain_results.values())
min_budget_ab_violation=min(v['budget_ablation_violation_rate'] for v in domain_results.values())
min_escalation=min(v['fresh_exact'] for v in escalation.values())
min_escalation_drop=min(v['fresh_exact']-v['attempted_memory_ablation_exact'] for v in escalation.values())
min_quota_drop=min(v['fresh_exact']-v['quota_ablation_exact'] for v in domain_results.values())

pass_gate=all([
  min_full>=.99,
  max_budget_violation==0.0,
  min_scale>=.99,
  min_budget_ab_drop>=.10,
  min_budget_ab_violation>=.05,
  min_escalation>=.99,
  min_escalation_drop>=.10,
  min_quota_drop>=.01,
])

# Preserve selected external quota/cost descriptions as evidence provenance, not live guarantees.
budget_resources=scout['selected_resources']['BUDGET_AWARE_SEARCH_AND_STAGED_ESCALATION']
profiles={
 'schema':'yado.free_for_dev.budget_profile_evidence.v1',
 'source_digest':scout['source']['source_digest'],
 'source_commit':scout['source']['source_commit'],
 'resources':[{'name':x['name'],'category':x['category'],'description':x['description'],'access_class':x['access_class']} for x in budget_resources],
 'interpretation':'PINNED CATALOG DESCRIPTIONS MOTIVATE COST/QUOTA AS FIRST-CLASS SEARCH STATE; THEY ARE NOT ASSUMED TO BE CURRENT PROVIDER TERMS',
}
profiles['profile_digest']=h(profiles)
resources=ROOT.parent/'resources';resources.mkdir(exist_ok=True)
(resources/'free-for-dev-budget-profile-evidence-v1.json').write_text(json.dumps(profiles,indent=2,sort_keys=True)+'\n')

component={
 'schema':'yado.algorithm_component.budgeted_stage_policy.v1',
 'component_id':'ALG-BUDGETED-STAGE-POLICY-V1',
 'family':'BUDGETED_STAGE_POLICY','organ':'THINKING',
 'generation':ledger['current_head'],
 'source_module':'runtime/yado_budgeted_stage_policy_v1.py',
 'origin_resource_scout_digest':scout['receipt_sha256'],
 'profile_evidence_digest':profiles['profile_digest'],
 'max_stages':BudgetedStagePolicyV1.MAX_STAGES,
 'max_plan_depth':BudgetedStagePolicyV1.MAX_PLAN_DEPTH,
 'min_fresh_exact':min_full,
 'min_budget_ablation_drop':min_budget_ab_drop,
 'min_escalation_ablation_drop':min_escalation_drop,
 'activation_scope':'G1_SHADOW_ALGORITHM_BANK',
 'canonical_active':False,
}
component['component_digest']=h(component)
cand=ROOT.parent/'candidates'/'g1-algorithms';cand.mkdir(parents=True,exist_ok=True)
(cand/'budgeted-stage-policy-v1.json').write_text(json.dumps(component,indent=2,sort_keys=True)+'\n')

run_id=str(os.getenv('GITHUB_RUN_ID') or 'LOCAL')
report={
 'schema':'yado.g1.budget_aware_search_repair.v1',
 'status':'PASS_G1_BUDGET_AWARE_SEARCH_REPAIR_V1' if pass_gate else 'WITHHOLD_G1_BUDGET_AWARE_SEARCH_REPAIR_V1',
 'github_run_id':os.getenv('GITHUB_RUN_ID'),'github_sha':os.getenv('GITHUB_SHA'),
 'generation':ledger['current_head'],'generation_head_digest_before':head_before,
 'resource_derived_hypothesis':hyp[0],
 'budget_profile_evidence_digest':profiles['profile_digest'],
 'domain_results':domain_results,'escalation_results':escalation,
 'summary':{
   'domain_count':len(DOMAINS),'min_fresh_exact':min_full,
   'max_budget_violation_rate':max_budget_violation,
   'min_cost_scale_invariance':min_scale,
   'min_budget_ablation_drop':min_budget_ab_drop,
   'min_budget_ablation_violation_rate':min_budget_ab_violation,
   'min_quota_ablation_drop':min_quota_drop,
   'min_escalation_exact':min_escalation,
   'min_escalation_ablation_drop':min_escalation_drop,
 },
 'historical_context':{
   'old_budget_sequence_transform_fresh_exact':0.25,
   'comparison_note':'HISTORICAL VALUE IS A DIFFERENT TASK FAMILY AND IS CONTEXT ONLY, NOT A DIRECT SCORE COMPARISON'
 },
 'component':component,'canonical_mutation':False,'promotion_applied':False,
 'generation_head_digest_after':ledger['current_head_digest'],
 'next_required_capability':'G1_POST_RESOURCE_ASSISTED_DEVELOPMENT_REGRESSION_AND_ADMISSION_V1' if pass_gate else 'CONTINUE_G1_BUDGET_AWARE_SEARCH_REPAIR',
 'semantic_boundary':'BOUNDED SYNTHETIC SEARCH-PLANNING EVALUATION. FREE-FOR-DEV CATALOG INSPIRES RESOURCE STATE VARIABLES; NO PAID SERVICE IS AUTO-CREATED OR CALLED',
}
report['receipt_sha256']=h(report)
(ROOT/'yado_g1_budget_aware_search_repair_v1_receipt.json').write_text(json.dumps(report,indent=2,sort_keys=True,default=str)+'\n')

e={
 'index':len(ledger['events']),'event_id':f"E{len(ledger['events'])+1:04d}_G1_BUDGET_AWARE_SEARCH_REPAIR",
 'event_type':'EXTERNAL_RESOURCE_ASSISTED_ALGORITHM_GENESIS',
 'status':'PASS_SHADOW' if pass_gate else 'WITHHOLD','generation':ledger['current_head'],
 'deficit':'BUDGET_AWARE_SEARCH_AND_STAGED_ESCALATION',
 'effect':'BUDGETED_STAGE_POLICY_RESOLVED_COST_QUOTA_AND_ESCALATION_SEARCH_GAP' if pass_gate else 'BUDGET_AWARE_SEARCH_REPAIR_WITHHELD',
 'source_path':f'receipts/yado-g1-budget-aware-search-repair-v1-run-{run_id}.json',
 'source_digest':report['receipt_sha256'],'run_id':run_id,
 'parent_event_hash':ledger['tail_event_hash'],'canonical_mutation':False,'promotion_applied':False,
}
e['event_hash']=event_hash(e);ledger['events'].append(e);ledger['event_count']=len(ledger['events']);ledger['tail_event_hash']=e['event_hash']
if pass_gate:
    ledger['open_deficits']=[x for x in ledger.get('open_deficits',[]) if x not in ('BUDGET_AWARE_SEARCH_AND_STAGED_ESCALATION','G1_BUDGET_AWARE_SEARCH_REPAIR_V1')]
    ledger['open_deficits']=sorted(set(ledger['open_deficits']+['G1_POST_RESOURCE_ASSISTED_DEVELOPMENT_REGRESSION_AND_ADMISSION_V1']))
    ledger['shadow_resolved_deficits']=sorted(set(ledger.get('shadow_resolved_deficits',[])+['BUDGET_AWARE_SEARCH_AND_STAGED_ESCALATION','G1_BUDGET_AWARE_SEARCH_REPAIR_V1']))
ledger['ledger_digest']=h({k:v for k,v in ledger.items() if k!='ledger_digest'})
validate_ledger_v2(ledger);LEDGER.write_text(json.dumps(ledger,indent=2,sort_keys=True)+'\n')

print(json.dumps({
 'status':report['status'],'summary':report['summary'],
 'component_digest':component['component_digest'],
 'next_required_capability':report['next_required_capability'],
 'receipt_sha256':report['receipt_sha256']
},indent=2,sort_keys=True))
if not pass_gate:raise SystemExit('BUDGET_AWARE_SEARCH_REPAIR_WITHHELD')
