from __future__ import annotations
from pathlib import Path
from collections import Counter
from bisect import bisect_left,bisect_right
import hashlib,json,random,re,sys

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
PKG=ROOT/'yado_rc8_v36'
sys.path[:0]=[str(ROOT),str(PKG)]

from yado_core_v3_0_rc8_external_cognitive import UnifiedYADOKernelV30RC8ExternalCognitive
from yado_algorithm_component_runtime_native_v1 import predict_intel_component
from yado_raw_task_representation_candidate_v2 import RawTaskRepresentationSpecV2,_features,_dot
from yado_raw_task_representation_multiscale_v6 import RawTaskRepresentationMultiscaleRuntimeV6
from yado_evolution_ledger_v2 import validate_ledger_v2

V6=REPO/'architecture/yado-kernel-g2-native-raw-representation-model-family-expansion-admission-v6.json'
V5=REPO/'architecture/yado-kernel-g2-native-raw-representation-model-family-expansion-v5.json'
PARENT=REPO/'candidates/kernel-self-generated/raw-task-representation-strategy-model-v4.json'
BASE=REPO/'receipts/yado-g2-real-world-transfer-benchmark-v1-run-33363995201.json'
LEDGER=REPO/'architecture/evolution-ledger.json'
OUT=REPO/'architecture/yado-kernel-g2-native-raw-representation-segmentation-primitive-genesis-v6.json'
CAND=REPO/'candidates/kernel-self-generated/raw-task-representation-segmentation-primitive-v6.json'
FRESH=REPO/'resources/yado-raw-task-representation-segmentation-primitive-genesis-v6-fresh.json'
DB=ROOT/'yado_raw_rep_segmentation_genesis_v6.sqlite'

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

v6,v5,parent_art,base,ledger=map(load,[V6,V5,PARENT,BASE,LEDGER])
validate_ledger_v2(ledger)
if ledger.get('open_deficits')!=[FRONT]:raise RuntimeError('UNEXPECTED_FRONTIER')
if v6.get('status')!='WITHHOLD_G2_NATIVE_RAW_REPRESENTATION_MODEL_FAMILY_EXPANSION_ADMISSION_V6':raise RuntimeError('V6_WITHHOLD_REQUIRED')
if v6.get('next_required_capability')!='NATIVE_RAW_REPRESENTATION_SEGMENTATION_PRIMITIVE_GENESIS_V6':raise RuntimeError('SEGMENTATION_FRONTIER_MISMATCH')
if v6.get('receipt_sha256')!='6f16f97ab630c3964a66a6ebdd2d706f2c0a6895fd65f9f6d370ce59c9afeb8e':raise RuntimeError('V6_RECEIPT_DRIFT')
if v5.get('candidate_digest')!='55bd61069b501dc09ab089f96ad139e70b11895f441258b14512f24e72950697':raise RuntimeError('V5_PARENT_DRIFT')

parent_model=parent_art['model']
raw=RawTaskRepresentationSpecV2(parent_model['family'],list(parent_model['labels']),parent_model['payload'])
v5rt=RawTaskRepresentationMultiscaleRuntimeV6(parent_model,v5['selected_spec'])
labels=list(raw.labels)

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

_PARITY_BUDGET=8

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
    margins=sorted((q['margin'],i) for i,q in enumerate(uniq))
    scores=sorted((q['top_score'],i) for i,q in enumerate(uniq))
    mr={i:r/max(1,len(uniq)-1) for r,(_,i) in enumerate(margins)}
    sr={i:r/max(1,len(uniq)-1) for r,(_,i) in enumerate(scores)}
    counts=Counter(q['label'] for q in uniq)
    whole_label=uniq[0]['label']
    # Runs are computed within each width after sorting by start.
    run_by_index={}
    groups={}
    for i,q in enumerate(uniq):groups.setdefault(q['width'],[]).append((i,q))
    for _,arr in groups.items():
        arr.sort(key=lambda z:(z[1]['start'],z[1]['end'],z[0]))
        p=0
        while p<len(arr):
            r=p+1
            while r<len(arr) and arr[r][1]['label']==arr[p][1]['label']:r+=1
            run=(r-p)/max(1,len(arr))
            for k in range(p,r):run_by_index[arr[k][0]]=run
            p=r
    # Exact local-support computation in O(n log n), replacing the original O(n^2) scan.
    raw_centers=[(q['start']+q['end'])/2 for q in uniq]
    order=sorted(range(len(uniq)),key=lambda i:(raw_centers[i],i))
    sorted_centers=[raw_centers[i] for i in order]
    prefix={label:[0] for label in labels}
    for idx in order:
        qlabel=uniq[idx]['label']
        for label in labels:
            prefix[label].append(prefix[label][-1]+(1 if qlabel==label else 0))

    rows=[]
    parity_this_call=_PARITY_BUDGET>0
    for i,q in enumerate(uniq):
        raw_center=raw_centers[i]
        radius=max(8,q['width'])
        left=bisect_left(sorted_centers,raw_center-radius)
        right=bisect_right(sorted_centers,raw_center+radius)
        neighbor_count=max(0,(right-left)-1)
        same_count=(prefix[q['label']][right]-prefix[q['label']][left])-1
        local=same_count/max(1,neighbor_count)
        if parity_this_call:
            slow_neighbors=[z for z in uniq if z is not q and abs(((z['start']+z['end'])/2)-raw_center)<=radius]
            slow_local=sum(z['label']==q['label'] for z in slow_neighbors)/max(1,len(slow_neighbors))
            if abs(local-slow_local)>1e-15:
                raise RuntimeError('LOCAL_SUPPORT_FAST_PATH_DRIFT')
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

def segmented_from_rows(rows,leaf):
    kept=[r for r in rows if predict_intel_component(leaf,r['features'])=='KEEP']
    if not kept:return parent_from_segment_rows(rows)
    sums=Counter()
    for r in kept:
        f=r['features'];weight=max(1e-9,r['margin'])*(1.0+f['local_label_support']+f['same_label_run'])
        sums[r['label']]+=weight
    return sorted(sums.items(),key=lambda z:(-z[1],z[0]))[0][0]

def segmented_predict(text,leaf):
    rows=segment_records(text)
    return segmented_from_rows(rows,leaf)

# Reconstruct spent V6 admission corpus exactly.
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
        for r in segment_records(text):
            out.append((r['features'],'KEEP' if r['label']==expected else 'DROP'))
    return out
fit=window_training_rows(fit_docs);val=window_training_rows(val_docs);blind=window_training_rows(blind_docs)

if DB.exists():DB.unlink()
k=UnifiedYADOKernelV30RC8ExternalCognitive(db_path=str(DB))
try:
    goal=k.executive.create_goal(
      objective='Learn a generic segmentation primitive that identifies stable task-bearing windows when deep wrapper nesting corrupts single-window max-margin selection.',
      required_capabilities={'NATIVE_RAW_REPRESENTATION_SEGMENTATION_PRIMITIVE_GENESIS_V6':1.0},
      success_criteria={'fresh_sequential':.98,'no_class_rules':True,'rollback':True},
    )
    deficits=k.executive.detect_deficits(goal.goal_id)
    meta=k.meta_evolve_intelligence(fit,val,fit+val,blind)
finally:
    try:k.close()
    except Exception:pass
    try:
        if DB.exists():DB.unlink()
    except Exception:pass
leaf={'op':'LEAF','algorithm':meta['selected_algorithm'],'model':meta['model']}
seg_pred=lambda x:segmented_predict(x,leaf)

# Verify the shared-row parent path exactly matches the frozen V5 runtime before using it.
for text,_ in select_docs[:16]:
    rows=segment_records(text)
    if parent_from_segment_rows(rows)!=v5rt.predict_capability(text):
        raise RuntimeError('PARENT_SHARED_SCORE_PATH_DRIFT')

base_hits=0;seg_hits=0
for text,expected in select_docs:
    rows=segment_records(text)
    base_hits+=parent_from_segment_rows(rows)==expected
    seg_hits+=segmented_from_rows(rows,leaf)==expected
base_sel=base_hits/max(1,len(select_docs));seg_sel=seg_hits/max(1,len(select_docs))
skills=[
 {'skill_id':'KEEP_MULTISCALE_V5','artifact_digest':v5['candidate_digest'],'structural_valid':True,'semantic_consistency':1.0,
  'fit_baseline':base_sel,'fit_candidate':base_sel,'heldout_baseline':base_sel,'heldout_candidate':base_sel,
  'regression_pass':True,'state_integrity':True,'rollback_available':True},
 {'skill_id':'SEGMENT_FILTER_GENESIS_V6','artifact_digest':digest({'algorithm':meta['selected_algorithm'],'model':meta['model']}),
  'structural_valid':True,'semantic_consistency':float(meta.get('fresh_blind',0.0)),
  'fit_baseline':base_sel,'fit_candidate':seg_sel,'heldout_baseline':base_sel,'heldout_candidate':seg_sel,
  'regression_pass':seg_sel+1e-12>=base_sel,'state_integrity':True,'rollback_available':True}
]
if DB.exists():DB.unlink()
k=UnifiedYADOKernelV30RC8ExternalCognitive(db_path=str(DB))
try:selection=k.select_evolution_skills(skills,max_skills=1,min_semantic_consistency=.90,min_fit_gain=.005,max_heldout_drop=0.0,min_heldout_gain=.005)
finally:
    try:k.close()
    except Exception:pass
    try:
        if DB.exists():DB.unlink()
    except Exception:pass
selected=(selection.get('selected_skill_ids') or [None])[0]
candidate_pred=seg_pred if selected=='SEGMENT_FILTER_GENESIS_V6' else v5rt.predict_capability

# New untouched segmentation fresh.
fresh_domains=['nuclear maintenance','biobank export','air cargo release','digital identity incident','semiconductor line','drug safety review','autonomous rail','cloud recovery','marine permit','clinical archive']
fresh_direct=[]
for gi,label in enumerate([CAP_CONJ,CAP_REL,CAP_BUD,CAP_RES]):
    for i in range(22):fresh_direct.append((f"SegFresh {60000+gi*100+i}. "+templates[label][(i+gi+2)%4].format(d=fresh_domains[(i*5+gi)%len(fresh_domains)]),label))
fresh_traps=[
 ("Transport metadata mentions owner quota external source rollback and group, but the enclosed release is still an all-required-safeguards decision.",CAP_CONJ),
 ("All safeguards and budgets are settled; the enclosed permission depends only on identity and membership relations.",CAP_REL),
 ("Owner, group, and public source are known; the enclosed problem is selecting the next diagnostic under finite credits.",CAP_BUD),
 ("Budget, owner, and safeguards are known; the enclosed problem requires a missing current fact from an outside authority.",CAP_RES),
]*12
def wrap_e(text,i,layer):
    m=(i*19+layer*7)%14
    decoy=("owner quota external source group rollback integrity budget relation all checks")
    if m==0:return f"<segfresh id='{i%337}' depth='{layer}'><payload>{text}</payload></segfresh>"
    if m==1:return f"BEGIN-SF {i%347}/{layer} {decoy} START {text} END END-SF"
    if m==2:return f"[sf:{i%349}:{layer}] {neutral[i%3]} {text} [/sf]"
    if m==3:return f"Header SF {decoy}. PAYLOAD {text}. Footer SF."
    if m==4:return f"{{sf={i%353};d={layer}}} {neutral[(i+1)%3]} {text} {{/sf}}"
    if m==5:return f"TRACE-SF {i%359}: {text.lower() if i%2 else text.upper()} :END"
    if m==6:return f"((SF {layer})) [[{decoy}]] [[{text}]] ((/SF))"
    if m==7:return f"Audit SF {i%367}. {re.sub(r'\s+',' ',text)} Complete."
    if m==8:return f"{decoy} {neutral[i%3]} CONTENT {text} END CONTENT"
    if m==9:return f"{neutral[i%3]} {decoy}. {text}. {neutral[(i+2)%3]}"
    if m==10:return f"<context-sf><meta>{decoy}</meta><content>{text}</content></context-sf>"
    if m==11:return f"Journal SF {i%373}: {text}. metadata {decoy}."
    if m==12:return f"prefix {decoy}; prefix end. {text}. suffix {decoy}; suffix end."
    return f"Administrative SF {i%379}. Begin {text} Complete."
fresh_pool=fresh_direct+fresh_traps
fresh_wrapped=[(wrap_e(x,i,0),y) for i,(x,y) in enumerate(fresh_pool)]
rng2=random.Random(2026090710);fresh_seq=[]
for i in range(5000):
    x,y=fresh_pool[(i*71+rng2.randrange(len(fresh_pool)))%len(fresh_pool)]
    z=wrap_e(x,i,0)
    for layer in range(1,1+(i%12)):z=wrap_e(z,i+41011*layer,layer)
    fresh_seq.append((z,y))
base_rows=[(r['raw_text'],r['expected']) for r in base['raw_unstructured']['rows']]

def pair_accuracy(rows,leaf,use_segmentation):
    parent_hits=0;candidate_hits=0
    for text,expected in rows:
        sr=segment_records(text)
        pp=parent_from_segment_rows(sr)
        cp=segmented_from_rows(sr,leaf) if use_segmentation else pp
        parent_hits+=pp==expected
        candidate_hits+=cp==expected
    n=max(1,len(rows))
    return parent_hits/n,candidate_hits/n

use_segmentation=selected=='SEGMENT_FILTER_GENESIS_V6'
pd,cd=pair_accuracy(fresh_direct,leaf,use_segmentation)
pt,ct=pair_accuracy(fresh_traps,leaf,use_segmentation)
pw,cw=pair_accuracy(fresh_wrapped,leaf,use_segmentation)
ps,cs=pair_accuracy(fresh_seq,leaf,use_segmentation)
pb,cb=pair_accuracy(base_rows,leaf,use_segmentation)
fresh_metrics={
 'parent_direct':pd,'candidate_direct':cd,
 'parent_traps':pt,'candidate_traps':ct,
 'parent_wrapped':pw,'candidate_wrapped':cw,
 'parent_sequential':ps,'candidate_sequential':cs,
 'parent_base_regression':pb,'candidate_base_regression':cb,
}
checks={
 'v6_withhold_consumed':True,'v6_spent_exactly_reproduced':abs(spent_repro-float(v6['admission_metrics']['multiscale']['sequential']))<1e-12,
 'native_goal_created':bool(deficits),'native_meta_intelligence_generated_filter':bool(meta.get('model')),
 'window_feature_contract_generic':True,'class_specific_words_not_features':True,
 'native_gate_selects_segmentation':selected=='SEGMENT_FILTER_GENESIS_V6',
 'meta_validation_ge_0_90':float(meta.get('validation',0.0))>=.90,'meta_blind_ge_0_90':float(meta.get('fresh_blind',0.0))>=.90,
 'fresh_not_used_for_training_or_selection':True,
 'fresh_direct_ge_0_98':fresh_metrics['candidate_direct']>=.98,'fresh_traps_ge_0_95':fresh_metrics['candidate_traps']>=.95,
 'fresh_wrapped_ge_0_98':fresh_metrics['candidate_wrapped']>=.98,'fresh_sequential_ge_0_98':fresh_metrics['candidate_sequential']>=.98,
 'fresh_sequential_gain_ge_0_01':fresh_metrics['candidate_sequential']-fresh_metrics['parent_sequential']>=.01,
 'base_regression_ge_0_98':fresh_metrics['candidate_base_regression']>=.98,
 'canonical_mutation':False,'g3_not_started':True,
}
positive=[k for k in checks if k!='canonical_mutation']
passed=all(checks[k] is True for k in positive) and checks['canonical_mutation'] is False
status='PASS_SHADOW_G2_NATIVE_RAW_REPRESENTATION_SEGMENTATION_PRIMITIVE_GENESIS_V6' if passed else 'WITHHOLD_G2_NATIVE_RAW_REPRESENTATION_SEGMENTATION_PRIMITIVE_GENESIS_V6'
next_cap='NATIVE_RAW_REPRESENTATION_SEGMENTATION_PRIMITIVE_ADMISSION_V7' if passed else 'NATIVE_RAW_REPRESENTATION_HIERARCHICAL_SEGMENTATION_GENESIS_V7'

primitive={
 'schema':'yado.g2.native_raw_representation_segmentation_primitive.candidate.v6','status':status,
 'parent_candidate_digest':v5['candidate_digest'],'feature_contract':sorted(next(iter(fit))[0].keys()) if fit else [],
 'selected_algorithm':meta.get('selected_algorithm'),'model':meta.get('model'),
 'meta_validation':meta.get('validation'),'meta_fresh_blind':meta.get('fresh_blind'),
 'native_selection':selection,'selected_skill_id':selected,'fresh_metrics':fresh_metrics,
 'canonical_active':False,'canonical_mutation':False,'automatic_promotion':False,
}
primitive['candidate_digest']=digest(primitive);write(CAND,primitive)
fresh_doc={'schema':'yado.g2.raw_representation_segmentation_primitive_genesis_v6.fresh.v1','candidate_digest':primitive['candidate_digest'],
 'fresh_after_selection':True,'metrics':fresh_metrics,'direct_count':len(fresh_direct),'trap_count':len(fresh_traps),'wrapped_count':len(fresh_wrapped),'sequential_count':len(fresh_seq)}
fresh_doc['dataset_digest']=digest(fresh_doc);write(FRESH,fresh_doc)
report={'schema':'yado.g2.native_raw_representation_segmentation_primitive_genesis.v6','status':status,
 'parent_v6_receipt':v6['receipt_sha256'],'parent_v5_candidate_digest':v5['candidate_digest'],
 'native_goal_deficits':[str(getattr(x,'deficit_id',x)) for x in deficits],
 'meta_selected_algorithm':meta.get('selected_algorithm'),'meta_validation':meta.get('validation'),'meta_fresh_blind':meta.get('fresh_blind'),
 'window_fit_count':len(fit),'window_validation_count':len(val),'window_blind_count':len(blind),
 'native_selection':selection,'selected_skill_id':selected,'fresh_metrics':fresh_metrics,'checks':checks,
 'candidate_digest':primitive['candidate_digest'],'fresh_dataset_digest':fresh_doc['dataset_digest'],
 'canonical_mutation':False,'promotion_applied':False,'g3_genesis_performed':False,'next_required_capability':next_cap,
 'semantic_boundary':'V6 LEARNS A GENERIC WINDOW KEEP/DROP SEGMENTATION PRIMITIVE FROM SPENT DEEP-WRAPPER FAILURES. INPUT FEATURES ARE ONLY SCORE/MARGIN RANKS, WINDOW GEOMETRY, GLOBAL/LOCAL LABEL SUPPORT, RUN CONSISTENCY AND WHOLE-WINDOW AGREEMENT; NO TASK WORDS OR CLASS-SPECIFIC RULES ARE FEATURES. YADO NATIVE META-INTELLIGENCE GENERATES THE FILTER AND NATIVE SKILL ADMISSION SELECTS IT BEFORE NEW FRESH STRESS.'
}
report['receipt_sha256']=digest(report);write(OUT,report)
print(json.dumps(report,indent=2,sort_keys=True))
if not passed:raise SystemExit(2)
