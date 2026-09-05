from __future__ import annotations
from pathlib import Path
from collections import defaultdict
import copy,hashlib,json,subprocess,sys

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
PKG=ROOT/'yado_rc8_v36'
sys.path[:0]=[str(ROOT),str(PKG)]

from yado_cognitive_growth_runtime_v1 import plan_multicontext,fit_knn_strategy,knn_predict,strategy_accuracy,fit_centroid_strategy,centroid_predict,centroid_accuracy
from yado_organ_runtime_native_v1 import fit_tree,tree_predict,tree_acc
from yado_neutral_evidence_profile_selector_v1 import NeutralEvidenceProfileSelectorV1,EvidenceCandidate
from yado_unified_core_v1 import UnifiedYADOCoreV1

BASE=REPO/'experience/yado-global-experience-corpus-v1.json'
HIST=REPO/'experience/yado-global-historical-experience-corpus-v2.json'
V6=REPO/'experience/yado-global-experience-cognitive-genesis-v6.json'
OUT=REPO/'candidates/kernel-self-generated/g2-global-experience-terminal-logic-historical-transfer-v1.json'
EXP=REPO/'experience/yado-global-experience-terminal-logic-historical-transfer-v1.json'

def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def digest(o):return hashlib.sha256(canon(o).encode()).hexdigest()
base=load(BASE);hist=load(HIST);v6=load(V6)
if v6.get('status')!='TRAINED':raise RuntimeError('V6_TRAINED_REQUIRED')
if hist.get('new_historical_outcome_count',0)<40:raise RuntimeError('HISTORICAL_TRANSFER_CORPUS_TOO_SMALL')

def flatten(obj,max_depth=9):
    out=[]
    def walk(x,path,depth):
        if depth>max_depth:return
        if isinstance(x,dict):
            for k in sorted(x):walk(x[k],path+[str(k)],depth+1)
        elif isinstance(x,list):
            for i,v in enumerate(x[:128]):walk(v,path+[str(i)],depth+1)
        elif isinstance(x,(str,int,float,bool)) or x is None:
            out.append(('.'.join(path),x))
    walk(obj,[],0);return out

def first_recursive(obj,keys):
    if isinstance(obj,dict):
        for k in keys:
            if k in obj and (isinstance(obj[k],(str,int,float,bool)) or obj[k] is None):return obj[k]
        for k in sorted(obj):
            v=first_recursive(obj[k],keys)
            if v is not None:return v
    elif isinstance(obj,list):
        for z in obj:
            v=first_recursive(z,keys)
            if v is not None:return v
    return None

def metric_summary(obj):
    flat=flatten(obj);lower=[(p.lower(),v) for p,v in flat]
    def bvals(tokens):
        return [v for p,v in lower if isinstance(v,bool) and any(t in p for t in tokens)]
    def nums(tokens):
        return [float(v) for p,v in lower if isinstance(v,(int,float)) and not isinstance(v,bool) and any(t in p for t in tokens)]
    fb=bvals(('fresh','hidden','full_domain'));fn=nums(('fresh_score','fresh_blind','hidden_score','full_domain_score','candidate_score'))
    has_f=bool(fb or fn);fp=(any(fb) or any(x>=.90 for x in fn)) if has_f else False
    ab=bvals(('ablation','causal_drop','material_drop'));an=nums(('ablation_drop','causal_gain','causal_drop'));cand=nums(('candidate_score',));absco=nums(('ablation_score',))
    has_a=bool(ab or an or absco);ap=any(ab) or any(x>=.20 for x in an)
    if cand and absco:ap=ap or (max(cand)-min(absco)>=.20)
    rb=bvals(('regression','restore','integrity','rollback'));has_r=bool(rb);rp=any(rb) if rb else False
    sb=bvals(('unknown','conflict','fail_closed','safety'));has_s=bool(sb);sp=any(sb) if sb else False
    cu=None
    for p,v in lower:
        if isinstance(v,bool) and ('canonical_unchanged' in p or 'canonical_head_immutable' in p):cu=bool(v);break
    if cu is None:
        cm=first_recursive(obj,('canonical_mutation',))
        if isinstance(cm,bool):cu=not cm
    roll=first_recursive(obj,('rollback_available','rollback_parent_available'))
    promo=first_recursive(obj,('promotion_applied','automatic_canonical_promotion'))
    return {'has_fresh':has_f,'fresh_positive':bool(fp),'has_ablation':has_a,'ablation_positive':bool(ap),
      'has_regression_restore_integrity':has_r,'regression_restore_integrity_positive':bool(rp),
      'has_safety_evidence':has_s,'safety_positive':bool(sp),'canonical_unchanged':bool(cu) if cu is not None else False,
      'rollback_available':bool(roll) if isinstance(roll,bool) else False,'promotion_applied':bool(promo) if isinstance(promo,bool) else False,
      'evidence_density':sum(map(int,[has_f,has_a,has_r,has_s,cu is not None,roll is not None]))}

# Rehydrate exact historical blobs into the same evidence representation as corpus V1.
hist_rows=[]
for r0 in hist.get('rows') or []:
    if r0.get('outcome') not in ('PASS','WITHHOLD'):continue
    b=subprocess.run(['git','cat-file','blob',r0['git_object']],cwd=REPO,capture_output=True,check=True).stdout
    obj=json.loads(b.decode('utf-8'))
    r=dict(r0)
    pth=str(r.get('path') or '')
    r['source_class']='RECEIPT' if pth.startswith('receipts/') else ('CANDIDATE' if pth.startswith('candidates/kernel-self-generated/') else ('EXPERIENCE' if pth.startswith('experience/') else 'HISTORICAL'))
    r['metrics']=metric_summary(obj)
    hist_rows.append(r)
if len(hist_rows)<40:raise RuntimeError('REHYDRATED_HISTORICAL_ROWS_TOO_SMALL')

def action(r):
    if r['outcome']=='PASS':return 'COMMIT' if not r.get('next_required_capability') else 'CONTINUE'
    return 'REVISE' if r.get('next_required_capability') else 'SEEK_EVIDENCE'

# Stratified blind transfer: every third item inside each action class; exact hashes fixed before model selection.
adapt=[];fresh=[]
for a in ('COMMIT','CONTINUE','REVISE','SEEK_EVIDENCE'):
    xs=sorted([r for r in hist_rows if action(r)==a],key=lambda r:(r['sha256'],r['path']))
    for i,r in enumerate(xs):
        (fresh if i%3==0 else adapt).append(r)
fresh=sorted(fresh,key=lambda r:(r['sha256'],r['path']));adapt=sorted(adapt,key=lambda r:(r['sha256'],r['path']))
fresh_counts={a:sum(action(r)==a for r in fresh) for a in ('COMMIT','CONTINUE','REVISE','SEEK_EVIDENCE')}
adapt_counts={a:sum(action(r)==a for r in adapt) for a in fresh_counts}
if min(fresh_counts.values())<3:raise RuntimeError('HISTORICAL_FRESH_CLASS_TOO_SMALL:'+str(fresh_counts))

base_rows=[r for r in (base.get('rows') or []) if r.get('outcome') in ('PASS','WITHHOLD')]
dev_rows=base_rows+adapt

def terminal_features(r):
    m=r['metrics']
    return {'fresh_positive':1.0 if m['fresh_positive'] else 0.0,'has_fresh':1.0 if m['has_fresh'] else 0.0,
      'ablation_positive':1.0 if m['ablation_positive'] else 0.0,'has_ablation':1.0 if m['has_ablation'] else 0.0,
      'regression_positive':1.0 if m['regression_restore_integrity_positive'] else 0.0,'has_regression':1.0 if m['has_regression_restore_integrity'] else 0.0,
      'safety_positive':1.0 if m['safety_positive'] else 0.0,'has_safety':1.0 if m['has_safety_evidence'] else 0.0,
      'canonical_unchanged':1.0 if m['canonical_unchanged'] else 0.0,'rollback_available':1.0 if m['rollback_available'] else 0.0,
      'promotion_applied':1.0 if m['promotion_applied'] else 0.0,'evidence_density':float(m['evidence_density'])/6.0,
      'source_receipt':1.0 if r['source_class']=='RECEIPT' else 0.0,'source_candidate':1.0 if r['source_class']=='CANDIDATE' else 0.0,
      'source_experience':1.0 if r['source_class']=='EXPERIENCE' else 0.0,'source_legacy':1.0 if r['source_class']=='LEGACY_REDERIVED' else 0.0,
      'domain_code':1.0 if r['domain']=='CODE' else 0.0,'domain_representation':1.0 if r['domain']=='REPRESENTATION' else 0.0,
      'domain_cognitive':1.0 if r['domain']=='COGNITIVE' else 0.0,'domain_execution':1.0 if r['domain']=='EXECUTION' else 0.0,
      'domain_memory':1.0 if r['domain']=='MEMORY' else 0.0,'domain_evolution':1.0 if r['domain']=='EVOLUTION' else 0.0}

def family_score(f,m,cases):
    if not cases:return 0.0
    if f=='CART_AXIS':return tree_acc(m,cases)
    if f=='KNN_STRATEGY':return strategy_accuracy(m,cases)
    return centroid_accuracy(m,cases)
def family_pred(f,m,x):
    if f=='CART_AXIS':return tree_predict(m,x)
    if f=='KNN_STRATEGY':return knn_predict(m,x)
    return centroid_predict(m,x)
def fit_family(f,param,cases):
    if f=='CART_AXIS':return fit_tree(cases,int(param))
    if f=='KNN_STRATEGY':return fit_knn_strategy(cases,int(param))
    return fit_centroid_strategy(cases,int(param))

terminal_dev=[r for r in dev_rows if not r.get('next_required_capability')]
terminal_fresh=[r for r in fresh if not r.get('next_required_capability')]
td=[(terminal_features(r),r['outcome']=='PASS',r['sha256']) for r in terminal_dev]
tf=[(terminal_features(r),r['outcome']=='PASS') for r in terminal_fresh]
if sum(y for _,y,_ in td)<10 or sum(not y for _,y,_ in td)<10:raise RuntimeError('TERMINAL_DEV_CLASS_TOO_SMALL')
profiles=[('CART_AXIS',d,d) for d in (1,2,3,4,5)]+[('KNN_STRATEGY',k,k) for k in (1,3,5,7,9)]+[('CENTROID_STRATEGY',n,n) for n in range(1,len(td[0][0])+1)]
trials=[]
for fam,param,complexity in profiles:
    fold_scores=[];pass_hits=pass_n=with_hits=with_n=0
    for fold in range(5):
        tr=[(x,y) for x,y,h in td if int(h[:8],16)%5!=fold]
        va=[(x,y) for x,y,h in td if int(h[:8],16)%5==fold]
        if not tr or not va:continue
        m=fit_family(fam,param,tr)
        fold_scores.append(family_score(fam,m,va))
        for x,y in va:
            p=bool(family_pred(fam,m,x))
            if y:pass_n+=1;pass_hits+=p==y
            else:with_n+=1;with_hits+=p==y
    if not fold_scores:continue
    pass_recall=pass_hits/max(1,pass_n);with_recall=with_hits/max(1,with_n)
    evidence=.55*(sum(fold_scores)/len(fold_scores))+.45*min(pass_recall,with_recall)
    trials.append({'token':fam+'_'+str(param),'family':fam,'param':param,'complexity':complexity,
                   'cv_accuracy':sum(fold_scores)/len(fold_scores),'cv_pass_recall':pass_recall,'cv_withhold_recall':with_recall,'evidence':evidence})
eligible=[t for t in trials if t['cv_accuracy']>=.70 and min(t['cv_pass_recall'],t['cv_withhold_recall'])>=.65]
if not eligible:raise RuntimeError('NO_ROBUST_TERMINAL_PROFILE')
lsel=NeutralEvidenceProfileSelectorV1.select([EvidenceCandidate(token=t['token'],evidence=t['evidence'],complexity=t['complexity'],risk=0,novelty=.2) for t in eligible],
    complexity_penalty=.008,risk_penalty=.2,novelty_bonus=.01)
lc=next(t for t in eligible if t['token']==lsel['selected_token'])
lmodel=fit_family(lc['family'],lc['param'],[(x,y) for x,y,_ in td])
term_fresh=family_score(lc['family'],lmodel,tf)
tp=[(x,y) for x,y in tf if y];tw=[(x,y) for x,y in tf if not y]
term_pass=family_score(lc['family'],lmodel,tp);term_with=family_score(lc['family'],lmodel,tw)

lg0=v6['genes']['LOGIC'];tg=v6['genes']['THINKING'];ig=v6['genes']['INTELLIGENCE']
logic_gene={'schema':'yado.g2.global_experience_logic_gene.v4',
 'gene_id':'GENE-G2-GLOBAL-EXPERIENCE-LOGIC-V4-'+digest({'parent':lg0['gene_digest'],'historical':hist['corpus_digest'],'model':lmodel})[:16],
 'organ':'LOGIC','heritage':[lg0['gene_id'],'ALG-G2-BUDGET-ADAPTIVE-COMPOSITIONAL-LOGIC-V2'],
 'general_model':lg0['general_model'],'terminal_expert_family':lc['family'],'terminal_expert_model':lmodel,
 'terminal_profile':lc,'native_selector':lsel,'historical_adaptation_count':len([r for r in adapt if not r.get('next_required_capability')]),
 'historical_fresh_count':len(terminal_fresh),'historical_fresh':term_fresh,'historical_pass_recall':term_pass,'historical_withhold_recall':term_with,
 'promotion_state':'SHADOW_ONLY','origin':'YADO_NATIVE_TERMINAL_LOGIC_RELEARNED_WITH_UNSEEN_GIT_HISTORY_TRANSFER'}
logic_gene['gene_digest']=digest(logic_gene)

lgen=logic_gene['general_model'];tmodel=tg['model'];imodel=ig['model']
def general_logic_features(r):
    m=r['metrics']
    return {'has_fresh':m['has_fresh'],'fresh_positive':m['fresh_positive'],'has_ablation':m['has_ablation'],'ablation_positive':m['ablation_positive'],
      'has_regression_restore_integrity':m['has_regression_restore_integrity'],'regression_restore_integrity_positive':m['regression_restore_integrity_positive'],
      'has_safety_evidence':m['has_safety_evidence'],'safety_positive':m['safety_positive'],'canonical_unchanged':m['canonical_unchanged'],
      'rollback_available':m['rollback_available'],'promotion_applied':m['promotion_applied'],'next_present':bool(r.get('next_required_capability')),
      'source_is_receipt':r['source_class']=='RECEIPT','source_is_candidate':r['source_class']=='CANDIDATE','source_is_legacy':r['source_class']=='LEGACY_REDERIVED'}
def intel_features(r):
    m=r['metrics']
    return {'status_pass':1.0 if r['outcome']=='PASS' else 0.0,'status_withhold':1.0 if r['outcome']=='WITHHOLD' else 0.0,
      'next_present':1.0 if r.get('next_required_capability') else 0.0,'same_domain_next':1.0 if r.get('next_required_capability') and r.get('next_domain')==r.get('domain') else 0.0,
      'fresh_positive':1.0 if m['fresh_positive'] else 0.0,'ablation_positive':1.0 if m['ablation_positive'] else 0.0,
      'canonical_unchanged':1.0 if m['canonical_unchanged'] else 0.0,'rollback_available':1.0 if m['rollback_available'] else 0.0,'evidence_density':float(m['evidence_density'])/6.0,
      'domain_code':1.0 if r['domain']=='CODE' else 0.0,'domain_representation':1.0 if r['domain']=='REPRESENTATION' else 0.0,
      'domain_cognitive':1.0 if r['domain']=='COGNITIVE' else 0.0,'domain_execution':1.0 if r['domain']=='EXECUTION' else 0.0,
      'domain_memory':1.0 if r['domain']=='MEMORY' else 0.0,'domain_evolution':1.0 if r['domain']=='EVOLUTION' else 0.0}
def row_context(r):
    return {'START_PASS':r.get('outcome')=='PASS','START_WITHHOLD':r.get('outcome')=='WITHHOLD','START_HAS_NEXT':bool(r.get('next_required_capability')),
      'START_NO_NEXT':not bool(r.get('next_required_capability')),'START_SAME_DOMAIN_NEXT':bool(r.get('next_required_capability')) and r.get('next_domain')==r.get('domain'),
      'START_FRESH_POSITIVE':bool(r['metrics'].get('fresh_positive')),'START_ABLATION_POSITIVE':bool(r['metrics'].get('ablation_positive')),
      'WINDOW_DOMAIN_STABLE':True,'WINDOW_HAS_WITHHOLD':r.get('outcome')=='WITHHOLD','WINDOW_HAS_PASS':r.get('outcome')=='PASS'}
def think_pref(r):
    roles=['ACCEPT','ADVANCE','REVISE','SEEK_EVIDENCE'];acts=[{'id':'STD-'+x,'role':x} for x in roles]
    ids=plan_multicontext(tmodel,row_context(r),acts);by={a['id']:a['role'] for a in acts}
    return by[ids[0]] if ids else 'SEEK_EVIDENCE'
def organ_features(r):
    lgp=bool(tree_predict(lgen,general_logic_features(r)));ltp=bool(family_pred(lc['family'],lmodel,terminal_features(r)))
    ip=str(tree_predict(imodel,intel_features(r)));tp=think_pref(r)
    return {'state_known':1.0,'logic_general':1.0 if lgp else 0.0,'logic_terminal':1.0 if ltp else 0.0,
      'intel_stop':1.0 if ip=='STOP' else 0.0,'intel_retry':1.0 if ip=='RETRY' else 0.0,'intel_advance':1.0 if ip=='ADVANCE' else 0.0,
      'think_accept':1.0 if tp=='ACCEPT' else 0.0,'think_advance':1.0 if tp=='ADVANCE' else 0.0,'think_revise':1.0 if tp=='REVISE' else 0.0,'think_seek':1.0 if tp=='SEEK_EVIDENCE' else 0.0}

cdev=[(organ_features(r),action(r),r['sha256']) for r in dev_rows]
cfresh=[(organ_features(r),action(r)) for r in fresh]
groups={'LOGIC':['logic_general','logic_terminal'],'THINKING':['think_accept','think_advance','think_revise','think_seek'],'INTELLIGENCE':['intel_stop','intel_retry','intel_advance']}
def ablate_cases(cases,group):
    out=[]
    for item in cases:
        x,y=item[:2];z=dict(x)
        for k in groups[group]:z[k]=0.0
        out.append((z,y))
    return out

cprofiles=[('CART_AXIS',d,d) for d in (1,2,3,4,5)]+[('KNN_STRATEGY',k,k) for k in (1,3,5,7,9)]+[('CENTROID_STRATEGY',n,n) for n in range(1,len(cdev[0][0])+1)]
ctrials=[]
for fam,param,complexity in cprofiles:
    folds=[];drops={g:[] for g in groups}
    for fold in range(5):
        tr=[(x,y) for x,y,h in cdev if int(h[:8],16)%5!=fold];va=[(x,y) for x,y,h in cdev if int(h[:8],16)%5==fold]
        if not tr or not va:continue
        m=fit_family(fam,param,tr);s=family_score(fam,m,va);folds.append(s)
        for g in groups:drops[g].append(s-family_score(fam,m,ablate_cases(va,g)))
    if not folds:continue
    md={g:sum(v)/len(v) for g,v in drops.items()}
    mean=sum(folds)/len(folds);ev=mean+.4*min(md.values())
    ctrials.append({'token':fam+'_'+str(param),'family':fam,'param':param,'complexity':complexity,'cv_accuracy':mean,'cv_drops':md,'evidence':ev})
celig=[t for t in ctrials if t['cv_accuracy']>=.72 and all(t['cv_drops'][g]>=.015 for g in groups)]
if not celig:raise RuntimeError('NO_HISTORICAL_TRANSFER_COGNITIVE_PROFILE')
csel=NeutralEvidenceProfileSelectorV1.select([EvidenceCandidate(token=t['token'],evidence=t['evidence'],complexity=t['complexity'],risk=0,novelty=.2) for t in celig],
    complexity_penalty=.008,risk_penalty=.2,novelty_bonus=.01)
cc=next(t for t in celig if t['token']==csel['selected_token'])
cmodel=fit_family(cc['family'],cc['param'],[(x,y) for x,y,_ in cdev])
cfresh_score=family_score(cc['family'],cmodel,cfresh)
fresh_class={}
for a in ('COMMIT','CONTINUE','REVISE','SEEK_EVIDENCE'):
    xs=[z for z in cfresh if z[1]==a];fresh_class[a]={'count':len(xs),'accuracy':family_score(cc['family'],cmodel,xs)}
fresh_drops={g:cfresh_score-family_score(cc['family'],cmodel,ablate_cases(cfresh,g)) for g in groups}

# Regression on entire old V1 corpus is allowed now because it is no longer fresh.
old=[(organ_features(r),action(r)) for r in base_rows]
old_score=family_score(cc['family'],cmodel,old)
old_class={}
for a in ('COMMIT','CONTINUE','REVISE','SEEK_EVIDENCE'):
    xs=[z for z in old if z[1]==a];old_class[a]={'count':len(xs),'accuracy':family_score(cc['family'],cmodel,xs)}

cg={'schema':'yado.g2.global_experience_cognitive_gene.v7',
 'gene_id':'GENE-G2-GLOBAL-EXPERIENCE-COGNITIVE-V7-'+digest({'parent':v6['genes']['COGNITIVE']['gene_digest'],'logic':logic_gene['gene_digest'],'model':cmodel,'historical':hist['corpus_digest']})[:16],
 'organ':'CONSCIOUS_WORKSPACE','heritage':[v6['genes']['COGNITIVE']['gene_id'],logic_gene['gene_id'],tg['gene_id'],ig['gene_id']],
 'strategy_family':cc['family'],'selected_profile':cc,'native_selector':csel,'model':cmodel,
 'historical_fresh':cfresh_score,'historical_class_scores':fresh_class,'historical_organ_ablation_drops':fresh_drops,
 'old_corpus_regression':old_score,'old_corpus_class_scores':old_class,
 'safety_program_id':v6['genes']['COGNITIVE']['safety_program_id'],'safety_program_digest':v6['genes']['COGNITIVE']['safety_program_digest'],
 'unknown_fail_closed':True,'promotion_state':'SHADOW_ONLY',
 'origin':'YADO_NATIVE_COGNITIVE_RELEARNING_WITH_UNSEEN_GIT_HISTORY_TRANSFER'}
cg['gene_digest']=digest(cg)

genes={'LOGIC':logic_gene,'THINKING':tg,'INTELLIGENCE':ig,'COGNITIVE':cg}
genome={'schema':'yado.g2.global_experience_cognitive_genome.v7',
 'genome_id':'GENOME-G2-GLOBAL-EXPERIENCE-COGNITIVE-V7-'+digest({k:v['gene_digest'] for k,v in genes.items()})[:16],
 'generation':'G2_SHADOW','base_corpus_digest':base.get('corpus_digest'),'historical_corpus_digest':hist.get('corpus_digest'),
 'organs':{k:v['gene_id'] for k,v in genes.items()},'promotion_state':'SHADOW_ONLY','automatic_canonical_promotion':False}
genome['genome_digest']=digest(genome)

core=UnifiedYADOCoreV1(REPO);head_before=copy.deepcopy(core.head)
checks={
 'new_historical_evidence_consumed':len(hist_rows)==50,
 'historical_fresh_stratified':min(fresh_counts.values())>=3,
 'historical_fresh_not_in_adaptation':not ({r['sha256'] for r in fresh}&{r['sha256'] for r in adapt}),
 'terminal_native_selection':lsel.get('selected_token')==lc['token'],
 'terminal_historical_fresh_ge_0_75':term_fresh>=.75,
 'terminal_historical_pass_ge_2_3':term_pass>=2/3,
 'terminal_historical_withhold_ge_2_3':term_with>=2/3,
 'new_logic_identity':logic_gene['gene_id']!=v6['genes']['LOGIC']['gene_id'],
 'thinking_preserved':genes['THINKING']==tg,'intelligence_preserved':genes['INTELLIGENCE']==ig,
 'cognitive_native_selection':csel.get('selected_token')==cc['token'],
 'cognitive_historical_fresh_ge_0_75':cfresh_score>=.75,
 'cognitive_all_historical_classes_ge_0_60':all(v['accuracy']>=.60 for v in fresh_class.values()),
 'cognitive_historical_logic_causal':fresh_drops['LOGIC']>=.02,
 'cognitive_historical_thinking_causal':fresh_drops['THINKING']>=.02,
 'cognitive_historical_intelligence_causal':fresh_drops['INTELLIGENCE']>=.02,
 'old_corpus_regression_ge_0_93':old_score>=.93,
 'old_commit_ge_0_70':old_class['COMMIT']['accuracy']>=.70,
 'old_seek_evidence_ge_0_70':old_class['SEEK_EVIDENCE']['accuracy']>=.70,
 'v6_safety_preserved':bool((v6.get('checks') or {}).get('unknown_fail_closed')) and float((v6.get('safety_gate') or {}).get('candidate_score') or 0)==1.0,
 'external_models_used':False,'host_written_models':False,'automatic_canonical_promotion':False,
 'canonical_unchanged':core.head.get('canonical_head_digest')==head_before.get('canonical_head_digest')}
false_keys=['external_models_used','host_written_models','automatic_canonical_promotion']
passed=all(v is True for k,v in checks.items() if k not in false_keys) and all(checks[k] is False for k in false_keys)
status='PASS_SHADOW_G2_GLOBAL_EXPERIENCE_TERMINAL_LOGIC_HISTORICAL_TRANSFER_V1' if passed else 'WITHHOLD_G2_GLOBAL_EXPERIENCE_TERMINAL_LOGIC_HISTORICAL_TRANSFER_V1'

experience={'schema':'yado.g2.global_experience_terminal_logic_historical_transfer.experience.v1','status':'TRAINED' if passed else 'WITHHOLD',
 'historical_counts':{'total':len(hist_rows),'adapt':len(adapt),'fresh':len(fresh),'adapt_by_action':adapt_counts,'fresh_by_action':fresh_counts},
 'terminal_trials':trials,'terminal_selected':logic_gene['terminal_profile'],'terminal_fresh':term_fresh,'terminal_pass_recall':term_pass,'terminal_withhold_recall':term_with,
 'cognitive_trials':ctrials,'cognitive_selected':cg['selected_profile'],'cognitive_historical_fresh':cfresh_score,
 'cognitive_historical_class_scores':fresh_class,'cognitive_historical_organ_drops':fresh_drops,
 'old_corpus_regression':old_score,'old_corpus_class_scores':old_class,'genes':genes,'genome':genome,'checks':checks,'canonical_mutation':False,
 'semantic_boundary':'UNSEEN HISTORICAL GIT BLOBS NOT PRESENT IN GLOBAL CORPUS V1 ARE STRATIFIED BEFORE SELECTION. ONLY ADAPTATION BLOBS MAY INFLUENCE MODEL FIT; FRESH HISTORICAL BLOBS REMAIN BLIND UNTIL FINAL TRANSFER EVALUATION. OLD V1 HOLDOUT IS NOW REGRESSION DATA, NOT CLAIMED FRESH. THINKING AND INTELLIGENCE ARE PRESERVED.'
}
experience['experience_digest']=digest(experience);EXP.parent.mkdir(parents=True,exist_ok=True);EXP.write_text(json.dumps(experience,indent=2,sort_keys=True)+'\n')
report={'schema':'yado.g2.global_experience_terminal_logic_historical_transfer.v1','status':status,
 'historical_counts':experience['historical_counts'],'terminal_selected':logic_gene['terminal_profile'],'terminal_historical_fresh':term_fresh,
 'terminal_historical_pass_recall':term_pass,'terminal_historical_withhold_recall':term_with,'cognitive_selected':cg['selected_profile'],
 'cognitive_historical_fresh':cfresh_score,'cognitive_historical_class_scores':fresh_class,'cognitive_historical_organ_drops':fresh_drops,
 'old_corpus_regression':old_score,'old_corpus_class_scores':old_class,'gene_ids':{k:v['gene_id'] for k,v in genes.items()},
 'genome_id':genome['genome_id'],'genome_digest':genome['genome_digest'],'checks':checks,'canonical_mutation':False,'promotion_applied':False,
 'next_required_capability':'GLOBAL_EXPERIENCE_COGNITIVE_CANONICAL_ADMISSION_V1' if passed else 'GLOBAL_EXPERIENCE_TERMINAL_LOGIC_HISTORICAL_TRANSFER_REPAIR_V2',
 'semantic_boundary':experience['semantic_boundary']}
report['receipt_sha256']=digest(report);OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
print(json.dumps({'status':status,'historical_counts':report['historical_counts'],'terminal':{'selected':report['terminal_selected'],'fresh':term_fresh,'pass_recall':term_pass,'withhold_recall':term_with},
 'cognitive':{'selected':report['cognitive_selected'],'fresh':cfresh_score,'class_scores':fresh_class,'organ_drops':fresh_drops},
 'old_regression':old_score,'old_class_scores':old_class,'gene_ids':report['gene_ids'],'genome_id':genome['genome_id'],
 'next_required_capability':report['next_required_capability'],'receipt_sha256':report['receipt_sha256']},indent=2,sort_keys=True))
if not passed:raise SystemExit(2)
