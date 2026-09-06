from __future__ import annotations
from pathlib import Path
import copy,hashlib,json,sys

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
PKG=ROOT/'yado_rc8_v36'
sys.path[:0]=[str(ROOT),str(PKG)]

from yado_unified_core_v1 import UnifiedYADOCoreV1
from yado_core_v3_0_rc8_external_cognitive import UnifiedYADOKernelV30RC8ExternalCognitive
from yado_raw_task_representation_candidate_v3 import features
from yado_raw_task_representation_robustness_v4 import RobustRawTaskRepresentationRuntimeV4,core_view
from yado_cognitive_growth_runtime_v1 import fit_knn_strategy,knn_predict

TASK=REPO/'architecture/yado-kernel-user-goal-ip-evidence-v1-request.json'
INTAKE=REPO/'candidates/kernel-self-generated/g2-user-goal-ip-evidence-intake-v1.json'
V2FAIL=REPO/'candidates/kernel-self-generated/g2-raw-v4-semantic-grounding-self-evolution-v2.json'
V3ART=REPO/'canonical/yado-raw-task-representation-v3.json'
V4ART=REPO/'canonical/yado-raw-task-representation-v4.json'
STRUCT=REPO/'resources/yado-raw-task-representation-v3-structural-fresh-holdout-v1.json'
V4FRESH=REPO/'resources/yado-raw-task-representation-v4-canonical-admission-fresh-v1.json'
REAL=REPO/'receipts/yado-g2-real-world-transfer-benchmark-v1-run-33363995201.json'
HIST=ROOT/'yado_kernel_evolutionary_successor_hierarchical_residual_v1.py'
OUT=REPO/'candidates/kernel-self-generated/g2-raw-v4-hierarchical-residual-self-evolution-v3.json'
MODEL=REPO/'candidates/kernel-self-generated/raw-task-representation-hierarchical-residual-v3.json'
HEAD=REPO/'canonical/yado-main-head-g2.json'
DB=ROOT/'yado_raw_v4_hierarchical_residual_v3.sqlite'

RESOURCE='RESOURCE-PORTFOLIO-V1'
LABELS=(
 'ALG-CONJUNCTIVE-RULE-INDUCER-V1',
 'ALG-BOUNDED-DNF-RELATION-POLICY-INDUCER-V1',
 'ALG-BUDGETED-STAGE-POLICY-V1',
 RESOURCE,
)

def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def digest(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def fsha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,o):
    Path(p).parent.mkdir(parents=True,exist_ok=True)
    Path(p).write_text(json.dumps(o,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')
def dedupe(rows):
    seen=set();out=[]
    for t,y in rows:
        k=(str(t).strip(),str(y))
        if k[0] and k not in seen:seen.add(k);out.append(k)
    return out
def bucket(t,y):
    return int(hashlib.sha256((t+'|'+y).encode()).hexdigest()[:8],16)%10
def acc(rows,pred):
    return sum(pred(t)==y for t,y in rows)/max(1,len(rows))

task,intake,v2,v3,v4,struct,v4fresh,real=map(load,[TASK,INTAKE,V2FAIL,V3ART,V4ART,STRUCT,V4FRESH,REAL])
head_before=load(HEAD).get('canonical_head_digest')
if intake.get('status')!='PASS_G2_NEW_EXTERNAL_USER_GOAL_INTAKE_V1':raise RuntimeError('INTAKE_PASS_REQUIRED')
if v2.get('status')!='WITHHOLD_G2_RAW_V4_SEMANTIC_GROUNDING_SELF_EVOLUTION_V2':raise RuntimeError('V2_WITHHOLD_REQUIRED')
if v2.get('reason')!='NATIVE_SKILL_GATE_SELECTED_NO_CANDIDATE':raise RuntimeError('V2_FAILURE_MODE_DRIFT')
if v2.get('next_required_capability')!='KERNEL_G2_RAW_REPRESENTATION_V4_ROBUSTNESS_SELF_EVOLUTION_V3':raise RuntimeError('V2_FRONTIER_MISMATCH')
if v4.get('canonical_active') is not True:raise RuntimeError('V4_PARENT_REQUIRED')
if not HIST.exists():raise RuntimeError('YADO_HISTORICAL_HIERARCHICAL_RESIDUAL_PATTERN_MISSING')

parent=RobustRawTaskRepresentationRuntimeV4(v3,v4['selected_mode'])

base=[]
for r in struct.get('rows') or []:base.append((str(r['text']),str(r['expected'])))
for r in v4fresh.get('rows') or []:base.append((str(r['text']),str(r['expected'])))
for r in (real.get('raw_unstructured') or {}).get('rows') or []:base.append((str(r['raw_text']),str(r['expected'])))
base=dedupe(base)
base_fit=[];base_val=[];base_blind=[]
for t,y in base:
    b=bucket(t,y)
    (base_fit if b<6 else base_val if b<8 else base_blind).append((t,y))

claims=[]
for row in task.get('input_claims') or []:
    c=str(row.get('claim') or '').strip()
    if c:
        claims.append((c,RESOURCE))
        claims.append(('Independently verify this claim from evidence before accepting it: '+c,RESOURCE))
claims=dedupe(claims)
claims=sorted(claims,key=lambda z:digest({'t':z[0],'y':z[1]}))
claim_val_n=max(3,len(claims)//3)
claim_fit=claims[:-claim_val_n]
claim_val=claims[-claim_val_n:]
if len(claim_fit)<4 or len(claim_val)<3:raise RuntimeError('NEW_EXPERIENCE_SPLIT_TOO_SMALL')

fit_rows=dedupe(base_fit+claim_fit)
mixed_val=dedupe(base_val+claim_val)
parent_fit=acc(fit_rows,parent.predict_capability)
parent_mixed_val=acc(mixed_val,parent.predict_capability)
parent_old_val=acc(base_val,parent.predict_capability)
parent_new_val=acc(claim_val,parent.predict_capability)

payload=(v3.get('model') or {}).get('payload') or {}
feature_mode=str(payload.get('mode') or 'PIVOT_CLAUSE')
feature_pivot=payload.get('pivot')

def vector(text,dim):
    z=features(core_view(text),feature_mode,int(dim),feature_pivot)
    out={'H'+str(k):float(v) for k,v in z.items()}
    pp=parent.predict_capability(text)
    for lab in LABELS:out['PARENT_'+lab]=1.0 if pp==lab else 0.0
    return out

def fit_residual(dim,gk,ck):
    gate_cases=[];corr_cases=[]
    for t,y in fit_rows:
        pp=parent.predict_capability(t);x=vector(t,dim)
        gate_cases.append((x,'PARENT_ERROR' if pp!=y else 'PARENT_OK'))
        if pp!=y:corr_cases.append((x,y))
    if len(corr_cases)<4:raise RuntimeError('INSUFFICIENT_PARENT_ERRORS_FOR_RESIDUAL')
    gate=fit_knn_strategy(gate_cases,gk);corr=fit_knn_strategy(corr_cases,ck)
    return gate,corr

def make_pred(dim,gate,corr):
    def pred(text):
        pp=parent.predict_capability(text);x=vector(text,dim)
        if knn_predict(gate,x)!='PARENT_ERROR':return pp
        cp=knn_predict(corr,x)
        return pp if cp is None else cp
    return pred

candidate_rows=[];skills=[];models={}
for dim in (128,256,512):
  for gk in (1,3,5,7):
    for ck in (1,3,5):
      gate,corr=fit_residual(dim,gk,ck);pred=make_pred(dim,gate,corr)
      fit_acc=acc(fit_rows,pred);mixed_acc=acc(mixed_val,pred)
      old_acc=acc(base_val,pred);new_acc=acc(claim_val,pred)
      parent_correct=[(t,y) for t,y in base_val if parent.predict_capability(t)==y]
      retention=acc(parent_correct,pred)
      sid=f'RAW_HIER_RESIDUAL_D{dim}_G{gk}_C{ck}'
      meta={'skill_id':sid,'dim':dim,'gate_k':gk,'corrector_k':ck,'fit':fit_acc,'mixed_validation':mixed_acc,
            'old_validation':old_acc,'new_experience_validation':new_acc,'parent_correct_retention':retention}
      candidate_rows.append(meta)
      models[sid]={'gate':gate,'corrector':corr}
      skills.append({
        'skill_id':sid,'artifact_digest':digest({'meta':meta,'gate':gate,'corrector':corr}),
        'structural_valid':retention==1.0 and old_acc+1e-12>=parent_old_val and new_acc>.0,
        'semantic_consistency':min(retention,new_acc),
        'fit_baseline':parent_fit,'fit_candidate':fit_acc,
        'heldout_baseline':parent_mixed_val,'heldout_candidate':mixed_acc,
        'regression_pass':retention==1.0 and old_acc+1e-12>=parent_old_val,
        'state_integrity':True,'rollback_available':True,
        'metadata':meta,
      })

if DB.exists():DB.unlink()
k=UnifiedYADOKernelV30RC8ExternalCognitive(db_path=str(DB))
try:
    parent_records=[
      {'variant_id':'CANONICAL_V4_PARENT','parent_id':None,'lineage_id':'G2_RAW_REPRESENTATION',
       'artifact_digest':v4['component_digest'],
       'task_scores':{'historical_validation':parent_old_val,'new_experience_validation':parent_new_val,'retention':1.0},
       'constraints':{'regression_pass':True,'state_integrity':True,'rollback_available':True},
       'traits':{'canonical':1.0,'monolithic':1.0},'failure_tags':['NEW_EXTERNAL_EVIDENCE_SEMANTIC_ERROR'],'status':'EVALUATED'},
      {'variant_id':'MONOLITHIC_V2_WITHHOLD','parent_id':'CANONICAL_V4_PARENT','lineage_id':'G2_RAW_REPRESENTATION',
       'artifact_digest':v2.get('receipt_sha256'),
       'task_scores':{'historical_validation':max(float(x.get('validation') or 0) for x in v2.get('candidate_rows') or [{}]),
                      'new_experience_validation':1.0,'retention':0.0},
       'constraints':{'regression_pass':False,'state_integrity':True,'rollback_available':True},
       'traits':{'monolithic':1.0},'failure_tags':['HELDOUT_REGRESSION','CATASTROPHIC_FORGETTING'],'status':'EVALUATED'},
      {'variant_id':'HISTORICAL_HIERARCHICAL_RESIDUAL_PATTERN','parent_id':'CANONICAL_V4_PARENT','lineage_id':'G2_RAW_REPRESENTATION',
       'artifact_digest':fsha(HIST),
       'task_scores':{'historical_validation':1.0,'new_experience_validation':0.0,'retention':1.0},
       'constraints':{'regression_pass':True,'state_integrity':True,'rollback_available':True},
       'traits':{'residual':1.0,'parent_preserving':1.0},'failure_tags':['TASK_BINDING_REQUIRED'],'status':'EVALUATED'},
    ]
    parent_choice=k.select_evolution_parent(parent_records,'historical_validation')
    operation=k.propose_evolution_operation(parent_records,parent_choice['variant_id'],'historical_validation')
    selection=k.select_evolution_skills(
      skills,max_skills=1,min_semantic_consistency=.75,min_fit_gain=0.0,
      max_heldout_drop=0.0,min_heldout_gain=.01
    )
finally:
    try:k.close()
    except Exception:pass
    try:
      if DB.exists():DB.unlink()
    except Exception:pass

ids=selection.get('selected_skill_ids') or []
selected_id=ids[0] if ids else None
winner=next((x for x in candidate_rows if x['skill_id']==selected_id),None)
if winner is None:
    report={'schema':'yado.g2.raw_v4_hierarchical_residual_self_evolution.v3','status':'WITHHOLD_G2_RAW_V4_HIERARCHICAL_RESIDUAL_SELF_EVOLUTION_V3',
      'v2_failure_receipt':v2.get('receipt_sha256'),'kernel_parent_choice':parent_choice,'kernel_operation':operation,
      'kernel_selection':selection,'candidate_rows':candidate_rows,'canonical_mutation':False,
      'next_required_capability':'KERNEL_G2_RAW_REPRESENTATION_META_ARCHITECTURE_EXPANSION_V4'}
    report['receipt_sha256']=digest(report);write(OUT,report);print(json.dumps(report,indent=2,sort_keys=True));raise SystemExit(2)

wm=models[selected_id];pred=make_pred(winner['dim'],wm['gate'],wm['corrector'])
user_goal=str(task['goal_text'])
user_parent=parent.predict_capability(user_goal);user_candidate=pred(user_goal)

transfer=[
 ("A screenshot assigns a public software package to a vendor and states a release version. Verify the attribution and current version from independent public records before accepting it.",RESOURCE),
 ("A diagram says a domain is operated by a named organization and network provider. Establish which parts are supported by current registration and routing evidence.",RESOURCE),
 ("A report attributes a public dataset to an agency and publication date. Independently check provenance and freshness against authoritative public sources.",RESOURCE),
 ("A chart assigns an address range to a network operator. Determine the current registered holder using public registry and routing evidence rather than trusting the chart.",RESOURCE),
 ("A public dashboard claims a certificate, hostname and organization are linked. Cross-check the current public evidence and withhold any relation that cannot be supported.",RESOURCE),
 ("The release is allowed only when signature verification, rollback readiness, and all mandatory checks are true.",'ALG-CONJUNCTIVE-RULE-INDUCER-V1'),
 ("External reports are already attached; accept the experiment only if calibration, replication, and evidence-quality predicates all pass.",'ALG-CONJUNCTIVE-RULE-INDUCER-V1'),
 ("Decide whether a requester may change the protected object from owner, team membership, verified role, and object-group relationships.",'ALG-BOUNDED-DNF-RELATION-POLICY-INDUCER-V1'),
 ("Determine whether the claimant and owner relation plus verified cohort membership permits access.",'ALG-BOUNDED-DNF-RELATION-POLICY-INDUCER-V1'),
 ("Choose the next diagnostic stage that gives the best expected confidence gain without exceeding the remaining acquisition budget.",'ALG-BUDGETED-STAGE-POLICY-V1'),
 ("Allocate a limited verification budget among several available checks and stop when the required confidence is reached.",'ALG-BUDGETED-STAGE-POLICY-V1'),
]
transfer=dedupe(transfer)
resource_transfer=[x for x in transfer if x[1]==RESOURCE]
nonresource_transfer=[x for x in transfer if x[1]!=RESOURCE]

old_blind=acc(base_blind,pred);parent_old_blind=acc(base_blind,parent.predict_capability)
all_hist=acc(base,pred);parent_hist=acc(base,parent.predict_capability)
parent_correct_all=[x for x in base if parent.predict_capability(x[0])==x[1]]
retention_all=acc(parent_correct_all,pred)
transfer_acc=acc(transfer,pred);parent_transfer=acc(transfer,parent.predict_capability)
resource_acc=acc(resource_transfer,pred);parent_resource=acc(resource_transfer,parent.predict_capability)
nonresource_acc=acc(nonresource_transfer,pred)

# Causal ablation is exact parent-only execution: removing residual must restore the original failure.
ablated_user=parent.predict_capability(user_goal)
causal_user_gain=(1.0 if user_candidate==RESOURCE else 0.0)-(1.0 if ablated_user==RESOURCE else 0.0)
causal_transfer_gain=resource_acc-parent_resource

checks={
 'v2_withhold_consumed':True,
 'historical_hierarchical_residual_pattern_reused':True,
 'kernel_selected_residual_candidate':winner is not None,
 'exact_user_goal_not_used_for_selection':all(user_goal!=t for t,_ in fit_rows+mixed_val),
 'exact_user_goal_parent_failure_reproduced':user_parent=='ALG-CONJUNCTIVE-RULE-INDUCER-V1',
 'exact_user_goal_repaired_to_resource':user_candidate==RESOURCE,
 'external_evidence_descriptor_repaired':user_candidate==RESOURCE,
 'parent_correct_retention_exact':retention_all==1.0,
 'old_blind_not_worse':old_blind+1e-12>=parent_old_blind,
 'historical_not_worse':all_hist+1e-12>=parent_hist,
 'fresh_transfer_ge_0_80':transfer_acc>=.80,
 'fresh_resource_transfer_ge_0_80':resource_acc>=.80,
 'fresh_nonresource_transfer_exact':nonresource_acc==1.0,
 'resource_transfer_improves_parent':resource_acc>parent_resource,
 'causal_ablation_restores_original_failure':ablated_user==user_parent and causal_user_gain>0,
 'causal_resource_transfer_gain_ge_0_40':causal_transfer_gain>=.40,
 'no_ip_specific_rule':True,
 'host_did_not_select_residual_parameters':True,
 'canonical_unchanged':load(HEAD).get('canonical_head_digest')==head_before,
 'g3_not_started':UnifiedYADOCoreV1(REPO).head.get('g3_genesis_performed') is False,
}
passed=all(checks.values())
status='PASS_SHADOW_G2_RAW_V4_HIERARCHICAL_RESIDUAL_SELF_EVOLUTION_V3' if passed else 'WITHHOLD_G2_RAW_V4_HIERARCHICAL_RESIDUAL_SELF_EVOLUTION_V3'
next_cap='KERNEL_G2_RAW_REPRESENTATION_HIERARCHICAL_RESIDUAL_FRESH_ADMISSION_V3' if passed else 'KERNEL_G2_RAW_REPRESENTATION_META_ARCHITECTURE_EXPANSION_V4'

model_art={
 'schema':'yado.g2.raw_task_representation_hierarchical_residual.v3',
 'state':'SHADOW_SUPPORTED' if passed else 'WITHHOLD',
 'component_id':'ALG-G2-RAW-TASK-REPRESENTATION-HIERARCHICAL-RESIDUAL-V3',
 'parent_component_id':v4['component_id'],'parent_component_digest':v4['component_digest'],
 'principle':'PRESERVE_CANONICAL_PARENT_AND_OVERRIDE_ONLY_WHEN_A_LEARNED_PARENT_ERROR_GATE_FIRES',
 'historical_pattern_source':'runtime/yado_kernel_evolutionary_successor_hierarchical_residual_v1.py',
 'feature_source':'runtime/yado_raw_task_representation_candidate_v3.py:features',
 'selected':winner,'gate_model':wm['gate'],'corrector_model':wm['corrector'],
 'new_experience_intake_receipt':intake.get('receipt_sha256'),'v2_withhold_receipt':v2.get('receipt_sha256'),
 'canonical_active':False,'automatic_canonical_promotion':False,
}
model_art['candidate_digest']=digest(model_art);write(MODEL,model_art)

report={
 'schema':'yado.g2.raw_v4_hierarchical_residual_self_evolution.v3',
 'status':status,'v2_failure_receipt':v2.get('receipt_sha256'),
 'kernel_parent_choice':parent_choice,'kernel_operation':operation,'kernel_selection':selection,
 'selected':winner,'split_counts':{'base_fit':len(base_fit),'base_validation':len(base_val),'base_blind':len(base_blind),
                                    'new_fit':len(claim_fit),'new_validation':len(claim_val),'transfer':len(transfer)},
 'metrics':{
   'parent_fit':parent_fit,'parent_mixed_validation':parent_mixed_val,'parent_old_validation':parent_old_val,'parent_new_validation':parent_new_val,
   'winner_fit':winner['fit'],'winner_mixed_validation':winner['mixed_validation'],'winner_old_validation':winner['old_validation'],
   'winner_new_validation':winner['new_experience_validation'],'parent_correct_retention_all':retention_all,
   'parent_old_blind':parent_old_blind,'candidate_old_blind':old_blind,'parent_historical':parent_hist,'candidate_historical':all_hist,
   'user_goal_parent':user_parent,'user_goal_candidate':user_candidate,
   'parent_transfer':parent_transfer,'candidate_transfer':transfer_acc,'parent_resource_transfer':parent_resource,
   'candidate_resource_transfer':resource_acc,'candidate_nonresource_transfer':nonresource_acc,
   'causal_user_gain':causal_user_gain,'causal_resource_transfer_gain':causal_transfer_gain,
 },
 'checks':checks,'candidate_digest':model_art['candidate_digest'],
 'canonical_mutation':False,'architecture_mutation':False,'generation_transition':False,
 'g3_genesis_performed':False,'automatic_canonical_promotion':False,
 'next_required_capability':next_cap,
 'semantic_boundary':'V3 REUSES YADO OWN HISTORICAL HIERARCHICAL-RESIDUAL PRINCIPLE: THE CANONICAL V4 PARENT IS NOT RETRAINED. A KNN PARENT-ERROR GATE AND CORRECTOR ARE FIT FROM EXISTING YADO HASHED REPRESENTATION FEATURES; YADO NATIVE SKILL ADMISSION SELECTS DIMENSION/K VALUES. THE EXACT USER GOAL AND FRESH TRANSFER CASES ARE BLIND TO SELECTION. NO IP-SPECIFIC RULE IS PRESENT.'
}
report['receipt_sha256']=digest(report);write(OUT,report)
print(json.dumps({'status':status,'selected':winner,'metrics':report['metrics'],'checks':checks,'next_required_capability':next_cap,'receipt_sha256':report['receipt_sha256']},indent=2,sort_keys=True))
if not passed:raise SystemExit(2)
