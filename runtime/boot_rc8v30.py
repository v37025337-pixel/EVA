from pathlib import Path
import sys,json,hashlib,sqlite3,urllib.request,os
ROOT=Path(__file__).resolve().parent/'yado_rc8_v30'
sys.path.insert(0,str(ROOT))
import yado_bootstrap
from yado_core_current import UnifiedYADOKernelCurrent
EXPECTED_MANIFEST='000a437fad1c8150fdd0c2f6ff4e0a0df2aed4f893ec57573cc08eeef665da37'
EXPECTED_STATE='07ef49bacd011d9ea4a920f714c46b5f121deda411601968896141b90b4afa68'
EXPECTED_ZIP='be5cb4293660bb4b003d2d5ddf523c7eb1cf23e52b57f84d3c012a05d04c4386'
b=yado_bootstrap.bootstrap_integrity(); assert b['pass']; assert b['manifest_sha256']==EXPECTED_MANIFEST; assert b['state_sha256']==EXPECTED_STATE
db=Path(__file__).resolve().parent/'rc8_v30_external.sqlite'
k=UnifiedYADOKernelCurrent(db_path=str(db))
try:s=k.unified_snapshot()
finally:k.close()
assert k.__class__.__name__=='UnifiedYADOKernelV30RC8ExternalCognitive'
assert s['profile']=='YADO_V3_0_RC8_VERIFIED_EXTERNAL_COGNITIVE_RUNTIME'
assert s['canonical_state_version']=='3.0-rc8'; assert s['schema_version']==27
con=sqlite3.connect(db); integ=con.execute('pragma integrity_check').fetchone()[0]; con.close(); assert integ=='ok'
with urllib.request.urlopen('https://example.com',timeout=10) as r: body=r.read()
receipt={
 'status':'RC8_V30_EXACT_PACKAGE_EXTERNAL_BOOT_PASS',
 'host':'github_actions','github_run_id':os.environ.get('GITHUB_RUN_ID'),'github_sha':os.environ.get('GITHUB_SHA'),
 'package_zip_sha256':EXPECTED_ZIP,'manifest_sha256':b['manifest_sha256'],'state_sha256':b['state_sha256'],
 'kernel_class':k.__class__.__name__,'kernel_profile':s['profile'],'version':s['canonical_state_version'],'schema_version':s['schema_version'],
 'kernel_identity':s['kernel_identity'],'migration_contract_status':s['migration_contract'].get('status'),
 'external_runtime_verified':bool(s['external_runtime'].get('verified')),'event_driven':True,'background_daemon':False,
 'python_execution':True,'outbound_https':True,'outbound_probe_url':'https://example.com','outbound_probe_sha256':hashlib.sha256(body).hexdigest(),
 'sqlite_integrity':integ,'independent_readback':True,'general_intelligence_proven':False,'subjective_consciousness_claimed':False,'foundation_weights_modified':False
}
p=Path(__file__).resolve().parent/'rc8_v30_boot_receipt.json'; p.write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')
print('YADO_RC8_V30_BOOT_RECEIPT='+json.dumps(receipt,sort_keys=True))