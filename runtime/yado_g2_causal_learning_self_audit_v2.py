from __future__ import annotations
from pathlib import Path
import hashlib,json,os

REPO=Path(__file__).resolve().parents[1]
OUTDIR=REPO/'receipts'

import sys
sys.path.insert(0,str(REPO/'runtime'))
from yado_g2_causal_library_kernel_v1 import G2CausalLibraryKernelV1

def canon(o): return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def digest(o): return hashlib.sha256(canon(o).encode()).hexdigest()

def finding(code,area,layer,severity,status,evidence,recommendation):
    return {'code':code,'area':area,'causal_layer':layer,'severity':severity,'status':status,'evidence':evidence,'recommendation':recommendation}

k=G2CausalLibraryKernelV1(REPO)
validation=k.validate()
dm=k.dynamic_memory_snapshot()
cycle=k.learning_cycle_snapshot()

findings=[]
dm_applied=(dm['status']=='PASS_SHADOW_G2_DYNAMIC_EXPERIENCE_MEMORY_V1' and dm['remote_branch_count']>=dm['canonical_registry_branch_count'])
findings.append(finding(
    'DYNAMIC_BRANCH_INVENTORY_APPLIED','MEMORY_AND_EXPERIENCE','L1_MEMORY_EXPERIENCE','INFO',
    'PASS' if dm_applied else 'FAIL',
    {'remote_branch_count':dm['remote_branch_count'],'canonical_registry_branch_count':dm['canonical_registry_branch_count'],'raw_lineage_count':dm['raw_lineage_count']},
    'Use the live branch inventory rather than a fixed historical branch count.'
))

prov_closed=bool(dm_applied and dm['raw_branch_inventory_is_not_semantic_knowledge'])
findings.append(finding(
    'LEGACY_EXPERIENCE_SUMMARY_PROVENANCE','MEMORY_AND_EXPERIENCE','L1_MEMORY_EXPERIENCE','INFO' if prov_closed else 'MEDIUM',
    'PASS' if prov_closed else 'PARTIAL',
    {
      'dynamic_memory_digest':dm['experience_digest'],
      'raw_branch_inventory_is_not_semantic_knowledge':dm['raw_branch_inventory_is_not_semantic_knowledge'],
      'raw_lineage_count':dm['raw_lineage_count'],
      'semantic_boundary':'BRANCH_EXISTENCE != CONTENT_UNDERSTANDING; CURATED_SUMMARY != REDERIVED_EVIDENCE'
    },
    'Keep raw lineage, curated summaries, and re-derived evidence as separate knowledge classes.'
))

if dm['raw_lineage_count']>0:
    findings.append(finding(
      'RAW_BRANCH_EVIDENCE_REDERIVATION','MEMORY_AND_EXPERIENCE','L1_MEMORY_EXPERIENCE','MEDIUM','PARTIAL',
      {'raw_lineage_branches':dm['raw_lineage_branches'],'raw_lineage_count':dm['raw_lineage_count']},
      'Read exact evidence from each raw branch, derive observations from content, preserve provenance, and only then allow semantic reuse.'
    ))
else:
    findings.append(finding(
      'RAW_BRANCH_EVIDENCE_REDERIVATION','MEMORY_AND_EXPERIENCE','L1_MEMORY_EXPERIENCE','INFO','PASS',
      {'raw_lineage_count':0},'No raw branch re-derivation backlog remains.'
    ))

if 'CODING_UNSUPPORTED_PROGRAM_FAMILIES' in cycle['unresolved_deficits']:
    findings.append(finding(
      'CODING_UNSUPPORTED_PROGRAM_FAMILIES','LOGIC_THINKING','L3_LOGIC_THINKING','MEDIUM','PARTIAL',
      {'source_cycle':cycle['cycle_id'],'latest_experience_digest':cycle['latest_experience_digest']},
      'Use later learning cycles to extend bounded repair/write coverage only after memory evidence is clean.'
    ))

layer_order={
 'L0_INPUT_GROUNDING':0,'L1_MEMORY_EXPERIENCE':1,'L2_EXPERIENCE_CONDITIONING':2,
 'L3_LOGIC_THINKING':3,'L4_INTELLIGENCE_ROUTING':4,'L5_EXECUTION_EVIDENCE':5,
 'L6_SELF_AUDIT_EVOLUTION':6,'L7_CONTINUITY_TIME':7,
}
sev={'CRITICAL':4,'HIGH':3,'MEDIUM':2,'LOW':1,'INFO':0}
actionable=[x for x in findings if x['status']!='PASS' and sev.get(x['severity'],0)>0]
actionable.sort(key=lambda x:(layer_order.get(x['causal_layer'],99),-sev.get(x['severity'],0),x['code']))
priority=[{
  'rank':i+1,'code':x['code'],'area':x['area'],'causal_layer':x['causal_layer'],
  'severity':x['severity'],'recommended_action':x['recommendation']
} for i,x in enumerate(actionable)]
next_step=priority[0]['code'] if priority else None

report={
 'schema':'yado.g2.causal_learning_self_audit.v2',
 'status':'PASS_SHADOW_G2_CAUSAL_LEARNING_SELF_AUDIT_V2',
 'kernel_validation':validation,
 'dynamic_memory':dm,
 'learning_cycle':cycle,
 'findings':findings,
 'self_selected_priority':priority,
 'self_selected_next_step':next_step,
 'selection_rule':'EARLIER_CAUSAL_LAYER_BEFORE_DOWNSTREAM_CAPABILITY_EXPANSION; THEN HIGHER_SEVERITY; THEN STABLE_CODE_ORDER',
 'previous_repeated_deficit':'LEGACY_EXPERIENCE_SUMMARY_PROVENANCE',
 'previous_deficit_now_pass':next(x['status'] for x in findings if x['code']=='LEGACY_EXPERIENCE_SUMMARY_PROVENANCE')=='PASS',
 'behavior_changed':next_step!='LEGACY_EXPERIENCE_SUMMARY_PROVENANCE',
 'canonical_mutation':False,
 'automatic_promotion':False,
 'generation_transition':False,
 'g3_genesis':False,
 'semantic_boundary':'THIS IS A SOFTWARE DEVELOPMENT SELF-AUDIT OVER THE CAUSAL LIBRARY KERNEL. IT SHOWS CHANGED TASK SELECTION FROM APPLIED EXPERIENCE; IT IS NOT A CLAIM OF HUMAN-LIKE UNDERSTANDING OR SUBJECTIVE CONSCIOUSNESS.'
}
report['receipt_sha256']=digest(report)
run=os.getenv('GITHUB_RUN_ID','local')
OUTDIR.mkdir(parents=True,exist_ok=True)
path=OUTDIR/f'yado-g2-causal-learning-self-audit-v2-run-{run}.json'
path.write_text(json.dumps(report,indent=2,sort_keys=True)+'\n',encoding='utf-8')
(REPO/'candidates/kernel-self-generated').mkdir(parents=True,exist_ok=True)
(REPO/'candidates/kernel-self-generated/g2-causal-learning-self-audit-v2.json').write_text(json.dumps(report,indent=2,sort_keys=True)+'\n',encoding='utf-8')
print(json.dumps({
 'status':report['status'],
 'previous_deficit_now_pass':report['previous_deficit_now_pass'],
 'behavior_changed':report['behavior_changed'],
 'self_selected_next_step':report['self_selected_next_step'],
 'priority':priority,
 'receipt_sha256':report['receipt_sha256'],
},indent=2,sort_keys=True))
if not report['previous_deficit_now_pass'] or not report['behavior_changed']:
    raise SystemExit(2)
