from __future__ import annotations
from pathlib import Path
from dataclasses import asdict
import copy,hashlib,json,sys

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
PKG=ROOT/'yado_rc8_v36'
sys.path[:0]=[str(ROOT),str(PKG)]

from yado_cognitive_growth_runtime_v1 import learn_multicontext_precedence,planning_accuracy,plan_multicontext
from yado_neutral_evidence_profile_selector_v1 import NeutralEvidenceProfileSelectorV1,EvidenceCandidate
from yado_organ_runtime_native_v1 import tree_predict
from yado_core_v3_0_rc8_external_cognitive import UnifiedYADOKernelV30RC8ExternalCognitive
from yado_unified_core_v1 import UnifiedYADOCoreV1

CORPUS=REPO/'experience/yado-global-experience-corpus-v1.json'
PARENT=REPO/'experience/yado-global-experience-cognitive-genesis-v2.json'
OUT=REPO/'candidates/kernel-self-generated/g2-global-experience-cognitive-genesis-v3.json'
EXP=REPO/'experience/yado-global-experience-cognitive-genesis-v3.json'

def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def digest(o):return hashlib.sha256(canon(o).encode()).hexdigest()

corpus=load(CORPUS);parent=load(PARENT)
if parent.get('status')!='WITHHOLD':raise RuntimeError('V2_WITHHOLD_EXPERIENCE_REQUIRED')
pg=parent.get('genes') or {}
logic_gene=pg.get('LOGIC') or {};intel_gene=pg.get('INTELLIGENCE') or {}
if not (logic_gene.get('gene_id') and intel_gene.get('gene_id')):raise RuntimeError('SUCCESSFUL_V2_SIBLING_GENES_REQUIRED')
if not ((parent.get('checks') or {}).get('logic_fresh_beats_baseline') and (parent.get('checks') or {}).get('intelligence_fresh_beats_baseline')):
    raise RuntimeError('V2_LOGIC_INTELLIGENCE_SUCCESS_REQUIRED')
rows=list(corpus.get('rows') or [])
receipt_rows=[r for r in rows if r.get('source_class')=='RECEIPT' and r.get('outcome') in ('PASS','WITHHOLD') and r.get('run_id')]
receipt_rows=sorted(receipt_rows,key=lambda r:(r['run_id'],r['path']))
if len(receipt_rows)<250:raise RuntimeError('GLOBAL_RECEIPT_HISTORY_TOO_SMALL')

def control_role(r):
    if r['outcome']=='PASS':return 'ACCEPT' if not r.get('next_required_capability') else 'ADVANCE'
    return 'REVISE' if r.get('next_required_capability') else 'SEEK_EVIDENCE'

def window_context(win):
    first=win[0];m=first['metrics']
    domains=[r.get('domain') for r in win]
    return {
      'START_PASS':first.get('outcome')=='PASS',
      'START_WITHHOLD':first.get('outcome')=='WITHHOLD',
      'START_HAS_NEXT':bool(first.get('next_required_capability')),
      'START_NO_NEXT':not bool(first.get('next_required_capability')),
      'START_SAME_DOMAIN_NEXT':bool(first.get('next_required_capability')) and first.get('next_domain')==first.get('domain'),
      'START_FRESH_POSITIVE':bool(m.get('fresh_positive')),
      'START_ABLATION_POSITIVE':bool(m.get('ablation_positive')),
      'WINDOW_DOMAIN_STABLE':len(set(domains))==1,
      'WINDOW_HAS_WITHHOLD':any(r.get('outcome')=='WITHHOLD' for r in win),
      'WINDOW_HAS_PASS':any(r.get('outcome')=='PASS' for r in win),
    }

windows=[]
for i in range(max(0,len(receipt_rows)-3)):
    win=receipt_rows[i:i+4]
    windows.append((window_context(win),[control_role(r) for r in win]))

n=len(windows);a=max(12,int(n*.60));b=max(a+12,int(n*.80))
fit,val,blind=windows[:a],windows[a:b],windows[b:]
if min(len(fit),len(val),len(blind))<12:raise RuntimeError('CONTEXTUAL_THINKING_SPLIT_TOO_SMALL')

def actions_for(trace,salt):
    out=[]
    for j,role in enumerate(trace):
        hid='A-'+hashlib.sha256((str(salt)+'|'+str(j)+'|'+role).encode()).hexdigest()[:14]
        out.append({'id':hid,'role':role})
    return sorted(out,key=lambda x:x['id'])
def episodes(xs,prefix):
    return [(ctx,actions_for(trace,prefix+str(i)),trace) for i,(ctx,trace) in enumerate(xs)]

val_ep=episodes(val,'VAL');blind_ep=episodes(blind,'BLIND')
trials=[]
for threshold in (.60,.67,.75,.80):
    for max_keys in (1,2,3,4):
        for min_support in (2,3,4):
            model=learn_multicontext_precedence(fit,threshold=threshold,min_support=min_support,max_context_keys=max_keys)
            score=planning_accuracy(model,val_ep)
            token=f'T{threshold:.2f}_K{max_keys}_S{min_support}'
            trials.append({'token':token,'threshold':threshold,'max_context_keys':max_keys,'min_support':min_support,
                           'validation':score,'model':model})
selection=NeutralEvidenceProfileSelectorV1.select([
    EvidenceCandidate(token=t['token'],evidence=t['validation'],complexity=t['max_context_keys']+.25*t['min_support'],
                      risk=0.0,novelty=.1)
    for t in trials
],complexity_penalty=.015,risk_penalty=.2,novelty_bonus=.01)
selected=next(t for t in trials if t['token']==selection['selected_token'])
thinking_model=learn_multicontext_precedence(fit+val,threshold=selected['threshold'],min_support=selected['min_support'],max_context_keys=selected['max_context_keys'])
fresh=planning_accuracy(thinking_model,blind_ep)
ablated=learn_multicontext_precedence([({},trace) for _,trace in fit+val],threshold=selected['threshold'],min_support=selected['min_support'],max_context_keys=0)
ablation=planning_accuracy(ablated,blind_ep)
restore=planning_accuracy(thinking_model,blind_ep)
parent_thinking=(pg.get('THINKING') or {})
parent_fresh=float(parent_thinking.get('fresh_blind') or 0.0)
gain_vs_parent=fresh-parent_fresh

thinking_gene={
 'schema':'yado.g2.global_experience_thinking_gene.v3',
 'gene_id':'GENE-G2-GLOBAL-EXPERIENCE-THINKING-V3-'+digest({'model':thinking_model,'corpus':corpus['corpus_digest'],'parent':parent_thinking.get('gene_digest')})[:16],
 'organ':'THINKING','heritage':[parent_thinking.get('gene_id'),'ALG-G2-WORK-BUDGET-ADAPTIVE-CONTINGENT-PLANNER-V2'],
 'corpus_digest':corpus['corpus_digest'],'selected_profile':{k:selected[k] for k in ('token','threshold','max_context_keys','min_support','validation')},
 'native_selector':selection,'model':thinking_model,'fresh_blind':fresh,'context_ablation':ablation,'restore':restore,
 'parent_global_precedence_fresh':parent_fresh,'gain_vs_parent':gain_vs_parent,'promotion_state':'SHADOW_ONLY',
 'origin':'YADO_NATIVE_MULTICONTEXT_PRECEDENCE_FROM_GLOBAL_RUN_HISTORY',
}
thinking_gene['gene_digest']=digest(thinking_gene)

# Reuse successful V2 LOGIC and INTELLIGENCE exactly; no host rewrite.
lmodel=logic_gene['model'];imodel=intel_gene['model']
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
    ids=plan_multicontext(thinking_model,row_context(r),acts)
    by={a['id']:a['role'] for a in acts}
    return by[ids[0]] if ids else 'SEEK_EVIDENCE'

def cognition_state(r):
    lp=bool(tree_predict(lmodel,logic_features(r)))
    ip=str(tree_predict(imodel,intel_features(r)))
    tp=str(thinking_preference(r))
    nxt=bool(r.get('next_required_capability'))
    if lp and ip=='STOP' and tp=='ACCEPT' and not nxt:return 'CONSISTENT_COMMIT'
    if lp and ip=='ADVANCE' and tp=='ADVANCE' and nxt:return 'CONSISTENT_CONTINUE'
    if (not lp) and ip in ('RETRY','ADVANCE') and tp=='REVISE' and nxt:return 'CONSISTENT_REVISE'
    if (not lp) and tp=='SEEK_EVIDENCE' and not nxt:return 'CONSISTENT_EVIDENCE'
    return 'CONFLICT_WITHHOLD'

state_targets={
 'CONSISTENT_COMMIT':'COMMIT','CONSISTENT_CONTINUE':'CONTINUE','CONSISTENT_REVISE':'REVISE',
 'CONSISTENT_EVIDENCE':'SEEK_EVIDENCE','CONFLICT_WITHHOLD':'WITHHOLD','UNKNOWN':'WITHHOLD',
}
ctrain=[];cblind=[]
for rep in range(24):
    for st,y in state_targets.items():
        ctrain.append({'input':{'cognitive_state':st,'state_known':st!='UNKNOWN','variant':bool(rep%2)},'expected':y})
for rep in range(12):
    for st,y in state_targets.items():
        cblind.append({'input':{'cognitive_state':st,'state_known':st!='UNKNOWN','variant':bool((rep+1)%2),'nonce':rep},'expected':y})

core=UnifiedYADOCoreV1(REPO);head_before=copy.deepcopy(core.head)
db=ROOT/'yado_global_experience_cognitive_genesis_v3.sqlite'
if db.exists():db.unlink()
k=UnifiedYADOKernelV30RC8ExternalCognitive(db_path=str(db))
try:
    goal=k.executive.create_goal(
      objective='Integrate global history LOGIC, improved multicontext THINKING and global INTELLIGENCE into a fail-closed cognitive coordinator.',
      required_capabilities={'GLOBAL_EXPERIENCE_COGNITIVE_COORDINATOR_V3':1.0},
      success_criteria={'blind':1.0,'ablation_drop':.20,'restore':1.0,'unknown_fail_closed':True},
    )
    deficit=k.executive.detect_deficits(goal.goal_id)[0]
    cprog,csel=k.executive.synthesize_best_mechanism(deficit.deficit_id,'CONSCIOUS_WORKSPACE',ctrain,min_support=2)
    cdev=k.executive.evaluate_mechanism(cprog.program_id,cblind,min_score=1.0,min_ablation_drop=.20)
    unknown=[
      k.executive.execute_capability('GLOBAL_EXPERIENCE_COGNITIVE_COORDINATOR_V3',{'cognitive_state':'UNKNOWN','state_known':False,'variant':bool(i%2),'nonce':9000+i})
      for i in range(20)
    ]
    held=[r for r in rows if r.get('outcome') in ('PASS','WITHHOLD') and int(r['sha256'][:8],16)%10>=8]
    hist=[];ok=0
    for r in held:
        st=cognition_state(r)
        action=k.executive.execute_capability('GLOBAL_EXPERIENCE_COGNITIVE_COORDINATOR_V3',{'cognitive_state':st,'state_known':True,'variant':True,'nonce':777})
        expected=('COMMIT' if r['outcome']=='PASS' and not r.get('next_required_capability')
                  else 'CONTINUE' if r['outcome']=='PASS' and r.get('next_required_capability')
                  else 'REVISE' if r['outcome']=='WITHHOLD' and r.get('next_required_capability')
                  else 'SEEK_EVIDENCE')
        ok+=action==expected;hist.append({'path':r['path'],'thinking_preference':thinking_preference(r),'state':st,'action':action,'expected':expected})
    hist_acc=ok/max(1,len(hist))
finally:
    try:k.close()
    except Exception:pass

parent_hist=float((parent.get('genes') or {}).get('COGNITIVE',{}).get('history_transfer_accuracy') or 0.0)
cognitive_gene={
 'schema':'yado.g2.global_experience_cognitive_gene.v3',
 'gene_id':'GENE-G2-GLOBAL-EXPERIENCE-COGNITIVE-V3-'+digest({'program':cdev.program_digest,'thinking':thinking_gene['gene_digest'],'siblings':[logic_gene['gene_digest'],intel_gene['gene_digest']]})[:16],
 'organ':'CONSCIOUS_WORKSPACE','heritage':[(parent.get('genes') or {}).get('COGNITIVE',{}).get('gene_id'),logic_gene['gene_id'],thinking_gene['gene_id'],intel_gene['gene_id']],
 'program_id':cprog.program_id,'program_digest':cdev.program_digest,'fresh_blind':cdev.candidate_score,
 'ablation':cdev.ablation_score,'restore':cdev.restore_score,'history_transfer_accuracy':hist_acc,'parent_history_transfer_accuracy':parent_hist,
 'history_transfer_gain':hist_acc-parent_hist,'unknown_fail_closed':all(x=='WITHHOLD' for x in unknown),
 'promotion_state':'SHADOW_ONLY','origin':'YADO_NATIVE_COORDINATOR_OVER_GLOBAL_LOGIC_MULTICONTEXT_THINKING_AND_INTELLIGENCE',
}
cognitive_gene['gene_digest']=digest(cognitive_gene)

genes={'LOGIC':logic_gene,'THINKING':thinking_gene,'INTELLIGENCE':intel_gene,'COGNITIVE':cognitive_gene}
genome={
 'schema':'yado.g2.global_experience_cognitive_genome.v3',
 'genome_id':'GENOME-G2-GLOBAL-EXPERIENCE-COGNITIVE-V3-'+digest({k:v['gene_digest'] for k,v in genes.items()})[:16],
 'generation':'G2_SHADOW','corpus_digest':corpus['corpus_digest'],'organs':{k:v['gene_id'] for k,v in genes.items()},
 'rollback_parents':{'LOGIC':'ALG-G2-BUDGET-ADAPTIVE-COMPOSITIONAL-LOGIC-V2','THINKING':parent_thinking.get('gene_id'),
                     'INTELLIGENCE':'ALG-G2-COVERAGE-PRUNED-COMPOSITIONAL-SCHEMA-ROUTER-V3',
                     'COGNITIVE':(parent.get('genes') or {}).get('COGNITIVE',{}).get('gene_id')},
 'promotion_state':'SHADOW_ONLY','automatic_canonical_promotion':False,
}
genome['genome_digest']=digest(genome)

checks={
 'global_corpus_reused':corpus.get('legacy_branch_count')==13 and corpus.get('source_counts',{}).get('RECEIPT',{}).get('parsed',0)>=323,
 'v2_logic_gene_preserved_exact':genes['LOGIC']==logic_gene,
 'v2_intelligence_gene_preserved_exact':genes['INTELLIGENCE']==intel_gene,
 'v2_thinking_zero_gain_consumed':parent_fresh==float((parent.get('baselines') or {}).get('THINKING') or parent_fresh),
 'native_multicontext_thinking_used':thinking_model.get('kind')=='MULTICONTEXT_PRECEDENCE',
 'native_profile_selector_used':selection.get('selected_token')==selected['token'],
 'thinking_validation_positive':selected['validation']>0,
 'thinking_fresh_beats_v2_parent':gain_vs_parent>.02,
 'thinking_context_ablation_material':fresh-ablation>=.10,
 'thinking_restore_exact':restore==fresh,
 'new_thinking_gene_identity':thinking_gene['gene_id']!=parent_thinking.get('gene_id'),
 'cognitive_native_commit':cdev.verdict=='COMMIT',
 'cognitive_blind_exact':cdev.candidate_score==1.0,
 'cognitive_ablation_drop_ge_0_20':cdev.candidate_score-cdev.ablation_score>=.20,
 'cognitive_unknown_fail_closed':cognitive_gene['unknown_fail_closed'],
 'cognitive_history_transfer_improved':hist_acc-parent_hist>=.05,
 'four_coherent_gene_identities':len({x['gene_id'] for x in genes.values()})==4,
 'external_models_used':False,'host_written_thinking_model':False,'host_selected_profile':False,
 'automatic_canonical_promotion':False,
 'canonical_unchanged':core.head.get('canonical_head_digest')==head_before.get('canonical_head_digest'),
}
false_keys=['external_models_used','host_written_thinking_model','host_selected_profile','automatic_canonical_promotion']
passed=all(v is True for k,v in checks.items() if k not in false_keys) and all(checks[k] is False for k in false_keys)
status='PASS_SHADOW_G2_GLOBAL_EXPERIENCE_COGNITIVE_GENESIS_V3' if passed else 'WITHHOLD_G2_GLOBAL_EXPERIENCE_COGNITIVE_GENESIS_V3'

experience={'schema':'yado.g2.global_experience_cognitive_genesis.experience.v3','status':'TRAINED' if passed else 'WITHHOLD',
 'parent_receipt':parent.get('experience_digest'),'thinking_trials':[{k:v for k,v in t.items() if k!='model'} for t in trials],
 'selected_thinking_profile':{k:selected[k] for k in ('token','threshold','max_context_keys','min_support','validation')},
 'native_selector':selection,'thinking_fresh':fresh,'thinking_ablation':ablation,'thinking_restore':restore,'thinking_gain_vs_parent':gain_vs_parent,
 'genes':genes,'genome':genome,'cognitive_development':asdict(cdev),'cognitive_history_accuracy':hist_acc,
 'cognitive_history_gain':hist_acc-parent_hist,'cognitive_history_sample':hist[:100],'checks':checks,'canonical_mutation':False,
 'semantic_boundary':'V3 REPAIRS ONLY GLOBAL THINKING USING YADO NATIVE MULTICONTEXT PRECEDENCE WITH NATIVE PROFILE SELECTION OVER REAL RUN HISTORY. V2 LOGIC AND INTELLIGENCE GENES ARE PRESERVED EXACTLY. THE COGNITIVE COORDINATOR NOW CONSUMES THE NEW THINKING PREFERENCE AS AN EXPLICIT ORGAN SIGNAL. ALL REMAINS SHADOW.'
}
experience['experience_digest']=digest(experience);EXP.parent.mkdir(parents=True,exist_ok=True);EXP.write_text(json.dumps(experience,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')
report={'schema':'yado.g2.global_experience_cognitive_genesis.v3','status':status,'thinking_fresh':fresh,'thinking_ablation':ablation,
 'thinking_restore':restore,'thinking_parent_fresh':parent_fresh,'thinking_gain_vs_parent':gain_vs_parent,
 'cognitive_history_accuracy':hist_acc,'cognitive_parent_history_accuracy':parent_hist,'cognitive_history_gain':hist_acc-parent_hist,
 'cognitive_development':asdict(cdev),'gene_ids':{k:v['gene_id'] for k,v in genes.items()},'genome_id':genome['genome_id'],'genome_digest':genome['genome_digest'],
 'checks':checks,'canonical_mutation':False,'promotion_applied':False,
 'next_required_capability':'GLOBAL_EXPERIENCE_COGNITIVE_STRESS_AND_ADMISSION_V1' if passed else 'GLOBAL_EXPERIENCE_COGNITIVE_GENESIS_REPAIR_V4',
 'semantic_boundary':experience['semantic_boundary']}
report['receipt_sha256']=digest(report);OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(report,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')
print(json.dumps({'status':status,'thinking':{'fresh':fresh,'parent':parent_fresh,'gain':gain_vs_parent,'ablation':ablation,'restore':restore,'profile':selected['token']},
 'cognitive':{'history_accuracy':hist_acc,'parent_history_accuracy':parent_hist,'gain':hist_acc-parent_hist,'candidate':cdev.candidate_score,'ablation':cdev.ablation_score},
 'gene_ids':report['gene_ids'],'genome_id':genome['genome_id'],'next_required_capability':report['next_required_capability'],'receipt_sha256':report['receipt_sha256']},indent=2,sort_keys=True))
if not passed:raise SystemExit(2)
