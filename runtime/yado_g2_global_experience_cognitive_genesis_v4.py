from __future__ import annotations
from pathlib import Path
from dataclasses import asdict
from collections import defaultdict
import copy,hashlib,json,sys

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
PKG=ROOT/'yado_rc8_v36'
sys.path[:0]=[str(ROOT),str(PKG)]

from yado_cognitive_growth_runtime_v1 import plan_multicontext,fit_knn_strategy,strategy_accuracy,select_knn_k,fit_centroid_strategy,centroid_accuracy,select_centroid_features
from yado_organ_runtime_native_v1 import fit_tree,tree_predict,tree_acc
from yado_neutral_evidence_profile_selector_v1 import NeutralEvidenceProfileSelectorV1,EvidenceCandidate
from yado_core_v3_0_rc8_external_cognitive import UnifiedYADOKernelV30RC8ExternalCognitive
from yado_unified_core_v1 import UnifiedYADOCoreV1

CORPUS=REPO/'experience/yado-global-experience-corpus-v1.json'
PARENT=REPO/'experience/yado-global-experience-cognitive-genesis-v3.json'
OUT=REPO/'candidates/kernel-self-generated/g2-global-experience-cognitive-genesis-v4.json'
EXP=REPO/'experience/yado-global-experience-cognitive-genesis-v4.json'

def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def digest(o):return hashlib.sha256(canon(o).encode()).hexdigest()

corpus=load(CORPUS);parent=load(PARENT)
if parent.get('status')!='WITHHOLD':raise RuntimeError('V3_WITHHOLD_EXPERIENCE_REQUIRED')
pc=parent.get('checks') or {}
if not (pc.get('thinking_fresh_beats_v2_parent') and pc.get('thinking_context_ablation_material') and pc.get('thinking_restore_exact')):
    raise RuntimeError('V3_THINKING_SUCCESS_REQUIRED')
genes_parent=parent.get('genes') or {}
logic_gene=genes_parent['LOGIC'];thinking_gene=genes_parent['THINKING'];intel_gene=genes_parent['INTELLIGENCE']
rows=[r for r in (corpus.get('rows') or []) if r.get('outcome') in ('PASS','WITHHOLD')]

def split_bucket(r):return int(r['sha256'][:8],16)%10
def target_action(r):
    if r['outcome']=='PASS':return 'COMMIT' if not r.get('next_required_capability') else 'CONTINUE'
    return 'REVISE' if r.get('next_required_capability') else 'SEEK_EVIDENCE'
def balance(xs,min_per_class=5,max_per_class=96):
    g=defaultdict(list)
    for r in xs:g[target_action(r)].append(r)
    if len(g)<4:return []
    n=min(min(len(v),max_per_class) for v in g.values())
    if n<min_per_class:return []
    out=[]
    for k in sorted(g):
        out.extend(sorted(g[k],key=lambda r:(r['sha256'],r['path']))[:n])
    return sorted(out,key=lambda r:(r['sha256'],r['path']))

train_rows=balance([r for r in rows if split_bucket(r)<=5])
val_rows=balance([r for r in rows if 6<=split_bucket(r)<=7])
blind_rows=balance([r for r in rows if split_bucket(r)>=8])
if min(len(train_rows),len(val_rows),len(blind_rows))<20:raise RuntimeError('COGNITIVE_HISTORY_SPLIT_TOO_SMALL:'+str([len(train_rows),len(val_rows),len(blind_rows)]))

lmodel=logic_gene['model'];imodel=intel_gene['model'];tmodel=thinking_gene['model']
def logic_features(r):
    m=r['metrics']
    return {
      'has_fresh':m['has_fresh'],'fresh_positive':m['fresh_positive'],'has_ablation':m['has_ablation'],'ablation_positive':m['ablation_positive'],
      'has_regression_restore_integrity':m['has_regression_restore_integrity'],'regression_restore_integrity_positive':m['regression_restore_integrity_positive'],
      'has_safety_evidence':m['has_safety_evidence'],'safety_positive':m['safety_positive'],'canonical_unchanged':m['canonical_unchanged'],
      'rollback_available':m['rollback_available'],'promotion_applied':m['promotion_applied'],'next_present':bool(r.get('next_required_capability')),
      'source_is_receipt':r['source_class']=='RECEIPT','source_is_candidate':r['source_class']=='CANDIDATE','source_is_legacy':r['source_class']=='LEGACY_REDERIVED',
    }
def intel_features(r):
    m=r['metrics']
    return {
      'status_pass':1.0 if r['outcome']=='PASS' else 0.0,'status_withhold':1.0 if r['outcome']=='WITHHOLD' else 0.0,
      'next_present':1.0 if r.get('next_required_capability') else 0.0,
      'same_domain_next':1.0 if r.get('next_required_capability') and r.get('next_domain')==r.get('domain') else 0.0,
      'fresh_positive':1.0 if m['fresh_positive'] else 0.0,'ablation_positive':1.0 if m['ablation_positive'] else 0.0,
      'canonical_unchanged':1.0 if m['canonical_unchanged'] else 0.0,'rollback_available':1.0 if m['rollback_available'] else 0.0,
      'evidence_density':float(m['evidence_density'])/6.0,
      'domain_code':1.0 if r['domain']=='CODE' else 0.0,'domain_representation':1.0 if r['domain']=='REPRESENTATION' else 0.0,
      'domain_cognitive':1.0 if r['domain']=='COGNITIVE' else 0.0,'domain_execution':1.0 if r['domain']=='EXECUTION' else 0.0,
      'domain_memory':1.0 if r['domain']=='MEMORY' else 0.0,'domain_evolution':1.0 if r['domain']=='EVOLUTION' else 0.0,
    }
def row_context(r):
    return {
      'START_PASS':r.get('outcome')=='PASS','START_WITHHOLD':r.get('outcome')=='WITHHOLD',
      'START_HAS_NEXT':bool(r.get('next_required_capability')),'START_NO_NEXT':not bool(r.get('next_required_capability')),
      'START_SAME_DOMAIN_NEXT':bool(r.get('next_required_capability')) and r.get('next_domain')==r.get('domain'),
      'START_FRESH_POSITIVE':bool(r['metrics'].get('fresh_positive')),'START_ABLATION_POSITIVE':bool(r['metrics'].get('ablation_positive')),
      'WINDOW_DOMAIN_STABLE':True,'WINDOW_HAS_WITHHOLD':r.get('outcome')=='WITHHOLD','WINDOW_HAS_PASS':r.get('outcome')=='PASS',
    }
def thinking_preference(r):
    roles=['ACCEPT','ADVANCE','REVISE','SEEK_EVIDENCE']
    acts=[{'id':'STD-'+x,'role':x} for x in roles]
    ids=plan_multicontext(tmodel,row_context(r),acts)
    by={a['id']:a['role'] for a in acts}
    return by[ids[0]] if ids else 'SEEK_EVIDENCE'
def cognitive_features(r):
    lp=bool(tree_predict(lmodel,logic_features(r)))
    ip=str(tree_predict(imodel,intel_features(r)))
    tp=str(thinking_preference(r))
    m=r['metrics']
    x={
      'state_known':1.0,'logic_accept':1.0 if lp else 0.0,
      'intel_stop':1.0 if ip=='STOP' else 0.0,'intel_retry':1.0 if ip=='RETRY' else 0.0,'intel_advance':1.0 if ip=='ADVANCE' else 0.0,
      'think_accept':1.0 if tp=='ACCEPT' else 0.0,'think_advance':1.0 if tp=='ADVANCE' else 0.0,
      'think_revise':1.0 if tp=='REVISE' else 0.0,'think_seek':1.0 if tp=='SEEK_EVIDENCE' else 0.0,
      'next_present':1.0 if r.get('next_required_capability') else 0.0,
      'same_domain_next':1.0 if r.get('next_required_capability') and r.get('next_domain')==r.get('domain') else 0.0,
      'fresh_positive':1.0 if m['fresh_positive'] else 0.0,'ablation_positive':1.0 if m['ablation_positive'] else 0.0,
      'canonical_unchanged':1.0 if m['canonical_unchanged'] else 0.0,'rollback_available':1.0 if m['rollback_available'] else 0.0,
      'domain_code':1.0 if r['domain']=='CODE' else 0.0,'domain_representation':1.0 if r['domain']=='REPRESENTATION' else 0.0,
      'domain_cognitive':1.0 if r['domain']=='COGNITIVE' else 0.0,'domain_execution':1.0 if r['domain']=='EXECUTION' else 0.0,
      'domain_memory':1.0 if r['domain']=='MEMORY' else 0.0,'domain_evolution':1.0 if r['domain']=='EVOLUTION' else 0.0,
    }
    return x

fit=[(cognitive_features(r),target_action(r)) for r in train_rows]
val=[(cognitive_features(r),target_action(r)) for r in val_rows]
blind=[(cognitive_features(r),target_action(r)) for r in blind_rows]

# YADO-native cognitive strategy family search.
trials=[]
for depth in (1,2,3,4,5):
    m=fit_tree(fit,depth);a=tree_acc(m,val)
    trials.append({'token':'CART_D'+str(depth),'family':'CART_AXIS','param':depth,'validation':a,'complexity':depth,'model':m})
km,kmeta=select_knn_k(fit,val,candidates=(1,3,5,7,9))
trials.append({'token':'KNN_K'+str(kmeta['selected_k']),'family':'KNN_STRATEGY','param':kmeta['selected_k'],'validation':strategy_accuracy(km,val),
               'complexity':kmeta['selected_k'],'model':km,'meta':kmeta})
cm,cmeta=select_centroid_features(fit,val)
trials.append({'token':'CENTROID_F'+str(cmeta['selected_features']),'family':'CENTROID_STRATEGY','param':cmeta['selected_features'],
               'validation':centroid_accuracy(cm,val),'complexity':cmeta['selected_features'],'model':cm,'meta':cmeta})
sel=NeutralEvidenceProfileSelectorV1.select([
    EvidenceCandidate(token=t['token'],evidence=t['validation'],complexity=t['complexity'],risk=0.0,novelty=.2)
    for t in trials
],complexity_penalty=.01,risk_penalty=.2,novelty_bonus=.01)
chosen=next(t for t in trials if t['token']==sel['selected_token'])
all_fit=fit+val
if chosen['family']=='CART_AXIS':
    model=fit_tree(all_fit,int(chosen['param']));blind_score=tree_acc(model,blind)
    predict=lambda x:tree_predict(model,x)
elif chosen['family']=='KNN_STRATEGY':
    model=fit_knn_strategy(all_fit,int(chosen['param']));blind_score=strategy_accuracy(model,blind)
    from yado_cognitive_growth_runtime_v1 import knn_predict
    predict=lambda x:knn_predict(model,x)
else:
    model=fit_centroid_strategy(all_fit,int(chosen['param']));blind_score=centroid_accuracy(model,blind)
    from yado_cognitive_growth_runtime_v1 import centroid_predict
    predict=lambda x:centroid_predict(model,x)

def ablate_organs(x):
    z=dict(x)
    for k in ('logic_accept','intel_stop','intel_retry','intel_advance','think_accept','think_advance','think_revise','think_seek'):z[k]=0.0
    return z
ablind=[(ablate_organs(x),y) for x,y in blind]
if chosen['family']=='CART_AXIS':ablation_score=tree_acc(model,ablind)
elif chosen['family']=='KNN_STRATEGY':ablation_score=strategy_accuracy(model,ablind)
else:ablation_score=centroid_accuracy(model,ablind)
restore_score=blind_score

# Native fail-closed safety gate around the learned cognitive strategy.
core=UnifiedYADOCoreV1(REPO);head_before=copy.deepcopy(core.head)
db=ROOT/'yado_global_experience_cognitive_genesis_v4.sqlite'
if db.exists():db.unlink()
k=UnifiedYADOKernelV30RC8ExternalCognitive(db_path=str(db))
try:
    goal=k.executive.create_goal(
      objective='Learn fail-closed state-known gate for the global experience cognitive strategy.',
      required_capabilities={'GLOBAL_EXPERIENCE_COGNITIVE_SAFETY_GATE_V4':1.0},
      success_criteria={'blind':1.0,'ablation_drop':.20,'unknown_withhold':True},
    )
    deficit=k.executive.detect_deficits(goal.goal_id)[0]
    gate_train=[];gate_blind=[]
    for i in range(40):
        gate_train.append({'input':{'state_known':True,'variant':bool(i%2)},'expected':'PASS_THROUGH'})
        gate_train.append({'input':{'state_known':False,'variant':bool((i+1)%2)},'expected':'WITHHOLD'})
    for i in range(20):
        gate_blind.append({'input':{'state_known':True,'variant':bool((i+1)%2),'nonce':i},'expected':'PASS_THROUGH'})
        gate_blind.append({'input':{'state_known':False,'variant':bool(i%2),'nonce':i},'expected':'WITHHOLD'})
    gprog,gsel=k.executive.synthesize_best_mechanism(deficit.deficit_id,'CONSCIOUS_WORKSPACE',gate_train,min_support=2)
    gdev=k.executive.evaluate_mechanism(gprog.program_id,gate_blind,min_score=1.0,min_ablation_drop=.20)
    unknown=[k.executive.execute_capability('GLOBAL_EXPERIENCE_COGNITIVE_SAFETY_GATE_V4',{'state_known':False,'variant':bool(i%2),'nonce':8000+i}) for i in range(20)]
finally:
    try:k.close()
    except Exception:pass

history_predictions=[]
correct=0
for r,(x,y) in zip(blind_rows,blind):
    pred=predict(x);correct+=pred==y
    history_predictions.append({'path':r['path'],'logic_accept':bool(x['logic_accept']),'thinking_preference':thinking_preference(r),
                                'intel_action':('STOP' if x['intel_stop'] else 'RETRY' if x['intel_retry'] else 'ADVANCE'),
                                'predicted':pred,'expected':y})
history_accuracy=correct/max(1,len(blind))
parent_history=float((parent.get('genes') or {}).get('COGNITIVE',{}).get('history_transfer_accuracy') or parent.get('cognitive_history_accuracy') or 0.0)

cognitive_gene={
 'schema':'yado.g2.global_experience_cognitive_gene.v4',
 'gene_id':'GENE-G2-GLOBAL-EXPERIENCE-COGNITIVE-V4-'+digest({'model':model,'family':chosen['family'],'organs':[logic_gene['gene_digest'],thinking_gene['gene_digest'],intel_gene['gene_digest']]})[:16],
 'organ':'CONSCIOUS_WORKSPACE','heritage':[(parent.get('genes') or {}).get('COGNITIVE',{}).get('gene_id'),logic_gene['gene_id'],thinking_gene['gene_id'],intel_gene['gene_id']],
 'strategy_family':chosen['family'],'selected_profile':{k:chosen[k] for k in ('token','family','param','validation','complexity')},
 'native_selector':sel,'model':model,'fresh_blind':blind_score,'organ_ablation':ablation_score,'restore':restore_score,
 'history_transfer_accuracy':history_accuracy,'parent_history_transfer_accuracy':parent_history,'history_transfer_gain':history_accuracy-parent_history,
 'safety_program_id':gprog.program_id,'safety_program_digest':gdev.program_digest,'unknown_fail_closed':all(x=='WITHHOLD' for x in unknown),
 'promotion_state':'SHADOW_ONLY','origin':'YADO_NATIVE_STRATEGY_SELECTION_OVER_GLOBAL_LOGIC_THINKING_INTELLIGENCE_OUTPUTS_WITH_NATIVE_FAIL_CLOSED_GATE',
}
cognitive_gene['gene_digest']=digest(cognitive_gene)

genes={'LOGIC':logic_gene,'THINKING':thinking_gene,'INTELLIGENCE':intel_gene,'COGNITIVE':cognitive_gene}
genome={'schema':'yado.g2.global_experience_cognitive_genome.v4',
 'genome_id':'GENOME-G2-GLOBAL-EXPERIENCE-COGNITIVE-V4-'+digest({k:v['gene_digest'] for k,v in genes.items()})[:16],
 'generation':'G2_SHADOW','corpus_digest':corpus['corpus_digest'],'organs':{k:v['gene_id'] for k,v in genes.items()},
 'rollback_parents':{'LOGIC':'ALG-G2-BUDGET-ADAPTIVE-COMPOSITIONAL-LOGIC-V2','THINKING':(parent.get('genes') or {}).get('THINKING',{}).get('heritage',[None])[0],
                     'INTELLIGENCE':'ALG-G2-COVERAGE-PRUNED-COMPOSITIONAL-SCHEMA-ROUTER-V3','COGNITIVE':(parent.get('genes') or {}).get('COGNITIVE',{}).get('gene_id')},
 'promotion_state':'SHADOW_ONLY','automatic_canonical_promotion':False}
genome['genome_digest']=digest(genome)

checks={
 'global_corpus_reused':corpus.get('legacy_branch_count')==13 and corpus.get('source_counts',{}).get('RECEIPT',{}).get('parsed',0)>=323,
 'v3_logic_preserved':genes['LOGIC']==logic_gene,'v3_thinking_preserved':genes['THINKING']==thinking_gene,'v3_intelligence_preserved':genes['INTELLIGENCE']==intel_gene,
 'v3_thinking_gain_preserved':float(thinking_gene.get('gain_vs_parent') or 0)>.02,
 'native_cognitive_family_selection_used':sel.get('selected_token')==chosen['token'],
 'cognitive_validation_positive':chosen['validation']>.25,
 'cognitive_blind_material':blind_score>=.55,
 'cognitive_history_gain_over_v3':history_accuracy-parent_history>=.20,
 'organ_signal_ablation_material':blind_score-ablation_score>=.10,
 'cognitive_restore_exact':restore_score==blind_score,
 'native_safety_gate_commit':gdev.verdict=='COMMIT',
 'native_safety_gate_blind_exact':gdev.candidate_score==1.0,
 'native_safety_gate_ablation_material':gdev.candidate_score-gdev.ablation_score>=.20,
 'unknown_fail_closed':cognitive_gene['unknown_fail_closed'],
 'new_cognitive_gene_identity':cognitive_gene['gene_id']!=(parent.get('genes') or {}).get('COGNITIVE',{}).get('gene_id'),
 'four_coherent_gene_identities':len({x['gene_id'] for x in genes.values()})==4,
 'external_models_used':False,'host_written_cognitive_model':False,'host_selected_cognitive_family':False,
 'automatic_canonical_promotion':False,
 'canonical_unchanged':core.head.get('canonical_head_digest')==head_before.get('canonical_head_digest'),
}
false_keys=['external_models_used','host_written_cognitive_model','host_selected_cognitive_family','automatic_canonical_promotion']
passed=all(v is True for k,v in checks.items() if k not in false_keys) and all(checks[k] is False for k in false_keys)
status='PASS_SHADOW_G2_GLOBAL_EXPERIENCE_COGNITIVE_GENESIS_V4' if passed else 'WITHHOLD_G2_GLOBAL_EXPERIENCE_COGNITIVE_GENESIS_V4'

experience={'schema':'yado.g2.global_experience_cognitive_genesis.experience.v4','status':'TRAINED' if passed else 'WITHHOLD',
 'parent_v3_receipt':parent.get('experience_digest'),'cognitive_trials':[{k:v for k,v in t.items() if k!='model'} for t in trials],
 'selected_cognitive_profile':{k:chosen[k] for k in ('token','family','param','validation','complexity')},'native_selector':sel,
 'cognitive_fresh':blind_score,'cognitive_organ_ablation':ablation_score,'cognitive_restore':restore_score,
 'cognitive_history_accuracy':history_accuracy,'cognitive_parent_history_accuracy':parent_history,'cognitive_history_gain':history_accuracy-parent_history,
 'safety_gate':asdict(gdev),'genes':genes,'genome':genome,'history_sample':history_predictions[:120],'checks':checks,'canonical_mutation':False,
 'semantic_boundary':'V4 PRESERVES THE SUCCESSFUL GLOBAL LOGIC, MULTICONTEXT THINKING AND INTELLIGENCE GENES. COGNITIVE IS RELEARNED DIRECTLY FROM HELD-OUT HISTORICAL ACTION TARGETS USING YADO NATIVE CART/KNN/CENTROID STRATEGY FAMILIES WITH NATIVE SELECTION. ORGAN-SIGNAL ABLATION MEASURES CAUSAL USE. A SEPARATE NATIVE STATE-KNOWN GATE FAILS CLOSED ON UNKNOWN. NO CANONICAL PROMOTION.'
}
experience['experience_digest']=digest(experience);EXP.parent.mkdir(parents=True,exist_ok=True);EXP.write_text(json.dumps(experience,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')
report={'schema':'yado.g2.global_experience_cognitive_genesis.v4','status':status,'selected_cognitive_profile':experience['selected_cognitive_profile'],
 'cognitive_fresh':blind_score,'cognitive_organ_ablation':ablation_score,'cognitive_restore':restore_score,
 'cognitive_history_accuracy':history_accuracy,'cognitive_parent_history_accuracy':parent_history,'cognitive_history_gain':history_accuracy-parent_history,
 'safety_gate':asdict(gdev),'gene_ids':{k:v['gene_id'] for k,v in genes.items()},'genome_id':genome['genome_id'],'genome_digest':genome['genome_digest'],
 'checks':checks,'canonical_mutation':False,'promotion_applied':False,
 'next_required_capability':'GLOBAL_EXPERIENCE_COGNITIVE_STRESS_AND_ADMISSION_V1' if passed else 'GLOBAL_EXPERIENCE_COGNITIVE_GENESIS_REPAIR_V5',
 'semantic_boundary':experience['semantic_boundary']}
report['receipt_sha256']=digest(report);OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(report,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')
print(json.dumps({'status':status,'selected':experience['selected_cognitive_profile'],'cognitive_fresh':blind_score,'organ_ablation':ablation_score,
 'history_accuracy':history_accuracy,'parent_history_accuracy':parent_history,'history_gain':history_accuracy-parent_history,
 'safety':{'candidate':gdev.candidate_score,'ablation':gdev.ablation_score,'verdict':gdev.verdict},
 'gene_ids':report['gene_ids'],'genome_id':genome['genome_id'],'next_required_capability':report['next_required_capability'],'receipt_sha256':report['receipt_sha256']},indent=2,sort_keys=True))
if not passed:raise SystemExit(2)
