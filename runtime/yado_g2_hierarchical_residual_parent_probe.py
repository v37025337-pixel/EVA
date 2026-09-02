from pathlib import Path
import json,sys
ROOT=Path(__file__).resolve().parent; PKG=ROOT/'yado_rc8_v36'
sys.path[:0]=[str(ROOT),str(PKG)]
from yado_core_v3_0_rc8_external_cognitive import UnifiedYADOKernelV30RC8ExternalCognitive
k=UnifiedYADOKernelV30RC8ExternalCognitive(db_path=str(ROOT/'yado_hierarchical_parent_probe.sqlite'))
try:
    records=[
      {'variant_id':'EXECUTABLE_PARENT','parent_id':None,'lineage_id':'G2_SELECTOR_LINEAGE','artifact_digest':'parent',
       'task_scores':{'fresh_blind':0.8043478260869565,'parent_correct_retention':1.0,'parent_error_repair_rate':0.0},
       'constraints':{'regression_pass':True,'state_integrity':True,'rollback_available':True},
       'traits':{'executable':1.0,'bounded':1.0},'failure_tags':['parent_error_repair_rate'],'status':'EVALUATED'},
      {'variant_id':'CENTROID_CHILD_V1','parent_id':'EXECUTABLE_PARENT','lineage_id':'G2_SELECTOR_LINEAGE',
       'artifact_digest':'016cbe8a791b6c1089f016d0047283109b16cf48cd28598752904d98b35fe384',
       'task_scores':{'fresh_blind':0.717391304347826,'parent_correct_retention':0.8648648648648649,'parent_error_repair_rate':0.1111111111111111},
       'constraints':{'regression_pass':True,'state_integrity':True,'rollback_available':True},
       'traits':{'executable':1.0,'bounded':1.0},'failure_tags':['gate_false_positive_regression'],'status':'EVALUATED'},
      {'variant_id':'CALIBRATED_CHILD_V2','parent_id':'EXECUTABLE_PARENT','lineage_id':'G2_SELECTOR_LINEAGE',
       'artifact_digest':'f54ec98fb52421f632e47c6b6db3b2a213c6853726f39c8880d2af9a59ff1523',
       'task_scores':{'fresh_blind':0.8478260869565217,'parent_correct_retention':1.0,'parent_error_repair_rate':0.2222222222222222},
       'constraints':{'regression_pass':True,'state_integrity':True,'rollback_available':True},
       'traits':{'executable':1.0,'bounded':1.0,'calibrated':1.0},
       'failure_tags':['parent_error_repair_rate'],'status':'EVALUATED'}
    ]
    parent=k.select_evolution_parent(records,'fresh_blind')
    op=k.propose_evolution_operation(records,parent['variant_id'],'fresh_blind')
finally:k.close()
out={'schema':'yado.g2.hierarchical_residual_parent_probe.v1','status':'PASS','kernel_parent':parent,'kernel_operation':op}
(ROOT/'yado_g2_hierarchical_residual_parent_probe_receipt.json').write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
print(json.dumps(out,indent=2,sort_keys=True))
