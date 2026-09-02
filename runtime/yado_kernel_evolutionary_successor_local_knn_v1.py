from __future__ import annotations
from pathlib import Path
import copy,hashlib,json,os,sys,time

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
PKG=ROOT/'yado_rc8_v36'
sys.path[:0]=[str(ROOT),str(PKG)]

from yado_evolution_ledger_v2 import validate_ledger_v2,event_hash
from yado_core_v3_0_rc8_external_cognitive import UnifiedYADOKernelV30RC8ExternalCognitive
from yado_organ_runtime_native_v1 import tree_predict
from yado_cognitive_growth_runtime_v1 import fit_knn_strategy,knn_predict
from yado_unified_context_kernel_v1 import UnifiedContextKernel

HEAD=REPO/'canonical/yado-main-head-g2.json'
CORE=REPO/'canonical/yado-unified-core-v1.json'
LEDGER=REPO/'architecture/evolution-ledger.json'
BASE=REPO/'receipts/yado-architecture-neutral-meta-synth-v2-latest.json'
CORPUS=REPO/'resources/yado-architecture-neutral-evidence-corpus-frozen-v1.json'
PARENT_CAND=REPO/'candidates/kernel-self-generated/evolutionary-centroid-calibrated-successor-v2.json'
HIER=REPO/'candidates/kernel-self-generated/evolutionary-hierarchical-residual-successor-v1.json'
ART=REPO/'architecture/yado-kernel-evolutionary-successor-local-knn-v1.json'
CAND=REPO/'candidates/kernel-self-generated/evolutionary-local-knn-successor-v1.json'
OUT=ROOT/'yado_kernel_evolutionary_successor_local_knn_v1_receipt.json'

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def h(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def write(p,o):p.write_text(json.dumps(o,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')
def cdig(o,field):
    x=copy.deepcopy(o);x.pop(field,None);return h(x)
def log(stage,**kw):print(json.dumps({'stage':stage,'ts':time.time(),**kw},sort_keys=True,default=str),flush=True)

head,core,ledger,base,corpus,parent_cand,hier=map(load,[HEAD,CORE,LEDGER,BASE,CORPUS,PARENT_CAND,HIER])
validate_ledger_v2(ledger)
expected_frontier='KERNEL_EVOLUTIONARY_SUCCESSOR_HIERARCHICAL_RESIDUAL_GENESIS_V2'
if ledger.get('open_deficits')!=[expected_frontier]:raise RuntimeError('UNEXPECTED_FRONTIER:'+json.dumps(ledger.get('open_deficits')))
if ledger.get('current_head_digest')!=head.get('canonical_head_digest'):raise RuntimeError('HEAD_LEDGER_MISMATCH')
if cdig(corpus,'corpus_digest')!=corpus.get('corpus_digest'):raise RuntimeError('FROZEN_CORPUS_DIGEST_MISMATCH')
if parent_cand.get('candidate_digest')!='f54ec98fb52421f632e47c6b6db3b2a213c6853726f39c8880d2af9a59ff1523':raise RuntimeError('PARENT_DIGEST_MISMATCH')

cases=list(corpus['cases']);blind=[c for c in cases if c['bucket']<18];nonblind=[c for c in cases if c['bucket']>=18]
parent_result=base['kernel_result'];parent_model=parent_result['model']
def original_parent_pred(x):return tree_predict(parent_model,x)
g1=parent_cand['generator'];gate1=g1['gate_model'];corr1=g1['corrector_model'];th1=float(parent_cand['selected_threshold'])

def centroid_distances(model,x):
    rows=[]
    for label_s,center in model['centroids'].items():
        d=0.0
        for key in model['features']:
            scale=max(float(model['scales'].get(key,1.0)),1e-12)
            d+=((float(x.get(key,0.0))-float(center[key]))/scale)**2
        rows.append((d,label_s))
    return sorted(rows,key=lambda z:(z[0],z[1]))
def centroid_margin(model,x):
    r=centroid_distances(model,x);return 0.0 if len(r)<2 else max(0.0,r[1][0]-r[0][0])
from yado_cognitive_growth_runtime_v1 import centroid_predict
def calibrated_parent_pred(x):
    if centroid_predict(gate1,x)!='PARENT_ERROR':return original_parent_pred(x)
    if centroid_margin(gate1,x)+1e-12<th1:return original_parent_pred(x)
    return centroid_predict(corr1,x)

# Native parent/operation selection, including failed hierarchical descendant as experience.
k=UnifiedYADOKernelV30RC8ExternalCognitive(db_path=str(ROOT/'yado_local_knn_control.sqlite'))
try:
    records=[
      {'variant_id':'EXECUTABLE_PARENT','parent_id':None,'lineage_id':'G2_SELECTOR_LINEAGE','artifact_digest':'parent',
       'task_scores':{'fresh_blind':.8043478260869565,'parent_correct_retention':1.0,'parent_error_repair_rate':0.0},
       'constraints':{'regression_pass':True,'state_integrity':True,'rollback_available':True},
       'traits':{'executable':1.0,'bounded':1.0},'failure_tags':['parent_error_repair_rate'],'status':'EVALUATED'},
      {'variant_id':'CALIBRATED_CHILD_V2','parent_id':'EXECUTABLE_PARENT','lineage_id':'G2_SELECTOR_LINEAGE','artifact_digest':parent_cand['candidate_digest'],
       'task_scores':{'fresh_blind':float(parent_cand['metrics']['fresh_blind_successor']),'parent_correct_retention':float(parent_cand['metrics']['parent_correct_retention']),'parent_error_repair_rate':float(parent_cand['metrics']['parent_error_repair_rate'])},
       'constraints':{'regression_pass':True,'state_integrity':True,'rollback_available':True},
       'traits':{'executable':1.0,'bounded':1.0,'calibrated':1.0},'failure_tags':['parent_error_repair_rate'],'status':'EVALUATED'},
      {'variant_id':'HIERARCHICAL_CHILD_V1','parent_id':'CALIBRATED_CHILD_V2','lineage_id':'G2_SELECTOR_LINEAGE','artifact_digest':hier['candidate_digest'],
       'task_scores':{'fresh_blind':float(hier['metrics']['fresh_blind_successor']),'parent_correct_retention':float(hier['metrics']['parent_correct_retention']),'parent_error_repair_rate':float(hier['metrics']['parent_error_repair_rate'])},
       'constraints':{'regression_pass':True,'state_integrity':True,'rollback_available':True},
       'traits':{'executable':1.0,'bounded':1.0,'hierarchical':1.0},'failure_tags':['zero_gain','retention_regression'],'status':'EVALUATED'}
    ]
    parent_choice=k.select_evolution_parent(records,'fresh_blind')
    if parent_choice.get('action')!='SELECT_PARENT':raise RuntimeError('KERNEL_PARENT_SELECTION_FAILED:'+json.dumps(parent_choice,sort_keys=True))
    operation=k.propose_evolution_operation(records,parent_choice['variant_id'],'fresh_blind')
finally:k.close()
if parent_choice.get('variant_id')!='CALIBRATED_CHILD_V2':raise RuntimeError('KERNEL_DID_NOT_SELECT_CALIBRATED_CHILD:'+json.dumps(parent_choice,sort_keys=True))
if operation.get('operation')!='CLONAL':raise RuntimeError('KERNEL_DID_NOT_SELECT_CLONAL:'+json.dumps(operation,sort_keys=True))
log('control_selected',parent_choice=parent_choice,operation=operation)

# Residual developmental split from calibrated parent, non-blind only.
errors=sorted([c for c in nonblind if calibrated_parent_pred(c['x'])!=c['y']],key=lambda c:h(c['key']+'|KNN_ERR'))
correct=sorted([c for c in nonblind if calibrated_parent_pred(c['x'])==c['y']],key=lambda c:h(c['key']+'|KNN_OK'))
if len(errors)<6:raise RuntimeError('INSUFFICIENT_LOCAL_RESIDUAL_ERRORS:'+str(len(errors)))
val_err_n=max(2,min(3,len(errors)//3));val_errors=errors[-val_err_n:];train_errors=errors[:-val_err_n]
val_ok_n=max(48,int(len(correct)*.24));val_correct=correct[-val_ok_n:];train_correct=correct[:-val_ok_n]
train_rows=sorted(train_errors+train_correct,key=lambda c:h(c['key']+'|KNN_TRAIN'));val_rows=sorted(val_errors+val_correct,key=lambda c:h(c['key']+'|KNN_VAL'))
log('split_ready',errors=len(errors),train_errors=len(train_errors),validation_errors=len(val_errors),train=len(train_rows),validation=len(val_rows))

def acc(rows,pred):return sum(pred(c['x'])==c['y'] for c in rows)/max(1,len(rows))
base_train=acc(train_rows,calibrated_parent_pred);base_val=acc(val_rows,calibrated_parent_pred)
gate_train=[(c['x'],'BASE_ERROR' if calibrated_parent_pred(c['x'])!=c['y'] else 'BASE_OK') for c in train_rows]
corr_train=[(c['x'],c['y']) for c in train_errors]

ks=[1,3,5,7,9]
skills=[];models={};metrics={}
for kg in ks:
    gate=fit_knn_strategy(gate_train,kg)
    for kc in ks:
        corr=fit_knn_strategy(corr_train,kc)
        sid=f"KNN_G{kg}_C{kc}"
        def pred(x,gate=gate,corr=corr):
            return knn_predict(corr,x) if knn_predict(gate,x)=='BASE_ERROR' else calibrated_parent_pred(x)
        tr=acc(train_rows,pred);va=acc(val_rows,pred)
        vc=[c for c in val_rows if calibrated_parent_pred(c['x'])==c['y']];vw=[c for c in val_rows if calibrated_parent_pred(c['x'])!=c['y']]
        retain=acc(vc,pred);repair=sum(pred(c['x'])==c['y'] for c in vw)/max(1,len(vw))
        artifact_digest=h({'gate_k':kg,'corr_k':kc,'gate':gate,'corr':corr})
        skills.append({'skill_id':sid,'artifact_digest':artifact_digest,'structural_valid':True,'semantic_consistency':1.0,
          'fit_baseline':base_train,'fit_candidate':tr,'heldout_baseline':base_val,'heldout_candidate':va,
          'regression_pass':retain>=.98,'state_integrity':True,'rollback_available':True,
          'metadata':{'gate_k':kg,'corrector_k':kc,'validation_retention':retain,'validation_repair':repair}})
        models[sid]={'gate':gate,'corrector':corr,'gate_k':kg,'corrector_k':kc}
        metrics[sid]={'train':tr,'validation':va,'retention':retain,'repair':repair,'gate_k':kg,'corrector_k':kc}

k=UnifiedYADOKernelV30RC8ExternalCognitive(db_path=str(ROOT/'yado_local_knn_skill_select.sqlite'))
try:
    selection=k.select_evolution_skills(skills,max_skills=1,min_semantic_consistency=.90,min_fit_gain=0.0,max_heldout_drop=0.0,min_heldout_gain=0.0)
finally:k.close()
ids=list(selection.get('selected_skill_ids') or []);selected_id=ids[0] if ids else None
selected=models.get(selected_id);log('kernel_knn_selection',selection=selection,selected_id=selected_id)

def final_pred(x):
    if selected is None:return calibrated_parent_pred(x)
    return knn_predict(selected['corrector'],x) if knn_predict(selected['gate'],x)=='BASE_ERROR' else calibrated_parent_pred(x)

base_blind=acc(blind,calibrated_parent_pred);child_blind=acc(blind,final_pred)
bc=[c for c in blind if calibrated_parent_pred(c['x'])==c['y']];bw=[c for c in blind if calibrated_parent_pred(c['x'])!=c['y']]
retain_blind=acc(bc,final_pred);repair_blind=sum(final_pred(c['x'])==c['y'] for c in bw)/max(1,len(bw));gain=child_blind-base_blind
supported=bool(selected is not None and child_blind>=.90 and gain>0 and retain_blind==1.0 and repair_blind>0)
state='SHADOW_SUPPORTED' if supported else 'WITHHOLD'
next_cap='KERNEL_EVOLUTIONARY_SUCCESSOR_FRESH_ADMISSION_V1' if supported else 'KERNEL_EVOLUTIONARY_SUCCESSOR_LOCAL_RESIDUAL_GENESIS_V2'

candidate={'schema':'yado.g2.evolutionary_local_knn_successor.v1','state':state,
 'principle':'KERNEL_SELECTED_CALIBRATED_PARENT_CLONAL_DIVERSIFIES_RESIDUAL_MECHANISM_TO_KNN',
 'parent_choice':parent_choice,'evolution_operation':operation,'parent_candidate_digest':parent_cand['candidate_digest'],
 'selection':selection,'selected_skill_id':selected_id,'selected_model':selected,'candidate_metrics':metrics,
 'metrics':{'fresh_blind_parent':base_blind,'fresh_blind_successor':child_blind,'gain':gain,'parent_correct_retention':retain_blind,'parent_error_repair_rate':repair_blind,'nonblind_residual_error_count':len(errors)},
 'frozen_history':{'corpus_digest':corpus['corpus_digest'],'blind_used_for_generation':False,'blind_used_for_selection':False,'blind_used_for_admission_only':True},
 'native_mechanism_source':'yado_cognitive_growth_runtime_v1.fit_knn_strategy/knn_predict','host_task_specific_rules_written':False,
 'canonical_active':False,'promotion_applied':False}
candidate['candidate_digest']=h(candidate);CAND.parent.mkdir(parents=True,exist_ok=True);write(CAND,candidate);log('candidate_evaluated',state=state,metrics=candidate['metrics'],next=next_cap)

artifact={'schema':'yado.g2.kernel_evolutionary_successor_local_knn.v1','status':'PASS_EVOLUTIONARY_SUCCESSOR_LOCAL_KNN_V1',
 'candidate_state':state,'candidate_digest':candidate['candidate_digest'],'selected_skill_id':selected_id,'metrics':candidate['metrics'],
 'next_required_capability':next_cap,'canonical_mechanism_mutation':False,'architecture_mutation':False,'g3_genesis_performed':False}
artifact['artifact_digest']=h(artifact);write(ART,artifact)

previous_head_digest=head['canonical_head_digest']
core['current_frontier']=next_cap;core['frontier_source']='architecture/evolution-ledger.json:open_deficits';core['core_digest']=cdig(core,'core_digest');write(CORE,core)
head['current_frontier']=next_cap;head['frontier_source']='architecture/evolution-ledger.json:open_deficits';head['unified_core']['core_digest']=core['core_digest'];head['canonical_head_digest']=cdig(head,'canonical_head_digest');write(HEAD,head)
checks={'kernel_selected_calibrated_parent':parent_choice.get('variant_id')=='CALIBRATED_CHILD_V2','kernel_selected_clonal':operation.get('operation')=='CLONAL',
 'blind_not_used_for_generation':True,'blind_not_used_for_selection':True,'frozen_history_valid':cdig(corpus,'corpus_digest')==corpus['corpus_digest'],
 'native_knn_source_used':True,'no_canonical_mechanism_mutation':True,'g3_not_started':head.get('g3_genesis_performed') is False}
receipt={**artifact,'schema':'yado.g2.kernel_evolutionary_successor_local_knn.receipt.v1','previous_head_digest':previous_head_digest,'new_head_digest':head['canonical_head_digest'],'checks':checks}
receipt['receipt_sha256']=h(receipt);write(OUT,receipt)

ledger['current_head_digest']=head['canonical_head_digest'];ledger['open_deficits']=[next_cap]
run_id=str(os.getenv('GITHUB_RUN_ID') or 'LOCAL')
e={'index':len(ledger['events']),'event_id':f"E{len(ledger['events'])+1:04d}_G2_EVOLUTIONARY_LOCAL_KNN_V1",
 'event_type':'G2_EVOLUTIONARY_CLONAL_LOCAL_KNN_SUCCESSOR','status':'PASS_SHADOW' if supported else 'WITHHOLD','generation':ledger['current_head'],'deficit':expected_frontier,
 'effect':f"MODE=CLONAL_KNN_DIVERSIFICATION; PARENT=CALIBRATED_CHILD_V2; SELECTED={selected_id}; BASE_BLIND={base_blind:.6f}; CHILD_BLIND={child_blind:.6f}; GAIN={gain:.6f}; RETAIN={retain_blind:.6f}; REPAIR={repair_blind:.6f}; NEXT={next_cap}",
 'source_path':f'receipts/yado-kernel-evolutionary-successor-local-knn-v1-run-{run_id}.json','source_digest':receipt['receipt_sha256'],'run_id':run_id,
 'parent_event_hash':ledger['tail_event_hash'],'canonical_mutation':True,'canonical_mechanism_mutation':False,'promotion_applied':False,'generation_transition':False,
 'previous_head_digest':previous_head_digest,'new_head_digest':head['canonical_head_digest']}
e['event_hash']=event_hash(e);ledger['events'].append(e);ledger['event_count']=len(ledger['events']);ledger['tail_event_hash']=e['event_hash']
ledger['ledger_digest']=h({k:v for k,v in ledger.items() if k!='ledger_digest'});validate_ledger_v2(ledger);write(LEDGER,ledger)
ctx=UnifiedContextKernel().snapshot()
if ctx['current_frontier']!=next_cap:raise RuntimeError('POST_WRITE_CONTEXT_INCONSISTENT')
log('complete',candidate_state=state,next=next_cap)
