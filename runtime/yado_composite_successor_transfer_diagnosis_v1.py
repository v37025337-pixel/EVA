from __future__ import annotations
from pathlib import Path
from dataclasses import asdict
import hashlib,json,os,random,sys
ROOT=Path(__file__).resolve().parent;REPO=ROOT.parent;PKG=ROOT/'yado_rc8_v36'
sys.path[:0]=[str(ROOT),str(PKG)]
from yado_conjunctive_rule_inducer_v1 import ConjunctiveRuleInducerV1,program_acc,canonical_program
from yado_bounded_dnf_relation_policy_inducer_v1 import BoundedDNFRelationPolicyInducerV1,program_acc as rel_acc
from yado_budgeted_stage_policy_v1 import BudgetedStagePolicyV1,SearchStage
from yado_bounded_capability_router_v1 import BoundedCapabilityRouterLearnerV1,router_acc
from yado_g2_typed_recurrent_capability_graph_runtime_v1 import G2TypedRecurrentCapabilityGraphRuntimeV1
from yado_evolution_ledger_v2 import validate_ledger_v2,event_hash

HEAD=REPO/'canonical/yado-main-head-g2.json';ARCH=REPO/'canonical/yado-g2-architecture-v1.json'
LEDGER=REPO/'architecture/evolution-ledger.json';PORT=REPO/'resources/yado-unified-external-resource-portfolio-v1.json'
SRC=REPO/'resources/yado-composite-successor-fresh-transfer-v1.json'
OUT=ROOT/'yado_composite_successor_transfer_diagnosis_v1_receipt.json'
CAP_CONJ='ALG-CONJUNCTIVE-RULE-INDUCER-V1';CAP_REL='ALG-BOUNDED-DNF-RELATION-POLICY-INDUCER-V1';CAP_BUD='ALG-BUDGETED-STAGE-POLICY-V1';CAP_RES='RESOURCE-PORTFOLIO-V1'
def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def h(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def load(p):return json.loads(p.read_text())
ledger,head,arch,portfolio,src=map(load,[LEDGER,HEAD,ARCH,PORT,SRC]);validate_ledger_v2(ledger)
front='KERNEL_SELECTED_ARCHITECTURE_COMPOSITE_EXECUTABLE_SUCCESSOR_TRANSFER_REPAIR_V1'
if ledger.get('open_deficits')!=[front]:raise RuntimeError('UNEXPECTED_FRONTIER')
seed=2609021701;blind_seed=90217001

def desc(cap,amb=False,noise=0):
 d={'budget_limited':False,'quota_limited':False,'external_evidence_needed':False,'relation_needed':False,'disjunction_needed':False,'context_ambiguous':amb,'fresh_descriptor_noise':noise}
 if not amb:
  if cap==CAP_BUD:d['quota_limited']=True
  elif cap==CAP_RES:d['external_evidence_needed']=True
  elif cap==CAP_REL:d['disjunction_needed']=True
 return d
def router_cases(n,s):
 r=random.Random(s);caps=[CAP_CONJ,CAP_REL,CAP_BUD,CAP_RES];out=[]
 for i in range(n):
  cap=caps[(i+r.randrange(4))%4];out.append({'input':desc(cap,False,r.randint(-10**8,10**8)),'expected':cap})
 return out
router_train=router_cases(1200,seed+1);router_val=router_cases(480,seed+2)
router=BoundedCapabilityRouterLearnerV1.synthesize(router_train,router_val,CAP_CONJ,min_support=6)

def scalar_cases(n,s):
 r=random.Random(s);out=[]
 for i in range(n):
  good=i%2==0
  if good:x={'attested_integrity':True,'novel_evidence':True,'revert_path_ready':True,'fresh_scalar_nonce':r.randrange(10**12)}
  else:
   vals=[True,True,True];vals[i%3]=False;x={'attested_integrity':vals[0],'novel_evidence':vals[1],'revert_path_ready':vals[2],'fresh_scalar_nonce':r.randrange(10**12)}
  out.append({'input':x,'expected':'DEPLOY' if good else 'DEFER'})
 r.shuffle(out);return out
scalar_train=scalar_cases(840,seed+11);scalar=ConjunctiveRuleInducerV1.synthesize('D','LOGIC',scalar_train,min_support=3,max_rules=12)
scalar_blind=scalar_cases(600,blind_seed+101)

def rel_cases(n,s,prefix):
 r=random.Random(s);out=[]
 for i in range(n):
  good=i%2==0;subject=f'{prefix}_SUBJ_{i}';owner=subject if good else f'{prefix}_OWNER_{i}'
  x={'principal_token':subject,'custodian_token':owner,'cohort_token':f'{prefix}_C_{i%29}','asset_cohort_token':f'{prefix}_A_{(i+7)%29}',
     'access_tier':r.choice(['EDGE','CORE','AUX']),'attested':bool(r.getrandbits(1)),'fresh_relation_nonce':r.randint(-10**9,10**9)}
  out.append({'input':x,'expected':'GRANT' if good else 'REJECT'})
 r.shuffle(out);return out
rel_train=rel_cases(900,seed+21,'TR');rel_val=rel_cases(360,seed+22,'VA')
relation=BoundedDNFRelationPolicyInducerV1.synthesize('DREL','LOGIC',rel_train,min_support=3,max_clauses=12,validation_cases=rel_val)
rel_blind=rel_cases(600,blind_seed+202,'BL')

# Direct budget serialization equivalence + runtime comparison.
budget_direct=budget_serial=budget_runtime=0;mismatches=[]
route_keys=sorted(portfolio.get('routes_for_current_open_deficits',{}))
runtime=G2TypedRecurrentCapabilityGraphRuntimeV1(arch,router,scalar,relation,portfolio)
for i in range(160):
 r=random.Random(blind_seed+303+i*17)
 costs=sorted([r.uniform(.25,1.6),r.uniform(1.7,3.9),r.uniform(4.0,7.8),r.uniform(7.9,15.0)])
 gains=sorted([r.uniform(.03,.14),r.uniform(.12,.28),r.uniform(.24,.44),r.uniform(.43,.68)])
 stages=[SearchStage(f'DX_{i}_{j}',costs[j],gains[j],1+r.randrange(3),True,r.uniform(.05,3),False) for j in range(4)]
 cur=r.uniform(.22,.58);target=r.uniform(max(.68,cur+.10),.94);budget=r.uniform(2,13)
 expected=BudgetedStagePolicyV1.plan(cur,target,budget,stages).action
 rows=[asdict(s) for s in stages]
 restored=[SearchStage(stage_id=s['stage_id'],cost=float(s['cost']),expected_gain=float(s['expected_gain']),quota_remaining=int(s['quota_remaining']),available=bool(s['available']),latency=float(s['latency']),attempted=bool(s['attempted'])) for s in rows]
 serial=BudgetedStagePolicyV1.plan(cur,target,budget,restored).action
 task={'kind':'diag_budget','descriptor':desc(CAP_BUD,False,i),'stream_id':f'DX_{i}','current_confidence':cur,'target_confidence':target,'remaining_budget':budget,'stages':rows}
 out=runtime.run(task)['result']
 budget_direct+=expected==serial;budget_serial+=serial==expected;budget_runtime+=out==expected
 if out!=expected and len(mismatches)<8:mismatches.append({'i':i,'expected':expected,'runtime':out,'serial':serial,'cur':cur,'target':target,'budget':budget,'stages':rows})

diag={
 'router_train_accuracy':router_acc(router,router_train),'router_validation_accuracy':router_acc(router,router_val),
 'scalar_train_accuracy':program_acc(scalar,scalar_train),'scalar_blind_accuracy':program_acc(scalar,scalar_blind),
 'scalar_program':canonical_program(scalar),
 'relation_train_accuracy':rel_acc(relation,rel_train),'relation_validation_accuracy':rel_acc(relation,rel_val),'relation_blind_accuracy':rel_acc(relation,rel_blind),
 'relation_program':relation.canonical(),
 'budget_serialization_equivalence':budget_serial/160,'budget_runtime_accuracy':budget_runtime/160,'budget_mismatches':mismatches
}
# Localize likely root causes from direct evidence.
roots=[]
if diag['scalar_blind_accuracy']<.99:roots.append('SCALAR_SYMBOLIC_TRANSFER')
if diag['relation_blind_accuracy']<.99:roots.append('RELATIONAL_SYMBOLIC_TRANSFER')
if diag['budget_serialization_equivalence']>=.99 and diag['budget_runtime_accuracy']<.99:roots.append('BUDGET_RUNTIME_INTERFACE')
elif diag['budget_serialization_equivalence']<.99:roots.append('BUDGET_SERIALIZATION')
if not roots:roots.append('FRESH_TRANSFER_HARNESS_EXPECTATION')
receipt={'schema':'yado.g2.composite_successor_transfer_diagnosis.receipt.v1','status':'PASS_TRANSFER_DIAGNOSIS_V1',
 'generation':ledger['current_head'],'frontier':front,'source_fresh_transfer_digest':src['dataset_digest'],'diagnosis':diag,'root_candidates':roots,
 'canonical_mutation':False,'architecture_mutation':False,'g3_genesis_performed':False,'next_required_capability':front}
receipt['receipt_sha256']=h(receipt);OUT.write_text(json.dumps(receipt,indent=2,sort_keys=True,default=str)+'\n')
run_id=str(os.getenv('GITHUB_RUN_ID') or 'LOCAL')
e={'index':len(ledger['events']),'event_id':f"E{len(ledger['events'])+1:04d}_G2_COMPOSITE_TRANSFER_DIAGNOSIS_V1",'event_type':'G2_TRANSFER_FAILURE_DIAGNOSIS','status':'PASS',
 'generation':ledger['current_head'],'deficit':front,'effect':f"ROOTS={'+'.join(roots)}; SCALAR={diag['scalar_blind_accuracy']:.6f}; REL={diag['relation_blind_accuracy']:.6f}; BUDGET_RUNTIME={diag['budget_runtime_accuracy']:.6f}; NEXT={front}",
 'source_path':f'receipts/yado-composite-successor-transfer-diagnosis-v1-run-{run_id}.json','source_digest':receipt['receipt_sha256'],'run_id':run_id,
 'parent_event_hash':ledger['tail_event_hash'],'canonical_mutation':False,'promotion_applied':False,'generation_transition':False}
e['event_hash']=event_hash(e);ledger['events'].append(e);ledger['event_count']=len(ledger['events']);ledger['tail_event_hash']=e['event_hash'];ledger['ledger_digest']=h({k:v for k,v in ledger.items() if k!='ledger_digest'})
validate_ledger_v2(ledger);LEDGER.write_text(json.dumps(ledger,indent=2,sort_keys=True)+'\n')
print(json.dumps({'status':receipt['status'],'root_candidates':roots,'diagnosis':{k:v for k,v in diag.items() if k not in ('scalar_program','relation_program','budget_mismatches')},'mismatches':mismatches},indent=2,sort_keys=True))
