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
from yado_ambiguity_aware_program_repair_v11 import AmbiguityAwareProgramRepairV11

HEAD=REPO/'canonical'/'yado-main-head-g2.json'
ARCH=REPO/'canonical'/'yado-g2-architecture-v1.json'
LEDGER=REPO/'architecture'/'evolution-ledger.json'
STATE=REPO/'architecture'/'yado-g2-lti-ceiling-state-v1.json'
OUT=ROOT/'yado_g2_lti_code_architectural_ceiling_plateau_probe_v5_receipt.json'

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
if ledger.get('open_deficits')!=['LTI_CODE_ARCHITECTURAL_CEILING_PLATEAU_PROBE_V5']:raise RuntimeError('UNEXPECTED_FRONTIER')
if ledger.get('current_head_digest')!=head.get('canonical_head_digest'):raise RuntimeError('HEAD_LEDGER_MISMATCH')
arch_sha=fsha(ARCH);head_sha=fsha(HEAD)
probes={};contracts={}

# LOGIC fresh transfer inside active work budgets.
L=BudgetAdaptiveCompositionalLogicV2
contracts['LOGIC']={'MAX_BOOLEAN_CELLS':L.MAX_BOOLEAN_CELLS,'MAX_POLYNOMIAL_TERMS':L.MAX_POLYNOMIAL_TERMS,'MAX_POLYNOMIAL_ROWS':L.MAX_POLYNOMIAL_ROWS}
n=28
rows=[]
for c in range(n+1):
    shift=(c*11+3)%n
    trues={(shift+j*3)%n for j in range(c)}
    x={f'l{i:02d}':i in trues for i in range(n)}
    rows.append({'input':x,'expected':'Y' if c%7 in {1,3,6} else 'N'})
lm=L.learn_symmetric_boolean(rows)
logic_bool=all(L.predict_symmetric_boolean(lm,z['input'])==z['expected'] for z in rows)
pts=[(x,y) for x in range(-4,5) for y in range(-4,5)]
poly=[{'x':x,'y':y,'expected':2*x**4+x*x*y*y-3*y**4+4*x-2*y+5} for x,y in pts]
pm=L.fit_polynomial(poly,max_degree=4)
logic_poly=pm.get('kind')!='WITHHOLD' and all(L.predict_polynomial(pm,z['x'],z['y'])==Fraction(z['expected']) for z in poly)
probes['LOGIC']={'WIDTH28_FRESH':{'score':1.0 if logic_bool else 0.0},'DEGREE4_FRESH_V5':{'score':1.0 if logic_poly else 0.0}}

# THINKING current next boundary.
P=BoundedAdaptiveContingentPlannerV1;S=ContingentStage
contracts['THINKING']={'MAX_STAGES':P.MAX_STAGES,'MAX_PLAN_DEPTH':P.MAX_PLAN_DEPTH}
stage_n=P.MAX_STAGES+1
st=[S(f's{i}',1,.12,1,True,.1,False,()) for i in range(stage_n)]
pl=P.plan(.02,1.0,float(stage_n),st)
stage_score=min(1.0,pl.expected_confidence)
remaining=P.MAX_PLAN_DEPTH+1
ids=[f'd{i}' for i in range(remaining+1)]
ds=[S(ids[0],1,.03,1,True,.1,False,())]+[S(ids[j],1,.12,1,False,.1,False,(ids[j-1],)) for j in range(1,len(ids))]
dp=P.next_after_observation(.03,1.0,float(len(ids)),ds,ids[0],.03)
depth_score=min(1.0,dp.expected_confidence)
probes['THINKING']={
 'STAGE_WIDTH_PLUS_ONE_V5':{'score':stage_score,'bound':P.MAX_STAGES,'probe_value':stage_n,'sequence_len':len(pl.sequence)},
 'DEPENDENCY_DEPTH_PLUS_ONE_V5':{'score':depth_score,'bound':P.MAX_PLAN_DEPTH,'probe_value':remaining,'sequence_len':len(dp.sequence)}
}

# INTELLIGENCE fresh distribution/composition within active V3 contract.
R=CoveragePrunedCompositionalSchemaRouterV3
contracts['INTELLIGENCE']={'MAX_FIELD_CELLS':R.MAX_FIELD_CELLS,'MAX_TRIGGER_WIDTH':R.MAX_TRIGGER_WIDTH,'MAX_TRIGGER_CANDIDATES':R.MAX_TRIGGER_CANDIDATES}
train=[];test=[];fields=[f'i{i:02d}' for i in range(27)]+['zz_signal']
for k in range(560):
    x={f:bool(((k+29)>>(j%8))&1) for j,f in enumerate(fields)}
    x['zz_signal']=bool((k//5)%2)
    train.append({'input':x,'expected':(CAP_REL,) if x['zz_signal'] else (CAP_CONJ,)})
for k in range(280):
    x={f:bool(((k+131)>>(j%7))&1) for j,f in enumerate(fields)}
    x['zz_signal']=bool((k//7)%2)
    test.append({'input':x,'expected':(CAP_REL,) if x['zz_signal'] else (CAP_CONJ,)})
rm=R.fit(train,CAP_CONJ)
width_score=sum(R.route(rm,z['input'])==z['expected'] for z in test)/len(test)
pairs=[]
for a,b,c,d,e,f in product([False,True],repeat=6):
    out=set()
    if a and e:out.add(CAP_REL)
    if c and f:out.add(CAP_RES)
    if not out:out.add(CAP_CONJ)
    for _ in range(5):pairs.append({'input':{'a':a,'b':b,'c':c,'d':d,'e':e,'f':f},'expected':tuple(sorted(out))})
prm=R.fit(pairs,CAP_CONJ)
pair_score=sum(R.route(prm,z['input'])==z['expected'] for z in pairs)/len(pairs)
probes['INTELLIGENCE']={'WIDTH28_FRESH':{'score':width_score},'PAIRWISE_COMPOSITION_FRESH_V5':{'score':pair_score}}

# CODE current V11 contract: ambiguity withhold, evidence resolution, nested depth2, regressions.
C=AmbiguityAwareProgramRepairV11
contracts['CODE']={'COMPONENT_ID':C.COMPONENT_ID,'MAX_CANDIDATES':C.MAX_CANDIDATES,
 'MAX_EDIT_DEPTH':C.MAX_EDIT_DEPTH,'MAX_CONDITIONAL_DEPTH':C.MAX_CONDITIONAL_DEPTH,
 'SEMANTIC_SCOPE':'ONE_SAFE_PYTHON_FUNCTION_WITH_AMBIGUITY_WITHHOLD'}

amb=[((-8,),-16),((-5,),-10),((0,),0),((1,),1),((5,),16),((9,),28)]
ra=C.repair('def f(x):\n    return x\n','f',amb,max_candidates=24000)
amb_score=1.0 if ra.get('source') is None and ra.get('reason')=='AMBIGUOUS_UNSEEN_THRESHOLD' else 0.0
resolved=amb+[((2,),2),((3,),3),((4,),4)]
rr=C.repair('def f(x):\n    return x\n','f',resolved,max_candidates=24000)
resolved_hold=[((-10,),-20),((2,),2),((4,),4),((6,),19),((11,),34)]
resolved_score=0.0 if not rr.get('source') else sum(C.execute(rr['source'],'f',a)==e for a,e in resolved_hold)/len(resolved_hold)
nested=[
 ((-5,),10),((-4,),8),((-3,),6),
 ((-2,),-4),((-1,),-2),((0,),0),((1,),2),
 ((2,),9),((3,),13),((4,),17)
]
nr=C.repair('def f(x):\n    return x\n','f',nested,max_candidates=24000)
nested_hold=[((-8,),16),((-2,),-4),((1,),2),((2,),9),((6,),25)]
nested_score=0.0 if not nr.get('source') else sum(C.execute(nr['source'],'f',a)==e for a,e in nested_hold)/len(nested_hold)
two=[((1,2),6),((2,4),9),((-2,3),4),((0,0),3)]
tr=C.repair('def f(x,y):\n    return x-y+1\n','f',two,max_candidates=24000)
two_hold=[((5,6),14),((-3,-4),-4),((0,7),10)]
two_score=0.0 if not tr.get('source') else sum(C.execute(tr['source'],'f',a)==e for a,e in two_hold)/len(two_hold)
probes['CODE']={
 'AMBIGUOUS_WITHHOLD_FRESH_V5':{'score':amb_score},
 'RESOLVED_COMMIT_FRESH_V5':{'score':resolved_score},
 'NESTED_DEPTH2_FRESH_V5':{'score':nested_score},
 'TWO_EDIT_REGRESSION_V5':{'score':two_score}
}

plane_scores={p:avg([float(v['score']) for v in fam.values()]) for p,fam in probes.items()}
severity={p:1.0-s for p,s in plane_scores.items()}
meta={'LOGIC':(.20,.03,.45),'THINKING':(.34,.06,.82),'INTELLIGENCE':(.31,.05,.88),'CODE':(.33,.04,.94)}
tokens={};cands=[]
for i,p in enumerate(sorted(plane_scores)):
    tok='opaque_'+h({'plateau_probe':5,'slot':i,'head':head['canonical_head_digest']})[:18]
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
    next_cap='LTI_CODE_ARCHITECTURAL_CEILING_PLATEAU_PROBE_V6' if streak<req else 'LTI_CODE_ARCHITECTURAL_CEILING_EMPIRICAL_PLATEAU_CONFIRMATION_V1'
    probe_status='PLATEAU_ROUND'

checks={
 'logic_v2_active':head.get('unified_core',{}).get('logic_active_component')=='ALG-G2-BUDGET-ADAPTIVE-COMPOSITIONAL-LOGIC-V2',
 'intelligence_v3_active':head.get('unified_core',{}).get('intelligence_active_router_component')=='ALG-G2-COVERAGE-PRUNED-COMPOSITIONAL-SCHEMA-ROUTER-V3',
 'code_v11_active':head.get('unified_core',{}).get('code_self_repair_component')=='ALG-G2-AMBIGUITY-AWARE-PROGRAM-REPAIR-V11',
 'four_planes_probed':set(probes)=={'LOGIC','THINKING','INTELLIGENCE','CODE'},
 'architecture_immutable':fsha(ARCH)==arch_sha,
 'canonical_head_immutable':fsha(HEAD)==head_sha and ledger.get('current_head_digest')==head.get('canonical_head_digest'),
 'g3_not_started':head.get('g3_genesis_performed') is False
}
passed=all(checks.values())

state['round']=int(state.get('round',0))+1
state['plateau_streak']=streak
state['plateau_probe']={'probe_version':5,'scope':'LOGIC_THINKING_INTELLIGENCE_CODE','contract_snapshot':contracts,
 'probes':probes,'plane_scores':plane_scores,'deficit_severity':severity,'neutral_selection':sel,
 'selected_plane':selected,'status':probe_status,'architecture_sha256':arch_sha}
state['self_selected_weakest_plane']=selected
state['status']='EVOLVING_TO_CEILING' if new_deficit else 'PLATEAU_SEARCH'
state['next_required_capability']=next_cap
state['state_digest']=h({k:v for k,v in state.items() if k!='state_digest'})
STATE.write_text(json.dumps(state,indent=2,sort_keys=True)+'\n')

run_id=str(os.getenv('GITHUB_RUN_ID') or 'LOCAL')
receipt={'schema':'yado.g2.lti_code_architectural_ceiling_plateau_probe.v5',
 'status':'PASS_LTI_CODE_ARCHITECTURAL_CEILING_PLATEAU_PROBE_V5' if passed else 'WITHHOLD_LTI_CODE_ARCHITECTURAL_CEILING_PLATEAU_PROBE_V5',
 'probe_status':probe_status,'contract_snapshot':contracts,'probes':probes,'plane_scores':plane_scores,
 'deficit_severity':severity,'neutral_selection':sel,'self_selected_plane':selected,'new_deficit_found':new_deficit,
 'plateau_streak':streak,'checks':checks,'architecture_sha256':arch_sha,'canonical_mutation':False,
 'promotion_applied':False,'g3_genesis_performed':False,'next_required_capability':next_cap,
 'semantic_boundary':'FIXED-G2 FOUR-PLANE RECHECK AFTER CANONICAL CODE V11. CODE IS TESTED INSIDE ITS ADMITTED AMBIGUITY-AWARE SINGLE-FUNCTION CONTRACT; THINKING IS TESTED AT ITS CURRENT NEXT WIDTH/DEPTH BOUNDARY.'
}
receipt['receipt_sha256']=h(receipt);OUT.write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')

e={'index':len(ledger['events']),'event_id':f"E{len(ledger['events'])+1:04d}_G2_LTI_CODE_PLATEAU_PROBE_V5",
 'event_type':'FIXED_ARCHITECTURE_LTI_CODE_PLATEAU_PROBE','status':'PASS_SHADOW' if passed else 'WITHHOLD',
 'generation':ledger['current_head'],'deficit':'LTI_CODE_ARCHITECTURAL_CEILING_PLATEAU_PROBE_V5',
 'effect':f"SELECTED={selected}; SCORES={canon(plane_scores)}; NEXT={next_cap}",
 'source_path':f'receipts/yado-g2-lti-code-architectural-ceiling-plateau-probe-v5-run-{run_id}.json',
 'source_digest':receipt['receipt_sha256'],'run_id':run_id,'parent_event_hash':ledger['tail_event_hash'],
 'canonical_mutation':False,'promotion_applied':False}
e['event_hash']=event_hash(e);ledger['events'].append(e);ledger['event_count']=len(ledger['events']);ledger['tail_event_hash']=e['event_hash']
ledger['open_deficits']=[next_cap];ledger['ledger_digest']=h({k:v for k,v in ledger.items() if k!='ledger_digest'})
validate_ledger_v2(ledger);LEDGER.write_text(json.dumps(ledger,indent=2,sort_keys=True)+'\n')

print(json.dumps({'status':receipt['status'],'probe_status':probe_status,'plane_scores':plane_scores,'probes':probes,
 'self_selected_plane':selected,'next_required_capability':next_cap,'receipt_sha256':receipt['receipt_sha256']},indent=2,sort_keys=True))
if not passed:raise SystemExit('LTI_CODE_PLATEAU_PROBE_V5_WITHHELD')
