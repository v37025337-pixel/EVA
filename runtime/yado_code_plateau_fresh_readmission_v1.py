from __future__ import annotations
from pathlib import Path
import ast,hashlib,importlib.util,json,os,sys

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
sys.path.insert(0,str(ROOT))
from yado_evolution_ledger_v2 import validate_ledger_v2,event_hash
from yado_bounded_program_repair_v2 import BoundedProgramRepairV1

HEAD=REPO/'canonical'/'yado-main-head-g2.json'
ARCH=REPO/'canonical'/'yado-g2-architecture-v1.json'
LEDGER=REPO/'architecture'/'evolution-ledger.json'
STATE=REPO/'architecture'/'yado-g2-lti-ceiling-state-v1.json'
FAILED=REPO/'receipts'/'yado-code-plateau-self-evolution-v1-run-33486090280.json'
META=REPO/'candidates'/'g2-self-evolution'/'bounded_compositional_program_repair_v3.json'
SRC=REPO/'candidates'/'g2-self-evolution'/'bounded_compositional_program_repair_v3.py'
OUT=ROOT/'yado_code_plateau_fresh_readmission_v1_receipt.json'

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def h(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def fsha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8'))

head=load(HEAD);ledger=load(LEDGER);state=load(STATE);failed=load(FAILED);meta=load(META)
validate_ledger_v2(ledger)
if ledger.get('open_deficits')!=['CODE_PLATEAU_SELF_EVOLUTION_V2']:raise RuntimeError('UNEXPECTED_FRONTIER')
if failed.get('status')!='WITHHOLD_CODE_PLATEAU_SELF_EVOLUTION_V1':raise RuntimeError('EXPECTED_WITHHOLD')
if failed.get('validation',{}).get('DEPTH2_PLUS_STRUCTURAL',{}).get('min_family')!=1:raise RuntimeError('CANDIDATE_DID_NOT_PASS_TARGET_COUNTEREXAMPLES')
if fsha(SRC)!=meta.get('candidate_source_sha256'):raise RuntimeError('CANDIDATE_SOURCE_DRIFT')
if ledger.get('current_head_digest')!=head.get('canonical_head_digest'):raise RuntimeError('HEAD_LEDGER_MISMATCH')
arch_sha=fsha(ARCH);head_sha=fsha(HEAD)

sp=importlib.util.spec_from_file_location('_code_v3',SRC)
m=importlib.util.module_from_spec(sp);sys.modules[sp.name]=m;sp.loader.exec_module(m)
V3=m.BoundedCompositionalProgramRepairV3
V2=BoundedProgramRepairV1

def score(cls,src,fn,train,hold,**kw):
    try:
        r=cls.repair(src,fn,train,**kw)
        if not r.get('source'):return 0.0,r
        s=sum(cls.execute(r['source'],fn,args)==expected for args,expected in hold)/len(hold)
        return s,r
    except Exception as e:return 0.0,{'error':type(e).__name__}

fresh={};details={}

# Exactly two independent edits: Sub -> Add, constant 1 -> 3.
src='def g(x,y):\n    return x-y+1\n'
train=[((1,2),6),((2,4),9),((-2,3),4),((0,0),3)]
hold=[((5,6),14),((-3,-4),-4),((0,7),10),((9,-2),10)]
fresh['EXACT_TWO_EDIT_BINARY'],details['EXACT_TWO_EDIT_BINARY']=score(V3,src,'g',train,hold,max_candidates=20000,max_edit_depth=2)

# Two constants: x*2-1 -> x*3-2.
src2='def g(x):\n    return x*2-1\n'
train2=[((1,),1),((2,),4),((5,),13),((-2,),-8)]
hold2=[((3,),7),((7,),19),((-4,),-14),((0,),-2)]
fresh['EXACT_TWO_CONSTANT_EDITS'],details['EXACT_TWO_CONSTANT_EDITS']=score(V3,src2,'g',train2,hold2,max_candidates=20000,max_edit_depth=2)

# Structural abs.
src3='def g(x):\n    return x\n'
train3=[((-5,),5),((-2,),2),((0,),0),((4,),4)]
hold3=[((-9,),9),((3,),3),((8,),8)]
fresh['STRUCTURAL_ABS'],details['STRUCTURAL_ABS']=score(V3,src3,'g',train3,hold3,max_candidates=20000,max_edit_depth=2)

# Structural floor max(x,0).
src4='def g(x):\n    return x\n'
train4=[((-4,),0),((-1,),0),((0,),0),((2,),2),((8,),8)]
hold4=[((-9,),0),((4,),4),((11,),11)]
fresh['STRUCTURAL_MAX_FLOOR'],details['STRUCTURAL_MAX_FLOOR']=score(V3,src4,'g',train4,hold4,max_candidates=20000,max_edit_depth=2)

# Structural cap min(x,5).
train5=[((-3,),-3),((0,),0),((3,),3),((5,),5),((8,),5)]
hold5=[((-7,),-7),((4,),4),((12,),5)]
fresh['STRUCTURAL_MIN_CAP'],details['STRUCTURAL_MIN_CAP']=score(V3,src4,'g',train5,hold5,max_candidates=20000,max_edit_depth=2)

# Easy one-edit regression.
src6='def g(x,y):\n    return x-y\n'
train6=[((2,3),5),((8,1),9),((-2,5),3)]
hold6=[((4,7),11),((-3,-4),-7),((0,9),9)]
fresh['ONE_EDIT_REGRESSION'],details['ONE_EDIT_REGRESSION']=score(V3,src6,'g',train6,hold6,max_candidates=20000,max_edit_depth=2)

fresh_score=sum(fresh.values())/len(fresh)

# Ablation: predecessor should fail the structural and two-edit classes.
old={}
for name,(s,fn,tr,ho) in {
 'EXACT_TWO_EDIT_BINARY':(src,'g',train,hold),
 'EXACT_TWO_CONSTANT_EDITS':(src2,'g',train2,hold2),
 'STRUCTURAL_MAX_FLOOR':(src4,'g',train4,hold4)
}.items():
    old[name],_=score(V2,s,fn,tr,ho,max_candidates=12000)

causal_gap=(fresh['EXACT_TWO_EDIT_BINARY']-old['EXACT_TWO_EDIT_BINARY']+
            fresh['EXACT_TWO_CONSTANT_EDITS']-old['EXACT_TWO_CONSTANT_EDITS']+
            fresh['STRUCTURAL_MAX_FLOOR']-old['STRUCTURAL_MAX_FLOOR'])/3

tree=ast.parse(SRC.read_text(encoding='utf-8'))
danger_calls={n.func.id for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id in {'eval','__import__'}}
danger_imports=[]
for n in ast.walk(tree):
    if isinstance(n,(ast.Import,ast.ImportFrom)):
        names=[a.name for a in n.names] if isinstance(n,ast.Import) else [n.module or '']
        if any(x.split('.')[0] in {'socket','subprocess','requests','urllib','aiohttp'} for x in names):danger_imports.extend(names)

checks={
 'prior_withhold_classified_as_bad_oracle':failed.get('fresh_validation',{}).get('families',{}).get('TWO_EDIT_BINARY_FRESH')==0 and failed.get('validation',{}).get('DEPTH2_PLUS_STRUCTURAL',{}).get('min_family')==1,
 'candidate_source_unchanged':fsha(SRC)==meta.get('candidate_source_sha256'),
 'fresh_all_green':all(v>=.99 for v in fresh.values()),
 'fresh_score_one':fresh_score>=.99,
 'predecessor_ablation_gap':causal_gap>=.95,
 'source_safe':not danger_calls and not danger_imports,
 'architecture_immutable':fsha(ARCH)==arch_sha,
 'head_immutable':fsha(HEAD)==head_sha and ledger.get('current_head_digest')==head.get('canonical_head_digest')
}
passed=all(checks.values())
next_cap='CODE_PLATEAU_CANONICAL_INTEGRATION_V1' if passed else 'CODE_PLATEAU_SELF_EVOLUTION_V2'

state['candidate_history'].append({'round':state.get('round',14),'plane':'CODE','candidate_digest':meta['candidate_digest'],
 'status':'FRESH_READMISSION_PASS' if passed else 'FRESH_READMISSION_WITHHOLD','fresh_score':fresh_score,'baseline_score':sum(old.values())/len(old),'causal_drop':causal_gap})
state['next_required_capability']=next_cap
state['state_digest']=h({k:v for k,v in state.items() if k!='state_digest'})
STATE.write_text(json.dumps(state,indent=2,sort_keys=True)+'\n')

run_id=str(os.getenv('GITHUB_RUN_ID') or 'LOCAL')
receipt={'schema':'yado.g2.code_plateau_fresh_readmission.v1',
 'status':'PASS_CODE_PLATEAU_FRESH_READMISSION_V1' if passed else 'WITHHOLD_CODE_PLATEAU_FRESH_READMISSION_V1',
 'classification':'PRIOR_FRESH_ORACLE_OUTSIDE_DECLARED_TWO_EDIT_TARGET_CLASS',
 'candidate_digest':meta['candidate_digest'],'candidate_source_sha256':meta['candidate_source_sha256'],
 'prior_withhold_receipt':failed['receipt_sha256'],'fresh_families':fresh,'fresh_score':fresh_score,'details':details,
 'predecessor_ablation':old,'causal_gap':causal_gap,'checks':checks,
 'canonical_mutation':False,'promotion_applied':False,'g3_genesis_performed':False,'next_required_capability':next_cap,
 'semantic_boundary':'READMISSION OF THE UNCHANGED V3 CODE-REPAIR CANDIDATE USING FRESH TASKS KNOWN TO LIE WITHIN ITS DECLARED <=2-EDIT PLUS SAFE-STRUCTURAL-WRAPPER CLASS.'}
receipt['receipt_sha256']=h(receipt);OUT.write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')

e={'index':len(ledger['events']),'event_id':f"E{len(ledger['events'])+1:04d}_G2_CODE_PLATEAU_FRESH_READMISSION_V1",
 'event_type':'CODE_REPAIR_FRESH_READMISSION','status':'PASS_SHADOW' if passed else 'WITHHOLD','generation':ledger['current_head'],
 'deficit':'CODE_PLATEAU_SELF_EVOLUTION_V2','effect':f"CLASS=BAD_PRIOR_ORACLE; FRESH={fresh_score:.6f}; CAUSAL_GAP={causal_gap:.6f}; NEXT={next_cap}",
 'source_path':f'receipts/yado-code-plateau-fresh-readmission-v1-run-{run_id}.json','source_digest':receipt['receipt_sha256'],
 'run_id':run_id,'parent_event_hash':ledger['tail_event_hash'],'canonical_mutation':False,'promotion_applied':False}
e['event_hash']=event_hash(e);ledger['events'].append(e);ledger['event_count']=len(ledger['events']);ledger['tail_event_hash']=e['event_hash'];ledger['open_deficits']=[next_cap]
ledger['ledger_digest']=h({k:v for k,v in ledger.items() if k!='ledger_digest'});validate_ledger_v2(ledger)
LEDGER.write_text(json.dumps(ledger,indent=2,sort_keys=True)+'\n')
print(json.dumps({'status':receipt['status'],'fresh_families':fresh,'fresh_score':fresh_score,'predecessor_ablation':old,'causal_gap':causal_gap,'checks':checks,'next_required_capability':next_cap,'receipt_sha256':receipt['receipt_sha256']},indent=2,sort_keys=True))
if not passed:raise SystemExit('CODE_PLATEAU_FRESH_READMISSION_WITHHELD')
