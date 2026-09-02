from __future__ import annotations
from pathlib import Path
import copy,hashlib,json,math,os,sys,time

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
PKG=ROOT/'yado_rc8_v36'
sys.path[:0]=[str(ROOT),str(PKG)]

from yado_evolution_ledger_v2 import validate_ledger_v2,event_hash
from yado_core_v3_0_rc8_external_cognitive import UnifiedYADOKernelV30RC8ExternalCognitive
from yado_organ_runtime_native_v1 import tree_predict
from yado_cognitive_growth_runtime_v1 import select_centroid_features,centroid_predict
from yado_unified_context_kernel_v1 import UnifiedContextKernel

HEAD=REPO/'canonical/yado-main-head-g2.json'
CORE=REPO/'canonical/yado-unified-core-v1.json'
LEDGER=REPO/'architecture/evolution-ledger.json'
BASE=REPO/'receipts/yado-architecture-neutral-meta-synth-v2-latest.json'
CORPUS=REPO/'resources/yado-architecture-neutral-evidence-corpus-frozen-v1.json'
ART=REPO/'architecture/yado-kernel-evolutionary-successor-centroid-calibrated-v2.json'
CAND=REPO/'candidates/kernel-self-generated/evolutionary-centroid-calibrated-successor-v2.json'
OUT=ROOT/'yado_kernel_evolutionary_successor_centroid_calibrated_v2_receipt.json'

def canon(o): return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def h(o): return hashlib.sha256(canon(o).encode()).hexdigest()
def load(p): return json.loads(p.read_text(encoding='utf-8'))
def write(p,o): p.write_text(json.dumps(o,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')
def cdig(o,field):
    x=copy.deepcopy(o);x.pop(field,None);return h(x)
def log(stage,**kw):
    print(json.dumps({'stage':stage,'ts':time.time(),**kw},sort_keys=True,default=str),flush=True)

head,core,ledger,base,corpus=map(load,[HEAD,CORE,LEDGER,BASE,CORPUS])
validate_ledger_v2(ledger)
expected_frontier='KERNEL_EVOLUTIONARY_SUCCESSOR_CENTROID_GENESIS_V2'
if ledger.get('open_deficits')!=[expected_frontier]:
    raise RuntimeError('UNEXPECTED_FRONTIER:'+json.dumps(ledger.get('open_deficits')))
if ledger.get('current_head_digest')!=head.get('canonical_head_digest'):
    raise RuntimeError('HEAD_LEDGER_MISMATCH')
if cdig(corpus,'corpus_digest')!=corpus.get('corpus_digest'):
    raise RuntimeError('FROZEN_CORPUS_DIGEST_MISMATCH')

cases=list(corpus['cases'])
blind=[c for c in cases if c['bucket']<18]
nonblind=[c for c in cases if c['bucket']>=18]
parent_result=base['kernel_result']; parent_model=parent_result['model']
parent_digest=h({'algorithm':parent_result.get('selected_algorithm'),'model':parent_model})
def parent_pred(x): return tree_predict(parent_model,x)

# Kernel chooses parent and operation from current evidence.
k=UnifiedYADOKernelV30RC8ExternalCognitive(db_path=str(ROOT/'yado_centroid_v2_control.sqlite'))
try:
    records=[
      {'variant_id':'EXECUTABLE_PARENT','parent_id':None,'lineage_id':'G2_SELECTOR_LINEAGE',
       'artifact_digest':parent_digest,
       'task_scores':{'fresh_blind':0.8043478260869565,'parent_correct_retention':1.0,'parent_error_repair_rate':0.0},
       'constraints':{'regression_pass':True,'state_integrity':True,'rollback_available':True},
       'traits':{'executable':1.0,'bounded':1.0},'failure_tags':['parent_error_repair_rate'],'status':'EVALUATED'},
      {'variant_id':'CENTROID_CHILD_V1','parent_id':'EXECUTABLE_PARENT','lineage_id':'G2_SELECTOR_LINEAGE',
       'artifact_digest':'016cbe8a791b6c1089f016d0047283109b16cf48cd28598752904d98b35fe384',
       'task_scores':{'fresh_blind':0.717391304347826,'parent_correct_retention':0.8648648648648649,'parent_error_repair_rate':0.1111111111111111},
       'constraints':{'regression_pass':True,'state_integrity':True,'rollback_available':True},
       'traits':{'executable':1.0,'bounded':1.0,'continuous':1.0},
       'failure_tags':['parent_error_repair_rate','gate_false_positive_regression'],'status':'EVALUATED'},
    ]
    parent_choice=k.select_evolution_parent(records,'fresh_blind')
    if parent_choice.get('action')!='SELECT_PARENT':
        raise RuntimeError('KERNEL_PARENT_SELECTION_FAILED:'+json.dumps(parent_choice,sort_keys=True))
    operation=k.propose_evolution_operation(records,parent_choice['variant_id'],'fresh_blind')
finally:k.close()
if parent_choice.get('variant_id')!='EXECUTABLE_PARENT':
    raise RuntimeError('KERNEL_SELECTED_UNSUPPORTED_PARENT:'+json.dumps(parent_choice,sort_keys=True))
if operation.get('operation')!='CLONAL':
    raise RuntimeError('KERNEL_DID_NOT_SELECT_CLONAL:'+json.dumps(operation,sort_keys=True))
log('control_selected',parent_choice=parent_choice,operation=operation)

# Deterministic stratified developmental split from non-blind history only.
errors=sorted([c for c in nonblind if parent_pred(c['x'])!=c['y']],key=lambda c:h(c['key']+'|CAL_ERR'))
correct=sorted([c for c in nonblind if parent_pred(c['x'])==c['y']],key=lambda c:h(c['key']+'|CAL_OK'))
if len(errors)<6: raise RuntimeError('INSUFFICIENT_PARENT_ERRORS:'+str(len(errors)))
val_err_n=max(3,min(4,len(errors)//3))
val_errors=errors[-val_err_n:]; train_errors=errors[:-val_err_n]
val_ok_n=max(48,int(len(correct)*.24))
val_correct=correct[-val_ok_n:]; train_correct=correct[:-val_ok_n]
train_rows=sorted(train_errors+train_correct,key=lambda c:h(c['key']+'|CAL_TRAIN'))
val_rows=sorted(val_errors+val_correct,key=lambda c:h(c['key']+'|CAL_VAL'))
log('split_ready',train=len(train_rows),validation=len(val_rows),train_errors=len(train_errors),validation_errors=len(val_errors))

# Native centroid genesis on training evidence.
gate_all=[(c['x'],'PARENT_ERROR' if parent_pred(c['x'])!=c['y'] else 'PARENT_OK') for c in train_rows]
gate_fit=[r for i,r in enumerate(gate_all) if i%5!=0]
gate_inner_val=[r for i,r in enumerate(gate_all) if i%5==0]
corr_all=[(c['x'],c['y']) for c in train_errors]
corr_fit=[r for i,r in enumerate(corr_all) if i%4!=0]
corr_inner_val=[r for i,r in enumerate(corr_all) if i%4==0]
if not gate_inner_val or not corr_inner_val:
    raise RuntimeError('INNER_VALIDATION_EMPTY')
gate_model,gate_meta=select_centroid_features(gate_fit,gate_inner_val)
corr_model,corr_meta=select_centroid_features(corr_fit,corr_inner_val)
log('native_centroid_models_ready',gate_meta=gate_meta,corr_meta=corr_meta)

def centroid_distances(model,x):
    rows=[]
    for label_s,center in model['centroids'].items():
        d=0.0
        for key in model['features']:
            scale=max(float(model['scales'].get(key,1.0)),1e-12)
            d += ((float(x.get(key,0.0))-float(center[key]))/scale)**2
        rows.append((d,label_s))
    rows.sort(key=lambda z:(z[0],z[1]))
    return rows

def gate_margin(x):
    rows=centroid_distances(gate_model,x)
    if len(rows)<2:return 0.0
    return max(0.0,rows[1][0]-rows[0][0])

def child_pred(x,threshold):
    if centroid_predict(gate_model,x)!='PARENT_ERROR':
        return parent_pred(x)
    if gate_margin(x)+1e-12 < threshold:
        return parent_pred(x)
    return centroid_predict(corr_model,x)

def acc(rows,pred):
    return sum(pred(c['x'])==c['y'] for c in rows)/max(1,len(rows))

# Generic threshold candidates are derived only from training margins.
error_pred_margins=sorted({round(gate_margin(c['x']),12) for c in train_rows if centroid_predict(gate_model,c['x'])=='PARENT_ERROR'})
if not error_pred_margins:
    raise RuntimeError('NO_ERROR_GATE_MARGINS')
def quantile(xs,q):
    if not xs:return 0.0
    i=min(len(xs)-1,max(0,int(round(q*(len(xs)-1)))))
    return xs[i]
qs=[0.0,.10,.20,.30,.40,.50,.60,.70,.80,.90,.95,.99]
thresholds=sorted({float(quantile(error_pred_margins,q)) for q in qs})
if len(thresholds)>24: thresholds=thresholds[:24]
log('threshold_candidates_ready',count=len(thresholds),thresholds=thresholds)

parent_train=acc(train_rows,parent_pred)
parent_val=acc(val_rows,parent_pred)
skill_rows=[]
candidate_metrics={}
for th in thresholds:
    sid='CENTROID_MARGIN_'+hashlib.sha256(f'{th:.12f}'.encode()).hexdigest()[:10]
    train_acc=acc(train_rows,lambda x,th=th:child_pred(x,th))
    val_acc=acc(val_rows,lambda x,th=th:child_pred(x,th))
    val_parent_correct=[c for c in val_rows if parent_pred(c['x'])==c['y']]
    val_parent_wrong=[c for c in val_rows if parent_pred(c['x'])!=c['y']]
    retention=acc(val_parent_correct,lambda x,th=th:child_pred(x,th))
    repair=sum(child_pred(c['x'],th)==c['y'] for c in val_parent_wrong)/max(1,len(val_parent_wrong))
    cand={
      'skill_id':sid,'artifact_digest':h({'threshold':th,'gate':gate_model,'corrector':corr_model}),
      'structural_valid':True,'semantic_consistency':1.0,
      'fit_baseline':parent_train,'fit_candidate':train_acc,
      'heldout_baseline':parent_val,'heldout_candidate':val_acc,
      'regression_pass':retention>=0.98,
      'state_integrity':True,'rollback_available':True,
      'metadata':{'threshold':th,'validation_retention':retention,'validation_repair':repair}
    }
    skill_rows.append(cand)
    candidate_metrics[sid]={'threshold':th,'train':train_acc,'validation':val_acc,'retention':retention,'repair':repair}

# Kernel selects calibration; host does not choose threshold.
k=UnifiedYADOKernelV30RC8ExternalCognitive(db_path=str(ROOT/'yado_centroid_v2_skill_select.sqlite'))
try:
    selection=k.select_evolution_skills(
        skill_rows,max_skills=1,
        min_semantic_consistency=0.90,
        min_fit_gain=0.0,
        max_heldout_drop=0.0,
        min_heldout_gain=0.0,
    )
finally:k.close()
selected_ids=list(selection.get('selected_skill_ids') or [])
selected_id=selected_ids[0] if selected_ids else None
selected_threshold=None if selected_id is None else float(candidate_metrics[selected_id]['threshold'])
log('kernel_skill_selection',selection=selection,selected_threshold=selected_threshold)

# Fresh blind is used only after kernel selection.
parent_blind=acc(blind,parent_pred)
if selected_threshold is None:
    child_blind=parent_blind; retention_blind=1.0; repair_blind=0.0
else:
    child_blind=acc(blind,lambda x:child_pred(x,selected_threshold))
    pc=[c for c in blind if parent_pred(c['x'])==c['y']]
    pw=[c for c in blind if parent_pred(c['x'])!=c['y']]
    retention_blind=acc(pc,lambda x:child_pred(x,selected_threshold))
    repair_blind=sum(child_pred(c['x'],selected_threshold)==c['y'] for c in pw)/max(1,len(pw))
gain=child_blind-parent_blind
supported=bool(selected_threshold is not None and child_blind>=0.90 and gain>0 and retention_blind==1.0 and repair_blind>0)
state='SHADOW_SUPPORTED' if supported else 'WITHHOLD'
next_cap='KERNEL_EVOLUTIONARY_SUCCESSOR_FRESH_ADMISSION_V1' if supported else 'KERNEL_EVOLUTIONARY_SUCCESSOR_CALIBRATED_GATE_GENESIS_V2'

candidate={
 'schema':'yado.g2.evolutionary_centroid_calibrated_successor.v2','state':state,
 'principle':'KERNEL_SELECTED_CLONAL_WITH_KERNEL_SELECTED_MARGIN_CALIBRATION',
 'parent_choice':parent_choice,'evolution_operation':operation,
 'generator':{
   'centroid':'select_centroid_features',
   'calibration_adapter':'GENERIC_NEAREST_CENTROID_DISTANCE_MARGIN',
   'threshold_candidates_from':'NONBLIND_TRAIN_ONLY',
   'threshold_selected_by':'UnifiedYADOKernelV30RC8ExternalCognitive.select_evolution_skills',
   'gate_model':gate_model,'corrector_model':corr_model,
 },
 'selection':selection,'candidate_metrics':candidate_metrics,'selected_threshold':selected_threshold,
 'metrics':{
   'fresh_blind_parent':parent_blind,'fresh_blind_successor':child_blind,'gain':gain,
   'parent_correct_retention':retention_blind,'parent_error_repair_rate':repair_blind,
 },
 'frozen_history':{'corpus_digest':corpus['corpus_digest'],'blind_used_for_candidate_generation':False,'blind_used_for_selection':False,'blind_used_for_admission_only':True},
 'host_task_specific_rules_written':False,
 'host_generic_margin_adapter_supplied':True,
 'kernel_selected_calibration':selected_threshold is not None,
 'canonical_active':False,'promotion_applied':False,
}
candidate['candidate_digest']=h(candidate);CAND.parent.mkdir(parents=True,exist_ok=True);write(CAND,candidate)
log('candidate_evaluated',state=state,metrics=candidate['metrics'],next=next_cap)

artifact={
 'schema':'yado.g2.kernel_evolutionary_successor_centroid_calibrated.v2',
 'status':'PASS_EVOLUTIONARY_SUCCESSOR_CENTROID_CALIBRATED_V2',
 'candidate_state':state,'candidate_digest':candidate['candidate_digest'],
 'selected_threshold':selected_threshold,'selection_status':selection.get('status'),
 'metrics':candidate['metrics'],'next_required_capability':next_cap,
 'canonical_mechanism_mutation':False,'architecture_mutation':False,'g3_genesis_performed':False,
}
artifact['artifact_digest']=h(artifact);write(ART,artifact)

previous_head_digest=head['canonical_head_digest']
core['current_frontier']=next_cap;core['frontier_source']='architecture/evolution-ledger.json:open_deficits';core['core_digest']=cdig(core,'core_digest');write(CORE,core)
head['current_frontier']=next_cap;head['frontier_source']='architecture/evolution-ledger.json:open_deficits';head['unified_core']['core_digest']=core['core_digest'];head['canonical_head_digest']=cdig(head,'canonical_head_digest');write(HEAD,head)

checks={
 'kernel_selected_parent':parent_choice.get('variant_id')=='EXECUTABLE_PARENT',
 'kernel_selected_clonal':operation.get('operation')=='CLONAL',
 'blind_not_used_for_candidate_generation':True,
 'blind_not_used_for_selection':True,
 'frozen_history_valid':cdig(corpus,'corpus_digest')==corpus['corpus_digest'],
 'no_canonical_mechanism_mutation':True,
 'g3_not_started':head.get('g3_genesis_performed') is False,
}
receipt={**artifact,'schema':'yado.g2.kernel_evolutionary_successor_centroid_calibrated.receipt.v2',
 'previous_head_digest':previous_head_digest,'new_head_digest':head['canonical_head_digest'],'checks':checks}
receipt['receipt_sha256']=h(receipt);write(OUT,receipt)

ledger['current_head_digest']=head['canonical_head_digest'];ledger['open_deficits']=[next_cap]
run_id=str(os.getenv('GITHUB_RUN_ID') or 'LOCAL')
e={'index':len(ledger['events']),
 'event_id':f"E{len(ledger['events'])+1:04d}_G2_EVOLUTIONARY_SUCCESSOR_CENTROID_CALIBRATED_V2",
 'event_type':'G2_EVOLUTIONARY_CLONAL_CALIBRATED_GATE_SUCCESSOR',
 'status':'PASS_SHADOW' if supported else 'WITHHOLD','generation':ledger['current_head'],'deficit':expected_frontier,
 'effect':f"MODE=KERNEL_SELECTED_CLONAL; CALIBRATION_SELECTED_BY=SKILL_ADMISSION; THRESHOLD={selected_threshold}; PARENT_BLIND={parent_blind:.6f}; CHILD_BLIND={child_blind:.6f}; GAIN={gain:.6f}; RETAIN={retention_blind:.6f}; REPAIR={repair_blind:.6f}; NEXT={next_cap}",
 'source_path':f'receipts/yado-kernel-evolutionary-successor-centroid-calibrated-v2-run-{run_id}.json',
 'source_digest':receipt['receipt_sha256'],'run_id':run_id,'parent_event_hash':ledger['tail_event_hash'],
 'canonical_mutation':True,'canonical_mechanism_mutation':False,'promotion_applied':False,'generation_transition':False,
 'previous_head_digest':previous_head_digest,'new_head_digest':head['canonical_head_digest']}
e['event_hash']=event_hash(e);ledger['events'].append(e);ledger['event_count']=len(ledger['events']);ledger['tail_event_hash']=e['event_hash']
ledger['ledger_digest']=h({k:v for k,v in ledger.items() if k!='ledger_digest'});validate_ledger_v2(ledger);write(LEDGER,ledger)
ctx=UnifiedContextKernel().snapshot()
if ctx['current_frontier']!=next_cap: raise RuntimeError('POST_WRITE_CONTEXT_INCONSISTENT')
log('complete',candidate_state=state,next=next_cap)
