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
from yado_g2_contextual_stream_capability_adapter_v1 import ContextualStreamCapabilityAdapterV1
from yado_g2_composite_transfer_repair_adapter_v1 import G2CompositeTransferRepairAdapterV1
from yado_evolution_ledger_v2 import validate_ledger_v2,event_hash
from yado_unified_context_kernel_v1 import UnifiedContextKernel

HEAD=REPO/'canonical/yado-main-head-g2.json';CORE=REPO/'canonical/yado-unified-core-v1.json';ARCH=REPO/'canonical/yado-g2-architecture-v1.json'
LEDGER=REPO/'architecture/evolution-ledger.json';PROV=REPO/'canonical/yado-algorithm-provenance-registry-v1.json';PORT=REPO/'resources/yado-unified-external-resource-portfolio-v1.json'
REPAIR=REPO/'candidates/kernel-self-generated/architecture-composite-executable-successor-transfer-repair-v1.json'
STABILITY=REPO/'candidates/kernel-self-generated/architecture-composite-executable-successor-stability-v1.json'
ART=REPO/'architecture/yado-kernel-selected-architecture-composite-executable-successor-canonical-admission-v1.json'
CAND=REPO/'candidates/kernel-self-generated/architecture-composite-executable-successor-canonical-admission-v1.json'
CANON=REPO/'canonical/yado-g2-composite-executable-successor-v1.json'
DATA=REPO/'resources/yado-composite-successor-canonical-admission-fresh-v1.json'
OUT=ROOT/'yado_kernel_selected_architecture_composite_executable_successor_canonical_admission_v1_receipt.json'
GUARD=ROOT/'yado_canonical_invariant_guard_v1.py';REPAIR_SRC=ROOT/'yado_g2_composite_transfer_repair_adapter_v1.py'

CAP_CONJ='ALG-CONJUNCTIVE-RULE-INDUCER-V1';CAP_REL='ALG-BOUNDED-DNF-RELATION-POLICY-INDUCER-V1';CAP_BUD='ALG-BUDGETED-STAGE-POLICY-V1';CAP_RES='RESOURCE-PORTFOLIO-V1'
COMP='ALG-G2-COMPOSITE-TRANSFER-REPAIR-ADAPTER-V1'
def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def h(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def fsha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def write(p,o):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(o,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')
def cdig(o,field):
 x=copy.deepcopy(o);x.pop(field,None);return h(x)
def log(stage,**kw):print(json.dumps({'stage':stage,**kw},sort_keys=True,default=str),flush=True)

head,core,arch,ledger,prov,portfolio,repair,stability=map(load,[HEAD,CORE,ARCH,LEDGER,PROV,PORT,REPAIR,STABILITY]);validate_ledger_v2(ledger)
front='KERNEL_SELECTED_ARCHITECTURE_COMPOSITE_EXECUTABLE_SUCCESSOR_CANONICAL_ADMISSION_V1'
if ledger.get('open_deficits')!=[front]:raise RuntimeError('UNEXPECTED_FRONTIER:'+json.dumps(ledger.get('open_deficits')))
if repair.get('state')!='SHADOW_REPAIR_SUPPORTED' or repair.get('selected_skill_id')!='FORCED_SINGLE_CAPABILITY_EXECUTION_V1':raise RuntimeError('REPAIR_NOT_FIXED')
if stability.get('state')!='STABILITY_SUPPORTED':raise RuntimeError('STABILITY_NOT_SUPPORTED')
if head.get('g3_genesis_performed') is not False:raise RuntimeError('G3_ALREADY_STARTED')
fixed_repair=repair['candidate_digest'];fixed_stability=stability['candidate_digest'];route_keys=sorted(portfolio.get('routes_for_current_open_deficits',{}))
seed=2609023101;blind_seed=90231001

def desc(cap,amb=False,noise=0):
 d={'budget_limited':False,'quota_limited':False,'external_evidence_needed':False,'relation_needed':False,'disjunction_needed':False,'context_ambiguous':amb,'admission_noise':noise}
 if not amb:
  if cap==CAP_BUD:d['quota_limited']=True
  elif cap==CAP_RES:d['external_evidence_needed']=True
  elif cap==CAP_REL:d['disjunction_needed']=True
 return d
def router_cases(n,s):
 r=random.Random(s);caps=[CAP_CONJ,CAP_REL,CAP_BUD,CAP_RES];out=[]
 for i in range(n):
  cap=caps[(i*3+r.randrange(4))%4];out.append({'input':desc(cap,False,r.randint(-10**12,10**12)),'expected':cap})
 return out
router=BoundedCapabilityRouterLearnerV1.synthesize(router_cases(1000,seed+1),router_cases(400,seed+2),CAP_CONJ,min_support=6)

def scalar_cases(n,s):
 r=random.Random(s);out=[]
 for i in range(n):
  good=i%2==0
  if good:x={'integrity_marker':True,'evidence_marker':True,'rollback_marker':True,'adm_nonce':r.randrange(10**17)}
  else:
   vals=[True,True,True];vals[(i//2)%3]=False;x={'integrity_marker':vals[0],'evidence_marker':vals[1],'rollback_marker':vals[2],'adm_nonce':r.randrange(10**17)}
  out.append({'input':x,'expected':'ADMIT_OK' if good else 'ADMIT_HOLD'})
 return out
scalar=ConjunctiveRuleInducerV1.synthesize('CANONICAL_ADMISSION_SCALAR','LOGIC',scalar_cases(800,seed+11),min_support=3,max_rules=12)
def rel_cases(n,s,prefix):
 r=random.Random(s);out=[]
 for i in range(n):
  good=i%2==0;q=f'{prefix}_Q_{i}';o=q if good else f'{prefix}_O_{i}'
  x={'requester_key':q,'owner_key':o,'scope_key':f'{prefix}_S_{i%37}','asset_scope_key':f'{prefix}_AS_{(i+15)%37}',
     'trust_level':r.choice(['A','B','C']),'verified':bool(r.getrandbits(1)),'adm_rel_nonce':r.randrange(10**17)}
  out.append({'input':x,'expected':'ACCESS_OK' if good else 'ACCESS_DENY'})
 return out
relation=BoundedDNFRelationPolicyInducerV1.synthesize('CANONICAL_ADMISSION_REL','LOGIC',rel_cases(860,seed+21,'TR'),min_support=3,max_clauses=12,validation_cases=rel_cases(360,seed+22,'VA'))

def make_parent():return G2TypedRecurrentCapabilityGraphRuntimeV1(arch,router,scalar,relation,portfolio)
def task(cap,sid,index,amb=False,salt=0):
 r=random.Random(blind_seed+salt+index*29+23)
 if cap==CAP_CONJ:
  good=index%2==0
  if good:x={'integrity_marker':True,'evidence_marker':True,'rollback_marker':True,'adm_nonce':r.randrange(10**18)}
  else:
   vals=[True,True,True];vals[(index//2)%3]=False;x={'integrity_marker':vals[0],'evidence_marker':vals[1],'rollback_marker':vals[2],'adm_nonce':r.randrange(10**18)}
  return {'kind':'admission_scalar','descriptor':desc(cap,amb,r.randint(-10**13,10**13)),'stream_id':sid,'payload':x},('ADMIT_OK' if good else 'ADMIT_HOLD')
 if cap==CAP_REL:
  good=index%2==0;q=f'AQ_{index}_{salt}';o=q if good else f'AO_{index}_{salt}'
  x={'requester_key':q,'owner_key':o,'scope_key':f'AS_{index%41}','asset_scope_key':f'AAS_{(index+17)%41}','trust_level':r.choice(['A','B','C']),'verified':bool(r.getrandbits(1)),'adm_rel_nonce':r.randrange(10**18)}
  return {'kind':'admission_relation','descriptor':desc(cap,amb,r.randint(-10**13,10**13)),'stream_id':sid,'payload':x},('ACCESS_OK' if good else 'ACCESS_DENY')
 if cap==CAP_BUD:
  costs=sorted([r.uniform(.2,1.2),r.uniform(1.3,2.8),r.uniform(2.9,5.7),r.uniform(5.8,11.5)])
  gains=sorted([r.uniform(.04,.16),r.uniform(.14,.30),r.uniform(.27,.48),r.uniform(.46,.72)])
  stages=[SearchStage(f'ADM_{sid}_{index}_{j}',costs[j],gains[j],1+r.randrange(3),True,r.uniform(.05,2.2),False) for j in range(4)]
  cur=r.uniform(.18,.54);target=r.uniform(max(.68,cur+.11),.95);budget=r.uniform(1.8,10);exp=BudgetedStagePolicyV1.plan(cur,target,budget,stages).action
  return {'kind':'admission_budget','descriptor':desc(cap,amb,r.randint(-10**13,10**13)),'stream_id':sid,'current_confidence':cur,'target_confidence':target,'remaining_budget':budget,'stages':[asdict(s) for s in stages]},exp
 key=route_keys[(index*17+9)%len(route_keys)];arr=portfolio['routes_for_current_open_deficits'][key];exp=arr[0]['resource_id'] if arr else None
 return {'kind':'admission_resource','descriptor':desc(cap,amb,r.randint(-10**13,10**13)),'stream_id':sid,'route_key':key,'payload':{}},exp

# Fresh admission compares current canonical double-route with fixed repaired path.
def eval_mode(mode):
 parent=make_parent();w=ContextualStreamCapabilityAdapterV1(parent,'BOUNDED_STREAM_CONTEXT_MAP') if mode=='CURRENT' else G2CompositeTransferRepairAdapterV1(parent)
 caps=[CAP_CONJ,CAP_REL,CAP_BUD,CAP_RES];explicit=0;prepared=[]
 for i in range(320):
  cap=caps[(i+1)%4];sid=f'ADM_{mode}_{i}';t,e=task(cap,sid,100000+i,False,1)
  o=w.run(t);sel=o.get('context_selected_capability',o.get('selected_capability'));explicit+=sel==cap and o['result']==e
  f,e2=task(cap,sid,200000+i,True,2);prepared.append((cap,f,e2))
 random.Random(blind_seed+77).shuffle(prepared);amb=0
 for cap,t,e in prepared:
  o=w.run(t);sel=o.get('context_selected_capability',o.get('selected_capability'));amb+=sel==cap and o['result']==e
 # ablation for repaired/current.
 abl=0
 for i in range(200):
  cap=caps[(i+2)%4];sid=f'ABL_{mode}_{i}';p,_=task(cap,sid,300000+i,False,3);w.run(p);f,_=task(cap,sid,400000+i,True,4)
  try:
   o=w.run(f,ablated_context=True) if mode=='REPAIR' else w.run(f,ablated_context=True)
   sel=o.get('context_selected_capability',o.get('selected_capability'));abl+=sel==cap
  except Exception:pass
 return {'explicit':explicit/320,'ambiguous':amb/320,'ablation':abl/200}

current=eval_mode('CURRENT');repaired=eval_mode('REPAIR');local_drop=repaired['ambiguous']-repaired['ablation']
# Additional fresh safety/result gates only on fixed repaired path.
w=G2CompositeTransferRepairAdapterV1(make_parent());neuro=naive=0
for i in range(240):
 cap=CAP_CONJ if i%2==0 else CAP_REL;t,e=task(cap,f'NEU_{i}',500000+i,False,5);o=w.run(t);neuro+=o['result']==e;naive+=('ADMIT_HOLD' if cap==CAP_CONJ else 'ACCESS_DENY')==e
neuro_acc=neuro/240;naive_acc=naive/240
bud=viol=0
for i in range(160):
 t,e=task(CAP_BUD,f'BUD_{i}',600000+i,False,6);o=w.run(t);bud+=o['result']==e
 if o['result'] not in ('STOP','WITHHOLD'):
  row=next((s for s in t['stages'] if s['stage_id']==o['result']),None)
  if row and float(row['cost'])>float(t['remaining_budget'])+1e-12:viol+=1
res=0
for i in range(120):
 t,e=task(CAP_RES,f'RES_{i}',700000+i,False,7);o=w.run(t);res+=o['result']==e
rollback=make_parent();roll=0
for i in range(100):
 cap=[CAP_CONJ,CAP_REL,CAP_BUD,CAP_RES][i%4];t,e=task(cap,f'RB_{i}',800000+i,False,8);o=rollback.run(t);roll+=o['selected_capability']==cap and o['result']==e
metrics={'current_explicit':current['explicit'],'current_ambiguous':current['ambiguous'],'repaired_explicit':repaired['explicit'],'repaired_ambiguous':repaired['ambiguous'],
 'repaired_ablation':repaired['ablation'],'local_context_causal_drop':local_drop,'neuro_symbolic_accuracy':neuro_acc,'neuro_symbolic_gain':neuro_acc-naive_acc,
 'budget_accuracy':bud/160,'budget_violations':viol,'resource_accuracy':res/120,'rollback_accuracy':roll/100}

kernel=UnifiedYADOKernelV30RC8ExternalCognitive(db_path=str(ROOT/'yado_canonical_admission_v1.sqlite'))
candidates=[
 {'skill_id':'CURRENT_CANONICAL_DOUBLE_ROUTE_V1','artifact_digest':head['canonical_head_digest'],'structural_valid':True,'semantic_consistency':1.0,
  'fit_baseline':current['explicit'],'fit_candidate':current['explicit'],'heldout_baseline':current['ambiguous'],'heldout_candidate':current['ambiguous'],'regression_pass':True,'state_integrity':True,'rollback_available':True},
 {'skill_id':'ADMIT_COMPOSITE_REPAIRED_SUCCESSOR_V1','artifact_digest':fixed_repair,'structural_valid':True,'semantic_consistency':1.0,
  'fit_baseline':current['explicit'],'fit_candidate':repaired['explicit'],'heldout_baseline':current['ambiguous'],'heldout_candidate':repaired['ambiguous'],'regression_pass':repaired['ambiguous']>=current['ambiguous'],'state_integrity':True,'rollback_available':True}
]
selection=kernel.select_evolution_skills(candidates,max_skills=1,min_semantic_consistency=.90,min_fit_gain=.01,max_heldout_drop=0,min_heldout_gain=.01);kernel.close()
selected=(selection.get('selected_skill_ids') or [None])[0]
checks={'repair_digest_fixed_before_admission':fixed_repair==repair['candidate_digest'],'stability_digest_fixed_before_admission':fixed_stability==stability['candidate_digest'],
 'kernel_admits_repaired_successor':selected=='ADMIT_COMPOSITE_REPAIRED_SUCCESSOR_V1','fresh_repaired_explicit':repaired['explicit']>=.99,'fresh_repaired_ambiguous':repaired['ambiguous']>=.99,
 'fresh_local_causal_drop':local_drop>=.50,'fresh_neuro_symbolic':neuro_acc>=.99,'fresh_neuro_gain':neuro_acc-naive_acc>=.20,'fresh_budget':bud/160>=.99,'budget_violations_zero':viol==0,
 'fresh_resource':res/120>=.99,'rollback_parent':roll/100>=.99,'g3_not_started':head.get('g3_genesis_performed') is False,'architecture_family_unchanged':head.get('architecture_family')=='TYPED_RECURRENT_CAPABILITY_GRAPH'}
admit=all(checks.values());state='CANONICAL_ADMITTED' if admit else 'WITHHOLD'
next_cap='KERNEL_G2_COMPOSITE_CANONICAL_POST_ADMISSION_AUDIT_V1' if admit else 'KERNEL_SELECTED_ARCHITECTURE_COMPOSITE_EXECUTABLE_SUCCESSOR_CANONICAL_ADMISSION_V2'

dataset={'schema':'yado.g2.composite_successor_canonical_admission_fresh.v1','status':'SPENT_AFTER_SINGLE_CANONICAL_ADMISSION','repair_digest_fixed':fixed_repair,'stability_digest_fixed':fixed_stability,
 'seed':seed,'blind_seed':blind_seed,'metrics':metrics};dataset['dataset_digest']=cdig(dataset,'dataset_digest');write(DATA,dataset)

canonical_component=None
if admit:
 canonical_component={'schema':'yado.g2.composite_executable_successor.canonical.v1','status':'CANONICAL_ACTIVE','component_id':COMP,
  'component':G2CompositeTransferRepairAdapterV1.component(),'runtime_source':'runtime/yado_g2_composite_transfer_repair_adapter_v1.py','runtime_sha256':fsha(REPAIR_SRC),
  'architecture_family':'TYPED_RECURRENT_CAPABILITY_GRAPH','architecture_mutation':False,'formal_generation':'G2_CANDIDATE_TRCG_V1',
  'selected_families':['OPEN_ENDED_EVOLUTION','LOCAL_SELF_ORGANIZING','NEURO_SYMBOLIC'],'evolution_operation':'CLONAL',
  'repair_candidate_digest':fixed_repair,'stability_candidate_digest':fixed_stability,'fresh_admission_dataset_digest':dataset['dataset_digest'],'fresh_admission_metrics':metrics,
  'semantic_boundary':'CANONICAL G2 EXECUTION ADAPTER FOR SINGLE-SELECTION FORCED-CAPABILITY EXECUTION OVER THE EXISTING TYPED RECURRENT CAPABILITY GRAPH. THIS IS NOT G3 AND DOES NOT CHANGE THE FORMAL ARCHITECTURE FAMILY.'}
 canonical_component['canonical_component_digest']=cdig(canonical_component,'canonical_component_digest');write(CANON,canonical_component)

candidate={'schema':'yado.g2.architecture_composite_executable_successor_canonical_admission.v1','state':state,'repair_candidate_digest':fixed_repair,'stability_candidate_digest':fixed_stability,
 'fresh_dataset_digest':dataset['dataset_digest'],'fresh_metrics':metrics,'kernel_selection':selection,'selected_skill_id':selected,'checks':checks,'canonical_component':canonical_component,
 'canonical_mechanism_mutation':admit,'architecture_mutation':False,'generation_transition':False,'g3_genesis_performed':False}
candidate['candidate_digest']=h(candidate);write(CAND,candidate)
artifact={'schema':'yado.g2.kernel_selected_architecture_composite_executable_successor_canonical_admission.v1','status':'PASS_COMPOSITE_EXECUTABLE_SUCCESSOR_CANONICAL_ADMISSION_V1' if admit else 'WITHHOLD_COMPOSITE_EXECUTABLE_SUCCESSOR_CANONICAL_ADMISSION_V1',
 'candidate_state':state,'candidate_digest':candidate['candidate_digest'],'selected_skill_id':selected,'fresh_metrics':metrics,'canonical_component_digest':None if not canonical_component else canonical_component['canonical_component_digest'],
 'next_required_capability':next_cap,'canonical_mechanism_mutation':admit,'architecture_mutation':False,'generation_transition':False,'g3_genesis_performed':False}
artifact['artifact_digest']=h(artifact);write(ART,artifact)

prev=head['canonical_head_digest']
prov['current_g2_binding'].update({'current_execution_label':'G2_COMPOSITE_REPAIRED_CANONICAL_V1' if admit else 'G2_COMPOSITE_CANONICAL_ADMISSION_V2_PENDING','frontier':next_cap,
 'frontier_native_method':'select_evolution_skills','frontier_native_owner':'UnifiedYADOKernelV30RC8ExternalCognitive','selected_transfer_repair_skill':'FORCED_SINGLE_CAPABILITY_EXECUTION_V1',
 'canonical_composite_component':COMP if admit else None})
prov['registry_digest']=cdig(prov,'registry_digest');write(PROV,prov)
if admit:
 core['active_runtime_sources']=sorted(set(core.get('active_runtime_sources',[])+['runtime/yado_g2_composite_transfer_repair_adapter_v1.py']))
 core['composite_executable_successor_v1']={'status':'CANONICAL_ACTIVE','component_id':COMP,'canonical_component_digest':canonical_component['canonical_component_digest'],'runtime_sha256':fsha(REPAIR_SRC),
  'selected_families':canonical_component['selected_families'],'evolution_operation':'CLONAL','fresh_admission_metrics':metrics,'architecture_mutation':False}
 core['canonical_mechanism_mutation']=True
 head['active_capabilities']=sorted(set(head.get('active_capabilities',[])+[COMP]))
 head['new_capabilities']=sorted(set(head.get('new_capabilities',[])+[COMP]))
 head['composite_executable_successor_v1']={'status':'CANONICAL_ACTIVE','component_id':COMP,'canonical_component_digest':canonical_component['canonical_component_digest'],'selected_families':canonical_component['selected_families'],'evolution_operation':'CLONAL','fresh_admission_metrics':metrics,'architecture_mutation':False}
core['algorithm_provenance_registry_digest']=prov['registry_digest'];core['current_frontier']=next_cap;core['frontier_source']='architecture/evolution-ledger.json:open_deficits';core['core_digest']=cdig(core,'core_digest');write(CORE,core)
head['algorithm_provenance_registry']['registry_digest']=prov['registry_digest'];head['algorithm_provenance_registry']['current_execution_label']=prov['current_g2_binding']['current_execution_label'];head['unified_core']['algorithm_provenance_registry_digest']=prov['registry_digest'];head['unified_core']['core_digest']=core['core_digest'];head['current_frontier']=next_cap;head['frontier_source']='architecture/evolution-ledger.json:open_deficits';head['canonical_head_digest']=cdig(head,'canonical_head_digest');write(HEAD,head)
ledger['current_head_digest']=head['canonical_head_digest'];ledger['open_deficits']=[next_cap]
run_id=str(os.getenv('GITHUB_RUN_ID') or 'LOCAL')
receipt={**artifact,'schema':'yado.g2.kernel_selected_architecture_composite_executable_successor_canonical_admission.receipt.v1','previous_head_digest':prev,'new_head_digest':head['canonical_head_digest'],'checks':checks,'provenance_registry_digest':prov['registry_digest']}
receipt['receipt_sha256']=h(receipt);write(OUT,receipt)
e={'index':len(ledger['events']),'event_id':f"E{len(ledger['events'])+1:04d}_G2_COMPOSITE_EXECUTABLE_SUCCESSOR_CANONICAL_ADMISSION_V1",'event_type':'G2_COMPOSITE_REPAIRED_CANONICAL_ADMISSION',
 'status':'PASS_CANONICAL' if admit else 'WITHHOLD','generation':ledger['current_head'],'deficit':front,
 'effect':f"STATE={state}; SELECTED={selected}; CURRENT_EXPLICIT={current['explicit']:.6f}; REPAIRED_EXPLICIT={repaired['explicit']:.6f}; CURRENT_AMBIG={current['ambiguous']:.6f}; REPAIRED_AMBIG={repaired['ambiguous']:.6f}; LOCAL_DROP={local_drop:.6f}; CANONICAL={admit}; G3=False; NEXT={next_cap}",
 'source_path':f'receipts/yado-kernel-selected-architecture-composite-executable-successor-canonical-admission-v1-run-{run_id}.json','source_digest':receipt['receipt_sha256'],'run_id':run_id,'parent_event_hash':ledger['tail_event_hash'],
 'canonical_mutation':True,'canonical_mechanism_mutation':admit,'architecture_mutation':False,'promotion_applied':False,'generation_transition':False,'previous_head_digest':prev,'new_head_digest':head['canonical_head_digest']}
e['event_hash']=event_hash(e);ledger['events'].append(e);ledger['event_count']=len(ledger['events']);ledger['tail_event_hash']=e['event_hash'];ledger['ledger_digest']=h({k:v for k,v in ledger.items() if k!='ledger_digest'})
validate_ledger_v2(ledger);write(LEDGER,ledger);ctx=UnifiedContextKernel().snapshot()
if ctx['current_frontier']!=next_cap:raise RuntimeError('POST_WRITE_CONTEXT_INCONSISTENT')
cp=subprocess.run([sys.executable,str(GUARD)],cwd=REPO,capture_output=True,text=True,timeout=60)
if cp.returncode!=0:raise RuntimeError('POST_CANONICAL_ADMISSION_GUARD_FAILED:'+cp.stdout[-4000:]+cp.stderr[-1000:])
log('complete',state=state,selected=selected,metrics=metrics,next=next_cap)
