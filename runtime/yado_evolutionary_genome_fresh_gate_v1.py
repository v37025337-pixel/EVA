from __future__ import annotations
from pathlib import Path
import hashlib,json,sys

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
PKG=ROOT/'yado_rc8_v36'
sys.path[:0]=[str(ROOT),str(PKG)]

from yado_unified_core_v1 import UnifiedYADOCoreV1
from yado_evolutionary_genome_v1 import YADOEvolutionaryGenomeV1

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def digest(o):return hashlib.sha256(canon(o).encode()).hexdigest()

core=UnifiedYADOCoreV1(REPO)
head=core.head
component_sources={
 'LOGIC':'runtime/yado_budget_adaptive_compositional_logic_v2.py',
 'THINKING':'runtime/yado_work_budget_adaptive_contingent_planner_v2.py',
 'INTELLIGENCE':'runtime/yado_coverage_pruned_compositional_schema_router_v3.py',
 'CODE':'runtime/yado_ambiguity_aware_program_repair_v11.py',
}
component_digests={k:sha(REPO/v) for k,v in component_sources.items()}
experience=core.experience_search(['logic','thinking','intelligence','repair','counterexample'],limit=8)
experience_digest=digest(experience)
parent=YADOEvolutionaryGenomeV1.parent_genome(
    head['canonical_head_digest'],component_digests,experience_digest=experience_digest
)
ctrl=YADOEvolutionaryGenomeV1(parent,experience_sources=experience)
run1=ctrl.evolve_once()
run2=YADOEvolutionaryGenomeV1(parent,experience_sources=experience).evolve_once()

checks={
 'parent_bound_to_current_head':parent['parent_head_digest']==head['canonical_head_digest'],
 'four_chromosomes':set(parent['chromosomes'])=={'LOGIC','THINKING','INTELLIGENCE','CODE'},
 'all_four_parent_deficits_observed':all(run1['deficits'][k].get('deficit') for k in ('LOGIC','THINKING','INTELLIGENCE','CODE')),
 'child_selected':run1['selection']=='CHILD',
 'child_mutates_all_four_chromosomes':run1['child']['mutation_count']==4,
 'novel_gene_synthesis_at_least_two':run1['child']['novel_gene_count']>=2,
 'logic_child_fresh_1':run1['fitness']['child']['LOGIC']==1.0,
 'thinking_child_fresh_1':run1['fitness']['child']['THINKING']==1.0,
 'intelligence_child_fresh_1':run1['fitness']['child']['INTELLIGENCE']==1.0,
 'code_child_fresh_1':run1['fitness']['child']['CODE']==1.0,
 'strict_positive_fitness_gain':run1['fitness']['fitness_gain']>0,
 'all_regressions_pass':run1['fitness']['all_regressions_pass'] is True,
 'child_not_promoted_automatically':run1['promotion_authorized'] is False,
 'deterministic_reproduction':run1['child']['genome_digest']==run2['child']['genome_digest'] and run1['fitness']==run2['fitness'],
 'experience_bound':len(experience)>0 and run1['child']['experience_sources']==experience,
 'generation_unchanged':head.get('generation_id')=='G2_CANDIDATE_TRCG_V1',
 'frontier_unchanged':head.get('current_frontier')=='KERNEL_G2_RAW_REPRESENTATION_V5_CANONICAL_ADMISSION_V1',
 'g3_not_started':head.get('g3_genesis_performed') is False,
}
status='PASS_SHADOW_G2_EVOLUTIONARY_GENOME_V1' if all(checks.values()) else 'WITHHOLD_G2_EVOLUTIONARY_GENOME_V1'
report={
 'schema':'yado.g2.evolutionary_genome.fresh_gate.v1',
 'status':status,'checks':checks,
 'controller':YADOEvolutionaryGenomeV1.component(),
 'parent_genome':parent,
 'evolution_run':run1,
 'reproduction':{
   'second_child_genome_digest':run2['child']['genome_digest'],
   'same_child':run1['child']['genome_digest']==run2['child']['genome_digest'],
   'same_fitness':run1['fitness']==run2['fitness'],
 },
 'experience_source_count':len(experience),
 'experience_digest':experience_digest,
 'canonical_mutation':False,'architecture_mutation':False,
 'generation_transition':False,'g3_genesis_performed':False,
 'semantic_boundary':'FRESH SHADOW EVOLUTION OF LOGIC/THINKING/INTELLIGENCE/CODE GENOMES. A CHILD MAY WIN FITNESS BUT CANNOT PROMOTE ITSELF; SEPARATE CANONICAL ADMISSION IS REQUIRED.'
}
report['receipt_sha256']=digest(report)
out=REPO/'candidates/kernel-self-generated/g2-evolutionary-genome-v1.json'
out.parent.mkdir(parents=True,exist_ok=True)
out.write_text(json.dumps(report,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')
print(json.dumps({
 'status':status,
 'checks':checks,
 'parent_fitness':run1['fitness']['parent'],
 'child_fitness':run1['fitness']['child'],
 'fitness_gain':run1['fitness']['fitness_gain'],
 'mutation_count':run1['child']['mutation_count'],
 'novel_gene_count':run1['child']['novel_gene_count'],
 'selection':run1['selection'],
 'child_genome_digest':run1['child']['genome_digest'],
 'receipt_sha256':report['receipt_sha256'],
},indent=2,sort_keys=True))
if not all(checks.values()):raise SystemExit(2)
