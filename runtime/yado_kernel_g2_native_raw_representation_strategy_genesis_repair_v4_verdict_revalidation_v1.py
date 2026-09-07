from __future__ import annotations
from pathlib import Path
import hashlib,json,sys

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
PKG=ROOT/'yado_rc8_v36'
sys.path[:0]=[str(ROOT),str(PKG)]

V4=REPO/'architecture/yado-kernel-g2-native-raw-representation-strategy-genesis-repair-v4.json'
CAND=REPO/'candidates/kernel-self-generated/raw-task-representation-strategy-model-v4.json'
FRESH=REPO/'resources/yado-raw-task-representation-strategy-genesis-repair-v4-fresh.json'
HEAD=REPO/'canonical/yado-main-head-g2.json'
OUT=REPO/'architecture/yado-kernel-g2-native-raw-representation-strategy-genesis-repair-v4-verdict-revalidation-v1.json'

def load(p): return json.loads(Path(p).read_text(encoding='utf-8'))
def canon(o): return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def digest(o): return hashlib.sha256(canon(o).encode()).hexdigest()
def write(p,o):
    Path(p).parent.mkdir(parents=True,exist_ok=True)
    Path(p).write_text(json.dumps(o,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')

v4,cand,fresh,head=map(load,[V4,CAND,FRESH,HEAD])

if v4.get('receipt_sha256')!='55bc5cf7633a47b13059dbd8f9de3ae47347a44cc1a0d47a68004b31f0b89922':
    raise RuntimeError('V4_RECEIPT_DRIFT')
if cand.get('candidate_digest')!='03bf3624f16ddca433f02ce4f956258e2dee72046f65571fa4b226c65183ef6d':
    raise RuntimeError('V4_CANDIDATE_DRIFT')
if fresh.get('dataset_digest')!='f3f504958c8c3126adaf12d91dc20efe0a56b74e65462c86119d7cecc8083ff5':
    raise RuntimeError('V4_FRESH_DRIFT')

checks=dict(v4.get('checks') or {})
required_true=[
 'v3_exact_withhold_consumed','v3_spent_sequential_exactly_reproduced',
 'generic_family_surface_discovered_from_yado_source','native_goal_created',
 'native_selector_selected_one_family','fresh_not_used_for_training_or_selection',
 'selected_validation_ge_0_95','fresh_direct_accuracy','fresh_wrapped_accuracy',
 'fresh_sequential_accuracy','fresh_sequential_gain_over_v3','base_regression',
 'causal_ablation_drop','class_specific_rules_absent','canonical_unchanged','g3_not_started'
]
required_false=['host_selected_family','automatic_promotion']

true_fail=[k for k in required_true if checks.get(k) is not True]
false_fail=[k for k in required_false if checks.get(k) is not False]

m=v4.get('fresh_metrics') or {}
metric_checks={
 'direct_ge_0_98':float(m.get('direct',0))>=.98,
 'wrapped_ge_0_98':float(m.get('fresh_wrapped',0))>=.98,
 'sequential_ge_0_98':float(m.get('fresh_sequential',0))>=.98,
 'sequential_gain_ge_0_01':float(m.get('fresh_sequential',0))-float(m.get('v3_fresh_sequential',0))>=.01,
 'base_regression_ge_0_98':float(m.get('base_regression',0))>=.98,
 'ablation_drop_ge_0_20':float(m.get('fresh_sequential',0))-float(m.get('ablated_sequential',1))>=.20,
}
selection=v4.get('native_selection') or {}
selection_ok=(
 selection.get('selected_count')==1
 and (selection.get('selected_skill_ids') or [])==['RAW_MODEL_V4_HASHED_CHAR45_PERCEPTRON']
 and v4.get('selected_family')=='HASHED_CHAR45_PERCEPTRON'
)
artifact_consistency=(
 cand.get('selected_family')==v4.get('selected_family')
 and cand.get('model_digest')=='ec9ab1ecc29d45ee2d7c0d616e7e23fcf28d235348a0f5a270dffdeb4e0f7505'
 and fresh.get('selected_family')==v4.get('selected_family')
 and fresh.get('metrics')==m
)
canonical_unchanged=(
 head.get('current_frontier')=='KERNEL_G2_RAW_REPRESENTATION_V4_ROBUSTNESS_SELF_EVOLUTION_V2'
 and head.get('g3_genesis_performed') is False
)

corrected_pass=(
 not true_fail and not false_fail and all(metric_checks.values())
 and selection_ok and artifact_consistency and canonical_unchanged
)

report={
 'schema':'yado.g2.native_raw_representation_strategy_genesis_repair_v4.verdict_revalidation.v1',
 'status':'PASS_SHADOW_G2_NATIVE_RAW_REPRESENTATION_STRATEGY_GENESIS_REPAIR_V4_REVALIDATED'
          if corrected_pass else 'WITHHOLD_G2_NATIVE_RAW_REPRESENTATION_STRATEGY_GENESIS_REPAIR_V4_REVALIDATION',
 'source_v4_status':v4.get('status'),
 'source_v4_receipt':v4.get('receipt_sha256'),
 'candidate_digest':cand.get('candidate_digest'),
 'model_digest':cand.get('model_digest'),
 'fresh_dataset_digest':fresh.get('dataset_digest'),
 'selected_family':v4.get('selected_family'),
 'fresh_metrics':m,
 'required_true_failures':true_fail,
 'required_false_failures':false_fail,
 'metric_checks':metric_checks,
 'selection_consistent':selection_ok,
 'artifact_consistency':artifact_consistency,
 'canonical_unchanged':canonical_unchanged,
 'evaluator_defect':{
   'kind':'BOOLEAN_POLARITY_ERROR',
   'description':'The original V4 observer used all(checks.values()) even though host_selected_family and automatic_promotion are safety invariants that must be false on success.',
   'model_retrained_for_revalidation':False,
   'fresh_cases_regenerated_for_revalidation':False,
   'thresholds_changed':False,
   'candidate_changed':False,
 },
 'canonical_mutation':False,'promotion_applied':False,'g3_genesis_performed':False,
 'next_required_capability':'NATIVE_RAW_REPRESENTATION_STRATEGY_CANONICAL_ADMISSION_V5'
      if corrected_pass else 'NATIVE_RAW_REPRESENTATION_MODEL_FAMILY_EXPANSION_V5',
 'semantic_boundary':'VERDICT-ONLY REVALIDATION OF IMMUTABLE V4 EVIDENCE. NO MODEL TRAINING, FRESH-DATA REGENERATION, THRESHOLD CHANGE, CANDIDATE CHANGE, OR CANONICAL MUTATION IS PERFORMED.'
}
report['receipt_sha256']=digest(report);write(OUT,report)
print(json.dumps(report,indent=2,sort_keys=True))
if not corrected_pass: raise SystemExit(2)
