from __future__ import annotations
from pathlib import Path
from typing import Any
import copy,hashlib,json,os,subprocess,sys

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
PKG=ROOT/'yado_rc8_v36'
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(PKG))

from yado_unified_core_v1 import UnifiedYADOCoreV1
from yado_evolution_ledger_v2 import validate_ledger_v2,event_hash

HEAD=REPO/'canonical'/'yado-main-head-g2.json'
ARCH=REPO/'canonical'/'yado-g2-architecture-v1.json'
CORE=REPO/'canonical'/'yado-unified-core-v1.json'
EXP=REPO/'canonical'/'yado-unified-experience-registry-v1.json'
CAND_CORE=REPO/'candidates'/'unified-core-v1'/'manifest.json'
CAND_EXP=REPO/'candidates'/'unified-core-v1'/'experience-registry.json'
LEDGER=REPO/'architecture'/'evolution-ledger.json'
SHADOW=REPO/'candidates'/'g2-development'/'contextual-stream-capability-adapter-v1.json'
BURN=REPO/'architecture'/'g2-burnin-state-v1.json'
WORK=REPO/'architecture'/'g2-applied-workload-state-v1.json'
DEV=REPO/'architecture'/'g2-development-state-v1.json'
REAL_LEGACY=REPO/'receipts'/'yado-g2-real-world-transfer-benchmark-v1-run-33363995201.json'
REAL_LATEST=REPO/'receipts'/'yado-g2-real-world-transfer-recheck-canonical-v1-latest.json'
REAL=REAL_LATEST if REAL_LATEST.exists() else REAL_LEGACY
REAL_NATIVE_V2=REPO/'architecture'/'yado-real-world-generalization-state-v2.json'
POST=REPO/'receipts'/'yado-g2-post-workload-capability-audit-v1-run-33363851997.json'
CONSOL=REPO/'receipts'/'yado-unified-core-consolidation-gate-v1-run-33371375385.json'
RECON=REPO/'receipts'/'yado-unified-core-ledger-reconciliation-v1-run-33371661769.json'
RUNTIME=REPO/'runtime'/'yado_unified_core_v1.py'
OUT=ROOT/'yado_unified_core_deep_self_audit_v1_receipt.json'

def canon(o:Any)->str:return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def h(o:Any)->str:return hashlib.sha256(canon(o).encode()).hexdigest()
def fsha(p:Path)->str:return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p:Path)->dict[str,Any]:return json.loads(p.read_text(encoding='utf-8'))

core=UnifiedYADOCoreV1(REPO)
head=load(HEAD);arch=load(ARCH);ccore=load(CORE);cexp=load(EXP)
cand_core=load(CAND_CORE);cand_exp=load(CAND_EXP);ledger=load(LEDGER);shadow=load(SHADOW)
burn=load(BURN);work=load(WORK);dev=load(DEV);real=load(REAL);legacy_real=load(REAL_LEGACY);post=load(POST);consol=load(CONSOL);recon=load(RECON)
native_v2=load(REAL_NATIVE_V2) if REAL_NATIVE_V2.exists() else {}
real_evidence_source=str(REAL.relative_to(REPO)).replace('\\','/')
validate_ledger_v2(ledger)

findings=[]
def add(code,area,severity,status,evidence,recommendation,blocking=False):
    findings.append({
      'code':code,'area':area,'severity':severity,'status':status,
      'blocking':bool(blocking),'evidence':evidence,'recommendation':recommendation
    })

# ---------- self-integrity ----------
tmp=copy.deepcopy(head);stored=tmp.pop('canonical_head_digest',None)
head_digest_ok=stored==h(tmp)
add('HEAD_CONTENT_DIGEST','IDENTITY_AND_LINEAGE','CRITICAL' if not head_digest_ok else 'INFO',
    'PASS' if head_digest_ok else 'FAIL',
    {'stored':stored,'computed':h(tmp)},
    'Preserve content-addressed head integrity.' if head_digest_ok else 'Freeze development and rebuild the head from verified bytes.',not head_digest_ok)

tmp=copy.deepcopy(ccore);stored_core=tmp.pop('core_digest',None)
core_digest_ok=stored_core==h(tmp)
add('UNIFIED_CORE_CONTENT_DIGEST','IDENTITY_AND_LINEAGE','CRITICAL' if not core_digest_ok else 'INFO',
    'PASS' if core_digest_ok else 'FAIL',
    {'stored':stored_core,'computed':h(tmp)},
    'Keep core manifest content-addressed.' if core_digest_ok else 'Freeze development and reconstruct canonical core manifest.',not core_digest_ok)

tmp=copy.deepcopy(cexp);stored_exp=tmp.pop('registry_digest',None)
exp_digest_ok=stored_exp==h(tmp)
add('EXPERIENCE_REGISTRY_CONTENT_DIGEST','MEMORY_AND_EXPERIENCE','CRITICAL' if not exp_digest_ok else 'INFO',
    'PASS' if exp_digest_ok else 'FAIL',
    {'stored':stored_exp,'computed':h(tmp)},
    'Keep experience registry content-addressed.' if exp_digest_ok else 'Rebuild registry from verified branch evidence.',not exp_digest_ok)

runtime_sha=fsha(RUNTIME)
runtime_bound_ok=(runtime_sha==ccore.get('runtime_sha256')==head.get('unified_core',{}).get('runtime_sha256'))
add('UNIFIED_RUNTIME_HASH_BINDING','IDENTITY_AND_LINEAGE','CRITICAL' if not runtime_bound_ok else 'INFO',
    'PASS' if runtime_bound_ok else 'FAIL',
    {'actual_runtime_sha256':runtime_sha,'core_manifest_sha256':ccore.get('runtime_sha256'),
     'head_runtime_sha256':head.get('unified_core',{}).get('runtime_sha256')},
    'Maintain exact runtime binding.' if runtime_bound_ok else 'Do not execute further development until runtime is re-admitted and canonical hashes are updated.',not runtime_bound_ok)

ledger_ok=(ledger.get('current_head')==head.get('generation_id') and ledger.get('current_head_digest')==head.get('canonical_head_digest'))
add('HEAD_LEDGER_COHERENCE','IDENTITY_AND_LINEAGE','CRITICAL' if not ledger_ok else 'INFO',
    'PASS' if ledger_ok else 'FAIL',
    {'ledger_generation':ledger.get('current_head'),'head_generation':head.get('generation_id'),
     'ledger_digest':ledger.get('current_head_digest'),'head_digest':head.get('canonical_head_digest'),
     'current_head_event_id':ledger.get('current_head_event_id')},
    'Preserve reconciled single-head lineage.' if ledger_ok else 'Fail closed and reconcile head/ledger before any capability work.',not ledger_ok)

recon_ok=recon.get('status')=='PASS_UNIFIED_CORE_LEDGER_RECONCILIATION_V1' and all(recon.get('checks',{}).values())
add('LAST_SPLIT_BRAIN_REPAIR','SELF_AUDIT_AND_REPAIR','HIGH' if not recon_ok else 'INFO',
    'PASS' if recon_ok else 'FAIL',
    {'status':recon.get('status'),'checks':recon.get('checks')},
    'Retain split-brain regression guard.' if recon_ok else 'Re-run reconciliation and independent readback.',not recon_ok)

# ---------- runtime control-plane binding ----------
runtime_manifest_scope='CANONICAL' if core.manifest==ccore else ('CANDIDATE' if core.manifest==cand_core else 'OTHER')
runtime_experience_scope='CANONICAL' if core.experience==cexp else ('CANDIDATE' if core.experience==cand_exp else 'OTHER')
binding_ok=runtime_manifest_scope=='CANONICAL' and runtime_experience_scope=='CANONICAL'
add('RUNTIME_CONTROL_PLANE_BINDING','IDENTITY_AND_LINEAGE','HIGH' if not binding_ok else 'INFO',
    'PASS' if binding_ok else 'FAIL',
    {'manifest_scope':runtime_manifest_scope,'experience_scope':runtime_experience_scope,
     'canonical_core_active':ccore.get('canonical_active'),'canonical_experience_active':cexp.get('canonical_active')},
    'Runtime should read canonical unified-core manifest and canonical experience registry after consolidation.',
    not binding_ok)

# ---------- branch/experience audit ----------
branches=cexp.get('branches',[])
active=[x for x in branches if x.get('mode')=='ACTIVE_LINEAGE']
legacy=[x for x in branches if x.get('mode')=='EXPERIENCE_ONLY']
inventory_ok=len(branches)==14 and len(active)==1 and len(legacy)==13
add('EXPERIENCE_BRANCH_MODE_INVARIANT','MEMORY_AND_EXPERIENCE','HIGH' if not inventory_ok else 'INFO',
    'PASS' if inventory_ok else 'FAIL',
    {'branch_count':len(branches),'active_count':len(active),'experience_only_count':len(legacy)},
    'Keep exactly one active lineage and all legacy branches read-only.',not inventory_ok)

remote_branches=[]
remote_error=None
try:
    cp=subprocess.run(['git','ls-remote','--heads','origin'],cwd=REPO,capture_output=True,text=True,timeout=20)
    if cp.returncode==0:
        for line in cp.stdout.splitlines():
            parts=line.split()
            if len(parts)==2 and parts[1].startswith('refs/heads/'):
                remote_branches.append(parts[1][len('refs/heads/'):])
    else: remote_error=cp.stderr[-500:]
except Exception as exc:
    remote_error=type(exc).__name__+':'+str(exc)
registered={x.get('branch') for x in branches}
remote_set=set(remote_branches)
remote_inventory_ok=bool(remote_branches) and registered==remote_set
add('REMOTE_BRANCH_INVENTORY_MATCH','MEMORY_AND_EXPERIENCE',
    'MEDIUM' if remote_branches and not remote_inventory_ok else ('LOW' if not remote_branches else 'INFO'),
    'PASS' if remote_inventory_ok else ('UNAVAILABLE' if not remote_branches else 'FAIL'),
    {'registered_count':len(registered),'remote_count':len(remote_set),'missing_from_registry':sorted(remote_set-registered),
     'registry_only':sorted(registered-remote_set),'error':remote_error},
    'Keep experience registry synchronized with actual branch inventory.',
    False)

# Is the experience actually retrievable, or only summarized metadata?
# Is the experience actually retrievable, or only summarized metadata?
runtime_text=RUNTIME.read_text(encoding='utf-8')
legacy_missing_refs=[]
for entry in legacy:
    for ep in entry.get('evidence',[]):
        if not (REPO/ep).exists():
            legacy_missing_refs.append({'branch':entry.get('branch'),'path':ep})

mem_plane=next((x for x in ccore.get('planes',[]) if x.get('plane_id')=='MEMORY_AND_EXPERIENCE'),{})
legacy_component_bound='ALG-G2-LEGACY-EXPERIENCE-RETRIEVER-V1' in mem_plane.get('active_components',[])
legacy_runtime_bound=hasattr(core,'experience_read_exact') and hasattr(core,'experience_search_verified')
legacy_probe_ok=False
legacy_probe_evidence=None
try:
    probe_entry=next(x for x in core.experience.get('branches',[]) if x.get('mode')=='EXPERIENCE_ONLY' and x.get('evidence'))
    probe_path=probe_entry['evidence'][0]
    probe_item=core.experience_read_exact(probe_entry['branch'],probe_path)
    legacy_probe_ok=(probe_item.get('branch')==probe_entry['branch']
        and probe_item.get('registered_commit')==probe_entry['head_sha']
        and probe_item.get('path')==probe_path
        and probe_item.get('bytes',0)>0
        and len(probe_item.get('sha256',''))==64)
    legacy_probe_evidence={'branch':probe_entry['branch'],'commit':probe_entry['head_sha'],'path':probe_path,
        'sha256':probe_item.get('sha256'),'bytes':probe_item.get('bytes'),'transport':probe_item.get('transport')}
except Exception as exc:
    legacy_probe_evidence={'error':type(exc).__name__+':'+str(exc)[:180]}

full_experience_retrieval=legacy_component_bound and legacy_runtime_bound and legacy_probe_ok
add('LEGACY_EXPERIENCE_CONTENT_RETRIEVAL','MEMORY_AND_EXPERIENCE','HIGH' if not full_experience_retrieval else 'INFO',
    'PASS' if full_experience_retrieval else 'FAIL',
    {'missing_current_branch_evidence_paths':legacy_missing_refs[:30],'missing_count':len(legacy_missing_refs),
     'legacy_component_bound':legacy_component_bound,'legacy_runtime_bound':legacy_runtime_bound,
     'legacy_probe_ok':legacy_probe_ok,'legacy_probe_evidence':legacy_probe_evidence,
     'experience_search_returns_metadata_only':not full_experience_retrieval},
    'Maintain bounded read-only exact legacy retrieval with canonical component binding and live provenance probe.',
    not full_experience_retrieval)

add('LEGACY_EXPERIENCE_SUMMARY_PROVENANCE','MEMORY_AND_EXPERIENCE','MEDIUM','PARTIAL',
    {'registry_lessons_are_precompiled_summaries':True,'raw_legacy_content_not_loaded_by_core':not full_experience_retrieval,
     'verified_raw_retrieval_available':full_experience_retrieval},
    'Distinguish host-curated lesson summaries from lessons independently re-derived by YADO from raw historical evidence.',
    False)

# ---------- capability/evidence scope ----------
head_caps=set(head.get('inherited_capabilities',[])+head.get('new_capabilities',[]))
manifest_active=set()
for plane in ccore.get('planes',[]):
    manifest_active.update(plane.get('active_components',[]))
unbound_caps=sorted(x for x in head_caps if x not in manifest_active and not x.startswith('RESOURCE-') and not x.startswith('RUNTIME-'))
# Runtime is listed, resource is listed; counterexample memory is likely the notable gap.
add('HEAD_CAPABILITY_TO_CORE_BINDING','WORKSPACE_AND_INTEGRATION','MEDIUM' if unbound_caps else 'INFO',
    'PASS' if not unbound_caps else 'PARTIAL',
    {'head_capabilities':sorted(head_caps),'manifest_active_components':sorted(manifest_active),'unbound_capabilities':unbound_caps},
    'Every claimed active capability should have an explicit runtime/component binding in the unified core manifest.',
    False)

shadow_active=shadow.get('canonical_active') is True
burn_uses_context='BOUNDED_STREAM_CONTEXT_MAP' in (REPO/'runtime'/'yado_g2_burnin_stress_v1.py').read_text(encoding='utf-8')
work_uses_context='BOUNDED_STREAM_CONTEXT_MAP' in (REPO/'runtime'/'yado_g2_applied_workload_suite_v1.py').read_text(encoding='utf-8')
shadow_dependency=(not shadow_active) and burn_uses_context and work_uses_context
add('SHADOW_CONTEXT_ADAPTER_DEPENDENCE','MEMORY_AND_EXPERIENCE','HIGH' if shadow_dependency else 'INFO',
    'FAIL' if shadow_dependency else 'PASS',
    {'adapter_canonical_active':shadow.get('canonical_active'),'adapter_state':shadow.get('state'),
     'burnin_uses_adapter':burn_uses_context,'applied_workload_uses_adapter':work_uses_context,
     'burnin_status':burn.get('status'),'workload_status':work.get('status')},
    'Either admit the contextual stream adapter through an independent canonical gate or repeat key workload claims without it.',
    shadow_dependency)

# ---------- real-world transfer boundary ----------
if 'canonical_raw_routing' in real:
    raw=real.get('canonical_raw_routing',{}).get('accuracy')
    raw_task_count=real.get('canonical_raw_routing',{}).get('task_count')
    structured=legacy_real.get('structured_mirror_accuracy')
    raw_evidence_mode='CANONICAL_RECHECK'
else:
    raw=real.get('raw_unstructured',{}).get('accuracy')
    raw_task_count=real.get('raw_unstructured',{}).get('task_count')
    structured=real.get('structured_mirror_accuracy')
    raw_evidence_mode='LEGACY_BASELINE'
raw_block=(isinstance(raw,(int,float)) and raw<0.8 and isinstance(structured,(int,float)) and structured>=0.99)
add('SELF_AUDIT_EVIDENCE_FRESHNESS','SELF_AUDIT_AND_REPAIR','INFO',
    'PASS',
    {'selected_evidence_source':real_evidence_source,'mode':raw_evidence_mode,
     'latest_canonical_recheck_available':REAL_LATEST.exists()},
    'Always select the newest verified canonical evidence compatible with the audited capability.',
    False)
add('RAW_TASK_REPRESENTATION_GAP','REPRESENTATION_AND_GROUNDING','CRITICAL' if raw_block else 'INFO',
    'FAIL' if raw_block else 'PASS',
    {'raw_unstructured_accuracy':raw,'structured_mirror_accuracy':structured,'task_count':raw_task_count,
     'evidence_source':real_evidence_source,'evidence_mode':raw_evidence_mode,
     'next_required_capability':real.get('next_required_capability')},
    'Build or improve a bounded raw-task representation/grounding layer without secret host feature extraction, then repeat fresh real-world transfer.',
    raw_block)

# Current native-only transfer evidence supersedes stale pre-integration capability claims.
native_pass=native_v2.get('domain_pass',{}) if isinstance(native_v2,dict) else {}
math_bound=ccore.get('mathematical_reasoning',{}).get('mode')=='ACTIVE_BOUNDED_SEMANTIC_EXPRESSION_SYNTHESIS'
program_bound=ccore.get('program_execution',{}).get('mode')=='ACTIVE_BOUNDED_SINGLE_FUNCTION_REPAIR'
raw_proven=native_pass.get('REAL_UNSTRUCTURED_INPUT_TRANSFER') is True
math_proven=(native_pass.get('REAL_MATHEMATICAL_REASONING_TRANSFER') is True and math_bound)
program_proven=(program_bound and float(ccore.get('program_execution',{}).get('fresh_score',0.0))>=1.0)
science_binding=ccore.get('science_reasoning',{}) if isinstance(ccore.get('science_reasoning',{}),dict) else {}
science_bound=science_binding.get('mode')=='ACTIVE_BOUNDED_TABULAR_SCIENTIFIC_REASONING'
science_fresh_receipt=bool(science_binding.get('fresh_admission_receipt_sha256'))
science_fresh_datasets=set(science_binding.get('fresh_datasets',[]))
science_proven=(science_bound and science_fresh_receipt and {'PENGUINS','TIPS'}.issubset(science_fresh_datasets))
remaining=[]
if not raw_proven:remaining.append('REAL_UNSTRUCTURED_INPUT_TRANSFER')
if not math_proven:remaining.append('REAL_MATHEMATICAL_REASONING_TRANSFER')
if not program_proven:remaining.append('REAL_PROGRAM_EXECUTION_TRANSFER')
if not science_proven:remaining.append('REAL_SCIENCE_DATA_TRANSFER')
host_scaffold_dependence=not science_proven

add('REAL_WORLD_GENERALIZATION_SCOPE','REPRESENTATION_AND_GROUNDING','MEDIUM' if remaining else 'INFO',
    'PARTIAL' if remaining else 'PASS',
    {'remaining_native_domains':remaining,'raw_proven':raw_proven,'math_proven':math_proven,
     'program_proven':program_proven,'science_proven':science_proven,
     'host_scaffold_dependence':host_scaffold_dependence,
     'native_v2_state_source':str(REAL_NATIVE_V2.relative_to(REPO)).replace('\\','/')},
    'Continue only on native capabilities still missing; do not reopen capabilities already admitted through canonical gates.',
    False)

add('REAL_SCIENCE_DATA_TRANSFER_NATIVE_EVOLUTION_V1','RESOURCE_AND_EVIDENCE','HIGH' if not science_proven else 'INFO',
    'FAIL' if not science_proven else 'PASS',
    {'public_data_download_seen':native_v2.get('domain_scores',{}).get('REAL_SCIENCE_DATA_TRANSFER') is not None,
     'native_scientific_reasoning_present':science_proven,'science_canonical_bound':science_bound,'science_fresh_receipt_bound':science_fresh_receipt,'science_fresh_datasets':sorted(science_fresh_datasets),
     'program_capability_now_canonical':program_bound,'mathematics_capability_now_canonical':math_bound},
    'Create and independently admit a bounded native scientific-data reasoning capability over fresh public datasets.',
    not science_proven)

# ---------- self-audit and repair plane ----------
self_audit_plane=next((x for x in ccore.get('planes',[]) if x.get('plane_id')=='SELF_AUDIT_AND_REPAIR'),{})
audit_runtime_bound=any('SELF_AUDIT' in str(x) or 'AUDIT' in str(x) for x in self_audit_plane.get('active_components',[]))
add('SELF_AUDIT_RUNTIME_BINDING','SELF_AUDIT_AND_REPAIR','MEDIUM' if not audit_runtime_bound else 'INFO',
    'PARTIAL' if not audit_runtime_bound else 'PASS',
    {'active_components':self_audit_plane.get('active_components',[]),
     'this_audit_runtime':'runtime/yado_unified_core_deep_self_audit_v1.py',
     'canonical_self_audit_component_present':audit_runtime_bound},
    'If this deep self-audit survives independent comparison, admit it as a bounded canonical self-audit capability.',
    False)

# ---------- workspace/consciousness boundaries ----------
workspace_plane=next((x for x in ccore.get('planes',[]) if x.get('plane_id')=='WORKSPACE_AND_INTEGRATION'),{})
legacy_consciousness_active=any('CONSCIOUS' in str(x).upper() for x in workspace_plane.get('active_components',[]))
add('CONSCIOUSNESS_CLAIM_BOUNDARY','WORKSPACE_AND_INTEGRATION','INFO',
    'PASS',
    {'active_consciousness_component':legacy_consciousness_active,
     'legacy_experience_sources':workspace_plane.get('experience_sources',[]),
     'semantic_boundary':ccore.get('semantic_boundary')},
    'Keep legacy functional-consciousness experiments as experience until fresh admission; do not infer subjective consciousness.',
    False)

# ---------- resources ----------
live_score=real.get('live_resource_availability',{}).get('score')
add('LIVE_RESOURCE_EVIDENCE_SCOPE','RESOURCE_AND_EVIDENCE','LOW' if live_score==1.0 else 'MEDIUM',
    'PARTIAL',
    {'last_live_availability_score':live_score,'sample_size':real.get('live_resource_availability',{}).get('total'),
     'note':'Availability is point-in-time infrastructure evidence; comprehension/integration was not proven.'},
    'Re-check live resources on demand and separately test content comprehension/conflict resolution.',
    False)

# ---------- developmental priority synthesis ----------
severity_weight={'CRITICAL':5,'HIGH':4,'MEDIUM':3,'LOW':2,'INFO':0}
actionable=[f for f in findings if f['status'] not in ('PASS',) and severity_weight.get(f['severity'],0)>0]
actionable.sort(key=lambda f:(-int(f['blocking']),-severity_weight.get(f['severity'],0),f['code']))
priority=[{
  'rank':i+1,'code':f['code'],'area':f['area'],'severity':f['severity'],
  'blocking':f['blocking'],'recommended_action':f['recommendation']
} for i,f in enumerate(actionable)]

summary={
 'finding_count':len(findings),
 'critical_failures':sum(f['severity']=='CRITICAL' and f['status']=='FAIL' for f in findings),
 'high_failures':sum(f['severity']=='HIGH' and f['status']=='FAIL' for f in findings),
 'blocking_findings':sum(bool(f['blocking']) for f in findings),
 'pass_findings':sum(f['status']=='PASS' for f in findings),
 'partial_findings':sum(f['status']=='PARTIAL' for f in findings),
}

# Overall verdict: fail-closed if critical/blocking findings exist; otherwise bounded pass with limitations.
verdict='WITHHOLD_FURTHER_GENERATION_ADVANCE' if summary['blocking_findings'] else 'PASS_WITH_LIMITATIONS'
next_step=priority[0]['code'] if priority else core.developmental_frontier().get('manifest_frontier')

# Close the self-audit -> developmental-control loop without discarding the backlog.
audit_blockers=[p['code'] for p in priority if p.get('blocking')]
ledger['audit_blockers']=audit_blockers
ledger['audit_priority']=copy.deepcopy(priority)
if next_step:
    ledger['open_deficits']=[next_step]

receipt={
 'schema':'yado.unified_core.deep_self_audit.receipt.v1',
 'status':'PASS_YADO_UNIFIED_CORE_DEEP_SELF_AUDIT_V1',
 'audit_actor':{
   'core_id':core.CORE_ID,
   'generation':head.get('generation_id'),
   'execution_mode':'KERNEL_NATIVE_SELF_INSPECTION',
   'host_role':'TRIGGER_TRANSPORT_PERSISTENCE_ONLY',
 },
 'github_run_id':os.getenv('GITHUB_RUN_ID'),'github_sha':os.getenv('GITHUB_SHA'),
 'core_snapshot':core.snapshot(),
 'summary':summary,
 'overall_verdict':verdict,
 'findings':findings,
 'self_selected_priority':priority,
 'self_selected_next_step':next_step,
 'audit_frontier_binding':{'open_deficit':next_step,'blocking_backlog':audit_blockers},
 'canonical_mutation':False,
 'repair_applied':False,
 'g3_genesis_performed':False,
 'semantic_boundary':'THE UNIFIED YADO SOFTWARE KERNEL INSPECTED ITS OWN LOCAL CANONICAL STATE, RUNTIME BINDINGS, EVIDENCE, BRANCH EXPERIENCE REGISTRY, AND CAPABILITY BOUNDARIES. THIS IS A SOFTWARE SELF-AUDIT, NOT PROOF OF SUBJECTIVE SELF-AWARENESS.',
}
receipt['receipt_sha256']=h(receipt)
OUT.write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')

# Append audit result only; do not change head/frontier/deficits before independent comparison.
run_id=str(os.getenv('GITHUB_RUN_ID') or 'LOCAL')
e={
 'index':len(ledger['events']),
 'event_id':f"E{len(ledger['events'])+1:04d}_UNIFIED_CORE_DEEP_SELF_AUDIT",
 'event_type':'KERNEL_NATIVE_SELF_AUDIT',
 'status':'PASS',
 'generation':ledger['current_head'],
 'deficit':'FULL_UNIFIED_CORE_SELF_AUDIT_V1',
 'effect':f"SELF_AUDIT_COMPLETE; VERDICT={verdict}; FINDINGS={len(findings)}; BLOCKING={summary['blocking_findings']}",
 'source_path':f'receipts/yado-unified-core-deep-self-audit-v1-run-{run_id}.json',
 'source_digest':receipt['receipt_sha256'],'run_id':run_id,
 'parent_event_hash':ledger['tail_event_hash'],'canonical_mutation':False,'promotion_applied':False,
}
e['event_hash']=event_hash(e);ledger['events'].append(e);ledger['event_count']=len(ledger['events']);ledger['tail_event_hash']=e['event_hash']
ledger['ledger_digest']=h({k:v for k,v in ledger.items() if k!='ledger_digest'})
validate_ledger_v2(ledger)
LEDGER.write_text(json.dumps(ledger,indent=2,sort_keys=True)+'\n')

print(json.dumps({
 'status':receipt['status'],'overall_verdict':verdict,'summary':summary,
 'self_selected_priority':priority[:10],'self_selected_next_step':next_step,
 'receipt_sha256':receipt['receipt_sha256']
},indent=2,sort_keys=True))
