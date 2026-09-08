from __future__ import annotations

from fractions import Fraction
from itertools import combinations, product, permutations
from pathlib import Path
import copy
import hashlib
import json
import sys

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
PKG=ROOT/'yado_rc8_v36'
sys.path[:0]=[str(ROOT),str(PKG)]

from yado_budget_adaptive_compositional_logic_v2 import BudgetAdaptiveCompositionalLogicV2
from yado_work_budget_adaptive_contingent_planner_v2 import ContingentStage,WorkBudgetAdaptiveContingentPlannerV2
from yado_coverage_pruned_compositional_schema_router_v3 import CoveragePrunedCompositionalSchemaRouterV3
from yado_g2_all_experience_tri_organ_runtime_v1 import G2AllExperienceTriOrganRuntimeV1
from yado_generic_relational_meta_language_v1 import GenericRelationalMetaLanguageV1
from yado_generic_event_state_meta_language_v1 import GenericEventStateMetaLanguageV1
from yado_g2_experience_conditioned_cognitive_layer_v4 import G2ExperienceConditionedCognitiveLayerV4
from yado_unified_core_v1 import UnifiedYADOCoreV1

HEAD=REPO/'canonical/yado-main-head-g2.json'
CORE=REPO/'canonical/yado-unified-core-v1.json'
TRI=REPO/'canonical/yado-g2-all-experience-tri-organ-v1.json'
COG=REPO/'canonical/yado-g2-experience-conditioned-cognitive-layer-v4.json'
REQ=REPO/'architecture/yado-g2-fresh-cognitive-load-benchmark-v1-request.json'
OUT=ROOT/'yado_g2_fresh_cognitive_load_benchmark_v1_receipt.json'


def load(p):
    return json.loads(Path(p).read_text(encoding='utf-8'))

def canon(o):
    return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)

def digest(o):
    return hashlib.sha256(canon(o).encode()).hexdigest()

def score_bool(xs):
    return sum(bool(x) for x in xs)/len(xs) if xs else 0.0

head=load(HEAD);core_manifest=load(CORE);req=load(REQ)
head_before=copy.deepcopy(head)
core_before=copy.deepcopy(core_manifest)

if req.get('generation')!=head.get('generation_id'):
    raise RuntimeError('REQUEST_GENERATION_MISMATCH')
if req.get('expected_head_digest')!=head.get('canonical_head_digest'):
    raise RuntimeError('REQUEST_HEAD_DIGEST_MISMATCH')
if req.get('expected_frontier')!=head.get('current_frontier'):
    raise RuntimeError('REQUEST_FRONTIER_MISMATCH')
if len(head.get('active_capabilities',[]))!=int(req.get('expected_active_capability_count',-1)):
    raise RuntimeError('REQUEST_CAPABILITY_COUNT_MISMATCH')
if head.get('g3_genesis_performed') is not False:
    raise RuntimeError('G3_ALREADY_STARTED')

nonce=str(req.get('fresh_nonce') or '')
fresh_seed=digest({'head':head['canonical_head_digest'],'nonce':nonce,'schema':'yado.g2.fresh_cognitive_load.v1'})

# ---------------------------------------------------------------------------
# LOGIC: two new task families, independently checked by simple oracles.
# ---------------------------------------------------------------------------
fields=[f'b{i}' for i in range(7)]
def sym_truth(x):
    c=sum(bool(x[f]) for f in fields)
    return c in {1,3,6}

all_bool=[]
for bits in product((False,True),repeat=len(fields)):
    x=dict(zip(fields,bits))
    all_bool.append({'input':x,'expected':sym_truth(x)})

# Guarantee every count is represented in fit; evaluate on different configurations.
logic_fit=[];logic_hold=[]
by_count={}
for row in all_bool:
    c=sum(row['input'].values())
    by_count.setdefault(c,[]).append(row)
for c,rows in sorted(by_count.items()):
    logic_fit.extend(rows[:min(2,len(rows))])
    logic_hold.extend(rows[min(2,len(rows)):min(7,len(rows))])

sym_model=BudgetAdaptiveCompositionalLogicV2.learn_symmetric_boolean(logic_fit)
sym_results=[
    BudgetAdaptiveCompositionalLogicV2.predict_symmetric_boolean(sym_model,r['input'])==r['expected']
    for r in logic_hold
]
sym_accuracy=score_bool(sym_results)

# Exact new polynomial with coefficients not stored in canonical artifacts.
def poly_truth(x,y):
    x=Fraction(x);y=Fraction(y)
    return 5 + 3*x*x - 2*x*y + 4*y*y + 2*x - 3*y

poly_fit=[]
for x,y in [(-3,-2),(-3,1),(-2,3),(-1,-1),(0,0),(0,2),(1,-3),(1,1),(2,-2),(2,3),(3,0),(3,2)]:
    poly_fit.append({'x':x,'y':y,'expected':poly_truth(x,y)})
poly_hold=[(x,y) for x,y in [(-4,1),(-2,-3),(-1,4),(0,-4),(1,3),(2,1),(3,-2),(4,0),(4,3)]]
poly_model=BudgetAdaptiveCompositionalLogicV2.fit_polynomial(poly_fit,max_degree=4)
poly_results=[
    BudgetAdaptiveCompositionalLogicV2.predict_polynomial(poly_model,x,y)==poly_truth(x,y)
    for x,y in poly_hold
]
poly_accuracy=score_bool(poly_results)
logic_accuracy=(sym_accuracy+poly_accuracy)/2

# ---------------------------------------------------------------------------
# THINKING: independent exhaustive oracle vs bounded contingent planner.
# ---------------------------------------------------------------------------
def oracle_plan(current,target,budget,stages,completed=()):
    done0=frozenset(str(x) for x in completed)
    usable={s.stage_id:s for s in stages if not s.attempted and s.quota_remaining>0 and s.available}
    candidates=[]
    ids=sorted(usable)
    for n in range(1,len(ids)+1):
        for seq_ids in permutations(ids,n):
            seen=set(done0);cost=0.0;conf=float(current);ok=True
            for sid in seq_ids:
                s=usable[sid]
                if s.requires and not all(r in seen for r in s.requires):
                    ok=False;break
                cost+=max(0.0,float(s.cost))
                if cost>float(budget)+1e-12:
                    ok=False;break
                conf=max(0.0,min(1.0,conf+max(0.0,float(s.expected_gain))))
                seen.add(sid)
            if not ok:continue
            reaches=conf>=float(target)
            key=(0,cost,n,-conf,seq_ids) if reaches else (1,-conf,cost,n,seq_ids)
            candidates.append((key,list(seq_ids),cost,conf,reaches))
    if not candidates:
        return {'sequence':[],'action':'WITHHOLD','confidence':float(current),'cost':0.0,'feasible':False}
    candidates.sort(key=lambda z:z[0])
    _,seq,cost,conf,_=candidates[0]
    return {'sequence':seq,'action':seq[0],'confidence':conf,'cost':cost,'feasible':True}

thinking_cases=[]
for i in range(12):
    a=ContingentStage(f'A{i}',0.8+0.03*i,0.18+0.005*(i%3))
    b=ContingentStage(f'B{i}',0.7+0.02*i,0.22+0.004*(i%4),requires=(f'A{i}',))
    c=ContingentStage(f'C{i}',1.05+0.01*i,0.31+0.003*(i%5))
    d=ContingentStage(f'D{i}',0.55+0.015*i,0.16+0.002*(i%2),requires=(f'C{i}',))
    e=ContingentStage(f'E{i}',1.2+0.01*i,0.27+0.002*(i%3),requires=(f'B{i}',))
    stages=[a,b,c,d,e]
    current=0.19+0.01*(i%4);target=0.78+0.01*(i%3);budget=3.6+0.05*(i%4)
    thinking_cases.append((current,target,budget,stages))

think_match=[];replan_match=[]
for i,(current,target,budget,stages) in enumerate(thinking_cases):
    got=WorkBudgetAdaptiveContingentPlannerV2.plan(current,target,budget,stages)
    exp=oracle_plan(current,target,budget,stages)
    think_match.append(
        got.sequence==exp['sequence'] and got.action==exp['action']
        and abs(got.expected_confidence-exp['confidence'])<1e-12
        and abs(got.total_cost-exp['cost'])<1e-12
    )
    if got.sequence:
        first=got.sequence[0]
        observed=(-0.11 if i%2==0 else 0.09)
        got2=WorkBudgetAdaptiveContingentPlannerV2.next_after_observation(
            current,target,budget,stages,first,observed,completed=()
        )
        updated=[]
        spent=0.0
        for s in stages:
            if s.stage_id==first:
                spent=s.cost
                updated.append(ContingentStage(s.stage_id,s.cost,s.expected_gain,max(0,s.quota_remaining-1),s.available,s.latency,True,s.requires))
            else:updated.append(s)
        exp2=oracle_plan(max(0.0,min(1.0,current+observed)),target,budget-spent,updated,completed=(first,))
        replan_match.append(
            got2.sequence==exp2['sequence'] and got2.action==exp2['action']
            and abs(got2.expected_confidence-exp2['confidence'])<1e-12
            and abs(got2.total_cost-exp2['cost'])<1e-12
        )
thinking_plan_accuracy=score_bool(think_match)
thinking_replan_accuracy=score_bool(replan_match)
thinking_accuracy=(thinking_plan_accuracy+thinking_replan_accuracy)/2

# ---------------------------------------------------------------------------
# INTELLIGENCE: fresh compositional routing + schema alias transfer + fail closed.
# ---------------------------------------------------------------------------
router_train=[]
def route_truth(x):
    if x['domain']=='OPS' and bool(x['urgent']):return 'ACT'
    if x['domain']=='SCI' and x['severity']=='HIGH':return 'REVIEW'
    return 'HOLD'

base_inputs=[]
for domain,urgent,severity,trusted in product(('OPS','SCI'),(False,True),('LOW','HIGH'),(False,True)):
    x={'domain':domain,'urgent':urgent,'severity':severity,'trusted':trusted}
    base_inputs.append(x)
    router_train.append({'input':copy.deepcopy(x),'expected':route_truth(x)})
router_model=CoveragePrunedCompositionalSchemaRouterV3.fit(router_train,'HOLD',max_trigger_width=2)
router_fresh=[]
for i,x in enumerate(reversed(base_inputs)):
    q=copy.deepcopy(x);q['fresh_token']=fresh_seed[i:i+12]
    got=CoveragePrunedCompositionalSchemaRouterV3.route(router_model,q)
    router_fresh.append(got==(route_truth(x),))
router_accuracy=score_bool(router_fresh)

refs=[copy.deepcopy(x) for x in base_inputs]
aliases=[
    {'sector_alias':x['domain'],'needs_now':x['urgent'],'risk_band':x['severity'],'trusted_src':x['trusted']}
    for x in refs
]
alignment=CoveragePrunedCompositionalSchemaRouterV3.fit_schema_alignment(refs,aliases)
alias_results=[]
for x,a in zip(refs,aliases):
    got=CoveragePrunedCompositionalSchemaRouterV3.route_aligned(router_model,alignment,a)
    alias_results.append(got==(route_truth(x),))
alias_accuracy=score_bool(alias_results)

budget_cases=[
    {'input':{'k':i,'toggle':bool(i%2)},'expected':f'O{i}'}
    for i in range(9)
]
budget_model=CoveragePrunedCompositionalSchemaRouterV3.fit(budget_cases,'O0')
router_fail_closed=(budget_model.get('kind')=='WITHHOLD' and budget_model.get('reason')=='OUTPUT_BUDGET')
intelligence_accuracy=(router_accuracy+alias_accuracy+float(router_fail_closed))/3

# ---------------------------------------------------------------------------
# ALL-EXPERIENCE TRI-ORGAN: frozen self-synthesized genes on new symbols.
# ---------------------------------------------------------------------------
tri_artifact=load(TRI)
tri=G2AllExperienceTriOrganRuntimeV1(tri_artifact)

def closure_truth(edges,start):
    state={start}
    for _ in range(64):
        nxt=state|{b for a,b in edges if a in state}
        if nxt==state:break
        state=nxt
    return tuple(sorted(state,key=lambda x:(str(type(x)),str(x))))

rel_cases=[]
for i in range(12):
    nodes=[f'N{i}_{j}_{fresh_seed[j:j+6]}' for j in range(8)]
    distract=[f'D{i}_{j}_{fresh_seed[j+12:j+18]}' for j in range(4)]
    edges=[(nodes[j],nodes[j+1]) for j in range(7)]
    edges += [(nodes[1],nodes[4]),(nodes[2],nodes[6])]
    # Disconnected distractor component is intentionally present so that
    # RELATION_LEFT_DOMAIN is no longer observationally equivalent to START.
    # The canonical START/FORWARD/UNION/UNTIL_STABLE program must exclude it.
    edges += [(distract[0],distract[1]),(distract[1],distract[2]),(distract[2],distract[3])]
    rel_cases.append({'relation':edges,'start':nodes[0],'expected':closure_truth(edges,nodes[0])})
tri_logic_results=[tri.logic(c['relation'],c['start'])['result']==c['expected'] for c in rel_cases]
tri_logic_accuracy=score_bool(tri_logic_results)

event_cases=[]
for i in range(8):
    keys=[f'K{i}_{j}_{fresh_seed[j+8:j+14]}' for j in range(4)]
    valid=[('Q',k) for k in keys]+[('R',k) for k in reversed(keys)]
    mismatch=[('Q',keys[0]),('Q',keys[1]),('R',keys[0]),('R',keys[1])]
    underflow=[('R',keys[0])]
    unclosed=[('Q',keys[0]),('Q',keys[1]),('R',keys[1])]
    event_cases.extend([
        {'events':valid,'expected':True},
        {'events':mismatch,'expected':False},
        {'events':underflow,'expected':False},
        {'events':unclosed,'expected':False},
    ])
tri_thinking_results=[tri.thinking(c['events'])['result'] is c['expected'] for c in event_cases]
tri_thinking_accuracy=score_bool(tri_thinking_results)

tri_route=[]
for c in rel_cases[:6]:
    r=tri.intelligence({'input_contract':'RELATION_START_TO_STATE','relation':c['relation'],'start':c['start']})
    tri_route.append(r['status']=='PASS_TRI_ORGAN_INTELLIGENCE_ROUTE' and r['result']==c['expected'])
for c in event_cases[:12]:
    r=tri.intelligence({'input_contract':'EVENT_SEQUENCE_TO_BOOLEAN','events':c['events']})
    tri_route.append(r['status']=='PASS_TRI_ORGAN_INTELLIGENCE_ROUTE' and r['result'] is c['expected'])
unsupported=tri.intelligence({'input_contract':'UNSEEN_CONTRACT_'+fresh_seed[:8]})
tri_route.append(unsupported['status']=='WITHHOLD_UNSUPPORTED_CONTRACT' and unsupported['selected_component'] is None)
tri_route_accuracy=score_bool(tri_route)

rel_ablations=GenericRelationalMetaLanguageV1.ablations(tri.logic_program)
rel_ablation_best=max(
    (
      sum(GenericRelationalMetaLanguageV1.execute(a['program'],c['relation'],c['start'])==c['expected'] for c in rel_cases)/len(rel_cases)
      for a in rel_ablations
    ),default=0.0
)
evt_ablations=GenericEventStateMetaLanguageV1.ablations(tri.thinking_program)
evt_ablation_best=max(
    (
      sum(GenericEventStateMetaLanguageV1.execute(a['program'],c['events']) is c['expected'] for c in event_cases)/len(event_cases)
      for a in evt_ablations
    ),default=0.0
)
tri_logic_causal_drop=tri_logic_accuracy-rel_ablation_best
tri_thinking_causal_drop=tri_thinking_accuracy-evt_ablation_best

# ---------------------------------------------------------------------------
# COGNITIVE COMPOSER: all fresh boolean profiles, no retraining.
# ---------------------------------------------------------------------------
layer=G2ExperienceConditionedCognitiveLayerV4(load(COG))

def cognitive_truth(logic_accept,thinking_cautious,intelligence_robust):
    if not logic_accept:return 'WITHHOLD'
    if not intelligence_robust:return 'REPLAN' if thinking_cautious else 'ACT'
    return 'VERIFY' if thinking_cautious else 'ACT_WITH_GUARD'

cognitive_cases=[]
for logic_accept,thinking_cautious,intelligence_robust in product((False,True),repeat=3):
    signals={
      'logic_accept':logic_accept,
      'thinking_cautious':thinking_cautious,
      'intelligence_robust':intelligence_robust,
    }
    got=layer.compose(signals)
    cognitive_cases.append(got.get('decision')==cognitive_truth(**signals))
missing=layer.compose({'logic_accept':True,'thinking_cautious':False})
cognitive_cases.append(missing.get('decision')=='WITHHOLD' and missing.get('gate')=='WITHHOLD')
cognitive_accuracy=score_bool(cognitive_cases)

# Canonical core must remain untouched by the benchmark.
core_runtime=UnifiedYADOCoreV1(REPO)
core_audit=core_runtime.audit()
head_after=load(HEAD);core_after=load(CORE)

checks={
  'logic_fresh_ge_0_95':logic_accuracy>=.95,
  'logic_symmetric_fresh_ge_0_95':sym_accuracy>=.95,
  'logic_polynomial_fresh_ge_0_95':poly_accuracy>=.95,
  'thinking_fresh_ge_0_95':thinking_accuracy>=.95,
  'thinking_plan_oracle_ge_0_95':thinking_plan_accuracy>=.95,
  'thinking_replan_oracle_ge_0_95':thinking_replan_accuracy>=.95,
  'intelligence_fresh_ge_0_95':intelligence_accuracy>=.95,
  'router_fresh_ge_0_95':router_accuracy>=.95,
  'schema_alias_transfer_ge_0_95':alias_accuracy>=.95,
  'router_budget_fail_closed':router_fail_closed,
  'tri_logic_fresh_exact':tri_logic_accuracy==1.0,
  'tri_thinking_fresh_exact':tri_thinking_accuracy==1.0,
  'tri_intelligence_route_exact':tri_route_accuracy==1.0,
  'tri_logic_causal_drop_ge_0_15':tri_logic_causal_drop>=.15,
  'tri_thinking_causal_drop_ge_0_10':tri_thinking_causal_drop>=.10,
  'cognitive_composer_exact':cognitive_accuracy==1.0,
  'core_self_audit_pass':core_audit.get('pass') is True,
  'active_capability_count_31':len(head_after.get('active_capabilities',[]))==31,
  'canonical_head_unchanged':head_after.get('canonical_head_digest')==head_before.get('canonical_head_digest'),
  'canonical_core_unchanged':core_after==core_before,
  'frontier_unchanged':head_after.get('current_frontier')==req.get('expected_frontier'),
  'g3_not_started':head_after.get('g3_genesis_performed') is False,
  'no_retraining_of_canonical_tri_organ':tri_artifact.get('status')=='CANONICAL_ACTIVE',
  'automatic_promotion_forbidden':load(COG).get('automatic_canonical_promotion') is False,
}
passed=all(checks.values())
status='PASS_SHADOW_G2_FRESH_COGNITIVE_LOAD_BENCHMARK_V1' if passed else 'WITHHOLD_G2_FRESH_COGNITIVE_LOAD_BENCHMARK_V1'

metrics={
  'LOGIC':{
    'overall':logic_accuracy,'symmetric_fresh':sym_accuracy,'polynomial_fresh':poly_accuracy,
    'symmetric_holdout_count':len(logic_hold),'polynomial_holdout_count':len(poly_hold),
  },
  'THINKING':{
    'overall':thinking_accuracy,'plan_oracle':thinking_plan_accuracy,'replan_oracle':thinking_replan_accuracy,
    'plan_case_count':len(think_match),'replan_case_count':len(replan_match),
  },
  'INTELLIGENCE':{
    'overall':intelligence_accuracy,'router_fresh':router_accuracy,'schema_alias_transfer':alias_accuracy,
    'budget_fail_closed':router_fail_closed,'fresh_case_count':len(router_fresh),
  },
  'TRI_ORGAN':{
    'logic_fresh':tri_logic_accuracy,'thinking_fresh':tri_thinking_accuracy,'intelligence_route':tri_route_accuracy,
    'logic_best_ablation':rel_ablation_best,'logic_causal_drop':tri_logic_causal_drop,
    'thinking_best_ablation':evt_ablation_best,'thinking_causal_drop':tri_thinking_causal_drop,
    'relation_case_count':len(rel_cases),'event_case_count':len(event_cases),
  },
  'COGNITIVE_WORKSPACE':{
    'composer_accuracy':cognitive_accuracy,'profile_count':len(cognitive_cases),
  },
}
weighted_scores=[
    logic_accuracy,thinking_accuracy,intelligence_accuracy,
    tri_logic_accuracy,tri_thinking_accuracy,tri_route_accuracy,cognitive_accuracy,
]
overall_score=sum(weighted_scores)/len(weighted_scores)

receipt={
  'schema':'yado.g2.fresh_cognitive_load_benchmark.receipt.v1',
  'status':status,
  'generation':head.get('generation_id'),
  'frontier':head.get('current_frontier'),
  'canonical_head_digest':head.get('canonical_head_digest'),
  'fresh_nonce':nonce,
  'fresh_seed_digest':fresh_seed,
  'active_capability_count':len(head.get('active_capabilities',[])),
  'metrics':metrics,
  'overall_score':overall_score,
  'checks':checks,
  'canonical_mutation':False,
  'retraining_performed':False,
  'promotion_applied':False,
  'generation_transition':False,
  'g3_genesis_performed':False,
  'next_required_capability':(
      'G2_FRESH_REAL_DATA_COGNITIVE_TRANSFER_V1'
      if passed else 'G2_FRESH_COGNITIVE_LOAD_DEFICIT_REPAIR_V2'
  ),
  'semantic_boundary':(
      'FRESH SHADOW LOAD TEST OF CURRENT CANONICAL G2 LOGIC, THINKING, INTELLIGENCE, '
      'ALL-EXPERIENCE TRI-ORGAN AND COGNITIVE COMPOSER. INDEPENDENT ORACLES ARE USED '
      'FOR NEW BOOLEAN/POLYNOMIAL/PLANNING/ROUTING TASKS. NO CANONICAL RETRAINING, '
      'CAPABILITY ADMISSION, PROMOTION, G3 TRANSITION OR CLAIM OF SUBJECTIVE CONSCIOUSNESS.'
  ),
}
receipt['receipt_sha256']=digest(receipt)
OUT.write_text(json.dumps(receipt,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')
print(json.dumps(receipt,indent=2,sort_keys=True,default=str))
