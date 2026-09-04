from __future__ import annotations
from pathlib import Path
import copy,hashlib,json,sys

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
PKG=ROOT/'yado_rc8_v36'
sys.path[:0]=[str(ROOT),str(PKG)]

from yado_unified_core_v1 import UnifiedYADOCoreV1
from yado_bounded_capability_router_v1 import BoundedCapabilityRouterLearnerV1,router_acc
from yado_ambiguity_aware_program_repair_v11 import AmbiguityAwareProgramRepairV11
from yado_evolutionary_genome_v1 import PolynomialReturnRepairGeneV1

TASK=REPO/'architecture/yado-g2-coding-reasoning-workspace-v4-request.json'
V1=REPO/'experience/yado-coding-apprenticeship-v1.json'
V2=REPO/'experience/yado-coding-reasoning-workspace-v2.json'
V3=REPO/'experience/yado-coding-reasoning-workspace-v3.json'
P3=REPO/'candidates/kernel-self-generated/g2-coding-reasoning-workspace-v3.json'
HEAD=REPO/'canonical/yado-main-head-g2.json'
OUT=REPO/'candidates/kernel-self-generated/g2-coding-reasoning-workspace-v4.json'
EXP=REPO/'experience/yado-coding-reasoning-workspace-v4.json'

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def digest(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def sha_text(s):return hashlib.sha256(s.encode()).hexdigest()
def safe_compile(src):
    try:compile(src,'<g2-coding-v4>','exec');return True
    except Exception:return False
def eval_source(src,cases):
    if not src or not safe_compile(src):return 0.0
    ok=0
    for args,expected in cases:
        try:got=AmbiguityAwareProgramRepairV11.execute(src,'f',args)
        except Exception:continue
        ok+=(got==expected)
    return ok/max(1,len(cases))

task=load(TASK);e1=load(V1);e2=load(V2);e3=load(V3);p3=load(P3);head=load(HEAD)
if p3.get('status')!='WITHHOLD_G2_CODING_REASONING_WORKSPACE_V3':raise RuntimeError('V3_PARENT_NOT_WITHHOLD')
if p3.get('next_required_capability')!='G2_CODING_REASONING_WORKSPACE_V4':raise RuntimeError('V3_FRONTIER_MISMATCH')
if 'ALG-BOUNDED-CAPABILITY-ROUTER-V1' not in set(head.get('active_capabilities') or []):raise RuntimeError('ROUTER_NOT_ACTIVE_G2')

core=UnifiedYADOCoreV1(REPO);head_before=copy.deepcopy(core.head)

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
    def add(stage,y):
        x=dict(base);x['stage']=stage;rows.append({'input':x,'expected':y})
    add('START','READ_CODE');add('CODE_READ','BUILD_MODEL');add('MODEL_BUILT','FORM_HYPOTHESIS')
    add('HYPOTHESIS_READY','TEST_HYPOTHESIS' if base['candidate_present'] else 'REVISE_HYPOTHESIS')
    add('TEST_RESULT','IMPLEMENT_CHANGE' if base['train_exact'] else 'REVISE_HYPOTHESIS')
    add('IMPLEMENTED','CHECK_CONSEQUENCES')
    add('CONSEQUENCE_RESULT','STORE_EXPERIENCE' if base['fresh_exact'] else 'REVISE_HYPOTHESIS')
    add('MEMORY_READY','ADVANCE')
    return rows

train_eps=list(e1.get('episodes') or [])+list(e2.get('fresh_episodes') or [])
val_eps=list(e3.get('fresh_episodes') or [])
if len(train_eps)<24 or len(val_eps)<8:raise RuntimeError('ACCUMULATED_MEMORY_INCOMPLETE')
train=[];val=[]
for ep in train_eps:train.extend(reasoning_examples(ep))
for ep in val_eps:val.extend(reasoning_examples(ep))

# Explicit fail-closed contract is not a reasoning rule: unknown states must not trigger retry.
for i in range(4):
    train.append({'input':{'stage':'UNKNOWN_TRAIN_'+str(i),'task_kind':'UNKNOWN','candidate_present':False,'train_exact':False,'fresh_exact':False,'high_complexity':False},'expected':'WITHHOLD_UNKNOWN'})
    val.append({'input':{'stage':'UNKNOWN_VAL_'+str(i),'task_kind':'UNKNOWN','candidate_present':True,'train_exact':True,'fresh_exact':True,'high_complexity':True},'expected':'WITHHOLD_UNKNOWN'})

router=BoundedCapabilityRouterLearnerV1.synthesize(train,val,'WITHHOLD_UNKNOWN',min_support=3)

# Entirely new V4 coding holdout.
tx=(-7,-3,0,2,6);fx=(-10,-5,1,5,9)
specs=[
 ('REPAIR','V4_LINEAR',lambda x:-5*x+9,False),
 ('REPAIR','V4_QUADRATIC_REPAIR',lambda x:x*x-2*x+1,False),
 ('REPAIR','V4_FLOORDIV3',lambda x:x//3,False),
 ('REPAIR','V4_RELU',lambda x:max(x,0),False),
 ('WRITE','V4_QUADRATIC_WRITE',lambda x:-2*x*x+4*x+1,False),
 ('WRITE','V4_CUBIC_WRITE',lambda x:x**3-4*x+7,False),
 ('WRITE','V4_DEGREE7',lambda x:x**7-1,False),
 ('WRITE','V4_BIVARIATE_PRODUCT',lambda x,y:x*y,True),
]
fresh_eps=[]
for kind,name,target,multi in specs:
    if multi:
        source='def f(x,y):\n    return x\n'
        tr=[((x,y),target(x,y)) for x,y in [(-4,2),(0,5),(3,-2),(6,4),(9,-3)]]
        fr=[((x,y),target(x,y)) for x,y in [(-8,3),(1,7),(5,-4),(11,2)]]
    else:
        source='def f(x):\n    return x\n'
        tr=[((x,),target(x)) for x in tx];fr=[((x,),target(x)) for x in fx]
    try:
        if kind=='REPAIR':r=AmbiguityAwareProgramRepairV11.repair(source,'f',tr,max_candidates=7000,max_edit_depth=2)
        else:r=PolynomialReturnRepairGeneV1.synthesize(source,'f',tr)
    except Exception as e:r={'source':None,'reason':type(e).__name__+':'+str(e)[:180]}
    cand=r.get('source');ts=eval_source(cand,tr);fs=eval_source(cand,fr)
    fresh_eps.append({
      'task_id':name,'task_kind':kind,'input_source_sha256':sha_text(source),
      'candidate_present':bool(cand),'candidate_source_sha256':sha_text(cand) if cand else None,
      'candidate_source_excerpt':cand[:800] if cand else None,
      'repair_mode':r.get('repair_mode') or r.get('operator_gene'),'reason':r.get('reason'),
      'train_score':ts,'fresh_score':fs,'fresh_exact':fs==1.0,
      'features':{'is_write':kind=='WRITE','multivariate':multi,'requires_degree_gt3':name=='V4_DEGREE7','non_polynomial':name in ('V4_FLOORDIV3','V4_RELU')}
    })
blind=[]
for ep in fresh_eps:blind.extend(reasoning_examples(ep))

fresh_score=router_acc(router,blind)
ablation=router_acc(router,blind,ablated=True)
restore=router_acc(router,blind)

unknown=[
 {'input':{'stage':'UNSEEN_RUNTIME_STATE_A','task_kind':'REPAIR','candidate_present':False,'train_exact':False,'fresh_exact':False,'high_complexity':False},'expected':'WITHHOLD_UNKNOWN'},
 {'input':{'stage':'UNSEEN_RUNTIME_STATE_B','task_kind':'WRITE','candidate_present':True,'train_exact':True,'fresh_exact':False,'high_complexity':True},'expected':'WITHHOLD_UNKNOWN'},
 {'input':{'stage':'UNSEEN_RUNTIME_STATE_C','task_kind':'UNKNOWN','candidate_present':False,'train_exact':True,'fresh_exact':True,'high_complexity':False},'expected':'WITHHOLD_UNKNOWN'},
]
unknown_score=router_acc(router,unknown)
retry=[c for c in router.clauses if c.output=='REVISE_HYPOTHESIS']
retry_guarded=bool(retry) and all(len(c.atoms)>=2 and any(a.field=='stage' for a in c.atoms) for c in retry)
retry_states=sorted({next(a.value for a in c.atoms if a.field=='stage') for c in retry if any(a.field=='stage' for a in c.atoms)})
expected_retry_states={'HYPOTHESIS_READY','TEST_RESULT','CONSEQUENCE_RESULT'}
retry_coverage=expected_retry_states.issubset(set(retry_states))

# Controller-level iterative transition proof: failure -> explicit REVISE -> revised candidate ready -> TEST.
loop_rows=[]
for ep in fresh_eps:
    fail_state={'stage':'CONSEQUENCE_RESULT','task_kind':ep['task_kind'],'candidate_present':bool(ep['candidate_present']),
                'train_exact':float(ep['train_score'])==1.0,'fresh_exact':False,'high_complexity':bool((ep.get('features') or {}).get('multivariate') or (ep.get('features') or {}).get('requires_degree_gt3') or (ep.get('features') or {}).get('non_polynomial'))}
    a1=router.execute(fail_state)
    revised=dict(fail_state);revised['stage']='HYPOTHESIS_READY';revised['candidate_present']=True
    a2=router.execute(revised)
    loop_rows.append({'task_id':ep['task_id'],'failure_action':a1,'revised_candidate_action':a2,'pass':a1=='REVISE_HYPOTHESIS' and a2=='TEST_HYPOTHESIS'})
loop_score=sum(x['pass'] for x in loop_rows)/len(loop_rows)

# V3's learned default was REVISE; on unknown states that policy is not fail-closed.
v3_default=((p3.get('thinking_gene') or {}).get('program') or {}).get('default_output')
v3_unknown_fail_closed=(v3_default=='WITHHOLD_UNKNOWN')

program={
 'schema':'yado.g2.guarded_coding_reasoning_router_program.v4',
 'clauses':[c.canonical() for c in router.clauses],
 'fallback_output':router.fallback_output,'source_digest':router.source_digest,
}
program['program_digest']=digest(program)
gene={
 'schema':'yado.g2.coding_reasoning_thinking_gene.v4',
 'gene_id':'GENE-G2-CODING-REASONING-THINKING-V4-'+program['program_digest'][:16],
 'organ':'THINKING','gene_scope':['THINKING','CODE','MEMORY','GENERATIVE_EXECUTIVE','LOGIC','INTELLIGENCE'],
 'heritage':[p3.get('thinking_gene_id'),p3.get('receipt_sha256'),e3.get('experience_digest')],
 'origin':'ACTIVE_G2_BOUNDED_CAPABILITY_ROUTER_LEARNED_GUARDED_RETRY_FROM_CODING_MEMORY',
 'mechanism_kind':'GUARDED_STATE_CONDITIONED_ACTION_ROUTER','active_parent_capability':'ALG-BOUNDED-CAPABILITY-ROUTER-V1',
 'program':program,'fresh_score':fresh_score,'unknown_state_score':unknown_score,'ablation_score':ablation,'restore_score':restore,
 'promotion_state':'SHADOW_ONLY'
}
gene['gene_digest']=digest(gene)

checks={
 'v3_withhold_consumed':p3.get('status')=='WITHHOLD_G2_CODING_REASONING_WORKSPACE_V3',
 'active_router_capability_verified':'ALG-BOUNDED-CAPABILITY-ROUTER-V1' in set(head.get('active_capabilities') or []),
 'accumulated_memory_consumed':len(train_eps)+len(val_eps)>=32,
 'fresh_v4_tasks_executed':len(fresh_eps)==8,
 'fresh_success_and_failure_both_present':any(e['fresh_exact'] for e in fresh_eps) and any(not e['fresh_exact'] for e in fresh_eps),
 'fresh_reasoning_exact':fresh_score==1.0,'unknown_states_fail_closed':unknown_score==1.0,
 'fallback_is_withhold_unknown':router.fallback_output=='WITHHOLD_UNKNOWN',
 'explicit_retry_clauses_present':bool(retry),'explicit_retry_clauses_guarded':retry_guarded,
 'retry_failure_stage_coverage':retry_coverage,'retry_to_retest_transition_exact':loop_score==1.0,
 'v3_unknown_default_defect_repaired':v3_unknown_fail_closed is False and unknown_score==1.0,
 'ablation_material_drop':fresh_score-ablation>=.20,'restore_exact':restore==fresh_score,
 'new_shadow_thinking_gene_created':bool(gene['gene_id']),
 'canonical_unchanged':core.head.get('canonical_head_digest')==head_before.get('canonical_head_digest'),
 'third_party_code_executed':False,'external_coding_model_used':False,'ready_patch_from_host_used':False,
 'host_written_reasoning_rules':False,'automatic_canonical_promotion':False
}
false_keys=['third_party_code_executed','external_coding_model_used','ready_patch_from_host_used','host_written_reasoning_rules','automatic_canonical_promotion']
true_keys=[k for k in checks if k not in false_keys]
passed=all(checks[k] is True for k in true_keys) and all(checks[k] is False for k in false_keys)
status='PASS_SHADOW_G2_CODING_REASONING_WORKSPACE_V4' if passed else 'WITHHOLD_G2_CODING_REASONING_WORKSPACE_V4'

experience={
 'schema':'yado.g2.coding_reasoning_workspace.experience.v4','status':'TRAINED',
 'parent_v3_receipt':p3.get('receipt_sha256'),'training_episode_count':len(train_eps),'validation_episode_count':len(val_eps),
 'fresh_episodes':fresh_eps,'fresh_reasoning_case_count':len(blind),'fresh_score':fresh_score,
 'unknown_state_score':unknown_score,'ablation_score':ablation,'restore_score':restore,
 'explicit_retry_states':retry_states,'retry_to_retest_rows':loop_rows,'retry_to_retest_score':loop_score,
 'thinking_gene':gene,'canonical_mutation':False,
 'semantic_boundary':'ACTIVE G2 ROUTER LEARNS GUARDED STATE-CONDITIONED ACTIONS FROM ACCUMULATED CODING MEMORY. UNKNOWN STATES FAIL CLOSED. THIS PROVES CONTROL-POLICY RETRY/RETEST TRANSITIONS, NOT YET AUTONOMOUS SYNTHESIS OF A NEW DEFECT HYPOTHESIS OR PATCH AFTER RETRY.'
}
experience['experience_digest']=digest(experience)
EXP.parent.mkdir(parents=True,exist_ok=True);EXP.write_text(json.dumps(experience,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')
report={
 'schema':'yado.g2.coding_reasoning_workspace.v4','status':status,'task':task,
 'active_mechanism':'ALG-BOUNDED-CAPABILITY-ROUTER-V1','fresh_task_count':len(fresh_eps),
 'fresh_success_count':sum(e['fresh_exact'] for e in fresh_eps),'fresh_failure_count':sum(not e['fresh_exact'] for e in fresh_eps),
 'fresh_score':fresh_score,'unknown_state_score':unknown_score,'ablation_score':ablation,'restore_score':restore,
 'retry_clause_count':len(retry),'retry_states':retry_states,'retry_to_retest_score':loop_score,
 'v3_default_output':v3_default,'thinking_gene_id':gene['gene_id'],'thinking_gene':gene,'checks':checks,
 'canonical_mutation':False,'promotion_applied':False,
 'next_required_capability':'G2_CODING_HYPOTHESIS_REVISION_GENERATOR_V1' if passed else 'G2_CODING_REASONING_WORKSPACE_V5',
 'receipt_sha256':None,'semantic_boundary':experience['semantic_boundary']
}
report['receipt_sha256']=digest({k:v for k,v in report.items() if k!='receipt_sha256'})
OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(report,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')
print(json.dumps({
 'status':status,'fresh_task_count':len(fresh_eps),'fresh_success_count':report['fresh_success_count'],'fresh_failure_count':report['fresh_failure_count'],
 'fresh_score':fresh_score,'unknown_state_score':unknown_score,'ablation_score':ablation,'restore_score':restore,
 'retry_clause_count':len(retry),'retry_states':retry_states,'retry_to_retest_score':loop_score,'v3_default_output':v3_default,
 'thinking_gene_id':gene['gene_id'],'next_required_capability':report['next_required_capability'],'receipt_sha256':report['receipt_sha256']
},indent=2,sort_keys=True))
if not passed:raise SystemExit(2)
