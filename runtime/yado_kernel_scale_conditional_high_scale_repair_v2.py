from __future__ import annotations
from pathlib import Path
from itertools import combinations
import copy,hashlib,json,os,sys
ROOT=Path(__file__).resolve().parent;REPO=ROOT.parent;PKG=ROOT/'yado_rc8_v36'
sys.path[:0]=[str(ROOT),str(PKG)]

import yado_architecture_neutral_meta_synthesizer_v2 as neutral
from yado_core_v3_0_rc8_external_cognitive import UnifiedYADOKernelV30RC8ExternalCognitive
from yado_cognitive_growth_runtime_v1 import select_centroid_features,fit_centroid_strategy,centroid_predict,select_knn_k,fit_knn_strategy,knn_predict
from yado_evolution_ledger_v2 import validate_ledger_v2,event_hash
from yado_unified_context_kernel_v1 import UnifiedContextKernel

HEAD=REPO/'canonical/yado-main-head-g2.json'
CORE=REPO/'canonical/yado-unified-core-v1.json'
LEDGER=REPO/'architecture/evolution-ledger.json'
CORPUS=REPO/'resources/yado-architecture-neutral-evidence-corpus-frozen-v1.json'
F4=REPO/'candidates/kernel-self-generated/fresh-four-source-curriculum-v1.json'
SCALE=REPO/'candidates/kernel-self-generated/scale-conditional-pair-knn-successor-v1.json'
BIND_FAIL=REPO/'candidates/kernel-self-generated/native-selector-canonical-binding-v1.json'
ART=REPO/'architecture/yado-kernel-scale-conditional-high-scale-repair-v2.json'
CAND=REPO/'candidates/kernel-self-generated/high-scale-repair-v2.json'
HIST8=REPO/'resources/yado-eight-source-transfer-history-v1.json'
OUT=ROOT/'yado_kernel_scale_conditional_high_scale_repair_v2_receipt.json'

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def h(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def write(p,o):p.write_text(json.dumps(o,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')
def cdig(o,field):
    x=copy.deepcopy(o);x.pop(field,None);return h(x)
def log(stage,**kw):print(json.dumps({'stage':stage,**kw},sort_keys=True,default=str),flush=True)

head,core,ledger,corpus,f4,scale,bind_fail=map(load,[HEAD,CORE,LEDGER,CORPUS,F4,SCALE,BIND_FAIL])
validate_ledger_v2(ledger)
front='KERNEL_SCALE_CONDITIONAL_SUCCESSOR_HIGH_SCALE_REPAIR_V2'
if ledger.get('open_deficits')!=[front]:raise RuntimeError('UNEXPECTED_FRONTIER:'+json.dumps(ledger.get('open_deficits')))
if scale.get('state')!='SHADOW_SUPPORTED':raise RuntimeError('SCALE_PARENT_NOT_SUPPORTED')
if bind_fail.get('state')!='WITHHOLD':raise RuntimeError('EXPECTED_SIZE7_BINDING_WITHHOLD')

data=neutral.build_dataset(force=True)
expected={x['id']:x['sha256'] for x in corpus['source_digests']}
actual={sid:r['sha256'] for sid,r in data['rows'].items()}
if expected!=actual:raise RuntimeError('SOURCE_DIGEST_DRIFT')
ids=sorted(data['rows'])

def make_cases(size):
    out=[]
    for combo in combinations(ids,size):
        x,y,counts=neutral._vector(combo,data['rows'])
        out.append({'key':'|'.join(combo),'x':x,'y':y,'size':size})
    return out

spaces={s:make_cases(s) for s in (4,5,6,7,8)}
if [len(spaces[s]) for s in (4,5,6,7,8)]!=[495,792,924,792,495]:
    raise RuntimeError('HIGH_SCALE_COUNTS_INVALID')
history=sum((spaces[s] for s in (4,5,6,7)),[])
fresh8=spaces[8]
log('spaces_ready',history=len(history),fresh8=len(fresh8))

source_ids=ids
pairs=list(combinations(source_ids,2))
triples=list(combinations(source_ids,3))
def rep(c,order):
    if order==0:return dict(c['x'])
    z=dict(c['x']);present=set(c['key'].split('|'))
    for sid in source_ids:z['src::'+sid]=1.0 if sid in present else 0.0
    if order>=2:
        for a,b in pairs:z['srcpair::'+a+'&&'+b]=1.0 if a in present and b in present else 0.0
    if order>=3:
        for a,b,c3 in triples:z['srctri::'+a+'&&'+b+'&&'+c3]=1.0 if a in present and b in present and c3 in present else 0.0
    return z

old_model=f4['selected_model']
def old_high(c):return knn_predict(old_model,rep(c,2))
def acc(rows,pred):return sum(pred(c)==c['y'] for c in rows)/max(1,len(rows))

# Current G2 archive chooses parent and operation from the actual latest lineage.
k=UnifiedYADOKernelV30RC8ExternalCognitive(db_path=str(ROOT/'yado_high_scale_repair_control.sqlite'))
try:
    records=[
      {'variant_id':'FRESH_FOUR_PAIR_KNN_V1','parent_id':None,'lineage_id':'G2_HIGH_SCALE_LINEAGE','artifact_digest':f4['candidate_digest'],
       'task_scores':{'size5':0.9494949494949495,'size6':0.9047619047619048,'size7':0.8446969696969697},
       'constraints':{'regression_pass':True,'state_integrity':True,'rollback_available':True},
       'traits':{'pair_knn':1.0,'high_scale':1.0},'failure_tags':['size7_below_gate'],'status':'EVALUATED'},
      {'variant_id':'SCALE_CONDITIONAL_V1','parent_id':'FRESH_FOUR_PAIR_KNN_V1','lineage_id':'G2_HIGH_SCALE_LINEAGE','artifact_digest':scale['candidate_digest'],
       'task_scores':{'size5':0.9494949494949495,'size6':0.9047619047619048,'size7':0.8446969696969697},
       'constraints':{'regression_pass':True,'state_integrity':True,'rollback_available':True},
       'traits':{'native_selector':1.0,'low_scale_preserved':1.0},'failure_tags':['high_branch_size7_below_gate'],'status':'EVALUATED'},
      {'variant_id':'CANONICAL_BINDING_ATTEMPT_V1','parent_id':'SCALE_CONDITIONAL_V1','lineage_id':'G2_HIGH_SCALE_LINEAGE','artifact_digest':bind_fail['candidate_digest'],
       'task_scores':{'size7':float(bind_fail['fresh7_score']),'history':float(bind_fail['history16_score'])},
       'constraints':{'regression_pass':True,'state_integrity':True,'rollback_available':True},
       'traits':{'binding_exact':1.0},'failure_tags':['fresh7_below_gate'],'status':'EVALUATED'},
    ]
    parent=k.select_evolution_parent(records,'size7')
    op=k.propose_evolution_operation(records,parent['variant_id'],'size7')
finally:k.close()
if parent.get('variant_id') not in {'FRESH_FOUR_PAIR_KNN_V1','SCALE_CONDITIONAL_V1','CANONICAL_BINDING_ATTEMPT_V1'}:
    raise RuntimeError('UNSUPPORTED_KERNEL_PARENT:'+json.dumps(parent))
if op.get('operation')!='CLONAL':
    raise RuntimeError('EXPECTED_CLONAL_HIGH_SCALE_REPAIR:'+json.dumps(op))
log('control_selected',parent=parent,operation=op)

# Stratified developmental holdout by (size,label); size8 remains untouched.
groups={}
for c in history:groups.setdefault((c['size'],str(c['y'])),[]).append(c)
train=[];hold=[]
for key,rows in sorted(groups.items()):
    rows=sorted(rows,key=lambda c:h(c['key']+'|HIGH_V2_HOLD'))
    n=len(rows);nh=0 if n<4 else max(1,int(round(n*.20)))
    hold+=rows[-nh:] if nh else []
    train+=rows[:-nh] if nh else rows
groups2={}
for c in train:groups2.setdefault((c['size'],str(c['y'])),[]).append(c)
fitrows=[];valrows=[]
for key,rows in sorted(groups2.items()):
    rows=sorted(rows,key=lambda c:h(c['key']+'|HIGH_V2_INNER'))
    n=len(rows);nh=0 if n<5 else max(1,int(round(n*.20)))
    valrows+=rows[-nh:] if nh else []
    fitrows+=rows[:-nh] if nh else rows
if not hold or not valrows:raise RuntimeError('HIGH_SCALE_SPLIT_EMPTY')

base_train=acc(train,old_high);base_hold=acc(hold,old_high)
skills=[];specs={};metrics={}
for order,name in ((0,'RAW'),(2,'PAIR'),(3,'TRIPLE')):
    fit=[(rep(c,order),c['y']) for c in fitrows]
    val=[(rep(c,order),c['y']) for c in valrows]
    full=[(rep(c,order),c['y']) for c in train]

    _,km=select_knn_k(fit,val,(1,3,5,7,9,11,15))
    kf=fit_knn_strategy(full,km['selected_k'])
    tr=sum(knn_predict(kf,rep(c,order))==c['y'] for c in train)/len(train)
    ho=sum(knn_predict(kf,rep(c,order))==c['y'] for c in hold)/len(hold)
    per={}
    regression=True
    for s in (4,5,6,7):
        rows=[c for c in hold if c['size']==s]
        if rows:
            b=acc(rows,old_high);v=sum(knn_predict(kf,rep(c,order))==c['y'] for c in rows)/len(rows)
            per[str(s)]={'baseline':b,'candidate':v,'gain':v-b,'count':len(rows)}
            if v+1e-12<b:regression=False
    sid=name+'_KNN'
    skills.append({'skill_id':sid,'artifact_digest':h(kf),'structural_valid':True,'semantic_consistency':1.0,
      'fit_baseline':base_train,'fit_candidate':tr,'heldout_baseline':base_hold,'heldout_candidate':ho,
      'regression_pass':regression,'state_integrity':True,'rollback_available':True,
      'metadata':{'family':'KNN','order':order,'selected_k':km['selected_k'],'per_size':per}})
    specs[sid]={'family':'KNN','order':order,'selected_k':km['selected_k']}
    metrics[sid]={'train':tr,'holdout':ho,'inner':km,'per_size':per,'regression_pass':regression}

    _,cm=select_centroid_features(fit,val)
    cf=fit_centroid_strategy(full,cm['selected_features'])
    tr=sum(centroid_predict(cf,rep(c,order))==c['y'] for c in train)/len(train)
    ho=sum(centroid_predict(cf,rep(c,order))==c['y'] for c in hold)/len(hold)
    per={}
    regression=True
    for s in (4,5,6,7):
        rows=[c for c in hold if c['size']==s]
        if rows:
            b=acc(rows,old_high);v=sum(centroid_predict(cf,rep(c,order))==c['y'] for c in rows)/len(rows)
            per[str(s)]={'baseline':b,'candidate':v,'gain':v-b,'count':len(rows)}
            if v+1e-12<b:regression=False
    sid=name+'_CENTROID'
    skills.append({'skill_id':sid,'artifact_digest':h(cf),'structural_valid':True,'semantic_consistency':1.0,
      'fit_baseline':base_train,'fit_candidate':tr,'heldout_baseline':base_hold,'heldout_candidate':ho,
      'regression_pass':regression,'state_integrity':True,'rollback_available':True,
      'metadata':{'family':'CENTROID','order':order,'selected_features':cm['selected_features'],'per_size':per}})
    specs[sid]={'family':'CENTROID','order':order,'selected_features':cm['selected_features']}
    metrics[sid]={'train':tr,'holdout':ho,'inner':cm,'per_size':per,'regression_pass':regression}

k=UnifiedYADOKernelV30RC8ExternalCognitive(db_path=str(ROOT/'yado_high_scale_repair_skill_select.sqlite'))
try:
    selection=k.select_evolution_skills(skills,max_skills=1,min_semantic_consistency=.90,min_fit_gain=0.0,max_heldout_drop=0.0,min_heldout_gain=0.0)
finally:k.close()
selids=list(selection.get('selected_skill_ids') or [])
selected_id=selids[0] if selids else None
spec=specs.get(selected_id)
log('kernel_selection',selection=selection,selected=selected_id,base_hold=base_hold)

model=None
if spec:
    full=[(rep(c,spec['order']),c['y']) for c in history]
    if spec['family']=='KNN':model=fit_knn_strategy(full,spec['selected_k'])
    else:model=fit_centroid_strategy(full,spec['selected_features'])

def candidate_high(c):
    if model is None:return old_high(c)
    x=rep(c,spec['order'])
    return knn_predict(model,x) if spec['family']=='KNN' else centroid_predict(model,x)

# Fresh size8 opened only after kernel selection and refit.
fresh8_base=acc(fresh8,old_high)
fresh8_candidate=acc(fresh8,candidate_high)
history_base=acc(history,old_high)
history_candidate=acc(history,candidate_high)
gain=fresh8_candidate-fresh8_base
checks={
 'source_sha_exact_match':expected==actual,
 'history_sizes_4_to_7_only_for_selection':True,
 'fresh8_count_495':len(fresh8)==495,
 'fresh8_not_used_for_selection_or_refit':True,
 'kernel_selected_candidate':selected_id is not None,
 'history_no_regression':history_candidate+1e-12>=history_base,
 'fresh8_above_gate':fresh8_candidate>=.90,
 'fresh8_beats_old_high_branch':fresh8_candidate>fresh8_base,
 'g3_not_started':head.get('g3_genesis_performed') is False,
}
supported=all(checks.values())
state='SHADOW_SUPPORTED' if supported else 'WITHHOLD'
next_cap='KERNEL_NATIVE_SELECTOR_CANONICAL_BINDING_V2' if supported else 'KERNEL_SCALE_CONDITIONAL_SUCCESSOR_HIGH_SCALE_REPAIR_V3'

candidate={
 'schema':'yado.g2.scale_conditional_high_scale_repair.v2','state':state,
 'principle':'PRESERVE_NATIVE_SELECTOR_AND_LOW_BRANCH_REPAIR_ONLY_HIGH_SCALE_BRANCH_FROM_SPENT_4_TO_7_HISTORY',
 'parent_choice':parent,'evolution_operation':op,
 'selection':selection,'selected_skill_id':selected_id,'selected_spec':spec,'selected_model':model,
 'development_metrics':metrics,
 'metrics':{'history_old_high':history_base,'history_candidate':history_candidate,
            'fresh8_old_high':fresh8_base,'fresh8_candidate':fresh8_candidate,'fresh8_gain':gain},
 'fresh_transfer':{'size':8,'count':len(fresh8),'used_for_selection':False,'used_for_refit':False},
 'selector_unchanged':True,'low_branch_unchanged':True,'checks':checks,
 'canonical_active':False,'promotion_applied':False,'canonical_mechanism_mutation':False,'g3_genesis_performed':False,
}
candidate['candidate_digest']=h(candidate);CAND.parent.mkdir(parents=True,exist_ok=True);write(CAND,candidate)
hist8={'schema':'yado.g2.eight_source_transfer_history.v1','status':'SPENT_AFTER_SINGLE_ADMISSION',
 'source_sha256':actual,'case_count':len(fresh8),'old_high_score':fresh8_base,'candidate_score':fresh8_candidate,
 'selected_skill_id':selected_id,'dataset_digest':h(fresh8)}
write(HIST8,hist8)

artifact={'schema':'yado.g2.kernel_scale_conditional_high_scale_repair.v2',
 'status':'PASS_HIGH_SCALE_REPAIR_V2' if supported else 'WITHHOLD_HIGH_SCALE_REPAIR_V2',
 'candidate_state':state,'candidate_digest':candidate['candidate_digest'],'selected_skill_id':selected_id,
 'metrics':candidate['metrics'],'next_required_capability':next_cap,
 'canonical_mechanism_mutation':False,'architecture_mutation':False,'g3_genesis_performed':False}
artifact['artifact_digest']=h(artifact);write(ART,artifact)

prev=head['canonical_head_digest']
core['current_frontier']=next_cap;core['frontier_source']='architecture/evolution-ledger.json:open_deficits';core['core_digest']=cdig(core,'core_digest');write(CORE,core)
head['current_frontier']=next_cap;head['frontier_source']='architecture/evolution-ledger.json:open_deficits';head['unified_core']['core_digest']=core['core_digest'];head['canonical_head_digest']=cdig(head,'canonical_head_digest');write(HEAD,head)
receipt={**artifact,'schema':'yado.g2.kernel_scale_conditional_high_scale_repair.receipt.v2',
 'previous_head_digest':prev,'new_head_digest':head['canonical_head_digest'],'checks':checks}
receipt['receipt_sha256']=h(receipt);write(OUT,receipt)

ledger['current_head_digest']=head['canonical_head_digest'];ledger['open_deficits']=[next_cap];run_id=str(os.getenv('GITHUB_RUN_ID') or 'LOCAL')
e={'index':len(ledger['events']),'event_id':f"E{len(ledger['events'])+1:04d}_G2_HIGH_SCALE_REPAIR_V2",
 'event_type':'G2_SCALE_CONDITIONAL_HIGH_SCALE_BRANCH_REPAIR','status':'PASS_SHADOW' if supported else 'WITHHOLD',
 'generation':ledger['current_head'],'deficit':front,
 'effect':f"SELECTED={selected_id}; HISTORY_OLD={history_base:.6f}; HISTORY_NEW={history_candidate:.6f}; FRESH8_OLD={fresh8_base:.6f}; FRESH8_NEW={fresh8_candidate:.6f}; GAIN={gain:.6f}; SELECTOR_UNCHANGED=True; LOW_UNCHANGED=True; NEXT={next_cap}",
 'source_path':f'receipts/yado-kernel-scale-conditional-high-scale-repair-v2-run-{run_id}.json','source_digest':receipt['receipt_sha256'],'run_id':run_id,
 'parent_event_hash':ledger['tail_event_hash'],'canonical_mutation':True,'canonical_mechanism_mutation':False,'promotion_applied':False,'generation_transition':False,
 'previous_head_digest':prev,'new_head_digest':head['canonical_head_digest']}
e['event_hash']=event_hash(e);ledger['events'].append(e);ledger['event_count']=len(ledger['events']);ledger['tail_event_hash']=e['event_hash'];ledger['ledger_digest']=h({k:v for k,v in ledger.items() if k!='ledger_digest'});validate_ledger_v2(ledger);write(LEDGER,ledger)
ctx=UnifiedContextKernel().snapshot()
if ctx['current_frontier']!=next_cap:raise RuntimeError('POST_WRITE_CONTEXT_INCONSISTENT')
log('complete',state=state,selected=selected_id,metrics=candidate['metrics'],next=next_cap)
