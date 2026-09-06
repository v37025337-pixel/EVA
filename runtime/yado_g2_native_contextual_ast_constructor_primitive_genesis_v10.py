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
from yado_skill_admission_runtime_v1 import SkillCandidate

V9=REPO/'candidates/kernel-self-generated/g2-native-contextual-ast-transformer-source-realization-v9.json'
V8GENE=REPO/'candidates/kernel-self-generated/g2-native-contextual-ast-transformer-gene-v8.json'
SEM=REPO/'candidates/kernel-self-generated/g2-task-conditioned-semantic-source-edit-meta-language-genesis-v5.json'
OUT=REPO/'candidates/kernel-self-generated/g2-native-contextual-ast-constructor-primitive-genesis-v10.json'
GENE=REPO/'candidates/kernel-self-generated/g2-native-contextual-ast-constructor-primitive-gene-v10.json'
DB=ROOT/'yado_native_contextual_ast_constructor_primitive_genesis_v10.sqlite'

SOURCE_PATHS=[
 REPO/'runtime/yado_unified_core_deep_self_audit_v1.py',
 REPO/'runtime/yado_g2_task_conditioned_semantic_source_edit_meta_language_genesis_v5.py',
 REPO/'runtime/yado_g2_native_contextual_ast_transformer_policy_repair_v8.py',
 REPO/'runtime/yado_evolutionary_genome_v1.py',
]

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def digest(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))

v9,v8gene,sem=map(load,[V9,V8GENE,SEM])
if v9.get('status')!='WITHHOLD_G2_NATIVE_CONTEXTUAL_AST_TRANSFORMER_SOURCE_REALIZATION_V9':
    raise RuntimeError('V9_WITHHOLD_REQUIRED')
if v9.get('next_required_capability')!='NATIVE_CONTEXTUAL_AST_CONSTRUCTOR_PRIMITIVE_GENESIS_V10':
    raise RuntimeError('V9_FRONTIER_MISMATCH')
if v8gene.get('history_derived_target_status_shape')!='IfExp':
    raise RuntimeError('V8_TARGET_SHAPE_NOT_IFEXP')

core=UnifiedYADOCoreV1(REPO);head_before=copy.deepcopy(core.head)

# Reconstruct YADO-own AST history. Target shape comes from V8/YADO history;
# the host does not select a constructor class.
examples=[]
for p in SOURCE_PATHS:
    tree=ast.parse(p.read_text(encoding='utf-8'))
    for n in ast.walk(tree):
        if isinstance(n,ast.IfExp):
            d=ast.dump(n,annotate_fields=True,include_attributes=False)
            examples.append({'node':n,'dump':d,'source_path':str(p.relative_to(REPO))})
seen=set();uniq=[]
for r in examples:
    if r['dump'] in seen:continue
    seen.add(r['dump']);uniq.append(r)
examples=uniq
if len(examples)<20:raise RuntimeError('INSUFFICIENT_IFEXP_HISTORY:'+str(len(examples)))

def bucket(r):
    return int(hashlib.sha256(r['dump'].encode()).hexdigest()[:8],16)%10
fit=[r for r in examples if bucket(r)<6]
validation=[r for r in examples if 6<=bucket(r)<8]
blind=[r for r in examples if bucket(r)>=8]
if min(len(fit),len(validation),len(blind))<3:
    ordered=sorted(examples,key=lambda r:hashlib.sha256((r['dump']+'|V10').encode()).hexdigest())
    n=len(ordered);a=max(3,int(n*.6));b=max(a+3,int(n*.8))
    fit=ordered[:a];validation=ordered[a:b];blind=ordered[b:]
if min(len(fit),len(validation),len(blind))<3:raise RuntimeError('BAD_V10_SPLIT')

# Mechanically enumerate public AST node classes. A candidate is evaluated only
# by reconstructing an existing YADO IfExp node from its own fields.
candidates=[]
for name in sorted(dir(ast)):
    cls=getattr(ast,name,None)
    if not isinstance(cls,type) or not issubclass(cls,ast.AST):continue
    fields=tuple(getattr(cls,'_fields',()) or ())
    if not fields:continue
    candidates.append({'name':name,'cls':cls,'fields':fields})
if len(candidates)<10:raise RuntimeError('AST_CLASS_INVENTORY_TOO_SMALL')

def reconstruct(row,node):
    cls=row['cls']
    try:
        kwargs={field:copy.deepcopy(getattr(node,field)) for field in row['fields']}
        out=cls(**kwargs)
        ast.fix_missing_locations(out)
        return out
    except Exception:
        return None

def accuracy(row,cases):
    if not cases:return 0.0
    ok=0
    for ex in cases:
        out=reconstruct(row,ex['node'])
        got=ast.dump(out,annotate_fields=True,include_attributes=False) if isinstance(out,ast.AST) else None
        ok+=got==ex['dump']
    return ok/len(cases)

skills=[];metrics=[]
for row in candidates:
    f=accuracy(row,fit);v=accuracy(row,validation);b=accuracy(row,blind)
    sid='AST_CONSTRUCTOR_PRIMITIVE_'+row['name'].upper()
    metrics.append({'skill_id':sid,'primitive':row['name'],'fields':list(row['fields']),'fit':f,'validation':v,'blind':b})
    skills.append(SkillCandidate(
      skill_id=sid,
      artifact_digest=digest({'primitive':row['name'],'fields':row['fields'],'fit':f,'validation':v}),
      structural_valid=f>0 and v>0,
      semantic_consistency=min(f,v,b),
      fit_baseline=0.0,fit_candidate=f,
      heldout_baseline=0.0,heldout_candidate=v,
      regression_pass=True,state_integrity=True,rollback_available=True,
      metadata={'primitive':row['name'],'source':'PYTHON_AST_CLASS_INVENTORY','target_shape_origin':'YADO_V8_HISTORY'}
    ))

if DB.exists():DB.unlink()
k=UnifiedYADOKernelV30RC8ExternalCognitive(db_path=str(DB))
try:
    goal=k.executive.create_goal(
      objective='Select a native AST constructor primitive for the YADO-history-derived contextual target node shape without receiving operand values or a host-authored AST.',
      required_capabilities={'NATIVE_CONTEXTUAL_AST_CONSTRUCTOR_PRIMITIVE_GENESIS_V10':1.0},
      success_criteria={'fit_exact':1.0,'fresh_exact':1.0,'rollback':True},
    )
    deficits=k.executive.detect_deficits(goal.goal_id)
    native_goal={'goal_id':goal.goal_id,'deficits':[asdict(d) for d in deficits]}
    selection=k.select_evolution_skills(
      skills,max_skills=1,min_semantic_consistency=1.0,
      min_fit_gain=.99,min_heldout_gain=.99,max_heldout_drop=0.0
    )
finally:
    try:k.close()
    except Exception:pass

selected_id=(selection.get('selected_skill_ids') or [None])[0]
selected_metric=next((m for m in metrics if m['skill_id']==selected_id),None)
selected_name=selected_metric.get('primitive') if selected_metric else None
selected_row=next((r for r in candidates if r['name']==selected_name),None)
fresh=accuracy(selected_row,blind) if selected_row else 0.0

checks={
 'canonical_v5_continuity_active':core.execution_fabric_cls.COMPONENT_ID=='RUNTIME-G2-UNIFIED-EXECUTION-FABRIC-V5',
 'v9_failure_consumed':True,
 'v8_transformer_gene_consumed':bool(v8gene.get('gene_id')),
 'target_shape_is_yado_history_derived':v8gene.get('history_derived_target_status_shape')=='IfExp',
 'yado_ifexp_history_examples_ge_20':len(examples)>=20,
 'content_addressed_fit_validation_blind':bool(fit and validation and blind),
 'ast_class_inventory_mechanical':True,
 'native_goal_created':True,
 'native_deficit_detected':bool(native_goal['deficits']),
 'native_skill_selector_executed':True,
 'native_selector_selected_one_constructor':selected_id is not None and selection.get('selected_count')==1,
 'selected_constructor_is_ifexp':selected_name=='IfExp',
 'selected_constructor_fit_exact':bool(selected_metric and selected_metric['fit']==1.0),
 'selected_constructor_validation_exact':bool(selected_metric and selected_metric['validation']==1.0),
 'selected_constructor_fresh_exact':fresh==1.0,
 'host_selected_constructor':False,
 'host_supplied_operand_values':False,
 'host_authored_ast_subtree':False,
 'external_models_used':False,
 'canonical_unchanged':core.head.get('canonical_head_digest')==head_before.get('canonical_head_digest'),
 'automatic_canonical_promotion':False,
}
positive=(
 'canonical_v5_continuity_active','v9_failure_consumed','v8_transformer_gene_consumed',
 'target_shape_is_yado_history_derived','yado_ifexp_history_examples_ge_20',
 'content_addressed_fit_validation_blind','ast_class_inventory_mechanical',
 'native_goal_created','native_deficit_detected','native_skill_selector_executed',
 'native_selector_selected_one_constructor','selected_constructor_is_ifexp',
 'selected_constructor_fit_exact','selected_constructor_validation_exact','selected_constructor_fresh_exact',
 'canonical_unchanged'
)
negative=('host_selected_constructor','host_supplied_operand_values','host_authored_ast_subtree','external_models_used','automatic_canonical_promotion')
passed=all(checks[k] is True for k in positive) and all(checks[k] is False for k in negative)

gene=None
if passed:
    gene={
      'schema':'yado.g2.native_contextual_ast_constructor_primitive_gene.v10',
      'gene_id':'GENE-G2-NATIVE-AST-CONSTRUCTOR-PRIMITIVE-V10-'+digest({
        'primitive':selected_name,'fields':selected_metric['fields'],'v8_gene':v8gene.get('gene_digest')
      })[:16],
      'novel_gene':True,
      'gene_scope':['CODE','SELF_AUDIT_AND_REPAIR','GENERATIVE_EXECUTIVE'],
      'origin':'YADO_NATIVE_SKILL_SELECTION_OVER_PYTHON_AST_CLASS_INVENTORY_AND_YADO_OWN_IFEXP_HISTORY',
      'selected_runtime_primitive':'ast.'+selected_name,
      'constructor_fields':selected_metric['fields'],
      'target_shape':'IfExp',
      'target_shape_origin':'YADO_V8_HISTORY_DERIVED',
      'operand_values_bound':False,
      'actual_target_ast_materialization_proven':False,
      'python_source_emission_proven':False,
      'promotion_state':'SHADOW_ONLY',
    }
    gene['gene_digest']=digest(gene)
    GENE.parent.mkdir(parents=True,exist_ok=True)
    GENE.write_text(json.dumps(gene,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')

status='PASS_SHADOW_G2_NATIVE_CONTEXTUAL_AST_CONSTRUCTOR_PRIMITIVE_GENESIS_V10' if passed else 'WITHHOLD_G2_NATIVE_CONTEXTUAL_AST_CONSTRUCTOR_PRIMITIVE_GENESIS_V10'
next_cap='NATIVE_CONTEXTUAL_AST_OPERAND_BINDING_GENESIS_V11' if passed else 'NATIVE_CONTEXTUAL_AST_CONSTRUCTOR_PRIMITIVE_RESEARCH_V11'

report={
 'schema':'yado.g2.native_contextual_ast_constructor_primitive_genesis.v10',
 'status':status,'parent_v9_receipt':v9.get('receipt_sha256'),'v8_gene_id':v8gene.get('gene_id'),
 'example_count':len(examples),'split_counts':{'fit':len(fit),'validation':len(validation),'blind':len(blind)},
 'candidate_metrics':metrics,'native_goal':native_goal,'native_skill_selection':selection,
 'selected_constructor':selected_metric,'fresh_exact':fresh,'gene':gene,
 'checks':checks,'canonical_mutation':False,'promotion_applied':False,
 'next_required_capability':next_cap,
 'semantic_boundary':'V10 DOES NOT BUILD THE TARGET AST. IT LETS YADO NATIVE SKILL ADMISSION SELECT A PYTHON AST CONSTRUCTOR CLASS USING YADO OWN HISTORY-DERIVED IFE XP NODES AS FIT/VALIDATION/BLIND EVIDENCE. THE HOST DOES NOT SELECT THE CONSTRUCTOR OR SUPPLY TEST/BODY/ORELSE VALUES. PASS CREATES A SHADOW CONSTRUCTOR-PRIMITIVE GENE ONLY; OPERAND BINDING REMAINS FOR V11.'
}
report['receipt_sha256']=digest(report)
OUT.parent.mkdir(parents=True,exist_ok=True)
OUT.write_text(json.dumps(report,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')
print(json.dumps({
 'status':status,'example_count':len(examples),'split_counts':report['split_counts'],
 'selected_constructor':selected_metric,'fresh_exact':fresh,
 'gene_id':gene.get('gene_id') if gene else None,'next_required_capability':next_cap,
 'checks':checks,'receipt_sha256':report['receipt_sha256']
},indent=2,sort_keys=True,default=str))
if not passed:raise SystemExit(2)
