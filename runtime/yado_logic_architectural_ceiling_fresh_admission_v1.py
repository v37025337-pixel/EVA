from __future__ import annotations
from pathlib import Path
from itertools import product
from fractions import Fraction
import ast,hashlib,importlib.util,json,os,sys

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
sys.path.insert(0,str(ROOT))
from yado_evolution_ledger_v2 import validate_ledger_v2,event_hash
from yado_bounded_dnf_relation_policy_inducer_v1 import BoundedDNFRelationPolicyInducerV1,program_acc
from yado_semantic_expression_synthesizer_v1 import SemanticExpressionSynthesizerV1

HEAD=REPO/'canonical'/'yado-main-head-g2.json'
ARCH=REPO/'canonical'/'yado-g2-architecture-v1.json'
LEDGER=REPO/'architecture'/'evolution-ledger.json'
META=REPO/'candidates'/'g2-self-evolution'/'bounded_compositional_logic_v1.json'
SRC=REPO/'candidates'/'g2-self-evolution'/'bounded_compositional_logic_v1.py'
OUT=ROOT/'yado_logic_architectural_ceiling_fresh_admission_v1_receipt.json'

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def h(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def fsha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8'))

head=load(HEAD);ledger=load(LEDGER);meta=load(META)
validate_ledger_v2(ledger)
if ledger.get('open_deficits')!=['LOGIC_ARCHITECTURAL_CEILING_FRESH_ADMISSION_V1']:raise RuntimeError('UNEXPECTED_FRONTIER')
if meta.get('state')!='AUTHORIZED_FOR_SHADOW_ADMISSION':raise RuntimeError('CANDIDATE_NOT_AUTHORIZED')
if fsha(SRC)!=meta.get('candidate_source_sha256'):raise RuntimeError('SOURCE_DRIFT')
if ledger.get('current_head_digest')!=head.get('canonical_head_digest'):raise RuntimeError('HEAD_LEDGER_MISMATCH')
arch_sha=fsha(ARCH);head_sha=fsha(HEAD)

sp=importlib.util.spec_from_file_location('_logic_candidate',SRC)
mod=importlib.util.module_from_spec(sp);sys.modules[sp.name]=mod;sp.loader.exec_module(mod)
Logic=mod.BoundedCompositionalLogicV1

def bool_rows(n,fn,prefix):
    return [{'input':{f'{prefix}{i}':v[i] for i in range(n)},'expected':'YES' if fn(v) else 'NO'} for v in product([False,True],repeat=n)]

families={}
for name,rows in [
 ('PARITY7',bool_rows(7,lambda v:sum(v)%2==1,'a')),
 ('EXACT4OF9',bool_rows(9,lambda v:sum(v)==4,'b')),
 ('THRESHOLD6OF10',bool_rows(10,lambda v:sum(v)>=6,'c')),
]:
    m=Logic.learn_symmetric_boolean(rows)
    families[name]=sum(Logic.predict_symmetric_boolean(m,z['input'])==z['expected'] for z in rows)/len(rows)

pts=[(x,y) for x in range(-4,5) for y in range(-4,5)]
p1=[{'x':x,'y':y,'expected':2*x*x*x-3*x*x*y+y*y+4*x-2} for x,y in pts]
p2=[{'x':x,'y':y,'expected':-x*x*x+y*y*y+2*x*y+5} for x,y in pts]
for name,rows in [('CUBIC_TRANSFER_A',p1),('CUBIC_TRANSFER_B',p2)]:
    m=Logic.fit_polynomial(rows,max_degree=3)
    families[name]=0.0 if m.get('kind')=='WITHHOLD' else sum(Logic.predict_polynomial(m,z['x'],z['y'])==Fraction(z['expected']) for z in rows)/len(rows)

# Must fail closed beyond bounded degree rather than hallucinate a fit.
quartic=[{'x':x,'y':y,'expected':x**4+y} for x,y in pts]
q=Logic.fit_polynomial(quartic,max_degree=3)
families['QUARTIC_WITHHOLD']=1.0 if q.get('kind')=='WITHHOLD' else 0.0

fresh_score=sum(families.values())/len(families)

# Causal ablations against prior canonical mechanisms.
par=bool_rows(7,lambda v:sum(v)%2==1,'z')
basep=BoundedDNFRelationPolicyInducerV1.synthesize('ABL_PAR','LOGIC',par,min_support=1,max_clauses=12,validation_cases=par)
base_par=program_acc(basep,par)
sym=Logic.learn_symmetric_boolean(par)
new_par=sum(Logic.predict_symmetric_boolean(sym,z['input'])==z['expected'] for z in par)/len(par)
symmetric_causal=new_par-base_par>=.35

base_expr=SemanticExpressionSynthesizerV1.synthesize(p1,max_ops=3,max_states_per_level=30000)
base_poly=0.0 if base_expr.get('expression') is None else sum(SemanticExpressionSynthesizerV1.predict(base_expr,z['x'],z['y'])==z['expected'] for z in p1)/len(p1)
pm=Logic.fit_polynomial(p1,max_degree=3)
new_poly=sum(Logic.predict_polynomial(pm,z['x'],z['y'])==Fraction(z['expected']) for z in p1)/len(p1)
polynomial_causal=new_poly-base_poly>=.50

tree=ast.parse(SRC.read_text(encoding='utf-8'))
danger_calls={n.func.id for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id in {'eval','exec','compile','__import__'}}
danger_imports=[]
for n in ast.walk(tree):
    if isinstance(n,(ast.Import,ast.ImportFrom)):
        names=[a.name for a in n.names] if isinstance(n,ast.Import) else [n.module or '']
        if any(x.split('.')[0] in {'socket','subprocess','requests','urllib','aiohttp'} for x in names):danger_imports.extend(names)

checks={
 'fresh_all_families':all(v>=.99 for v in families.values()),
 'fresh_score_one':fresh_score>=.99,
 'symmetric_feature_causal':symmetric_causal,
 'polynomial_feature_causal':polynomial_causal,
 'bounded_boolean_fields':Logic.MAX_BOOLEAN_FIELDS<=12,
 'bounded_polynomial_degree':Logic.MAX_POLYNOMIAL_DEGREE<=3,
 'bounded_polynomial_terms':Logic.MAX_POLYNOMIAL_TERMS<=10,
 'source_safe':not danger_calls and not danger_imports,
 'architecture_immutable':fsha(ARCH)==arch_sha,
 'canonical_head_immutable':fsha(HEAD)==head_sha and ledger.get('current_head_digest')==head.get('canonical_head_digest'),
}
passed=all(checks.values())
next_cap='LOGIC_ARCHITECTURAL_CEILING_CANONICAL_INTEGRATION_V1' if passed else 'LOGIC_ARCHITECTURAL_CEILING_SELF_EVOLUTION_V2'
run_id=str(os.getenv('GITHUB_RUN_ID') or 'LOCAL')
receipt={'schema':'yado.g2.logic_architectural_ceiling_fresh_admission.v1',
 'status':'PASS_LOGIC_ARCHITECTURAL_CEILING_FRESH_ADMISSION_V1' if passed else 'WITHHOLD_LOGIC_ARCHITECTURAL_CEILING_FRESH_ADMISSION_V1',
 'candidate_digest':meta['candidate_digest'],'candidate_source_sha256':meta['candidate_source_sha256'],
 'fresh_families':families,'fresh_score':fresh_score,
 'causal':{'symmetric_boolean':symmetric_causal,'polynomial':polynomial_causal,'baseline_parity':base_par,'new_parity':new_par,'baseline_polynomial':base_poly,'new_polynomial':new_poly},
 'source_safety':{'danger_calls':sorted(danger_calls),'danger_imports':danger_imports},'checks':checks,
 'canonical_mutation':False,'promotion_applied':False,'g3_genesis_performed':False,'next_required_capability':next_cap,
 'semantic_boundary':'INDEPENDENT FRESH ADMISSION OF BOUNDED SYMMETRIC-BOOLEAN AND EXACT LOW-DEGREE POLYNOMIAL LOGIC. QUARTIC OUT-OF-SCOPE MUST WITHHOLD.'
}
receipt['receipt_sha256']=h(receipt);OUT.write_text(json.dumps(receipt,indent=2,sort_keys=True,default=str)+'\n')

e={'index':len(ledger['events']),'event_id':f"E{len(ledger['events'])+1:04d}_G2_LOGIC_CEILING_FRESH_ADMISSION",
 'event_type':'LOGIC_CAPABILITY_FRESH_ADMISSION','status':'PASS_SHADOW' if passed else 'WITHHOLD','generation':ledger['current_head'],
 'deficit':'LOGIC_ARCHITECTURAL_CEILING_FRESH_ADMISSION_V1',
 'effect':f"FRESH={fresh_score:.6f}; SYMMETRIC_CAUSAL={symmetric_causal}; POLY_CAUSAL={polynomial_causal}; NEXT={next_cap}",
 'source_path':f'receipts/yado-logic-architectural-ceiling-fresh-admission-v1-run-{run_id}.json','source_digest':receipt['receipt_sha256'],
 'run_id':run_id,'parent_event_hash':ledger['tail_event_hash'],'canonical_mutation':False,'promotion_applied':False}
e['event_hash']=event_hash(e);ledger['events'].append(e);ledger['event_count']=len(ledger['events']);ledger['tail_event_hash']=e['event_hash'];ledger['open_deficits']=[next_cap]
ledger['ledger_digest']=h({k:v for k,v in ledger.items() if k!='ledger_digest'});validate_ledger_v2(ledger);LEDGER.write_text(json.dumps(ledger,indent=2,sort_keys=True)+'\n')
print(json.dumps({'status':receipt['status'],'fresh_families':families,'fresh_score':fresh_score,'causal':receipt['causal'],'checks':checks,'next_required_capability':next_cap,'receipt_sha256':receipt['receipt_sha256']},indent=2,sort_keys=True,default=str))
if not passed:raise SystemExit('LOGIC_CEILING_FRESH_ADMISSION_WITHHELD')
