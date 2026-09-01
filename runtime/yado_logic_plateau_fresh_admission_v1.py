from __future__ import annotations
from pathlib import Path
from fractions import Fraction
import ast,hashlib,importlib.util,json,os,sys

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
sys.path.insert(0,str(ROOT))

from yado_evolution_ledger_v2 import validate_ledger_v2,event_hash
from yado_bounded_compositional_logic_v1 import BoundedCompositionalLogicV1

HEAD=REPO/'canonical'/'yado-main-head-g2.json'
ARCH=REPO/'canonical'/'yado-g2-architecture-v1.json'
LEDGER=REPO/'architecture'/'evolution-ledger.json'
META=REPO/'candidates'/'g2-self-evolution'/'budget_adaptive_compositional_logic_v2.json'
SRC=REPO/'candidates'/'g2-self-evolution'/'budget_adaptive_compositional_logic_v2.py'
OUT=ROOT/'yado_logic_plateau_fresh_admission_v1_receipt.json'

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def h(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def fsha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8'))

head=load(HEAD);ledger=load(LEDGER);meta=load(META)
validate_ledger_v2(ledger)
if ledger.get('open_deficits')!=['LOGIC_PLATEAU_FRESH_ADMISSION_V1']:raise RuntimeError('UNEXPECTED_FRONTIER')
if meta.get('state')!='AUTHORIZED_FOR_SHADOW_ADMISSION':raise RuntimeError('CANDIDATE_NOT_AUTHORIZED')
if fsha(SRC)!=meta.get('candidate_source_sha256'):raise RuntimeError('SOURCE_DRIFT')
if ledger.get('current_head_digest')!=head.get('canonical_head_digest'):raise RuntimeError('HEAD_LEDGER_MISMATCH')
arch_sha=fsha(ARCH);head_sha=fsha(HEAD)

sp=importlib.util.spec_from_file_location('_logic_v2_candidate',SRC)
mod=importlib.util.module_from_spec(sp);sys.modules[sp.name]=mod;sp.loader.exec_module(mod)
V2=mod.BudgetAdaptiveCompositionalLogicV2
V1=BoundedCompositionalLogicV1

def count_rows(n,label_fn,prefix,repeats=1):
    rows=[]
    for c in range(n+1):
        for r in range(repeats):
            # Same count, different positions, so the learner must really use symmetry rather than fixed coordinates.
            shift=(r*3+c)%n if n else 0
            trues={(shift+j)%n for j in range(c)}
            x={f'{prefix}{i:02d}':i in trues for i in range(n)}
            rows.append({'input':x,'expected':'YES' if label_fn(c) else 'NO'})
    return rows

def random_patterns(n,label_fn,prefix,count=240):
    rows=[]
    for k in range(count):
        c=(k*7+3)%(n+1)
        trues={(k*5+j*11)%n for j in range(c)}
        x={f'{prefix}{i:02d}':i in trues for i in range(n)}
        rows.append({'input':x,'expected':'YES' if label_fn(sum(x.values())) else 'NO'})
    return rows

fresh={}
# Width 20, non-parity symmetric map.
tr20=count_rows(20,lambda c:c%3==1,'u',repeats=2)
te20=random_patterns(20,lambda c:c%3==1,'u',300)
m20=V2.learn_symmetric_boolean(tr20)
fresh['WIDTH20_MOD3_SYMMETRY']=sum(V2.predict_symmetric_boolean(m20,z['input'])==z['expected'] for z in te20)/len(te20)

# Width 24, threshold map.
tr24=count_rows(24,lambda c:c>=13,'v',repeats=2)
te24=random_patterns(24,lambda c:c>=13,'v',300)
m24=V2.learn_symmetric_boolean(tr24)
fresh['WIDTH24_THRESHOLD_SYMMETRY']=sum(V2.predict_symmetric_boolean(m24,z['input'])==z['expected'] for z in te24)/len(te24)

pts=[(x,y) for x in range(-4,5) for y in range(-4,5)]
p4a=[{'x':x,'y':y,'expected':3*x**4-2*x*x*y*y+y**3+5} for x,y in pts]
p4b=[{'x':x,'y':y,'expected':-x**4+2*x**3*y+y**4-3*x+2} for x,y in pts]
for name,rows in [('D4_MIXED_A',p4a),('D4_MIXED_B',p4b)]:
    m=V2.fit_polynomial(rows,max_degree=4)
    fresh[name]=0.0 if m.get('kind')=='WITHHOLD' else sum(V2.predict_polynomial(m,z['x'],z['y'])==Fraction(z['expected']) for z in rows)/len(rows)

# Regression below old boundary.
tr8=count_rows(8,lambda c:c in {2,5,7},'r',repeats=2);te8=random_patterns(8,lambda c:c in {2,5,7},'r',120)
mr=V2.learn_symmetric_boolean(tr8)
fresh['LOW_WIDTH_REGRESSION']=sum(V2.predict_symmetric_boolean(mr,z['input'])==z['expected'] for z in te8)/len(te8)
p2=[{'x':x,'y':y,'expected':2*x*x-x*y+3*y+1} for x,y in pts]
mp2=V2.fit_polynomial(p2,max_degree=4)
fresh['LOW_DEGREE_REGRESSION']=sum(V2.predict_polynomial(mp2,z['x'],z['y'])==Fraction(z['expected']) for z in p2)/len(p2)

# Fail-closed compute contract, using compact but over-budget rows.
over_rows=[]
fields=[f'z{i:02d}' for i in range(64)]
for k in range(4100): # 262400 cells > 262144
    over_rows.append({'input':{f:bool((k+i)%2) for i,f in enumerate(fields)},'expected':'YES'})
bo=V2.learn_symmetric_boolean(over_rows)
fresh['BOOLEAN_WORK_BUDGET_WITHHOLD']=1.0 if bo.get('kind')=='WITHHOLD' and bo.get('reason')=='BOOLEAN_WORK_BUDGET' else 0.0

p5=[{'x':x,'y':y,'expected':x**5+y} for x,y in pts]
m5=V2.fit_polynomial(p5,max_degree=5)
fresh['TERM_BUDGET_WITHHOLD']=1.0 if m5.get('kind')=='WITHHOLD' and m5.get('reason')=='POLYNOMIAL_TERM_BUDGET' else 0.0

p257=[{'x':i,'y':i%5,'expected':i} for i in range(257)]
m257=V2.fit_polynomial(p257,max_degree=1)
fresh['ROW_BUDGET_WITHHOLD']=1.0 if m257.get('kind')=='WITHHOLD' and m257.get('reason')=='POLYNOMIAL_ROW_BUDGET' else 0.0

fresh_score=sum(fresh.values())/len(fresh)

# Causal comparison to V1 on two genuinely new positive families.
try:
    old20=V1.learn_symmetric_boolean(tr20)
    old20score=sum(V1.predict_symmetric_boolean(old20,z['input'])==z['expected'] for z in te20)/len(te20)
except Exception:old20score=0.0
try:
    oldp=V1.fit_polynomial(p4a,max_degree=4)
    oldp_score=0.0 if oldp.get('kind')=='WITHHOLD' else sum(V1.predict_polynomial(oldp,z['x'],z['y'])==Fraction(z['expected']) for z in p4a)/len(p4a)
except Exception:oldp_score=0.0
causal_width=fresh['WIDTH20_MOD3_SYMMETRY']-old20score>=.95
causal_poly=fresh['D4_MIXED_A']-oldp_score>=.95

tree=ast.parse(SRC.read_text(encoding='utf-8'))
danger_calls={n.func.id for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id in {'eval','exec','compile','__import__'}}
danger_imports=[]
for n in ast.walk(tree):
    if isinstance(n,(ast.Import,ast.ImportFrom)):
        names=[a.name for a in n.names] if isinstance(n,ast.Import) else [n.module or '']
        if any(x.split('.')[0] in {'socket','subprocess','requests','urllib','aiohttp'} for x in names):danger_imports.extend(names)

checks={
 'fresh_all_families':all(v>=.99 for v in fresh.values()),
 'fresh_score_one':fresh_score>=.99,
 'width_mechanism_causal':causal_width,
 'polynomial_mechanism_causal':causal_poly,
 'compute_contract_exact':meta.get('compute_contract')=={
   'max_boolean_cells':V2.MAX_BOOLEAN_CELLS,
   'max_polynomial_rows':V2.MAX_POLYNOMIAL_ROWS,
   'max_polynomial_terms':V2.MAX_POLYNOMIAL_TERMS,
 },
 'source_safe':not danger_calls and not danger_imports,
 'architecture_immutable':fsha(ARCH)==arch_sha,
 'canonical_head_immutable':fsha(HEAD)==head_sha and ledger.get('current_head_digest')==head.get('canonical_head_digest'),
}
passed=all(checks.values())
next_cap='LOGIC_PLATEAU_CANONICAL_INTEGRATION_V1' if passed else 'LOGIC_PLATEAU_SELF_EVOLUTION_V2'
run_id=str(os.getenv('GITHUB_RUN_ID') or 'LOCAL')
receipt={
 'schema':'yado.g2.logic_plateau_fresh_admission.v1',
 'status':'PASS_LOGIC_PLATEAU_FRESH_ADMISSION_V1' if passed else 'WITHHOLD_LOGIC_PLATEAU_FRESH_ADMISSION_V1',
 'candidate_digest':meta['candidate_digest'],'candidate_source_sha256':meta['candidate_source_sha256'],
 'fresh_families':fresh,'fresh_score':fresh_score,
 'causal':{'width_v2':causal_width,'poly_v2':causal_poly,'old_width20_score':old20score,'old_d4_score':oldp_score},
 'compute_contract':meta.get('compute_contract'),'source_safety':{'danger_calls':sorted(danger_calls),'danger_imports':danger_imports},
 'checks':checks,'canonical_mutation':False,'promotion_applied':False,'g3_genesis_performed':False,'next_required_capability':next_cap,
 'semantic_boundary':'INDEPENDENT FRESH ADMISSION OF WORK-BUDGET-ADAPTIVE LOGIC V2. POSITIVE TESTS USE NEW WIDTH/FUNCTIONS; RESOURCE LIMITS MUST FAIL CLOSED.'
}
receipt['receipt_sha256']=h(receipt);OUT.write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')

e={'index':len(ledger['events']),'event_id':f"E{len(ledger['events'])+1:04d}_G2_LOGIC_PLATEAU_FRESH_ADMISSION_V1",
 'event_type':'LOGIC_PLATEAU_FRESH_ADMISSION','status':'PASS_SHADOW' if passed else 'WITHHOLD','generation':ledger['current_head'],
 'deficit':'LOGIC_PLATEAU_FRESH_ADMISSION_V1','effect':f"FRESH={fresh_score:.6f}; WIDTH_CAUSAL={causal_width}; POLY_CAUSAL={causal_poly}; NEXT={next_cap}",
 'source_path':f'receipts/yado-logic-plateau-fresh-admission-v1-run-{run_id}.json','source_digest':receipt['receipt_sha256'],'run_id':run_id,
 'parent_event_hash':ledger['tail_event_hash'],'canonical_mutation':False,'promotion_applied':False}
e['event_hash']=event_hash(e);ledger['events'].append(e);ledger['event_count']=len(ledger['events']);ledger['tail_event_hash']=e['event_hash'];ledger['open_deficits']=[next_cap]
ledger['ledger_digest']=h({k:v for k,v in ledger.items() if k!='ledger_digest'});validate_ledger_v2(ledger);LEDGER.write_text(json.dumps(ledger,indent=2,sort_keys=True)+'\n')
print(json.dumps({'status':receipt['status'],'fresh_families':fresh,'fresh_score':fresh_score,'causal':receipt['causal'],'checks':checks,'next_required_capability':next_cap,'receipt_sha256':receipt['receipt_sha256']},indent=2,sort_keys=True))
if not passed:raise SystemExit('LOGIC_PLATEAU_FRESH_ADMISSION_WITHHELD')
