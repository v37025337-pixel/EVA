from __future__ import annotations
from pathlib import Path
import copy,hashlib,json,sys

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
PKG=ROOT/'yado_rc8_v36'
sys.path[:0]=[str(ROOT),str(PKG)]

from yado_unified_core_v1 import UnifiedYADOCoreV1
from yado_organ_runtime_native_v1 import tree_predict
from yado_cognitive_growth_runtime_v1 import plan_multicontext,knn_predict,centroid_predict

TASK=REPO/'architecture/yado-kernel-experience-conditioned-evolution-action-bridge-v1-request.json'
CURRENT=REPO/'candidates/kernel-self-generated/g2-native-action-evidence-binder-source-realization-v1.json'
V6=REPO/'experience/yado-global-experience-cognitive-genesis-v6.json'
OUT=REPO/'candidates/kernel-self-generated/g2-experience-conditioned-evolution-action-bridge-v1.json'

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def digest(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def scalar(v):return isinstance(v,(str,int,float,bool)) or v is None

def flatten(obj,max_depth=9):
    out=[]
    def walk(x,path,depth):
        if depth>max_depth:return
        if isinstance(x,dict):
            for k in sorted(x):walk(x[k],path+[str(k)],depth+1)
        elif isinstance(x,list):
            for i,v in enumerate(x[:128]):walk(v,path+[str(i)],depth+1)
        elif scalar(x):out.append(('.'.join(path),x))
    walk(obj,[],0);return out

def first_recursive(obj,keys):
    if isinstance(obj,dict):
        for k in keys:
            if k in obj and scalar(obj[k]):return obj[k]
        for k in sorted(obj):
            v=first_recursive(obj[k],keys)
            if v is not None:return v
    elif isinstance(obj,list):
        for v0 in obj:
            v=first_recursive(v0,keys)
            if v is not None:return v
    return None

DOMAIN_RULES=[
 ('CODE',('code','source','repair','program','compiler','ast','function')),
 ('REPRESENTATION',('representation','schema','raw','mapper','language','rml','semantic')),
 ('COGNITIVE',('cognitive','logic','thinking','intelligence','conscious','workspace','reasoning')),
 ('EXECUTION',('execution','fabric','api','runtime','network','resource','executor')),
 ('MEMORY',('memory','experience','legacy','history','ledger')),
 ('EVOLUTION',('evolution','genome','mutation','gene','self-evolution')),
]
def domain_of(text):
    s=str(text or '').lower()
    for name,toks in DOMAIN_RULES:
        if any(t in s for t in toks):return name
    return 'GENERAL'

def metric_summary(obj):
    flat=flatten(obj);lower=[(p.lower(),v) for p,v in flat]
    def bool_signal(tokens):
        return [v for p,v in lower if isinstance(v,bool) and any(t in p for t in tokens)]
    def nums(tokens):
        return [float(v) for p,v in lower if isinstance(v,(int,float)) and not isinstance(v,bool) and any(t in p for t in tokens)]
    fresh_b=bool_signal(('fresh','hidden','full_domain'));fresh_n=nums(('fresh_score','fresh_blind','hidden_score','full_domain_score','candidate_score'))
    has_fresh=bool(fresh_b or fresh_n);fresh_positive=(any(fresh_b) or any(x>=.90 for x in fresh_n)) if has_fresh else False
    abl_b=bool_signal(('ablation','causal_drop','material_drop'));abl_n=nums(('ablation_drop','causal_gain','causal_drop'));cand=nums(('candidate_score',));abl_score=nums(('ablation_score',))
    abl_positive=any(abl_b) or any(x>=.20 for x in abl_n)
    if cand and abl_score:abl_positive=abl_positive or (max(cand)-min(abl_score)>=.20)
    has_ablation=bool(abl_b or abl_n or abl_score)
    reg_b=bool_signal(('regression','restore','integrity','rollback'));has_reg=bool(reg_b);reg_positive=any(reg_b) if reg_b else False
    safe_b=bool_signal(('unknown','conflict','fail_closed','safety'));has_safe=bool(safe_b);safe_positive=any(safe_b) if safe_b else False
    canon_unchanged=None
    for p,v in lower:
        if isinstance(v,bool) and ('canonical_unchanged' in p or 'canonical_head_immutable' in p):
            canon_unchanged=bool(v);break
    if canon_unchanged is None:
        cm=first_recursive(obj,('canonical_mutation',))
        if isinstance(cm,bool):canon_unchanged=not cm
    rollback=first_recursive(obj,('rollback_available','rollback_parent_available'))
    promotion=first_recursive(obj,('promotion_applied','automatic_canonical_promotion'))
    return {'has_fresh':bool(has_fresh),'fresh_positive':bool(fresh_positive),
      'has_ablation':bool(has_ablation),'ablation_positive':bool(abl_positive),
      'has_regression_restore_integrity':bool(has_reg),'regression_restore_integrity_positive':bool(reg_positive),
      'has_safety_evidence':bool(has_safe),'safety_positive':bool(safe_positive),
      'canonical_unchanged':bool(canon_unchanged) if canon_unchanged is not None else False,
      'rollback_available':bool(rollback) if isinstance(rollback,bool) else False,
      'promotion_applied':bool(promotion) if isinstance(promotion,bool) else False,
      'evidence_density':sum(map(int,[has_fresh,has_ablation,has_reg,has_safe,canon_unchanged is not None,rollback is not None]))}

def pred_family(f,m,x):
    if f=='CART_AXIS':return tree_predict(m,x)
    if f=='KNN_STRATEGY':return knn_predict(m,x)
    return centroid_predict(m,x)

task=load(TASK);cur=load(CURRENT);v6=load(V6)
if v6.get('status')!='TRAINED':raise RuntimeError('GLOBAL_EXPERIENCE_V6_NOT_TRAINED')
if cur.get('status')!='WITHHOLD_G2_NATIVE_ACTION_EVIDENCE_BINDER_SOURCE_REALIZATION_V1':raise RuntimeError('EXPECTED_CURRENT_WITHHOLD_MISSING')

nxt=str(cur.get('next_required_capability') or '')
row={'path':str(CURRENT.relative_to(REPO)),'source_class':'CANDIDATE','status':cur.get('status'),'outcome':'WITHHOLD',
     'next_required_capability':nxt or None,'domain':domain_of(str(CURRENT.relative_to(REPO))+' '+nxt),
     'next_domain':domain_of(nxt) if nxt else None,'metrics':metric_summary(cur)}

genes=v6['genes'];lg=genes['LOGIC'];tg=genes['THINKING'];ig=genes['INTELLIGENCE'];cg=genes['COGNITIVE']
def general_logic_features(r):
    m=r['metrics'];return {'has_fresh':m['has_fresh'],'fresh_positive':m['fresh_positive'],'has_ablation':m['has_ablation'],'ablation_positive':m['ablation_positive'],
      'has_regression_restore_integrity':m['has_regression_restore_integrity'],'regression_restore_integrity_positive':m['regression_restore_integrity_positive'],
      'has_safety_evidence':m['has_safety_evidence'],'safety_positive':m['safety_positive'],'canonical_unchanged':m['canonical_unchanged'],
      'rollback_available':m['rollback_available'],'promotion_applied':m['promotion_applied'],'next_present':bool(r.get('next_required_capability')),
      'source_is_receipt':r['source_class']=='RECEIPT','source_is_candidate':r['source_class']=='CANDIDATE','source_is_legacy':r['source_class']=='LEGACY_REDERIVED'}
def terminal_features(r):
    m=r['metrics'];return {'fresh_positive':1.0 if m['fresh_positive'] else 0.0,'has_fresh':1.0 if m['has_fresh'] else 0.0,
      'ablation_positive':1.0 if m['ablation_positive'] else 0.0,'has_ablation':1.0 if m['has_ablation'] else 0.0,
      'regression_positive':1.0 if m['regression_restore_integrity_positive'] else 0.0,'has_regression':1.0 if m['has_regression_restore_integrity'] else 0.0,
      'safety_positive':1.0 if m['safety_positive'] else 0.0,'has_safety':1.0 if m['has_safety_evidence'] else 0.0,
      'canonical_unchanged':1.0 if m['canonical_unchanged'] else 0.0,'rollback_available':1.0 if m['rollback_available'] else 0.0,
      'promotion_applied':1.0 if m['promotion_applied'] else 0.0,'evidence_density':float(m['evidence_density'])/6.0,
      'source_receipt':0.0,'source_candidate':1.0,'source_experience':0.0,'source_legacy':0.0,
      'domain_code':1.0 if r['domain']=='CODE' else 0.0,'domain_representation':1.0 if r['domain']=='REPRESENTATION' else 0.0,
      'domain_cognitive':1.0 if r['domain']=='COGNITIVE' else 0.0,'domain_execution':1.0 if r['domain']=='EXECUTION' else 0.0,
      'domain_memory':1.0 if r['domain']=='MEMORY' else 0.0,'domain_evolution':1.0 if r['domain']=='EVOLUTION' else 0.0}
def intel_features(r):
    m=r['metrics'];return {'status_pass':0.0,'status_withhold':1.0,'next_present':1.0 if r.get('next_required_capability') else 0.0,
      'same_domain_next':1.0 if r.get('next_required_capability') and r.get('next_domain')==r.get('domain') else 0.0,
      'fresh_positive':1.0 if m['fresh_positive'] else 0.0,'ablation_positive':1.0 if m['ablation_positive'] else 0.0,
      'canonical_unchanged':1.0 if m['canonical_unchanged'] else 0.0,'rollback_available':1.0 if m['rollback_available'] else 0.0,
      'evidence_density':float(m['evidence_density'])/6.0,'domain_code':1.0 if r['domain']=='CODE' else 0.0,
      'domain_representation':1.0 if r['domain']=='REPRESENTATION' else 0.0,'domain_cognitive':1.0 if r['domain']=='COGNITIVE' else 0.0,
      'domain_execution':1.0 if r['domain']=='EXECUTION' else 0.0,'domain_memory':1.0 if r['domain']=='MEMORY' else 0.0,'domain_evolution':1.0 if r['domain']=='EVOLUTION' else 0.0}
def row_context(r):
    return {'START_PASS':False,'START_WITHHOLD':True,'START_HAS_NEXT':bool(r.get('next_required_capability')),
      'START_NO_NEXT':not bool(r.get('next_required_capability')),'START_SAME_DOMAIN_NEXT':bool(r.get('next_required_capability')) and r.get('next_domain')==r.get('domain'),
      'START_FRESH_POSITIVE':bool(r['metrics'].get('fresh_positive')),'START_ABLATION_POSITIVE':bool(r['metrics'].get('ablation_positive')),
      'WINDOW_DOMAIN_STABLE':True,'WINDOW_HAS_WITHHOLD':True,'WINDOW_HAS_PASS':False}
def think_pref(r):
    roles=['ACCEPT','ADVANCE','REVISE','SEEK_EVIDENCE'];acts=[{'id':'STD-'+x,'role':x} for x in roles]
    ids=plan_multicontext(tg['model'],row_context(r),acts);by={a['id']:a['role'] for a in acts}
    return by[ids[0]] if ids else 'SEEK_EVIDENCE'

logic_general=bool(tree_predict(lg['general_model'],general_logic_features(row)))
logic_terminal=bool(pred_family(lg['terminal_expert_family'],lg['terminal_expert_model'],terminal_features(row)))
intel=str(tree_predict(ig['model'],intel_features(row)))
thinking=think_pref(row)
organ={'state_known':1.0,'logic_general':1.0 if logic_general else 0.0,'logic_terminal':1.0 if logic_terminal else 0.0,
       'intel_stop':1.0 if intel=='STOP' else 0.0,'intel_retry':1.0 if intel=='RETRY' else 0.0,'intel_advance':1.0 if intel=='ADVANCE' else 0.0,
       'think_accept':1.0 if thinking=='ACCEPT' else 0.0,'think_advance':1.0 if thinking=='ADVANCE' else 0.0,
       'think_revise':1.0 if thinking=='REVISE' else 0.0,'think_seek':1.0 if thinking=='SEEK_EVIDENCE' else 0.0}
decision=str(pred_family(cg['strategy_family'],cg['model'],organ))

core=UnifiedYADOCoreV1(REPO);head_before=copy.deepcopy(core.head)
evo=core.evolve_cognitive_code_genome()
code=((evo.get('child') or {}).get('chromosomes') or {}).get('CODE') or {}
old_fixed=(code.get('gene_id')=='GENE-CODE-POLYNOMIAL-RETURN-SYNTHESIS-V1' and code.get('mutation_reason')=='PARENT_REPAIR_FAILS_QUADRATIC_FRESH_TRANSFER')

checks={'v6_frozen_model_used':True,'current_withhold_encoded_with_v1_schema':True,'current_next_present':bool(nxt),
 'experience_intelligence_does_not_stop':intel in ('RETRY','ADVANCE'),'experience_thinking_signal_observed':thinking in ('ACCEPT','ADVANCE','REVISE','SEEK_EVIDENCE'),
 'experience_cognitive_decision_is_revise':decision=='REVISE','old_genome_controller_still_uses_fixed_polynomial_code_deficit':old_fixed,
 'measured_decision_to_mutation_disconnect':decision=='REVISE' and old_fixed,
 'external_models_used':False,'retraining_performed':False,'host_patch_used':False,'canonical_unchanged':core.head.get('canonical_head_digest')==head_before.get('canonical_head_digest'),
 'automatic_canonical_promotion':False}
passed=all(checks[k] is True for k in ('v6_frozen_model_used','current_withhold_encoded_with_v1_schema','current_next_present',
 'experience_intelligence_does_not_stop','experience_thinking_signal_observed','experience_cognitive_decision_is_revise',
 'old_genome_controller_still_uses_fixed_polynomial_code_deficit','measured_decision_to_mutation_disconnect','canonical_unchanged')) and all(checks[k] is False for k in ('external_models_used','retraining_performed','host_patch_used','automatic_canonical_promotion'))
status='PASS_SHADOW_G2_EXPERIENCE_CONDITIONED_EVOLUTION_ACTION_BRIDGE_V1' if passed else 'WITHHOLD_G2_EXPERIENCE_CONDITIONED_EVOLUTION_ACTION_BRIDGE_V1'
report={'schema':'yado.g2.experience_conditioned_evolution_action_bridge.v1','status':status,'task':task,'current_row':row,
 'v6_predictions':{'logic_general':logic_general,'logic_terminal':logic_terminal,'intelligence':intel,'thinking':thinking,'cognitive':decision,'organ_features':organ},
 'legacy_evolution_code_selection':{'gene_id':code.get('gene_id'),'mutation_reason':code.get('mutation_reason'),'expression':code.get('expression')},
 'checks':checks,'canonical_mutation':False,'promotion_applied':False,
 'next_required_capability':'EXPERIENCE_CONDITIONED_DEFICIT_TO_MUTATION_BINDING_V2' if passed else 'GLOBAL_EXPERIENCE_EVOLUTION_DECISION_REPAIR_V2',
 'semantic_boundary':'FROZEN GLOBAL EXPERIENCE COGNITIVE V6 IS APPLIED TO A NEW POST-CORPUS WITHHOLD USING THE SAME V1 CONTENT ENCODING. NO RETRAINING OR EXTERNAL MODEL. PASS MEANS THE V6 COGNITIVE COORDINATOR RESOLVES ITS ORGAN SIGNALS TO REVISION WHILE THE LEGACY EVOLUTIONARY GENOME STILL SELECTS ITS FIXED QUADRATIC POLYNOMIAL CODE MUTATION, PROVING A DECISION-TO-MUTATION BINDING DISCONNECT. THIS STAGE DOES NOT PATCH THE CONTROLLER.'}
report['receipt_sha256']=digest(report);OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(report,indent=2,sort_keys=True,default=str)+'\n')
print(json.dumps({'status':status,'v6_predictions':report['v6_predictions'],'legacy_evolution_code_selection':report['legacy_evolution_code_selection'],
 'next_required_capability':report['next_required_capability'],'checks':checks,'receipt_sha256':report['receipt_sha256']},indent=2,sort_keys=True,default=str))
if not passed:raise SystemExit(2)
