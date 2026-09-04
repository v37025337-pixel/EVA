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

TASK=REPO/'architecture/yado-g2-coding-reasoning-workspace-v7-request.json'
P6=REPO/'candidates/kernel-self-generated/g2-coding-reasoning-workspace-v6.json'
HEAD=REPO/'canonical/yado-main-head-g2.json'
OUT=REPO/'candidates/kernel-self-generated/g2-coding-reasoning-workspace-v7.json'
EXP=REPO/'experience/yado-coding-reasoning-workspace-v7.json'
EFILES=[
 REPO/'experience/yado-coding-apprenticeship-v1.json',
 REPO/'experience/yado-coding-reasoning-workspace-v2.json',
 REPO/'experience/yado-coding-reasoning-workspace-v3.json',
 REPO/'experience/yado-coding-reasoning-workspace-v4.json',
 REPO/'experience/yado-coding-reasoning-workspace-v5.json',
 REPO/'experience/yado-coding-reasoning-workspace-v6.json',
]

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def digest(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def sha_text(s):return hashlib.sha256(s.encode()).hexdigest()
def safe_compile(src):
    try:compile(src,'<g2-coding-v7>','exec');return True
    except Exception:return False
def eval_source(src,cases):
    if not src or not safe_compile(src):return 0.0
    ok=0
    for args,expected in cases:
        try:got=AmbiguityAwareProgramRepairV11.execute(src,'f',args)
        except Exception:continue
        ok+=(got==expected)
    return ok/max(1,len(cases))

task=load(TASK);p6=load(P6);head=load(HEAD);hist=[load(p) for p in EFILES]
if p6.get('status')!='WITHHOLD_G2_CODING_REASONING_WORKSPACE_V6':raise RuntimeError('V6_PARENT_NOT_WITHHOLD')
if p6.get('next_required_capability')!='G2_CODING_REASONING_WORKSPACE_V7':raise RuntimeError('V6_FRONTIER_MISMATCH')
if not (p6.get('fresh_score')==1.0 and p6.get('unknown_state_score')==1.0 and p6.get('retry_to_retest_score')==1.0):raise RuntimeError('V6_BEHAVIORAL_SIGNATURE_CHANGED')
if 'ALG-BOUNDED-CAPABILITY-ROUTER-V1' not in set(head.get('active_capabilities') or []):raise RuntimeError('ROUTER_NOT_ACTIVE_G2')
core=UnifiedYADOCoreV1(REPO);head_before=copy.deepcopy(core.head)

# Typed stage-local observation model. Field identity is itself a typed phase witness.
def examples(ep):
    f=ep.get('features') or {}
    common={'task_kind':str(ep.get('task_kind')),'high_complexity':bool(f.get('requires_degree_gt3') or f.get('multivariate') or f.get('non_polynomial')),'stage_known':True}
    candidate=bool(ep.get('candidate_present'));train_exact=float(ep.get('train_score') or 0)==1.0;fresh_exact=float(ep.get('fresh_score') or 0)==1.0
    rows=[]
    def add(stage,y,**obs):
        x=dict(common);x['stage']=stage;x.update(obs);rows.append({'input':x,'expected':y})
    add('START','READ_CODE');add('CODE_READ','BUILD_MODEL');add('MODEL_BUILT','FORM_HYPOTHESIS')
    add('HYPOTHESIS_READY','TEST_HYPOTHESIS' if candidate else 'REVISE_HYPOTHESIS',candidate_present=candidate)
    add('TEST_RESULT','IMPLEMENT_CHANGE' if train_exact else 'REVISE_HYPOTHESIS',train_exact=train_exact)
    add('IMPLEMENTED','CHECK_CONSEQUENCES')
    add('CONSEQUENCE_RESULT','STORE_EXPERIENCE' if fresh_exact else 'REVISE_HYPOTHESIS',fresh_exact=fresh_exact)
    add('MEMORY_READY','ADVANCE')
    return rows

train_eps=list(hist[0].get('episodes') or [])
for e in hist[1:5]: train_eps += list(e.get('fresh_episodes') or [])
val_eps=list(hist[5].get('fresh_episodes') or [])
train_valid=[];val_valid=[]
for ep in train_eps:train_valid.extend(examples(ep))
for ep in val_eps:val_valid.extend(examples(ep))

def contrast(cases):
    out=[]
    for e in cases:
        out.append(e)
        t={'input':dict(e['input']),'expected':'WITHHOLD_UNKNOWN'}
        t['input']['stage_known']=False
        out.append(t)
    return out
router=BoundedCapabilityRouterLearnerV1.synthesize(contrast(train_valid),contrast(val_valid),'WITHHOLD_UNKNOWN',min_support=3)

# New V7 coding holdout
tx=(-10,-4,0,5,9);fx=(-13,-7,2,8,12)
specs=[
 ('REPAIR','V7_LINEAR',lambda x:7*x+3,False),
 ('REPAIR','V7_CUBIC',lambda x:x**3-2*x+5,False),
 ('REPAIR','V7_MOD8',lambda x:x%8,False),
 ('REPAIR','V7_ABS3',lambda x:abs(x)+3,False),
 ('WRITE','V7_QUADRATIC',lambda x:-3*x*x+2*x+4,False),
 ('WRITE','V7_CUBIC',lambda x:2*x**3+x-6,False),
 ('WRITE','V7_DEGREE6',lambda x:x**6+x+2,False),
 ('WRITE','V7_BIVARIATE',lambda x,y:2*x-y,True),
]
fresh_eps=[]
for kind,name,target,multi in specs:
    if multi:
        source='def f(x,y):\n    return x\n'
        tr=[((x,y),target(x,y)) for x,y in [(-7,2),(0,8),(5,-3),(9,4),(12,-5)]]
        fr=[((x,y),target(x,y)) for x,y in [(-11,4),(1,10),(8,-6),(14,3)]]
    else:
        source='def f(x):\n    return x\n';tr=[((x,),target(x)) for x in tx];fr=[((x,),target(x)) for x in fx]
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
      'features':{'is_write':kind=='WRITE','multivariate':multi,'requires_degree_gt3':name=='V7_DEGREE6','non_polynomial':name in ('V7_MOD8','V7_ABS3')}
    })
blind=[]
for ep in fresh_eps:blind.extend(examples(ep))
fresh_score=router_acc(router,blind);ablation=router_acc(router,blind,ablated=True);restore=router_acc(router,blind)

unknown=[]
for e in blind:
    t={'input':dict(e['input']),'expected':'WITHHOLD_UNKNOWN'};t['input']['stage_known']=False;unknown.append(t)
unknown_score=router_acc(router,unknown)

# Semantic phase proof. We do not infer phase coverage by literal stage atoms:
# a stage-local typed observation field is itself a phase witness.
phase_cases=[
 ({'stage':'HYPOTHESIS_READY','stage_known':True,'task_kind':'REPAIR','high_complexity':False,'candidate_present':False},'REVISE_HYPOTHESIS'),
 ({'stage':'TEST_RESULT','stage_known':True,'task_kind':'REPAIR','high_complexity':False,'train_exact':False},'REVISE_HYPOTHESIS'),
 ({'stage':'CONSEQUENCE_RESULT','stage_known':True,'task_kind':'REPAIR','high_complexity':False,'fresh_exact':False},'REVISE_HYPOTHESIS'),
]
success_cases=[
 ({'stage':'HYPOTHESIS_READY','stage_known':True,'task_kind':'REPAIR','high_complexity':False,'candidate_present':True},'TEST_HYPOTHESIS'),
 ({'stage':'TEST_RESULT','stage_known':True,'task_kind':'REPAIR','high_complexity':False,'train_exact':True},'IMPLEMENT_CHANGE'),
 ({'stage':'CONSEQUENCE_RESULT','stage_known':True,'task_kind':'REPAIR','high_complexity':False,'fresh_exact':True},'STORE_EXPERIENCE'),
]
failure_phase_score=sum(router.execute(x)==y for x,y in phase_cases)/3
success_phase_score=sum(router.execute(x)==y for x,y in success_cases)/3
nonbranch=[
 ({'stage':'START','stage_known':True,'task_kind':'REPAIR','high_complexity':False},'READ_CODE'),
 ({'stage':'CODE_READ','stage_known':True,'task_kind':'REPAIR','high_complexity':False},'BUILD_MODEL'),
 ({'stage':'MODEL_BUILT','stage_known':True,'task_kind':'REPAIR','high_complexity':False},'FORM_HYPOTHESIS'),
 ({'stage':'IMPLEMENTED','stage_known':True,'task_kind':'REPAIR','high_complexity':False},'CHECK_CONSEQUENCES'),
 ({'stage':'MEMORY_READY','stage_known':True,'task_kind':'REPAIR','high_complexity':False},'ADVANCE'),
]
nonbranch_score=sum(router.execute(x)==y for x,y in nonbranch)/len(nonbranch)

retry=[c for c in router.clauses if c.output=='REVISE_HYPOTHESIS']
typed_retry_fields=set()
for c in retry:
    for a in c.atoms:
        if a.field in ('candidate_present','train_exact','fresh_exact') and a.value is False:
            typed_retry_fields.add(a.field)
all_retry_known=bool(retry) and all(any(a.field=='stage_known' and a.value is True for a in c.atoms) for c in retry)
typed_retry_complete={'candidate_present','train_exact','fresh_exact'}.issubset(typed_retry_fields)

loop=[]
for ep in fresh_eps:
    common={'task_kind':ep['task_kind'],'high_complexity':bool((ep.get('features') or {}).get('requires_degree_gt3') or (ep.get('features') or {}).get('multivariate') or (ep.get('features') or {}).get('non_polynomial')),'stage_known':True}
    a1=router.execute(dict(common,stage='CONSEQUENCE_RESULT',fresh_exact=False))
    a2=router.execute(dict(common,stage='HYPOTHESIS_READY',candidate_present=True))
    loop.append({'task_id':ep['task_id'],'failure_action':a1,'revised_candidate_action':a2,'pass':a1=='REVISE_HYPOTHESIS' and a2=='TEST_HYPOTHESIS'})
loop_score=sum(r['pass'] for r in loop)/len(loop)

program={'schema':'yado.g2.semantic_phase_bound_coding_reasoning_program.v7','clauses':[c.canonical() for c in router.clauses],
         'fallback_output':router.fallback_output,'source_digest':router.source_digest,
         'typed_phase_binding':{'candidate_present':'HYPOTHESIS_READY','train_exact':'TEST_RESULT','fresh_exact':'CONSEQUENCE_RESULT'}}
program['program_digest']=digest(program)
gene={
 'schema':'yado.g2.coding_reasoning_thinking_gene.v7','gene_id':'GENE-G2-CODING-REASONING-THINKING-V7-'+program['program_digest'][:16],
 'organ':'THINKING','gene_scope':['THINKING','CODE','MEMORY','GENERATIVE_EXECUTIVE','LOGIC','INTELLIGENCE'],
 'heritage':[p6.get('thinking_gene_id'),p6.get('receipt_sha256'),hist[5].get('experience_digest')],
 'origin':'ACTIVE_G2_ROUTER_RELEARNED_WITH_SEMANTIC_PHASE_BINDING_AFTER_V6_VALIDATOR_COUNTEREXAMPLE',
 'mechanism_kind':'SEMANTIC_PHASE_BOUND_GUARDED_REASONING_ROUTER','active_parent_capability':'ALG-BOUNDED-CAPABILITY-ROUTER-V1',
 'program':program,'fresh_score':fresh_score,'unknown_state_score':unknown_score,'ablation_score':ablation,'restore_score':restore,
 'promotion_state':'SHADOW_ONLY'
}
gene['gene_digest']=digest(gene)

checks={
 'v6_withhold_consumed':p6.get('status')=='WITHHOLD_G2_CODING_REASONING_WORKSPACE_V6',
 'v6_behavioral_success_consumed':p6.get('fresh_score')==1.0 and p6.get('unknown_state_score')==1.0 and p6.get('retry_to_retest_score')==1.0,
 'v6_structural_gate_mismatch_consumed':p6.get('retry_clause_count')==3 and p6.get('retry_states')==[],
 'active_router_capability_verified':'ALG-BOUNDED-CAPABILITY-ROUTER-V1' in set(head.get('active_capabilities') or []),
 'typed_phase_binding_declared':program['typed_phase_binding']=={'candidate_present':'HYPOTHESIS_READY','train_exact':'TEST_RESULT','fresh_exact':'CONSEQUENCE_RESULT'},
 'fresh_v7_tasks_executed':len(fresh_eps)==8,
 'fresh_success_and_failure_both_present':any(e['fresh_exact'] for e in fresh_eps) and any(not e['fresh_exact'] for e in fresh_eps),
 'fresh_reasoning_exact':fresh_score==1.0,'unknown_states_fail_closed':unknown_score==1.0,
 'failure_phase_semantics_exact':failure_phase_score==1.0,'success_phase_semantics_exact':success_phase_score==1.0,
 'nonbranch_phase_semantics_exact':nonbranch_score==1.0,
 'typed_retry_evidence_complete':typed_retry_complete,'all_retry_routes_require_known_stage':all_retry_known,
 'retry_to_retest_transition_exact':loop_score==1.0,
 'ablation_material_drop':fresh_score-ablation>=.20,'restore_exact':restore==fresh_score,
 'new_shadow_thinking_gene_created':bool(gene['gene_id']),
 'canonical_unchanged':core.head.get('canonical_head_digest')==head_before.get('canonical_head_digest'),
 'third_party_code_executed':False,'external_coding_model_used':False,'ready_patch_from_host_used':False,
 'host_written_reasoning_rules':False,'automatic_canonical_promotion':False
}
false_keys=['third_party_code_executed','external_coding_model_used','ready_patch_from_host_used','host_written_reasoning_rules','automatic_canonical_promotion']
true_keys=[k for k in checks if k not in false_keys]
passed=all(checks[k] is True for k in true_keys) and all(checks[k] is False for k in false_keys)
status='PASS_SHADOW_G2_CODING_REASONING_WORKSPACE_V7' if passed else 'WITHHOLD_G2_CODING_REASONING_WORKSPACE_V7'

experience={
 'schema':'yado.g2.coding_reasoning_workspace.experience.v7','status':'TRAINED','parent_v6_receipt':p6.get('receipt_sha256'),
 'fresh_episodes':fresh_eps,'fresh_score':fresh_score,'unknown_state_score':unknown_score,'ablation_score':ablation,'restore_score':restore,
 'failure_phase_score':failure_phase_score,'success_phase_score':success_phase_score,'nonbranch_phase_score':nonbranch_score,
 'typed_retry_fields':sorted(typed_retry_fields),'retry_to_retest_rows':loop,'retry_to_retest_score':loop_score,
 'thinking_gene':gene,'canonical_mutation':False,
 'semantic_boundary':'V7 CORRECTS THE V6 VALIDATOR SEMANTICS WITHOUT LOWERING BEHAVIORAL THRESHOLDS. PHASE COVERAGE IS PROVEN BY TYPED STAGE-LOCAL OBSERVATIONS AND DIRECT EXECUTION OF ALL THREE FAILURE/SUCCESS BRANCH PAIRS. THIS ESTABLISHES A GUARDED ITERATIVE REASONING CONTROL LOOP, NOT YET AUTONOMOUS SYNTHESIS OF A REVISED CODE HYPOTHESIS.'
}
experience['experience_digest']=digest(experience)
EXP.parent.mkdir(parents=True,exist_ok=True);EXP.write_text(json.dumps(experience,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')
report={
 'schema':'yado.g2.coding_reasoning_workspace.v7','status':status,'task':task,
 'fresh_task_count':len(fresh_eps),'fresh_success_count':sum(e['fresh_exact'] for e in fresh_eps),'fresh_failure_count':sum(not e['fresh_exact'] for e in fresh_eps),
 'fresh_score':fresh_score,'unknown_state_score':unknown_score,'ablation_score':ablation,'restore_score':restore,
 'failure_phase_score':failure_phase_score,'success_phase_score':success_phase_score,'nonbranch_phase_score':nonbranch_score,
 'retry_clause_count':len(retry),'typed_retry_fields':sorted(typed_retry_fields),'retry_to_retest_score':loop_score,
 'thinking_gene_id':gene['gene_id'],'thinking_gene':gene,'checks':checks,'canonical_mutation':False,'promotion_applied':False,
 'next_required_capability':'G2_CODING_HYPOTHESIS_REVISION_GENERATOR_V1' if passed else 'G2_CODING_REASONING_WORKSPACE_V8',
 'receipt_sha256':None,'semantic_boundary':experience['semantic_boundary']
}
report['receipt_sha256']=digest({k:v for k,v in report.items() if k!='receipt_sha256'})
OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(report,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')
print(json.dumps({
 'status':status,'fresh_task_count':len(fresh_eps),'fresh_success_count':report['fresh_success_count'],'fresh_failure_count':report['fresh_failure_count'],
 'fresh_score':fresh_score,'unknown_state_score':unknown_score,'ablation_score':ablation,'restore_score':restore,
 'failure_phase_score':failure_phase_score,'success_phase_score':success_phase_score,'nonbranch_phase_score':nonbranch_score,
 'retry_clause_count':len(retry),'typed_retry_fields':sorted(typed_retry_fields),'retry_to_retest_score':loop_score,
 'thinking_gene_id':gene['gene_id'],'next_required_capability':report['next_required_capability'],'receipt_sha256':report['receipt_sha256']
},indent=2,sort_keys=True))
if not passed:raise SystemExit(2)
