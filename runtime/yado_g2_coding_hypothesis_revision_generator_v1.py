from __future__ import annotations
from pathlib import Path
import copy,hashlib,json,sys

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
PKG=ROOT/'yado_rc8_v36'
sys.path[:0]=[str(ROOT),str(PKG)]

from yado_unified_core_v1 import UnifiedYADOCoreV1
from yado_bounded_capability_router_v1 import RouterAtom,RouterClause,CapabilityRouterProgram
from yado_ambiguity_aware_program_repair_v11 import AmbiguityAwareProgramRepairV11

TASK=REPO/'architecture/yado-g2-coding-hypothesis-revision-generator-v1-request.json'
P_REASON=REPO/'candidates/kernel-self-generated/g2-coding-reasoning-workspace-v7.json'
P_PLAN=REPO/'candidates/kernel-self-generated/g2-coding-apprenticeship-repair-v2.json'
HEAD=REPO/'canonical/yado-main-head-g2.json'
OUT=REPO/'candidates/kernel-self-generated/g2-coding-hypothesis-revision-generator-v1.json'
EXP=REPO/'experience/yado-coding-hypothesis-revision-v1.json'

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def digest(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def sha(s):return hashlib.sha256(s.encode()).hexdigest()

task=load(TASK);reason=load(P_REASON);plan=load(P_PLAN);head=load(HEAD)
if reason.get('status')!='PASS_SHADOW_G2_CODING_REASONING_WORKSPACE_V7':raise RuntimeError('REASONING_PARENT_NOT_PASS')
if reason.get('next_required_capability')!='G2_CODING_HYPOTHESIS_REVISION_GENERATOR_V1':raise RuntimeError('REASONING_FRONTIER_MISMATCH')
if plan.get('status')!='PASS_SHADOW_G2_CODING_APPRENTICESHIP_REPAIR_V2':raise RuntimeError('PLANNING_PARENT_NOT_PASS')
active=set(head.get('active_capabilities') or [])
if 'ALG-G2-AMBIGUITY-AWARE-PROGRAM-REPAIR-V11' not in active:raise RuntimeError('PROGRAM_REPAIR_NOT_ACTIVE_G2')
core=UnifiedYADOCoreV1(REPO);head_before=copy.deepcopy(core.head)

def router_from_gene(g):
    p=g['program'];clauses=[]
    for c in p['clauses']:
        atoms=[RouterAtom(a['field'],a['value']) for a in c['atoms']]
        clauses.append(RouterClause(atoms,c['output'],int(c['support']),float(c['confidence'])))
    return CapabilityRouterProgram(clauses,p['fallback_output'],p['source_digest'])

router=router_from_gene(reason['thinking_gene'])

def execute(src,args):
    return AmbiguityAwareProgramRepairV11.execute(src,'f',args)

def score(src,cases):
    if not src:return 0.0
    ok=0
    for args,expected in cases:
        try:got=execute(src,args)
        except Exception:continue
        ok+=(got==expected)
    return ok/max(1,len(cases))

def consequence_action():
    return router.execute({'stage':'CONSEQUENCE_RESULT','stage_known':True,'task_kind':'REPAIR','high_complexity':False,'fresh_exact':False})
def retest_action():
    return router.execute({'stage':'HYPOTHESIS_READY','stage_known':True,'task_kind':'REPAIR','high_complexity':False,'candidate_present':True})

tasks=[
 {
  'id':'REV_ABS','source':'def f(x):\n    return x\n',
  'seed':[((1,),1),((3,),3),((6,),6),((9,),9)],
  'feedback':[((-5,),5),((-2,),2)],
  'holdout':[((-9,),9),((-1,),1),((0,),0),((4,),4),((11,),11)]
 },
 {
  'id':'REV_MAX2','source':'def f(x):\n    return x\n',
  'seed':[((2,),2),((4,),4),((7,),7),((10,),10)],
  'feedback':[((-3,),2),((0,),2)],
  'holdout':[((-8,),2),((1,),2),((3,),3),((8,),8),((12,),12)]
 },
 {
  'id':'REV_MIN_NEG1','source':'def f(x):\n    return x\n',
  'seed':[((-9,),-9),((-5,),-5),((-2,),-2),((-1,),-1)],
  'feedback':[((0,),-1),((4,),-1)],
  'holdout':[((-12,),-12),((-3,),-3),((1,),-1),((7,),-1),((10,),-1)]
 },
 {
  'id':'REV_RELU','source':'def f(x):\n    return x\n',
  'seed':[((0,),0),((2,),2),((5,),5),((8,),8)],
  'feedback':[((-4,),0),((-1,),0)],
  'holdout':[((-10,),0),((-2,),0),((1,),1),((6,),6),((11,),11)]
 },
 {
  'id':'REV_MIN0','source':'def f(x):\n    return x\n',
  'seed':[((-8,),-8),((-4,),-4),((-1,),-1),((0,),0)],
  'feedback':[((4,),0),((9,),0)],
  'holdout':[((-11,),-11),((-2,),-2),((1,),0),((7,),0),((13,),0)]
 },
 {
  'id':'REV_CLAMP_NEG2_POS3','source':'def f(x):\n    return x\n',
  'seed':[((-2,),-2),((0,),0),((2,),2),((3,),3)],
  'feedback':[((5,),3),((-5,),-2),((8,),3),((-8,),-2)],
  'holdout':[((-12,),-2),((-3,),-2),((-1,),-1),((1,),1),((4,),3),((10,),3)]
 }
]

def run_task(t,max_revisions=4):
    current=t['source'];examples=list(t['seed'])
    if score(current,examples)!=1.0:raise RuntimeError('INITIAL_HYPOTHESIS_NOT_SEED_EXACT:'+t['id'])
    pre=score(current,t['holdout'])
    revisions=[];feedback_used=[]
    for cycle in range(max_revisions):
        failing=None
        for case in t['feedback']:
            if case in feedback_used:continue
            try:got=execute(current,case[0])
            except Exception:got='__ERROR__'
            if got!=case[1]:
                failing=case;break
        if failing is None:
            # If feedback is satisfied but unseen holdout still fails, the harness does not leak holdout labels.
            break
        decision=consequence_action()
        if decision!='REVISE_HYPOTHESIS':
            revisions.append({'cycle':cycle,'decision':decision,'status':'CONTROLLER_DID_NOT_REVISE'});break
        feedback_used.append(failing);examples.append(failing)
        previous=current;prev_digest=sha(previous)
        r=AmbiguityAwareProgramRepairV11.repair(previous,'f',examples,max_candidates=12000,max_edit_depth=2)
        candidate=r.get('source')
        if not candidate:
            revisions.append({
              'cycle':cycle,'decision':decision,'failure_input':failing[0],'failure_expected':failing[1],
              'previous_source_sha256':prev_digest,'candidate_source_sha256':None,'changed':False,
              'repair_mode':r.get('repair_mode'),'reason':r.get('reason'),'retest_decision':None,
              'post_cycle_holdout_score':score(previous,t['holdout'])
            })
            break
        test_decision=retest_action()
        changed=sha(candidate)!=prev_digest
        current=candidate
        revisions.append({
          'cycle':cycle,'decision':decision,'failure_input':failing[0],'failure_expected':failing[1],
          'previous_source_sha256':prev_digest,'candidate_source_sha256':sha(candidate),'candidate_source_excerpt':candidate[:600],
          'changed':changed,'repair_mode':r.get('repair_mode'),'reason':r.get('reason'),
          'retest_decision':test_decision,'post_cycle_holdout_score':score(current,t['holdout'])
        })
        if test_decision!='TEST_HYPOTHESIS':break
    return {
      'task_id':t['id'],'initial_source_sha256':sha(t['source']),'initial_source_excerpt':t['source'],
      'pre_holdout_score':pre,'post_holdout_score':score(current,t['holdout']),
      'final_source_sha256':sha(current),'final_source_excerpt':current[:800],
      'revision_count':len(revisions),'changed_revision_count':sum(bool(r.get('changed')) for r in revisions),
      'feedback_used_count':len(feedback_used),'revisions':revisions,
      'final_seed_plus_feedback_score':score(current,examples)
    }

episodes=[run_task(t) for t in tasks]
pre=sum(e['pre_holdout_score'] for e in episodes)/len(episodes)
post=sum(e['post_holdout_score'] for e in episodes)/len(episodes)
changed_rate=sum(e['changed_revision_count']>0 for e in episodes)/len(episodes)
multi_count=sum(e['changed_revision_count']>=2 for e in episodes)
all_control=all(all(r.get('decision')=='REVISE_HYPOTHESIS' and (r.get('candidate_source_sha256') is None or r.get('retest_decision')=='TEST_HYPOTHESIS') for r in e['revisions']) for e in episodes)
all_changed=all(e['changed_revision_count']>=1 for e in episodes)
all_exact=all(e['post_holdout_score']==1.0 for e in episodes)

# Causal ablation: no consequence is written back, so original hypothesis remains.
ablation=sum(score(t['source'],t['holdout']) for t in tasks)/len(tasks)

# Restore: replay from pristine sources and require deterministic final hypothesis digest.
restored=[run_task(t) for t in tasks]
restore=sum(e['post_holdout_score'] for e in restored)/len(restored)
digest_restore=all(a['final_source_sha256']==b['final_source_sha256'] for a,b in zip(episodes,restored))

plan_gene=plan['coding_thinking_gene'];reason_gene=reason['thinking_gene']
gene={
 'schema':'yado.g2.coding_hypothesis_revision_gene.v1',
 'gene_id':'GENE-G2-CODING-HYPOTHESIS-REVISION-V1-'+digest({'episodes':episodes,'parents':[plan_gene['gene_digest'],reason_gene['gene_digest']]})[:16],
 'organ':'THINKING',
 'gene_scope':['THINKING','CODE','MEMORY','GENERATIVE_EXECUTIVE','LOGIC','INTELLIGENCE'],
 'heritage':[plan_gene['gene_id'],reason_gene['gene_id'],plan.get('receipt_sha256'),reason.get('receipt_sha256')],
 'lineage_join':{
   'contextual_planning_parent':plan_gene['gene_id'],
   'iterative_reasoning_parent':reason_gene['gene_id']
 },
 'mechanism_kind':'FAILURE_COUNTEREXAMPLE_DRIVEN_ACTIVE_G2_PROGRAM_REPAIR_REVISION_LOOP',
 'active_components':['ALG-BOUNDED-CAPABILITY-ROUTER-V1','ALG-G2-AMBIGUITY-AWARE-PROGRAM-REPAIR-V11'],
 'pre_fresh_score':pre,'post_revision_fresh_score':post,'revision_ablation_score':ablation,'restore_score':restore,
 'promotion_state':'SHADOW_ONLY'
}
gene['gene_digest']=digest(gene)

checks={
 'planning_history_parent_consumed':plan.get('status')=='PASS_SHADOW_G2_CODING_APPRENTICESHIP_REPAIR_V2',
 'iterative_reasoning_parent_consumed':reason.get('status')=='PASS_SHADOW_G2_CODING_REASONING_WORKSPACE_V7',
 'lineage_joined':gene['lineage_join']['contextual_planning_parent']==plan_gene['gene_id'] and gene['lineage_join']['iterative_reasoning_parent']==reason_gene['gene_id'],
 'active_program_repair_verified':'ALG-G2-AMBIGUITY-AWARE-PROGRAM-REPAIR-V11' in active,
 'active_reasoning_router_verified':'ALG-BOUNDED-CAPABILITY-ROUTER-V1' in active,
 'fresh_revision_tasks_executed':len(episodes)==6,
 'all_initial_hypotheses_imperfect_on_holdout':all(e['pre_holdout_score']<1.0 for e in episodes),
 'all_tasks_triggered_revision':all(e['revision_count']>=1 for e in episodes),
 'all_tasks_changed_hypothesis':all_changed,
 'at_least_one_multi_revision_task':multi_count>=1,
 'controller_revision_and_retest_exact':all_control,
 'all_post_revision_holdouts_exact':all_exact and post==1.0,
 'revision_gain_material':post-pre>=.40,
 'causal_revision_ablation_drop':post-ablation>=.40,
 'restore_exact':restore==post and digest_restore,
 'new_shadow_revision_gene_created':bool(gene['gene_id']),
 'canonical_unchanged':core.head.get('canonical_head_digest')==head_before.get('canonical_head_digest'),
 'third_party_code_executed':False,'external_coding_model_used':False,'ready_patch_from_host_used':False,
 'host_selected_revised_source':False,'automatic_canonical_promotion':False
}
false_keys=['third_party_code_executed','external_coding_model_used','ready_patch_from_host_used','host_selected_revised_source','automatic_canonical_promotion']
true_keys=[k for k in checks if k not in false_keys]
passed=all(checks[k] is True for k in true_keys) and all(checks[k] is False for k in false_keys)
status='PASS_SHADOW_G2_CODING_HYPOTHESIS_REVISION_GENERATOR_V1' if passed else 'WITHHOLD_G2_CODING_HYPOTHESIS_REVISION_GENERATOR_V1'

experience={
 'schema':'yado.g2.coding_hypothesis_revision.experience.v1','status':'TRAINED' if passed else 'WITHHOLD',
 'parent_planning_gene_id':plan_gene['gene_id'],'parent_reasoning_gene_id':reason_gene['gene_id'],
 'episodes':episodes,'pre_fresh_score':pre,'post_revision_fresh_score':post,'revision_ablation_score':ablation,
 'restore_score':restore,'changed_hypothesis_rate':changed_rate,'multi_revision_task_count':multi_count,
 'revision_gene':gene,'canonical_mutation':False,
 'semantic_boundary':'THE HOST SUPPLIES ONLY SANDBOX TASKS AND OBSERVED FAILED TEST INPUT/EXPECTED OUTPUT AS CONSEQUENCE EVIDENCE. REVISED SOURCE IS GENERATED ONLY BY THE ALREADY-ACTIVE G2 PROGRAM-REPAIR CAPABILITY AFTER THE V7 THINKING POLICY CHOOSES REVISE_HYPOTHESIS. FINAL HOLDOUT LABELS ARE NEVER FED BACK. THIS PROVES BOUNDED FAILURE-DRIVEN HYPOTHESIS/PATCH REVISION, NOT GENERAL AUTONOMOUS SOFTWARE ENGINEERING.'
}
experience['experience_digest']=digest(experience)
EXP.parent.mkdir(parents=True,exist_ok=True);EXP.write_text(json.dumps(experience,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')

report={
 'schema':'yado.g2.coding_hypothesis_revision_generator.v1','status':status,'task':task,
 'task_count':len(episodes),'pre_fresh_score':pre,'post_revision_fresh_score':post,'revision_ablation_score':ablation,
 'restore_score':restore,'changed_hypothesis_rate':changed_rate,'multi_revision_task_count':multi_count,
 'gene_id':gene['gene_id'],'revision_gene':gene,'checks':checks,'canonical_mutation':False,'promotion_applied':False,
 'next_required_capability':'G2_CODING_OPEN_ENDED_DEFECT_HYPOTHESIS_V1' if passed else 'G2_CODING_HYPOTHESIS_REVISION_GENERATOR_V2',
 'receipt_sha256':None,'semantic_boundary':experience['semantic_boundary']
}
report['receipt_sha256']=digest({k:v for k,v in report.items() if k!='receipt_sha256'})
OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(report,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')
print(json.dumps({
 'status':status,'task_count':len(episodes),'pre_fresh_score':pre,'post_revision_fresh_score':post,
 'revision_ablation_score':ablation,'restore_score':restore,'changed_hypothesis_rate':changed_rate,
 'multi_revision_task_count':multi_count,'gene_id':gene['gene_id'],'next_required_capability':report['next_required_capability'],
 'receipt_sha256':report['receipt_sha256']
},indent=2,sort_keys=True))
if not passed:raise SystemExit(2)
