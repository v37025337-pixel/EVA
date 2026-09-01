from __future__ import annotations
from pathlib import Path
import hashlib,json,os,sys

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
sys.path.insert(0,str(ROOT))
from yado_evolution_ledger_v2 import validate_ledger_v2,event_hash
from yado_neutral_evidence_profile_selector_v1 import NeutralEvidenceProfileSelectorV1,EvidenceCandidate
from yado_bounded_adaptive_contingent_planner_v1 import BoundedAdaptiveContingentPlannerV1,ContingentStage

HEAD=REPO/'canonical'/'yado-main-head-g2.json'
ARCH=REPO/'canonical'/'yado-g2-architecture-v1.json'
LEDGER=REPO/'architecture'/'evolution-ledger.json'
STATE=REPO/'architecture'/'yado-g2-lti-ceiling-state-v1.json'
PROBE=REPO/'receipts'/'yado-g2-lti-code-architectural-ceiling-plateau-probe-v5-run-33502810867.json'
CAND_DIR=REPO/'candidates'/'g2-self-evolution'
CAND_SRC=CAND_DIR/'work_budget_adaptive_contingent_planner_v2.py'
CAND_META=CAND_DIR/'work_budget_adaptive_contingent_planner_v2.json'
OUT=ROOT/'yado_thinking_plateau_self_evolution_v1_receipt.json'

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def h(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def fsha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def avg(xs):return sum(xs)/max(1,len(xs))

head=load(HEAD);ledger=load(LEDGER);state=load(STATE);probe=load(PROBE)
validate_ledger_v2(ledger)
if ledger.get('open_deficits')!=['THINKING_PLATEAU_SELF_EVOLUTION_V1']:raise RuntimeError('UNEXPECTED_FRONTIER')
if probe.get('self_selected_plane')!='THINKING':raise RuntimeError('THINKING_NOT_SELF_SELECTED')
if ledger.get('current_head_digest')!=head.get('canonical_head_digest'):raise RuntimeError('HEAD_LEDGER_MISMATCH')
arch_sha=fsha(ARCH);head_sha=fsha(HEAD)

candidate_source=r'''from __future__ import annotations
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

class WorkBudgetAdaptiveContingentPlannerV2:
    COMPONENT_ID="ALG-G2-WORK-BUDGET-ADAPTIVE-CONTINGENT-PLANNER-V2"
    MAX_STAGE_RECORDS=64
    MAX_PLAN_STEPS=32
    MAX_SEARCH_NODES=24000
    BEAM_WIDTH=256
    SIGNED_OBSERVATION=True
    DEPENDENCY_AWARE=True

    @classmethod
    def _usable(cls,s,done):
        if s.attempted or s.quota_remaining<=0:return False
        if s.requires and cls.DEPENDENCY_AWARE:return all(x in done for x in s.requires)
        return bool(s.available)

    @classmethod
    def _state_key(cls,seq,cost,conf,target):
        reaches=conf>=target
        ids=tuple(x.stage_id for x in seq)
        return (0,cost,len(seq),-conf,ids) if reaches else (1,-conf,cost,len(seq),ids)

    @classmethod
    def plan(cls,current_confidence,target_confidence,remaining_budget,stages:Iterable[ContingentStage],completed=()):
        current=max(0.0,min(1.0,float(current_confidence)));target=float(target_confidence);budget=float(remaining_budget)
        xs=list(stages)
        if len(xs)>cls.MAX_STAGE_RECORDS:
            return ContingentPlan("WITHHOLD",[],current,0.0,False,"STAGE_RECORD_WORK_BUDGET")
        done0=frozenset(str(x) for x in completed)
        if current>=target:return ContingentPlan("STOP",[],current,0.0,True,"TARGET_ALREADY_MET")

        frontier=[([],done0,0.0,current)]
        candidates=[];nodes=0
        max_steps=min(cls.MAX_PLAN_STEPS,len(xs))

        for _depth in range(max_steps):
            nxt=[]
            for seq,seen,cost,conf in frontier:
                for s in xs:
                    if s.stage_id in seen or not cls._usable(s,seen):continue
                    nc=cost+max(0.0,float(s.cost))
                    if nc>budget+1e-12:continue
                    ng=max(0.0,float(s.expected_gain))
                    nconf=max(0.0,min(1.0,conf+ng))
                    nseq=seq+[s];nseen=seen|{s.stage_id}
                    nodes+=1
                    if nodes>cls.MAX_SEARCH_NODES:
                        if candidates:
                            candidates.sort(key=lambda z:z[0])
                            _,best,cost2,conf2,reaches=candidates[0]
                            return ContingentPlan(best[0].stage_id,[x.stage_id for x in best],conf2,cost2,True,
                                "TARGET_REACHABLE_WORK_BUDGET" if reaches else "BEST_REACHABLE_WORK_BUDGET")
                        return ContingentPlan("WITHHOLD",[],current,0.0,False,"SEARCH_WORK_BUDGET")
                    key=cls._state_key(nseq,nc,nconf,target)
                    candidates.append((key,nseq,nc,nconf,nconf>=target))
                    nxt.append((nseq,nseen,nc,nconf))
            if not nxt:break
            nxt.sort(key=lambda z:cls._state_key(z[0],z[2],z[3],target))
            frontier=nxt[:cls.BEAM_WIDTH]

        if not candidates:return ContingentPlan("WITHHOLD",[],current,0.0,False,"NO_FEASIBLE_PLAN")
        candidates.sort(key=lambda z:z[0]);_,seq,cost,conf,reaches=candidates[0]
        return ContingentPlan(seq[0].stage_id,[x.stage_id for x in seq],conf,cost,True,
            "TARGET_REACHABLE" if reaches else "BEST_REACHABLE")

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
        return cls.plan(conf,target_confidence,float(remaining_budget)-spent,updated,tuple(set(completed)|{completed_stage_id}))

__all__=["ContingentStage","ContingentPlan","WorkBudgetAdaptiveContingentPlannerV2"]
'''
CAND_DIR.mkdir(parents=True,exist_ok=True);CAND_SRC.write_text(candidate_source,encoding='utf-8')
ns={};exec(compile(candidate_source,'<candidate>','exec'),ns)
V2=ns['WorkBudgetAdaptiveContingentPlannerV2'];S2=ns['ContingentStage']
V1=BoundedAdaptiveContingentPlannerV1;S1=ContingentStage

def stage(clsS,i,gain=.12,requires=()):
    return clsS(f's{i}',1.0,gain,1,True,.1,False,tuple(requires))

def eval_cls(C,S):
    out={}
    # V5 exact counterexamples.
    n=9
    st=[stage(S,i,.12) for i in range(n)]
    p=C.plan(.02,1.0,float(n),st)
    out['WIDTH9']=min(1.0,p.expected_confidence)
    ids=[f'd{i}' for i in range(10)]
    dep=[S(ids[0],1,.03,1,True,.1,False,())]+[S(ids[j],1,.12,1,True,.1,False,(ids[j-1],)) for j in range(1,len(ids))]
    q=C.next_after_observation(.03,1.0,10.0,dep,ids[0],.03)
    out['DEPENDENCY9']=min(1.0,q.expected_confidence)

    # Signed negative update regression.
    ss=[stage(S,i,.3) for i in range(4)]
    neg=C.next_after_observation(.8,.9,4.0,ss,'s0',-.35)
    out['SIGNED_NEGATIVE']=1.0 if neg.expected_confidence>=.9 and len(neg.sequence)>=2 else 0.0

    # Fail-closed impossible budget.
    hard=[stage(S,i,.1) for i in range(12)]
    hp=C.plan(.1,1.0,0.5,hard)
    out['BUDGET_FAIL_CLOSED']=1.0 if hp.action=='WITHHOLD' and not hp.feasible else 0.0
    return out

strategies=[
 {'id':'BASE_FIXED_GEOMETRY','kind':'V1','complexity':.18,'risk':.03,'novelty':.15},
 {'id':'WORK_BUDGET_BEAM','kind':'V2','complexity':.35,'risk':.05,'novelty':.94},
]
validation={};tok={}
for i,s in enumerate(strategies):
    fam=eval_cls(V1,S1) if s['kind']=='V1' else eval_cls(V2,S2)
    token='opaque_'+h({'thinking_plateau':1,'slot':i,'head':head['canonical_head_digest']})[:18]
    validation[s['id']]={'families':fam,'score':avg(list(fam.values())),'min_family':min(fam.values()),
                         'token':token,'complexity':s['complexity'],'risk':s['risk'],'novelty':s['novelty']}
    tok[token]=s
sel=NeutralEvidenceProfileSelectorV1.select([EvidenceCandidate(v['token'],v['score'],v['complexity'],v['risk'],v['novelty']) for v in validation.values()])
selected=tok[sel['selected_token']]

# Fresh transfer beyond the original 8/8 geometry, still within fixed work budget.
fresh={}
st10=[stage(S2,i,.1) for i in range(10)]
p10=V2.plan(.0,1.0,10.0,st10)
fresh['WIDTH10_FRESH']=1.0 if p10.expected_confidence>=.999 and len(p10.sequence)==10 else 0.0

ids=[f'z{i}' for i in range(11)]
dep=[S2(ids[0],1,.02,1,True,.1,False,())]+[S2(ids[j],1,.1,1,True,.1,False,(ids[j-1],)) for j in range(1,len(ids))]
pd=V2.next_after_observation(.0,1.0,11.0,dep,ids[0],.02)
fresh['DEPENDENCY10_FRESH']=1.0 if pd.expected_confidence>=.999 and len(pd.sequence)>=10 else 0.0

# Mixed dependency graph with optional distractors.
mix=[
 S2('a',1,.15,1,True,.1,False,()),
 S2('b',1,.15,1,True,.1,False,('a',)),
 S2('c',1,.15,1,True,.1,False,('b',)),
 S2('d',1,.15,1,True,.1,False,('c',)),
 S2('e',1,.15,1,True,.1,False,('d',)),
 S2('f',1,.15,1,True,.1,False,('e',)),
 S2('x1',2,.02,1,True,.1,False,()),
 S2('x2',2,.02,1,True,.1,False,()),
 S2('x3',2,.02,1,True,.1,False,()),
]
mp=V2.plan(.1,.95,6.0,mix)
fresh['DEPENDENCY_WITH_DISTRACTORS']=1.0 if mp.expected_confidence>=.95 and mp.sequence[:6]==['a','b','c','d','e','f'] else 0.0

# Work budget refusal on oversized descriptor set.
overs=[stage(S2,i,.01) for i in range(V2.MAX_STAGE_RECORDS+1)]
op=V2.plan(.0,1.0,100.0,overs)
fresh['STAGE_WORK_BUDGET_WITHHOLD']=1.0 if op.action=='WITHHOLD' and op.reason=='STAGE_RECORD_WORK_BUDGET' else 0.0

holdout={'families':fresh,'score':avg(list(fresh.values())),'min_family':min(fresh.values())}
old=validation['BASE_FIXED_GEOMETRY']['score'];new=validation['WORK_BUDGET_BEAM']['score'];causal_gain=new-old
old_worst_case_nodes=109600

checks={
 'thinking_self_selected':probe.get('self_selected_plane')=='THINKING',
 'selected_work_budget_beam':selected['id']=='WORK_BUDGET_BEAM',
 'counterexamples_repaired':validation['WORK_BUDGET_BEAM']['families']['WIDTH9']>=.99 and validation['WORK_BUDGET_BEAM']['families']['DEPENDENCY9']>=.99,
 'fresh_min_one':holdout['min_family']>=.99,
 'causal_gain_positive':causal_gain>=.02,
 'new_search_budget_below_old_worst_case':V2.MAX_SEARCH_NODES<old_worst_case_nodes,
 'architecture_immutable':fsha(ARCH)==arch_sha,
 'head_immutable':fsha(HEAD)==head_sha and ledger.get('current_head_digest')==head.get('canonical_head_digest')
}
passed=all(checks.values());next_cap='THINKING_PLATEAU_FRESH_ADMISSION_V1' if passed else 'THINKING_PLATEAU_SELF_EVOLUTION_V2'

candidate={'schema':'yado.g2.work_budget_adaptive_contingent_planner_candidate.v2',
 'component_id':'ALG-G2-WORK-BUDGET-ADAPTIVE-CONTINGENT-PLANNER-V2','selected_strategy':selected['id'],
 'validation':validation,'neutral_selection':sel,'fresh_validation':holdout,'causal_gain':causal_gain,
 'compute_contract':{'max_stage_records':V2.MAX_STAGE_RECORDS,'max_plan_steps':V2.MAX_PLAN_STEPS,
                     'max_search_nodes':V2.MAX_SEARCH_NODES,'beam_width':V2.BEAM_WIDTH,
                     'old_v1_theoretical_worst_case_nodes_8_stages':old_worst_case_nodes},
 'candidate_source_sha256':fsha(CAND_SRC),'architecture_sha256':arch_sha,'parent_head_digest':head['canonical_head_digest'],
 'canonical_active':False,'promotion_applied':False,'state':'AUTHORIZED_FOR_SHADOW_ADMISSION' if passed else 'WITHHOLD',
 'semantic_boundary':'BOUNDED CONTINGENT PLANNING THAT REPLACES FIXED 8-STAGE/8-DEPTH TRUNCATION WITH EXPLICIT SEARCH-WORK BUDGETS AND BEAM PRUNING. NOT UNBOUNDED PLANNING.'
}
candidate['candidate_digest']=h(candidate);CAND_META.write_text(json.dumps(candidate,indent=2,sort_keys=True)+'\n')

state['candidate_history'].append({'round':state.get('round',12),'plane':'THINKING','candidate_digest':candidate['candidate_digest'],
 'selected_strategy':selected['id'],'fresh_score':holdout['score'],'baseline_score':old,'causal_drop':causal_gain,
 'status':'PASS_SHADOW' if passed else 'WITHHOLD'})
state['next_required_capability']=next_cap
state['state_digest']=h({k:v for k,v in state.items() if k!='state_digest'})
STATE.write_text(json.dumps(state,indent=2,sort_keys=True)+'\n')

run_id=str(os.getenv('GITHUB_RUN_ID') or 'LOCAL')
receipt={'schema':'yado.g2.thinking_plateau_self_evolution.v1',
 'status':'PASS_THINKING_PLATEAU_SELF_EVOLUTION_V1' if passed else 'WITHHOLD_THINKING_PLATEAU_SELF_EVOLUTION_V1',
 'selected_strategy':selected['id'],'validation':validation,'neutral_selection':sel,'fresh_validation':holdout,
 'causal_gain':causal_gain,'candidate_digest':candidate['candidate_digest'],'candidate_source_sha256':candidate['candidate_source_sha256'],
 'checks':checks,'canonical_mutation':False,'promotion_applied':False,'g3_genesis_performed':False,
 'next_required_capability':next_cap,'semantic_boundary':candidate['semantic_boundary']}
receipt['receipt_sha256']=h(receipt);OUT.write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')

e={'index':len(ledger['events']),'event_id':f"E{len(ledger['events'])+1:04d}_G2_THINKING_PLATEAU_SELF_EVOLUTION_V1",
 'event_type':'WORK_BUDGET_THINKING_SELF_EVOLUTION','status':'PASS_SHADOW' if passed else 'WITHHOLD',
 'generation':ledger['current_head'],'deficit':'THINKING_PLATEAU_SELF_EVOLUTION_V1',
 'effect':f"SELECTED={selected['id']}; FRESH={holdout['score']:.6f}; GAIN={causal_gain:.6f}; NEXT={next_cap}",
 'source_path':f'receipts/yado-thinking-plateau-self-evolution-v1-run-{run_id}.json','source_digest':receipt['receipt_sha256'],
 'run_id':run_id,'parent_event_hash':ledger['tail_event_hash'],'canonical_mutation':False,'promotion_applied':False}
e['event_hash']=event_hash(e);ledger['events'].append(e);ledger['event_count']=len(ledger['events']);ledger['tail_event_hash']=e['event_hash']
ledger['open_deficits']=[next_cap];ledger['ledger_digest']=h({k:v for k,v in ledger.items() if k!='ledger_digest'})
validate_ledger_v2(ledger);LEDGER.write_text(json.dumps(ledger,indent=2,sort_keys=True)+'\n')

print(json.dumps({'status':receipt['status'],'selected_strategy':selected['id'],'validation':validation,'fresh_validation':holdout,
 'causal_gain':causal_gain,'checks':checks,'next_required_capability':next_cap,'receipt_sha256':receipt['receipt_sha256']},indent=2,sort_keys=True))
if not passed:raise SystemExit('THINKING_PLATEAU_SELF_EVOLUTION_V1_WITHHELD')
