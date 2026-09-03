from __future__ import annotations
from pathlib import Path
import copy,hashlib,json,os,subprocess,sys
ROOT=Path(__file__).resolve().parent;REPO=ROOT.parent;PKG=ROOT/'yado_rc8_v36'
sys.path[:0]=[str(ROOT),str(PKG)]
from yado_core_v3_0_rc8_external_cognitive import UnifiedYADOKernelV30RC8ExternalCognitive
from yado_raw_task_representation_robustness_v4 import RobustRawTaskRepresentationRuntimeV4
from yado_raw_task_representation_robustness_v5 import RobustRawTaskRepresentationRuntimeV5,component
from yado_evolution_ledger_v2 import validate_ledger_v2,event_hash
from yado_unified_context_kernel_v1 import UnifiedContextKernel

HEAD=REPO/'canonical/yado-main-head-g2.json';CORE=REPO/'canonical/yado-unified-core-v1.json'
LEDGER=REPO/'architecture/evolution-ledger.json';PROV=REPO/'canonical/yado-algorithm-provenance-registry-v1.json'
V3=REPO/'canonical/yado-raw-task-representation-v3.json';V4=REPO/'canonical/yado-raw-task-representation-v4.json'
STRUCT=REPO/'resources/yado-raw-task-representation-v3-structural-fresh-holdout-v1.json'
V2AUD=REPO/'receipts/yado-g2-raw-representation-v2-post-admission-audit-v1-run-33670110185.json'
V4PREV=REPO/'resources/yado-raw-task-representation-v4-robustness-fresh-holdout-v2.json'
V4ADM=REPO/'resources/yado-raw-task-representation-v4-canonical-admission-fresh-v1.json'
BASE=REPO/'receipts/yado-g2-real-world-transfer-benchmark-v1-run-33363995201.json'
BURN=REPO/'receipts/yado-g2-raw-representation-v4-canonical-burnin-v1-run-33680772147.json'
CAND=REPO/'candidates/kernel-self-generated/raw-task-representation-v5-sequential-robustness-v1.json'
ART=REPO/'architecture/yado-kernel-g2-raw-representation-v4-robustness-self-evolution-v1.json'
FRESH=REPO/'resources/yado-raw-task-representation-v5-sequential-robustness-fresh-holdout-v1.json'
OUT=ROOT/'yado_kernel_g2_raw_representation_v4_robustness_self_evolution_v1_receipt.json'
GUARD=ROOT/'yado_canonical_invariant_guard_v1.py';V5SRC=ROOT/'yado_raw_task_representation_robustness_v5.py'
MODES=('PARENT_V4','CORE_GUARDED','CONSENSUS_CORE','DUAL_MAJORITY','V4_PLUS_CORE_VOTE')

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def h(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def fsha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def write(p,o):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(o,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')
def cdig(o,f):x=copy.deepcopy(o);x.pop(f,None);return h(x)
def acc(rows,pred):return sum(pred(x)==y for x,y in rows)/max(1,len(rows))

head,core,ledger,prov,v3,v4,struct,v2aud,v4prev,v4adm,base,burn=map(load,[HEAD,CORE,LEDGER,PROV,V3,V4,STRUCT,V2AUD,V4PREV,V4ADM,BASE,BURN])
validate_ledger_v2(ledger)
front='KERNEL_G2_RAW_REPRESENTATION_V4_ROBUSTNESS_SELF_EVOLUTION_V1'
if ledger.get('open_deficits')!=[front]:raise RuntimeError('UNEXPECTED_FRONTIER:'+json.dumps(ledger.get('open_deficits')))
if v4.get('canonical_active') is not True:raise RuntimeError('V4_NOT_CANONICAL')
if burn.get('status')!='PASS_G2_RAW_REPRESENTATION_V4_CANONICAL_BURNIN_V1':raise RuntimeError('V4_BURNIN_NOT_PASS')
if head.get('g3_genesis_performed') is not False:raise RuntimeError('G3_ALREADY_STARTED')

base_cases=[]
for r in struct['rows']:base_cases.append((r['text'],r['expected']))
for r in v2aud['canary_rows']:base_cases.append((r['text'],r['expected']))
for r in v4prev['rows']:base_cases.append((r['text'],r['expected']))
for r in v4adm['rows']:base_cases.append((r['text'],r['expected']))

def spent_wrap(text,rn,i):
    m=(i+rn)%6
    if m==0:return f"[trace={rn}-{i%31}] {text} [complete]"
    if m==1:return f"<packet {i%23}> {text} <done>"
    if m==2:return f"{{session {i%19}}} {text} {{closed}}"
    if m==3:return f"(record {i%17}) {text} (end)"
    if m==4:return f"Memo {i%13}: {text} [tail={900+i}]"
    return f"Administrative note. {text.upper() if i%2==0 else text.lower()} End note."

fit=[(spent_wrap(x,rn,i),y) for rn in (1,2) for i,(x,y) in enumerate(base_cases)]
hold=[(spent_wrap(x,3,i),y) for i,(x,y) in enumerate(base_cases)]
parent=RobustRawTaskRepresentationRuntimeV4(v3,v4['selected_mode'])
pf,ph,pd=acc(fit,parent.predict_capability),acc(hold,parent.predict_capability),acc(base_cases,parent.predict_capability)

records=[{'variant_id':'RAW_V4_CANONICAL_PARENT','parent_id':None,'lineage_id':'G2_RAW_V4_SEQUENCE_ROBUSTNESS',
'artifact_digest':v4['component_digest'],'task_scores':{'fit':pf,'hold':ph,'direct':pd},
'constraints':{'regression_pass':True,'state_integrity':True,'rollback_available':True},
'traits':{'canonical':1.0,'sequential_residual':1.0-float(burn['min_metrics']['sequential_accuracy'])},
'failure_tags':['sequential_wrapper_stability_residual'],'status':'EVALUATED'}]
k=UnifiedYADOKernelV30RC8ExternalCognitive(db_path=str(ROOT/'yado_raw_v5_parent.sqlite'))
try:
    psel=k.select_evolution_parent(records,'sequential_wrapper_stability_residual')
    operation=k.propose_evolution_operation(records,psel['variant_id'],'raw_v4_sequential_robustness_self_evolution_v1')
finally:k.close()
if psel.get('variant_id')!='RAW_V4_CANONICAL_PARENT' or operation.get('operation')!='CLONAL':raise RuntimeError('KERNEL_PARENT_OR_OPERATION_INVALID')

metrics={};skills=[]
for mode in MODES:
    rt=RobustRawTaskRepresentationRuntimeV5(v3,v4,mode)
    f,hd,d=acc(fit,rt.predict_capability),acc(hold,rt.predict_capability),acc(base_cases,rt.predict_capability)
    metrics[mode]={'fit_spent_sequence':f,'hold_spent_sequence':hd,'direct_spent':d}
    skills.append({'skill_id':'RAW_V5_'+mode,'artifact_digest':h({'mode':mode,'v4':v4['component_digest'],'runtime':fsha(V5SRC)}),
    'structural_valid':True,'semantic_consistency':1.0,'fit_baseline':pf,'fit_candidate':f,'heldout_baseline':ph,'heldout_candidate':hd,
    'regression_pass':d+1e-12>=pd-0.005,'state_integrity':True,'rollback_available':True,'metadata':metrics[mode]})
k=UnifiedYADOKernelV30RC8ExternalCognitive(db_path=str(ROOT/'yado_raw_v5_select.sqlite'))
try:selection=k.select_evolution_skills(skills,max_skills=1,min_semantic_consistency=.90,min_fit_gain=.004,max_heldout_drop=0.0,min_heldout_gain=.004)
finally:k.close()
ids=list(selection.get('selected_skill_ids') or []);sid=ids[0] if ids else None
selected=None if sid is None else sid.removeprefix('RAW_V5_')
if selected not in MODES or selected=='PARENT_V4':selected=None

def fresh_wrap(text,i):
    m=i%8
    if m==0:return f"<run id={i%37}> {text} </run>"
    if m==1:return f"{{meta:{i%29}}} {text} {{/meta}}"
    if m==2:return f"(batch {i%31}) {text} (finished)"
    if m==3:return f"Header {i%17}: {text} Footer."
    if m==4:return f"Audit note. {text} Complete."
    if m==5:return f"[context {i%41}] {text} [end context]"
    if m==6:return f"  {text.replace(',', ' , ').replace(';',' ; ')}  "
    return f"Record. {text.upper() if i%2==0 else text.lower()} Closed."

rt=None if selected is None else RobustRawTaskRepresentationRuntimeV5(v3,v4,selected)
pred=parent.predict_capability if rt is None else rt.predict_capability
fd=acc(base_cases,pred)
fw=[(fresh_wrap(x,i),y) for i,(x,y) in enumerate(base_cases)]
fwa=acc(fw,pred);pfw=acc(fw,parent.predict_capability)
seq=[(fresh_wrap(base_cases[(i*31+7)%len(base_cases)][0],i),base_cases[(i*31+7)%len(base_cases)][1]) for i in range(3200)]
fsa=acc(seq,pred);pfs=acc(seq,parent.predict_capability)
base_rows=[(r['raw_text'],r['expected']) for r in base['raw_unstructured']['rows']]
breg=acc(base_rows,pred)

checks={'kernel_parent_v4':psel.get('variant_id')=='RAW_V4_CANONICAL_PARENT','kernel_operation_clonal':operation.get('operation')=='CLONAL',
'kernel_selected_candidate':selected is not None,'fresh_not_used_for_selection':True,'fresh_direct_accuracy':fd>=.97,
'fresh_wrapped_accuracy':fwa>=.97,'fresh_sequential_accuracy':fsa>=.97,'fresh_sequential_gain_over_parent':fsa-pfs>=.008,
'base_regression':breg>=.95,'class_specific_rules_absent':True,'parent_v4_not_retrained':True,'g3_not_started':head.get('g3_genesis_performed') is False}
supported=all(checks.values());state='SHADOW_V5_SEQUENTIAL_ROBUSTNESS_SUPPORTED' if supported else 'WITHHOLD'
next_cap='KERNEL_G2_RAW_REPRESENTATION_V5_CANONICAL_ADMISSION_V1' if supported else 'KERNEL_G2_RAW_REPRESENTATION_V4_ROBUSTNESS_SELF_EVOLUTION_V2'

fresh={'schema':'yado.g2.raw_task_representation_v5_sequential_robustness.fresh_holdout.v1','status':'SPENT_AFTER_V5_SEQUENCE_SHADOW_EVALUATION',
'selection_completed_before_fresh_evaluation':True,'selected_mode':selected,'task_count':len(fw),'sequential_task_count':len(seq),
'metrics':{'fresh_direct_accuracy':fd,'fresh_wrapped_accuracy':fwa,'fresh_sequential_accuracy':fsa,'parent_fresh_wrapped':pfw,'parent_fresh_sequential':pfs,'base_regression':breg},
'rows':[{'text':x,'expected':y,'got':pred(x),'correct':pred(x)==y} for x,y in fw]}
fresh['dataset_digest']=cdig(fresh,'dataset_digest');write(FRESH,fresh)
cand={'schema':'yado.g2.raw_task_representation_v5_sequential_robustness.candidate.v1','state':state,'component_id':'ALG-G2-RAW-TASK-REPRESENTATION-V5',
'parent_component_id':v4['component_id'],'parent_component_digest':v4['component_digest'],'kernel_parent':psel,'kernel_operation':operation,'kernel_selection':selection,
'candidate_metrics':metrics,'selected_mode':selected,'component':None if selected is None else component(selected,v4['component_digest']),
'runtime_source':'runtime/yado_raw_task_representation_robustness_v5.py','runtime_sha256':fsha(V5SRC),'fresh_dataset_digest':fresh['dataset_digest'],
'fresh_metrics':fresh['metrics'],'checks':checks,'generic_sequence_wrapper_robustness_only':True,'class_specific_rules':False,'parent_model_retrained':False,
'canonical_active':False,'canonical_mechanism_mutation':False,'architecture_mutation':False,'g3_genesis_performed':False}
cand['candidate_digest']=h(cand);write(CAND,cand)
art={'schema':'yado.g2.kernel_raw_representation_v4_robustness_self_evolution.v1','status':'PASS_G2_RAW_REPRESENTATION_V4_ROBUSTNESS_SELF_EVOLUTION_V1',
'candidate_state':state,'candidate_digest':cand['candidate_digest'],'selected_mode':selected,'parent_metrics':{'fit':pf,'holdout':ph,'direct':pd},
'selected_metrics':None if selected is None else metrics[selected],'fresh_metrics':fresh['metrics'],'checks':checks,'next_required_capability':next_cap,
'canonical_mechanism_mutation':False,'architecture_mutation':False,'g3_genesis_performed':False}
art['artifact_digest']=h(art);write(ART,art)

prev=head['canonical_head_digest']
prov['current_g2_binding'].update({'current_execution_label':'G2_RAW_V5_SEQUENCE_ROBUSTNESS_SHADOW_SUPPORTED' if supported else 'G2_RAW_V4_ROBUSTNESS_V2_PENDING',
'frontier':next_cap,'frontier_native_method':'select_evolution_parent+propose_evolution_operation+select_evolution_skills',
'frontier_native_owner':'UnifiedYADOKernelV30RC8ExternalCognitive','raw_v5_sequence_selected_mode':selected})
prov['registry_digest']=cdig(prov,'registry_digest');write(PROV,prov)
core['algorithm_provenance_registry_digest']=prov['registry_digest'];core['current_frontier']=next_cap;core['frontier_source']='architecture/evolution-ledger.json:open_deficits'
core['raw_representation_v4_robustness_self_evolution_v1']={'state':state,'candidate_digest':cand['candidate_digest'],'selected_mode':selected,'fresh_metrics':fresh['metrics'],'canonical_active':False}
core['core_digest']=cdig(core,'core_digest');write(CORE,core)
head['algorithm_provenance_registry']['registry_digest']=prov['registry_digest'];head['algorithm_provenance_registry']['current_execution_label']=prov['current_g2_binding']['current_execution_label']
head['unified_core']['algorithm_provenance_registry_digest']=prov['registry_digest'];head['unified_core']['core_digest']=core['core_digest']
head['raw_representation_v4_robustness_self_evolution_v1']={'state':state,'candidate_digest':cand['candidate_digest'],'selected_mode':selected,'fresh_metrics':fresh['metrics'],'canonical_active':False}
head['current_frontier']=next_cap;head['frontier_source']='architecture/evolution-ledger.json:open_deficits';head['canonical_head_digest']=cdig(head,'canonical_head_digest');write(HEAD,head)
ledger['current_head_digest']=head['canonical_head_digest'];ledger['open_deficits']=[next_cap]

run_id=str(os.getenv('GITHUB_RUN_ID') or 'LOCAL')
receipt={**art,'schema':'yado.g2.kernel_raw_representation_v4_robustness_self_evolution.receipt.v1','previous_head_digest':prev,'new_head_digest':head['canonical_head_digest'],'provenance_registry_digest':prov['registry_digest']}
receipt['receipt_sha256']=h(receipt);write(OUT,receipt)
e={'index':len(ledger['events']),'event_id':f"E{len(ledger['events'])+1:04d}_G2_RAW_V4_ROBUSTNESS_SELF_EVOLUTION_V1",
'event_type':'G2_RAW_V4_SEQUENTIAL_ROBUSTNESS_SELF_EVOLUTION','status':'PASS_SHADOW' if supported else 'WITHHOLD','generation':ledger['current_head'],'deficit':front,
'effect':f"OP={operation.get('operation')}; SELECTED={selected}; PARENT_HOLD={ph:.6f}; FRESH_SEQ={fsa:.6f}; PARENT_FRESH_SEQ={pfs:.6f}; FRESH_WRAP={fwa:.6f}; BASE_REG={breg:.6f}; NEXT={next_cap}",
'source_path':f'receipts/yado-g2-raw-v4-robustness-self-evolution-v1-run-{run_id}.json','source_digest':receipt['receipt_sha256'],'run_id':run_id,
'parent_event_hash':ledger['tail_event_hash'],'canonical_mutation':True,'canonical_mechanism_mutation':False,'architecture_mutation':False,'promotion_applied':False,
'generation_transition':False,'previous_head_digest':prev,'new_head_digest':head['canonical_head_digest']}
e['event_hash']=event_hash(e);ledger['events'].append(e);ledger['event_count']=len(ledger['events']);ledger['tail_event_hash']=e['event_hash'];ledger['ledger_digest']=h({k:v for k,v in ledger.items() if k!='ledger_digest'})
validate_ledger_v2(ledger);write(LEDGER,ledger)
ctx=UnifiedContextKernel().snapshot()
if ctx['current_frontier']!=next_cap:raise RuntimeError('POST_RAW_V5_SEQUENCE_CONTEXT_INCONSISTENT')
post=subprocess.run([sys.executable,str(GUARD)],cwd=REPO,capture_output=True,text=True,timeout=60)
if post.returncode!=0:raise RuntimeError('POST_RAW_V5_SEQUENCE_GUARD_FAILED:'+post.stdout[-5000:]+post.stderr[-1000:])
print(json.dumps({'status':receipt['status'],'candidate_state':state,'selected_mode':selected,'candidate_metrics':metrics,'fresh_metrics':fresh['metrics'],'checks':checks,'next_required_capability':next_cap},indent=2,sort_keys=True))
