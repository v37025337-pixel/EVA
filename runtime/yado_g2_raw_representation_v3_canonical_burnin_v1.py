from __future__ import annotations
from pathlib import Path
import copy,hashlib,json,os,subprocess,sys,time

ROOT=Path(__file__).resolve().parent;REPO=ROOT.parent;PKG=ROOT/'yado_rc8_v36'
sys.path[:0]=[str(ROOT),str(PKG)]

from yado_unified_core_v1 import UnifiedYADOCoreV1
from yado_raw_task_representation_candidate_v2 import RawTaskRepresentationRuntimeV2
from yado_bounded_capability_router_v1 import BoundedCapabilityRouterLearnerV1
from yado_evolution_ledger_v2 import validate_ledger_v2,event_hash
from yado_unified_context_kernel_v1 import UnifiedContextKernel

HEAD=REPO/'canonical/yado-main-head-g2.json'
CORE=REPO/'canonical/yado-unified-core-v1.json'
LEDGER=REPO/'architecture/evolution-ledger.json'
PROV=REPO/'canonical/yado-algorithm-provenance-registry-v1.json'
V3ART=REPO/'canonical/yado-raw-task-representation-v3.json'
V2ART=REPO/'canonical/yado-raw-task-representation-v2.json'
STRUCT=REPO/'resources/yado-raw-task-representation-v3-structural-fresh-holdout-v1.json'
V2AUD=REPO/'receipts/yado-g2-raw-representation-v2-post-admission-audit-v1-run-33670110185.json'
BASE=REPO/'receipts/yado-g2-real-world-transfer-benchmark-v1-run-33363995201.json'
OUT=ROOT/'yado_g2_raw_representation_v3_canonical_burnin_v1_receipt.json'
GUARD=ROOT/'yado_canonical_invariant_guard_v1.py'

V3='ALG-G2-RAW-TASK-REPRESENTATION-V3'
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

head,core,ledger,prov,v3,v2,struct,v2aud,base=map(load,[HEAD,CORE,LEDGER,PROV,V3ART,V2ART,STRUCT,V2AUD,BASE])
validate_ledger_v2(ledger)
front='KERNEL_G2_RAW_REPRESENTATION_V3_CANONICAL_BURNIN_V1'
if ledger.get('open_deficits')!=[front]:raise RuntimeError('UNEXPECTED_FRONTIER:'+json.dumps(ledger.get('open_deficits')))
if v3.get('canonical_active') is not True or V3 not in head.get('active_capabilities',[]):raise RuntimeError('V3_NOT_CANONICAL_ACTIVE')
if head.get('g3_genesis_performed') is not False:raise RuntimeError('G3_ALREADY_STARTED')

rows=[]
for i,label in enumerate([CAP_CONJ,CAP_REL,CAP_BUD,CAP_RES]*180):
    rows.append({'input':{'budget_limited':label==CAP_BUD,'quota_limited':False,'external_evidence_needed':label==CAP_RES,
                          'relation_needed':label==CAP_REL,'disjunction_needed':False,'noise':i},'expected':label})
router=BoundedCapabilityRouterLearnerV1.synthesize(rows,rows,CAP_CONJ,min_support=8)

base_cases=[{'text':r['text'],'expected':r['expected'],'source':'STRUCTURAL_HOLDOUT'} for r in struct['rows']]
base_cases += [{'text':r['text'],'expected':r['expected'],'source':'V2_FAILURE_CANARY'} for r in v2aud['canary_rows']]

def perturb(text,round_no,index):
    if round_no==1:
        prefix=f"Case metadata {index%17}: "
        suffix=f" [trace {1000+index}]"
        return prefix+text+suffix
    if round_no==2:
        t=text.upper() if index%2==0 else text.lower()
        return "Administrative note. "+t+" End note."
    # punctuation and whitespace perturbation only.
    t="  ".join(text.replace(";"," ; ").replace(","," , ").split())
    return f"Review item {index%23}. {t} [normal priority]"

def route(ucore,text):
    return ucore.route_raw_task(text,router)['selected_capability']

rounds=[]
for rn in (1,2,3):
    ucore=UnifiedYADOCoreV1(REPO)
    direct_ok=pert_ok=0
    direct_rows=[];pert_rows=[]
    for i,row in enumerate(base_cases):
        got=route(ucore,row['text']);ok=got==row['expected'];direct_ok+=ok
        direct_rows.append({'expected':row['expected'],'got':got,'correct':ok,'source':row['source']})
        pt=perturb(row['text'],rn,i);pg=route(ucore,pt);pok=pg==row['expected'];pert_ok+=pok
        pert_rows.append({'expected':row['expected'],'got':pg,'correct':pok,'source':row['source']})
    direct_acc=direct_ok/len(base_cases);pert_acc=pert_ok/len(base_cases)

    # Long deterministic repeated-routing stress; no model changes between calls.
    start=time.perf_counter();seq_ok=0;seq_n=1800
    for i in range(seq_n):
        row=base_cases[(i*17+rn)%len(base_cases)]
        pt=perturb(row['text'],rn,i%len(base_cases))
        seq_ok+=route(ucore,pt)==row['expected']
    elapsed=time.perf_counter()-start
    seq_acc=seq_ok/seq_n

    # Reload equivalence: a new unified core must give the same predictions.
    reloaded=UnifiedYADOCoreV1(REPO);reload_same=0
    sample=base_cases[:min(40,len(base_cases))]
    for i,row in enumerate(sample):
        t=perturb(row['text'],rn,i)
        reload_same+=route(ucore,t)==route(reloaded,t)
    reload_equivalence=reload_same/len(sample)

    metrics={'direct_accuracy':direct_acc,'perturbation_accuracy':pert_acc,'sequential_accuracy':seq_acc,
             'reload_equivalence':reload_equivalence,'ops_per_second':seq_n/max(elapsed,1e-9)}
    passed=direct_acc>=.97 and pert_acc>=.90 and seq_acc>=.90 and reload_equivalence==1.0
    rounds.append({'round':rn,'status':'PASS' if passed else 'WITHHOLD','metrics':metrics})
    print(json.dumps({'stage':'burnin_round','round':rn,'status':rounds[-1]['status'],'metrics':metrics},sort_keys=True),flush=True)

# V2 rollback remains operational throughout burn-in.
rollback=RawTaskRepresentationRuntimeV2(v2)
base_rows=[(r['raw_text'],r['expected']) for r in base['raw_unstructured']['rows']]
rollback_acc=sum(rollback.predict_capability(x)==y for x,y in base_rows)/len(base_rows)

mins={k:min(r['metrics'][k] for r in rounds) for k in rounds[0]['metrics']}
checks={
 'three_rounds_pass':all(r['status']=='PASS' for r in rounds),
 'min_direct_accuracy':mins['direct_accuracy']>=.97,
 'min_perturbation_accuracy':mins['perturbation_accuracy']>=.90,
 'min_sequential_accuracy':mins['sequential_accuracy']>=.90,
 'reload_equivalence_exact':mins['reload_equivalence']==1.0,
 'rollback_v2_accuracy':rollback_acc>=.95,
 'v3_still_canonical':v3.get('canonical_active') is True and V3 in head.get('active_capabilities',[]),
 'architecture_family_unchanged':head.get('architecture_family')=='TYPED_RECURRENT_CAPABILITY_GRAPH',
 'g3_not_started':head.get('g3_genesis_performed') is False,
}
passed=all(checks.values())
next_cap='KERNEL_G2_POST_RAW_V3_ARCHITECTURAL_CEILING_REASSESSMENT_V2' if passed else 'KERNEL_G2_RAW_REPRESENTATION_V3_CANONICAL_BURNIN_REPAIR_V1'

prev=head['canonical_head_digest']
prov['current_g2_binding'].update({
 'current_execution_label':'G2_POST_RAW_V3_CEILING_REASSESSMENT_PENDING' if passed else 'G2_RAW_REPRESENTATION_V3_BURNIN_REPAIR_PENDING',
 'frontier':next_cap,'frontier_native_method':'UnifiedYADOCoreV1.route_raw_task',
 'frontier_native_owner':'UnifiedYADOCoreV1','raw_representation_active_component':V3
})
prov['registry_digest']=cdig(prov,'registry_digest');write(PROV,prov)
core['algorithm_provenance_registry_digest']=prov['registry_digest'];core['current_frontier']=next_cap;core['frontier_source']='architecture/evolution-ledger.json:open_deficits'
core['raw_representation_v3_canonical_burnin_v1']={'status':'PASS' if passed else 'WITHHOLD','rounds':rounds,'min_metrics':mins,'rollback_v2_accuracy':rollback_acc,'checks':checks}
core['core_digest']=cdig(core,'core_digest');write(CORE,core)
head['algorithm_provenance_registry']['registry_digest']=prov['registry_digest'];head['algorithm_provenance_registry']['current_execution_label']=prov['current_g2_binding']['current_execution_label']
head['unified_core']['algorithm_provenance_registry_digest']=prov['registry_digest'];head['unified_core']['core_digest']=core['core_digest']
head['raw_representation_v3_canonical_burnin_v1']={'status':'PASS' if passed else 'WITHHOLD','min_metrics':mins,'rollback_v2_accuracy':rollback_acc}
head['current_frontier']=next_cap;head['frontier_source']='architecture/evolution-ledger.json:open_deficits';head['canonical_head_digest']=cdig(head,'canonical_head_digest');write(HEAD,head)
ledger['current_head_digest']=head['canonical_head_digest'];ledger['open_deficits']=[next_cap]

run_id=str(os.getenv('GITHUB_RUN_ID') or 'LOCAL')
receipt={'schema':'yado.g2.raw_representation_v3_canonical_burnin.receipt.v1',
 'status':'PASS_G2_RAW_REPRESENTATION_V3_CANONICAL_BURNIN_V1' if passed else 'WITHHOLD_G2_RAW_REPRESENTATION_V3_CANONICAL_BURNIN_V1',
 'rounds':rounds,'min_metrics':mins,'rollback_v2_accuracy':rollback_acc,'checks':checks,
 'previous_head_digest':prev,'new_head_digest':head['canonical_head_digest'],
 'canonical_mutation':True,'canonical_mechanism_mutation':False,'architecture_mutation':False,'g3_genesis_performed':False,
 'next_required_capability':next_cap,
 'semantic_boundary':'THREE-ROUND CANONICAL BURN-IN OF ACTIVE RAW REPRESENTATION V3 UNDER RELOAD, SEMANTICALLY NEUTRAL TEXT PERTURBATIONS, AND LONG REPEATED ROUTING. NO RETRAINING OR ADMISSION CLAIM.'
}
receipt['receipt_sha256']=h(receipt);write(OUT,receipt)
e={'index':len(ledger['events']),'event_id':f"E{len(ledger['events'])+1:04d}_G2_RAW_REPRESENTATION_V3_CANONICAL_BURNIN_V1",
 'event_type':'G2_RAW_REPRESENTATION_V3_CANONICAL_BURNIN','status':'PASS_CANONICAL' if passed else 'WITHHOLD','generation':ledger['current_head'],'deficit':front,
 'effect':f"BURNIN={'PASS' if passed else 'WITHHOLD'}; ROUNDS=3; MIN_DIRECT={mins['direct_accuracy']:.6f}; MIN_PERT={mins['perturbation_accuracy']:.6f}; MIN_SEQ={mins['sequential_accuracy']:.6f}; RELOAD={mins['reload_equivalence']:.6f}; ROLLBACK_V2={rollback_acc:.6f}; NEXT={next_cap}",
 'source_path':f'receipts/yado-g2-raw-representation-v3-canonical-burnin-v1-run-{run_id}.json','source_digest':receipt['receipt_sha256'],'run_id':run_id,
 'parent_event_hash':ledger['tail_event_hash'],'canonical_mutation':True,'canonical_mechanism_mutation':False,'architecture_mutation':False,
 'promotion_applied':False,'generation_transition':False,'previous_head_digest':prev,'new_head_digest':head['canonical_head_digest']}
e['event_hash']=event_hash(e);ledger['events'].append(e);ledger['event_count']=len(ledger['events']);ledger['tail_event_hash']=e['event_hash'];ledger['ledger_digest']=h({k:v for k,v in ledger.items() if k!='ledger_digest'})
validate_ledger_v2(ledger);write(LEDGER,ledger)

ctx=UnifiedContextKernel().snapshot()
if ctx['current_frontier']!=next_cap:raise RuntimeError('POST_RAW_V3_BURNIN_CONTEXT_INCONSISTENT')
post=subprocess.run([sys.executable,str(GUARD)],cwd=REPO,capture_output=True,text=True,timeout=60)
if post.returncode!=0:raise RuntimeError('POST_RAW_V3_BURNIN_GUARD_FAILED:'+post.stdout[-5000:]+post.stderr[-1000:])
print(json.dumps({'status':receipt['status'],'min_metrics':mins,'rollback_v2_accuracy':rollback_acc,'checks':checks,'next_required_capability':next_cap},indent=2,sort_keys=True))
