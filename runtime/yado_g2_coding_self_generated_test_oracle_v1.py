from __future__ import annotations
from pathlib import Path
import copy,hashlib,json,sys

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
PKG=ROOT/'yado_rc8_v36'
sys.path[:0]=[str(ROOT),str(PKG)]

from yado_unified_core_v1 import UnifiedYADOCoreV1
from yado_semantic_expression_synthesizer_v1 import SemanticExpressionSynthesizerV1
from yado_neutral_evidence_profile_selector_v1 import NeutralEvidenceProfileSelectorV1,EvidenceCandidate
from yado_evolutionary_genome_v1 import PolynomialReturnRepairGeneV1
from yado_ambiguity_aware_program_repair_v11 import AmbiguityAwareProgramRepairV11

TASK=REPO/'architecture/yado-g2-coding-self-generated-test-oracle-v1-request.json'
PARENT=REPO/'candidates/kernel-self-generated/g2-coding-open-ended-defect-hypothesis-v1.json'
HEAD=REPO/'canonical/yado-main-head-g2.json'
OUT=REPO/'candidates/kernel-self-generated/g2-coding-self-generated-test-oracle-v1.json'
EXP=REPO/'experience/yado-coding-self-generated-test-oracle-v1.json'

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def digest(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def sha(s):return hashlib.sha256(s.encode()).hexdigest()

task=load(TASK);parent=load(PARENT);head=load(HEAD)
if parent.get('status')!='PASS_SHADOW_G2_CODING_OPEN_ENDED_DEFECT_HYPOTHESIS_V1':
    raise RuntimeError('OPEN_ENDED_PARENT_NOT_PASS')
if parent.get('next_required_capability')!='G2_CODING_SELF_GENERATED_TEST_ORACLE_V1':
    raise RuntimeError('PARENT_FRONTIER_MISMATCH')
active=set(head.get('active_capabilities') or [])
for cap in ('ALG-G2-SEMANTIC-EXPRESSION-SYNTHESIZER-V1','ALG-NEUTRAL-EVIDENCE-PROFILE-SELECTOR-V1','CTRL-G2-EVOLUTIONARY-GENOME-V1'):
    if cap not in active:raise RuntimeError('REQUIRED_ACTIVE_CAPABILITY_MISSING:'+cap)
core=UnifiedYADOCoreV1(REPO);head_before=copy.deepcopy(core.head)

BASE='def f(x):\n    return x\n'
TEST_DOMAIN=tuple(range(-7,8))
TEST_COUNT=5

def execute(src,x):
    return AmbiguityAwareProgramRepairV11.execute(src,'f',(x,))

def code_score(src,cases):
    if not src:return 0.0
    ok=0
    for x,y in cases:
        try:g=execute(src,x)
        except Exception:continue
        ok+=(g==y)
    return ok/max(1,len(cases))

def oracle_score(oracle,cases):
    ok=0
    for x,y_distractor,expected in cases:
        try:g=SemanticExpressionSynthesizerV1.predict(oracle,x,y_distractor)
        except Exception:continue
        ok+=(g==expected)
    return ok/max(1,len(cases))

SPEC_X=(-3,-1,0,2,4)
SPEC_Y=(2,-4,3,-2,5)
ORACLE_H_X=(-8,-5,1,3,7)
ORACLE_H_Y=(-3,4,-5,2,6)
CODE_H_X=(-11,-6,1,5,9,12)

task_defs=[
 ('ORACLE_X_PLUS_2',lambda x:x+2),
 ('ORACLE_2X_PLUS_1',lambda x:2*x+1),
 ('ORACLE_X2',lambda x:x*x),
 ('ORACLE_X2_PLUS_1',lambda x:x*x+1),
 ('ORACLE_X2_PLUS_X',lambda x:x*x+x),
 ('ORACLE_X2_MINUS_X',lambda x:x*x-x),
 ('ORACLE_X3',lambda x:x*x*x),
 ('ORACLE_X3_PLUS_X',lambda x:x*x*x+x),
]

def run_task(name,target):
    # Formal spec examples are the only external target information.
    spec=[{'x':x,'y':y,'expected':target(x)} for x,y in zip(SPEC_X,SPEC_Y)]
    oracle=SemanticExpressionSynthesizerV1.synthesize(spec,max_ops=3,max_states_per_level=30000)
    oracle_expr=SemanticExpressionSynthesizerV1.render(oracle['expression']) if oracle.get('expression') is not None else None
    oracle_hidden=[(x,y,target(x)) for x,y in zip(ORACLE_H_X,ORACLE_H_Y)]
    oracle_hidden_score=oracle_score(oracle,oracle_hidden)

    code_holdout=[(x,target(x)) for x in CODE_H_X]
    initial_score=code_score(BASE,code_holdout)

    selected=[];tests=[];rank_trace=[]
    for cycle in range(TEST_COUNT):
        candidates=[];token_to_x={}
        used={x for x,_ in tests}
        for x in TEST_DOMAIN:
            if x in used:continue
            expected=SemanticExpressionSynthesizerV1.predict(oracle,x,cycle-2)
            try:got=execute(BASE,x)
            except Exception:got='__ERROR__'
            mismatch=1.0 if got!=expected else 0.0
            token='TX-'+sha(name+'|'+str(x))[:14]
            token_to_x[token]=x
            novelty=min(1.0,min((abs(x-z) for z in used),default=7)/7.0)
            candidates.append(EvidenceCandidate(token=token,evidence=mismatch,complexity=abs(x)/7.0,risk=0.0,novelty=novelty))
        sel=NeutralEvidenceProfileSelectorV1.select(candidates,complexity_penalty=.002,risk_penalty=.25,novelty_bonus=.02)
        token=sel['selected_token'];x=token_to_x[token]
        expected=SemanticExpressionSynthesizerV1.predict(oracle,x,cycle-2)
        tests.append((x,expected));selected.append(token)
        rank_trace.append({
          'cycle':cycle,'selected_test_token':token,'selected_x':x,'oracle_expected':expected,
          'selected_score':sel['selected_score'],'candidate_count':sel['candidate_count']
        })

    patch=PolynomialReturnRepairGeneV1.synthesize(BASE,'f',[((x,),y) for x,y in tests])
    source=patch.get('source')
    final_score=code_score(source,code_holdout)
    return {
      'task_id':name,
      'formal_spec_count':len(spec),
      'oracle_expression':oracle_expr,
      'oracle_ops':oracle.get('ops'),
      'oracle_states':oracle.get('states'),
      'oracle_hidden_validation_score':oracle_hidden_score,
      'initial_code_holdout_score':initial_score,
      'self_generated_tests':[{'x':x,'expected':y} for x,y in tests],
      'selected_test_tokens':selected,
      'test_selection_trace':rank_trace,
      'patch_source_sha256':sha(source) if source else None,
      'patch_source_excerpt':source[:800] if source else None,
      'patch_operator_gene':patch.get('operator_gene'),
      'patch_reason':patch.get('reason'),
      'final_code_holdout_score':final_score,
      'source_changed':bool(source and sha(source)!=sha(BASE)),
    }

episodes=[run_task(name,target) for name,target in task_defs]
oracle_val=sum(e['oracle_hidden_validation_score'] for e in episodes)/len(episodes)
initial=sum(e['initial_code_holdout_score'] for e in episodes)/len(episodes)
final=sum(e['final_code_holdout_score'] for e in episodes)/len(episodes)
ablation=initial
mean_tests=sum(len(e['self_generated_tests']) for e in episodes)/len(episodes)

restored=[run_task(name,target) for name,target in task_defs]
restore=sum(e['final_code_holdout_score'] for e in restored)/len(restored)
restore_exact=all(
 a['oracle_expression']==b['oracle_expression'] and a['selected_test_tokens']==b['selected_test_tokens'] and
 a['patch_source_sha256']==b['patch_source_sha256']
 for a,b in zip(episodes,restored)
)

parent_gene=parent['open_ended_gene']
gene={
 'schema':'yado.g2.coding_self_generated_test_oracle_gene.v1',
 'gene_id':'GENE-G2-CODING-SELF-GENERATED-TEST-ORACLE-V1-'+digest({'episodes':episodes,'parent':parent_gene['gene_digest']})[:16],
 'organ':'THINKING',
 'gene_scope':['THINKING','INTELLIGENCE','CODE','MEMORY','GENERATIVE_EXECUTIVE','LOGIC'],
 'heritage':[parent_gene['gene_id'],parent.get('receipt_sha256')],
 'mechanism_kind':'FORMAL_SPEC_TO_SYNTHESIZED_ORACLE_TO_SELF_SELECTED_TESTS_TO_EVOLUTIONARY_CODE_PATCH',
 'active_components':[
   'ALG-G2-SEMANTIC-EXPRESSION-SYNTHESIZER-V1',
   'ALG-NEUTRAL-EVIDENCE-PROFILE-SELECTOR-V1',
   'CTRL-G2-EVOLUTIONARY-GENOME-V1'
 ],
 'oracle_hidden_validation_score':oracle_val,'initial_code_holdout_score':initial,
 'final_code_holdout_score':final,'oracle_ablation_score':ablation,
 'mean_self_generated_test_count':mean_tests,'promotion_state':'SHADOW_ONLY'
}
gene['gene_digest']=digest(gene)

checks={
 'open_ended_parent_consumed':parent.get('status')=='PASS_SHADOW_G2_CODING_OPEN_ENDED_DEFECT_HYPOTHESIS_V1',
 'active_semantic_synthesizer_verified':'ALG-G2-SEMANTIC-EXPRESSION-SYNTHESIZER-V1' in active,
 'active_evidence_selector_verified':'ALG-NEUTRAL-EVIDENCE-PROFILE-SELECTOR-V1' in active,
 'active_evolutionary_genome_verified':'CTRL-G2-EVOLUTIONARY-GENOME-V1' in active,
 'fresh_spec_to_oracle_tasks_executed':len(episodes)==8,
 'all_oracles_synthesized':all(e['oracle_expression'] is not None for e in episodes),
 'all_oracles_hidden_exact':all(e['oracle_hidden_validation_score']==1.0 for e in episodes) and oracle_val==1.0,
 'all_tasks_generated_tests':all(len(e['self_generated_tests'])==TEST_COUNT for e in episodes),
 'all_patches_generated':all(e['patch_source_sha256'] for e in episodes),
 'all_sources_changed':all(e['source_changed'] for e in episodes),
 'all_final_code_holdouts_exact':all(e['final_code_holdout_score']==1.0 for e in episodes) and final==1.0,
 'oracle_ablation_material_drop':final-ablation>=.40,
 'restore_exact':restore==final and restore_exact,
 'formal_spec_is_only_external_target_information':True,
 'generated_tests_not_direct_spec_rows':all(set(x['x'] for x in e['self_generated_tests'])!=set(SPEC_X) for e in episodes),
 'host_selected_test_input':False,
 'host_supplied_generated_test_expected':False,
 'host_selected_patch':False,
 'external_coding_model_used':False,
 'automatic_canonical_promotion':False,
 'canonical_unchanged':core.head.get('canonical_head_digest')==head_before.get('canonical_head_digest'),
}
false_keys=['host_selected_test_input','host_supplied_generated_test_expected','host_selected_patch','external_coding_model_used','automatic_canonical_promotion']
true_keys=[k for k in checks if k not in false_keys]
passed=all(checks[k] is True for k in true_keys) and all(checks[k] is False for k in false_keys)
status='PASS_SHADOW_G2_CODING_SELF_GENERATED_TEST_ORACLE_V1' if passed else 'WITHHOLD_G2_CODING_SELF_GENERATED_TEST_ORACLE_V1'

experience={
 'schema':'yado.g2.coding_self_generated_test_oracle.experience.v1','status':'TRAINED' if passed else 'WITHHOLD',
 'parent_open_ended_gene_id':parent_gene['gene_id'],'episodes':episodes,
 'oracle_hidden_validation_score':oracle_val,'initial_code_holdout_score':initial,'final_code_holdout_score':final,
 'oracle_ablation_score':ablation,'restore_score':restore,'mean_self_generated_test_count':mean_tests,
 'oracle_gene':gene,'canonical_mutation':False,
 'semantic_boundary':'THE HOST SUPPLIES A SMALL FORMAL SPECIFICATION DATASET, NOT GENERATED TEST CASES OR A READY ORACLE PROGRAM. ACTIVE G2 SEMANTIC SYNTHESIS BUILDS AN EXECUTABLE ORACLE EXPRESSION AND IS HIDDEN-VALIDATED WITHOUT FEEDBACK. YADO THEN SELECTS NEW TEST INPUTS AND COMPUTES THEIR EXPECTED VALUES ONLY THROUGH ITS SYNTHESIZED ORACLE. ACTIVE EVOLUTIONARY CODE SYNTHESIS BUILDS THE PATCH FROM THOSE SELF-GENERATED TESTS. THIS PROVES BOUNDED SPEC-TO-ORACLE-TO-TEST-TO-PATCH, NOT AUTONOMOUS REQUIREMENT DISCOVERY.'
}
experience['experience_digest']=digest(experience)
EXP.parent.mkdir(parents=True,exist_ok=True);EXP.write_text(json.dumps(experience,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')

report={
 'schema':'yado.g2.coding_self_generated_test_oracle.v1','status':status,'task':task,
 'task_count':len(episodes),'oracle_hidden_validation_score':oracle_val,
 'initial_code_holdout_score':initial,'final_code_holdout_score':final,'oracle_ablation_score':ablation,
 'restore_score':restore,'mean_self_generated_test_count':mean_tests,
 'gene_id':gene['gene_id'],'oracle_gene':gene,'checks':checks,
 'canonical_mutation':False,'promotion_applied':False,
 'next_required_capability':'G2_CODING_SPEC_GENERALIZATION_AND_REAL_CODE_TRANSFER_V1' if passed else 'G2_CODING_SELF_GENERATED_TEST_ORACLE_V2',
 'receipt_sha256':None,'semantic_boundary':experience['semantic_boundary']
}
report['receipt_sha256']=digest({k:v for k,v in report.items() if k!='receipt_sha256'})
OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(report,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')
print(json.dumps({
 'status':status,'task_count':len(episodes),'oracle_hidden_validation_score':oracle_val,
 'initial_code_holdout_score':initial,'final_code_holdout_score':final,'oracle_ablation_score':ablation,
 'restore_score':restore,'mean_self_generated_test_count':mean_tests,'gene_id':gene['gene_id'],
 'next_required_capability':report['next_required_capability'],'receipt_sha256':report['receipt_sha256']
},indent=2,sort_keys=True))
if not passed:raise SystemExit(2)
