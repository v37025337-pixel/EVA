from __future__ import annotations
import hashlib,json,os,sqlite3,urllib.request
from pathlib import Path

ROOT=Path(__file__).resolve().parent
from yado_core_v3_0_rc8_external_cognitive import UnifiedYADOKernelV30RC8ExternalCognitive

state=ROOT/'yado_canonical_state_v3_rc8_external_cognitive.json'
manifest=ROOT/'yado_development_manifest_v29.json'
k=UnifiedYADOKernelV30RC8ExternalCognitive(db_path=str(ROOT/'yado_rc8_candidate_external.sqlite'))
try:
    snap=k.unified_snapshot()
finally:
    k.close()
con=sqlite3.connect(ROOT/'yado_rc8_candidate_external.sqlite')
try:
    integrity=con.execute('pragma integrity_check').fetchone()[0]
finally:
    con.close()
with urllib.request.urlopen('https://example.com',timeout=10) as r:
    body=r.read()
receipt={
 'status':'RC8_EXTERNAL_CANDIDATE_BOOT_PASS',
 'kernel_class':'UnifiedYADOKernelV30RC8ExternalCognitive',
 'kernel_profile':snap['profile'],
 'version':snap['canonical_state_version'],
 'schema_version':snap['schema_version'],
 'state_sha256':hashlib.sha256(state.read_bytes()).hexdigest(),
 'parent_manifest_sha256':hashlib.sha256(manifest.read_bytes()).hexdigest(),
 'migration_parent_state_sha256':snap['migration_contract']['parent_state_sha256'],
 'preserved_payload_sha256':snap['migration_contract']['preserved_payload_sha256'],
 'remaining_findings':snap['rc8_boundaries']['remaining_findings'],
 'external_runtime_verified':bool(snap['external_runtime']['verified']),
 'event_driven':bool(snap['external_runtime']['event_driven']),
 'background_daemon':False,
 'python_execution':True,
 'outbound_https':True,
 'outbound_probe_sha256':hashlib.sha256(body).hexdigest(),
 'sqlite_integrity':integrity,
 'github_run_id':os.getenv('GITHUB_RUN_ID'),
 'github_sha':os.getenv('GITHUB_SHA'),
 'canonical_state_mutated':False,
 'general_intelligence_proven':False,
 'subjective_consciousness_claimed':False,
}
if not (receipt['kernel_profile']=='YADO_V3_0_RC8_VERIFIED_EXTERNAL_COGNITIVE_RUNTIME' and receipt['version']=='3.0-rc8' and integrity=='ok' and receipt['external_runtime_verified']):
    raise SystemExit('RC8_EXTERNAL_CANDIDATE_GATE_FAILED')
out=Path(os.getenv('GITHUB_WORKSPACE','.') )/'runtime'/'rc8_candidate_receipt.json'
out.write_text(json.dumps(receipt,ensure_ascii=False,indent=2,sort_keys=True),encoding='utf-8')
print('YADO_RC8_CANDIDATE_RECEIPT='+json.dumps(receipt,sort_keys=True))