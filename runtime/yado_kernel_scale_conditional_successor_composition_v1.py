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
from yado_cognitive_growth_runtime_v1 import centroid_predict,knn_predict
from yado_unified_context_kernel_v1 import UnifiedContextKernel

HEAD=REPO/'canonical/yado-main-head-g2.json'
CORE=REPO/'canonical/yado-unified-core-v1.json'
LEDGER=REPO/'architecture/evolution-ledger.json'
BASE=REPO/'receipts/yado-architecture-neutral-meta-synth-v2-latest.json'
CORPUS=REPO/'resources/yado-architecture-neutral-evidence-corpus-frozen-v1.json'
CAL=REPO/'candidates/kernel-self-generated/evolutionary-centroid-calibrated-successor-v2.json'
KNN=REPO/'candidates/kernel-self-generated/evolutionary-local-knn-successor-v1.json'
F4=REPO/'candidates/kernel-self-generated/fresh-four-source-curriculum-v1.json'
ADMIT=REPO/'candidates/kernel-self-generated/fresh-four-pair-knn-five-source-admission-v1.json'
ART=REPO/'architecture/yado-kernel-scale-conditional-successor-composition-v1.json'
CAND=REPO/'candidates/kernel-self-generated/scale-conditional-pair-knn-successor-v1.json'
HISTORY=REPO/'resources/yado-six-source-transfer-history-v1.json'
OUT=ROOT/'yado_kernel_scale_conditional_successor_composition_v1_receipt.json'

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def h(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def write(p,o):p.write_text(json.dumps(o,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')
def cdig(o,field):
    x=copy.deepcopy(o);x.pop(field,None);return h(x)
def log(stage,**kw):print(json.dumps({'stage':stage,'ts':time.time(),**kw},sort_keys=True,default=str),flush=True)

head,core,ledger,base,corpus,cal,knn,f4,admit=map(load,[HEAD,CORE,LEDGER,BASE,CORPUS,CAL,KNN,F4,ADMIT])
validate_ledger_v2(ledger)
front='KERNEL_FRESH_TRANSFER_SUCCESSOR_CANONICAL_ADMISSION_V1'
if ledger.get('open_deficits')!=[front]:raise RuntimeError('UNEXPECTED_FRONTIER:'+json.dumps(ledger.get('open_deficits')))
if admit.get('state')!='SHADOW_SUPPORTED':raise RuntimeError('PARENT_NOT_SHADOW_SUPPORTED')
if f4.get('selected_skill_id')!='PAIR_KNN':raise RuntimeError('PAIR_KNN_PARENT_MISSING')

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
spaces={s:make_cases(s) for s in (1,2,3,4,5,6)}
if [len(spaces[s]) for s in (1,2,3,4,5,6)]!=[12,66,220,495,792,924]:raise RuntimeError('SPACE_COUNTS_INVALID')
history=sum((spaces[s] for s in (1,2,3,4,5)),[])
fresh6=spaces[6]
log('spaces_ready',history=len(history),fresh6=len(fresh6),source_sha_exact=True)

# Old stable branch.
parent_model=base['kernel_result']['model']
g=cal['generator'];gate=g['gate_model'];corr=g['corrector_model'];th=float(cal['selected_threshold'])
def orig(x):return tree_predict(parent_model,x)
def dists(model,x):
    rows=[]
    for label,center in model['centroids'].items():
        d=0.0
        for key in model['features']:
            scale=max(float(model['scales'].get(key,1.0)),1e-12)
            d+=((float(x.get(key,0.0))-float(center[key]))/scale)**2
        rows.append((d,label))
    return sorted(rows,key=lambda z:(z[0],z[1]))
def margin(model,x):
    r=dists(model,x);return 0.0 if len(r)<2 else max(0.0,r[1][0]-r[0][0])
def cal_pred(x):
    if centroid_predict(gate,x)!='PARENT_ERROR':return orig(x)
    if margin(gate,x)+1e-12<th:return orig(x)
    return centroid_predict(corr,x)
def old_pred(c):
    sm=knn.get('selected_model') or {}
    if not sm:return cal_pred(c['x'])
    return knn_predict(sm['corrector'],c['x']) if knn_predict(sm['gate'],c['x'])=='BASE_ERROR' else cal_pred(c['x'])

# New high-scale branch.
source_ids=ids;pairs=list(combinations(source_ids,2))
def augment_pair(c):
    x=dict(c['x']);present=set(c['key'].split('|'))
    for s in source_ids:x['src::'+s]=1.0 if s in present else 0.0
    for a,b in pairs:x['srcpair::'+a+'&&'+b]=1.0 if a in present and b in present else 0.0
    return x
pair_model=f4['selected_model']
def new_pred(c):return knn_predict(pair_model,augment_pair(c))

# Current shadow candidate is the archive reference parent for the composition.
k=UnifiedYADOKernelV30RC8ExternalCognitive(db_path=str(ROOT/'yado_scale_condition_control.sqlite'))
try:
    records=[
      {'variant_id':'OLD_STABLE_PARENT','parent_id':None,'lineage_id':'G2_SELECTOR_LINEAGE','artifact_digest':'old-stable',
       'task_scores':{'fresh5':float(admit['evidence']['five_source_ablation']),'history':float(admit['evidence']['aggregate_sizes_1_to_4']['ablation'])},
       'constraints':{'regression_pass':True,'state_integrity':True,'rollback_available':True},'traits':{'stable_low_scale':1.0},'failure_tags':['weak_high_scale'],'status':'EVALUATED'},
      {'variant_id':'FRESH_FOUR_PAIR_KNN_V1','parent_id':'OLD_STABLE_PARENT','lineage_id':'G2_SELECTOR_LINEAGE','artifact_digest':f4['candidate_digest'],
       'task_scores':{'fresh5':float(admit['evidence']['recorded_fresh_five_first_exposure']),'history':float(admit['evidence']['aggregate_sizes_1_to_4']['candidate'])},
       'constraints':{'regression_pass':True,'state_integrity':True,'rollback_available':True},'traits':{'high_scale_transfer':1.0},'failure_tags':['low_scale_regression'],'status':'EVALUATED'}
    ]
    parent=k.select_evolution_parent(records,'fresh5')
    op=k.propose_evolution_operation(records,parent['variant_id'],'fresh5')
finally:k.close()
if parent.get('variant_id')!='FRESH_FOUR_PAIR_KNN_V1':raise RuntimeError('KERNEL_DID_NOT_SELECT_HIGH_SCALE_PARENT:'+json.dumps(parent))
if op.get('operation')!='CLONAL':raise RuntimeError('KERNEL_OP_NOT_CLONAL:'+json.dumps(op))
log('control_selected',parent=parent,operation=op)

# Deterministic history split preserving each (size,label) group.
groups={}
for c in history:groups.setdefault((c['size'],str(c['y'])),[]).append(c)
train=[];hold=[]
for key,rows in sorted(groups.items()):
    rows=sorted(rows,key=lambda c:h(c['key']+'|SCALE_GATE_HOLD'))
    n=len(rows);nh=0 if n<3 else max(1,int(round(n*.20)))
    hold+=rows[-nh:] if nh else [];train+=rows[:-nh] if nh else rows
if not hold:raise RuntimeError('HOLDOUT_EMPTY')

def acc(rows,pred):return sum(pred(c)==c['y'] for c in rows)/max(1,len(rows))
base_train=acc(train,new_pred);base_hold=acc(hold,new_pred)

# Generic reaction-norm thresholds are derived only from observed source_count values.
values=sorted({float(c['x']['source_count']) for c in history})
thresholds=values[:]  # includes "always new" at min and progressively more conservative gates.
skills=[];metrics={}
for t in thresholds:
    sid='SCALE_GATE_'+hashlib.sha256(f'{t:.12f}'.encode()).hexdigest()[:10]
    def pred(c,t=t):return new_pred(c) if float(c['x']['source_count'])+1e-12>=t else old_pred(c)
    tr=acc(train,pred);ho=acc(hold,pred)
    per={}
    regression=True
    for s in (1,2,3,4,5):
        rows=[c for c in hold if c['size']==s]
        if rows:
            b=acc(rows,new_pred);v=acc(rows,pred)
            per[str(s)]={'new_parent':b,'composed':v,'gain':v-b,'count':len(rows)}
            if v+1e-12<b:regression=False
    skills.append({'skill_id':sid,'artifact_digest':h({'threshold':t,'old':'OLD_STABLE_PARENT','new':'FRESH_FOUR_PAIR_KNN_V1'}),
      'structural_valid':True,'semantic_consistency':1.0,'fit_baseline':base_train,'fit_candidate':tr,
      'heldout_baseline':base_hold,'heldout_candidate':ho,'regression_pass':regression,
      'state_integrity':True,'rollback_available':True,
      'metadata':{'threshold':t,'gate_feature':'source_count','holdout_per_size':per}})
    metrics[sid]={'threshold':t,'train':tr,'holdout':ho,'per_size':per,'regression_pass':regression}

k=UnifiedYADOKernelV30RC8ExternalCognitive(db_path=str(ROOT/'yado_scale_condition_skill_select.sqlite'))
try:
    selection=k.select_evolution_skills(skills,max_skills=1,min_semantic_consistency=.90,min_fit_gain=0.0,max_heldout_drop=0.0,min_heldout_gain=0.0)
finally:k.close()
ids_sel=list(selection.get('selected_skill_ids') or [])
selected_id=ids_sel[0] if ids_sel else None
selected_t=None if selected_id is None else float(metrics[selected_id]['threshold'])
log('kernel_threshold_selection',selection=selection,selected_threshold=selected_t,base_hold=base_hold)

def composed(c):
    if selected_t is None:return new_pred(c)
    return new_pred(c) if float(c['x']['source_count'])+1e-12>=selected_t else old_pred(c)

# Fresh size-6 is opened only after threshold selection.
fresh6_old=acc(fresh6,old_pred)
fresh6_new=acc(fresh6,new_pred)
fresh6_composed=acc(fresh6,composed)
history_new=acc(history,new_pred)
history_composed=acc(history,composed)
gain_old=fresh6_composed-fresh6_old
checks={
 'source_sha_exact_match':expected==actual,
 'six_source_count_924':len(fresh6)==924,
 'six_source_not_used_for_threshold_selection':True,
 'kernel_selected_threshold':selected_t is not None,
 'history_no_regression_vs_new_parent':history_composed+1e-12>=history_new,
 'fresh6_above_gate':fresh6_composed>=0.90,
 'fresh6_beats_old_parent':fresh6_composed>fresh6_old,
 'g3_not_started':head.get('g3_genesis_performed') is False,
}
supported=all(checks.values())
state='SHADOW_SUPPORTED' if supported else 'WITHHOLD'
next_cap='KERNEL_SCALE_CONDITIONAL_SUCCESSOR_CANONICAL_ADMISSION_V1' if supported else 'KERNEL_SCALE_CONDITIONAL_SUCCESSOR_REPAIR_V2'

candidate={'schema':'yado.g2.scale_conditional_pair_knn_successor.v1','state':state,
 'principle':'KERNEL_SELECTED_SCALE_CONDITIONAL_REACTION_NORM',
 'parent_choice':parent,'evolution_operation':op,'selection':selection,'selected_skill_id':selected_id,'selected_threshold':selected_t,
 'branches':{'low_scale':'OLD_STABLE_PARENT','high_scale':'FRESH_FOUR_PAIR_KNN_V1','gate_feature':'source_count'},
 'development_metrics':metrics,
 'metrics':{'history_new_parent':history_new,'history_composed':history_composed,
            'fresh6_old_parent':fresh6_old,'fresh6_new_parent':fresh6_new,'fresh6_composed':fresh6_composed,'fresh6_gain_vs_old':gain_old},
 'fresh_transfer':{'size':6,'case_count':924,'used_for_selection':False,'used_for_admission_only':True},
 'checks':checks,'canonical_active':False,'promotion_applied':False,'canonical_mechanism_mutation':False,'architecture_mutation':False,'g3_genesis_performed':False}
candidate['candidate_digest']=h(candidate);CAND.parent.mkdir(parents=True,exist_ok=True);write(CAND,candidate)
history6={'schema':'yado.g2.six_source_transfer_history.v1','status':'SPENT_AFTER_SINGLE_ADMISSION','source_sha256':actual,
 'case_count':len(fresh6),'result':{'old_parent':fresh6_old,'new_parent':fresh6_new,'composed':fresh6_composed,'selected_threshold':selected_t},'dataset_digest':h(fresh6)}
write(HISTORY,history6)
artifact={'schema':'yado.g2.kernel_scale_conditional_successor_composition.v1','status':'PASS_SCALE_CONDITIONAL_COMPOSITION_V1',
 'candidate_state':state,'candidate_digest':candidate['candidate_digest'],'selected_threshold':selected_t,'metrics':candidate['metrics'],
 'next_required_capability':next_cap,'canonical_mechanism_mutation':False,'architecture_mutation':False,'g3_genesis_performed':False}
artifact['artifact_digest']=h(artifact);write(ART,artifact)

prev=head['canonical_head_digest']
core['current_frontier']=next_cap;core['frontier_source']='architecture/evolution-ledger.json:open_deficits';core['core_digest']=cdig(core,'core_digest');write(CORE,core)
head['current_frontier']=next_cap;head['frontier_source']='architecture/evolution-ledger.json:open_deficits';head['unified_core']['core_digest']=core['core_digest'];head['canonical_head_digest']=cdig(head,'canonical_head_digest');write(HEAD,head)
receipt={**artifact,'schema':'yado.g2.kernel_scale_conditional_successor_composition.receipt.v1','previous_head_digest':prev,'new_head_digest':head['canonical_head_digest'],'checks':checks}
receipt['receipt_sha256']=h(receipt);write(OUT,receipt)

ledger['current_head_digest']=head['canonical_head_digest'];ledger['open_deficits']=[next_cap];run_id=str(os.getenv('GITHUB_RUN_ID') or 'LOCAL')
e={'index':len(ledger['events']),'event_id':f"E{len(ledger['events'])+1:04d}_G2_SCALE_CONDITIONAL_REACTION_NORM_V1",
 'event_type':'G2_SCALE_CONDITIONAL_SUCCESSOR_COMPOSITION','status':'PASS_SHADOW' if supported else 'WITHHOLD','generation':ledger['current_head'],'deficit':front,
 'effect':f"LOW=OLD_STABLE_PARENT; HIGH=FRESH_FOUR_PAIR_KNN_V1; THRESHOLD={selected_t}; HISTORY={history_composed:.6f}; FRESH6={fresh6_composed:.6f}; OLD6={fresh6_old:.6f}; NEW6={fresh6_new:.6f}; STATE={state}; NEXT={next_cap}",
 'source_path':f'receipts/yado-kernel-scale-conditional-successor-composition-v1-run-{run_id}.json','source_digest':receipt['receipt_sha256'],'run_id':run_id,
 'parent_event_hash':ledger['tail_event_hash'],'canonical_mutation':True,'canonical_mechanism_mutation':False,'promotion_applied':False,'generation_transition':False,
 'previous_head_digest':prev,'new_head_digest':head['canonical_head_digest']}
e['event_hash']=event_hash(e);ledger['events'].append(e);ledger['event_count']=len(ledger['events']);ledger['tail_event_hash']=e['event_hash'];ledger['ledger_digest']=h({k:v for k,v in ledger.items() if k!='ledger_digest'});validate_ledger_v2(ledger);write(LEDGER,ledger)
ctx=UnifiedContextKernel().snapshot()
if ctx['current_frontier']!=next_cap:raise RuntimeError('POST_WRITE_CONTEXT_INCONSISTENT')
log('complete',state=state,threshold=selected_t,metrics=candidate['metrics'],next=next_cap)
