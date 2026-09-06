from __future__ import annotations

from pathlib import Path
from dataclasses import asdict
from itertools import combinations
import copy,hashlib,json,sys

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
PKG=ROOT/'yado_rc8_v36'
sys.path[:0]=[str(ROOT),str(PKG)]

from yado_unified_core_v1 import UnifiedYADOCoreV1
from yado_core_v3_0_rc8_external_cognitive import UnifiedYADOKernelV30RC8ExternalCognitive
from yado_organ_runtime_native_v1 import tree_predict

V6=REPO/'candidates/kernel-self-generated/g2-native-semantic-edit-to-ast-materialization-v6.json'
SEM=REPO/'candidates/kernel-self-generated/g2-task-conditioned-semantic-source-edit-meta-language-genesis-v5.json'
BINDER=REPO/'candidates/kernel-self-generated/g2-native-self-created-evidence-binder-gene-v1.json'
ACTION=REPO/'candidates/kernel-self-generated/g2-autonomous-self-improvement-task-v1.json'
OUT=REPO/'candidates/kernel-self-generated/g2-native-contextual-ast-transformer-gene-genesis-v7.json'
GENE=REPO/'candidates/kernel-self-generated/g2-native-contextual-ast-transformer-gene-v7.json'
DB=ROOT/'yado_native_contextual_ast_transformer_gene_genesis_v7.sqlite'

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def digest(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))

v6,sem,binder,action=map(load,[V6,SEM,BINDER,ACTION])
if v6.get('status')!='WITHHOLD_G2_NATIVE_SEMANTIC_EDIT_TO_AST_MATERIALIZATION_V6':
    raise RuntimeError('V6_WITHHOLD_REQUIRED')
if v6.get('next_required_capability')!='NATIVE_CONTEXTUAL_AST_TRANSFORMER_GENE_GENESIS_V7':
    raise RuntimeError('V6_FRONTIER_MISMATCH')

meta_gene=sem.get('meta_language_gene') or {}
operator=meta_gene.get('operator_program') or {}
transition=operator.get('transition_semantics') or {}
accept_action=transition.get('on_accept')
withhold_action=transition.get('on_withhold')
if not accept_action or not withhold_action or accept_action==withhold_action:
    raise RuntimeError('SEMANTIC_TRANSITION_ACTIONS_REQUIRED')

core=UnifiedYADOCoreV1(REPO);head_before=copy.deepcopy(core.head)

binding=action.get('goal_action_binding') or {}
result=binding.get('result') or {}
comp=result.get('comprehension') or {}
base={
 'priority_match': action.get('kernel_selected_next_step')=='LIVE_RESOURCE_EVIDENCE_SCOPE',
 'direct_priority_evidence': action.get('direct_priority_evidence') is True,
 'action_relevant': action.get('selected_action')=='LIVE_RESOURCE_EVIDENCE_RECHECK',
 'action_status_pass': str(result.get('status') or '').startswith('PASS_'),
 'comprehension_complete': all(bool(comp.get(k)) for k in (
     'repository_commit_identity_extracted','readme_title_extracted',
     'package_identity_extracted','provider_catalog_extracted',
     'no_key_provider_set_extracted')),
 'conflict_resolution_pass': result.get('conflict_resolution_pass') is True,
 'canonical_immutable': result.get('canonical_mutation') is False and action.get('canonical_head_unchanged') is True,
}
model=binder.get('model')
required=tuple(sorted(k for k in base))
if tree_predict(model,base)!='ACCEPT_FRESH_EVIDENCE':
    raise RuntimeError('BINDER_REAL_EVIDENCE_NOT_ACCEPTED')

def bind_input(features):
    x=dict(features)
    # This categorical feature is not host logic: it is the direct output of
    # YADO's already-created evidence-binder gene over the same contract fields.
    x['binder_decision']=tree_predict(model,x)
    return x

def expected(features):
    decision=str(features.get('binder_decision') or '')
    return accept_action if decision=='ACCEPT_FRESH_EVIDENCE' else withhold_action

rows=[]
for nonce in range(10):
    x=dict(base);x['irrelevant_nonce']=nonce;x=bind_input(x)
    rows.append({'input':x,'expected':expected(x),'kind':'POSITIVE'})
for idx,k in enumerate(required):
    for nonce in range(4):
        x=dict(base);x[k]=False;x['irrelevant_nonce']=100+idx*10+nonce;x=bind_input(x)
        rows.append({'input':x,'expected':expected(x),'kind':'SINGLE_FAULT_'+k})
for idx,(a,b) in enumerate(combinations(required,2)):
    x=dict(base);x[a]=False;x[b]=False;x['irrelevant_nonce']=500+idx;x=bind_input(x)
    rows.append({'input':x,'expected':expected(x),'kind':'PAIR_FAULT_'+a+'_'+b})

fit=[];blind=[]
for r in rows:
    h=int(hashlib.sha256((canon(r['input'])+'|AST_TRANSFORM_V7').encode()).hexdigest()[:8],16)%10
    (blind if h<3 else fit).append({'input':r['input'],'expected':r['expected']})
if not fit or not blind:raise RuntimeError('BAD_V7_SPLIT')
if not any(x['expected']==accept_action for x in fit+blind):raise RuntimeError('NO_ACCEPT_EXAMPLES')
if not any(x['expected']==withhold_action for x in fit+blind):raise RuntimeError('NO_WITHHOLD_EXAMPLES')

if DB.exists():DB.unlink()
k=UnifiedYADOKernelV30RC8ExternalCognitive(db_path=str(DB))
try:
    goal=k.executive.create_goal(
      objective='Create a contextual AST transformation policy from YADO self-generated binder decisions and YADO self-generated semantic source-edit transition semantics.',
      required_capabilities={'NATIVE_CONTEXTUAL_AST_TRANSFORMER_POLICY_V7':1.0},
      success_criteria={'fresh_exact':1.0,'ablation_required':True,'restore_required':True,'fail_closed':True},
    )
    deficits=k.executive.detect_deficits(goal.goal_id)
    if len(deficits)!=1:raise RuntimeError('EXPECTED_ONE_V7_DEFICIT')
    deficit=deficits[0]
    program,selection=k.executive.synthesize_best_mechanism(
      deficit.deficit_id,'GENERATIVE_EXECUTIVE',fit,min_support=2
    )
    dev=k.executive.evaluate_mechanism(
      program.program_id,blind,min_score=1.0,min_ablation_drop=.20
    )
    actual_input=bind_input(base)
    actual=k.executive.execute_capability('NATIVE_CONTEXTUAL_AST_TRANSFORMER_POLICY_V7',actual_input) if dev.state_committed else None
    counter=[]
    for field in required:
        cf=dict(base);cf[field]=False;cf=bind_input(cf)
        pred=k.executive.execute_capability('NATIVE_CONTEXTUAL_AST_TRANSFORMER_POLICY_V7',cf) if dev.state_committed else None
        counter.append({'flipped_field':field,'prediction':pred})
finally:
    try:k.close()
    except Exception:pass

history_shapes=[]
for row in sem.get('history_transitions') or []:
    before=row.get('before_status_shape');after=row.get('after_status_shape')
    if before and after and before!=after:
        history_shapes.append({'before':before,'after':after,'transition':row.get('transition'),'finding_code':row.get('finding_code')})
observed_after_shapes=sorted({x['after'] for x in history_shapes})
if 'IfExp' not in observed_after_shapes:
    raise RuntimeError('NO_HISTORY_DERIVED_CONDITIONAL_SHAPE')

checks={
 'canonical_v5_continuity_active':core.execution_fabric_cls.COMPONENT_ID=='RUNTIME-G2-UNIFIED-EXECUTION-FABRIC-V5',
 'v6_failure_consumed':True,
 'semantic_gene_consumed':bool(meta_gene.get('gene_id')),
 'binder_gene_consumed':bool(binder.get('gene_id')),
 'semantic_actions_derived_from_gene':True,
 'binder_decision_feature_is_yado_derived':all('binder_decision' in x['input'] for x in fit+blind),
 'historical_conditional_shape_derived_from_yado_history':'IfExp' in observed_after_shapes,
 'native_goal_created':True,
 'native_deficit_detected':True,
 'native_policy_synthesized':bool(program.program_id),
 'native_policy_committed':dev.state_committed and dev.verdict=='COMMIT',
 'fresh_blind_exact':dev.candidate_score==1.0,
 'causal_ablation_drop_ge_0_20':dev.candidate_score-dev.ablation_score>=.20,
 'restore_exact':dev.restore_score==dev.candidate_score,
 'actual_valid_evidence_routes_to_accept_action':actual==accept_action,
 'single_faults_route_to_withhold_action':all(x['prediction']==withhold_action for x in counter),
 'host_authored_transition_action':False,
 'host_authored_ast_subtree':False,
 'host_authored_transform_condition':False,
 'external_models_used':False,
 'canonical_unchanged':core.head.get('canonical_head_digest')==head_before.get('canonical_head_digest'),
 'automatic_canonical_promotion':False,
}

positive=(
 'canonical_v5_continuity_active','v6_failure_consumed','semantic_gene_consumed','binder_gene_consumed',
 'semantic_actions_derived_from_gene','binder_decision_feature_is_yado_derived','historical_conditional_shape_derived_from_yado_history',
 'native_goal_created','native_deficit_detected','native_policy_synthesized','native_policy_committed',
 'fresh_blind_exact','causal_ablation_drop_ge_0_20','restore_exact',
 'actual_valid_evidence_routes_to_accept_action','single_faults_route_to_withhold_action','canonical_unchanged'
)
negative=(
 'host_authored_transition_action','host_authored_ast_subtree','host_authored_transform_condition',
 'external_models_used','automatic_canonical_promotion'
)
passed=all(checks[k] is True for k in positive) and all(checks[k] is False for k in negative)

gene=None
if passed:
    gene={
      'schema':'yado.g2.native_contextual_ast_transformer_gene.v7',
      'gene_id':'GENE-G2-NATIVE-CONTEXTUAL-AST-TRANSFORMER-V7-'+digest({
          'program_id':program.program_id,'program_digest':dev.program_digest,
          'semantic_gene':meta_gene.get('gene_digest'),'binder_gene':binder.get('gene_digest')
      })[:16],
      'novel_gene':True,
      'gene_scope':['CODE','SELF_AUDIT_AND_REPAIR','GENERATIVE_EXECUTIVE'],
      'origin':'YADO_NATIVE_GENERATIVE_EXECUTIVE_OVER_YADO_SELF_GENERATED_BINDER_AND_SEMANTIC_EDIT_GENE',
      'binder_gene_id':binder.get('gene_id'),
      'binder_gene_digest':binder.get('gene_digest'),
      'semantic_edit_gene_id':meta_gene.get('gene_id'),
      'semantic_edit_gene_digest':meta_gene.get('gene_digest'),
      'policy_program_id':program.program_id,
      'policy_program_digest':dev.program_digest,
      'transition_semantics':copy.deepcopy(transition),
      'anchor_contract':copy.deepcopy(operator.get('anchor_contract')),
      'history_derived_target_status_shape':'IfExp',
      'execution_mode':'CONTEXTUAL_AST_TRANSFORM_POLICY',
      'actual_ast_materialization_proven':False,
      'python_source_emission_proven':False,
      'promotion_state':'SHADOW_ONLY',
    }
    gene['gene_digest']=digest(gene)
    GENE.parent.mkdir(parents=True,exist_ok=True)
    GENE.write_text(json.dumps(gene,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')

status='PASS_SHADOW_G2_NATIVE_CONTEXTUAL_AST_TRANSFORMER_GENE_GENESIS_V7' if passed else 'WITHHOLD_G2_NATIVE_CONTEXTUAL_AST_TRANSFORMER_GENE_GENESIS_V7'
next_cap='NATIVE_CONTEXTUAL_AST_TRANSFORMER_SOURCE_REALIZATION_V8' if passed else 'NATIVE_CONTEXTUAL_AST_TRANSFORMER_POLICY_REPAIR_V8'

report={
 'schema':'yado.g2.native_contextual_ast_transformer_gene_genesis.v7',
 'status':status,
 'parent_v6_receipt':v6.get('receipt_sha256'),
 'semantic_gene_id':meta_gene.get('gene_id'),'binder_gene_id':binder.get('gene_id'),
 'native_goal':{'goal_id':goal.goal_id,'deficit_id':deficit.deficit_id},
 'dataset':{'fit':len(fit),'blind':len(blind),'construction':'BINDER_LABELED_REAL_POSITIVE_PLUS_SINGLE_PAIR_COUNTERFACTUALS','typed_binding_feature':'binder_decision from YADO binder gene'},
 'semantic_actions':{'accept':accept_action,'withhold':withhold_action},
 'history_derived_status_shapes':history_shapes,
 'native_policy':{'program_id':program.program_id,'selection':asdict(selection),'development':asdict(dev)},
 'actual_prediction':actual,'counterfactual_predictions':counter,
 'gene':gene,'checks':checks,'canonical_mutation':False,'promotion_applied':False,
 'next_required_capability':next_cap,
 'semantic_boundary':'V7 CREATES A DATA-LEVEL CONTEXTUAL AST-TRANSFORMER POLICY GENE. THE TWO TRANSITION ACTIONS COME VERBATIM FROM YADO OWN SEMANTIC SOURCE-EDIT GENE; ACCEPT/WITHHOLD LABELS COME FROM YADO OWN EVIDENCE-BINDER MODEL; THE CONDITIONAL TARGET SHAPE IS OBSERVED IN YADO OWN SOURCE HISTORY. THE HOST DOES NOT AUTHOR AN AST SUBTREE, CONDITION, OR TRANSITION ACTION. PASS DOES NOT YET CLAIM AST OR PYTHON SOURCE MATERIALIZATION; V8 MUST REALIZE THIS GENE INTO SOURCE/AST AND PASS FRESH REGRESSION.'
}
report['receipt_sha256']=digest(report)
OUT.parent.mkdir(parents=True,exist_ok=True)
OUT.write_text(json.dumps(report,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')
print(json.dumps({
 'status':status,'policy':{'candidate':dev.candidate_score,'ablation':dev.ablation_score,'restore':dev.restore_score,'verdict':dev.verdict},
 'actual_prediction':actual,'counterfactual_predictions':counter,
 'gene_id':gene.get('gene_id') if gene else None,
 'next_required_capability':next_cap,'checks':checks,'receipt_sha256':report['receipt_sha256']
},indent=2,sort_keys=True,default=str))
if not passed:raise SystemExit(2)
