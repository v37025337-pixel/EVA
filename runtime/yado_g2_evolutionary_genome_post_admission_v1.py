from __future__ import annotations
from pathlib import Path
import hashlib,json,sys

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
PKG=ROOT/'yado_rc8_v36'
sys.path[:0]=[str(ROOT),str(PKG)]

from yado_unified_core_v1 import UnifiedYADOCoreV1

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def digest(o):return hashlib.sha256(canon(o).encode()).hexdigest()

core=UnifiedYADOCoreV1(REPO)
active=set(core.head.get('active_capabilities',[]))
parents={
 'ALG-G2-BUDGET-ADAPTIVE-COMPOSITIONAL-LOGIC-V2',
 'ALG-G2-WORK-BUDGET-ADAPTIVE-CONTINGENT-PLANNER-V2',
 'ALG-G2-COVERAGE-PRUNED-COMPOSITIONAL-SCHEMA-ROUTER-V3',
 'ALG-G2-AMBIGUITY-AWARE-PROGRAM-REPAIR-V11',
}
state=core.evolutionary_parent_genome()
run1=core.evolve_cognitive_code_genome()
run2=core.evolve_cognitive_code_genome()
child_ids={x['gene_id'] for x in run1['child']['chromosomes'].values()}
checks={
 'controller_active':'CTRL-G2-EVOLUTIONARY-GENOME-V1' in active,
 'parent_genome_bound_current_head':state['parent']['parent_head_digest']==core.head['canonical_head_digest'],
 'canonical_parents_still_active':parents <= active,
 'shadow_child_selected':run1['selection']=='CHILD',
 'shadow_child_not_promoted':run1['promotion_authorized'] is False,
 'four_chromosomes_mutated':run1['child']['mutation_count']==4,
 'three_novel_genes':run1['child']['novel_gene_count']>=3,
 'child_fitness_all_one':all(run1['fitness']['child'][k]==1.0 for k in ('LOGIC','THINKING','INTELLIGENCE','CODE')),
 'positive_fitness_gain':run1['fitness']['fitness_gain']>0,
 'all_regressions_pass':run1['fitness']['all_regressions_pass'] is True,
 'child_genes_not_active':not (child_ids & active),
 'deterministic_current_head_reproduction':run1['child']['genome_digest']==run2['child']['genome_digest'] and run1['fitness']==run2['fitness'],
 'experience_inherited':len(state['experience'])>0 and run1['child']['experience_sources']==state['experience'],
 'frontier_preserved':core.head.get('current_frontier')=='KERNEL_G2_RAW_REPRESENTATION_V5_CANONICAL_ADMISSION_V1',
 'g3_not_started':core.head.get('g3_genesis_performed') is False,
}
status='PASS_G2_EVOLUTIONARY_GENOME_POST_ADMISSION_V1' if all(checks.values()) else 'WITHHOLD_G2_EVOLUTIONARY_GENOME_POST_ADMISSION_V1'
report={
 'schema':'yado.g2.evolutionary_genome.post_admission.v1','status':status,
 'checks':checks,
 'current_parent_genome_digest':state['parent']['genome_digest'],
 'current_shadow_child_genome_digest':run1['child']['genome_digest'],
 'child_gene_ids':sorted(child_ids),
 'fitness':run1['fitness'],
 'selection':run1['selection'],
 'promotion_authorized':run1['promotion_authorized'],
 'active_capability_count':len(active),
 'canonical_mutation':False,'architecture_mutation':False,
 'generation_transition':False,'g3_genesis_performed':False,
 'semantic_boundary':'POST-ADMISSION VERIFICATION OF THE CANONICAL EVOLUTION CONTROLLER. CHILD GENES REMAIN SHADOW AND CANONICAL PARENT CAPABILITIES REMAIN ACTIVE.'
}
report['receipt_sha256']=digest(report)
out=REPO/'audits/yado-g2-evolutionary-genome-post-admission-v1.json'
out.parent.mkdir(parents=True,exist_ok=True)
out.write_text(json.dumps(report,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')
print(json.dumps(report,indent=2,sort_keys=True,default=str))
if not all(checks.values()):raise SystemExit(2)
