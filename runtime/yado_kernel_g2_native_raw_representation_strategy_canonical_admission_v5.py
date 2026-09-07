from __future__ import annotations
from pathlib import Path
from collections import Counter
import hashlib,json,random,re,sys

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
PKG=ROOT/'yado_rc8_v36'
sys.path[:0]=[str(ROOT),str(PKG)]

from yado_core_v3_0_rc8_external_cognitive import UnifiedYADOKernelV30RC8ExternalCognitive
from yado_raw_task_representation_candidate_v2 import RawTaskRepresentationSpecV2
from yado_raw_task_representation_robustness_v4 import RobustRawTaskRepresentationRuntimeV4
from yado_evolution_ledger_v2 import validate_ledger_v2

REVAL=REPO/'architecture/yado-kernel-g2-native-raw-representation-strategy-genesis-repair-v4-verdict-revalidation-v1.json'
CAND=REPO/'candidates/kernel-self-generated/raw-task-representation-strategy-model-v4.json'
V3=REPO/'canonical/yado-raw-task-representation-v3.json'
V4=REPO/'canonical/yado-raw-task-representation-v4.json'
BASE=REPO/'receipts/yado-g2-real-world-transfer-benchmark-v1-run-33363995201.json'
LEDGER=REPO/'architecture/evolution-ledger.json'
OUT=REPO/'architecture/yado-kernel-g2-native-raw-representation-strategy-canonical-admission-v5.json'
FRESH=REPO/'resources/yado-raw-task-representation-v6-canonical-admission-fresh-v1.json'
DB=ROOT/'yado_raw_rep_admission_v5.sqlite'

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

reval,cand,v3,v4,base,ledger=map(load,[REVAL,CAND,V3,V4,BASE,LEDGER])
validate_ledger_v2(ledger)
if ledger.get('open_deficits')!=[FRONT]:raise RuntimeError('UNEXPECTED_CANONICAL_FRONTIER')
if reval.get('status')!='PASS_SHADOW_G2_NATIVE_RAW_REPRESENTATION_STRATEGY_GENESIS_REPAIR_V4_REVALIDATED':raise RuntimeError('V4_REVALIDATED_PASS_REQUIRED')
if reval.get('receipt_sha256')!='2d4866f26c9601794e0815f3d48bfbce6abd2a42eb45b219da59cb7b7721404e':raise RuntimeError('REVALIDATION_RECEIPT_DRIFT')
if cand.get('candidate_digest')!='03bf3624f16ddca433f02ce4f956258e2dee72046f65571fa4b226c65183ef6d':raise RuntimeError('CANDIDATE_DRIFT')
if cand.get('model_digest')!='ec9ab1ecc29d45ee2d7c0d616e7e23fcf28d235348a0f5a270dffdeb4e0f7505':raise RuntimeError('MODEL_DRIFT')

m=cand['model'];candidate=RawTaskRepresentationSpecV2(m['family'],list(m['labels']),m['payload'])
parent=RobustRawTaskRepresentationRuntimeV4(v3,v4['selected_mode'])
cp=candidate.predict;pp=parent.predict_capability

domains=['medical release','spacecraft command','warehouse dispatch','financial settlement','research dataset','legal filing','industrial control','identity service','energy grid','package deployment','clinical trial','mission workflow']
conj=[
 "For {d}, authorize only when provenance, integrity, and rollback readiness all pass together; ownership metadata is incidental.",
 "In {d}, one failed mandatory safeguard blocks activation even if quota and group information are present.",
 "Decide whether every compulsory acceptance condition for {d} is simultaneously true; no search planning is requested.",
 "For {d}, proceed iff authorization validation, integrity validation, and recovery readiness all succeed."
]
rel=[
 "For {d}, permission depends on requester-owner identity or membership in the authorized group; remaining budget is irrelevant.",
 "In {d}, infer access from principal, owner, tenant, and role relations rather than independent readiness gates.",
 "For {d}, determine whether the claimant is the same principal as the owner or belongs to the approved cohort.",
 "In {d}, entity equality and membership edges decide authorization; external documentation is not missing."
]
bud=[
 "For {d}, choose the next diagnostic under a finite compute allowance using cost and expected information gain; ownership is settled.",
 "In {d}, allocate remaining credits among verification stages so confidence rises without exceeding quota.",
 "For {d}, schedule the least-cost next experiment under budget, latency, and expected evidence gain constraints.",
 "In {d}, select an affordable sequence of deeper checks; the governing facts and identities are already known."
]
res=[
 "For {d}, local state lacks the decisive fact, so retrieve a current authoritative public reference rather than run another local test.",
 "In {d}, identity and budget are known but the missing requirement must come from current external documentation.",
 "For {d}, obtain the unresolved specification from a trustworthy outside source because local evidence cannot establish it.",
 "In {d}, the information gap is external to the system; fetch authoritative evidence instead of scheduling another diagnostic."
]
groups=[(conj,CAP_CONJ),(rel,CAP_REL),(bud,CAP_BUD),(res,CAP_RES)]
direct=[]
for gi,(temps,label) in enumerate(groups):
    for i in range(36):
        t=temps[(i*3+gi)%len(temps)].format(d=domains[(i*5+gi)%len(domains)])
        direct.append((t+f" Reference token {1000+gi*100+i}.",label))

traps=[
 ("Ownership, budget and public documentation are all mentioned, but activation still requires every mandatory integrity and recovery gate to pass.",CAP_CONJ),
 ("All readiness checks pass and a quota is displayed, but permission is determined by requester-owner identity and authorized-group membership.",CAP_REL),
 ("An external stage name and owner field appear in the record, but the task is to choose the next test under remaining compute budget.",CAP_BUD),
 ("Budget and membership data are available, but the missing governing fact can only be obtained from current public documentation.",CAP_RES),
 ("A manual is attached and an owner is named; nevertheless the decision is simply whether every compulsory safeguard succeeds.",CAP_CONJ),
 ("The word rollback appears in metadata, yet access changes only with principal equality or group membership relations.",CAP_REL),
 ("All mandatory gates are already true; now allocate finite credits among deeper diagnostic stages.",CAP_BUD),
 ("A quota remains and all actors are known, but no local experiment can reveal the missing standard, so retrieve it externally.",CAP_RES),
]*6

def wrap_a(text,i,layer):
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

wrapped=[(wrap_a(x,i,0),y) for i,(x,y) in enumerate(direct+traps)]
rng=random.Random(2026090705)
seq=[]
pool=direct+traps
for i in range(5000):
    x,y=pool[(i*47+rng.randrange(len(pool)))%len(pool)]
    z=wrap_a(x,i,0)
    for layer in range(1,1+(i%6)):
        z=wrap_a(z,i+19001*layer,layer)
    seq.append((z,y))

base_rows=[(r['raw_text'],r['expected']) for r in base['raw_unstructured']['rows']]
metrics={
 'parent_direct':acc(direct,pp),'candidate_direct':acc(direct,cp),
 'parent_traps':acc(traps,pp),'candidate_traps':acc(traps,cp),
 'parent_wrapped':acc(wrapped,pp),'candidate_wrapped':acc(wrapped,cp),
 'parent_sequential':acc(seq,pp),'candidate_sequential':acc(seq,cp),
 'parent_base_regression':acc(base_rows,pp),'candidate_base_regression':acc(base_rows,cp),
}

skills=[
 {'skill_id':'KEEP_CANONICAL_RAW_V4','artifact_digest':v4['component_digest'],'structural_valid':True,'semantic_consistency':1.0,
  'fit_baseline':metrics['parent_direct'],'fit_candidate':metrics['parent_direct'],
  'heldout_baseline':metrics['parent_sequential'],'heldout_candidate':metrics['parent_sequential'],
  'regression_pass':True,'state_integrity':True,'rollback_available':True},
 {'skill_id':'ADMIT_RAW_MODEL_V6','artifact_digest':cand['candidate_digest'],'structural_valid':True,'semantic_consistency':1.0,
  'fit_baseline':metrics['parent_direct'],'fit_candidate':metrics['candidate_direct'],
  'heldout_baseline':metrics['parent_sequential'],'heldout_candidate':metrics['candidate_sequential'],
  'regression_pass':metrics['candidate_base_regression']>=.98 and metrics['candidate_traps']>=.95 and metrics['candidate_wrapped']>=.97,
  'state_integrity':True,'rollback_available':True}
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

# Second independent post-selection fresh challenge.
domains2=['aviation procedure','genomics pipeline','tax compliance','robotics cell','network incident','pharmaceutical batch','satellite telemetry','supply-chain approval']
direct2=[]
for gi,(temps,label) in enumerate(groups):
    for i in range(16):
        t=temps[(i+2*gi+1)%len(temps)].format(d=domains2[(i*3+gi)%len(domains2)])
        direct2.append((f"Independent review {20000+gi*100+i}. "+t,label))
traps2=[
 ("The note lists a public source and a team, yet release is allowed only if all compulsory safety checks pass.",CAP_CONJ),
 ("Integrity and rollback are green, but access still follows owner identity and authorized membership.",CAP_REL),
 ("A reference exists and ownership is known; choose the next verification stage under the remaining resource ceiling.",CAP_BUD),
 ("All local checks and identities are known, but the absent specification requires a current outside authority.",CAP_RES),
]*8

def wrap_b(text,i,layer):
    m=(i*5+layer)%9
    if m==0:return f"<fresh-b id='{i%127}' level='{layer}'>{text}</fresh-b>"
    if m==1:return f"BEGIN-B/{i%131}/{layer}\n{text}\nEND-B"
    if m==2:return f"[meta-b:{i%137}:{layer}] {text} [/meta-b]"
    if m==3:return f"Envelope-B {i%139}. payload-start {text} payload-end."
    if m==4:return f"{{context-b={i%149};depth={layer}}} {text} {{/context-b}}"
    if m==5:return f"TRACE-B {i%151}: {text.lower() if i%2 else text.upper()} :END"
    if m==6:return f"((B{layer})) [[{i%157}]] {text} [[/B]]"
    if m==7:return f"Audit-B nonce {i%163}. {re.sub(r'\s+',' ',text)} Complete."
    return f"Header-B {i%167}; {text}; Footer-B."

fresh2=direct2+traps2
wrapped2=[(wrap_b(x,i,0),y) for i,(x,y) in enumerate(fresh2)]
rng2=random.Random(2026090706)
seq2=[]
for i in range(3000):
    x,y=fresh2[(i*53+rng2.randrange(len(fresh2)))%len(fresh2)]
    z=wrap_b(x,i,0)
    for layer in range(1,1+(i%7)):
        z=wrap_b(z,i+23003*layer,layer)
    seq2.append((z,y))
post={
 'candidate_direct':acc(direct2,cp),'candidate_traps':acc(traps2,cp),
 'candidate_wrapped':acc(wrapped2,cp),'candidate_sequential':acc(seq2,cp),
 'parent_direct':acc(direct2,pp),'parent_wrapped':acc(wrapped2,pp),'parent_sequential':acc(seq2,pp)
}

checks={
 'candidate_fixed_by_digest':cand.get('candidate_digest')=='03bf3624f16ddca433f02ce4f956258e2dee72046f65571fa4b226c65183ef6d',
 'model_fixed_by_digest':cand.get('model_digest')=='ec9ab1ecc29d45ee2d7c0d616e7e23fcf28d235348a0f5a270dffdeb4e0f7505',
 'revalidated_shadow_pass_consumed':True,
 'native_gate_selects_candidate':selected=='ADMIT_RAW_MODEL_V6',
 'admission_direct_ge_0_97':metrics['candidate_direct']>=.97,
 'admission_traps_ge_0_95':metrics['candidate_traps']>=.95,
 'admission_wrapped_ge_0_97':metrics['candidate_wrapped']>=.97,
 'admission_sequential_ge_0_98':metrics['candidate_sequential']>=.98,
 'base_regression_ge_0_98':metrics['candidate_base_regression']>=.98,
 'post_direct_ge_0_97':post['candidate_direct']>=.97,
 'post_traps_ge_0_95':post['candidate_traps']>=.95,
 'post_wrapped_ge_0_97':post['candidate_wrapped']>=.97,
 'post_sequential_ge_0_98':post['candidate_sequential']>=.98,
 'post_selection_fresh_not_used_by_gate':True,
 'rollback_v4_available':v4.get('canonical_active') is True,
 'canonical_mutation':False,
 'g3_not_started':True,
}
passed=all(v is True for k,v in checks.items() if k!='canonical_mutation') and checks['canonical_mutation'] is False
status='PASS_READY_G2_NATIVE_RAW_REPRESENTATION_STRATEGY_CANONICAL_ADMISSION_V5' if passed else 'WITHHOLD_G2_NATIVE_RAW_REPRESENTATION_STRATEGY_CANONICAL_ADMISSION_V5'
next_cap='NATIVE_RAW_REPRESENTATION_STRATEGY_CANONICAL_BINDING_V6' if passed else 'NATIVE_RAW_REPRESENTATION_MODEL_FAMILY_EXPANSION_V5'

fresh_doc={'schema':'yado.g2.raw_representation_v6.canonical_admission_fresh.v1','candidate_digest':cand['candidate_digest'],
 'model_digest':cand['model_digest'],'selected_skill_id':selected,'admission_metrics':metrics,'post_selection_fresh_metrics':post,
 'direct_count':len(direct),'trap_count':len(traps),'wrapped_count':len(wrapped),'sequential_count':len(seq),
 'post_direct_count':len(direct2),'post_trap_count':len(traps2),'post_wrapped_count':len(wrapped2),'post_sequential_count':len(seq2)}
fresh_doc['dataset_digest']=digest(fresh_doc);write(FRESH,fresh_doc)
report={'schema':'yado.g2.native_raw_representation_strategy_canonical_admission.v5','status':status,
 'source_revalidation_receipt':reval['receipt_sha256'],'candidate_digest':cand['candidate_digest'],'model_digest':cand['model_digest'],
 'selected_family':cand['selected_family'],'native_selection':selection,'admission_metrics':metrics,'post_selection_fresh_metrics':post,
 'checks':checks,'fresh_dataset_digest':fresh_doc['dataset_digest'],'canonical_mutation':False,'promotion_applied':False,
 'g3_genesis_performed':False,'next_required_capability':next_cap,
 'semantic_boundary':'INDEPENDENT CANONICAL-ADMISSION READINESS GATE FOR A FROZEN YADO-SELECTED REPRESENTATION MODEL. THIS STAGE DOES NOT MUTATE CANONICAL G2. THE CANDIDATE IS COMPARED AGAINST CANONICAL V4 ON NEW CONTRASTIVE DIRECT/WRAPPED/DEEP-SEQUENTIAL CASES, THEN A SECOND POST-SELECTION FRESH CHALLENGE. PASS ONLY AUTHORIZES A SEPARATE TRANSACTIONAL BINDING STAGE.'}
report['receipt_sha256']=digest(report);write(OUT,report)
print(json.dumps(report,indent=2,sort_keys=True))
if not passed:raise SystemExit(2)
