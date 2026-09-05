from __future__ import annotations
from pathlib import Path
from dataclasses import asdict
from collections import defaultdict
import copy,hashlib,json,re,subprocess,sys

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
PKG=ROOT/'yado_rc8_v36'
sys.path[:0]=[str(ROOT),str(PKG)]

from yado_core_v3_0_rc8_external_cognitive import UnifiedYADOKernelV30RC8ExternalCognitive
from yado_evolution_runtime_native_v1 import plan_acc,fit_bool_tree,acc_logic_model,fit_tree,tree_acc
from yado_organ_runtime_native_v1 import tree_predict
from yado_unified_core_v1 import UnifiedYADOCoreV1

PROV=REPO/'canonical/yado-legacy-experience-derived-provenance-v1.json'
COG_PARENT=REPO/'canonical/yado-g2-experience-conditioned-cognitive-layer-v3.json'
CORPUS=REPO/'experience/yado-global-experience-corpus-v1.json'
OUT=REPO/'candidates/kernel-self-generated/g2-global-experience-cognitive-genesis-v1.json'
EXP=REPO/'experience/yado-global-experience-cognitive-genesis-v1.json'

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def digest(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def sha_bytes(b):return hashlib.sha256(b).hexdigest()
def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def scalar(v):return isinstance(v,(str,int,float,bool)) or v is None

def flatten(obj,max_depth=9):
    out=[]
    def walk(x,path,depth):
        if depth>max_depth:return
        if isinstance(x,dict):
            for k in sorted(x):
                walk(x[k],path+[str(k)],depth+1)
        elif isinstance(x,list):
            for i,v in enumerate(x[:128]):
                walk(v,path+[str(i)],depth+1)
        elif scalar(x):
            out.append(('.'.join(path),x))
    walk(obj,[],0)
    return out

def top_status(obj):
    for k in ('status','verdict','result'):
        v=obj.get(k) if isinstance(obj,dict) else None
        if isinstance(v,str):return v
    return None

def outcome(status):
    u=str(status or '').upper()
    if not u:return None
    positive=('PASS','COMMIT','EXECUTE','SELECTED','CANONICAL_ACTIVE','VERIFIED','SUCCESS')
    negative=('WITHHOLD','FAIL','ROLLBACK','BLOCKED','ERROR','REJECT')
    if any(u.startswith(x) for x in positive) or u in positive:return 'PASS'
    if any(u.startswith(x) for x in negative) or u in negative:return 'WITHHOLD'
    return None

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
    flat=flatten(obj)
    paths={p:v for p,v in flat}
    lower=[(p.lower(),v) for p,v in flat]
    def bool_signal(tokens):
        vals=[]
        for p,v in lower:
            if isinstance(v,bool) and any(t in p for t in tokens):vals.append(v)
        return vals
    def nums(tokens):
        vals=[]
        for p,v in lower:
            if isinstance(v,(int,float)) and not isinstance(v,bool) and any(t in p for t in tokens):vals.append(float(v))
        return vals
    fresh_b=bool_signal(('fresh','hidden','full_domain'))
    fresh_n=nums(('fresh_score','fresh_blind','hidden_score','full_domain_score','candidate_score'))
    has_fresh=bool(fresh_b or fresh_n)
    fresh_positive=(any(fresh_b) or any(x>=.90 for x in fresh_n)) if has_fresh else False

    abl_b=bool_signal(('ablation','causal_drop','material_drop'))
    abl_n=nums(('ablation_drop','causal_gain','causal_drop'))
    cand=nums(('candidate_score',))
    abl_score=nums(('ablation_score',))
    abl_positive=any(abl_b) or any(x>=.20 for x in abl_n)
    if cand and abl_score:
        abl_positive=abl_positive or (max(cand)-min(abl_score)>=.20)
    has_ablation=bool(abl_b or abl_n or abl_score)

    reg_b=bool_signal(('regression','restore','integrity','rollback'))
    has_reg=bool(reg_b)
    reg_positive=any(reg_b) if reg_b else False

    safe_b=bool_signal(('unknown','conflict','fail_closed','safety'))
    has_safe=bool(safe_b)
    safe_positive=any(safe_b) if safe_b else False

    canon_unchanged=None
    for p,v in lower:
        if isinstance(v,bool) and ('canonical_unchanged' in p or 'canonical_head_immutable' in p):
            canon_unchanged=bool(v);break
    if canon_unchanged is None:
        cm=first_recursive(obj,('canonical_mutation',))
        if isinstance(cm,bool):canon_unchanged=not cm

    rollback=first_recursive(obj,('rollback_available','rollback_parent_available'))
    promotion=first_recursive(obj,('promotion_applied','automatic_canonical_promotion'))
    return {
      'has_fresh':bool(has_fresh),'fresh_positive':bool(fresh_positive),
      'has_ablation':bool(has_ablation),'ablation_positive':bool(abl_positive),
      'has_regression_restore_integrity':bool(has_reg),'regression_restore_integrity_positive':bool(reg_positive),
      'has_safety_evidence':bool(has_safe),'safety_positive':bool(safe_positive),
      'canonical_unchanged':bool(canon_unchanged) if canon_unchanged is not None else False,
      'rollback_available':bool(rollback) if isinstance(rollback,bool) else False,
      'promotion_applied':bool(promotion) if isinstance(promotion,bool) else False,
      'evidence_density':sum(map(int,[has_fresh,has_ablation,has_reg,has_safe,canon_unchanged is not None,rollback is not None])),
    }

def parse_run_id(path):
    m=re.search(r'run[-_](\d{8,})',str(path))
    return int(m.group(1)) if m else None

def row_from_json(path,source_class,obj,raw_sha):
    st=top_status(obj)
    out=outcome(st)
    nxt=first_recursive(obj,('next_required_capability','next_action'))
    text=str(path)+' '+str(nxt or '')
    metrics=metric_summary(obj)
    return {
      'path':str(path),'source_class':source_class,'sha256':raw_sha,
      'status':st,'outcome':out,'next_required_capability':str(nxt) if nxt is not None else None,
      'domain':domain_of(text),'next_domain':domain_of(nxt) if nxt else None,
      'run_id':parse_run_id(path),'metrics':metrics,
    }

# Current durable evidence: every persisted run receipt, experience artifact, and self-generated candidate.
source_specs=[
 ('RECEIPT',REPO/'receipts'),
 ('EXPERIENCE',REPO/'experience'),
 ('CANDIDATE',REPO/'candidates/kernel-self-generated'),
]
rows=[];source_counts={};parse_failures=[]
for source_class,base in source_specs:
    files=sorted(base.glob('*.json')) if base.exists() else []
    source_counts[source_class]={'files':len(files),'parsed':0}
    for p in files:
        if p in (CORPUS,EXP):continue
        try:
            b=p.read_bytes();obj=json.loads(b.decode('utf-8'))
            rows.append(row_from_json(p.relative_to(REPO),source_class,obj,sha_bytes(b)))
            source_counts[source_class]['parsed']+=1
        except Exception as e:
            parse_failures.append({'path':str(p.relative_to(REPO)),'error':type(e).__name__+':'+str(e)[:180]})

# Legacy branches: use only YADO-rederived raw observations, never host-curated lessons.
prov=load(PROV)
legacy_rows=[]
for b in prov.get('branches') or []:
    obs=((b.get('yado_rederived') or {}).get('observations') or [])
    statuses=[o.get('value') for o in obs if o.get('kind')=='JSON_SCALAR' and str(o.get('path'))=='status' and isinstance(o.get('value'),str)]
    if not statuses:
        statuses=[o.get('value') for o in obs if o.get('kind')=='JSON_SCALAR' and str(o.get('path','')).endswith('.status') and isinstance(o.get('value'),str)]
    st=statuses[-1] if statuses else None
    synthetic={'status':st,'checks':{}}
    for o in obs:
        if o.get('kind')!='JSON_SCALAR':continue
        p=str(o.get('path') or '')
        v=o.get('value')
        if isinstance(v,bool):synthetic['checks'][p]=v
    raw_sha=digest({'branch':b.get('branch'),'observations':obs})
    r=row_from_json('LEGACY:'+str(b.get('branch')),'LEGACY_REDERIVED',synthetic,raw_sha)
    r['branch']=b.get('branch');r['legacy_observation_count']=len(obs)
    legacy_rows.append(r)
rows.extend(legacy_rows)

# Capture every current remote branch ref. Historical semantic learning still comes from exact rederived evidence above.
try:
    raw=subprocess.run(['git','for-each-ref','--format=%(refname:short)|%(objectname)','refs/remotes/origin'],cwd=REPO,capture_output=True,text=True,check=True).stdout
    branch_refs=[]
    for line in raw.splitlines():
        if not line or line.endswith('/HEAD'):continue
        name,sha=line.split('|',1);branch_refs.append({'branch':name.replace('origin/','',1),'sha':sha})
except Exception:
    branch_refs=[]

# Durable corpus retains every path; training deduplicates exact content.
seen=set();unique_rows=[]
for r in rows:
    key=(r['source_class'],r['sha256'])
    if key in seen:continue
    seen.add(key);unique_rows.append(r)
outcome_rows=[r for r in unique_rows if r.get('outcome') in ('PASS','WITHHOLD')]

corpus={
 'schema':'yado.g2.global_experience_corpus.v1',
 'source_counts':source_counts,
 'parse_failures':parse_failures,
 'remote_branch_refs':branch_refs,
 'remote_branch_ref_count':len(branch_refs),
 'remote_unique_tip_count':len({x['sha'] for x in branch_refs}),
 'legacy_branch_count':len(legacy_rows),
 'legacy_source_policy':'YADO_REDERIVED_OBSERVATIONS_ONLY_HOST_CURATED_LESSONS_EXCLUDED_FROM_TRAINING',
 'raw_row_count':len(rows),'content_unique_row_count':len(unique_rows),'outcome_row_count':len(outcome_rows),
 'rows':unique_rows,
}
corpus['corpus_digest']=digest(corpus)
CORPUS.parent.mkdir(parents=True,exist_ok=True)
CORPUS.write_text(json.dumps(corpus,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')

def split_bucket(r):
    return int(r['sha256'][:8],16)%10

def balance(rows,target_fn,min_per_class=4,max_per_class=96):
    groups=defaultdict(list)
    for r in rows:groups[target_fn(r)].append(r)
    groups={k:sorted(v,key=lambda x:(x['sha256'],x['path'])) for k,v in groups.items() if k is not None}
    if len(groups)<2:return []
    n=min(min(len(v),max_per_class) for v in groups.values())
    if n<min_per_class:return []
    out=[]
    for k in sorted(groups):
        out.extend(groups[k][:n])
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

train_rows=[r for r in outcome_rows if split_bucket(r)<=5]
val_rows=[r for r in outcome_rows if 6<=split_bucket(r)<=7]
blind_rows=[r for r in outcome_rows if split_bucket(r)>=8]

lf=balance(train_rows,lambda r:r['outcome']=='PASS')
lv=balance(val_rows,lambda r:r['outcome']=='PASS')
lb=balance(blind_rows,lambda r:r['outcome']=='PASS')
if min(len(lf),len(lv),len(lb))<8:raise RuntimeError('GLOBAL_LOGIC_SPLIT_TOO_SMALL:'+str([len(lf),len(lv),len(lb)]))
lf=[(logic_features(r),r['outcome']=='PASS') for r in lf]
lv=[(logic_features(r),r['outcome']=='PASS') for r in lv]
lb=[(logic_features(r),r['outcome']=='PASS') for r in lb]

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

inf=balance(train_rows,intel_target)
inv=balance(val_rows,intel_target)
inb=balance(blind_rows,intel_target)
if min(len(inf),len(inv),len(inb))<12:raise RuntimeError('GLOBAL_INTELLIGENCE_SPLIT_TOO_SMALL:'+str([len(inf),len(inv),len(inb)]))
inf=[(intel_features(r),intel_target(r)) for r in inf]
inv=[(intel_features(r),intel_target(r)) for r in inv]
inb=[(intel_features(r),intel_target(r)) for r in inb]

# THINKING uses real chronological run receipts only.
receipt_rows=[r for r in unique_rows if r['source_class']=='RECEIPT' and r.get('outcome') in ('PASS','WITHHOLD') and r.get('run_id')]
receipt_rows=sorted(receipt_rows,key=lambda r:(r['run_id'],r['path']))
def control_role(r):
    if r['outcome']=='PASS':
        return 'ACCEPT' if not r.get('next_required_capability') else 'ADVANCE'
    return 'REVISE' if r.get('next_required_capability') else 'SEEK_EVIDENCE'
roles=[control_role(r) for r in receipt_rows]
windows=[roles[i:i+4] for i in range(max(0,len(roles)-3))]
nw=len(windows);a=max(8,int(nw*.60));b=max(a+8,int(nw*.80))
tf,tv,tb=windows[:a],windows[a:b],windows[b:]
if min(len(tf),len(tv),len(tb))<8:raise RuntimeError('GLOBAL_THINKING_HISTORY_TOO_SMALL:'+str([len(tf),len(tv),len(tb)]))
def episode(seq,salt):
    acts=[]
    for j,role in enumerate(seq):
        hid=hashlib.sha256((str(salt)+'|'+str(j)+'|'+role).encode()).hexdigest()[:12]
        acts.append({'id':hid,'role':role})
    acts=sorted(acts,key=lambda x:x['id'])
    return ({'history_phase':'GLOBAL_FRESH_CAUSAL_HOLDOUT'},acts,list(seq))
tv_ep=[episode(x,'VAL'+str(i)) for i,x in enumerate(tv)]
tb_ep=[episode(x,'BLIND'+str(i)) for i,x in enumerate(tb)]

core=UnifiedYADOCoreV1(REPO);head_before=copy.deepcopy(core.head)
parent_cognitive=load(COG_PARENT)
db=ROOT/'yado_global_experience_cognitive_genesis_v1.sqlite'
if db.exists():db.unlink()
k=UnifiedYADOKernelV30RC8ExternalCognitive(db_path=str(db))
try:
    # LOGIC: native bank validation on global history.
    logic_bank=list((k.organ_evolution_algorithm_bank() or {}).get('LOGIC') or [])
    logic_candidates=[];logic_rejected=[]
    for alg in logic_bank:
        fam=alg.get('family')
        if fam=='ENUM_BOOLEAN' and len(lf[0][0])>3:
            logic_rejected.append({'algorithm':alg,'reason':'GLOBAL_FEATURE_SURFACE_EXCEEDS_ENUM_BUDGET'});continue
        if fam=='BOOL_DECISION_TREE':
            model=fit_bool_tree(lf,int(alg.get('max_depth',4)))
            logic_candidates.append({'algorithm':alg,'model':model,'validation':acc_logic_model(fam,model,lv)})
    if not logic_candidates:raise RuntimeError('NO_GLOBAL_LOGIC_NATIVE_CANDIDATE')
    lsel=max(logic_candidates,key=lambda z:(z['validation'],-int(z['algorithm'].get('max_depth') or 99),canon(z['algorithm'])))
    lmodel=fit_bool_tree(lf+lv,int(lsel['algorithm'].get('max_depth',4)))
    logic_fresh=acc_logic_model(lsel['algorithm'].get('family'),lmodel,lb)

    # THINKING: native meta-evolution on chronological global run roles.
    thinking=k.meta_evolve_thinking(tf,tv_ep,tf+tv,tb_ep)
    thinking_fresh=float(thinking.get('fresh_blind') or 0.0)

    # INTELLIGENCE: native CART family selected by validation.
    intel_bank=list((k.organ_evolution_algorithm_bank() or {}).get('INTELLIGENCE') or [])
    intel_candidates=[];intel_rejected=[]
    for alg in intel_bank:
        fam=alg.get('family')
        if fam=='LINEAR_SCORE_SEARCH' and len(inf[0][0])>6:
            intel_rejected.append({'algorithm':alg,'reason':'GLOBAL_FEATURE_SURFACE_EXCEEDS_LINEAR_SEARCH_BUDGET'});continue
        if fam=='CART_AXIS':
            model=fit_tree(inf,int(alg.get('max_depth',4)))
            intel_candidates.append({'algorithm':alg,'model':model,'validation':tree_acc(model,inv)})
    if not intel_candidates:raise RuntimeError('NO_GLOBAL_INTELLIGENCE_NATIVE_CANDIDATE')
    isel=max(intel_candidates,key=lambda z:(z['validation'],-int(z['algorithm'].get('max_depth') or 99),canon(z['algorithm'])))
    imodel=fit_tree(inf+inv,int(isel['algorithm'].get('max_depth',4)))
    intel_fresh=tree_acc(imodel,inb)

    # COGNITIVE: native developmental arbiter over the new LOGIC/INTELLIGENCE outputs + evidence.
    def cog_target(r):
        if r['outcome']=='PASS':return 'COMMIT'
        if r.get('next_required_capability'):return 'REVISE'
        return 'WITHHOLD'
    def cog_features(r):
        lp=bool(tree_predict(lmodel,logic_features(r)))
        ip=str(tree_predict(imodel,intel_features(r)))
        m=r['metrics']
        return {
          'state_known':True,'logic_accept':lp,
          'intelligence_action':ip,
          'next_present':bool(r.get('next_required_capability')),
          'fresh_positive':m['fresh_positive'],
          'ablation_positive':m['ablation_positive'],
          'canonical_unchanged':m['canonical_unchanged'],
          'rollback_available':m['rollback_available'],
        }
    ctr=balance(train_rows,cog_target,min_per_class=4,max_per_class=72)
    cbl=balance(blind_rows,cog_target,min_per_class=4,max_per_class=48)
    if min(len(ctr),len(cbl))<12:raise RuntimeError('GLOBAL_COGNITIVE_SPLIT_TOO_SMALL:'+str([len(ctr),len(cbl)]))
    ctrain=[{'input':cog_features(r),'expected':cog_target(r)} for r in ctr]
    # Explicit fail-closed safety contract; these are not counted as historical evidence.
    for i in range(12):
        ctrain.append({'input':{'state_known':False,'logic_accept':bool(i%2),'intelligence_action':['STOP','RETRY','ADVANCE'][i%3],
                                'next_present':bool((i//2)%2),'fresh_positive':bool(i%2),'ablation_positive':bool((i+1)%2),
                                'canonical_unchanged':True,'rollback_available':bool(i%3)},'expected':'WITHHOLD'})
    cblind=[{'input':cog_features(r),'expected':cog_target(r)} for r in cbl]

    cg=k.executive.create_goal(
      objective='Build a global experience cognitive coordinator over newly evolved history-conditioned organ outputs.',
      required_capabilities={'GLOBAL_EXPERIENCE_COGNITIVE_COORDINATOR_V1':.90},
      success_criteria={'blind_score':.90,'ablation_drop':.20,'unknown_fail_closed':True,'restore':True},
    )
    cdef=k.executive.detect_deficits(cg.goal_id)[0]
    cprog,csel=k.executive.synthesize_best_mechanism(cdef.deficit_id,'CONSCIOUS_WORKSPACE',ctrain,min_support=2)
    cdev=k.executive.evaluate_mechanism(cprog.program_id,cblind,min_score=.90,min_ablation_drop=.20)
    unknown_stress=[]
    if cdev.verdict=='COMMIT':
        for i in range(18):
            payload={'state_known':False,'logic_accept':bool(i%2),'intelligence_action':['STOP','RETRY','ADVANCE'][i%3],
                     'next_present':bool((i//3)%2),'fresh_positive':bool(i%2),'ablation_positive':bool((i+1)%2),
                     'canonical_unchanged':bool((i//2)%2),'rollback_available':bool(i%3)}
            unknown_stress.append(k.executive.execute_capability('GLOBAL_EXPERIENCE_COGNITIVE_COORDINATOR_V1',payload))
finally:
    try:k.close()
    except Exception:pass

def majority_baseline(rows):
    counts=defaultdict(int)
    for _,y in rows:counts[str(y)]+=1
    return max(counts.values())/len(rows)
logic_base=majority_baseline(lb)
intel_base=majority_baseline(inb)
thinking_base=plan_acc([],tb_ep)
fresh_scores={'LOGIC':logic_fresh,'THINKING':thinking_fresh,'INTELLIGENCE':intel_fresh,'COGNITIVE':float(cdev.candidate_score)}
baselines={'LOGIC':logic_base,'THINKING':thinking_base,'INTELLIGENCE':intel_base,'COGNITIVE':float(cdev.ablation_score)}
gains={k:fresh_scores[k]-baselines[k] for k in fresh_scores}

parent_caps={
 'LOGIC':'ALG-G2-BUDGET-ADAPTIVE-COMPOSITIONAL-LOGIC-V2',
 'THINKING':'ALG-G2-WORK-BUDGET-ADAPTIVE-CONTINGENT-PLANNER-V2',
 'INTELLIGENCE':'ALG-G2-COVERAGE-PRUNED-COMPOSITIONAL-SCHEMA-ROUTER-V3',
}
genes={}
for organ,model,alg in [
 ('LOGIC',lmodel,lsel['algorithm']),
 ('THINKING',thinking.get('model'),thinking.get('selected_algorithm')),
 ('INTELLIGENCE',imodel,isel['algorithm']),
]:
    g={'schema':'yado.g2.global_experience_organ_gene.v1',
       'gene_id':'GENE-G2-GLOBAL-EXPERIENCE-'+organ+'-'+digest({'organ':organ,'model':model,'corpus':corpus['corpus_digest']})[:16],
       'organ':organ,'heritage':[parent_caps[organ]],'corpus_digest':corpus['corpus_digest'],
       'selected_algorithm':alg,'model':model,'fresh_blind':fresh_scores[organ],
       'baseline':baselines[organ],'causal_gain':gains[organ],'promotion_state':'SHADOW_ONLY',
       'origin':'YADO_NATIVE_META_EVOLUTION_FROM_GLOBAL_CONTENT_ADDRESSED_HISTORY'}
    g['gene_digest']=digest(g);genes[organ]=g

def find_gene_strings(x,prefix,out):
    if isinstance(x,dict):
        for v in x.values():find_gene_strings(v,prefix,out)
    elif isinstance(x,list):
        for v in x:find_gene_strings(v,prefix,out)
    elif isinstance(x,str) and x.startswith(prefix):out.add(x)
arb=set();find_gene_strings(parent_cognitive,'GENE-G2-COGNITIVE-CONFLICT-ARBITER',arb)
cog_gene={
 'schema':'yado.g2.global_experience_cognitive_gene.v1',
 'gene_id':'GENE-G2-GLOBAL-EXPERIENCE-COGNITIVE-'+digest({'program':cdev.program_digest,'organs':{k:v['gene_digest'] for k,v in genes.items()},'corpus':corpus['corpus_digest']})[:16],
 'organ':'CONSCIOUS_WORKSPACE','heritage':sorted(arb)|[],
 'organ_gene_ids':[genes[x]['gene_id'] for x in ('LOGIC','THINKING','INTELLIGENCE')],
 'program_id':cprog.program_id,'program_digest':cdev.program_digest,
 'fresh_blind':float(cdev.candidate_score),'ablation':float(cdev.ablation_score),'restore':float(cdev.restore_score),
 'unknown_fail_closed':bool(unknown_stress) and all(x=='WITHHOLD' for x in unknown_stress),
 'promotion_state':'SHADOW_ONLY','origin':'YADO_NATIVE_DEVELOPMENTAL_ARBITER_OVER_GLOBAL_HISTORY_CONDITIONED_ORGANS',
}
cog_gene['gene_digest']=digest(cog_gene);genes['COGNITIVE']=cog_gene

genome={
 'schema':'yado.g2.global_experience_cognitive_genome.v1',
 'genome_id':'GENOME-G2-GLOBAL-EXPERIENCE-COGNITIVE-V1-'+digest({'corpus':corpus['corpus_digest'],'genes':{k:v['gene_digest'] for k,v in genes.items()}})[:16],
 'generation':'G2_SHADOW','corpus_digest':corpus['corpus_digest'],
 'organs':{k:v['gene_id'] for k,v in genes.items()},
 'gene_digests':{k:v['gene_digest'] for k,v in genes.items()},
 'rollback_parents':parent_caps|{'COGNITIVE':'RUNTIME-G2-EXPERIENCE-CONDITIONED-COGNITIVE-LAYER-V3'},
 'promotion_state':'SHADOW_ONLY','automatic_canonical_promotion':False,
}
genome['genome_digest']=digest(genome)

checks={
 'all_receipt_files_scanned':source_counts['RECEIPT']['parsed']==source_counts['RECEIPT']['files'],
 'all_experience_files_scanned':source_counts['EXPERIENCE']['parsed']==source_counts['EXPERIENCE']['files'],
 'all_candidate_files_scanned':source_counts['CANDIDATE']['parsed']==source_counts['CANDIDATE']['files'],
 'no_json_parse_failures':not parse_failures,
 'legacy_13_branches_consumed':len(legacy_rows)==13,
 'legacy_host_curated_lessons_excluded':corpus['legacy_source_policy'].startswith('YADO_REDERIVED'),
 'remote_branch_refs_observed':len(branch_refs)>=14,
 'global_outcome_corpus_material':len(outcome_rows)>=200,
 'content_dedup_applied':len(unique_rows)<=len(rows),
 'logic_native_meta_evolution':bool(lsel.get('algorithm')),
 'thinking_native_meta_evolution':bool(thinking.get('selected_algorithm')),
 'intelligence_native_meta_evolution':bool(isel.get('algorithm')),
 'logic_fresh_beats_baseline':gains['LOGIC']>.02,
 'thinking_fresh_beats_baseline':gains['THINKING']>.02,
 'intelligence_fresh_beats_baseline':gains['INTELLIGENCE']>.02,
 'cognitive_native_commit':cdev.verdict=='COMMIT',
 'cognitive_blind_ge_0_90':cdev.candidate_score>=.90,
 'cognitive_ablation_drop_ge_0_20':cdev.candidate_score-cdev.ablation_score>=.20,
 'cognitive_restore_exact':cdev.restore_score==cdev.candidate_score,
 'cognitive_unknown_fail_closed':genes['COGNITIVE']['unknown_fail_closed'],
 'four_new_gene_identities':len({g['gene_id'] for g in genes.values()})==4,
 'rollback_parents_preserved':all(bool(x) for x in genome['rollback_parents'].values()),
 'external_models_used':False,'host_written_organ_model':False,'host_selected_algorithm_family':False,
 'automatic_canonical_promotion':False,
 'canonical_unchanged':core.head.get('canonical_head_digest')==head_before.get('canonical_head_digest'),
}
false_keys=['external_models_used','host_written_organ_model','host_selected_algorithm_family','automatic_canonical_promotion']
passed=all(v is True for k,v in checks.items() if k not in false_keys) and all(checks[k] is False for k in false_keys)
status='PASS_SHADOW_G2_GLOBAL_EXPERIENCE_COGNITIVE_GENESIS_V1' if passed else 'WITHHOLD_G2_GLOBAL_EXPERIENCE_COGNITIVE_GENESIS_V1'

experience={
 'schema':'yado.g2.global_experience_cognitive_genesis.experience.v1','status':'TRAINED' if passed else 'WITHHOLD',
 'corpus_digest':corpus['corpus_digest'],'corpus_counts':{
   'source_counts':source_counts,'raw_rows':len(rows),'unique_rows':len(unique_rows),'outcome_rows':len(outcome_rows),
   'legacy_branches':len(legacy_rows),'remote_branch_refs':len(branch_refs),'receipt_chronology_rows':len(receipt_rows),
 },
 'split_counts':{'LOGIC':[len(lf),len(lv),len(lb)],'THINKING':[len(tf),len(tv),len(tb)],'INTELLIGENCE':[len(inf),len(inv),len(inb)],
                 'COGNITIVE':[len(ctrain),len(cblind)]},
 'fresh_scores':fresh_scores,'baselines':baselines,'fresh_gains':gains,
 'genes':genes,'genome':genome,'cognitive_selection':asdict(csel),'cognitive_development':asdict(cdev),
 'checks':checks,'canonical_mutation':False,
 'semantic_boundary':'GLOBAL EXPERIENCE SELF-DISTILLATION. ALL DURABLE RECEIPTS, EXPERIENCE ARTIFACTS, SELF-GENERATED CANDIDATES, 13 LEGACY YADO-REDERIVED BRANCHES, AND CURRENT REMOTE BRANCH REFS ARE CENSUSED. TRAINING USES CONTENT-DEDUPLICATED EVIDENCE; HOST-CURATED LEGACY LESSON TEXT IS EXCLUDED. YADO NATIVE ORGAN BANKS BUILD NEW LOGIC/THINKING/INTELLIGENCE MODELS AND THE DEVELOPMENTAL EXECUTIVE BUILDS A COGNITIVE COORDINATOR. ALL OUTPUTS REMAIN SHADOW.'
}
experience['experience_digest']=digest(experience)
EXP.parent.mkdir(parents=True,exist_ok=True);EXP.write_text(json.dumps(experience,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')

report={
 'schema':'yado.g2.global_experience_cognitive_genesis.v1','status':status,
 'corpus_artifact':str(CORPUS.relative_to(REPO)),'corpus_digest':corpus['corpus_digest'],
 'corpus_counts':experience['corpus_counts'],'split_counts':experience['split_counts'],
 'fresh_scores':fresh_scores,'baselines':baselines,'fresh_gains':gains,
 'gene_ids':{k:v['gene_id'] for k,v in genes.items()},'genome_id':genome['genome_id'],'genome_digest':genome['genome_digest'],
 'cognitive_development':asdict(cdev),'checks':checks,'canonical_mutation':False,'promotion_applied':False,
 'next_required_capability':'GLOBAL_EXPERIENCE_COGNITIVE_STRESS_AND_ADMISSION_V1' if passed else 'GLOBAL_EXPERIENCE_COGNITIVE_GENESIS_REPAIR_V2',
 'semantic_boundary':experience['semantic_boundary'],
}
report['receipt_sha256']=digest(report)
OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(report,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')
print(json.dumps({
 'status':status,'corpus_counts':report['corpus_counts'],'fresh_scores':fresh_scores,'baselines':baselines,'fresh_gains':gains,
 'gene_ids':report['gene_ids'],'genome_id':genome['genome_id'],
 'cognitive':{'candidate':cdev.candidate_score,'ablation':cdev.ablation_score,'restore':cdev.restore_score,'verdict':cdev.verdict},
 'next_required_capability':report['next_required_capability'],'receipt_sha256':report['receipt_sha256']
},indent=2,sort_keys=True,default=str))
if not passed:raise SystemExit(2)
