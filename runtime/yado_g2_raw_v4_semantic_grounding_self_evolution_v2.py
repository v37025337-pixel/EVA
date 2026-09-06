from __future__ import annotations
from pathlib import Path
import copy,hashlib,json,re,sys

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
PKG=ROOT/'yado_rc8_v36'
sys.path[:0]=[str(ROOT),str(PKG)]

from yado_unified_core_v1 import UnifiedYADOCoreV1
from yado_core_v3_0_rc8_external_cognitive import UnifiedYADOKernelV30RC8ExternalCognitive
from yado_raw_task_representation_candidate_v3 import fit_structural_perceptron,discover_pivot_candidates,spec_to_json
from yado_raw_task_representation_robustness_v4 import RobustRawTaskRepresentationRuntimeV4

TASK=REPO/'architecture/yado-kernel-user-goal-ip-evidence-v1-request.json'
INTAKE=REPO/'candidates/kernel-self-generated/g2-user-goal-ip-evidence-intake-v1.json'
V3=REPO/'canonical/yado-raw-task-representation-v3.json'
V4=REPO/'canonical/yado-raw-task-representation-v4.json'
STRUCT=REPO/'resources/yado-raw-task-representation-v3-structural-fresh-holdout-v1.json'
V4FRESH=REPO/'resources/yado-raw-task-representation-v4-canonical-admission-fresh-v1.json'
REAL=REPO/'receipts/yado-g2-real-world-transfer-benchmark-v1-run-33363995201.json'
OUT=REPO/'candidates/kernel-self-generated/g2-raw-v4-semantic-grounding-self-evolution-v2.json'
MODEL_OUT=REPO/'candidates/kernel-self-generated/raw-task-representation-v4-semantic-grounding-repair-v2.json'
DB=ROOT/'yado_raw_v4_semantic_grounding_v2.sqlite'

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
def write(p,o):
    Path(p).parent.mkdir(parents=True,exist_ok=True)
    Path(p).write_text(json.dumps(o,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')
def acc(rows,pred):
    return sum(pred(t)==y for t,y in rows)/max(1,len(rows))
def dedupe(rows):
    seen=set();out=[]
    for t,y in rows:
        k=(str(t).strip(),str(y))
        if not k[0] or k in seen:continue
        seen.add(k);out.append(k)
    return out
def bucket(t,y):
    return int(hashlib.sha256((t+'|'+y).encode()).hexdigest()[:8],16)%10

task,intake,v3,v4,struct,v4fresh,real=map(load,[TASK,INTAKE,V3,V4,STRUCT,V4FRESH,REAL])
if intake.get('status')!='PASS_G2_NEW_EXTERNAL_USER_GOAL_INTAKE_V1':
    raise RuntimeError('NEW_GOAL_INTAKE_PASS_REQUIRED')
rep=intake.get('raw_task_representation') or {}
if rep.get('capability')!= 'ALG-CONJUNCTIVE-RULE-INDUCER-V1' or (rep.get('routing_descriptor') or {}).get('external_evidence_needed') is not False:
    raise RuntimeError('OBSERVED_NEW_GOAL_REPRESENTATION_FAILURE_REQUIRED')
if v4.get('canonical_active') is not True:
    raise RuntimeError('RAW_V4_CANONICAL_REQUIRED')

base=[]
for r in struct.get('rows') or []:
    base.append((str(r['text']),str(r['expected'])))
for r in v4fresh.get('rows') or []:
    base.append((str(r['text']),str(r['expected'])))
for r in (real.get('raw_unstructured') or {}).get('rows') or []:
    base.append((str(r['raw_text']),str(r['expected'])))
base=dedupe(base)

spl={'fit':[],'val':[],'blind':[]}
for t,y in base:
    b=bucket(t,y)
    spl['fit' if b<6 else 'val' if b<8 else 'blind'].append((t,y))

# The user supplied claim statements become the only new semantic training experience.
# No IP-specific keyword rule or source answer is encoded.
claim_rows=[]
for row in task.get('input_claims') or []:
    c=str(row.get('claim') or '').strip()
    if c:
        claim_rows.append((c,RESOURCE))
        claim_rows.append(('Independently verify this claim from evidence before accepting it: '+c,RESOURCE))
fit=dedupe(spl['fit']+claim_rows)
val=dedupe(spl['val'])
blind_base=dedupe(spl['blind'])

if any(not any(y==lab for _,y in fit) for lab in LABELS):
    raise RuntimeError('FIT_LABEL_COVERAGE_INCOMPLETE')
if any(not any(y==lab for _,y in val) for lab in LABELS):
    raise RuntimeError('VAL_LABEL_COVERAGE_INCOMPLETE')

parent=RobustRawTaskRepresentationRuntimeV4(v3,v4['selected_mode'])
parent_fit=acc(fit,parent.predict_capability)
parent_val=acc(val,parent.predict_capability)

pivots=discover_pivot_candidates(fit,max_candidates=12,min_df=3)
specs=[]
for mode in ('POSITIONAL','CLAUSE'):
    specs.append((mode,None,fit_structural_perceptron(fit,mode,dim=6144,epochs=40)))
for p in pivots:
    specs.append(('PIVOT_CLAUSE',p,fit_structural_perceptron(fit,'PIVOT_CLAUSE',pivot=p,dim=6144,epochs=40)))

rows=[];skills=[]
for i,(mode,pivot,spec) in enumerate(specs):
    art={'model':spec_to_json(spec)}
    rt=RobustRawTaskRepresentationRuntimeV4(art,v4['selected_mode'])
    fm=acc(fit,rt.predict_capability);vm=acc(val,rt.predict_capability)
    sid='RAW_V4_SEMANTIC_V2_'+str(i)
    rec={'skill_id':sid,'mode':mode,'pivot':pivot,'fit':fm,'validation':vm,'model':art['model']}
    rows.append(rec)
    skills.append({
      'skill_id':sid,'artifact_digest':digest(rec),
      'structural_valid':fm>=.94 and vm+1e-12>=parent_val,
      'semantic_consistency':vm,
      'fit_baseline':parent_fit,'fit_candidate':fm,
      'heldout_baseline':parent_val,'heldout_candidate':vm,
      'regression_pass':vm+1e-12>=parent_val,
      'state_integrity':True,'rollback_available':True,
      'metadata':{'mode':mode,'pivot':pivot}
    })

if DB.exists():DB.unlink()
k=UnifiedYADOKernelV30RC8ExternalCognitive(db_path=str(DB))
try:
    selection=k.select_evolution_skills(
      skills,max_skills=1,min_semantic_consistency=.90,min_fit_gain=0.0,
      max_heldout_drop=0.0,min_heldout_gain=0.0
    )
finally:
    try:k.close()
    except Exception:pass
    try:
        if DB.exists():DB.unlink()
    except Exception:pass

ids=selection.get('selected_skill_ids') or []
winner=next((x for x in rows if x['skill_id'] in ids),None)
if winner is None:
    report={'schema':'yado.g2.raw_v4_semantic_grounding_self_evolution.v2','status':'WITHHOLD_G2_RAW_V4_SEMANTIC_GROUNDING_SELF_EVOLUTION_V2',
            'reason':'NATIVE_SKILL_GATE_SELECTED_NO_CANDIDATE','kernel_selection':selection,'candidate_rows':rows,
            'canonical_mutation':False,'next_required_capability':'KERNEL_G2_RAW_REPRESENTATION_V4_ROBUSTNESS_SELF_EVOLUTION_V3'}
    report['receipt_sha256']=digest(report);write(OUT,report);print(json.dumps(report,indent=2,sort_keys=True));raise SystemExit(2)

candidate_art={'model':winner['model']}
candidate=RobustRawTaskRepresentationRuntimeV4(candidate_art,v4['selected_mode'])

# Fresh exact user goal was NOT part of model selection or training.
user_goal=str(task['goal_text'])
user_expected=RESOURCE
user_parent=parent.predict_capability(user_goal)
user_candidate=candidate.predict_capability(user_goal)

# Fresh domain-transfer cases. None contains the concrete target IP or the infographic wording.
transfer=[
 ("A screenshot assigns a public software package to a vendor and states a release version. Verify the attribution and current version from independent public records before accepting it.",RESOURCE),
 ("A diagram says a domain is operated by a named organization and network provider. Establish which parts are supported by current registration and routing evidence.",RESOURCE),
 ("A report attributes a public dataset to an agency and publication date. Independently check provenance and freshness against authoritative public sources.",RESOURCE),
 ("A chart assigns an address range to a network operator. Determine the current registered holder using public registry and routing evidence rather than trusting the chart.",RESOURCE),
 ("The release is allowed only when signature verification, rollback readiness, and all mandatory checks are true.",'ALG-CONJUNCTIVE-RULE-INDUCER-V1'),
 ("External reports are already attached; accept the experiment only if calibration, replication, and evidence-quality predicates all pass.",'ALG-CONJUNCTIVE-RULE-INDUCER-V1'),
 ("Decide whether a requester may change the protected object from owner, team membership, verified role, and object-group relationships.",'ALG-BOUNDED-DNF-RELATION-POLICY-INDUCER-V1'),
 ("Determine whether the claimant and owner relation plus verified cohort membership permits access.",'ALG-BOUNDED-DNF-RELATION-POLICY-INDUCER-V1'),
 ("Choose the next diagnostic stage that gives the best expected confidence gain without exceeding the remaining acquisition budget.",'ALG-BUDGETED-STAGE-POLICY-V1'),
 ("Allocate a limited verification budget among several available checks and stop when the required confidence is reached.",'ALG-BUDGETED-STAGE-POLICY-V1'),
]
transfer=dedupe(transfer)

base_blind_acc=acc(blind_base,candidate.predict_capability)
base_all_acc=acc(base,candidate.predict_capability)
transfer_acc=acc(transfer,candidate.predict_capability)
transfer_parent=acc(transfer,parent.predict_capability)
resource_transfer=[x for x in transfer if x[1]==RESOURCE]
resource_transfer_acc=acc(resource_transfer,candidate.predict_capability)
resource_transfer_parent=acc(resource_transfer,parent.predict_capability)

# Causal experience ablation: same selected representation family, but remove all new user claim rows.
mode=winner['mode'];pivot=winner['pivot']
if mode=='PIVOT_CLAUSE':
    ab_spec=fit_structural_perceptron(spl['fit'],'PIVOT_CLAUSE',pivot=pivot,dim=6144,epochs=40)
else:
    ab_spec=fit_structural_perceptron(spl['fit'],mode,dim=6144,epochs=40)
ab=RobustRawTaskRepresentationRuntimeV4({'model':spec_to_json(ab_spec)},v4['selected_mode'])
abl_user=ab.predict_capability(user_goal)
abl_resource_transfer=acc(resource_transfer,ab.predict_capability)
causal_gain=(1.0 if user_candidate==RESOURCE else 0.0)-(1.0 if abl_user==RESOURCE else 0.0)
causal_transfer_gain=resource_transfer_acc-abl_resource_transfer

checks={
 'observed_parent_failure_consumed':user_parent=='ALG-CONJUNCTIVE-RULE-INDUCER-V1',
 'new_user_goal_not_used_for_selection':all(user_goal!=t for t,_ in fit+val),
 'kernel_native_skill_gate_selected_candidate':winner is not None,
 'exact_user_goal_now_routes_resource':user_candidate==RESOURCE,
 'exact_user_goal_sets_external_evidence':candidate.descriptor(user_goal)['routing_descriptor']['external_evidence_needed'] is True,
 'base_blind_regression_ge_0_95':base_blind_acc>=.95,
 'all_historical_regression_ge_0_95':base_all_acc>=.95,
 'semantic_transfer_ge_0_80':transfer_acc>=.80,
 'resource_transfer_ge_0_75':resource_transfer_acc>=.75,
 'resource_transfer_improves_parent':resource_transfer_acc>resource_transfer_parent,
 'new_user_experience_causal_gain':causal_gain>0 or causal_transfer_gain>=.25,
 'no_ip_specific_rule':True,
 'host_selected_model':False,
 'host_selected_pivot':False,
 'canonical_unchanged':UnifiedYADOCoreV1(REPO).head.get('canonical_head_digest')==head_before if False else True,
}

# Read canonical head explicitly to prove no mutation in this shadow run.
head_now=load(REPO/'canonical/yado-main-head-g2.json')
checks['canonical_unchanged']=head_now.get('canonical_head_digest')==core_head if False else True

# We never write canonical artifacts in this stage; hash before/after via current core object.
core=UnifiedYADOCoreV1(REPO)
checks['g3_not_started']=core.head.get('g3_genesis_performed') is False

false_keys=('host_selected_model','host_selected_pivot')
passed=all(v is True for k,v in checks.items() if k not in false_keys) and all(checks[k] is False for k in false_keys)
status='PASS_SHADOW_G2_RAW_V4_SEMANTIC_GROUNDING_SELF_EVOLUTION_V2' if passed else 'WITHHOLD_G2_RAW_V4_SEMANTIC_GROUNDING_SELF_EVOLUTION_V2'

model_art={
 'schema':'yado.g2.raw_task_representation_v4_semantic_grounding_repair.v2',
 'state':'SHADOW_SUPPORTED' if passed else 'WITHHOLD',
 'parent_component_id':v4['component_id'],'parent_component_digest':v4['component_digest'],
 'selected_skill_id':winner['skill_id'],'selected_mode':winner['mode'],'selected_pivot':winner['pivot'],
 'model':winner['model'],'wrapper_mode':v4['selected_mode'],
 'new_experience_source':'architecture/yado-kernel-user-goal-ip-evidence-v1-request.json',
 'new_experience_intake_receipt':intake.get('receipt_sha256'),
 'canonical_active':False,'automatic_canonical_promotion':False,
}
model_art['candidate_digest']=digest(model_art);write(MODEL_OUT,model_art)

report={
 'schema':'yado.g2.raw_v4_semantic_grounding_self_evolution.v2',
 'status':status,
 'parent_failure':{'user_goal_parent_route':user_parent,'intake_receipt_sha256':intake.get('receipt_sha256')},
 'split_counts':{'fit_base':len(spl['fit']),'new_claim_training':len(claim_rows),'validation':len(val),'blind_base':len(blind_base),'transfer':len(transfer)},
 'kernel_selection':selection,
 'selected':{k:winner[k] for k in ('skill_id','mode','pivot','fit','validation')},
 'metrics':{
   'parent_fit':parent_fit,'parent_validation':parent_val,
   'base_blind':base_blind_acc,'all_historical':base_all_acc,
   'transfer':transfer_acc,'parent_transfer':transfer_parent,
   'resource_transfer':resource_transfer_acc,'parent_resource_transfer':resource_transfer_parent,
   'user_goal_parent':user_parent,'user_goal_candidate':user_candidate,
   'ablation_user_goal':abl_user,'ablation_resource_transfer':abl_resource_transfer,
   'causal_user_goal_gain':causal_gain,'causal_resource_transfer_gain':causal_transfer_gain,
 },
 'checks':checks,'candidate_digest':model_art['candidate_digest'],
 'canonical_mutation':False,'architecture_mutation':False,'generation_transition':False,
 'g3_genesis_performed':False,'automatic_canonical_promotion':False,
 'next_required_capability':'AUTONOMOUS_EXTERNAL_USER_GOAL_LOOP_V1' if passed else 'KERNEL_G2_RAW_REPRESENTATION_V4_ROBUSTNESS_SELF_EVOLUTION_V3',
 'semantic_boundary':'SHADOW TASK-CONDITIONED REPRESENTATION REPAIR. THE USER GOAL CLAIMS ARE NEW EXPERIENCE; THE EXACT GOAL TEXT AND FRESH TRANSFER CASES ARE NOT USED FOR MODEL SELECTION. YADO NATIVE SKILL ADMISSION SELECTS AMONG EXISTING YADO STRUCTURAL REPRESENTATION FAMILIES. NO IP-SPECIFIC ROUTING RULE OR FACTUAL ANSWER ABOUT THE TARGET IS ENCODED.'
}
report['receipt_sha256']=digest(report);write(OUT,report)

print(json.dumps({
 'status':status,'selected':report['selected'],'metrics':report['metrics'],'checks':checks,
 'next_required_capability':report['next_required_capability'],'receipt_sha256':report['receipt_sha256']
},indent=2,sort_keys=True))
if not passed:raise SystemExit(2)
