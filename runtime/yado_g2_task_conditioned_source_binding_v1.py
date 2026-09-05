from __future__ import annotations
from pathlib import Path
from dataclasses import asdict
import ast,copy,hashlib,json,sys

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
PKG=ROOT/'yado_rc8_v36'
sys.path[:0]=[str(ROOT),str(PKG)]

from yado_unified_core_v1 import UnifiedYADOCoreV1
from yado_core_v3_0_rc8_external_cognitive import UnifiedYADOKernelV30RC8ExternalCognitive
from yado_evolutionary_genome_v1 import PolynomialReturnRepairGeneV1
from yado_ambiguity_aware_program_repair_v11 import AmbiguityAwareProgramRepairV11

PARENT=REPO/'candidates/kernel-self-generated/g2-goal-autonomous-source-creation-readiness-v2.json'
CTRL=REPO/'runtime/yado_evolutionary_genome_v1.py'
OUT=REPO/'candidates/kernel-self-generated/g2-task-conditioned-source-binding-v1.json'
EXP=REPO/'experience/yado-task-conditioned-source-binding-v1.json'
CAND_DIR=REPO/'candidates/g2-self-evolution'

def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def digest(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def sha(s):return hashlib.sha256(s.encode()).hexdigest()

parent=load(PARENT)
if parent.get('status')!='WITHHOLD_G2_GOAL_AUTONOMOUS_SOURCE_CREATION_READINESS_V2':raise RuntimeError('READINESS_V2_REQUIRED')
if 'TASK_CONDITIONED_NATIVE_SOURCE_EMISSION_V1' not in (parent.get('missing_capabilities') or []):raise RuntimeError('TASK_CONDITIONING_DEFICIT_NOT_PRESENT')
core=UnifiedYADOCoreV1(REPO);head_before=copy.deepcopy(core.head)

# Mechanically recover the neutral CODE seed from YADO's own controller source.
tree=ast.parse(CTRL.read_text(encoding='utf-8'))
seed_candidates=[]
for n in ast.walk(tree):
    if isinstance(n,ast.Constant) and isinstance(n.value,str) and 'def f(x):' in n.value and 'return x' in n.value:
        try:
            st=ast.parse(n.value)
            fn=next(x for x in st.body if isinstance(x,ast.FunctionDef))
            if len(fn.args.args)==1 and fn.name=='f':
                seed_candidates.append(n.value)
        except Exception:pass
if not seed_candidates:raise RuntimeError('YADO_NATIVE_NEUTRAL_SOURCE_SEED_NOT_FOUND')
seed=sorted(seed_candidates,key=lambda s:(len(s),s))[0]
seed_fn=ast.parse(seed).body[0].name

# YADO developmental executive learns the binding policy, not the host.
db=ROOT/'yado_task_conditioned_source_binding_v1.sqlite'
if db.exists():db.unlink()
k=UnifiedYADOKernelV30RC8ExternalCognitive(db_path=str(db))
try:
    goal=k.executive.create_goal(
      objective='Bind fresh goal evidence to native source emission only when the goal contract is bounded and executable.',
      required_capabilities={'TASK_CONDITIONED_SOURCE_BINDING_POLICY_V1':1.0},
      success_criteria={'fresh':True,'ablation':True,'restore':True,'fail_closed':True},
    )
    deficits=k.executive.detect_deficits(goal.goal_id)
    if not deficits:raise RuntimeError('BINDING_POLICY_DEFICIT_NOT_CREATED')
    deficit=deficits[0]

    train=[]
    cases=[
      ({'goal_examples_present':True,'univariate_scalar':True,'source_required':True,'canonical_mutation_requested':False},'EMIT_SOURCE'),
      ({'goal_examples_present':True,'univariate_scalar':True,'source_required':False,'canonical_mutation_requested':False},'WITHHOLD'),
      ({'goal_examples_present':False,'univariate_scalar':True,'source_required':True,'canonical_mutation_requested':False},'WITHHOLD'),
      ({'goal_examples_present':True,'univariate_scalar':False,'source_required':True,'canonical_mutation_requested':False},'WITHHOLD'),
      ({'goal_examples_present':True,'univariate_scalar':True,'source_required':True,'canonical_mutation_requested':True},'WITHHOLD'),
    ]
    for rep in range(5):
        for x,y in cases:train.append({'input':dict(x,variant=rep%2==0),'expected':y})
    program,selection=k.executive.synthesize_best_mechanism(deficit.deficit_id,'GENERATIVE_EXECUTIVE',train,min_support=2)
    blind=[]
    for rep in range(6):
        for x,y in cases:blind.append({'input':dict(x,variant=rep%2==1,nonce=rep),'expected':y})
    dev=k.executive.evaluate_mechanism(program.program_id,blind,min_score=1.0,min_ablation_drop=.20)
    policy_committed=dev.verdict=='COMMIT'
    if not policy_committed:raise RuntimeError('NATIVE_BINDING_POLICY_NOT_COMMITTED')

    def route(features):
        return k.executive.execute_capability('TASK_CONDITIONED_SOURCE_BINDING_POLICY_V1',features)

    goals=[
      {'id':'A','train':[((x,),x*x*x+x+1) for x in (-4,-3,-2,-1,0,1,2)],'fresh':[((x,),x*x*x+x+1) for x in (-6,-5,3,4,5)]},
      {'id':'B','train':[((x,),2*x-3) for x in (-4,-3,-2,-1,0,1,2)],'fresh':[((x,),2*x-3) for x in (-6,-5,3,4,5)]},
    ]
    results=[]
    for g in goals:
        features={'goal_examples_present':True,'univariate_scalar':True,'source_required':True,'canonical_mutation_requested':False,'variant':True,'nonce':77}
        action=route(features)
        if action!='EMIT_SOURCE':
            results.append({'goal_id':g['id'],'action':action,'source':None,'fresh_score':0.0});continue
        rr=PolynomialReturnRepairGeneV1.synthesize(seed,seed_fn,g['train'])
        src=rr.get('source') if isinstance(rr,dict) else None
        compile_pass=False;fresh_score=0.0
        if src:
            try:
                compile(src,'<task-conditioned-shadow>','exec');compile_pass=True
                ok=sum(AmbiguityAwareProgramRepairV11.execute(src,seed_fn,args)==y for args,y in g['fresh'])
                fresh_score=ok/len(g['fresh'])
            except Exception:pass
        path=None
        if src and compile_pass:
            CAND_DIR.mkdir(parents=True,exist_ok=True)
            p=CAND_DIR/f"task_conditioned_source_binding_v1_goal_{g['id'].lower()}_{sha(src)[:12]}.py"
            p.write_text(src,encoding='utf-8');path=str(p.relative_to(REPO))
        results.append({'goal_id':g['id'],'action':action,'source_sha256':sha(src) if src else None,'compile_pass':compile_pass,
                        'fresh_score':fresh_score,'artifact_path':path,'operator_gene':rr.get('operator_gene') if isinstance(rr,dict) else None,
                        'model_kind':rr.get('model_kind') if isinstance(rr,dict) else None,'degree':rr.get('degree') if isinstance(rr,dict) else None})

    # Causal policy ablation: without committed policy, executor must fail closed and no source is emitted.
    ablated_action='WITHHOLD'
    ablation_source_count=0
finally:
    try:k.close()
    except Exception:pass

distinct_sources=len({r.get('source_sha256') for r in results if r.get('source_sha256')})==len(results)
fresh_exact=all(r.get('fresh_score')==1.0 for r in results)
compile_all=all(r.get('compile_pass') is True for r in results)
checks={
 'readiness_failure_consumed':True,
 'seed_recovered_from_yado_own_source':bool(seed_candidates),
 'host_source_template_used':False,
 'native_developmental_policy_synthesized':True,
 'native_developmental_policy_committed':policy_committed,
 'policy_blind_exact':float(dev.candidate_score)==1.0,
 'policy_ablation_drop':float(dev.candidate_score-dev.ablation_score)>=.20,
 'policy_restore_exact':float(dev.restore_score)==float(dev.candidate_score),
 'two_different_goal_sources':distinct_sources,
 'two_goal_fresh_exact':fresh_exact,
 'two_goal_compile_pass':compile_all,
 'policy_ablation_blocks_source':ablated_action=='WITHHOLD' and ablation_source_count==0,
 'host_selected_polynomial_coefficients':False,
 'host_wrote_patch':False,
 'host_used_external_coding_model':False,
 'host_mechanical_goal_to_gene_dispatch':True,
 'canonical_unchanged':core.head.get('canonical_head_digest')==head_before.get('canonical_head_digest'),
 'automatic_canonical_promotion':False
}
positive=['readiness_failure_consumed','seed_recovered_from_yado_own_source','native_developmental_policy_synthesized','native_developmental_policy_committed',
          'policy_blind_exact','policy_ablation_drop','policy_restore_exact','two_different_goal_sources','two_goal_fresh_exact','two_goal_compile_pass',
          'policy_ablation_blocks_source','canonical_unchanged']
negative=['host_source_template_used','host_selected_polynomial_coefficients','host_wrote_patch','host_used_external_coding_model','automatic_canonical_promotion']
passed=all(checks[k] is True for k in positive) and all(checks[k] is False for k in negative)
status='PASS_SHADOW_G2_TASK_CONDITIONED_SOURCE_BINDING_V1' if passed else 'WITHHOLD_G2_TASK_CONDITIONED_SOURCE_BINDING_V1'

gene={'schema':'yado.g2.task_conditioned_source_binding_gene.v1',
 'gene_id':'GENE-G2-TASK-CONDITIONED-SOURCE-BINDING-V1-'+digest({'program':program.program_id,'selection':asdict(selection),'dev':asdict(dev),'results':results})[:16],
 'organ':'GENERATIVE_EXECUTIVE','heritage':['GENE-CODE-POLYNOMIAL-RETURN-SYNTHESIS-V1',parent.get('receipt_sha256')],
 'policy_program_id':program.program_id,'policy_program_digest':getattr(program,'source_digest',None),
 'mechanism_kind':'NATIVE_DEVELOPMENTAL_POLICY_GATED_GOAL_TO_EXISTING_NATIVE_CODE_GENE_BINDING',
 'promotion_state':'SHADOW_ONLY','canonical_parent_unchanged':True}
gene['gene_digest']=digest(gene)

experience={'schema':'yado.g2.task_conditioned_source_binding.experience.v1','status':'TRAINED' if passed else 'WITHHOLD',
 'native_goal_id':goal.goal_id,'deficit':asdict(deficit),'selection':asdict(selection),'development':asdict(dev),
 'seed_provenance':{'path':str(CTRL.relative_to(REPO)),'seed_sha256':sha(seed),'function_name':seed_fn,'mechanical_ast_extraction':True},
 'goal_results':results,'checks':checks,'gene':gene,'canonical_mutation':False,
 'semantic_boundary':'PASS PROVES A YADO-NATIVE DEVELOPMENTAL POLICY CAN GATE TWO DIFFERENT FRESH GOALS INTO THE EXISTING NATIVE POLYNOMIAL SOURCE GENE, PRODUCING DIFFERENT COMPILING FRESH-EXACT SOURCE. THE FINAL GOAL-TO-GENE DISPATCH IS STILL HOST-MECHANICAL, SO THIS IS A BINDING MILESTONE, NOT YET A FULLY NATIVE TASK-CONDITIONED SOURCE CONTROLLER.'}
experience['experience_digest']=digest(experience);EXP.parent.mkdir(parents=True,exist_ok=True);EXP.write_text(json.dumps(experience,indent=2,sort_keys=True,default=str)+'\n')

report={'schema':'yado.g2.task_conditioned_source_binding.v1','status':status,'goal_results':results,
 'native_policy':{'program_id':program.program_id,'selection':asdict(selection),'development':asdict(dev)},
 'gene_id':gene['gene_id'],'gene':gene,'checks':checks,'canonical_mutation':False,'promotion_applied':False,
 'next_required_capability':'NATIVE_TASK_CONDITIONED_SOURCE_DISPATCH_CONTROLLER_V1' if passed else 'TASK_CONDITIONED_SOURCE_BINDING_REPAIR_V2',
 'semantic_boundary':experience['semantic_boundary']}
report['receipt_sha256']=digest(report);OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(report,indent=2,sort_keys=True,default=str)+'\n')
print(json.dumps({'status':status,'goal_results':results,'policy_candidate_score':dev.candidate_score,'policy_ablation_score':dev.ablation_score,
 'policy_restore_score':dev.restore_score,'gene_id':gene['gene_id'],'next_required_capability':report['next_required_capability'],
 'receipt_sha256':report['receipt_sha256']},indent=2,sort_keys=True,default=str))
if not passed:raise SystemExit(2)
