from __future__ import annotations
from pathlib import Path
from collections import Counter,defaultdict
import copy,datetime,hashlib,json,math,os,random,sys,urllib.request

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
PKG=ROOT/'yado_rc8_v36'
sys.path[:0]=[str(ROOT),str(PKG)]

from yado_organ_runtime_native_v1 import fit_tree,tree_predict,tree_acc
from yado_cognitive_growth_runtime_v1 import learn_multicontext_precedence,plan_multicontext,fit_knn_strategy,knn_predict,strategy_accuracy,fit_centroid_strategy,centroid_predict,centroid_accuracy
from yado_neutral_evidence_profile_selector_v1 import NeutralEvidenceProfileSelectorV1,EvidenceCandidate
from yado_unified_core_v1 import UnifiedYADOCoreV1

PARENT=REPO/'experience/yado-multidomain-real-data-training-v1.json'
COMP=REPO/'experience/yado-multidomain-cognitive-composition-training-v1.json'
OUT=REPO/'candidates/kernel-self-generated/g2-real-yado-recovery-cognitive-task-v1.json'
EXP=REPO/'experience/yado-real-yado-recovery-cognitive-task-v1.json'

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def digest(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
parent=load(PARENT);comp=load(COMP)
if parent.get('status')!='TRAINED':raise RuntimeError('REAL_DATA_PARENT_REQUIRED')
if comp.get('status')!='TRAINED':raise RuntimeError('CONTROLLED_COGNITIVE_PARENT_REQUIRED')

token=os.getenv('GITHUB_TOKEN') or ''
repo_name=os.getenv('GITHUB_REPOSITORY','v37025337-pixel/EVA')
headers={'Accept':'application/vnd.github+json','User-Agent':'YADO-G2-REAL-RECOVERY-COGNITIVE/1.0'}
if token:headers['Authorization']='Bearer '+token

page_blobs=[];runs=[]
for page in range(1,21):
    url=f'https://api.github.com/repos/{repo_name}/actions/runs?per_page=100&page={page}'
    req=urllib.request.Request(url,headers=headers)
    with urllib.request.urlopen(req,timeout=30) as resp:b=resp.read()
    page_blobs.append(b)
    runs.extend((json.loads(b.decode('utf-8')).get('workflow_runs') or []))
source_sha=hashlib.sha256(b''.join(page_blobs)).hexdigest()
runs=[r for r in runs if str(r.get('conclusion') or '') in ('success','failure')]
runs.sort(key=lambda r:(str(r.get('created_at') or ''),int(r.get('id') or 0)))
if len(runs)<1500:raise RuntimeError('REAL_RUN_HISTORY_TOO_SMALL:'+str(len(runs)))

by=defaultdict(list)
for r in runs:by[str(r.get('name') or '')].append(r)
episodes=[]
for name,xs in by.items():
    xs.sort(key=lambda r:(str(r.get('created_at') or ''),int(r.get('id') or 0)))
    streak=0
    for i in range(len(xs)-1):
        cur=xs[i];nxt=xs[i+1]
        streak=streak+1 if cur.get('conclusion')=='failure' else 0
        if cur.get('conclusion')!='failure':continue
        prev=xs[i-1] if i>0 else None
        try:
            ca=datetime.datetime.fromisoformat(str(cur['created_at']).replace('Z','+00:00'))
            ua=datetime.datetime.fromisoformat(str(cur['updated_at']).replace('Z','+00:00'))
            nb=datetime.datetime.fromisoformat(str(nxt['updated_at']).replace('Z','+00:00'))
            nc=datetime.datetime.fromisoformat(str(nxt['created_at']).replace('Z','+00:00'))
            cur_dur=max(0.0,(ua-ca).total_seconds());next_dur=max(0.0,(nb-nc).total_seconds())
        except Exception:
            cur_dur=0.0;next_dur=0.0
        episodes.append({
          'workflow':name,'run_id':str(cur.get('id')),'next_run_id':str(nxt.get('id')),
          'created_at':str(cur.get('created_at') or ''),'current_duration':cur_dur,'next_duration':next_dur,
          'next_success':nxt.get('conclusion')=='success','failure_streak':streak,'run_attempt':int(cur.get('run_attempt') or 1),
          'same_sha_prev':bool(prev and prev.get('head_sha')==cur.get('head_sha')),
          'event':str(cur.get('event') or ''),'title':str(cur.get('display_title') or ''),
        })
episodes.sort(key=lambda e:(e['created_at'],int(e['run_id'])))
if len(episodes)<90:raise RuntimeError('FAILURE_EPISODES_TOO_SMALL:'+str(len(episodes)))
n=len(episodes);i1=int(n*.60);i2=int(n*.80)
train0,validation0,blind0=episodes[:i1],episodes[i1:i2],episodes[i2:]
if min(len(train0),len(validation0),len(blind0))<18:raise RuntimeError('CHRONOLOGICAL_SPLIT_TOO_SMALL')

# Thresholds derive from training history only.
durs=sorted(e['current_duration'] for e in train0)
q50=durs[int(.50*(len(durs)-1))];q75=durs[int(.75*(len(durs)-1)]
recovery_durs=sorted(e['next_duration'] for e in train0 if e['next_success'])
if len(recovery_durs)<10:raise RuntimeError('RECOVERY_TRAIN_TOO_SMALL')
rec_med=recovery_durs[len(recovery_durs)//2]

TOKENS=('coding','audit','logic','intelligence','representation','cognitive','repair','evolution','admission','transfer','source','module','rewrite','self','kernel')
def features(e):
    text=(e['workflow']+' '+e['title']).lower()
    x={
      'duration_ge_q50':1.0 if e['current_duration']>=q50 else 0.0,
      'duration_ge_q75':1.0 if e['current_duration']>=q75 else 0.0,
      'streak_ge_2':1.0 if e['failure_streak']>=2 else 0.0,
      'streak_ge_3':1.0 if e['failure_streak']>=3 else 0.0,
      'attempt_gt_1':1.0 if e['run_attempt']>1 else 0.0,
      'same_sha_prev':1.0 if e['same_sha_prev'] else 0.0,
      'event_push':1.0 if e['event']=='push' else 0.0,
      'event_dispatch':1.0 if e['event']=='workflow_dispatch' else 0.0,
      'event_schedule':1.0 if e['event']=='schedule' else 0.0,
    }
    for t in TOKENS:x['tok_'+t]=1.0 if t in text else 0.0
    return x

def strategy_truth(e):
    if not e['next_success']:return 'ESCALATE'
    return 'QUICK' if e['next_duration']<=rec_med else 'DEEP'
def risk_truth(e):
    if e['failure_streak']>=2 or e['current_duration']>=q75:return 'HIGH'
    if e['current_duration']>=q50 or e['same_sha_prev'] or e['run_attempt']>1:return 'MEDIUM'
    return 'LOW'
def action_truth(e):
    s=strategy_truth(e);r=risk_truth(e)
    if not e['next_success']:return 'WITHHOLD'
    if s=='DEEP':return 'REPLAN_VERIFY'
    if s=='QUICK' and r=='LOW':return 'ACT_REPAIR'
    return 'VERIFY'

def macro_acc(pred,truth):
    labels=sorted(set(truth),key=str)
    vals=[]
    for y in labels:
        idx=[i for i,t in enumerate(truth) if t==y]
        if idx:vals.append(sum(pred[i]==truth[i] for i in idx)/len(idx))
    return sum(vals)/len(vals) if vals else 0.0
def class_scores(pred,truth):
    out={}
    for y in sorted(set(truth),key=str):
        idx=[i for i,t in enumerate(truth) if t==y]
        out[y]={'count':len(idx),'accuracy':sum(pred[i]==truth[i] for i in idx)/len(idx)}
    return out

# -------- LOGIC: predict empirical next-run recovery --------
ltr=[(features(e),bool(e['next_success'])) for e in train0]
lva=[(features(e),bool(e['next_success'])) for e in validation0]
lbl=[(features(e),bool(e['next_success'])) for e in blind0]
logic_trials=[]
for depth in (1,2,3,4,5,6,7):
    m=fit_tree(ltr,depth);vp=[bool(tree_predict(m,x)) for x,_ in lva];vy=[y for _,y in lva]
    logic_trials.append({'token':'CART_D'+str(depth),'depth':depth,'complexity':depth,'validation_macro':macro_acc(vp,vy),'model':m})
lsel=NeutralEvidenceProfileSelectorV1.select([EvidenceCandidate(token=t['token'],evidence=t['validation_macro'],complexity=t['complexity'],risk=0,novelty=.2) for t in logic_trials],
 complexity_penalty=.006,risk_penalty=.2,novelty_bonus=.01)
lc=next(t for t in logic_trials if t['token']==lsel['selected_token'])
lmodel=fit_tree(ltr+lva,lc['depth'])
lp=[bool(tree_predict(lmodel,x)) for x,_ in lbl];ly=[y for _,y in lbl]
logic_fresh=macro_acc(lp,ly);logic_classes=class_scores(lp,ly)
lmaj=Counter(y for _,y in ltr+lva).most_common(1)[0][0]
logic_ablation=macro_acc([lmaj]*len(ly),ly)

# -------- THINKING: choose recovery ordering from the same failure episode --------
ROLE_SET=['OBSERVE','DIAGNOSE','LOCAL_REPAIR','VERIFY','DEEP_REPLAN']
ORDERS={
 'QUICK':['OBSERVE','DIAGNOSE','LOCAL_REPAIR','VERIFY','DEEP_REPLAN'],
 'DEEP':['OBSERVE','DIAGNOSE','LOCAL_REPAIR','DEEP_REPLAN','VERIFY'],
 'ESCALATE':['OBSERVE','DIAGNOSE','DEEP_REPLAN','LOCAL_REPAIR','VERIFY'],
}
def trace(e):return ORDERS[strategy_truth(e)]
def think_episode(e,seed):
    acts=[{'id':f"{e['run_id']}-{j}",'role':r} for j,r in enumerate(ROLE_SET)]
    random.Random(seed+int(e['run_id'])%100000).shuffle(acts)
    return (features(e),acts,trace(e))
def think_predict(model,e,seed):
    ep=think_episode(e,seed);ids=plan_multicontext(model,ep[0],ep[1]);byid={a['id']:a['role'] for a in ep[1]}
    order=[byid[i] for i in ids]
    for k,v in ORDERS.items():
        if order==v:return k
    return 'UNKNOWN'
def think_macro(model,rows,seed):
    p=[think_predict(model,e,seed) for e in rows];y=[strategy_truth(e) for e in rows]
    return macro_acc(p,y),class_scores(p,y),p,y
fit_traces=[(features(e),trace(e)) for e in train0]
thinking_trials=[]
for th in (.55,.60,.67,.75,.80):
  for keys in (1,2,3,4,5):
    for sup in (2,3,4):
      m=learn_multicontext_precedence(fit_traces,threshold=th,min_support=sup,max_context_keys=keys)
      va,_,_,_=think_macro(m,validation0,5000)
      thinking_trials.append({'token':f'T{th}_K{keys}_S{sup}','threshold':th,'keys':keys,'support':sup,'complexity':keys+.25*sup,'validation_macro':va,'model':m})
tsel=NeutralEvidenceProfileSelectorV1.select([EvidenceCandidate(token=t['token'],evidence=t['validation_macro'],complexity=t['complexity'],risk=0,novelty=.2) for t in thinking_trials],
 complexity_penalty=.006,risk_penalty=.2,novelty_bonus=.01)
tc=next(t for t in thinking_trials if t['token']==tsel['selected_token'])
tmodel=learn_multicontext_precedence(fit_traces+[(features(e),trace(e)) for e in validation0],threshold=tc['threshold'],min_support=tc['support'],max_context_keys=tc['keys'])
thinking_fresh,thinking_classes,tp,ty=think_macro(tmodel,blind0,9000)
tab=learn_multicontext_precedence([({},trace(e)) for e in train0+validation0],threshold=tc['threshold'],min_support=tc['support'],max_context_keys=0)
thinking_ablation,_,_,_=think_macro(tab,blind0,11000)

# -------- INTELLIGENCE: assess current operational risk --------
itr=[(features(e),risk_truth(e)) for e in train0];iva=[(features(e),risk_truth(e)) for e in validation0];ibl=[(features(e),risk_truth(e)) for e in blind0]
intel_trials=[]
for depth in (1,2,3,4,5,6):
    m=fit_tree(itr,depth);vp=[str(tree_predict(m,x)) for x,_ in iva];vy=[y for _,y in iva]
    intel_trials.append({'token':'CART_D'+str(depth),'depth':depth,'complexity':depth,'validation_macro':macro_acc(vp,vy),'model':m})
isel=NeutralEvidenceProfileSelectorV1.select([EvidenceCandidate(token=t['token'],evidence=t['validation_macro'],complexity=t['complexity'],risk=0,novelty=.2) for t in intel_trials],
 complexity_penalty=.006,risk_penalty=.2,novelty_bonus=.01)
ic=next(t for t in intel_trials if t['token']==isel['selected_token'])
imodel=fit_tree(itr+iva,ic['depth'])
ip=[str(tree_predict(imodel,x)) for x,_ in ibl];iy=[y for _,y in ibl]
intel_fresh=macro_acc(ip,iy);intel_classes=class_scores(ip,iy)
imaj=Counter(y for _,y in itr+iva).most_common(1)[0][0]
intel_ablation=macro_acc([imaj]*len(iy),iy)

# -------- COGNITIVE: organ outputs only; final control action --------
def organ_vector(e,lm,tm,im,seed):
    x=features(e)
    lo=bool(tree_predict(lm,x))
    ts=think_predict(tm,e,seed)
    ir=str(tree_predict(im,x))
    return {
      'state_known':1.0,
      'logic_recoverable':1.0 if lo else 0.0,
      'thinking_quick':1.0 if ts=='QUICK' else 0.0,
      'thinking_deep':1.0 if ts=='DEEP' else 0.0,
      'thinking_escalate':1.0 if ts=='ESCALATE' else 0.0,
      'intel_low':1.0 if ir=='LOW' else 0.0,
      'intel_medium':1.0 if ir=='MEDIUM' else 0.0,
      'intel_high':1.0 if ir=='HIGH' else 0.0,
    }

# Initial stacking models trained on training interval only.
ltmp=fit_tree(ltr,lc['depth'])
ttmp=learn_multicontext_precedence(fit_traces,threshold=tc['threshold'],min_support=tc['support'],max_context_keys=tc['keys'])
itmp=fit_tree(itr,ic['depth'])
ctr=[(organ_vector(e,ltmp,ttmp,itmp,13000),action_truth(e)) for e in train0]
cva=[(organ_vector(e,ltmp,ttmp,itmp,14000),action_truth(e)) for e in validation0]

def cfit(f,param,cases):
    if f=='CART_AXIS':return fit_tree(cases,int(param))
    if f=='KNN_STRATEGY':return fit_knn_strategy(cases,int(param))
    return fit_centroid_strategy(cases,int(param))
def cpred(f,m,x):
    if f=='CART_AXIS':return tree_predict(m,x)
    if f=='KNN_STRATEGY':return knn_predict(m,x)
    return centroid_predict(m,x)
def cscore(f,m,cases):
    p=[str(cpred(f,m,x)) for x,_ in cases];y=[str(y) for _,y in cases]
    return macro_acc(p,y)
GROUPS={'LOGIC':['logic_recoverable'],'THINKING':['thinking_quick','thinking_deep','thinking_escalate'],'INTELLIGENCE':['intel_low','intel_medium','intel_high']}
def ablate(cases,g):
    out=[]
    for x,y in cases:
        z=dict(x)
        for k in GROUPS[g]:z[k]=0.0
        out.append((z,y))
    return out

c_trials=[]
profiles=[('CART_AXIS',d,d) for d in (1,2,3,4,5)]+[('KNN_STRATEGY',k,k) for k in (1,3,5,7)]+[('CENTROID_STRATEGY',n,n) for n in (1,2,3,4,5,6,7,8)]
for fam,param,complexity in profiles:
    m=cfit(fam,param,ctr);va=cscore(fam,m,cva)
    drops={g:va-cscore(fam,m,ablate(cva,g)) for g in GROUPS}
    c_trials.append({'token':fam+'_'+str(param),'family':fam,'param':param,'complexity':complexity,'validation_macro':va,'drops':drops,'model':m})
eligible=[t for t in c_trials if t['validation_macro']>=.50]
if not eligible:raise RuntimeError('NO_COGNITIVE_REAL_TASK_MODEL_GE_050')
csel=NeutralEvidenceProfileSelectorV1.select([EvidenceCandidate(token=t['token'],evidence=t['validation_macro']+.25*min(t['drops'].values()),complexity=t['complexity'],risk=0,novelty=.2) for t in eligible],
 complexity_penalty=.006,risk_penalty=.2,novelty_bonus=.01)
cc=next(t for t in eligible if t['token']==csel['selected_token'])

# Final blind uses refit organ models and cognitive fit on train+validation organ outputs.
cdev=[(organ_vector(e,lmodel,tmodel,imodel,15000),action_truth(e)) for e in train0+validation0]
cblind=[(organ_vector(e,lmodel,tmodel,imodel,16000),action_truth(e)) for e in blind0]
cmodel=cfit(cc['family'],cc['param'],cdev)
cp=[str(cpred(cc['family'],cmodel,x)) for x,_ in cblind];cy=[str(y) for _,y in cblind]
cognitive_fresh=macro_acc(cp,cy);cognitive_classes=class_scores(cp,cy)
cognitive_drops={g:cognitive_fresh-cscore(cc['family'],cmodel,ablate(cblind,g)) for g in GROUPS}
single_scores={}
for g,keys in GROUPS.items():
    xs=[]
    for x,y in cblind:
        z={k:0.0 for k in x};z['state_known']=x['state_known']
        for k in keys:z[k]=x[k]
        xs.append((z,y))
    single_scores[g]=cscore(cc['family'],cmodel,xs)
best_single=max(single_scores.values())
all_ab=cblind
for g in GROUPS:all_ab=ablate(all_ab,g)
combined_ablation=cscore(cc['family'],cmodel,all_ab)

genes={
 'LOGIC':{'gene_id':'GENE-G2-REAL-RECOVERY-LOGIC-V1-'+digest(lmodel)[:16],'model':lmodel,'parent':parent['genes']['LOGIC']['gene_id']},
 'THINKING':{'gene_id':'GENE-G2-REAL-RECOVERY-THINKING-V1-'+digest(tmodel)[:16],'model':tmodel,'parent':parent['genes']['THINKING']['gene_id']},
 'INTELLIGENCE':{'gene_id':'GENE-G2-REAL-RECOVERY-INTELLIGENCE-V1-'+digest(imodel)[:16],'model':imodel,'parent':parent['genes']['INTELLIGENCE']['gene_id']},
 'COGNITIVE':{'gene_id':'GENE-G2-REAL-RECOVERY-COGNITIVE-V1-'+digest(cmodel)[:16],'model':cmodel,'parent':comp['genes']['COGNITIVE']['gene_id']},
}
for k,v in genes.items():v['gene_digest']=digest(v)
genome={'schema':'yado.g2.real_yado_recovery_cognitive_genome.v1',
 'genome_id':'GENOME-G2-REAL-YADO-RECOVERY-V1-'+digest({k:v['gene_digest'] for k,v in genes.items()})[:16],
 'organs':{k:v['gene_id'] for k,v in genes.items()},'promotion_state':'SHADOW_ONLY','automatic_canonical_promotion':False}
genome['genome_digest']=digest(genome)

core=UnifiedYADOCoreV1(REPO);head_before=copy.deepcopy(core.head)
checks={
 'real_actions_runs_ge_1500':len(runs)>=1500,
 'failure_episodes_ge_90':len(episodes)>=90,
 'chronological_split':train0[-1]['created_at']<validation0[0]['created_at'] and validation0[-1]['created_at']<blind0[0]['created_at'],
 'logic_fresh_macro_ge_0_60':logic_fresh>=.60,
 'logic_gain_ge_0_08':logic_fresh-logic_ablation>=.08,
 'thinking_fresh_macro_ge_0_50':thinking_fresh>=.50,
 'thinking_gain_ge_0_08':thinking_fresh-thinking_ablation>=.08,
 'intelligence_fresh_macro_ge_0_90':intel_fresh>=.90,
 'intelligence_gain_ge_0_30':intel_fresh-intel_ablation>=.30,
 'cognitive_fresh_macro_ge_0_60':cognitive_fresh>=.60,
 'cognitive_beats_best_single_by_0_03':cognitive_fresh-best_single>=.03,
 'logic_causal':cognitive_drops['LOGIC']>=.03,
 'thinking_causal':cognitive_drops['THINKING']>=.03,
 'intelligence_causal':cognitive_drops['INTELLIGENCE']>=.03,
 'combined_ablation_drop_ge_0_20':cognitive_fresh-combined_ablation>=.20,
 'all_blind_action_classes_present':len(cognitive_classes)>=4 and all(v['count']>=1 for v in cognitive_classes.values()),
 'source_hashed':bool(source_sha),
 'external_models_used':False,'automatic_canonical_promotion':False,
 'canonical_unchanged':core.head.get('canonical_head_digest')==head_before.get('canonical_head_digest'),
}
false_keys=['external_models_used','automatic_canonical_promotion']
passed=all(v is True for k,v in checks.items() if k not in false_keys) and all(checks[k] is False for k in false_keys)
status='PASS_SHADOW_G2_REAL_YADO_RECOVERY_COGNITIVE_TASK_V1' if passed else 'WITHHOLD_G2_REAL_YADO_RECOVERY_COGNITIVE_TASK_V1'

metrics={
 'source':{'github_actions_pages':20,'usable_runs':len(runs),'failure_episodes':len(episodes),'source_sha256':source_sha,
           'train_count':len(train0),'validation_count':len(validation0),'blind_count':len(blind0),
           'train_end':train0[-1]['created_at'],'validation_end':validation0[-1]['created_at'],'blind_end':blind0[-1]['created_at']},
 'thresholds_from_train':{'duration_q50_s':q50,'duration_q75_s':q75,'recovery_duration_median_s':rec_med},
 'LOGIC':{'selected':{k:lc[k] for k in ('token','depth','validation_macro')},'fresh_macro':logic_fresh,'ablation_macro':logic_ablation,'drop':logic_fresh-logic_ablation,'class_scores':logic_classes},
 'THINKING':{'selected':{k:tc[k] for k in ('token','threshold','keys','support','validation_macro')},'fresh_macro':thinking_fresh,'ablation_macro':thinking_ablation,'drop':thinking_fresh-thinking_ablation,'class_scores':thinking_classes},
 'INTELLIGENCE':{'selected':{k:ic[k] for k in ('token','depth','validation_macro')},'fresh_macro':intel_fresh,'ablation_macro':intel_ablation,'drop':intel_fresh-intel_ablation,'class_scores':intel_classes},
 'COGNITIVE':{'selected':{k:cc[k] for k in ('token','family','param','validation_macro','drops')},'fresh_macro':cognitive_fresh,'class_scores':cognitive_classes,
              'organ_ablation_drops':cognitive_drops,'single_organ_scores':single_scores,'best_single':best_single,'combined_ablation':combined_ablation},
}
exp={'schema':'yado.g2.real_yado_recovery_cognitive_task.experience.v1','status':'TRAINED' if passed else 'WITHHOLD',
 'metrics':metrics,'genes':genes,'genome':genome,'checks':checks,'canonical_mutation':False,
 'semantic_boundary':'ONE SHARED REAL OPERATIONAL TASK: RECOVERY AFTER AN ACTUAL YADO GITHUB ACTIONS FAILURE. FEATURES AVAILABLE AT THE FAILED RUN OR EARLIER FEED ALL THREE ORGANS. LOGIC PREDICTS NEXT-RUN RECOVERY; THINKING PREDICTS A RECOVERY ORDER; INTELLIGENCE PREDICTS CURRENT OPERATIONAL RISK. COGNITIVE SEES ONLY ORGAN OUTPUTS AND SELECTS THE CONTROL ACTION. TARGET RECOVERY LABELS USE ACTUAL NEXT SAME-WORKFLOW OUTCOMES. THIS IS HISTORICAL CHRONOLOGICAL HOLDOUT, NOT A CLAIM OF GENERAL AUTONOMY.'}
exp['experience_digest']=digest(exp);EXP.parent.mkdir(parents=True,exist_ok=True);EXP.write_text(json.dumps(exp,indent=2,sort_keys=True,default=str)+'\n')
report={'schema':'yado.g2.real_yado_recovery_cognitive_task.v1','status':status,'metrics':metrics,'gene_ids':{k:v['gene_id'] for k,v in genes.items()},
 'genome_id':genome['genome_id'],'genome_digest':genome['genome_digest'],'checks':checks,'canonical_mutation':False,'promotion_applied':False,
 'next_required_capability':'REAL_YADO_RECOVERY_COGNITIVE_FRESH_LIVE_TRANSFER_V1' if passed else 'REAL_YADO_RECOVERY_COGNITIVE_REPAIR_V2',
 'semantic_boundary':exp['semantic_boundary']}
report['receipt_sha256']=digest(report);OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
print(json.dumps(report,indent=2,sort_keys=True))
if not passed:raise SystemExit(2)
