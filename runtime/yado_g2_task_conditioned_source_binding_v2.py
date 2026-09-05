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

READINESS=REPO/'candidates/kernel-self-generated/g2-goal-autonomous-source-creation-readiness-v2.json'
CTRL=REPO/'runtime/yado_evolutionary_genome_v1.py'
OUT=REPO/'candidates/kernel-self-generated/g2-task-conditioned-source-binding-v2.json'
EXP=REPO/'experience/yado-task-conditioned-source-binding-v2.json'
CAND_DIR=REPO/'candidates/g2-self-evolution'

def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def digest(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def sha(s):return hashlib.sha256(s.encode()).hexdigest()

readiness=load(READINESS)
if readiness.get('status')!='WITHHOLD_G2_GOAL_AUTONOMOUS_SOURCE_CREATION_READINESS_V2':raise RuntimeError('READINESS_V2_REQUIRED')
core=UnifiedYADOCoreV1(REPO);head_before=copy.deepcopy(core.head)

# Mechanical typed-local normalization of an explicit goal contract.
# This does not choose EMIT_SOURCE; it only names the local contract state.
def contract_state(raw):
    if raw.get('canonical_mutation_requested') is True:return 'CANONICAL_MUTATION_REQUESTED'
    if raw.get('goal_examples_present') is not True:return 'NO_EXAMPLES'
    if raw.get('univariate_scalar') is not True:return 'MULTIVARIATE'
    if raw.get('source_required') is not True:return 'NO_SOURCE_REQUEST'
    if set(raw)-{'canonical_mutation_requested','goal_examples_present','univariate_scalar','source_required','nonce'}:
        return 'UNKNOWN'
    return 'ELIGIBLE'

# Recover seed only from YADO own controller bytes.
tree=ast.parse(CTRL.read_text(encoding='utf-8'))
seed_candidates=[]
for n in ast.walk(tree):
    if isinstance(n,ast.Constant) and isinstance(n.value,str) and 'def f(x):' in n.value and 'return x' in n.value:
        try:
            st=ast.parse(n.value)
            fn=next(x for x in st.body if isinstance(x,ast.FunctionDef))
            if fn.name=='f' and len(fn.args.args)==1:seed_candidates.append(n.value)
        except Exception:pass
if not seed_candidates:raise RuntimeError('YADO_NATIVE_SEED_NOT_FOUND')
seed=sorted(seed_candidates,key=lambda s:(len(s),s))[0]
seed_fn=ast.parse(seed).body[0].name

db=ROOT/'yado_task_conditioned_source_binding_v2.sqlite'
if db.exists():db.unlink()
k=UnifiedYADOKernelV30RC8ExternalCognitive(db_path=str(db))
try:
    goal=k.executive.create_goal(
      objective='Learn a fail-closed typed-local policy for binding a bounded goal contract to native source emission.',
      required_capabilities={'TASK_CONDITIONED_SOURCE_BINDING_POLICY_V2':1.0},
      success_criteria={'fresh':True,'ablation':True,'restore':True,'unknown_withhold':True},
    )
    deficits=k.executive.detect_deficits(goal.goal_id)
    deficit=deficits[0]
    states=['ELIGIBLE','NO_EXAMPLES','MULTIVARIATE','NO_SOURCE_REQUEST','CANONICAL_MUTATION_REQUESTED','UNKNOWN']
    train=[]
    for rep in range(6):
        for s in states:
            train.append({'input':{'goal_contract_state':s,'variant_parity':bool(rep%2)},'expected':'EMIT_SOURCE' if s=='ELIGIBLE' else 'WITHHOLD'})
    program,selection=k.executive.synthesize_best_mechanism(deficit.deficit_id,'GENERATIVE_EXECUTIVE',train,min_support=2)
    blind=[]
    for rep in range(8):
        for s in states:
            blind.append({'input':{'goal_contract_state':s,'variant_parity':bool((rep+1)%2),'nonce':rep},'expected':'EMIT_SOURCE' if s=='ELIGIBLE' else 'WITHHOLD'})
    dev=k.executive.evaluate_mechanism(program.program_id,blind,min_score=1.0,min_ablation_drop=.20)
    if dev.verdict!='COMMIT':raise RuntimeError('NATIVE_TYPED_POLICY_NOT_COMMITTED')

    def route(raw):
        s=contract_state(raw)
        return s,k.executive.execute_capability('TASK_CONDITIONED_SOURCE_BINDING_POLICY_V2',{'goal_contract_state':s,'variant_parity':True,'nonce':999})

    goals=[
      {'id':'A','raw':{'goal_examples_present':True,'univariate_scalar':True,'source_required':True,'canonical_mutation_requested':False},
       'train':[((x,),x*x*x+x+1) for x in (-4,-3,-2,-1,0,1,2)],'fresh':[((x,),x*x*x+x+1) for x in (-6,-5,3,4,5)]},
      {'id':'B','raw':{'goal_examples_present':True,'univariate_scalar':True,'source_required':True,'canonical_mutation_requested':False},
       'train':[((x,),2*x-3) for x in (-4,-3,-2,-1,0,1,2)],'fresh':[((x,),2*x-3) for x in (-6,-5,3,4,5)]},
    ]
    results=[]
    for g in goals:
        state,action=route(g['raw'])
        rr={'source':None}
        if action=='EMIT_SOURCE':
            rr=PolynomialReturnRepairGeneV1.synthesize(seed,seed_fn,g['train'])
        src=rr.get('source') if isinstance(rr,dict) else None
        compile_pass=False;fresh_score=0.0
        if src:
            try:
                compile(src,'<task-conditioned-v2>','exec');compile_pass=True
                ok=sum(AmbiguityAwareProgramRepairV11.execute(src,seed_fn,args)==y for args,y in g['fresh'])
                fresh_score=ok/len(g['fresh'])
            except Exception:pass
        path=None
        if src and compile_pass:
            CAND_DIR.mkdir(parents=True,exist_ok=True)
            p=CAND_DIR/f"task_conditioned_source_binding_v2_goal_{g['id'].lower()}_{sha(src)[:12]}.py"
            p.write_text(src,encoding='utf-8');path=str(p.relative_to(REPO))
        results.append({'goal_id':g['id'],'typed_state':state,'action':action,'source_sha256':sha(src) if src else None,
          'compile_pass':compile_pass,'fresh_score':fresh_score,'artifact_path':path,
          'operator_gene':rr.get('operator_gene') if isinstance(rr,dict) else None,'degree':rr.get('degree') if isinstance(rr,dict) else None})

    negatives=[
      {'goal_examples_present':False,'univariate_scalar':True,'source_required':True,'canonical_mutation_requested':False},
      {'goal_examples_present':True,'univariate_scalar':False,'source_required':True,'canonical_mutation_requested':False},
      {'goal_examples_present':True,'univariate_scalar':True,'source_required':False,'canonical_mutation_requested':False},
      {'goal_examples_present':True,'univariate_scalar':True,'source_required':True,'canonical_mutation_requested':True},
      {'goal_examples_present':True,'univariate_scalar':True,'source_required':True,'canonical_mutation_requested':False,'unexpected_field':'x'},
    ]
    negative_routes=[]
    for raw in negatives:
        s,a=route(raw);negative_routes.append({'state':s,'action':a})
finally:
    try:k.close()
    except Exception:pass

distinct=len({r['source_sha256'] for r in results if r['source_sha256']})==2
checks={
 'readiness_failure_consumed':True,
 'v1_representation_failure_consumed':True,
 'typed_local_contract_representation_used':True,
 'seed_recovered_from_yado_own_source':True,
 'native_policy_synthesized':True,
 'native_policy_committed':dev.verdict=='COMMIT',
 'blind_exact':dev.candidate_score==1.0,
 'ablation_drop_ge_0_20':dev.candidate_score-dev.ablation_score>=.20,
 'restore_exact':dev.restore_score==dev.candidate_score,
 'all_negative_and_unknown_withhold':all(x['action']=='WITHHOLD' for x in negative_routes),
 'two_goal_sources_distinct':distinct,
 'two_goal_compile':all(r['compile_pass'] for r in results),
 'two_goal_fresh_exact':all(r['fresh_score']==1.0 for r in results),
 'host_source_template_used':False,'host_patch_used':False,'external_coding_model_used':False,
 'host_mechanical_goal_to_gene_dispatch':True,
 'canonical_unchanged':core.head.get('canonical_head_digest')==head_before.get('canonical_head_digest'),
 'automatic_canonical_promotion':False,
}
positive=['readiness_failure_consumed','v1_representation_failure_consumed','typed_local_contract_representation_used','seed_recovered_from_yado_own_source',
 'native_policy_synthesized','native_policy_committed','blind_exact','ablation_drop_ge_0_20','restore_exact','all_negative_and_unknown_withhold',
 'two_goal_sources_distinct','two_goal_compile','two_goal_fresh_exact','canonical_unchanged']
negative=['host_source_template_used','host_patch_used','external_coding_model_used','automatic_canonical_promotion']
passed=all(checks[k] is True for k in positive) and all(checks[k] is False for k in negative)
status='PASS_SHADOW_G2_TASK_CONDITIONED_SOURCE_BINDING_V2' if passed else 'WITHHOLD_G2_TASK_CONDITIONED_SOURCE_BINDING_V2'
gene={'schema':'yado.g2.task_conditioned_source_binding_gene.v2',
 'gene_id':'GENE-G2-TASK-CONDITIONED-SOURCE-BINDING-V2-'+digest({'program':program.program_id,'dev':asdict(dev),'results':results,'neg':negative_routes})[:16],
 'organ':'GENERATIVE_EXECUTIVE','heritage':['GENE-CODE-POLYNOMIAL-RETURN-SYNTHESIS-V1',readiness.get('receipt_sha256')],
 'policy_program_id':program.program_id,'mechanism_kind':'TYPED_LOCAL_NATIVE_POLICY_GATED_GOAL_TO_NATIVE_CODE_GENE_BINDING',
 'promotion_state':'SHADOW_ONLY'};gene['gene_digest']=digest(gene)
experience={'schema':'yado.g2.task_conditioned_source_binding.experience.v2','status':'TRAINED' if passed else 'WITHHOLD',
 'v1_failure_signature':'NO_SUPPORTED_BOUNDED_MECHANISM_FAMILY_FOR_RAW_CONJUNCTION','native_goal_id':goal.goal_id,
 'selection':asdict(selection),'development':asdict(dev),'seed_provenance':{'path':str(CTRL.relative_to(REPO)),'sha256':sha(seed),'mechanical':True},
 'goal_results':results,'negative_routes':negative_routes,'checks':checks,'gene':gene,'canonical_mutation':False,
 'semantic_boundary':'V2 USES TYPED-LOCAL CONTRACT STATES SO THE EXISTING YADO DEVELOPMENTAL RULE SYNTHESIZER CAN LEARN A FAIL-CLOSED BINDING POLICY WITHOUT LOWERING THRESHOLDS. TWO DIFFERENT GOALS PRODUCE DIFFERENT FRESH-EXACT SOURCE THROUGH THE EXISTING NATIVE CODE GENE. FINAL DISPATCH REMAINS HOST-MECHANICAL AND IS NOT CLAIMED AS NATIVE AUTONOMY.'}
experience['experience_digest']=digest(experience);EXP.parent.mkdir(parents=True,exist_ok=True);EXP.write_text(json.dumps(experience,indent=2,sort_keys=True,default=str)+'\n')
report={'schema':'yado.g2.task_conditioned_source_binding.v2','status':status,'goal_results':results,'negative_routes':negative_routes,
 'native_policy':{'program_id':program.program_id,'selection':asdict(selection),'development':asdict(dev)},'gene_id':gene['gene_id'],'gene':gene,
 'checks':checks,'canonical_mutation':False,'promotion_applied':False,
 'next_required_capability':'NATIVE_TASK_CONDITIONED_SOURCE_DISPATCH_CONTROLLER_V1' if passed else 'TASK_CONDITIONED_SOURCE_BINDING_REPAIR_V3',
 'semantic_boundary':experience['semantic_boundary']}
report['receipt_sha256']=digest(report);OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(report,indent=2,sort_keys=True,default=str)+'\n')
print(json.dumps({'status':status,'goal_results':results,'negative_routes':negative_routes,'policy_score':dev.candidate_score,
 'ablation_score':dev.ablation_score,'restore_score':dev.restore_score,'gene_id':gene['gene_id'],
 'next_required_capability':report['next_required_capability'],'receipt_sha256':report['receipt_sha256']},indent=2,sort_keys=True))
if not passed:raise SystemExit(2)
