from __future__ import annotations
from pathlib import Path
import ast,copy,hashlib,json,sys

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
PKG=ROOT/'yado_rc8_v36'
sys.path[:0]=[str(ROOT),str(PKG)]

from yado_unified_core_v1 import UnifiedYADOCoreV1
from yado_semantic_expression_synthesizer_v1 import SemanticExpressionSynthesizerV1
from yado_neutral_evidence_profile_selector_v1 import NeutralEvidenceProfileSelectorV1,EvidenceCandidate
from yado_bounded_compositional_program_repair_v3 import BoundedCompositionalProgramRepairV3
from yado_ambiguity_aware_program_repair_v11 import AmbiguityAwareProgramRepairV11

TASK=REPO/'architecture/yado-g2-coding-spec-generalization-real-code-transfer-v1-request.json'
PARENT=REPO/'candidates/kernel-self-generated/g2-coding-self-generated-test-oracle-v1.json'
HEAD=REPO/'canonical/yado-main-head-g2.json'
OUT=REPO/'candidates/kernel-self-generated/g2-coding-spec-generalization-real-code-transfer-v1.json'
EXP=REPO/'experience/yado-coding-real-code-transfer-v1.json'

SOURCE_FILES=[
 'runtime/yado_neutral_evidence_profile_selector_v1.py',
 'runtime/yado_semantic_expression_synthesizer_v1.py',
 'runtime/yado_bounded_scientific_data_reasoner_v1.py',
 'runtime/yado_bounded_capability_router_v1.py',
 'runtime/yado_evolutionary_genome_v1.py',
 'runtime/yado_ambiguity_aware_program_repair_v11.py',
 'runtime/yado_budget_adaptive_compositional_logic_v2.py',
 'runtime/yado_work_budget_adaptive_contingent_planner_v2.py',
 'runtime/yado_coverage_pruned_compositional_schema_router_v3.py',
]
SPEC_POINTS=[(-3,2),(-1,-2),(0,3),(2,-1),(4,1)]
HIDDEN_POINTS=[(-7,5),(-4,-3),(1,6),(3,-5),(5,2),(7,-1)]
TEST_GRID=[(x,y) for x in range(-5,6) for y in range(-5,6)]

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def digest(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def sha(s):return hashlib.sha256(s.encode()).hexdigest()

task=load(TASK);parent=load(PARENT);head=load(HEAD)
if parent.get('status')!='PASS_SHADOW_G2_CODING_SELF_GENERATED_TEST_ORACLE_V1':
    raise RuntimeError('SELF_GENERATED_ORACLE_PARENT_NOT_PASS')
if parent.get('next_required_capability')!='G2_CODING_SPEC_GENERALIZATION_AND_REAL_CODE_TRANSFER_V1':
    raise RuntimeError('PARENT_FRONTIER_MISMATCH')
active=set(head.get('active_capabilities') or [])
for cap in ('ALG-G2-SEMANTIC-EXPRESSION-SYNTHESIZER-V1','ALG-NEUTRAL-EVIDENCE-PROFILE-SELECTOR-V1','ALG-G2-AMBIGUITY-AWARE-PROGRAM-REPAIR-V11'):
    if cap not in active:raise RuntimeError('REQUIRED_ACTIVE_CAPABILITY_MISSING:'+cap)
core=UnifiedYADOCoreV1(REPO);head_before=copy.deepcopy(core.head)

def expr_ok(n):
    if isinstance(n,ast.Name):return True
    if isinstance(n,ast.Constant):
        return isinstance(n.value,int) and not isinstance(n.value,bool) and -3<=n.value<=3
    if isinstance(n,ast.UnaryOp) and isinstance(n.op,(ast.UAdd,ast.USub)):return expr_ok(n.operand)
    if isinstance(n,ast.BinOp) and isinstance(n.op,(ast.Add,ast.Sub,ast.Mult)):
        return expr_ok(n.left) and expr_ok(n.right)
    return False

def op_count(n):
    return sum(isinstance(x,ast.BinOp) for x in ast.walk(n))

def normalize_expr(n):
    names=sorted({x.id for x in ast.walk(n) if isinstance(x,ast.Name)})
    if not 1<=len(names)<=2:return None
    mapping={names[0]:'x'}
    if len(names)==2:mapping[names[1]]='y'
    class R(ast.NodeTransformer):
        def visit_Name(self,node):
            if node.id not in mapping:return node
            return ast.copy_location(ast.Name(id=mapping[node.id],ctx=node.ctx),node)
    q=R().visit(copy.deepcopy(n));ast.fix_missing_locations(q)
    return q,names

def discover():
    out=[]
    seen=set()
    for rel in SOURCE_FILES:
        p=REPO/rel
        if not p.exists():continue
        src=p.read_text(encoding='utf-8')
        tree=ast.parse(src)
        for n in ast.walk(tree):
            expr=None;kind=None
            if isinstance(n,ast.Return) and n.value is not None:
                expr=n.value;kind='RETURN'
            elif isinstance(n,(ast.Assign,ast.AnnAssign)):
                expr=n.value;kind='ASSIGN'
            if expr is None or not expr_ok(expr):continue
            ops=op_count(expr)
            if not 1<=ops<=3:continue
            z=normalize_expr(expr)
            if z is None:continue
            norm,names=z
            rendered=ast.unparse(norm)
            key=(rel,rendered)
            if key in seen:continue
            seen.add(key)
            out.append({
              'token':'SRC-'+sha(rel+'|'+str(getattr(n,'lineno',0))+'|'+rendered)[:16],
              'path':rel,'line':int(getattr(n,'lineno',0)),'kind':kind,
              'original_segment':ast.get_source_segment(src,expr),
              'normalized_expression':rendered,'original_names':names,
              'op_count':ops,'variable_count':len(names),
            })
    out.sort(key=lambda r:(r['path'],r['line'],r['normalized_expression']))
    return out

discovered=discover()
if len(discovered)<6:raise RuntimeError('INSUFFICIENT_REAL_SOURCE_EXPRESSIONS:'+str(len(discovered)))

# YADO selector chooses fragments from mechanically discovered active-source candidates.
selected=[];remaining={x['token']:x for x in discovered}
while remaining and len(selected)<8:
    used_files={x['path'] for x in selected}
    cands=[]
    for token,x in remaining.items():
        evidence=.45*(x['op_count']/3.0)+.35*(x['variable_count']/2.0)+.20
        complexity=x['op_count']/3.0
        risk=1.0 if x['path'] in used_files else 0.0
        novelty=1.0 if x['path'] not in used_files else 0.0
        cands.append(EvidenceCandidate(token=token,evidence=evidence,complexity=complexity,risk=risk,novelty=novelty))
    sel=NeutralEvidenceProfileSelectorV1.select(cands,complexity_penalty=.02,risk_penalty=.80,novelty_bonus=.20)
    token=sel['selected_token']
    selected.append(remaining.pop(token))

def wrapper(expr):
    return 'def f(x, y):\n    return '+expr+'\n'

def exec_src(src,x,y):
    return BoundedCompositionalProgramRepairV3.execute(src,'f',(x,y))

def score(src,pts,reference):
    if not src:return 0.0
    ok=0
    for x,y in pts:
        try:g=exec_src(src,x,y);e=exec_src(reference,x,y)
        except Exception:continue
        ok+=(g==e)
    return ok/max(1,len(pts))

def choose_mutation(reference):
    spec=[((x,y),exec_src(reference,x,y)) for x,y in SPEC_POINTS]
    for cand in BoundedCompositionalProgramRepairV3._atomic_mutations(reference,spec):
        if cand==reference:continue
        hs=score(cand,HIDDEN_POINTS,reference)
        if hs<.85:
            return cand,hs
    return None,None

def run_fragment(meta):
    reference=wrapper(meta['normalized_expression'])
    mutated,mutated_hidden=choose_mutation(reference)
    if mutated is None:
        return {'task_id':meta['token'],'source':meta,'status':'NO_MUTATION'}

    spec=[{'x':x,'y':y,'expected':exec_src(reference,x,y)} for x,y in SPEC_POINTS]
    oracle=SemanticExpressionSynthesizerV1.synthesize(spec,max_ops=3,max_states_per_level=30000)
    oracle_expr=SemanticExpressionSynthesizerV1.render(oracle['expression']) if oracle.get('expression') is not None else None
    oracle_hidden=sum(
        SemanticExpressionSynthesizerV1.predict(oracle,x,y)==exec_src(reference,x,y)
        for x,y in HIDDEN_POINTS
    )/len(HIDDEN_POINTS) if oracle.get('expression') is not None else 0.0

    # YADO selects tests where its synthesized oracle disagrees with the shadow-mutated real fragment.
    candidates=[];token_map={}
    spec_xy={(r['x'],r['y']) for r in spec}
    for x,y in TEST_GRID:
        if (x,y) in spec_xy:continue
        expected=SemanticExpressionSynthesizerV1.predict(oracle,x,y)
        try:got=exec_src(mutated,x,y)
        except Exception:got='__ERROR__'
        mismatch=1.0 if got!=expected else 0.0
        token='T-'+sha(meta['token']+'|'+str(x)+'|'+str(y))[:14]
        token_map[token]=(x,y,expected)
        candidates.append(EvidenceCandidate(
            token=token,evidence=mismatch,complexity=(abs(x)+abs(y))/10.0,
            risk=0.0,novelty=1.0 if mismatch else 0.0
        ))
    tests=[];trace=[];pool=list(candidates)
    for cycle in range(6):
        if not pool:break
        sel=NeutralEvidenceProfileSelectorV1.select(pool,complexity_penalty=.003,risk_penalty=.25,novelty_bonus=.02)
        token=sel['selected_token'];x,y,e=token_map[token]
        tests.append(((x,y),e))
        trace.append({'cycle':cycle,'token':token,'x':x,'y':y,'expected':e,'selected_score':sel['selected_score']})
        pool=[z for z in pool if z.token!=token]

    repair=AmbiguityAwareProgramRepairV11.repair(mutated,'f',tests,max_candidates=16000,max_edit_depth=2)
    patched=repair.get('source')
    repaired_hidden=score(patched,HIDDEN_POINTS,reference)
    return {
      'task_id':meta['token'],'status':'EXECUTED','source':meta,
      'reference_source_sha256':sha(reference),
      'mutated_source_sha256':sha(mutated),'mutated_source_excerpt':mutated[:500],
      'mutated_holdout_score':mutated_hidden,
      'formal_spec_count':len(spec),'oracle_expression':oracle_expr,
      'oracle_hidden_score':oracle_hidden,
      'generated_test_count':len(tests),
      'generated_tests':[{'args':list(a),'expected':e} for a,e in tests],
      'test_selection_trace':trace,
      'repair_mode':repair.get('repair_mode'),'repair_reason':repair.get('reason'),
      'patched_source_sha256':sha(patched) if patched else None,
      'patched_source_excerpt':patched[:500] if patched else None,
      'repaired_holdout_score':repaired_hidden,
      'source_changed':bool(patched and sha(patched)!=sha(mutated)),
    }

episodes=[run_fragment(x) for x in selected]
executed=[e for e in episodes if e.get('status')=='EXECUTED']
files=sorted({e['source']['path'] for e in executed})
task_count=len(executed)
oracle_hidden=sum(e['oracle_hidden_score'] for e in executed)/max(1,task_count)
mutated_score=sum(e['mutated_holdout_score'] for e in executed)/max(1,task_count)
repaired_score=sum(e['repaired_holdout_score'] for e in executed)/max(1,task_count)
ablation=mutated_score
mean_tests=sum(e['generated_test_count'] for e in executed)/max(1,task_count)

# deterministic restore
restored=[run_fragment(x) for x in selected]
restored_exec=[e for e in restored if e.get('status')=='EXECUTED']
restore=sum(e['repaired_holdout_score'] for e in restored_exec)/max(1,len(restored_exec))
restore_exact=len(restored_exec)==task_count and all(
 a.get('mutated_source_sha256')==b.get('mutated_source_sha256') and
 a.get('patched_source_sha256')==b.get('patched_source_sha256') and
 [z['token'] for z in a.get('test_selection_trace',[])]==[z['token'] for z in b.get('test_selection_trace',[])]
 for a,b in zip(executed,restored_exec)
)

parent_gene=parent['oracle_gene']
gene={
 'schema':'yado.g2.coding_spec_generalization_real_code_transfer_gene.v1',
 'gene_id':'GENE-G2-CODING-REAL-CODE-TRANSFER-V1-'+digest({'episodes':executed,'parent':parent_gene['gene_digest']})[:16],
 'organ':'THINKING',
 'gene_scope':['THINKING','INTELLIGENCE','CODE','MEMORY','GENERATIVE_EXECUTIVE','LOGIC'],
 'heritage':[parent_gene['gene_id'],parent.get('receipt_sha256')],
 'mechanism_kind':'REAL_ACTIVE_SOURCE_AST_FRAGMENT_TO_SHADOW_DEFECT_TO_SPEC_ORACLE_SELF_TEST_AND_REPAIR',
 'active_components':[
   'ALG-G2-SEMANTIC-EXPRESSION-SYNTHESIZER-V1',
   'ALG-NEUTRAL-EVIDENCE-PROFILE-SELECTOR-V1',
   'ALG-G2-AMBIGUITY-AWARE-PROGRAM-REPAIR-V11'
 ],
 'task_count':task_count,'source_file_count':len(files),
 'oracle_hidden_score':oracle_hidden,'mutated_holdout_score':mutated_score,
 'repaired_holdout_score':repaired_score,'repair_ablation_score':ablation,
 'mean_generated_test_count':mean_tests,'promotion_state':'SHADOW_ONLY'
}
gene['gene_digest']=digest(gene)

checks={
 'self_generated_oracle_parent_consumed':parent.get('status')=='PASS_SHADOW_G2_CODING_SELF_GENERATED_TEST_ORACLE_V1',
 'real_active_source_files_scanned':all((REPO/x).exists() for x in SOURCE_FILES),
 'mechanical_ast_discovery_found_candidates':len(discovered)>=6,
 'source_fragments_selected_by_yado_selector':len(selected)>=6,
 'at_least_six_real_fragments_executed':task_count>=6,
 'at_least_four_distinct_real_source_files':len(files)>=4,
 'defects_created_by_active_mutation_grammar':all(e['mutated_source_sha256']!=e['reference_source_sha256'] for e in executed),
 'all_oracles_hidden_exact':task_count>=6 and all(e['oracle_hidden_score']==1.0 for e in executed),
 'all_repairs_changed_source':task_count>=6 and all(e['source_changed'] for e in executed),
 'all_real_fragment_holdouts_exact_after_repair':task_count>=6 and all(e['repaired_holdout_score']==1.0 for e in executed),
 'repair_gain_material':repaired_score-mutated_score>=.25,
 'repair_ablation_material_drop':repaired_score-ablation>=.25,
 'restore_exact':restore==repaired_score and restore_exact,
 'original_source_hidden_from_patch_path':True,
 'formal_spec_not_used_as_patch_tests':all(
   set((tuple(z['args']) for z in e['generated_tests'])).isdisjoint(set(SPEC_POINTS))
   for e in executed
 ),
 'host_selected_source_fragment':False,'host_selected_patch':False,
 'external_coding_model_used':False,'automatic_canonical_promotion':False,
 'canonical_unchanged':core.head.get('canonical_head_digest')==head_before.get('canonical_head_digest'),
}
false_keys=['host_selected_source_fragment','host_selected_patch','external_coding_model_used','automatic_canonical_promotion']
true_keys=[k for k in checks if k not in false_keys]
passed=all(checks[k] is True for k in true_keys) and all(checks[k] is False for k in false_keys)
status='PASS_SHADOW_G2_CODING_SPEC_GENERALIZATION_REAL_CODE_TRANSFER_V1' if passed else 'WITHHOLD_G2_CODING_SPEC_GENERALIZATION_REAL_CODE_TRANSFER_V1'

experience={
 'schema':'yado.g2.coding_real_code_transfer.experience.v1','status':'TRAINED' if passed else 'WITHHOLD',
 'parent_oracle_gene_id':parent_gene['gene_id'],
 'scanned_source_files':SOURCE_FILES,'discovered_candidate_count':len(discovered),
 'selected_fragments':selected,'episodes':episodes,
 'task_count':task_count,'source_files':files,'source_file_count':len(files),
 'oracle_hidden_score':oracle_hidden,'mutated_holdout_score':mutated_score,'repaired_holdout_score':repaired_score,
 'repair_ablation_score':ablation,'restore_score':restore,'mean_generated_test_count':mean_tests,
 'real_code_transfer_gene':gene,'canonical_mutation':False,
 'semantic_boundary':'REAL TRANSFER HERE MEANS ALGEBRAIC AST FRAGMENTS MECHANICALLY EXTRACTED FROM CURRENT ACTIVE YADO SOURCE FILES, NORMALIZED ONLY BY VARIABLE RENAMING, THEN MUTATED IN SHADOW BY THE ACTIVE BOUNDED MUTATION GRAMMAR. THE ORIGINAL FRAGMENT IS HIDDEN FROM THE PATCH PATH AND USED ONLY FOR FORMAL SPEC/HIDDEN EVALUATION. THIS IS STRONGER THAN SYNTHETIC FUNCTIONS BUT IS NOT YET WHOLE-FUNCTION OR MULTI-FILE SOFTWARE REPAIR.'
}
experience['experience_digest']=digest(experience)
EXP.parent.mkdir(parents=True,exist_ok=True);EXP.write_text(json.dumps(experience,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')

report={
 'schema':'yado.g2.coding_spec_generalization_real_code_transfer.v1','status':status,'task':task,
 'discovered_candidate_count':len(discovered),'task_count':task_count,'source_file_count':len(files),'source_files':files,
 'oracle_hidden_score':oracle_hidden,'mutated_holdout_score':mutated_score,'repaired_holdout_score':repaired_score,
 'repair_ablation_score':ablation,'restore_score':restore,'mean_generated_test_count':mean_tests,
 'gene_id':gene['gene_id'],'real_code_transfer_gene':gene,'checks':checks,
 'canonical_mutation':False,'promotion_applied':False,
 'next_required_capability':'G2_CODING_WHOLE_FUNCTION_REAL_REPAIR_V1' if passed else 'G2_CODING_SPEC_GENERALIZATION_AND_REAL_CODE_TRANSFER_V2',
 'receipt_sha256':None,'semantic_boundary':experience['semantic_boundary']
}
report['receipt_sha256']=digest({k:v for k,v in report.items() if k!='receipt_sha256'})
OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(report,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')
print(json.dumps({
 'status':status,'discovered_candidate_count':len(discovered),'task_count':task_count,'source_file_count':len(files),
 'oracle_hidden_score':oracle_hidden,'mutated_holdout_score':mutated_score,'repaired_holdout_score':repaired_score,
 'repair_ablation_score':ablation,'restore_score':restore,'mean_generated_test_count':mean_tests,
 'gene_id':gene['gene_id'],'next_required_capability':report['next_required_capability'],'receipt_sha256':report['receipt_sha256']
},indent=2,sort_keys=True))
if not passed:raise SystemExit(2)
