from __future__ import annotations
from pathlib import Path
import copy,hashlib,json,os,subprocess,sys,time

ROOT=Path(__file__).resolve().parent;REPO=ROOT.parent;PKG=ROOT/'yado_rc8_v36'
sys.path[:0]=[str(ROOT),str(PKG)]

from yado_unified_core_v1 import UnifiedYADOCoreV1
from yado_raw_task_representation_candidate_v3 import RawTaskRepresentationRuntimeV3
from yado_bounded_capability_router_v1 import BoundedCapabilityRouterLearnerV1
from yado_evolution_ledger_v2 import validate_ledger_v2,event_hash
from yado_unified_context_kernel_v1 import UnifiedContextKernel

HEAD=REPO/'canonical/yado-main-head-g2.json'
CORE=REPO/'canonical/yado-unified-core-v1.json'
LEDGER=REPO/'architecture/evolution-ledger.json'
PROV=REPO/'canonical/yado-algorithm-provenance-registry-v1.json'
V4ART=REPO/'canonical/yado-raw-task-representation-v4.json'
V3ART=REPO/'canonical/yado-raw-task-representation-v3.json'
STRUCT=REPO/'resources/yado-raw-task-representation-v3-structural-fresh-holdout-v1.json'
V2AUD=REPO/'receipts/yado-g2-raw-representation-v2-post-admission-audit-v1-run-33670110185.json'
V4PREV=REPO/'resources/yado-raw-task-representation-v4-robustness-fresh-holdout-v2.json'
V4ADM=REPO/'resources/yado-raw-task-representation-v4-canonical-admission-fresh-v1.json'
BASE=REPO/'receipts/yado-g2-real-world-transfer-benchmark-v1-run-33363995201.json'
OUT=ROOT/'yado_g2_raw_representation_v4_canonical_burnin_v1_receipt.json'
GUARD=ROOT/'yado_canonical_invariant_guard_v1.py'

V4='ALG-G2-RAW-TASK-REPRESENTATION-V4'
C1='ALG-CONJUNCTIVE-RULE-INDUCER-V1';CR='ALG-BOUNDED-DNF-RELATION-POLICY-INDUCER-V1';CB='ALG-BUDGETED-STAGE-POLICY-V1';CE='RESOURCE-PORTFOLIO-V1'

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def h(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def write(p,o):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(o,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')
def cdig(o,field):x=copy.deepcopy(o);x.pop(field,None);return h(x)

head,core,ledger,prov,v4,v3,struct,v2aud,v4prev,v4adm,base=map(load,[HEAD,CORE,LEDGER,PROV,V4ART,V3ART,STRUCT,V2AUD,V4PREV,V4ADM,BASE])
validate_ledger_v2(ledger)
front='KERNEL_G2_RAW_REPRESENTATION_V4_CANONICAL_BURNIN_V1'
if ledger.get('open_deficits')!=[front]:raise RuntimeError('UNEXPECTED_FRONTIER:'+json.dumps(ledger.get('open_deficits')))
if v4.get('canonical_active') is not True or V4 not in head.get('active_capabilities',[]):raise RuntimeError('V4_NOT_CANONICAL_ACTIVE')
if head.get('g3_genesis_performed') is not False:raise RuntimeError('G3_ALREADY_STARTED')

router_rows=[]
for i,label in enumerate([C1,CR,CB,CE]*200):
    router_rows.append({'input':{'budget_limited':label==CB,'quota_limited':False,'external_evidence_needed':label==CE,'relation_needed':label==CR,'disjunction_needed':False,'noise':i},'expected':label})
router=BoundedCapabilityRouterLearnerV1.synthesize(router_rows,router_rows,C1,min_support=8)

base_cases=[]
for r in struct['rows']:base_cases.append((r['text'],r['expected'],'STRUCT'))
for r in v2aud['canary_rows']:base_cases.append((r['text'],r['expected'],'V2_AUDIT'))
for r in v4prev['rows']:base_cases.append((r['text'],r['expected'],'V4_PREV'))
# V4 admission rows store already wrapped text in "text"; still useful as canonical workload.
for r in v4adm['rows']:base_cases.append((r['text'],r['expected'],'V4_ADMISSION'))

def wrap(text,rn,i):
    m=(i+rn)%6
    if m==0:return f"[trace={rn}-{i%31}] {text} [complete]"
    if m==1:return f"<packet {i%23}> {text} <done>"
    if m==2:return f"{{session {i%19}}} {text} {{closed}}"
    if m==3:return f"(record {i%17}) {text} (end)"
    if m==4:return f"Memo {i%13}: {text} [tail={900+i}]"
    t=text.upper() if i%2==0 else text.lower()
    return f"Administrative note. {t} End note."

rounds=[]
for rn in (1,2,3):
    u=UnifiedYADOCoreV1(REPO)
    direct_ok=wrap_ok=0
    for i,(text,expected,src) in enumerate(base_cases):
        direct_ok+=u.route_raw_task(text,router)['selected_capability']==expected
        wt=wrap(text,rn,i);wrap_ok+=u.route_raw_task(wt,router)['selected_capability']==expected
    direct=direct_ok/len(base_cases);wrapped=wrap_ok/len(base_cases)

    seq_n=2400;seq_ok=0;start=time.perf_counter()
    for i in range(seq_n):
        text,expected,_=base_cases[(i*29+rn)%len(base_cases)]
        wt=wrap(text,rn,i)
        seq_ok+=u.route_raw_task(wt,router)['selected_capability']==expected
    elapsed=time.perf_counter()-start
    seq=seq_ok/seq_n

    u2=UnifiedYADOCoreV1(REPO);same=0;sample=base_cases[:min(64,len(base_cases))]
    for i,(text,_,_) in enumerate(sample):
        wt=wrap(text,rn,i)
        same+=u.route_raw_task(wt,router)['selected_capability']==u2.route_raw_task(wt,router)['selected_capability']
    reload_eq=same/len(sample)

    metrics={'direct_accuracy':direct,'wrapped_accuracy':wrapped,'sequential_accuracy':seq,'reload_equivalence':reload_eq,'ops_per_second':seq_n/max(elapsed,1e-9)}
    passed=direct>=.97 and wrapped>=.95 and seq>=.95 and reload_eq==1.0
    rounds.append({'round':rn,'status':'PASS' if passed else 'WITHHOLD','metrics':metrics})
    print(json.dumps({'stage':'burnin_round','round':rn,'status':rounds[-1]['status'],'metrics':metrics},sort_keys=True),flush=True)

rollback=RawTaskRepresentationRuntimeV3(v3)
base_rows=[(r['raw_text'],r['expected']) for r in base['raw_unstructured']['rows']]
rollback_acc=sum(rollback.predict_capability(x)==y for x,y in base_rows)/len(base_rows)

mins={k:min(r['metrics'][k] for r in rounds) for k in rounds[0]['metrics']}
checks={
 'three_rounds_pass':all(r['status']=='PASS' for r in rounds),
 'min_direct_accuracy':mins['direct_accuracy']>=.97,
 'min_wrapped_accuracy':mins['wrapped_accuracy']>=.95,
 'min_sequential_accuracy':mins['sequential_accuracy']>=.95,
 'reload_equivalence_exact':mins['reload_equivalence']==1.0,
 'rollback_v3_accuracy':rollback_acc>=.95,
 'v4_still_canonical':v4.get('canonical_active') is True and V4 in head.get('active_capabilities',[]),
 'architecture_family_unchanged':head.get('architecture_family')=='TYPED_RECURRENT_CAPABILITY_GRAPH',
 'g3_not_started':head.get('g3_genesis_performed') is False,
}
passed=all(checks.values())
next_cap='KERNEL_G2_POST_RAW_V4_ARCHITECTURAL_CEILING_REASSESSMENT_V3' if passed else 'KERNEL_G2_RAW_REPRESENTATION_V4_CANONICAL_BURNIN_REPAIR_V1'

prev_head=head['canonical_head_digest']
prov['current_g2_binding'].update({'current_execution_label':'G2_POST_RAW_V4_CEILING_REASSESSMENT_PENDING' if passed else 'G2_RAW_V4_BURNIN_REPAIR_PENDING',
 'frontier':next_cap,'frontier_native_method':'UnifiedYADOCoreV1.route_raw_task','frontier_native_owner':'UnifiedYADOCoreV1','raw_representation_active_component':V4})
prov['registry_digest']=cdig(prov,'registry_digest');write(PROV,prov)
core['algorithm_provenance_registry_digest']=prov['registry_digest'];core['current_frontier']=next_cap;core['frontier_source']='architecture/evolution-ledger.json:open_deficits'
core['raw_representation_v4_canonical_burnin_v1']={'status':'PASS' if passed else 'WITHHOLD','rounds':rounds,'min_metrics':mins,'rollback_v3_accuracy':rollback_acc,'checks':checks}
core['core_digest']=cdig(core,'core_digest');write(CORE,core)
head['algorithm_provenance_registry']['registry_digest']=prov['registry_digest'];head['algorithm_provenance_registry']['current_execution_label']=prov['current_g2_binding']['current_execution_label']
head['unified_core']['algorithm_provenance_registry_digest']=prov['registry_digest'];head['unified_core']['core_digest']=core['core_digest']
head['raw_representation_v4_canonical_burnin_v1']={'status':'PASS' if passed else 'WITHHOLD','min_metrics':mins,'rollback_v3_accuracy':rollback_acc}
head['current_frontier']=next_cap;head['frontier_source']='architecture/evolution-ledger.json:open_deficits';head['canonical_head_digest']=cdig(head,'canonical_head_digest');write(HEAD,head)
ledger['current_head_digest']=head['canonical_head_digest'];ledger['open_deficits']=[next_cap]

run_id=str(os.getenv('GITHUB_RUN_ID') or 'LOCAL')
receipt={'schema':'yado.g2.raw_representation_v4_canonical_burnin.receipt.v1',
 'status':'PASS_G2_RAW_REPRESENTATION_V4_CANONICAL_BURNIN_V1' if passed else 'WITHHOLD_G2_RAW_REPRESENTATION_V4_CANONICAL_BURNIN_V1',
 'rounds':rounds,'min_metrics':mins,'rollback_v3_accuracy':rollback_acc,'checks':checks,
 'previous_head_digest':prev_head,'new_head_digest':head['canonical_head_digest'],
 'canonical_mutation':True,'canonical_mechanism_mutation':False,'architecture_mutation':False,'g3_genesis_performed':False,
 'next_required_capability':next_cap,
 'semantic_boundary':'THREE-ROUND CANONICAL BURN-IN OF ACTIVE RAW REPRESENTATION V4 UNDER GENERIC WRAPPER VARIANTS, LONG SEQUENTIAL ROUTING, RELOAD EQUIVALENCE, AND V3 ROLLBACK. NO RETRAINING.'
}
receipt['receipt_sha256']=h(receipt);write(OUT,receipt)
e={'index':len(ledger['events']),'event_id':f"E{len(ledger['events'])+1:04d}_G2_RAW_REPRESENTATION_V4_CANONICAL_BURNIN_V1",
 'event_type':'G2_RAW_REPRESENTATION_V4_CANONICAL_BURNIN','status':'PASS_CANONICAL' if passed else 'WITHHOLD','generation':ledger['current_head'],'deficit':front,
 'effect':f"BURNIN={'PASS' if passed else 'WITHHOLD'}; ROUNDS=3; MIN_DIRECT={mins['direct_accuracy']:.6f}; MIN_WRAP={mins['wrapped_accuracy']:.6f}; MIN_SEQ={mins['sequential_accuracy']:.6f}; RELOAD={mins['reload_equivalence']:.6f}; ROLLBACK_V3={rollback_acc:.6f}; NEXT={next_cap}",
 'source_path':f'receipts/yado-g2-raw-representation-v4-canonical-burnin-v1-run-{run_id}.json','source_digest':receipt['receipt_sha256'],'run_id':run_id,
 'parent_event_hash':ledger['tail_event_hash'],'canonical_mutation':True,'canonical_mechanism_mutation':False,'architecture_mutation':False,'promotion_applied':False,'generation_transition':False,
 'previous_head_digest':prev_head,'new_head_digest':head['canonical_head_digest']}
e['event_hash']=event_hash(e);ledger['events'].append(e);ledger['event_count']=len(ledger['events']);ledger['tail_event_hash']=e['event_hash'];ledger['ledger_digest']=h({k:v for k,v in ledger.items() if k!='ledger_digest'})
validate_ledger_v2(ledger);write(LEDGER,ledger)
ctx=UnifiedContextKernel().snapshot()
if ctx['current_frontier']!=next_cap:raise RuntimeError('POST_V4_BURNIN_CONTEXT_INCONSISTENT')
post=subprocess.run([sys.executable,str(GUARD)],cwd=REPO,capture_output=True,text=True,timeout=60)
if post.returncode!=0:raise RuntimeError('POST_V4_BURNIN_GUARD_FAILED:'+post.stdout[-5000:]+post.stderr[-1000:])
print(json.dumps({'status':receipt['status'],'min_metrics':mins,'rollback_v3_accuracy':rollback_acc,'checks':checks,'next_required_capability':next_cap},indent=2,sort_keys=True))
