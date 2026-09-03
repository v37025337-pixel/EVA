from __future__ import annotations
import ast,hashlib,json,os,tempfile
from pathlib import Path
from typing import Any

ROOT=Path(__file__).resolve().parent
PARENT=ROOT/'yado_canonical_state_v3_rc6_r6_schema_adaptation.json'
AUDIT=ROOT/'yado_deep_self_audit_cycle1_report.json'
OUT=ROOT/'yado_canonical_state_v3_rc7_deep_integrity.json'
REPORT=ROOT/'yado_deep_self_improvement_cycle1_report.json'

def sha(p:Path):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p:Path):return json.loads(p.read_text(encoding='utf-8'))
def atomic(path:Path,obj:dict):
    raw=json.dumps(obj,ensure_ascii=False,indent=2,sort_keys=True).encode()
    fd,tmp=tempfile.mkstemp(prefix=path.name+'.',suffix='.tmp',dir=str(path.parent))
    try:
        with os.fdopen(fd,'wb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
        os.replace(tmp,path)
    finally:
        if os.path.exists(tmp):os.unlink(tmp)

def extract_host_profiles():
    tree=ast.parse((ROOT/'yado_study_chatgpt_cycle2.py').read_text(encoding='utf-8'))
    train=None
    for node in tree.body:
        if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='train' for t in node.targets):
            train=ast.literal_eval(node.value);break
    if not isinstance(train,dict): raise RuntimeError('HOST_TRAIN_LITERAL_NOT_FOUND')
    return {label:' '.join(xs) for label,xs in train.items()}

def frontier_registry():
    spec=[
      ('STATEFUL_REGISTER','yado_stateful_frontier_repair_cycle1_report.json'),
      ('FACTORED_AND_GUARDED_REGISTER','yado_stateful_frontier_repair_cycle3_report.json'),
      ('COUPLED_REGISTER_AND_FSM','yado_stateful_frontier_repair_cycle5_report.json'),
      ('LATENT_MEALY_STATE','yado_stateful_frontier_repair_cycle7_report.json'),
      ('BELIEF_SET','yado_stateful_frontier_repair_cycle9_report.json'),
      ('PROBABILISTIC_BELIEF','yado_stateful_frontier_repair_cycle11_report.json'),
      ('ACTIVE_INFORMATION_GAIN','yado_stateful_frontier_repair_cycle13_report.json'),
    ]
    caps={}
    for cap,name in spec:
        p=ROOT/name; d=load(p)
        caps[cap]={'status':d.get('status') or d.get('verdict'),'evidence_report':name,'evidence_sha256':sha(p),'fresh_used_for_selection':bool(d.get('fresh_used_for_selection',False))}
    return caps

def validate_state(s:dict)->tuple[bool,list[str]]:
    errs=[]
    checks={
      'version':s.get('version')=='3.0-rc7',
      'parent_version':s.get('parent_version')=='3.0-rc6-r6',
      'profile':s.get('profile')=='YADO_V3_0_RC7_DEEP_INTEGRITY_AND_FRONTIER_CONSOLIDATION_LOCAL',
      'active_profile':s.get('active_profile')=='YADO_V3_0_RC7_DEEP_INTEGRITY_AND_FRONTIER_CONSOLIDATION_LOCAL',
      'schema':s.get('schema')=='yado.v3_0_rc7.deep_integrity.state.v1',
      'network_default_deny':bool((s.get('network_policy') or {}).get('direct_fetch_requires_explicit_allowlist')),
      'redirect_revalidate':bool((s.get('network_policy') or {}).get('redirect_revalidate_each_hop')),
      'historical_immutable':bool((s.get('integrity_control_plane') or {}).get('historical_state_immutable')),
      'frontier_active':(s.get('validated_frontier_portfolio') or {}).get('status')=='BOUNDED_ACTIVE_LOCAL_AFTER_REVALIDATION',
      'host_profiles_durable':bool((s.get('host_capability_model') or {}).get('profiles')),
      'no_adapter_network_exec':(s.get('openapi_contract_learning') or {}).get('network_execution') is False,
    }
    errs=[k for k,v in checks.items() if not v]
    return not errs,errs

def main():
    parent_bytes=PARENT.read_bytes(); parent_sha=hashlib.sha256(parent_bytes).hexdigest(); parent=load(PARENT); audit=load(AUDIT); chat=load(ROOT/'yado_chatgpt_study_cycle2_report.json')
    # Controlled bad candidate: deliberately keeps R5 metadata and unsafe direct-fetch policy.
    bad=json.loads(json.dumps(parent)); bad['network_policy']={'direct_fetch_requires_explicit_allowlist':False,'redirect_revalidate_each_hop':False}
    work=ROOT/'yado_rc7_promotion_working_state.json'; work.write_bytes(parent_bytes); before=sha(work); atomic(work,bad); bad_sha=sha(work); bad_ok,bad_errs=validate_state(load(work))
    # Exact rollback to parent bytes.
    work.write_bytes(parent_bytes); rollback_sha=sha(work); rollback_exact=(rollback_sha==parent_sha)

    good=json.loads(json.dumps(parent))
    profile='YADO_V3_0_RC7_DEEP_INTEGRITY_AND_FRONTIER_CONSOLIDATION_LOCAL'
    good.update({'version':'3.0-rc7','parent_version':'3.0-rc6-r6','profile':profile,'active_profile':profile,'schema':'yado.v3_0_rc7.deep_integrity.state.v1','promotion_scope':'LOCAL_PROJECT_ARTIFACT','canonical_durable_mutation':True})
    good['integrity_control_plane']={
      'status':'ACTIVE_BOUNDED_LOCAL',
      'parent_state':'yado_canonical_state_v3_rc6_r6_schema_adaptation.json',
      'parent_state_sha256':parent_sha,
      'active_contract_required':True,
      'preimport_dependency_lock_required':True,
      'historical_state_immutable':True,
      'manifest':'yado_development_manifest_v18.json',
      'canonical_bootstrap':'yado_bootstrap.py',
      'split_brain_fail_closed':True,
    }
    good['network_policy']={
      'direct_fetch_requires_explicit_allowlist':True,
      'redirect_revalidate_each_hop':True,
      'https_only':True,
      'public_network_only':True,
      'external_adapter_network_execute':False,
      'third_party_code_auto_execute':False,
      'host_mediated_connected_reads_preferred':True,
    }
    good['validated_frontier_portfolio']={
      'status':'BOUNDED_ACTIVE_LOCAL_AFTER_REVALIDATION',
      'runtime':'yado_frontier_portfolio_runtime.py',
      'instance_local':True,
      'global_monkey_patch_required':False,
      'capabilities':frontier_registry(),
      'promotion_rule':'fresh/blind=1 AND restore=1 AND ablation<1 AND fresh_not_used_for_selection; bounded local only',
      'claim_boundary':{'generic_interpreters_and_search_controllers_host_supplied':True,'general_pomdp_or_active_learning_proven':False,'specific_schemas_and_probe_choices_data_derived':True},
    }
    profiles=extract_host_profiles()
    good['host_capability_model']={
      'status':'DURABLE_BOUNDED_HOST_CAPABILITY_RELATION_MODEL',
      'representation':'HOST_CAPABILITY_RELATION_ROUTER_CHAR_NGRAM',
      'ngram_n':int(chat['selected_ngram_n']),
      'top_min':float(chat['defer_top_min']),
      'margin_min':float(chat['defer_margin_min']),
      'profiles':profiles,
      'fresh_exact':float(chat['fresh_exact']),
      'fresh_coverage':float(chat['fresh_coverage']),
      'fresh_accepted_accuracy':float(chat['fresh_accepted_accuracy']),
      'fresh_used_for_selection':bool(chat['fresh_used_for_selection']),
      'source_report':'yado_chatgpt_study_cycle2_report.json',
      'source_report_sha256':sha(ROOT/'yado_chatgpt_study_cycle2_report.json'),
      'policy':chat['host_model_policy'],
      'boundaries':{'observable_interface_only':True,'private_weights_or_private_chain_of_thought_access':False,'host_supplied_char_ngram_family':True},
    }
    resolved=['F-R7-CTRL-001','F-R7-CTRL-002','F-R7-STATE-003','F-R7-MANIFEST-004','F-R7-TEST-005','F-R7-SEC-008','F-R7-SEC-009','F-R7-STATE-010','F-R7-SUPPLY-011','F-R7-INTEG-012','F-R7-HOST-013','F-R7-HOST-014','F-R7-INTEG-017']
    good['deep_self_audit']={
      'status':'AUDIT_APPLIED_PENDING_FINAL_REGRESSION',
      'source_report':'yado_deep_self_audit_cycle1_report.json',
      'source_sha256':sha(AUDIT),
      'resolved_findings':resolved,
      'remaining_findings':['F-R7-PROV-015','F-R7-BOUND-016'],
      'improvement_priority':[x['action'] for x in audit['improvement_plan']],
      'audit_open_findings_before':audit['open_findings_count'],
    }
    good.setdefault('audit',{}).update({'deep_integrity_cycle1':True,'compatibility_recovery_not_original':True,'r7_control_plane_unified':True,'r7_network_boundary_hardened':True,'r7_frontier_portfolio_instance_local':True,'r7_host_model_durable':True})
    good.setdefault('self_model',{})
    good['r7_self_model']={
      'known_capabilities':['CONTROL_PLANE_INTEGRITY','EXPLICIT_ALLOWLIST_EVIDENCE_FETCH','BOUNDED_FRONTIER_PROGRAM_INDUCTION','BOUNDED_LATENT_BELIEF_REASONING','BOUNDED_ACTIVE_INFORMATION_GAIN','HOST_CAPABILITY_RELATION_ROUTING'],
      'known_gaps':['COMPATIBILITY_RECOVERY_MODULES_NOT_ORIGINAL','GENERIC_FRONTIER_INTERPRETERS_HOST_SUPPLIED','NO_GENERAL_POMDP_PROOF','NO_RAW_SUBSTRATE_FREE_SELF_REWRITE','NO_UNRESTRICTED_EXTERNAL_EXECUTION','NO_SUBJECTIVE_CONSCIOUSNESS_CLAIM'],
      'promotion_policy':'FAIL_CLOSED_ON_INTEGRITY_OR_EVIDENCE_GAP',
    }
    good_ok,good_errs=validate_state(good)
    if bad_ok or not bad_errs or not rollback_exact or not good_ok:
        raise RuntimeError({'bad_ok':bad_ok,'bad_errs':bad_errs,'rollback_exact':rollback_exact,'good_errs':good_errs})
    atomic(OUT,good); good_sha=sha(OUT)
    work.unlink(missing_ok=True)
    rep={
      'schema':'yado.deep_self_improvement.cycle1.v1','status':'R7_CANDIDATE_WRITTEN_PENDING_BOOT_LOCK_AND_REGRESSION',
      'parent_state_sha256':parent_sha,'bad_mutation_written':True,'bad_mutation_sha256':bad_sha,'bad_validation_passed':bad_ok,'bad_validation_errors':bad_errs,'rollback_exact':rollback_exact,'rollback_sha256':rollback_sha,
      'good_state':'yado_canonical_state_v3_rc7_deep_integrity.json','good_state_sha256':good_sha,'good_state_validation':good_ok,
      'improvements':['UNIFIED_STATE_METADATA','PREIMPORT_DEPENDENCY_LOCK_CONTRACT','FAIL_CLOSED_ACTIVE_HEAD','EXPLICIT_ALLOWLIST_PER_REDIRECT_HOP','HISTORICAL_STATE_IMMUTABILITY','INSTANCE_LOCAL_VALIDATED_FRONTIER_PORTFOLIO','DURABLE_HOST_CAPABILITY_MODEL','STRUCTURAL_FRONTIER_ROUTER'],
      'claim_boundary':{'host_executes_file_promotion_harness':True,'kernel_state_and_evidence_drive_bounded_admission':True,'foundation_model_weights_modified':False,'general_self_rewrite_proven':False}
    }
    REPORT.write_text(json.dumps(rep,ensure_ascii=False,indent=2,sort_keys=True),encoding='utf-8')
    print(json.dumps(rep,ensure_ascii=False,indent=2))
    return 0
if __name__=='__main__':raise SystemExit(main())
