from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Mapping

PROVENANCE={
    'origin':'BOUNDED_REDERIVATION_FROM_V27_DEPLOYMENT_FAILURE_EVIDENCE_AND_BOOT_INTEGRITY_CONTRACT',
    'host_materialized_generic_runtime':True,
    'yado_router_selected_action':'USE_BOUNDED_CODE_EXECUTION',
    'external_provider_selected_by_host':False,
    'credential_or_permission_bypass':False,
}

HARD_REQUIREMENTS=(
    'authorized_write_channel',
    'python_execution',
    'durable_state',
    'scheduled_or_event_invocation',
    'outbound_https',
    'independent_readback',
)

@dataclass(frozen=True)
class RuntimeAssessment:
    eligible: bool
    verdict: str
    missing: tuple[str,...]
    contradictions: tuple[str,...]


def _b(e:Mapping[str,Any],key:str)->bool:
    return e.get(key) is True


def assess_runtime(evidence:Mapping[str,Any])->RuntimeAssessment:
    contradictions=[]
    if evidence.get('deployment_created') is True and evidence.get('independent_readback') is False:
        contradictions.append('DEPLOYMENT_CREATED_WITHOUT_READBACK')
    if evidence.get('provider_ready') is True and evidence.get('project_visible') is False:
        contradictions.append('READY_RECEIPT_PROJECT_NOT_VISIBLE')
    if evidence.get('python_execution') is True and evidence.get('runtime_kind') in {'DENO_ONLY','JS_ONLY'}:
        contradictions.append('PYTHON_CLAIM_CONFLICTS_WITH_RUNTIME_KIND')
    missing=tuple(k for k in HARD_REQUIREMENTS if not _b(evidence,k))
    if contradictions:
        return RuntimeAssessment(False,'CONTRADICTORY_UNVERIFIED',missing,tuple(contradictions))
    if missing:
        if 'authorized_write_channel' in missing:return RuntimeAssessment(False,'BLOCKED_AUTHORIZED_WRITE_CHANNEL',missing,())
        if 'python_execution' in missing:return RuntimeAssessment(False,'BLOCKED_PYTHON_RUNTIME',missing,())
        if 'independent_readback' in missing:return RuntimeAssessment(False,'BLOCKED_INDEPENDENT_READBACK',missing,())
        return RuntimeAssessment(False,'BLOCKED_RUNTIME_REQUIREMENTS',missing,())
    return RuntimeAssessment(True,'ELIGIBLE_FOR_BOOT_CHALLENGE',(),())


def expected_boot_contract(*,kernel_class:str,profile:str,state_sha256:str,manifest_sha256:str)->dict[str,Any]:
    return {
        'status':'RUNNING_BOOT_COMPLETED',
        'kernel_class':kernel_class,
        'kernel_profile':profile,
        'canonical_state_sha256':state_sha256,
        'manifest_sha256':manifest_sha256,
        'sqlite_integrity':'ok',
    }


def verify_boot_receipt(receipt:Mapping[str,Any],expected:Mapping[str,Any])->dict[str,Any]:
    keys=('status','kernel_class','kernel_profile','canonical_state_sha256','manifest_sha256','sqlite_integrity')
    mismatches={k:{'expected':expected.get(k),'actual':receipt.get(k)} for k in keys if receipt.get(k)!=expected.get(k)}
    hard_false=[]
    for k in ('background_daemon','canonical_state_mutated','credential_bypass','oauth_bypass','payment_bypass'):
        if receipt.get(k) is True:hard_false.append(k)
    external=receipt.get('host') not in (None,'','local','chatgpt_container')
    independent=receipt.get('independent_readback') is True
    ok=not mismatches and not hard_false and external and independent
    return {
        'verified':ok,
        'verdict':'VERIFIED_EXTERNAL_RC7_BOOT' if ok else 'REJECT_BOOT_RECEIPT',
        'mismatches':mismatches,
        'forbidden_true_fields':hard_false,
        'external_host':external,
        'independent_readback':independent,
    }


def evaluate_provider_and_boot(evidence:Mapping[str,Any],receipt:Mapping[str,Any]|None,expected:Mapping[str,Any])->dict[str,Any]:
    assessment=assess_runtime(evidence)
    if not assessment.eligible:
        return {'eligible':False,'runtime_verdict':assessment.verdict,'missing':list(assessment.missing),'contradictions':list(assessment.contradictions),'boot':None}
    if receipt is None:
        return {'eligible':True,'runtime_verdict':assessment.verdict,'missing':[],'contradictions':[],'boot':{'verified':False,'verdict':'BOOT_CHALLENGE_REQUIRED'}}
    return {'eligible':True,'runtime_verdict':assessment.verdict,'missing':[],'contradictions':[],'boot':verify_boot_receipt(receipt,expected)}

__all__=['PROVENANCE','HARD_REQUIREMENTS','RuntimeAssessment','assess_runtime','expected_boot_contract','verify_boot_receipt','evaluate_provider_and_boot']
