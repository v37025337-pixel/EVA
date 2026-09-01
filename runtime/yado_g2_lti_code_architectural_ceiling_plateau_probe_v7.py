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
from yado_work_budget_adaptive_contingent_planner_v2 import WorkBudgetAdaptiveContingentPlannerV2,ContingentStage
from yado_coverage_pruned_compositional_schema_router_v3 import CoveragePrunedCompositionalSchemaRouterV3
from yado_ambiguity_aware_program_repair_v11 import AmbiguityAwareProgramRepairV11

HEAD=REPO/'canonical'/'yado-main-head-g2.json'
ARCH=REPO/'canonical'/'yado-g2-architecture-v1.json'
LEDGER=REPO/'architecture'/'evolution-ledger.json'
STATE=REPO/'architecture'/'yado-g2-lti-ceiling-state-v1.json'
OUT=ROOT/'yado_g2_lti_code_architectural_ceiling_plateau_probe_v7_receipt.json'

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
if ledger.get('open_deficits')!=['LTI_CODE_ARCHITECTURAL_CEILING_PLATEAU_PROBE_V7']:raise RuntimeError('UNEXPECTED_FRONTIER')
if ledger.get('current_head_digest')!=head.get('canonical_head_digest'):raise RuntimeError('HEAD_LEDGER_MISMATCH')
arch_sha=fsha(ARCH);head_sha=fsha(HEAD)
probes={};contracts={}

L=BudgetAdaptiveCompositionalLogicV2
contracts['LOGIC']={'MAX_BOOLEAN_CELLS':L.MAX_BOOLEAN_CELLS,'MAX_POLYNOMIAL_TERMS':L.MAX_POLYNOMIAL_TERMS,'MAX_POLYNOMIAL_ROWS':L.MAX_POLYNOMIAL_ROWS}
n=32;rows=[]
for c in range(n+1):
    shift=(c*17+7)%n
    trues={(shift+j*9)%n for j in range(c)}
    x={f'm{i:02d}':i in trues for i in range(n)}
    rows.append({'input':x,'expected':'A' if c%9 in {2,5,8} else 'B'})
lm=L.learn_symmetric_boolean(rows)
lb=all(L.predict_symmetric_boolean(lm,z['input'])==z['expected'] for z in rows)
pts=[(x,y) for x in range(-4,5) for y in range(-4,5)]
poly=[{'x':x,'y':y,'expected':2*x**4-x**3*y+3*x*y**3+2*y**4-5*x+2*y+11} for x,y in pts]
pm=L.fit_polynomial(poly,max_degree=4)
lp=pm.get('kind')!='WITHHOLD' and all(L.predict_polynomial(pm,z['x'],z['y'])==Fraction(z['expected']) for z in poly)
probes['LOGIC']={'WIDTH32_FRESH':{'score':1.0 if lb else 0.0},'DEGREE4_SHIFT_FRESH_V7':{'score':1.0 if lp else 0.0}}

P=WorkBudgetAdaptiveContingentPlannerV2;S=ContingentStage
contracts['THINKING']={'MAX_STAGE_RECORDS':P.MAX_STAGE_RECORDS,'MAX_PLAN_STEPS':P.MAX_PLAN_STEPS,'MAX_SEARCH_NODES':P.MAX_SEARCH_NODES,'BEAM_WIDTH':P.BEAM_WIDTH}
st=[S(f'w{i}',1,.075,1,True,.1,False,()) for i in range(13)]
p=P.plan(.025,1.0,13.0,st)
wscore=1.0 if p.expected_confidence>=.999 and len(p.sequence)==13 else 0.0
ids=[f'd{i}' for i in range(14)]
dep=[S(ids[0],1,.025,1,True,.1,False,())]+[S(ids[j],1,.075,1,True,.1,False,(ids[j-1],)) for j in range(1,len(ids))]
q=P.next_after_observation(.0,1.0,14.0,dep,ids[0],.025)
dscore=1.0 if q.expected_confidence>=.999 and len(q.sequence)>=13 else 0.0
probes['THINKING']={'WIDTH13_FRESH':{'score':wscore},'DEPENDENCY13_FRESH':{'score':dscore}}

R=CoveragePrunedCompositionalSchemaRouterV3
contracts['INTELLIGENCE']={'MAX_FIELD_CELLS':R.MAX_FIELD_CELLS,'MAX_TRIGGER_WIDTH':R.MAX_TRIGGER_WIDTH,'MAX_TRIGGER_CANDIDATES':R.MAX_TRIGGER_CANDIDATES}
train=[];test=[];fields=[f'j{i:02d}' for i in range(31)]+['yy_signal']
for k in range(600):
    x={f:bool(((k+43)>>(j%8))&1) for j,f in enumerate(fields)};x['yy_signal']=bool((k//7)%2)
    train.append({'input':x,'expected':(CAP_REL,) if x['zz_signal'] else (CAP_CONJ,)})
for k in range(300):
    x={f:bool(((k+173)>>(j%7))&1) for j,f in enumerate(fields)};x['zz_signal']=bool((k//9)%2)
    test.append({'input':x,'expected':(CAP_REL,) if x['zz_signal'] else (CAP_CONJ,)})
rm=R.fit(train,CAP_CONJ)
iw=sum(R.route(rm,z['input'])==z['expected'] for z in test)/len(test)
pairs=[]
for a,b,c,d in product([False,True],repeat=4):
    out=set()
    if a and c:out.add(CAP_REL)
    if b and d:out.add(CAP_RES)
    if not out:out.add(CAP_CONJ)
    for _ in range(12):pairs.append({'input':{'a':a,'b':b,'c':c,'d':d},'expected':tuple(sorted(out))})
pr=R.fit(pairs,CAP_CONJ)
ip=sum(R.route(pr,z['input'])==z['expected'] for z in pairs)/len(pairs)
probes['INTELLIGENCE']={'WIDTH32_INTELLIGENCE_FRESH':{'score':iw},'PAIRWISE_FRESH_V7':{'score':ip}}

C=AmbiguityAwareProgramRepairV11
contracts['CODE']={'MAX_CANDIDATES':C.MAX_CANDIDATES,'MAX_EDIT_DEPTH':C.MAX_EDIT_DEPTH,'MAX_CONDITIONAL_DEPTH':C.MAX_CONDITIONAL_DEPTH}
amb=[((-10,),30),((-6,),18),((0,),0),((2,),2),((6,),25),((10,),41)]
ra=C.repair('def f(x):\n    return x\n','f',amb,max_candidates=24000)
ca=1.0 if ra.get('reason')=='AMBIGUOUS_UNSEEN_THRESHOLD' else 0.0
resolved=amb+[((3,),3),((4,),4),((5,),5)]
rr=C.repair('def f(x):\n    return x\n','f',resolved,max_candidates=24000)
rh=[((-12,),36),((3,),3),((5,),5),((7,),29),((12,),49)]
cr=0.0 if not rr.get('source') else sum(C.execute(rr['source'],'f',a)==e for a,e in rh)/len(rh)
aff=[((-5,),-13),((0,),2),((3,),11),((6,),20)]
ar=C.repair('def f(x):\n    return x\n','f',aff,max_candidates=24000)
ch=[((-8,),-22),((1,),5),((10,),32)]
cf=0.0 if not ar.get('source') else sum(C.execute(ar['source'],'f',a)==e for a,e in ch)/len(ch)
probes['CODE']={'AMBIGUOUS_WITHHOLD_V7':{'score':ca},'RESOLVED_COMMIT_V7':{'score':cr},'AFFINE_REPAIR_V7':{'score':cf}}

plane_scores={p:avg([float(v['score']) for v in fam.values()]) for p,fam in probes.items()}
threshold=float(state['ceiling_definition']['success_threshold_per_family'])
all_pass=all(v>=threshold for v in plane_scores.values())
best_gain={p:max(0.0,1.0-s) for p,s in plane_scores.items()}
max_gain=max(best_gain.values())
delta_max=float(state['ceiling_definition']['plateau_delta_max'])
plateau_round=all_pass and max_gain<=delta_max
streak=(int(state.get('plateau_streak',0))+1) if plateau_round else 0

severity={p:1.0-s for p,s in plane_scores.items()}
meta={'LOGIC':(.20,.03,.45),'THINKING':(.30,.05,.82),'INTELLIGENCE':(.31,.05,.88),'CODE':(.33,.04,.94)}
tokens={};cands=[]
for i,p in enumerate(sorted(plane_scores)):
    tok='opaque_'+h({'plateau_probe':7,'slot':i,'head':head['canonical_head_digest']})[:18]
    tokens[tok]=p;cx,rk,nv=meta[p];cands.append(EvidenceCandidate(tok,severity[p],cx,rk,nv))
sel=NeutralEvidenceProfileSelectorV1.select(cands);selected=tokens[sel['selected_token']]

if plateau_round:
    req=int(state['ceiling_definition']['plateau_required_consecutive_rounds'])
    next_cap='LTI_CODE_ARCHITECTURAL_CEILING_PLATEAU_PROBE_V8' if streak<req else 'LTI_CODE_ARCHITECTURAL_CEILING_EMPIRICAL_PLATEAU_CONFIRMATION_V1'
    probe_status='PLATEAU_ROUND'
else:
    next_cap=f'{selected}_PLATEAU_SELF_EVOLUTION_V1'
    probe_status='FRONTIER_FOUND'

checks={
 'thinking_v2_active':head.get('unified_core',{}).get('thinking_active_component')=='ALG-G2-WORK-BUDGET-ADAPTIVE-CONTINGENT-PLANNER-V2',
 'code_v11_active':head.get('unified_core',{}).get('code_self_repair_component')=='ALG-G2-AMBIGUITY-AWARE-PROGRAM-REPAIR-V11',
 'all_planes_meet_threshold':all_pass,
 'max_gain_within_plateau_delta':max_gain<=delta_max,
 'architecture_immutable':fsha(ARCH)==arch_sha,
 'canonical_head_immutable':fsha(HEAD)==head_sha and ledger.get('current_head_digest')==head.get('canonical_head_digest'),
 'g3_not_started':head.get('g3_genesis_performed') is False
}
passed=all(v for k,v in checks.items() if k not in {'all_planes_meet_threshold','max_gain_within_plateau_delta'}) and probe_status in {'PLATEAU_ROUND','FRONTIER_FOUND'}

state['round']=int(state.get('round',0))+1;state['plateau_streak']=streak
state['plateau_probe']={'probe_version':7,'probes':probes,'plane_scores':plane_scores,'best_candidate_gain_upper_bound':best_gain,
 'max_gain_upper_bound':max_gain,'neutral_selection':sel,'selected_plane':selected,'status':probe_status,'architecture_sha256':arch_sha}
state['self_selected_weakest_plane']=selected;state['status']='PLATEAU_SEARCH' if plateau_round else 'EVOLVING_TO_CEILING'
state['next_required_capability']=next_cap;state['state_digest']=h({k:v for k,v in state.items() if k!='state_digest'})
STATE.write_text(json.dumps(state,indent=2,sort_keys=True)+'\n')

run_id=str(os.getenv('GITHUB_RUN_ID') or 'LOCAL')
receipt={'schema':'yado.g2.lti_code_architectural_ceiling_plateau_probe.v7',
 'status':'PASS_LTI_CODE_ARCHITECTURAL_CEILING_PLATEAU_PROBE_V7' if passed else 'WITHHOLD_LTI_CODE_ARCHITECTURAL_CEILING_PLATEAU_PROBE_V7',
 'probe_status':probe_status,'probes':probes,'plane_scores':plane_scores,'best_candidate_gain_upper_bound':best_gain,
 'max_gain_upper_bound':max_gain,'self_selected_plane':selected,'plateau_streak':streak,'checks':checks,
 'architecture_sha256':arch_sha,'canonical_mutation':False,'promotion_applied':False,'g3_genesis_performed':False,
 'next_required_capability':next_cap,
 'semantic_boundary':'SECOND FORMAL PLATEAU ROUND AFTER CODE V11 AND THINKING V2. GAIN IS UPPER-BOUNDED BY REMAINING SCORE HEADROOM ON FRESH FAMILIES; ABSOLUTE CEILING IS NOT CLAIMED.'}
receipt['receipt_sha256']=h(receipt);OUT.write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')

e={'index':len(ledger['events']),'event_id':f"E{len(ledger['events'])+1:04d}_G2_LTI_CODE_PLATEAU_PROBE_V7",
 'event_type':'FIXED_ARCHITECTURE_LTI_CODE_PLATEAU_PROBE','status':'PASS_SHADOW' if passed else 'WITHHOLD','generation':ledger['current_head'],
 'deficit':'LTI_CODE_ARCHITECTURAL_CEILING_PLATEAU_PROBE_V7',
 'effect':f"STATUS={probe_status}; STREAK={streak}; SCORES={canon(plane_scores)}; NEXT={next_cap}",
 'source_path':f'receipts/yado-g2-lti-code-architectural-ceiling-plateau-probe-v7-run-{run_id}.json','source_digest':receipt['receipt_sha256'],
 'run_id':run_id,'parent_event_hash':ledger['tail_event_hash'],'canonical_mutation':False,'promotion_applied':False}
e['event_hash']=event_hash(e);ledger['events'].append(e);ledger['event_count']=len(ledger['events']);ledger['tail_event_hash']=e['event_hash']
ledger['open_deficits']=[next_cap];ledger['ledger_digest']=h({k:v for k,v in ledger.items() if k!='ledger_digest'})
validate_ledger_v2(ledger);LEDGER.write_text(json.dumps(ledger,indent=2,sort_keys=True)+'\n')
print(json.dumps({'status':receipt['status'],'probe_status':probe_status,'plane_scores':plane_scores,'plateau_streak':streak,
 'self_selected_plane':selected,'next_required_capability':next_cap,'receipt_sha256':receipt['receipt_sha256']},indent=2,sort_keys=True))
if not passed:raise SystemExit('LTI_CODE_PLATEAU_PROBE_V7_WITHHELD')
