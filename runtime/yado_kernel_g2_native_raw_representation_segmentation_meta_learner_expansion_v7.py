from __future__ import annotations
from pathlib import Path
from collections import Counter
from bisect import bisect_left,bisect_right
from functools import lru_cache
import hashlib,json,math,os,random,re,sys,time

import numpy as np

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
PKG=ROOT/'yado_rc8_v36'
sys.path[:0]=[str(ROOT),str(PKG)]

from yado_core_v3_0_rc8_external_cognitive import UnifiedYADOKernelV30RC8ExternalCognitive
from yado_raw_task_representation_candidate_v2 import RawTaskRepresentationSpecV2,_features,_dot
from yado_raw_task_representation_multiscale_v6 import RawTaskRepresentationMultiscaleRuntimeV6
from yado_organ_runtime_native_v1 import fit_tree,tree_acc,tree_predict
from yado_cognitive_growth_runtime_v1 import (
    fit_knn_strategy,knn_predict,
    fit_centroid_strategy,centroid_predict,centroid_accuracy,
)
from yado_evolution_ledger_v2 import validate_ledger_v2

V6=REPO/'architecture/yado-kernel-g2-native-raw-representation-model-family-expansion-admission-v6.json'
V5=REPO/'architecture/yado-kernel-g2-native-raw-representation-model-family-expansion-v5.json'
PARENT=REPO/'candidates/kernel-self-generated/raw-task-representation-strategy-model-v4.json'
BASE=REPO/'receipts/yado-g2-real-world-transfer-benchmark-v1-run-33363995201.json'
COMPUTE=REPO/'receipts/yado-g2-native-raw-segmentation-meta-compute-deficit-v1-run-34260882252.json'
LEDGER=REPO/'architecture/evolution-ledger.json'
OUT=REPO/'architecture/yado-kernel-g2-native-raw-representation-segmentation-meta-learner-expansion-v7.json'
CAND=REPO/'candidates/kernel-self-generated/raw-task-representation-segmentation-meta-learner-v7.json'
FRESH=REPO/'resources/yado-raw-task-representation-segmentation-meta-learner-v7-fresh.json'
DB=ROOT/'yado_raw_segmentation_meta_learner_v7.sqlite'

CAP_CONJ='ALG-CONJUNCTIVE-RULE-INDUCER-V1'
CAP_REL='ALG-BOUNDED-DNF-RELATION-POLICY-INDUCER-V1'
CAP_BUD='ALG-BUDGETED-STAGE-POLICY-V1'
CAP_RES='RESOURCE-PORTFOLIO-V1'
FRONT='KERNEL_G2_RAW_REPRESENTATION_V4_ROBUSTNESS_SELF_EVOLUTION_V2'

def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def digest(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def write(p,o):Path(p).parent.mkdir(parents=True,exist_ok=True);Path(p).write_text(json.dumps(o,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')
def acc(rows,pred):return sum(pred(x)==y for x,y in rows)/max(1,len(rows))
def log(stage,**kw):print(json.dumps({'stage':stage,'ts':time.time(),**kw},sort_keys=True,default=str),flush=True)

v6,v5,parent_art,base,compute,ledger=map(load,[V6,V5,PARENT,BASE,COMPUTE,LEDGER])
validate_ledger_v2(ledger)
if ledger.get('open_deficits')!=[FRONT]:raise RuntimeError('UNEXPECTED_FRONTIER:'+canon(ledger.get('open_deficits')))
if v6.get('status')!='WITHHOLD_G2_NATIVE_RAW_REPRESENTATION_MODEL_FAMILY_EXPANSION_ADMISSION_V6':raise RuntimeError('V6_ADMISSION_WITHHOLD_REQUIRED')
if v6.get('next_required_capability')!='NATIVE_RAW_REPRESENTATION_SEGMENTATION_PRIMITIVE_GENESIS_V6':raise RuntimeError('V6_SEGMENTATION_FRONTIER_MISMATCH')
if v6.get('receipt_sha256')!='6f16f97ab630c3964a66a6ebdd2d706f2c0a6895fd65f9f6d370ce59c9afeb8e':raise RuntimeError('V6_RECEIPT_DRIFT')
if v5.get('candidate_digest')!='55bd61069b501dc09ab089f96ad139e70b11895f441258b14512f24e72950697':raise RuntimeError('V5_PARENT_DRIFT')
if compute.get('exact_blocker')!='EXACT_LINEAR_SCORE_SEARCH_STILL_SEMANTICALLY_REQUIRED':raise RuntimeError('COMPUTE_DEFICIT_EVIDENCE_REQUIRED')
if float((compute.get('cart_evidence') or {}).get('best_validation',0))!=0.9167883211678832:raise RuntimeError('COMPUTE_CART_EVIDENCE_DRIFT')

parent_model=parent_art['model']
raw=RawTaskRepresentationSpecV2(parent_model['family'],list(parent_model['labels']),parent_model['payload'])
v5rt=RawTaskRepresentationMultiscaleRuntimeV6(parent_model,v5['selected_spec'])
labels=list(raw.labels)

@lru_cache(maxsize=400000)
def raw_scores(text):
    mode=raw.payload['mode'];dim=int(raw.payload['dim']);x=_features(text,mode,dim);rows=[]
    for label in labels:
        s=_dot(raw.payload['weights'].get(label,{}),x)+float(raw.payload['bias'].get(label,0.0))
        rows.append((float(s),label))
    rows.sort(key=lambda z:(-z[0],z[1]));return rows

def word_windows_from_tokens(toks,original_text,width,stride):
    n=len(toks)
    if not toks:return [(0,0,str(original_text))]
    if n<=width:return [(0,n,' '.join(toks))]
    out=[]
    for start in range(0,max(1,n-width+1),max(1,stride)):
        out.append((start,min(n,start+width),' '.join(toks[start:start+width])))
    tail=max(0,n-width)
    if not out or out[-1][0]!=tail:out.append((tail,n,' '.join(toks[tail:])))
    return out

_PARITY_BUDGET=6
def segment_records(text):
    global _PARITY_BUDGET
    toks=re.findall(r"[a-zA-Z0-9_]+",str(text));n=max(1,len(toks))
    segs=[{'start':0,'end':n,'width':n,'text':str(text),'whole':1.0}]
    for w in v5['selected_spec']['widths']:
        for a,b,z in word_windows_from_tokens(toks,text,int(w),max(1,int(w)//int(v5['selected_spec']['stride_div']))):
            segs.append({'start':a,'end':b,'width':int(w),'text':z,'whole':0.0})
    uniq=[];seen=set()
    for q in segs:
        k=(q['start'],q['end'],hashlib.sha256(q['text'].encode()).hexdigest())
        if k not in seen:seen.add(k);uniq.append(q)
    for q in uniq:
        rs=raw_scores(q['text']);q['label']=rs[0][1];q['margin']=float(rs[0][0]-rs[1][0]);q['top_score']=float(rs[0][0])
    margins=sorted((q['margin'],i) for i,q in enumerate(uniq));scores=sorted((q['top_score'],i) for i,q in enumerate(uniq))
    mr={i:r/max(1,len(uniq)-1) for r,(_,i) in enumerate(margins)}
    sr={i:r/max(1,len(uniq)-1) for r,(_,i) in enumerate(scores)}
    counts=Counter(q['label'] for q in uniq);whole_label=uniq[0]['label']
    run_by_index={};groups={}
    for i,q in enumerate(uniq):groups.setdefault(q['width'],[]).append((i,q))
    for _,arr in groups.items():
        arr.sort(key=lambda z:(z[1]['start'],z[1]['end'],z[0]));p=0
        while p<len(arr):
            r=p+1
            while r<len(arr) and arr[r][1]['label']==arr[p][1]['label']:r+=1
            run=(r-p)/max(1,len(arr))
            for k in range(p,r):run_by_index[arr[k][0]]=run
            p=r
    raw_centers=[(q['start']+q['end'])/2 for q in uniq]
    order=sorted(range(len(uniq)),key=lambda i:(raw_centers[i],i));sorted_centers=[raw_centers[i] for i in order]
    prefix={label:[0] for label in labels}
    for idx in order:
        qlabel=uniq[idx]['label']
        for label in labels:prefix[label].append(prefix[label][-1]+(1 if qlabel==label else 0))
    rows=[];parity_this_call=_PARITY_BUDGET>0
    for i,q in enumerate(uniq):
        raw_center=raw_centers[i];radius=max(8,q['width'])
        left=bisect_left(sorted_centers,raw_center-radius);right=bisect_right(sorted_centers,raw_center+radius)
        neighbor_count=max(0,(right-left)-1);same_count=(prefix[q['label']][right]-prefix[q['label']][left])-1
        local=same_count/max(1,neighbor_count)
        if parity_this_call:
            slow_neighbors=[z for z in uniq if z is not q and abs(((z['start']+z['end'])/2)-raw_center)<=radius]
            slow_local=sum(z['label']==q['label'] for z in slow_neighbors)/max(1,len(slow_neighbors))
            if abs(local-slow_local)>1e-15:raise RuntimeError('LOCAL_SUPPORT_FAST_PATH_DRIFT')
        center=raw_center/n
        feat={
          'margin':q['margin'],'top_score':q['top_score'],'margin_rank':mr[i],'score_rank':sr[i],
          'start_frac':q['start']/n,'end_frac':q['end']/n,'center_dist':abs(center-.5),
          'width_frac':min(1.0,q['width']/n),'whole':q['whole'],
          'global_label_support':counts[q['label']]/len(uniq),'local_label_support':local,
          'same_label_run':run_by_index.get(i,0.0),'whole_agreement':1.0 if q['label']==whole_label else 0.0,
        }
        rows.append({'label':q['label'],'margin':q['margin'],'top_score':q['top_score'],'features':feat,'index':i})
    if parity_this_call:_PARITY_BUDGET-=1
    return rows

def parent_from_segment_rows(rows):
    q=sorted(rows,key=lambda r:(-r['margin'],-r['top_score'],r['label'],r['index']))[0]
    return q['label']

templates={
 CAP_CONJ:[
  "For {d}, release only when authorization, integrity, provenance, and recovery readiness are all satisfied together.",
  "In {d}, one false mandatory safeguard blocks execution even though budget and membership fields are present.",
  "Decide whether every required operational invariant for {d} passes; do not optimize search cost.",
  "For {d}, commit exactly when all compulsory validation conditions are true."],
 CAP_REL:[
  "For {d}, access depends on requester-owner identity or membership in the approved role group; quota fields are incidental.",
  "In {d}, permission follows principal, owner, tenant, and membership relations rather than independent boolean safeguards.",
  "For {d}, determine whether actor identity matches the resource owner or an authorized cohort relation exists.",
  "In {d}, entity equality and group edges decide the result; no outside fact is missing."],
 CAP_BUD:[
  "For {d}, choose the next verification stage under finite compute, latency, and expected evidence gain constraints.",
  "In {d}, allocate remaining credits across diagnostics so confidence improves without exceeding quota.",
  "For {d}, plan the lowest-cost next experiment under a hard resource ceiling; identity is already resolved.",
  "In {d}, select an affordable investigation sequence from several valid stages."],
 CAP_RES:[
  "For {d}, local state cannot establish the decisive requirement, so obtain a current authoritative external reference.",
  "In {d}, ownership and budget are known but the missing fact must come from current public documentation.",
  "For {d}, retrieve the absent specification from a trustworthy outside source instead of running another local test.",
  "In {d}, the unresolved information lies outside local memory and must be fetched from an eligible authority."]
}
domains=['air traffic release','molecular assay','customs workflow','autonomous vehicle fleet','payment clearing','hospital pharmacy','satellite payload','data retention review','factory interlock','telecom restoration','research export','energy dispatch']
direct=[]
for gi,label in enumerate([CAP_CONJ,CAP_REL,CAP_BUD,CAP_RES]):
    for i in range(30):direct.append((f"Admission6 {40000+gi*100+i}. "+templates[label][(i*5+gi)%4].format(d=domains[(i*7+gi)%len(domains)]),label))
traps=[
 ("The header lists owner, quota, and external documentation, but the operation still requires every mandatory integrity and recovery safeguard to pass.",CAP_CONJ),
 ("All safety checks are true and a budget is displayed, yet authorization changes only with principal identity and approved membership.",CAP_REL),
 ("Ownership is resolved and a manual is attached; choose the next diagnostic under the remaining compute allowance.",CAP_BUD),
 ("Budget remains and group membership is known, but the missing rule is absent locally and requires a current outside authority.",CAP_RES),
 ("A public guide and quota are mentioned, but acceptance remains an all-required-conditions decision.",CAP_CONJ),
 ("Rollback and integrity appear in metadata, while access still depends on owner equality or authorized group relations.",CAP_REL),
 ("External resources are available, but the actual task is allocating limited credits among staged investigations.",CAP_BUD),
 ("All local gates pass, but the unanswered requirement must be retrieved from current authoritative documentation.",CAP_RES),
]*8
neutral=[
 "Administrative note. This carrier contains transport metadata only and does not change the enclosed decision.",
 "System relay. Identifiers, timestamps, counters, and routing headers below are non-semantic transport context.",
 "Archive wrapper. The payload remains the only task statement; surrounding metadata is not part of the decision.",
]
def wrap_c(text,i,layer):
    m=(i*13+layer*5)%15
    if m==0:return f"<admit6 id='{i%229}' depth='{layer}'><payload>{text}</payload></admit6>"
    if m==1:return f"BEGIN-A6 {i%233}/{layer}\n{neutral[i%3]}\n{text}\nEND-A6"
    if m==2:return f"[carrier-a6:{i%239}:{layer}] {text} [/carrier-a6]"
    if m==3:return f"Routing header owner quota manual rollback team integrity. START {text} STOP."
    if m==4:return f"{{packet={i%241};depth={layer}}} {neutral[(i+1)%3]} {text} {{/packet}}"
    if m==5:return f"TRACE-A6 {i%251}: {text.lower() if i%2 else text.upper()} :TRACE-END"
    if m==6:return f"((frame {layer})) [[segment {i%257}]] {text} [[/segment]] ((/frame))"
    if m==7:return f"Audit envelope {i%263}. {re.sub(r'\s+',' ',text)} Audit envelope complete."
    if m==8:return f"Metadata preface: owner budget external relation conjunction. Payload: {text}. Metadata suffix."
    if m==9:return f"{neutral[i%3]} Header {i%269}. {text} Footer {layer%17}. {neutral[(i+2)%3]}"
    if m==10:return f"<context><meta>{i%271}:{layer}</meta><content>{text}</content></context>"
    if m==11:return f"Journal-A6 {i%277}: BEGIN-CONTENT {text} END-CONTENT."
    if m==12:return f"prefix tokens owner group quota public source all checks. {text}. suffix tokens."
    if m==13:return f"Transport record {i%281}. {neutral[i%3]} PAYLOAD {text} END PAYLOAD."
    return f"Administrative relay {i%283}. Begin {text} Complete."

pool=direct+traps
rng=random.Random(2026090708);spent=[]
for i in range(7000):
    x,y=pool[(i*61+rng.randrange(len(pool)))%len(pool)]
    z=wrap_c(x,i,0)
    for layer in range(1,1+(i%10)):z=wrap_c(z,i+31013*layer,layer)
    spent.append((z,y))
spent_repro=acc(spent,v5rt.predict_capability)
if abs(spent_repro-float(v6['admission_metrics']['multiscale']['sequential']))>1e-12:raise RuntimeError('V6_SPENT_REPRO_DRIFT')
ordered=sorted(spent,key=lambda r:hashlib.sha256((r[0]+'|'+r[1]+'|SEG6').encode()).hexdigest())
fit_docs=ordered[:200];val_docs=ordered[200:260];blind_docs=ordered[260:320];select_docs=ordered[320:1320]

def window_training_rows(docs):
    out=[]
    for text,expected in docs:
        for r in segment_records(text):out.append((r['features'],'KEEP' if r['label']==expected else 'DROP'))
    return out
fit=window_training_rows(fit_docs);val=window_training_rows(val_docs);blind=window_training_rows(blind_docs)
if (len(fit),len(val),len(blind))!=(2394,685,880):raise RuntimeError('V6_WINDOW_SPLIT_DRIFT:'+str((len(fit),len(val),len(blind))))
log('spent_window_evidence_ready',spent_repro=spent_repro,fit=len(fit),validation=len(val),blind=len(blind))

# Existing CART family is the baseline; V7 expands only with already-native centroid/KNN.
cart_trials=[]
for depth in range(1,8):
    m=fit_tree(fit,depth);va=tree_acc(m,val);tr=tree_acc(m,fit)
    cart_trials.append((va,-depth,depth,m,tr))
_,_,cart_depth,cart_model,cart_fit=max(cart_trials,key=lambda z:z[:2])
cart_val=tree_acc(cart_model,val)
if abs(cart_val-float(compute['cart_evidence']['best_validation']))>1e-12:raise RuntimeError('CART_BASELINE_DRIFT')

skill_fit_probe=fit[:400]
base_fit_probe=tree_acc(cart_model,skill_fit_probe)
base_val=cart_val
skills=[];models={};metrics={}

# Keep-current CART candidate is always available as rollback.
sid=f'CART_KEEP_D{cart_depth}'
skills.append({'skill_id':sid,'artifact_digest':digest({'family':'CART_AXIS','depth':cart_depth,'model':cart_model}),
 'structural_valid':True,'semantic_consistency':base_val,'fit_baseline':base_fit_probe,'fit_candidate':base_fit_probe,
 'heldout_baseline':base_val,'heldout_candidate':base_val,'regression_pass':True,'state_integrity':True,'rollback_available':True,
 'metadata':{'family':'CART_AXIS','depth':cart_depth,'compute_bounded':True}})
models[sid]={'family':'CART_AXIS','depth':cart_depth,'model':cart_model}
metrics[sid]={'family':'CART_AXIS','fit_probe':base_fit_probe,'validation':base_val,'depth':cart_depth}

# Generic centroid feature-count family.
keys=sorted({k for x,_ in fit for k in x})
for n in range(1,len(keys)+1):
    m=fit_centroid_strategy(fit,n);va=centroid_accuracy(m,val);tr=centroid_accuracy(m,skill_fit_probe)
    sid=f'CENTROID_F{n:02d}'
    skills.append({'skill_id':sid,'artifact_digest':digest({'family':'CENTROID','features':n,'model':m}),
      'structural_valid':True,'semantic_consistency':va,'fit_baseline':base_fit_probe,'fit_candidate':tr,
      'heldout_baseline':base_val,'heldout_candidate':va,'regression_pass':True,'state_integrity':True,'rollback_available':True,
      'metadata':{'family':'CENTROID','feature_count':n,'compute_bounded':True}})
    models[sid]={'family':'CENTROID','feature_count':n,'model':m}
    metrics[sid]={'family':'CENTROID','fit_probe':tr,'validation':va,'feature_count':n}

# Exact native KNN trials with one shared distance ordering per query.
ks=(1,3,5,7,9)
knn_models={k:fit_knn_strategy(fit,k) for k in ks}
base_knn=knn_models[1]
feat_keys=list(base_knn['features'])
train_matrix=np.asarray([r[0] for r in base_knn['rows']],dtype=float)
train_labels=[r[1] for r in base_knn['rows']]
label_str=np.asarray([str(x) for x in train_labels],dtype=object)
indices=np.arange(len(train_labels))

def knn_trial_predictions(cases):
    by_k={k:[] for k in ks}
    for x,_ in cases:
        q=np.asarray([float(x.get(key,0.0)) for key in feat_keys],dtype=float)
        d2=np.sum((train_matrix-q)**2,axis=1)
        order=np.lexsort((indices,label_str,d2))
        for k in ks:
            nearest=order[:k];votes=Counter(str(train_labels[int(i)]) for i in nearest)
            best=sorted(votes.items(),key=lambda kv:(-kv[1],kv[0]))[0][0]
            chosen=next(train_labels[int(i)] for i in nearest if str(train_labels[int(i)])==best)
            by_k[k].append(chosen)
    return by_k

probe_preds=knn_trial_predictions(skill_fit_probe);val_preds=knn_trial_predictions(val)
# Parity exactness against native knn_predict on a bounded deterministic probe.
for k in ks:
    m=knn_models[k]
    for x,_ in val[:24]:
        q=np.asarray([float(x.get(key,0.0)) for key in feat_keys],dtype=float);d2=np.sum((train_matrix-q)**2,axis=1)
        order=np.lexsort((indices,label_str,d2))[:k];votes=Counter(str(train_labels[int(i)]) for i in order)
        best=sorted(votes.items(),key=lambda kv:(-kv[1],kv[0]))[0][0]
        fast=next(train_labels[int(i)] for i in order if str(train_labels[int(i)])==best)
        if fast!=knn_predict(m,x):raise RuntimeError('FAST_KNN_PARITY_DRIFT:'+str(k))
    tr=sum(p==y for p,(_,y) in zip(probe_preds[k],skill_fit_probe))/len(skill_fit_probe)
    va=sum(p==y for p,(_,y) in zip(val_preds[k],val))/len(val)
    sid=f'KNN_K{k}'
    skills.append({'skill_id':sid,'artifact_digest':digest({'family':'KNN','k':k,'model':m}),
      'structural_valid':True,'semantic_consistency':va,'fit_baseline':base_fit_probe,'fit_candidate':tr,
      'heldout_baseline':base_val,'heldout_candidate':va,'regression_pass':True,'state_integrity':True,'rollback_available':True,
      'metadata':{'family':'KNN','k':k,'compute_bounded':True,'fast_path_parity':True}})
    models[sid]={'family':'KNN','k':k,'model':m}
    metrics[sid]={'family':'KNN','fit_probe':tr,'validation':va,'k':k}

if DB.exists():DB.unlink()
k=UnifiedYADOKernelV30RC8ExternalCognitive(db_path=str(DB))
try:
    goal=k.executive.create_goal(
      objective='Replace an intractable exhaustive segmentation meta-learner branch with a bounded native learner family while preserving the same KEEP/DROP feature contract and fresh robustness gates.',
      required_capabilities={'NATIVE_RAW_REPRESENTATION_SEGMENTATION_META_LEARNER_EXPANSION_V7':1.0},
      success_criteria={'window_validation':.90,'window_blind':.90,'fresh_sequential':.98,'rollback':True},
    )
    deficits=k.executive.detect_deficits(goal.goal_id)
    selection=k.select_evolution_skills(skills,max_skills=1,min_semantic_consistency=.90,min_fit_gain=0.0,max_heldout_drop=0.0,min_heldout_gain=0.0)
finally:
    try:k.close()
    except Exception:pass
    try:
        if DB.exists():DB.unlink()
    except Exception:pass

selected_id=(selection.get('selected_skill_ids') or [None])[0]
selected=models.get(selected_id)
if selected is None:raise RuntimeError('NO_NATIVE_META_LEARNER_SELECTED')
log('native_meta_family_selected',selected_id=selected_id,selection=selection,metrics=metrics.get(selected_id))

if os.getenv('YADO_V7_SELECTION_ONLY')=='1':
    probe={
      'schema':'yado.g2.native_raw_representation_segmentation_meta_learner.selection_probe.v7',
      'status':'PASS_SELECTION_ONLY',
      'spent_repro':spent_repro,
      'cart_baseline_validation':cart_val,
      'family_candidate_count':len(skills),
      'native_selection':selection,
      'selected_skill_id':selected_id,
      'selected_family':selected.get('family') if selected else None,
      'selected_metrics':metrics.get(selected_id),
      'fresh_consumed':False,
      'canonical_mutation':False,
      'g3_genesis_performed':False,
    }
    probe['probe_digest']=digest(probe)
    pp=REPO/'architecture/yado-kernel-g2-native-raw-representation-segmentation-meta-learner-v7-selection-probe.json'
    write(pp,probe)
    print(json.dumps(probe,indent=2,sort_keys=True,default=str))
    raise SystemExit(0)

revealed=fit+val
family=selected['family']
if family=='CART_AXIS':
    final_model=fit_tree(revealed,int(selected['depth']))
    meta_predict=lambda x:tree_predict(final_model,x)
elif family=='CENTROID':
    final_model=fit_centroid_strategy(revealed,int(selected['feature_count']))
    meta_predict=lambda x:centroid_predict(final_model,x)
elif family=='KNN':
    final_model=fit_knn_strategy(revealed,int(selected['k']))
    fk_keys=list(final_model['features']);fk_X=np.asarray([r[0] for r in final_model['rows']],dtype=float)
    fk_labels=[r[1] for r in final_model['rows']];fk_s=np.asarray([str(x) for x in fk_labels],dtype=object);fk_i=np.arange(len(fk_labels));fk_k=int(selected['k'])
    def meta_predict(x):
        q=np.asarray([float(x.get(key,0.0)) for key in fk_keys],dtype=float);d2=np.sum((fk_X-q)**2,axis=1)
        order=np.lexsort((fk_i,fk_s,d2))[:fk_k];votes=Counter(str(fk_labels[int(i)]) for i in order)
        best=sorted(votes.items(),key=lambda kv:(-kv[1],kv[0]))[0][0]
        return next(fk_labels[int(i)] for i in order if str(fk_labels[int(i)])==best)
    for x,_ in blind[:24]:
        if meta_predict(x)!=knn_predict(final_model,x):raise RuntimeError('FINAL_FAST_KNN_PARITY_DRIFT')
else:raise RuntimeError('UNKNOWN_SELECTED_FAMILY:'+str(family))

window_blind=sum(meta_predict(x)==y for x,y in blind)/len(blind)
window_validation=float(metrics[selected_id]['validation'])

def segmented_from_rows(rows):
    kept=[r for r in rows if meta_predict(r['features'])=='KEEP']
    if not kept:return parent_from_segment_rows(rows)
    sums=Counter()
    for r in kept:
        f=r['features'];weight=max(1e-9,r['margin'])*(1.0+f['local_label_support']+f['same_label_run'])
        sums[r['label']]+=weight
    return sorted(sums.items(),key=lambda z:(-z[1],z[0]))[0][0]

def candidate_predict(text):return segmented_from_rows(segment_records(text))

# Fresh V7 family is created only after native family selection.
fresh_domains=['fusion maintenance','pathology exchange','autonomous harbor','identity federation','chip fabrication','pharmacovigilance','lunar logistics','distributed recovery','water permit','clinical registry','rail dispatch','research escrow']
fresh_direct=[]
for gi,label in enumerate([CAP_CONJ,CAP_REL,CAP_BUD,CAP_RES]):
    for i in range(24):
        fresh_direct.append((f"Meta7 {70000+gi*100+i}. "+templates[label][(i*3+gi+1)%4].format(d=fresh_domains[(i*7+gi)%len(fresh_domains)]),label))
fresh_traps=[
 ("Carrier metadata lists owner quota public source rollback and team, but the enclosed release still depends on every compulsory safeguard.",CAP_CONJ),
 ("Every safeguard is green and a quota is visible; the enclosed authorization still depends only on identity and membership relations.",CAP_REL),
 ("Ownership and documentation are settled; the enclosed task is to choose the next investigation under a finite compute allowance.",CAP_BUD),
 ("Budget and membership are settled, but the enclosed task needs a missing current requirement from an authoritative outside source.",CAP_RES),
]*12
def wrap_v7(text,i,layer):
    m=(i*23+layer*11)%16;decoy='owner quota public source rollback group integrity budget relation checks'
    if m==0:return f"<meta7 id='{i%401}' depth='{layer}'><payload>{text}</payload></meta7>"
    if m==1:return f"BEGIN-M7 {i%409}/{layer} {decoy} START {text} END END-M7"
    if m==2:return f"[m7:{i%419}:{layer}] {neutral[i%3]} {text} [/m7]"
    if m==3:return f"Routing M7 {decoy}. PAYLOAD {text}. ROUTING END."
    if m==4:return f"{{m7={i%421};d={layer}}} {neutral[(i+1)%3]} {text} {{/m7}}"
    if m==5:return f"TRACE-M7 {i%431}: {text.lower() if i%2 else text.upper()} :ENDTRACE"
    if m==6:return f"((M7 {layer})) [[decoy {decoy}]] [[{text}]] ((/M7))"
    if m==7:return f"Audit M7 {i%433}. {re.sub(r'\s+',' ',text)} Complete."
    if m==8:return f"{decoy}. {neutral[i%3]} CONTENT {text} END CONTENT."
    if m==9:return f"{neutral[i%3]} meta {decoy}; {text}; {neutral[(i+2)%3]}"
    if m==10:return f"<context-m7><meta>{decoy}</meta><content>{text}</content></context-m7>"
    if m==11:return f"Journal M7 {i%439}: BEGIN {text} END. Metadata {decoy}."
    if m==12:return f"prefix {decoy}; carrier start. {text}. carrier end; suffix {decoy}."
    if m==13:return f"Administrative M7 {i%443}. {neutral[i%3]} PAYLOAD {text} FINISH."
    if m==14:return f"Header M7 nonce={i%449}; {text}; Footer depth={layer}; {decoy}."
    return f"Relay M7 {i%457}. Begin. {text}. Complete."

fresh_pool=fresh_direct+fresh_traps
fresh_wrapped=[(wrap_v7(x,i,0),y) for i,(x,y) in enumerate(fresh_pool)]
rng2=random.Random(2026090817);fresh_seq=[]
for i in range(4000):
    x,y=fresh_pool[(i*73+rng2.randrange(len(fresh_pool)))%len(fresh_pool)]
    z=wrap_v7(x,i,0)
    for layer in range(1,1+(i%12)):z=wrap_v7(z,i+43003*layer,layer)
    fresh_seq.append((z,y))
base_rows=[(r['raw_text'],r['expected']) for r in base['raw_unstructured']['rows']]

def pair(rows):
    ph=0;ch=0
    for text,y in rows:
        sr=segment_records(text);ph+=parent_from_segment_rows(sr)==y;ch+=segmented_from_rows(sr)==y
    n=max(1,len(rows));return ph/n,ch/n
pd,cd=pair(fresh_direct);pt,ct=pair(fresh_traps);pw,cw=pair(fresh_wrapped);ps,cs=pair(fresh_seq);pb,cb=pair(base_rows)
fresh_metrics={
 'parent_direct':pd,'candidate_direct':cd,'parent_traps':pt,'candidate_traps':ct,
 'parent_wrapped':pw,'candidate_wrapped':cw,'parent_sequential':ps,'candidate_sequential':cs,
 'parent_base_regression':pb,'candidate_base_regression':cb,
}
log('fresh_evaluation_done',selected_id=selected_id,window_validation=window_validation,window_blind=window_blind,metrics=fresh_metrics)

checks={
 'v6_admission_withhold_consumed':True,
 'meta_compute_deficit_consumed':compute.get('exact_blocker')=='EXACT_LINEAR_SCORE_SEARCH_STILL_SEMANTICALLY_REQUIRED',
 'cart_baseline_exactly_reproduced':abs(cart_val-0.9167883211678832)<1e-12,
 'native_goal_created':bool(deficits),
 'native_family_menu_generic':all(x['metadata']['family'] in {'CART_AXIS','CENTROID','KNN'} for x in skills),
 'no_class_specific_words_as_features':set(keys)==set(next(iter(fit))[0].keys()) and not any(k in {'text','word','token','label'} for k in keys),
 'native_selector_selected_one_family':selection.get('selected_count')==1 and selected_id is not None,
 'window_validation_ge_0_90':window_validation>=.90,
 'window_blind_ge_0_90':window_blind>=.90,
 'fresh_after_selection':True,
 'fresh_direct_ge_0_98':cd>=.98,
 'fresh_traps_ge_0_95':ct>=.95,
 'fresh_wrapped_ge_0_98':cw>=.98,
 'fresh_sequential_ge_0_98':cs>=.98,
 'fresh_sequential_gain_ge_0_01':cs-ps>=.01,
 'base_regression_ge_0_98':cb>=.98,
 'canonical_mutation':False,
 'g3_not_started':True,
}
positive=[k for k in checks if k!='canonical_mutation']
passed=all(checks[k] is True for k in positive) and checks['canonical_mutation'] is False
status='PASS_SHADOW_G2_NATIVE_RAW_REPRESENTATION_SEGMENTATION_META_LEARNER_EXPANSION_V7' if passed else 'WITHHOLD_G2_NATIVE_RAW_REPRESENTATION_SEGMENTATION_META_LEARNER_EXPANSION_V7'
next_cap='NATIVE_RAW_REPRESENTATION_SEGMENTATION_META_LEARNER_ADMISSION_V8' if passed else 'NATIVE_RAW_REPRESENTATION_HIERARCHICAL_SEGMENTATION_GENESIS_V8'

candidate={
 'schema':'yado.g2.native_raw_representation_segmentation_meta_learner.candidate.v7',
 'status':status,'parent_v5_candidate_digest':v5['candidate_digest'],
 'compute_deficit_receipt':str(COMPUTE.relative_to(REPO)),
 'feature_contract':keys,'family_menu':['CART_AXIS','CENTROID','KNN'],
 'native_selection':selection,'selected_skill_id':selected_id,'selected_family':family,
 'selected_model':final_model,'selection_metrics':metrics,
 'window_validation':window_validation,'window_blind':window_blind,
 'fresh_metrics':fresh_metrics,'canonical_active':False,'canonical_mutation':False,'automatic_promotion':False,
}
candidate['candidate_digest']=digest(candidate);write(CAND,candidate)
fresh_doc={
 'schema':'yado.g2.raw_representation_segmentation_meta_learner_v7.fresh.v1',
 'candidate_digest':candidate['candidate_digest'],'selected_skill_id':selected_id,'fresh_after_selection':True,
 'window_validation':window_validation,'window_blind':window_blind,'metrics':fresh_metrics,
 'direct_count':len(fresh_direct),'trap_count':len(fresh_traps),'wrapped_count':len(fresh_wrapped),'sequential_count':len(fresh_seq),
}
fresh_doc['dataset_digest']=digest(fresh_doc);write(FRESH,fresh_doc)
report={
 'schema':'yado.g2.native_raw_representation_segmentation_meta_learner_expansion.v7',
 'status':status,'parent_v6_receipt':v6['receipt_sha256'],'compute_deficit_receipt':str(COMPUTE.relative_to(REPO)),
 'native_goal_deficits':[str(getattr(x,'deficit_id',x)) for x in deficits],
 'family_candidate_count':len(skills),'native_selection':selection,'selected_skill_id':selected_id,'selected_family':family,
 'window_validation':window_validation,'window_blind':window_blind,'fresh_metrics':fresh_metrics,'checks':checks,
 'candidate_digest':candidate['candidate_digest'],'fresh_dataset_digest':fresh_doc['dataset_digest'],
 'canonical_mutation':False,'promotion_applied':False,'g3_genesis_performed':False,'next_required_capability':next_cap,
 'semantic_boundary':'V7 CONSUMES THE COMPUTE DEFICIT OF THE ORIGINAL CART/EXHAUSTIVE-LINEAR META BANK AND EXPANDS ONLY TO YADO EXISTING BOUNDED CART, CENTROID AND KNN FAMILIES. ALL FAMILIES USE THE SAME NONLEXICAL SEGMENT SCORE/GEOMETRY/CONSISTENCY FEATURE CONTRACT. NATIVE SKILL ADMISSION SELECTS THE FAMILY BEFORE A NEW FRESH DEEP-WRAPPER CHALLENGE. NO CANONICAL MUTATION OR G3 TRANSITION.',
}
report['receipt_sha256']=digest(report);write(OUT,report)
print(json.dumps(report,indent=2,sort_keys=True,default=str))
if not passed:raise SystemExit(2)
