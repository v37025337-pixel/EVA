from __future__ import annotations
from pathlib import Path
import copy,hashlib,json,os,subprocess,sys

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
PKG=ROOT/'yado_rc8_v36'
sys.path[:0]=[str(ROOT),str(PKG)]

from yado_evolution_ledger_v2 import validate_ledger_v2,event_hash
from yado_evolutionary_genome_v1 import YADOEvolutionaryGenomeV1

HEAD=REPO/'canonical/yado-main-head-g2.json'
CORE=REPO/'canonical/yado-unified-core-v1.json'
PROV=REPO/'canonical/yado-algorithm-provenance-registry-v1.json'
LEDGER=REPO/'architecture/evolution-ledger.json'
FRESH=REPO/'candidates/kernel-self-generated/g2-evolutionary-genome-v1.json'
CANON=REPO/'canonical/yado-g2-evolutionary-genome-v1.json'
UNIFIED=ROOT/'yado_unified_core_v1.py'
OUT=ROOT/'yado_g2_evolutionary_genome_canonical_admission_v1_receipt.json'
GUARD=ROOT/'yado_canonical_invariant_guard_v1.py'

COMP='CTRL-G2-EVOLUTIONARY-GENOME-V1'
FRONT='KERNEL_G2_RAW_REPRESENTATION_V5_CANONICAL_ADMISSION_V1'
PARENTS={
 'LOGIC':'ALG-G2-BUDGET-ADAPTIVE-COMPOSITIONAL-LOGIC-V2',
 'THINKING':'ALG-G2-WORK-BUDGET-ADAPTIVE-CONTINGENT-PLANNER-V2',
 'INTELLIGENCE':'ALG-G2-COVERAGE-PRUNED-COMPOSITIONAL-SCHEMA-ROUTER-V3',
 'CODE':'ALG-G2-AMBIGUITY-AWARE-PROGRAM-REPAIR-V11',
}

def load(p):return json.loads(p.read_text(encoding='utf-8'))
def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def h(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def fsha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,o):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(o,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')
def cdig(o,field):x=copy.deepcopy(o);x.pop(field,None);return h(x)

head,core,prov,ledger,fresh=map(load,[HEAD,CORE,PROV,LEDGER,FRESH])
validate_ledger_v2(ledger)
if head.get('current_frontier')!=FRONT or ledger.get('open_deficits')!=[FRONT]:raise RuntimeError('FRONTIER_DRIFT')
if head.get('g3_genesis_performed') is not False:raise RuntimeError('G3_ALREADY_STARTED')
if fresh.get('status')!='PASS_SHADOW_G2_EVOLUTIONARY_GENOME_V1':raise RuntimeError('GENOME_FRESH_GATE_NOT_PASS')
if fresh.get('evolution_run',{}).get('selection')!='CHILD':raise RuntimeError('SHADOW_CHILD_NOT_SELECTED')
if fresh.get('evolution_run',{}).get('promotion_authorized') is not False:raise RuntimeError('FRESH_GATE_PROMOTION_BOUNDARY_BROKEN')
if COMP in head.get('active_capabilities',[]):raise RuntimeError('GENOME_CONTROLLER_ALREADY_ACTIVE')
for p in PARENTS.values():
    if p not in head.get('active_capabilities',[]):raise RuntimeError('PARENT_CAPABILITY_NOT_ACTIVE:'+p)

controller=YADOEvolutionaryGenomeV1.component()
shadow_child=fresh['evolution_run']['child']
canon_art={
 'schema':'yado.g2.evolutionary_genome.controller.canonical.v1',
 'status':'CANONICAL_ACTIVE',
 'component_id':COMP,
 'controller':controller,
 'runtime_source':'runtime/yado_evolutionary_genome_v1.py',
 'runtime_sha256':fsha(ROOT/'yado_evolutionary_genome_v1.py'),
 'fresh_gate_artifact':'candidates/kernel-self-generated/g2-evolutionary-genome-v1.json',
 'fresh_gate_receipt_sha256':fresh.get('receipt_sha256'),
 'fresh_checks':fresh.get('checks'),
 'chromosomes':['LOGIC','THINKING','INTELLIGENCE','CODE'],
 'canonical_parent_capabilities':PARENTS,
 'shadow_selected_child':{
   'genome_id':shadow_child.get('genome_id'),
   'genome_digest':shadow_child.get('genome_digest'),
   'mutation_count':shadow_child.get('mutation_count'),
   'novel_gene_count':shadow_child.get('novel_gene_count'),
   'promotion_state':shadow_child.get('promotion_state'),
 },
 'automatic_canonical_promotion':False,
 'fresh_gate_required_for_every_child':True,
 'parent_rollback_preserved':True,
 'architecture_mutation':False,
 'semantic_boundary':'CANONICAL G2 EVOLUTION CONTROLLER ONLY. IT MAY CREATE AND SELECT SHADOW CHILD GENOMES FOR LOGIC/THINKING/INTELLIGENCE/CODE, BUT CHILD GENES CANNOT BECOME CANONICAL WITHOUT A SEPARATE ADMISSION.'
}
canon_art['canonical_component_digest']=cdig(canon_art,'canonical_component_digest');write(CANON,canon_art)

# Bind controller into UnifiedYADOCoreV1 as a read/evaluate-only evolutionary entry point.
src=UNIFIED.read_text(encoding='utf-8')
import_anchor='from yado_g2_openapi_readonly_executor_v1 import G2OpenAPIReadOnlyExecutorV1\n'
import_line='from yado_evolutionary_genome_v1 import YADOEvolutionaryGenomeV1\n'
if import_line not in src:
    if import_anchor not in src:raise RuntimeError('UNIFIED_IMPORT_ANCHOR_MISSING')
    src=src.replace(import_anchor,import_anchor+import_line)
init_anchor='        self.openapi_readonly_executor_cls=G2OpenAPIReadOnlyExecutorV1\n'
if 'self.evolutionary_genome_cls=YADOEvolutionaryGenomeV1' not in src:
    if init_anchor not in src:raise RuntimeError('UNIFIED_INIT_ANCHOR_MISSING')
    src=src.replace(init_anchor,init_anchor+'        self.evolutionary_genome_cls=YADOEvolutionaryGenomeV1\n')
method_anchor='    def snapshot(self)->dict[str,Any]:\n'
methods="""    def evolutionary_parent_genome(self)->dict[str,Any]:
        component_sources={
          'LOGIC':'runtime/yado_budget_adaptive_compositional_logic_v2.py',
          'THINKING':'runtime/yado_work_budget_adaptive_contingent_planner_v2.py',
          'INTELLIGENCE':'runtime/yado_coverage_pruned_compositional_schema_router_v3.py',
          'CODE':'runtime/yado_ambiguity_aware_program_repair_v11.py',
        }
        component_digests={k:hashlib.sha256((self.repo/v).read_bytes()).hexdigest() for k,v in component_sources.items()}
        experience=self.experience_search(['logic','thinking','intelligence','repair','counterexample'],limit=8)
        parent=self.evolutionary_genome_cls.parent_genome(
            self.head['canonical_head_digest'],component_digests,experience_digest=digest(experience)
        )
        return {'parent':parent,'experience':experience}

    def evolve_cognitive_code_genome(self)->dict[str,Any]:
        state=self.evolutionary_parent_genome()
        controller=self.evolutionary_genome_cls(state['parent'],experience_sources=state['experience'])
        return controller.evolve_once()

"""
if 'def evolve_cognitive_code_genome(' not in src:
    if method_anchor not in src:raise RuntimeError('UNIFIED_SNAPSHOT_ANCHOR_MISSING')
    src=src.replace(method_anchor,methods+method_anchor)
UNIFIED.write_text(src,encoding='utf-8')
unified_sha=fsha(UNIFIED)

# Plane binding: controller is an audited control mechanism; targets remain their current canonical parents.
self_plane=next((p for p in core.get('planes',[]) if p.get('plane_id')=='SELF_AUDIT_AND_REPAIR'),None)
intel_plane=next((p for p in core.get('planes',[]) if p.get('plane_id')=='INTELLIGENCE_AND_META_SELECTION'),None)
memory_plane=next((p for p in core.get('planes',[]) if p.get('plane_id')=='MEMORY_AND_EXPERIENCE'),None)
if not self_plane or not intel_plane or not memory_plane:raise RuntimeError('REQUIRED_PLANE_MISSING')
self_plane['active_components']=sorted(set(self_plane.get('active_components',[])+[COMP]))
self_plane['responsibilities']=sorted(set(self_plane.get('responsibilities',[])+[
 'bounded_evolutionary_candidate_generation','fresh_fitness_gate_before_promotion','parent_rollback_preservation'
]))
intel_plane['responsibilities']=sorted(set(intel_plane.get('responsibilities',[])+[
 'shadow_genome_fitness_selection','multi_chromosome_evolution_selection'
]))
memory_plane['responsibilities']=sorted(set(memory_plane.get('responsibilities',[])+[
 'evolutionary_experience_inheritance','fitness_and_counterexample_lineage'
]))

core['evolutionary_genome_v1']={
 'status':'CANONICAL_ACTIVE','component_id':COMP,
 'canonical_component_digest':canon_art['canonical_component_digest'],
 'runtime_sha256':canon_art['runtime_sha256'],
 'fresh_gate_receipt_sha256':fresh.get('receipt_sha256'),
 'chromosomes':['LOGIC','THINKING','INTELLIGENCE','CODE'],
 'automatic_canonical_promotion':False,
 'fresh_gate_required_for_every_child':True,
 'parent_rollback_preserved':True,
 'latest_shadow_selected_child_digest':shadow_child.get('genome_digest'),
 'latest_shadow_mutation_count':shadow_child.get('mutation_count'),
 'latest_shadow_novel_gene_count':shadow_child.get('novel_gene_count'),
}

active_sources=set(core.get('active_runtime_sources',[]))
active_sources.add('runtime/yado_evolutionary_genome_v1.py')
core['active_runtime_sources']=sorted(active_sources)
rim=core.get('runtime_integrity_manifest')
if not isinstance(rim,dict) or not isinstance(rim.get('sources'),dict):raise RuntimeError('RUNTIME_INTEGRITY_MANIFEST_MISSING')
rim['sources']={rel:fsha(REPO/rel) for rel in core['active_runtime_sources']}
rim['manifest_digest']=h(rim['sources'])
core['runtime_sha256']=unified_sha

prev=head['canonical_head_digest']
prov['current_g2_binding'].update({
 'current_execution_label':'G2_UNIFIED_FABRIC_V2_EVOLUTIONARY_GENOME_CONTROLLER_ACTIVE',
 'frontier':FRONT,
 'evolutionary_genome_controller':COMP,
 'evolutionary_genome_source_sha256':canon_art['runtime_sha256'],
 'evolutionary_genome_fresh_receipt_sha256':fresh.get('receipt_sha256'),
 'latest_shadow_child_genome_digest':shadow_child.get('genome_digest'),
 'automatic_child_promotion':False,
})
prov['registry_digest']=cdig(prov,'registry_digest');write(PROV,prov)

core['algorithm_provenance_registry_digest']=prov['registry_digest']
core['current_frontier']=FRONT
core['core_digest']=cdig(core,'core_digest');write(CORE,core)

head['active_capabilities']=sorted(set(head.get('active_capabilities',[])+[COMP]))
head['new_capabilities']=sorted(set(head.get('new_capabilities',[])+[COMP]))
head['evolutionary_genome_v1']={
 'status':'CANONICAL_ACTIVE','component_id':COMP,
 'canonical_component_digest':canon_art['canonical_component_digest'],
 'fresh_gate_receipt_sha256':fresh.get('receipt_sha256'),
 'automatic_canonical_promotion':False,
 'latest_shadow_selected_child_digest':shadow_child.get('genome_digest'),
}
head['algorithm_provenance_registry']['registry_digest']=prov['registry_digest']
head['algorithm_provenance_registry']['current_execution_label']=prov['current_g2_binding']['current_execution_label']
head['unified_core']['algorithm_provenance_registry_digest']=prov['registry_digest']
head['unified_core']['core_digest']=core['core_digest']
head['unified_core']['runtime_sha256']=unified_sha
head['unified_core']['runtime_integrity_manifest_digest']=rim['manifest_digest']
head['current_frontier']=FRONT
head['canonical_head_digest']=cdig(head,'canonical_head_digest');write(HEAD,head)

ledger['current_head_digest']=head['canonical_head_digest']
run_id=str(os.getenv('GITHUB_RUN_ID') or 'LOCAL')
receipt={
 'schema':'yado.g2.evolutionary_genome.controller.canonical_admission.receipt.v1',
 'status':'PASS_G2_EVOLUTIONARY_GENOME_CONTROLLER_CANONICAL_ADMISSION_V1',
 'component_id':COMP,
 'active_capability_count_after':len(head['active_capabilities']),
 'fresh_gate_receipt_sha256':fresh.get('receipt_sha256'),
 'latest_shadow_child_genome_digest':shadow_child.get('genome_digest'),
 'shadow_child_selected':fresh['evolution_run']['selection'],
 'automatic_canonical_promotion':False,
 'canonical_parent_capabilities':PARENTS,
 'previous_head_digest':prev,'new_head_digest':head['canonical_head_digest'],
 'frontier_unchanged':FRONT,'canonical_mutation':True,'canonical_mechanism_mutation':True,
 'architecture_mutation':False,'generation_transition':False,'g3_genesis_performed':False,
 'semantic_boundary':'SAME-G2 ADMISSION OF THE EVOLUTION CONTROLLER ONLY. WINNING SHADOW CHILD GENES REMAIN NON-CANONICAL UNTIL A SEPARATE ADMISSION.'
}
receipt['receipt_sha256']=h(receipt);write(OUT,receipt)
e={
 'index':len(ledger['events']),
 'event_id':f"E{len(ledger['events'])+1:04d}_G2_EVOLUTIONARY_GENOME_CONTROLLER_CANONICAL_ADMISSION_V1",
 'event_type':'G2_EVOLUTIONARY_GENOME_CONTROLLER_CANONICAL_ADMISSION','status':'PASS_CANONICAL',
 'generation':ledger['current_head'],'deficit':'NO_BOUND_SELF_EVOLUTION_CONTROLLER_FOR_LOGIC_THINKING_INTELLIGENCE_CODE',
 'effect':f"ADDED={COMP}; CHROMOSOMES=LOGIC,THINKING,INTELLIGENCE,CODE; AUTO_PROMOTION=False; ACTIVE_CAPS={len(head['active_capabilities'])}; FRONTIER_UNCHANGED={FRONT}",
 'source_path':f'receipts/yado-g2-evolutionary-genome-controller-canonical-admission-v1-run-{run_id}.json',
 'source_digest':receipt['receipt_sha256'],'run_id':run_id,'parent_event_hash':ledger['tail_event_hash'],
 'canonical_mutation':True,'canonical_mechanism_mutation':True,'architecture_mutation':False,'promotion_applied':False,'generation_transition':False,
 'previous_head_digest':prev,'new_head_digest':head['canonical_head_digest']
}
e['event_hash']=event_hash(e);ledger['events'].append(e);ledger['event_count']=len(ledger['events']);ledger['tail_event_hash']=e['event_hash']
ledger['ledger_digest']=h({k:v for k,v in ledger.items() if k!='ledger_digest'})
validate_ledger_v2(ledger);write(LEDGER,ledger)

post=subprocess.run([sys.executable,str(GUARD)],cwd=REPO,capture_output=True,text=True,timeout=90)
if post.returncode!=0:raise RuntimeError('POST_GENOME_CANONICAL_GUARD_FAILED:'+post.stdout[-6000:]+post.stderr[-2000:])
print(json.dumps({
 'status':receipt['status'],'active_capability_count_after':len(head['active_capabilities']),
 'component_id':COMP,'shadow_child':shadow_child.get('genome_digest'),
 'automatic_canonical_promotion':False,'frontier':FRONT
},indent=2,sort_keys=True))
