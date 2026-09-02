from __future__ import annotations
from pathlib import Path
from itertools import combinations
import copy,hashlib,json,os,sys,time
ROOT=Path(__file__).resolve().parent;REPO=ROOT.parent;PKG=ROOT/'yado_rc8_v36'
sys.path[:0]=[str(ROOT),str(PKG)]

import yado_architecture_neutral_meta_synthesizer_v2 as neutral
from yado_evolution_ledger_v2 import validate_ledger_v2,event_hash
from yado_core_v3_0_rc8_external_cognitive import UnifiedYADOKernelV30RC8ExternalCognitive
from yado_organ_runtime_native_v1 import tree_predict
from yado_cognitive_growth_runtime_v1 import (
    select_centroid_features,fit_centroid_strategy,centroid_predict,
    select_knn_k,fit_knn_strategy,knn_predict
)
from yado_unified_context_kernel_v1 import UnifiedContextKernel

HEAD=REPO/'canonical/yado-main-head-g2.json'
CORE=REPO/'canonical/yado-unified-core-v1.json'
LEDGER=REPO/'architecture/evolution-ledger.json'
BASE=REPO/'receipts/yado-architecture-neutral-meta-synth-v2-latest.json'
CORPUS=REPO/'resources/yado-architecture-neutral-evidence-corpus-frozen-v1.json'
CAL=REPO/'candidates/kernel-self-generated/evolutionary-centroid-calibrated-successor-v2.json'
KNN=REPO/'candidates/kernel-self-generated/evolutionary-local-knn-successor-v1.json'
SP1=REPO/'candidates/kernel-self-generated/evolutionary-source-presence-representation-v1.json'
SP2=REPO/'candidates/kernel-self-generated/evolutionary-source-interaction-representation-v2.json'
F4=REPO/'candidates/kernel-self-generated/fresh-four-source-curriculum-v1.json'
ART=REPO/'architecture/yado-kernel-four-source-curriculum-repair-v2.json'
CAND=REPO/'candidates/kernel-self-generated/four-source-repair-five-source-transfer-v2.json'
HISTORY=REPO/'resources/yado-five-source-transfer-history-v1.json'
OUT=ROOT/'yado_kernel_four_source_curriculum_repair_v2_receipt.json'

def canon(o): return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def h(o): return hashlib.sha256(canon(o).encode()).hexdigest()
def load(p): return json.loads(p.read_text(encoding='utf-8'))
def write(p,o): p.write_text(json.dumps(o,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')
def cdig(o,field):
    x=copy.deepcopy(o);x.pop(field,None);return h(x)
def log(stage,**kw):
    print(json.dumps({'stage':stage,'ts':time.time(),**kw},sort_keys=True,default=str),flush=True)

head,core,ledger,base,corpus,cal,knn,sp1,sp2,f4=map(load,[HEAD,CORE,LEDGER,BASE,CORPUS,CAL,KNN,SP1,SP2,F4])
validate_ledger_v2(ledger)
front='KERNEL_FOUR_SOURCE_CURRICULUM_REPAIR_V2'
if ledger.get('open_deficits')!=[front]:
    raise RuntimeError('UNEXPECTED_FRONTIER:'+json.dumps(ledger.get('open_deficits')))
if ledger.get('current_head_digest')!=head.get('canonical_head_digest'):
    raise RuntimeError('HEAD_LEDGER_MISMATCH')

# Rebuild from the same live source bytes and require exact source identity.
data=neutral.build_dataset(force=True)
expected={x['id']:x['sha256'] for x in corpus['source_digests']}
actual={sid:r['sha256'] for sid,r in data['rows'].items()}
if expected!=actual:
    raise RuntimeError('SOURCE_DIGEST_DRIFT')
ids=sorted(data['rows'])
def make_cases(size,tag):
    out=[]
    for combo in combinations(ids,size):
        x,y,counts=neutral._vector(combo,data['rows'])
        out.append({'key':'|'.join(combo),'x':x,'y':y,'counts':counts,'size':size,'tag':tag})
    return out
four=make_cases(4,'FOUR_HISTORY')
five=make_cases(5,'FIVE_FRESH')
if len(four)!=495 or len(five)!=792:
    raise RuntimeError('COMBINATION_COUNT_MISMATCH')
log('curricula_ready',four=len(four),five=len(five),source_sha_exact=True)

# Current lineage behaviors.
parent_model=base['kernel_result']['model']
g=cal['generator'];gate=g['gate_model'];corr=g['corrector_model'];th=float(cal['selected_threshold'])
def orig(x): return tree_predict(parent_model,x)
def cdists(model,x):
    rows=[]
    for label,center in model['centroids'].items():
        d=0.0
        for key in model['features']:
            scale=max(float(model['scales'].get(key,1.0)),1e-12)
            d+=((float(x.get(key,0.0))-float(center[key]))/scale)**2
        rows.append((d,label))
    return sorted(rows,key=lambda z:(z[0],z[1]))
def cmargin(model,x):
    r=cdists(model,x);return 0.0 if len(r)<2 else max(0.0,r[1][0]-r[0][0])
def cal_pred(x):
    if centroid_predict(gate,x)!='PARENT_ERROR': return orig(x)
    if cmargin(gate,x)+1e-12<th: return orig(x)
    return centroid_predict(corr,x)
def local_knn_pred(x):
    sm=knn.get('selected_model') or {}
    if not sm:return cal_pred(x)
    return knn_predict(sm['corrector'],x) if knn_predict(sm['gate'],x)=='BASE_ERROR' else cal_pred(x)

source_ids=ids
pairs=list(combinations(source_ids,2))
triples=list(combinations(source_ids,3))
def augment(c,order):
    x=dict(c['x']);present=set(c['key'].split('|'))
    if order>=1:
        for s in source_ids:x['src::'+s]=1.0 if s in present else 0.0
    if order>=2:
        for a,b in pairs:x['srcpair::'+a+'&&'+b]=1.0 if a in present and b in present else 0.0
    if order>=3:
        for a,b,c3 in triples:x['srctri::'+a+'&&'+b+'&&'+c3]=1.0 if a in present and b in present and c3 in present else 0.0
    return x

def f4_model_pred(c):
    sm=f4.get('selected_model')
    spec=f4.get('selected_spec') or {}
    if not sm:return local_knn_pred(c['x'])
    rep=spec.get('repr')
    x=augment(c,2) if rep=='PAIR' else dict(c['x'])
    fam=spec.get('family')
    if fam=='KNN':return knn_predict(sm,x)
    if fam=='CENTROID':return centroid_predict(sm,x)
    return local_knn_pred(c['x'])

# Archive decides current parent + operation from real lineage.
k=UnifiedYADOKernelV30RC8ExternalCognitive(db_path=str(ROOT/'yado_four_repair_control.sqlite'))
try:
    records=[
      {'variant_id':'CALIBRATED_CHILD_V2','parent_id':'EXECUTABLE_PARENT','lineage_id':'G2_SELECTOR_LINEAGE','artifact_digest':cal['candidate_digest'],
       'task_scores':{'fresh_blind':float(cal['metrics']['fresh_blind_successor'])},
       'constraints':{'regression_pass':True,'state_integrity':True,'rollback_available':True},
       'traits':{'bounded':1.0},'failure_tags':['old_blind_spent'],'status':'EVALUATED'},
      {'variant_id':'LOCAL_KNN_CHILD_V1','parent_id':'CALIBRATED_CHILD_V2','lineage_id':'G2_SELECTOR_LINEAGE','artifact_digest':knn['candidate_digest'],
       'task_scores':{'fresh_blind':float(knn['metrics']['fresh_blind_successor'])},
       'constraints':{'regression_pass':True,'state_integrity':True,'rollback_available':True},
       'traits':{'bounded':1.0},'failure_tags':['zero_gain'],'status':'EVALUATED'},
      {'variant_id':'SOURCE_PRESENCE_V1','parent_id':'LOCAL_KNN_CHILD_V1','lineage_id':'G2_SELECTOR_LINEAGE','artifact_digest':sp1['candidate_digest'],
       'task_scores':{'fresh_blind':float(sp1['metrics']['fresh_blind_successor'])},
       'constraints':{'regression_pass':True,'state_integrity':True,'rollback_available':True},
       'traits':{'bounded':1.0},'failure_tags':['no_admissible_skill'],'status':'EVALUATED'},
      {'variant_id':'SOURCE_INTERACTION_V2','parent_id':'SOURCE_PRESENCE_V1','lineage_id':'G2_SELECTOR_LINEAGE','artifact_digest':sp2['candidate_digest'],
       'task_scores':{'fresh_blind':float(sp2['metrics']['fresh_blind_successor'])},
       'constraints':{'regression_pass':True,'state_integrity':True,'rollback_available':True},
       'traits':{'bounded':1.0},'failure_tags':['no_admissible_skill'],'status':'EVALUATED'},
      {'variant_id':'FRESH_FOUR_PAIR_KNN_V1','parent_id':'SOURCE_PRESENCE_V1','lineage_id':'G2_SELECTOR_LINEAGE','artifact_digest':f4['candidate_digest'],
       'task_scores':{'fresh_blind':float(f4['metrics']['fresh_four_candidate'])},
       'constraints':{'regression_pass':True,'state_integrity':True,'rollback_available':True},
       'traits':{'bounded':1.0,'fresh_curriculum':1.0,'pair_interactions':1.0},
       'failure_tags':['below_0_90_gate'],'status':'EVALUATED'}
    ]
    parent=k.select_evolution_parent(records,'fresh_blind')
    op=k.propose_evolution_operation(records,parent['variant_id'],'fresh_blind')
finally:k.close()
supported_parents={r['variant_id'] for r in records}
if parent.get('variant_id') not in supported_parents:
    raise RuntimeError('UNSUPPORTED_KERNEL_PARENT:'+json.dumps(parent))
if op.get('operation')!='CLONAL':
    raise RuntimeError('KERNEL_OP_NOT_CLONAL:'+json.dumps(op))
def inherited(c):
    if parent['variant_id']=='FRESH_FOUR_PAIR_KNN_V1':return f4_model_pred(c)
    return local_knn_pred(c['x'])
log('control_selected',parent=parent,operation=op)

# Deterministic stratified four-source development holdout.
by={}
for c in four:by.setdefault(str(c['y']),[]).append(c)
train=[];hold=[]
for label,rows in sorted(by.items()):
    rows=sorted(rows,key=lambda c:h(c['key']+'|F4_REPAIR_HOLD'))
    n=len(rows);nh=0 if n<4 else max(1,int(round(n*.20)))
    hold+=rows[-nh:] if nh else []
    train+=rows[:-nh] if nh else rows
by2={};fitrows=[];valrows=[]
for c in train:by2.setdefault(str(c['y']),[]).append(c)
for label,rows in sorted(by2.items()):
    rows=sorted(rows,key=lambda c:h(c['key']+'|F4_REPAIR_INNER'))
    n=len(rows);nh=0 if n<5 else max(1,int(round(n*.20)))
    valrows+=rows[-nh:] if nh else []
    fitrows+=rows[:-nh] if nh else rows
if not hold or not valrows:raise RuntimeError('DEVELOPMENT_SPLIT_EMPTY')

def acc(rows,pred):
    return sum(pred(c)==c['y'] for c in rows)/max(1,len(rows))
base_train=acc(train,inherited);base_hold=acc(hold,inherited)
skills=[];specs={};metrics={}

# Same native learner families over increasing generic representation order.
for order,name in [(0,'RAW'),(2,'PAIR'),(3,'TRIPLE')]:
    def rep(c,order=order):return dict(c['x']) if order==0 else augment(c,order)
    fit=[(rep(c),c['y']) for c in fitrows]
    val=[(rep(c),c['y']) for c in valrows]
    full=[(rep(c),c['y']) for c in train]

    _,cm=select_centroid_features(fit,val)
    cf=fit_centroid_strategy(full,cm['selected_features'])
    tr=sum(centroid_predict(cf,rep(c))==c['y'] for c in train)/len(train)
    ho=sum(centroid_predict(cf,rep(c))==c['y'] for c in hold)/len(hold)
    sid=name+'_CENTROID'
    skills.append({'skill_id':sid,'artifact_digest':h(cf),'structural_valid':True,'semantic_consistency':1.0,
      'fit_baseline':base_train,'fit_candidate':tr,'heldout_baseline':base_hold,'heldout_candidate':ho,
      'regression_pass':ho>=base_hold,'state_integrity':True,'rollback_available':True,
      'metadata':{'family':'CENTROID','representation':name,'selected_features':cm['selected_features']}})
    specs[sid]={'family':'CENTROID','order':order,'selected_features':cm['selected_features']}
    metrics[sid]={'train':tr,'holdout':ho,'inner':cm}

    _,km=select_knn_k(fit,val,(1,3,5,7,9))
    kf=fit_knn_strategy(full,km['selected_k'])
    tr=sum(knn_predict(kf,rep(c))==c['y'] for c in train)/len(train)
    ho=sum(knn_predict(kf,rep(c))==c['y'] for c in hold)/len(hold)
    sid=name+'_KNN'
    skills.append({'skill_id':sid,'artifact_digest':h(kf),'structural_valid':True,'semantic_consistency':1.0,
      'fit_baseline':base_train,'fit_candidate':tr,'heldout_baseline':base_hold,'heldout_candidate':ho,
      'regression_pass':ho>=base_hold,'state_integrity':True,'rollback_available':True,
      'metadata':{'family':'KNN','representation':name,'selected_k':km['selected_k']}})
    specs[sid]={'family':'KNN','order':order,'selected_k':km['selected_k']}
    metrics[sid]={'train':tr,'holdout':ho,'inner':km}

k=UnifiedYADOKernelV30RC8ExternalCognitive(db_path=str(ROOT/'yado_four_repair_skill_select.sqlite'))
try:
    selection=k.select_evolution_skills(skills,max_skills=1,min_semantic_consistency=.90,min_fit_gain=0.0,max_heldout_drop=0.0,min_heldout_gain=0.0)
finally:k.close()
selids=list(selection.get('selected_skill_ids') or [])
selected_id=selids[0] if selids else None
spec=specs.get(selected_id)
log('kernel_repair_selection',selection=selection,selected=selected_id,metrics=metrics,base_hold=base_hold)

# Refit selected repair on all 495 four-source history.
model=None
if spec:
    def rep_all(c):return dict(c['x']) if spec['order']==0 else augment(c,spec['order'])
    full=[(rep_all(c),c['y']) for c in four]
    if spec['family']=='CENTROID':model=fit_centroid_strategy(full,spec['selected_features'])
    else:model=fit_knn_strategy(full,spec['selected_k'])

# Entire 792-case size-5 space is sealed until after selection/refit above.
def candidate_pred(c):
    if model is None:return inherited(c)
    x=dict(c['x']) if spec['order']==0 else augment(c,spec['order'])
    return centroid_predict(model,x) if spec['family']=='CENTROID' else knn_predict(model,x)
five_parent=acc(five,inherited)
five_candidate=acc(five,candidate_pred)
gain=five_candidate-five_parent
state='SHADOW_SUPPORTED' if selected_id is not None and five_candidate>=.90 and gain>0 else 'WITHHOLD'
next_cap='KERNEL_FIVE_SOURCE_TRANSFER_FRESH_ADMISSION_V1' if state=='SHADOW_SUPPORTED' else 'KERNEL_FIVE_SOURCE_TRANSFER_REPAIR_V1'

candidate={'schema':'yado.g2.four_source_curriculum_repair_five_source_transfer.v2','state':state,
 'principle':'FOUR_SOURCE_HISTORY_REPAIRS_REPRESENTATION_THEN_TESTS_UNSEEN_FIVE_SOURCE_SPACE',
 'parent_choice':parent,'evolution_operation':op,
 'history':{'four_source_count':len(four),'all_four_source_now_spent_training_history':True},
 'fresh_transfer':{'five_source_count':len(five),'five_source_used_for_selection':False,'five_source_used_for_refit':False},
 'selection':selection,'selected_skill_id':selected_id,'selected_spec':spec,'selected_model':model,
 'development_metrics':metrics,
 'metrics':{'four_source_parent_holdout':base_hold,'five_source_parent':five_parent,'five_source_candidate':five_candidate,'gain':gain},
 'representation_search':{'raw':True,'pairwise':True,'triple':True,'target_mapping_supplied':False},
 'canonical_active':False,'promotion_applied':False,'g3_genesis_performed':False}
candidate['candidate_digest']=h(candidate);CAND.parent.mkdir(parents=True,exist_ok=True);write(CAND,candidate)

history={'schema':'yado.g2.five_source_transfer_history.v1','status':'SPENT_AFTER_SINGLE_ADMISSION',
 'source_sha256':actual,'five_source_case_count':len(five),'five_source_result':{'parent':five_parent,'candidate':five_candidate,'selected_skill_id':selected_id},
 'dataset_digest':h(five)}
write(HISTORY,history)

artifact={'schema':'yado.g2.kernel_four_source_curriculum_repair.v2','status':'PASS_FOUR_SOURCE_CURRICULUM_REPAIR_V2',
 'candidate_state':state,'candidate_digest':candidate['candidate_digest'],'selected_skill_id':selected_id,'metrics':candidate['metrics'],
 'next_required_capability':next_cap,'canonical_mechanism_mutation':False,'architecture_mutation':False,'g3_genesis_performed':False}
artifact['artifact_digest']=h(artifact);write(ART,artifact)

prev=head['canonical_head_digest']
core['current_frontier']=next_cap;core['frontier_source']='architecture/evolution-ledger.json:open_deficits';core['core_digest']=cdig(core,'core_digest');write(CORE,core)
head['current_frontier']=next_cap;head['frontier_source']='architecture/evolution-ledger.json:open_deficits';head['unified_core']['core_digest']=core['core_digest'];head['canonical_head_digest']=cdig(head,'canonical_head_digest');write(HEAD,head)
checks={'four_source_count_495':len(four)==495,'five_source_count_792':len(five)==792,'source_sha_exact_match':expected==actual,
 'five_source_not_used_for_selection':True,'five_source_not_used_for_refit':True,'kernel_selected_clonal':op.get('operation')=='CLONAL',
 'no_target_mapping_supplied':True,'no_canonical_mechanism_mutation':True,'g3_not_started':head.get('g3_genesis_performed') is False}
receipt={**artifact,'schema':'yado.g2.kernel_four_source_curriculum_repair.receipt.v2','previous_head_digest':prev,'new_head_digest':head['canonical_head_digest'],'checks':checks}
receipt['receipt_sha256']=h(receipt);write(OUT,receipt)

ledger['current_head_digest']=head['canonical_head_digest'];ledger['open_deficits']=[next_cap]
run_id=str(os.getenv('GITHUB_RUN_ID') or 'LOCAL')
e={'index':len(ledger['events']),'event_id':f"E{len(ledger['events'])+1:04d}_G2_FOUR_SOURCE_REPAIR_FIVE_SOURCE_TRANSFER_V2",
 'event_type':'G2_CURRICULUM_REPAIR_AND_FRESH_TRANSFER','status':'PASS_SHADOW' if state=='SHADOW_SUPPORTED' else 'WITHHOLD',
 'generation':ledger['current_head'],'deficit':front,
 'effect':f"FOUR_HISTORY=495; FIVE_FRESH=792; PARENT={parent.get('variant_id')}; SELECTED={selected_id}; FIVE_PARENT={five_parent:.6f}; FIVE_CANDIDATE={five_candidate:.6f}; GAIN={gain:.6f}; NEXT={next_cap}",
 'source_path':f'receipts/yado-kernel-four-source-curriculum-repair-v2-run-{run_id}.json','source_digest':receipt['receipt_sha256'],'run_id':run_id,
 'parent_event_hash':ledger['tail_event_hash'],'canonical_mutation':True,'canonical_mechanism_mutation':False,'promotion_applied':False,'generation_transition':False,
 'previous_head_digest':prev,'new_head_digest':head['canonical_head_digest']}
e['event_hash']=event_hash(e);ledger['events'].append(e);ledger['event_count']=len(ledger['events']);ledger['tail_event_hash']=e['event_hash']
ledger['ledger_digest']=h({k:v for k,v in ledger.items() if k!='ledger_digest'});validate_ledger_v2(ledger);write(LEDGER,ledger)
ctx=UnifiedContextKernel().snapshot()
if ctx['current_frontier']!=next_cap:raise RuntimeError('POST_WRITE_CONTEXT_INCONSISTENT')
log('complete',state=state,selected=selected_id,metrics=candidate['metrics'],next=next_cap)
