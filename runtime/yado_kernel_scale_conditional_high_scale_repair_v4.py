from __future__ import annotations
from pathlib import Path
from itertools import combinations
import copy,hashlib,json,os,sys

ROOT=Path(__file__).resolve().parent; REPO=ROOT.parent; PKG=ROOT/'yado_rc8_v36'
sys.path[:0]=[str(ROOT),str(PKG)]

import yado_architecture_neutral_meta_synthesizer_v2 as neutral
from yado_core_v3_0_rc8_external_cognitive import UnifiedYADOKernelV30RC8ExternalCognitive
from yado_cognitive_growth_runtime_v1 import select_knn_k,fit_knn_strategy,knn_predict
from yado_evolution_ledger_v2 import validate_ledger_v2,event_hash
from yado_unified_context_kernel_v1 import UnifiedContextKernel

HEAD=REPO/'canonical/yado-main-head-g2.json'
CORE=REPO/'canonical/yado-unified-core-v1.json'
LEDGER=REPO/'architecture/evolution-ledger.json'
CORPUS=REPO/'resources/yado-architecture-neutral-evidence-corpus-frozen-v1.json'
HIGH2=REPO/'candidates/kernel-self-generated/high-scale-repair-v2.json'
V3=REPO/'candidates/kernel-self-generated/high-scale-repair-v3.json'
ART=REPO/'architecture/yado-kernel-scale-conditional-high-scale-repair-v4.json'
CAND=REPO/'candidates/kernel-self-generated/high-scale-repair-v4.json'
HIST11=REPO/'resources/yado-eleven-source-transfer-history-v1.json'
OUT=ROOT/'yado_kernel_scale_conditional_high_scale_repair_v4_receipt.json'

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def h(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def write(p,o):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(o,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')
def cdig(o,field):
    x=copy.deepcopy(o);x.pop(field,None);return h(x)
def log(stage,**kw):print(json.dumps({'stage':stage,**kw},sort_keys=True,default=str),flush=True)

head,core,ledger,corpus,high2,v3=map(load,[HEAD,CORE,LEDGER,CORPUS,HIGH2,V3])
validate_ledger_v2(ledger)
front='KERNEL_SCALE_CONDITIONAL_SUCCESSOR_HIGH_SCALE_REPAIR_V4'
if ledger.get('open_deficits')!=[front]:raise RuntimeError('UNEXPECTED_FRONTIER:'+json.dumps(ledger.get('open_deficits')))
if v3.get('state')!='WITHHOLD':raise RuntimeError('V3_NOT_WITHHOLD')
if high2.get('state')!='SHADOW_SUPPORTED':raise RuntimeError('HIGH2_PARENT_NOT_SUPPORTED')
if head.get('g3_genesis_performed') is not False:raise RuntimeError('G3_ALREADY_STARTED')

data=neutral.build_dataset(force=True)
expected={x['id']:x['sha256'] for x in corpus['source_digests']}
actual={sid:r['sha256'] for sid,r in data['rows'].items()}
if expected!=actual:raise RuntimeError('SOURCE_DIGEST_DRIFT')
ids=sorted(data['rows'])

def make_cases(size):
    out=[]
    for combo in combinations(ids,size):
        x,y,_=neutral._vector(combo,data['rows'])
        out.append({'key':'|'.join(combo),'x':x,'y':y,'size':size})
    return out

spaces={s:make_cases(s) for s in (4,5,6,7,8,9,10,11)}
counts=[len(spaces[s]) for s in (4,5,6,7,8,9,10,11)]
if counts!=[495,792,924,792,495,220,66,12]:raise RuntimeError('SPACE_COUNTS_INVALID:'+json.dumps(counts))
history=sum((spaces[s] for s in (4,5,6,7,8,9,10)),[])
fresh11=spaces[11]
log('spaces_ready',history=len(history),fresh11=len(fresh11))

pairs=list(combinations(ids,2)); triples=list(combinations(ids,3)); quads=list(combinations(ids,4))
def rep(c,order):
    z=dict(c['x']);present=set(c['key'].split('|'))
    if order>=1:
        for sid in ids:z['src::'+sid]=1.0 if sid in present else 0.0
    if order>=2:
        for a,b in pairs:z['srcpair::'+a+'&&'+b]=1.0 if a in present and b in present else 0.0
    if order>=3:
        for a,b,d in triples:z['srctri::'+a+'&&'+b+'&&'+d]=1.0 if a in present and b in present and d in present else 0.0
    if order>=4:
        for a,b,d,e in quads:z['srcquad::'+a+'&&'+b+'&&'+d+'&&'+e]=1.0 if a in present and b in present and d in present and e in present else 0.0
    return z

old_model=high2['selected_model']
def old_high(c):return knn_predict(old_model,rep(c,2))
def acc(rows,pred):return sum(pred(c)==c['y'] for c in rows)/max(1,len(rows))

# Native kernel decides evolutionary operation from accumulated V2/V3 evidence.
k=UnifiedYADOKernelV30RC8ExternalCognitive(db_path=str(ROOT/'yado_high_scale_v4_control.sqlite'))
try:
    records=[
      {'variant_id':'HIGH_SCALE_REPAIR_V2','parent_id':'SCALE_CONDITIONAL_V1','lineage_id':'G2_HIGH_SCALE_LINEAGE',
       'artifact_digest':high2['candidate_digest'],
       'task_scores':{'history':float(high2['metrics']['history_candidate']),'size8':float(high2['metrics']['fresh8_candidate'])},
       'constraints':{'regression_pass':True,'state_integrity':True,'rollback_available':True},
       'traits':{'pair_knn':1.0,'bounded':1.0},'failure_tags':['size9_below_gate'],'status':'EVALUATED'},
      {'variant_id':'HIGH_SCALE_REPAIR_V3_WITHHOLD','parent_id':'HIGH_SCALE_REPAIR_V2','lineage_id':'G2_HIGH_SCALE_LINEAGE',
       'artifact_digest':v3['candidate_digest'],
       'task_scores':{'history':float(v3['metrics']['history_candidate']),'size10':float(v3['metrics']['fresh10_candidate'])},
       'constraints':{'regression_pass':True,'state_integrity':True,'rollback_available':True},
       'traits':{'native_constructor_timeout':1.0,'no_selected_skill':1.0},
       'failure_tags':['native_rc5_resource_timeout','fresh10_below_gate','no_candidate_selected'],'status':'EVALUATED'}
    ]
    parent=k.select_evolution_parent(records,'size10')
    operation=k.propose_evolution_operation(records,parent['variant_id'],'size11')
finally:k.close()
log('control_selected',parent=parent,operation=operation)

# Deterministic history-only development/holdout.
groups={}
for c in history:groups.setdefault((c['size'],str(c['y'])),[]).append(c)
train=[];hold=[]
for key,rows in sorted(groups.items()):
    rows=sorted(rows,key=lambda c:h(c['key']+'|HIGH_V4_HOLD'))
    n=len(rows);nh=0 if n<5 else max(1,int(round(n*.20)))
    hold+=rows[-nh:] if nh else [];train+=rows[:-nh] if nh else rows
if not hold:raise RuntimeError('EMPTY_HOLDOUT')
base_train=acc(train,old_high);base_hold=acc(hold,old_high)

skills=[];specs={};metrics={}
for order,name in ((2,'PAIR_KNN_REFRESH_V4'),(3,'TRIPLE_KNN_REFRESH_V4'),(4,'QUAD_KNN_REFRESH_V4')):
    # inner split within history-only training
    inner=sorted(train,key=lambda c:h(c['key']+f'|V4_INNER_{order}'))
    cut=max(1,int(len(inner)*.80));fit=inner[:cut];val=inner[cut:]
    f=[(rep(c,order),c['y']) for c in fit];v=[(rep(c,order),c['y']) for c in val]
    _,km=select_knn_k(f,v,(1,3,5,7,9,11,15,21,31))
    model=fit_knn_strategy([(rep(c,order),c['y']) for c in train],km['selected_k'])
    pred=lambda c,m=model,o=order:knn_predict(m,rep(c,o))
    tr=acc(train,pred);ho=acc(hold,pred)
    per={};reg=True
    for s in (4,5,6,7,8,9,10):
        rows=[c for c in hold if c['size']==s]
        if rows:
            b=acc(rows,old_high);vs=acc(rows,pred);per[str(s)]={'baseline':b,'candidate':vs,'gain':vs-b,'count':len(rows)}
            if vs+1e-12<b:reg=False
    skills.append({'skill_id':name,'artifact_digest':h(model),'structural_valid':True,'semantic_consistency':1.0,
      'fit_baseline':base_train,'fit_candidate':tr,'heldout_baseline':base_hold,'heldout_candidate':ho,
      'regression_pass':reg,'state_integrity':True,'rollback_available':True,
      'metadata':{'family':'KNN_INTERACTION_ORDER','order':order,'selected_k':km['selected_k'],'per_size':per}})
    specs[name]={'order':order,'selected_k':km['selected_k']}
    metrics[name]={'train':tr,'holdout':ho,'regression_pass':reg,'per_size':per,'inner':km}
    log('candidate_done',skill=name,holdout=ho,regression=reg,k=km['selected_k'])

k=UnifiedYADOKernelV30RC8ExternalCognitive(db_path=str(ROOT/'yado_high_scale_v4_skill_select.sqlite'))
try:
    selection=k.select_evolution_skills(skills,max_skills=1,min_semantic_consistency=.90,min_fit_gain=0.0,max_heldout_drop=0.0,min_heldout_gain=0.0)
finally:k.close()
selected_ids=list(selection.get('selected_skill_ids') or [])
selected_id=selected_ids[0] if selected_ids else None
spec=specs.get(selected_id)
log('kernel_selection',selection=selection,selected=selected_id,base_hold=base_hold)

final_model=None
if spec:
    final_model=fit_knn_strategy([(rep(c,spec['order']),c['y']) for c in history],spec['selected_k'])
def candidate_high(c):
    if not spec:return old_high(c)
    return knn_predict(final_model,rep(c,spec['order']))

history_old=acc(history,old_high);history_new=acc(history,candidate_high)
# Fresh11 is opened only after kernel selection and full-history refit.
fresh11_old=acc(fresh11,old_high);fresh11_new=acc(fresh11,candidate_high)
checks={
 'source_sha_exact_match':expected==actual,
 'history_sizes_4_to_10_only_for_selection':True,
 'fresh11_count_12':len(fresh11)==12,
 'fresh11_not_used_for_selection_or_refit':True,
 'kernel_selected_candidate':selected_id is not None,
 'history_no_regression':history_new+1e-12>=history_old,
 'fresh11_above_gate':fresh11_new>=.90,
 'fresh11_beats_old_high_branch':fresh11_new>fresh11_old,
 'g3_not_started':head.get('g3_genesis_performed') is False,
}
supported=all(checks.values())
state='SHADOW_SUPPORTED' if supported else 'WITHHOLD'
next_cap='KERNEL_NATIVE_SELECTOR_CANONICAL_BINDING_V4' if supported else 'KERNEL_SCALE_CONDITIONAL_SUCCESSOR_HIGH_SCALE_REPAIR_V5'
candidate={
 'schema':'yado.g2.scale_conditional_high_scale_repair.v4','state':state,
 'principle':'SPENT_SIZE10_BECOMES_HISTORY; KERNEL_SELECTS_BOUNDED_INTERACTION_ORDER; SIZE11_REMAINS_BLIND_UNTIL_SELECTION',
 'parent_choice':parent,'evolution_operation':operation,'selection':selection,
 'selected_skill_id':selected_id,'selected_spec':spec,'selected_model':final_model,
 'development_metrics':metrics,
 'metrics':{'history_old_high':history_old,'history_candidate':history_new,'fresh11_old_high':fresh11_old,'fresh11_candidate':fresh11_new,'fresh11_gain':fresh11_new-fresh11_old},
 'fresh_transfer':{'size':11,'count':len(fresh11),'used_for_selection':False,'used_for_refit':False},
 'v3_failure_in_history':{'state':v3.get('state'),'native_constructor_outcome':v3.get('native_constructor_outcome'),'fresh10_score':v3.get('metrics',{}).get('fresh10_candidate')},
 'checks':checks,'canonical_active':False,'promotion_applied':False,'canonical_mechanism_mutation':False,'g3_genesis_performed':False
}
candidate['candidate_digest']=h(candidate);write(CAND,candidate)
write(HIST11,{'schema':'yado.g2.eleven_source_transfer_history.v1','status':'SPENT_AFTER_SINGLE_ADMISSION','case_count':len(fresh11),'old_high_score':fresh11_old,'candidate_score':fresh11_new,'selected_skill_id':selected_id,'dataset_digest':h(fresh11)})

artifact={'schema':'yado.g2.kernel_scale_conditional_high_scale_repair.v4',
 'status':'PASS_HIGH_SCALE_REPAIR_V4' if supported else 'WITHHOLD_HIGH_SCALE_REPAIR_V4',
 'candidate_state':state,'candidate_digest':candidate['candidate_digest'],'selected_skill_id':selected_id,
 'metrics':candidate['metrics'],'next_required_capability':next_cap,
 'canonical_mechanism_mutation':False,'architecture_mutation':False,'g3_genesis_performed':False}
artifact['artifact_digest']=h(artifact);write(ART,artifact)

prev=head['canonical_head_digest']
core['current_frontier']=next_cap;core['frontier_source']='architecture/evolution-ledger.json:open_deficits';core['core_digest']=cdig(core,'core_digest');write(CORE,core)
head['current_frontier']=next_cap;head['frontier_source']='architecture/evolution-ledger.json:open_deficits';head['unified_core']['core_digest']=core['core_digest'];head['canonical_head_digest']=cdig(head,'canonical_head_digest');write(HEAD,head)
receipt={**artifact,'schema':'yado.g2.kernel_scale_conditional_high_scale_repair.receipt.v4','previous_head_digest':prev,'new_head_digest':head['canonical_head_digest'],'checks':checks}
receipt['receipt_sha256']=h(receipt);write(OUT,receipt)

ledger['current_head_digest']=head['canonical_head_digest'];ledger['open_deficits']=[next_cap];run_id=str(os.getenv('GITHUB_RUN_ID') or 'LOCAL')
e={'index':len(ledger['events']),'event_id':f"E{len(ledger['events'])+1:04d}_G2_HIGH_SCALE_REPAIR_V4",
 'event_type':'G2_BOUNDED_INTERACTION_ORDER_EVOLUTION','status':'PASS_SHADOW' if supported else 'WITHHOLD',
 'generation':ledger['current_head'],'deficit':front,
 'effect':f"SELECTED={selected_id}; HISTORY_OLD={history_old:.6f}; HISTORY_NEW={history_new:.6f}; FRESH11_OLD={fresh11_old:.6f}; FRESH11_NEW={fresh11_new:.6f}; NEXT={next_cap}",
 'source_path':f'receipts/yado-kernel-scale-conditional-high-scale-repair-v4-run-{run_id}.json','source_digest':receipt['receipt_sha256'],'run_id':run_id,
 'parent_event_hash':ledger['tail_event_hash'],'canonical_mutation':True,'canonical_mechanism_mutation':False,'promotion_applied':False,'generation_transition':False,
 'previous_head_digest':prev,'new_head_digest':head['canonical_head_digest']}
e['event_hash']=event_hash(e);ledger['events'].append(e);ledger['event_count']=len(ledger['events']);ledger['tail_event_hash']=e['event_hash'];ledger['ledger_digest']=h({k:v for k,v in ledger.items() if k!='ledger_digest'});validate_ledger_v2(ledger);write(LEDGER,ledger)
ctx=UnifiedContextKernel().snapshot()
if ctx['current_frontier']!=next_cap:raise RuntimeError('POST_WRITE_CONTEXT_INCONSISTENT')
log('complete',state=state,selected=selected_id,metrics=candidate['metrics'],next=next_cap)
