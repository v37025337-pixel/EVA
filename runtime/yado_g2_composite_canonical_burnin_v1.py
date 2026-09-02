from __future__ import annotations
from pathlib import Path
from dataclasses import asdict
import copy,hashlib,json,os,random,subprocess,sys,time

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
CANON=REPO/'canonical/yado-g2-composite-executable-successor-v1.json';OUT=ROOT/'yado_g2_composite_canonical_burnin_v1_receipt.json';GUARD=ROOT/'yado_canonical_invariant_guard_v1.py'
CAP_CONJ='ALG-CONJUNCTIVE-RULE-INDUCER-V1';CAP_REL='ALG-BOUNDED-DNF-RELATION-POLICY-INDUCER-V1';CAP_BUD='ALG-BUDGETED-STAGE-POLICY-V1';CAP_RES='RESOURCE-PORTFOLIO-V1';COMP='ALG-G2-COMPOSITE-TRANSFER-REPAIR-ADAPTER-V1'
def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def h(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def write(p,o):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(o,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')
def cdig(o,field):
 x=copy.deepcopy(o);x.pop(field,None);return h(x)
head,core,arch,ledger,prov,portfolio,cc=map(load,[HEAD,CORE,ARCH,LEDGER,PROV,PORT,CANON]);validate_ledger_v2(ledger)
front='KERNEL_G2_COMPOSITE_CANONICAL_BURNIN_V1'
if ledger.get('open_deficits')!=[front]:raise RuntimeError('UNEXPECTED_FRONTIER')
if cc.get('status')!='CANONICAL_ACTIVE' or COMP not in head.get('active_capabilities',[]):raise RuntimeError('COMPOSITE_NOT_CANONICAL')
if head.get('g3_genesis_performed') is not False:raise RuntimeError('G3_ALREADY_STARTED')
route_keys=sorted(portfolio.get('routes_for_current_open_deficits',{}));caps=[CAP_CONJ,CAP_REL,CAP_BUD,CAP_RES]

def desc(cap,amb=False,noise=0):
 d={'budget_limited':False,'quota_limited':False,'external_evidence_needed':False,'relation_needed':False,'disjunction_needed':False,'context_ambiguous':amb,'burn_noise':noise}
 if not amb:
  if cap==CAP_BUD:d['quota_limited']=True
  elif cap==CAP_RES:d['external_evidence_needed']=True
  elif cap==CAP_REL:d['disjunction_needed']=True
 return d
def build(round_no,seed):
 def rcases(n,s):
  r=random.Random(s);return [{'input':desc(caps[i%4],False,r.randrange(10**10)),'expected':caps[i%4]} for i in range(n)]
 router=BoundedCapabilityRouterLearnerV1.synthesize(rcases(900,seed+1),rcases(360,seed+2),CAP_CONJ,min_support=6)
 sc=[]
 for i in range(700):
  good=i%2==0;x={'integrity':good,'evidence':True,'rollback':True,'n':i};sc.append({'input':x,'expected':'GO' if good else 'HOLD'})
 scalar=ConjunctiveRuleInducerV1.synthesize(f'BURN_SC_{round_no}','LOGIC',sc,min_support=3,max_rules=8)
 tr=[];va=[]
 for arr,n,p in ((tr,760,'T'),(va,300,'V')):
  for i in range(n):
   good=i%2==0;q=f'{p}Q{round_no}_{i}';o=q if good else f'{p}O{round_no}_{i}'
   arr.append({'input':{'q':q,'o':o,'g':f'{p}G{i%29}','og':f'{p}H{(i+7)%29}','tier':'X','nonce':i},'expected':'ALLOW' if good else 'DENY'})
 rel=BoundedDNFRelationPolicyInducerV1.synthesize(f'BURN_REL_{round_no}','LOGIC',tr,min_support=3,max_clauses=8,validation_cases=va)
 return G2TypedRecurrentCapabilityGraphRuntimeV1(arch,router,scalar,rel,portfolio)

def task(cap,sid,i,seed,amb=False):
 r=random.Random(seed+i*31+11)
 if cap==CAP_CONJ:
  good=i%2==0;return {'kind':'burn_scalar','descriptor':desc(cap,amb,r.randrange(10**11)),'stream_id':sid,'payload':{'integrity':good,'evidence':True,'rollback':True,'n':100000+i}},('GO' if good else 'HOLD')
 if cap==CAP_REL:
  good=i%2==0;q=f'BQ{seed}_{i}';o=q if good else f'BO{seed}_{i}';return {'kind':'burn_rel','descriptor':desc(cap,amb,r.randrange(10**11)),'stream_id':sid,'payload':{'q':q,'o':o,'g':f'BG{i%31}','og':f'BH{(i+9)%31}','tier':'X','nonce':i}},('ALLOW' if good else 'DENY')
 if cap==CAP_BUD:
  costs=sorted([r.uniform(.2,1.2),r.uniform(1.3,2.7),r.uniform(2.8,5.5),r.uniform(5.6,11)])
  gains=sorted([r.uniform(.04,.16),r.uniform(.14,.29),r.uniform(.26,.47),r.uniform(.45,.71)])
  stages=[SearchStage(f'{sid}_{i}_{j}',costs[j],gains[j],1+r.randrange(3),True,r.uniform(.05,2.0),False) for j in range(4)]
  cur=r.uniform(.2,.55);target=r.uniform(max(.69,cur+.1),.95);budget=r.uniform(1.8,9.5);exp=BudgetedStagePolicyV1.plan(cur,target,budget,stages).action
  return {'kind':'burn_budget','descriptor':desc(cap,amb,r.randrange(10**11)),'stream_id':sid,'current_confidence':cur,'target_confidence':target,'remaining_budget':budget,'stages':[asdict(s) for s in stages]},exp
 key=route_keys[(i*7+round(seed)%5)%len(route_keys)];arr=portfolio['routes_for_current_open_deficits'][key];exp=arr[0]['resource_id'] if arr else None
 return {'kind':'burn_resource','descriptor':desc(cap,amb,r.randrange(10**11)),'stream_id':sid,'route_key':key,'payload':{}},exp
def round(x):return int(x)%997

rounds=[]
for rn in range(1,4):
 seed=2609026000+rn*1237;runtime=build(rn,seed);adapter=G2CompositeTransferRepairAdapterV1(runtime)
 explicit=0;prepared=[]
 for i in range(600):
  cap=caps[(i+rn)%4];sid=f'BR{rn}_{i}';t,e=task(cap,sid,100000+i,seed,False);o=adapter.run(t);explicit+=o['selected_capability']==cap and o['result']==e
  f,e2=task(cap,sid,200000+i,seed+1,True);prepared.append((cap,f,e2))
 random.Random(seed+2).shuffle(prepared);amb=0
 for cap,t,e in prepared:
  o=adapter.run(t);amb+=o['selected_capability']==cap and o['result']==e
 # Long mixed sequential stress.
 seq=0;start=time.perf_counter()
 for i in range(2200):
  cap=caps[(i*3+rn)%4];sid=f'SEQ{rn}_{i%900}';t,e=task(cap,sid,300000+i,seed+3,False);o=adapter.run(t);seq+=o['selected_capability']==cap and o['result']==e
 elapsed=time.perf_counter()-start
 # Causal ablation.
 abl=0
 for i in range(240):
  cap=caps[(i+2)%4];sid=f'AB{rn}_{i}';p,_=task(cap,sid,400000+i,seed+4,False);adapter.run(p);f,_=task(cap,sid,500000+i,seed+5,True)
  try:o=adapter.run(f,ablated_context=True);abl+=o['selected_capability']==cap
  except Exception:pass
 # LRU overflow.
 lru=[]
 for i in range(1250):
  cap=caps[i%4];sid=f'LR{rn}_{i}';t,_=task(cap,sid,600000+i,seed+6,False);adapter.run(t);lru.append((sid,cap))
 recent=lru[-1024:];lru_ok=0
 for i,(sid,cap) in enumerate(recent):
  t,e=task(cap,sid,700000+i,seed+7,True);o=adapter.run(t);lru_ok+=o['selected_capability']==cap and o['result']==e
 # Budget fault sweep.
 bud=viol=0
 for i in range(320):
  t,e=task(CAP_BUD,f'BF{rn}_{i}',800000+i,seed+8,False);o=adapter.run(t);bud+=o['result']==e
  if o['result'] not in ('STOP','WITHHOLD'):
   row=next((s for s in t['stages'] if s['stage_id']==o['result']),None)
   if row and float(row['cost'])>float(t['remaining_budget'])+1e-12:viol+=1
 metrics={'explicit_accuracy':explicit/600,'ambiguous_accuracy':amb/600,'sequential_accuracy':seq/2200,'ops_per_second':2200/max(elapsed,1e-9),
          'ablated_context_accuracy':abl/240,'causal_drop':amb/600-abl/240,'lru_recent_accuracy':lru_ok/1024,'budget_accuracy':bud/320,'budget_violations':viol}
 passed=metrics['explicit_accuracy']>=.99 and metrics['ambiguous_accuracy']>=.99 and metrics['sequential_accuracy']>=.99 and metrics['causal_drop']>=.50 and metrics['lru_recent_accuracy']>=.99 and metrics['budget_accuracy']>=.99 and viol==0
 rounds.append({'round':rn,'seed':seed,'status':'PASS' if passed else 'WITHHOLD','metrics':metrics})
 print(json.dumps({'stage':'round','round':rn,'status':rounds[-1]['status'],'metrics':metrics},sort_keys=True),flush=True)

mins={k:min(x['metrics'][k] for x in rounds) for k in rounds[0]['metrics']};checks={'three_rounds_pass':all(x['status']=='PASS' for x in rounds),'min_explicit':mins['explicit_accuracy']>=.99,'min_ambiguous':mins['ambiguous_accuracy']>=.99,
 'min_sequential':mins['sequential_accuracy']>=.99,'min_causal_drop':mins['causal_drop']>=.50,'min_lru':mins['lru_recent_accuracy']>=.99,'min_budget':mins['budget_accuracy']>=.99,
 'budget_violations_zero':max(x['metrics']['budget_violations'] for x in rounds)==0,'canonical_component_still_active':cc.get('status')=='CANONICAL_ACTIVE' and COMP in head.get('active_capabilities',[]),
 'architecture_unchanged':head.get('architecture_family')=='TYPED_RECURRENT_CAPABILITY_GRAPH','g3_not_started':head.get('g3_genesis_performed') is False}
passed=all(checks.values());next_cap='KERNEL_G2_COMPOSITE_CANONICAL_ARCHITECTURAL_CEILING_REASSESSMENT_V1' if passed else 'KERNEL_G2_COMPOSITE_CANONICAL_BURNIN_REPAIR_V1'
prev=head['canonical_head_digest'];prov['current_g2_binding']['frontier']=next_cap;prov['current_g2_binding']['current_execution_label']='G2_COMPOSITE_CANONICAL_BURNIN_PASS' if passed else 'G2_COMPOSITE_CANONICAL_BURNIN_REPAIR_PENDING';prov['registry_digest']=cdig(prov,'registry_digest');write(PROV,prov)
core['algorithm_provenance_registry_digest']=prov['registry_digest'];core['current_frontier']=next_cap;core['frontier_source']='architecture/evolution-ledger.json:open_deficits';core['core_digest']=cdig(core,'core_digest');write(CORE,core)
head['algorithm_provenance_registry']['registry_digest']=prov['registry_digest'];head['algorithm_provenance_registry']['current_execution_label']=prov['current_g2_binding']['current_execution_label'];head['unified_core']['algorithm_provenance_registry_digest']=prov['registry_digest'];head['unified_core']['core_digest']=core['core_digest'];head['current_frontier']=next_cap;head['frontier_source']='architecture/evolution-ledger.json:open_deficits';head['canonical_head_digest']=cdig(head,'canonical_head_digest');write(HEAD,head)
ledger['current_head_digest']=head['canonical_head_digest'];ledger['open_deficits']=[next_cap]
report={'schema':'yado.g2.composite_canonical_burnin.receipt.v1','status':'PASS_G2_COMPOSITE_CANONICAL_BURNIN_V1' if passed else 'WITHHOLD_G2_COMPOSITE_CANONICAL_BURNIN_V1','generation':ledger['current_head'],'rounds':rounds,'min_metrics':mins,'checks':checks,
 'canonical_mutation':True,'canonical_mechanism_mutation':False,'architecture_mutation':False,'g3_genesis_performed':False,'next_required_capability':next_cap,
 'semantic_boundary':'THREE-ROUND CANONICAL BURN-IN OF THE ACTIVE G2 COMPOSITE EXECUTION ADAPTER WITH LONG MIXED SEQUENCES, LRU OVERFLOW, CONTEXT ABLATION, AND BUDGET SAFETY.'}
report['receipt_sha256']=h(report);write(OUT,report)
run_id=str(os.getenv('GITHUB_RUN_ID') or 'LOCAL')
e={'index':len(ledger['events']),'event_id':f"E{len(ledger['events'])+1:04d}_G2_COMPOSITE_CANONICAL_BURNIN_V1",'event_type':'G2_COMPOSITE_CANONICAL_BURNIN','status':'PASS_CANONICAL' if passed else 'WITHHOLD','generation':ledger['current_head'],'deficit':front,
 'effect':f"BURNIN={'PASS' if passed else 'WITHHOLD'}; ROUNDS=3; MIN_EXPLICIT={mins['explicit_accuracy']:.6f}; MIN_AMBIG={mins['ambiguous_accuracy']:.6f}; MIN_SEQ={mins['sequential_accuracy']:.6f}; MIN_DROP={mins['causal_drop']:.6f}; MIN_LRU={mins['lru_recent_accuracy']:.6f}; NEXT={next_cap}",
 'source_path':f'receipts/yado-g2-composite-canonical-burnin-v1-run-{run_id}.json','source_digest':report['receipt_sha256'],'run_id':run_id,'parent_event_hash':ledger['tail_event_hash'],'canonical_mutation':True,'canonical_mechanism_mutation':False,'architecture_mutation':False,
 'promotion_applied':False,'generation_transition':False,'previous_head_digest':prev,'new_head_digest':head['canonical_head_digest']}
e['event_hash']=event_hash(e);ledger['events'].append(e);ledger['event_count']=len(ledger['events']);ledger['tail_event_hash']=e['event_hash'];ledger['ledger_digest']=h({k:v for k,v in ledger.items() if k!='ledger_digest'});validate_ledger_v2(ledger);write(LEDGER,ledger)
ctx=UnifiedContextKernel().snapshot()
if ctx['current_frontier']!=next_cap:raise RuntimeError('POST_BURNIN_CONTEXT_INCONSISTENT')
post=subprocess.run([sys.executable,str(GUARD)],cwd=REPO,capture_output=True,text=True,timeout=60)
if post.returncode!=0:raise RuntimeError('POST_BURNIN_GUARD_FAILED:'+post.stdout[-4000:]+post.stderr[-1000:])
print(json.dumps({'status':report['status'],'min_metrics':mins,'checks':checks,'next_required_capability':next_cap},indent=2,sort_keys=True))
