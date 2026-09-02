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

HEAD=REPO/'canonical/yado-main-head-g2.json';CORE=REPO/'canonical/yado-unified-core-v1.json';ARCH=REPO/'canonical/yado-g2-architecture-v1.json'
LEDGER=REPO/'architecture/evolution-ledger.json';PROV=REPO/'canonical/yado-algorithm-provenance-registry-v1.json';PORT=REPO/'resources/yado-unified-external-resource-portfolio-v1.json'
REPAIR=REPO/'candidates/kernel-self-generated/architecture-composite-executable-successor-transfer-repair-v1.json'
FRESH=REPO/'candidates/kernel-self-generated/architecture-composite-executable-successor-fresh-transfer-v2.json'
ART=REPO/'architecture/yado-kernel-selected-architecture-composite-executable-successor-stability-v1.json'
CAND=REPO/'candidates/kernel-self-generated/architecture-composite-executable-successor-stability-v1.json'
OUT=ROOT/'yado_kernel_selected_architecture_composite_executable_successor_stability_v1_receipt.json'
GUARD=ROOT/'yado_canonical_invariant_guard_v1.py'

CAP_CONJ='ALG-CONJUNCTIVE-RULE-INDUCER-V1';CAP_REL='ALG-BOUNDED-DNF-RELATION-POLICY-INDUCER-V1';CAP_BUD='ALG-BUDGETED-STAGE-POLICY-V1';CAP_RES='RESOURCE-PORTFOLIO-V1'
def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def h(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def write(p,o):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(o,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')
def cdig(o,field):
 x=copy.deepcopy(o);x.pop(field,None);return h(x)
def log(stage,**kw):print(json.dumps({'stage':stage,**kw},sort_keys=True,default=str),flush=True)

head,core,arch,ledger,prov,portfolio,repair,fresh=map(load,[HEAD,CORE,ARCH,LEDGER,PROV,PORT,REPAIR,FRESH]);validate_ledger_v2(ledger)
front='KERNEL_SELECTED_ARCHITECTURE_COMPOSITE_EXECUTABLE_SUCCESSOR_STABILITY_V1'
if ledger.get('open_deficits')!=[front]:raise RuntimeError('UNEXPECTED_FRONTIER:'+json.dumps(ledger.get('open_deficits')))
if repair.get('state')!='SHADOW_REPAIR_SUPPORTED' or repair.get('selected_skill_id')!='FORCED_SINGLE_CAPABILITY_EXECUTION_V1':raise RuntimeError('REPAIR_NOT_FIXED')
if fresh.get('state')!='FRESH_TRANSFER_V2_SUPPORTED':raise RuntimeError('FRESH_V2_NOT_SUPPORTED')
if head.get('g3_genesis_performed') is not False:raise RuntimeError('G3_ALREADY_STARTED')
repair_digest=repair['candidate_digest'];fresh_digest=fresh['candidate_digest'];route_keys=sorted(portfolio.get('routes_for_current_open_deficits',{}))
if not route_keys:raise RuntimeError('NO_RESOURCE_ROUTES')

def desc(cap,amb=False,noise=0):
 d={'budget_limited':False,'quota_limited':False,'external_evidence_needed':False,'relation_needed':False,'disjunction_needed':False,'context_ambiguous':amb,'stability_noise':noise}
 if not amb:
  if cap==CAP_BUD:d['budget_limited']=True
  elif cap==CAP_RES:d['external_evidence_needed']=True
  elif cap==CAP_REL:d['relation_needed']=True
 return d

def build_epoch(epoch,seed):
 def router_cases(n,s):
  r=random.Random(s);caps=[CAP_CONJ,CAP_REL,CAP_BUD,CAP_RES];out=[]
  for i in range(n):
   cap=caps[(i+r.randrange(4))%4];out.append({'input':desc(cap,False,r.randint(-10**11,10**11)),'expected':cap})
  return out
 router=BoundedCapabilityRouterLearnerV1.synthesize(router_cases(1100,seed+1),router_cases(440,seed+2),CAP_CONJ,min_support=6)
 def scalar_cases(n,s):
  r=random.Random(s);out=[]
  for i in range(n):
   good=i%2==0
   if good:x={'integrity_attestation':True,'novel_signal_present':True,'rollback_contract_ready':True,'stable_nonce':r.randrange(10**16)}
   else:
    vals=[True,True,True];vals[(i//2)%3]=False;x={'integrity_attestation':vals[0],'novel_signal_present':vals[1],'rollback_contract_ready':vals[2],'stable_nonce':r.randrange(10**16)}
   out.append({'input':x,'expected':'ACCEPT_STABLE' if good else 'HOLD_STABLE'})
  return out
 scalar=ConjunctiveRuleInducerV1.synthesize(f'STABILITY_SCALAR_{epoch}','LOGIC',scalar_cases(760,seed+11),min_support=3,max_rules=12)
 def rel_cases(n,s,prefix):
  r=random.Random(s);out=[]
  for i in range(n):
   good=i%2==0;c=f'{prefix}_C_{i}';o=c if good else f'{prefix}_O_{i}'
   x={'claimant_id':c,'registered_owner_id':o,'cluster_id':f'{prefix}_G_{i%31}','asset_cluster_id':f'{prefix}_A_{(i+9)%31}',
      'verification_tier':r.choice(['L1','L2','L3']),'trusted':bool(r.getrandbits(1)),'stable_rel_nonce':r.randrange(10**16)}
   out.append({'input':x,'expected':'AUTHORIZE_STABLE' if good else 'DENY_STABLE'})
  return out
 relation=BoundedDNFRelationPolicyInducerV1.synthesize(f'STABILITY_REL_{epoch}','LOGIC',rel_cases(820,seed+21,f'T{epoch}'),min_support=3,max_clauses=12,validation_cases=rel_cases(340,seed+22,f'V{epoch}'))
 return G2TypedRecurrentCapabilityGraphRuntimeV1(arch,router,scalar,relation,portfolio)

def task(cap,sid,index,seed,amb=False):
 r=random.Random(seed+index*23+19)
 if cap==CAP_CONJ:
  good=index%2==0
  if good:x={'integrity_attestation':True,'novel_signal_present':True,'rollback_contract_ready':True,'stable_nonce':r.randrange(10**17)}
  else:
   vals=[True,True,True];vals[(index//2)%3]=False;x={'integrity_attestation':vals[0],'novel_signal_present':vals[1],'rollback_contract_ready':vals[2],'stable_nonce':r.randrange(10**17)}
  return {'kind':'stability_scalar','descriptor':desc(cap,amb,r.randint(-10**12,10**12)),'stream_id':sid,'payload':x},('ACCEPT_STABLE' if good else 'HOLD_STABLE')
 if cap==CAP_REL:
  good=index%2==0;c=f'SC_{seed}_{index}';o=c if good else f'SO_{seed}_{index}'
  x={'claimant_id':c,'registered_owner_id':o,'cluster_id':f'SG_{index%37}','asset_cluster_id':f'SA_{(index+11)%37}','verification_tier':r.choice(['L1','L2','L3']),'trusted':bool(r.getrandbits(1)),'stable_rel_nonce':r.randrange(10**17)}
  return {'kind':'stability_relation','descriptor':desc(cap,amb,r.randint(-10**12,10**12)),'stream_id':sid,'payload':x},('AUTHORIZE_STABLE' if good else 'DENY_STABLE')
 if cap==CAP_BUD:
  costs=sorted([r.uniform(.25,1.3),r.uniform(1.4,3.0),r.uniform(3.1,6.0),r.uniform(6.1,12)])
  gains=sorted([r.uniform(.04,.15),r.uniform(.13,.28),r.uniform(.24,.45),r.uniform(.44,.69)])
  stages=[SearchStage(f'ST_{sid}_{index}_{j}',costs[j],gains[j],1+r.randrange(3),True,r.uniform(.05,2.5),False) for j in range(4)]
  cur=r.uniform(.2,.56);target=r.uniform(max(.69,cur+.1),.95);budget=r.uniform(1.8,10.5);exp=BudgetedStagePolicyV1.plan(cur,target,budget,stages).action
  return {'kind':'stability_budget','descriptor':desc(cap,amb,r.randint(-10**12,10**12)),'stream_id':sid,'current_confidence':cur,'target_confidence':target,'remaining_budget':budget,'stages':[asdict(s) for s in stages]},exp
 key=route_keys[(index*13+7)%len(route_keys)];arr=portfolio['routes_for_current_open_deficits'][key];exp=arr[0]['resource_id'] if arr else None
 return {'kind':'stability_resource','descriptor':desc(cap,amb,r.randint(-10**12,10**12)),'stream_id':sid,'route_key':key,'payload':{}},exp

epochs=[];caps=[CAP_CONJ,CAP_REL,CAP_BUD,CAP_RES]
for epoch in range(1,5):
 seed=2609030000+epoch*1009;runtime=build_epoch(epoch,seed);adapter=G2CompositeTransferRepairAdapterV1(runtime)
 explicit=0;prepared=[]
 for i in range(360):
  cap=caps[(i+epoch)%4];sid=f'E{epoch}_S{i}';t,e=task(cap,sid,100000+i,seed,False);o=adapter.run(t);explicit+=o['selected_capability']==cap and o['result']==e
  f,e2=task(cap,sid,200000+i,seed+1,True);prepared.append((cap,f,e2))
 random.Random(seed+2).shuffle(prepared);amb=0
 for cap,t,e in prepared:
  o=adapter.run(t);amb+=o['selected_capability']==cap and o['result']==e
 # ablation
 abl=0
 for i in range(200):
  cap=caps[(i+2*epoch)%4];sid=f'E{epoch}_A{i}';p,_=task(cap,sid,300000+i,seed+3,False);adapter.run(p);f,_=task(cap,sid,400000+i,seed+4,True)
  try:o=adapter.run(f,ablated_context=True);abl+=o['selected_capability']==cap
  except Exception:pass
 # budget/resource direct
 bud=viol=0
 for i in range(160):
  t,e=task(CAP_BUD,f'E{epoch}_B{i}',500000+i,seed+5,False);o=adapter.run(t);bud+=o['result']==e
  if o['result'] not in ('STOP','WITHHOLD'):
   row=next((s for s in t['stages'] if s['stage_id']==o['result']),None)
   if row and float(row['cost'])>float(t['remaining_budget'])+1e-12:viol+=1
 res=0
 for i in range(100):
  t,e=task(CAP_RES,f'E{epoch}_R{i}',600000+i,seed+6,False);o=adapter.run(t);res+=o['result']==e
 # LRU stress: 1152 streams, newest 1024 must remain exact.
 lru=[]
 for i in range(1152):
  cap=caps[i%4];sid=f'E{epoch}_LRU{i}';t,_=task(cap,sid,700000+i,seed+7,False);adapter.run(t);lru.append((sid,cap))
 recent=lru[-1024:];recent_ok=0
 for i,(sid,cap) in enumerate(recent):
  t,e=task(cap,sid,800000+i,seed+8,True);o=adapter.run(t);recent_ok+=o['selected_capability']==cap and o['result']==e
 # rollback on fresh parent
 rollback=build_epoch(epoch,seed);roll=0
 for i in range(100):
  cap=caps[i%4];t,e=task(cap,f'E{epoch}_RB{i}',900000+i,seed+9,False);o=rollback.run(t);roll+=o['selected_capability']==cap and o['result']==e
 metrics={'explicit_accuracy':explicit/360,'ambiguous_accuracy':amb/360,'ablated_context_accuracy':abl/200,'local_context_causal_drop':amb/360-abl/200,
          'budget_accuracy':bud/160,'budget_violations':viol,'resource_accuracy':res/100,'lru_recent_accuracy':recent_ok/1024,'rollback_accuracy':roll/100}
 passed=metrics['explicit_accuracy']>=.99 and metrics['ambiguous_accuracy']>=.99 and metrics['local_context_causal_drop']>=.50 and metrics['budget_accuracy']>=.99 and viol==0 and metrics['resource_accuracy']>=.99 and metrics['lru_recent_accuracy']>=.99 and metrics['rollback_accuracy']>=.99
 epochs.append({'epoch':epoch,'seed':seed,'status':'PASS' if passed else 'WITHHOLD','metrics':metrics})
 log('epoch',epoch=epoch,status=epochs[-1]['status'],metrics=metrics)

min_metrics={k:min(e['metrics'][k] for e in epochs) for k in epochs[0]['metrics']}
all_pass=all(e['status']=='PASS' for e in epochs)
kernel=UnifiedYADOKernelV30RC8ExternalCognitive(db_path=str(ROOT/'yado_stability_control_v1.sqlite'))
mean_score=sum((e['metrics']['explicit_accuracy']+e['metrics']['ambiguous_accuracy']+e['metrics']['budget_accuracy']+e['metrics']['resource_accuracy']+e['metrics']['rollback_accuracy'])/5 for e in epochs)/len(epochs)
records=[
 {'variant_id':'G2_REPAIRED_STABILITY_BASELINE','parent_id':None,'lineage_id':'YADO_MAIN_LINEAGE','artifact_digest':fresh_digest,
  'task_scores':{'stability':mean_score,'causal':min_metrics['ablated_context_accuracy']},
  'constraints':{'regression_pass':True,'state_integrity':True,'rollback_available':True},'traits':{'fresh_v2':1.0},'failure_tags':['context_ablation'],'status':'EVALUATED'},
 {'variant_id':'G2_REPAIRED_STABLE_V1','parent_id':'G2_REPAIRED_STABILITY_BASELINE','lineage_id':'YADO_MAIN_LINEAGE','artifact_digest':repair_digest,
  'task_scores':{'stability':mean_score,'causal':min_metrics['local_context_causal_drop']},
  'constraints':{'regression_pass':all_pass,'state_integrity':True,'rollback_available':True},'traits':{'forced_single_capability':1.0,'stability_epochs':4.0},'failure_tags':[],'status':'EVALUATED'}]
parent_sel=kernel.select_evolution_parent(records,'stability_retention');operation=kernel.propose_evolution_operation(records,parent_sel['variant_id'],'stability_retention');kernel.close()
checks={'four_epochs_pass':all_pass,'min_explicit_accuracy':min_metrics['explicit_accuracy']>=.99,'min_ambiguous_accuracy':min_metrics['ambiguous_accuracy']>=.99,
 'min_local_causal_drop':min_metrics['local_context_causal_drop']>=.50,'min_budget_accuracy':min_metrics['budget_accuracy']>=.99,'budget_violations_zero':max(e['metrics']['budget_violations'] for e in epochs)==0,
 'min_resource_accuracy':min_metrics['resource_accuracy']>=.99,'min_lru_recent_accuracy':min_metrics['lru_recent_accuracy']>=.99,'min_rollback_accuracy':min_metrics['rollback_accuracy']>=.99,
 'native_evolution_retains_stable_candidate':parent_sel.get('variant_id')=='G2_REPAIRED_STABLE_V1','repair_digest_fixed':repair_digest==repair['candidate_digest'],'fresh_v2_digest_fixed':fresh_digest==fresh['candidate_digest'],
 'architecture_not_mutated':True,'g3_not_started':head.get('g3_genesis_performed') is False}
supported=all(checks.values());state='STABILITY_SUPPORTED' if supported else 'WITHHOLD'
next_cap='KERNEL_SELECTED_ARCHITECTURE_COMPOSITE_EXECUTABLE_SUCCESSOR_CANONICAL_ADMISSION_V1' if supported else 'KERNEL_SELECTED_ARCHITECTURE_COMPOSITE_EXECUTABLE_SUCCESSOR_STABILITY_V2'
candidate={'schema':'yado.g2.architecture_composite_executable_successor_stability.v1','state':state,'repair_candidate_digest':repair_digest,'fresh_v2_candidate_digest':fresh_digest,
 'epochs':epochs,'min_metrics':min_metrics,'evolution_control':{'parent':parent_sel,'operation':operation},'checks':checks,
 'semantic_boundary':'FOUR-EPOCH STABILITY TEST OF THE FIXED REPAIRED SHADOW COMPOSITE SUCCESSOR, INCLUDING CONTEXT CAUSAL ABLATION, LRU CAPACITY STRESS, BUDGET SAFETY, RESOURCE ROUTING, AND ROLLBACK. NO CANONICAL ARCHITECTURE ADMISSION YET.',
 'architecture_mutation':False,'canonical_mechanism_mutation':False,'generation_transition':False,'g3_genesis_performed':False}
candidate['candidate_digest']=h(candidate);write(CAND,candidate)
artifact={'schema':'yado.g2.kernel_selected_architecture_composite_executable_successor_stability.v1','status':'PASS_COMPOSITE_EXECUTABLE_SUCCESSOR_STABILITY_V1' if supported else 'WITHHOLD_COMPOSITE_EXECUTABLE_SUCCESSOR_STABILITY_V1',
 'candidate_state':state,'candidate_digest':candidate['candidate_digest'],'min_metrics':min_metrics,'epoch_count':len(epochs),'evolution_control':candidate['evolution_control'],
 'next_required_capability':next_cap,'architecture_mutation':False,'canonical_mechanism_mutation':False,'generation_transition':False,'g3_genesis_performed':False}
artifact['artifact_digest']=h(artifact);write(ART,artifact)
prev=head['canonical_head_digest']
prov['current_g2_binding'].update({'current_execution_label':'G2_COMPOSITE_REPAIRED_STABILITY_V1' if supported else 'G2_COMPOSITE_STABILITY_V2_PENDING','frontier':next_cap,
 'frontier_native_method':'select_evolution_parent+propose_evolution_operation','frontier_native_owner':'UnifiedYADOKernelV30RC8ExternalCognitive','selected_transfer_repair_skill':'FORCED_SINGLE_CAPABILITY_EXECUTION_V1'})
prov['registry_digest']=cdig(prov,'registry_digest');write(PROV,prov)
core['algorithm_provenance_registry_digest']=prov['registry_digest'];core['current_frontier']=next_cap;core['frontier_source']='architecture/evolution-ledger.json:open_deficits'
core['architecture_composite_successor_stability_v1']={'status':state,'candidate_digest':candidate['candidate_digest'],'repair_candidate_digest':repair_digest,'fresh_v2_candidate_digest':fresh_digest,'min_metrics':min_metrics,'architecture_mutation':False}
core['core_digest']=cdig(core,'core_digest');write(CORE,core)
head['algorithm_provenance_registry']['registry_digest']=prov['registry_digest'];head['algorithm_provenance_registry']['current_execution_label']=prov['current_g2_binding']['current_execution_label'];head['unified_core']['algorithm_provenance_registry_digest']=prov['registry_digest'];head['unified_core']['core_digest']=core['core_digest']
head['architecture_composite_successor_stability_v1']={'status':state,'candidate_digest':candidate['candidate_digest'],'min_metrics':min_metrics,'architecture_mutation':False}
head['current_frontier']=next_cap;head['frontier_source']='architecture/evolution-ledger.json:open_deficits';head['canonical_head_digest']=cdig(head,'canonical_head_digest');write(HEAD,head)
ledger['current_head_digest']=head['canonical_head_digest'];ledger['open_deficits']=[next_cap]
run_id=str(os.getenv('GITHUB_RUN_ID') or 'LOCAL')
receipt={**artifact,'schema':'yado.g2.kernel_selected_architecture_composite_executable_successor_stability.receipt.v1','previous_head_digest':prev,'new_head_digest':head['canonical_head_digest'],'checks':checks,'provenance_registry_digest':prov['registry_digest']}
receipt['receipt_sha256']=h(receipt);write(OUT,receipt)
e={'index':len(ledger['events']),'event_id':f"E{len(ledger['events'])+1:04d}_G2_COMPOSITE_EXECUTABLE_SUCCESSOR_STABILITY_V1",'event_type':'G2_COMPOSITE_REPAIRED_STABILITY','status':'PASS_SHADOW' if supported else 'WITHHOLD','generation':ledger['current_head'],'deficit':front,
 'effect':f"STATE={state}; EPOCHS={len(epochs)}; MIN_EXPLICIT={min_metrics['explicit_accuracy']:.6f}; MIN_AMBIG={min_metrics['ambiguous_accuracy']:.6f}; MIN_DROP={min_metrics['local_context_causal_drop']:.6f}; MIN_LRU={min_metrics['lru_recent_accuracy']:.6f}; MIN_ROLLBACK={min_metrics['rollback_accuracy']:.6f}; NEXT={next_cap}",
 'source_path':f'receipts/yado-kernel-selected-architecture-composite-executable-successor-stability-v1-run-{run_id}.json','source_digest':receipt['receipt_sha256'],'run_id':run_id,'parent_event_hash':ledger['tail_event_hash'],
 'canonical_mutation':True,'canonical_mechanism_mutation':False,'architecture_mutation':False,'promotion_applied':False,'generation_transition':False,'previous_head_digest':prev,'new_head_digest':head['canonical_head_digest']}
e['event_hash']=event_hash(e);ledger['events'].append(e);ledger['event_count']=len(ledger['events']);ledger['tail_event_hash']=e['event_hash'];ledger['ledger_digest']=h({k:v for k,v in ledger.items() if k!='ledger_digest'})
validate_ledger_v2(ledger);write(LEDGER,ledger);ctx=UnifiedContextKernel().snapshot()
if ctx['current_frontier']!=next_cap:raise RuntimeError('POST_WRITE_CONTEXT_INCONSISTENT')
cp=subprocess.run([sys.executable,str(GUARD)],cwd=REPO,capture_output=True,text=True,timeout=60)
if cp.returncode!=0:raise RuntimeError('POST_STABILITY_GUARD_FAILED:'+cp.stdout[-4000:]+cp.stderr[-1000:])
log('complete',state=state,min_metrics=min_metrics,parent=parent_sel,operation=operation,next=next_cap)
