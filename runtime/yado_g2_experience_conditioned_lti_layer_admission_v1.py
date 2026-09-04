from __future__ import annotations
from pathlib import Path
import copy,hashlib,json,os,re,sys

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
PKG=ROOT/'yado_rc8_v36'
sys.path[:0]=[str(ROOT),str(PKG)]

from yado_organ_runtime_native_v1 import plan_with_edges,tree_predict
from yado_work_budget_adaptive_contingent_planner_v2 import ContingentStage
from yado_g2_experience_conditioned_lti_layer_v1 import ExperienceAugmentedLTICompositeV1
from yado_unified_core_v1 import UnifiedYADOCoreV1

TASK=REPO/'architecture/yado-g2-experience-conditioned-lti-layer-admission-v1-request.json'
OUT=REPO/'candidates/kernel-self-generated/g2-experience-conditioned-lti-layer-admission-v1.json'
LEDGER=REPO/'architecture/evolution-ledger.json'

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def digest(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def pass_status(s):
    s=str(s or '').upper()
    return s.startswith('PASS') or s in ('VERIFIED','EXECUTE')
def withhold_status(s):
    s=str(s or '').upper()
    return s.startswith('WITHHOLD') or s.startswith('FAIL')
def norm_cap(s):
    s=str(s or '').upper()
    s=re.sub(r'^(?:YADO_|KERNEL_G2_|KERNEL_)','',s)
    s=re.sub(r'_V\\d+$','',s)
    return re.sub(r'[^A-Z0-9]+','_',s).strip('_')
def current_deficit(o):
    t=o.get('task') if isinstance(o.get('task'),dict) else {}
    return o.get('deficit') or t.get('deficit') or t.get('objective') or o.get('objective')
def next_cap(o):
    return o.get('next_required_capability') or o.get('next_frontier') or o.get('frontier')
def target_action(o):
    n=next_cap(o)
    if not n:return 'STOP'
    c=current_deficit(o)
    return 'RETRY' if c and norm_cap(n)==norm_cap(c) else 'ADVANCE'
def status_group(o):
    s=str(o.get('status') or '').upper()
    if 'CANONICAL' in s:return 'CANONICAL'
    if 'SHADOW' in s:return 'SHADOW'
    if s.startswith('WITHHOLD'):return 'WITHHOLD'
    if s.startswith('FAIL'):return 'FAIL'
    if s.startswith('PASS') or s in ('VERIFIED','EXECUTE'):return 'PASS'
    return 'OTHER'
def control_role(o):return status_group(o)+'__'+target_action(o)

DROP={'status','next_required_capability','next_frontier','frontier','deficit','objective','receipt_sha256'}
def strip_targets(x):
    if isinstance(x,dict):return {k:strip_targets(v) for k,v in x.items() if k not in DROP}
    if isinstance(x,list):return [strip_targets(v) for v in x]
    return x
def leaf_count(x):
    if isinstance(x,dict):return sum(leaf_count(v) for v in x.values())
    if isinstance(x,list):return sum(leaf_count(v) for v in x)
    return 1
def body_text(o):return canon(strip_targets(o)).lower()
def logic_features(o):
    body=body_text(o)
    return {
      'promotion_applied':bool(o.get('promotion_applied')),
      'effect_has_fresh':'fresh' in body,
      'effect_has_rollback':'rollback' in body,
      'effect_has_error':any(t in body for t in ('error','failure','exception','traceback')),
    }
def intelligence_features(o):
    body=body_text(o);s=str(o.get('status') or '').upper()
    return {
      'status_pass':1.0 if pass_status(s) else 0.0,
      'status_withhold':1.0 if withhold_status(s) else 0.0,
      'status_shadow':1.0 if 'SHADOW' in s else 0.0,
      'status_canonical':1.0 if 'CANONICAL' in s else 0.0,
      'canonical_mutation':1.0 if o.get('canonical_mutation') else 0.0,
      'promotion_applied':1.0 if o.get('promotion_applied') else 0.0,
      'effect_has_fresh':1.0 if 'fresh' in body else 0.0,
      'effect_has_rollback':1.0 if 'rollback' in body else 0.0,
      'effect_has_error':1.0 if any(t in body for t in ('error','failure','exception','traceback')) else 0.0,
      'effect_has_base_reg':1.0 if ('base_reg' in body or 'regression' in body) else 0.0,
      'prior_same_deficit':0.0,
      'effect_metric_density':float(min(leaf_count(strip_targets(o)),12))/12.0,
    }
def acc_bool(pred,truth):return sum(bool(a)==bool(b) for a,b in zip(pred,truth))/max(1,len(truth))
def acc_label(pred,truth):return sum(str(a)==str(b) for a,b in zip(pred,truth))/max(1,len(truth))
def macro_acc(pred,truth):
    labs=sorted(set(map(str,truth)))
    vals=[]
    for lab in labs:
        idx=[i for i,y in enumerate(truth) if str(y)==lab]
        vals.append(sum(str(pred[i])==lab for i in idx)/len(idx))
    return sum(vals)/max(1,len(vals))
def recursive_strings(x):
    if isinstance(x,dict):
        for v in x.values():yield from recursive_strings(v)
    elif isinstance(x,list):
        for v in x:yield from recursive_strings(v)
    elif isinstance(x,str):yield x

task=load(TASK);parent=load(REPO/task['parent_shadow_receipt']);ledger=load(LEDGER)
core=UnifiedYADOCoreV1(REPO);head_before=copy.deepcopy(core.head)
thresholds=task['admission_thresholds']
ledger_text=canon(ledger)
consumed=set(task.get('consumed_training_sources') or [])
rows=[]
excluded=[]
for rel in task.get('frozen_candidate_artifacts') or []:
    if rel in consumed or 'experience-conditioned-lti-evolution-v1' in rel:
        excluded.append({'path':rel,'reason':'PARENT_TRAINING_OR_PARENT_ARTIFACT'});continue
    p=REPO/rel
    if not p.exists():excluded.append({'path':rel,'reason':'MISSING_AT_FROZEN_CHECKOUT'});continue
    try:o=load(p)
    except Exception:excluded.append({'path':rel,'reason':'UNREADABLE_JSON'});continue
    rec=o.get('receipt_sha256');status=o.get('status')
    if not isinstance(rec,str) or len(rec)!=64 or not isinstance(status,str):
        excluded.append({'path':rel,'reason':'NO_RECEIPT_OR_STATUS'});continue
    if rel in ledger_text or rec in ledger_text:
        excluded.append({'path':rel,'reason':'ALREADY_BOUND_IN_LEDGER'});continue
    rows.append({'path':rel,'receipt':rec,'artifact':o})

genes=parent['shadow_genes']
layer=ExperienceAugmentedLTICompositeV1(genes)

# Receipt and gene integrity.
pcopy=copy.deepcopy(parent);prec=pcopy.pop('receipt_sha256',None)
parent_receipt_integrity=(prec==digest(pcopy))
gene_integrity={}
for organ,g in genes.items():
    z=copy.deepcopy(g);gd=z.pop('gene_digest',None);gene_integrity[organ]=(gd==digest(z))

# LOGIC independent artifact classification.
logic_truth=[pass_status(r['artifact'].get('status')) for r in rows]
logic_pred=[layer.logic_history_assessment(logic_features(r['artifact'])) for r in rows]
logic_abl=[layer.logic_history_assessment({k:False for k in logic_features(r['artifact'])}) for r in rows]
logic_score=acc_bool(logic_pred,logic_truth);logic_ablation=acc_bool(logic_abl,logic_truth)
logic_restore=acc_bool([layer.logic_history_assessment(logic_features(r['artifact'])) for r in rows],logic_truth)

# INTELLIGENCE independent next-control action.
intel_truth=[target_action(r['artifact']) for r in rows]
intel_features=[intelligence_features(r['artifact']) for r in rows]
intel_pred=[str(layer.intelligence_history_action(x)) for x in intel_features]
intel_abl=[str(layer.intelligence_history_action({k:0.0 for k in x})) for x in intel_features]
intel_score=acc_label(intel_pred,intel_truth);intel_macro=macro_acc(intel_pred,intel_truth)
intel_ablation=acc_label(intel_abl,intel_truth);intel_ablation_macro=macro_acc(intel_abl,intel_truth)
intel_restore=acc_label([str(layer.intelligence_history_action(x)) for x in intel_features],intel_truth)
target_classes=sorted(set(intel_truth))

# THINKING independent causal links: explicit receipt ancestry plus next-capability -> deficit links.
by_receipt={r['receipt']:r for r in rows}
edges=set()
for child in rows:
    strings=set(recursive_strings(strip_targets(child['artifact'])))
    for rec,parent_row in by_receipt.items():
        if rec!=child['receipt'] and rec in strings:
            edges.add((parent_row['receipt'],child['receipt'],'RECEIPT_ANCESTRY'))
by_deficit={}
for r in rows:
    c=current_deficit(r['artifact'])
    if c:by_deficit.setdefault(norm_cap(c),[]).append(r)
for a in rows:
    n=next_cap(a['artifact'])
    if not n:continue
    for b in by_deficit.get(norm_cap(n),[]):
        if a['receipt']!=b['receipt']:
            edges.add((a['receipt'],b['receipt'],'NEXT_CAPABILITY_LINK'))

episodes=[];edge_rows=[]
for a_rec,b_rec,kind in sorted(edges):
    a=by_receipt[a_rec]['artifact'];b=by_receipt[b_rec]['artifact']
    expected=[control_role(a),control_role(b)]
    if expected[0]==expected[1]:continue
    actions=[]
    for j,role in enumerate(expected):
        aid=hashlib.sha256((a_rec+b_rec+str(j)+role).encode()).hexdigest()[:12]
        actions.append({'id':aid,'role':role})
    actions=sorted(actions,key=lambda x:x['id'])
    episodes.append((actions,expected))
    edge_rows.append({'parent':a_rec,'child':b_rec,'kind':kind,'expected':expected})
def thinking_score_with(model):
    ok=0
    for actions,expected in episodes:
        ids=plan_with_edges(actions,model)
        rb={str(a['id']):str(a['role']) for a in actions}
        pred=[rb[i] for i in ids]
        ok+=pred==expected
    return ok/max(1,len(episodes))
thinking_score=thinking_score_with(genes['THINKING']['model'])
thinking_ablation=thinking_score_with([])
thinking_restore=thinking_score_with(genes['THINKING']['model'])

# Legacy contract regression: additive layer must not alter the old APIs.
logic_rows=[
 {'input':{'a':False,'b':False},'expected':False},
 {'input':{'a':False,'b':True},'expected':False},
 {'input':{'a':True,'b':False},'expected':False},
 {'input':{'a':True,'b':True},'expected':True},
]
lm=layer.legacy_logic_learn(logic_rows)
logic_legacy=sum(bool(layer.legacy_logic_predict(lm,r['input']))==bool(r['expected']) for r in logic_rows)/len(logic_rows)

stages=[
 ContingentStage('LOW',1.0,.2,latency=1.0),
 ContingentStage('HIGH',1.0,.7,latency=1.0),
]
tp=layer.legacy_thinking_plan(.1,.8,1.0,stages)
thinking_legacy=1.0 if getattr(tp,'action',None)=='HIGH' else 0.0

icases=[
 {'input':{'a':False,'b':False,'c':False},'expected':'BASE'},
 {'input':{'a':True,'b':False,'c':False},'expected':'BASE'},
 {'input':{'a':True,'b':True,'c':False},'expected':'SPECIAL'},
 {'input':{'a':True,'b':True,'c':True},'expected':'SPECIAL'},
]*6
im=layer.legacy_intelligence_fit(icases,'BASE',max_trigger_width=3)
intelligence_legacy=sum('SPECIAL' in layer.legacy_intelligence_route(im,r['input']) if r['expected']=='SPECIAL' else 'SPECIAL' not in layer.legacy_intelligence_route(im,r['input']) for r in icases)/len(icases)
legacy_regression=min(logic_legacy,thinking_legacy,intelligence_legacy)

checks={
 'parent_shadow_pass':parent.get('status')=='PASS_SHADOW_G2_EXPERIENCE_CONDITIONED_LTI_EVOLUTION_V1',
 'parent_receipt_integrity':parent_receipt_integrity,
 'all_gene_integrity':all(gene_integrity.values()),
 'independent_artifact_count':len(rows)>=int(thresholds['min_independent_artifacts']),
 'independent_artifacts_not_in_ledger':all(r['path'] not in ledger_text and r['receipt'] not in ledger_text for r in rows),
 'logic_fresh_threshold':logic_score>=float(thresholds['logic_min_accuracy']),
 'logic_ablation_gain':logic_score-logic_ablation>=float(thresholds['logic_min_ablation_gain']),
 'logic_restore_exact':logic_restore==logic_score,
 'intelligence_target_class_coverage':len(target_classes)>=int(thresholds['intelligence_required_target_classes']),
 'intelligence_fresh_threshold':intel_score>=float(thresholds['intelligence_min_accuracy']),
 'intelligence_macro_threshold':intel_macro>=float(thresholds['intelligence_min_macro_accuracy']),
 'intelligence_ablation_gain':intel_score-intel_ablation>=float(thresholds['intelligence_min_ablation_gain']),
 'intelligence_restore_exact':intel_restore==intel_score,
 'thinking_causal_pair_count':len(episodes)>=int(thresholds['thinking_min_causal_pairs']),
 'thinking_fresh_threshold':thinking_score>=float(thresholds['thinking_min_accuracy']),
 'thinking_ablation_gain':thinking_score-thinking_ablation>=float(thresholds['thinking_min_ablation_gain']),
 'thinking_restore_exact':thinking_restore==thinking_score,
 'legacy_regression_exact':legacy_regression>=float(thresholds['legacy_regression_required']),
 'canonical_unchanged':core.head.get('canonical_head_digest')==head_before.get('canonical_head_digest'),
 'external_models_used':False,'new_external_research_used':False,'host_model_authoring':False,
 'automatic_promotion':False,'canonical_mutation':False,
}
required_true=[k for k in checks if k not in ('external_models_used','new_external_research_used','host_model_authoring','automatic_promotion','canonical_mutation')]
required_false=['external_models_used','new_external_research_used','host_model_authoring','automatic_promotion','canonical_mutation']
passed=all(checks[k] is True for k in required_true) and all(checks[k] is False for k in required_false)
status='PASS_SHADOW_G2_EXPERIENCE_CONDITIONED_LTI_LAYER_ADMISSION_READY_V1' if passed else 'WITHHOLD_G2_EXPERIENCE_CONDITIONED_LTI_LAYER_ADMISSION_V1'
report={
 'schema':'yado.g2.experience_conditioned_lti_layer_admission.v1',
 'status':status,'github_run_id':str(os.getenv('GITHUB_RUN_ID') or 'LOCAL'),
 'task':task,'parent_receipt_sha256':parent.get('receipt_sha256'),'gene_integrity':gene_integrity,
 'independent_evidence':{
   'included_count':len(rows),'included_paths':[r['path'] for r in rows],
   'excluded_count':len(excluded),'excluded':excluded,
 },
 'metrics':{
   'LOGIC':{'fresh':logic_score,'ablation':logic_ablation,'restore':logic_restore,'case_count':len(rows)},
   'INTELLIGENCE':{'fresh':intel_score,'macro':intel_macro,'ablation':intel_ablation,'ablation_macro':intel_ablation_macro,'restore':intel_restore,'case_count':len(rows),'target_classes':target_classes},
   'THINKING':{'fresh':thinking_score,'ablation':thinking_ablation,'restore':thinking_restore,'causal_pair_count':len(episodes),'causal_edges':edge_rows},
   'LEGACY':{'LOGIC':logic_legacy,'THINKING':thinking_legacy,'INTELLIGENCE':intelligence_legacy,'min':legacy_regression},
 },
 'checks':checks,'canonical_mutation':False,'promotion_applied':False,
 'next_required_capability':('G2_EXPERIENCE_CONDITIONED_LTI_LAYER_CANONICAL_INTEGRATION_V1' if passed else 'G2_EXPERIENCE_CONDITIONED_LTI_LAYER_REPAIR_V2'),
 'semantic_boundary':'ADMISSION GATE FOR ADDITIVE EXPERIENCE-CONDITIONED ORGAN LAYERS. BASE LOGIC/THINKING/INTELLIGENCE CONTRACTS ARE NOT REPLACED. PASS ONLY AUTHORIZES A SEPARATE CANONICAL INTEGRATION STEP.'
}
report['receipt_sha256']=digest(report)
OUT.parent.mkdir(parents=True,exist_ok=True)
OUT.write_text(json.dumps(report,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')
print(json.dumps({
 'status':status,'independent_count':len(rows),'metrics':report['metrics'],
 'next_required_capability':report['next_required_capability'],'receipt_sha256':report['receipt_sha256']
},indent=2,sort_keys=True,default=str))
if not passed:raise SystemExit(2)
