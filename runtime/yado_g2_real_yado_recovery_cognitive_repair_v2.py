from __future__ import annotations
from pathlib import Path
from collections import Counter,defaultdict
import copy,datetime,hashlib,json,os,random,sys,urllib.request

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
PKG=ROOT/'yado_rc8_v36'
sys.path[:0]=[str(ROOT),str(PKG)]

from yado_organ_runtime_native_v1 import fit_tree,tree_predict
from yado_cognitive_growth_runtime_v1 import learn_multicontext_precedence,plan_multicontext,fit_knn_strategy,knn_predict,fit_centroid_strategy,centroid_predict
from yado_neutral_evidence_profile_selector_v1 import NeutralEvidenceProfileSelectorV1,EvidenceCandidate
from yado_unified_core_v1 import UnifiedYADOCoreV1

PARENT=REPO/'experience/yado-real-yado-recovery-cognitive-task-v1.json'
REAL=REPO/'experience/yado-multidomain-real-data-training-v1.json'
COMP=REPO/'experience/yado-multidomain-cognitive-composition-training-v1.json'
OUT=REPO/'candidates/kernel-self-generated/g2-real-yado-recovery-cognitive-repair-v2.json'
EXP=REPO/'experience/yado-real-yado-recovery-cognitive-repair-v2.json'

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def digest(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
v1=load(PARENT);real=load(REAL);comp=load(COMP)
if v1.get('status')!='WITHHOLD':raise RuntimeError('V1_WITHHOLD_REQUIRED')
if (v1.get('metrics') or {}).get('INTELLIGENCE',{}).get('fresh_macro',0)<.99:raise RuntimeError('V1_INTELLIGENCE_DIAGNOSIS_REQUIRED')

token=os.getenv('GITHUB_TOKEN') or ''
repo_name=os.getenv('GITHUB_REPOSITORY','v37025337-pixel/EVA')
headers={'Accept':'application/vnd.github+json','User-Agent':'YADO-G2-REAL-RECOVERY-V2/1.0'}
if token:headers['Authorization']='Bearer '+token

def gh(url):
    req=urllib.request.Request(url,headers=headers)
    with urllib.request.urlopen(req,timeout=40) as r:return r.read()

page_blobs=[];runs=[]
for page in range(1,26):
    b=gh(f'https://api.github.com/repos/{repo_name}/actions/runs?per_page=100&page={page}')
    page_blobs.append(b);runs.extend((json.loads(b.decode('utf-8')).get('workflow_runs') or []))
source_sha=hashlib.sha256(b''.join(page_blobs)).hexdigest()
runs=[r for r in runs if str(r.get('conclusion') or '') in ('success','failure')]
runs.sort(key=lambda r:(str(r.get('created_at') or ''),int(r.get('id') or 0)))

by=defaultdict(list)
for r in runs:by[str(r.get('name') or '')].append(r)
episodes=[]
job_cache={}

def job_evidence(run_id):
    rid=str(run_id)
    if rid in job_cache:return job_cache[rid]
    b=gh(f'https://api.github.com/repos/{repo_name}/actions/runs/{rid}/jobs?per_page=100')
    data=json.loads(b.decode('utf-8'));jobs=data.get('jobs') or []
    names=[];all_steps=[];fail_positions=[]
    for j in jobs:
        steps=j.get('steps') or []
        for ix,s in enumerate(steps):
            nm=str(s.get('name') or '').lower();con=str(s.get('conclusion') or '')
            all_steps.append((nm,con))
            if con=='failure':
                names.append(nm);fail_positions.append(ix/max(1,len(steps)-1))
        if str(j.get('conclusion') or '')=='failure' and not steps:
            names.append(('job:'+str(j.get('name') or '')).lower())
    txt=' | '.join(names)
    ev={
      'failed_step_count':len(names),'step_count':len(all_steps),
      'fail_compile':('compile' in txt or 'py_compile' in txt),
      'fail_setup':any(t in txt for t in ('setup-python','checkout','reconstruct','pip install','install ')),
      'fail_fetch':any(t in txt for t in ('fetch','download','curl','wget')),
      'fail_canonical':any(t in txt for t in ('canonical','invariant','integrity','ledger')),
      'fail_persist':any(t in txt for t in ('persist','git push','push origin')),
      'fail_enforce':any(t in txt for t in ('enforce','verdict','admission','gate')),
      'fail_test':('test' in txt or 'benchmark' in txt or 'stress' in txt),
      'fail_train':any(t in txt for t in ('train','evolve','repair','synthes','cognitive','execute')),
      'fail_position':sum(fail_positions)/len(fail_positions) if fail_positions else 0.0,
      'failed_step_names':names[:12],
      'jobs_response_sha256':hashlib.sha256(b).hexdigest(),
    }
    job_cache[rid]=ev;return ev

for name,xs0 in by.items():
    xs=sorted(xs0,key=lambda r:(str(r.get('created_at') or ''),int(r.get('id') or 0)))
    streak=0;local=[]
    for i in range(len(xs)-1):
        cur=xs[i];nxt=xs[i+1]
        streak=streak+1 if cur.get('conclusion')=='failure' else 0
        if cur.get('conclusion')!='failure':continue
        prev=xs[i-1] if i>0 else None
        try:
            ca=datetime.datetime.fromisoformat(str(cur['created_at']).replace('Z','+00:00'))
            ua=datetime.datetime.fromisoformat(str(cur['updated_at']).replace('Z','+00:00'))
            cur_dur=max(0.0,(ua-ca).total_seconds())
        except Exception:cur_dur=0.0
        ev=job_evidence(cur.get('id'))
        local.append({
          'workflow':name,'run_id':str(cur.get('id')),'next_run_id':str(nxt.get('id')),
          'created_at':str(cur.get('created_at') or ''),'current_duration':cur_dur,
          'next_success':nxt.get('conclusion')=='success','failure_streak':streak,'run_attempt':int(cur.get('run_attempt') or 1),
          'same_sha_prev':bool(prev and prev.get('head_sha')==cur.get('head_sha')),
          'event':str(cur.get('event') or ''),'evidence':ev,
        })
    # Prevent a few very repetitive workflow families from dominating the learner.
    episodes.extend(local[-16:])

if len(episodes)<90:raise RuntimeError('V2_FAILURE_EPISODES_TOO_SMALL:'+str(len(episodes)))
episodes.sort(key=lambda e:(e['workflow'],e['created_at'],int(e['run_id'])))

def bucket(name):return int(hashlib.sha256(name.encode()).hexdigest()[:8],16)%10
train0=[e for e in episodes if bucket(e['workflow'])<=6]
validation0=[e for e in episodes if bucket(e['workflow'])==7]
blind0=[e for e in episodes if bucket(e['workflow'])>=8]
if min(len(train0),len(validation0),len(blind0))<15:raise RuntimeError('WORKFLOW_DISJOINT_SPLIT_TOO_SMALL:'+str([len(train0),len(validation0),len(blind0)]))
if ({e['workflow'] for e in train0}&{e['workflow'] for e in blind0}) or ({e['workflow'] for e in validation0}&{e['workflow'] for e in blind0}):
    raise RuntimeError('WORKFLOW_SPLIT_LEAK')

durs=sorted(e['current_duration'] for e in train0)
q50=durs[int(.50*(len(durs)-1))];q75=durs[int(.75*(len(durs)-1))]

def failure_category(e):
    v=e['evidence']
    if v['fail_compile'] or v['fail_setup'] or v['fail_fetch']:return 'TRANSPORT'
    if v['fail_canonical'] or v['fail_persist']:return 'STATE'
    if v['fail_enforce'] or v['fail_test'] or v['fail_train']:return 'SEMANTIC'
    return 'OTHER'
def risk_truth(e):
    c=failure_category(e)
    if c=='STATE' or e['failure_streak']>=2:return 'HIGH'
    if c=='SEMANTIC':return 'MEDIUM'
    return 'LOW'
def action_truth(e):
    c=failure_category(e);r=risk_truth(e)
    if e['next_success'] and c=='TRANSPORT' and r=='LOW':return 'RETRY_AFTER_FIX'
    if e['next_success']:return 'VERIFY_RECOVERY'
    if r=='HIGH':return 'WITHHOLD_ESCALATE'
    return 'REPLAN'

def features(e):
    v=e['evidence']
    return {
      'duration_ge_q50':1.0 if e['current_duration']>=q50 else 0.0,
      'duration_ge_q75':1.0 if e['current_duration']>=q75 else 0.0,
      'streak_ge_2':1.0 if e['failure_streak']>=2 else 0.0,'streak_ge_3':1.0 if e['failure_streak']>=3 else 0.0,
      'attempt_gt_1':1.0 if e['run_attempt']>1 else 0.0,'same_sha_prev':1.0 if e['same_sha_prev'] else 0.0,
      'event_push':1.0 if e['event']=='push' else 0.0,'event_dispatch':1.0 if e['event']=='workflow_dispatch' else 0.0,
      'failed_step_count_ge2':1.0 if v['failed_step_count']>=2 else 0.0,'fail_position_late':1.0 if v['fail_position']>=.65 else 0.0,
      'fail_compile':1.0 if v['fail_compile'] else 0.0,'fail_setup':1.0 if v['fail_setup'] else 0.0,'fail_fetch':1.0 if v['fail_fetch'] else 0.0,
      'fail_canonical':1.0 if v['fail_canonical'] else 0.0,'fail_persist':1.0 if v['fail_persist'] else 0.0,
      'fail_enforce':1.0 if v['fail_enforce'] else 0.0,'fail_test':1.0 if v['fail_test'] else 0.0,'fail_train':1.0 if v['fail_train'] else 0.0,
    }

def macro_acc(pred,truth):
    labs=sorted(set(truth),key=str);vals=[]
    for y in labs:
        ids=[i for i,t in enumerate(truth) if t==y]
        if ids:vals.append(sum(pred[i]==truth[i] for i in ids)/len(ids))
    return sum(vals)/len(vals) if vals else 0.0
def class_scores(pred,truth):
    out={}
    for y in sorted(set(truth),key=str):
        ids=[i for i,t in enumerate(truth) if t==y]
        out[y]={'count':len(ids),'accuracy':sum(pred[i]==truth[i] for i in ids)/len(ids)}
    return out

# Generic native model family helpers.
def fitfam(f,param,cases):
    if f=='CART_AXIS':return fit_tree(cases,int(param))
    if f=='KNN_STRATEGY':return fit_knn_strategy(cases,int(param))
    return fit_centroid_strategy(cases,int(param))
def predfam(f,m,x):
    if f=='CART_AXIS':return tree_predict(m,x)
    if f=='KNN_STRATEGY':return knn_predict(m,x)
    return centroid_predict(m,x)
def scorefam(f,m,cases):
    p=[predfam(f,m,x) for x,_ in cases];y=[y for _,y in cases]
    return macro_acc(p,y)

profiles=[('CART_AXIS',d,d) for d in (1,2,3,4,5,6,7)]+[('KNN_STRATEGY',k,k) for k in (1,3,5,7,9)]+[('CENTROID_STRATEGY',n,n) for n in range(1,19)]

# LOGIC: next-run recovery with failure evidence.
ltr=[(features(e),bool(e['next_success'])) for e in train0];lva=[(features(e),bool(e['next_success'])) for e in validation0];lbl=[(features(e),bool(e['next_success'])) for e in blind0]
ltrials=[]
for fam,param,complexity in profiles:
    m=fitfam(fam,param,ltr);ltrials.append({'token':fam+'_'+str(param),'family':fam,'param':param,'complexity':complexity,'validation':scorefam(fam,m,lva),'model':m})
lsel=NeutralEvidenceProfileSelectorV1.select([EvidenceCandidate(token=t['token'],evidence=t['validation'],complexity=t['complexity'],risk=0,novelty=.2) for t in ltrials],
 complexity_penalty=.006,risk_penalty=.2,novelty_bonus=.01)
lc=next(t for t in ltrials if t['token']==lsel['selected_token'])
lmodel=fitfam(lc['family'],lc['param'],ltr+lva)
logic_fresh=scorefam(lc['family'],lmodel,lbl)
lp=[bool(predfam(lc['family'],lmodel,x)) for x,_ in lbl];ly=[y for _,y in lbl];logic_classes=class_scores(lp,ly)
logic_ablation=macro_acc([Counter(y for _,y in ltr+lva).most_common(1)[0][0]]*len(ly),ly)

# THINKING: response ordering derived from the actual failed step category.
ROLES=['OBSERVE','FIX_TRANSPORT','INSPECT_EVIDENCE','REPAIR_MECHANISM','PROTECT_STATE','VERIFY']
ORDERS={
 'TRANSPORT':['OBSERVE','FIX_TRANSPORT','VERIFY','INSPECT_EVIDENCE','REPAIR_MECHANISM','PROTECT_STATE'],
 'SEMANTIC':['OBSERVE','INSPECT_EVIDENCE','REPAIR_MECHANISM','VERIFY','FIX_TRANSPORT','PROTECT_STATE'],
 'STATE':['OBSERVE','PROTECT_STATE','INSPECT_EVIDENCE','REPAIR_MECHANISM','VERIFY','FIX_TRANSPORT'],
 'OTHER':['OBSERVE','INSPECT_EVIDENCE','VERIFY','REPAIR_MECHANISM','FIX_TRANSPORT','PROTECT_STATE'],
}
def trace(e):return ORDERS[failure_category(e)]
def think_episode(e,seed):
    acts=[{'id':f"{e['run_id']}-{i}",'role':r} for i,r in enumerate(ROLES)]
    random.Random(seed+int(e['run_id'])%99991).shuffle(acts)
    return features(e),acts,trace(e)
def think_predict(m,e,seed):
    ctx,acts,_=think_episode(e,seed);ids=plan_multicontext(m,ctx,acts);mp={a['id']:a['role'] for a in acts};order=[mp[i] for i in ids]
    for k,v in ORDERS.items():
        if order==v:return k
    return 'UNKNOWN'
def think_macro(m,rows,seed):
    p=[think_predict(m,e,seed) for e in rows];y=[failure_category(e) for e in rows]
    return macro_acc(p,y),class_scores(p,y)
fit_traces=[(features(e),trace(e)) for e in train0]
ttrials=[]
for th in (.55,.60,.67,.75,.80):
  for keys in (1,2,3,4,5):
    for sup in (2,3,4):
      m=learn_multicontext_precedence(fit_traces,threshold=th,min_support=sup,max_context_keys=keys)
      va,_=think_macro(m,validation0,5000)
      ttrials.append({'token':f'T{th}_K{keys}_S{sup}','threshold':th,'keys':keys,'support':sup,'complexity':keys+.25*sup,'validation':va,'model':m})
tsel=NeutralEvidenceProfileSelectorV1.select([EvidenceCandidate(token=t['token'],evidence=t['validation'],complexity=t['complexity'],risk=0,novelty=.2) for t in ttrials],
 complexity_penalty=.006,risk_penalty=.2,novelty_bonus=.01)
tc=next(t for t in ttrials if t['token']==tsel['selected_token'])
tmodel=learn_multicontext_precedence(fit_traces+[(features(e),trace(e)) for e in validation0],threshold=tc['threshold'],min_support=tc['support'],max_context_keys=tc['keys'])
thinking_fresh,thinking_classes=think_macro(tmodel,blind0,9000)
tab=learn_multicontext_precedence([({},trace(e)) for e in train0+validation0],threshold=tc['threshold'],min_support=tc['support'],max_context_keys=0)
thinking_ablation,_=think_macro(tab,blind0,11000)

# INTELLIGENCE: risk from current real failure evidence.
itr=[(features(e),risk_truth(e)) for e in train0];iva=[(features(e),risk_truth(e)) for e in validation0];ibl=[(features(e),risk_truth(e)) for e in blind0]
itrials=[]
for fam,param,complexity in profiles:
    m=fitfam(fam,param,itr);itrials.append({'token':fam+'_'+str(param),'family':fam,'param':param,'complexity':complexity,'validation':scorefam(fam,m,iva),'model':m})
isel=NeutralEvidenceProfileSelectorV1.select([EvidenceCandidate(token=t['token'],evidence=t['validation'],complexity=t['complexity'],risk=0,novelty=.2) for t in itrials],
 complexity_penalty=.006,risk_penalty=.2,novelty_bonus=.01)
ic=next(t for t in itrials if t['token']==isel['selected_token'])
imodel=fitfam(ic['family'],ic['param'],itr+iva)
intel_fresh=scorefam(ic['family'],imodel,ibl);ip=[str(predfam(ic['family'],imodel,x)) for x,_ in ibl];iy=[y for _,y in ibl];intel_classes=class_scores(ip,iy)
intel_ablation=macro_acc([Counter(y for _,y in itr+iva).most_common(1)[0][0]]*len(iy),iy)

def organ_vector(e,lm,tm,im,seed):
    x=features(e);lo=bool(predfam(lc['family'],lm,x));ts=think_predict(tm,e,seed);ir=str(predfam(ic['family'],im,x))
    return {'state_known':1.0,'logic_recoverable':1.0 if lo else 0.0,
      'thinking_transport':1.0 if ts=='TRANSPORT' else 0.0,'thinking_semantic':1.0 if ts=='SEMANTIC' else 0.0,
      'thinking_state':1.0 if ts=='STATE' else 0.0,'thinking_other':1.0 if ts=='OTHER' else 0.0,
      'intel_low':1.0 if ir=='LOW' else 0.0,'intel_medium':1.0 if ir=='MEDIUM' else 0.0,'intel_high':1.0 if ir=='HIGH' else 0.0}

# Stacking selection uses training-fit organ models, then blind uses refit organ models.
ltmp=fitfam(lc['family'],lc['param'],ltr);ttmp=learn_multicontext_precedence(fit_traces,threshold=tc['threshold'],min_support=tc['support'],max_context_keys=tc['keys']);itmp=fitfam(ic['family'],ic['param'],itr)
ctr=[(organ_vector(e,ltmp,ttmp,itmp,13000),action_truth(e)) for e in train0]
cva=[(organ_vector(e,ltmp,ttmp,itmp,14000),action_truth(e)) for e in validation0]
GROUPS={'LOGIC':['logic_recoverable'],'THINKING':['thinking_transport','thinking_semantic','thinking_state','thinking_other'],'INTELLIGENCE':['intel_low','intel_medium','intel_high']}
def ablate(cases,g):
    out=[]
    for x,y in cases:
        z=dict(x)
        for k in GROUPS[g]:z[k]=0.0
        out.append((z,y))
    return out
ctrials=[]
cprofiles=[('CART_AXIS',d,d) for d in (1,2,3,4,5,6)]+[('KNN_STRATEGY',k,k) for k in (1,3,5,7)]+[('CENTROID_STRATEGY',n,n) for n in range(1,11)]
for fam,param,complexity in cprofiles:
    m=fitfam(fam,param,ctr);va=scorefam(fam,m,cva);drops={g:va-scorefam(fam,m,ablate(cva,g)) for g in GROUPS}
    ctrials.append({'token':fam+'_'+str(param),'family':fam,'param':param,'complexity':complexity,'validation':va,'drops':drops,'model':m})
eligible=[t for t in ctrials if t['validation']>=.60]
if not eligible:raise RuntimeError('NO_V2_COGNITIVE_MODEL_GE_060')
csel=NeutralEvidenceProfileSelectorV1.select([EvidenceCandidate(token=t['token'],evidence=t['validation']+.25*min(t['drops'].values()),complexity=t['complexity'],risk=0,novelty=.2) for t in eligible],
 complexity_penalty=.006,risk_penalty=.2,novelty_bonus=.01)
cc=next(t for t in eligible if t['token']==csel['selected_token'])
cdev=[(organ_vector(e,lmodel,tmodel,imodel,15000),action_truth(e)) for e in train0+validation0]
cblind=[(organ_vector(e,lmodel,tmodel,imodel,16000),action_truth(e)) for e in blind0]
cmodel=fitfam(cc['family'],cc['param'],cdev)
cp=[str(predfam(cc['family'],cmodel,x)) for x,_ in cblind];cy=[y for _,y in cblind]
cognitive_fresh=macro_acc(cp,cy);cognitive_classes=class_scores(cp,cy)
cognitive_drops={g:cognitive_fresh-scorefam(cc['family'],cmodel,ablate(cblind,g)) for g in GROUPS}
single_scores={}
for g,keys in GROUPS.items():
    xs=[]
    for x,y in cblind:
        z={k:0.0 for k in x};z['state_known']=1.0
        for k in keys:z[k]=x[k]
        xs.append((z,y))
    single_scores[g]=scorefam(cc['family'],cmodel,xs)
best_single=max(single_scores.values())
all_ab=cblind
for g in GROUPS:all_ab=ablate(all_ab,g)
combined=scorefam(cc['family'],cmodel,all_ab)

genes={
 'LOGIC':{'gene_id':'GENE-G2-REAL-RECOVERY-EVIDENCE-LOGIC-V2-'+digest(lmodel)[:16],'model':lmodel,'parent':real['genes']['LOGIC']['gene_id']},
 'THINKING':{'gene_id':'GENE-G2-REAL-RECOVERY-EVIDENCE-THINKING-V2-'+digest(tmodel)[:16],'model':tmodel,'parent':real['genes']['THINKING']['gene_id']},
 'INTELLIGENCE':{'gene_id':'GENE-G2-REAL-RECOVERY-EVIDENCE-INTELLIGENCE-V2-'+digest(imodel)[:16],'model':imodel,'parent':real['genes']['INTELLIGENCE']['gene_id']},
 'COGNITIVE':{'gene_id':'GENE-G2-REAL-RECOVERY-EVIDENCE-COGNITIVE-V2-'+digest(cmodel)[:16],'model':cmodel,'parent':comp['genes']['COGNITIVE']['gene_id']},
}
for v in genes.values():v['gene_digest']=digest(v)
genome={'schema':'yado.g2.real_yado_recovery_evidence_genome.v2','genome_id':'GENOME-G2-REAL-YADO-RECOVERY-EVIDENCE-V2-'+digest({k:v['gene_digest'] for k,v in genes.items()})[:16],
 'organs':{k:v['gene_id'] for k,v in genes.items()},'promotion_state':'SHADOW_ONLY','automatic_canonical_promotion':False}
genome['genome_digest']=digest(genome)

core=UnifiedYADOCoreV1(REPO);head_before=copy.deepcopy(core.head)
checks={
 'v1_failure_consumed':True,'actions_runs_ge_2000':len(runs)>=2000,'failure_episodes_ge_90':len(episodes)>=90,
 'workflow_disjoint_split':not ({e['workflow'] for e in train0}&{e['workflow'] for e in blind0}) and not ({e['workflow'] for e in validation0}&{e['workflow'] for e in blind0}),
 'job_step_evidence_complete':all(e['evidence']['step_count']>=1 for e in episodes),
 'logic_fresh_ge_0_60':logic_fresh>=.60,'logic_gain_ge_0_08':logic_fresh-logic_ablation>=.08,
 'thinking_fresh_ge_0_70':thinking_fresh>=.70,'thinking_gain_ge_0_20':thinking_fresh-thinking_ablation>=.20,
 'intelligence_fresh_ge_0_90':intel_fresh>=.90,'intelligence_gain_ge_0_30':intel_fresh-intel_ablation>=.30,
 'cognitive_fresh_ge_0_70':cognitive_fresh>=.70,'cognitive_beats_best_single_by_0_05':cognitive_fresh-best_single>=.05,
 'logic_causal':cognitive_drops['LOGIC']>=.03,'thinking_causal':cognitive_drops['THINKING']>=.03,'intelligence_causal':cognitive_drops['INTELLIGENCE']>=.03,
 'combined_ablation_drop_ge_0_25':cognitive_fresh-combined>=.25,'source_hashed':bool(source_sha),
 'external_models_used':False,'automatic_canonical_promotion':False,
 'canonical_unchanged':core.head.get('canonical_head_digest')==head_before.get('canonical_head_digest')}
false_keys=['external_models_used','automatic_canonical_promotion']
passed=all(v is True for k,v in checks.items() if k not in false_keys) and all(checks[k] is False for k in false_keys)
status='PASS_SHADOW_G2_REAL_YADO_RECOVERY_COGNITIVE_REPAIR_V2' if passed else 'WITHHOLD_G2_REAL_YADO_RECOVERY_COGNITIVE_REPAIR_V2'

metrics={
 'source':{'usable_runs':len(runs),'failure_episodes':len(episodes),'train':len(train0),'validation':len(validation0),'blind':len(blind0),
           'train_workflows':len({e['workflow'] for e in train0}),'validation_workflows':len({e['workflow'] for e in validation0}),'blind_workflows':len({e['workflow'] for e in blind0}),
           'source_sha256':source_sha,'job_evidence_count':len(job_cache)},
 'LOGIC':{'selected':{k:lc[k] for k in ('token','family','param','validation')},'fresh_macro':logic_fresh,'ablation_macro':logic_ablation,'drop':logic_fresh-logic_ablation,'classes':logic_classes},
 'THINKING':{'selected':{k:tc[k] for k in ('token','threshold','keys','support','validation')},'fresh_macro':thinking_fresh,'ablation_macro':thinking_ablation,'drop':thinking_fresh-thinking_ablation,'classes':thinking_classes},
 'INTELLIGENCE':{'selected':{k:ic[k] for k in ('token','family','param','validation')},'fresh_macro':intel_fresh,'ablation_macro':intel_ablation,'drop':intel_fresh-intel_ablation,'classes':intel_classes},
 'COGNITIVE':{'selected':{k:cc[k] for k in ('token','family','param','validation','drops')},'fresh_macro':cognitive_fresh,'classes':cognitive_classes,
              'organ_drops':cognitive_drops,'single_scores':single_scores,'best_single':best_single,'combined_ablation':combined},
}
exp={'schema':'yado.g2.real_yado_recovery_cognitive_repair.experience.v2','status':'TRAINED' if passed else 'WITHHOLD','metrics':metrics,'genes':genes,'genome':genome,'checks':checks,
 'canonical_mutation':False,'semantic_boundary':'V2 REPAIRS THE V1 OBSERVABILITY DEFICIT BY ADDING ONLY REAL FAILED-JOB/STEP EVIDENCE AVAILABLE AT THE CURRENT RUN. ENTIRE WORKFLOW NAMES ARE DISJOINT BETWEEN TRAIN/VALIDATION/BLIND. LOGIC STILL PREDICTS ACTUAL NEXT SAME-WORKFLOW RECOVERY; THINKING LEARNS RESPONSE ORDER FROM CURRENT FAILURE CATEGORY; INTELLIGENCE LEARNS CURRENT RISK; COGNITIVE SEES ONLY ORGAN OUTPUTS. NO WORKFLOW NAME OR FUTURE OUTCOME IS A MODEL FEATURE.'}
exp['experience_digest']=digest(exp);EXP.parent.mkdir(parents=True,exist_ok=True);EXP.write_text(json.dumps(exp,indent=2,sort_keys=True,default=str)+'\n')
report={'schema':'yado.g2.real_yado_recovery_cognitive_repair.v2','status':status,'metrics':metrics,'gene_ids':{k:v['gene_id'] for k,v in genes.items()},
 'genome_id':genome['genome_id'],'genome_digest':genome['genome_digest'],'checks':checks,'canonical_mutation':False,'promotion_applied':False,
 'next_required_capability':'REAL_YADO_RECOVERY_LIVE_CAUSAL_TRANSFER_V1' if passed else 'REAL_YADO_RECOVERY_EVIDENCE_REPAIR_V3',
 'semantic_boundary':exp['semantic_boundary']}
report['receipt_sha256']=digest(report);OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
print(json.dumps(report,indent=2,sort_keys=True))
if not passed:raise SystemExit(2)
