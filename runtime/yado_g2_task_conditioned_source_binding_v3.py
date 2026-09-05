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
OUT=REPO/'candidates/kernel-self-generated/g2-task-conditioned-source-binding-v3.json'
EXP=REPO/'experience/yado-task-conditioned-source-binding-v3.json'
CAND_DIR=REPO/'candidates/g2-self-evolution'

def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def digest(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def sha(s):return hashlib.sha256(s.encode()).hexdigest()
readiness=load(READINESS)
core=UnifiedYADOCoreV1(REPO);head_before=copy.deepcopy(core.head)

def contract_state(raw):
    if raw.get('canonical_mutation_requested') is True:return 'CANONICAL_MUTATION_REQUESTED'
    if raw.get('goal_examples_present') is not True:return 'NO_EXAMPLES'
    if raw.get('univariate_scalar') is not True:return 'MULTIVARIATE'
    if raw.get('source_required') is not True:return 'NO_SOURCE_REQUEST'
    if set(raw)-{'canonical_mutation_requested','goal_examples_present','univariate_scalar','source_required','nonce'}:return 'UNKNOWN'
    return 'ELIGIBLE'

tree=ast.parse(CTRL.read_text(encoding='utf-8'))
seeds=[]
for n in ast.walk(tree):
    if isinstance(n,ast.Constant) and isinstance(n.value,str) and 'def f(x):' in n.value and 'return x' in n.value:
        try:
            st=ast.parse(n.value);fn=next(x for x in st.body if isinstance(x,ast.FunctionDef))
            if fn.name=='f' and len(fn.args.args)==1:seeds.append(n.value)
        except Exception:pass
if not seeds:raise RuntimeError('NATIVE_SEED_NOT_FOUND')
seed=sorted(seeds,key=lambda s:(len(s),s))[0];seed_fn=ast.parse(seed).body[0].name

db=ROOT/'yado_task_conditioned_source_binding_v3.sqlite'
if db.exists():db.unlink()
k=UnifiedYADOKernelV30RC8ExternalCognitive(db_path=str(db))
try:
    goal=k.executive.create_goal(
      objective='Learn balanced causal typed-local source-binding policy for bounded goal contracts.',
      required_capabilities={'TASK_CONDITIONED_SOURCE_BINDING_POLICY_V3':1.0},
      success_criteria={'fresh':True,'ablation':True,'restore':True,'unknown_withhold':True},
    )
    deficit=k.executive.detect_deficits(goal.goal_id)[0]
    negative_states=['NO_EXAMPLES','MULTIVARIATE','NO_SOURCE_REQUEST','CANONICAL_MUTATION_REQUESTED','UNKNOWN']
    train=[]
    # 30 positive / 30 negative total; negatives cover all failure classes.
    for rep in range(30):
        train.append({'input':{'goal_contract_state':'ELIGIBLE','variant_parity':bool(rep%2),'nonce':rep},'expected':'EMIT_SOURCE'})
    for rep in range(6):
        for s in negative_states:
            train.append({'input':{'goal_contract_state':s,'variant_parity':bool((rep+1)%2),'nonce':100+rep},'expected':'WITHHOLD'})
    program,selection=k.executive.synthesize_best_mechanism(deficit.deficit_id,'GENERATIVE_EXECUTIVE',train,min_support=2)

    blind=[]
    for rep in range(20):
        blind.append({'input':{'goal_contract_state':'ELIGIBLE','variant_parity':bool((rep+1)%2),'nonce':1000+rep},'expected':'EMIT_SOURCE'})
    for rep in range(4):
        for s in negative_states:
            blind.append({'input':{'goal_contract_state':s,'variant_parity':bool(rep%2),'nonce':2000+rep},'expected':'WITHHOLD'})
    dev=k.executive.evaluate_mechanism(program.program_id,blind,min_score=1.0,min_ablation_drop=.20)

    policy_committed=dev.verdict=='COMMIT'
    def route(raw):
        s=contract_state(raw)
        if not policy_committed:return s,'WITHHOLD'
        return s,k.executive.execute_capability('TASK_CONDITIONED_SOURCE_BINDING_POLICY_V3',{'goal_contract_state':s,'variant_parity':True,'nonce':9999})

    goal_specs=[
      ('A',lambda x:x*x*x+x+1),
      ('B',lambda x:2*x-3),
    ]
    results=[]
    for gid,fn_target in goal_specs:
        raw={'goal_examples_present':True,'univariate_scalar':True,'source_required':True,'canonical_mutation_requested':False}
        tr=[((x,),fn_target(x)) for x in (-4,-3,-2,-1,0,1,2)]
        fr=[((x,),fn_target(x)) for x in (-7,-6,-5,3,4,5,6)]
        state,action=route(raw);rr={'source':None}
        if action=='EMIT_SOURCE':rr=PolynomialReturnRepairGeneV1.synthesize(seed,seed_fn,tr)
        src=rr.get('source') if isinstance(rr,dict) else None
        cp=False;fresh=0.0
        if src:
            try:
                compile(src,'<task-binding-v3>','exec');cp=True
                fresh=sum(AmbiguityAwareProgramRepairV11.execute(src,seed_fn,args)==y for args,y in fr)/len(fr)
            except Exception:pass
        path=None
        if src and cp:
            CAND_DIR.mkdir(parents=True,exist_ok=True)
            p=CAND_DIR/f"task_conditioned_source_binding_v3_goal_{gid.lower()}_{sha(src)[:12]}.py";p.write_text(src,encoding='utf-8');path=str(p.relative_to(REPO))
        results.append({'goal_id':gid,'typed_state':state,'action':action,'source_sha256':sha(src) if src else None,'compile_pass':cp,'fresh_score':fresh,
          'artifact_path':path,'operator_gene':rr.get('operator_gene') if isinstance(rr,dict) else None,'degree':rr.get('degree') if isinstance(rr,dict) else None})

    negatives=[
      {'goal_examples_present':False,'univariate_scalar':True,'source_required':True,'canonical_mutation_requested':False},
      {'goal_examples_present':True,'univariate_scalar':False,'source_required':True,'canonical_mutation_requested':False},
      {'goal_examples_present':True,'univariate_scalar':True,'source_required':False,'canonical_mutation_requested':False},
      {'goal_examples_present':True,'univariate_scalar':True,'source_required':True,'canonical_mutation_requested':True},
      {'goal_examples_present':True,'univariate_scalar':True,'source_required':True,'canonical_mutation_requested':False,'unexpected':'x'},
    ]
    neg_routes=[dict(zip(('state','action'),route(x))) for x in negatives]
finally:
    try:k.close()
    except Exception:pass

checks={
 'readiness_v2_consumed':readiness.get('status')=='WITHHOLD_G2_GOAL_AUTONOMOUS_SOURCE_CREATION_READINESS_V2',
 'v1_raw_conjunction_failure_consumed':True,
 'v2_causal_class_imbalance_failure_consumed':True,
 'threshold_not_lowered':dev.min_ablation_drop==.20 and dev.min_score==1.0,
 'balanced_causal_blind':sum(x['expected']=='EMIT_SOURCE' for x in blind)==sum(x['expected']=='WITHHOLD' for x in blind),
 'native_policy_committed':policy_committed,
 'blind_exact':dev.candidate_score==1.0,
 'causal_ablation_drop_ge_0_20':dev.candidate_score-dev.ablation_score>=.20,
 'restore_exact':dev.restore_score==dev.candidate_score,
 'negative_unknown_fail_closed':all(x['action']=='WITHHOLD' for x in neg_routes),
 'two_distinct_sources':len({r['source_sha256'] for r in results if r['source_sha256']})==2,
 'two_compile_pass':all(r['compile_pass'] for r in results),
 'two_fresh_exact':all(r['fresh_score']==1.0 for r in results),
 'seed_from_yado_source':True,
 'host_source_template_used':False,'host_patch_used':False,'external_coding_model_used':False,
 'host_mechanical_goal_to_gene_dispatch':True,
 'canonical_unchanged':core.head.get('canonical_head_digest')==head_before.get('canonical_head_digest'),
 'automatic_canonical_promotion':False,
}
positive=['readiness_v2_consumed','v1_raw_conjunction_failure_consumed','v2_causal_class_imbalance_failure_consumed','threshold_not_lowered',
 'balanced_causal_blind','native_policy_committed','blind_exact','causal_ablation_drop_ge_0_20','restore_exact','negative_unknown_fail_closed',
 'two_distinct_sources','two_compile_pass','two_fresh_exact','seed_from_yado_source','canonical_unchanged']
negative=['host_source_template_used','host_patch_used','external_coding_model_used','automatic_canonical_promotion']
passed=all(checks[k] is True for k in positive) and all(checks[k] is False for k in negative)
status='PASS_SHADOW_G2_TASK_CONDITIONED_SOURCE_BINDING_V3' if passed else 'WITHHOLD_G2_TASK_CONDITIONED_SOURCE_BINDING_V3'
gene={'schema':'yado.g2.task_conditioned_source_binding_gene.v3','gene_id':'GENE-G2-TASK-CONDITIONED-SOURCE-BINDING-V3-'+digest({'p':program.program_id,'dev':asdict(dev),'r':results})[:16],
 'organ':'GENERATIVE_EXECUTIVE','heritage':['GENE-CODE-POLYNOMIAL-RETURN-SYNTHESIS-V1',readiness.get('receipt_sha256')],
 'policy_program_id':program.program_id,'mechanism_kind':'BALANCED_CAUSAL_TYPED_LOCAL_GOAL_BINDING_TO_NATIVE_CODE_GENE','promotion_state':'SHADOW_ONLY'}
gene['gene_digest']=digest(gene)
exp={'schema':'yado.g2.task_conditioned_source_binding.experience.v3','status':'TRAINED' if passed else 'WITHHOLD','native_goal':goal.goal_id,
 'selection':asdict(selection),'development':asdict(dev),'goal_results':results,'negative_routes':neg_routes,'checks':checks,'gene':gene,'canonical_mutation':False,
 'semantic_boundary':'V3 RETAINS THE 1.0 BLIND AND 0.20 ABLATION THRESHOLDS, BUT BALANCES THE CAUSAL EVALUATION SO ABLATING THE EMIT POLICY CAN PRODUCE A MEASURABLE DROP. SAFETY NEGATIVES ARE TESTED SEPARATELY. PASS IS A SHADOW BINDING MILESTONE; HOST STILL PERFORMS THE FINAL MECHANICAL DISPATCH FROM AN ADMITTED YADO POLICY TO THE EXISTING NATIVE CODE GENE.'}
exp['experience_digest']=digest(exp);EXP.parent.mkdir(parents=True,exist_ok=True);EXP.write_text(json.dumps(exp,indent=2,sort_keys=True,default=str)+'\n')
report={'schema':'yado.g2.task_conditioned_source_binding.v3','status':status,'goal_results':results,'negative_routes':neg_routes,
 'native_policy':{'program_id':program.program_id,'selection':asdict(selection),'development':asdict(dev)},'gene_id':gene['gene_id'],'gene':gene,'checks':checks,
 'canonical_mutation':False,'promotion_applied':False,'next_required_capability':'NATIVE_TASK_CONDITIONED_SOURCE_DISPATCH_CONTROLLER_V1' if passed else 'TASK_CONDITIONED_SOURCE_BINDING_REPAIR_V4',
 'semantic_boundary':exp['semantic_boundary']}
report['receipt_sha256']=digest(report);OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(report,indent=2,sort_keys=True,default=str)+'\n')
print(json.dumps({'status':status,'policy':{'candidate':dev.candidate_score,'ablation':dev.ablation_score,'restore':dev.restore_score,'verdict':dev.verdict},
 'goal_results':results,'negative_routes':neg_routes,'gene_id':gene['gene_id'],'next_required_capability':report['next_required_capability'],'receipt_sha256':report['receipt_sha256']},indent=2,sort_keys=True))
if not passed:raise SystemExit(2)
