from __future__ import annotations
from pathlib import Path
import ast,hashlib,importlib.util,json,os,sys

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
PKG=ROOT/'yado_rc8_v36'
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(PKG))

from yado_evolution_ledger_v2 import validate_ledger_v2,event_hash
from yado_g2_typed_recurrent_capability_graph_runtime_v1 import G2TypedRecurrentCapabilityGraphRuntimeV1

HEAD=REPO/'canonical'/'yado-main-head-g2.json'
ARCH=REPO/'canonical'/'yado-g2-architecture-v1.json'
LEDGER=REPO/'architecture'/'evolution-ledger.json'
PORT=REPO/'resources'/'yado-unified-external-resource-portfolio-v1.json'
META=REPO/'candidates'/'g2-self-evolution'/'bounded_capability_set_coordinator_v1.json'
SRC=REPO/'candidates'/'g2-self-evolution'/'bounded_capability_set_coordinator_v1.py'
OUT=ROOT/'yado_intelligence_multi_dispatch_fresh_admission_v1_receipt.json'

CAP_CONJ='ALG-CONJUNCTIVE-RULE-INDUCER-V1'
CAP_REL='ALG-BOUNDED-DNF-RELATION-POLICY-INDUCER-V1'
CAP_BUD='ALG-BUDGETED-STAGE-POLICY-V1'

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def h(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def fsha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8'))

head=load(HEAD);arch=load(ARCH);ledger=load(LEDGER);portfolio=load(PORT);meta=load(META)
validate_ledger_v2(ledger)
if ledger.get('open_deficits')!=['INTELLIGENCE_MULTI_DISPATCH_FRESH_ADMISSION_V1']:raise RuntimeError('UNEXPECTED_FRONTIER')
if meta.get('state')!='AUTHORIZED_FOR_SHADOW_ADMISSION':raise RuntimeError('CANDIDATE_NOT_AUTHORIZED')
if fsha(SRC)!=meta.get('candidate_source_sha256'):raise RuntimeError('SOURCE_DRIFT')
if ledger.get('current_head_digest')!=head.get('canonical_head_digest'):raise RuntimeError('HEAD_LEDGER_MISMATCH')
arch_sha=fsha(ARCH);head_sha=fsha(HEAD)

sp=importlib.util.spec_from_file_location('_coord_candidate',SRC)
mod=importlib.util.module_from_spec(sp);sys.modules[sp.name]=mod;sp.loader.exec_module(mod)
C=mod.BoundedCapabilitySetCoordinatorV1

class DummyRouter:
    fallback_output=CAP_CONJ
    def execute(self,x):return CAP_CONJ
class DummyScalar:
    def execute(self,x):return 'S_OK'
class DummyRelation:
    def execute(self,x):return 'R_OK'

def runtime():
    return G2TypedRecurrentCapabilityGraphRuntimeV1(arch,DummyRouter(),DummyScalar(),DummyRelation(),portfolio)

def three_tasks():
    return {
      CAP_BUD:{
        'kind':'budget','stream_id':'B3','descriptor':{},'current_confidence':.25,'target_confidence':.7,'remaining_budget':3,
        'stages':[{'stage_id':'stage','cost':1,'expected_gain':.5,'quota_remaining':1,'available':True}],
      },
      CAP_REL:{
        'kind':'relation','stream_id':'R3','descriptor':{},'payload':{'v':1},
        'requires_capabilities':[CAP_BUD],
      },
      CAP_CONJ:{
        'kind':'scalar','stream_id':'C3','descriptor':{},'payload':{'v':1},
        'requires_capabilities':[CAP_REL],
      },
    }

fresh={}
rt=runtime();original_router=rt.router
three=C.run(rt,(CAP_CONJ,CAP_REL,CAP_BUD),three_tasks())
fresh['THREE_CAPABILITY_EXECUTION']=1.0 if three.get('status')=='PASS' and set(three.get('results',{}))=={CAP_CONJ,CAP_REL,CAP_BUD} else 0.0
fresh['CHAINED_DEPENDENCY_ORDER']=1.0 if three.get('order')==[CAP_BUD,CAP_REL,CAP_CONJ] else 0.0
fresh['ROUTER_RESTORED_AFTER_COORDINATION']=1.0 if rt.router is original_router else 0.0

# Duplicated selections should deduplicate safely.
dup=C.run(runtime(),(CAP_BUD,CAP_REL,CAP_REL,CAP_BUD),{
 CAP_BUD:three_tasks()[CAP_BUD],CAP_REL:{k:v for k,v in three_tasks()[CAP_REL].items() if k!='requires_capabilities'}
})
fresh['DUPLICATE_SELECTION_DEDUP']=1.0 if dup.get('status')=='PASS' and len(dup.get('order',[]))==2 else 0.0

# Capability count bound.
many={f'C{i}':{'kind':'x'} for i in range(5)}
bound=C.order(tuple(many),many)
fresh['CAPABILITY_COUNT_BOUND_WITHHOLD']=1.0 if bound.get('status')=='WITHHOLD' and bound.get('reason')=='CAPABILITY_SET_BOUND' else 0.0

# Missing required capability.
missing={
 CAP_REL:{'kind':'relation','descriptor':{},'payload':{},'requires_capabilities':[CAP_BUD]}
}
mr=C.order((CAP_REL,),missing)
fresh['MISSING_REQUIRED_CAPABILITY_WITHHOLD']=1.0 if mr.get('status')=='WITHHOLD' and mr.get('reason')=='MISSING_REQUIRED_CAPABILITY' else 0.0

# Dependency edge bound with four fake capabilities.
fake=('A','B','C','D')
edge_tasks={
 'A':{'requires_capabilities':['B','C','D']},
 'B':{'requires_capabilities':['A','C','D']},
 'C':{'requires_capabilities':['A','B','D']},
 'D':{'requires_capabilities':[]},
}
eb=C.order(fake,edge_tasks)
fresh['DEPENDENCY_EDGE_BOUND_WITHHOLD']=1.0 if eb.get('status')=='WITHHOLD' and eb.get('reason')=='DEPENDENCY_EDGE_BOUND' else 0.0

# Current raw runtime remains the ablation: tuple selection cannot execute directly.
class SetRouter:
    fallback_output=CAP_CONJ
    def execute(self,x):return (CAP_BUD,CAP_REL)
ab=runtime();ab.router=SetRouter()
try:
    ab.run({'kind':'multi','stream_id':'ABL','descriptor':{},'payload':{},'current_confidence':.3,'target_confidence':.7,'remaining_budget':3,
            'stages':[{'stage_id':'s','cost':1,'expected_gain':.5,'quota_remaining':1,'available':True}]})
    ablation_score=1.0
except Exception:
    ablation_score=0.0
coordinator_score=fresh['THREE_CAPABILITY_EXECUTION']
causal=coordinator_score-ablation_score>=.99

fresh_score=sum(fresh.values())/len(fresh)
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
 'runtime_dispatch_causal':causal,
 'bounded_capability_count':C.MAX_CAPABILITIES<=4,
 'bounded_dependency_edges':C.MAX_DEPENDENCY_EDGES<=8,
 'source_safe':not danger_calls and not danger_imports,
 'architecture_immutable':fsha(ARCH)==arch_sha,
 'canonical_head_immutable':fsha(HEAD)==head_sha and ledger.get('current_head_digest')==head.get('canonical_head_digest'),
}
passed=all(checks.values())
next_cap='INTELLIGENCE_MULTI_DISPATCH_CANONICAL_INTEGRATION_V1' if passed else 'INTELLIGENCE_ARCHITECTURAL_CEILING_SELF_EVOLUTION_V3'
run_id=str(os.getenv('GITHUB_RUN_ID') or 'LOCAL')
receipt={'schema':'yado.g2.intelligence_multi_dispatch_fresh_admission.v1',
 'status':'PASS_INTELLIGENCE_MULTI_DISPATCH_FRESH_ADMISSION_V1' if passed else 'WITHHOLD_INTELLIGENCE_MULTI_DISPATCH_FRESH_ADMISSION_V1',
 'candidate_digest':meta['candidate_digest'],'candidate_source_sha256':meta['candidate_source_sha256'],'fresh_families':fresh,'fresh_score':fresh_score,
 'causal':{'coordinator_score':coordinator_score,'raw_runtime_set_dispatch_ablation_score':ablation_score,'causal':causal},
 'checks':checks,'source_safety':{'danger_calls':sorted(danger_calls),'danger_imports':danger_imports},
 'canonical_mutation':False,'promotion_applied':False,'g3_genesis_performed':False,'next_required_capability':next_cap,
 'semantic_boundary':'INDEPENDENT FRESH ADMISSION OF BOUNDED MULTI-CAPABILITY RUNTIME COORDINATION OVER THE EXISTING G2 RUNTIME; NO TOPOLOGY CHANGE.'
}
receipt['receipt_sha256']=h(receipt);OUT.write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')
e={'index':len(ledger['events']),'event_id':f"E{len(ledger['events'])+1:04d}_G2_INTELLIGENCE_MULTI_DISPATCH_FRESH_ADMISSION",
 'event_type':'INTELLIGENCE_RUNTIME_COORDINATION_FRESH_ADMISSION','status':'PASS_SHADOW' if passed else 'WITHHOLD','generation':ledger['current_head'],
 'deficit':'INTELLIGENCE_MULTI_DISPATCH_FRESH_ADMISSION_V1',
 'effect':f"FRESH={fresh_score:.6f}; CAUSAL={causal}; NEXT={next_cap}",
 'source_path':f'receipts/yado-intelligence-multi-dispatch-fresh-admission-v1-run-{run_id}.json','source_digest':receipt['receipt_sha256'],
 'run_id':run_id,'parent_event_hash':ledger['tail_event_hash'],'canonical_mutation':False,'promotion_applied':False}
e['event_hash']=event_hash(e);ledger['events'].append(e);ledger['event_count']=len(ledger['events']);ledger['tail_event_hash']=e['event_hash'];ledger['open_deficits']=[next_cap]
ledger['ledger_digest']=h({k:v for k,v in ledger.items() if k!='ledger_digest'});validate_ledger_v2(ledger);LEDGER.write_text(json.dumps(ledger,indent=2,sort_keys=True)+'\n')
print(json.dumps({'status':receipt['status'],'fresh_families':fresh,'fresh_score':fresh_score,'causal':receipt['causal'],'checks':checks,'next_required_capability':next_cap,'receipt_sha256':receipt['receipt_sha256']},indent=2,sort_keys=True))
if not passed:raise SystemExit('INTELLIGENCE_MULTI_DISPATCH_FRESH_ADMISSION_WITHHELD')
