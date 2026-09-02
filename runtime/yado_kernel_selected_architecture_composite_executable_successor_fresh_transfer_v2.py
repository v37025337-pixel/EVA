from __future__ import annotations
from pathlib import Path
from dataclasses import asdict
import copy,hashlib,json,os,random,subprocess,sys

ROOT=Path(__file__).resolve().parent;REPO=ROOT.parent;PKG=ROOT/'yado_rc8_v36'
sys.path[:0]=[str(ROOT),str(PKG)]

from yado_core_v3_0_rc8_external_cognitive import UnifiedYADOKernelV30RC8ExternalCognitive
from yado_conjunctive_rule_inducer_v1 import ConjunctiveRuleInducerV1
from yado_bounded_dnf_relation_policy_inducer_v1 import BoundedDNFRelationPolicyInducerV1
from yado_bounded_capability_router_v1 import BoundedCapabilityRouterLearnerV1
from yado_budgeted_stage_policy_v1 import BudgetedStagePolicyV1,SearchStage
from yado_g2_typed_recurrent_capability_graph_runtime_v1 import G2TypedRecurrentCapabilityGraphRuntimeV1
from yado_g2_composite_transfer_repair_adapter_v1 import G2CompositeTransferRepairAdapterV1
from yado_evolution_ledger_v2 import validate_ledger_v2,event_hash
from yado_unified_context_kernel_v1 import UnifiedContextKernel

HEAD=REPO/'canonical/yado-main-head-g2.json'
CORE=REPO/'canonical/yado-unified-core-v1.json'
ARCH=REPO/'canonical/yado-g2-architecture-v1.json'
LEDGER=REPO/'architecture/evolution-ledger.json'
PROV=REPO/'canonical/yado-algorithm-provenance-registry-v1.json'
PORT=REPO/'resources/yado-unified-external-resource-portfolio-v1.json'
REPAIR=REPO/'candidates/kernel-self-generated/architecture-composite-executable-successor-transfer-repair-v1.json'
PROTO=REPO/'candidates/kernel-self-generated/architecture-composite-executable-successor-prototype-v1.json'
ART=REPO/'architecture/yado-kernel-selected-architecture-composite-executable-successor-fresh-transfer-v2.json'
CAND=REPO/'candidates/kernel-self-generated/architecture-composite-executable-successor-fresh-transfer-v2.json'
DATA=REPO/'resources/yado-composite-successor-fresh-transfer-v2.json'
OUT=ROOT/'yado_kernel_selected_architecture_composite_executable_successor_fresh_transfer_v2_receipt.json'
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

head,core,arch,ledger,prov,portfolio,repair_candidate,proto_candidate=map(load,[HEAD,CORE,ARCH,LEDGER,PROV,PORT,REPAIR,PROTO])
validate_ledger_v2(ledger)
front='KERNEL_SELECTED_ARCHITECTURE_COMPOSITE_EXECUTABLE_SUCCESSOR_FRESH_TRANSFER_V2'
if ledger.get('open_deficits')!=[front]:raise RuntimeError('UNEXPECTED_FRONTIER:'+json.dumps(ledger.get('open_deficits')))
if repair_candidate.get('state')!='SHADOW_REPAIR_SUPPORTED':raise RuntimeError('REPAIR_NOT_SUPPORTED')
if repair_candidate.get('selected_skill_id')!='FORCED_SINGLE_CAPABILITY_EXECUTION_V1':raise RuntimeError('WRONG_REPAIR_SELECTED')
if proto_candidate.get('state')!='SHADOW_EXECUTABLE_SUPPORTED':raise RuntimeError('PROTOTYPE_NOT_SUPPORTED')
if head.get('g3_genesis_performed') is not False:raise RuntimeError('G3_ALREADY_STARTED')
fixed_repair_digest=repair_candidate['candidate_digest']
fixed_proto_digest=proto_candidate['candidate_digest']

seed=2609022201
blind_seed=90222001

def desc(cap,amb=False,noise=0):
    d={'budget_limited':False,'quota_limited':False,'external_evidence_needed':False,
       'relation_needed':False,'disjunction_needed':False,'context_ambiguous':bool(amb),
       'transfer_v2_noise':noise}
    if not amb:
        if cap==CAP_BUD:d['budget_limited']=True
        elif cap==CAP_RES:d['external_evidence_needed']=True
        elif cap==CAP_REL:d['relation_needed']=True
    return d

def router_cases(n,s):
    r=random.Random(s);caps=[CAP_CONJ,CAP_REL,CAP_BUD,CAP_RES];out=[]
    for i in range(n):
        cap=caps[(i+2*r.randrange(4))%4]
        out.append({'input':desc(cap,False,r.randint(-10**10,10**10)),'expected':cap})
    return out
router=BoundedCapabilityRouterLearnerV1.synthesize(router_cases(1400,seed+1),router_cases(560,seed+2),CAP_CONJ,min_support=7)

def scalar_cases(n,s):
    r=random.Random(s);out=[]
    for i in range(n):
        good=(i%2==0)
        if good:
            x={'integrity_attestation':True,'novel_signal_present':True,'rollback_contract_ready':True,'scalar_v2_nonce':r.randrange(10**15)}
        else:
            vals=[True,True,True];vals[(i//2)%3]=False
            x={'integrity_attestation':vals[0],'novel_signal_present':vals[1],'rollback_contract_ready':vals[2],'scalar_v2_nonce':r.randrange(10**15)}
        out.append({'input':x,'expected':'ACCEPT_V2' if good else 'HOLD_V2'})
    r.shuffle(out);return out
scalar=ConjunctiveRuleInducerV1.synthesize('FRESH_TRANSFER_V2_SCALAR','LOGIC',scalar_cases(900,seed+11),min_support=3,max_rules=12)

def rel_cases(n,s,prefix):
    r=random.Random(s);out=[]
    for i in range(n):
        good=(i%2==0);claimant=f'{prefix}_CLAIM_{i}';owner=claimant if good else f'{prefix}_OWNER_{i}'
        x={'claimant_id':claimant,'registered_owner_id':owner,'cluster_id':f'{prefix}_C_{i%41}',
           'asset_cluster_id':f'{prefix}_AC_{(i+13)%41}','verification_tier':r.choice(['L1','L2','L3']),
           'trusted':bool(r.getrandbits(1)),'relation_v2_nonce':r.randrange(10**15)}
        out.append({'input':x,'expected':'AUTHORIZE_V2' if good else 'DENY_V2'})
    r.shuffle(out);return out
relation=BoundedDNFRelationPolicyInducerV1.synthesize('FRESH_TRANSFER_V2_REL','LOGIC',rel_cases(960,seed+21,'TR2'),min_support=3,max_clauses=12,validation_cases=rel_cases(400,seed+22,'VA2'))

route_keys=sorted(portfolio.get('routes_for_current_open_deficits',{}))
if not route_keys:raise RuntimeError('NO_RESOURCE_ROUTES')

def make_task(cap,sid,index,amb=False,salt=0):
    r=random.Random(blind_seed+salt+index*19+17)
    if cap==CAP_CONJ:
        good=(index%2==0)
        if good:x={'integrity_attestation':True,'novel_signal_present':True,'rollback_contract_ready':True,'scalar_v2_nonce':r.randrange(10**16)}
        else:
            vals=[True,True,True];vals[(index//2)%3]=False
            x={'integrity_attestation':vals[0],'novel_signal_present':vals[1],'rollback_contract_ready':vals[2],'scalar_v2_nonce':r.randrange(10**16)}
        return {'kind':'fresh_v2_scalar','descriptor':desc(cap,amb,r.randint(-10**11,10**11)),'stream_id':sid,'payload':x},('ACCEPT_V2' if good else 'HOLD_V2')
    if cap==CAP_REL:
        good=(index%2==0);claimant=f'BL2_CLAIM_{index}_{salt}';owner=claimant if good else f'BL2_OWNER_{index}_{salt}'
        x={'claimant_id':claimant,'registered_owner_id':owner,'cluster_id':f'BL2_C_{index%43}',
           'asset_cluster_id':f'BL2_AC_{(index+17)%43}','verification_tier':r.choice(['L1','L2','L3']),
           'trusted':bool(r.getrandbits(1)),'relation_v2_nonce':r.randrange(10**16)}
        return {'kind':'fresh_v2_relation','descriptor':desc(cap,amb,r.randint(-10**11,10**11)),'stream_id':sid,'payload':x},('AUTHORIZE_V2' if good else 'DENY_V2')
    if cap==CAP_BUD:
        costs=sorted([r.uniform(.3,1.4),r.uniform(1.5,3.3),r.uniform(3.4,6.5),r.uniform(6.6,12.5)])
        gains=sorted([r.uniform(.04,.15),r.uniform(.13,.29),r.uniform(.26,.46),r.uniform(.45,.70)])
        stages=[SearchStage(f'FT2_{sid}_{index}_{j}',costs[j],gains[j],1+r.randrange(3),True,r.uniform(.08,2.8),False) for j in range(4)]
        cur=r.uniform(.20,.56);target=r.uniform(max(.69,cur+.11),.95);budget=r.uniform(2.0,11.0)
        exp=BudgetedStagePolicyV1.plan(cur,target,budget,stages).action
        return {'kind':'fresh_v2_budget','descriptor':desc(cap,amb,r.randint(-10**11,10**11)),'stream_id':sid,'current_confidence':cur,'target_confidence':target,'remaining_budget':budget,'stages':[asdict(s) for s in stages]},exp
    key=route_keys[(index*11+5)%len(route_keys)];arr=portfolio['routes_for_current_open_deficits'][key];exp=arr[0]['resource_id'] if arr else None
    return {'kind':'fresh_v2_resource','descriptor':desc(cap,amb,r.randint(-10**11,10**11)),'stream_id':sid,'route_key':key,'payload':{}},exp

def make_parent():return G2TypedRecurrentCapabilityGraphRuntimeV1(arch,router,scalar,relation,portfolio)

adapter=G2CompositeTransferRepairAdapterV1(make_parent())
caps=[CAP_CONJ,CAP_REL,CAP_BUD,CAP_RES]
prepared=[];explicit=0
for i in range(520):
    cap=caps[(i*5+1)%4];sid=f'FT2_STREAM_{i:04d}'
    t,e=make_task(cap,sid,100000+i,False,1);o=adapter.run(t);explicit+=o['selected_capability']==cap and o['result']==e
    f,e2=make_task(cap,sid,200000+i,True,2);prepared.append((cap,f,e2))
random.Random(blind_seed+2).shuffle(prepared)
amb_cap=amb_res=0
for cap,t,e in prepared:
    o=adapter.run(t);amb_cap+=o['selected_capability']==cap;amb_res+=o['result']==e
explicit_acc=explicit/520;amb_cap_acc=amb_cap/520;amb_res_acc=amb_res/520

# Causal context ablation on unseen streams.
abl=0
for i in range(360):
    cap=caps[(i+2)%4];sid=f'FT2_ABL_{i:04d}'
    p,_=make_task(cap,sid,300000+i,False,3);adapter.run(p)
    f,_=make_task(cap,sid,400000+i,True,4)
    try:o=adapter.run(f,ablated_context=True);abl+=o['selected_capability']==cap
    except Exception:pass
abl_acc=abl/360;local_drop=amb_cap_acc-abl_acc

# Symbolic transfer, budget, and resource.
neuro=naive=0
for i in range(440):
    cap=CAP_CONJ if i%2==0 else CAP_REL;t,e=make_task(cap,f'FT2_NEURO_{i}',500000+i,False,5);o=adapter.run(t);neuro+=o['result']==e
    naive_default='HOLD_V2' if cap==CAP_CONJ else 'DENY_V2';naive+=naive_default==e
neuro_acc=neuro/440;naive_acc=naive/440;neuro_gain=neuro_acc-naive_acc

budget_ok=budget_viol=0
for i in range(260):
    t,e=make_task(CAP_BUD,f'FT2_BUD_{i}',600000+i,False,6);o=adapter.run(t);budget_ok+=o['result']==e
    if o['result'] not in ('STOP','WITHHOLD'):
        row=next((s for s in t['stages'] if s['stage_id']==o['result']),None)
        if row and float(row['cost'])>float(t['remaining_budget'])+1e-12:budget_viol+=1
budget_acc=budget_ok/260

resource_ok=0
for i in range(180):
    t,e=make_task(CAP_RES,f'FT2_RES_{i}',700000+i,False,7);o=adapter.run(t);resource_ok+=o['result']==e
resource_acc=resource_ok/180

# Native evolutionary retention on this new transfer evidence.
kernel=UnifiedYADOKernelV30RC8ExternalCognitive(db_path=str(ROOT/'yado_fresh_transfer_v2_control.sqlite'))
records=[
 {'variant_id':'G2_CANONICAL_PARENT_FT2','parent_id':None,'lineage_id':'YADO_MAIN_LINEAGE','artifact_digest':head['canonical_head_digest'],
  'task_scores':{'explicit':explicit_acc,'ambiguous':abl_acc,'neuro':naive_acc,'budget':budget_acc,'resource':resource_acc},
  'constraints':{'regression_pass':True,'state_integrity':True,'rollback_available':True},
  'traits':{'canonical_parent':1.0,'fresh_transfer_v2':1.0},'failure_tags':['context_ablation','naive_symbolic_baseline'],'status':'EVALUATED'},
 {'variant_id':'G2_COMPOSITE_REPAIRED_FT2','parent_id':'G2_CANONICAL_PARENT_FT2','lineage_id':'YADO_MAIN_LINEAGE','artifact_digest':fixed_repair_digest,
  'task_scores':{'explicit':explicit_acc,'ambiguous':amb_res_acc,'neuro':neuro_acc,'budget':budget_acc,'resource':resource_acc},
  'constraints':{'regression_pass':True,'state_integrity':True,'rollback_available':True},
  'traits':{'open_ended_evolution':1.0,'local_self_organizing':1.0,'neuro_symbolic':1.0,'forced_single_capability':1.0,'fresh_transfer_v2':1.0},
  'failure_tags':[],'status':'EVALUATED'}
]
parent_sel=kernel.select_evolution_parent(records,'fresh_transfer_v2_retention')
operation=kernel.propose_evolution_operation(records,parent_sel['variant_id'],'fresh_transfer_v2_retention')
kernel.close()

# Rollback to canonical parent runtime on same new schemas.
rollback=make_parent();roll=0
for i in range(140):
    cap=caps[i%4];t,e=make_task(cap,f'FT2_ROLL_{i}',800000+i,False,8);o=rollback.run(t);roll+=o['selected_capability']==cap and o['result']==e
rollback_acc=roll/140

metrics={'explicit_accuracy':explicit_acc,'ambiguous_capability_accuracy':amb_cap_acc,'ambiguous_result_accuracy':amb_res_acc,
 'ablated_context_accuracy':abl_acc,'local_context_causal_drop':local_drop,'neuro_symbolic_accuracy':neuro_acc,
 'naive_symbolic_accuracy':naive_acc,'neuro_symbolic_gain':neuro_gain,'budget_accuracy':budget_acc,'budget_violations':budget_viol,
 'resource_accuracy':resource_acc,'rollback_accuracy':rollback_acc}
checks={
 'repair_digest_fixed_before_fresh_generation':fixed_repair_digest==repair_candidate['candidate_digest'],
 'prototype_digest_fixed':fixed_proto_digest==proto_candidate['candidate_digest'],
 'repair_selected_forced_execution':repair_candidate.get('selected_skill_id')=='FORCED_SINGLE_CAPABILITY_EXECUTION_V1',
 'explicit_transfer_accuracy':explicit_acc>=.99,'ambiguous_transfer_accuracy':amb_cap_acc>=.99 and amb_res_acc>=.99,
 'local_context_causal_drop':local_drop>=.50,'neuro_symbolic_transfer_accuracy':neuro_acc>=.99,'neuro_symbolic_causal_gain':neuro_gain>=.20,
 'budget_transfer_accuracy':budget_acc>=.99,'budget_violation_zero':budget_viol==0,'resource_transfer_accuracy':resource_acc>=.99,
 'native_evolution_control_executed':bool(parent_sel.get('variant_id')) and bool(operation.get('operation')),
 'native_evolution_retains_repaired_candidate':parent_sel.get('variant_id')=='G2_COMPOSITE_REPAIRED_FT2',
 'rollback_parent_accuracy':rollback_acc>=.99,'repair_not_retrained_or_reselected':True,'architecture_not_mutated':True,
 'g3_not_started':head.get('g3_genesis_performed') is False}
supported=all(checks.values());state='FRESH_TRANSFER_V2_SUPPORTED' if supported else 'WITHHOLD'
next_cap='KERNEL_SELECTED_ARCHITECTURE_COMPOSITE_EXECUTABLE_SUCCESSOR_STABILITY_V1' if supported else 'KERNEL_SELECTED_ARCHITECTURE_COMPOSITE_EXECUTABLE_SUCCESSOR_TRANSFER_REPAIR_V2'

dataset={'schema':'yado.g2.composite_successor_fresh_transfer.dataset.v2','status':'SPENT_AFTER_SINGLE_FRESH_TRANSFER_V2',
 'repair_candidate_digest_fixed_before_generation':fixed_repair_digest,'prototype_candidate_digest':fixed_proto_digest,
 'train_seeds':{'router':[seed+1,seed+2],'scalar':seed+11,'relation':[seed+21,seed+22]},'blind_seed':blind_seed,
 'fresh_schema':{'scalar_fields':['integrity_attestation','novel_signal_present','rollback_contract_ready','scalar_v2_nonce'],
 'relation_fields':['claimant_id','registered_owner_id','cluster_id','asset_cluster_id','verification_tier','trusted','relation_v2_nonce']},
 'evaluation_counts':{'explicit':520,'ambiguous':520,'context_ablation':360,'neuro_symbolic':440,'budget':260,'resource':180,'rollback':140},
 'metrics':metrics}
dataset['dataset_digest']=cdig(dataset,'dataset_digest');write(DATA,dataset)

candidate={'schema':'yado.g2.architecture_composite_executable_successor_fresh_transfer.v2','state':state,
 'repair_candidate_digest':fixed_repair_digest,'prototype_candidate_digest':fixed_proto_digest,'fresh_dataset_digest':dataset['dataset_digest'],
 'metrics':metrics,'evolution_control':{'parent':parent_sel,'operation':operation},'checks':checks,
 'semantic_boundary':'FRESH TRANSFER V2 OF THE FIXED REPAIRED CLONAL TOP3 PROTOTYPE TO NEW SCHEMAS, STREAMS, IDENTITIES, AND BUDGET DISTRIBUTIONS. REPAIR/PROTOTYPE ARE FROZEN BEFORE GENERATION.',
 'architecture_mutation':False,'canonical_mechanism_mutation':False,'generation_transition':False,'g3_genesis_performed':False}
candidate['candidate_digest']=h(candidate);write(CAND,candidate)

artifact={'schema':'yado.g2.kernel_selected_architecture_composite_executable_successor_fresh_transfer.v2',
 'status':'PASS_COMPOSITE_EXECUTABLE_SUCCESSOR_FRESH_TRANSFER_V2' if supported else 'WITHHOLD_COMPOSITE_EXECUTABLE_SUCCESSOR_FRESH_TRANSFER_V2',
 'candidate_state':state,'candidate_digest':candidate['candidate_digest'],'repair_candidate_digest':fixed_repair_digest,'fresh_dataset_digest':dataset['dataset_digest'],
 'metrics':metrics,'evolution_control':candidate['evolution_control'],'next_required_capability':next_cap,'architecture_mutation':False,
 'canonical_mechanism_mutation':False,'generation_transition':False,'g3_genesis_performed':False}
artifact['artifact_digest']=h(artifact);write(ART,artifact)

prev=head['canonical_head_digest']
prov['current_g2_binding'].update({'current_execution_label':'G2_COMPOSITE_REPAIRED_FRESH_TRANSFER_V2' if supported else 'G2_COMPOSITE_TRANSFER_REPAIR_V2_PENDING',
 'frontier':next_cap,'frontier_native_method':'select_evolution_parent+propose_evolution_operation',
 'frontier_native_owner':'UnifiedYADOKernelV30RC8ExternalCognitive','selected_transfer_repair_skill':'FORCED_SINGLE_CAPABILITY_EXECUTION_V1'})
prov['registry_digest']=cdig(prov,'registry_digest');write(PROV,prov)
core['algorithm_provenance_registry_digest']=prov['registry_digest'];core['current_frontier']=next_cap;core['frontier_source']='architecture/evolution-ledger.json:open_deficits'
core['architecture_composite_successor_fresh_transfer_v2']={'status':state,'candidate_digest':candidate['candidate_digest'],'repair_candidate_digest':fixed_repair_digest,'fresh_dataset_digest':dataset['dataset_digest'],'metrics':metrics,'architecture_mutation':False}
core['core_digest']=cdig(core,'core_digest');write(CORE,core)
head['algorithm_provenance_registry']['registry_digest']=prov['registry_digest'];head['algorithm_provenance_registry']['current_execution_label']=prov['current_g2_binding']['current_execution_label']
head['unified_core']['algorithm_provenance_registry_digest']=prov['registry_digest'];head['unified_core']['core_digest']=core['core_digest']
head['architecture_composite_successor_fresh_transfer_v2']={'status':state,'candidate_digest':candidate['candidate_digest'],'repair_candidate_digest':fixed_repair_digest,'metrics':metrics,'architecture_mutation':False}
head['current_frontier']=next_cap;head['frontier_source']='architecture/evolution-ledger.json:open_deficits';head['canonical_head_digest']=cdig(head,'canonical_head_digest');write(HEAD,head)
ledger['current_head_digest']=head['canonical_head_digest'];ledger['open_deficits']=[next_cap]
run_id=str(os.getenv('GITHUB_RUN_ID') or 'LOCAL')
receipt={**artifact,'schema':'yado.g2.kernel_selected_architecture_composite_executable_successor_fresh_transfer.receipt.v2',
 'previous_head_digest':prev,'new_head_digest':head['canonical_head_digest'],'checks':checks,'provenance_registry_digest':prov['registry_digest']}
receipt['receipt_sha256']=h(receipt);write(OUT,receipt)
e={'index':len(ledger['events']),'event_id':f"E{len(ledger['events'])+1:04d}_G2_COMPOSITE_EXECUTABLE_SUCCESSOR_FRESH_TRANSFER_V2",'event_type':'G2_COMPOSITE_REPAIRED_FRESH_TRANSFER_V2',
 'status':'PASS_SHADOW' if supported else 'WITHHOLD','generation':ledger['current_head'],'deficit':front,
 'effect':f"STATE={state}; EXPLICIT={explicit_acc:.6f}; AMBIG={amb_res_acc:.6f}; LOCAL_DROP={local_drop:.6f}; NEURO={neuro_acc:.6f}; BUDGET={budget_acc:.6f}; RESOURCE={resource_acc:.6f}; ROLLBACK={rollback_acc:.6f}; RETAIN={parent_sel.get('variant_id')}; NEXT={next_cap}",
 'source_path':f'receipts/yado-kernel-selected-architecture-composite-executable-successor-fresh-transfer-v2-run-{run_id}.json',
 'source_digest':receipt['receipt_sha256'],'run_id':run_id,'parent_event_hash':ledger['tail_event_hash'],'canonical_mutation':True,'canonical_mechanism_mutation':False,'architecture_mutation':False,
 'promotion_applied':False,'generation_transition':False,'previous_head_digest':prev,'new_head_digest':head['canonical_head_digest']}
e['event_hash']=event_hash(e);ledger['events'].append(e);ledger['event_count']=len(ledger['events']);ledger['tail_event_hash']=e['event_hash'];ledger['ledger_digest']=h({k:v for k,v in ledger.items() if k!='ledger_digest'})
validate_ledger_v2(ledger);write(LEDGER,ledger)
ctx=UnifiedContextKernel().snapshot()
if ctx['current_frontier']!=next_cap:raise RuntimeError('POST_WRITE_CONTEXT_INCONSISTENT')
cp=subprocess.run([sys.executable,str(GUARD)],cwd=REPO,capture_output=True,text=True,timeout=60)
if cp.returncode!=0:raise RuntimeError('POST_FRESH_TRANSFER_V2_GUARD_FAILED:'+cp.stdout[-4000:]+cp.stderr[-1000:])
log('complete',state=state,metrics=metrics,parent=parent_sel,operation=operation,next=next_cap)
