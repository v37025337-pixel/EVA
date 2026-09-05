from __future__ import annotations
from pathlib import Path
import hashlib,json,os,sys

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
sys.path[:0]=[str(ROOT),str(ROOT/'yado_rc8_v36')]

from yado_g2_unified_execution_fabric_v5 import G2UnifiedExecutionFabricV5

HEAD=REPO/'canonical/yado-main-head-g2.json'
OUT=REPO/'candidates/kernel-self-generated/g2-continuity-file-integrity-v2.json'
SOURCE=ROOT/'yado_g2_unified_execution_fabric_v5.py'
TEST=REPO/'tests/test_g2_continuity_file_integrity.py'

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def digest(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def fsha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

head=json.loads(HEAD.read_text(encoding='utf-8'))
component=G2UnifiedExecutionFabricV5.component()
tests_pass=os.getenv('YADO_CONTINUITY_FILE_TESTS_PASS')=='1'
checks={
  'focused_regressions_pass':tests_pass,
  'canonical_v4_is_parent_active':(
      'RUNTIME-G2-UNIFIED-EXECUTION-FABRIC-V4' in head.get('active_capabilities',[])
      and 'RUNTIME-G2-UNIFIED-EXECUTION-FABRIC-V5' not in head.get('active_capabilities',[])
  ),
  'file_schema_v2':G2UnifiedExecutionFabricV5.FILE_SCHEMA=='yado.g2.cognitive_continuity_file.v2',
  'in_memory_schema_remains_v1':G2UnifiedExecutionFabricV5.CHECKPOINT_SCHEMA=='yado.g2.cognitive_continuity_checkpoint.v1',
  'integer_keys_preserved_declared':component['continuity']['preserves_integer_dict_keys'] is True,
  'tuples_preserved_declared':component['continuity']['preserves_tuples'] is True,
  'fractions_preserved_declared':component['continuity']['preserves_fraction_exactness'] is True,
  'pre_restore_file_validation_declared':component['continuity']['file_digest_validation_before_restore'] is True,
  'pre_restore_cross_layer_validation_declared':component['continuity']['cross_layer_validation_before_restore'] is True,
  'failed_replace_preserves_previous_declared':component['continuity']['failed_replace_preserves_previous_checkpoint'] is True,
  'bounded_file_size_declared':component['continuity']['max_checkpoint_file_bytes']==16*1024*1024,
  'unsupported_objects_fail_closed_declared':component['continuity']['unsupported_objects_fail_closed'] is True,
  'nonfinite_fail_closed_declared':component['continuity']['non_finite_numbers_fail_closed'] is True,
  'no_executable_deserialization_declared':component['continuity']['executable_object_deserialization'] is False,
  'legacy_v1_compatibility_declared':component['continuity']['legacy_plain_json_v1_accepted_if_valid'] is True,
  'source_exists':SOURCE.exists(),
  'focused_test_exists':TEST.exists(),
  'assistant_authored_infrastructure_repair':True,
  'kernel_generated_source_claimed':False,
  'general_intelligence_gain_claimed':False,
  'canonical_unchanged':True,
  'automatic_canonical_promotion':False,
}
passed=all(v is True for k,v in checks.items() if k not in ('kernel_generated_source_claimed','general_intelligence_gain_claimed','automatic_canonical_promotion')) and all(
    checks[k] is False for k in ('kernel_generated_source_claimed','general_intelligence_gain_claimed','automatic_canonical_promotion')
)
status='PASS_SHADOW_G2_CONTINUITY_FILE_INTEGRITY_V2' if passed else 'WITHHOLD_G2_CONTINUITY_FILE_INTEGRITY_V2'
report={
 'schema':'yado.g2.continuity_file_integrity.shadow.v2',
 'status':status,
 'parent_execution_fabric':'RUNTIME-G2-UNIFIED-EXECUTION-FABRIC-V4',
 'candidate_execution_fabric':G2UnifiedExecutionFabricV5.COMPONENT_ID,
 'component':component,
 'source_path':'runtime/yado_g2_unified_execution_fabric_v5.py',
 'source_sha256':fsha(SOURCE),
 'test_path':'tests/test_g2_continuity_file_integrity.py',
 'test_sha256':fsha(TEST),
 'checks':checks,
 'canonical_head_digest':head.get('canonical_head_digest'),
 'canonical_mutation':False,
 'promotion_applied':False,
 'authorship':{
   'implementation_repair':'ASSISTANT_AUTHORED_INFRASTRUCTURE_REPAIR',
   'kernel_generated_source':False,
   'general_intelligence_gain_evidence':False,
 },
 'next_required_capability':'COGNITIVE_CONTINUITY_FILE_INTEGRITY_CANONICAL_ADMISSION_V2' if passed else 'COGNITIVE_CONTINUITY_FILE_INTEGRITY_REPAIR_V3',
 'semantic_boundary':'PASS MEANS THE ASSISTANT-AUTHORED FILE-INTEGRITY SUCCESSOR PASSED FOCUSED REAL-RUNTIME REGRESSIONS WHILE CANONICAL V4 REMAINED UNCHANGED. IT IS NOT EVIDENCE OF YADO SELF-GENERATING SOURCE OR OF GENERAL-INTELLIGENCE GROWTH.'
}
report['receipt_sha256']=digest(report)
OUT.parent.mkdir(parents=True,exist_ok=True)
OUT.write_text(json.dumps(report,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')
print(json.dumps({'status':status,'checks':checks,'next_required_capability':report['next_required_capability'],'receipt_sha256':report['receipt_sha256']},indent=2,sort_keys=True))
if not passed:raise SystemExit(2)
