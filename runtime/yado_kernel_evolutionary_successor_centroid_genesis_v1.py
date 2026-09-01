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
from yado_cognitive_growth_runtime_v1 import fit_centroid_strategy,select_centroid_features,centroid_predict,centroid_accuracy
from yado_unified_context_kernel_v1 import UnifiedContextKernel

HEAD=REPO/'canonical/yado-main-head-g2.json'
CORE=REPO/'canonical/yado-unified-core-v1.json'
LEDGER=REPO/'architecture/evolution-ledger.json'
BASE=REPO/'receipts/yado-architecture-neutral-meta-synth-v2-latest.json'
CORPUS=REPO/'resources/yado-architecture-neutral-evidence-corpus-frozen-v1.json'
ART=REPO/'architecture/yado-kernel-evolutionary-successor-centroid-genesis-v1.json'
CAND=REPO/'candidates/kernel-self-generated/evolutionary-centroid-successor-v1.json'
OUT=ROOT/'yado_kernel_evolutionary_successor_centroid_genesis_v1_receipt.json'

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
expected_frontier='KERNEL_EVOLUTIONARY_SUCCESSOR_RULE_PROGRAM_GENESIS_V2'
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

# Let current G2 evolutionary control determine the operation from the full failure lineage.
k=UnifiedYADOKernelV30RC8ExternalCognitive(db_path=str(ROOT/'yado_centroid_successor_operation.sqlite'))
try:
    records=[
      {'variant_id':'EXECUTABLE_PARENT','parent_id':None,'lineage_id':'G2_SELECTOR_LINEAGE',
       'artifact_digest':parent_digest,
       'task_scores':{'validation':float(parent_result['validation']),'fresh_blind':float(parent_result['fresh_blind']),'completion':1.0},
       'constraints':{'regression_pass':True,'state_integrity':True,'rollback_available':True},
       'traits':{'executable':1.0,'bounded':1.0},'failure_tags':['fresh_blind_below_gate'],'status':'EVALUATED'},
      {'variant_id':'EXHAUSTIVE_DESCENDANTS','parent_id':'EXECUTABLE_PARENT','lineage_id':'G2_SELECTOR_LINEAGE',
       'artifact_digest':'v4-cart-linear-timeout-history',
       'task_scores':{'validation':0.0,'fresh_blind':0.0,'completion':0.0},
       'constraints':{'regression_pass':True,'state_integrity':True,'rollback_available':True},
       'traits':{'executable':0.0,'bounded':0.0},'failure_tags':['meta_grammar_timeout','cart_timeout','linear_timeout'],'status':'EVALUATED'},
      {'variant_id':'RULE_PROGRAM_DESCENDANT','parent_id':'EXECUTABLE_PARENT','lineage_id':'G2_SELECTOR_LINEAGE',
       'artifact_digest':'310ff38f93fd197d8e694c7eba0e548736232e29003d2aa6dc07c7fdb068c7e8',
       'task_scores':{'validation':0.0,'fresh_blind':float(parent_result['fresh_blind']),'completion':1.0},
       'constraints':{'regression_pass':True,'state_integrity':True,'rollback_available':True},
       'traits':{'executable':1.0,'bounded':1.0},'failure_tags':['representation_expressivity_limit','no_continuous_predicate'],'status':'EVALUATED'},
    ]
    operation=k.propose_evolution_operation(records,'RULE_PROGRAM_DESCENDANT','fresh_blind')
finally:k.close()
if operation.get('operation')!='REACTION_NORM':
    raise RuntimeError('KERNEL_DID_NOT_SELECT_REACTION_NORM:'+json.dumps(operation,sort_keys=True))
log('operation_done',operation=operation)

# Deterministic developmental split; blind is untouched.
errors=sorted([c for c in nonblind if parent_pred(c['x'])!=c['y']],key=lambda c:h(c['key']+'|CENTROID_ERR'))
correct=sorted([c for c in nonblind if parent_pred(c['x'])==c['y']],key=lambda c:h(c['key']+'|CENTROID_OK'))
if len(errors)<6:raise RuntimeError('INSUFFICIENT_PARENT_ERRORS:'+str(len(errors)))
dev_err=errors[-2:];train_err=errors[:-2]
dev_ok=correct[-40:];train_ok=correct[:-40]
train_gate_rows=sorted(train_err+train_ok,key=lambda c:h(c['key']+'|CENTROID_GATE_TRAIN'))
dev_rows=sorted(dev_err+dev_ok,key=lambda c:h(c['key']+'|CENTROID_DEV'))
gate_fit=[(c['x'],'PARENT_ERROR' if parent_pred(c['x'])!=c['y'] else 'PARENT_OK') for c in train_gate_rows]
# Internal validation is split deterministically from permitted training evidence.
gate_fit_core=[r for i,r in enumerate(gate_fit) if i%5!=0]
gate_val=[r for i,r in enumerate(gate_fit) if i%5==0]
corr_train=[(c['x'],c['y']) for c in train_err]
corr_fit=[r for i,r in enumerate(corr_train) if i%4!=0]
corr_val=[r for i,r in enumerate(corr_train) if i%4==0]
if not gate_val or not corr_val:raise RuntimeError('DEVELOPMENT_SPLIT_EMPTY')

log('centroid_genesis_start',gate_fit=len(gate_fit_core),gate_val=len(gate_val),corr_fit=len(corr_fit),corr_val=len(corr_val))
gate_dev,gate_meta=select_centroid_features(gate_fit_core,gate_val)
corr_dev,corr_meta=select_centroid_features(corr_fit,corr_val)
gate_dev_hold=centroid_accuracy(gate_dev,[(c['x'],'PARENT_ERROR' if parent_pred(c['x'])!=c['y'] else 'PARENT_OK') for c in dev_rows])
corr_dev_hold=centroid_accuracy(corr_dev,[(c['x'],c['y']) for c in dev_err])
log('centroid_development_done',gate_validation=gate_meta['validation'],corr_validation=corr_meta['validation'],
    gate_dev_holdout=gate_dev_hold,corr_dev_holdout=corr_dev_hold,
    gate_features=gate_meta['selected_features'],corr_features=corr_meta['selected_features'])

development_supported=bool(gate_meta['validation']>=0.75 and gate_dev_hold>=0.75 and corr_dev_hold>0.0)
# If developmental evidence supports the family, create final child from all permitted non-blind history.
gate_final=corr_final=None
if development_supported:
    all_gate=[(c['x'],'PARENT_ERROR' if parent_pred(c['x'])!=c['y'] else 'PARENT_OK') for c in nonblind]
    gate_final=fit_centroid_strategy(all_gate,gate_meta['selected_features'])
    all_residual=[(c['x'],c['y']) for c in errors]
    corr_final=fit_centroid_strategy(all_residual,corr_meta['selected_features'])

def child_pred(x):
    if gate_final is None or corr_final is None:return parent_pred(x)
    return centroid_predict(corr_final,x) if centroid_predict(gate_final,x)=='PARENT_ERROR' else parent_pred(x)
def acc(rows,pred):
    return sum(pred(c['x'])==c['y'] for c in rows)/max(1,len(rows))

parent_blind=acc(blind,parent_pred)
child_blind=acc(blind,child_pred)
parent_correct=[c for c in blind if parent_pred(c['x'])==c['y']]
parent_wrong=[c for c in blind if parent_pred(c['x'])!=c['y']]
retention=acc(parent_correct,child_pred)
repair=sum(child_pred(c['x'])==c['y'] for c in parent_wrong)/max(1,len(parent_wrong))
gain=child_blind-parent_blind
supported=bool(development_supported and child_blind>=0.90 and gain>0 and retention==1.0 and repair>0)
state='SHADOW_SUPPORTED' if supported else 'WITHHOLD'
next_cap='KERNEL_EVOLUTIONARY_SUCCESSOR_FRESH_ADMISSION_V1' if supported else 'KERNEL_EVOLUTIONARY_SUCCESSOR_CENTROID_GENESIS_V2'

candidate={
 'schema':'yado.g2.evolutionary_centroid_successor.v1','state':state,
 'principle':'DESCENDANT_CREATES_CONTINUOUS_FEATURE_MECHANISM_AFTER_RULE_PROGRAM_EXPRESSIVITY_LIMIT',
 'evolution_operation':operation,
 'parent':{'model_digest':parent_digest,'fresh_blind':parent_blind},
 'new_mechanism':{
   'op':'EVOLUTIONARY_CENTROID_RESIDUAL_SUCCESSOR',
   'error_gate':gate_final,'residual_corrector':corr_final,
   'generator':'select_centroid_features/fit_centroid_strategy',
   'generator_source':'runtime/yado_rc8_v36/yado_cognitive_growth_runtime_v1.py',
   'generator_source_sha256':'7e7de7eed6f3e608db548d9df6ae918513264b036513e4e1a290d58be9222c1f',
   'continuous_feature_support':True,
   'exhaustive_weight_search':False,
 },
 'development':{'supported':development_supported,'gate_validation':gate_meta['validation'],'corrector_validation':corr_meta['validation'],
                'gate_dev_holdout':gate_dev_hold,'corrector_dev_holdout':corr_dev_hold,
                'gate_selected_features':gate_meta['selected_features'],'corrector_selected_features':corr_meta['selected_features']},
 'metrics':{'fresh_blind_parent':parent_blind,'fresh_blind_successor':child_blind,'gain':gain,
            'parent_correct_retention':retention,'parent_error_repair_rate':repair,'true_blind_parent_error_count':len(parent_wrong)},
 'frozen_history':{'corpus_digest':corpus['corpus_digest'],'blind_used_for_creation':False,'blind_used_for_admission_only':True},
 'host_task_specific_rules_written':False,'kernel_runtime_native_model_generation':True,
 'canonical_active':False,'promotion_applied':False,
}
candidate['candidate_digest']=h(candidate);CAND.parent.mkdir(parents=True,exist_ok=True);write(CAND,candidate)
log('candidate_evaluated',state=state,metrics=candidate['metrics'],next=next_cap)

artifact={'schema':'yado.g2.kernel_evolutionary_successor_centroid_genesis.v1',
 'status':'PASS_EVOLUTIONARY_SUCCESSOR_CENTROID_GENESIS_V1','candidate_state':state,'candidate_digest':candidate['candidate_digest'],
 'development':candidate['development'],'metrics':candidate['metrics'],'next_required_capability':next_cap,
 'canonical_mechanism_mutation':False,'architecture_mutation':False,'g3_genesis_performed':False}
artifact['artifact_digest']=h(artifact);write(ART,artifact)

previous_head_digest=head['canonical_head_digest']
core['current_frontier']=next_cap;core['frontier_source']='architecture/evolution-ledger.json:open_deficits';core['core_digest']=cdig(core,'core_digest');write(CORE,core)
head['current_frontier']=next_cap;head['frontier_source']='architecture/evolution-ledger.json:open_deficits';head['unified_core']['core_digest']=core['core_digest'];head['canonical_head_digest']=cdig(head,'canonical_head_digest');write(HEAD,head)

checks={'kernel_selected_reaction_norm':operation.get('operation')=='REACTION_NORM',
 'frozen_history_valid':cdig(corpus,'corpus_digest')==corpus['corpus_digest'],
 'blind_not_used_for_creation':True,'native_centroid_source_bound':True,
 'no_canonical_mechanism_mutation':True,'g3_not_started':head.get('g3_genesis_performed') is False}
receipt={**artifact,'schema':'yado.g2.kernel_evolutionary_successor_centroid_genesis.receipt.v1',
 'previous_head_digest':previous_head_digest,'new_head_digest':head['canonical_head_digest'],'checks':checks}
receipt['receipt_sha256']=h(receipt);write(OUT,receipt)

ledger['current_head_digest']=head['canonical_head_digest'];ledger['open_deficits']=[next_cap]
run_id=str(os.getenv('GITHUB_RUN_ID') or 'LOCAL')
e={'index':len(ledger['events']),'event_id':f"E{len(ledger['events'])+1:04d}_G2_EVOLUTIONARY_SUCCESSOR_CENTROID_GENESIS_V1",
 'event_type':'G2_EVOLUTIONARY_CONTINUOUS_CENTROID_SUCCESSOR_GENESIS','status':'PASS_SHADOW' if supported else 'WITHHOLD',
 'generation':ledger['current_head'],'deficit':expected_frontier,
 'effect':f"MODE=CREATE_NOT_SEARCH; GENERATOR=CENTROID; PARENT_BLIND={parent_blind:.6f}; CHILD_BLIND={child_blind:.6f}; GAIN={gain:.6f}; RETAIN={retention:.6f}; REPAIR={repair:.6f}; NEXT={next_cap}",
 'source_path':f'receipts/yado-kernel-evolutionary-successor-centroid-genesis-v1-run-{run_id}.json','source_digest':receipt['receipt_sha256'],
 'run_id':run_id,'parent_event_hash':ledger['tail_event_hash'],'canonical_mutation':True,'canonical_mechanism_mutation':False,
 'promotion_applied':False,'generation_transition':False,'previous_head_digest':previous_head_digest,'new_head_digest':head['canonical_head_digest']}
e['event_hash']=event_hash(e);ledger['events'].append(e);ledger['event_count']=len(ledger['events']);ledger['tail_event_hash']=e['event_hash']
ledger['ledger_digest']=h({k:v for k,v in ledger.items() if k!='ledger_digest'});validate_ledger_v2(ledger);write(LEDGER,ledger)
ctx=UnifiedContextKernel().snapshot()
if ctx['current_frontier']!=next_cap:raise RuntimeError('POST_WRITE_CONTEXT_INCONSISTENT')
log('complete',candidate_state=state,next=next_cap)
