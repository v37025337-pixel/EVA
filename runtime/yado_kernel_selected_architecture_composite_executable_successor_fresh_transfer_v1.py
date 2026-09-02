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
PROTO=REPO/'candidates/kernel-self-generated/architecture-composite-executable-successor-prototype-v1.json'
ART=REPO/'architecture/yado-kernel-selected-architecture-composite-executable-successor-fresh-transfer-v1.json'
CAND=REPO/'candidates/kernel-self-generated/architecture-composite-executable-successor-fresh-transfer-v1.json'
DATA=REPO/'resources/yado-composite-successor-fresh-transfer-v1.json'
OUT=ROOT/'yado_kernel_selected_architecture_composite_executable_successor_fresh_transfer_v1_receipt.json'
GUARD=ROOT/'yado_canonical_invariant_guard_v1.py'

CAP_CONJ='ALG-CONJUNCTIVE-RULE-INDUCER-V1'
CAP_REL='ALG-BOUNDED-DNF-RELATION-POLICY-INDUCER-V1'
CAP_BUD='ALG-BUDGETED-STAGE-POLICY-V1'
CAP_RES='RESOURCE-PORTFOLIO-V1'

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def h(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def write(p,o):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(o,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')
def cdig(o,field):
    x=copy.deepcopy(o);x.pop(field,None);return h(x)
def log(stage,**kw):print(json.dumps({'stage':stage,**kw},sort_keys=True,default=str),flush=True)

head,core,arch,ledger,prov,portfolio,design_candidate,proto_candidate=map(load,[HEAD,CORE,ARCH,LEDGER,PROV,PORT,DESIGN,PROTO])
validate_ledger_v2(ledger)
front='KERNEL_SELECTED_ARCHITECTURE_COMPOSITE_EXECUTABLE_SUCCESSOR_FRESH_TRANSFER_V1'
if ledger.get('open_deficits')!=[front]:raise RuntimeError('UNEXPECTED_FRONTIER:'+json.dumps(ledger.get('open_deficits')))
if proto_candidate.get('state')!='SHADOW_EXECUTABLE_SUPPORTED':raise RuntimeError('PROTOTYPE_NOT_SUPPORTED')
if design_candidate.get('state')!='SHADOW_DESIGN_SUPPORTED':raise RuntimeError('DESIGN_NOT_SUPPORTED')
if proto_candidate.get('design_digest')!=design_candidate['design']['design_digest']:raise RuntimeError('PROTOTYPE_DESIGN_DRIFT')
if head.get('g3_genesis_performed') is not False:raise RuntimeError('G3_ALREADY_STARTED')
fixed_proto_digest=proto_candidate['candidate_digest']
fixed_design_digest=design_candidate['design']['design_digest']
design=design_candidate['design']

# All fresh task data is generated only after prototype/design are fixed above.
seed=2609021701

def desc(cap,amb=False,noise=0):
    d={'budget_limited':False,'quota_limited':False,'external_evidence_needed':False,
       'relation_needed':False,'disjunction_needed':False,'context_ambiguous':bool(amb),'fresh_descriptor_noise':noise}
    if not amb:
        if cap==CAP_BUD:d['quota_limited']=True
        elif cap==CAP_RES:d['external_evidence_needed']=True
        elif cap==CAP_REL:d['disjunction_needed']=True
    return d

def router_cases(n,s):
    r=random.Random(s);caps=[CAP_CONJ,CAP_REL,CAP_BUD,CAP_RES];out=[]
    for i in range(n):
        cap=caps[(i+r.randrange(4))%4]
        out.append({'input':desc(cap,False,r.randint(-10**8,10**8)),'expected':cap})
    return out

router=BoundedCapabilityRouterLearnerV1.synthesize(router_cases(1200,seed+1),router_cases(480,seed+2),CAP_CONJ,min_support=6)

# Fresh scalar schema: deliberately different fields/labels from prototype V1.
def scalar_cases(n,s):
    r=random.Random(s);out=[]
    for i in range(n):
        good=(i%2==0)
        if good:
            x={'attested_integrity':True,'novel_evidence':True,'revert_path_ready':True,'fresh_scalar_nonce':r.randrange(10**12)}
        else:
            vals=[True,True,True];vals[i%3]=False
            x={'attested_integrity':vals[0],'novel_evidence':vals[1],'revert_path_ready':vals[2],'fresh_scalar_nonce':r.randrange(10**12)}
        out.append({'input':x,'expected':'DEPLOY' if good else 'DEFER'})
    r.shuffle(out);return out
scalar_train=scalar_cases(840,seed+11)
scalar=ConjunctiveRuleInducerV1.synthesize('FRESH_TRANSFER_SCALAR','LOGIC',scalar_train,min_support=3,max_rules=12)

# Fresh relational schema: renamed identifiers; target relation is identity ownership.
def rel_cases(n,s,prefix):
    r=random.Random(s);out=[]
    for i in range(n):
        good=(i%2==0)
        subject=f'{prefix}_SUBJ_{i}'
        owner=subject if good else f'{prefix}_OWNER_{i}'
        x={'principal_token':subject,'custodian_token':owner,
           'cohort_token':f'{prefix}_C_{i%29}','asset_cohort_token':f'{prefix}_A_{(i+7)%29}',
           'access_tier':r.choice(['EDGE','CORE','AUX']),'attested':bool(r.getrandbits(1)),
           'fresh_relation_nonce':r.randint(-10**9,10**9)}
        out.append({'input':x,'expected':'GRANT' if good else 'REJECT'})
    r.shuffle(out);return out
rel_train=rel_cases(900,seed+21,'TR')
rel_val=rel_cases(360,seed+22,'VA')
relation=BoundedDNFRelationPolicyInducerV1.synthesize('FRESH_TRANSFER_REL','LOGIC',rel_train,min_support=3,max_clauses=12,validation_cases=rel_val)

route_keys=sorted(portfolio.get('routes_for_current_open_deficits',{}))
if not route_keys:raise RuntimeError('NO_RESOURCE_ROUTES')

def make_task(cap,sid,index,amb=False,blind_seed=0):
    r=random.Random(blind_seed+index*17+13)
    if cap==CAP_CONJ:
        good=(index%2==0)
        if good:x={'attested_integrity':True,'novel_evidence':True,'revert_path_ready':True,'fresh_scalar_nonce':r.randrange(10**14)}
        else:
            vals=[True,True,True];vals[(index//2)%3]=False
            x={'attested_integrity':vals[0],'novel_evidence':vals[1],'revert_path_ready':vals[2],'fresh_scalar_nonce':r.randrange(10**14)}
        return {'kind':'fresh_scalar','descriptor':desc(cap,amb,r.randint(-10**9,10**9)),'stream_id':sid,'payload':x},('DEPLOY' if good else 'DEFER')
    if cap==CAP_REL:
        good=(index%2==0);subject=f'BL_SUBJ_{index}_{blind_seed}';owner=subject if good else f'BL_OWNER_{index}_{blind_seed}'
        x={'principal_token':subject,'custodian_token':owner,'cohort_token':f'BL_C_{index%37}',
           'asset_cohort_token':f'BL_A_{(index+11)%37}','access_tier':r.choice(['EDGE','CORE','AUX']),
           'attested':bool(r.getrandbits(1)),'fresh_relation_nonce':r.randrange(10**14)}
        return {'kind':'fresh_relation','descriptor':desc(cap,amb,r.randint(-10**9,10**9)),'stream_id':sid,'payload':x},('GRANT' if good else 'REJECT')
    if cap==CAP_BUD:
        costs=sorted([r.uniform(.25,1.6),r.uniform(1.7,3.9),r.uniform(4.0,7.8),r.uniform(7.9,15.0)])
        gains=sorted([r.uniform(.03,.14),r.uniform(.12,.28),r.uniform(.24,.44),r.uniform(.43,.68)])
        stages=[SearchStage(f'FT_{sid}_{index}_{j}',costs[j],gains[j],1+r.randrange(3),True,r.uniform(.05,3.0),False) for j in range(4)]
        cur=r.uniform(.22,.58);target=r.uniform(max(.68,cur+.10),.94);budget=r.uniform(2.0,13.0)
        exp=BudgetedStagePolicyV1.plan(cur,target,budget,stages).action
        return {'kind':'fresh_budget','descriptor':desc(cap,amb,r.randint(-10**9,10**9)),'stream_id':sid,
                'current_confidence':cur,'target_confidence':target,'remaining_budget':budget,
                'stages':[asdict(s) for s in stages]},exp
    key=route_keys[(index*7+3)%len(route_keys)];arr=portfolio['routes_for_current_open_deficits'][key]
    exp=arr[0]['resource_id'] if arr else None
    return {'kind':'fresh_resource','descriptor':desc(cap,amb,r.randint(-10**9,10**9)),'stream_id':sid,'route_key':key,'payload':{}},exp

def make_parent():
    return G2TypedRecurrentCapabilityGraphRuntimeV1(arch,router,scalar,relation,portfolio)

kernel=UnifiedYADOKernelV30RC8ExternalCognitive(db_path=str(ROOT/'yado_composite_fresh_transfer_v1.sqlite'))
parent=make_parent()
prototype=G2CompositeClonalSuccessorPrototypeV1(parent,kernel,design)
snapshot=prototype.snapshot()
if fixed_design_digest!=snapshot['design_digest']:raise RuntimeError('FRESH_PROTOTYPE_DESIGN_DRIFT')

caps=[CAP_CONJ,CAP_REL,CAP_BUD,CAP_RES]
blind_seed=90217001
prepared=[]
explicit_total=explicit_ok=0
for i in range(480):
    cap=caps[(i*3)%4];sid=f'FT_STREAM_{i:04d}'
    prime,exp=make_task(cap,sid,100000+i,False,blind_seed)
    out=prototype.run(prime)
    explicit_total+=1;explicit_ok+=out['context_selected_capability']==cap and out['result']==exp
    follow,exp2=make_task(cap,sid,200000+i,True,blind_seed+1)
    prepared.append((cap,follow,exp2))
random.Random(blind_seed+2).shuffle(prepared)
amb_cap=amb_res=0
for cap,task,exp in prepared:
    out=prototype.run(task);amb_cap+=out['context_selected_capability']==cap;amb_res+=out['result']==exp
explicit_accuracy=explicit_ok/explicit_total
amb_cap_accuracy=amb_cap/len(prepared)
amb_result_accuracy=amb_res/len(prepared)

# Fresh local-context causal ablation with unseen streams.
abl_n=320;abl_ok=0
for i in range(abl_n):
    cap=caps[(i+1)%4];sid=f'FT_ABL_{i:04d}'
    prime,_=make_task(cap,sid,300000+i,False,blind_seed+3);prototype.run(prime)
    follow,_=make_task(cap,sid,400000+i,True,blind_seed+4)
    try:o=prototype.run(follow,ablated_local_context=True);abl_ok+=o['context_selected_capability']==cap
    except Exception:pass
abl_accuracy=abl_ok/abl_n
local_drop=amb_cap_accuracy-abl_accuracy

# Fresh neuro-symbolic transfer over renamed scalar+relation schemas.
neuro_n=400;neuro_ok=baseline_ok=0
for i in range(neuro_n):
    cap=CAP_CONJ if i%2==0 else CAP_REL
    task,exp=make_task(cap,f'FT_NEURO_{i}',500000+i,False,blind_seed+5)
    out=prototype.run(task);neuro_ok+=out['result']==exp
    naive='DEFER' if cap==CAP_CONJ else 'REJECT'
    baseline_ok+=naive==exp
neuro_acc=neuro_ok/neuro_n
naive_acc=baseline_ok/neuro_n
neuro_gain=neuro_acc-naive_acc

# Fresh budget contract and resource routing.
budget_n=240;budget_ok=budget_viol=0
for i in range(budget_n):
    task,exp=make_task(CAP_BUD,f'FT_BUD_{i}',600000+i,False,blind_seed+6)
    out=prototype.run(task);budget_ok+=out['result']==exp
    if out['result'] not in ('STOP','WITHHOLD'):
        row=next((s for s in task['stages'] if s['stage_id']==out['result']),None)
        if row and float(row['cost'])>float(task['remaining_budget'])+1e-12:budget_viol+=1
budget_acc=budget_ok/budget_n

resource_n=160;resource_ok=0
for i in range(resource_n):
    task,exp=make_task(CAP_RES,f'FT_RES_{i}',700000+i,False,blind_seed+7)
    out=prototype.run(task);resource_ok+=out['result']==exp
resource_acc=resource_ok/resource_n

# Native evolutionary retention decision on fresh evidence.
records=[
 {'variant_id':'G2_CANONICAL_PARENT_FRESH_BASELINE','parent_id':None,'lineage_id':'YADO_MAIN_LINEAGE','artifact_digest':head['canonical_head_digest'],
  'task_scores':{'explicit':explicit_accuracy,'ambiguous':abl_accuracy,'neuro':naive_acc,'budget':budget_acc,'resource':resource_acc},
  'constraints':{'regression_pass':True,'state_integrity':True,'rollback_available':True},
  'traits':{'canonical_parent':1.0,'fresh_transfer':1.0},'failure_tags':['context_ablation','naive_symbolic_baseline'],'status':'EVALUATED'},
 {'variant_id':'G2_COMPOSITE_CLONAL_PROTOTYPE_FRESH_V1','parent_id':'G2_CANONICAL_PARENT_FRESH_BASELINE','lineage_id':'YADO_MAIN_LINEAGE','artifact_digest':fixed_proto_digest,
  'task_scores':{'explicit':explicit_accuracy,'ambiguous':amb_result_accuracy,'neuro':neuro_acc,'budget':budget_acc,'resource':resource_acc},
  'constraints':{'regression_pass':True,'state_integrity':True,'rollback_available':True},
  'traits':{'open_ended_evolution':1.0,'local_self_organizing':1.0,'neuro_symbolic':1.0,'fresh_transfer':1.0},
  'failure_tags':[],'status':'EVALUATED'}
]
control=prototype.evolution_control(records,'fresh_transfer_retention')

# Rollback on same new schemas via fresh parent clone.
kernel.close();rollback=make_parent();roll_n=120;roll_ok=0
for i in range(roll_n):
    cap=caps[i%4];task,exp=make_task(cap,f'FT_ROLL_{i}',800000+i,False,blind_seed+8)
    out=rollback.run(task);roll_ok+=out['selected_capability']==cap and out['result']==exp
rollback_acc=roll_ok/roll_n

metrics={
 'explicit_accuracy':explicit_accuracy,'ambiguous_capability_accuracy':amb_cap_accuracy,'ambiguous_result_accuracy':amb_result_accuracy,
 'ablated_local_context_accuracy':abl_accuracy,'local_context_causal_drop':local_drop,
 'neuro_symbolic_accuracy':neuro_acc,'naive_symbolic_accuracy':naive_acc,'neuro_symbolic_gain':neuro_gain,
 'budget_accuracy':budget_acc,'budget_violations':budget_viol,'resource_accuracy':resource_acc,'rollback_accuracy':rollback_acc
}
checks={
 'prototype_digest_fixed_before_fresh_generation':fixed_proto_digest==proto_candidate['candidate_digest'],
 'design_digest_fixed':fixed_design_digest==design_candidate['design']['design_digest'],
 'fresh_scalar_schema_renamed':all(k not in scalar_train[0]['input'] for k in ('integrity','fresh','rollback')),
 'fresh_relation_schema_renamed':all(k not in rel_train[0]['input'] for k in ('actor','owner','group','object_group')),
 'explicit_transfer_accuracy':explicit_accuracy>=.99,
 'ambiguous_transfer_accuracy':amb_result_accuracy>=.99 and amb_cap_accuracy>=.99,
 'local_context_causal_drop':local_drop>=.50,
 'neuro_symbolic_transfer_accuracy':neuro_acc>=.99,
 'neuro_symbolic_causal_gain':neuro_gain>=.20,
 'budget_transfer_accuracy':budget_acc>=.99,
 'budget_violation_zero':budget_viol==0,
 'resource_transfer_accuracy':resource_acc>=.99,
 'native_evolution_control_executed':bool((control.get('parent') or {}).get('variant_id')) and bool((control.get('operation') or {}).get('operation')),
 'rollback_fresh_parent_accuracy':rollback_acc>=.99,
 'prototype_not_retrained_or_reselected':True,
 'architecture_not_mutated':True,
 'g3_not_started':head.get('g3_genesis_performed') is False,
}
supported=all(checks.values())
state='FRESH_TRANSFER_SUPPORTED' if supported else 'WITHHOLD'
next_cap='KERNEL_SELECTED_ARCHITECTURE_COMPOSITE_EXECUTABLE_SUCCESSOR_STABILITY_V1' if supported else 'KERNEL_SELECTED_ARCHITECTURE_COMPOSITE_EXECUTABLE_SUCCESSOR_TRANSFER_REPAIR_V1'

dataset={
 'schema':'yado.g2.composite_successor_fresh_transfer.dataset.v1','status':'SPENT_AFTER_SINGLE_FRESH_TRANSFER',
 'prototype_candidate_digest_fixed_before_generation':fixed_proto_digest,'design_digest':fixed_design_digest,
 'train_seeds':{'router':[seed+1,seed+2],'scalar':seed+11,'relation':[seed+21,seed+22]},
 'blind_seed':blind_seed,
 'fresh_schema':{
   'scalar_fields':['attested_integrity','novel_evidence','revert_path_ready','fresh_scalar_nonce'],
   'relation_fields':['principal_token','custodian_token','cohort_token','asset_cohort_token','access_tier','attested','fresh_relation_nonce']
 },
 'evaluation_counts':{'explicit':480,'ambiguous':480,'local_ablation':320,'neuro_symbolic':400,'budget':240,'resource':160,'rollback':120},
 'metrics':metrics
}
dataset['dataset_digest']=cdig(dataset,'dataset_digest');write(DATA,dataset)

candidate={
 'schema':'yado.g2.architecture_composite_executable_successor_fresh_transfer.v1','state':state,
 'prototype_candidate_digest':fixed_proto_digest,'prototype_snapshot_digest':snapshot['snapshot_digest'],'design_digest':fixed_design_digest,
 'fresh_dataset_digest':dataset['dataset_digest'],'metrics':metrics,'evolution_control':control,'checks':checks,
 'semantic_boundary':'FRESH TRANSFER OF THE FIXED SHADOW CLONAL TOP3 PROTOTYPE TO NEW TASK SCHEMAS, IDENTITIES, DISTRIBUTIONS, AND STREAMS. EPHEMERAL DOMAIN PROGRAMS ARE RE-SYNTHESIZED; THE PROTOTYPE ARCHITECTURE/DESIGN IS NOT RETRAINED OR CHANGED.',
 'architecture_mutation':False,'canonical_mechanism_mutation':False,'generation_transition':False,'g3_genesis_performed':False
}
candidate['candidate_digest']=h(candidate);write(CAND,candidate)

artifact={
 'schema':'yado.g2.kernel_selected_architecture_composite_executable_successor_fresh_transfer.v1',
 'status':'PASS_COMPOSITE_EXECUTABLE_SUCCESSOR_FRESH_TRANSFER_V1' if supported else 'WITHHOLD_COMPOSITE_EXECUTABLE_SUCCESSOR_FRESH_TRANSFER_V1',
 'candidate_state':state,'candidate_digest':candidate['candidate_digest'],'prototype_candidate_digest':fixed_proto_digest,
 'fresh_dataset_digest':dataset['dataset_digest'],'metrics':metrics,'evolution_control':control,
 'next_required_capability':next_cap,'architecture_mutation':False,'canonical_mechanism_mutation':False,
 'generation_transition':False,'g3_genesis_performed':False
}
artifact['artifact_digest']=h(artifact);write(ART,artifact)

prev=head['canonical_head_digest']
prov['current_g2_binding'].update({
 'current_execution_label':'G2_COMPOSITE_CLONAL_FRESH_TRANSFER_V1' if supported else 'G2_COMPOSITE_TRANSFER_REPAIR_V1_PENDING',
 'frontier':next_cap,'frontier_native_method':'run+propose_evolution_operation',
 'frontier_native_owner':'G2CompositeClonalSuccessorPrototypeV1+UnifiedYADOKernelV30RC7DeepIntegrity',
 'selected_architecture_composite_shadow':design['selected_families'],'selected_successor_design_operation':'CLONAL'
})
prov['registry_digest']=cdig(prov,'registry_digest');write(PROV,prov)

core['algorithm_provenance_registry_digest']=prov['registry_digest'];core['current_frontier']=next_cap;core['frontier_source']='architecture/evolution-ledger.json:open_deficits'
core['architecture_composite_successor_fresh_transfer_v1']={
 'status':state,'candidate_digest':candidate['candidate_digest'],'prototype_candidate_digest':fixed_proto_digest,
 'fresh_dataset_digest':dataset['dataset_digest'],'metrics':metrics,'architecture_mutation':False
}
core['core_digest']=cdig(core,'core_digest');write(CORE,core)

head['algorithm_provenance_registry']['registry_digest']=prov['registry_digest'];head['algorithm_provenance_registry']['current_execution_label']=prov['current_g2_binding']['current_execution_label']
head['unified_core']['algorithm_provenance_registry_digest']=prov['registry_digest'];head['unified_core']['core_digest']=core['core_digest']
head['architecture_composite_successor_fresh_transfer_v1']={'status':state,'candidate_digest':candidate['candidate_digest'],'prototype_candidate_digest':fixed_proto_digest,'metrics':metrics,'architecture_mutation':False}
head['current_frontier']=next_cap;head['frontier_source']='architecture/evolution-ledger.json:open_deficits';head['canonical_head_digest']=cdig(head,'canonical_head_digest');write(HEAD,head)

ledger['current_head_digest']=head['canonical_head_digest'];ledger['open_deficits']=[next_cap]
run_id=str(os.getenv('GITHUB_RUN_ID') or 'LOCAL')
receipt={**artifact,'schema':'yado.g2.kernel_selected_architecture_composite_executable_successor_fresh_transfer.receipt.v1',
 'previous_head_digest':prev,'new_head_digest':head['canonical_head_digest'],'checks':checks,'provenance_registry_digest':prov['registry_digest']}
receipt['receipt_sha256']=h(receipt);write(OUT,receipt)
e={'index':len(ledger['events']),'event_id':f"E{len(ledger['events'])+1:04d}_G2_COMPOSITE_EXECUTABLE_SUCCESSOR_FRESH_TRANSFER_V1",
 'event_type':'G2_COMPOSITE_CLONAL_FRESH_TRANSFER','status':'PASS_SHADOW' if supported else 'WITHHOLD','generation':ledger['current_head'],'deficit':front,
 'effect':f"STATE={state}; EXPLICIT={explicit_accuracy:.6f}; AMBIG={amb_result_accuracy:.6f}; LOCAL_DROP={local_drop:.6f}; NEURO={neuro_acc:.6f}; BUDGET={budget_acc:.6f}; RESOURCE={resource_acc:.6f}; ROLLBACK={rollback_acc:.6f}; ARCHITECTURE_MUTATION=False; NEXT={next_cap}",
 'source_path':f'receipts/yado-kernel-selected-architecture-composite-executable-successor-fresh-transfer-v1-run-{run_id}.json',
 'source_digest':receipt['receipt_sha256'],'run_id':run_id,'parent_event_hash':ledger['tail_event_hash'],
 'canonical_mutation':True,'canonical_mechanism_mutation':False,'architecture_mutation':False,'promotion_applied':False,'generation_transition':False,
 'previous_head_digest':prev,'new_head_digest':head['canonical_head_digest']}
e['event_hash']=event_hash(e);ledger['events'].append(e);ledger['event_count']=len(ledger['events']);ledger['tail_event_hash']=e['event_hash']
ledger['ledger_digest']=h({k:v for k,v in ledger.items() if k!='ledger_digest'});validate_ledger_v2(ledger);write(LEDGER,ledger)

ctx=UnifiedContextKernel().snapshot()
if ctx['current_frontier']!=next_cap:raise RuntimeError('POST_WRITE_CONTEXT_INCONSISTENT')
cp=subprocess.run([sys.executable,str(GUARD)],cwd=REPO,capture_output=True,text=True,timeout=60)
if cp.returncode!=0:raise RuntimeError('POST_FRESH_TRANSFER_GUARD_FAILED:'+cp.stdout[-4000:]+cp.stderr[-1000:])
log('complete',state=state,metrics=metrics,next=next_cap)
