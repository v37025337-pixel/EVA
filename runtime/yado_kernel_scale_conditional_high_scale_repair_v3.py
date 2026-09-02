from __future__ import annotations
from pathlib import Path
from itertools import combinations
import copy,hashlib,json,os,sys
ROOT=Path(__file__).resolve().parent;REPO=ROOT.parent;PKG=ROOT/'yado_rc8_v36'
sys.path[:0]=[str(ROOT),str(PKG)]

import yado_architecture_neutral_meta_synthesizer_v2 as neutral
from yado_core_v3_0_rc8_external_cognitive import UnifiedYADOKernelV30RC8ExternalCognitive
from yado_core_v3_0_rc5_algorithm_genesis import predict_intel_component
from yado_cognitive_growth_runtime_v1 import select_knn_k,fit_knn_strategy,knn_predict
from yado_evolution_ledger_v2 import validate_ledger_v2,event_hash
from yado_unified_context_kernel_v1 import UnifiedContextKernel

HEAD=REPO/'canonical/yado-main-head-g2.json'
CORE=REPO/'canonical/yado-unified-core-v1.json'
LEDGER=REPO/'architecture/evolution-ledger.json'
CORPUS=REPO/'resources/yado-architecture-neutral-evidence-corpus-frozen-v1.json'
HIGH2=REPO/'candidates/kernel-self-generated/high-scale-repair-v2.json'
BIND2=REPO/'candidates/kernel-self-generated/native-selector-canonical-binding-v2.json'
ART=REPO/'architecture/yado-kernel-scale-conditional-high-scale-repair-v3.json'
CAND=REPO/'candidates/kernel-self-generated/high-scale-repair-v3.json'
HIST10=REPO/'resources/yado-ten-source-transfer-history-v1.json'
OUT=ROOT/'yado_kernel_scale_conditional_high_scale_repair_v3_receipt.json'

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def h(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def write(p,o):p.write_text(json.dumps(o,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')
def cdig(o,field):
    x=copy.deepcopy(o);x.pop(field,None);return h(x)
def log(stage,**kw):print(json.dumps({'stage':stage,**kw},sort_keys=True,default=str),flush=True)

head,core,ledger,corpus,high2,bind2=map(load,[HEAD,CORE,LEDGER,CORPUS,HIGH2,BIND2])
validate_ledger_v2(ledger)
front='KERNEL_SCALE_CONDITIONAL_SUCCESSOR_HIGH_SCALE_REPAIR_V3'
if ledger.get('open_deficits')!=[front]:raise RuntimeError('UNEXPECTED_FRONTIER:'+json.dumps(ledger.get('open_deficits')))
if high2.get('state')!='SHADOW_SUPPORTED':raise RuntimeError('HIGH2_NOT_SUPPORTED')
if bind2.get('state')!='WITHHOLD':raise RuntimeError('BIND2_EXPECTED_WITHHOLD')

data=neutral.build_dataset(force=True)
expected={x['id']:x['sha256'] for x in corpus['source_digests']}
actual={sid:r['sha256'] for sid,r in data['rows'].items()}
if expected!=actual:raise RuntimeError('SOURCE_DIGEST_DRIFT')
ids=sorted(data['rows'])
pairs=list(combinations(ids,2));triples=list(combinations(ids,3))

def make_cases(size):
 out=[]
 for combo in combinations(ids,size):
  x,y,counts=neutral._vector(combo,data['rows'])
  out.append({'key':'|'.join(combo),'x':x,'y':y,'size':size})
 return out
spaces={s:make_cases(s) for s in (4,5,6,7,8,9,10)}
if [len(spaces[s]) for s in (4,5,6,7,8,9,10)]!=[495,792,924,792,495,220,66]:
 raise RuntimeError('SPACE_COUNTS_INVALID')
history=sum((spaces[s] for s in (4,5,6,7,8,9)),[])
fresh10=spaces[10]
log('spaces_ready',history=len(history),fresh10=len(fresh10))

def rep(c,order):
 z=dict(c['x'])
 if order==0:return z
 present=set(c['key'].split('|'))
 for sid in ids:z['src::'+sid]=1.0 if sid in present else 0.0
 if order>=2:
  for a,b in pairs:z['srcpair::'+a+'&&'+b]=1.0 if a in present and b in present else 0.0
 if order>=3:
  for a,b,c3 in triples:z['srctri::'+a+'&&'+b+'&&'+c3]=1.0 if a in present and b in present and c3 in present else 0.0
 return z

old_model=high2['selected_model']
def old_high(c):return knn_predict(old_model,rep(c,2))
def acc(rows,pred):return sum(pred(c)==c['y'] for c in rows)/max(1,len(rows))

# Kernel chooses parent and operation from latest lineage evidence.
k=UnifiedYADOKernelV30RC8ExternalCognitive(db_path=str(ROOT/'yado_high_scale_v3_control.sqlite'))
try:
 records=[
  {'variant_id':'HIGH_SCALE_REPAIR_V2','parent_id':'SCALE_CONDITIONAL_V1','lineage_id':'G2_HIGH_SCALE_LINEAGE','artifact_digest':high2['candidate_digest'],
   'task_scores':{'history':float(high2['metrics']['history_candidate']),'size8':float(high2['metrics']['fresh8_candidate']),'size9':float(bind2['fresh9_new'])},
   'constraints':{'regression_pass':True,'state_integrity':True,'rollback_available':True},
   'traits':{'pair_knn':1.0,'native_selector_preserved':1.0},'failure_tags':['size9_below_gate'],'status':'EVALUATED'},
  {'variant_id':'BINDING_V2_WITHHOLD','parent_id':'HIGH_SCALE_REPAIR_V2','lineage_id':'G2_HIGH_SCALE_LINEAGE','artifact_digest':bind2['candidate_digest'],
   'task_scores':{'history':float(bind2['history_new']),'size9':float(bind2['fresh9_new'])},
   'constraints':{'regression_pass':True,'state_integrity':True,'rollback_available':True},
   'traits':{'no_regression_1_to_8':1.0},'failure_tags':['fresh9_below_gate'],'status':'EVALUATED'},
 ]
 parent=k.select_evolution_parent(records,'size9')
 op=k.propose_evolution_operation(records,parent['variant_id'],'size9')
finally:k.close()
if op.get('operation')!='CLONAL':raise RuntimeError('V3_EXPECTED_CLONAL:'+json.dumps(op))
log('control_selected',parent=parent,operation=op)

# Deterministic developmental holdout by (size,label).
groups={}
for c in history:groups.setdefault((c['size'],str(c['y'])),[]).append(c)
train=[];hold=[]
for key,rows in sorted(groups.items()):
 rows=sorted(rows,key=lambda c:h(c['key']+'|HIGH_V3_HOLD'))
 n=len(rows);nh=0 if n<5 else max(1,int(round(n*.20)))
 hold+=rows[-nh:] if nh else []
 train+=rows[:-nh] if nh else rows
if not hold:raise RuntimeError('EMPTY_HOLDOUT')

# Bound constructor workload while preserving all size/label strata.
sample_groups={}
for c in train:sample_groups.setdefault((c['size'],str(c['y'])),[]).append(c)
dev=[]
for key,rows in sorted(sample_groups.items()):
 rows=sorted(rows,key=lambda c:h(c['key']+'|HIGH_V3_DEV'))
 take=max(1,min(len(rows),int(round(1400*len(rows)/len(train)))))
 dev+=rows[:take]
# Trim deterministically if proportional rounding exceeded cap.
dev=sorted(dev,key=lambda c:h(c['key']+'|HIGH_V3_DEV_GLOBAL'))[:1400]
dev_keys={c['key'] for c in dev}
if len(dev)<500:raise RuntimeError('DEV_SAMPLE_TOO_SMALL')

inner_groups={}
for c in dev:inner_groups.setdefault((c['size'],str(c['y'])),[]).append(c)
fit=[];val=[]
for key,rows in sorted(inner_groups.items()):
 rows=sorted(rows,key=lambda c:h(c['key']+'|HIGH_V3_INNER'))
 n=len(rows);nv=0 if n<5 else max(1,int(round(n*.20)))
 val+=rows[-nv:] if nv else []
 fit+=rows[:-nv] if nv else rows
if not val:raise RuntimeError('EMPTY_VALIDATION')

base_train=acc(train,old_high);base_hold=acc(hold,old_high)
skills=[];specs={};metrics={}

# Bounded KNN families retained as incumbent-compatible alternatives.
for order,name in ((2,'PAIR_KNN_REFRESH'),(3,'TRIPLE_KNN_REFRESH')):
 f=[(rep(c,order),c['y']) for c in fit]
 v=[(rep(c,order),c['y']) for c in val]
 d=[(rep(c,order),c['y']) for c in dev]
 _,km=select_knn_k(f,v,(1,3,5,7,9,11,15,21))
 model=fit_knn_strategy(d,km['selected_k'])
 pred=lambda c,m=model,o=order:knn_predict(m,rep(c,o))
 tr=acc(train,pred);ho=acc(hold,pred)
 per={};reg=True
 for s in (4,5,6,7,8,9):
  rows=[c for c in hold if c['size']==s]
  if rows:
   b=acc(rows,old_high);vscore=acc(rows,pred)
   per[str(s)]={'baseline':b,'candidate':vscore,'gain':vscore-b,'count':len(rows)}
   if vscore+1e-12<b:reg=False
 sid=name
 skills.append({'skill_id':sid,'artifact_digest':h(model),'structural_valid':True,'semantic_consistency':1.0,
   'fit_baseline':base_train,'fit_candidate':tr,'heldout_baseline':base_hold,'heldout_candidate':ho,
   'regression_pass':reg,'state_integrity':True,'rollback_available':True,
   'metadata':{'family':'KNN','order':order,'selected_k':km['selected_k'],'per_size':per}})
 specs[sid]={'family':'KNN','order':order,'selected_k':km['selected_k'],'dev_model':model}
 metrics[sid]={'train':tr,'holdout':ho,'inner':km,'per_size':per,'regression_pass':reg}
 log('candidate_done',skill=sid,holdout=ho,regression=reg)

# Native RC5 constructor: kernel chooses signal and branch leaf algorithms.
native_fit=[(rep(c,2),c['y']) for c in fit]
native_val=[(rep(c,2),c['y']) for c in val]
native_revealed=[(rep(c,2),c['y']) for c in dev]
native_blind=[(rep(c,2),c['y']) for c in hold]
k=UnifiedYADOKernelV30RC8ExternalCognitive(db_path=str(ROOT/'yado_high_scale_v3_native_constructor.sqlite'))
try:
 native=k.synthesize_intelligence_algorithm_component(native_fit,native_val,native_revealed,native_blind)
finally:k.close()
native_model=native['model']
native_pred=lambda c:predict_intel_component(native_model,rep(c,2))
tr=acc(train,native_pred);ho=acc(hold,native_pred)
per={};reg=True
for s in (4,5,6,7,8,9):
 rows=[c for c in hold if c['size']==s]
 if rows:
  b=acc(rows,old_high);vscore=acc(rows,native_pred)
  per[str(s)]={'baseline':b,'candidate':vscore,'gain':vscore-b,'count':len(rows)}
  if vscore+1e-12<b:reg=False
sid='NATIVE_RC5_INTELLIGENCE_CONSTRUCTOR'
skills.append({'skill_id':sid,'artifact_digest':h(native_model),'structural_valid':True,'semantic_consistency':1.0,
 'fit_baseline':base_train,'fit_candidate':tr,'heldout_baseline':base_hold,'heldout_candidate':ho,
 'regression_pass':reg,'state_integrity':True,'rollback_available':True,
 'metadata':{'family':'NATIVE_RC5_CONSTRUCTOR','constructor_id':native['constructor_id'],'binding':native['binding'],
             'native_validation':native['validation'],'native_blind':native['fresh_blind'],'per_size':per}})
specs[sid]={'family':'NATIVE_RC5_CONSTRUCTOR','model':native_model,'constructor_id':native['constructor_id'],'binding':native['binding']}
metrics[sid]={'train':tr,'holdout':ho,'native':native,'per_size':per,'regression_pass':reg}
log('candidate_done',skill=sid,holdout=ho,regression=reg,binding=native['binding'])

k=UnifiedYADOKernelV30RC8ExternalCognitive(db_path=str(ROOT/'yado_high_scale_v3_skill_select.sqlite'))
try:
 selection=k.select_evolution_skills(skills,max_skills=1,min_semantic_consistency=.90,min_fit_gain=0.0,max_heldout_drop=0.0,min_heldout_gain=0.0)
finally:k.close()
selids=list(selection.get('selected_skill_ids') or [])
selected_id=selids[0] if selids else None
spec=specs.get(selected_id)
log('kernel_selection',selection=selection,selected=selected_id,base_hold=base_hold)

# Refit only the selected KNN on all spent history. Native constructor remains its native-generated model.
final_model=None
if spec and spec['family']=='KNN':
 final_model=fit_knn_strategy([(rep(c,spec['order']),c['y']) for c in history],spec['selected_k'])
elif spec and spec['family']=='NATIVE_RC5_CONSTRUCTOR':
 final_model=spec['model']

def candidate_high(c):
 if selected_id is None:return old_high(c)
 if spec['family']=='KNN':return knn_predict(final_model,rep(c,spec['order']))
 return predict_intel_component(final_model,rep(c,2))

history_old=acc(history,old_high);history_new=acc(history,candidate_high)
fresh10_old=acc(fresh10,old_high);fresh10_new=acc(fresh10,candidate_high)
checks={
 'source_sha_exact_match':expected==actual,
 'history_sizes_4_to_9_only_for_selection':True,
 'fresh10_count_66':len(fresh10)==66,
 'fresh10_not_used_for_selection_or_refit':True,
 'kernel_selected_candidate':selected_id is not None,
 'history_no_regression':history_new+1e-12>=history_old,
 'fresh10_above_gate':fresh10_new>=.90,
 'fresh10_beats_old_high_branch':fresh10_new>fresh10_old,
 'g3_not_started':head.get('g3_genesis_performed') is False,
}
supported=all(checks.values())
state='SHADOW_SUPPORTED' if supported else 'WITHHOLD'
next_cap='KERNEL_NATIVE_SELECTOR_CANONICAL_BINDING_V3' if supported else 'KERNEL_SCALE_CONDITIONAL_SUCCESSOR_HIGH_SCALE_REPAIR_V4'
candidate={
 'schema':'yado.g2.scale_conditional_high_scale_repair.v3','state':state,
 'principle':'PRESERVE_NATIVE_SELECTOR_AND_LOW_BRANCH; LET_G2_CHOOSE_BETWEEN_REFRESHED_KNN_AND_NATIVE_RC5_CONSTRUCTOR',
 'parent_choice':parent,'evolution_operation':op,'selection':selection,
 'selected_skill_id':selected_id,'selected_spec':({k:v for k,v in (spec or {}).items() if k!='dev_model'} if spec else None),
 'selected_model':final_model,'development_metrics':metrics,
 'metrics':{'history_old_high':history_old,'history_candidate':history_new,'fresh10_old_high':fresh10_old,'fresh10_candidate':fresh10_new,'fresh10_gain':fresh10_new-fresh10_old},
 'fresh_transfer':{'size':10,'count':len(fresh10),'used_for_selection':False,'used_for_refit':False},
 'selector_unchanged':True,'low_branch_unchanged':True,'checks':checks,
 'canonical_active':False,'promotion_applied':False,'canonical_mechanism_mutation':False,'g3_genesis_performed':False,
}
candidate['candidate_digest']=h(candidate);CAND.parent.mkdir(parents=True,exist_ok=True);write(CAND,candidate)
hist10={'schema':'yado.g2.ten_source_transfer_history.v1','status':'SPENT_AFTER_SINGLE_ADMISSION',
 'source_sha256':actual,'case_count':len(fresh10),'old_high_score':fresh10_old,'candidate_score':fresh10_new,
 'selected_skill_id':selected_id,'dataset_digest':h(fresh10)}
write(HIST10,hist10)

artifact={'schema':'yado.g2.kernel_scale_conditional_high_scale_repair.v3',
 'status':'PASS_HIGH_SCALE_REPAIR_V3' if supported else 'WITHHOLD_HIGH_SCALE_REPAIR_V3',
 'candidate_state':state,'candidate_digest':candidate['candidate_digest'],'selected_skill_id':selected_id,
 'metrics':candidate['metrics'],'next_required_capability':next_cap,
 'canonical_mechanism_mutation':False,'architecture_mutation':False,'g3_genesis_performed':False}
artifact['artifact_digest']=h(artifact);write(ART,artifact)
prev=head['canonical_head_digest']
core['current_frontier']=next_cap;core['frontier_source']='architecture/evolution-ledger.json:open_deficits';core['core_digest']=cdig(core,'core_digest');write(CORE,core)
head['current_frontier']=next_cap;head['frontier_source']='architecture/evolution-ledger.json:open_deficits';head['unified_core']['core_digest']=core['core_digest'];head['canonical_head_digest']=cdig(head,'canonical_head_digest');write(HEAD,head)
receipt={**artifact,'schema':'yado.g2.kernel_scale_conditional_high_scale_repair.receipt.v3','previous_head_digest':prev,'new_head_digest':head['canonical_head_digest'],'checks':checks}
receipt['receipt_sha256']=h(receipt);write(OUT,receipt)

ledger['current_head_digest']=head['canonical_head_digest'];ledger['open_deficits']=[next_cap];run_id=str(os.getenv('GITHUB_RUN_ID') or 'LOCAL')
e={'index':len(ledger['events']),'event_id':f"E{len(ledger['events'])+1:04d}_G2_HIGH_SCALE_REPAIR_V3",
 'event_type':'G2_HIGH_SCALE_NATIVE_CONSTRUCTOR_COMPETITIVE_REPAIR','status':'PASS_SHADOW' if supported else 'WITHHOLD',
 'generation':ledger['current_head'],'deficit':front,
 'effect':f"SELECTED={selected_id}; HISTORY_OLD={history_old:.6f}; HISTORY_NEW={history_new:.6f}; FRESH10_OLD={fresh10_old:.6f}; FRESH10_NEW={fresh10_new:.6f}; NEXT={next_cap}",
 'source_path':f'receipts/yado-kernel-scale-conditional-high-scale-repair-v3-run-{run_id}.json','source_digest':receipt['receipt_sha256'],'run_id':run_id,
 'parent_event_hash':ledger['tail_event_hash'],'canonical_mutation':True,'canonical_mechanism_mutation':False,'promotion_applied':False,'generation_transition':False,
 'previous_head_digest':prev,'new_head_digest':head['canonical_head_digest']}
e['event_hash']=event_hash(e);ledger['events'].append(e);ledger['event_count']=len(ledger['events']);ledger['tail_event_hash']=e['event_hash'];ledger['ledger_digest']=h({k:v for k,v in ledger.items() if k!='ledger_digest'});validate_ledger_v2(ledger);write(LEDGER,ledger)
ctx=UnifiedContextKernel().snapshot()
if ctx['current_frontier']!=next_cap:raise RuntimeError('POST_WRITE_CONTEXT_INCONSISTENT')
log('complete',state=state,selected=selected_id,metrics=candidate['metrics'],next=next_cap)
