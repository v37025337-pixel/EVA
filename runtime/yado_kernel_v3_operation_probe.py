from pathlib import Path
import json,sys
ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
PKG=ROOT/'yado_rc8_v36'
sys.path.insert(0,str(PKG))
from yado_core_v3_0_rc8_external_cognitive import UnifiedYADOKernelV30RC8ExternalCognitive

v1=json.loads((REPO/'architecture'/'yado-kernel-self-expand-architecture-selector-constructor-v1.json').read_text())
v2=json.loads((REPO/'receipts'/'yado-kernel-self-expand-architecture-selector-constructor-v2-run-33538562733.json').read_text())
records=[
 {'variant_id':'V1','parent_id':None,'lineage_id':'G2_SELECTOR','artifact_digest':v1['artifact_digest'],
  'task_scores':{'validation':v1['validation'],'fresh_blind':v1['fresh_blind'],'completion':1.0},
  'constraints':{'regression_pass':True,'state_integrity':True,'rollback_available':True},
  'failure_tags':['fresh_blind'],'status':'WITHHOLD'},
 {'variant_id':'V2','parent_id':'V1','lineage_id':'G2_SELECTOR','artifact_digest':v2['receipt_sha256'],
  'task_scores':{'validation':v2['validation'],'fresh_blind':v2['fresh_blind'],'completion':0.0},
  'constraints':{'regression_pass':True,'state_integrity':True,'rollback_available':True},
  'failure_tags':['validation','fresh_blind','completion'],'status':'WITHHOLD'}
]
k=UnifiedYADOKernelV30RC8ExternalCognitive(db_path=str(ROOT/'yado_v3_operation_probe.sqlite'))
try:
    op=k.propose_evolution_operation(records,'V2','fresh_blind')
    snap={'meta_evolution':k.meta_evolution_snapshot(),'meta_grammar':k.meta_grammar_snapshot(),
          'constructor_count':len(k.algorithm_constructor_registry())}
finally:
    k.close()
out={'schema':'yado.g2.v3_operation_probe.v1','kernel_operation':op,'kernel_snapshot':snap,
     'host_selected_operation':False,'canonical_mutation':False,'architecture_mutation':False}
(ROOT/'yado_kernel_v3_operation_probe_receipt.json').write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
print(json.dumps(out,indent=2,sort_keys=True))
