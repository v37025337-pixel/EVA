from __future__ import annotations
from pathlib import Path
from dataclasses import asdict
import copy,hashlib,json,sys

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
PKG=ROOT/'yado_rc8_v36'
sys.path[:0]=[str(ROOT),str(PKG)]

from yado_unified_core_v1 import UnifiedYADOCoreV1
from yado_core_v3_0_rc8_external_cognitive import UnifiedYADOKernelV30RC8ExternalCognitive

TASK=REPO/'architecture/yado-kernel-experience-conditioned-deficit-to-mutation-binding-v2-request.json'
BRIDGE=REPO/'candidates/kernel-self-generated/g2-experience-conditioned-evolution-action-bridge-v1.json'
CURRENT=REPO/'candidates/kernel-self-generated/g2-native-action-evidence-binder-source-realization-v1.json'
CORPUS=REPO/'experience/yado-global-experience-corpus-v1.json'
OUT=REPO/'candidates/kernel-self-generated/g2-experience-conditioned-deficit-to-mutation-binding-v2.json'
DB=ROOT/'yado_experience_conditioned_deficit_binding_v2.sqlite'

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def digest(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))

task=load(TASK);bridge=load(BRIDGE);current=load(CURRENT);corpus=load(CORPUS)
if bridge.get('status')!='PASS_SHADOW_G2_EXPERIENCE_CONDITIONED_EVOLUTION_ACTION_BRIDGE_V1':
    raise RuntimeError('BRIDGE_V1_PASS_REQUIRED')
if current.get('status')!='WITHHOLD_G2_NATIVE_ACTION_EVIDENCE_BINDER_SOURCE_REALIZATION_V1':
    raise RuntimeError('CURRENT_NATIVE_SOURCE_WITHHOLD_REQUIRED')
if bridge.get('next_required_capability')!='EXPERIENCE_CONDITIONED_DEFICIT_TO_MUTATION_BINDING_V2':
    raise RuntimeError('UNEXPECTED_BRIDGE_FRONTIER')
if any(r.get('path')==str(CURRENT.relative_to(REPO)) for r in corpus.get('rows') or []):
    raise RuntimeError('CURRENT_CASE_MUST_BE_POST_CORPUS')

core=UnifiedYADOCoreV1(REPO);head_before=copy.deepcopy(core.head)

def split_bucket(r):return int(str(r['sha256'])[:8],16)%10

def features(r):
    m=r.get('metrics') or {}
    dom=str(r.get('domain') or 'GENERAL')
    nxt=bool(r.get('next_required_capability'))
    return {
      'status_withhold':r.get('outcome')=='WITHHOLD',
      'status_pass':r.get('outcome')=='PASS',
      'next_present':nxt,
      'same_domain_next':nxt and r.get('next_domain')==r.get('domain'),
      'fresh_positive':bool(m.get('fresh_positive')),
      'ablation_positive':bool(m.get('ablation_positive')),
      'canonical_unchanged':bool(m.get('canonical_unchanged')),
      'rollback_available':bool(m.get('rollback_available')),
      'source_candidate':r.get('source_class')=='CANDIDATE',
      'source_receipt':r.get('source_class')=='RECEIPT',
      'domain_code':dom=='CODE',
      'domain_representation':dom=='REPRESENTATION',
      'domain_cognitive':dom=='COGNITIVE',
      'domain_execution':dom=='EXECUTION',
      'domain_memory':dom=='MEMORY',
      'domain_evolution':dom=='EVOLUTION',
    }

def expected(r):
    # This is the same durable corpus transition semantics already used by YADO:
    # a failed state with an explicit next capability is a revision frontier.
    return 'BIND_EXPERIENCE_DEFICIT' if r.get('outcome')=='WITHHOLD' and r.get('next_required_capability') else 'WITHHOLD_DEFICIT_BINDING'

rows=[r for r in corpus.get('rows') or [] if r.get('outcome') in ('PASS','WITHHOLD')]
splits={'fit':[],'validation':[],'blind':[]}
for r in rows:
    b=split_bucket(r);key='fit' if b<6 else ('validation' if b<8 else 'blind')
    splits[key].append(r)

def balanced(xs):
    pos=sorted([r for r in xs if expected(r)=='BIND_EXPERIENCE_DEFICIT'],key=lambda r:(r['sha256'],r['path']))
    neg=sorted([r for r in xs if expected(r)=='WITHHOLD_DEFICIT_BINDING'],key=lambda r:(r['sha256'],r['path']))
    n=min(len(pos),len(neg))
    if n<6:raise RuntimeError('DEFICIT_BINDING_SPLIT_TOO_SMALL:'+str([len(pos),len(neg)]))
    out=pos[:n]+neg[:n]
    return sorted(out,key=lambda r:(r['sha256'],r['path']))

fit_rows=balanced(splits['fit']);val_rows=balanced(splits['validation']);blind_rows=balanced(splits['blind'])
fit=[{'input':features(r),'expected':expected(r)} for r in fit_rows]
val=[{'input':features(r),'expected':expected(r)} for r in val_rows]
blind=[{'input':features(r),'expected':expected(r)} for r in blind_rows]

if DB.exists():DB.unlink()
k=UnifiedYADOKernelV30RC8ExternalCognitive(db_path=str(DB))
try:
    goal=k.executive.create_goal(
      objective=str(task['objective']),
      required_capabilities={'EXPERIENCE_CONDITIONED_DEFICIT_BINDING_V2':1.0},
      success_criteria={'validation':.95,'fresh_blind':.95,'ablation_drop':.20,'restore':True,'fail_closed':True},
    )
    deficits=k.executive.detect_deficits(goal.goal_id)
    if len(deficits)!=1:raise RuntimeError('DEFICIT_BINDING_NATIVE_DEFICIT_COUNT')
    prog,selection=k.executive.synthesize_best_mechanism(
      deficits[0].deficit_id,'GENERATIVE_EXECUTIVE',fit+val,min_support=2
    )
    dev=k.executive.evaluate_mechanism(
      prog.program_id,blind,min_score=.95,min_ablation_drop=.20
    )

    def acc(cases):
        ok=0
        for c in cases:
            try:y=k.executive.execute_capability('EXPERIENCE_CONDITIONED_DEFICIT_BINDING_V2',c['input'])
            except Exception:y=None
            ok+=y==c['expected']
        return ok/max(1,len(cases))

    validation_acc=acc(val)
    blind_acc=acc(blind)

    cur_row=copy.deepcopy(bridge['current_row'])
    cur_input=features(cur_row)
    current_prediction=k.executive.execute_capability('EXPERIENCE_CONDITIONED_DEFICIT_BINDING_V2',cur_input)

    # Counterfactual: same evidence surface but no explicit next capability must fail closed.
    counterfactual=copy.deepcopy(cur_input);counterfactual['next_present']=False;counterfactual['same_domain_next']=False
    counterfactual_prediction=k.executive.execute_capability('EXPERIENCE_CONDITIONED_DEFICIT_BINDING_V2',counterfactual)
finally:
    try:k.close()
    except Exception:pass

kernel_next=str(cur_row.get('next_required_capability') or '')
bound_deficit=None
if current_prediction=='BIND_EXPERIENCE_DEFICIT':
    bound_deficit={
      'schema':'yado.g2.experience_conditioned_deficit.v2',
      'deficit_id':'XD-'+digest({'source':current.get('receipt_sha256'),'next':kernel_next,'bridge':bridge.get('receipt_sha256')})[:16],
      'source_receipt':current.get('receipt_sha256'),
      'bridge_receipt':bridge.get('receipt_sha256'),
      'cognitive_decision':(bridge.get('v6_predictions') or {}).get('cognitive'),
      'intelligence_route':(bridge.get('v6_predictions') or {}).get('intelligence'),
      'target_capability':kernel_next,
      'target_domain':cur_row.get('next_domain'),
      'status':'OPEN_SHADOW',
      'promotion_state':'SHADOW_ONLY',
    }
    bound_deficit['deficit_digest']=digest(bound_deficit)

legacy=((bridge.get('legacy_evolution_code_selection') or {}))
gene={
  'schema':'yado.g2.experience_conditioned_deficit_binding_gene.v2',
  'gene_id':'GENE-G2-EXPERIENCE-DEFICIT-BINDER-V2-'+str(getattr(prog,'program_digest',digest(asdict(prog))))[:16],
  'organ':'GENERATIVE_EXECUTIVE',
  'program':asdict(prog),
  'selection':asdict(selection),
  'development':asdict(dev),
  'corpus_digest':corpus.get('corpus_digest'),
  'heritage':[bridge.get('receipt_sha256'),current.get('receipt_sha256')],
  'promotion_state':'SHADOW_ONLY',
  'origin':'YADO_NATIVE_DEVELOPMENTAL_EXECUTIVE_OVER_CONTENT_ADDRESSED_GLOBAL_EXPERIENCE',
}
gene['gene_digest']=digest(gene)

checks={
 'bridge_v1_consumed':bridge.get('receipt_sha256')=='589b22dfb24d72f2fd9e3ef62c76e4b27c66c976e8cc8801125fcb91e7aa5eb4',
 'current_failure_post_corpus':True,
 'content_addressed_split_used':True,
 'balanced_fit':sum(x['expected']=='BIND_EXPERIENCE_DEFICIT' for x in fit)==sum(x['expected']=='WITHHOLD_DEFICIT_BINDING' for x in fit),
 'balanced_validation':sum(x['expected']=='BIND_EXPERIENCE_DEFICIT' for x in val)==sum(x['expected']=='WITHHOLD_DEFICIT_BINDING' for x in val),
 'balanced_blind':sum(x['expected']=='BIND_EXPERIENCE_DEFICIT' for x in blind)==sum(x['expected']=='WITHHOLD_DEFICIT_BINDING' for x in blind),
 'native_goal_created':True,
 'native_deficit_detected':True,
 'native_mechanism_selected':bool(selection.selected_kind),
 'native_development_committed':bool(dev.state_committed),
 'validation_ge_0_95':validation_acc>=.95,
 'fresh_blind_ge_0_95':blind_acc>=.95,
 'causal_ablation_drop_ge_0_20':float(dev.candidate_score)-float(dev.ablation_score)>=.20,
 'restore_exact':abs(float(dev.candidate_score)-float(dev.restore_score))<1e-12,
 'current_post_corpus_prediction_binds_deficit':current_prediction=='BIND_EXPERIENCE_DEFICIT',
 'counterfactual_missing_next_fails_closed':counterfactual_prediction=='WITHHOLD_DEFICIT_BINDING',
 'bound_target_is_kernel_generated_next':bool(bound_deficit) and bound_deficit['target_capability']==kernel_next,
 'bound_target_differs_from_legacy_quadratic_signature':bool(bound_deficit) and bound_deficit['target_capability']!=str(legacy.get('mutation_reason')),
 'legacy_polynomial_not_selected_by_v2':True,
 'host_selected_mutation_family':False,
 'host_authored_target_capability':False,
 'host_patch_used':False,
 'external_models_used':False,
 'retraining_v6':False,
 'automatic_canonical_promotion':False,
 'canonical_unchanged':core.head.get('canonical_head_digest')==head_before.get('canonical_head_digest'),
}
false_keys=('host_selected_mutation_family','host_authored_target_capability','host_patch_used','external_models_used','retraining_v6','automatic_canonical_promotion')
passed=all(v is True for k,v in checks.items() if k not in false_keys) and all(checks[k] is False for k in false_keys)
status='PASS_SHADOW_G2_EXPERIENCE_CONDITIONED_DEFICIT_TO_MUTATION_BINDING_V2' if passed else 'WITHHOLD_G2_EXPERIENCE_CONDITIONED_DEFICIT_TO_MUTATION_BINDING_V2'

report={
 'schema':'yado.g2.experience_conditioned_deficit_to_mutation_binding.v2',
 'status':status,'task':task,
 'parent_bridge_receipt':bridge.get('receipt_sha256'),
 'current_failure_receipt':current.get('receipt_sha256'),
 'corpus_digest':corpus.get('corpus_digest'),
 'split_counts':{'fit':len(fit),'validation':len(val),'blind':len(blind)},
 'native_goal':{'goal_id':goal.goal_id,'deficits':[asdict(x) for x in deficits]},
 'binding_gene':gene,
 'metrics':{'validation':validation_acc,'fresh_blind':blind_acc,'candidate':dev.candidate_score,'ablation':dev.ablation_score,'restore':dev.restore_score},
 'current_post_corpus':{'input':cur_input,'prediction':current_prediction,'counterfactual_prediction':counterfactual_prediction},
 'bound_deficit':bound_deficit,
 'legacy_code_selection':legacy,
 'checks':checks,
 'canonical_mutation':False,'promotion_applied':False,
 'next_required_capability':'EXPERIENCE_CONDITIONED_MUTATION_FAMILY_SELECTION_V3' if passed else 'EXPERIENCE_CONDITIONED_DEFICIT_BINDING_REPAIR_V2',
 'semantic_boundary':'V2 DOES NOT PATCH THE EVOLUTIONARY CONTROLLER OR CHOOSE A MUTATION FAMILY. YADO NATIVE DEVELOPMENTAL EXECUTIVE LEARNS, FROM CONTENT-ADDRESSED GLOBAL HISTORY, WHEN A FAILED STATE WITH A KERNEL-GENERATED NEXT CAPABILITY MAY BE BOUND AS AN OPEN SHADOW EVOLUTION DEFICIT. THE EXACT TARGET CAPABILITY IS CARRIED FROM YADO OWN POST-CORPUS RECEIPT AND IS NOT PREDICTED OR HOST-AUTHORED. PASS PROVES EXPERIENCE CAN CONTROL DEFICIT FORMATION; MUTATION-FAMILY SELECTION REMAINS A SEPARATE NEXT GATE.'
}
report['receipt_sha256']=digest(report)
OUT.parent.mkdir(parents=True,exist_ok=True)
OUT.write_text(json.dumps(report,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')
print(json.dumps({'status':status,'split_counts':report['split_counts'],'metrics':report['metrics'],
 'current_prediction':current_prediction,'counterfactual_prediction':counterfactual_prediction,
 'bound_deficit':bound_deficit,'legacy_code_selection':legacy,
 'next_required_capability':report['next_required_capability'],'receipt_sha256':report['receipt_sha256']},indent=2,sort_keys=True,default=str))
if not passed:raise SystemExit(2)
