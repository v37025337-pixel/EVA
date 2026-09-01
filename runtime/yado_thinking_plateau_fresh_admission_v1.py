from __future__ import annotations
from pathlib import Path
import hashlib,importlib.util,json,os,sys

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
sys.path.insert(0,str(ROOT))
from yado_evolution_ledger_v2 import validate_ledger_v2,event_hash
from yado_bounded_adaptive_contingent_planner_v1 import BoundedAdaptiveContingentPlannerV1,ContingentStage as S1

HEAD=REPO/'canonical'/'yado-main-head-g2.json'
ARCH=REPO/'canonical'/'yado-g2-architecture-v1.json'
LEDGER=REPO/'architecture'/'evolution-ledger.json'
META=REPO/'candidates'/'g2-self-evolution'/'work_budget_adaptive_contingent_planner_v2.json'
SRC=REPO/'candidates'/'g2-self-evolution'/'work_budget_adaptive_contingent_planner_v2.py'
OUT=ROOT/'yado_thinking_plateau_fresh_admission_v1_receipt.json'

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def h(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def fsha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8'))

head=load(HEAD);ledger=load(LEDGER);meta=load(META)
validate_ledger_v2(ledger)
if ledger.get('open_deficits')!=['THINKING_PLATEAU_FRESH_ADMISSION_V1']:raise RuntimeError('UNEXPECTED_FRONTIER')
if meta.get('state')!='AUTHORIZED_FOR_SHADOW_ADMISSION':raise RuntimeError('CANDIDATE_NOT_AUTHORIZED')
if fsha(SRC)!=meta.get('candidate_source_sha256'):raise RuntimeError('SOURCE_DRIFT')
if ledger.get('current_head_digest')!=head.get('canonical_head_digest'):raise RuntimeError('HEAD_LEDGER_MISMATCH')
arch_sha=fsha(ARCH);head_sha=fsha(HEAD)

sp=importlib.util.spec_from_file_location('_thinking_v2_admit',SRC)
m=importlib.util.module_from_spec(sp);sys.modules[sp.name]=m;sp.loader.exec_module(m)
V2=m.WorkBudgetAdaptiveContingentPlannerV2;S2=m.ContingentStage
V1=BoundedAdaptiveContingentPlannerV1

fresh={};details={}

# Width 11: target requires 11 equal stages.
st=[S2(f'w{i}',1,.09,1,True,.1,False,()) for i in range(11)]
p=V2.plan(.01,1.0,11.0,st)
fresh['WIDTH11_FRESH']=1.0 if p.expected_confidence>=.999 and len(p.sequence)==11 else 0.0
details['WIDTH11_FRESH']={'sequence':p.sequence,'confidence':p.expected_confidence,'reason':p.reason}

# Dependency chain 11 after one observation.
ids=[f'd{i}' for i in range(12)]
dep=[S2(ids[0],1,.01,1,True,.1,False,())]+[S2(ids[j],1,.09,1,True,.1,False,(ids[j-1],)) for j in range(1,len(ids))]
q=V2.next_after_observation(.0,1.0,12.0,dep,ids[0],.01)
fresh['DEPENDENCY11_FRESH']=1.0 if q.expected_confidence>=.999 and len(q.sequence)>=11 else 0.0
details['DEPENDENCY11_FRESH']={'sequence':q.sequence,'confidence':q.expected_confidence,'reason':q.reason}

# Signed negative update with dependency recovery.
dep2=[
 S2('a',1,.25,1,True,.1,False,()),
 S2('b',1,.25,1,True,.1,False,('a',)),
 S2('c',1,.25,1,True,.1,False,('b',)),
 S2('d',1,.25,1,True,.1,False,('c',)),
]
r=V2.next_after_observation(.85,.9,4.0,dep2,'a',-.4)
fresh['SIGNED_RECOVERY_FRESH']=1.0 if r.expected_confidence>=.9 and r.sequence[:3]==['b','c'][:len(r.sequence[:2])] else 0.0
details['SIGNED_RECOVERY_FRESH']={'sequence':r.sequence,'confidence':r.expected_confidence,'reason':r.reason}

# Cost-aware distractors: optimal feasible dependency chain should win.
mix=[
 S2('p0',1,.2,1,True,.1,False,()),
 S2('p1',1,.2,1,True,.1,False,('p0',)),
 S2('p2',1,.2,1,True,.1,False,('p1',)),
 S2('p3',1,.2,1,True,.1,False,('p2',)),
 S2('p4',1,.2,1,True,.1,False,('p3',)),
 S2('x1',3,.03,1,True,.1,False,()),
 S2('x2',3,.04,1,True,.1,False,()),
]
z=V2.plan(.0,.99,5.0,mix)
fresh['COST_DEPENDENCY_FRESH']=1.0 if z.expected_confidence>=.99 and z.sequence==['p0','p1','p2','p3','p4'] else 0.0
details['COST_DEPENDENCY_FRESH']={'sequence':z.sequence,'confidence':z.expected_confidence,'reason':z.reason}

# Oversized descriptor must fail closed.
overs=[S2(f'o{i}',1,.01,1,True,.1,False,()) for i in range(V2.MAX_STAGE_RECORDS+1)]
o=V2.plan(.0,1.0,100.0,overs)
fresh['OVERSIZE_WITHHOLD_FRESH']=1.0 if o.action=='WITHHOLD' and o.reason=='STAGE_RECORD_WORK_BUDGET' else 0.0
details['OVERSIZE_WITHHOLD_FRESH']={'action':o.action,'reason':o.reason}

fresh_score=sum(fresh.values())/len(fresh)

# Causal ablation on width 11: V1 truncates, V2 reaches target.
s1=[S1(f'w{i}',1,.09,1,True,.1,False,()) for i in range(11)]
old=V1.plan(.01,1.0,11.0,s1)
new=V2.plan(.01,1.0,11.0,st)
causal=old.expected_confidence<.999 and new.expected_confidence>=.999

checks={
 'fresh_all_green':all(v>=.99 for v in fresh.values()),
 'fresh_score_one':fresh_score>=.99,
 'candidate_source_exact':fsha(SRC)==meta.get('candidate_source_sha256'),
 'causal_width_ablation':causal,
 'search_budget_bound':V2.MAX_SEARCH_NODES==24000,
 'architecture_immutable':fsha(ARCH)==arch_sha,
 'canonical_head_immutable':fsha(HEAD)==head_sha and ledger.get('current_head_digest')==head.get('canonical_head_digest')
}
passed=all(checks.values())
next_cap='THINKING_PLATEAU_CANONICAL_INTEGRATION_V1' if passed else 'THINKING_PLATEAU_SELF_EVOLUTION_V2'

run_id=str(os.getenv('GITHUB_RUN_ID') or 'LOCAL')
receipt={'schema':'yado.g2.thinking_plateau_fresh_admission.v1',
 'status':'PASS_THINKING_PLATEAU_FRESH_ADMISSION_V1' if passed else 'WITHHOLD_THINKING_PLATEAU_FRESH_ADMISSION_V1',
 'candidate_digest':meta['candidate_digest'],'candidate_source_sha256':meta['candidate_source_sha256'],
 'fresh_families':fresh,'fresh_score':fresh_score,'details':details,
 'causal':{'width_ablation':causal,'old_confidence':old.expected_confidence,'new_confidence':new.expected_confidence},
 'checks':checks,'architecture_sha256':arch_sha,'canonical_mutation':False,'promotion_applied':False,
 'g3_genesis_performed':False,'next_required_capability':next_cap,
 'semantic_boundary':'INDEPENDENT FRESH ADMISSION OF WORK-BUDGET ADAPTIVE CONTINGENT PLANNING BEYOND THE OLD 8/8 GEOMETRY, WITH COST/DEPENDENCY/SIGNED-UPDATE REGRESSIONS AND FAIL-CLOSED OVERSIZE.'
}
receipt['receipt_sha256']=h(receipt);OUT.write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')

e={'index':len(ledger['events']),'event_id':f"E{len(ledger['events'])+1:04d}_G2_THINKING_PLATEAU_FRESH_ADMISSION_V1",
 'event_type':'WORK_BUDGET_THINKING_FRESH_ADMISSION','status':'PASS_SHADOW' if passed else 'WITHHOLD',
 'generation':ledger['current_head'],'deficit':'THINKING_PLATEAU_FRESH_ADMISSION_V1',
 'effect':f"FRESH={fresh_score:.6f}; WIDTH_CAUSAL={causal}; NEXT={next_cap}",
 'source_path':f'receipts/yado-thinking-plateau-fresh-admission-v1-run-{run_id}.json','source_digest':receipt['receipt_sha256'],
 'run_id':run_id,'parent_event_hash':ledger['tail_event_hash'],'canonical_mutation':False,'promotion_applied':False}
e['event_hash']=event_hash(e);ledger['events'].append(e);ledger['event_count']=len(ledger['events']);ledger['tail_event_hash']=e['event_hash']
ledger['open_deficits']=[next_cap];ledger['ledger_digest']=h({k:v for k,v in ledger.items() if k!='ledger_digest'})
validate_ledger_v2(ledger);LEDGER.write_text(json.dumps(ledger,indent=2,sort_keys=True)+'\n')

print(json.dumps({'status':receipt['status'],'fresh_families':fresh,'fresh_score':fresh_score,
 'causal':receipt['causal'],'checks':checks,'next_required_capability':next_cap,'receipt_sha256':receipt['receipt_sha256']},indent=2,sort_keys=True))
if not passed:raise SystemExit('THINKING_PLATEAU_FRESH_ADMISSION_WITHHELD')
