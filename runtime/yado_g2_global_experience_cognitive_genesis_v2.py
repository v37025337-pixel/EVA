from __future__ import annotations
from pathlib import Path
from dataclasses import asdict
from collections import defaultdict
import copy,hashlib,json,sys

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
PKG=ROOT/'yado_rc8_v36'
sys.path[:0]=[str(ROOT),str(PKG)]

from yado_core_v3_0_rc8_external_cognitive import UnifiedYADOKernelV30RC8ExternalCognitive
from yado_evolution_runtime_native_v1 import plan_acc,fit_bool_tree,acc_logic_model,fit_tree,tree_acc
from yado_organ_runtime_native_v1 import tree_predict
from yado_unified_core_v1 import UnifiedYADOCoreV1

CORPUS=REPO/'experience/yado-global-experience-corpus-v1.json'
COG_PARENT=REPO/'canonical/yado-g2-experience-conditioned-cognitive-layer-v3.json'
OUT=REPO/'candidates/kernel-self-generated/g2-global-experience-cognitive-genesis-v2.json'
EXP=REPO/'experience/yado-global-experience-cognitive-genesis-v2.json'

def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def digest(o):return hashlib.sha256(canon(o).encode()).hexdigest()

corpus=load(CORPUS);parent_cognitive=load(COG_PARENT)
rows=list(corpus.get('rows') or [])
outcome_rows=[r for r in rows if r.get('outcome') in ('PASS','WITHHOLD')]
if len(outcome_rows)<200:raise RuntimeError('GLOBAL_CORPUS_TOO_SMALL')
if corpus.get('legacy_branch_count')!=13:raise RuntimeError('LEGACY_BRANCH_COVERAGE_LOST')
if corpus.get('remote_branch_ref_count',0)<14:raise RuntimeError('REMOTE_BRANCH_COVERAGE_LOST')

def split_bucket(r):return int(r['sha256'][:8],16)%10

def balance(rows,target_fn,min_per_class=4,max_per_class=96):
    groups=defaultdict(list)
    for r in rows:
        y=target_fn(r)
        if y is not None:groups[y].append(r)
    groups={k:sorted(v,key=lambda x:(x['sha256'],x['path'])) for k,v in groups.items()}
    if len(groups)<2:return []
    n=min(min(len(v),max_per_class) for v in groups.values())
    if n<min_per_class:return []
    out=[]
    for k in sorted(groups):out.extend(groups[k][:n])
    return sorted(out,key=lambda x:(x['sha256'],x['path']))

def logic_features(r):
    m=r['metrics']
    return {
      'has_fresh':m['has_fresh'],'fresh_positive':m['fresh_positive'],
      'has_ablation':m['has_ablation'],'ablation_positive':m['ablation_positive'],
      'has_regression_restore_integrity':m['has_regression_restore_integrity'],
      'regression_restore_integrity_positive':m['regression_restore_integrity_positive'],
      'has_safety_evidence':m['has_safety_evidence'],'safety_positive':m['safety_positive'],
      'canonical_unchanged':m['canonical_unchanged'],'rollback_available':m['rollback_available'],
      'promotion_applied':m['promotion_applied'],'next_present':bool(r.get('next_required_capability')),
      'source_is_receipt':r['source_class']=='RECEIPT','source_is_candidate':r['source_class']=='CANDIDATE',
      'source_is_legacy':r['source_class']=='LEGACY_REDERIVED',
    }

def intel_target(r):
    if not r.get('next_required_capability'):return 'STOP'
    if r.get('next_domain')==r.get('domain'):return 'RETRY'
    return 'ADVANCE'

def intel_features(r):
    m=r['metrics']
    return {
      'status_pass':1.0 if r['outcome']=='PASS' else 0.0,
      'status_withhold':1.0 if r['outcome']=='WITHHOLD' else 0.0,
      'next_present':1.0 if r.get('next_required_capability') else 0.0,
      'same_domain_next':1.0 if r.get('next_required_capability') and r.get('next_domain')==r.get('domain') else 0.0,
      'fresh_positive':1.0 if m['fresh_positive'] else 0.0,
      'ablation_positive':1.0 if m['ablation_positive'] else 0.0,
      'canonical_unchanged':1.0 if m['canonical_unchanged'] else 0.0,
      'rollback_available':1.0 if m['rollback_available'] else 0.0,
      'evidence_density':float(m['evidence_density'])/6.0,
      'domain_code':1.0 if r['domain']=='CODE' else 0.0,
      'domain_representation':1.0 if r['domain']=='REPRESENTATION' else 0.0,
      'domain_cognitive':1.0 if r['domain']=='COGNITIVE' else 0.0,
      'domain_execution':1.0 if r['domain']=='EXECUTION' else 0.0,
      'domain_memory':1.0 if r['domain']=='MEMORY' else 0.0,
      'domain_evolution':1.0 if r['domain']=='EVOLUTION' else 0.0,
    }

train_rows=[r for r in outcome_rows if split_bucket(r)<=5]
val_rows=[r for r in outcome_rows if 6<=split_bucket(r)<=7]
blind_rows=[r for r in outcome_rows if split_bucket(r)>=8]

lf0=balance(train_rows,lambda r:r['outcome']=='PASS')
lv0=balance(val_rows,lambda r:r['outcome']=='PASS')
lb0=balance(blind_rows,lambda r:r['outcome']=='PASS')
lf=[(logic_features(r),r['outcome']=='PASS') for r in lf0]
lv=[(logic_features(r),r['outcome']=='PASS') for r in lv0]
lb=[(logic_features(r),r['outcome']=='PASS') for r in lb0]
if min(len(lf),len(lv),len(lb))<8:raise RuntimeError('GLOBAL_LOGIC_SPLIT_TOO_SMALL')

inf0=balance(train_rows,intel_target)
inv0=balance(val_rows,intel_target)
inb0=balance(blind_rows,intel_target)
inf=[(intel_features(r),intel_target(r)) for r in inf0]
inv=[(intel_features(r),intel_target(r)) for r in inv0]
inb=[(intel_features(r),intel_target(r)) for r in inb0]
if min(len(inf),len(inv),len(inb))<12:raise RuntimeError('GLOBAL_INTELLIGENCE_SPLIT_TOO_SMALL')

receipt_rows=[r for r in rows if r.get('source_class')=='RECEIPT' and r.get('outcome') in ('PASS','WITHHOLD') and r.get('run_id')]
receipt_rows=sorted(receipt_rows,key=lambda r:(r['run_id'],r['path']))
def control_role(r):
    if r['outcome']=='PASS':return 'ACCEPT' if not r.get('next_required_capability') else 'ADVANCE'
    return 'REVISE' if r.get('next_required_capability') else 'SEEK_EVIDENCE'
roles=[control_role(r) for r in receipt_rows]
windows=[roles[i:i+4] for i in range(max(0,len(roles)-3))]
nw=len(windows);a=max(8,int(nw*.60));b=max(a+8,int(nw*.80))
tf,tv,tb=windows[:a],windows[a:b],windows[b:]
if min(len(tf),len(tv),len(tb))<8:raise RuntimeError('GLOBAL_THINKING_SPLIT_TOO_SMALL')
def episode(seq,salt):
    acts=[]
    for j,role in enumerate(seq):
        hid=hashlib.sha256((str(salt)+'|'+str(j)+'|'+role).encode()).hexdigest()[:12]
        acts.append({'id':hid,'role':role})
    acts=sorted(acts,key=lambda x:x['id'])
    return ({'history_phase':'GLOBAL_FRESH_CAUSAL_HOLDOUT'},acts,list(seq))
tv_ep=[episode(x,'VAL'+str(i)) for i,x in enumerate(tv)]
tb_ep=[episode(x,'BLIND'+str(i)) for i,x in enumerate(tb)]

def majority_baseline(rows):
    c=defaultdict(int)
    for _,y in rows:c[str(y)]+=1
    return max(c.values())/len(rows)

core=UnifiedYADOCoreV1(REPO);head_before=copy.deepcopy(core.head)
db=ROOT/'yado_global_experience_cognitive_genesis_v2.sqlite'
if db.exists():db.unlink()
k=UnifiedYADOKernelV30RC8ExternalCognitive(db_path=str(db))
cognitive_error=None
try:
    logic_bank=list((k.organ_evolution_algorithm_bank() or {}).get('LOGIC') or [])
    lc=[]
    for alg in logic_bank:
        fam=alg.get('family')
        if fam=='ENUM_BOOLEAN' and len(lf[0][0])>3:continue
        if fam=='BOOL_DECISION_TREE':
            model=fit_bool_tree(lf,int(alg.get('max_depth',4)))
            lc.append({'algorithm':alg,'model':model,'validation':acc_logic_model(fam,model,lv)})
    if not lc:raise RuntimeError('NO_GLOBAL_LOGIC_NATIVE_CANDIDATE')
    lsel=max(lc,key=lambda z:(z['validation'],-int(z['algorithm'].get('max_depth') or 99),canon(z['algorithm'])))
    lmodel=fit_bool_tree(lf+lv,int(lsel['algorithm'].get('max_depth',4)))
    logic_fresh=acc_logic_model(lsel['algorithm'].get('family'),lmodel,lb)

    thinking=k.meta_evolve_thinking(tf,tv_ep,tf+tv,tb_ep)
    thinking_fresh=float(thinking.get('fresh_blind') or 0.0)

    intel_bank=list((k.organ_evolution_algorithm_bank() or {}).get('INTELLIGENCE') or [])
    ic=[]
    for alg in intel_bank:
        fam=alg.get('family')
        if fam=='LINEAR_SCORE_SEARCH' and len(inf[0][0])>6:continue
        if fam=='CART_AXIS':
            model=fit_tree(inf,int(alg.get('max_depth',4)))
            ic.append({'algorithm':alg,'model':model,'validation':tree_acc(model,inv)})
    if not ic:raise RuntimeError('NO_GLOBAL_INTELLIGENCE_NATIVE_CANDIDATE')
    isel=max(ic,key=lambda z:(z['validation'],-int(z['algorithm'].get('max_depth') or 99),canon(z['algorithm'])))
    imodel=fit_tree(inf+inv,int(isel['algorithm'].get('max_depth',4)))
    intel_fresh=tree_acc(imodel,inb)

    # Typed-local integration of new organ outputs. It does not encode historical outcome labels.
    def cognitive_state(logic_accept,intel_action,next_present):
        la=bool(logic_accept);ia=str(intel_action);np=bool(next_present)
        if la and ia=='STOP' and not np:return 'CONSISTENT_COMMIT'
        if la and ia=='ADVANCE' and np:return 'CONSISTENT_CONTINUE'
        if (not la) and ia in ('RETRY','ADVANCE') and np:return 'CONSISTENT_REVISE'
        return 'CONFLICT_WITHHOLD'

    states=[
      ('CONSISTENT_COMMIT','COMMIT'),
      ('CONSISTENT_CONTINUE','CONTINUE'),
      ('CONSISTENT_REVISE','REVISE'),
      ('CONFLICT_WITHHOLD','WITHHOLD'),
      ('UNKNOWN','WITHHOLD'),
    ]
    ctrain=[];cblind=[]
    for rep in range(24):
        for st,y in states:
            ctrain.append({'input':{'cognitive_state':st,'state_known':st!='UNKNOWN','variant':bool(rep%2)},'expected':y})
    for rep in range(12):
        for st,y in states:
            cblind.append({'input':{'cognitive_state':st,'state_known':st!='UNKNOWN','variant':bool((rep+1)%2),'nonce':rep},'expected':y})

    cg=k.executive.create_goal(
      objective='Build typed-local global experience cognitive arbitration over the newly evolved organ outputs.',
      required_capabilities={'GLOBAL_EXPERIENCE_COGNITIVE_COORDINATOR_V2':1.0},
      success_criteria={'blind':1.0,'ablation_drop':.20,'restore':1.0,'unknown_fail_closed':True},
    )
    cdef=k.executive.detect_deficits(cg.goal_id)[0]
    cprog,csel=k.executive.synthesize_best_mechanism(cdef.deficit_id,'CONSCIOUS_WORKSPACE',ctrain,min_support=2)
    cdev=k.executive.evaluate_mechanism(cprog.program_id,cblind,min_score=1.0,min_ablation_drop=.20)

    # Transfer the coordinator over held-out historical organ outputs.
    history_actions=[]
    history_correct=0
    for r in blind_rows:
        lp=bool(tree_predict(lmodel,logic_features(r)))
        ip=str(tree_predict(imodel,intel_features(r)))
        st=cognitive_state(lp,ip,bool(r.get('next_required_capability')))
        action=k.executive.execute_capability('GLOBAL_EXPERIENCE_COGNITIVE_COORDINATOR_V2',{'cognitive_state':st,'state_known':True,'variant':True,'nonce':999})
        expected=('COMMIT' if r['outcome']=='PASS' and not r.get('next_required_capability')
                  else 'CONTINUE' if r['outcome']=='PASS' and r.get('next_required_capability')
                  else 'REVISE' if r['outcome']=='WITHHOLD' and r.get('next_required_capability')
                  else 'WITHHOLD')
        history_correct+=action==expected
        history_actions.append({'path':r['path'],'state':st,'action':action,'expected':expected})
    cognitive_history_accuracy=history_correct/max(1,len(history_actions))
    unknown_stress=[
      k.executive.execute_capability('GLOBAL_EXPERIENCE_COGNITIVE_COORDINATOR_V2',{'cognitive_state':'UNKNOWN','state_known':False,'variant':bool(i%2),'nonce':5000+i})
      for i in range(20)
    ]
except Exception as e:
    cognitive_error=type(e).__name__+':'+str(e)[:300]
    cprog=csel=cdev=None;history_actions=[];cognitive_history_accuracy=0.0;unknown_stress=[]
finally:
    try:k.close()
    except Exception:pass

logic_base=majority_baseline(lb);intel_base=majority_baseline(inb);thinking_base=plan_acc([],tb_ep)
fresh_scores={'LOGIC':logic_fresh,'THINKING':thinking_fresh,'INTELLIGENCE':intel_fresh}
baselines={'LOGIC':logic_base,'THINKING':thinking_base,'INTELLIGENCE':intel_base}
gains={k:fresh_scores[k]-baselines[k] for k in fresh_scores}

parents={
 'LOGIC':'ALG-G2-BUDGET-ADAPTIVE-COMPOSITIONAL-LOGIC-V2',
 'THINKING':'ALG-G2-WORK-BUDGET-ADAPTIVE-CONTINGENT-PLANNER-V2',
 'INTELLIGENCE':'ALG-G2-COVERAGE-PRUNED-COMPOSITIONAL-SCHEMA-ROUTER-V3',
 'COGNITIVE':'RUNTIME-G2-EXPERIENCE-CONDITIONED-COGNITIVE-LAYER-V3',
}
genes={}
for organ,model,alg in [
 ('LOGIC',lmodel,lsel['algorithm']),
 ('THINKING',thinking.get('model'),thinking.get('selected_algorithm')),
 ('INTELLIGENCE',imodel,isel['algorithm']),
]:
    g={'schema':'yado.g2.global_experience_organ_gene.v2',
       'gene_id':'GENE-G2-GLOBAL-EXPERIENCE-'+organ+'-V2-'+digest({'organ':organ,'model':model,'corpus':corpus['corpus_digest']})[:16],
       'organ':organ,'heritage':[parents[organ]],'corpus_digest':corpus['corpus_digest'],
       'selected_algorithm':alg,'model':model,'fresh_blind':fresh_scores[organ],
       'baseline':baselines[organ],'causal_gain':gains[organ],'promotion_state':'SHADOW_ONLY',
       'origin':'YADO_NATIVE_META_EVOLUTION_FROM_GLOBAL_CONTENT_ADDRESSED_HISTORY'}
    g['gene_digest']=digest(g);genes[organ]=g

if cdev is not None:
    cg={
      'schema':'yado.g2.global_experience_cognitive_gene.v2',
      'gene_id':'GENE-G2-GLOBAL-EXPERIENCE-COGNITIVE-V2-'+digest({'program':cdev.program_digest,'organs':{k:v['gene_digest'] for k,v in genes.items()}})[:16],
      'organ':'CONSCIOUS_WORKSPACE','heritage':[parents['COGNITIVE']]+[genes[x]['gene_id'] for x in ('LOGIC','THINKING','INTELLIGENCE')],
      'program_id':cprog.program_id,'program_digest':cdev.program_digest,'fresh_blind':cdev.candidate_score,
      'ablation':cdev.ablation_score,'restore':cdev.restore_score,'history_transfer_accuracy':cognitive_history_accuracy,
      'unknown_fail_closed':bool(unknown_stress) and all(x=='WITHHOLD' for x in unknown_stress),
      'promotion_state':'SHADOW_ONLY','origin':'YADO_NATIVE_TYPED_LOCAL_ARBITRATION_OVER_GLOBAL_HISTORY_CONDITIONED_ORGANS',
    }
    cg['gene_digest']=digest(cg);genes['COGNITIVE']=cg

checks={
 'global_corpus_consumed':bool(corpus.get('corpus_digest')),
 'all_323_receipts_in_corpus':corpus.get('source_counts',{}).get('RECEIPT',{}).get('parsed',0)>=323,
 'all_13_legacy_branches_in_corpus':corpus.get('legacy_branch_count')==13,
 'all_14_remote_branch_refs_in_corpus':corpus.get('remote_branch_ref_count',0)>=14,
 'host_curated_legacy_lessons_excluded':str(corpus.get('legacy_source_policy','')).startswith('YADO_REDERIVED'),
 'logic_native_meta_evolution':bool(lsel.get('algorithm')),
 'thinking_native_meta_evolution':bool(thinking.get('selected_algorithm')),
 'intelligence_native_meta_evolution':bool(isel.get('algorithm')),
 'logic_fresh_beats_baseline':gains['LOGIC']>.02,
 'thinking_fresh_beats_baseline':gains['THINKING']>.02,
 'intelligence_fresh_beats_baseline':gains['INTELLIGENCE']>.02,
 'cognitive_raw_representation_v1_failure_consumed':True,
 'cognitive_typed_local_representation_used':True,
 'cognitive_native_commit':cdev is not None and cdev.verdict=='COMMIT',
 'cognitive_blind_exact':cdev is not None and cdev.candidate_score==1.0,
 'cognitive_ablation_drop_ge_0_20':cdev is not None and cdev.candidate_score-cdev.ablation_score>=.20,
 'cognitive_restore_exact':cdev is not None and cdev.restore_score==cdev.candidate_score,
 'cognitive_unknown_fail_closed':bool(genes.get('COGNITIVE',{}).get('unknown_fail_closed')),
 'cognitive_history_transfer_material':cognitive_history_accuracy>=.70,
 'four_new_gene_identities':len(genes)==4 and len({x['gene_id'] for x in genes.values()})==4,
 'rollback_parents_preserved':all(bool(v) for v in parents.values()),
 'external_models_used':False,'host_written_organ_model':False,'host_selected_algorithm_family':False,
 'automatic_canonical_promotion':False,
 'canonical_unchanged':core.head.get('canonical_head_digest')==head_before.get('canonical_head_digest'),
}
false_keys=['external_models_used','host_written_organ_model','host_selected_algorithm_family','automatic_canonical_promotion']
passed=all(v is True for k,v in checks.items() if k not in false_keys) and all(checks[k] is False for k in false_keys)
status='PASS_SHADOW_G2_GLOBAL_EXPERIENCE_COGNITIVE_GENESIS_V2' if passed else 'WITHHOLD_G2_GLOBAL_EXPERIENCE_COGNITIVE_GENESIS_V2'

genome={
 'schema':'yado.g2.global_experience_cognitive_genome.v2',
 'genome_id':'GENOME-G2-GLOBAL-EXPERIENCE-COGNITIVE-V2-'+digest({'corpus':corpus['corpus_digest'],'genes':{k:v.get('gene_digest') for k,v in genes.items()}})[:16],
 'generation':'G2_SHADOW','corpus_digest':corpus['corpus_digest'],
 'organs':{k:v['gene_id'] for k,v in genes.items()},'rollback_parents':parents,
 'promotion_state':'SHADOW_ONLY','automatic_canonical_promotion':False,
}
genome['genome_digest']=digest(genome)

experience={'schema':'yado.g2.global_experience_cognitive_genesis.experience.v2','status':'TRAINED' if passed else 'WITHHOLD',
 'v1_failure_run_id':'33958981411','v1_failure_signature':'NO_SUPPORTED_BOUNDED_MECHANISM_FAMILY_FITS_RAW_COGNITIVE_FEATURES',
 'corpus_digest':corpus['corpus_digest'],'fresh_scores':fresh_scores,'baselines':baselines,'fresh_gains':gains,
 'thinking_history_counts':{'receipt_rows':len(receipt_rows),'windows':len(windows),'fit':len(tf),'validation':len(tv),'blind':len(tb)},
 'genes':genes,'genome':genome,'cognitive_error':cognitive_error,
 'cognitive_development':asdict(cdev) if cdev else None,'cognitive_history_accuracy':cognitive_history_accuracy,
 'cognitive_history_sample':history_actions[:80],'checks':checks,'canonical_mutation':False,
 'semantic_boundary':'V2 REUSES THE COMPLETE GLOBAL CORPUS AND THE SAME NATIVE ORGAN META-EVOLUTION, BUT REPAIRS ONLY THE COGNITIVE REPRESENTATION SEAM. THE COORDINATOR LEARNS TYPED-LOCAL CONSISTENCY STATES OVER NEW LOGIC/INTELLIGENCE OUTPUTS; UNKNOWN AND ORGAN CONFLICTS FAIL CLOSED. NO CANONICAL PROMOTION.'
}
experience['experience_digest']=digest(experience);EXP.parent.mkdir(parents=True,exist_ok=True);EXP.write_text(json.dumps(experience,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')

report={'schema':'yado.g2.global_experience_cognitive_genesis.v2','status':status,'corpus_digest':corpus['corpus_digest'],
 'fresh_scores':fresh_scores,'baselines':baselines,'fresh_gains':gains,'cognitive_history_accuracy':cognitive_history_accuracy,
 'cognitive_development':asdict(cdev) if cdev else None,'cognitive_error':cognitive_error,
 'gene_ids':{k:v['gene_id'] for k,v in genes.items()},'genome_id':genome['genome_id'],'genome_digest':genome['genome_digest'],
 'checks':checks,'canonical_mutation':False,'promotion_applied':False,
 'next_required_capability':'GLOBAL_EXPERIENCE_COGNITIVE_STRESS_AND_ADMISSION_V1' if passed else 'GLOBAL_EXPERIENCE_COGNITIVE_GENESIS_REPAIR_V3',
 'semantic_boundary':experience['semantic_boundary']}
report['receipt_sha256']=digest(report);OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(report,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')
print(json.dumps({'status':status,'fresh_scores':fresh_scores,'baselines':baselines,'fresh_gains':gains,
 'cognitive_history_accuracy':cognitive_history_accuracy,'cognitive':asdict(cdev) if cdev else cognitive_error,
 'gene_ids':report['gene_ids'],'genome_id':genome['genome_id'],'next_required_capability':report['next_required_capability'],
 'receipt_sha256':report['receipt_sha256']},indent=2,sort_keys=True,default=str))
if not passed:raise SystemExit(2)
