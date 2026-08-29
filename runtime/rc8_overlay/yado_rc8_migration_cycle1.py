from __future__ import annotations
import hashlib, json, copy
from pathlib import Path
from typing import Any

ROOT=Path(__file__).resolve().parent
PARENT_STATE=ROOT/'yado_canonical_state_v3_rc7_deep_integrity.json'
PARENT_MANIFEST=ROOT/'yado_development_manifest_v29.json'
COGNITIVE_REPORT=ROOT/'yado_cognitive_growth_cycle1_report.json'
OUT_STATE=ROOT/'yado_canonical_state_v3_rc8_external_cognitive.json'
OUT_REPORT=ROOT/'yado_rc8_migration_cycle1_report.json'

PROFILE='YADO_V3_0_RC8_VERIFIED_EXTERNAL_COGNITIVE_RUNTIME'
SCHEMA='yado.v3_0_rc8.external_cognitive.state.v1'
VERSION='3.0-rc8'
ALLOWED_CHANGED={
    'version','parent_version','profile','active_profile','schema','promotion_scope',
    'deep_self_audit','audit','authority','kernel_identity','rc8_migration',
    'external_runtime','cognitive_capability_lineage','r8_self_model'
}

def sha256(p:Path)->str:
    return hashlib.sha256(p.read_bytes()).hexdigest()

def load(p:Path)->dict[str,Any]:
    return json.loads(p.read_text(encoding='utf-8'))

def canonical_sha(obj:Any)->str:
    raw=json.dumps(obj,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode('utf-8')
    return hashlib.sha256(raw).hexdigest()

def preserved_view(s:dict[str,Any])->dict[str,Any]:
    return {k:copy.deepcopy(v) for k,v in s.items() if k not in ALLOWED_CHANGED}

def validate_migration(parent:dict[str,Any], child:dict[str,Any])->list[str]:
    errs=[]
    expected={
        'version':VERSION,'parent_version':'3.0-rc7','profile':PROFILE,
        'active_profile':PROFILE,'schema':SCHEMA,
    }
    for k,v in expected.items():
        if child.get(k)!=v: errs.append(f'METADATA:{k}')
    if preserved_view(parent)!=preserved_view(child): errs.append('PRESERVED_PAYLOAD_CHANGED')
    mig=child.get('rc8_migration') or {}
    if mig.get('parent_state_sha256')!=sha256(PARENT_STATE): errs.append('PARENT_STATE_HASH')
    if mig.get('parent_manifest_sha256')!=sha256(PARENT_MANIFEST): errs.append('PARENT_MANIFEST_HASH')
    if mig.get('preserved_payload_sha256')!=canonical_sha(preserved_view(parent)): errs.append('PRESERVED_PAYLOAD_HASH')
    ext=child.get('external_runtime') or {}
    if not (ext.get('verified') and ext.get('python_execution') and ext.get('event_driven') and ext.get('independent_readback')):
        errs.append('EXTERNAL_RUNTIME_NOT_VERIFIED')
    if ext.get('background_daemon') is not False: errs.append('DAEMON_CLAIM_BOUNDARY')
    caps=child.get('cognitive_capability_lineage') or {}
    if set(caps.get('active_layers') or []) != {'LOGIC','THINKING','INTELLIGENCE'}: errs.append('COGNITIVE_LINEAGE')
    audit=child.get('deep_self_audit') or {}
    remaining=set(audit.get('remaining_findings') or [])
    if 'F-R7-PROV-015' in remaining or 'F-R7-BOUND-016' in remaining: errs.append('STALE_R7_FINDINGS')
    return errs

def main()->int:
    parent=load(PARENT_STATE); pm=load(PARENT_MANIFEST); cg=load(COGNITIVE_REPORT)
    if parent.get('version')!='3.0-rc7': raise RuntimeError('PARENT_NOT_RC7')
    if pm.get('active_contract',{}).get('version')!='3.0-rc7': raise RuntimeError('PARENT_MANIFEST_NOT_RC7')
    if not pm.get('claim_boundary',{}).get('external_deployment_verified'): raise RuntimeError('EXTERNAL_BOOT_NOT_PROVEN_IN_PARENT_MANIFEST')
    if cg.get('status')!='PASS_BOUNDED_LOGIC_THINKING_INTELLIGENCE_GROWTH': raise RuntimeError('COGNITIVE_GROWTH_NOT_PROVEN')

    child=copy.deepcopy(parent)
    child.update({
        'version':VERSION,
        'parent_version':'3.0-rc7',
        'profile':PROFILE,
        'active_profile':PROFILE,
        'schema':SCHEMA,
        'promotion_scope':'BOUNDED_EXTERNAL_EVENT_RUNTIME',
    })
    parent_state_sha=sha256(PARENT_STATE); parent_manifest_sha=sha256(PARENT_MANIFEST)
    preserved_sha=canonical_sha(preserved_view(parent))
    child['kernel_identity']={
        'kernel_id':'YADO-V3-RC8-EXTERNAL-COGNITIVE',
        'release_candidate':8,
        'identity_kind':'VERSIONED_KERNEL_CONTRACT',
        'parent_kernel_id':'YADO-V3-RC7-DEEP-INTEGRITY',
        'state_schema_version':27,
        'identity_change_reason':[
            'ACTIVE_COMPATIBILITY_RECOVERY_CLOSURE_ZERO',
            'VERIFIED_EXTERNAL_EVENT_DRIVEN_PYTHON_BOOT',
            'EXTERNALLY_VERIFIED_COGNITIVE_GROWTH_LOGIC_THINKING_INTELLIGENCE',
            'CANONICAL_STATE_AUDIT_LINEAGE_REQUIRES_SYNCHRONIZATION',
        ],
    }
    child['external_runtime']={
        'verified':True,
        'kind':'GITHUB_ACTIONS_EVENT_DRIVEN_PYTHON',
        'repository':'v37025337-pixel/EVA',
        'python_execution':True,
        'event_driven':True,
        'scheduled':False,
        'outbound_https':True,
        'durable_receipts':True,
        'independent_readback':True,
        'background_daemon':False,
        'verified_boot_run_id':33257347280,
        'verified_cognitive_run_id':33258608105,
        'claim_boundary':'VERIFIED_EVENT_RUNTIME_NOT_CONTINUOUS_DAEMON',
    }
    child['cognitive_capability_lineage']={
        'status':'ACTIVE_BOUNDED_EXTERNAL_VERIFIED',
        'active_layers':['LOGIC','THINKING','INTELLIGENCE'],
        'runtime':'yado_cognitive_growth_runtime_v1.py',
        'runtime_sha256':sha256(ROOT/'yado_cognitive_growth_runtime_v1.py'),
        'source_report':'yado_cognitive_growth_cycle1_report.json',
        'source_report_sha256':sha256(COGNITIVE_REPORT),
        'parent_manifest_sha256':parent_manifest_sha,
        'fallback_preserved':True,
        'general_intelligence_proven':False,
        'general_logic_proven':False,
        'general_thinking_proven':False,
    }
    audit=copy.deepcopy(parent.get('deep_self_audit') or {})
    resolved=list(audit.get('resolved_findings') or [])
    for f in ['F-R7-PROV-015','F-R7-BOUND-016']:
        if f not in resolved: resolved.append(f)
    audit.update({
        'status':'RC8_MIGRATED_VERIFIED_EXTERNAL_COGNITIVE_RUNTIME',
        'resolved_findings':resolved,
        'remaining_findings':['F-R8-XFER-001','F-R8-DAEMON-002'],
        'remaining_finding_meanings':{
            'F-R8-XFER-001':'GENERAL_TRANSFER_ACROSS_OPEN_ENDED_DOMAINS_NOT_PROVEN',
            'F-R8-DAEMON-002':'CONTINUOUS_BACKGROUND_DAEMON_NOT_PROVEN_OR_ENABLED',
        },
    })
    child['deep_self_audit']=audit
    child.setdefault('audit',{}).update({
        'r8_identity_migration':True,
        'r8_parent_payload_preserved':True,
        'r8_external_runtime_verified':True,
        'r8_cognitive_lineage_external_verified':True,
    })
    auth=copy.deepcopy(parent.get('authority') or {})
    auth.update({
        'external_runtime_execution':'GITHUB_ACTIONS_EVENT_DRIVEN_VERIFIED',
        'external_runtime_write_scope':'RECEIPTS_AND_PROJECT_BRANCH_ONLY',
        'unrestricted_external_operator':False,
    })
    child['authority']=auth
    child['r8_self_model']={
        'known_capabilities':['CONTENT_ADDRESSED_BOOT','RECOVERY_CLOSURE_ZERO','EVENT_DRIVEN_EXTERNAL_PYTHON_RUNTIME','BOUNDED_LOGIC_GROWTH','BOUNDED_MULTICONTEXT_THINKING','BOUNDED_VALIDATION_SELECTED_INTELLIGENCE','DURABLE_EXTERNAL_RECEIPTS'],
        'known_gaps':['GENERAL_OPEN_ENDED_TRANSFER_NOT_PROVEN','CONTINUOUS_DAEMON_NOT_ENABLED','FOUNDATION_WEIGHTS_NOT_SELF_MODIFIED','SUBJECTIVE_CONSCIOUSNESS_NOT_CLAIMED'],
        'promotion_policy':'FRESH_OR_BLIND_EVIDENCE_PLUS_ROLLBACK_PLUS_EXTERNAL_READBACK',
    }
    child['rc8_migration']={
        'schema':'yado.rc8.migration.v1',
        'status':'MIGRATED_PENDING_FINAL_LOCKED_REGRESSION_AND_EXTERNAL_BOOT',
        'parent_state':'yado_canonical_state_v3_rc7_deep_integrity.json',
        'parent_state_sha256':parent_state_sha,
        'parent_manifest':'yado_development_manifest_v29.json',
        'parent_manifest_sha256':parent_manifest_sha,
        'preserved_payload_sha256':preserved_sha,
        'allowed_changed_keys':sorted(ALLOWED_CHANGED),
        'migration_reversible':True,
        'rollback_target_version':'3.0-rc7',
        'rollback_target_manifest_sha256':parent_manifest_sha,
        'external_boot_required_before_commit':True,
    }

    errs=validate_migration(parent,child)
    if errs: raise RuntimeError({'migration_errors':errs})
    OUT_STATE.write_text(json.dumps(child,ensure_ascii=False,indent=2,sort_keys=True),encoding='utf-8')
    report={
        'schema':'yado.rc8.migration.cycle1.report.v1',
        'status':'RC8_CANDIDATE_MIGRATION_PASS_PENDING_PROMOTION_GATE',
        'parent_version':'3.0-rc7','candidate_version':VERSION,
        'parent_state_sha256':parent_state_sha,'candidate_state_sha256':sha256(OUT_STATE),
        'parent_manifest_sha256':parent_manifest_sha,'preserved_payload_sha256':preserved_sha,
        'preserved_key_count':len(preserved_view(parent)),
        'changed_keys':sorted(k for k in child if parent.get(k)!=child.get(k)),
        'migration_validation_errors':[],
        'architectural_threshold_reasons':child['kernel_identity']['identity_change_reason'],
        'remaining_boundaries':audit['remaining_findings'],
        'claim_boundary':{
            'general_intelligence_proven':False,'subjective_consciousness_claimed':False,
            'continuous_daemon_enabled':False,'foundation_weights_modified':False,
        },
    }
    OUT_REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2,sort_keys=True),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False,indent=2))
    return 0

if __name__=='__main__': raise SystemExit(main())