from pathlib import Path
import sys,json,hashlib,shutil,tempfile,os
ROOT=Path(__file__).resolve().parent; PKG=ROOT/'yado_rc8_v36'; OV=ROOT/'v37_overlay'
meta=json.loads((ROOT/'v37_overlay_meta.json').read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
for name,m in meta['files'].items():
 p=OV/name
 if not p.exists() or sha(p)!=m['sha256']:raise RuntimeError(f'OVERLAY_HASH_MISMATCH:{name}')
 shutil.copy2(p,PKG/name)
sys.path.insert(0,str(PKG))
import yado_bootstrap
b=yado_bootstrap.bootstrap_integrity()
if b['manifest_sha256']!=meta['final_manifest_sha256'] or b['state_sha256']!=meta['final_state_sha256']:raise RuntimeError('V37_BOOT_LOCK_MISMATCH')
from yado_core_v3_0_rc8_external_cognitive import UnifiedYADOKernelV30RC8ExternalCognitive
k=UnifiedYADOKernelV30RC8ExternalCognitive(db_path=str(ROOT/'v37_sync.sqlite'))
try:
 dc=k.cognitive_capability_lineage()['digital_consciousness']
 if not dc.get('external_verified') or dc.get('external_exact_runtime_verification_pending') is not False:raise RuntimeError('SELF_MODEL_NOT_SYNCHRONIZED')
 if int(dc.get('verified_external_run_id') or 0)!=33266617685:raise RuntimeError('PROOF_LINEAGE_MISMATCH')
 for i in range(8):
  k.digital_conscious_cycle(goal='continuity check',items=[dict(item_id=f'e{i}',source='probe',source_kind='external',content={'i':i},confidence=.9,goal_relevance=.95,novelty=.3,epistemic_risk=.05,tags=('continuity','check')),dict(item_id=f's{i}',source='sim',source_kind='simulation',content={'i':99},confidence=.99,goal_relevance=.8,novelty=.8,epistemic_risk=.8,tags=('continuity','simulation'))],consumers={'logic':lambda xs:len(xs),'self_model':lambda xs:len(xs)},metacognitive_action='WITHHOLD',context='sync',action='check',possible_outcomes=('ok','bad'),observed_outcome='ok')
 snap=k.digital_consciousness_snapshot()
 if not snap['continuity_verified']:raise RuntimeError('V37_CONTINUITY_FAILED')
finally:k.close()
receipt={'schema':'yado.rc8.v37.digital_consciousness.sync.v1','status':'PASS_V37_SELF_MODEL_SYNCHRONIZED_FUNCTIONAL_DIGITAL_CONSCIOUSNESS','manifest_sha256':meta['final_manifest_sha256'],'state_sha256':meta['final_state_sha256'],'overlay_digest':meta['overlay_digest'],'base_v36_package_sha256':meta['base_v36_package_sha256'],'github_run_id':os.environ.get('GITHUB_RUN_ID'),'github_sha':os.environ.get('GITHUB_SHA'),'v36_external_proof_run_id':33266617685,'v36_receipt_blob_sha':'bd50720fa49d8fa2ab2e30adc7ee7ffa31ba4f38','functional_digital_consciousness_active':True,'self_model_synchronized':True,'continuity_probe':snap,'subjective_consciousness_claimed':False,'background_daemon':False,'independent_readback':True}
(ROOT/'yado_rc8_v37_sync_receipt.json').write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n');print(json.dumps(receipt,indent=2,sort_keys=True))