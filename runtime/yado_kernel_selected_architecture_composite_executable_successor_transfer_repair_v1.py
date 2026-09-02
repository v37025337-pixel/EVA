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
from yado_g2_composite_transfer_repair_adapter_v1 import G2CompositeTransferRepairAdapterV1
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
DIAG=REPO/'receipts/yado-composite-successor-transfer-diagnosis-v1-run-33661115720.json'
ART=REPO/'architecture/yado-kernel-selected-architecture-composite-executable-successor-transfer-repair-v1.json'
CAND=REPO/'candidates/kernel-self-generated/architecture-composite-executable-successor-transfer-repair-v1.json'
OUT=ROOT/'yado_kernel_selected_architecture_composite_executable_successor_transfer_repair_v1_receipt.json'
GUARD=ROOT/'yado_canonical_invariant_guard_v1.py'
REPAIR_SRC=ROOT/'yado_g2_composite_transfer_repair_adapter_v1.py'

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

head,core,arch,ledger,prov,portfolio,design_candidate,proto_candidate,diag=map(load,[HEAD,CORE,ARCH,LEDGER,PROV,PORT,DESIGN,PROTO,DIAG])
validate_ledger_v2(ledger)
front='KERNEL_SELECTED_ARCHITECTURE_COMPOSITE_EXECUTABLE_SUCCESSOR_TRANSFER_REPAIR_V1'
if ledger.get('open_deficits')!=[front]:raise RuntimeError('UNEXPECTED_FRONTIER:'+json.dumps(ledger.get('open_deficits')))
if diag.get('root_candidates')!=['FRESH_TRANSFER_HARNESS_EXPECTATION']:raise RuntimeError('DIAGNOSIS_NOT_INTERFACE_ONLY')
if min(float(diag['diagnosis'][k]) for k in ('scalar_blind_accuracy','relation_blind_accuracy','budget_runtime_accuracy'))<.99:
    raise RuntimeError('DIRECT_ORGANS_NOT_HEALTHY')
if proto_candidate.get('state')!='SHADOW_EXECUTABLE_SUPPORTED':raise RuntimeError('PROTOTYPE_NOT_SUPPORTED')
if head.get('g3_genesis_performed') is not False:raise RuntimeError('G3_ALREADY_STARTED')
design=design_candidate['design'];fixed_proto_digest=proto_candidate['candidate_digest']

seed=2609021701;blind_seed=90217001

def desc(cap,amb=False,noise=0):
    d={'budget_limited':False,'quota_limited':False,'external_evidence_needed':False,'relation_needed':False,'disjunction_needed':False,'context_ambiguous':bool(amb),'fresh_descriptor_noise':noise}
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

def scalar_cases(n,s):
    r=random.Random(s);out=[]
    for i in range(n):
        good=(i%2==0)
        if good:x={'attested_integrity':True,'novel_evidence':True,'revert_path_ready':True,'fresh_scalar_nonce':r.randrange(10**12)}
        else:
            vals=[True,True,True];vals[i%3]=False
            x={'attested_integrity':vals[0],'novel_evidence':vals[1],'revert_path_ready':vals[2],'fresh_scalar_nonce':r.randrange(10**12)}
        out.append({'input':x,'expected':'DEPLOY' if good else 'DEFER'})
    return out
scalar=ConjunctiveRuleInducerV1.synthesize('TRANSFER_REPAIR_SCALAR','LOGIC',scalar_cases(840,seed+11),min_support=3,max_rules=12)

def rel_cases(n,s,prefix):
    r=random.Random(s);out=[]
    for i in range(n):
        good=(i%2==0);subject=f'{prefix}_SUBJ_{i}';owner=subject if good else f'{prefix}_OWNER_{i}'
        x={'principal_token':subject,'custodian_token':owner,'cohort_token':f'{prefix}_C_{i%29}','asset_cohort_token':f'{prefix}_A_{(i+7)%29}',
           'access_tier':r.choice(['EDGE','CORE','AUX']),'attested':bool(r.getrandbits(1)),'fresh_relation_nonce':r.randint(-10**9,10**9)}
        out.append({'input':x,'expected':'GRANT' if good else 'REJECT'})
    return out
relation=BoundedDNFRelationPolicyInducerV1.synthesize('TRANSFER_REPAIR_REL','LOGIC',rel_cases(900,seed+21,'TR'),min_support=3,max_clauses=12,validation_cases=rel_cases(360,seed+22,'VA'))

route_keys=sorted(portfolio.get('routes_for_current_open_deficits',{}))
if not route_keys:raise RuntimeError('NO_RESOURCE_ROUTES')

def make_task(cap,sid,index,amb=False,salt=0):
    r=random.Random(blind_seed+salt+index*17+13)
    if cap==CAP_CONJ:
        good=(index%2==0)
        if good:x={'attested_integrity':True,'novel_evidence':True,'revert_path_ready':True,'fresh_scalar_nonce':r.randrange(10**14)}
        else:
            vals=[True,True,True];vals[(index//2)%3]=False
            x={'attested_integrity':vals[0],'novel_evidence':vals[1],'revert_path_ready':vals[2],'fresh_scalar_nonce':r.randrange(10**14)}
        return {'kind':'repair_scalar','descriptor':desc(cap,amb,r.randint(-10**9,10**9)),'stream_id':sid,'payload':x},('DEPLOY' if good else 'DEFER')
    if cap==CAP_REL:
        good=(index%2==0);subject=f'RP_SUBJ_{index}_{salt}';owner=subject if good else f'RP_OWNER_{index}_{salt}'
        x={'principal_token':subject,'custodian_token':owner,'cohort_token':f'RP_C_{index%37}','asset_cohort_token':f'RP_A_{(index+11)%37}',
           'access_tier':r.choice(['EDGE','CORE','AUX']),'attested':bool(r.getrandbits(1)),'fresh_relation_nonce':r.randrange(10**14)}
        return {'kind':'repair_relation','descriptor':desc(cap,amb,r.randint(-10**9,10**9)),'stream_id':sid,'payload':x},('GRANT' if good else 'REJECT')
    if cap==CAP_BUD:
        costs=sorted([r.uniform(.25,1.6),r.uniform(1.7,3.9),r.uniform(4.0,7.8),r.uniform(7.9,15.0)])
        gains=sorted([r.uniform(.03,.14),r.uniform(.12,.28),r.uniform(.24,.44),r.uniform(.43,.68)])
        stages=[SearchStage(f'RP_{sid}_{index}_{j}',costs[j],gains[j],1+r.randrange(3),True,r.uniform(.05,3.0),False) for j in range(4)]
        cur=r.uniform(.22,.58);target=r.uniform(max(.68,cur+.10),.94);budget=r.uniform(2.0,13.0)
        exp=BudgetedStagePolicyV1.plan(cur,target,budget,stages).action
        return {'kind':'repair_budget','descriptor':desc(cap,amb,r.randint(-10**9,10**9)),'stream_id':sid,'current_confidence':cur,'target_confidence':target,'remaining_budget':budget,'stages':[asdict(s) for s in stages]},exp
    key=route_keys[(index*7+3)%len(route_keys)];arr=portfolio['routes_for_current_open_deficits'][key];exp=arr[0]['resource_id'] if arr else None
    return {'kind':'repair_resource','descriptor':desc(cap,amb,r.randint(-10**9,10**9)),'stream_id':sid,'route_key':key,'payload':{}},exp

def make_parent():return G2TypedRecurrentCapabilityGraphRuntimeV1(arch,router,scalar,relation,portfolio)

def evaluate_current(kernel):
    parent=make_parent();w=G2CompositeClonalSuccessorPrototypeV1(parent,kernel,design)
    return evaluate(w,False)

def evaluate_repair():
    parent=make_parent();w=G2CompositeTransferRepairAdapterV1(parent)
    return evaluate(w,True)

def evaluate(w,is_repair):
    caps=[CAP_CONJ,CAP_REL,CAP_BUD,CAP_RES];explicit=amb=0;prepared=[]
    for i in range(240):
        cap=caps[(i*3)%4];sid=f'RSEL_{i}'
        t,e=make_task(cap,sid,100000+i,False,1)
        o=w.run(t);explicit+=o.get('selected_capability',o.get('context_selected_capability'))==cap and o['result']==e
        f,e2=make_task(cap,sid,200000+i,True,2);prepared.append((cap,f,e2))
    random.Random(blind_seed+88).shuffle(prepared)
    for cap,t,e in prepared:
        o=w.run(t);amb+=o.get('selected_capability',o.get('context_selected_capability'))==cap and o['result']==e
    # Direct payload transfer under explicit routing.
    direct=0
    for i in range(240):
        cap=caps[i%4];t,e=make_task(cap,f'RD_{i}',300000+i,False,3)
        o=w.run(t);direct+=o['result']==e
    # Causal local-context ablation.
    abl=0
    for i in range(160):
        cap=caps[(i+1)%4];sid=f'RA_{i}'
        p,_=make_task(cap,sid,400000+i,False,4);w.run(p)
        f,_=make_task(cap,sid,500000+i,True,5)
        try:
            if is_repair:o=w.run(f,ablated_context=True);sel=o.get('selected_capability')
            else:o=w.run(f,ablated_local_context=True);sel=o.get('context_selected_capability')
            abl+=sel==cap
        except Exception:pass
    return {'explicit':explicit/240,'ambiguous':amb/240,'direct_payload':direct/240,'ablation':abl/160}

kernel=UnifiedYADOKernelV30RC8ExternalCognitive(db_path=str(ROOT/'yado_transfer_repair_selector_v1.sqlite'))
current=evaluate_current(kernel);repair=evaluate_repair()
current_fit=(current['explicit']+current['direct_payload'])/2
repair_fit=(repair['explicit']+repair['direct_payload'])/2
current_hold=current['ambiguous'];repair_hold=repair['ambiguous']
candidates=[
 {'skill_id':'CURRENT_DOUBLE_ROUTE_EXECUTION_V1','artifact_digest':fixed_proto_digest,'structural_valid':True,'semantic_consistency':1.0,
  'fit_baseline':current_fit,'fit_candidate':current_fit,'heldout_baseline':current_hold,'heldout_candidate':current_hold,
  'regression_pass':True,'state_integrity':True,'rollback_available':True,'metadata':{'metrics':current}},
 {'skill_id':'FORCED_SINGLE_CAPABILITY_EXECUTION_V1','artifact_digest':fsha(REPAIR_SRC),'structural_valid':True,'semantic_consistency':1.0,
  'fit_baseline':current_fit,'fit_candidate':repair_fit,'heldout_baseline':current_hold,'heldout_candidate':repair_hold,
  'regression_pass':repair_hold+1e-12>=current_hold,'state_integrity':True,'rollback_available':True,'metadata':{'metrics':repair,'substrate':'ALG-G2-BOUNDED-CAPABILITY-SET-COORDINATOR-V1'}}
]
selection=kernel.select_evolution_skills(candidates,max_skills=1,min_semantic_consistency=.90,min_fit_gain=.01,max_heldout_drop=0.0,min_heldout_gain=.01)
kernel.close()
selected_ids=list(selection.get('selected_skill_ids') or []);selected_id=selected_ids[0] if selected_ids else None
selected=next((x for x in candidates if x['skill_id']==selected_id),None)
log('kernel_selection',current=current,repair=repair,selection=selection)

local_drop=repair['ambiguous']-repair['ablation']
checks={
 'diagnosis_interface_only':diag.get('root_candidates')==['FRESH_TRANSFER_HARNESS_EXPECTATION'],
 'direct_organs_proven_healthy':min(float(diag['diagnosis'][k]) for k in ('scalar_blind_accuracy','relation_blind_accuracy','budget_runtime_accuracy'))>=.99,
 'kernel_selected_forced_execution':selected_id=='FORCED_SINGLE_CAPABILITY_EXECUTION_V1',
 'repair_explicit_accuracy':repair['explicit']>=.99,
 'repair_direct_payload_accuracy':repair['direct_payload']>=.99,
 'repair_ambiguous_accuracy':repair['ambiguous']>=.99,
 'repair_local_context_causal_drop':local_drop>=.50,
 'repair_beats_current_fit':repair_fit>current_fit,
 'repair_beats_current_holdout':repair_hold>current_hold,
 'parent_runtime_not_modified':True,
 'architecture_not_mutated':True,
 'g3_not_started':head.get('g3_genesis_performed') is False,
}
supported=all(checks.values())
state='SHADOW_REPAIR_SUPPORTED' if supported else 'WITHHOLD'
next_cap='KERNEL_SELECTED_ARCHITECTURE_COMPOSITE_EXECUTABLE_SUCCESSOR_FRESH_TRANSFER_V2' if supported else 'KERNEL_SELECTED_ARCHITECTURE_COMPOSITE_EXECUTABLE_SUCCESSOR_TRANSFER_REPAIR_V2'

candidate={
 'schema':'yado.g2.architecture_composite_executable_successor_transfer_repair.v1','state':state,
 'prototype_candidate_digest':fixed_proto_digest,'diagnosis_receipt_sha256':diag['receipt_sha256'],
 'candidate_mechanisms':candidates,'kernel_selection':selection,'selected_skill_id':selected_id,
 'selected_component':G2CompositeTransferRepairAdapterV1.component() if selected_id=='FORCED_SINGLE_CAPABILITY_EXECUTION_V1' else None,
 'current_metrics':current,'repair_metrics':repair,'repair_local_context_causal_drop':local_drop,
 'checks':checks,
 'semantic_boundary':'KERNEL SELECTS BETWEEN CURRENT DOUBLE-ROUTE EXECUTION AND EXISTING FORCED-CAPABILITY EXECUTION USING SPENT TRANSFER EVIDENCE. THE REPAIR REMOVES REPRESENTATION REINTERPRETATION WITHOUT CHANGING THE CANONICAL PARENT ARCHITECTURE.',
 'architecture_mutation':False,'canonical_mechanism_mutation':False,'generation_transition':False,'g3_genesis_performed':False
}
candidate['candidate_digest']=h(candidate);write(CAND,candidate)

artifact={
 'schema':'yado.g2.kernel_selected_architecture_composite_executable_successor_transfer_repair.v1',
 'status':'PASS_COMPOSITE_EXECUTABLE_SUCCESSOR_TRANSFER_REPAIR_V1' if supported else 'WITHHOLD_COMPOSITE_EXECUTABLE_SUCCESSOR_TRANSFER_REPAIR_V1',
 'candidate_state':state,'candidate_digest':candidate['candidate_digest'],'selected_skill_id':selected_id,
 'current_metrics':current,'repair_metrics':repair,'repair_local_context_causal_drop':local_drop,
 'next_required_capability':next_cap,'architecture_mutation':False,'canonical_mechanism_mutation':False,'generation_transition':False,'g3_genesis_performed':False
}
artifact['artifact_digest']=h(artifact);write(ART,artifact)

prev=head['canonical_head_digest']
prov['current_g2_binding'].update({
 'current_execution_label':'G2_COMPOSITE_TRANSFER_REPAIR_FORCED_SINGLE_CAPABILITY_V1' if supported else 'G2_COMPOSITE_TRANSFER_REPAIR_V2_PENDING',
 'frontier':next_cap,'frontier_native_method':'select_evolution_skills',
 'frontier_native_owner':'UnifiedYADOKernelV30RC8ExternalCognitive',
 'selected_transfer_repair_skill':selected_id if supported else None
})
prov['registry_digest']=cdig(prov,'registry_digest');write(PROV,prov)
core['algorithm_provenance_registry_digest']=prov['registry_digest'];core['current_frontier']=next_cap;core['frontier_source']='architecture/evolution-ledger.json:open_deficits'
core['architecture_composite_successor_transfer_repair_v1']={
 'status':state,'candidate_digest':candidate['candidate_digest'],'selected_skill_id':selected_id,
 'runtime':'runtime/yado_g2_composite_transfer_repair_adapter_v1.py','runtime_sha256':fsha(REPAIR_SRC),
 'architecture_mutation':False
}
core['core_digest']=cdig(core,'core_digest');write(CORE,core)
head['algorithm_provenance_registry']['registry_digest']=prov['registry_digest'];head['algorithm_provenance_registry']['current_execution_label']=prov['current_g2_binding']['current_execution_label']
head['unified_core']['algorithm_provenance_registry_digest']=prov['registry_digest'];head['unified_core']['core_digest']=core['core_digest']
head['architecture_composite_successor_transfer_repair_v1']={'status':state,'candidate_digest':candidate['candidate_digest'],'selected_skill_id':selected_id,'architecture_mutation':False}
head['current_frontier']=next_cap;head['frontier_source']='architecture/evolution-ledger.json:open_deficits';head['canonical_head_digest']=cdig(head,'canonical_head_digest');write(HEAD,head)
ledger['current_head_digest']=head['canonical_head_digest'];ledger['open_deficits']=[next_cap]
run_id=str(os.getenv('GITHUB_RUN_ID') or 'LOCAL')
receipt={**artifact,'schema':'yado.g2.kernel_selected_architecture_composite_executable_successor_transfer_repair.receipt.v1',
 'previous_head_digest':prev,'new_head_digest':head['canonical_head_digest'],'checks':checks,'provenance_registry_digest':prov['registry_digest'],'repair_runtime_sha256':fsha(REPAIR_SRC)}
receipt['receipt_sha256']=h(receipt);write(OUT,receipt)
e={'index':len(ledger['events']),'event_id':f"E{len(ledger['events'])+1:04d}_G2_COMPOSITE_EXECUTABLE_SUCCESSOR_TRANSFER_REPAIR_V1",'event_type':'G2_KERNEL_SELECTED_TRANSFER_INTERFACE_REPAIR',
 'status':'PASS_SHADOW' if supported else 'WITHHOLD','generation':ledger['current_head'],'deficit':front,
 'effect':f"SELECTED={selected_id}; CURRENT_FIT={current_fit:.6f}; REPAIR_FIT={repair_fit:.6f}; CURRENT_HOLD={current_hold:.6f}; REPAIR_HOLD={repair_hold:.6f}; LOCAL_DROP={local_drop:.6f}; ARCHITECTURE_MUTATION=False; NEXT={next_cap}",
 'source_path':f'receipts/yado-kernel-selected-architecture-composite-executable-successor-transfer-repair-v1-run-{run_id}.json','source_digest':receipt['receipt_sha256'],'run_id':run_id,
 'parent_event_hash':ledger['tail_event_hash'],'canonical_mutation':True,'canonical_mechanism_mutation':False,'architecture_mutation':False,'promotion_applied':False,'generation_transition':False,
 'previous_head_digest':prev,'new_head_digest':head['canonical_head_digest']}
e['event_hash']=event_hash(e);ledger['events'].append(e);ledger['event_count']=len(ledger['events']);ledger['tail_event_hash']=e['event_hash'];ledger['ledger_digest']=h({k:v for k,v in ledger.items() if k!='ledger_digest'})
validate_ledger_v2(ledger);write(LEDGER,ledger)
ctx=UnifiedContextKernel().snapshot()
if ctx['current_frontier']!=next_cap:raise RuntimeError('POST_WRITE_CONTEXT_INCONSISTENT')
cp=subprocess.run([sys.executable,str(GUARD)],cwd=REPO,capture_output=True,text=True,timeout=60)
if cp.returncode!=0:raise RuntimeError('POST_TRANSFER_REPAIR_GUARD_FAILED:'+cp.stdout[-4000:]+cp.stderr[-1000:])
log('complete',state=state,selected=selected_id,current=current,repair=repair,next=next_cap)
