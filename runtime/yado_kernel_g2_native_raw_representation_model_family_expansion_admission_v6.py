from __future__ import annotations
from pathlib import Path
from collections import Counter
from functools import lru_cache
import ast,hashlib,json,random,re,sys

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
PKG=ROOT/'yado_rc8_v36'
sys.path[:0]=[str(ROOT),str(PKG)]

from yado_core_v3_0_rc8_external_cognitive import UnifiedYADOKernelV30RC8ExternalCognitive
from yado_raw_task_representation_candidate_v2 import RawTaskRepresentationSpecV2,_features,_dot
from yado_raw_task_representation_robustness_v4 import RobustRawTaskRepresentationRuntimeV4
from yado_raw_task_representation_multiscale_v6 import RawTaskRepresentationMultiscaleRuntimeV6
from yado_evolution_ledger_v2 import validate_ledger_v2

V5=REPO/'architecture/yado-kernel-g2-native-raw-representation-model-family-expansion-v5.json'
V5C=REPO/'candidates/kernel-self-generated/raw-task-representation-multiscale-family-v5.json'
PARENT=REPO/'candidates/kernel-self-generated/raw-task-representation-strategy-model-v4.json'
V5SRC=ROOT/'yado_kernel_g2_native_raw_representation_model_family_expansion_v5.py'
V3=REPO/'canonical/yado-raw-task-representation-v3.json'
V4=REPO/'canonical/yado-raw-task-representation-v4.json'
BASE=REPO/'receipts/yado-g2-real-world-transfer-benchmark-v1-run-33363995201.json'
LEDGER=REPO/'architecture/evolution-ledger.json'
OUT=REPO/'architecture/yado-kernel-g2-native-raw-representation-model-family-expansion-admission-v6.json'
FRESH=REPO/'resources/yado-raw-task-representation-model-family-expansion-admission-v6-fresh.json'
DB=ROOT/'yado_raw_rep_family_expansion_admission_v6.sqlite'

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

v5,v5c,parent_art,v3,v4,base,ledger=map(load,[V5,V5C,PARENT,V3,V4,BASE,LEDGER])
validate_ledger_v2(ledger)
if ledger.get('open_deficits')!=[FRONT]:raise RuntimeError('UNEXPECTED_FRONTIER')
if v5.get('status')!='PASS_SHADOW_G2_NATIVE_RAW_REPRESENTATION_MODEL_FAMILY_EXPANSION_V5':raise RuntimeError('V5_PASS_REQUIRED')
if v5.get('receipt_sha256')!='0396838dc5b419c04c4ee5b3f0f0a5f2891c0ea2d8767016b08aecd7beb02a85':raise RuntimeError('V5_RECEIPT_DRIFT')
if v5.get('candidate_digest')!='55bd61069b501dc09ab089f96ad139e70b11895f441258b14512f24e72950697':raise RuntimeError('V5_CANDIDATE_DRIFT')
if v5c.get('candidate_digest')!=v5.get('candidate_digest'):raise RuntimeError('V5_CANDIDATE_FILE_DRIFT')
if parent_art.get('model_digest')!='ec9ab1ecc29d45ee2d7c0d616e7e23fcf28d235348a0f5a270dffdeb4e0f7505':raise RuntimeError('PARENT_MODEL_DRIFT')

parent_model=parent_art['model']
parent=RawTaskRepresentationSpecV2(parent_model['family'],list(parent_model['labels']),parent_model['payload'])
expanded=RawTaskRepresentationMultiscaleRuntimeV6(parent_model,v5['selected_spec'])
canonical=RobustRawTaskRepresentationRuntimeV4(v3,v4['selected_mode'])

# Mechanically recover V5 reference family implementation and verify the new reusable runtime is equivalent.
src=V5SRC.read_text(encoding='utf-8');tree=ast.parse(src)
names={'raw_scores','token_windows','predict_family'}
nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names]
if {n.name for n in nodes}!=names:raise RuntimeError('V5_REFERENCE_FUNCTIONS_MISSING')
ns={'Counter':Counter,'hashlib':hashlib,'re':re,'lru_cache':lru_cache,'parent_spec':parent,'labels':list(parent.labels),'_features':_features,'_dot':_dot}
mod=ast.Module(body=nodes,type_ignores=[]);ast.fix_missing_locations(mod);exec(compile(mod,'<v5-reference>','exec'),ns)
ref_predict=lambda text:ns['predict_family'](text,v5['selected_spec'])

compat=[
 "Simple release requires integrity authorization and rollback readiness all together.",
 "Access depends on owner identity and authorized team membership.",
 "Choose the next diagnostic under finite compute quota and expected information gain.",
 "Retrieve a current public specification because local evidence is insufficient.",
]
for i in range(128):
    x=compat[i%4]
    z=f"<compat {i}><layer>{i%7}</layer> meta owner quota external rollback {x} end </compat>"
    if expanded.predict_capability(z)!=ref_predict(z):
        raise RuntimeError('RUNTIME_EQUIVALENCE_FAILURE:'+str(i))
runtime_equivalence=True

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
    ts=templates[label]
    for i in range(30):
        direct.append((f"Admission6 {40000+gi*100+i}. "+ts[(i*5+gi)%len(ts)].format(d=domains[(i*7+gi)%len(domains)]),label))
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
wrapped=[(wrap_c(x,i,0),y) for i,(x,y) in enumerate(pool)]
rng=random.Random(2026090708)
seq=[]
for i in range(7000):
    x,y=pool[(i*61+rng.randrange(len(pool)))%len(pool)]
    z=wrap_c(x,i,0)
    for layer in range(1,1+(i%10)):z=wrap_c(z,i+31013*layer,layer)
    seq.append((z,y))

base_rows=[(r['raw_text'],r['expected']) for r in base['raw_unstructured']['rows']]
def metrics_for(pred):
    return {'direct':acc(direct,pred),'traps':acc(traps,pred),'wrapped':acc(wrapped,pred),'sequential':acc(seq,pred),'base_regression':acc(base_rows,pred)}
m_can=metrics_for(canonical.predict_capability);m_parent=metrics_for(parent.predict);m_exp=metrics_for(expanded.predict_capability)

skills=[
 {'skill_id':'KEEP_CANONICAL_V4','artifact_digest':v4['component_digest'],'structural_valid':True,'semantic_consistency':1.0,
  'fit_baseline':m_can['direct'],'fit_candidate':m_can['direct'],'heldout_baseline':m_can['sequential'],'heldout_candidate':m_can['sequential'],
  'regression_pass':True,'state_integrity':True,'rollback_available':True},
 {'skill_id':'KEEP_SHADOW_CHAR45','artifact_digest':parent_art['candidate_digest'],'structural_valid':True,'semantic_consistency':1.0,
  'fit_baseline':m_can['direct'],'fit_candidate':m_parent['direct'],'heldout_baseline':m_can['sequential'],'heldout_candidate':m_parent['sequential'],
  'regression_pass':m_parent['base_regression']>=.98 and m_parent['traps']>=.95,'state_integrity':True,'rollback_available':True},
 {'skill_id':'ADMIT_MULTISCALE_V6','artifact_digest':v5['candidate_digest'],'structural_valid':True,'semantic_consistency':1.0,
  'fit_baseline':m_can['direct'],'fit_candidate':m_exp['direct'],'heldout_baseline':m_can['sequential'],'heldout_candidate':m_exp['sequential'],
  'regression_pass':m_exp['base_regression']>=.98 and m_exp['traps']>=.95 and m_exp['wrapped']>=.98,'state_integrity':True,'rollback_available':True}
]
if DB.exists():DB.unlink()
k=UnifiedYADOKernelV30RC8ExternalCognitive(db_path=str(DB))
try:
    selection=k.select_evolution_skills(skills,max_skills=1,min_semantic_consistency=.95,min_fit_gain=.005,max_heldout_drop=0.0,min_heldout_gain=.01)
finally:
    try:k.close()
    except Exception:pass
    try:
        if DB.exists():DB.unlink()
    except Exception:pass
selected=(selection.get('selected_skill_ids') or [None])[0]

# Second untouched post-selection fresh family.
domains2=['maritime clearance','protein pipeline','insurance settlement','warehouse robotics','identity recovery','vaccine release','orbital maintenance','environmental permit']
direct2=[]
for gi,label in enumerate([CAP_CONJ,CAP_REL,CAP_BUD,CAP_RES]):
    for i in range(18):
        direct2.append((f"Post6 {50000+gi*100+i}. "+templates[label][(i+2*gi+1)%4].format(d=domains2[(i*3+gi)%len(domains2)]),label))
traps2=[
 ("Quota, owner and external guide appear in transport metadata; the enclosed release still requires every compulsory safeguard.",CAP_CONJ),
 ("All gates are green and documentation exists, but the enclosed authorization depends on identity and membership relations.",CAP_REL),
 ("Owner and standard are known; the enclosed task is to choose a next experiment under finite resources.",CAP_BUD),
 ("Budget and roles are known; the enclosed task needs a missing current fact from an external authority.",CAP_RES),
]*10
def wrap_d(text,i,layer):
    m=(i*17+layer)%11
    if m==0:return f"<post6 n='{i%293}' d='{layer}'>{text}</post6>"
    if m==1:return f"BEGIN-P6 {i%307} {neutral[i%3]} {text} END-P6"
    if m==2:return f"[p6:{layer}:{i%311}] owner quota external team rollback {text} [/p6]"
    if m==3:return f"Carrier P6 header. {text}. Carrier P6 footer."
    if m==4:return f"{{p6={i%313};d={layer}}} {text} {{/p6}}"
    if m==5:return f"TRACE-P6 {text.upper() if i%2==0 else text.lower()} END"
    if m==6:return f"((P6 {layer})) {neutral[(i+1)%3]} [[{text}]] ((/P6))"
    if m==7:return f"Audit P6 nonce={i%317}. {re.sub(r'\s+',' ',text)} complete."
    if m==8:return f"metadata all conditions relation budget source. PAYLOAD {text}. END."
    if m==9:return f"{neutral[i%3]} {text} {neutral[(i+2)%3]}"
    return f"Administrative P6 {i%331}. {text}. Done."

pool2=direct2+traps2
wrapped2=[(wrap_d(x,i,0),y) for i,(x,y) in enumerate(pool2)]
rng2=random.Random(2026090709)
seq2=[]
for i in range(4000):
    x,y=pool2[(i*67+rng2.randrange(len(pool2)))%len(pool2)]
    z=wrap_d(x,i,0)
    for layer in range(1,1+(i%11)):z=wrap_d(z,i+37019*layer,layer)
    seq2.append((z,y))
post={'direct':acc(direct2,expanded.predict_capability),'traps':acc(traps2,expanded.predict_capability),
      'wrapped':acc(wrapped2,expanded.predict_capability),'sequential':acc(seq2,expanded.predict_capability)}

checks={
 'v5_shadow_pass_consumed':True,'candidate_fixed_by_digest':v5['candidate_digest']=='55bd61069b501dc09ab089f96ad139e70b11895f441258b14512f24e72950697',
 'runtime_equivalent_to_v5_reference':runtime_equivalence,'native_gate_selects_multiscale':selected=='ADMIT_MULTISCALE_V6',
 'admission_direct_ge_0_98':m_exp['direct']>=.98,'admission_traps_ge_0_95':m_exp['traps']>=.95,'admission_wrapped_ge_0_98':m_exp['wrapped']>=.98,
 'admission_sequential_ge_0_98':m_exp['sequential']>=.98,'base_regression_ge_0_98':m_exp['base_regression']>=.98,
 'sequential_gain_over_parent_ge_0_01':m_exp['sequential']-m_parent['sequential']>=.01,
 'post_direct_ge_0_98':post['direct']>=.98,'post_traps_ge_0_95':post['traps']>=.95,'post_wrapped_ge_0_98':post['wrapped']>=.98,
 'post_sequential_ge_0_98':post['sequential']>=.98,'post_selection_fresh_not_used_by_gate':True,
 'canonical_mutation':False,'g3_not_started':True,
}
positive=[k for k in checks if k!='canonical_mutation']
passed=all(checks[k] is True for k in positive) and checks['canonical_mutation'] is False
status='PASS_READY_G2_NATIVE_RAW_REPRESENTATION_MODEL_FAMILY_EXPANSION_ADMISSION_V6' if passed else 'WITHHOLD_G2_NATIVE_RAW_REPRESENTATION_MODEL_FAMILY_EXPANSION_ADMISSION_V6'
next_cap='NATIVE_RAW_REPRESENTATION_MODEL_FAMILY_CANONICAL_BINDING_V7' if passed else 'NATIVE_RAW_REPRESENTATION_SEGMENTATION_PRIMITIVE_GENESIS_V6'

fresh={'schema':'yado.g2.native_raw_representation_model_family_expansion_admission_v6.fresh.v1','candidate_digest':v5['candidate_digest'],
 'admission_metrics':{'canonical_v4':m_can,'parent_char45':m_parent,'multiscale':m_exp},'post_selection_fresh':post,
 'admission_counts':{'direct':len(direct),'traps':len(traps),'wrapped':len(wrapped),'sequential':len(seq)},
 'post_counts':{'direct':len(direct2),'traps':len(traps2),'wrapped':len(wrapped2),'sequential':len(seq2)}}
fresh['dataset_digest']=digest(fresh);write(FRESH,fresh)
report={'schema':'yado.g2.native_raw_representation_model_family_expansion_admission.v6','status':status,
 'parent_v5_receipt':v5['receipt_sha256'],'candidate_digest':v5['candidate_digest'],'selected_spec':v5['selected_spec'],
 'runtime_component_id':RawTaskRepresentationMultiscaleRuntimeV6.COMPONENT_ID,'runtime_equivalence':runtime_equivalence,
 'native_selection':selection,'admission_metrics':fresh['admission_metrics'],'post_selection_fresh':post,'checks':checks,
 'fresh_dataset_digest':fresh['dataset_digest'],'canonical_mutation':False,'promotion_applied':False,'g3_genesis_performed':False,
 'next_required_capability':next_cap,
 'semantic_boundary':'V6 FREEZES THE V5 MULTISCALE CANDIDATE, FIRST PROVES A REUSABLE RUNTIME IS OUTPUT-EQUIVALENT TO THE V5 REFERENCE IMPLEMENTATION, THEN COMPARES CANONICAL V4, THE CHAR45 PARENT AND MULTISCALE CHILD ON A NEW INDEPENDENT ADMISSION CORPUS. NATIVE YADO SELECTS BEFORE A SECOND UNTOUCHED POST-SELECTION FRESH CHALLENGE. NO TRAINING OR CANDIDATE CHANGE OCCURS.'
}
report['receipt_sha256']=digest(report);write(OUT,report)
print(json.dumps(report,indent=2,sort_keys=True))
if not passed:raise SystemExit(2)
