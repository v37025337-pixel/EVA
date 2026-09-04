from __future__ import annotations
from pathlib import Path
import hashlib,json,sys

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
PKG=ROOT/'yado_rc8_v36'
sys.path[:0]=[str(ROOT),str(PKG)]

from yado_unified_core_v1 import UnifiedYADOCoreV1
from yado_evolutionary_genome_v1 import YADOEvolutionaryGenomeV1

TASK=REPO/'architecture/yado-kernel-native-source-constructor-genesis-v1-request.json'
GENE=REPO/'candidates/kernel-self-generated/g2-native-self-created-evidence-binder-gene-v1.json'
OUT=REPO/'candidates/kernel-self-generated/g2-native-source-constructor-genesis-v1.json'

def canon(o): return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def digest(o): return hashlib.sha256(canon(o).encode()).hexdigest()
def load(p): return json.loads(Path(p).read_text(encoding='utf-8'))

task=load(TASK)
gene=load(GENE)
core=UnifiedYADOCoreV1(REPO)

head_before=core.head.get('canonical_head_digest')
parent=core.evolutionary_parent_genome()
evolution=core.evolve_cognitive_code_genome()

# Observer-only capability inspection: do not provide a source seed/template, target file,
# patch, external model, or substitute emitter. A PASS requires YADO's current native
# mechanisms themselves to expose an actual candidate source artifact.
native_methods=sorted(
    x for x in dir(core)
    if any(tok in x.lower() for tok in ('repair','synth','evol','code','program'))
    and callable(getattr(core,x,None))
)

child=((evolution.get('child') or {}).get('chromosomes') or {})
code_gene=child.get('CODE') or {}
selection=evolution.get('selection')
fitness=evolution.get('fitness') or {}

# A native source constructor must return executable source without receiving
# a host-written solution template. Existing repair_program requires source input;
# evolutionary genome currently returns a gene description rather than source bytes.
repair_requires_source=True
evolution_source=evolution.get('candidate_source') or code_gene.get('source') or code_gene.get('candidate_source')
native_source_produced=isinstance(evolution_source,str) and bool(evolution_source.strip())

checks={
  'source_gene_is_yado_native': gene.get('external_model_generated') is False and gene.get('self_created_model') is True,
  'external_models_used': False,
  'host_patch_used': False,
  'host_target_file_selected': False,
  'host_solution_template_used': False,
  'native_evolution_executed': bool(evolution.get('run_digest')),
  'native_code_gene_present': bool(code_gene.get('gene_id')),
  'native_seedless_source_constructor_present': native_source_produced,
  'candidate_source_produced_by_yado': native_source_produced,
  'canonical_unchanged': core.head.get('canonical_head_digest')==head_before,
}

status='PASS_SHADOW_G2_NATIVE_SOURCE_CONSTRUCTOR_GENESIS_V1' if all(checks.values()) else 'WITHHOLD_G2_NATIVE_SOURCE_CONSTRUCTOR_GENESIS_V1'
next_required=None if status.startswith('PASS_SHADOW') else 'NATIVE_SEEDLESS_SOURCE_CONSTRUCTOR_GENESIS_V1'

report={
  'schema':'yado.g2.native_source_constructor_genesis.v1',
  'status':status,
  'task':task,
  'source_gene':{
    'gene_id':gene.get('gene_id'),'gene_digest':gene.get('gene_digest'),
    'selected_native_route':gene.get('selected_native_route'),
    'selected_algorithm':gene.get('selected_algorithm'),
  },
  'native_capability_inventory':{
    'core_methods':native_methods,
    'repair_program_requires_source_seed':repair_requires_source,
    'evolutionary_genome_component':YADOEvolutionaryGenomeV1.component(),
  },
  'native_evolution':{
    'selection':selection,
    'code_gene':code_gene,
    'fitness':fitness,
    'run_digest':evolution.get('run_digest'),
  },
  'candidate_source':evolution_source if native_source_produced else None,
  'checks':checks,
  'next_required_capability':next_required,
  'canonical_mutation':False,
  'semantic_boundary':'STRICT NATIVE SOURCE-LEVEL MILESTONE. NO EXTERNAL MODEL, HOST PATCH, HOST TARGET, OR HOST SOLUTION TEMPLATE IS ALLOWED. THIS RUN ASKS WHETHER CURRENT YADO NATIVE CODE/EVOLUTION SUBSTRATES CAN THEMSELVES MATERIALIZE SOURCE. IF THEY ONLY PRODUCE A MODEL/GENE OR REQUIRE A HOST SOURCE SEED, THE RESULT MUST WITHHOLD.'
}
report['receipt_sha256']=digest(report)
OUT.parent.mkdir(parents=True,exist_ok=True)
OUT.write_text(json.dumps(report,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')
print(json.dumps({
  'status':status,
  'native_evolution_selection':selection,
  'code_gene_id':code_gene.get('gene_id'),
  'candidate_source_produced_by_yado':native_source_produced,
  'next_required_capability':next_required,
  'checks':checks,
  'receipt_sha256':report['receipt_sha256'],
},indent=2,sort_keys=True,default=str))
if status!='PASS_SHADOW_G2_NATIVE_SOURCE_CONSTRUCTOR_GENESIS_V1':
    raise SystemExit(2)
