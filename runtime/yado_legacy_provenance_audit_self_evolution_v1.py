from __future__ import annotations
from pathlib import Path
import hashlib,importlib.util,json,os,sys

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
sys.path.insert(0,str(ROOT))
from yado_evolution_ledger_v2 import validate_ledger_v2,event_hash

HEAD=REPO/'canonical'/'yado-main-head-g2.json'
LEDGER=REPO/'architecture'/'evolution-ledger.json'
SOURCE=REPO/'runtime'/'yado_unified_core_deep_self_audit_v1.py'
CAND_DIR=REPO/'candidates'/'g2-self-evolution'
CAND_SRC=CAND_DIR/'unified_core_deep_self_audit_v6.py'
CAND_META=CAND_DIR/'unified_core_deep_self_audit_v6.json'
COUNTER=REPO/'receipts'/'yado-unified-core-deep-self-audit-v1-run-33438264009.json'
OUT=ROOT/'yado_legacy_provenance_audit_self_evolution_v1_receipt.json'

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def h(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def fsha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8'))

head=load(HEAD);ledger=load(LEDGER);counter=load(COUNTER)
validate_ledger_v2(ledger)
if ledger.get('open_deficits')!=['LEGACY_EXPERIENCE_SUMMARY_PROVENANCE']:raise RuntimeError('UNEXPECTED_FRONTIER')
if counter.get('self_selected_next_step')!='LEGACY_EXPERIENCE_SUMMARY_PROVENANCE':raise RuntimeError('STALE_PROVENANCE_COUNTEREXAMPLE_NOT_PRESENT')
if ledger.get('current_head_digest')!=head.get('canonical_head_digest'):raise RuntimeError('HEAD_LEDGER_MISMATCH')

old=SOURCE.read_text(encoding='utf-8')
old_block="""add('LEGACY_EXPERIENCE_SUMMARY_PROVENANCE','MEMORY_AND_EXPERIENCE','MEDIUM','PARTIAL',
    {'registry_lessons_are_precompiled_summaries':True,'raw_legacy_content_not_loaded_by_core':not full_experience_retrieval,
     'verified_raw_retrieval_available':full_experience_retrieval},
    'Distinguish host-curated lesson summaries from lessons independently re-derived by YADO from raw historical evidence.',
    False)
"""
new_block="""# ---------- legacy summary provenance separation ----------
prov_cfg=ccore.get('legacy_experience_provenance',{}) if isinstance(ccore.get('legacy_experience_provenance',{}),dict) else {}
prov_path=REPO/prov_cfg.get('artifact','__missing__')
prov_art={}
prov_error=None
try:
    prov_art=load(prov_path)
except Exception as exc:
    prov_error=type(exc).__name__+':'+str(exc)[:180]
prov_tmp=copy.deepcopy(prov_art) if isinstance(prov_art,dict) else {}
prov_stored=prov_tmp.pop('artifact_digest',None) if isinstance(prov_tmp,dict) else None
prov_digest_ok=bool(prov_stored) and prov_stored==h(prov_tmp) and prov_stored==prov_cfg.get('artifact_digest')
legacy_entries=[x for x in cexp.get('branches',[]) if x.get('mode')=='EXPERIENCE_ONLY']
registry_labels_ok=bool(legacy_entries) and all(
    x.get('lesson_provenance',{}).get('source_class')=='HOST_CURATED_REGISTRY_SUMMARY'
    and x.get('lesson_provenance',{}).get('semantic_validation_by_rederivation') is False
    and x.get('rederived_evidence',{}).get('source_class')=='YADO_REDERIVED_FROM_VERIFIED_RAW_EVIDENCE'
    and x.get('rederived_evidence',{}).get('semantic_equivalence_to_host_lessons_claimed') is False
    for x in legacy_entries
)
prov_policy=prov_art.get('provenance_policy',{}) if isinstance(prov_art,dict) else {}
prov_retrieval=prov_art.get('retrieval',{}) if isinstance(prov_art,dict) else {}
prov_branch_coverage=prov_art.get('legacy_branch_count')==len(legacy_entries)==13
prov_raw_coverage=(prov_retrieval.get('ratio')==1.0 and not prov_retrieval.get('failures'))
prov_no_overclaim=(
    prov_policy.get('host_curated_lessons')=='PRESERVED_UNCHANGED_AND_EXPLICITLY_LABELLED'
    and prov_policy.get('yado_rederived_observations')=='DERIVED_ONLY_FROM_EXACT_REGISTERED_RAW_EVIDENCE'
    and prov_policy.get('semantic_equivalence_claimed') is False
    and prov_policy.get('legacy_code_execution') is False
)
runtime_provenance_exposed=('lesson_provenance' in runtime_text and 'rederived_evidence' in runtime_text)
provenance_ok=all([full_experience_retrieval,prov_digest_ok,registry_labels_ok,prov_branch_coverage,
                   prov_raw_coverage,prov_no_overclaim,runtime_provenance_exposed])
add('LEGACY_EXPERIENCE_SUMMARY_PROVENANCE','MEMORY_AND_EXPERIENCE','INFO' if provenance_ok else 'MEDIUM',
    'PASS' if provenance_ok else 'PARTIAL',
    {'registry_lessons_are_precompiled_summaries':True,
     'host_summaries_explicitly_labelled':registry_labels_ok,
     'verified_raw_retrieval_available':full_experience_retrieval,
     'rederived_artifact_path':prov_cfg.get('artifact'),
     'rederived_artifact_digest_ok':prov_digest_ok,
     'legacy_branch_coverage':prov_branch_coverage,
     'registered_raw_path_coverage':prov_retrieval.get('ratio'),
     'raw_retrieval_failures':prov_retrieval.get('failures'),
     'semantic_equivalence_claimed':prov_policy.get('semantic_equivalence_claimed'),
     'runtime_provenance_exposed':runtime_provenance_exposed,
     'error':prov_error},
    'Keep host-curated summaries separate from exact raw-evidence-derived observations; never silently promote lexical/structural observations into semantic validation.',
    False)
"""
if old_block not in old:raise RuntimeError('V5_PROVENANCE_BLOCK_NOT_FOUND')
new=old.replace(old_block,new_block)
CAND_DIR.mkdir(parents=True,exist_ok=True);CAND_SRC.write_text(new,encoding='utf-8')

ledger_bytes=LEDGER.read_bytes()
audit_out=ROOT/'yado_unified_core_deep_self_audit_v1_receipt.json'
old_out=audit_out.read_bytes() if audit_out.exists() else None
tmp=ROOT/'_audit_v6_shadow_candidate.py';tmp.write_text(new,encoding='utf-8')
try:
    sp=importlib.util.spec_from_file_location('_audit_v6_shadow',tmp)
    mod=importlib.util.module_from_spec(sp);sp.loader.exec_module(mod)
    rec=load(audit_out)
finally:
    try:tmp.unlink()
    except FileNotFoundError:pass
    LEDGER.write_bytes(ledger_bytes)
    if old_out is None:
        try:audit_out.unlink()
        except FileNotFoundError:pass
    else:audit_out.write_bytes(old_out)

prov=next((x for x in rec.get('findings',[]) if x.get('code')=='LEGACY_EXPERIENCE_SUMMARY_PROVENANCE'),{})
live=next((x for x in rec.get('findings',[]) if x.get('code')=='LIVE_RESOURCE_EVIDENCE_SCOPE'),{})
checks={
 'candidate_executes':rec.get('status')=='PASS_YADO_UNIFIED_CORE_DEEP_SELF_AUDIT_V1',
 'provenance_now_pass':prov.get('status')=='PASS' and prov.get('severity')=='INFO',
 'provenance_digest_verified':prov.get('evidence',{}).get('rederived_artifact_digest_ok') is True,
 'full_raw_coverage':prov.get('evidence',{}).get('registered_raw_path_coverage')==1.0,
 'no_semantic_equivalence_overclaim':prov.get('evidence',{}).get('semantic_equivalence_claimed') is False,
 'live_resource_partial_preserved':live.get('status')=='PARTIAL',
 'next_step_live_resource':rec.get('self_selected_next_step')=='LIVE_RESOURCE_EVIDENCE_SCOPE',
 'canonical_head_immutable':load(LEDGER).get('current_head_digest')==head.get('canonical_head_digest'),
}
passed=all(checks.values())
candidate_digest=h({'source_sha256':fsha(CAND_SRC),'checks':checks,'next':rec.get('self_selected_next_step')})
meta={
 'schema':'yado.g2.deep_self_audit_provenance_candidate.v6',
 'component_id':'ALG-G2-DEEP-SELF-AUDIT-V1','implementation_version':6,
 'candidate_digest':candidate_digest,'candidate_source_sha256':fsha(CAND_SRC),
 'source_runtime_sha256':fsha(SOURCE),'generation':ledger['current_head'],'parent_head_digest':head['canonical_head_digest'],
 'source_counterexample_receipt':counter['receipt_sha256'],'checks':checks,
 'canonical_active':False,'promotion_applied':False,
 'state':'AUTHORIZED_FOR_SHADOW_ADMISSION' if passed else 'WITHHELD_AUDIT_EVOLUTION_V6',
 'semantic_boundary':'SELF-AUDIT V6 RECOGNIZES VERIFIED LEGACY-PROVENANCE SEPARATION WITHOUT CLAIMING SEMANTIC EQUIVALENCE OF HOST SUMMARIES AND RAW-DERIVED OBSERVATIONS.'
}
CAND_META.write_text(json.dumps(meta,indent=2,sort_keys=True)+'\n')
next_cap='LEGACY_PROVENANCE_AUDIT_FRESH_ADMISSION_V1' if passed else 'LEGACY_PROVENANCE_AUDIT_SELF_EVOLUTION_V2'
run_id=str(os.getenv('GITHUB_RUN_ID') or 'LOCAL')
receipt={
 'schema':'yado.g2.legacy_provenance_audit_self_evolution.v1',
 'status':'PASS_LEGACY_PROVENANCE_AUDIT_SELF_EVOLUTION_V1' if passed else 'WITHHOLD_LEGACY_PROVENANCE_AUDIT_SELF_EVOLUTION_V1',
 'candidate_digest':candidate_digest,'candidate_source_sha256':fsha(CAND_SRC),'checks':checks,
 'candidate_next_step':rec.get('self_selected_next_step'),
 'canonical_mutation':False,'promotion_applied':False,'g3_genesis_performed':False,
 'next_required_capability':next_cap,'semantic_boundary':meta['semantic_boundary']
}
receipt['receipt_sha256']=h(receipt);OUT.write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')

ledger=load(LEDGER)
e={'index':len(ledger['events']),'event_id':f"E{len(ledger['events'])+1:04d}_G2_LEGACY_PROVENANCE_AUDIT_SELF_EVOLUTION",
 'event_type':'KERNEL_SELF_AUDIT_PROVENANCE_EVOLUTION','status':'PASS_SHADOW' if passed else 'WITHHOLD',
 'generation':ledger['current_head'],'deficit':'LEGACY_EXPERIENCE_SUMMARY_PROVENANCE',
 'effect':f"AUDIT_V6_PROVENANCE_RECOGNITION; NEXT={next_cap}",
 'source_path':f'receipts/yado-legacy-provenance-audit-self-evolution-v1-run-{run_id}.json',
 'source_digest':receipt['receipt_sha256'],'run_id':run_id,'parent_event_hash':ledger['tail_event_hash'],
 'canonical_mutation':False,'promotion_applied':False}
e['event_hash']=event_hash(e);ledger['events'].append(e);ledger['event_count']=len(ledger['events']);ledger['tail_event_hash']=e['event_hash']
ledger['open_deficits']=[next_cap];ledger['ledger_digest']=h({k:v for k,v in ledger.items() if k!='ledger_digest'})
validate_ledger_v2(ledger);LEDGER.write_text(json.dumps(ledger,indent=2,sort_keys=True)+'\n')
print(json.dumps({'status':receipt['status'],'checks':checks,'candidate_next_step':rec.get('self_selected_next_step'),
 'next_required_capability':next_cap,'receipt_sha256':receipt['receipt_sha256']},indent=2,sort_keys=True))
if not passed:raise SystemExit('LEGACY_PROVENANCE_AUDIT_SELF_EVOLUTION_WITHHELD')
