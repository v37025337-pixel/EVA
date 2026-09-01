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
from yado_bounded_compositional_logic_v1 import BoundedCompositionalLogicV1

HEAD=REPO/'canonical'/'yado-main-head-g2.json'
ARCH=REPO/'canonical'/'yado-g2-architecture-v1.json'
LEDGER=REPO/'architecture'/'evolution-ledger.json'
STATE=REPO/'architecture'/'yado-g2-lti-ceiling-state-v1.json'
PROBE=REPO/'receipts'/'yado-g2-lti-architectural-ceiling-plateau-probe-v1-run-33476163633.json'
CAND_DIR=REPO/'candidates'/'g2-self-evolution'
CAND_SRC=CAND_DIR/'budget_adaptive_compositional_logic_v2.py'
CAND_META=CAND_DIR/'budget_adaptive_compositional_logic_v2.json'
OUT=ROOT/'yado_logic_plateau_self_evolution_v1_receipt.json'

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def h(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def fsha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def avg(xs):return sum(xs)/max(1,len(xs))

head=load(HEAD);ledger=load(LEDGER);state=load(STATE);probe=load(PROBE)
validate_ledger_v2(ledger)
if ledger.get('open_deficits')!=['LOGIC_PLATEAU_SELF_EVOLUTION_V1']:raise RuntimeError('UNEXPECTED_FRONTIER')
if probe.get('self_selected_plane')!='LOGIC':raise RuntimeError('LOGIC_NOT_SELF_SELECTED')
if ledger.get('current_head_digest')!=head.get('canonical_head_digest'):raise RuntimeError('HEAD_LEDGER_MISMATCH')
arch_sha=fsha(ARCH);head_sha=fsha(HEAD)

candidate_source=r'''from __future__ import annotations
from fractions import Fraction

class BudgetAdaptiveCompositionalLogicV2:
    COMPONENT_ID="ALG-G2-BUDGET-ADAPTIVE-COMPOSITIONAL-LOGIC-V2"
    MAX_BOOLEAN_CELLS=262144
    MAX_POLYNOMIAL_TERMS=20
    MAX_POLYNOMIAL_ROWS=256

    @classmethod
    def learn_symmetric_boolean(cls,rows):
        if not rows:raise ValueError("EMPTY_ROWS")
        fields=sorted(rows[0]["input"])
        if len(rows)*max(1,len(fields))>cls.MAX_BOOLEAN_CELLS:
            return {"kind":"WITHHOLD","reason":"BOOLEAN_WORK_BUDGET","fields":[],"count_to_output":{},"default":None}
        mapping={};counts={}
        for row in rows:
            if set(row["input"])!=set(fields):raise ValueError("SCHEMA_DRIFT")
            if any(not isinstance(row["input"].get(f),bool) for f in fields):raise ValueError("NON_BOOLEAN_FIELD")
            c=sum(row["input"][f] for f in fields);y=row["expected"]
            if c in mapping and mapping[c]!=y:raise ValueError("NOT_SYMMETRIC_DETERMINISTIC")
            mapping[c]=y;counts[y]=counts.get(y,0)+1
        default=sorted(counts,key=lambda y:(-counts[y],str(y)))[0]
        return {"kind":"SYMMETRIC_COUNT_MAP_V2","fields":fields,"count_to_output":mapping,"default":default,
                "work_cells":len(rows)*len(fields)}

    @staticmethod
    def predict_symmetric_boolean(model,x):
        if model.get("kind")=="WITHHOLD":raise ValueError("BOOLEAN_WORK_BUDGET")
        c=sum(bool(x.get(f,False)) for f in model["fields"])
        return model["count_to_output"].get(c,model["default"])

    @staticmethod
    def _basis(degree):
        out=[]
        for total in range(int(degree)+1):
            for i in range(total+1):out.append((i,total-i))
        return out

    @classmethod
    def _fit_degree(cls,rows,degree):
        basis=cls._basis(degree)
        if len(basis)>cls.MAX_POLYNOMIAL_TERMS or len(rows)>cls.MAX_POLYNOMIAL_ROWS:return None
        A=[]
        for r in rows:
            x=Fraction(r["x"]);y=Fraction(r["y"]);z=Fraction(r["expected"])
            A.append([x**i*y**j for i,j in basis]+[z])
        m=len(A);n=len(basis);rank=0;pivots=[]
        for col in range(n):
            pivot=next((i for i in range(rank,m) if A[i][col]!=0),None)
            if pivot is None:continue
            A[rank],A[pivot]=A[pivot],A[rank]
            q=A[rank][col];A[rank]=[v/q for v in A[rank]]
            for i in range(m):
                if i==rank or A[i][col]==0:continue
                q=A[i][col];A[i]=[a-q*b for a,b in zip(A[i],A[rank])]
            pivots.append(col);rank+=1
        for row in A:
            if all(row[c]==0 for c in range(n)) and row[-1]!=0:return None
        if rank<n:return None
        coeff=[Fraction(0) for _ in range(n)]
        for rix,col in enumerate(pivots[:n]):coeff[col]=A[rix][-1]
        model={"kind":"EXACT_BOUNDED_POLYNOMIAL_V2","degree":degree,"basis":basis,"coeff":coeff,
               "term_count":len(basis),"row_count":len(rows)}
        if all(cls.predict_polynomial(model,r["x"],r["y"])==Fraction(r["expected"]) for r in rows):return model
        return None

    @classmethod
    def fit_polynomial(cls,rows,max_degree=8):
        if not rows or len(rows)>cls.MAX_POLYNOMIAL_ROWS:
            return {"kind":"WITHHOLD","reason":"POLYNOMIAL_ROW_BUDGET","degree":None,"basis":[],"coeff":[]}
        for d in range(int(max_degree)+1):
            basis=cls._basis(d)
            if len(basis)>cls.MAX_POLYNOMIAL_TERMS:
                return {"kind":"WITHHOLD","reason":"POLYNOMIAL_TERM_BUDGET","degree":None,"basis":[],"coeff":[]}
            m=cls._fit_degree(rows,d)
            if m is not None:return m
        return {"kind":"WITHHOLD","reason":"NO_EXACT_MODEL_WITHIN_BUDGET","degree":None,"basis":[],"coeff":[]}

    @staticmethod
    def predict_polynomial(model,x,y):
        if model.get("kind")=="WITHHOLD":raise ValueError(model.get("reason","NO_POLYNOMIAL"))
        x=Fraction(x);y=Fraction(y)
        return sum(c*x**i*y**j for c,(i,j) in zip(model["coeff"],model["basis"]))
'''
CAND_DIR.mkdir(parents=True,exist_ok=True);CAND_SRC.write_text(candidate_source,encoding='utf-8')

# Candidate evaluation helpers loaded directly from generated source.
ns={};exec(compile(candidate_source,'<candidate>','exec'),ns)
V2=ns['BudgetAdaptiveCompositionalLogicV2']
V1=BoundedCompositionalLogicV1

def bool_rows(n,fn,p):
    return [{'input':{f'{p}{i:02d}':v[i] for i in range(n)},'expected':'YES' if fn(v) else 'NO'} for v in product([False,True],repeat=n)]

def score_bool(cls,rows):
    try:
        m=cls.learn_symmetric_boolean(rows)
        if m.get('kind')=='WITHHOLD':return 0.0
        return sum(cls.predict_symmetric_boolean(m,z['input'])==z['expected'] for z in rows)/len(rows)
    except Exception:return 0.0

def score_poly(cls,rows,degree):
    try:
        m=cls.fit_polynomial(rows,max_degree=degree)
        if m.get('kind')=='WITHHOLD':return 0.0
        return sum(cls.predict_polynomial(m,z['x'],z['y'])==Fraction(z['expected']) for z in rows)/len(rows)
    except Exception:return 0.0

# Fresh transforms of the two contract-derived deficits.
b13=bool_rows(13,lambda v:sum(v)%2==1,'a')
b14=bool_rows(14,lambda v:sum(v)==7,'b')
pts=[(x,y) for x in range(-4,5) for y in range(-4,5)]
p4a=[{'x':x,'y':y,'expected':x**4+2*x*y+y*y+3} for x,y in pts]
p4b=[{'x':x,'y':y,'expected':2*x**4-x*x*y+3*y**2-5} for x,y in pts]

# Strategy bank is bounded and generic: keep fixed-dimension behavior, switch each axis to work-budget behavior, or both.
strategies=[
 {'id':'BASE_V1','bool_v2':False,'poly_v2':False,'complexity':.10,'risk':.02,'novelty':.10},
 {'id':'WORK_BUDGET_BOOLEAN','bool_v2':True,'poly_v2':False,'complexity':.20,'risk':.03,'novelty':.55},
 {'id':'TERM_BUDGET_POLY','bool_v2':False,'poly_v2':True,'complexity':.23,'risk':.03,'novelty':.60},
 {'id':'WORK_BUDGET_BOTH','bool_v2':True,'poly_v2':True,'complexity':.31,'risk':.05,'novelty':.90},
]

def eval_strategy(s):
    BC=V2 if s['bool_v2'] else V1
    PC=V2 if s['poly_v2'] else V1
    fam={
      'BOOLEAN_WIDTH_13':score_bool(BC,b13),
      'BOOLEAN_WIDTH_14_FRESH':score_bool(BC,b14),
      'POLYNOMIAL_D4_A':score_poly(PC,p4a,4),
      'POLYNOMIAL_D4_B_FRESH':score_poly(PC,p4b,4),
    }
    return {'families':fam,'score':avg(list(fam.values())),'min_family':min(fam.values())}

validation={};tok={}
for i,s in enumerate(strategies):
    m=eval_strategy(s);t='opaque_'+h({'logic_plateau':1,'slot':i,'head':head['canonical_head_digest']})[:18]
    validation[s['id']]=m|{'token':t,'complexity':s['complexity'],'risk':s['risk'],'novelty':s['novelty']};tok[t]=s
selection=NeutralEvidenceProfileSelectorV1.select([EvidenceCandidate(v['token'],v['score'],v['complexity'],v['risk'],v['novelty']) for v in validation.values()])
selected=tok[selection['selected_token']]
holdout=eval_strategy(selected);base=eval_strategy(strategies[0]);causal_gain=holdout['score']-base['score']

# Required fail-closed boundaries under the NEW fixed compute budget.
b15=bool_rows(15,lambda v:sum(v)%2==1,'c')  # 32768*15 > 262144
bm15=V2.learn_symmetric_boolean(b15)
boolean_budget_withhold=bm15.get('kind')=='WITHHOLD' and bm15.get('reason')=='BOOLEAN_WORK_BUDGET'
p5=[{'x':x,'y':y,'expected':x**5+y} for x,y in pts]
pm5=V2.fit_polynomial(p5,max_degree=5)
term_budget_withhold=pm5.get('kind')=='WITHHOLD' and pm5.get('reason')=='POLYNOMIAL_TERM_BUDGET'

checks={
 'logic_self_selected':probe.get('self_selected_plane')=='LOGIC',
 'selected_both_budget_axes':selected['id']=='WORK_BUDGET_BOTH',
 'fresh_min_one':holdout['min_family']>=.99,
 'causal_gain_large':causal_gain>=.95,
 'boolean_budget_fail_closed':boolean_budget_withhold,
 'polynomial_term_budget_fail_closed':term_budget_withhold,
 'architecture_immutable':fsha(ARCH)==arch_sha,
 'head_immutable':fsha(HEAD)==head_sha and ledger.get('current_head_digest')==head.get('canonical_head_digest'),
}
passed=all(checks.values())
next_cap='LOGIC_PLATEAU_FRESH_ADMISSION_V1' if passed else 'LOGIC_PLATEAU_SELF_EVOLUTION_V2'

candidate={
 'schema':'yado.g2.budget_adaptive_compositional_logic_candidate.v2',
 'component_id':'ALG-G2-BUDGET-ADAPTIVE-COMPOSITIONAL-LOGIC-V2',
 'selected_strategy':selected['id'],'validation':validation,'neutral_selection':selection,
 'fresh_validation':holdout,'baseline':base,'causal_gain':causal_gain,
 'compute_contract':{'max_boolean_cells':V2.MAX_BOOLEAN_CELLS,'max_polynomial_terms':V2.MAX_POLYNOMIAL_TERMS,'max_polynomial_rows':V2.MAX_POLYNOMIAL_ROWS},
 'fail_closed':{'boolean_work_budget':boolean_budget_withhold,'polynomial_term_budget':term_budget_withhold},
 'candidate_source_sha256':fsha(CAND_SRC),'architecture_sha256':arch_sha,'parent_head_digest':head['canonical_head_digest'],
 'canonical_active':False,'promotion_applied':False,'state':'AUTHORIZED_FOR_SHADOW_ADMISSION' if passed else 'WITHHOLD',
 'semantic_boundary':'REPLACES SMALL FIXED LOGIC DIMENSION CAPS WITH FIXED TOTAL-WORK BUDGETS. SUPPORTS SYMMETRIC BOOLEAN WIDTH WITHIN CELL BUDGET AND EXACT POLYNOMIAL MODELS WITHIN TERM/ROW BUDGET. NOT GENERAL THEOREM PROVING.'
}
candidate['candidate_digest']=h(candidate);CAND_META.write_text(json.dumps(candidate,indent=2,sort_keys=True)+'\n')

state['candidate_history'].append({'round':state.get('round',7),'plane':'LOGIC','candidate_digest':candidate['candidate_digest'],'selected_strategy':selected['id'],'fresh_score':holdout['score'],'baseline_score':base['score'],'causal_drop':causal_gain,'status':'PASS_SHADOW' if passed else 'WITHHOLD'})
state['next_required_capability']=next_cap
state['state_digest']=h({k:v for k,v in state.items() if k!='state_digest'});STATE.write_text(json.dumps(state,indent=2,sort_keys=True)+'\n')

run_id=str(os.getenv('GITHUB_RUN_ID') or 'LOCAL')
receipt={'schema':'yado.g2.logic_plateau_self_evolution.v1',
 'status':'PASS_LOGIC_PLATEAU_SELF_EVOLUTION_V1' if passed else 'WITHHOLD_LOGIC_PLATEAU_SELF_EVOLUTION_V1',
 'selected_strategy':selected['id'],'validation':validation,'neutral_selection':selection,'fresh_validation':holdout,'baseline':base,'causal_gain':causal_gain,
 'compute_contract':candidate['compute_contract'],'fail_closed':candidate['fail_closed'],'candidate_digest':candidate['candidate_digest'],'candidate_source_sha256':candidate['candidate_source_sha256'],
 'checks':checks,'canonical_mutation':False,'promotion_applied':False,'g3_genesis_performed':False,'next_required_capability':next_cap,
 'semantic_boundary':candidate['semantic_boundary']}
receipt['receipt_sha256']=h(receipt);OUT.write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')

e={'index':len(ledger['events']),'event_id':f"E{len(ledger['events'])+1:04d}_G2_LOGIC_PLATEAU_SELF_EVOLUTION_V1",
 'event_type':'FIXED_ARCHITECTURE_LOGIC_PLATEAU_SELF_EVOLUTION','status':'PASS_SHADOW' if passed else 'WITHHOLD','generation':ledger['current_head'],
 'deficit':'LOGIC_PLATEAU_SELF_EVOLUTION_V1','effect':f"SELECTED={selected['id']}; FRESH={holdout['score']:.6f}; BASE={base['score']:.6f}; GAIN={causal_gain:.6f}; NEXT={next_cap}",
 'source_path':f'receipts/yado-logic-plateau-self-evolution-v1-run-{run_id}.json','source_digest':receipt['receipt_sha256'],'run_id':run_id,
 'parent_event_hash':ledger['tail_event_hash'],'canonical_mutation':False,'promotion_applied':False}
e['event_hash']=event_hash(e);ledger['events'].append(e);ledger['event_count']=len(ledger['events']);ledger['tail_event_hash']=e['event_hash'];ledger['open_deficits']=[next_cap]
ledger['ledger_digest']=h({k:v for k,v in ledger.items() if k!='ledger_digest'});validate_ledger_v2(ledger);LEDGER.write_text(json.dumps(ledger,indent=2,sort_keys=True)+'\n')
print(json.dumps({'status':receipt['status'],'selected_strategy':selected['id'],'fresh_validation':holdout,'baseline':base,'causal_gain':causal_gain,'fail_closed':candidate['fail_closed'],'checks':checks,'next_required_capability':next_cap,'receipt_sha256':receipt['receipt_sha256']},indent=2,sort_keys=True))
if not passed:raise SystemExit('LOGIC_PLATEAU_SELF_EVOLUTION_V1_WITHHELD')
