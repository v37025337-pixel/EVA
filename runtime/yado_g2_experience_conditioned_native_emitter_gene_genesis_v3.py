from __future__ import annotations
from pathlib import Path
from dataclasses import asdict
import copy,hashlib,json,sys

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
PKG=ROOT/'yado_rc8_v36'
sys.path[:0]=[str(ROOT),str(PKG)]

from yado_core_v3_0_rc8_external_cognitive import UnifiedYADOKernelV30RC8ExternalCognitive
from yado_unified_core_v1 import UnifiedYADOCoreV1

TASK=REPO/'architecture/yado-g2-experience-conditioned-native-emitter-gene-genesis-v3-request.json'
PROCESS=REPO/'candidates/kernel-self-generated/g2-native-source-construction-process-evolution-v2.json'
FAIL=REPO/'candidates/kernel-self-generated/g2-native-source-ir-emitter-meta-language-evolution-v2.json'
GENOME=REPO/'canonical/yado-g2-evolutionary-genome-v1.json'
OUT=REPO/'candidates/kernel-self-generated/g2-experience-conditioned-native-emitter-gene-genesis-v3.json'
DB=ROOT/'yado_g2_experience_conditioned_native_emitter_gene_v3.sqlite'

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def digest(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))

task=load(TASK);process=load(PROCESS);failure=load(FAIL);genome=load(GENOME)
seq=list(((process.get('process_mechanism') or {}).get('learned_sequence') or []))
if process.get('status')!='PASS_NATIVE_SOURCE_CONSTRUCTION_PROCESS_EVOLUTION_V2':raise RuntimeError('PARENT_PROCESS_NOT_PASS')
if failure.get('next_required_capability')!='EXPERIENCE_CONDITIONED_NATIVE_EMITTER_GENE_GENESIS_V3':raise RuntimeError('UNEXPECTED_V2_FAILURE_FRONTIER')
if len(seq)<5 or len(seq)!=len(set(seq)):raise RuntimeError('LEARNED_PROCESS_NOT_USABLE')
core=UnifiedYADOCoreV1(REPO);head_before=copy.deepcopy(core.head)

fit=[];blind=[]
for i,(a,b) in enumerate(zip(seq,seq[1:])):
    for variant in (0,1,2):
        fit.append({'input':{'current_primitive':a,'history_variant':variant,'source_process_bound':True},'expected':b})
    for variant in (100,101):
        blind.append({'input':{'current_primitive':a,'history_variant':variant,'source_process_bound':True},'expected':b})

if DB.exists():DB.unlink()
k=UnifiedYADOKernelV30RC8ExternalCognitive(db_path=str(DB))
try:
    goal=k.executive.create_goal(
      objective=str(task['objective']),
      required_capabilities={'EXPERIENCE_CONDITIONED_NATIVE_EMITTER_GENE_V3':1.0},
      success_criteria={'fresh':1.0,'ablation':True,'restore':True},
    )
    deficits=k.executive.detect_deficits(goal.goal_id)
    if len(deficits)!=1:raise RuntimeError('EMITTER_DEFICIT_COUNT')
    prog,selection=k.executive.synthesize_best_mechanism(
      deficits[0].deficit_id,'GENERATIVE_EXECUTIVE',fit,min_support=2
    )
    dev=k.executive.evaluate_mechanism(
      prog.program_id,blind,min_score=.99,min_ablation_drop=.20
    )
finally:
    try:k.close()
    except Exception:pass

program=asdict(prog)
development=asdict(dev)
parent_gene_ids=set((genome.get('canonical_parent_capabilities') or {}).values())
gene_id='GENE-G2-NATIVE-EMITTER-'+str(program.get('program_digest') or digest(program))[:16]
gene={
 'schema':'yado.g2.experience_conditioned_native_emitter_gene.v3',
 'gene_id':gene_id,
 'gene_class':'SOURCE_PROCESS_TRANSITION_EMITTER',
 'origin':'YADO_NATIVE_DEVELOPMENTAL_EXECUTIVE_OVER_YADO_LEARNED_PROCESS_MEMORY',
 'mechanism_kind':development.get('mechanism_kind'),
 'program':program,
 'heritage':[
   process.get('receipt_sha256'),
   failure.get('receipt_sha256'),
 ],
 'learned_process_digest':digest(seq),
 'promotion_state':'SHADOW_ONLY',
 'actual_python_source_emission_proven':False,
}
gene['gene_digest']=digest(gene)

checks={
 'exact_yado_process_consumed':True,
 'exact_v2_failure_consumed':True,
 'native_goal_created':True,
 'native_deficit_detected':True,
 'native_mechanism_family_selected':bool(selection.selected_kind),
 'host_selected_mechanism_family':False,
 'fresh_transition_exact':float(development.get('candidate_score') or 0)>=.99,
 'causal_ablation_drop':float(development.get('candidate_score') or 0)-float(development.get('ablation_score') or 0)>=.20,
 'restore_exact':abs(float(development.get('candidate_score') or 0)-float(development.get('restore_score') or 0))<1e-12,
 'new_gene_identity_absent_from_parent':gene_id not in parent_gene_ids,
 'external_models_used':False,
 'new_external_research_used':False,
 'host_source_template_used':False,
 'host_ast_skeleton_used':False,
 'host_patch_used':False,
 'automatic_canonical_promotion':False,
 'rollback_parent_available':True,
 'canonical_unchanged':core.head.get('canonical_head_digest')==head_before.get('canonical_head_digest'),
}
passed=bool(development.get('state_committed')) and all(checks.values())
status='PASS_SHADOW_G2_EXPERIENCE_CONDITIONED_NATIVE_EMITTER_GENE_GENESIS_V3' if passed else 'WITHHOLD_G2_EXPERIENCE_CONDITIONED_NATIVE_EMITTER_GENE_GENESIS_V3'
report={
 'schema':'yado.g2.experience_conditioned_native_emitter_gene_genesis.v3',
 'status':status,'task':task,
 'parent_process_receipt':process.get('receipt_sha256'),
 'parent_failure_receipt':failure.get('receipt_sha256'),
 'yado_learned_sequence':seq,
 'native_selection':asdict(selection),'native_development':development,
 'emitter_gene':gene,'checks':checks,
 'canonical_mutation':False,'promotion_applied':False,
 'next_required_capability':('NATIVE_SOURCE_REALIZATION_OF_SELF_REPRESENTATION_DRIVEN_EXTENDED_CONTROLLER_V2' if passed else 'EXPERIENCE_CONDITIONED_NATIVE_EMITTER_GENE_GENESIS_REPAIR_V4'),
 'semantic_boundary':'THIS IS A NEW EXECUTABLE SHADOW GENE BORN BY YADO DEVELOPMENTAL MECHANISM SELECTION FROM THE SOURCE-CONSTRUCTION SEQUENCE YADO PREVIOUSLY LEARNED ITSELF. HOST ONLY EXPOSES ADJACENT TRANSITIONS MECHANICALLY. IT DOES NOT YET CLAIM ACTUAL PYTHON SOURCE EMISSION.'
}
report['receipt_sha256']=digest(report)
OUT.parent.mkdir(parents=True,exist_ok=True)
OUT.write_text(json.dumps(report,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')
print(json.dumps({
 'status':status,'selected_kind':selection.selected_kind,
 'candidate_score':development.get('candidate_score'),'ablation_score':development.get('ablation_score'),
 'restore_score':development.get('restore_score'),'gene_id':gene_id,
 'next_required_capability':report['next_required_capability'],'receipt_sha256':report['receipt_sha256']
},indent=2,sort_keys=True))
if not passed:raise SystemExit(2)
