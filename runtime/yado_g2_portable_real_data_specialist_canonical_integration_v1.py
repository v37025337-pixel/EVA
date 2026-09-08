from __future__ import annotations

from pathlib import Path
import copy
import hashlib
import json
import os
import py_compile
import random
import subprocess
import sys

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
sys.path.insert(0,str(ROOT))

from yado_evolution_ledger_v2 import validate_ledger_v2,event_hash
from yado_g2_experience_conditioned_cognitive_layer_v4 import G2ExperienceConditionedCognitiveLayerV4
from yado_g2_experience_conditioned_cognitive_layer_v5 import G2ExperienceConditionedCognitiveLayerV5
from yado_organ_runtime_native_v1 import tree_predict
from yado_cognitive_growth_runtime_v1 import plan_multicontext

HEAD=REPO/'canonical/yado-main-head-g2.json'
CORE=REPO/'canonical/yado-unified-core-v1.json'
PROV=REPO/'canonical/yado-algorithm-provenance-registry-v1.json'
LEDGER=REPO/'architecture/evolution-ledger.json'
V4=REPO/'canonical/yado-g2-experience-conditioned-cognitive-layer-v4.json'
V5=REPO/'canonical/yado-g2-experience-conditioned-cognitive-layer-v5.json'
CAND=REPO/'candidates/kernel-self-generated/g2-portable-usgs-real-data-specialist-repair-v1.json'
READMIT=REPO/'receipts/yado-g2-portable-real-data-specialist-readmission-repair-v3-run-34223065053.json'
REQ=REPO/'architecture/yado-g2-portable-real-data-specialist-canonical-integration-v1-request.json'
UNIFIED=REPO/'runtime/yado_unified_core_v1.py'
MODULE=REPO/'runtime/yado_g2_unified_module_kernel_v1.py'
MODULE_GATE=REPO/'runtime/yado_g2_unified_module_kernel_fresh_gate_v1.py'
POST_AUDIT=REPO/'runtime/yado_g2_post_module_full_integrity_v1.py'
V5SRC=REPO/'runtime/yado_g2_experience_conditioned_cognitive_layer_v5.py'
GUARD=REPO/'runtime/yado_canonical_invariant_guard_v1.py'
OUT=ROOT/'yado_g2_portable_real_data_specialist_canonical_integration_v1_receipt.json'

OLD='RUNTIME-G2-EXPERIENCE-CONDITIONED-COGNITIVE-LAYER-V4'
NEW='RUNTIME-G2-EXPERIENCE-CONDITIONED-COGNITIVE-LAYER-V5'
FRONT='KERNEL_G2_RAW_REPRESENTATION_V4_ROBUSTNESS_SELF_EVOLUTION_V2'


def load(p):
    return json.loads(Path(p).read_text(encoding='utf-8'))

def canon(o):
    return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)

def digest(o):
    return hashlib.sha256(canon(o).encode()).hexdigest()

def fsha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def cdig(o,field):
    x=copy.deepcopy(o);x.pop(field,None);return digest(x)

def write(p,o):
    Path(p).parent.mkdir(parents=True,exist_ok=True)
    Path(p).write_text(json.dumps(o,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')

head=load(HEAD);core=load(CORE);prov=load(PROV);ledger=load(LEDGER);v4=load(V4);cand=load(CAND);readmit=load(READMIT);req=load(REQ)
validate_ledger_v2(ledger)

if req.get('expected_head_digest')!=head.get('canonical_head_digest'):raise RuntimeError('STALE_HEAD')
if req.get('expected_frontier')!=FRONT or head.get('current_frontier')!=FRONT:raise RuntimeError('FRONTIER_DRIFT')
if ledger.get('open_deficits')!=[FRONT]:raise RuntimeError('LEDGER_FRONTIER_DRIFT')
if OLD not in head.get('active_capabilities',[]):raise RuntimeError('V4_NOT_ACTIVE')
if NEW in head.get('active_capabilities',[]):raise RuntimeError('V5_ALREADY_ACTIVE')
if v4.get('status')!='CANONICAL_ACTIVE':raise RuntimeError('V4_CANONICAL_PARENT_REQUIRED')
if cand.get('status')!='SHADOW_READY':raise RuntimeError('PORTABLE_CANDIDATE_NOT_READY')
if readmit.get('status')!='PASS_SHADOW_G2_PORTABLE_REAL_DATA_SPECIALIST_READMISSION_REPAIR_V3':raise RuntimeError('V3_READMISSION_PASS_REQUIRED')
if readmit.get('candidate_digest')!=cand.get('candidate_digest'):raise RuntimeError('READMISSION_CANDIDATE_MISMATCH')
if not all((readmit.get('checks') or {}).values()):raise RuntimeError('READMISSION_CHECKS_NOT_ALL_TRUE')
if head.get('g3_genesis_performed') is not False or core.get('g3_genesis_performed') is not False:raise RuntimeError('G3_ALREADY_STARTED')

portable=copy.deepcopy(cand)
portable['readmission_receipt_sha256']=readmit.get('receipt_sha256')
portable['readmission_status']=readmit.get('status')
portable['readmission_metrics']=copy.deepcopy(readmit.get('metrics'))
portable['canonical_route_aliases']=[cand.get('task'),cand.get('parent_task')]
portable['promotion_state']='CANONICAL_VIA_V5'
portable['automatic_canonical_promotion']=False

art={
  'schema':'yado.g2.experience_conditioned_cognitive_layer.canonical.v5',
  'status':'SHADOW_READY',
  'component_id':NEW,
  'parent_component':OLD,
  'rollback_parent_component':OLD,
  'parent_v4':copy.deepcopy(v4),
  'portable_real_data_specialists':{'LOGIC':portable},
  'portable_specialist_candidate_digest':cand.get('candidate_digest'),
  'portable_specialist_readmission_receipt_sha256':readmit.get('receipt_sha256'),
  'portable_specialist_fresh_balanced':float((readmit.get('metrics') or {}).get('fresh_balanced',0)),
  'portable_specialist_causal_gain':float((readmit.get('metrics') or {}).get('causal_gain',0)),
  'portable_specialist_preprocessing_causal_drop':float((readmit.get('metrics') or {}).get('preprocessing_causal_drop',0)),
  'automatic_canonical_promotion':False,
  'architecture_mutation':False,
  'generation_transition':False,
  'g3_genesis_performed':False,
  'semantic_boundary':'SAME-G2 V5 ADDS A FRESH-READMITTED DECLARATIVE RAW-USGS PREPROCESSING ROUTE ABOVE CANONICAL V4. V4 REMAINS THE ROLLBACK PARENT AND HANDLES ALL PRE-EXISTING MULTIDOMAIN/REAL-DATA/FALLBACK BEHAVIOR.'
}

# Shadow runtime gate before any canonical mutation.
v5=G2ExperienceConditionedCognitiveLayerV5(art)
parent=G2ExperienceConditionedCognitiveLayerV4(v4)
ft=cand['feature_transform']
raw_cases=[
 {'mag':1.0,'depth':5.0,'tsunami':False,'felt_any':False,'reviewed':True},
 {'mag':2.56,'depth':100.0,'tsunami':False,'felt_any':True,'reviewed':False},
 {'mag':2.57,'depth':19.0,'tsunami':True,'felt_any':True,'reviewed':True},
 {'mag':3.1,'depth':70.0,'tsunami':False,'felt_any':False,'reviewed':True},
 {'mag':5.0,'depth':300.0,'tsunami':True,'felt_any':True,'reviewed':False},
]
raw_ok=True
for x in raw_cases:
    transformed={
      'mag_ge_q75':float(x['mag'])>=float(ft['mag_q75']),
      'shallow':float(x['depth'])<float(ft['depth_shallow_lt']),
      'very_shallow':float(x['depth'])<float(ft['depth_very_shallow_lt']),
      'tsunami':bool(x['tsunami']),'felt_any':bool(x['felt_any']),'reviewed':bool(x['reviewed']),
    }
    expected=bool(tree_predict(cand['model'],transformed))
    for task_id in (cand['task'],cand['parent_task']):
        got=v5.decide('LOGIC',{'task_id':task_id,**x})
        raw_ok &= got.get('decision') is expected and got.get('source')=='PORTABLE_REAL_DATA_V5' and got.get('route_cardinality')=='ONE'

# New portable task fails closed if raw feature contract is incomplete.
missing=v5.decide('LOGIC',{'task_id':cand['task'],'mag':3.0})
missing_fail_closed=missing.get('decision')=='WITHHOLD' and missing.get('gate')=='WITHHOLD'

# Legacy pre-transformed task remains byte-semantically equivalent through V4 parent.
legacy_cases=[
 {'task_id':cand['parent_task'],'mag_ge_q75':False,'shallow':True,'very_shallow':True,'tsunami':False,'felt_any':False,'reviewed':True},
 {'task_id':cand['parent_task'],'mag_ge_q75':True,'shallow':False,'very_shallow':False,'tsunami':True,'felt_any':True,'reviewed':False},
]
legacy_equiv=all(v5.decide('LOGIC',x)==parent.decide('LOGIC',x) for x in legacy_cases)

# All nonportable routes must delegate exactly to V4.
rng=random.Random(20260908)
delegate_ok=True;delegate_cases=0
for organ in ('LOGIC','INTELLIGENCE'):
    for task in (v4.get('multidomain_genes',{}).get(organ,{}).get('task_models') or []):
        for _ in range(8):
            p={'task_id':task['task_id']}
            # Tree/symmetric models tolerate extra boolean features; use bounded generic keys.
            for k in ['a','b','c','dag','unweighted','negative','exact_required','large_sparse','ill_conditioned','temporal','categorical_group','causal_question','intervention_possible','budget_low','latency_pressure','missingness','outliers','schema_broken','tests_pass','rollback_ready','invariant_break','reviewed','low_risk','replicated','measurement_valid','contradiction','strong_effect','high_power','temporal_order','selection_bias','mechanism','intervention','confounder','schema_valid','sample_adequate','leakage','external_check']:
                p[k]=bool(rng.getrandbits(1))
            a=parent.decide(organ,p);b=v5.decide(organ,p);delegate_ok &= a==b;delegate_cases+=1
for organ in ('THINKING','INTELLIGENCE'):
    g=(v4.get('real_data_genes') or {}).get(organ) or {}
    if not g:continue
    if organ=='THINKING':
        roles=sorted({str(e.get(k)) for e in (g.get('model',{}).get('fallback_edges') or []) for k in ('before','after') if e.get(k)})
        actions=[{'id':'A'+str(i),'role':r} for i,r in enumerate(roles)]
        p={'task_id':g['task'],'context':{'success':True},'actions':actions}
    else:
        p={'task_id':g['task'],'sepal_length':5.1,'sepal_width':3.5,'petal_length':1.4,'petal_width':0.2}
    delegate_ok &= parent.decide(organ,p)==v5.decide(organ,p);delegate_cases+=1
compose_ok=all(v5.compose({'logic_accept':bool(m&1),'thinking_cautious':bool(m&2),'intelligence_robust':bool(m&4)})==parent.compose({'logic_accept':bool(m&1),'thinking_cautious':bool(m&2),'intelligence_robust':bool(m&4)}) for m in range(8))

checks={
  'readmission_all_checks_true':all((readmit.get('checks') or {}).values()),
  'readmission_fresh_ge_0_90':float((readmit.get('metrics') or {}).get('fresh_balanced',0))>=.90,
  'readmission_causal_gain_ge_0_25':float((readmit.get('metrics') or {}).get('causal_gain',0))>=.25,
  'readmission_preprocess_drop_ge_0_25':float((readmit.get('metrics') or {}).get('preprocessing_causal_drop',0))>=.25,
  'raw_portable_route_exact':raw_ok,
  'portable_missing_raw_fail_closed':missing_fail_closed,
  'legacy_pretransformed_backward_compatible':legacy_equiv,
  'v4_nonportable_delegate_equivalence':delegate_ok and delegate_cases>=80,
  'v4_composer_delegate_equivalence':compose_ok,
  'v4_parent_active':OLD in head.get('active_capabilities',[]),
  'g3_not_started':head.get('g3_genesis_performed') is False,
}
if not all(checks.values()):
    raise RuntimeError('V5_CANONICAL_INTEGRATION_GATE_WITHHOLD:'+json.dumps({'checks':checks,'delegate_cases':delegate_cases}))

# Build canonical V5 artifact.
art['status']='CANONICAL_ACTIVE'
art['runtime_source']=str(V5SRC.relative_to(REPO))
art['runtime_sha256']=fsha(V5SRC)
art['canonical_component_digest']=cdig(art,'canonical_component_digest')
write(V5,art)

# Bind V5 into runtime sources.
src=UNIFIED.read_text(encoding='utf-8')
old_import='from yado_g2_experience_conditioned_cognitive_layer_v4 import G2ExperienceConditionedCognitiveLayerV4'
new_import='from yado_g2_experience_conditioned_cognitive_layer_v5 import G2ExperienceConditionedCognitiveLayerV5'
if old_import not in src:raise RuntimeError('UNIFIED_V4_IMPORT_BINDING_NOT_FOUND')
src=src.replace(old_import,new_import,1)
old_init="self.experience_cognitive_layer=G2ExperienceConditionedCognitiveLayerV4(self._load('canonical/yado-g2-experience-conditioned-cognitive-layer-v4.json'))"
new_init="self.experience_cognitive_layer=G2ExperienceConditionedCognitiveLayerV5(self._load('canonical/yado-g2-experience-conditioned-cognitive-layer-v5.json'))"
if old_init not in src:raise RuntimeError('UNIFIED_V4_INIT_BINDING_NOT_FOUND')
src=src.replace(old_init,new_init,1)
UNIFIED.write_text(src,encoding='utf-8')

ms=MODULE.read_text(encoding='utf-8')
ms=ms.replace("CAP_COGNITIVE='RUNTIME-G2-EXPERIENCE-CONDITIONED-COGNITIVE-LAYER-V4'","CAP_COGNITIVE='RUNTIME-G2-EXPERIENCE-CONDITIONED-COGNITIVE-LAYER-V5'",1)
ms=ms.replace("CAP_COGNITIVE:('COGNITIVE_COORDINATOR','runtime/yado_g2_experience_conditioned_cognitive_layer_v4.py')","CAP_COGNITIVE:('COGNITIVE_COORDINATOR','runtime/yado_g2_experience_conditioned_cognitive_layer_v5.py')",1)
MODULE.write_text(ms,encoding='utf-8')

gs=MODULE_GATE.read_text(encoding='utf-8')
gs=gs.replace("core_manifest.get('experience_conditioned_cognitive_layer_v4',{}).get('status')=='CANONICAL_ACTIVE'","core_manifest.get('experience_conditioned_cognitive_layer_v5',{}).get('status')=='CANONICAL_ACTIVE'",1)
MODULE_GATE.write_text(gs,encoding='utf-8')

ps=POST_AUDIT.read_text(encoding='utf-8')
ps=ps.replace("COG='RUNTIME-G2-EXPERIENCE-CONDITIONED-COGNITIVE-LAYER-V4'","COG='RUNTIME-G2-EXPERIENCE-CONDITIONED-COGNITIVE-LAYER-V5'",1)
POST_AUDIT.write_text(ps,encoding='utf-8')

for p in [V5SRC,UNIFIED,MODULE,MODULE_GATE,POST_AUDIT]:
    py_compile.compile(str(p),doraise=True)

# Update planes and component manifests.
for p in core.get('planes',[]):
    comps=p.get('active_components',[])
    if OLD in comps:p['active_components']=sorted(set(NEW if x==OLD else x for x in comps))
if isinstance(core.get('experience_conditioned_cognitive_layer_v4'),dict):
    core['experience_conditioned_cognitive_layer_v4']['status']='SUPERSEDED_BY_V5'
    core['experience_conditioned_cognitive_layer_v4']['canonical_active']=False
    core['experience_conditioned_cognitive_layer_v4']['superseded_by']=NEW
core['experience_conditioned_cognitive_layer_v5']={
  'status':'CANONICAL_ACTIVE','component_id':NEW,'parent_component':OLD,
  'canonical_component_digest':art['canonical_component_digest'],'runtime_sha256':art['runtime_sha256'],
  'portable_specialist_candidate_digest':cand.get('candidate_digest'),
  'portable_specialist_readmission_receipt_sha256':readmit.get('receipt_sha256'),
  'portable_specialist_fresh_balanced':art['portable_specialist_fresh_balanced'],
  'portable_specialist_causal_gain':art['portable_specialist_causal_gain'],
  'portable_specialist_preprocessing_causal_drop':art['portable_specialist_preprocessing_causal_drop'],
  'rollback_parent_component':OLD,'automatic_canonical_promotion':False,
}
core['active_runtime_sources']=sorted(set(core.get('active_runtime_sources',[])+[
  'runtime/yado_g2_experience_conditioned_cognitive_layer_v4.py',
  'runtime/yado_g2_experience_conditioned_cognitive_layer_v5.py'
]))
rim=core.get('runtime_integrity_manifest') or {}
if not isinstance(rim.get('sources'),dict):raise RuntimeError('RUNTIME_INTEGRITY_MANIFEST_MISSING')
rim['sources']={rel:fsha(REPO/rel) for rel in core['active_runtime_sources']}
rim['manifest_digest']=digest(rim['sources'])
core['runtime_sha256']=fsha(UNIFIED)

# Provenance binding.
prov['current_g2_binding'].update({
  'experience_conditioned_cognitive_layer':NEW,
  'experience_conditioned_cognitive_layer_digest':art['canonical_component_digest'],
  'experience_conditioned_cognitive_layer_source_sha256':art['runtime_sha256'],
  'experience_conditioned_cognitive_layer_parent':OLD,
  'experience_conditioned_cognitive_layer_portable_candidate_digest':cand.get('candidate_digest'),
  'experience_conditioned_cognitive_layer_portable_readmission_receipt_sha256':readmit.get('receipt_sha256'),
  'experience_conditioned_cognitive_layer_portable_preprocessing_bound':True,
  'cognitive_layer_automatic_promotion':False,
})
prov['registry_digest']=cdig(prov,'registry_digest')
write(PROV,prov)

core['algorithm_provenance_registry_digest']=prov['registry_digest']
core['current_frontier']=FRONT
core['core_digest']=cdig(core,'core_digest')
write(CORE,core)

prev_head=head['canonical_head_digest']
head['active_capabilities']=sorted(set(NEW if x==OLD else x for x in head.get('active_capabilities',[])))
head['new_capabilities']=sorted(set(head.get('new_capabilities',[])+[NEW]))
if isinstance(head.get('experience_conditioned_cognitive_layer_v4'),dict):
    head['experience_conditioned_cognitive_layer_v4']['status']='SUPERSEDED_BY_V5'
    head['experience_conditioned_cognitive_layer_v4']['canonical_active']=False
    head['experience_conditioned_cognitive_layer_v4']['superseded_by']=NEW
head['experience_conditioned_cognitive_layer_v5']={
  'status':'CANONICAL_ACTIVE','component_id':NEW,'parent_component':OLD,
  'canonical_component_digest':art['canonical_component_digest'],
  'portable_specialist_candidate_digest':cand.get('candidate_digest'),
  'portable_specialist_readmission_receipt_sha256':readmit.get('receipt_sha256'),
  'fresh_balanced':art['portable_specialist_fresh_balanced'],
  'causal_gain':art['portable_specialist_causal_gain'],
  'preprocessing_causal_drop':art['portable_specialist_preprocessing_causal_drop'],
  'rollback_parent_component':OLD,'automatic_canonical_promotion':False,
}
head['algorithm_provenance_registry']['registry_digest']=prov['registry_digest']
head['unified_core']['algorithm_provenance_registry_digest']=prov['registry_digest']
head['unified_core']['core_digest']=core['core_digest']
head['unified_core']['runtime_sha256']=core['runtime_sha256']
head['unified_core']['runtime_integrity_manifest_digest']=rim['manifest_digest']
head['current_frontier']=FRONT
head['canonical_head_digest']=cdig(head,'canonical_head_digest')
write(HEAD,head)

ledger['current_head_digest']=head['canonical_head_digest']
ledger['open_deficits']=[FRONT]
run_id=str(os.getenv('GITHUB_RUN_ID') or 'LOCAL')
report={
  'schema':'yado.g2.portable_real_data_specialist_canonical_integration.v1',
  'status':'PASS_G2_PORTABLE_REAL_DATA_SPECIALIST_CANONICAL_INTEGRATION_V1',
  'component_id':NEW,'parent_component':OLD,
  'candidate_digest':cand.get('candidate_digest'),'readmission_receipt_sha256':readmit.get('receipt_sha256'),
  'fresh_metrics':copy.deepcopy(readmit.get('metrics')),
  'checks':checks,'delegate_equivalence_cases':delegate_cases,
  'previous_head_digest':prev_head,'new_head_digest':head['canonical_head_digest'],
  'active_capability_count':len(head['active_capabilities']),
  'active_runtime_source_count':len(core['active_runtime_sources']),
  'canonical_mutation':True,'canonical_mechanism_mutation':True,'architecture_mutation':False,
  'generation_transition':False,'g3_genesis_performed':False,'automatic_canonical_promotion':False,
  'next_required_capability':FRONT,
  'semantic_boundary':'V5 IS A SAME-G2 CANONICAL REPLACEMENT OF THE ACTIVE COGNITIVE LAYER ID. IT ADDS ONLY THE FRESH-READMITTED PORTABLE RAW-USGS SPECIALIST ROUTE; V4 REMAINS THE COMPLETE ROLLBACK PARENT. NO G3 TRANSITION OR CONSCIOUSNESS CLAIM.'
}
report['receipt_sha256']=digest(report)
write(OUT,report)

event={
  'index':len(ledger['events']),
  'event_id':f"E{len(ledger['events'])+1:04d}_G2_PORTABLE_REAL_DATA_SPECIALIST_CANONICAL_INTEGRATION_V1",
  'event_type':'G2_PORTABLE_REAL_DATA_SPECIALIST_CANONICAL_INTEGRATION',
  'status':'PASS_CANONICAL','generation':ledger['current_head'],
  'deficit':'G2_PORTABLE_REAL_DATA_SPECIALIST_CANONICAL_INTEGRATION_V1',
  'effect':f"REPLACED_ACTIVE={OLD}->{NEW}; PORTABLE_USGS_FRESH={art['portable_specialist_fresh_balanced']:.6f}; CAUSAL_GAIN={art['portable_specialist_causal_gain']:.6f}; PREPROCESS_DROP={art['portable_specialist_preprocessing_causal_drop']:.6f}; FRONTIER_PRESERVED={FRONT}",
  'source_path':f'receipts/yado-g2-portable-real-data-specialist-canonical-integration-v1-run-{run_id}.json',
  'source_digest':report['receipt_sha256'],'run_id':run_id,'parent_event_hash':ledger['tail_event_hash'],
  'canonical_mutation':True,'canonical_mechanism_mutation':True,'architecture_mutation':False,
  'promotion_applied':False,'generation_transition':False,
  'previous_head_digest':prev_head,'new_head_digest':head['canonical_head_digest']
}
event['event_hash']=event_hash(event)
ledger['events'].append(event);ledger['event_count']=len(ledger['events']);ledger['tail_event_hash']=event['event_hash']
ledger['ledger_digest']=digest({k:v for k,v in ledger.items() if k!='ledger_digest'})
validate_ledger_v2(ledger)
write(LEDGER,ledger)

post=subprocess.run([sys.executable,str(GUARD)],cwd=REPO,capture_output=True,text=True,timeout=120)
if post.returncode!=0:
    raise RuntimeError('POST_V5_CANONICAL_GUARD_FAILED:'+post.stdout[-8000:]+post.stderr[-3000:])
print(json.dumps({
  'status':report['status'],'component_id':NEW,'checks':checks,
  'delegate_equivalence_cases':delegate_cases,
  'active_capability_count':len(head['active_capabilities']),
  'active_runtime_source_count':len(core['active_runtime_sources']),
  'previous_head_digest':prev_head,'new_head_digest':head['canonical_head_digest'],
  'next_required_capability':FRONT,'receipt_sha256':report['receipt_sha256']
},indent=2,sort_keys=True))
