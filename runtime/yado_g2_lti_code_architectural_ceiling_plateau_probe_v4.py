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
from yado_bounded_compositional_program_repair_v3 import BoundedCompositionalProgramRepairV3

HEAD=REPO/'canonical'/'yado-main-head-g2.json'
ARCH=REPO/'canonical'/'yado-g2-architecture-v1.json'
LEDGER=REPO/'architecture'/'evolution-ledger.json'
STATE=REPO/'architecture'/'yado-g2-lti-ceiling-state-v1.json'
EXP=REPO/'experience'/'yado-external-agent-systems-learning-v1.json'
OUT=ROOT/'yado_g2_lti_code_architectural_ceiling_plateau_probe_v4_receipt.json'

CAP_CONJ='ALG-CONJUNCTIVE-RULE-INDUCER-V1'
CAP_REL='ALG-BOUNDED-DNF-RELATION-POLICY-INDUCER-V1'
CAP_RES='RESOURCE-PORTFOLIO-V1'

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def h(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def fsha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def avg(xs):return sum(xs)/max(1,len(xs))

head=load(HEAD);ledger=load(LEDGER);state=load(STATE);experience=load(EXP)
validate_ledger_v2(ledger)
if ledger.get('open_deficits')!=['LTI_CODE_ARCHITECTURAL_CEILING_PLATEAU_PROBE_V4']:raise RuntimeError('UNEXPECTED_FRONTIER')
if ledger.get('current_head_digest')!=head.get('canonical_head_digest'):raise RuntimeError('HEAD_LEDGER_MISMATCH')
if experience.get('status')!='LEARNED_EXTERNAL_EXPERIENCE':raise RuntimeError('EXTERNAL_EXPERIENCE_NOT_READY')
arch_sha=fsha(ARCH);head_sha=fsha(HEAD)

probes={};contracts={}

# LOGIC — fresh transfer inside active V2 compute contract.
L=BudgetAdaptiveCompositionalLogicV2
contracts['LOGIC']={'MAX_BOOLEAN_CELLS':L.MAX_BOOLEAN_CELLS,'MAX_POLYNOMIAL_TERMS':L.MAX_POLYNOMIAL_TERMS,'MAX_POLYNOMIAL_ROWS':L.MAX_POLYNOMIAL_ROWS}
n=26
rows=[]
for c in range(n+1):
    shift=(c*9+1)%n
    trues={(shift+j*5)%n for j in range(c)}
    x={f'l{i:02d}':i in trues for i in range(n)}
    rows.append({'input':x,'expected':'YES' if c%6 in {1,2,5} else 'NO'})
lm=L.learn_symmetric_boolean(rows)
logic_bool=all(L.predict_symmetric_boolean(lm,z['input'])==z['expected'] for z in rows)
pts=[(x,y) for x in range(-4,5) for y in range(-4,5)]
poly=[{'x':x,'y':y,'expected':3*x**4-2*x**2*y**2+y**4+2*x-y+7} for x,y in pts]
pm=L.fit_polynomial(poly,max_degree=4)
logic_poly=pm.get('kind')!='WITHHOLD' and all(L.predict_polynomial(pm,z['x'],z['y'])==Fraction(z['expected']) for z in poly)
probes['LOGIC']={'WIDTH26_FRESH':{'score':1.0 if logic_bool else 0.0},'DEGREE4_FRESH':{'score':1.0 if logic_poly else 0.0}}

# THINKING — exact next-step contract probes.
P=BoundedAdaptiveContingentPlannerV1;S=ContingentStage
contracts['THINKING']={'MAX_STAGES':P.MAX_STAGES,'MAX_PLAN_DEPTH':P.MAX_PLAN_DEPTH}
stage_n=P.MAX_STAGES+1
st=[S(f's{i}',1,.11,1,True,.1,False,()) for i in range(stage_n)]
pl=P.plan(.01,1.0,float(stage_n),st)
stage_score=min(1.0,pl.expected_confidence)
remaining=P.MAX_PLAN_DEPTH+1
ids=[f'd{i}' for i in range(remaining+1)]
ds=[S(ids[0],1,.02,1,True,.1,False,())]+[S(ids[j],1,.11,1,False,.1,False,(ids[j-1],)) for j in range(1,len(ids))]
dp=P.next_after_observation(.02,1.0,float(len(ids)),ds,ids[0],.02)
depth_score=min(1.0,dp.expected_confidence)
probes['THINKING']={
 'STAGE_WIDTH_PLUS_ONE_V4':{'score':stage_score,'bound':P.MAX_STAGES,'probe_value':stage_n,'sequence_len':len(pl.sequence)},
 'DEPENDENCY_DEPTH_PLUS_ONE_V4':{'score':depth_score,'bound':P.MAX_PLAN_DEPTH,'probe_value':remaining,'sequence_len':len(dp.sequence)}
}

# INTELLIGENCE — fresh distribution shift and width-2 composition inside V3 contract.
R=CoveragePrunedCompositionalSchemaRouterV3
contracts['INTELLIGENCE']={'MAX_FIELD_CELLS':R.MAX_FIELD_CELLS,'MAX_TRIGGER_WIDTH':R.MAX_TRIGGER_WIDTH,'MAX_TRIGGER_CANDIDATES':R.MAX_TRIGGER_CANDIDATES}
train=[];test=[];fields=[f'i{i:02d}' for i in range(25)]+['zz_signal']
for k in range(520):
    x={f:bool(((k+19)>>(j%8))&1) for j,f in enumerate(fields)}
    x['zz_signal']=bool((k//4)%2)
    train.append({'input':x,'expected':(CAP_REL,) if x['zz_signal'] else (CAP_CONJ,)})
for k in range(260):
    x={f:bool(((k+101)>>(j%7))&1) for j,f in enumerate(fields)}
    x['zz_signal']=bool((k//6)%2)
    test.append({'input':x,'expected':(CAP_REL,) if x['zz_signal'] else (CAP_CONJ,)})
rm=R.fit(train,CAP_CONJ)
width_score=sum(R.route(rm,z['input'])==z['expected'] for z in test)/len(test)
pairs=[]
for a,b,c,d,e,f in product([False,True],repeat=6):
    out=set()
    if a and d:out.add(CAP_REL)
    if c and f:out.add(CAP_RES)
    if not out:out.add(CAP_CONJ)
    for _ in range(6):pairs.append({'input':{'a':a,'b':b,'c':c,'d':d,'e':e,'f':f},'expected':tuple(sorted(out))})
prm=R.fit(pairs,CAP_CONJ)
pair_score=sum(R.route(prm,z['input'])==z['expected'] for z in pairs)/len(pairs)
probes['INTELLIGENCE']={'WIDTH26_FRESH':{'score':width_score},'PAIRWISE_TOPOLOGY_FRESH':{'score':pair_score}}

# CODE — derive probes from V3 declared scope.
C=BoundedCompositionalProgramRepairV3
contracts['CODE']={
 'COMPONENT_ID':C.COMPONENT_ID,
 'MAX_EDIT_DEPTH':C.MAX_EDIT_DEPTH,
 'MAX_CANDIDATES':C.MAX_CANDIDATES,
 'SAFE_STRUCTURAL_WRAPPERS':['abs','min','max'],
 'FUNCTION_SCOPE':'EXACTLY_ONE_FUNCTION'
}
def repair_score(src,fn,train,hold,depth=None):
    try:
        r=C.repair(src,fn,train,max_candidates=C.MAX_CANDIDATES,max_edit_depth=depth or C.MAX_EDIT_DEPTH)
        if not r.get('source'):return 0.0,r
        s=sum(C.execute(r['source'],fn,args)==exp for args,exp in hold)/len(hold)
        return s,r
    except Exception as e:return 0.0,{'error':type(e).__name__}

# In-contract regression: exactly two edits.
tr2=[((1,2),6),((2,4),9),((-2,3),4),((0,0),3)]
ho2=[((5,6),14),((-3,-4),-4),((0,7),10)]
two_score,two_r=repair_score('def f(x,y):\n    return x-y+1\n','f',tr2,ho2)

# Next depth: three independent edits: x-y+1 -> x+y+4.
tr3=[((1,2),7),((2,4),10),((-2,3),5),((0,0),4)]
ho3=[((5,6),15),((-3,-4),-3),((0,7),11)]
three_score,three_r=repair_score('def f(x,y):\n    return x-y+1\n','f',tr3,ho3)

# New expression form: conditional expression max-like but branch-dependent.
tri=[((-3,),3),((-1,),1),((0,),0),((2,),4),((5,),10)]
hoi=[((-7,),7),((3,),6),((8,),16)]
ifexpr_score,if_r=repair_score('def f(x):\n    return x\n','f',tri,hoi)

# Function-shape evolution: current validator insists exactly one function and no helper insertion.
helper_train=[((1,2),9),((2,4),18),((-2,3),3)]
helper_hold=[((5,6),33),((-3,-4),-21)]
helper_source='def f(x,y):\n    return x+y\n'
# Oracle is 3*(x+y), expressible by one Mult insertion but not by current atomic structural wrappers.
helper_score,helper_r=repair_score(helper_source,'f',helper_train,helper_hold)

probes['CODE']={
 'TWO_EDIT_REGRESSION':{'score':two_score,'detail':two_r.get('reason') or two_r.get('edit_depth')},
 'THREE_EDIT_PLUS_ONE':{'score':three_score,'bound':C.MAX_EDIT_DEPTH,'probe_value':C.MAX_EDIT_DEPTH+1,'detail':three_r.get('reason') or three_r.get('edit_depth')},
 'CONDITIONAL_EXPRESSION_INSERTION':{'score':ifexpr_score,'detail':if_r.get('reason') or if_r.get('edit_depth')},
 'NEW_EXPRESSION_SHAPE_MULT_WRAP':{'score':helper_score,'detail':helper_r.get('reason') or helper_r.get('edit_depth')}
}

plane_scores={p:avg([float(v['score']) for v in fam.values()]) for p,fam in probes.items()}
severity={p:1.0-s for p,s in plane_scores.items()}

meta={'LOGIC':(.20,.03,.45),'THINKING':(.34,.06,.80),'INTELLIGENCE':(.31,.05,.88),'CODE':(.28,.05,.94)}
tokens={};cands=[]
for i,p in enumerate(sorted(plane_scores)):
    tok='opaque_'+h({'plateau_probe':4,'slot':i,'head':head['canonical_head_digest'],'experience':experience['experience_digest']})[:18]
    tokens[tok]=p
    cx,rk,nv=meta[p]
    cands.append(EvidenceCandidate(tok,severity[p],cx,rk,nv))
sel=NeutralEvidenceProfileSelectorV1.select(cands)
selected=tokens[sel['selected_token']]
threshold=float(state['ceiling_definition']['success_threshold_per_family'])
new_deficit=plane_scores[selected]<threshold
if new_deficit:
    streak=0;next_cap=f'{selected}_PLATEAU_SELF_EVOLUTION_V2' if selected=='CODE' else f'{selected}_PLATEAU_SELF_EVOLUTION_V1';probe_status='FRONTIER_FOUND'
else:
    streak=int(state.get('plateau_streak',0))+1
    req=int(state['ceiling_definition']['plateau_required_consecutive_rounds'])
    next_cap='LTI_CODE_ARCHITECTURAL_CEILING_PLATEAU_PROBE_V5' if streak<req else 'LTI_CODE_ARCHITECTURAL_CEILING_EMPIRICAL_PLATEAU_CONFIRMATION_V1'
    probe_status='PLATEAU_ROUND'

checks={
 'code_v3_active':head.get('unified_core',{}).get('code_self_repair_component')=='ALG-G2-BOUNDED-COMPOSITIONAL-PROGRAM-REPAIR-V3',
 'external_experience_available':experience.get('status')=='LEARNED_EXTERNAL_EXPERIENCE',
 'four_planes_probed':set(probes)=={'LOGIC','THINKING','INTELLIGENCE','CODE'},
 'architecture_immutable':fsha(ARCH)==arch_sha,
 'canonical_head_immutable':fsha(HEAD)==head_sha and ledger.get('current_head_digest')==head.get('canonical_head_digest'),
 'g3_not_started':head.get('g3_genesis_performed') is False
}
passed=all(checks.values())

state['round']=int(state.get('round',0))+1
state['plateau_streak']=streak
state['plateau_probe']={'probe_version':4,'scope':'LOGIC_THINKING_INTELLIGENCE_CODE','contract_snapshot':contracts,'probes':probes,
 'plane_scores':plane_scores,'deficit_severity':severity,'neutral_selection':sel,'selected_plane':selected,'status':probe_status,
 'external_experience_digest':experience['experience_digest'],'architecture_sha256':arch_sha}
state['self_selected_weakest_plane']=selected
state['status']='EVOLVING_TO_CEILING' if new_deficit else 'PLATEAU_SEARCH'
state['next_required_capability']=next_cap
state['state_digest']=h({k:v for k,v in state.items() if k!='state_digest'})
STATE.write_text(json.dumps(state,indent=2,sort_keys=True)+'\n')

run_id=str(os.getenv('GITHUB_RUN_ID') or 'LOCAL')
receipt={'schema':'yado.g2.lti_code_architectural_ceiling_plateau_probe.v4',
 'status':'PASS_LTI_CODE_ARCHITECTURAL_CEILING_PLATEAU_PROBE_V4' if passed else 'WITHHOLD_LTI_CODE_ARCHITECTURAL_CEILING_PLATEAU_PROBE_V4',
 'probe_status':probe_status,'contract_snapshot':contracts,'probes':probes,'plane_scores':plane_scores,'deficit_severity':severity,
 'neutral_selection':sel,'self_selected_plane':selected,'new_deficit_found':new_deficit,'plateau_streak':streak,
 'external_experience_digest':experience['experience_digest'],'checks':checks,'architecture_sha256':arch_sha,
 'canonical_mutation':False,'promotion_applied':False,'g3_genesis_performed':False,'next_required_capability':next_cap,
 'semantic_boundary':'FOUR-PLANE FIXED-G2 FRONTIER SEARCH AFTER CODE V3 AND EXTERNAL EXPERIENCE. CODE PROBES ARE ONE STEP BEYOND DECLARED EDIT/STRUCTURE SCOPE; NO CANONICAL MUTATION OCCURS.'
}
receipt['receipt_sha256']=h(receipt);OUT.write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')

e={'index':len(ledger['events']),'event_id':f"E{len(ledger['events'])+1:04d}_G2_LTI_CODE_PLATEAU_PROBE_V4",
 'event_type':'FIXED_ARCHITECTURE_LTI_CODE_PLATEAU_PROBE','status':'PASS_SHADOW' if passed else 'WITHHOLD',
 'generation':ledger['current_head'],'deficit':'LTI_CODE_ARCHITECTURAL_CEILING_PLATEAU_PROBE_V4',
 'effect':f"SELECTED={selected}; SCORES={canon(plane_scores)}; NEXT={next_cap}",
 'source_path':f'receipts/yado-g2-lti-code-architectural-ceiling-plateau-probe-v4-run-{run_id}.json','source_digest':receipt['receipt_sha256'],
 'run_id':run_id,'parent_event_hash':ledger['tail_event_hash'],'canonical_mutation':False,'promotion_applied':False}
e['event_hash']=event_hash(e);ledger['events'].append(e);ledger['event_count']=len(ledger['events']);ledger['tail_event_hash']=e['event_hash']
ledger['open_deficits']=[next_cap];ledger['ledger_digest']=h({k:v for k,v in ledger.items() if k!='ledger_digest'})
validate_ledger_v2(ledger);LEDGER.write_text(json.dumps(ledger,indent=2,sort_keys=True)+'\n')

print(json.dumps({'status':receipt['status'],'probe_status':probe_status,'plane_scores':plane_scores,'probes':probes,
 'self_selected_plane':selected,'next_required_capability':next_cap,'receipt_sha256':receipt['receipt_sha256']},indent=2,sort_keys=True))
if not passed:raise SystemExit('LTI_CODE_PLATEAU_PROBE_V4_WITHHELD')
