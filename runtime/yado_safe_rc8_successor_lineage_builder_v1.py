from __future__ import annotations
from dataclasses import asdict, is_dataclass
from pathlib import Path
import copy, hashlib, json, os, random, sys

ROOT=Path(__file__).resolve().parent
PKG=ROOT/'yado_rc8_v36'
sys.path.insert(0,str(PKG))

from yado_core_v2_1 import BoundedRuleSandbox
from yado_core_v2_2 import MechanismSelector, FieldMapperSandbox, SequencePlannerSandbox
from yado_core_v2_4_audited import AuditedMechanismSelector

PARENT=PKG/'yado_canonical_state_v3_rc8_external_cognitive.json'
BUNDLE_PATH=ROOT.parent/'candidates'/'rc8-cognitive-genesis-v3'/'component-bundle.json'
OUT=ROOT/'safe_rc8_successor_lineage_builder_v1'
OUT.mkdir(exist_ok=True)

def canonical(obj):
    return json.dumps(obj,sort_keys=True,separators=(',',':'),ensure_ascii=False,default=str)

def sha_bytes(p:Path):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def payload_bundle(tag:int):
    return {
        'schema':'yado.rc8.shadow.cognitive_component_bundle.v3',
        'admission_pass':True,
        'components':{
            'LOGIC':{'origin':'RC5_ALGORITHM_GENESIS','model':{'tag':tag,'organ':'LOGIC'}},
            'THINKING':{'origin':'RC6_META_GRAMMAR','model':{'tag':tag,'organ':'THINKING'}},
            'INTELLIGENCE':{'origin':'RC6_META_GRAMMAR','model':{'tag':tag,'organ':'INTELLIGENCE'}},
        }
    }

def expected_plan(inp):
    return {
        'schema':'yado.rc8.successor.lineage.plan.v1',
        'lineage_mode':'CONTENT_ADDRESSED_PARENT_PLUS_BUNDLE',
        'parent_state_sha256':inp['parent_state_sha256'],
        'component_bundle_sha256':inp['component_bundle_sha256'],
        'component_bundle':inp['component_bundle'],
        'parent_state_immutable':True,
        'canonical_parent_mutation_allowed':False,
        'fail_closed':True,
        'application_mode':'EPHEMERAL_POST_BOOT_COMPONENT_OVERLAY',
        'rollback_target_sha256':inp['parent_state_sha256'],
        'allowed_component_keys':['LOGIC','THINKING','INTELLIGENCE'],
        'required_verification':['BASE_HASH','BUNDLE_HASH','FRESH','ABLATION','ROLLBACK','READBACK'],
        'promotion_policy':'WITHHOLD_UNTIL_EXTERNAL_SUCCESSOR_BOOT_AND_REGRESSION',
    }

def example(tag:int):
    b=payload_bundle(tag)
    inp={
        'parent_state_sha256':hashlib.sha256(f'parent-{tag}'.encode()).hexdigest(),
        'component_bundle_sha256':hashlib.sha256(canonical(b).encode()).hexdigest(),
        'component_bundle':b,
        'unrelated_nonce':tag*17,
    }
    return {'input':inp,'expected':expected_plan(inp)}

training=[example(i) for i in range(1,7)]
validation=[example(i) for i in range(21,27)]
fresh=[example(i) for i in range(101,113)]

candidates,rejected=AuditedMechanismSelector.synthesize_candidates_with_diagnostics(
    target_capability='SAFE_RC8_SUCCESSOR_LINEAGE_BUILDER_V1',
    target_organ='GENERATIVE_EXECUTIVE',
    examples=training,
    min_support=2,
)

def kind(p):
    return getattr(p,'kind',type(p).__name__)

def execute(p,payload,ablated=False):
    k=kind(p)
    if k=='FIELD_MAPPER':
        return FieldMapperSandbox.execute(p,payload,ablated=ablated)
    if k=='RULE_PROGRAM':
        return BoundedRuleSandbox.execute(p,payload,ablated=ablated)
    if k=='SEQUENCE_PLANNER':
        return SequencePlannerSandbox.execute(p,payload,ablated=ablated)
    raise RuntimeError(f'UNSUPPORTED_MECHANISM_KIND:{k}')

def exact_score(p,cases,ablated=False):
    ok=0
    for e in cases:
        try: got=execute(p,e['input'],ablated=ablated)
        except Exception: got={'__error__':True}
        ok += canonical(got)==canonical(e['expected'])
    return ok/max(1,len(cases))

scored=[]
for p in candidates:
    val=exact_score(p,validation)
    comp=MechanismSelector.complexity(p)
    tie=MechanismSelector.KIND_TIEBREAK.get(kind(p),99)
    scored.append((val,-tie,-comp,p))

scored.sort(key=lambda z:(z[0],z[1],z[2]),reverse=True)
selected=scored[0][3]
selected_validation=scored[0][0]
selected_fresh=exact_score(selected,fresh)
selected_ablation=exact_score(selected,fresh,ablated=True)

# Live input: actual verified v36 parent + admitted V3 bundle.
parent_before=sha_bytes(PARENT)
bundle=json.loads(BUNDLE_PATH.read_text())
declared=bundle.get('bundle_sha256')
verify_obj=copy.deepcopy(bundle)
verify_obj.pop('bundle_sha256',None)
computed_declared=hashlib.sha256(canonical(verify_obj).encode()).hexdigest()
if declared!=computed_declared:
    raise RuntimeError(f'BUNDLE_CONTENT_DIGEST_MISMATCH:{declared}:{computed_declared}')
if bundle.get('admission_pass') is not True:
    raise RuntimeError('COGNITIVE_BUNDLE_NOT_ADMITTED')

live_input={
    'parent_state_sha256':parent_before,
    'component_bundle_sha256':declared,
    'component_bundle':bundle,
    'unrelated_nonce':999999,
}
live_plan=execute(selected,live_input)
if canonical(live_plan)!=canonical(expected_plan(live_input)):
    raise RuntimeError('LIVE_SUCCESSOR_PLAN_MISMATCH')

program_dict=asdict(selected) if is_dataclass(selected) else dict(selected.__dict__)
program_digest=selected.digest() if hasattr(selected,'digest') else hashlib.sha256(canonical(program_dict).encode()).hexdigest()
lineage_id='S1-'+hashlib.sha256((parent_before+declared+program_digest).encode()).hexdigest()[:20]

capsule={
    'schema':'yado.rc8.safe_successor_capsule.v1',
    'status':'SHADOW_SUCCESSOR_CAPSULE_READY_FOR_RUNTIME_VERIFICATION',
    'lineage_id':lineage_id,
    'parent':{
        'kind':'VERIFIED_RC8_V36',
        'state_path':'runtime/yado_rc8_v36/yado_canonical_state_v3_rc8_external_cognitive.json',
        'state_sha256':parent_before,
        'immutable':True,
    },
    'builder':{
        'capability':'SAFE_RC8_SUCCESSOR_LINEAGE_BUILDER_V1',
        'mechanism_kind':kind(selected),
        'program_digest':program_digest,
        'program':program_dict,
        'selection_validation':selected_validation,
        'fresh_blind':selected_fresh,
        'ablation_exact_score':selected_ablation,
        'rejected_families':rejected,
    },
    'plan':live_plan,
    'component_bundle':{
        'path':'candidates/rc8-cognitive-genesis-v3/component-bundle.json',
        'bundle_sha256':declared,
        'admission_pass':True,
        'components':bundle['components'],
    },
    'promotion_applied':False,
    'canonical_parent_mutation':False,
}
capsule['capsule_sha256']=hashlib.sha256(canonical(capsule).encode()).hexdigest()
capsule_path=OUT/'successor-capsule.json'
capsule_path.write_text(json.dumps(capsule,indent=2,sort_keys=True,ensure_ascii=False,default=str)+'\n')

# Independent readback / rollback proof.
readback=json.loads(capsule_path.read_text())
readback_copy=copy.deepcopy(readback)
declared_capsule=readback_copy.pop('capsule_sha256')
computed_capsule=hashlib.sha256(canonical(readback_copy).encode()).hexdigest()
parent_after=sha_bytes(PARENT)
rollback_proof={
    'parent_before_sha256':parent_before,
    'parent_after_sha256':parent_after,
    'parent_byte_identical':parent_before==parent_after,
    'rollback_target_matches_parent':live_plan['rollback_target_sha256']==parent_before,
    'capsule_readback_digest_valid':declared_capsule==computed_capsule,
}

admission=(
    kind(selected)=='FIELD_MAPPER'
    and selected_validation==1.0
    and selected_fresh==1.0
    and selected_ablation==0.0
    and rollback_proof['parent_byte_identical']
    and rollback_proof['rollback_target_matches_parent']
    and rollback_proof['capsule_readback_digest_valid']
)

receipt={
    'schema':'yado.rc8.safe_successor_lineage_builder.receipt.v1',
    'status':'PASS_SAFE_RC8_SUCCESSOR_LINEAGE_BUILDER_V1' if admission else 'WITHHOLD',
    'github_run_id':os.getenv('GITHUB_RUN_ID'),
    'github_sha':os.getenv('GITHUB_SHA'),
    'host_role':'task_transport_generic_sandbox_and_observation_only',
    'target_capability':'SAFE_RC8_SUCCESSOR_LINEAGE_BUILDER_V1',
    'selected_mechanism_kind':kind(selected),
    'selected_program_digest':program_digest,
    'candidate_count':len(candidates),
    'rejected_families':rejected,
    'validation_exact':selected_validation,
    'fresh_blind_exact':selected_fresh,
    'ablation_exact':selected_ablation,
    'fresh_case_count':len(fresh),
    'parent_state_sha256':parent_before,
    'component_bundle_sha256':declared,
    'successor_lineage_id':lineage_id,
    'successor_capsule_sha256':capsule['capsule_sha256'],
    'rollback_proof':rollback_proof,
    'canonical_parent_mutation':False,
    'promotion_applied':False,
    'next_required_capability':'SAFE_RC8_SUCCESSOR_RUNTIME_ADAPTER_V1' if admission else 'REVISE_SUCCESSOR_BUILDER',
    'semantic_boundary':'BUILDER_SYNTHESIZED_AND_SHADOW_VERIFIED; SUCCESSOR_RUNTIME_NOT_YET_PROMOTED; NOT_AGI_OR_SUBJECTIVE_CONSCIOUSNESS_PROOF',
}
receipt['receipt_sha256']=hashlib.sha256(canonical(receipt).encode()).hexdigest()
(ROOT/'yado_safe_rc8_successor_lineage_builder_v1_receipt.json').write_text(json.dumps(receipt,indent=2,sort_keys=True,ensure_ascii=False)+'\n')
print(json.dumps(receipt,indent=2,sort_keys=True,ensure_ascii=False))
if not admission:
    raise SystemExit('SUCCESSOR_BUILDER_WITHHELD')
