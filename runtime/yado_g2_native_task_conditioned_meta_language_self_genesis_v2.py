from __future__ import annotations
from pathlib import Path
from dataclasses import asdict
import copy,hashlib,json,sys

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
PKG=ROOT/'yado_rc8_v36'
sys.path[:0]=[str(ROOT),str(PKG)]

from yado_unified_core_v1 import UnifiedYADOCoreV1
from yado_core_v3_0_rc8_external_cognitive import UnifiedYADOKernelV30RC8ExternalCognitive

TASK=REPO/'architecture/yado-kernel-native-task-conditioned-meta-language-self-genesis-v2-request.json'
FAIL=REPO/'candidates/kernel-self-generated/g2-self-evolving-meta-language-spontaneous-genesis-v1.json'
IRFAIL=REPO/'candidates/kernel-self-generated/g2-native-source-ir-emitter-birth-v1.json'
OUT=REPO/'candidates/kernel-self-generated/g2-native-task-conditioned-meta-language-self-genesis-v2.json'
DB=ROOT/'yado_native_task_conditioned_meta_language_v2.sqlite'

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def digest(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))

task=load(TASK);failure=load(FAIL);irfail=load(IRFAIL)
core=UnifiedYADOCoreV1(REPO)
head_before=copy.deepcopy(core.head)

if DB.exists():DB.unlink()
k=UnifiedYADOKernelV30RC8ExternalCognitive(db_path=str(DB))
try:
    goal=k.executive.create_goal(
      objective=str(task['objective']),
      required_capabilities={'SELF_EVOLVING_META_LANGUAGE_V2':1.0},
      success_criteria={'new_language_gene':True,'self_extension':True,'rollback':True},
    )
    deficits=k.executive.detect_deficits(goal.goal_id)
    native_goal={'goal_id':goal.goal_id,'deficits':[asdict(d) for d in deficits]}
finally:
    try:k.close()
    except Exception:pass

# Inject YADO's own failure as experience into its existing evolutionary genome controller.
state=core.evolutionary_parent_genome()
experience=copy.deepcopy(state.get('experience') or [])
experience += [
  {
    'role':'YADO_OWN_META_LANGUAGE_FAILURE',
    'artifact':str(FAIL.relative_to(REPO)),
    'status':failure.get('status'),
    'next_required_capability':failure.get('next_required_capability'),
    'receipt_sha256':failure.get('receipt_sha256'),
    'checks':failure.get('checks'),
  },
  {
    'role':'YADO_OWN_IR_EMITTER_FAILURE',
    'artifact':str(IRFAIL.relative_to(REPO)),
    'status':irfail.get('status'),
    'next_required_capability':irfail.get('next_required_capability'),
    'receipt_sha256':irfail.get('receipt_sha256'),
    'native_ir_results':irfail.get('native_ir_results'),
  },
]
controller=core.evolutionary_genome_cls(state['parent'],experience_sources=experience)
evolution=controller.evolve_once()

child=evolution.get('child') or {}
child_blob=canon(child).lower()
parent_failure_digest=failure.get('receipt_sha256')
experience_bound=parent_failure_digest in canon(child.get('experience_sources') or [])

# Strict detector: new language must be an explicit child gene/artifact carrying language semantics,
# not just old RC6 meta-grammar snapshots or generic CODE/LOGIC/THINKING/INTELLIGENCE genes.
language_hits=[]
for chrom,gene in sorted((child.get('chromosomes') or {}).items()):
    blob=canon(gene).lower()
    if any(tok in blob for tok in ('meta_language','meta-language','language_gene','grammar_gene','self_extension_language')):
        language_hits.append({'chromosome':chrom,'gene':gene})

task_conditioned=bool(
    experience_bound and
    any(parent_failure_digest==x.get('receipt_sha256') for x in child.get('experience_sources') or [] if isinstance(x,dict))
)
new_language_gene=bool(language_hits)
self_extension=any(
    any(tok in canon(x).lower() for tok in ('self_extension','extend','evolution_rule','mutation_rule','operator_genesis'))
    for x in language_hits
)

checks={
  'prior_failure_injected_as_experience':experience_bound,
  'native_goal_created':True,
  'native_deficit_detected':bool(native_goal['deficits']),
  'native_evolution_executed':bool(evolution.get('run_digest')),
  'evolution_output_retains_failure_experience':task_conditioned,
  'new_language_gene_created':new_language_gene,
  'self_extension_rule_exposed':self_extension,
  'external_coding_models_used':False,
  'new_external_research_used':False,
  'host_meta_language_template_used':False,
  'host_operator_list_used':False,
  'host_representation_schema_used':False,
  'host_source_seed_used':False,
  'host_patch_used':False,
  'host_target_file_selected':False,
  'rollback_parent_available':bool(evolution.get('parent',{}).get('genome_digest')),
  'canonical_unchanged':core.head.get('canonical_head_digest')==head_before.get('canonical_head_digest'),
}
passed=all([
 checks['prior_failure_injected_as_experience'],
 checks['native_goal_created'],
 checks['native_deficit_detected'],
 checks['native_evolution_executed'],
 checks['evolution_output_retains_failure_experience'],
 checks['new_language_gene_created'],
 checks['self_extension_rule_exposed'],
 checks['rollback_parent_available'],
 checks['canonical_unchanged'],
])
status='PASS_SHADOW_G2_NATIVE_TASK_CONDITIONED_META_LANGUAGE_SELF_GENESIS_V2' if passed else 'WITHHOLD_G2_NATIVE_TASK_CONDITIONED_META_LANGUAGE_SELF_GENESIS_V2'
report={
 'schema':'yado.g2.native_task_conditioned_meta_language_self_genesis.v2',
 'status':status,'task':task,'native_goal':native_goal,
 'parent_failure_receipt':parent_failure_digest,
 'ir_emitter_failure_receipt':irfail.get('receipt_sha256'),
 'injected_experience_count':len(experience),
 'native_evolution':evolution,
 'language_gene_hits':language_hits,
 'checks':checks,
 'canonical_mutation':False,
 'next_required_capability':None if passed else 'SELF_EVOLVING_META_LANGUAGE_V2',
 'semantic_boundary':'YADO RECEIVES ITS OWN PRIOR FAILURE AS EXPERIENCE AND RUNS ITS EXISTING NATIVE EVOLUTIONARY GENOME CONTROLLER. THE HOST DOES NOT DEFINE A LANGUAGE OR OPERATOR SET. PASS REQUIRES AN EXPLICIT NEW LANGUAGE GENE WITH A SELF-EXTENSION/EVOLUTION RULE; MERELY CARRYING FAILURE EXPERIENCE OR REPLAYING EXISTING RC6 STRUCTURES IS WITHHOLD.'
}
report['receipt_sha256']=digest(report)
OUT.parent.mkdir(parents=True,exist_ok=True)
OUT.write_text(json.dumps(report,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')
print(json.dumps({
 'status':status,
 'experience_bound':experience_bound,
 'task_conditioned':task_conditioned,
 'new_language_gene':new_language_gene,
 'self_extension':self_extension,
 'selection':evolution.get('selection'),
 'language_gene_hit_count':len(language_hits),
 'next_required_capability':report['next_required_capability'],
 'receipt_sha256':report['receipt_sha256'],
},indent=2,sort_keys=True))
if not passed:raise SystemExit(2)
