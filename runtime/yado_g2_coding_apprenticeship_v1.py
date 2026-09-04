from __future__ import annotations
from pathlib import Path
from dataclasses import asdict
import ast,copy,hashlib,json,sys,urllib.request

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
PKG=ROOT/'yado_rc8_v36'
sys.path[:0]=[str(ROOT),str(PKG)]

from yado_unified_core_v1 import UnifiedYADOCoreV1
from yado_core_v3_0_rc8_external_cognitive import UnifiedYADOKernelV30RC8ExternalCognitive
from yado_ambiguity_aware_program_repair_v11 import AmbiguityAwareProgramRepairV11
from yado_evolutionary_genome_v1 import PolynomialReturnRepairGeneV1
from yado_evolution_runtime_native_v1 import fit_bool_tree,acc_logic_model,fit_tree,tree_acc,plan_acc

TASK=REPO/'architecture/yado-g2-coding-apprenticeship-v1-request.json'
OUT=REPO/'candidates/kernel-self-generated/g2-coding-cognitive-layer-v1.json'
EXP=REPO/'experience/yado-coding-apprenticeship-v1.json'
DB=ROOT/'yado_g2_coding_apprenticeship_v1.sqlite'

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def digest(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def sha_text(s):return hashlib.sha256(s.encode()).hexdigest()
def safe_compile(src): 
    try: compile(src,'<coding-apprenticeship>','exec'); return True
    except Exception:return False

task=load(TASK)
core=UnifiedYADOCoreV1(REPO)
head_before=copy.deepcopy(core.head)

# ---------- READ CODE: third-party source is parsed only, never executed ----------
def source_summary(label,text,origin):
    t=ast.parse(text)
    funcs=[n for n in ast.walk(t) if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))]
    classes=[n for n in ast.walk(t) if isinstance(n,ast.ClassDef)]
    imports=[n for n in ast.walk(t) if isinstance(n,(ast.Import,ast.ImportFrom))]
    calls=[n for n in ast.walk(t) if isinstance(n,ast.Call)]
    branches=[n for n in ast.walk(t) if isinstance(n,(ast.If,ast.Match))]
    loops=[n for n in ast.walk(t) if isinstance(n,(ast.For,ast.AsyncFor,ast.While))]
    tries=[n for n in ast.walk(t) if isinstance(n,ast.Try)]
    returns=[n for n in ast.walk(t) if isinstance(n,ast.Return)]
    asyncs=[n for n in ast.walk(t) if isinstance(n,(ast.AsyncFunctionDef,ast.AsyncFor,ast.AsyncWith,ast.Await))]
    return {
      'label':label,'origin':origin,'sha256':sha_text(text),'chars':len(text),'lines':len(text.splitlines()),
      'function_count':len(funcs),'class_count':len(classes),'import_count':len(imports),'call_count':len(calls),
      'branch_count':len(branches),'loop_count':len(loops),'try_count':len(tries),'return_count':len(returns),
      'async_node_count':len(asyncs),
      'function_name_sample':sorted({getattr(n,'name','') for n in funcs if getattr(n,'name','')})[:24],
      'class_name_sample':sorted({n.name for n in classes})[:16],
    }

read_records=[]
for rel in task.get('internal_code_sources') or []:
    p=REPO/rel
    txt=p.read_text(encoding='utf-8')
    read_records.append(source_summary(rel,txt,'YADO_INTERNAL'))

external_failures=[]
for url in task.get('external_code_read_only') or []:
    try:
        req=urllib.request.Request(url,headers={'User-Agent':'YADO-G2-Coding-Apprenticeship/1.0','Accept':'text/plain'})
        with urllib.request.urlopen(req,timeout=18) as r:
            body=r.read(220000)
        txt=body.decode('utf-8','replace')
        read_records.append(source_summary(url,txt,'PUBLIC_EXTERNAL_READ_ONLY'))
    except Exception as e:
        external_failures.append({'url':url,'error':type(e).__name__+':'+str(e)[:240]})

external_read=[x for x in read_records if x['origin']=='PUBLIC_EXTERNAL_READ_ONLY']
if len(external_read)<2: raise RuntimeError('INSUFFICIENT_PUBLIC_CODE_READING_EVIDENCE')

# External learning evidence is context/memory, never a ready patch.
external_learning_path=REPO/'experience/yado-user-external-corpus-learning-v1.json'
external_learning=load(external_learning_path) if external_learning_path.exists() else {}
external_learning_digest=external_learning.get('experience_digest') or digest(external_learning)

# ---------- REPAIR / WRITE executable sandbox curriculum ----------
train_x=(-3,-1,0,2,4)
fresh_x=(-7,-4,3,6,9)

repair_specs=[
 ('R_AFFINE_PLUS_2',lambda x:x+2,False,False,False),
 ('R_SCALE_2',lambda x:2*x,False,False,False),
 ('R_AFFINE_3X1',lambda x:3*x+1,False,False,False),
 ('R_OFFSET_MINUS_4',lambda x:x-4,False,False,False),
 ('R_SCALE_NEG2',lambda x:-2*x,False,False,False),
 ('R_MOD_3',lambda x:x%3,False,False,True),
 ('R_FLOORDIV',lambda x:x//2+1,False,False,True),
 ('R_DEGREE4',lambda x:x**4+1,False,True,False),
]
write_specs=[
 ('W_QUAD_1',1,0,1,False,False),
 ('W_QUAD_2',2,0,-3,False,False),
 ('W_CUBIC_1',1,-1,2,False,False),
 ('W_AFFINE',0,3,4,False,False),
 ('W_CONST',0,0,7,False,False),
 ('W_DEGREE4',None,None,None,False,True),
 ('W_DEGREE5',None,None,None,False,True),
 ('W_BIVARIATE',None,None,None,True,False),
]

episodes=[]

def evaluate_source(src,args_expected):
    if not src or not safe_compile(src):return 0.0
    ok=0
    for args,expected in args_expected:
        try:got=AmbiguityAwareProgramRepairV11.execute(src,'f',args)
        except Exception:continue
        ok += (got==expected)
    return ok/max(1,len(args_expected))

for name,fn,multi,highdeg,nonpoly in repair_specs:
    source='def f(x):\n    return x\n'
    tr=[((x,),fn(x)) for x in train_x]
    fr=[((x,),fn(x)) for x in fresh_x]
    try:r=AmbiguityAwareProgramRepairV11.repair(source,'f',tr,max_candidates=6000,max_edit_depth=2)
    except Exception as e:r={'source':None,'reason':type(e).__name__+':'+str(e)[:160]}
    cand=r.get('source')
    tr_score=evaluate_source(cand,tr);fr_score=evaluate_source(cand,fr)
    episodes.append({
      'task_id':name,'task_kind':'REPAIR','input_source_sha256':sha_text(source),
      'candidate_present':bool(cand),'candidate_source_sha256':sha_text(cand) if cand else None,
      'candidate_source_excerpt':cand[:800] if cand else None,'repair_mode':r.get('repair_mode'),'reason':r.get('reason'),
      'train_score':tr_score,'fresh_score':fr_score,'fresh_exact':fr_score==1.0,
      'features':{'is_write':False,'multivariate':multi,'requires_degree_gt3':highdeg,'non_polynomial':nonpoly,'bounded_supported_shape':not(highdeg or nonpoly or multi)}
    })

for name,a,b,c,multi,highdeg in write_specs:
    if multi:
        source='def f(x,y):\n    return x\n'
        tr=[((x,y),x+y) for x,y in [(-2,1),(0,3),(2,4),(5,-1)]]
        fr=[((x,y),x+y) for x,y in [(-4,5),(3,7),(8,-2)]]
    elif highdeg:
        degree=4 if name=='W_DEGREE4' else 5
        source='def f(x):\n    return x\n'
        tr=[((x,),x**degree+1) for x in train_x]
        fr=[((x,),x**degree+1) for x in fresh_x]
    else:
        source='def f(x):\n    return x\n'
        def target(x,a=a,b=b,c=c):
            if a==0:return b*x+c
            return a*x*x + b*x + c
        if name=='W_CUBIC_1':
            target=lambda x:x**3-x+2
        tr=[((x,),target(x)) for x in train_x]
        fr=[((x,),target(x)) for x in fresh_x]
    try:r=PolynomialReturnRepairGeneV1.synthesize(source,'f',tr)
    except Exception as e:r={'source':None,'reason':type(e).__name__+':'+str(e)[:160]}
    cand=r.get('source')
    tr_score=evaluate_source(cand,tr);fr_score=evaluate_source(cand,fr)
    episodes.append({
      'task_id':name,'task_kind':'WRITE','input_source_sha256':sha_text(source),
      'candidate_present':bool(cand),'candidate_source_sha256':sha_text(cand) if cand else None,
      'candidate_source_excerpt':cand[:800] if cand else None,'repair_mode':r.get('operator_gene'),'reason':r.get('reason'),
      'train_score':tr_score,'fresh_score':fr_score,'fresh_exact':fr_score==1.0,
      'features':{'is_write':True,'multivariate':multi,'requires_degree_gt3':highdeg,'non_polynomial':False,'bounded_supported_shape':not(highdeg or multi)}
    })

# Predetermined unseen split, defined by task IDs rather than observed outcome.
fit_ids={'R_AFFINE_PLUS_2','W_QUAD_1','R_SCALE_2','W_QUAD_2','R_MOD_3','W_DEGREE4','R_AFFINE_3X1','W_CUBIC_1'}
val_ids={'R_OFFSET_MINUS_4','W_AFFINE','R_FLOORDIV','W_DEGREE5'}
blind_ids={'R_SCALE_NEG2','W_CONST','R_DEGREE4','W_BIVARIATE'}
if fit_ids|val_ids|blind_ids != {e['task_id'] for e in episodes}:raise RuntimeError('TASK_SPLIT_MISMATCH')

def logic_rows(ids):
    out=[]
    for e in episodes:
        if e['task_id'] not in ids:continue
        x={k:bool(v) for k,v in e['features'].items()}
        out.append((x,bool(e['fresh_exact'])))
    return out
lf,lv,lb=logic_rows(fit_ids),logic_rows(val_ids),logic_rows(blind_ids)

# THINKING learns the coding loop order; action IDs are fresh and unrelated to roles.
coding_trace=['READ','UNDERSTAND','PLAN','IMPLEMENT','COMPILE_OR_TEST','REFLECT','MEMORY_UPDATE']
tf=[coding_trace[:] for _ in range(8)]
tv=[coding_trace[:] for _ in range(4)]
tb=[coding_trace[:] for _ in range(4)]
def episode_actions(seq,salt):
    actions=[]
    for role in seq:
        hid=hashlib.sha256((salt+'|'+role).encode()).hexdigest()[:12]
        actions.append({'id':hid,'role':role})
    actions=sorted(actions,key=lambda z:z['id'])
    return actions,list(seq)
tv_ep=[episode_actions(x,'VAL'+str(i)) for i,x in enumerate(tv)]
tb_ep=[episode_actions(x,'BLIND'+str(i)) for i,x in enumerate(tb)]

# INTELLIGENCE uses observed execution evidence to decide ACCEPT vs WITHHOLD.
def intel_rows(ids):
    out=[]
    for e in episodes:
        if e['task_id'] not in ids:continue
        f=e['features']
        x={
          'is_write':1.0 if f['is_write'] else 0.0,
          'multivariate':1.0 if f['multivariate'] else 0.0,
          'high_degree':1.0 if f['requires_degree_gt3'] else 0.0,
          'non_polynomial':1.0 if f['non_polynomial'] else 0.0,
          'candidate_present':1.0 if e['candidate_present'] else 0.0,
          'train_score':float(e['train_score']),
        }
        out.append((x,'ACCEPT' if e['fresh_exact'] else 'WITHHOLD'))
    return out
inf,inv,inb=intel_rows(fit_ids),intel_rows(val_ids),intel_rows(blind_ids)

if DB.exists():DB.unlink()
k=UnifiedYADOKernelV30RC8ExternalCognitive(db_path=str(DB))
try:
    # Resource-safe use of YADO native banks; the winner is selected by validation.
    logic_bank=list((k.organ_evolution_algorithm_bank() or {}).get('LOGIC') or [])
    logic_candidates=[]
    for a in logic_bank:
        if a.get('family')!='BOOL_DECISION_TREE':continue
        m=fit_bool_tree(lf,int(a.get('max_depth',4)))
        logic_candidates.append({'algorithm':a,'model':m,'validation':acc_logic_model(a.get('family'),m,lv)})
    if not logic_candidates:raise RuntimeError('NO_NATIVE_LOGIC_CANDIDATE')
    lsel=max(logic_candidates,key=lambda z:(z['validation'],-int(z['algorithm'].get('max_depth') or 99)))
    lmodel=fit_bool_tree(lf+lv,int(lsel['algorithm'].get('max_depth',4)))
    logic={'selected_algorithm':lsel['algorithm'],'validation':lsel['validation'],'model':lmodel,
           'fresh_blind':acc_logic_model(lsel['algorithm'].get('family'),lmodel,lb)}

    thinking=k.meta_evolve_thinking(tf,tv_ep,tf+tv,tb_ep)

    intel_bank=list((k.organ_evolution_algorithm_bank() or {}).get('INTELLIGENCE') or [])
    intel_candidates=[]
    for a in intel_bank:
        if a.get('family')!='CART_AXIS':continue
        m=fit_tree(inf,int(a.get('max_depth',4)))
        intel_candidates.append({'algorithm':a,'model':m,'validation':tree_acc(m,inv)})
    if not intel_candidates:raise RuntimeError('NO_NATIVE_INTELLIGENCE_CANDIDATE')
    isel=max(intel_candidates,key=lambda z:(z['validation'],-int(z['algorithm'].get('max_depth') or 99)))
    imodel=fit_tree(inf+inv,int(isel['algorithm'].get('max_depth',4)))
    intelligence={'selected_algorithm':isel['algorithm'],'validation':isel['validation'],'model':imodel,'fresh_blind':tree_acc(imodel,inb)}

    # Coding cognitive layer: YADO chooses/synthesizes the bounded mechanism.
    layer_fit=[]
    layer_blind=[]
    for ids,dst in ((fit_ids|val_ids,layer_fit),(blind_ids,layer_blind)):
        for e in episodes:
            if e['task_id'] not in ids:continue
            inp={
              'task_kind':e['task_kind'],
              'candidate_present':bool(e['candidate_present']),
              'train_exact':float(e['train_score'])==1.0,
              'high_complexity':bool(e['features']['requires_degree_gt3'] or e['features']['multivariate'] or e['features']['non_polynomial']),
            }
            dst.append({'input':inp,'expected':'ACCEPT' if e['fresh_exact'] else 'WITHHOLD'})
    goal=k.executive.create_goal(
      objective='FORM_CODING_COGNITIVE_CONTROL_LAYER_FROM_APPRENTICESHIP_EXPERIENCE',
      required_capabilities={'CODING_COGNITIVE_CONTROL_LAYER_V1':1.0},
      success_criteria={'fresh':1.0,'ablation':True,'restore':True}
    )
    deficits=k.executive.detect_deficits(goal.goal_id)
    prog=None;selection=None;development=None
    if deficits:
        try:
            prog,selection=k.executive.synthesize_best_mechanism(deficits[0].deficit_id,'GENERATIVE_EXECUTIVE',layer_fit,min_support=2)
            development=k.executive.evaluate_mechanism(prog.program_id,layer_blind,min_score=.99,min_ablation_drop=.20)
        except Exception:
            prog=selection=development=None
finally:
    try:k.close()
    except Exception:pass

def majority(rows):
    counts={}
    for _,y in rows:counts[y]=counts.get(y,0)+1
    return max(counts.values())/len(rows)
logic_base=majority(lb)
intel_base=majority(inb)
thinking_base=plan_acc([],tb_ep)
fresh_scores={'LOGIC':float(logic['fresh_blind']),'THINKING':float(thinking.get('fresh_blind') or 0),'INTELLIGENCE':float(intelligence['fresh_blind'])}
baselines={'LOGIC':logic_base,'THINKING':thinking_base,'INTELLIGENCE':intel_base}
fresh_gains={x:fresh_scores[x]-baselines[x] for x in fresh_scores}

code_read_pass=len(external_read)>=2 and len(read_records)>=5
repair_rows=[e for e in episodes if e['task_kind']=='REPAIR']
write_rows=[e for e in episodes if e['task_kind']=='WRITE']
repair_fresh=sum(e['fresh_exact'] for e in repair_rows)/len(repair_rows)
write_fresh=sum(e['fresh_exact'] for e in write_rows)/len(write_rows)

layer_gene=None
if development is not None and getattr(development,'state_committed',False):
    pd=asdict(prog)
    layer_gene={
      'schema':'yado.g2.coding_cognitive_layer_gene.v1',
      'gene_id':'GENE-G2-CODING-COGNITIVE-LAYER-'+str(pd.get('program_digest') or digest(pd))[:16],
      'gene_scope':['LOGIC','THINKING','INTELLIGENCE','CODE','MEMORY','GENERATIVE_EXECUTIVE'],
      'origin':'YADO_NATIVE_DEVELOPMENTAL_EXECUTIVE_FROM_CODING_APPRENTICESHIP_EPISODES',
      'mechanism_kind':getattr(development,'mechanism_kind',None),
      'program':pd,'selection':asdict(selection),'development':asdict(development),
      'promotion_state':'SHADOW_ONLY'
    }
    layer_gene['gene_digest']=digest(layer_gene)

checks={
 'internal_code_read':sum(x['origin']=='YADO_INTERNAL' for x in read_records)>=3,
 'external_public_code_read':len(external_read)>=2,
 'third_party_code_executed':False,
 'external_learning_evidence_consumed':bool(external_learning),
 'repair_training_executed':len(repair_rows)>=8,
 'write_training_executed':len(write_rows)>=8,
 'at_least_one_real_repair_generalized':any(e['fresh_exact'] for e in repair_rows),
 'at_least_one_real_written_program_generalized':any(e['fresh_exact'] for e in write_rows),
 'logic_coding_evolution_fresh_ge_baseline':fresh_gains['LOGIC']>=0,
 'thinking_coding_evolution_fresh_gt_baseline':fresh_gains['THINKING']>0,
 'intelligence_coding_evolution_fresh_ge_baseline':fresh_gains['INTELLIGENCE']>=0,
 'coding_cognitive_layer_born':layer_gene is not None,
 'coding_layer_fresh_exact':layer_gene is not None and float(layer_gene['development'].get('candidate_score') or 0)>=.99,
 'coding_layer_ablation_drop':layer_gene is not None and float(layer_gene['development'].get('candidate_score') or 0)>float(layer_gene['development'].get('ablation_score') or 0),
 'coding_layer_restore_exact':layer_gene is not None and abs(float(layer_gene['development'].get('candidate_score') or 0)-float(layer_gene['development'].get('restore_score') or 0))<1e-12,
 'external_coding_model_used':False,
 'ready_patch_from_host_used':False,
 'automatic_canonical_promotion':False,
 'canonical_unchanged':core.head.get('canonical_head_digest')==head_before.get('canonical_head_digest'),
 'rollback_parent_available':True,
}

essential=[
 'internal_code_read','external_public_code_read','external_learning_evidence_consumed',
 'repair_training_executed','write_training_executed','at_least_one_real_repair_generalized',
 'at_least_one_real_written_program_generalized','thinking_coding_evolution_fresh_gt_baseline',
 'coding_cognitive_layer_born','coding_layer_fresh_exact','coding_layer_ablation_drop',
 'coding_layer_restore_exact','canonical_unchanged'
]
passed=all(checks[k] for k in essential) and checks['third_party_code_executed'] is False and checks['external_coding_model_used'] is False and checks['ready_patch_from_host_used'] is False
status='PASS_SHADOW_G2_CODING_APPRENTICESHIP_V1' if passed else 'WITHHOLD_G2_CODING_APPRENTICESHIP_V1'

experience={
 'schema':'yado.g2.coding_apprenticeship.experience.v1',
 'status':'TRAINED',
 'external_learning_digest':external_learning_digest,
 'code_reading':read_records,'external_read_failures':external_failures,
 'episodes':episodes,
 'repair_fresh_exact_rate':repair_fresh,'write_fresh_exact_rate':write_fresh,
 'coding_loop':['READ','UNDERSTAND','PLAN','IMPLEMENT','COMPILE_OR_TEST','REFLECT','MEMORY_UPDATE'],
 'lti':{'LOGIC':logic,'THINKING':thinking,'INTELLIGENCE':intelligence,'baselines':baselines,'fresh_scores':fresh_scores,'fresh_gains':fresh_gains},
 'cognitive_layer_gene':layer_gene,
 'canonical_mutation':False,
 'semantic_boundary':'THIRD-PARTY SOURCE IS READ/PARSED ONLY. EXECUTABLE REPAIR/WRITE TASKS ARE SANDBOXED PURE TRAINING FUNCTIONS. YADO NATIVE REPAIR/SYNTHESIS AND DEVELOPMENTAL MECHANISM SELECTION PRODUCE CANDIDATES. ALL LEARNING OUTPUTS REMAIN SHADOW.'
}
experience['experience_digest']=digest(experience)
EXP.parent.mkdir(parents=True,exist_ok=True)
EXP.write_text(json.dumps(experience,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')

report={
 'schema':'yado.g2.coding_apprenticeship.v1','status':status,'task':task,
 'experience_digest':experience['experience_digest'],
 'read_source_count':len(read_records),'external_code_read_count':len(external_read),
 'repair_fresh_exact_rate':repair_fresh,'write_fresh_exact_rate':write_fresh,
 'fresh_scores':fresh_scores,'baselines':baselines,'fresh_gains':fresh_gains,
 'coding_cognitive_layer_gene':layer_gene,'checks':checks,
 'canonical_mutation':False,'promotion_applied':False,
 'next_required_capability':None if passed else 'G2_CODING_APPRENTICESHIP_REPAIR_V2',
 'receipt_sha256':None,
 'semantic_boundary':experience['semantic_boundary']
}
report['receipt_sha256']=digest({k:v for k,v in report.items() if k!='receipt_sha256'})
OUT.parent.mkdir(parents=True,exist_ok=True)
OUT.write_text(json.dumps(report,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')
print(json.dumps({
 'status':status,'read_source_count':len(read_records),'external_code_read_count':len(external_read),
 'repair_fresh_exact_rate':repair_fresh,'write_fresh_exact_rate':write_fresh,
 'fresh_scores':fresh_scores,'baselines':baselines,'fresh_gains':fresh_gains,
 'coding_layer_gene_id':layer_gene.get('gene_id') if layer_gene else None,
 'next_required_capability':report['next_required_capability'],'receipt_sha256':report['receipt_sha256']
},indent=2,sort_keys=True))
if not passed:raise SystemExit(2)
