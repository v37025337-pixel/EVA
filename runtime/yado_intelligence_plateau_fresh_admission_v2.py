from __future__ import annotations
from pathlib import Path
from itertools import product
import ast,hashlib,importlib.util,json,os,random,sys

ROOT=Path(__file__).resolve().parent;REPO=ROOT.parent;sys.path.insert(0,str(ROOT))
from yado_evolution_ledger_v2 import validate_ledger_v2,event_hash

HEAD=REPO/'canonical'/'yado-main-head-g2.json';ARCH=REPO/'canonical'/'yado-g2-architecture-v1.json';LEDGER=REPO/'architecture'/'evolution-ledger.json'
META=REPO/'candidates'/'g2-self-evolution'/'coverage_pruned_compositional_schema_router_v3.json';SRC=REPO/'candidates'/'g2-self-evolution'/'coverage_pruned_compositional_schema_router_v3.py'
V2SRC=REPO/'candidates'/'g2-self-evolution'/'budget_adaptive_compositional_schema_router_v2.py'
OUT=ROOT/'yado_intelligence_plateau_fresh_admission_v2_receipt.json'
CAP_CONJ='ALG-CONJUNCTIVE-RULE-INDUCER-V1';CAP_REL='ALG-BOUNDED-DNF-RELATION-POLICY-INDUCER-V1';CAP_RES='RESOURCE-PORTFOLIO-V1'

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def h(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def fsha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8'))
head=load(HEAD);ledger=load(LEDGER);meta=load(META);validate_ledger_v2(ledger)
if ledger.get('open_deficits')!=['INTELLIGENCE_PLATEAU_FRESH_ADMISSION_V2']:raise RuntimeError('UNEXPECTED_FRONTIER')
if meta.get('state')!='AUTHORIZED_FOR_SHADOW_ADMISSION':raise RuntimeError('CANDIDATE_NOT_AUTHORIZED')
if fsha(SRC)!=meta.get('candidate_source_sha256'):raise RuntimeError('SOURCE_DRIFT')
if ledger.get('current_head_digest')!=head.get('canonical_head_digest'):raise RuntimeError('HEAD_LEDGER_MISMATCH')
arch_sha=fsha(ARCH);head_sha=fsha(HEAD)
sp=importlib.util.spec_from_file_location('_router_v3',SRC);m3=importlib.util.module_from_spec(sp);sys.modules[sp.name]=m3;sp.loader.exec_module(m3);V3=m3.CoveragePrunedCompositionalSchemaRouterV3
sp2=importlib.util.spec_from_file_location('_router_v2_old',V2SRC);m2=importlib.util.module_from_spec(sp2);sys.modules[sp2.name]=m2;sp2.loader.exec_module(m2);V2=m2.BudgetAdaptiveCompositionalSchemaRouterV2

# Fresh width26 with deliberately spurious TRAIN-ONLY pair correlation.
def shifted_cases(train=True,n=26,count=600):
    rng=random.Random(22001 if train else 22002);rows=[];noise=[f'n{i:02d}' for i in range(n-4)]
    for k in range(count):
        s=bool(k%2);x={f:bool(rng.getrandbits(1)) for f in noise}
        if train:
            if s:
                patterns=[(1,1),(1,0),(0,1),(0,0)];p,q=patterns[(k//2)%4]
            else:
                patterns=[(1,0),(0,1),(0,0)];p,q=patterns[(k//2)%3]
        else:
            patterns=[(1,1),(1,0),(0,1),(0,0)];p,q=patterns[(k//2)%4]
        x.update({'p_spurious':bool(p),'q_spurious':bool(q),'zz_true_signal':s,'zz_noise':bool(rng.getrandbits(1))})
        rows.append({'input':x,'expected':(CAP_REL,) if s else (CAP_CONJ,)})
    return rows
tr=shifted_cases(True,26,640);te=shifted_cases(False,26,320)
v3m=V3.fit(tr,CAP_CONJ);v2m=V2.fit(tr,CAP_CONJ)
fresh={}
fresh['WIDTH26_SPURIOUS_PAIR_SHIFT']=sum(V3.route(v3m,z['input'])==z['expected'] for z in te)/len(te)
old_shift=sum(V2.route(v2m,z['input'])==z['expected'] for z in te)/len(te)

# Fresh mixed-width rule: single OR pair plus a separate pair output.
mix=[]
for s,a,b,c,d in product([False,True],repeat=5):
    out=set()
    if s or (a and b):out.add(CAP_REL)
    if c and d:out.add(CAP_RES)
    if not out:out.add(CAP_CONJ)
    for _ in range(9):mix.append({'input':{'s':s,'a':a,'b':b,'c':c,'d':d},'expected':tuple(sorted(out))})
mm=V3.fit(mix,CAP_CONJ);fresh['MIXED_WIDTH_SET_COVER']=sum(V3.route(mm,z['input'])==z['expected'] for z in mix)/len(mix)

# Another pair topology.
pair=[]
for a,b,c,d,e,f in product([False,True],repeat=6):
    out=set()
    if b and e:out.add(CAP_REL)
    if a and f:out.add(CAP_RES)
    if not out:out.add(CAP_CONJ)
    for _ in range(5):pair.append({'input':{'a':a,'b':b,'c':c,'d':d,'e':e,'f':f},'expected':tuple(sorted(out))})
ppm=V3.fit(pair,CAP_CONJ);fresh['PAIRWISE_TOPOLOGY_FRESH']=sum(V3.route(ppm,z['input'])==z['expected'] for z in pair)/len(pair)

# 26-field schema alignment with unique two-hot signatures.
n=26;refs=[];als=[];rnames=[f'r{i:02d}' for i in range(n)];anames=[f'a{(i*11)%n:02d}' for i in range(n)]
for row in range(64):
    ref={}
    for j,f in enumerate(rnames):
        mask=(1<<j)|(1<<((j+31)%64));ref[f]=bool((mask>>row)&1)
    refs.append(ref);als.append({anames[j]:ref[rnames[j]] for j in range(n)})
al=V3.fit_schema_alignment(refs,als)
fresh['ALIGNMENT26_UNIQUE_SIGNATURES']=1.0 if al.get('kind')=='EXACT_PAIRED_SCHEMA_ALIGNMENT_V3' and len(al.get('map',{}))==26 else 0.0

# Safety/fail-closed: output budget and ambiguity.
outs=[]
for i in range(9):
    for _ in range(6):outs.append({'input':{'slot':i},'expected':(f'O{i}',)})
om=V3.fit(outs,'O0');fresh['OUTPUT_BUDGET_WITHHOLD']=1.0 if om.get('kind')=='WITHHOLD' and om.get('reason')=='OUTPUT_BUDGET' else 0.0
ar=[{'x':bool(i%2),'y':bool(i%2),'z':bool((i//2)%2)} for i in range(30)];aa=[{'u':q['x'],'v':q['y'],'w':q['z']} for q in ar]
amb=V3.fit_schema_alignment(ar,aa);fresh['AMBIGUOUS_ALIGNMENT_WITHHOLD']=1.0 if amb.get('kind')=='WITHHOLD' else 0.0
fresh_score=sum(fresh.values())/len(fresh)

causal_pruning=fresh['WIDTH26_SPURIOUS_PAIR_SHIFT']-old_shift>=.10
tree=ast.parse(SRC.read_text(encoding='utf-8'))
danger_calls={n.func.id for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id in {'eval','exec','compile','__import__'}}
danger_imports=[]
for node in ast.walk(tree):
    if isinstance(node,(ast.Import,ast.ImportFrom)):
        names=[a.name for a in node.names] if isinstance(node,ast.Import) else [node.module or '']
        if any(x.split('.')[0] in {'socket','subprocess','requests','urllib','aiohttp'} for x in names):danger_imports.extend(names)
checks={'fresh_all_families':all(v>=.99 for v in fresh.values()),'fresh_score_one':fresh_score>=.99,'coverage_pruning_causal':causal_pruning,
 'old_v2_shift_score_below_one':old_shift<.90,'source_safe':not danger_calls and not danger_imports,
 'architecture_immutable':fsha(ARCH)==arch_sha,'canonical_head_immutable':fsha(HEAD)==head_sha and ledger.get('current_head_digest')==head.get('canonical_head_digest')}
passed=all(checks.values());next_cap='INTELLIGENCE_PLATEAU_CANONICAL_INTEGRATION_V1' if passed else 'INTELLIGENCE_PLATEAU_SELF_EVOLUTION_V3'
run_id=str(os.getenv('GITHUB_RUN_ID') or 'LOCAL')
receipt={'schema':'yado.g2.intelligence_plateau_fresh_admission.v2','status':'PASS_INTELLIGENCE_PLATEAU_FRESH_ADMISSION_V2' if passed else 'WITHHOLD_INTELLIGENCE_PLATEAU_FRESH_ADMISSION_V2',
 'candidate_digest':meta['candidate_digest'],'candidate_source_sha256':meta['candidate_source_sha256'],'fresh_families':fresh,'fresh_score':fresh_score,
 'causal':{'coverage_pruning':causal_pruning,'old_v2_distribution_shift_score':old_shift,'new_v3_distribution_shift_score':fresh['WIDTH26_SPURIOUS_PAIR_SHIFT']},
 'checks':checks,'source_safety':{'danger_calls':sorted(danger_calls),'danger_imports':danger_imports},
 'canonical_mutation':False,'promotion_applied':False,'g3_genesis_performed':False,'next_required_capability':next_cap,
 'semantic_boundary':'FRESH ADMISSION OF COVERAGE-PRUNED INTELLIGENCE V3 AGAINST A NEW TRAIN-ONLY SPURIOUS PAIR CORRELATION, MIXED-WIDTH SET COVER, PAIRWISE TOPOLOGY, AND ALIGNMENT26.'}
receipt['receipt_sha256']=h(receipt);OUT.write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')
e={'index':len(ledger['events']),'event_id':f"E{len(ledger['events'])+1:04d}_G2_INTELLIGENCE_PLATEAU_FRESH_ADMISSION_V2",'event_type':'COUNTEREXAMPLE_REPAIR_FRESH_ADMISSION',
 'status':'PASS_SHADOW' if passed else 'WITHHOLD','generation':ledger['current_head'],'deficit':'INTELLIGENCE_PLATEAU_FRESH_ADMISSION_V2',
 'effect':f"FRESH={fresh_score:.6f}; PRUNING_CAUSAL={causal_pruning}; OLD={old_shift:.6f}; NEW={fresh['WIDTH26_SPURIOUS_PAIR_SHIFT']:.6f}; NEXT={next_cap}",
 'source_path':f'receipts/yado-intelligence-plateau-fresh-admission-v2-run-{run_id}.json','source_digest':receipt['receipt_sha256'],'run_id':run_id,'parent_event_hash':ledger['tail_event_hash'],
 'canonical_mutation':False,'promotion_applied':False}
e['event_hash']=event_hash(e);ledger['events'].append(e);ledger['event_count']=len(ledger['events']);ledger['tail_event_hash']=e['event_hash'];ledger['open_deficits']=[next_cap]
ledger['ledger_digest']=h({k:v for k,v in ledger.items() if k!='ledger_digest'});validate_ledger_v2(ledger);LEDGER.write_text(json.dumps(ledger,indent=2,sort_keys=True)+'\n')
print(json.dumps({'status':receipt['status'],'fresh_families':fresh,'fresh_score':fresh_score,'causal':receipt['causal'],'checks':checks,'next_required_capability':next_cap,'receipt_sha256':receipt['receipt_sha256']},indent=2,sort_keys=True))
if not passed:raise SystemExit('INTELLIGENCE_PLATEAU_FRESH_ADMISSION_V2_WITHHELD')
