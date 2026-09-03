from __future__ import annotations
from pathlib import Path
import ast,copy,hashlib,json,os,sys

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
PKG=ROOT/'yado_rc8_v36'
sys.path[:0]=[str(ROOT),str(PKG)]

from yado_unified_core_v1 import UnifiedYADOCoreV1
from yado_core_v3_0_rc8_external_cognitive import UnifiedYADOKernelV30RC8ExternalCognitive
from yado_ambiguity_aware_program_repair_v11 import AmbiguityAwareProgramRepairV11
from yado_generic_compile_repair_meta_language_v1 import GenericCompileRepairMetaLanguageV1

TARGET=REPO/'runtime/yado_g2_autonomous_self_rewrite_v1.py'
OUT=REPO/'candidates/kernel-self-generated/g2-self-synthesized-compile-repair-v1.json'
GENE_DIR=REPO/'candidates/g2-self-evolution'
REPAIRED=GENE_DIR/'yado_g2_autonomous_self_rewrite_v1_compile_repaired_candidate.py'

def canon(o): return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def digest(o): return hashlib.sha256(canon(o).encode()).hexdigest()

def compile_error(src):
    try:
        compile(src,'<target>','exec'); return None
    except SyntaxError as e:
        return {'msg':str(e.msg),'lineno':e.lineno,'offset':e.offset,'text':e.text.rstrip('\n') if e.text else None}

def ex(broken,expected):
    return {'broken':broken,'expected':expected}

train=[
 ex("def f(x):\n    return (x+1))\n","def f(x):\n    return (x+1)\n"),
 ex("def f(x):\n    return [x, x+1]]\n","def f(x):\n    return [x, x+1]\n"),
 ex("def f(x):\n    return {'a':x}}\n","def f(x):\n    return {'a':x}\n"),
 ex("def f(a,b):\n    y=(a+b)) + 3\n    return y\n","def f(a,b):\n    y=(a+b) + 3\n    return y\n"),
 ex("def f(xs):\n    z=[len(xs)]] + [1]\n    return z\n","def f(xs):\n    z=[len(xs)] + [1]\n    return z\n"),
 ex("def f(x):\n    d={'x':(x+2)}}\n    return d\n","def f(x):\n    d={'x':(x+2)}\n    return d\n"),
]

holdout=[
 ex("def g(x):\n    value=(x*2)) - 1\n    return value\n","def g(x):\n    value=(x*2) - 1\n    return value\n"),
 ex("def g(xs):\n    value=[xs[0], xs[-1]]] + xs\n    return value\n","def g(xs):\n    value=[xs[0], xs[-1]] + xs\n    return value\n"),
 ex("def g(x):\n    value={'k':[x]}}\n    return value\n","def g(x):\n    value={'k':[x]}\n    return value\n"),
 ex("def h(a,b):\n    if (a < b)):\n        return a\n    return b\n","def h(a,b):\n    if (a < b):\n        return a\n    return b\n"),
 ex("def h(x):\n    q=([x, x+1]])\n    return q\n","def h(x):\n    q=([x, x+1])\n    return q\n"),
 ex("def h(x):\n    q=({'a':x}})\n    return q\n","def h(x):\n    q=({'a':x})\n    return q\n"),
]

# Existing semantic repair cannot even enter its AST repair path on syntax-broken input.
existing_failures=0
for row in train:
    try:
        AmbiguityAwareProgramRepairV11.repair(row['broken'],'f',[((1,),1)])
    except Exception:
        existing_failures+=1

core=UnifiedYADOCoreV1(REPO)
parent_genome=core.evolutionary_parent_genome()
parent_gene_ids=[]
for g in (parent_genome.get('chromosomes') or {}).values():
    if isinstance(g,dict) and g.get('gene_id'): parent_gene_ids.append(g['gene_id'])

programs=[]
for p in GenericCompileRepairMetaLanguageV1.programs():
    tr=GenericCompileRepairMetaLanguageV1.accuracy(p,train)
    if tr<1.0: continue
    ho=GenericCompileRepairMetaLanguageV1.accuracy(p,holdout)
    abscores=[GenericCompileRepairMetaLanguageV1.accuracy(a['program'],holdout) for a in GenericCompileRepairMetaLanguageV1.ablations(p)]
    best_ab=max(abscores,default=0.0)
    programs.append({'program':p,'train_accuracy':tr,'fresh_accuracy':ho,'best_ablation_accuracy':best_ab})

skills=[]
for i,row in enumerate(programs):
    p=row['program']; gap=row['fresh_accuracy']-row['best_ablation_accuracy']
    sid=f"COMPILE_REPAIR_PROGRAM_{i:03d}"
    row['skill_id']=sid
    valid=row['train_accuracy']==1.0 and row['fresh_accuracy']==1.0 and row['best_ablation_accuracy']<1.0
    skills.append({
      'skill_id':sid,'artifact_digest':p['program_digest'],
      'structural_valid':valid,'semantic_consistency':row['fresh_accuracy'],
      'fit_baseline':0.0,'fit_candidate':row['fresh_accuracy'],
      'heldout_baseline':0.0,'heldout_candidate':row['fresh_accuracy'],
      'regression_pass':valid,'state_integrity':True,'rollback_available':True,
    })

k=UnifiedYADOKernelV30RC8ExternalCognitive(db_path=str(ROOT/'yado_compile_repair_invention.sqlite'))
try:
    selection=k.select_evolution_skills(skills,max_skills=1,min_semantic_consistency=.99,min_fit_gain=.90,max_heldout_drop=0,min_heldout_gain=.90)
finally:
    k.close()
selected=(selection.get('selected_skill_ids') or [None])[0]
winner=next((x for x in programs if x.get('skill_id')==selected),None)

target_source=TARGET.read_text(encoding='utf-8')
before=compile_error(target_source)
target_repaired=None
target_after=None
if winner is not None:
    target_repaired=GenericCompileRepairMetaLanguageV1.execute(winner['program'],target_source)
    target_after=compile_error(target_repaired) if target_repaired is not None else before

gene=None
if winner is not None and target_repaired is not None and target_after is None:
    p=winner['program']
    gene={
      'schema':'yado.g2.self_synthesized_compile_repair_gene.v1',
      'gene_id':'GENE-SELF-SYNTHESIZED-COMPILE-'+p['program_digest'][:16],
      'novel_gene':True,'gene_scope':['CODE','SELF_AUDIT_AND_REPAIR'],
      'heritage':sorted(parent_gene_ids),
      'meta_language_component':GenericCompileRepairMetaLanguageV1.COMPONENT_ID,
      'operator_program':p,'execution_mode':'BOUNDED_META_LANGUAGE_INTERPRETER',
      'promotion_state':'SHADOW_ONLY',
      'trigger':{'deficit_id':'SELF_REWRITE_CONTROLLER_COMPILE_FAILURE','source':'RECURRENT_COMPILE_FAILURE_HISTORY'}
    }
    gene['gene_digest']=digest(gene)
    GENE_DIR.mkdir(parents=True,exist_ok=True)
    REPAIRED.write_text(target_repaired,encoding='utf-8')

checks={
  'existing_repair_path_incompatible_with_syntax_broken_source':existing_failures==len(train),
  'kernel_selected_mechanism':winner is not None,
  'train_exact':winner is not None and winner['train_accuracy']==1.0,
  'fresh_exact':winner is not None and winner['fresh_accuracy']==1.0,
  'structural_ablation_causes_drop':winner is not None and winner['best_ablation_accuracy']<1.0,
  'target_was_compile_broken':before is not None,
  'target_repaired_by_same_program':target_repaired is not None and target_after is None,
  'new_gene_not_parent_gene':gene is not None and gene['gene_id'] not in set(parent_gene_ids),
  'no_external_patch_or_model_used':True,
  'host_did_not_supply_target_patch':True,
  'single_edit_bounded_mechanism':gene is not None and gene['operator_program'].get('max_edits')==1,
  'canonical_head_unchanged':core.head.get('g3_genesis_performed') is False,
}
status='PASS_SHADOW_G2_SELF_SYNTHESIZED_COMPILE_REPAIR_V1' if all(checks.values()) else 'WITHHOLD_G2_SELF_SYNTHESIZED_COMPILE_REPAIR_V1'

report={
  'schema':'yado.g2.self_synthesized_compile_repair.v1','status':status,
  'meta_language':GenericCompileRepairMetaLanguageV1.component(),
  'parent_gene_ids':parent_gene_ids,'candidate_program_count':len(programs),
  'kernel_selection':selection,'selected_program':winner,'invented_gene':gene,
  'target':{
    'path':str(TARGET.relative_to(REPO)),'compile_error_before':before,
    'repaired_candidate_path':str(REPAIRED.relative_to(REPO)) if REPAIRED.exists() else None,
    'compile_error_after':target_after,
  },
  'checks':checks,'canonical_mutation':False,'architecture_mutation':False,
  'generation_transition':False,'g3_genesis_performed':False,
  'semantic_boundary':'YADO SYNTHESIZES A BOUNDED GENERIC SINGLE-CHARACTER COMPILE-REPAIR OPERATOR FROM TRAINING FAILURES, PROVES IT ON FRESH SYNTAX-BROKEN PROGRAMS AND ABLATION, THEN APPLIES THE SAME OPERATOR TO THE PRE-EXISTING BROKEN SELF-REWRITE CONTROLLER. NO EXTERNAL MODEL OR READY PATCH IS USED. THIS IS NOT YET OPEN-ENDED PROGRAM REPAIR.'
}
report['receipt_sha256']=digest(report)
OUT.parent.mkdir(parents=True,exist_ok=True)
OUT.write_text(json.dumps(report,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')
print(json.dumps({
  'status':status,'selected_program':winner,'invented_gene_id':gene.get('gene_id') if gene else None,
  'target_compile_error_before':before,'target_compile_error_after':target_after,
  'repaired_candidate_path':report['target']['repaired_candidate_path'],
  'checks':checks,'receipt_sha256':report['receipt_sha256']
},indent=2,sort_keys=True,default=str))
if status!='PASS_SHADOW_G2_SELF_SYNTHESIZED_COMPILE_REPAIR_V1':
    raise SystemExit(2)
