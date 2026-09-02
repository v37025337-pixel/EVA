from __future__ import annotations
from pathlib import Path
from dataclasses import asdict
import copy,hashlib,json,os,random,subprocess,sys

ROOT=Path(__file__).resolve().parent;REPO=ROOT.parent;PKG=ROOT/'yado_rc8_v36'
sys.path[:0]=[str(ROOT),str(PKG)]
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
CANON=REPO/'canonical/yado-g2-composite-executable-successor-v1.json';ADMIT=REPO/'receipts/yado-kernel-selected-architecture-composite-executable-successor-canonical-admission-v1-run-33664703437.json'
STABILITY=REPO/'candidates/kernel-self-generated/architecture-composite-executable-successor-stability-v1.json'
OUT=ROOT/'yado_g2_composite_canonical_post_admission_audit_v1_receipt.json';GUARD=ROOT/'yado_canonical_invariant_guard_v1.py';SRC=ROOT/'yado_g2_composite_transfer_repair_adapter_v1.py'
COMP='ALG-G2-COMPOSITE-TRANSFER-REPAIR-ADAPTER-V1'
CAP_CONJ='ALG-CONJUNCTIVE-RULE-INDUCER-V1';CAP_REL='ALG-BOUNDED-DNF-RELATION-POLICY-INDUCER-V1';CAP_BUD='ALG-BUDGETED-STAGE-POLICY-V1';CAP_RES='RESOURCE-PORTFOLIO-V1'
def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def h(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def fsha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def write(p,o):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(o,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')
def cdig(o,field):
 x=copy.deepcopy(o);x.pop(field,None);return h(x)

head,core,arch,ledger,prov,portfolio,cc,admit,stability=map(load,[HEAD,CORE,ARCH,LEDGER,PROV,PORT,CANON,ADMIT,STABILITY]);validate_ledger_v2(ledger)
front='KERNEL_G2_COMPOSITE_CANONICAL_POST_ADMISSION_AUDIT_V1'
if ledger.get('open_deficits')!=[front]:raise RuntimeError('UNEXPECTED_FRONTIER')
plane=next((p for p in core.get('planes',[]) if p.get('plane_id')=='INTELLIGENCE_AND_META_SELECTION'),{})
rim=core.get('runtime_integrity_manifest',{})
last_admit=next((e for e in reversed(ledger['events']) if e.get('event_id')=='E0234_G2_COMPOSITE_EXECUTABLE_SUCCESSOR_CANONICAL_ADMISSION_V1'),None)
prior_detail=next((e for e in reversed(ledger['events']) if e.get('event_id')=='E0233_G2_CANONICAL_ADMISSION_FAILURE_DETAIL_33664450398'),None)
guard=subprocess.run([sys.executable,str(GUARD)],cwd=REPO,capture_output=True,text=True,timeout=60)
guard_json={}
try:guard_json=json.loads(guard.stdout)
except Exception:pass

# Restart canary: reconstruct an ephemeral workload after reading canonical state from disk.
seed=2609025201
def desc(cap,amb=False):
 d={'budget_limited':False,'quota_limited':False,'external_evidence_needed':False,'relation_needed':False,'disjunction_needed':False,'context_ambiguous':amb}
 if not amb:
  if cap==CAP_BUD:d['budget_limited']=True
  elif cap==CAP_RES:d['external_evidence_needed']=True
  elif cap==CAP_REL:d['relation_needed']=True
 return d
def router_cases(n,s):
 r=random.Random(s);caps=[CAP_CONJ,CAP_REL,CAP_BUD,CAP_RES];return [{'input':desc(caps[i%4],False)|{'audit_noise':r.randrange(10**9)},'expected':caps[i%4]} for i in range(n)]
router=BoundedCapabilityRouterLearnerV1.synthesize(router_cases(480,seed+1),router_cases(200,seed+2),CAP_CONJ,min_support=5)
scalar_cases=[]
for i in range(360):
 good=i%2==0;x={'a':good,'b':True,'c':True,'nonce':i};scalar_cases.append({'input':x,'expected':'YES' if good else 'NO'})
scalar=ConjunctiveRuleInducerV1.synthesize('POST_ADMISSION_AUDIT_SCALAR','LOGIC',scalar_cases,min_support=3,max_rules=8)
rel_train=[];rel_val=[]
for arr,n,prefix in ((rel_train,420,'TR'),(rel_val,180,'VA')):
 for i in range(n):
  good=i%2==0;q=f'{prefix}Q{i}';o=q if good else f'{prefix}O{i}'
  arr.append({'input':{'q':q,'o':o,'g':f'{prefix}G{i%17}','og':f'{prefix}H{(i+5)%17}','tier':'X','nonce':i},'expected':'ALLOW' if good else 'DENY'})
relation=BoundedDNFRelationPolicyInducerV1.synthesize('POST_ADMISSION_AUDIT_REL','LOGIC',rel_train,min_support=3,max_clauses=8,validation_cases=rel_val)
runtime=G2TypedRecurrentCapabilityGraphRuntimeV1(arch,router,scalar,relation,portfolio);adapter=G2CompositeTransferRepairAdapterV1(runtime)
route_keys=sorted(portfolio.get('routes_for_current_open_deficits',{}))
caps=[CAP_CONJ,CAP_REL,CAP_BUD,CAP_RES]
def task(cap,sid,i,amb=False):
 if cap==CAP_CONJ:
  good=i%2==0;return {'kind':'audit_scalar','descriptor':desc(cap,amb),'stream_id':sid,'payload':{'a':good,'b':True,'c':True,'nonce':10000+i}},('YES' if good else 'NO')
 if cap==CAP_REL:
  good=i%2==0;q=f'AQ{i}';o=q if good else f'AO{i}';return {'kind':'audit_rel','descriptor':desc(cap,amb),'stream_id':sid,'payload':{'q':q,'o':o,'g':f'AG{i%19}','og':f'AH{(i+7)%19}','tier':'X','nonce':i}},('ALLOW' if good else 'DENY')
 if cap==CAP_BUD:
  stages=[SearchStage(f'{sid}_s0',1,.15,1,True,.1,False),SearchStage(f'{sid}_s1',2,.35,1,True,.2,False),SearchStage(f'{sid}_s2',4,.55,1,True,.3,False)]
  exp=BudgetedStagePolicyV1.plan(.4,.7,3.5,stages).action
  return {'kind':'audit_budget','descriptor':desc(cap,amb),'stream_id':sid,'current_confidence':.4,'target_confidence':.7,'remaining_budget':3.5,'stages':[asdict(s) for s in stages]},exp
 key=route_keys[i%len(route_keys)];arr=portfolio['routes_for_current_open_deficits'][key];exp=arr[0]['resource_id'] if arr else None
 return {'kind':'audit_resource','descriptor':desc(cap,amb),'stream_id':sid,'route_key':key,'payload':{}},exp

explicit=amb=0;prepared=[]
for i in range(128):
 cap=caps[i%4];sid=f'AUD{i}';t,e=task(cap,sid,i,False);o=adapter.run(t);explicit+=o['selected_capability']==cap and o['result']==e
 f,e2=task(cap,sid,1000+i,True);prepared.append((cap,f,e2))
random.Random(seed+3).shuffle(prepared)
for cap,t,e in prepared:
 o=adapter.run(t);amb+=o['selected_capability']==cap and o['result']==e
abl=0
for i in range(96):
 cap=caps[(i+1)%4];sid=f'AB{i}';p,_=task(cap,sid,2000+i,False);adapter.run(p);f,_=task(cap,sid,3000+i,True)
 try:o=adapter.run(f,ablated_context=True);abl+=o['selected_capability']==cap
 except Exception:pass
canary={'explicit_accuracy':explicit/128,'ambiguous_accuracy':amb/128,'ablated_context_accuracy':abl/96,'causal_drop':amb/128-abl/96}

checks={
 'guard_pass':guard.returncode==0 and guard_json.get('status')=='PASS_CANONICAL_INVARIANT_GUARD_V1',
 'canonical_component_digest':cc.get('canonical_component_digest')==cdig(cc,'canonical_component_digest'),
 'canonical_component_active':cc.get('status')=='CANONICAL_ACTIVE',
 'component_active_head':COMP in head.get('active_capabilities',[]),
 'component_active_plane':COMP in plane.get('active_components',[]),
 'runtime_source_active':cc.get('runtime_source') in core.get('active_runtime_sources',[]),
 'runtime_source_hash_exact':cc.get('runtime_sha256')==fsha(SRC)==rim.get('sources',{}).get(cc.get('runtime_source')),
 'runtime_manifest_digest_exact':rim.get('manifest_digest')==h(rim.get('sources',{}))==head.get('unified_core',{}).get('runtime_integrity_manifest_digest'),
 'architecture_family_unchanged':head.get('architecture_family')==cc.get('architecture_family')=='TYPED_RECURRENT_CAPABILITY_GRAPH',
 'admission_receipt_pass':admit.get('status')=='PASS_COMPOSITE_EXECUTABLE_SUCCESSOR_CANONICAL_ADMISSION_V1',
 'admission_event_pass':bool(last_admit and last_admit.get('status')=='PASS_CANONICAL'),
 'prior_failure_reconciled':bool(prior_detail and 'FRESH_V3_CONSUMED=True' in prior_detail.get('effect','')),
 'stability_fixed':stability.get('state')=='STABILITY_SUPPORTED',
 'restart_canary_explicit':canary['explicit_accuracy']>=.99,
 'restart_canary_ambiguous':canary['ambiguous_accuracy']>=.99,
 'restart_canary_causal_drop':canary['causal_drop']>=.50,
 'g3_not_started':head.get('g3_genesis_performed') is False,
}
passed=all(checks.values())
next_cap='KERNEL_G2_COMPOSITE_CANONICAL_BURNIN_V1' if passed else 'KERNEL_G2_COMPOSITE_CANONICAL_POST_ADMISSION_REPAIR_V1'
report={'schema':'yado.g2.composite_canonical_post_admission_audit.receipt.v1','status':'PASS_G2_COMPOSITE_CANONICAL_POST_ADMISSION_AUDIT_V1' if passed else 'WITHHOLD_G2_COMPOSITE_CANONICAL_POST_ADMISSION_AUDIT_V1',
 'generation':ledger['current_head'],'canonical_head_digest':head['canonical_head_digest'],'canonical_component_digest':cc['canonical_component_digest'],'canary':canary,'checks':checks,
 'canonical_mutation':False,'canonical_mechanism_mutation':False,'architecture_mutation':False,'g3_genesis_performed':False,'next_required_capability':next_cap,
 'semantic_boundary':'POST-ADMISSION AUDIT OF THE CANONICAL G2 COMPOSITE EXECUTION ADAPTER INCLUDING RESTART CANARY, MANIFEST/PLANE BINDING, CAUSAL CONTEXT ABLATION, AND PRIOR FAILURE RECONCILIATION.'}
report['receipt_sha256']=h(report);write(OUT,report)
run_id=str(os.getenv('GITHUB_RUN_ID') or 'LOCAL')
e={'index':len(ledger['events']),'event_id':f"E{len(ledger['events'])+1:04d}_G2_COMPOSITE_CANONICAL_POST_ADMISSION_AUDIT_V1",'event_type':'G2_COMPOSITE_CANONICAL_POST_ADMISSION_AUDIT',
 'status':'PASS' if passed else 'WITHHOLD','generation':ledger['current_head'],'deficit':front,
 'effect':f"AUDIT={'PASS' if passed else 'WITHHOLD'}; GUARD={checks['guard_pass']}; CANARY_EXPLICIT={canary['explicit_accuracy']:.6f}; CANARY_AMBIG={canary['ambiguous_accuracy']:.6f}; CAUSAL_DROP={canary['causal_drop']:.6f}; G3=False; NEXT={next_cap}",
 'source_path':f'receipts/yado-g2-composite-canonical-post-admission-audit-v1-run-{run_id}.json','source_digest':report['receipt_sha256'],'run_id':run_id,'parent_event_hash':ledger['tail_event_hash'],
 'canonical_mutation':False,'canonical_mechanism_mutation':False,'architecture_mutation':False,'promotion_applied':False,'generation_transition':False}
e['event_hash']=event_hash(e);ledger['events'].append(e);ledger['event_count']=len(ledger['events']);ledger['tail_event_hash']=e['event_hash'];ledger['open_deficits']=[next_cap];ledger['ledger_digest']=h({k:v for k,v in ledger.items() if k!='ledger_digest'});validate_ledger_v2(ledger);write(LEDGER,ledger)
# Observational audit changes frontier only; synchronize head/core/provenance without changing mechanism.
prev=head['canonical_head_digest'];prov['current_g2_binding']['frontier']=next_cap;prov['current_g2_binding']['current_execution_label']='G2_COMPOSITE_CANONICAL_BURNIN_PENDING' if passed else 'G2_COMPOSITE_POST_ADMISSION_REPAIR_PENDING';prov['registry_digest']=cdig(prov,'registry_digest');write(PROV,prov)
core['algorithm_provenance_registry_digest']=prov['registry_digest'];core['current_frontier']=next_cap;core['frontier_source']='architecture/evolution-ledger.json:open_deficits';core['core_digest']=cdig(core,'core_digest');write(CORE,core)
head['algorithm_provenance_registry']['registry_digest']=prov['registry_digest'];head['algorithm_provenance_registry']['current_execution_label']=prov['current_g2_binding']['current_execution_label'];head['unified_core']['algorithm_provenance_registry_digest']=prov['registry_digest'];head['unified_core']['core_digest']=core['core_digest'];head['current_frontier']=next_cap;head['frontier_source']='architecture/evolution-ledger.json:open_deficits';head['canonical_head_digest']=cdig(head,'canonical_head_digest');write(HEAD,head)
# The audit event is observational but head digest changed because frontier advanced; patch ledger current head and event digest fields causally by appending a sync event rather than rewriting audit evidence.
ledger=load(LEDGER);ledger['current_head_digest']=head['canonical_head_digest']
sync={'index':len(ledger['events']),'event_id':f"E{len(ledger['events'])+1:04d}_G2_COMPOSITE_POST_AUDIT_FRONTIER_SYNC_V1",'event_type':'G2_FRONTIER_CANONICAL_SYNC','status':'PASS',
 'generation':ledger['current_head'],'deficit':'G2_FRONTIER_SYNC_AFTER_COMPOSITE_AUDIT','effect':f"FRONTIER={next_cap}; NEXT={next_cap}",
 'source_path':f'receipts/yado-g2-composite-canonical-post-admission-audit-v1-run-{run_id}.json','source_digest':report['receipt_sha256'],'run_id':run_id,'parent_event_hash':ledger['tail_event_hash'],
 'canonical_mutation':True,'canonical_mechanism_mutation':False,'architecture_mutation':False,'promotion_applied':False,'generation_transition':False,
 'previous_head_digest':prev,'new_head_digest':head['canonical_head_digest']}
sync['event_hash']=event_hash(sync);ledger['events'].append(sync);ledger['event_count']=len(ledger['events']);ledger['tail_event_hash']=sync['event_hash'];ledger['ledger_digest']=h({k:v for k,v in ledger.items() if k!='ledger_digest'});validate_ledger_v2(ledger);write(LEDGER,ledger)
ctx=UnifiedContextKernel().snapshot()
if ctx['current_frontier']!=next_cap:raise RuntimeError('POST_AUDIT_CONTEXT_INCONSISTENT')
post=subprocess.run([sys.executable,str(GUARD)],cwd=REPO,capture_output=True,text=True,timeout=60)
if post.returncode!=0:raise RuntimeError('POST_AUDIT_GUARD_FAILED:'+post.stdout[-4000:]+post.stderr[-1000:])
print(json.dumps({'status':report['status'],'canary':canary,'checks':checks,'next_required_capability':next_cap},indent=2,sort_keys=True))
