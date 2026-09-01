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
from yado_bounded_compositional_schema_router_v1 import BoundedCompositionalSchemaRouterV1

HEAD=REPO/'canonical'/'yado-main-head-g2.json'
ARCH=REPO/'canonical'/'yado-g2-architecture-v1.json'
LEDGER=REPO/'architecture'/'evolution-ledger.json'
STATE=REPO/'architecture'/'yado-g2-lti-ceiling-state-v1.json'
OUT=ROOT/'yado_g2_lti_architectural_ceiling_plateau_probe_v2_receipt.json'
CAP_CONJ='ALG-CONJUNCTIVE-RULE-INDUCER-V1';CAP_REL='ALG-BOUNDED-DNF-RELATION-POLICY-INDUCER-V1';CAP_RES='RESOURCE-PORTFOLIO-V1'

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def h(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def fsha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def avg(xs):return sum(xs)/max(1,len(xs))
head=load(HEAD);ledger=load(LEDGER);state=load(STATE);validate_ledger_v2(ledger)
if ledger.get('open_deficits')!=['LTI_ARCHITECTURAL_CEILING_PLATEAU_PROBE_V2']:raise RuntimeError('UNEXPECTED_FRONTIER')
if ledger.get('current_head_digest')!=head.get('canonical_head_digest'):raise RuntimeError('HEAD_LEDGER_MISMATCH')
arch_sha=fsha(ARCH);head_sha=fsha(HEAD)

probes={};contracts={}
# LOGIC V2: test structural transfer inside declared work budget; test resource limits as correct withhold.
L=BudgetAdaptiveCompositionalLogicV2
contracts['LOGIC']={'MAX_BOOLEAN_CELLS':L.MAX_BOOLEAN_CELLS,'MAX_POLYNOMIAL_TERMS':L.MAX_POLYNOMIAL_TERMS,'MAX_POLYNOMIAL_ROWS':L.MAX_POLYNOMIAL_ROWS}
def count_rows(n,fn,p):
    rows=[]
    for c in range(n+1):
        shift=(c*7)%n
        trues={(shift+j)%n for j in range(c)}
        rows.append({'input':{f'{p}{i:02d}':i in trues for i in range(n)},'expected':'YES' if fn(c) else 'NO'})
    return rows
def test_rows(n,fn,p,count=240):
    rows=[]
    for k in range(count):
        c=(k*11+5)%(n+1);trues={(k*3+j*7)%n for j in range(c)}
        x={f'{p}{i:02d}':i in trues for i in range(n)}
        rows.append({'input':x,'expected':'YES' if fn(sum(x.values())) else 'NO'})
    return rows
tr=count_rows(24,lambda c:c%4 in {1,2},'l');te=test_rows(24,lambda c:c%4 in {1,2},'l')
lm=L.learn_symmetric_boolean(tr)
ls=sum(L.predict_symmetric_boolean(lm,z['input'])==z['expected'] for z in te)/len(te)
pts=[(x,y) for x in range(-4,5) for y in range(-4,5)]
p4=[{'x':x,'y':y,'expected':2*x**4-3*x*x*y*y+y**4+x-2} for x,y in pts]
pm=L.fit_polynomial(p4,max_degree=4)
ps=0.0 if pm.get('kind')=='WITHHOLD' else sum(L.predict_polynomial(pm,z['x'],z['y'])==Fraction(z['expected']) for z in p4)/len(p4)
p5=[{'x':x,'y':y,'expected':x**5+y} for x,y in pts];p5m=L.fit_polynomial(p5,max_degree=5)
budget_ok=1.0 if p5m.get('kind')=='WITHHOLD' and p5m.get('reason')=='POLYNOMIAL_TERM_BUDGET' else 0.0
probes['LOGIC']={
 'WITHIN_BUDGET_WIDTH24_TRANSFER':{'score':ls,'reason':'STRUCTURAL_TRANSFER_INSIDE_BOOLEAN_WORK_BUDGET'},
 'WITHIN_BUDGET_DEGREE4_TRANSFER':{'score':ps,'reason':'STRUCTURAL_TRANSFER_INSIDE_POLYNOMIAL_TERM_BUDGET'},
 'TERM_BUDGET_FAIL_CLOSED':{'score':budget_ok,'reason':p5m.get('reason')},
}

# THINKING: unresolved one-step-beyond contract.
P=BoundedAdaptiveContingentPlannerV1;S=ContingentStage
contracts['THINKING']={'MAX_STAGES':P.MAX_STAGES,'MAX_PLAN_DEPTH':P.MAX_PLAN_DEPTH}
n=P.MAX_STAGES+1
st=[S(f's{i}',1,.1,1,True,.1,False,()) for i in range(n)]
pl=P.plan(.1,1.0,float(n),st)
stage_score=min(1.0,pl.expected_confidence)
remaining=P.MAX_PLAN_DEPTH+1
ids=[f'd{i}' for i in range(remaining+1)]
ds=[S(ids[0],1,.05,1,True,.1,False,())]+[S(ids[j],1,.1,1,False,.1,False,(ids[j-1],)) for j in range(1,len(ids))]
dp=P.next_after_observation(.05,1.0,float(len(ids)),ds,ids[0],.05)
dep_score=min(1.0,dp.expected_confidence)
probes['THINKING']={
 'STAGE_WIDTH_PLUS_ONE':{'score':stage_score,'bound':P.MAX_STAGES,'probe_value':n,'sequence_len':len(pl.sequence)},
 'DEPENDENCY_DEPTH_PLUS_ONE':{'score':dep_score,'bound':P.MAX_PLAN_DEPTH,'probe_value':remaining,'sequence_len':len(dp.sequence)},
}

# INTELLIGENCE: unresolved field-order and interaction-order frontiers.
R=BoundedCompositionalSchemaRouterV1
contracts['INTELLIGENCE']={'MAX_FIELDS':R.MAX_FIELDS,'MAX_OUTPUTS':R.MAX_OUTPUTS,'MAX_TRIGGERS_PER_OUTPUT':R.MAX_TRIGGERS_PER_OUTPUT}
field_n=R.MAX_FIELDS+1
fields=[f'f{i:02d}' for i in range(field_n-1)]+['zz_signal']
train=[];test=[]
for k in range(320):
    x={f:bool(((k+13)>>(i%8))&1) for i,f in enumerate(fields)}
    x['zz_signal']=bool((k//3)%2);y=(CAP_REL,) if x['zz_signal'] else (CAP_CONJ,)
    train.append({'input':x,'expected':y})
for k in range(160):
    x={f:bool(((k+47)>>(i%7))&1) for i,f in enumerate(fields)}
    x['zz_signal']=bool((k//5)%2);y=(CAP_REL,) if x['zz_signal'] else (CAP_CONJ,)
    test.append({'input':x,'expected':y})
rm=R.fit(train,CAP_CONJ);field_score=sum(R.route(rm,z['input'])==z['expected'] for z in test)/len(test)
ix=[]
for a,b,c,d in product([False,True],repeat=4):
    out=set()
    if a and b:out.add(CAP_REL)
    if c and d:out.add(CAP_RES)
    if not out:out.add(CAP_CONJ)
    for _ in range(10):ix.append({'input':{'a':a,'b':b,'c':c,'d':d},'expected':tuple(sorted(out))})
irm=R.fit(ix,CAP_CONJ);interaction=sum(R.route(irm,z['input'])==z['expected'] for z in ix)/len(ix)
probes['INTELLIGENCE']={
 'FIELD_WIDTH_PLUS_ONE':{'score':field_score,'bound':R.MAX_FIELDS,'probe_value':field_n},
 'TRIGGER_INTERACTION_ORDER_PLUS_ONE':{'score':interaction,'current_order':1,'probe_order':2},
}

plane_scores={p:avg([v['score'] for v in fam.values()]) for p,fam in probes.items()}
severity={p:1-s for p,s in plane_scores.items()}
tokens={};cands=[]
meta={'LOGIC':(.20,.03,.45),'THINKING':(.34,.06,.80),'INTELLIGENCE':(.31,.05,.88)}
for i,p in enumerate(sorted(plane_scores)):
    tok='opaque_'+h({'plateau_probe':2,'slot':i,'head':head['canonical_head_digest']})[:18];tokens[tok]=p
    cx,rk,nv=meta[p];cands.append(EvidenceCandidate(tok,severity[p],cx,rk,nv))
sel=NeutralEvidenceProfileSelectorV1.select(cands);selected=tokens[sel['selected_token']]
threshold=float(state['ceiling_definition']['success_threshold_per_family']);new_deficit=plane_scores[selected]<threshold
if new_deficit:
    streak=0;next_cap=f'{selected}_PLATEAU_SELF_EVOLUTION_V1';probe_status='FRONTIER_FOUND'
else:
    streak=int(state.get('plateau_streak',0))+1;req=int(state['ceiling_definition']['plateau_required_consecutive_rounds'])
    next_cap='LTI_ARCHITECTURAL_CEILING_PLATEAU_PROBE_V3' if streak<req else 'LTI_ARCHITECTURAL_CEILING_EMPIRICAL_PLATEAU_CONFIRMATION_V1';probe_status='PLATEAU_ROUND'

checks={'logic_v2_active_in_head':head.get('unified_core',{}).get('logic_active_component')=='ALG-G2-BUDGET-ADAPTIVE-COMPOSITIONAL-LOGIC-V2',
 'three_planes_probed':set(probes)=={'LOGIC','THINKING','INTELLIGENCE'},'architecture_immutable':fsha(ARCH)==arch_sha,
 'canonical_head_immutable':fsha(HEAD)==head_sha and ledger.get('current_head_digest')==head.get('canonical_head_digest'),'g3_not_started':head.get('g3_genesis_performed') is False}
passed=all(checks.values())
state['round']=int(state.get('round',0))+1;state['plateau_streak']=streak
state['plateau_probe']={'probe_version':2,'contract_snapshot':contracts,'probes':probes,'plane_scores':plane_scores,'deficit_severity':severity,'neutral_selection':sel,'selected_plane':selected,'status':probe_status,'architecture_sha256':arch_sha}
state['self_selected_weakest_plane']=selected;state['status']='EVOLVING_TO_CEILING' if new_deficit else 'PLATEAU_SEARCH';state['next_required_capability']=next_cap
state['state_digest']=h({k:v for k,v in state.items() if k!='state_digest'});STATE.write_text(json.dumps(state,indent=2,sort_keys=True)+'\n')
run_id=str(os.getenv('GITHUB_RUN_ID') or 'LOCAL')
receipt={'schema':'yado.g2.lti_architectural_ceiling_plateau_probe.v2','status':'PASS_LTI_ARCHITECTURAL_CEILING_PLATEAU_PROBE_V2' if passed else 'WITHHOLD_LTI_ARCHITECTURAL_CEILING_PLATEAU_PROBE_V2',
 'probe_status':probe_status,'contract_snapshot':contracts,'probes':probes,'plane_scores':plane_scores,'deficit_severity':severity,'neutral_selection':sel,
 'self_selected_plane':selected,'new_deficit_found':new_deficit,'plateau_streak':streak,'checks':checks,'architecture_sha256':arch_sha,
 'canonical_mutation':False,'promotion_applied':False,'g3_genesis_performed':False,'next_required_capability':next_cap,
 'semantic_boundary':'SECOND CONTRACT-DERIVED PLATEAU SEARCH AFTER LOGIC V2. RESOURCE-BUDGET WITHHOLD IS SCORED AS CORRECT; ONLY FAILURES INSIDE CURRENT COMPUTE CONTRACT REOPEN SELF-EVOLUTION.'}
receipt['receipt_sha256']=h(receipt);OUT.write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')
e={'index':len(ledger['events']),'event_id':f"E{len(ledger['events'])+1:04d}_G2_LTI_PLATEAU_PROBE_V2",'event_type':'FIXED_ARCHITECTURE_CONTRACT_DERIVED_PLATEAU_PROBE',
 'status':'PASS_SHADOW' if passed else 'WITHHOLD','generation':ledger['current_head'],'deficit':'LTI_ARCHITECTURAL_CEILING_PLATEAU_PROBE_V2',
 'effect':f"PROBE={probe_status}; SELECTED={selected}; SCORE={plane_scores[selected]:.6f}; STREAK={streak}; NEXT={next_cap}",
 'source_path':f'receipts/yado-g2-lti-architectural-ceiling-plateau-probe-v2-run-{run_id}.json','source_digest':receipt['receipt_sha256'],'run_id':run_id,'parent_event_hash':ledger['tail_event_hash'],
 'canonical_mutation':False,'promotion_applied':False}
e['event_hash']=event_hash(e);ledger['events'].append(e);ledger['event_count']=len(ledger['events']);ledger['tail_event_hash']=e['event_hash'];ledger['open_deficits']=[next_cap]
ledger['ledger_digest']=h({k:v for k,v in ledger.items() if k!='ledger_digest'});validate_ledger_v2(ledger);LEDGER.write_text(json.dumps(ledger,indent=2,sort_keys=True)+'\n')
print(json.dumps({'status':receipt['status'],'probe_status':probe_status,'plane_scores':plane_scores,'probes':probes,'self_selected_plane':selected,'next_required_capability':next_cap,'receipt_sha256':receipt['receipt_sha256']},indent=2,sort_keys=True))
if not passed:raise SystemExit('PLATEAU_PROBE_V2_WITHHELD')
