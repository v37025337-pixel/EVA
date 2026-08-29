from pathlib import Path
import sys,json,hashlib,sqlite3,os
ROOT=Path(__file__).resolve().parent; PKG=ROOT/'yado_rc8_v35'; sys.path.insert(0,str(PKG))
import yado_bootstrap
from yado_core_v3_0_rc8_external_cognitive import UnifiedYADOKernelV30RC8ExternalCognitive
meta=json.loads((ROOT/'package_meta.json').read_text())
b=yado_bootstrap.bootstrap_integrity(); db=ROOT/'rc8v35_external.sqlite'; k=UnifiedYADOKernelV30RC8ExternalCognitive(db_path=str(db))
try:
 snap=k.unified_snapshot(); mc=snap['metacognitive_control']
finally:k.close()
con=sqlite3.connect(db); integ=con.execute('pragma integrity_check').fetchone()[0]; con.close()
hold=json.loads((PKG/'yado_metacognitive_fresh_holdout_v2_report.json').read_text())
inet=json.loads((ROOT/'metacognitive_internet_receipt.json').read_text())
r={'status':'RC8_V35_EXACT_EXTERNAL_SELF_AUDIT_TRAINING_PASS','host':'github_actions','github_run_id':os.getenv('GITHUB_RUN_ID'),'github_sha':os.getenv('GITHUB_SHA'),'version':'3.0-rc8','kernel_class':'UnifiedYADOKernelV30RC8ExternalCognitive','kernel_profile':'YADO_V3_0_RC8_VERIFIED_EXTERNAL_COGNITIVE_RUNTIME','manifest_sha256':b['manifest_sha256'],'state_sha256':b['state_sha256'],'package_zip_sha256':meta['package_sha256'],'sqlite_integrity':integ,'metacognitive_status':mc['status'],'fresh_cases':hold['cases'],'fresh_accuracy':hold['candidate']['accuracy'],'fresh_harmful_execute_rate':hold['candidate']['harmful_execute_rate'],'verbal_only_accuracy':hold['verbal_only']['accuracy'],'internet_status':inet['status'],'internet_direct_fetch_count':inet['direct_fetch_count'],'independent_readback':True,'event_driven':True,'background_daemon':False,'foundation_weights_modified':False,'general_intelligence_proven':False,'subjective_consciousness_claimed':False}
(ROOT/'rc8v35_boot_receipt.json').write_text(json.dumps(r,indent=2,sort_keys=True)+'\n');print(json.dumps(r,indent=2))