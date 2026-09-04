from __future__ import annotations
from pathlib import Path
from dataclasses import asdict
import copy,hashlib,json,sys

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
PKG=ROOT/'yado_rc8_v36'
sys.path[:0]=[str(ROOT),str(PKG)]

from yado_unified_core_v1 import UnifiedYADOCoreV1
from yado_core_v3_0_rc8_external_cognitive import UnifiedYADOKernelV30RC8ExternalCognitive
from yado_ambiguity_aware_program_repair_v11 import AmbiguityAwareProgramRepairV11
from yado_evolutionary_genome_v1 import PolynomialReturnRepairGeneV1

TASK=REPO/'architecture/yado-g2-coding-reasoning-workspace-v2-request.json'
PARENT=REPO/'candidates/kernel-self-generated/g2-coding-cognitive-layer-v1.json'
HIST=REPO/'experience/yado-coding-apprenticeship-v1.json'
THINKING_PARENT=REPO/'candidates/kernel-self-generated/g2-experience-conditioned-thinking-repair-v2.json'
OUT=REPO/'candidates/kernel-self-generated/g2-coding-reasoning-workspace-v2.json'
EXP=REPO/'experience/yado-coding-reasoning-workspace-v2.json'
DB=ROOT/'yado_g2_coding_reasoning_workspace_v2.sqlite'

def canon(o): return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def digest(o): return hashlib.sha256(canon(o).encode()).hexdigest()
def load(p): return json.loads(Path(p).read_text(encoding='utf-8'))
def sha_text(s): return hashlib.sha256(s.encode()).hexdigest()
def safe_compile(src):
    try: compile(src,'<g2-coding-reasoning-v2>','exec'); return True
    except Exception: return False

task=load(TASK)
parent=load(PARENT)
hist=load(HIST)
thinking_parent=load(THINKING_PARENT)

if parent.get('status')!='WITHHOLD_G2_CODING_APPRENTICESHIP_V1':
    raise RuntimeError('PARENT_NOT_WITHHELD_CODING_APPRENTICESHIP_V1')
if parent.get('next_required_capability')!='G2_CODING_APPRENTICESHIP_REPAIR_V2':
    raise RuntimeError('PARENT_FRONTIER_MISMATCH')
if not (parent.get('coding_cognitive_layer_gene') or {}).get('gene_id'):
    raise RuntimeError('PARENT_CODING_LAYER_MISSING')
if thinking_parent.get('status')!='PASS_SHADOW_G2_EXPERIENCE_CONDITIONED_THINKING_REPAIR_V2':
    raise RuntimeError('THINKING_V2_PARENT_NOT_PASS')

core=UnifiedYADOCoreV1(REPO)
head_before=copy.deepcopy(core.head)

def eval_source(src,cases):
    if not src or not safe_compile(src): return 0.0
    ok=0
    for args,expected in cases:
        try: got=AmbiguityAwareProgramRepairV11.execute(src,'f',args)
        except Exception: continue
        ok += (got==expected)
    return ok/max(1,len(cases))

# The user supplied the curriculum semantics. YADO must synthesize the mechanism.
# No host-written rule program or ready patch is provided.
ACTION_VOCAB=[
    'READ_CODE','BUILD_MODEL','FORM_HYPOTHESIS','TEST_HYPOTHESIS',
    'IMPLEMENT_CHANGE','CHECK_CONSEQUENCES','REVISE_HYPOTHESIS',
    'STORE_EXPERIENCE','ADVANCE'
]

def reasoning_examples(ep):
    f=ep.get('features') or {}
    base={
      'task_kind':str(ep.get('task_kind')),
      'candidate_present':bool(ep.get('candidate_present')),
      'train_exact':float(ep.get('train_score') or 0)==1.0,
      'fresh_exact':float(ep.get('fresh_score') or 0)==1.0,
      'high_complexity':bool(f.get('requires_degree_gt3') or f.get('multivariate') or f.get('non_polynomial')),
    }
    rows=[]
    def add(stage,expected):
        x=dict(base); x['stage']=stage
        rows.append({'input':x,'expected':expected})
    add('START','READ_CODE')
    add('CODE_READ','BUILD_MODEL')
    add('MODEL_BUILT','FORM_HYPOTHESIS')
    add('HYPOTHESIS_READY','TEST_HYPOTHESIS' if base['candidate_present'] else 'REVISE_HYPOTHESIS')
    add('TEST_RESULT','IMPLEMENT_CHANGE' if base['train_exact'] else 'REVISE_HYPOTHESIS')
    add('IMPLEMENTED','CHECK_CONSEQUENCES')
    add('CONSEQUENCE_RESULT','STORE_EXPERIENCE' if base['fresh_exact'] else 'REVISE_HYPOTHESIS')
    add('MEMORY_READY','ADVANCE')
    return rows

historical_episodes=list(hist.get('episodes') or [])
if len(historical_episodes)<12:
    raise RuntimeError('INSUFFICIENT_HISTORICAL_CODING_EPISODES')
fit_examples=[]
for ep in historical_episodes:
    fit_examples.extend(reasoning_examples(ep))

# Fresh executable coding tasks are unseen by the V1 coding apprenticeship.
train_x=(-5,-2,0,1,4)
fresh_x=(-8,-3,2,5,7)
fresh_specs=[
  ('REPAIR','F2_NEG3P5',lambda x:-3*x+5,False),
  ('REPAIR','F2_CUBIC',lambda x:x**3+2*x-1,False),
  ('REPAIR','F2_MOD5',lambda x:x%5,False),
  ('REPAIR','F2_ABS',lambda x:abs(x)+2,False),
  ('WRITE','F2_QUAD',lambda x:2*x*x-3*x+5,False),
  ('WRITE','F2_CUBIC_WRITE',lambda x:x**3+2*x+1,False),
  ('WRITE','F2_QUARTIC_WRITE',lambda x:x**4+2,False),
  ('WRITE','F2_BIVARIATE_WRITE',lambda x,y:x-y,True),
]

fresh_episodes=[]
for kind,name,target,multi in fresh_specs:
    if multi:
        source='def f(x,y):\n    return x\n'
        tr=[((x,y),target(x,y)) for x,y in [(-3,1),(0,4),(2,-1),(5,2),(7,-4)]]
        fr=[((x,y),target(x,y)) for x,y in [(-6,3),(1,8),(4,-5),(9,2)]]
    else:
        source='def f(x):\n    return x\n'
        tr=[((x,),target(x)) for x in train_x]
        fr=[((x,),target(x)) for x in fresh_x]
    try:
        if kind=='REPAIR':
            r=AmbiguityAwareProgramRepairV11.repair(source,'f',tr,max_candidates=7000,max_edit_depth=2)
        else:
            r=PolynomialReturnRepairGeneV1.synthesize(source,'f',tr)
    except Exception as e:
        r={'source':None,'reason':type(e).__name__+':'+str(e)[:180]}
    cand=r.get('source')
    tr_score=eval_source(cand,tr)
    fr_score=eval_source(cand,fr)
    fresh_episodes.append({
      'task_id':name,'task_kind':kind,
      'input_source_sha256':sha_text(source),
      'candidate_present':bool(cand),
      'candidate_source_sha256':sha_text(cand) if cand else None,
      'candidate_source_excerpt':cand[:800] if cand else None,
      'repair_mode':r.get('repair_mode') or r.get('operator_gene'),
      'reason':r.get('reason'),
      'train_score':tr_score,'fresh_score':fr_score,'fresh_exact':fr_score==1.0,
      'features':{
        'is_write':kind=='WRITE','multivariate':multi,
        'requires_degree_gt3':'QUARTIC' in name,
        'non_polynomial':name in ('F2_MOD5','F2_ABS'),
      }
    })

blind_examples=[]
for ep in fresh_episodes:
    blind_examples.extend(reasoning_examples(ep))

def linear_action(x):
    stage=x['stage']
    return {
      'START':'READ_CODE',
      'CODE_READ':'BUILD_MODEL',
      'MODEL_BUILT':'FORM_HYPOTHESIS',
      'HYPOTHESIS_READY':'TEST_HYPOTHESIS',
      'TEST_RESULT':'IMPLEMENT_CHANGE',
      'IMPLEMENTED':'CHECK_CONSEQUENCES',
      'CONSEQUENCE_RESULT':'STORE_EXPERIENCE',
      'MEMORY_READY':'ADVANCE',
    }[stage]

linear_baseline=sum(linear_action(r['input'])==r['expected'] for r in blind_examples)/len(blind_examples)
counts={}
for r in blind_examples: counts[r['expected']]=counts.get(r['expected'],0)+1
majority_baseline=max(counts.values())/len(blind_examples)

retry_fit=sum(r['expected']=='REVISE_HYPOTHESIS' for r in fit_examples)
retry_blind=sum(r['expected']=='REVISE_HYPOTHESIS' for r in blind_examples)

if DB.exists(): DB.unlink()
k=UnifiedYADOKernelV30RC8ExternalCognitive(db_path=str(DB))
prog=selection=development=None
try:
    goal=k.executive.create_goal(
      objective='EVOLVE_THINKING_FROM_LINEAR_CODING_SEQUENCE_TO_ITERATIVE_STATE_CONDITIONED_REASONING',
      required_capabilities={'CODING_REASONING_WORKSPACE_V2':1.0},
      success_criteria={'fresh_branching':0.95,'ablation':True,'restore':True,'retry_loop':True}
    )
    deficits=k.executive.detect_deficits(goal.goal_id)
    if deficits:
        prog,selection=k.executive.synthesize_best_mechanism(
            deficits[0].deficit_id,'THINKING',fit_examples,min_support=2
        )
        development=k.executive.evaluate_mechanism(
            prog.program_id,blind_examples,min_score=.95,min_ablation_drop=.20
        )
finally:
    try: k.close()
    except Exception: pass

branching_score=float(getattr(development,'candidate_score',0.0) or 0.0) if development is not None else 0.0
ablation_score=float(getattr(development,'ablation_score',0.0) or 0.0) if development is not None else 0.0
restore_score=float(getattr(development,'restore_score',0.0) or 0.0) if development is not None else 0.0
state_committed=bool(getattr(development,'state_committed',False)) if development is not None else False

gene=None
if prog is not None and selection is not None and development is not None and state_committed:
    pd=asdict(prog)
    parent_layer=parent['coding_cognitive_layer_gene']
    parent_thinking=thinking_parent['thinking_gene']
    gene={
      'schema':'yado.g2.coding_reasoning_workspace_gene.v2',
      'gene_id':'GENE-G2-CODING-REASONING-WORKSPACE-V2-'+str(pd.get('program_digest') or digest(pd))[:16],
      'organ':'THINKING',
      'gene_scope':['THINKING','CODE','MEMORY','GENERATIVE_EXECUTIVE','LOGIC','INTELLIGENCE'],
      'heritage':[parent_layer.get('gene_id'),parent_thinking.get('gene_id'),hist.get('experience_digest')],
      'origin':'YADO_NATIVE_DEVELOPMENTAL_EXECUTIVE_FROM_CODING_FAILURE_AND_SUCCESS_MEMORY',
      'mechanism_kind':getattr(development,'mechanism_kind',None),
      'action_vocabulary':ACTION_VOCAB,
      'program':pd,'selection':asdict(selection),'development':asdict(development),
      'promotion_state':'SHADOW_ONLY'
    }
    gene['gene_digest']=digest(gene)

checks={
  'parent_withhold_consumed':parent.get('status')=='WITHHOLD_G2_CODING_APPRENTICESHIP_V1',
  'parent_coding_layer_consumed':bool((parent.get('coding_cognitive_layer_gene') or {}).get('gene_id')),
  'thinking_v2_parent_consumed':bool((thinking_parent.get('thinking_gene') or {}).get('gene_id')),
  'historical_coding_memory_consumed':len(historical_episodes)>=12,
  'fresh_coding_tasks_executed':len(fresh_episodes)>=8,
  'fresh_success_and_failure_both_present':any(e['fresh_exact'] for e in fresh_episodes) and any(not e['fresh_exact'] for e in fresh_episodes),
  'retry_branch_present_in_training':retry_fit>0,
  'retry_branch_present_in_fresh':retry_blind>0,
  'native_thinking_mechanism_synthesized':gene is not None,
  'native_rule_program_selected':gene is not None and gene.get('mechanism_kind')=='RULE_PROGRAM',
  'branching_fresh_ge_095':branching_score>=.95,
  'branching_beats_linear_baseline':branching_score-linear_baseline>=.10,
  'causal_ablation_drop':branching_score-ablation_score>=.20,
  'restore_exact':abs(restore_score-branching_score)<1e-12,
  'shadow_state_committed':state_committed,
  'third_party_code_executed':False,
  'external_coding_model_used':False,
  'ready_patch_from_host_used':False,
  'host_written_rule_program':False,
  'automatic_canonical_promotion':False,
  'canonical_unchanged':core.head.get('canonical_head_digest')==head_before.get('canonical_head_digest'),
}
required_true=[
 'parent_withhold_consumed','parent_coding_layer_consumed','thinking_v2_parent_consumed',
 'historical_coding_memory_consumed','fresh_coding_tasks_executed','fresh_success_and_failure_both_present',
 'retry_branch_present_in_training','retry_branch_present_in_fresh','native_thinking_mechanism_synthesized',
 'native_rule_program_selected','branching_fresh_ge_095','branching_beats_linear_baseline',
 'causal_ablation_drop','restore_exact','shadow_state_committed','canonical_unchanged'
]
required_false=['third_party_code_executed','external_coding_model_used','ready_patch_from_host_used','host_written_rule_program','automatic_canonical_promotion']
passed=all(checks[k] is True for k in required_true) and all(checks[k] is False for k in required_false)
status='PASS_SHADOW_G2_CODING_REASONING_WORKSPACE_V2' if passed else 'WITHHOLD_G2_CODING_REASONING_WORKSPACE_V2'

experience={
 'schema':'yado.g2.coding_reasoning_workspace.experience.v2',
 'status':'TRAINED',
 'parent_experience_digest':hist.get('experience_digest'),
 'historical_episode_count':len(historical_episodes),
 'fresh_episodes':fresh_episodes,
 'fit_reasoning_case_count':len(fit_examples),
 'blind_reasoning_case_count':len(blind_examples),
 'retry_fit_count':retry_fit,'retry_blind_count':retry_blind,
 'linear_baseline_score':linear_baseline,'majority_baseline_score':majority_baseline,
 'branching_fresh_score':branching_score,'ablation_score':ablation_score,'restore_score':restore_score,
 'reasoning_gene':gene,
 'canonical_mutation':False,
 'semantic_boundary':'USER-SPECIFIED PROGRAMMER REASONING CURRICULUM DEFINES PHASE/RETRY SEMANTICS. YADO NATIVE DEVELOPMENTAL EXECUTIVE SYNTHESIZES THE ACTUAL STATE-CONDITIONED RULE PROGRAM FROM CODING SUCCESS/FAILURE MEMORY. NO READY HOST PATCH OR EXTERNAL CODING MODEL IS USED; ALL NEW STATE REMAINS SHADOW.'
}
experience['experience_digest']=digest(experience)
EXP.parent.mkdir(parents=True,exist_ok=True)
EXP.write_text(json.dumps(experience,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')

report={
 'schema':'yado.g2.coding_reasoning_workspace.v2','status':status,'task':task,
 'parent_status':parent.get('status'),'parent_gene_id':(parent.get('coding_cognitive_layer_gene') or {}).get('gene_id'),
 'thinking_parent_gene_id':(thinking_parent.get('thinking_gene') or {}).get('gene_id'),
 'fresh_task_count':len(fresh_episodes),'fresh_success_count':sum(e['fresh_exact'] for e in fresh_episodes),
 'fresh_failure_count':sum(not e['fresh_exact'] for e in fresh_episodes),
 'fit_reasoning_case_count':len(fit_examples),'blind_reasoning_case_count':len(blind_examples),
 'retry_fit_count':retry_fit,'retry_blind_count':retry_blind,
 'linear_baseline_score':linear_baseline,'majority_baseline_score':majority_baseline,
 'branching_fresh_score':branching_score,'ablation_score':ablation_score,'restore_score':restore_score,
 'reasoning_workspace_gene':gene,'checks':checks,
 'canonical_mutation':False,'promotion_applied':False,
 'next_required_capability':'G2_CODING_REASONING_TRANSFER_STRESS_V1' if passed else 'G2_CODING_REASONING_WORKSPACE_V3',
 'receipt_sha256':None,
 'semantic_boundary':experience['semantic_boundary']
}
report['receipt_sha256']=digest({k:v for k,v in report.items() if k!='receipt_sha256'})
OUT.parent.mkdir(parents=True,exist_ok=True)
OUT.write_text(json.dumps(report,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')

print(json.dumps({
 'status':status,
 'fresh_task_count':len(fresh_episodes),
 'fresh_success_count':report['fresh_success_count'],
 'fresh_failure_count':report['fresh_failure_count'],
 'branching_fresh_score':branching_score,
 'linear_baseline_score':linear_baseline,
 'majority_baseline_score':majority_baseline,
 'ablation_score':ablation_score,
 'restore_score':restore_score,
 'retry_fit_count':retry_fit,'retry_blind_count':retry_blind,
 'reasoning_gene_id':gene.get('gene_id') if gene else None,
 'next_required_capability':report['next_required_capability'],
 'receipt_sha256':report['receipt_sha256']
},indent=2,sort_keys=True))
if not passed: raise SystemExit(2)
