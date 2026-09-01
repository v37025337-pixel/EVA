from __future__ import annotations
from pathlib import Path
import ast,hashlib,importlib.util,json,os,sys

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
sys.path.insert(0,str(ROOT))
from yado_evolution_ledger_v2 import validate_ledger_v2,event_hash

HEAD=REPO/'canonical'/'yado-main-head-g2.json'
ARCH=REPO/'canonical'/'yado-g2-architecture-v1.json'
LEDGER=REPO/'architecture'/'evolution-ledger.json'
META=REPO/'candidates'/'g2-self-evolution'/'ambiguity_aware_program_repair_v11.json'
SRC=REPO/'candidates'/'g2-self-evolution'/'ambiguity_aware_program_repair_v11.py'
V10SRC=REPO/'candidates'/'g2-self-evolution'/'canonical_split_recursive_program_repair_v10.py'
OUT=ROOT/'yado_code_plateau_fresh_admission_v9_receipt.json'

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def h(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def fsha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8'))

head=load(HEAD);ledger=load(LEDGER);meta=load(META)
validate_ledger_v2(ledger)
if ledger.get('open_deficits')!=['CODE_PLATEAU_FRESH_ADMISSION_V9']:raise RuntimeError('UNEXPECTED_FRONTIER')
if meta.get('state')!='AUTHORIZED_FOR_SHADOW_ADMISSION':raise RuntimeError('CANDIDATE_NOT_AUTHORIZED')
if fsha(SRC)!=meta.get('candidate_source_sha256'):raise RuntimeError('SOURCE_DRIFT')
if ledger.get('current_head_digest')!=head.get('canonical_head_digest'):raise RuntimeError('HEAD_LEDGER_MISMATCH')
arch_sha=fsha(ARCH);head_sha=fsha(HEAD)

def load_cls(path,name,modname):
    sp=importlib.util.spec_from_file_location(modname,path)
    m=importlib.util.module_from_spec(sp);sys.modules[sp.name]=m;sp.loader.exec_module(m)
    return getattr(m,name)

V11=load_cls(SRC,'AmbiguityAwareProgramRepairV11','_v11_admit')
V10=load_cls(V10SRC,'CanonicalSplitRecursiveProgramRepairV10','_v10_ablate')

def run(cls,src,fn,tr):
    try:return cls.repair(src,fn,tr,max_candidates=24000,max_edit_depth=2)
    except Exception as e:return {'source':None,'error':type(e).__name__}

def exec_score(cls,r,fn,hold):
    if not r.get('source'):return 0.0
    try:return sum(cls.execute(r['source'],fn,args)==exp for args,exp in hold)/len(hold)
    except Exception:return 0.0

fresh={};details={}

# Ambiguous gap 1: no observations at x=2,3; two thresholds fit train.
amb1=[((-7,),-14),((-4,),-8),((0,),0),((1,),1),((4,),13),((8,),25)]
r1=run(V11,'def f(x):\n    return x\n','f',amb1)
fresh['AMBIGUOUS_GAP_WITHHOLD_A']=1.0 if r1.get('reason')=='AMBIGUOUS_UNSEEN_THRESHOLD' else 0.0
details['AMBIGUOUS_GAP_WITHHOLD_A']=r1

# Resolve the same family by providing every integer around the transition.
res1=amb1+[((2,),2),((3,),3)]
rr1=run(V11,'def f(x):\n    return x\n','f',res1)
fresh['RESOLVED_GAP_COMMIT_A']=exec_score(V11,rr1,'f',[((-9,),-18),((2,),2),((3,),3),((5,),16),((10,),31)])
details['RESOLVED_GAP_COMMIT_A']=rr1

# Ambiguous negative gap.
amb2=[((-9,),9),((-5,),5),((-1,),-2),((0,),0),((2,),4),((5,),16)]
r2=run(V11,'def f(x):\n    return x\n','f',amb2)
fresh['AMBIGUOUS_GAP_WITHHOLD_B']=1.0 if r2.get('reason')=='AMBIGUOUS_UNSEEN_THRESHOLD' else 0.0
details['AMBIGUOUS_GAP_WITHHOLD_B']=r2

# Fully specified nested regime, adjacent boundary evidence removes ambiguity.
nested=[
 ((-5,),10),((-4,),8),((-3,),6),  # -2*x
 ((-2,),-4),((-1,),-2),((0,),0),((1,),2), # 2*x
 ((2,),9),((3,),13),((4,),17) # 4*x+1
]
nr=run(V11,'def f(x):\n    return x\n','f',nested)
fresh['RESOLVED_NESTED_COMMIT']=exec_score(V11,nr,'f',[((-8,),16),((-2,),-4),((1,),2),((2,),9),((6,),25)])
details['RESOLVED_NESTED_COMMIT']=nr

# Non-threshold structural repairs must not be falsely withheld.
aff=[((-4,),-10),((0,),2),((2,),8),((5,),17)]
ar=run(V11,'def f(x):\n    return x\n','f',aff)
fresh['AFFINE_NO_FALSE_WITHHOLD']=exec_score(V11,ar,'f',[((-7,),-19),((1,),5),((9,),29)])
details['AFFINE_NO_FALSE_WITHHOLD']=ar

two=[((1,2),6),((2,4),9),((-2,3),4),((0,0),3)]
tr=run(V11,'def f(x,y):\n    return x-y+1\n','f',two)
fresh['TWO_EDIT_NO_FALSE_WITHHOLD']=exec_score(V11,tr,'f',[((5,6),14),((-3,-4),-4),((0,7),10)])
details['TWO_EDIT_NO_FALSE_WITHHOLD']=tr

fresh_score=sum(fresh.values())/len(fresh)

# Causal ablation: old V10 commits on ambiguous task, V11 withholds.
old=run(V10,'def f(x):\n    return x\n','f',amb1)
new=run(V11,'def f(x):\n    return x\n','f',amb1)
causal_ambiguity=(old.get('source') is not None and new.get('reason')=='AMBIGUOUS_UNSEEN_THRESHOLD')

# Safety/static checks.
tree=ast.parse(SRC.read_text(encoding='utf-8'))
danger_imports=[]
for n in ast.walk(tree):
    if isinstance(n,(ast.Import,ast.ImportFrom)):
        names=[a.name for a in n.names] if isinstance(n,ast.Import) else [n.module or '']
        if any((x or '').split('.')[0] in {'socket','subprocess','requests','urllib','aiohttp'} for x in names):
            danger_imports.extend(names)
unsafe_ok=False
try:V11.repair('import os\ndef f(x):\n    return x\n','f',[((1,),1)])
except Exception:unsafe_ok=True
multi_ok=False
try:V11.repair('def f(x):\n    return x\ndef h(x):\n    return x\n','f',[((1,),1)])
except Exception:multi_ok=True

checks={
 'fresh_all_green':all(v>=.99 for v in fresh.values()),
 'fresh_score_one':fresh_score>=.99,
 'causal_ambiguity_ablation':causal_ambiguity,
 'candidate_source_exact':fsha(SRC)==meta.get('candidate_source_sha256'),
 'source_no_network_imports':not danger_imports,
 'unsafe_program_rejected':unsafe_ok,
 'multi_function_rejected':multi_ok,
 'architecture_immutable':fsha(ARCH)==arch_sha,
 'canonical_head_immutable':fsha(HEAD)==head_sha and ledger.get('current_head_digest')==head.get('canonical_head_digest')
}
passed=all(checks.values())
next_cap='CODE_PLATEAU_CANONICAL_INTEGRATION_V2' if passed else 'CODE_PLATEAU_SELF_EVOLUTION_V10'

run_id=str(os.getenv('GITHUB_RUN_ID') or 'LOCAL')
receipt={'schema':'yado.g2.code_plateau_fresh_admission.v9',
 'status':'PASS_CODE_PLATEAU_FRESH_ADMISSION_V9' if passed else 'WITHHOLD_CODE_PLATEAU_FRESH_ADMISSION_V9',
 'candidate_digest':meta['candidate_digest'],'candidate_source_sha256':meta['candidate_source_sha256'],
 'fresh_families':fresh,'fresh_score':fresh_score,'details':details,
 'causal':{'ambiguity_ablation':causal_ambiguity,'v10_committed':old.get('source') is not None,'v11_reason':new.get('reason')},
 'checks':checks,'architecture_sha256':arch_sha,
 'canonical_mutation':False,'promotion_applied':False,'g3_genesis_performed':False,'next_required_capability':next_cap,
 'semantic_boundary':'INDEPENDENT FRESH ADMISSION OF AMBIGUITY-AWARE CODE REPAIR. AMBIGUOUS TRAIN-EQUIVALENT THRESHOLDS MUST WITHHOLD; ADDED BOUNDARY EVIDENCE MUST RESTORE EXECUTABLE REPAIR.'
}
receipt['receipt_sha256']=h(receipt);OUT.write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')

e={'index':len(ledger['events']),'event_id':f"E{len(ledger['events'])+1:04d}_G2_CODE_PLATEAU_FRESH_ADMISSION_V9",
 'event_type':'AMBIGUITY_AWARE_CODE_FRESH_ADMISSION','status':'PASS_SHADOW' if passed else 'WITHHOLD',
 'generation':ledger['current_head'],'deficit':'CODE_PLATEAU_FRESH_ADMISSION_V9',
 'effect':f"FRESH={fresh_score:.6f}; AMBIGUITY_CAUSAL={causal_ambiguity}; NEXT={next_cap}",
 'source_path':f'receipts/yado-code-plateau-fresh-admission-v9-run-{run_id}.json','source_digest':receipt['receipt_sha256'],
 'run_id':run_id,'parent_event_hash':ledger['tail_event_hash'],'canonical_mutation':False,'promotion_applied':False}
e['event_hash']=event_hash(e);ledger['events'].append(e);ledger['event_count']=len(ledger['events']);ledger['tail_event_hash']=e['event_hash']
ledger['open_deficits']=[next_cap];ledger['ledger_digest']=h({k:v for k,v in ledger.items() if k!='ledger_digest'})
validate_ledger_v2(ledger);LEDGER.write_text(json.dumps(ledger,indent=2,sort_keys=True)+'\n')

print(json.dumps({'status':receipt['status'],'fresh_families':fresh,'fresh_score':fresh_score,
 'causal':receipt['causal'],'checks':checks,'next_required_capability':next_cap,
 'receipt_sha256':receipt['receipt_sha256']},indent=2,sort_keys=True))
if not passed:raise SystemExit('CODE_PLATEAU_FRESH_ADMISSION_V9_WITHHELD')
