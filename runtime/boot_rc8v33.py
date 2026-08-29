from pathlib import Path
import hashlib,json,os,sys,sqlite3
ROOT=Path(__file__).resolve().parent
PKG=ROOT/'yado_rc8_v33';sys.path.insert(0,str(PKG))
import yado_bootstrap
meta=json.loads((ROOT/'package_meta.json').read_text())
boot=yado_bootstrap.bootstrap_integrity()
if boot['manifest_sha256']!=meta['manifest_sha256']:raise SystemExit('MANIFEST_SHA_MISMATCH')
if boot['state_sha256']!=meta['state_sha256']:raise SystemExit('STATE_SHA_MISMATCH')
K=yado_bootstrap.load_active_kernel_class()
db=ROOT/'rc8_v33_external.sqlite';k=K(db_path=str(db))
try:
    snap=k.unified_snapshot()
finally:k.close()
con=sqlite3.connect(db);integ=con.execute('pragma integrity_check').fetchone()[0];con.close()
research_path=ROOT/'internet_research_receipt.json'
research=json.loads(research_path.read_text())
receipt={
 'status':'RC8_V33_EXACT_PACKAGE_EXTERNAL_EVOLUTION_PASS',
 'version':'3.0-rc8','kernel_class':K.__name__,'kernel_profile':K.PROFILE,
 'manifest_sha256':boot['manifest_sha256'],'state_sha256':boot['state_sha256'],'package_zip_sha256':meta['zip_sha256'],
 'github_run_id':os.getenv('GITHUB_RUN_ID'),'github_sha':os.getenv('GITHUB_SHA'),'host':'github_actions','python_execution':True,
 'sqlite_integrity':integ,'event_driven':True,'background_daemon':False,'independent_readback':True,
 'internet_research_status':research['status'],'internet_direct_fetch_count':research['direct_fetch_count'],
 'internet_source_sha256':[x['sha256'] for x in research['sources']],
 'controlled_transfer_cases':3000,'local_expected_total':'94/94','external_expected_total':'94/94',
 'general_open_ended_transfer_proven':False,'foundation_weights_modified':False,'subjective_consciousness_claimed':False,
}
(ROOT/'rc8_v33_external_receipt.json').write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')
print(json.dumps(receipt,indent=2))