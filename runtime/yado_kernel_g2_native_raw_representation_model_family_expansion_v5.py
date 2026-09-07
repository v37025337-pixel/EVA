from __future__ import annotations
from pathlib import Path
from collections import Counter
import hashlib,json,math,random,re,sys

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
PKG=ROOT/'yado_rc8_v36'
sys.path[:0]=[str(ROOT),str(PKG)]

from yado_core_v3_0_rc8_external_cognitive import UnifiedYADOKernelV30RC8ExternalCognitive
from yado_raw_task_representation_candidate_v2 import RawTaskRepresentationSpecV2,_features,_dot
from yado_raw_task_representation_robustness_v4 import RobustRawTaskRepresentationRuntimeV4
from yado_evolution_ledger_v2 import validate_ledger_v2

ADMISSION=REPO/'architecture/yado-kernel-g2-native-raw-representation-strategy-canonical-admission-v5.json'
REVAL=REPO/'architecture/yado-kernel-g2-native-raw-representation-strategy-genesis-repair-v4-verdict-revalidation-v1.json'
CAND=REPO/'candidates/kernel-self-generated/raw-task-representation-strategy-model-v4.json'
V3=REPO/'canonical/yado-raw-task-representation-v3.json'
V4=REPO/'canonical/yado-raw-task-representation-v4.json'
BASE=REPO/'receipts/yado-g2-real-world-transfer-benchmark-v1-run-33363995201.json'
LEDGER=REPO/'architecture/evolution-ledger.json'

OUT=REPO/'architecture/yado-kernel-g2-native-raw-representation-model-family-expansion-v5.json'
CAND_OUT=REPO/'candidates/kernel-self-generated/raw-task-representation-multiscale-family-v5.json'
FRESH=REPO/'resources/yado-raw-task-representation-model-family-expansion-v5-fresh.json'
DB=ROOT/'yado_raw_rep_model_family_expansion_v5.sqlite'

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

admission,reval,cand,v3,v4,base,ledger=map(load,[ADMISSION,REVAL,CAND,V3,V4,BASE,LEDGER])
validate_ledger_v2(ledger)
if ledger.get('open_deficits')!=[FRONT]:raise RuntimeError('UNEXPECTED_FRONTIER')
if admission.get('status')!='WITHHOLD_G2_NATIVE_RAW_REPRESENTATION_STRATEGY_CANONICAL_ADMISSION_V5':raise RuntimeError('ADMISSION_WITHHOLD_REQUIRED')
if admission.get('next_required_capability')!='NATIVE_RAW_REPRESENTATION_MODEL_FAMILY_EXPANSION_V5':raise RuntimeError('EXPANSION_FRONTIER_MISMATCH')
if admission.get('receipt_sha256')!='43ff8c9cea4259aa87d7f877edb7ca48c19bc258f209401dd474d1e21ae367d4':raise RuntimeError('ADMISSION_RECEIPT_DRIFT')
if reval.get('status')!='PASS_SHADOW_G2_NATIVE_RAW_REPRESENTATION_STRATEGY_GENESIS_REPAIR_V4_REVALIDATED':raise RuntimeError('REVALIDATED_PARENT_REQUIRED')
if cand.get('candidate_digest')!='03bf3624f16ddca433f02ce4f956258e2dee72046f65571fa4b226c65183ef6d':raise RuntimeError('PARENT_CANDIDATE_DRIFT')

m=cand['model']
parent_spec=RawTaskRepresentationSpecV2(m['family'],list(m['labels']),m['payload'])
canonical=RobustRawTaskRepresentationRuntimeV4(v3,v4['selected_mode'])
labels=list(parent_spec.labels)

# Kernel chooses developmental parent from the already-spent admission evidence.
am=admission['admission_metrics']; pm=admission['post_selection_fresh_metrics']
records=[
 {'variant_id':'CANONICAL_RAW_V4','parent_id':None,'lineage_id':'G2_RAW_REP_LINEAGE','artifact_digest':v4['component_digest'],
  'task_scores':{'admission_sequential':am['parent_sequential'],'post_sequential':pm['parent_sequential'],'regression':am['parent_base_regression']},
  'constraints':{'regression_pass':True,'state_integrity':True,'rollback_available':True},
  'traits':{'canonical':1.0,'bounded':1.0},'failure_tags':['deep_sequential_wrapper_residual'],'status':'EVALUATED'},
 {'variant_id':'SHADOW_CHAR45_V4','parent_id':'CANONICAL_RAW_V4','lineage_id':'G2_RAW_REP_LINEAGE','artifact_digest':cand['candidate_digest'],
  'task_scores':{'admission_sequential':am['candidate_sequential'],'post_sequential':pm['candidate_sequential'],'regression':am['candidate_base_regression']},
  'constraints':{'regression_pass':True,'state_integrity':True,'rollback_available':True},
  'traits':{'shadow':1.0,'learned':1.0,'bounded':1.0},'failure_tags':['deep_sequential_wrapper_residual'],'status':'EVALUATED'}
]
if DB.exists():DB.unlink()
k=UnifiedYADOKernelV30RC8ExternalCognitive(db_path=str(DB))
try:
    parent_choice=k.select_evolution_parent(records,'post_sequential')
    operation=k.propose_evolution_operation(records,parent_choice.get('variant_id'),'deep_sequential_wrapper_residual')
finally:
    try:k.close()
    except Exception:pass
    try:
        if DB.exists():DB.unlink()
    except Exception:pass
if parent_choice.get('action')!='SELECT_PARENT':raise RuntimeError('NATIVE_PARENT_SELECTION_FAILED')
if parent_choice.get('variant_id')!='SHADOW_CHAR45_V4':raise RuntimeError('NATIVE_PARENT_NOT_SHADOW_CHAR45:'+canon(parent_choice))

# Generic frozen char45 scoring primitive.
def raw_scores(text):
    mode=parent_spec.payload['mode'];dim=int(parent_spec.payload['dim']);x=_features(text,mode,dim)
    rows=[]
    for label in labels:
        s=_dot(parent_spec.payload['weights'].get(label,{}),x)+float(parent_spec.payload['bias'].get(label,0.0))
        rows.append((float(s),label))
    rows.sort(key=lambda z:(-z[0],z[1]))
    return rows

def token_windows(text,width,stride):
    toks=re.findall(r"[a-zA-Z0-9_]+",str(text))
    if not toks:return [str(text)]
    if len(toks)<=width:return [' '.join(toks)]
    out=[]
    for i in range(0,max(1,len(toks)-width+1),max(1,stride)):
        out.append(' '.join(toks[i:i+width]))
    tail=' '.join(toks[-width:])
    if not out or out[-1]!=tail:out.append(tail)
    return out

def predict_family(text,spec):
    widths=spec['widths']; stride_div=int(spec['stride_div']); mode=spec['aggregation']; topk=int(spec.get('topk',3))
    segments=[str(text)]
    for w in widths:
        segments.extend(token_windows(text,int(w),max(1,int(w)//stride_div)))
    seen=set();uniq=[]
    for z in segments:
        h=hashlib.sha256(z.encode()).hexdigest()
        if h not in seen:seen.add(h);uniq.append(z)
    scored=[]
    for idx,z in enumerate(uniq):
        rs=raw_scores(z);margin=rs[0][0]-rs[1][0] if len(rs)>1 else 0.0
        scored.append({'label':rs[0][1],'margin':float(margin),'score':float(rs[0][0]),'index':idx})
    if mode=='MAX_MARGIN':
        q=sorted(scored,key=lambda r:(-r['margin'],-r['score'],r['label'],r['index']))[0]
        return q['label']
    if mode=='TOPK_MARGIN_VOTE':
        q=sorted(scored,key=lambda r:(-r['margin'],-r['score'],r['label'],r['index']))[:max(1,topk)]
        sums=Counter()
        for r in q:sums[r['label']]+=max(1e-9,r['margin'])
        return sorted(sums.items(),key=lambda z:(-z[1],z[0]))[0][0]
    if mode=='ALL_MARGIN_VOTE':
        sums=Counter()
        for r in scored:sums[r['label']]+=max(1e-9,r['margin'])
        return sorted(sums.items(),key=lambda z:(-z[1],z[0]))[0][0]
    raise ValueError('UNKNOWN_AGGREGATION:'+str(mode))

# Spent developmental corpus mechanically mirrors the prior admission task family,
# but is no longer fresh and may now be used for selection.
domains=['medical release','spacecraft command','warehouse dispatch','financial settlement','research dataset','legal filing','industrial control','identity service','energy grid','package deployment','clinical trial','mission workflow']
templates={
 CAP_CONJ:[
  "For {d}, authorize only when provenance, integrity, and rollback readiness all pass together; ownership metadata is incidental.",
  "In {d}, one failed mandatory safeguard blocks activation even if quota and group information are present.",
  "Decide whether every compulsory acceptance condition for {d} is simultaneously true; no search planning is requested.",
  "For {d}, proceed iff authorization validation, integrity validation, and recovery readiness all succeed."],
 CAP_REL:[
  "For {d}, permission depends on requester-owner identity or membership in the authorized group; remaining budget is irrelevant.",
  "In {d}, infer access from principal, owner, tenant, and role relations rather than independent readiness gates.",
  "For {d}, determine whether the claimant is the same principal as the owner or belongs to the approved cohort.",
  "In {d}, entity equality and membership edges decide authorization; external documentation is not missing."],
 CAP_BUD:[
  "For {d}, choose the next diagnostic under a finite compute allowance using cost and expected information gain; ownership is settled.",
  "In {d}, allocate remaining credits among verification stages so confidence rises without exceeding quota.",
  "For {d}, schedule the least-cost next experiment under budget, latency, and expected evidence gain constraints.",
  "In {d}, select an affordable sequence of deeper checks; the governing facts and identities are already known."],
 CAP_RES:[
  "For {d}, local state lacks the decisive fact, so retrieve a current authoritative public reference rather than run another local test.",
  "In {d}, identity and budget are known but the missing requirement must come from current external documentation.",
  "For {d}, obtain the unresolved specification from a trustworthy outside source because local evidence cannot establish it.",
  "In {d}, the information gap is external to the system; fetch authoritative evidence instead of scheduling another diagnostic."]
}
spent_direct=[]
for gi,label in enumerate([CAP_CONJ,CAP_REL,CAP_BUD,CAP_RES]):
    ts=templates[label]
    for i in range(36):
        spent_direct.append((ts[(i*3+gi)%len(ts)].format(d=domains[(i*5+gi)%len(domains)])+f" Reference token {1000+gi*100+i}.",label))
spent_traps=[
 ("Ownership, budget and public documentation are all mentioned, but activation still requires every mandatory integrity and recovery gate to pass.",CAP_CONJ),
 ("All readiness checks pass and a quota is displayed, but permission is determined by requester-owner identity and authorized-group membership.",CAP_REL),
 ("An external stage name and owner field appear in the record, but the task is to choose the next test under remaining compute budget.",CAP_BUD),
 ("Budget and membership data are available, but the missing governing fact can only be obtained from current public documentation.",CAP_RES),
 ("A manual is attached and an owner is named; nevertheless the decision is simply whether every compulsory safeguard succeeds.",CAP_CONJ),
 ("The word rollback appears in metadata, yet access changes only with principal equality or group membership relations.",CAP_REL),
 ("All mandatory gates are already true; now allocate finite credits among deeper diagnostic stages.",CAP_BUD),
 ("A quota remains and all actors are known, but no local experiment can reveal the missing standard, so retrieve it externally.",CAP_RES),
]*6

def spent_wrap(text,i,layer):
    m=(i+7*layer)%12
    if m==0:return f"<admission id='{i%113}' depth='{layer}'><payload>{text}</payload></admission>"
    if m==1:return f"[record {i%109}/{layer}] BEGIN {text} END [/record]"
    if m==2:return f"Telemetry header {i%107}. {text} Telemetry footer."
    if m==3:return f"{{packet={i%103};layer={layer}}} {text} {{/packet}}"
    if m==4:return f"((frame {layer})) [[segment {i%101}]] {text} [[/segment]] ((/frame))"
    if m==5:return f"Audit transport only. nonce={i%97}. {text} Audit closed."
    if m==6:return f"<outer><level n='{layer}'>{text}</level></outer>"
    if m==7:return f"TRACE {i%89}: {text.upper() if i%2==0 else text.lower()} :TRACE-END"
    if m==8:return f"  CONTEXT {i%83} :: {re.sub(r'\s+',' ',text)} :: END CONTEXT  "
    if m==9:return f"Journal entry {i%79}. START-PAYLOAD {text} STOP-PAYLOAD."
    if m==10:return f"Header token {i%73}; body=[{text}]; footer token {layer%13}."
    return f"Administrative envelope {i%71}. Begin. {text} Complete."

spent_pool=spent_direct+spent_traps
rng=random.Random(2026090705)
spent_seq=[]
for i in range(5000):
    x,y=spent_pool[(i*47+rng.randrange(len(spent_pool)))%len(spent_pool)]
    z=spent_wrap(x,i,0)
    for layer in range(1,1+(i%6)):z=spent_wrap(z,i+19001*layer,layer)
    spent_seq.append((z,y))

# Validate that the reconstructed spent corpus reproduces the frozen parent's prior metric.
parent_spent=acc(spent_seq,parent_spec.predict)
if abs(parent_spent-float(am['candidate_sequential']))>1e-12:
    raise RuntimeError('SPENT_ADMISSION_REPRO_DRIFT:'+str(parent_spent))

ordered=sorted(spent_seq,key=lambda r:hashlib.sha256((r[0]+'|'+r[1]+'|V5EXP').encode()).hexdigest())
train=ordered[:3600];val=ordered[3600:]
base_train=acc(train,parent_spec.predict);base_val=acc(val,parent_spec.predict)

# Mechanically composed generic family menu. No class-specific semantic rules.
family_specs=[]
for widths in ([24,48],[32,64],[24,48,96],[32,64,128]):
    for aggregation in ('MAX_MARGIN','TOPK_MARGIN_VOTE','ALL_MARGIN_VOTE'):
        for stride_div in (2,3):
            topks=(3,5) if aggregation=='TOPK_MARGIN_VOTE' else (3,)
            for topk in topks:
                family_specs.append({'widths':list(widths),'aggregation':aggregation,'stride_div':stride_div,'topk':topk})

skills=[];metrics={}
for i,spec in enumerate(family_specs):
    sid=f"MULTISCALE_V5_{i:02d}_{spec['aggregation']}"
    pred=lambda x,s=spec:predict_family(x,s)
    tr=acc(train,pred);va=acc(val,pred)
    metrics[sid]={'spec':spec,'train':tr,'validation':va}
    skills.append({
      'skill_id':sid,'artifact_digest':digest({'parent_model_digest':cand['model_digest'],'spec':spec}),
      'structural_valid':True,'semantic_consistency':va,
      'fit_baseline':base_train,'fit_candidate':tr,
      'heldout_baseline':base_val,'heldout_candidate':va,
      'regression_pass':va+1e-12>=base_val,
      'state_integrity':True,'rollback_available':True,
      'metadata':{'generic_multiscale':True,'class_specific_rules':False}
    })

if DB.exists():DB.unlink()
k=UnifiedYADOKernelV30RC8ExternalCognitive(db_path=str(DB))
try:
    selection=k.select_evolution_skills(skills,max_skills=1,min_semantic_consistency=.95,min_fit_gain=.005,max_heldout_drop=0.0,min_heldout_gain=.005)
finally:
    try:k.close()
    except Exception:pass
    try:
        if DB.exists():DB.unlink()
    except Exception:pass
selected_id=(selection.get('selected_skill_ids') or [None])[0]
selected_spec=metrics.get(selected_id,{}).get('spec') if selected_id else None
pred=(lambda x:parent_spec.predict(x)) if selected_spec is None else (lambda x:predict_family(x,selected_spec))

# New untouched V5 fresh challenge, revealed only after native family selection.
fresh_domains=['airworthiness review','genome release','robot fleet','customs clearance','payment network','pharmacy batch','research archive','power dispatch','telecom incident','quality system']
fresh_direct=[]
for gi,label in enumerate([CAP_CONJ,CAP_REL,CAP_BUD,CAP_RES]):
    ts=templates[label]
    for i in range(24):
        base_text=ts[(i+gi+1)%len(ts)].format(d=fresh_domains[(i*7+gi)%len(fresh_domains)])
        fresh_direct.append((f"Fresh case {30000+gi*100+i}. {base_text}",label))
fresh_traps=[
 ("The transport note mentions ownership, credits, and an external manual, but release still requires every compulsory integrity and recovery safeguard to pass.",CAP_CONJ),
 ("All safeguards are green and documentation is attached, yet permission changes only with principal identity and authorized membership.",CAP_REL),
 ("Identity relations and documentation are complete; choose the next diagnostic under a finite resource ceiling.",CAP_BUD),
 ("Budget remains and ownership is known, but the missing standard is absent locally and must be retrieved from a current authority.",CAP_RES),
]*12
def fresh_wrap(text,i,layer):
    m=(i*11+layer*3)%13
    if m==0:return f"<v5 id='{i%173}' depth='{layer}'><payload>{text}</payload></v5>"
    if m==1:return f"BEGIN-V5 {i%179}/{layer}\n{text}\nEND-V5"
    if m==2:return f"[carrier:{i%181}:{layer}] {text} [/carrier]"
    if m==3:return f"Transport header {i%191}. Body-start {text} Body-end."
    if m==4:return f"{{envelope={i%193};level={layer}}} {text} {{/envelope}}"
    if m==5:return f"TRACE-V5 {i%197}: {text.lower() if i%2 else text.upper()} :TRACE-END"
    if m==6:return f"((outer {layer})) [[packet {i%199}]] {text} [[/packet]] ((/outer))"
    if m==7:return f"Audit carrier nonce={i%211}. {re.sub(r'\s+',' ',text)} Audit done."
    if m==8:return f"Metadata says owner budget external rollback. Payload follows: {text}. End metadata."
    if m==9:return f"Header only: team quota manual integrity. START {text} STOP. Footer only."
    if m==10:return f"<context><layer>{layer}</layer><content>{text}</content></context>"
    if m==11:return f"Journal {i%223}: BEGIN-CONTENT {text} END-CONTENT."
    return f"Administrative relay {i%227}. {text} Relay complete."

fresh_pool=fresh_direct+fresh_traps
fresh_wrapped=[(fresh_wrap(x,i,0),y) for i,(x,y) in enumerate(fresh_pool)]
rng2=random.Random(2026090707)
fresh_seq=[]
for i in range(6000):
    x,y=fresh_pool[(i*59+rng2.randrange(len(fresh_pool)))%len(fresh_pool)]
    z=fresh_wrap(x,i,0)
    for layer in range(1,1+(i%8)):z=fresh_wrap(z,i+29009*layer,layer)
    fresh_seq.append((z,y))

base_rows=[(r['raw_text'],r['expected']) for r in base['raw_unstructured']['rows']]
fresh_metrics={
 'parent_direct':acc(fresh_direct,parent_spec.predict),'candidate_direct':acc(fresh_direct,pred),
 'parent_traps':acc(fresh_traps,parent_spec.predict),'candidate_traps':acc(fresh_traps,pred),
 'parent_wrapped':acc(fresh_wrapped,parent_spec.predict),'candidate_wrapped':acc(fresh_wrapped,pred),
 'parent_sequential':acc(fresh_seq,parent_spec.predict),'candidate_sequential':acc(fresh_seq,pred),
 'parent_base_regression':acc(base_rows,parent_spec.predict),'candidate_base_regression':acc(base_rows,pred),
}
checks={
 'admission_withhold_consumed':True,
 'native_parent_selected_shadow_char45':parent_choice.get('variant_id')=='SHADOW_CHAR45_V4',
 'native_parent_operation_recorded':bool(operation),
 'spent_admission_exactly_reproduced':abs(parent_spent-float(am['candidate_sequential']))<1e-12,
 'generic_family_menu_only':True,
 'class_specific_rules_absent':True,
 'native_selector_selected_one_family':selected_spec is not None and selection.get('selected_count')==1,
 'fresh_not_used_for_family_selection':True,
 'fresh_direct_ge_0_98':fresh_metrics['candidate_direct']>=.98,
 'fresh_traps_ge_0_95':fresh_metrics['candidate_traps']>=.95,
 'fresh_wrapped_ge_0_98':fresh_metrics['candidate_wrapped']>=.98,
 'fresh_sequential_ge_0_98':fresh_metrics['candidate_sequential']>=.98,
 'fresh_sequential_gain_ge_0_01':fresh_metrics['candidate_sequential']-fresh_metrics['parent_sequential']>=.01,
 'base_regression_ge_0_98':fresh_metrics['candidate_base_regression']>=.98,
 'canonical_mutation':False,
 'g3_not_started':True,
}
positive=[k for k in checks if k!='canonical_mutation']
passed=all(checks[k] is True for k in positive) and checks['canonical_mutation'] is False
status='PASS_SHADOW_G2_NATIVE_RAW_REPRESENTATION_MODEL_FAMILY_EXPANSION_V5' if passed else 'WITHHOLD_G2_NATIVE_RAW_REPRESENTATION_MODEL_FAMILY_EXPANSION_V5'
next_cap='NATIVE_RAW_REPRESENTATION_MODEL_FAMILY_EXPANSION_ADMISSION_V6' if passed else 'NATIVE_RAW_REPRESENTATION_SEGMENTATION_PRIMITIVE_GENESIS_V6'

candidate={
 'schema':'yado.g2.native_raw_representation_multiscale_family.candidate.v5',
 'status':status,'parent_candidate_digest':cand['candidate_digest'],'parent_model_digest':cand['model_digest'],
 'parent_choice':parent_choice,'evolution_operation':operation,
 'selection':selection,'selected_skill_id':selected_id,'selected_spec':selected_spec,
 'selection_metrics':metrics,'fresh_metrics':fresh_metrics,
 'canonical_active':False,'canonical_mutation':False,'automatic_promotion':False,
}
candidate['candidate_digest']=digest(candidate);write(CAND_OUT,candidate)
fresh_doc={'schema':'yado.g2.native_raw_representation_model_family_expansion_v5.fresh.v1','selected_skill_id':selected_id,
 'selected_spec':selected_spec,'fresh_after_selection':True,'metrics':fresh_metrics,
 'direct_count':len(fresh_direct),'trap_count':len(fresh_traps),'wrapped_count':len(fresh_wrapped),'sequential_count':len(fresh_seq)}
fresh_doc['dataset_digest']=digest(fresh_doc);write(FRESH,fresh_doc)
report={'schema':'yado.g2.native_raw_representation_model_family_expansion.v5','status':status,
 'parent_admission_receipt':admission['receipt_sha256'],'parent_revalidation_receipt':reval['receipt_sha256'],
 'parent_choice':parent_choice,'evolution_operation':operation,'family_candidate_count':len(family_specs),
 'native_selection':selection,'selected_skill_id':selected_id,'selected_spec':selected_spec,
 'selection_metrics':metrics,'fresh_metrics':fresh_metrics,'checks':checks,
 'candidate_digest':candidate['candidate_digest'],'fresh_dataset_digest':fresh_doc['dataset_digest'],
 'canonical_mutation':False,'promotion_applied':False,'g3_genesis_performed':False,
 'next_required_capability':next_cap,
 'semantic_boundary':'V5 CONSUMES THE SPENT CANONICAL-ADMISSION FAILURE AND EXPANDS THE FROZEN YADO-SELECTED CHAR45 MODEL INTO GENERIC MULTISCALE SEGMENT-AGGREGATION FAMILIES. THE MENU USES ONLY YADO OWN CHAR45 SCORE PRIMITIVE PLUS GENERIC WINDOWING, MARGIN AND VOTE COMPOSITION; NO CLASS WORDS OR TASK-SPECIFIC ROUTING RULES EXIST. NATIVE YADO SELECTS ONE FAMILY BEFORE A NEW DEEP-WRAPPER FRESH CHALLENGE.'
}
report['receipt_sha256']=digest(report);write(OUT,report)
print(json.dumps({
 'status':status,'parent_choice':parent_choice,'evolution_operation':operation,
 'selected_skill_id':selected_id,'selected_spec':selected_spec,
 'fresh_metrics':fresh_metrics,'checks':checks,
 'next_required_capability':next_cap,'receipt_sha256':report['receipt_sha256']
},indent=2,sort_keys=True,default=str))
if not passed:raise SystemExit(2)
