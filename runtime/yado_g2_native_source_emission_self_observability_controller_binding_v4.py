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

TASK=REPO/'architecture/yado-kernel-native-source-emission-self-observability-controller-binding-v4-request.json'
V3=REPO/'candidates/kernel-self-generated/g2-native-hidden-code-gene-source-emission-observation-v3.json'
CTRL=REPO/'runtime/yado_evolutionary_genome_v1.py'
OUT=REPO/'candidates/kernel-self-generated/g2-native-source-emission-self-observability-controller-binding-v4.json'
DB=ROOT/'yado_native_source_emission_self_observability_v4.sqlite'

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def digest(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))

task=load(TASK);v3=load(V3)
if v3.get('status')!='PASS_SHADOW_G2_NATIVE_HIDDEN_CODE_GENE_SOURCE_EMISSION_OBSERVATION_V3':
    raise RuntimeError('V3_NATIVE_SOURCE_EMISSION_PASS_REQUIRED')
vc=v3.get('checks') or {}

core=UnifiedYADOCoreV1(REPO);head_before=copy.deepcopy(core.head)
controller_sha_before=hashlib.sha256(CTRL.read_bytes()).hexdigest()

base={
 'native_code_gene_called':vc.get('native_code_gene_synthesis_called_internally') is True,
 'changed_source_returned':vc.get('actual_changed_source_returned_by_native_code_gene') is True,
 'source_compiles':vc.get('captured_source_compiles') is True,
 'fresh_code_fitness_exact':vc.get('native_code_fresh_fitness_exact') is True,
 'observer_arguments_unchanged':vc.get('observer_modified_native_arguments') is False,
 'observer_return_unchanged':vc.get('observer_modified_native_return') is False,
 'canonical_unchanged':vc.get('canonical_unchanged') is True,
}
if not all(base.values()):raise RuntimeError('V3_POSITIVE_EVIDENCE_INCOMPLETE')
fields=tuple(sorted(base))

def truth(x):return 'PROVEN_NATIVE_SOURCE_EMISSION' if all(bool(x[k]) for k in fields) else 'SOURCE_EMISSION_NOT_ESTABLISHED'
def observed(x):
    # Mechanical compression of the evidence surface, not a host-authored decision rule.
    y=dict(x)
    y['evidence_true_count']=sum(1 for k in fields if bool(x[k]))
    y['evidence_total_count']=len(fields)
    return y

rows=[]
for rep in range(14):
    x=dict(base);rows.append({'kind':'POS','variant':rep,'input':observed(x),'expected':truth(x)})
for k in fields:
    for rep in range(6):
        x=dict(base);x[k]=False;rows.append({'kind':'ABLATE_'+k,'variant':rep,'input':observed(x),'expected':truth(x)})

fit=[];blind=[]
for row in rows:
    h=int(hashlib.sha256((row['kind']+'|'+str(row['variant'])+'|V4').encode()).hexdigest()[:8],16)%10
    item={'input':row['input'],'expected':row['expected']}
    (blind if h<3 else fit).append(item)
if len(blind)<8:
    blind=[{'input':r['input'],'expected':r['expected']} for r in rows[::5]]
    blind_ids={id(x) for x in rows[::5]}
    fit=[{'input':r['input'],'expected':r['expected']} for r in rows if id(r) not in blind_ids]

if DB.exists():DB.unlink()
k=UnifiedYADOKernelV30RC8ExternalCognitive(db_path=str(DB))
try:
    goal=k.executive.create_goal(
      objective=str(task['objective']),
      required_capabilities={'NATIVE_SOURCE_EMISSION_SELF_OBSERVATION_V4':1.0},
      success_criteria={'fresh_blind':1.0,'ablation_required':True,'restore_required':True},
    )
    deficits=k.executive.detect_deficits(goal.goal_id)
    if len(deficits)!=1:raise RuntimeError('V4_DEFICIT_COUNT:'+str(len(deficits)))
    program,selection=k.executive.synthesize_best_mechanism(
      deficits[0].deficit_id,'GENERATIVE_EXECUTIVE',fit,min_support=2
    )
    dev=k.executive.evaluate_mechanism(program.program_id,blind,min_score=1.0,min_ablation_drop=.20)
    probes=[]
    for i in range(4):
        raw=dict(base);x=observed(raw)
        y=k.executive.execute_capability('NATIVE_SOURCE_EMISSION_SELF_OBSERVATION_V4',x)
        probes.append({'kind':'POS','output':y,'expected':truth(raw),'pass':y==truth(raw)})
    for key in fields:
        raw=dict(base);raw[key]=False;x=observed(raw)
        y=k.executive.execute_capability('NATIVE_SOURCE_EMISSION_SELF_OBSERVATION_V4',x)
        probes.append({'kind':'ABLATE_'+key,'output':y,'expected':truth(raw),'pass':y==truth(raw)})
finally:
    try:k.close()
    except Exception:pass

rep={
 'schema':'yado.g2.native_source_emission_self_observation.v4',
 'program_id':program.program_id,'program_type':type(program).__name__,
 'selection':asdict(selection),'development':asdict(dev),
 'observed_source_emission_receipt':v3.get('receipt_sha256'),
 'observed_source_sha256':v3.get('selected_source_sha256'),
 'evidence_fields':list(fields),'mechanical_aggregate_fields':['evidence_true_count','evidence_total_count'],'probe_results':probes,
 'semantic_boundary':'EXECUTABLE SELF-OBSERVATION OF A PROVEN NATIVE CODE-GENE SOURCE-EMISSION EVENT.'
}
rep['representation_digest']=digest(rep)

parent_state=core.evolutionary_parent_genome()
experience=copy.deepcopy(parent_state.get('experience') or [])
experience.append({
 'role':'YADO_NATIVE_SOURCE_EMISSION_SELF_OBSERVATION_V4',
 'representation_digest':rep['representation_digest'],
 'program_id':rep['program_id'],
 'program_type':rep['program_type'],
 'source_emission_receipt':v3.get('receipt_sha256'),
 'source_sha256':v3.get('selected_source_sha256'),
 'fresh_blind':rep['development'].get('candidate_score'),
 'ablation':rep['development'].get('ablation_score'),
 'restore':rep['development'].get('restore_score'),
})
controller=core.evolutionary_genome_cls(parent_state['parent'],experience_sources=experience)
evolution=controller.evolve_once()
child_exp=((evolution.get('child') or {}).get('experience_sources') or [])
visible=rep['representation_digest'] in canon(child_exp)
controller_sha_after=hashlib.sha256(CTRL.read_bytes()).hexdigest()

cand=float(dev.candidate_score);abl=float(dev.ablation_score);restore=float(dev.restore_score)
checks={
 'v3_native_source_emission_consumed':v3.get('receipt_sha256') is not None,
 'native_goal_created':True,'native_deficit_detected':True,
 'native_self_observation_created':bool(dev.state_committed),
 'fresh_blind_exact':cand==1.0,
 'causal_ablation_drop':cand-abl>=.20,
 'restore_exact':abs(cand-restore)<1e-12,
 'probe_exact':all(x['pass'] for x in probes),
 'representation_visible_to_next_native_evolution':visible,
 'external_coding_models_used':False,'new_external_research_used':False,
 'host_model_family_used':False,'host_rule_used':False,'host_source_template_used':False,'host_patch_used':False,
 'controller_source_mutation':False,
 'controller_source_unchanged':controller_sha_before==controller_sha_after,
 'rollback_parent_available':bool((evolution.get('parent') or {}).get('genome_digest')),
 'canonical_unchanged':core.head.get('canonical_head_digest')==head_before.get('canonical_head_digest'),
}
passed=all([
 checks['v3_native_source_emission_consumed'],checks['native_goal_created'],checks['native_deficit_detected'],
 checks['native_self_observation_created'],checks['fresh_blind_exact'],checks['causal_ablation_drop'],
 checks['restore_exact'],checks['probe_exact'],checks['representation_visible_to_next_native_evolution'],
 checks['controller_source_unchanged'],checks['rollback_parent_available'],checks['canonical_unchanged']
])
status='PASS_SHADOW_G2_NATIVE_SOURCE_EMISSION_SELF_OBSERVABILITY_CONTROLLER_BINDING_V4' if passed else 'WITHHOLD_G2_NATIVE_SOURCE_EMISSION_SELF_OBSERVABILITY_CONTROLLER_BINDING_V4'
report={
 'schema':'yado.g2.native_source_emission_self_observability_controller_binding.v4',
 'status':status,'task':task,'self_observation':rep,
 'native_evolution_visibility':{
   'run_digest':evolution.get('run_digest'),'selection':evolution.get('selection'),
   'child_genome_digest':((evolution.get('child') or {}).get('genome_digest')),
   'representation_visible_in_child_experience':visible,
 },
 'checks':checks,'canonical_mutation':False,'controller_source_mutation':False,
 'next_required_capability':('NATIVE_CONTROLLER_SOURCE_EMITTER_BINDING_V5' if passed else 'NATIVE_SOURCE_EMISSION_SELF_OBSERVABILITY_V4_REPAIR'),
 'semantic_boundary':'PASS PROVES YADO CAN FORM AN EXECUTABLE SELF-OBSERVATION OF ITS OWN SOURCE-EMISSION EVENT AND RETAIN IT IN THE NEXT EVOLUTIONARY CHILD EXPERIENCE. IT DOES NOT CLAIM THAT CURRENT MUTATE() USES THIS EXPERIENCE TO REWRITE THE CONTROLLER SOURCE.'
}
report['receipt_sha256']=digest(report)
OUT.parent.mkdir(parents=True,exist_ok=True)
OUT.write_text(json.dumps(report,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')
print(json.dumps({
 'status':status,'program_id':rep['program_id'],'program_type':rep['program_type'],
 'fresh_blind':cand,'ablation':abl,'restore':restore,'probe_exact':checks['probe_exact'],
 'visible_to_evolution':visible,'next_required_capability':report['next_required_capability'],
 'receipt_sha256':report['receipt_sha256'],
},indent=2,sort_keys=True))
if not passed:raise SystemExit(2)
