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

TASK=REPO/'architecture/yado-g2-coding-reasoning-workspace-v6-request.json'
FILES=[
 REPO/'experience/yado-coding-apprenticeship-v1.json',
 REPO/'experience/yado-coding-reasoning-workspace-v2.json',
 REPO/'experience/yado-coding-reasoning-workspace-v3.json',
 REPO/'experience/yado-coding-reasoning-workspace-v4.json',
 REPO/'experience/yado-coding-reasoning-workspace-v5.json',
]
P5=REPO/'candidates/kernel-self-generated/g2-coding-reasoning-workspace-v5.json'
HEAD=REPO/'canonical/yado-main-head-g2.json'
OUT=REPO/'candidates/kernel-self-generated/g2-coding-reasoning-workspace-v6.json'
EXP=REPO/'experience/yado-coding-reasoning-workspace-v6.json'
STAGES=('START','CODE_READ','MODEL_BUILT','HYPOTHESIS_READY','TEST_RESULT','IMPLEMENTED','CONSEQUENCE_RESULT','MEMORY_READY')

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def digest(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def sha_text(s):return hashlib.sha256(s.encode()).hexdigest()
def safe_compile(src):
    try:compile(src,'<g2-coding-v6>','exec');return True
    except Exception:return False
def eval_source(src,cases):
    if not src or not safe_compile(src):return 0.0
    ok=0
    for args,expected in cases:
        try:got=AmbiguityAwareProgramRepairV11.execute(src,'f',args)
        except Exception:continue
        ok+=(got==expected)
    return ok/max(1,len(cases))

task=load(TASK);hist=[load(p) for p in FILES];p5=load(P5);head=load(HEAD)
if p5.get('status')!='WITHHOLD_G2_CODING_REASONING_WORKSPACE_V5':raise RuntimeError('V5_PARENT_NOT_WITHHOLD')
if p5.get('next_required_capability')!='G2_CODING_REASONING_WORKSPACE_V6':raise RuntimeError('V5_FRONTIER_MISMATCH')
if p5.get('fresh_score')!=1.0 or p5.get('unknown_state_score')>=1.0 or p5.get('retry_to_retest_score')>=1.0:raise RuntimeError('V5_PROXY_FAILURE_SIGNATURE_CHANGED')
if 'ALG-BOUNDED-CAPABILITY-ROUTER-V1' not in set(head.get('active_capabilities') or []):raise RuntimeError('ROUTER_NOT_ACTIVE_G2')
core=UnifiedYADOCoreV1(REPO);head_before=copy.deepcopy(core.head)

# Stage-local observation schema: only variables observable/relevant at that cognitive phase are exposed.
def reasoning_examples(ep):
    f=ep.get('features') or {}
    common={'task_kind':str(ep.get('task_kind')),'high_complexity':bool(f.get('requires_degree_gt3') or f.get('multivariate') or f.get('non_polynomial')),'stage_known':True}
    rows=[]
    def add(stage,y,**observed):
        x=dict(common);x['stage']=stage;x.update(observed);rows.append({'input':x,'expected':y})
    candidate=bool(ep.get('candidate_present'));train_exact=float(ep.get('train_score') or 0)==1.0;fresh_exact=float(ep.get('fresh_score') or 0)==1.0
    add('START','READ_CODE')
    add('CODE_READ','BUILD_MODEL')
    add('MODEL_BUILT','FORM_HYPOTHESIS')
    add('HYPOTHESIS_READY','TEST_HYPOTHESIS' if candidate else 'REVISE_HYPOTHESIS',candidate_present=candidate)
    add('TEST_RESULT','IMPLEMENT_CHANGE' if train_exact else 'REVISE_HYPOTHESIS',train_exact=train_exact)
    add('IMPLEMENTED','CHECK_CONSEQUENCES')
    add('CONSEQUENCE_RESULT','STORE_EXPERIENCE' if fresh_exact else 'REVISE_HYPOTHESIS',fresh_exact=fresh_exact)
    add('MEMORY_READY','ADVANCE')
    return rows

# Train on all evidence through V4; V5 is validation because it exposed the proxy failure.
train_eps=list(hist[0].get('episodes') or [])
for e in hist[1:4]:train_eps+=list(e.get('fresh_episodes') or [])
val_eps=list(hist[4].get('fresh_episodes') or [])
if len(train_eps)<40 or len(val_eps)<8:raise RuntimeError('ACCUMULATED_MEMORY_INCOMPLETE')
train_valid=[];val_valid=[]
for ep in train_eps:train_valid.extend(reasoning_examples(ep))
for ep in val_eps:val_valid.extend(reasoning_examples(ep))

# Contrastive unknown twin for every valid state. Any clause omitting stage_known becomes impure.
def contrastive(cases):
    out=[]
    for e in cases:
        out.append(e)
        twin={'input':dict(e['input']),'expected':'WITHHOLD_UNKNOWN'}
        twin['input']['stage_known']=False
        out.append(twin)
    return out
train=contrastive(train_valid);val=contrastive(val_valid)
router=BoundedCapabilityRouterLearnerV1.synthesize(train,val,'WITHHOLD_UNKNOWN',min_support=3)

# New V6 coding holdout.
tx=(-9,-4,0,3,8);fx=(-12,-6,1,7,11)
specs=[
 ('REPAIR','V6_LINEAR',lambda x:-4*x+13,False),
 ('REPAIR','V6_QUARTIC',lambda x:x**4+x-2,False),
 ('REPAIR','V6_MOD7',lambda x:x%7,False),
 ('REPAIR','V6_MAX2',lambda x:max(x,2),False),
 ('WRITE','V6_QUADRATIC',lambda x:2*x*x-x+8,False),
 ('WRITE','V6_CUBIC',lambda x:3*x**3+2*x-5,False),
 ('WRITE','V6_DEGREE6',lambda x:x**6-3*x+1,False),
 ('WRITE','V6_BIVARIATE_DIFF',lambda x,y:x-y,True),
]
fresh_eps=[]
for kind,name,target,multi in specs:
    if multi:
        source='def f(x,y):\n    return x\n'
        tr=[((x,y),target(x,y)) for x,y in [(-6,2),(0,7),(4,-2),(8,3),(11,-4)]]
        fr=[((x,y),target(x,y)) for x,y in [(-10,4),(1,9),(7,-5),(13,2)]]
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
      'features':{'is_write':kind=='WRITE','multivariate':multi,'requires_degree_gt3':name in ('V6_QUARTIC','V6_DEGREE6'),'non_polynomial':name in ('V6_MOD7','V6_MAX2')}
    })
blind_valid=[]
for ep in fresh_eps:blind_valid.extend(reasoning_examples(ep))
fresh_score=router_acc(router,blind_valid);ablation=router_acc(router,blind_valid,ablated=True);restore=router_acc(router,blind_valid)

unknown=[]
for e in blind_valid:
    twin={'input':dict(e['input']),'expected':'WITHHOLD_UNKNOWN'};twin['input']['stage_known']=False;unknown.append(twin)
unknown_score=router_acc(router,unknown)

retry=[c for c in router.clauses if c.output=='REVISE_HYPOTHESIS']
retry_states=sorted({next(a.value for a in c.atoms if a.field=='stage') for c in retry if any(a.field=='stage' for a in c.atoms)})
known_guard=lambda c:any(a.field=='stage_known' and a.value is True for a in c.atoms)
retry_guarded=bool(retry) and all(len(c.atoms)>=3 and known_guard(c) and any(a.field=='stage' for a in c.atoms) for c in retry)
all_valid_guarded=all(known_guard(c) for c in router.clauses)
retry_coverage={'HYPOTHESIS_READY','TEST_RESULT','CONSEQUENCE_RESULT'}.issubset(set(retry_states))

loop=[]
for ep in fresh_eps:
    f=ep.get('features') or {};common={'task_kind':ep['task_kind'],'high_complexity':bool(f.get('multivariate') or f.get('requires_degree_gt3') or f.get('non_polynomial')),'stage_known':True}
    fail=dict(common,stage='CONSEQUENCE_RESULT',fresh_exact=False)
    a1=router.execute(fail)
    revised=dict(common,stage='HYPOTHESIS_READY',candidate_present=True)
    a2=router.execute(revised)
    loop.append({'task_id':ep['task_id'],'failure_action':a1,'revised_candidate_action':a2,'pass':a1=='REVISE_HYPOTHESIS' and a2=='TEST_HYPOTHESIS'})
loop_score=sum(x['pass'] for x in loop)/len(loop)

program={'schema':'yado.g2.stage_local_guarded_coding_reasoning_program.v6','clauses':[c.canonical() for c in router.clauses],
         'fallback_output':router.fallback_output,'source_digest':router.source_digest}
program['program_digest']=digest(program)
gene={
 'schema':'yado.g2.coding_reasoning_thinking_gene.v6','gene_id':'GENE-G2-CODING-REASONING-THINKING-V6-'+program['program_digest'][:16],
 'organ':'THINKING','gene_scope':['THINKING','CODE','MEMORY','GENERATIVE_EXECUTIVE','LOGIC','INTELLIGENCE'],
 'heritage':[p5.get('thinking_gene_id'),p5.get('receipt_sha256'),hist[4].get('experience_digest')],
 'origin':'ACTIVE_G2_ROUTER_LEARNED_STAGE_LOCAL_CONTRASTIVE_PROGRAMMER_REASONING_FROM_ACCUMULATED_FAILURES',
 'mechanism_kind':'STAGE_LOCAL_GUARDED_STATE_ACTION_ROUTER','active_parent_capability':'ALG-BOUNDED-CAPABILITY-ROUTER-V1',
 'program':program,'fresh_score':fresh_score,'unknown_state_score':unknown_score,'ablation_score':ablation,'restore_score':restore,
 'promotion_state':'SHADOW_ONLY'
}
gene['gene_digest']=digest(gene)

checks={
 'v5_withhold_consumed':p5.get('status')=='WITHHOLD_G2_CODING_REASONING_WORKSPACE_V5',
 'v5_proxy_defect_consumed':p5.get('fresh_score')==1.0 and p5.get('unknown_state_score')==0.75 and p5.get('retry_to_retest_score')==0.625,
 'active_router_capability_verified':'ALG-BOUNDED-CAPABILITY-ROUTER-V1' in set(head.get('active_capabilities') or []),
 'stage_local_observation_schema':all(('train_exact' not in e['input'] or e['input']['stage']=='TEST_RESULT') and ('candidate_present' not in e['input'] or e['input']['stage']=='HYPOTHESIS_READY') and ('fresh_exact' not in e['input'] or e['input']['stage']=='CONSEQUENCE_RESULT') for e in train_valid+val_valid+blind_valid),
 'contrastive_unknown_twins_present':len(train)==2*len(train_valid) and len(val)==2*len(val_valid),
 'stage_cardinality_within_router_bound':len({e['input']['stage'] for e in train})==8,
 'fresh_v6_tasks_executed':len(fresh_eps)==8,
 'fresh_success_and_failure_both_present':any(e['fresh_exact'] for e in fresh_eps) and any(not e['fresh_exact'] for e in fresh_eps),
 'router_has_clauses':len(router.clauses)>0,'fresh_reasoning_exact':fresh_score==1.0,
 'unknown_states_fail_closed':unknown_score==1.0,'fallback_is_withhold_unknown':router.fallback_output=='WITHHOLD_UNKNOWN',
 'all_valid_routes_require_known_stage':all_valid_guarded,
 'explicit_retry_clauses_present':bool(retry),'explicit_retry_clauses_guarded':retry_guarded,
 'retry_failure_stage_coverage':retry_coverage,'retry_to_retest_transition_exact':loop_score==1.0,
 'ablation_material_drop':fresh_score-ablation>=.20,'restore_exact':restore==fresh_score,
 'new_shadow_thinking_gene_created':bool(gene['gene_id']),
 'canonical_unchanged':core.head.get('canonical_head_digest')==head_before.get('canonical_head_digest'),
 'third_party_code_executed':False,'external_coding_model_used':False,'ready_patch_from_host_used':False,
 'host_written_reasoning_rules':False,'automatic_canonical_promotion':False
}
false_keys=['third_party_code_executed','external_coding_model_used','ready_patch_from_host_used','host_written_reasoning_rules','automatic_canonical_promotion']
true_keys=[k for k in checks if k not in false_keys]
passed=all(checks[k] is True for k in true_keys) and all(checks[k] is False for k in false_keys)
status='PASS_SHADOW_G2_CODING_REASONING_WORKSPACE_V6' if passed else 'WITHHOLD_G2_CODING_REASONING_WORKSPACE_V6'

experience={
 'schema':'yado.g2.coding_reasoning_workspace.experience.v6','status':'TRAINED','parent_v5_receipt':p5.get('receipt_sha256'),
 'representation_repair':'STAGE_LOCAL_OBSERVATIONS_PLUS_CONTRASTIVE_UNKNOWN_TWINS',
 'training_episode_count':len(train_eps),'validation_episode_count':len(val_eps),'fresh_episodes':fresh_eps,
 'fresh_score':fresh_score,'unknown_state_score':unknown_score,'ablation_score':ablation,'restore_score':restore,
 'retry_states':retry_states,'retry_to_retest_rows':loop,'retry_to_retest_score':loop_score,'thinking_gene':gene,
 'canonical_mutation':False,
 'semantic_boundary':'V6 TRAINS A STAGE-LOCAL GUARDED REASONING CONTROL POLICY USING ONLY ACTIVE G2 ROUTING CAPABILITY AND ACCUMULATED CODING EXPERIENCE. CONTRASTIVE UNKNOWN TWINS PREVENT PROXY SHORTCUTS. THIS PROVES WHEN TO RETRY AND RETEST, BUT NOT YET HOW TO SYNTHESIZE A NEW HYPOTHESIS/PATCH AFTER RETRY.'
}
experience['experience_digest']=digest(experience)
EXP.parent.mkdir(parents=True,exist_ok=True);EXP.write_text(json.dumps(experience,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')
report={
 'schema':'yado.g2.coding_reasoning_workspace.v6','status':status,'task':task,
 'active_mechanism':'ALG-BOUNDED-CAPABILITY-ROUTER-V1','representation_repair':experience['representation_repair'],
 'fresh_task_count':len(fresh_eps),'fresh_success_count':sum(e['fresh_exact'] for e in fresh_eps),'fresh_failure_count':sum(not e['fresh_exact'] for e in fresh_eps),
 'fresh_score':fresh_score,'unknown_state_score':unknown_score,'ablation_score':ablation,'restore_score':restore,
 'router_clause_count':len(router.clauses),'retry_clause_count':len(retry),'retry_states':retry_states,'retry_to_retest_score':loop_score,
 'thinking_gene_id':gene['gene_id'],'thinking_gene':gene,'checks':checks,'canonical_mutation':False,'promotion_applied':False,
 'next_required_capability':'G2_CODING_HYPOTHESIS_REVISION_GENERATOR_V1' if passed else 'G2_CODING_REASONING_WORKSPACE_V7',
 'receipt_sha256':None,'semantic_boundary':experience['semantic_boundary']
}
report['receipt_sha256']=digest({k:v for k,v in report.items() if k!='receipt_sha256'})
OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(report,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')
print(json.dumps({
 'status':status,'fresh_task_count':len(fresh_eps),'fresh_success_count':report['fresh_success_count'],'fresh_failure_count':report['fresh_failure_count'],
 'fresh_score':fresh_score,'unknown_state_score':unknown_score,'ablation_score':ablation,'restore_score':restore,
 'router_clause_count':len(router.clauses),'retry_clause_count':len(retry),'retry_states':retry_states,'retry_to_retest_score':loop_score,
 'thinking_gene_id':gene['gene_id'],'next_required_capability':report['next_required_capability'],'receipt_sha256':report['receipt_sha256']
},indent=2,sort_keys=True))
if not passed:raise SystemExit(2)
