from __future__ import annotations
from pathlib import Path
from itertools import product
import ast,hashlib,importlib.util,json,os,sys

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
sys.path.insert(0,str(ROOT))
from yado_evolution_ledger_v2 import validate_ledger_v2,event_hash
from yado_bounded_compositional_schema_router_v1 import BoundedCompositionalSchemaRouterV1

HEAD=REPO/'canonical'/'yado-main-head-g2.json';ARCH=REPO/'canonical'/'yado-g2-architecture-v1.json';LEDGER=REPO/'architecture'/'evolution-ledger.json'
META=REPO/'candidates'/'g2-self-evolution'/'budget_adaptive_compositional_schema_router_v2.json';SRC=REPO/'candidates'/'g2-self-evolution'/'budget_adaptive_compositional_schema_router_v2.py'
OUT=ROOT/'yado_intelligence_plateau_fresh_admission_v1_receipt.json'
CAP_CONJ='ALG-CONJUNCTIVE-RULE-INDUCER-V1';CAP_REL='ALG-BOUNDED-DNF-RELATION-POLICY-INDUCER-V1';CAP_RES='RESOURCE-PORTFOLIO-V1'

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def h(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def fsha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8'))
head=load(HEAD);ledger=load(LEDGER);meta=load(META);validate_ledger_v2(ledger)
if ledger.get('open_deficits')!=['INTELLIGENCE_PLATEAU_FRESH_ADMISSION_V1']:raise RuntimeError('UNEXPECTED_FRONTIER')
if meta.get('state')!='AUTHORIZED_FOR_SHADOW_ADMISSION':raise RuntimeError('CANDIDATE_NOT_AUTHORIZED')
if fsha(SRC)!=meta.get('candidate_source_sha256'):raise RuntimeError('SOURCE_DRIFT')
if ledger.get('current_head_digest')!=head.get('canonical_head_digest'):raise RuntimeError('HEAD_LEDGER_MISMATCH')
arch_sha=fsha(ARCH);head_sha=fsha(HEAD)

sp=importlib.util.spec_from_file_location('_intelligence_v2_candidate',SRC);mod=importlib.util.module_from_spec(sp);sys.modules[sp.name]=mod;sp.loader.exec_module(mod)
V2=mod.BudgetAdaptiveCompositionalSchemaRouterV2;V1=BoundedCompositionalSchemaRouterV1

def field_cases(n,signal,train_n=480,test_n=240):
    fs=[f'g{i:02d}' for i in range(n-1)]+[signal];tr=[];te=[]
    for k in range(train_n):
        x={f:bool(((k+29)>>(i%8))&1) for i,f in enumerate(fs)};x[signal]=bool((k//4)%2)
        tr.append({'input':x,'expected':(CAP_REL,) if x[signal] else (CAP_CONJ,)})
    for k in range(test_n):
        x={f:bool(((k+83)>>(i%7))&1) for i,f in enumerate(fs)};x[signal]=bool((k//7)%2)
        te.append({'input':x,'expected':(CAP_REL,) if x[signal] else (CAP_CONJ,)})
    return fs,tr,te

fs,tr,te=field_cases(22,'zz_fresh_signal')
m=V2.fit(tr,CAP_CONJ);fresh={}
fresh['FIELD_WIDTH22_FRESH']=sum(V2.route(m,z['input'])==z['expected'] for z in te)/len(te)

pairs=[]
for a,b,c,d,e,f in product([False,True],repeat=6):
    out=set()
    if a and d:out.add(CAP_REL)
    if c and f:out.add(CAP_RES)
    if not out:out.add(CAP_CONJ)
    for _ in range(5):pairs.append({'input':{'a':a,'b':b,'c':c,'d':d,'e':e,'f':f},'expected':tuple(sorted(out))})
pm=V2.fit(pairs,CAP_CONJ);fresh['PAIRWISE_COMPOSITION_FRESH']=sum(V2.route(pm,z['input'])==z['expected'] for z in pairs)/len(pairs)

# 20-field schema alignment with unique signatures, and routing after alignment.
n=20;ref_names=[f'r{i:02d}' for i in range(n)];alias_names=[f'x{(i*7)%n:02d}' for i in range(n)]
refs=[];als=[]
for row in range(64):
    ref={}
    for j,f in enumerate(ref_names):
        mask=(1<<j)|(1<<((j+29)%64))
        ref[f]=bool((mask>>row)&1)
    ali={alias_names[j]:ref[ref_names[j]] for j in range(n)}
    refs.append(ref);als.append(ali)
al=V2.fit_schema_alignment(refs,als)
# Train a router where the last reference field is causal.
rtrain=[];rtest=[]
sig=ref_names[-1]
for k in range(400):
    x={f:bool(((k+31)>>(i%8))&1) for i,f in enumerate(ref_names)};x[sig]=bool((k//3)%2)
    rtrain.append({'input':x,'expected':(CAP_RES,) if x[sig] else (CAP_CONJ,)})
for k in range(160):
    x={f:bool(((k+97)>>(i%7))&1) for i,f in enumerate(ref_names)};x[sig]=bool((k//5)%2)
    rtest.append({'input':x,'expected':(CAP_RES,) if x[sig] else (CAP_CONJ,)})
rmodel=V2.fit(rtrain,CAP_CONJ)
alias_test=[]
for z in rtest:
    alias_test.append({'input':{alias_names[j]:z['input'][ref_names[j]] for j in range(n)},'expected':z['expected']})
fresh['ALIGNMENT20_ROUTING_TRANSFER']=sum(V2.route_aligned(rmodel,al,z['input'])==z['expected'] for z in alias_test)/len(alias_test)

# Existing simple one-field and <=16 field behavior regression.
simple=[]
for a,b in product([False,True],repeat=2):
    y=(CAP_REL,) if a else (CAP_CONJ,)
    for _ in range(12):simple.append({'input':{'a':a,'b':b},'expected':y})
sm=V2.fit(simple,CAP_CONJ);fresh['SIMPLE_ROUTING_REGRESSION']=sum(V2.route(sm,z['input'])==z['expected'] for z in simple)/len(simple)

# Fail-closed output and ambiguity boundaries.
out_cases=[]
for i in range(9):
    for r in range(6):out_cases.append({'input':{'slot':i},'expected':(f'OUT{i}',)})
om=V2.fit(out_cases,'OUT0');fresh['OUTPUT_BUDGET_WITHHOLD']=1.0 if om.get('kind')=='WITHHOLD' and om.get('reason')=='OUTPUT_BUDGET' else 0.0
ar=[{'a':bool(i%2),'b':bool(i%2),'c':bool((i//2)%2)} for i in range(28)];aa=[{'u':z['a'],'v':z['b'],'w':z['c']} for z in ar]
amb=V2.fit_schema_alignment(ar,aa);fresh['AMBIGUOUS_ALIGNMENT_WITHHOLD']=1.0 if amb.get('kind')=='WITHHOLD' else 0.0

fresh_score=sum(fresh.values())/len(fresh)

# Causal ablation against V1.
try:
    old=V1.fit(tr,CAP_CONJ);old_field=sum(V1.route(old,z['input'])==z['expected'] for z in te)/len(te)
except Exception:old_field=0.0
try:
    oldp=V1.fit(pairs,CAP_CONJ);old_pair=sum(V1.route(oldp,z['input'])==z['expected'] for z in pairs)/len(pairs)
except Exception:old_pair=0.0
try:
    oldal=V1.fit_schema_alignment(refs,als);old_align=sum(V1.route_aligned(V1.fit(rtrain,CAP_CONJ),oldal,z['input'])==z['expected'] for z in alias_test)/len(alias_test)
except Exception:old_align=0.0
causal_field=fresh['FIELD_WIDTH22_FRESH']-old_field>=.45
causal_pair=fresh['PAIRWISE_COMPOSITION_FRESH']-old_pair>=.40
causal_align=fresh['ALIGNMENT20_ROUTING_TRANSFER']-old_align>=.45

tree=ast.parse(SRC.read_text(encoding='utf-8'))
danger_calls={n.func.id for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id in {'eval','exec','compile','__import__'}}
danger_imports=[]
for node in ast.walk(tree):
    if isinstance(node,(ast.Import,ast.ImportFrom)):
        names=[a.name for a in node.names] if isinstance(node,ast.Import) else [node.module or '']
        if any(x.split('.')[0] in {'socket','subprocess','requests','urllib','aiohttp'} for x in names):danger_imports.extend(names)

checks={'fresh_all_families':all(v>=.99 for v in fresh.values()),'fresh_score_one':fresh_score>=.99,
 'field_mechanism_causal':causal_field,'pair_mechanism_causal':causal_pair,'alignment_mechanism_causal':causal_align,
 'compute_contract_exact':meta.get('compute_contract')=={'max_alignment_cells':V2.MAX_ALIGNMENT_CELLS,'max_field_cells':V2.MAX_FIELD_CELLS,'max_outputs':V2.MAX_OUTPUTS,'max_trigger_candidates':V2.MAX_TRIGGER_CANDIDATES,'max_trigger_width':V2.MAX_TRIGGER_WIDTH,'max_triggers_per_output':V2.MAX_TRIGGERS_PER_OUTPUT},
 'source_safe':not danger_calls and not danger_imports,'architecture_immutable':fsha(ARCH)==arch_sha,'canonical_head_immutable':fsha(HEAD)==head_sha and ledger.get('current_head_digest')==head.get('canonical_head_digest')}
passed=all(checks.values());next_cap='INTELLIGENCE_PLATEAU_CANONICAL_INTEGRATION_V1' if passed else 'INTELLIGENCE_PLATEAU_SELF_EVOLUTION_V2'
run_id=str(os.getenv('GITHUB_RUN_ID') or 'LOCAL')
receipt={'schema':'yado.g2.intelligence_plateau_fresh_admission.v1','status':'PASS_INTELLIGENCE_PLATEAU_FRESH_ADMISSION_V1' if passed else 'WITHHOLD_INTELLIGENCE_PLATEAU_FRESH_ADMISSION_V1',
 'candidate_digest':meta['candidate_digest'],'candidate_source_sha256':meta['candidate_source_sha256'],'fresh_families':fresh,'fresh_score':fresh_score,
 'causal':{'field':causal_field,'pair':causal_pair,'alignment':causal_align,'old_field_score':old_field,'old_pair_score':old_pair,'old_alignment_score':old_align},
 'compute_contract':meta.get('compute_contract'),'source_safety':{'danger_calls':sorted(danger_calls),'danger_imports':danger_imports},'checks':checks,
 'canonical_mutation':False,'promotion_applied':False,'g3_genesis_performed':False,'next_required_capability':next_cap,
 'semantic_boundary':'INDEPENDENT FRESH ADMISSION OF BUDGET-ADAPTIVE INTELLIGENCE ROUTER V2 ON WIDTH22, NEW PAIRWISE COMPOSITION, AND >16-FIELD PAIRED ALIGNMENT.'}
receipt['receipt_sha256']=h(receipt);OUT.write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')
e={'index':len(ledger['events']),'event_id':f"E{len(ledger['events'])+1:04d}_G2_INTELLIGENCE_PLATEAU_FRESH_ADMISSION_V1",'event_type':'INTELLIGENCE_PLATEAU_FRESH_ADMISSION',
 'status':'PASS_SHADOW' if passed else 'WITHHOLD','generation':ledger['current_head'],'deficit':'INTELLIGENCE_PLATEAU_FRESH_ADMISSION_V1',
 'effect':f"FRESH={fresh_score:.6f}; FIELD={causal_field}; PAIR={causal_pair}; ALIGN={causal_align}; NEXT={next_cap}",
 'source_path':f'receipts/yado-intelligence-plateau-fresh-admission-v1-run-{run_id}.json','source_digest':receipt['receipt_sha256'],'run_id':run_id,'parent_event_hash':ledger['tail_event_hash'],
 'canonical_mutation':False,'promotion_applied':False}
e['event_hash']=event_hash(e);ledger['events'].append(e);ledger['event_count']=len(ledger['events']);ledger['tail_event_hash']=e['event_hash'];ledger['open_deficits']=[next_cap]
ledger['ledger_digest']=h({k:v for k,v in ledger.items() if k!='ledger_digest'});validate_ledger_v2(ledger);LEDGER.write_text(json.dumps(ledger,indent=2,sort_keys=True)+'\n')
print(json.dumps({'status':receipt['status'],'fresh_families':fresh,'fresh_score':fresh_score,'causal':receipt['causal'],'checks':checks,'next_required_capability':next_cap,'receipt_sha256':receipt['receipt_sha256']},indent=2,sort_keys=True))
if not passed:raise SystemExit('INTELLIGENCE_PLATEAU_FRESH_ADMISSION_WITHHELD')
