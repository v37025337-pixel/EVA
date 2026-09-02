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
from yado_cognitive_growth_runtime_v1 import select_centroid_features,centroid_predict
from yado_unified_context_kernel_v1 import UnifiedContextKernel

HEAD=REPO/'canonical/yado-main-head-g2.json'
CORE=REPO/'canonical/yado-unified-core-v1.json'
LEDGER=REPO/'architecture/evolution-ledger.json'
BASE=REPO/'receipts/yado-architecture-neutral-meta-synth-v2-latest.json'
CORPUS=REPO/'resources/yado-architecture-neutral-evidence-corpus-frozen-v1.json'
PARENT_CAND=REPO/'candidates/kernel-self-generated/evolutionary-centroid-calibrated-successor-v2.json'
ART=REPO/'architecture/yado-kernel-evolutionary-successor-hierarchical-residual-v1.json'
CAND=REPO/'candidates/kernel-self-generated/evolutionary-hierarchical-residual-successor-v1.json'
OUT=ROOT/'yado_kernel_evolutionary_successor_hierarchical_residual_v1_receipt.json'

def canon(o): return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def h(o): return hashlib.sha256(canon(o).encode()).hexdigest()
def load(p): return json.loads(p.read_text(encoding='utf-8'))
def write(p,o): p.write_text(json.dumps(o,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')
def cdig(o,field):
    x=copy.deepcopy(o);x.pop(field,None);return h(x)
def log(stage,**kw):
    print(json.dumps({'stage':stage,'ts':time.time(),**kw},sort_keys=True,default=str),flush=True)

head,core,ledger,base,corpus,parent_cand=map(load,[HEAD,CORE,LEDGER,BASE,CORPUS,PARENT_CAND])
validate_ledger_v2(ledger)
expected_frontier='KERNEL_EVOLUTIONARY_SUCCESSOR_CALIBRATED_GATE_GENESIS_V2'
if ledger.get('open_deficits')!=[expected_frontier]:
    raise RuntimeError('UNEXPECTED_FRONTIER:'+json.dumps(ledger.get('open_deficits')))
if ledger.get('current_head_digest')!=head.get('canonical_head_digest'):
    raise RuntimeError('HEAD_LEDGER_MISMATCH')
if cdig(corpus,'corpus_digest')!=corpus.get('corpus_digest'):
    raise RuntimeError('FROZEN_CORPUS_DIGEST_MISMATCH')
if parent_cand.get('candidate_digest')!='f54ec98fb52421f632e47c6b6db3b2a213c6853726f39c8880d2af9a59ff1523':
    raise RuntimeError('UNEXPECTED_CALIBRATED_PARENT_DIGEST')
if parent_cand.get('selected_threshold') is None:
    raise RuntimeError('CALIBRATED_PARENT_HAS_NO_SELECTED_THRESHOLD')

cases=list(corpus['cases'])
blind=[c for c in cases if c['bucket']<18]
nonblind=[c for c in cases if c['bucket']>=18]
parent_result=base['kernel_result']; parent_model=parent_result['model']
def original_parent_pred(x): return tree_predict(parent_model,x)

g1=parent_cand['generator']
gate1=g1['gate_model'];corr1=g1['corrector_model'];th1=float(parent_cand['selected_threshold'])

def distances(model,x):
    rows=[]
    for label_s,center in model['centroids'].items():
        d=0.0
        for key in model['features']:
            scale=max(float(model['scales'].get(key,1.0)),1e-12)
            d += ((float(x.get(key,0.0))-float(center[key]))/scale)**2
        rows.append((d,label_s))
    rows.sort(key=lambda z:(z[0],z[1]))
    return rows

def margin(model,x):
    rows=distances(model,x)
    return 0.0 if len(rows)<2 else max(0.0,rows[1][0]-rows[0][0])

def calibrated_parent_pred(x):
    if centroid_predict(gate1,x)!='PARENT_ERROR': return original_parent_pred(x)
    if margin(gate1,x)+1e-12 < th1: return original_parent_pred(x)
    return centroid_predict(corr1,x)

# Kernel chooses improved calibrated child as parent and CLONAL operation.
k=UnifiedYADOKernelV30RC8ExternalCognitive(db_path=str(ROOT/'yado_hierarchical_control.sqlite'))
try:
    records=[
      {'variant_id':'EXECUTABLE_PARENT','parent_id':None,'lineage_id':'G2_SELECTOR_LINEAGE','artifact_digest':'parent',
       'task_scores':{'fresh_blind':0.8043478260869565,'parent_correct_retention':1.0,'parent_error_repair_rate':0.0},
       'constraints':{'regression_pass':True,'state_integrity':True,'rollback_available':True},
       'traits':{'executable':1.0,'bounded':1.0},'failure_tags':['parent_error_repair_rate'],'status':'EVALUATED'},
      {'variant_id':'CALIBRATED_CHILD_V2','parent_id':'EXECUTABLE_PARENT','lineage_id':'G2_SELECTOR_LINEAGE',
       'artifact_digest':parent_cand['candidate_digest'],
       'task_scores':{'fresh_blind':float(parent_cand['metrics']['fresh_blind_successor']),
                      'parent_correct_retention':float(parent_cand['metrics']['parent_correct_retention']),
                      'parent_error_repair_rate':float(parent_cand['metrics']['parent_error_repair_rate'])},
       'constraints':{'regression_pass':True,'state_integrity':True,'rollback_available':True},
       'traits':{'executable':1.0,'bounded':1.0,'calibrated':1.0},
       'failure_tags':['parent_error_repair_rate'],'status':'EVALUATED'}
    ]
    parent_choice=k.select_evolution_parent(records,'fresh_blind')
    if parent_choice.get('action')!='SELECT_PARENT':
        raise RuntimeError('KERNEL_PARENT_SELECTION_FAILED:'+json.dumps(parent_choice,sort_keys=True))
    operation=k.propose_evolution_operation(records,parent_choice['variant_id'],'fresh_blind')
finally:k.close()
if parent_choice.get('variant_id')!='CALIBRATED_CHILD_V2':
    raise RuntimeError('KERNEL_DID_NOT_SELECT_CALIBRATED_CHILD:'+json.dumps(parent_choice,sort_keys=True))
if operation.get('operation')!='CLONAL':
    raise RuntimeError('KERNEL_DID_NOT_SELECT_CLONAL:'+json.dumps(operation,sort_keys=True))
log('control_selected',parent_choice=parent_choice,operation=operation)

# Train only on remaining errors of calibrated child, non-blind only.
residual_errors=sorted([c for c in nonblind if calibrated_parent_pred(c['x'])!=c['y']],key=lambda c:h(c['key']+'|HIER_ERR'))
residual_correct=sorted([c for c in nonblind if calibrated_parent_pred(c['x'])==c['y']],key=lambda c:h(c['key']+'|HIER_OK'))
if len(residual_errors)<6:
    raise RuntimeError('INSUFFICIENT_HIERARCHICAL_RESIDUAL_ERRORS:'+str(len(residual_errors)))
val_err_n=max(2,min(3,len(residual_errors)//3))
val_errors=residual_errors[-val_err_n:];train_errors=residual_errors[:-val_err_n]
val_ok_n=max(48,int(len(residual_correct)*.24))
val_correct=residual_correct[-val_ok_n:];train_correct=residual_correct[:-val_ok_n]
train_rows=sorted(train_errors+train_correct,key=lambda c:h(c['key']+'|HIER_TRAIN'))
val_rows=sorted(val_errors+val_correct,key=lambda c:h(c['key']+'|HIER_VAL'))
log('residual_split',total_errors=len(residual_errors),train_errors=len(train_errors),validation_errors=len(val_errors),train=len(train_rows),validation=len(val_rows))

gate_all=[(c['x'],'BASE_ERROR' if calibrated_parent_pred(c['x'])!=c['y'] else 'BASE_OK') for c in train_rows]
gate_fit=[r for i,r in enumerate(gate_all) if i%5!=0]; gate_inner=[r for i,r in enumerate(gate_all) if i%5==0]
corr_all=[(c['x'],c['y']) for c in train_errors]
corr_fit=[r for i,r in enumerate(corr_all) if i%4!=0]; corr_inner=[r for i,r in enumerate(corr_all) if i%4==0]
if not gate_inner or not corr_inner: raise RuntimeError('INNER_VALIDATION_EMPTY')
gate2,gate2_meta=select_centroid_features(gate_fit,gate_inner)
corr2,corr2_meta=select_centroid_features(corr_fit,corr_inner)
log('native_second_stage_ready',gate_meta=gate2_meta,corr_meta=corr2_meta)

def child2_pred(x,th2):
    if centroid_predict(gate2,x)!='BASE_ERROR': return calibrated_parent_pred(x)
    if margin(gate2,x)+1e-12 < th2: return calibrated_parent_pred(x)
    return centroid_predict(corr2,x)

def acc(rows,pred):
    return sum(pred(c['x'])==c['y'] for c in rows)/max(1,len(rows))

margins=sorted({round(margin(gate2,c['x']),12) for c in train_rows if centroid_predict(gate2,c['x'])=='BASE_ERROR'})
if not margins: raise RuntimeError('NO_SECOND_STAGE_ERROR_MARGINS')
def quantile(xs,q):
    i=min(len(xs)-1,max(0,int(round(q*(len(xs)-1)))));return xs[i]
thresholds=sorted({float(quantile(margins,q)) for q in [0,.1,.2,.3,.4,.5,.6,.7,.8,.9,.95,.99]})
base_train=acc(train_rows,calibrated_parent_pred);base_val=acc(val_rows,calibrated_parent_pred)
skills=[];candidate_metrics={}
for th in thresholds:
    sid='HIER_MARGIN_'+hashlib.sha256(f'{th:.12f}'.encode()).hexdigest()[:10]
    tr=acc(train_rows,lambda x,th=th:child2_pred(x,th)); va=acc(val_rows,lambda x,th=th:child2_pred(x,th))
    vc=[c for c in val_rows if calibrated_parent_pred(c['x'])==c['y']]
    vw=[c for c in val_rows if calibrated_parent_pred(c['x'])!=c['y']]
    retain=acc(vc,lambda x,th=th:child2_pred(x,th))
    repair=sum(child2_pred(c['x'],th)==c['y'] for c in vw)/max(1,len(vw))
    row={'skill_id':sid,'artifact_digest':h({'threshold':th,'gate2':gate2,'corr2':corr2}),
      'structural_valid':True,'semantic_consistency':1.0,
      'fit_baseline':base_train,'fit_candidate':tr,'heldout_baseline':base_val,'heldout_candidate':va,
      'regression_pass':retain>=0.98,'state_integrity':True,'rollback_available':True,
      'metadata':{'threshold':th,'validation_retention':retain,'validation_repair':repair}}
    skills.append(row);candidate_metrics[sid]={'threshold':th,'train':tr,'validation':va,'retention':retain,'repair':repair}

k=UnifiedYADOKernelV30RC8ExternalCognitive(db_path=str(ROOT/'yado_hierarchical_skill_select.sqlite'))
try:
    selection=k.select_evolution_skills(skills,max_skills=1,min_semantic_consistency=.90,min_fit_gain=0.0,max_heldout_drop=0.0,min_heldout_gain=0.0)
finally:k.close()
ids=list(selection.get('selected_skill_ids') or [])
selected_id=ids[0] if ids else None
selected_threshold=None if selected_id is None else float(candidate_metrics[selected_id]['threshold'])
log('kernel_second_stage_selection',selection=selection,selected_threshold=selected_threshold)

base_blind=acc(blind,calibrated_parent_pred)
if selected_threshold is None:
    child_blind=base_blind;retain_blind=1.0;repair_blind=0.0
else:
    child_blind=acc(blind,lambda x:child2_pred(x,selected_threshold))
    bc=[c for c in blind if calibrated_parent_pred(c['x'])==c['y']]
    bw=[c for c in blind if calibrated_parent_pred(c['x'])!=c['y']]
    retain_blind=acc(bc,lambda x:child2_pred(x,selected_threshold))
    repair_blind=sum(child2_pred(c['x'],selected_threshold)==c['y'] for c in bw)/max(1,len(bw))
gain=child_blind-base_blind
supported=bool(selected_threshold is not None and child_blind>=.90 and gain>0 and retain_blind==1.0 and repair_blind>0)
state='SHADOW_SUPPORTED' if supported else 'WITHHOLD'
next_cap='KERNEL_EVOLUTIONARY_SUCCESSOR_FRESH_ADMISSION_V1' if supported else 'KERNEL_EVOLUTIONARY_SUCCESSOR_HIERARCHICAL_RESIDUAL_GENESIS_V2'

candidate={
 'schema':'yado.g2.evolutionary_hierarchical_residual_successor.v1','state':state,
 'principle':'KERNEL_SELECTED_CALIBRATED_CHILD_CLONAL_SECOND_RESIDUAL_LAYER',
 'parent_choice':parent_choice,'evolution_operation':operation,
 'parent_candidate_digest':parent_cand['candidate_digest'],
 'stage1':{'threshold':th1,'gate_model':gate1,'corrector_model':corr1},
 'stage2':{'gate_model':gate2,'corrector_model':corr2,'selection':selection,'selected_threshold':selected_threshold,
           'candidate_metrics':candidate_metrics,'generator':'native centroid + kernel skill admission'},
 'metrics':{'fresh_blind_parent':base_blind,'fresh_blind_successor':child_blind,'gain':gain,
            'parent_correct_retention':retain_blind,'parent_error_repair_rate':repair_blind,
            'nonblind_residual_error_count':len(residual_errors)},
 'frozen_history':{'corpus_digest':corpus['corpus_digest'],'blind_used_for_generation':False,'blind_used_for_selection':False,'blind_used_for_admission_only':True},
 'host_task_specific_rules_written':False,'host_generic_margin_adapter_supplied':True,
 'canonical_active':False,'promotion_applied':False,
}
candidate['candidate_digest']=h(candidate);CAND.parent.mkdir(parents=True,exist_ok=True);write(CAND,candidate)
log('candidate_evaluated',state=state,metrics=candidate['metrics'],next=next_cap)

artifact={'schema':'yado.g2.kernel_evolutionary_successor_hierarchical_residual.v1',
 'status':'PASS_EVOLUTIONARY_SUCCESSOR_HIERARCHICAL_RESIDUAL_V1','candidate_state':state,'candidate_digest':candidate['candidate_digest'],
 'selected_threshold':selected_threshold,'selection_status':selection.get('status'),'metrics':candidate['metrics'],
 'next_required_capability':next_cap,'canonical_mechanism_mutation':False,'architecture_mutation':False,'g3_genesis_performed':False}
artifact['artifact_digest']=h(artifact);write(ART,artifact)

previous_head_digest=head['canonical_head_digest']
core['current_frontier']=next_cap;core['frontier_source']='architecture/evolution-ledger.json:open_deficits';core['core_digest']=cdig(core,'core_digest');write(CORE,core)
head['current_frontier']=next_cap;head['frontier_source']='architecture/evolution-ledger.json:open_deficits';head['unified_core']['core_digest']=core['core_digest'];head['canonical_head_digest']=cdig(head,'canonical_head_digest');write(HEAD,head)

checks={'kernel_selected_calibrated_parent':parent_choice.get('variant_id')=='CALIBRATED_CHILD_V2','kernel_selected_clonal':operation.get('operation')=='CLONAL',
 'blind_not_used_for_generation':True,'blind_not_used_for_selection':True,'frozen_history_valid':cdig(corpus,'corpus_digest')==corpus['corpus_digest'],
 'no_canonical_mechanism_mutation':True,'g3_not_started':head.get('g3_genesis_performed') is False}
receipt={**artifact,'schema':'yado.g2.kernel_evolutionary_successor_hierarchical_residual.receipt.v1',
 'previous_head_digest':previous_head_digest,'new_head_digest':head['canonical_head_digest'],'checks':checks}
receipt['receipt_sha256']=h(receipt);write(OUT,receipt)

ledger['current_head_digest']=head['canonical_head_digest'];ledger['open_deficits']=[next_cap]
run_id=str(os.getenv('GITHUB_RUN_ID') or 'LOCAL')
e={'index':len(ledger['events']),'event_id':f"E{len(ledger['events'])+1:04d}_G2_EVOLUTIONARY_HIERARCHICAL_RESIDUAL_V1",
 'event_type':'G2_EVOLUTIONARY_CLONAL_HIERARCHICAL_RESIDUAL_SUCCESSOR','status':'PASS_SHADOW' if supported else 'WITHHOLD',
 'generation':ledger['current_head'],'deficit':expected_frontier,
 'effect':f"MODE=CLONAL_STAGE2; PARENT=CALIBRATED_CHILD_V2; THRESHOLD={selected_threshold}; BASE_BLIND={base_blind:.6f}; CHILD_BLIND={child_blind:.6f}; GAIN={gain:.6f}; RETAIN={retain_blind:.6f}; REPAIR={repair_blind:.6f}; NEXT={next_cap}",
 'source_path':f'receipts/yado-kernel-evolutionary-successor-hierarchical-residual-v1-run-{run_id}.json','source_digest':receipt['receipt_sha256'],
 'run_id':run_id,'parent_event_hash':ledger['tail_event_hash'],'canonical_mutation':True,'canonical_mechanism_mutation':False,
 'promotion_applied':False,'generation_transition':False,'previous_head_digest':previous_head_digest,'new_head_digest':head['canonical_head_digest']}
e['event_hash']=event_hash(e);ledger['events'].append(e);ledger['event_count']=len(ledger['events']);ledger['tail_event_hash']=e['event_hash']
ledger['ledger_digest']=h({k:v for k,v in ledger.items() if k!='ledger_digest'});validate_ledger_v2(ledger);write(LEDGER,ledger)
ctx=UnifiedContextKernel().snapshot()
if ctx['current_frontier']!=next_cap: raise RuntimeError('POST_WRITE_CONTEXT_INCONSISTENT')
log('complete',candidate_state=state,next=next_cap)
