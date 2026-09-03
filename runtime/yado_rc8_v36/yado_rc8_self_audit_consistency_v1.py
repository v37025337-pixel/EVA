from __future__ import annotations
from typing import Any

REQUIRED_CAPS={
    'BOUNDED_PRECOMMIT_SKILL_ADMISSION',
    'PROCEDURAL_TRANSFER_MEMORY',
    'CONTROLLED_TRANSFER_EVALUATION',
    'BOUNDED_DIRECT_INTERNET_RESEARCH',
    'METACOGNITIVE_CAPABILITY_BOUNDARY_CONTROL',
    'YADO_CAUSAL_REFLECTIVE_WORKSPACE',
    'FUNCTIONAL_DIGITAL_CONSCIOUSNESS_EPISODE_LOOP',
}
VERIFIED_INTERNET_STATUS='VERIFIED_BOUNDED_DIRECT_INTERNET_RESEARCH'

def validate_state_self_model(state:dict[str,Any])->list[str]:
    errs=[]
    audit=state.get('deep_self_audit') or {}
    progress=audit.get('transfer_progress') or {}
    lineage=state.get('cognitive_capability_lineage') or {}
    internet=lineage.get('internet_research_cycle') or {}
    self_model=state.get('r8_self_model') or {}
    ext=state.get('external_runtime') or {}

    if progress.get('direct_research_external_verification_pending') is not False:
        errs.append('DIRECT_RESEARCH_STILL_MARKED_PENDING')
    if internet.get('status') != VERIFIED_INTERNET_STATUS:
        errs.append('INTERNET_LINEAGE_NOT_VERIFIED')
    if not internet.get('external_verified'):
        errs.append('INTERNET_EXTERNAL_PROOF_MISSING')
    if int(internet.get('verified_external_run_id') or 0) <= 0:
        errs.append('INTERNET_EXTERNAL_RUN_ID_MISSING')
    if int(internet.get('direct_fetch_count') or 0) < 1:
        errs.append('INTERNET_FETCH_EVIDENCE_MISSING')

    known=set(self_model.get('known_capabilities') or [])
    missing=sorted(REQUIRED_CAPS-known)
    if missing:
        errs.append('SELF_MODEL_CAPABILITIES_STALE:'+','.join(missing))

    latest=ext.get('latest_verified_evolution') or {}
    if not latest.get('independent_readback'):
        errs.append('LATEST_EXTERNAL_EVOLUTION_READBACK_MISSING')
    if int(latest.get('github_run_id') or 0) != int(internet.get('verified_external_run_id') or 0):
        errs.append('EXTERNAL_RUN_LINEAGE_SPLIT_BRAIN')
    if latest.get('internet_status') != 'PASS_BOUNDED_DIRECT_INTERNET_RESEARCH':
        errs.append('LATEST_EXTERNAL_INTERNET_STATUS_MISSING')
    return errs

def validate_package_coherence(manifest:dict[str,Any], head:dict[str,Any], state:dict[str,Any])->list[str]:
    errs=validate_state_self_model(state)
    cb=manifest.get('claim_boundary') or {}
    hb=head.get('boundaries') or {}
    if cb.get('internet_research_external_verification_pending') is not False:
        errs.append('MANIFEST_INTERNET_PENDING_STALE')
    if hb.get('internet_research_cycle_external_verification_pending') is not False:
        errs.append('HEAD_INTERNET_PENDING_STALE')
    if cb.get('direct_internet_research_verified') is not True:
        errs.append('MANIFEST_DIRECT_INTERNET_PROOF_MISSING')
    if hb.get('direct_internet_research_verified') is not True:
        errs.append('HEAD_DIRECT_INTERNET_PROOF_MISSING')
    reg=head.get('regression') or {}
    passed=int(reg.get('total_passed') or -1); available=int(reg.get('total_available') or -1)
    if passed < 0 or available < 0 or passed != available:
        errs.append('HEAD_REGRESSION_STALE')
    expected_reg=f'{passed}/{available} PASS' if passed >= 0 and available >= 0 else None
    if cb.get('rc8_cumulative_regression') != expected_reg:
        errs.append('MANIFEST_REGRESSION_STALE')
    return errs

__all__=['validate_state_self_model','validate_package_coherence','REQUIRED_CAPS','VERIFIED_INTERNET_STATUS']
