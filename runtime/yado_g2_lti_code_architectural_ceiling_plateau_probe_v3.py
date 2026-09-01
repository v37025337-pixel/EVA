from __future__ import annotations
from pathlib import Path
from itertools import product
from fractions import Fraction
import hashlib,json,os,sys

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
sys.path.insert(0,str(ROOT))

from yado_evolution_ledger_v2 import validate_ledger_v2,event_hash
from yado_neutral_evidence_profile_selector_v1 import NeutralEvidenceProfileSelectorV1,EvidenceCandidate
from yado_budget_adaptive_compositional_logic_v2 import BudgetAdaptiveCompositionalLogicV2
from yado_bounded_adaptive_contingent_planner_v1 import BoundedAdaptiveContingentPlannerV1,ContingentStage
from yado_coverage_pruned_compositional_schema_router_v3 import CoveragePrunedCompositionalSchemaRouterV3
from yado_bounded_program_repair_v2 import BoundedProgramRepairV1

HEAD=REPO/'canonical'/'yado-main-head-g2.json'
ARCH=REPO/'canonical'/'yado-g2-architecture-v1.json'
LEDGER=REPO/'architecture'/'evolution-ledger.json'
STATE=REPO/'architecture'/'yado-g2-lti-ceiling-state-v1.json'
OUT=ROOT/'yado_g2_lti_architectural_ceiling_plateau_probe_v3_receipt.json'
CAP_CONJ='ALG-CONJUNCTIVE-RULE-INDUCER-V1'
CAP_REL='ALG-BOUNDED-DNF-RELATION-POLICY-INDUCER-V1'
CAP_RES='RESOURCE-PORTFOLIO-V1'

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def h(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def fsha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def avg(xs):return sum(xs)/max(1,len(xs))

head=load(HEAD);ledger=load(LEDGER);state=load(STATE)
validate_ledger_v2(ledger)
if ledger.get('open_deficits')!=['LTI_ARCHITECTURAL_CEILING_PLATEAU_PROBE_V3']:raise RuntimeError('UNEXPECTED_FRONTIER')
if ledger.get('current_head_digest')!=head.get('canonical_head_digest'):raise RuntimeError('HEAD_LEDGER_MISMATCH')
arch_sha=fsha(ARCH);head_sha=fsha(HEAD)

probes={};contracts={}

# LOGIC: structural transfer inside the active work budget.
L=BudgetAdaptiveCompositionalLogicV2
contracts['LOGIC']={'MAX_BOOLEAN_CELLS':L.MAX_BOOLEAN_CELLS,'MAX_POLYNOMIAL_TERMS':L.MAX_POLYNOMIAL_TERMS,'MAX_POLYNOMIAL_ROWS':L.MAX_POLYNOMIAL_ROWS}
rows=[]
n=24
for c in range(n+1):
    shift=(c*5)%n
    trues={(shift+j)%n for j in range(c)}
    rows.append({'input':{f'l{i:02d}':i in trues for i in range(n)},'expected':'YES' if c%5 in {1,4} else 'NO'})
lm=L.learn_symmetric_boolean(rows)
logic_bool=all(L.predict_symmetric_boolean(lm,z['input'])==z['expected'] for z in rows)
pts=[(x,y) for x in range(-4,5) for y in range(-4,5)]
poly=[{'x':x,'y':y,'expected':x**4-2*x*x*y*y+3*y**4+x+1} for x,y in pts]
pm=L.fit_polynomial(poly,max_degree=4)
logic_poly=pm.get('kind')!='WITHHOLD' and all(L.predict_polynomial(pm,z['x'],z['y'])==Fraction(z['expected']) for z in poly)
p5=[{'x':x,'y':y,'expected':x**5+y} for x,y in pts];m5=L.fit_polynomial(p5,max_degree=5)
logic_budget=m5.get('kind')=='WITHHOLD' and m5.get('reason')=='POLYNOMIAL_TERM_BUDGET'
probes['LOGIC']={
 'WIDTH24_STRUCTURAL_TRANSFER':{'score':1.0 if logic_bool else 0.0},
 'DEGREE4_STRUCTURAL_TRANSFER':{'score':1.0 if logic_poly else 0.0},
 'TERM_BUDGET_FAIL_CLOSED':{'score':1.0 if logic_budget else 0.0},
}

# THINKING: one step beyond current stage/depth contract.
P=BoundedAdaptiveContingentPlannerV1;S=ContingentStage
contracts['THINKING']={'MAX_STAGES':P.MAX_STAGES,'MAX_PLAN_DEPTH':P.MAX_PLAN_DEPTH}
stage_n=P.MAX_STAGES+1
stages=[S(f's{i}',1,.1,1,True,.1,False,()) for i in range(stage_n)]
pl=P.plan(.1,1.0,float(stage_n),stages)
stage_score=min(1.0,pl.expected_confidence)
remaining=P.MAX_PLAN_DEPTH+1
ids=[f'd{i}' for i in range(remaining+1)]
dep=[S(ids[0],1,.05,1,True,.1,False,())]+[S(ids[j],1,.1,1,False,.1,False,(ids[j-1],)) for j in range(1,len(ids))]
dp=P.next_after_observation(.05,1.0,float(len(ids)),dep,ids[0],.05)
dep_score=min(1.0,dp.expected_confidence)
probes['THINKING']={
 'STAGE_WIDTH_PLUS_ONE':{'score':stage_score,'bound':P.MAX_STAGES,'probe_value':stage_n,'sequence_len':len(pl.sequence)},
 'DEPENDENCY_DEPTH_PLUS_ONE':{'score':dep_score,'bound':P.MAX_PLAN_DEPTH,'probe_value':remaining,'sequence_len':len(dp.sequence)},
}

# INTELLIGENCE V3: width, pairwise composition and spurious-pair suppression.
R=CoveragePrunedCompositionalSchemaRouterV3
contracts['INTELLIGENCE']={'MAX_FIELD_CELLS':R.MAX_FIELD_CELLS,'MAX_TRIGGER_WIDTH':R.MAX_TRIGGER_WIDTH,'MAX_TRIGGER_CANDIDATES':R.MAX_TRIGGER_CANDIDATES}
train=[];test=[];fields=[f'i{i:02d}' for i in range(22)]+['zz_signal']
for k in range(480):
    x={f:bool(((k+13)>>(j%8))&1) for j,f in enumerate(fields)}
    x['zz_signal']=bool((k//3)%2);train.append({'input':x,'expected':(CAP_REL,) if x['zz_signal'] else (CAP_CONJ,)})
for k in range(240):
    x={f:bool(((k+71)>>(j%7))&1) for j,f in enumerate(fields)}
    x['zz_signal']=bool((k//5)%2);test.append({'input':x,'expected':(CAP_REL,) if x['zz_signal'] else (CAP_CONJ,)})
rm=R.fit(train,CAP_CONJ);width_score=sum(R.route(rm,z['input'])==z['expected'] for z in test)/len(test)
pairs=[]
for a,b,c,d in product([False,True],repeat=4):
    out=set()
    if a and b:out.add(CAP_REL)
    if c and d:out.add(CAP_RES)
    if not out:out.add(CAP_CONJ)
    for _ in range(10):pairs.append({'input':{'a':a,'b':b,'c':c,'d':d},'expected':tuple(sorted(out))})
prm=R.fit(pairs,CAP_CONJ);pair_score=sum(R.route(prm,z['input'])==z['expected'] for z in pairs)/len(pairs)
probes['INTELLIGENCE']={
 'WIDTH23_TRANSFER':{'score':width_score},
 'PAIRWISE_COMPOSITION':{'score':pair_score},
}

# CODE: active bounded program repair contract.
C=BoundedProgramRepairV1
contracts['CODE']={
 'COMPONENT_ID':C.COMPONENT_ID,
 'MUTATION_FAMILIES':['binop','compare','boolop','constant'],
 'MAX_EDIT_DEPTH':1,
 'STRUCTURAL_INSERTION':False,
 'SEMANTIC_SCOPE':'ONE_SAFE_PYTHON_FUNCTION'
}
def repair_pass(source,fn,examples,holdout):
    r=C.repair(source,fn,examples,max_candidates=12000)
    if not r.get('source'):return 0.0
    try:
        return sum(C.execute(r['source'],fn,args)==expected for args,expected in holdout)/len(holdout)
    except Exception:return 0.0

op_train=[((1,2),3),((5,7),12),((-2,6),4)]
op_hold=[((9,4),13),((-5,-7),-12),((0,8),8)]
op_score=repair_pass('def f(x,y):\n    return x-y\n','f',op_train,op_hold)

const_train=[((1,),4),((5,),8),((-2,),1)]
const_hold=[((9,),12),((-5,),-2),((0,),3)]
const_score=repair_pass('def f(x):\n    return x+1\n','f',const_train,const_hold)

two_train=[((1,),4),((5,),8),((-2,),1)]
two_hold=[((9,),12),((-5,),-2),((0,),3)]
two_score=repair_pass('def f(x):\n    return x-1\n','f',two_train,two_hold)

guard_train=[((-3,),0),((-1,),0),((0,),0),((2,),2),((7,),7)]
guard_hold=[((-9,),0),((4,),4),((11,),11)]
guard_score=repair_pass('def f(x):\n    return x\n','f',guard_train,guard_hold)

probes['CODE']={
 'SINGLE_OPERATOR_REPAIR':{'score':op_score},
 'SINGLE_CONSTANT_REPAIR':{'score':const_score},
 'TWO_EDIT_REPAIR':{'score':two_score,'reason':'REQUIRES_COMPOSITION_OF_AT_LEAST_TWO_AST_EDITS'},
 'STRUCTURAL_GUARD_INSERTION':{'score':guard_score,'reason':'REQUIRES_NEW_CONTROL_OR_EXPRESSION_STRUCTURE'},
}

plane_scores={p:avg([float(v['score']) for v in fam.values()]) for p,fam in probes.items()}
severity={p:1.0-s for p,s in plane_scores.items()}

# Neutral selection: opaque tokens only, names mapped after ranking.
meta={
 'LOGIC':(.20,.03,.45),
 'THINKING':(.34,.06,.80),
 'INTELLIGENCE':(.31,.05,.88),
 'CODE':(.27,.05,.92),
}
tokens={};cands=[]
for i,p in enumerate(sorted(plane_scores)):
    tok='opaque_'+h({'plateau_probe':3,'slot':i,'head':head['canonical_head_digest']})[:18]
    tokens[tok]=p;cx,rk,nv=meta[p]
    cands.append(EvidenceCandidate(tok,severity[p],cx,rk,nv))
sel=NeutralEvidenceProfileSelectorV1.select(cands)
selected=tokens[sel['selected_token']]
threshold=float(state['ceiling_definition']['success_threshold_per_family'])
new_deficit=plane_scores[selected]<threshold
if new_deficit:
    streak=0
    next_cap=f'{selected}_PLATEAU_SELF_EVOLUTION_V1'
    probe_status='FRONTIER_FOUND'
else:
    streak=int(state.get('plateau_streak',0))+1
    req=int(state['ceiling_definition']['plateau_required_consecutive_rounds'])
    next_cap='LTI_CODE_ARCHITECTURAL_CEILING_PLATEAU_PROBE_V4' if streak<req else 'LTI_CODE_ARCHITECTURAL_CEILING_EMPIRICAL_PLATEAU_CONFIRMATION_V1'
    probe_status='PLATEAU_ROUND'

checks={
 'logic_v2_active':head.get('unified_core',{}).get('logic_active_component')=='ALG-G2-BUDGET-ADAPTIVE-COMPOSITIONAL-LOGIC-V2',
 'intelligence_v3_active':head.get('unified_core',{}).get('intelligence_active_router_component')=='ALG-G2-COVERAGE-PRUNED-COMPOSITIONAL-SCHEMA-ROUTER-V3',
 'four_planes_probed':set(probes)=={'LOGIC','THINKING','INTELLIGENCE','CODE'},
 'architecture_immutable':fsha(ARCH)==arch_sha,
 'canonical_head_immutable':fsha(HEAD)==head_sha and ledger.get('current_head_digest')==head.get('canonical_head_digest'),
 'g3_not_started':head.get('g3_genesis_performed') is False,
}
passed=all(checks.values())

state['round']=int(state.get('round',0))+1
state['plateau_streak']=streak
state['plateau_probe']={
 'probe_version':3,'scope':'LOGIC_THINKING_INTELLIGENCE_CODE',
 'contract_snapshot':contracts,'probes':probes,'plane_scores':plane_scores,
 'deficit_severity':severity,'neutral_selection':sel,'selected_plane':selected,
 'status':probe_status,'architecture_sha256':arch_sha
}
state['self_selected_weakest_plane']=selected
state['status']='EVOLVING_TO_CEILING' if new_deficit else 'PLATEAU_SEARCH'
state['next_required_capability']=next_cap
state['state_digest']=h({k:v for k,v in state.items() if k!='state_digest'})
STATE.write_text(json.dumps(state,indent=2,sort_keys=True)+'\n')

run_id=str(os.getenv('GITHUB_RUN_ID') or 'LOCAL')
receipt={
 'schema':'yado.g2.lti_code_architectural_ceiling_plateau_probe.v3',
 'status':'PASS_LTI_CODE_ARCHITECTURAL_CEILING_PLATEAU_PROBE_V3' if passed else 'WITHHOLD_LTI_CODE_ARCHITECTURAL_CEILING_PLATEAU_PROBE_V3',
 'probe_status':probe_status,'contract_snapshot':contracts,'probes':probes,
 'plane_scores':plane_scores,'deficit_severity':severity,'neutral_selection':sel,
 'self_selected_plane':selected,'new_deficit_found':new_deficit,
 'plateau_streak':streak,'checks':checks,'architecture_sha256':arch_sha,
 'canonical_mutation':False,'promotion_applied':False,'g3_genesis_performed':False,
 'next_required_capability':next_cap,
 'semantic_boundary':'EXTENDS THE FIXED-ARCHITECTURE PLATEAU SEARCH TO CODE SELF-MAINTENANCE. CODE MEANS BOUNDED SOURCE REPAIR/EVOLUTION CAPABILITY, NOT UNRESTRICTED SELF-MODIFICATION.'
}
receipt['receipt_sha256']=h(receipt)
OUT.write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')

e={'index':len(ledger['events']),
 'event_id':f"E{len(ledger['events'])+1:04d}_G2_LTI_CODE_PLATEAU_PROBE_V3",
 'event_type':'FIXED_ARCHITECTURE_LTI_CODE_PLATEAU_PROBE',
 'status':'PASS_SHADOW' if passed else 'WITHHOLD',
 'generation':ledger['current_head'],
 'deficit':'LTI_ARCHITECTURAL_CEILING_PLATEAU_PROBE_V3',
 'effect':f"SELECTED={selected}; SCORES={canon(plane_scores)}; NEXT={next_cap}",
 'source_path':f'receipts/yado-g2-lti-code-architectural-ceiling-plateau-probe-v3-run-{run_id}.json',
 'source_digest':receipt['receipt_sha256'],'run_id':run_id,
 'parent_event_hash':ledger['tail_event_hash'],
 'canonical_mutation':False,'promotion_applied':False}
e['event_hash']=event_hash(e)
ledger['events'].append(e);ledger['event_count']=len(ledger['events'])
ledger['tail_event_hash']=e['event_hash'];ledger['open_deficits']=[next_cap]
ledger['ledger_digest']=h({k:v for k,v in ledger.items() if k!='ledger_digest'})
validate_ledger_v2(ledger)
LEDGER.write_text(json.dumps(ledger,indent=2,sort_keys=True)+'\n')

print(json.dumps({
 'status':receipt['status'],'probe_status':probe_status,
 'plane_scores':plane_scores,'probes':probes,
 'self_selected_plane':selected,'next_required_capability':next_cap,
 'receipt_sha256':receipt['receipt_sha256']
},indent=2,sort_keys=True))
if not passed:raise SystemExit('LTI_CODE_PLATEAU_PROBE_V3_WITHHELD')
