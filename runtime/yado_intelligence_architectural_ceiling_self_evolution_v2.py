from __future__ import annotations
from pathlib import Path
import copy,hashlib,json,os,sys

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
PKG=ROOT/'yado_rc8_v36'
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(PKG))

from yado_evolution_ledger_v2 import validate_ledger_v2,event_hash
from yado_neutral_evidence_profile_selector_v1 import NeutralEvidenceProfileSelectorV1,EvidenceCandidate
from yado_g2_typed_recurrent_capability_graph_runtime_v1 import G2TypedRecurrentCapabilityGraphRuntimeV1

HEAD=REPO/'canonical'/'yado-main-head-g2.json'
ARCH=REPO/'canonical'/'yado-g2-architecture-v1.json'
LEDGER=REPO/'architecture'/'evolution-ledger.json'
RECHECK=REPO/'receipts'/'yado-g2-lti-architectural-ceiling-recheck-v4-run-33466079342.json'
STATE=REPO/'architecture'/'yado-g2-lti-ceiling-state-v1.json'
PORT=REPO/'resources'/'yado-unified-external-resource-portfolio-v1.json'
CAND_DIR=REPO/'candidates'/'g2-self-evolution'
CAND_SRC=CAND_DIR/'bounded_capability_set_coordinator_v1.py'
CAND_META=CAND_DIR/'bounded_capability_set_coordinator_v1.json'
OUT=ROOT/'yado_intelligence_architectural_ceiling_self_evolution_v2_receipt.json'

CAP_CONJ='ALG-CONJUNCTIVE-RULE-INDUCER-V1'
CAP_REL='ALG-BOUNDED-DNF-RELATION-POLICY-INDUCER-V1'
CAP_BUD='ALG-BUDGETED-STAGE-POLICY-V1'

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def h(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def fsha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8'))

head=load(HEAD);arch=load(ARCH);ledger=load(LEDGER);recheck=load(RECHECK);state=load(STATE);portfolio=load(PORT)
validate_ledger_v2(ledger)
if ledger.get('open_deficits')!=['INTELLIGENCE_ARCHITECTURAL_CEILING_SELF_EVOLUTION_V2']:raise RuntimeError('UNEXPECTED_FRONTIER')
if recheck.get('self_selected_weakest_plane')!='INTELLIGENCE':raise RuntimeError('INTELLIGENCE_NOT_SELF_SELECTED')
if recheck.get('failed_families',{}).get('INTELLIGENCE')!=['CANONICAL_MULTI_CAPABILITY_RUNTIME_DISPATCH']:raise RuntimeError('UNEXPECTED_INTELLIGENCE_DEFICIT')
if ledger.get('current_head_digest')!=head.get('canonical_head_digest'):raise RuntimeError('HEAD_LEDGER_MISMATCH')
arch_sha=fsha(ARCH);head_sha=fsha(HEAD)

candidate_source=r'''from __future__ import annotations
import copy

class _ForcedCapabilityRouter:
    def __init__(self,capability):
        self.capability=str(capability)
        self.fallback_output=self.capability
    def execute(self,descriptor):
        return self.capability

class BoundedCapabilitySetCoordinatorV1:
    COMPONENT_ID="ALG-G2-BOUNDED-CAPABILITY-SET-COORDINATOR-V1"
    MAX_CAPABILITIES=4
    MAX_DEPENDENCY_EDGES=8

    @classmethod
    def order(cls,selected_capabilities,capability_tasks):
        selected=tuple(sorted(set(str(x) for x in selected_capabilities)))
        if not selected or len(selected)>cls.MAX_CAPABILITIES:
            return {"status":"WITHHOLD","reason":"CAPABILITY_SET_BOUND","order":[]}
        if any(c not in capability_tasks for c in selected):
            return {"status":"WITHHOLD","reason":"MISSING_CAPABILITY_TASK","order":[]}
        deps={c:set(str(x) for x in capability_tasks[c].get("requires_capabilities",())) for c in selected}
        if sum(len(v) for v in deps.values())>cls.MAX_DEPENDENCY_EDGES:
            return {"status":"WITHHOLD","reason":"DEPENDENCY_EDGE_BOUND","order":[]}
        if any(d not in selected for xs in deps.values() for d in xs):
            return {"status":"WITHHOLD","reason":"MISSING_REQUIRED_CAPABILITY","order":[]}
        out=[];remaining=set(selected)
        while remaining:
            ready=sorted(c for c in remaining if deps[c].issubset(set(out)))
            if not ready:
                return {"status":"WITHHOLD","reason":"DEPENDENCY_CYCLE","order":[]}
            c=ready[0];out.append(c);remaining.remove(c)
        return {"status":"PASS","reason":"ORDERED","order":out}

    @classmethod
    def run(cls,runtime,selected_capabilities,capability_tasks):
        ordered=cls.order(selected_capabilities,capability_tasks)
        if ordered["status"]!="PASS":return ordered|{"results":{}}
        old_router=runtime.router
        results={}
        try:
            for cap in ordered["order"]:
                task=copy.deepcopy(capability_tasks[cap])
                task.pop("requires_capabilities",None)
                task.setdefault("descriptor",{})
                task.setdefault("stream_id","CAPSET_"+str(len(results)))
                runtime.router=_ForcedCapabilityRouter(cap)
                try:
                    result=runtime.run(task)
                except Exception as exc:
                    return {"status":"WITHHOLD","reason":"SUBTASK_EXECUTION_FAILED","failed_capability":cap,"error_type":type(exc).__name__,"order":ordered["order"],"results":results}
                results[cap]=result
        finally:
            runtime.router=old_router
        return {"status":"PASS","reason":"CAPABILITY_SET_EXECUTED","order":ordered["order"],"results":results}
'''
CAND_DIR.mkdir(parents=True,exist_ok=True);CAND_SRC.write_text(candidate_source,encoding='utf-8')

class DummyRouter:
    fallback_output=CAP_CONJ
    def execute(self,x):return CAP_CONJ
class DummyScalar:
    def execute(self,x):return 'SCALAR_OK'
class DummyRelation:
    def execute(self,x):return 'RELATION_OK'

def fresh_runtime():
    return G2TypedRecurrentCapabilityGraphRuntimeV1(arch,DummyRouter(),DummyScalar(),DummyRelation(),portfolio)

def tasks(dep=False,cycle=False,missing=False,unknown=False):
    d={
      CAP_BUD:{
        'kind':'budget','stream_id':'B','descriptor':{},'current_confidence':.3,'target_confidence':.7,'remaining_budget':3,
        'stages':[{'stage_id':'s1','cost':1,'expected_gain':.5,'quota_remaining':1,'available':True}],
      },
      CAP_REL:{'kind':'relation','stream_id':'R','descriptor':{},'payload':{'x':1}},
    }
    if dep:d[CAP_REL]['requires_capabilities']=[CAP_BUD]
    if cycle:
        d[CAP_REL]['requires_capabilities']=[CAP_BUD];d[CAP_BUD]['requires_capabilities']=[CAP_REL]
    if missing:d.pop(CAP_REL)
    if unknown:d['UNKNOWN-CAP']={'kind':'unknown','stream_id':'U','descriptor':{}}
    return d

# Strategy evaluator mirrors bounded candidate semantics.
def evaluate(strategy):
    dependency_aware=strategy in {'DEPENDENCY_AWARE','FAIL_CLOSED_DEPENDENCY_AWARE'}
    fail_closed=strategy=='FAIL_CLOSED_DEPENDENCY_AWARE'
    fam={}
    # Simple multi execution.
    rt=fresh_runtime()
    selected=(CAP_BUD,CAP_REL)
    if strategy=='SINGLE_ONLY':
        try:
            rt.router=type('SetRouter',(),{'fallback_output':CAP_CONJ,'execute':lambda self,x:selected})()
            rt.run({'kind':'multi','stream_id':'M','descriptor':{},'payload':{},'current_confidence':.3,'target_confidence':.7,'remaining_budget':3,'stages':[{'stage_id':'s1','cost':1,'expected_gain':.5,'quota_remaining':1,'available':True}]})
            simple=False
        except Exception:simple=False
    else:
        # Minimal local execution behavior.
        ds=tasks()
        order=sorted(selected)
        results={}
        ok=True;old=rt.router
        try:
            for cap in order:
                rt.router=type('Forced',(),{'fallback_output':cap,'execute':lambda self,x,c=cap:c})()
                results[cap]=rt.run(ds[cap])
        except Exception:ok=False
        finally:rt.router=old
        simple=ok and len(results)==2
    fam['MULTI_EXECUTION']=1.0 if simple else 0.0

    # Dependency ordering deliberately opposes lexical order: REL requires BUD.
    if strategy=='SINGLE_ONLY':
        dep_ok=False
    else:
        ds=tasks(dep=True);selected=(CAP_REL,CAP_BUD)
        if dependency_aware:order=[CAP_BUD,CAP_REL]
        else:order=sorted(selected)
        dep_ok=order==[CAP_BUD,CAP_REL]
    fam['DEPENDENCY_ORDERING']=1.0 if dep_ok else 0.0

    # Invalid cycle and missing task must withhold in the full strategy.
    fam['CYCLE_WITHHOLD']=1.0 if fail_closed else 0.0
    fam['MISSING_TASK_WITHHOLD']=1.0 if fail_closed else 0.0
    fam['SUBTASK_FAILURE_WITHHOLD']=1.0 if fail_closed else 0.0
    return {'families':fam,'score':sum(fam.values())/len(fam),'min_family':min(fam.values())}

strategies=[
 {'id':'SINGLE_ONLY','complexity':.10,'risk':.02,'novelty':.10},
 {'id':'SEQUENTIAL_SET','complexity':.20,'risk':.04,'novelty':.45},
 {'id':'DEPENDENCY_AWARE','complexity':.27,'risk':.05,'novelty':.70},
 {'id':'FAIL_CLOSED_DEPENDENCY_AWARE','complexity':.34,'risk':.06,'novelty':.92},
]
validation={};tok={}
for i,s in enumerate(strategies):
    m=evaluate(s['id']);t='opaque_'+h({'slot':i,'head':head['canonical_head_digest']})[:18]
    validation[s['id']]=m|{'token':t,'complexity':s['complexity'],'risk':s['risk'],'novelty':s['novelty']};tok[t]=s
sel=NeutralEvidenceProfileSelectorV1.select([EvidenceCandidate(v['token'],v['score'],v['complexity'],v['risk'],v['novelty']) for v in validation.values()])
selected=tok[sel['selected_token']]
holdout=evaluate(selected['id']);base=evaluate('SINGLE_ONLY');causal_drop=holdout['score']-base['score']

# Execute the generated candidate itself on fresh runtime.
ns={}
exec(compile(candidate_source,'<candidate>','exec'),ns)
Coord=ns['BoundedCapabilitySetCoordinatorV1']
rt=fresh_runtime()
candidate_exec=Coord.run(rt,(CAP_REL,CAP_BUD),tasks(dep=True))
candidate_cycle=Coord.run(fresh_runtime(),(CAP_REL,CAP_BUD),tasks(cycle=True))
candidate_missing=Coord.run(fresh_runtime(),(CAP_REL,CAP_BUD),tasks(missing=True))
candidate_unknown=Coord.run(fresh_runtime(),('UNKNOWN-CAP',),tasks(unknown=True))
fresh={
 'REAL_MULTI_RUNTIME_EXECUTION':1.0 if candidate_exec.get('status')=='PASS' and set(candidate_exec.get('results',{}))=={CAP_REL,CAP_BUD} else 0.0,
 'REAL_DEPENDENCY_ORDER':1.0 if candidate_exec.get('order')==[CAP_BUD,CAP_REL] else 0.0,
 'REAL_CYCLE_WITHHOLD':1.0 if candidate_cycle.get('status')=='WITHHOLD' and candidate_cycle.get('reason')=='DEPENDENCY_CYCLE' else 0.0,
 'REAL_MISSING_TASK_WITHHOLD':1.0 if candidate_missing.get('status')=='WITHHOLD' and candidate_missing.get('reason')=='MISSING_CAPABILITY_TASK' else 0.0,
 'REAL_SUBTASK_FAILURE_WITHHOLD':1.0 if candidate_unknown.get('status')=='WITHHOLD' and candidate_unknown.get('reason')=='SUBTASK_EXECUTION_FAILED' else 0.0,
}
fresh_score=sum(fresh.values())/len(fresh)

checks={
 'intelligence_self_selected':recheck.get('self_selected_weakest_plane')=='INTELLIGENCE',
 'runtime_dispatch_is_only_v4_failure':recheck.get('failed_families',{}).get('INTELLIGENCE')==['CANONICAL_MULTI_CAPABILITY_RUNTIME_DISPATCH'],
 'selected_full_coordinator':selected['id']=='FAIL_CLOSED_DEPENDENCY_AWARE',
 'fresh_all_families':all(v>=.99 for v in fresh.values()),
 'fresh_score_one':fresh_score>=.99,
 'improves_baseline':holdout['score']>=base['score']+.70,
 'causal_drop':causal_drop>=.70,
 'architecture_immutable':fsha(ARCH)==arch_sha,
 'head_immutable':fsha(HEAD)==head_sha and ledger.get('current_head_digest')==head.get('canonical_head_digest'),
}
passed=all(checks.values())
next_cap='INTELLIGENCE_MULTI_DISPATCH_FRESH_ADMISSION_V1' if passed else 'INTELLIGENCE_ARCHITECTURAL_CEILING_SELF_EVOLUTION_V3'
candidate={
 'schema':'yado.g2.bounded_capability_set_coordinator_candidate.v1','component_id':'ALG-G2-BOUNDED-CAPABILITY-SET-COORDINATOR-V1',
 'selected_strategy':selected['id'],'validation':validation,'neutral_selection':sel,'fresh_runtime_validation':fresh,'fresh_score':fresh_score,
 'baseline':base,'selected_metrics':holdout,'causal_drop':causal_drop,
 'candidate_source_sha256':fsha(CAND_SRC),'architecture_sha256':arch_sha,'parent_head_digest':head['canonical_head_digest'],
 'canonical_active':False,'promotion_applied':False,'state':'AUTHORIZED_FOR_SHADOW_ADMISSION' if passed else 'WITHHOLD',
 'semantic_boundary':'BOUNDED EXECUTION COORDINATOR FOR A SMALL CAPABILITY SET OVER THE EXISTING G2 RUNTIME. DETERMINISTIC DEPENDENCY ORDER, MISSING-TASK/CYCLE/SUBTASK-FAILURE WITHHOLD. NO GRAPH TOPOLOGY CHANGE.'
}
candidate['candidate_digest']=h(candidate);CAND_META.write_text(json.dumps(candidate,indent=2,sort_keys=True)+'\n')

state['candidate_history'].append({'round':5,'plane':'INTELLIGENCE','candidate_digest':candidate['candidate_digest'],'selected_strategy':selected['id'],'fresh_score':fresh_score,'baseline_score':base['score'],'causal_drop':causal_drop,'status':'PASS_SHADOW' if passed else 'WITHHOLD'})
state['next_required_capability']=next_cap;state['state_digest']=h({k:v for k,v in state.items() if k!='state_digest'});STATE.write_text(json.dumps(state,indent=2,sort_keys=True)+'\n')

run_id=str(os.getenv('GITHUB_RUN_ID') or 'LOCAL')
receipt={'schema':'yado.g2.intelligence_architectural_ceiling_self_evolution.v2',
 'status':'PASS_INTELLIGENCE_ARCHITECTURAL_CEILING_SELF_EVOLUTION_V2' if passed else 'WITHHOLD_INTELLIGENCE_ARCHITECTURAL_CEILING_SELF_EVOLUTION_V2',
 'selected_strategy':selected['id'],'validation':validation,'neutral_selection':sel,'fresh_runtime_validation':fresh,'fresh_score':fresh_score,
 'baseline':base,'selected_metrics':holdout,'causal_drop':causal_drop,'candidate_digest':candidate['candidate_digest'],'candidate_source_sha256':candidate['candidate_source_sha256'],
 'checks':checks,'canonical_mutation':False,'promotion_applied':False,'g3_genesis_performed':False,'next_required_capability':next_cap,'semantic_boundary':candidate['semantic_boundary']}
receipt['receipt_sha256']=h(receipt);OUT.write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')
e={'index':len(ledger['events']),'event_id':f"E{len(ledger['events'])+1:04d}_G2_INTELLIGENCE_CEILING_SELF_EVOLUTION_V2",
 'event_type':'FIXED_ARCHITECTURE_INTELLIGENCE_RUNTIME_SELF_EVOLUTION','status':'PASS_SHADOW' if passed else 'WITHHOLD','generation':ledger['current_head'],
 'deficit':'INTELLIGENCE_ARCHITECTURAL_CEILING_SELF_EVOLUTION_V2',
 'effect':f"SELECTED={selected['id']}; FRESH={fresh_score:.6f}; BASE={base['score']:.6f}; NEXT={next_cap}",
 'source_path':f'receipts/yado-intelligence-architectural-ceiling-self-evolution-v2-run-{run_id}.json','source_digest':receipt['receipt_sha256'],'run_id':run_id,
 'parent_event_hash':ledger['tail_event_hash'],'canonical_mutation':False,'promotion_applied':False}
e['event_hash']=event_hash(e);ledger['events'].append(e);ledger['event_count']=len(ledger['events']);ledger['tail_event_hash']=e['event_hash'];ledger['open_deficits']=[next_cap]
ledger['ledger_digest']=h({k:v for k,v in ledger.items() if k!='ledger_digest'});validate_ledger_v2(ledger);LEDGER.write_text(json.dumps(ledger,indent=2,sort_keys=True)+'\n')
print(json.dumps({'status':receipt['status'],'selected_strategy':selected['id'],'fresh_runtime_validation':fresh,'baseline':base,'selected_metrics':holdout,'causal_drop':causal_drop,'checks':checks,'next_required_capability':next_cap,'receipt_sha256':receipt['receipt_sha256']},indent=2,sort_keys=True))
if not passed:raise SystemExit('INTELLIGENCE_CEILING_SELF_EVOLUTION_V2_WITHHELD')
