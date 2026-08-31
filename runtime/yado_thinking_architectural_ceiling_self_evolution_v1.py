from __future__ import annotations
from pathlib import Path
from dataclasses import dataclass
from itertools import permutations
import hashlib,json,os,sys

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
sys.path.insert(0,str(ROOT))
from yado_evolution_ledger_v2 import validate_ledger_v2,event_hash
from yado_neutral_evidence_profile_selector_v1 import NeutralEvidenceProfileSelectorV1,EvidenceCandidate

HEAD=REPO/'canonical'/'yado-main-head-g2.json'
ARCH=REPO/'canonical'/'yado-g2-architecture-v1.json'
LEDGER=REPO/'architecture'/'evolution-ledger.json'
DIAG=REPO/'receipts'/'yado-g2-lti-architectural-ceiling-diagnostic-v1-run-33441194354.json'
CAND_DIR=REPO/'candidates'/'g2-self-evolution'
CAND_SRC=CAND_DIR/'bounded_adaptive_contingent_planner_v1.py'
CAND_META=CAND_DIR/'bounded_adaptive_contingent_planner_v1.json'
STATE=REPO/'architecture'/'yado-g2-lti-ceiling-state-v1.json'
OUT=ROOT/'yado_thinking_architectural_ceiling_self_evolution_v1_receipt.json'

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def h(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def fsha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8'))

head=load(HEAD);arch=load(ARCH);ledger=load(LEDGER);diag=load(DIAG);state=load(STATE)
validate_ledger_v2(ledger)
if ledger.get('open_deficits')!=['THINKING_ARCHITECTURAL_CEILING_SELF_EVOLUTION_V1']:raise RuntimeError('UNEXPECTED_FRONTIER')
if diag.get('self_selected_weakest_plane')!='THINKING':raise RuntimeError('THINKING_NOT_SELF_SELECTED')
if ledger.get('current_head_digest')!=head.get('canonical_head_digest'):raise RuntimeError('HEAD_LEDGER_MISMATCH')
arch_sha=fsha(ARCH);head_sha=fsha(HEAD)

@dataclass(frozen=True)
class Spec:
    sid:str
    max_depth:int
    signed:bool
    dependency:bool
    complexity:float
    risk:float
    novelty:float

SPECS=[
 Spec('BASE_COMPAT',4,False,False,.10,.02,.10),
 Spec('DEPTH8_ONLY',8,False,False,.18,.03,.35),
 Spec('SIGNED_ONLY',4,True,False,.16,.03,.35),
 Spec('DEPENDENCY_ONLY',4,False,True,.20,.04,.45),
 Spec('DEPTH8_SIGNED',8,True,False,.24,.04,.55),
 Spec('DEPTH8_DEPENDENCY',8,False,True,.27,.05,.65),
 Spec('SIGNED_DEPENDENCY',4,True,True,.26,.05,.65),
 Spec('ADAPTIVE_CONTINGENT',8,True,True,.34,.06,.90),
]

def plan(spec,current,target,budget,stages,completed=()):
    completed=set(completed);cand=[]
    def usable(s,done):
        if s.get('attempted'):return False
        if int(s.get('quota_remaining',0))<=0:return False
        req=tuple(s.get('requires',()))
        if req and spec.dependency:
            return all(x in done for x in req)
        return bool(s.get('available',True))
    def dfs(seq,done,cost,conf):
        if seq:
            reaches=conf>=target
            key=(0,cost,len(seq),-conf,tuple(x['stage_id'] for x in seq)) if reaches else (1,-conf,cost,len(seq),tuple(x['stage_id'] for x in seq))
            cand.append((key,list(seq),cost,conf,reaches))
        if len(seq)>=spec.max_depth:return
        for s in stages:
            if s['stage_id'] in done or not usable(s,done):continue
            nc=cost+max(0.0,float(s['cost']))
            if nc>budget+1e-12:continue
            dfs(seq+[s],done|{s['stage_id']},nc,min(1.0,max(0.0,conf+max(0.0,float(s['expected_gain'])))))
    if current>=target:return {'action':'STOP','sequence':[],'expected_confidence':current,'total_cost':0.0,'feasible':True}
    dfs([],completed,0.0,current)
    if not cand:return {'action':'WITHHOLD','sequence':[],'expected_confidence':current,'total_cost':0.0,'feasible':False}
    cand.sort(key=lambda z:z[0]);_,seq,cost,conf,_=cand[0]
    return {'action':seq[0]['stage_id'],'sequence':[x['stage_id'] for x in seq],'expected_confidence':conf,'total_cost':cost,'feasible':True}

def after(spec,current,target,budget,stages,done_stage,observed_gain,completed=()):
    spent=next((max(0.0,float(s['cost'])) for s in stages if s['stage_id']==done_stage),0.0)
    gain=float(observed_gain) if spec.signed else max(0.0,float(observed_gain))
    conf=min(1.0,max(0.0,float(current)+gain))
    updated=[]
    for s in stages:
        z=dict(s)
        if z['stage_id']==done_stage:
            z['attempted']=True;z['quota_remaining']=max(0,int(z.get('quota_remaining',0))-1)
        updated.append(z)
    return plan(spec,conf,target,float(budget)-spent,updated,tuple(set(completed)|{done_stage}))

def evaluate(spec,variant=0):
    scores={}
    # Additive ordinary planning.
    ok=0;n=100
    for i in range(n):
        stages=[{'stage_id':f'A{variant}_{i}_{j}','cost':1+j*.2,'expected_gain':.11+j*.02,'quota_remaining':1,'available':True,'attempted':False} for j in range(4)]
        p=plan(spec,.24,.61,7.0,stages)
        ok+=p['feasible'] and p['total_cost']<=7.0 and p['expected_confidence']>=.61-1e-9
    scores['ADDITIVE_BUDGET_PLAN']=ok/n
    # Horizon 5/6.
    ok=0;n=90
    depth=5 if variant%2==0 else 6
    start=.20 if depth==5 else .14
    gain=.10 if depth==5 else .095
    target=start+gain*depth
    for i in range(n):
        stages=[{'stage_id':f'H{variant}_{i}_{j}','cost':1,'expected_gain':gain,'quota_remaining':1,'available':True,'attempted':False} for j in range(depth)]
        p=plan(spec,start,target,float(depth),stages)
        ok+=p['expected_confidence']>=target-1e-9 and len(p['sequence'])>=depth
    scores['LONG_HORIZON_REQUIRED']=ok/n
    # Signed negative evidence.
    ok=0;n=90
    for i in range(n):
        a=f'N{variant}_{i}_A';b=f'N{variant}_{i}_B'
        stages=[{'stage_id':a,'cost':1,'expected_gain':.20,'quota_remaining':1,'available':True,'attempted':False},
                {'stage_id':b,'cost':1,'expected_gain':.20,'quota_remaining':1,'available':True,'attempted':False}]
        obs=-.20-.05*(i%2)
        p=after(spec,.55,.80,2.0,stages,a,obs)
        oracle=min(1.0,max(0.0,.55+obs)+.20)
        ok+=abs(p['expected_confidence']-oracle)<1e-9
    scores['SIGNED_NEGATIVE_EVIDENCE']=ok/n
    # Dependency chain unlock.
    ok=0;n=90
    chain=2 if variant%2==0 else 3
    for i in range(n):
        ids=[f'D{variant}_{i}_{j}' for j in range(chain+1)]
        stages=[]
        stages.append({'stage_id':ids[0],'cost':1,'expected_gain':.10,'quota_remaining':1,'available':True,'attempted':False,'requires':[]})
        for j in range(1,len(ids)):
            stages.append({'stage_id':ids[j],'cost':1,'expected_gain':.22,'quota_remaining':1,'available':False,'attempted':False,'requires':[ids[j-1]]})
        p=after(spec,.30,.70,5.0,stages,ids[0],.10)
        # The first newly unlocked stage must be selectable.
        ok+=p['action']==ids[1]
    scores['DEPENDENCY_UNLOCK']=ok/n
    # Mixed: long plan + dependency + signed update.
    ok=0;n=100
    for i in range(n):
        a=f'M{variant}_{i}_A';b=f'M{variant}_{i}_B';c=f'M{variant}_{i}_C';d=f'M{variant}_{i}_D';e=f'M{variant}_{i}_E'
        stages=[
          {'stage_id':a,'cost':1,'expected_gain':.10,'quota_remaining':1,'available':True,'attempted':False,'requires':[]},
          {'stage_id':b,'cost':1,'expected_gain':.12,'quota_remaining':1,'available':False,'attempted':False,'requires':[a]},
          {'stage_id':c,'cost':1,'expected_gain':.12,'quota_remaining':1,'available':False,'attempted':False,'requires':[b]},
          {'stage_id':d,'cost':1,'expected_gain':.12,'quota_remaining':1,'available':False,'attempted':False,'requires':[c]},
          {'stage_id':e,'cost':1,'expected_gain':.12,'quota_remaining':1,'available':False,'attempted':False,'requires':[d]},
        ]
        p=after(spec,.40,.78,6.0,stages,a,-.08)
        # Signed update -> .32, then chain B..E can reach .80.
        ok+=p['action']==b and p['expected_confidence']>=.78-1e-9
    scores['MIXED_CONTINGENT_CHAIN']=ok/n
    return {'families':scores,'score':sum(scores.values())/len(scores),'min_family':min(scores.values())}

validation={}
token_to_spec={}
for i,s in enumerate(SPECS):
    m=evaluate(s,variant=0)
    token='opaque_'+h({'slot':i,'head':head['canonical_head_digest']})[:18]
    token_to_spec[token]=s
    validation[s.sid]=m|{'token':token,'complexity':s.complexity,'risk':s.risk,'novelty':s.novelty}
selection=NeutralEvidenceProfileSelectorV1.select([
    EvidenceCandidate(v['token'],v['score'],v['complexity'],v['risk'],v['novelty']) for v in validation.values()
])
selected=token_to_spec[selection['selected_token']]
holdout=evaluate(selected,variant=1)
base_holdout=evaluate(SPECS[0],variant=1)
causal_drop=holdout['score']-base_holdout['score']

def render_source(spec):
    return f'''from __future__ import annotations
from dataclasses import dataclass
from typing import Iterable

@dataclass(frozen=True)
class ContingentStage:
    stage_id:str
    cost:float
    expected_gain:float
    quota_remaining:int=1
    available:bool=True
    latency:float=1.0
    attempted:bool=False
    requires:tuple[str,...]=()

@dataclass
class ContingentPlan:
    action:str
    sequence:list[str]
    expected_confidence:float
    total_cost:float
    feasible:bool
    reason:str

class BoundedAdaptiveContingentPlannerV1:
    COMPONENT_ID="ALG-G2-BOUNDED-ADAPTIVE-CONTINGENT-PLANNER-V1"
    MAX_STAGES=8
    MAX_PLAN_DEPTH={spec.max_depth}
    SIGNED_OBSERVATION={str(spec.signed)}
    DEPENDENCY_AWARE={str(spec.dependency)}

    @classmethod
    def _usable(cls,s,done):
        if s.attempted or s.quota_remaining<=0:return False
        if s.requires and cls.DEPENDENCY_AWARE:return all(x in done for x in s.requires)
        return bool(s.available)

    @classmethod
    def plan(cls,current_confidence,target_confidence,remaining_budget,stages:Iterable[ContingentStage],completed=()):
        current=max(0.0,min(1.0,float(current_confidence)));target=float(target_confidence);budget=float(remaining_budget)
        xs=list(stages)[:cls.MAX_STAGES];done=set(completed);cand=[]
        if current>=target:return ContingentPlan("STOP",[],current,0.0,True,"TARGET_ALREADY_MET")
        def dfs(seq,seen,cost,conf):
            if seq:
                reaches=conf>=target
                key=(0,cost,len(seq),-conf,tuple(x.stage_id for x in seq)) if reaches else (1,-conf,cost,len(seq),tuple(x.stage_id for x in seq))
                cand.append((key,list(seq),cost,conf,reaches))
            if len(seq)>=cls.MAX_PLAN_DEPTH:return
            for s in xs:
                if s.stage_id in seen or not cls._usable(s,seen):continue
                nc=cost+max(0.0,float(s.cost))
                if nc>budget+1e-12:continue
                dfs(seq+[s],seen|{{s.stage_id}},nc,max(0.0,min(1.0,conf+max(0.0,float(s.expected_gain)))))
        dfs([],done,0.0,current)
        if not cand:return ContingentPlan("WITHHOLD",[],current,0.0,False,"NO_FEASIBLE_PLAN")
        cand.sort(key=lambda z:z[0]);_,seq,cost,conf,reaches=cand[0]
        return ContingentPlan(seq[0].stage_id,[x.stage_id for x in seq],conf,cost,True,"TARGET_REACHABLE" if reaches else "BEST_REACHABLE")

    @classmethod
    def next_after_observation(cls,current_confidence,target_confidence,remaining_budget,stages,completed_stage_id,observed_gain,completed=()):
        xs=list(stages);spent=0.0;updated=[]
        for s in xs:
            if s.stage_id==completed_stage_id:
                spent=max(0.0,float(s.cost))
                updated.append(ContingentStage(s.stage_id,s.cost,s.expected_gain,max(0,s.quota_remaining-1),s.available,s.latency,True,s.requires))
            else:updated.append(s)
        gain=float(observed_gain) if cls.SIGNED_OBSERVATION else max(0.0,float(observed_gain))
        conf=max(0.0,min(1.0,float(current_confidence)+gain))
        return cls.plan(conf,target_confidence,float(remaining_budget)-spent,updated,tuple(set(completed)|{{completed_stage_id}}))
'''
CAND_DIR.mkdir(parents=True,exist_ok=True)
CAND_SRC.write_text(render_source(selected),encoding='utf-8')

checks={
 'thinking_self_selected':diag.get('self_selected_weakest_plane')=='THINKING',
 'selected_improves_holdout':holdout['score']>=base_holdout['score']+.50,
 'fresh_holdout_min_family':holdout['min_family']>=.99,
 'causal_drop':causal_drop>=.50,
 'architecture_immutable':fsha(ARCH)==arch_sha,
 'head_immutable':fsha(HEAD)==head_sha and ledger.get('current_head_digest')==head.get('canonical_head_digest'),
}
passed=all(checks.values())
candidate={
 'schema':'yado.g2.bounded_adaptive_contingent_planner_candidate.v1',
 'component_id':'ALG-G2-BOUNDED-ADAPTIVE-CONTINGENT-PLANNER-V1',
 'selected_strategy':selected.sid,
 'selected_features':{'max_depth':selected.max_depth,'signed_observation':selected.signed,'dependency_aware':selected.dependency},
 'validation':validation,'neutral_selection':selection,'fresh_holdout':holdout,'base_holdout':base_holdout,'causal_drop':causal_drop,
 'candidate_source_sha256':fsha(CAND_SRC),'architecture_sha256':arch_sha,'parent_head_digest':head['canonical_head_digest'],
 'canonical_active':False,'promotion_applied':False,
 'state':'AUTHORIZED_FOR_SHADOW_ADMISSION' if passed else 'WITHHOLD',
 'semantic_boundary':'BOUNDED THINKING/PLANNING MECHANISM INSIDE FIXED G2 THINKING PLANE; SUPPORTS LONGER BOUNDED HORIZONS, SIGNED OBSERVATIONS, AND PREREQUISITE-AWARE CONTINGENT SEARCH. NOT GENERAL PLANNING OR AGI.'
}
candidate['candidate_digest']=h(candidate);CAND_META.write_text(json.dumps(candidate,indent=2,sort_keys=True)+'\n')

next_cap='THINKING_ARCHITECTURAL_CEILING_FRESH_ADMISSION_V1' if passed else 'THINKING_ARCHITECTURAL_CEILING_SELF_EVOLUTION_V2'
state['round']=1
state['candidate_history'].append({'round':1,'plane':'THINKING','candidate_digest':candidate['candidate_digest'],'selected_strategy':selected.sid,'fresh_score':holdout['score'],'baseline_score':base_holdout['score'],'causal_drop':causal_drop,'status':'PASS_SHADOW' if passed else 'WITHHOLD'})
state['planes']['THINKING']['candidate_score']=holdout['score'];state['planes']['THINKING']['candidate_families']=holdout['families']
state['next_required_capability']=next_cap;state['state_digest']=h({k:v for k,v in state.items() if k!='state_digest'})
STATE.write_text(json.dumps(state,indent=2,sort_keys=True)+'\n')

run_id=str(os.getenv('GITHUB_RUN_ID') or 'LOCAL')
receipt={'schema':'yado.g2.thinking_architectural_ceiling_self_evolution.v1',
 'status':'PASS_THINKING_ARCHITECTURAL_CEILING_SELF_EVOLUTION_V1' if passed else 'WITHHOLD_THINKING_ARCHITECTURAL_CEILING_SELF_EVOLUTION_V1',
 'selected_strategy':selected.sid,'validation':validation,'neutral_selection':selection,'fresh_holdout':holdout,'base_holdout':base_holdout,'causal_drop':causal_drop,
 'candidate_digest':candidate['candidate_digest'],'candidate_source_sha256':candidate['candidate_source_sha256'],'checks':checks,
 'canonical_mutation':False,'promotion_applied':False,'generation_transition':False,'g3_genesis_performed':False,
 'next_required_capability':next_cap,'semantic_boundary':candidate['semantic_boundary']}
receipt['receipt_sha256']=h(receipt);OUT.write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')

e={'index':len(ledger['events']),'event_id':f"E{len(ledger['events'])+1:04d}_G2_THINKING_CEILING_SELF_EVOLUTION",
 'event_type':'FIXED_ARCHITECTURE_THINKING_SELF_EVOLUTION','status':'PASS_SHADOW' if passed else 'WITHHOLD',
 'generation':ledger['current_head'],'deficit':'THINKING_ARCHITECTURAL_CEILING_SELF_EVOLUTION_V1',
 'effect':f"SELECTED={selected.sid}; FRESH={holdout['score']:.6f}; BASE={base_holdout['score']:.6f}; NEXT={next_cap}",
 'source_path':f'receipts/yado-thinking-architectural-ceiling-self-evolution-v1-run-{run_id}.json',
 'source_digest':receipt['receipt_sha256'],'run_id':run_id,'parent_event_hash':ledger['tail_event_hash'],
 'canonical_mutation':False,'promotion_applied':False}
e['event_hash']=event_hash(e);ledger['events'].append(e);ledger['event_count']=len(ledger['events']);ledger['tail_event_hash']=e['event_hash']
ledger['open_deficits']=[next_cap];ledger['ledger_digest']=h({k:v for k,v in ledger.items() if k!='ledger_digest'})
validate_ledger_v2(ledger);LEDGER.write_text(json.dumps(ledger,indent=2,sort_keys=True)+'\n')
print(json.dumps({'status':receipt['status'],'selected_strategy':selected.sid,'fresh_holdout':holdout,'base_holdout':base_holdout,'causal_drop':causal_drop,'checks':checks,'next_required_capability':next_cap,'receipt_sha256':receipt['receipt_sha256']},indent=2,sort_keys=True))
if not passed:raise SystemExit('THINKING_CEILING_SELF_EVOLUTION_WITHHELD')
