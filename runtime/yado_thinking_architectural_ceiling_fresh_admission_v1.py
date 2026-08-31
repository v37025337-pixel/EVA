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
META=REPO/'candidates'/'g2-self-evolution'/'bounded_adaptive_contingent_planner_v1.json'
SRC=REPO/'candidates'/'g2-self-evolution'/'bounded_adaptive_contingent_planner_v1.py'
OUT=ROOT/'yado_thinking_architectural_ceiling_fresh_admission_v1_receipt.json'

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def h(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def fsha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8'))

head=load(HEAD);ledger=load(LEDGER);meta=load(META)
validate_ledger_v2(ledger)
if ledger.get('open_deficits')!=['THINKING_ARCHITECTURAL_CEILING_FRESH_ADMISSION_V1']:raise RuntimeError('UNEXPECTED_FRONTIER')
if meta.get('state')!='AUTHORIZED_FOR_SHADOW_ADMISSION':raise RuntimeError('CANDIDATE_NOT_AUTHORIZED')
if fsha(SRC)!=meta.get('candidate_source_sha256'):raise RuntimeError('SOURCE_DRIFT')
if ledger.get('current_head_digest')!=head.get('canonical_head_digest'):raise RuntimeError('HEAD_LEDGER_MISMATCH')
arch_sha=fsha(ARCH);head_file_sha=fsha(HEAD)

spec=importlib.util.spec_from_file_location('_thinking_candidate',SRC)
mod=importlib.util.module_from_spec(spec);sys.modules[spec.name]=mod;spec.loader.exec_module(mod)
Planner=mod.BoundedAdaptiveContingentPlannerV1;Stage=mod.ContingentStage

# Fresh 1: horizon 7 with uneven gains/costs; a valid reaching plan needs >4 steps.
h_ok=0;h_n=120
for i in range(h_n):
    stages=[
      Stage(f'H{i}_{j}',1.0+(j%3)*.1,.075+(j%2)*.005,1,True,.1,False,())
      for j in range(7)
    ]
    p=Planner.plan(.20,.70,8.0,stages)
    h_ok+=p.feasible and p.expected_confidence>=.70-1e-9 and len(p.sequence)>=6
horizon_score=h_ok/h_n

# Fresh 2: signed negative observations of varying magnitude.
n_ok=0;n_n=120
for i in range(n_n):
    a=f'N{i}_A';b=f'N{i}_B';c=f'N{i}_C'
    stages=[Stage(a,1,.18,1,True,.1,False,()),Stage(b,1,.22,1,True,.1,False,()),Stage(c,1,.25,1,True,.1,False,())]
    obs=[-.10,-.20,-.30][i%3]
    p=Planner.next_after_observation(.62,.82,3.0,stages,a,obs)
    true_conf=max(0.0,.62+obs)
    # Planner may choose B+C; exact expected confidence is determined by its chosen sequence.
    gain=sum(next(s.expected_gain for s in stages if s.stage_id==sid) for sid in p.sequence)
    expected=min(1.0,true_conf+gain)
    n_ok+=abs(p.expected_confidence-expected)<1e-9
negative_score=n_ok/n_n

# Fresh 3: prerequisite chain of length 4 after a completed root.
d_ok=0;d_n=120
for i in range(d_n):
    ids=[f'D{i}_{j}' for j in range(5)]
    stages=[Stage(ids[0],1,.08,1,True,.1,False,())]
    for j in range(1,5):
        stages.append(Stage(ids[j],1,.16,1,False,.1,False,(ids[j-1],)))
    p=Planner.next_after_observation(.28,.80,6.0,stages,ids[0],.08)
    d_ok+=p.action==ids[1] and p.sequence[:4]==ids[1:5] and p.expected_confidence>=.80-1e-9
dependency_score=d_ok/d_n

# Fresh 4: mixed signed setback + dependency chain + bounded budget.
m_ok=0;m_n=120
for i in range(m_n):
    root=f'M{i}_R';ids=[f'M{i}_{j}' for j in range(5)]
    stages=[Stage(root,1,.10,1,True,.1,False,())]
    prev=root
    for j,sid in enumerate(ids):
        stages.append(Stage(sid,1,.14+(j%2)*.02,1,False,.1,False,(prev,)))
        prev=sid
    p=Planner.next_after_observation(.46,.82,7.0,stages,root,-.08)
    m_ok+=p.action==ids[0] and p.total_cost<=6.0+1e-9 and p.expected_confidence>=.82-1e-9
mixed_score=m_ok/m_n

# Fresh 5: fail closed on impossible budget.
w_ok=0;w_n=100
for i in range(w_n):
    stages=[Stage(f'W{i}_{j}',3,.12,1,True,.1,False,()) for j in range(4)]
    p=Planner.plan(.20,.90,2.0,stages)
    w_ok+=p.action=='WITHHOLD' and not p.feasible
withhold_score=w_ok/w_n

fresh={'HORIZON7':horizon_score,'SIGNED_NEGATIVE':negative_score,'DEPENDENCY_CHAIN4':dependency_score,'MIXED_CONTINGENT':mixed_score,'BOUNDED_WITHHOLD':withhold_score}
fresh_score=sum(fresh.values())/len(fresh)

# Feature ablations use subclasses; each removed feature must expose a real loss.
class NoSigned(Planner):SIGNED_OBSERVATION=False
class NoDependency(Planner):DEPENDENCY_AWARE=False
class Shallow(Planner):MAX_PLAN_DEPTH=4

# Signed ablation.
a=Stage('A',1,.2,1,True,.1,False,());b=Stage('B',1,.2,1,True,.1,False,())
full=Planner.next_after_observation(.55,.8,2,[a,b],'A',-.25)
nos=NoSigned.next_after_observation(.55,.8,2,[a,b],'A',-.25)
signed_causal=abs(full.expected_confidence-nos.expected_confidence)>.20

# Dependency ablation.
a=Stage('DA',1,.1,1,True,.1,False,());b=Stage('DB',1,.4,1,False,.1,False,('DA',))
full_d=Planner.next_after_observation(.3,.75,3,[a,b],'DA',.1)
nod=NoDependency.next_after_observation(.3,.75,3,[a,b],'DA',.1)
dependency_causal=(full_d.action=='DB' and nod.action!='DB')

# Depth ablation.
st=[Stage(f'Z{j}',1,.1,1,True,.1,False,()) for j in range(6)]
full_h=Planner.plan(.2,.8,6,st);sh=Shallow.plan(.2,.8,6,st)
depth_causal=(full_h.expected_confidence>=.8-1e-9 and sh.expected_confidence<.8-1e-9)

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
 'signed_feature_causal':signed_causal,
 'dependency_feature_causal':dependency_causal,
 'depth_feature_causal':depth_causal,
 'source_safe':not danger_calls and not danger_imports,
 'bounded_depth':Planner.MAX_PLAN_DEPTH<=8 and Planner.MAX_STAGES<=8,
 'architecture_immutable':fsha(ARCH)==arch_sha,
 'canonical_head_immutable':fsha(HEAD)==head_file_sha and ledger.get('current_head_digest')==head.get('canonical_head_digest'),
}
passed=all(checks.values())
next_cap='THINKING_ARCHITECTURAL_CEILING_CANONICAL_INTEGRATION_V1' if passed else 'THINKING_ARCHITECTURAL_CEILING_SELF_EVOLUTION_V2'
run_id=str(os.getenv('GITHUB_RUN_ID') or 'LOCAL')
receipt={'schema':'yado.g2.thinking_architectural_ceiling_fresh_admission.v1',
 'status':'PASS_THINKING_ARCHITECTURAL_CEILING_FRESH_ADMISSION_V1' if passed else 'WITHHOLD_THINKING_ARCHITECTURAL_CEILING_FRESH_ADMISSION_V1',
 'candidate_digest':meta['candidate_digest'],'candidate_source_sha256':meta['candidate_source_sha256'],
 'fresh_families':fresh,'fresh_score':fresh_score,
 'causal':{'signed':signed_causal,'dependency':dependency_causal,'depth':depth_causal},
 'source_safety':{'danger_calls':sorted(danger_calls),'danger_imports':danger_imports},'checks':checks,
 'canonical_mutation':False,'promotion_applied':False,'generation_transition':False,'g3_genesis_performed':False,
 'next_required_capability':next_cap,
 'semantic_boundary':'INDEPENDENT FRESH ADMISSION FOR BOUNDED ADAPTIVE CONTINGENT PLANNING INSIDE FIXED G2 THINKING PLANE.'
}
receipt['receipt_sha256']=h(receipt);OUT.write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')

e={'index':len(ledger['events']),'event_id':f"E{len(ledger['events'])+1:04d}_G2_THINKING_CEILING_FRESH_ADMISSION",
 'event_type':'THINKING_CAPABILITY_FRESH_ADMISSION','status':'PASS_SHADOW' if passed else 'WITHHOLD',
 'generation':ledger['current_head'],'deficit':'THINKING_ARCHITECTURAL_CEILING_FRESH_ADMISSION_V1',
 'effect':f"FRESH={fresh_score:.6f}; SIGNED={signed_causal}; DEPENDENCY={dependency_causal}; DEPTH={depth_causal}; NEXT={next_cap}",
 'source_path':f'receipts/yado-thinking-architectural-ceiling-fresh-admission-v1-run-{run_id}.json',
 'source_digest':receipt['receipt_sha256'],'run_id':run_id,'parent_event_hash':ledger['tail_event_hash'],
 'canonical_mutation':False,'promotion_applied':False}
e['event_hash']=event_hash(e);ledger['events'].append(e);ledger['event_count']=len(ledger['events']);ledger['tail_event_hash']=e['event_hash']
ledger['open_deficits']=[next_cap];ledger['ledger_digest']=h({k:v for k,v in ledger.items() if k!='ledger_digest'})
validate_ledger_v2(ledger);LEDGER.write_text(json.dumps(ledger,indent=2,sort_keys=True)+'\n')
print(json.dumps({'status':receipt['status'],'fresh_families':fresh,'fresh_score':fresh_score,'causal':receipt['causal'],'checks':checks,'next_required_capability':next_cap,'receipt_sha256':receipt['receipt_sha256']},indent=2,sort_keys=True))
if not passed:raise SystemExit('THINKING_CEILING_FRESH_ADMISSION_WITHHELD')
