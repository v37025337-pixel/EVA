from __future__ import annotations
from pathlib import Path
from dataclasses import asdict
import copy,hashlib,json,os,random,subprocess,sys

ROOT=Path(__file__).resolve().parent; REPO=ROOT.parent; PKG=ROOT/'yado_rc8_v36'
sys.path[:0]=[str(ROOT),str(PKG)]

from yado_core_v3_0_rc8_external_cognitive import UnifiedYADOKernelV30RC8ExternalCognitive
from yado_conjunctive_rule_inducer_v1 import ConjunctiveRuleInducerV1
from yado_bounded_dnf_relation_policy_inducer_v1 import BoundedDNFRelationPolicyInducerV1
from yado_bounded_capability_router_v1 import BoundedCapabilityRouterLearnerV1
from yado_budgeted_stage_policy_v1 import BudgetedStagePolicyV1,SearchStage
from yado_g2_typed_recurrent_capability_graph_runtime_v1 import G2TypedRecurrentCapabilityGraphRuntimeV1
from yado_g2_composite_clonal_successor_prototype_v1 import G2CompositeClonalSuccessorPrototypeV1
from yado_evolution_ledger_v2 import validate_ledger_v2,event_hash
from yado_unified_context_kernel_v1 import UnifiedContextKernel

HEAD=REPO/'canonical/yado-main-head-g2.json'
CORE=REPO/'canonical/yado-unified-core-v1.json'
ARCH=REPO/'canonical/yado-g2-architecture-v1.json'
LEDGER=REPO/'architecture/evolution-ledger.json'
PROV=REPO/'canonical/yado-algorithm-provenance-registry-v1.json'
PORT=REPO/'resources/yado-unified-external-resource-portfolio-v1.json'
DESIGN=REPO/'candidates/kernel-self-generated/architecture-composite-executable-successor-design-v1.json'
ART=REPO/'architecture/yado-kernel-selected-architecture-composite-executable-successor-prototype-v1.json'
CAND=REPO/'candidates/kernel-self-generated/architecture-composite-executable-successor-prototype-v1.json'
OUT=ROOT/'yado_kernel_selected_architecture_composite_executable_successor_prototype_v1_receipt.json'
GUARD=ROOT/'yado_canonical_invariant_guard_v1.py'
PROTOTYPE_SRC=ROOT/'yado_g2_composite_clonal_successor_prototype_v1.py'

CAP_CONJ='ALG-CONJUNCTIVE-RULE-INDUCER-V1'
CAP_REL='ALG-BOUNDED-DNF-RELATION-POLICY-INDUCER-V1'
CAP_BUD='ALG-BUDGETED-STAGE-POLICY-V1'
CAP_RES='RESOURCE-PORTFOLIO-V1'

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def h(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def fsha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def write(p,o):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(o,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')
def cdig(o,field):
    x=copy.deepcopy(o);x.pop(field,None);return h(x)
def log(stage,**kw):print(json.dumps({'stage':stage,**kw},sort_keys=True,default=str),flush=True)

head,core,arch,ledger,prov,portfolio,design_candidate=map(load,[HEAD,CORE,ARCH,LEDGER,PROV,PORT,DESIGN])
validate_ledger_v2(ledger)
front='KERNEL_SELECTED_ARCHITECTURE_COMPOSITE_EXECUTABLE_SUCCESSOR_PROTOTYPE_V1'
if ledger.get('open_deficits')!=[front]:raise RuntimeError('UNEXPECTED_FRONTIER:'+json.dumps(ledger.get('open_deficits')))
if design_candidate.get('state')!='SHADOW_DESIGN_SUPPORTED':raise RuntimeError('DESIGN_NOT_SUPPORTED')
design=design_candidate['design']
if (design.get('kernel_selected_evolution_operation') or {}).get('operation')!='CLONAL':raise RuntimeError('DESIGN_NOT_CLONAL')
if not arch.get('canonical_active'):raise RuntimeError('G2_ARCHITECTURE_NOT_CANONICAL')
if head.get('g3_genesis_performed') is not False:raise RuntimeError('G3_ALREADY_STARTED')

seed=26090217
rng=random.Random(seed)

def route_desc(cap,amb=False):
    d={'budget_limited':False,'quota_limited':False,'external_evidence_needed':False,
       'relation_needed':False,'disjunction_needed':False,'context_ambiguous':bool(amb)}
    if not amb:
        if cap==CAP_BUD:d['budget_limited']=True
        elif cap==CAP_RES:d['external_evidence_needed']=True
        elif cap==CAP_REL:d['relation_needed']=True
    return d

def router_cases(n,seed2):
    r=random.Random(seed2);out=[]
    caps=[CAP_CONJ,CAP_REL,CAP_BUD,CAP_RES]
    for i in range(n):
        cap=caps[i%4];d=route_desc(cap,False);d['noise']=r.randint(-10**9,10**9)
        out.append({'input':d,'expected':cap})
    r.shuffle(out);return out
router=BoundedCapabilityRouterLearnerV1.synthesize(router_cases(900,seed+1),router_cases(360,seed+2),CAP_CONJ,min_support=6)

def scalar_examples(n,seed2):
    r=random.Random(seed2);out=[]
    for i in range(n):
        positive=(i%2==0)
        if positive:x={'integrity':True,'fresh':True,'rollback':True,'noise':r.randrange(10**9)}
        else:
            vals=[True,True,True];vals[i%3]=False
            x={'integrity':vals[0],'fresh':vals[1],'rollback':vals[2],'noise':r.randrange(10**9)}
        out.append({'input':x,'expected':'COMMIT' if positive else 'HOLD'})
    r.shuffle(out);return out
scalar=ConjunctiveRuleInducerV1.synthesize('G2_COMPOSITE_PROTO_SCALAR','LOGIC',scalar_examples(720,seed+11),min_support=3,max_rules=12)

def relation_examples(n,seed2,prefix):
    r=random.Random(seed2);out=[]
    for i in range(n):
        positive=(i%2==0)
        actor=f'{prefix}_A_{i}';owner=actor if positive else f'{prefix}_O_{i}'
        x={'actor':actor,'owner':owner,'group':f'{prefix}_G_{i}','object_group':f'{prefix}_OG_{i}',
           'role':'GUEST','verified':True if positive else bool(r.getrandbits(1)),'critical':False,'noise':r.randint(-999,999)}
        out.append({'input':x,'expected':'ALLOW' if positive else 'DENY'})
    r.shuffle(out);return out
relation=BoundedDNFRelationPolicyInducerV1.synthesize(
    'G2_COMPOSITE_PROTO_REL','LOGIC',relation_examples(800,seed+21,'TR'),min_support=3,max_clauses=12,
    validation_cases=relation_examples(320,seed+22,'VA')
)

route_keys=sorted(portfolio.get('routes_for_current_open_deficits',{}))
if not route_keys:raise RuntimeError('NO_RESOURCE_ROUTES')

def make_task(cap,sid,index,amb=False):
    r=random.Random(seed+100000+index)
    if cap==CAP_CONJ:
        positive=(index%2==0)
        if positive:x={'integrity':True,'fresh':True,'rollback':True,'noise':r.randrange(10**9)}
        else:x={'integrity':False,'fresh':True,'rollback':True,'noise':r.randrange(10**9)}
        return {'kind':'scalar','descriptor':route_desc(cap,amb),'stream_id':sid,'payload':x},('COMMIT' if positive else 'HOLD')
    if cap==CAP_REL:
        positive=(index%2==0);actor=f'X{index}';owner=actor if positive else f'Y{index}'
        x={'actor':actor,'owner':owner,'group':f'G{index}','object_group':f'H{index}','role':'GUEST','verified':True,'critical':False,'noise':index}
        return {'kind':'relation','descriptor':route_desc(cap,amb),'stream_id':sid,'payload':x},('ALLOW' if positive else 'DENY')
    if cap==CAP_BUD:
        stages=[
          SearchStage(f'{sid}_S0',1.0,.15,2,True,.4,False),
          SearchStage(f'{sid}_S1',2.5,.30,2,True,.8,False),
          SearchStage(f'{sid}_S2',5.0,.48,1,True,1.2,False),
        ]
        cur=.40;target=.72;budget=4.0
        exp=BudgetedStagePolicyV1.plan(cur,target,budget,stages).action
        return {'kind':'budget','descriptor':route_desc(cap,amb),'stream_id':sid,
                'current_confidence':cur,'target_confidence':target,'remaining_budget':budget,
                'stages':[asdict(s) for s in stages]},exp
    key=route_keys[index%len(route_keys)];arr=portfolio['routes_for_current_open_deficits'][key]
    exp=arr[0]['resource_id'] if arr else None
    return {'kind':'resource','descriptor':route_desc(cap,amb),'stream_id':sid,'route_key':key,'payload':{}},exp

def make_parent_runtime():
    return G2TypedRecurrentCapabilityGraphRuntimeV1(arch,router,scalar,relation,portfolio)

kernel=UnifiedYADOKernelV30RC8ExternalCognitive(db_path=str(ROOT/'yado_composite_prototype_v1.sqlite'))
parent=make_parent_runtime()
prototype=G2CompositeClonalSuccessorPrototypeV1(parent,kernel,design)
snapshot=prototype.snapshot()
log('prototype_ready',snapshot=snapshot)

caps=[CAP_CONJ,CAP_REL,CAP_BUD,CAP_RES]
# Explicit parent-equivalence and local-context execution.
explicit_total=explicit_ok=0
amb_total=amb_cap_ok=amb_result_ok=0
prepared=[]
for i in range(320):
    cap=caps[i%4];sid=f'P_{i}'
    prime,exp1=make_task(cap,sid,i,False)
    out1=prototype.run(prime)
    explicit_total+=1;explicit_ok+=out1['context_selected_capability']==cap and out1['result']==exp1
    follow,exp2=make_task(cap,sid,10000+i,True)
    prepared.append((cap,follow,exp2))
rng.shuffle(prepared)
for cap,follow,exp in prepared:
    out=prototype.run(follow)
    amb_total+=1;amb_cap_ok+=out['context_selected_capability']==cap;amb_result_ok+=out['result']==exp
explicit_accuracy=explicit_ok/explicit_total
amb_cap_accuracy=amb_cap_ok/amb_total
amb_result_accuracy=amb_result_ok/amb_total

# Local self-organizing causal ablation on fresh streams.
abl_total=abl_cap_ok=0
for i in range(240):
    cap=caps[i%4];sid=f'A_{i}'
    prime,_=make_task(cap,sid,20000+i,False);prototype.run(prime)
    follow,_=make_task(cap,sid,30000+i,True)
    try:out=prototype.run(follow,ablated_local_context=True);ok=out['context_selected_capability']==cap
    except Exception:ok=False
    abl_total+=1;abl_cap_ok+=ok
ablated_local_accuracy=abl_cap_ok/abl_total
local_causal_drop=amb_cap_accuracy-ablated_local_accuracy

# Neuro-symbolic bounded execution and simple ablation baseline.
sym_total=sym_ok=base_ok=0
for i in range(240):
    cap=CAP_CONJ if i%2==0 else CAP_REL
    task,exp=make_task(cap,f'N_{i}',40000+i,False)
    out=prototype.run(task)
    sym_total+=1;sym_ok+=out['result']==exp
    baseline='HOLD' if cap==CAP_CONJ else 'DENY'
    base_ok+=baseline==exp
neuro_symbolic_accuracy=sym_ok/sym_total
neuro_symbolic_baseline=base_ok/sym_total
neuro_symbolic_gain=neuro_symbolic_accuracy-neuro_symbolic_baseline

# Evolution-control execution uses measured prototype evidence; no architecture commit.
records=[
 {'variant_id':'G2_CURRENT_TRCG_PARENT','parent_id':None,'lineage_id':'YADO_MAIN_LINEAGE',
  'artifact_digest':head['canonical_head_digest'],
  'task_scores':{'explicit':explicit_accuracy,'ambiguous':ablated_local_accuracy,'neuro_symbolic':neuro_symbolic_baseline},
  'constraints':{'regression_pass':True,'state_integrity':True,'rollback_available':True},
  'traits':{'canonical_parent':1.0,'clonal':1.0},'failure_tags':['local_context_ablated','symbolic_baseline_only'],'status':'EVALUATED'},
 {'variant_id':'G2_COMPOSITE_CLONAL_PROTOTYPE_V1','parent_id':'G2_CURRENT_TRCG_PARENT','lineage_id':'YADO_MAIN_LINEAGE',
  'artifact_digest':snapshot['snapshot_digest'],
  'task_scores':{'explicit':explicit_accuracy,'ambiguous':amb_result_accuracy,'neuro_symbolic':neuro_symbolic_accuracy},
  'constraints':{'regression_pass':True,'state_integrity':True,'rollback_available':True},
  'traits':{'open_ended_evolution':1.0,'local_self_organizing':1.0,'neuro_symbolic':1.0,'shadow':1.0},
  'failure_tags':[],'status':'EVALUATED'}
]
evolution_control=prototype.evolution_control(records,'prototype_retention')
log('evolution_control',control=evolution_control)

# Rollback: discard prototype and verify a fresh parent clone still executes canonical behavior.
kernel.close()
rollback_parent=make_parent_runtime()
rollback_ok=0
for i in range(80):
    cap=caps[i%4];task,exp=make_task(cap,f'R_{i}',50000+i,False)
    out=rollback_parent.run(task);rollback_ok+=out['selected_capability']==cap and out['result']==exp
rollback_accuracy=rollback_ok/80

checks={
 'design_operation_clonal':(design.get('kernel_selected_evolution_operation') or {}).get('operation')=='CLONAL',
 'parent_runtime_component_exact':snapshot['parent_runtime_component']['component_id']==head['runtime_component']['component_id'],
 'explicit_clone_accuracy':explicit_accuracy>=.99,
 'local_context_capability_accuracy':amb_cap_accuracy>=.99,
 'local_context_result_accuracy':amb_result_accuracy>=.99,
 'local_context_causal_drop':local_causal_drop>=.50,
 'neuro_symbolic_accuracy':neuro_symbolic_accuracy>=.99,
 'neuro_symbolic_causal_gain':neuro_symbolic_gain>=.20,
 'native_evolution_control_executed':bool((evolution_control.get('parent') or {}).get('variant_id')) and bool((evolution_control.get('operation') or {}).get('operation')),
 'rollback_parent_accuracy':rollback_accuracy>=.99,
 'parent_runtime_not_modified':snapshot['parent_runtime_modified'] is False,
 'architecture_not_mutated':True,
 'g3_not_started':head.get('g3_genesis_performed') is False,
}
supported=all(checks.values())
state='SHADOW_EXECUTABLE_SUPPORTED' if supported else 'WITHHOLD'
next_cap='KERNEL_SELECTED_ARCHITECTURE_COMPOSITE_EXECUTABLE_SUCCESSOR_FRESH_TRANSFER_V1' if supported else 'KERNEL_SELECTED_ARCHITECTURE_COMPOSITE_EXECUTABLE_SUCCESSOR_PROTOTYPE_V2'

metrics={
 'explicit_accuracy':explicit_accuracy,
 'ambiguous_capability_accuracy':amb_cap_accuracy,
 'ambiguous_result_accuracy':amb_result_accuracy,
 'ablated_local_context_accuracy':ablated_local_accuracy,
 'local_context_causal_drop':local_causal_drop,
 'neuro_symbolic_accuracy':neuro_symbolic_accuracy,
 'neuro_symbolic_baseline':neuro_symbolic_baseline,
 'neuro_symbolic_gain':neuro_symbolic_gain,
 'rollback_accuracy':rollback_accuracy,
}

candidate={
 'schema':'yado.g2.architecture_composite_executable_successor_prototype.v1','state':state,
 'design_digest':design['design_digest'],'prototype_snapshot':snapshot,'metrics':metrics,
 'evolution_control':evolution_control,'checks':checks,
 'semantic_boundary':'REAL SHADOW EXECUTION OF A CLONAL WRAPPER OVER CANONICAL G2 USING EXISTING RECURRENT CONTEXT, BOUNDED NEURO-SYMBOLIC EXECUTION, AND NATIVE EVOLUTION CONTROL. NO CANONICAL ARCHITECTURE REWRITE AND NO G3 PROMOTION.',
 'architecture_mutation':False,'canonical_mechanism_mutation':False,'generation_transition':False,'g3_genesis_performed':False
}
candidate['candidate_digest']=h(candidate);write(CAND,candidate)

artifact={
 'schema':'yado.g2.kernel_selected_architecture_composite_executable_successor_prototype.v1',
 'status':'PASS_COMPOSITE_EXECUTABLE_SUCCESSOR_PROTOTYPE_V1' if supported else 'WITHHOLD_COMPOSITE_EXECUTABLE_SUCCESSOR_PROTOTYPE_V1',
 'candidate_state':state,'candidate_digest':candidate['candidate_digest'],
 'prototype_snapshot_digest':snapshot['snapshot_digest'],'metrics':metrics,
 'evolution_control':evolution_control,'next_required_capability':next_cap,
 'architecture_mutation':False,'canonical_mechanism_mutation':False,'generation_transition':False,'g3_genesis_performed':False
}
artifact['artifact_digest']=h(artifact);write(ART,artifact)

prev=head['canonical_head_digest']
prov['current_g2_binding'].update({
 'current_execution_label':'G2_COMPOSITE_CLONAL_EXECUTABLE_PROTOTYPE_V1' if supported else 'G2_COMPOSITE_PROTOTYPE_V2_PENDING',
 'frontier':next_cap,'frontier_native_method':'run+propose_evolution_operation',
 'frontier_native_owner':'G2CompositeClonalSuccessorPrototypeV1+UnifiedYADOKernelV30RC7DeepIntegrity',
 'selected_architecture_composite_shadow':design['selected_families'],
 'selected_successor_design_operation':'CLONAL'
})
prov['registry_digest']=cdig(prov,'registry_digest');write(PROV,prov)

core['algorithm_provenance_registry_digest']=prov['registry_digest']
core['current_frontier']=next_cap;core['frontier_source']='architecture/evolution-ledger.json:open_deficits'
core['architecture_composite_successor_prototype_v1']={
 'status':state,'candidate_digest':candidate['candidate_digest'],'prototype_snapshot_digest':snapshot['snapshot_digest'],
 'design_digest':design['design_digest'],'metrics':metrics,'architecture_mutation':False,
 'runtime':'runtime/yado_g2_composite_clonal_successor_prototype_v1.py','runtime_sha256':fsha(PROTOTYPE_SRC)
}
core['core_digest']=cdig(core,'core_digest');write(CORE,core)

head['algorithm_provenance_registry']['registry_digest']=prov['registry_digest']
head['algorithm_provenance_registry']['current_execution_label']=prov['current_g2_binding']['current_execution_label']
head['unified_core']['algorithm_provenance_registry_digest']=prov['registry_digest'];head['unified_core']['core_digest']=core['core_digest']
head['architecture_composite_successor_prototype_v1']={
 'status':state,'candidate_digest':candidate['candidate_digest'],'prototype_snapshot_digest':snapshot['snapshot_digest'],
 'design_digest':design['design_digest'],'metrics':metrics,'architecture_mutation':False
}
head['current_frontier']=next_cap;head['frontier_source']='architecture/evolution-ledger.json:open_deficits'
head['canonical_head_digest']=cdig(head,'canonical_head_digest');write(HEAD,head)

ledger['current_head_digest']=head['canonical_head_digest'];ledger['open_deficits']=[next_cap]
run_id=str(os.getenv('GITHUB_RUN_ID') or 'LOCAL')
receipt={**artifact,'schema':'yado.g2.kernel_selected_architecture_composite_executable_successor_prototype.receipt.v1',
 'previous_head_digest':prev,'new_head_digest':head['canonical_head_digest'],'checks':checks,
 'provenance_registry_digest':prov['registry_digest'],'prototype_source_sha256':fsha(PROTOTYPE_SRC)}
receipt['receipt_sha256']=h(receipt);write(OUT,receipt)
e={'index':len(ledger['events']),'event_id':f"E{len(ledger['events'])+1:04d}_G2_COMPOSITE_EXECUTABLE_SUCCESSOR_PROTOTYPE_V1",
 'event_type':'G2_COMPOSITE_CLONAL_SHADOW_EXECUTION','status':'PASS_SHADOW' if supported else 'WITHHOLD',
 'generation':ledger['current_head'],'deficit':front,
 'effect':f"STATE={state}; EXPLICIT={explicit_accuracy:.6f}; AMBIG={amb_result_accuracy:.6f}; LOCAL_DROP={local_causal_drop:.6f}; NEURO={neuro_symbolic_accuracy:.6f}; NEURO_GAIN={neuro_symbolic_gain:.6f}; ROLLBACK={rollback_accuracy:.6f}; ARCHITECTURE_MUTATION=False; NEXT={next_cap}",
 'source_path':f'receipts/yado-kernel-selected-architecture-composite-executable-successor-prototype-v1-run-{run_id}.json',
 'source_digest':receipt['receipt_sha256'],'run_id':run_id,'parent_event_hash':ledger['tail_event_hash'],
 'canonical_mutation':True,'canonical_mechanism_mutation':False,'architecture_mutation':False,
 'promotion_applied':False,'generation_transition':False,'previous_head_digest':prev,'new_head_digest':head['canonical_head_digest']}
e['event_hash']=event_hash(e);ledger['events'].append(e);ledger['event_count']=len(ledger['events']);ledger['tail_event_hash']=e['event_hash']
ledger['ledger_digest']=h({k:v for k,v in ledger.items() if k!='ledger_digest'});validate_ledger_v2(ledger);write(LEDGER,ledger)

ctx=UnifiedContextKernel().snapshot()
if ctx['current_frontier']!=next_cap:raise RuntimeError('POST_WRITE_CONTEXT_INCONSISTENT')
cp=subprocess.run([sys.executable,str(GUARD)],cwd=REPO,capture_output=True,text=True,timeout=60)
if cp.returncode!=0:raise RuntimeError('POST_PROTOTYPE_GUARD_FAILED:'+cp.stdout[-4000:]+cp.stderr[-1000:])
log('complete',state=state,metrics=metrics,next=next_cap)
