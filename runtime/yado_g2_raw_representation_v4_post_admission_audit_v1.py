from __future__ import annotations
from pathlib import Path
import copy,hashlib,json,os,subprocess,sys

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
PREV=REPO/'resources/yado-raw-task-representation-v4-robustness-fresh-holdout-v2.json'
ADMF=REPO/'resources/yado-raw-task-representation-v4-canonical-admission-fresh-v1.json'
BASE=REPO/'receipts/yado-g2-real-world-transfer-benchmark-v1-run-33363995201.json'
OUT=ROOT/'yado_g2_raw_representation_v4_post_admission_audit_v1_receipt.json'
GUARD=ROOT/'yado_canonical_invariant_guard_v1.py'
UNIFIED=ROOT/'yado_unified_core_v1.py'
V4SRC=ROOT/'yado_raw_task_representation_robustness_v4.py'
V3SRC=ROOT/'yado_raw_task_representation_candidate_v3.py'

V3='ALG-G2-RAW-TASK-REPRESENTATION-V3';V4='ALG-G2-RAW-TASK-REPRESENTATION-V4'
C1='ALG-CONJUNCTIVE-RULE-INDUCER-V1';CR='ALG-BOUNDED-DNF-RELATION-POLICY-INDUCER-V1';CB='ALG-BUDGETED-STAGE-POLICY-V1';CE='RESOURCE-PORTFOLIO-V1'

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def h(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def fsha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def write(p,o):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(o,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')
def cdig(o,field):x=copy.deepcopy(o);x.pop(field,None);return h(x)

head,core,ledger,prov,v4,v3,prev,admf,base=map(load,[HEAD,CORE,LEDGER,PROV,V4ART,V3ART,PREV,ADMF,BASE])
validate_ledger_v2(ledger)
front='KERNEL_G2_RAW_REPRESENTATION_V4_POST_ADMISSION_AUDIT_V1'
if ledger.get('open_deficits')!=[front]:raise RuntimeError('UNEXPECTED_FRONTIER:'+json.dumps(ledger.get('open_deficits')))
if head.get('g3_genesis_performed') is not False:raise RuntimeError('G3_ALREADY_STARTED')
if v4.get('canonical_active') is not True:raise RuntimeError('V4_NOT_CANONICAL')

plane=next((p for p in core.get('planes',[]) if p.get('plane_id')=='REPRESENTATION_AND_GROUNDING'),{})
rim=core.get('runtime_integrity_manifest',{})
sup=next((x for x in core.get('superseded_components',[]) if x.get('component_id')==V3),None)

router_rows=[]
for i,label in enumerate([C1,CR,CB,CE]*180):
    router_rows.append({'input':{'budget_limited':label==CB,'quota_limited':False,'external_evidence_needed':label==CE,'relation_needed':label==CR,'disjunction_needed':False,'noise':i},'expected':label})
router=BoundedCapabilityRouterLearnerV1.synthesize(router_rows,router_rows,C1,min_support=8)

ucore=UnifiedYADOCoreV1(REPO)
def eval_rows(rows,text_field):
    out=[]
    for r in rows:
        text=r[text_field];expected=r['expected'];got=ucore.route_raw_task(text,router)['selected_capability']
        out.append({'text':text,'expected':expected,'got':got,'correct':got==expected})
    return out

prev_rows=eval_rows(prev['rows'],'wrapped')
prev_acc=sum(x['correct'] for x in prev_rows)/len(prev_rows)
adm_rows=eval_rows(admf['rows'],'text')
adm_acc=sum(x['correct'] for x in adm_rows)/len(adm_rows)

# Direct V3 rollback remains constructible and must still preserve old baseline.
rollback=RawTaskRepresentationRuntimeV3(v3)
base_rows=[(r['raw_text'],r['expected']) for r in base['raw_unstructured']['rows']]
rollback_acc=sum(rollback.predict_capability(x)==y for x,y in base_rows)/len(base_rows)

checks={
 'v4_component_digest_exact':v4.get('component_digest')==cdig(v4,'component_digest'),
 'v4_canonical_active':v4.get('canonical_active') is True,
 'v4_mode_exact':v4.get('selected_mode')=='MULTIVIEW_EDGE_TIE_CORE',
 'head_active_v4_only':V4 in head.get('active_capabilities',[]) and V3 not in head.get('active_capabilities',[]),
 'plane_active_v4_only':V4 in plane.get('active_components',[]) and V3 not in plane.get('active_components',[]),
 'core_raw_binding_v4':core.get('raw_task_representation',{}).get('component_id')==V4,
 'v4_runtime_hash_bound':rim.get('sources',{}).get('runtime/yado_raw_task_representation_robustness_v4.py')==fsha(V4SRC),
 'v3_dependency_hash_bound':rim.get('sources',{}).get('runtime/yado_raw_task_representation_candidate_v3.py')==fsha(V3SRC),
 'unified_runtime_hash_bound':core.get('runtime_sha256')==head.get('unified_core',{}).get('runtime_sha256')==fsha(UNIFIED),
 'runtime_manifest_digest_bound':rim.get('manifest_digest')==h(rim.get('sources',{}))==head.get('unified_core',{}).get('runtime_integrity_manifest_digest'),
 'v3_superseded_with_history':bool(sup and sup.get('superseded_by')==V4 and sup.get('historical_evidence_retained') is True),
 'previous_v4_fresh_restart_reproduction':prev_acc>=.99,
 'canonical_admission_restart_reproduction':adm_acc>=.95,
 'rollback_v3_constructible':rollback_acc>=.95,
 'g3_not_started':head.get('g3_genesis_performed') is False,
}
passed=all(checks.values())
next_cap='KERNEL_G2_RAW_REPRESENTATION_V4_CANONICAL_BURNIN_V1' if passed else 'KERNEL_G2_RAW_REPRESENTATION_V4_POST_ADMISSION_REPAIR_V1'

prev_head=head['canonical_head_digest']
prov['current_g2_binding'].update({
 'current_execution_label':'G2_RAW_REPRESENTATION_V4_CANONICAL_BURNIN_PENDING' if passed else 'G2_RAW_REPRESENTATION_V4_POST_ADMISSION_REPAIR_PENDING',
 'frontier':next_cap,'frontier_native_method':'UnifiedYADOCoreV1.route_raw_task','frontier_native_owner':'UnifiedYADOCoreV1',
 'raw_representation_active_component':V4
})
prov['registry_digest']=cdig(prov,'registry_digest');write(PROV,prov)
core['algorithm_provenance_registry_digest']=prov['registry_digest'];core['current_frontier']=next_cap;core['frontier_source']='architecture/evolution-ledger.json:open_deficits'
core['raw_representation_v4_post_admission_audit_v1']={'status':'PASS' if passed else 'WITHHOLD','previous_v4_fresh_restart_accuracy':prev_acc,'canonical_admission_restart_accuracy':adm_acc,'rollback_v3_accuracy':rollback_acc,'checks':checks}
core['core_digest']=cdig(core,'core_digest');write(CORE,core)
head['algorithm_provenance_registry']['registry_digest']=prov['registry_digest'];head['algorithm_provenance_registry']['current_execution_label']=prov['current_g2_binding']['current_execution_label']
head['unified_core']['algorithm_provenance_registry_digest']=prov['registry_digest'];head['unified_core']['core_digest']=core['core_digest']
head['raw_representation_v4_post_admission_audit_v1']={'status':'PASS' if passed else 'WITHHOLD','previous_v4_fresh_restart_accuracy':prev_acc,'canonical_admission_restart_accuracy':adm_acc,'rollback_v3_accuracy':rollback_acc}
head['current_frontier']=next_cap;head['frontier_source']='architecture/evolution-ledger.json:open_deficits';head['canonical_head_digest']=cdig(head,'canonical_head_digest');write(HEAD,head)
ledger['current_head_digest']=head['canonical_head_digest'];ledger['open_deficits']=[next_cap]

run_id=str(os.getenv('GITHUB_RUN_ID') or 'LOCAL')
receipt={'schema':'yado.g2.raw_representation_v4_post_admission_audit.receipt.v1',
 'status':'PASS_G2_RAW_REPRESENTATION_V4_POST_ADMISSION_AUDIT_V1' if passed else 'WITHHOLD_G2_RAW_REPRESENTATION_V4_POST_ADMISSION_AUDIT_V1',
 'previous_v4_fresh_restart_accuracy':prev_acc,'canonical_admission_restart_accuracy':adm_acc,'rollback_v3_accuracy':rollback_acc,
 'checks':checks,'previous_head_digest':prev_head,'new_head_digest':head['canonical_head_digest'],
 'canonical_mutation':True,'canonical_mechanism_mutation':False,'architecture_mutation':False,'g3_genesis_performed':False,
 'next_required_capability':next_cap,
 'semantic_boundary':'POST-ADMISSION RESTART AUDIT OF CANONICAL RAW REPRESENTATION V4, ITS V3 DEPENDENCY/ROLLBACK, RUNTIME MANIFEST, AND SPENT FRESH EVIDENCE REPRODUCTION.'
}
receipt['receipt_sha256']=h(receipt);write(OUT,receipt)

e={'index':len(ledger['events']),'event_id':f"E{len(ledger['events'])+1:04d}_G2_RAW_REPRESENTATION_V4_POST_ADMISSION_AUDIT_V1",
 'event_type':'G2_RAW_REPRESENTATION_V4_POST_ADMISSION_AUDIT','status':'PASS' if passed else 'WITHHOLD','generation':ledger['current_head'],'deficit':front,
 'effect':f"AUDIT={'PASS' if passed else 'WITHHOLD'}; PREV_REPRO={prev_acc:.6f}; ADMISSION_REPRO={adm_acc:.6f}; ROLLBACK_V3={rollback_acc:.6f}; NEXT={next_cap}",
 'source_path':f'receipts/yado-g2-raw-representation-v4-post-admission-audit-v1-run-{run_id}.json','source_digest':receipt['receipt_sha256'],'run_id':run_id,
 'parent_event_hash':ledger['tail_event_hash'],'canonical_mutation':True,'canonical_mechanism_mutation':False,'architecture_mutation':False,'promotion_applied':False,'generation_transition':False,
 'previous_head_digest':prev_head,'new_head_digest':head['canonical_head_digest']}
e['event_hash']=event_hash(e);ledger['events'].append(e);ledger['event_count']=len(ledger['events']);ledger['tail_event_hash']=e['event_hash'];ledger['ledger_digest']=h({k:v for k,v in ledger.items() if k!='ledger_digest'})
validate_ledger_v2(ledger);write(LEDGER,ledger)
ctx=UnifiedContextKernel().snapshot()
if ctx['current_frontier']!=next_cap:raise RuntimeError('POST_V4_AUDIT_CONTEXT_INCONSISTENT')
post=subprocess.run([sys.executable,str(GUARD)],cwd=REPO,capture_output=True,text=True,timeout=60)
if post.returncode!=0:raise RuntimeError('POST_V4_AUDIT_GUARD_FAILED:'+post.stdout[-5000:]+post.stderr[-1000:])
print(json.dumps({'status':receipt['status'],'previous_v4_fresh_restart_accuracy':prev_acc,'canonical_admission_restart_accuracy':adm_acc,'rollback_v3_accuracy':rollback_acc,'checks':checks,'next_required_capability':next_cap},indent=2,sort_keys=True))
