from __future__ import annotations
from pathlib import Path
import hashlib,json,sys

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
PKG=ROOT/'yado_rc8_v36'
sys.path[:0]=[str(ROOT),str(PKG)]

from yado_unified_core_v1 import UnifiedYADOCoreV1
from yado_evolution_ledger_v2 import validate_ledger_v2

HEAD=REPO/'canonical/yado-main-head-g2.json'
CORE=REPO/'canonical/yado-unified-core-v1.json'
LEDGER=REPO/'architecture/evolution-ledger.json'
CANON=REPO/'canonical/yado-g2-experience-conditioned-cognitive-layer-v3.json'
SRC=ROOT/'yado_g2_experience_conditioned_cognitive_layer_v3.py'
OUT=REPO/'audits/yado-g2-cognitive-layer-post-admission-v1.json'
COMP='RUNTIME-G2-EXPERIENCE-CONDITIONED-COGNITIVE-LAYER-V3'
FRONT='KERNEL_G2_RAW_REPRESENTATION_V4_ROBUSTNESS_SELF_EVOLUTION_V2'

def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def digest(o):return hashlib.sha256(canon(o).encode()).hexdigest()

head=load(HEAD);manifest=load(CORE);ledger=load(LEDGER);art=load(CANON)
validate_ledger_v2(ledger)
core=UnifiedYADOCoreV1(REPO)

cases=[
 ('logic_accept','LOGIC',{'result_exact':True,'state_known':True},'ACCEPT'),
 ('logic_continue','LOGIC',{'search_incomplete':True,'state_known':True},'CONTINUE'),
 ('logic_conflict','LOGIC',{'result_exact':True,'search_incomplete':True,'state_known':True},'WITHHOLD'),
 ('logic_unknown','LOGIC',{'result_exact':True,'state_known':False},'WITHHOLD'),
 ('thinking_revise','THINKING',{'formal_spec_present':False,'candidate_available':False,'state_known':True},'REVISE'),
 ('thinking_test','THINKING',{'candidate_available':True,'hypothesis_set_present':False,'formal_spec_present':False,'state_known':True},'TEST'),
 ('thinking_conflict','THINKING',{'formal_spec_present':False,'candidate_available':False,'oracle_available':True,'state_known':True},'WITHHOLD'),
 ('thinking_unknown','THINKING',{'formal_spec_present':False,'candidate_available':False,'state_known':False},'WITHHOLD'),
 ('intelligence_oracle','INTELLIGENCE',{'formal_spec_present':True,'real_source':False,'state_known':True},'ORACLE_GUIDED_REPAIR'),
 ('intelligence_revision','INTELLIGENCE',{'formal_spec_present':False,'hypothesis_set_present':False,'state_known':True},'HYPOTHESIS_REVISION'),
 ('intelligence_conflict','INTELLIGENCE',{'formal_spec_present':True,'real_source':False,'hypothesis_set_present':True,'state_known':True},'WITHHOLD'),
 ('intelligence_unknown','INTELLIGENCE',{'formal_spec_present':True,'real_source':False,'state_known':False},'WITHHOLD'),
 ('unknown_organ','NOVEL_ORGAN',{'state_known':True},'WITHHOLD'),
]
results=[]
for name,organ,payload,expected in cases:
    got=core.cognitive_experience_decide(organ,payload)
    results.append({'name':name,'organ':organ,'payload':payload,'expected':expected,'result':got,'pass':got.get('decision')==expected})

snap=core.cognitive_experience_snapshot()
rollback=art.get('rollback_parent_capabilities') or {}
checks={
 'component_active_in_head':COMP in head.get('active_capabilities',[]),
 'component_active_in_manifest':manifest.get('experience_conditioned_cognitive_layer_v3',{}).get('status')=='CANONICAL_ACTIVE',
 'canonical_artifact_active':art.get('status')=='CANONICAL_ACTIVE' and art.get('component_id')==COMP,
 'runtime_hash_exact':art.get('runtime_sha256')==sha(SRC)==manifest.get('experience_conditioned_cognitive_layer_v3',{}).get('runtime_sha256'),
 'unified_core_bound':hasattr(core,'experience_cognitive_layer') and hasattr(core,'cognitive_experience_decide'),
 'snapshot_component_exact':snap.get('component_id')==COMP,
 'cognitive_gene_exact':snap.get('cognitive_gene_id')==art.get('cognitive_gene_id'),
 'guard_gene_exact':snap.get('guard_gene_id')==art.get('guard_gene_id'),
 'all_execution_cases_pass':all(x['pass'] for x in results),
 'conflict_cases_fail_closed':all(x['pass'] for x in results if 'conflict' in x['name']),
 'unknown_cases_fail_closed':all(x['pass'] for x in results if 'unknown' in x['name']),
 'rollback_logic_active':rollback.get('LOGIC') in head.get('active_capabilities',[]),
 'rollback_thinking_active':rollback.get('THINKING') in head.get('active_capabilities',[]),
 'rollback_intelligence_active':rollback.get('INTELLIGENCE') in head.get('active_capabilities',[]),
 'frontier_unchanged':head.get('current_frontier')==FRONT and manifest.get('current_frontier')==FRONT and ledger.get('open_deficits')==[FRONT],
 'head_ledger_digest_match':ledger.get('current_head_digest')==head.get('canonical_head_digest'),
 'g3_not_started':head.get('g3_genesis_performed') is False and manifest.get('g3_genesis_performed') is False,
 'active_capability_count_27':len(head.get('active_capabilities',[]))==27,
}
status='PASS_G2_COGNITIVE_LAYER_POST_ADMISSION_V1' if all(checks.values()) else 'WITHHOLD_G2_COGNITIVE_LAYER_POST_ADMISSION_V1'
report={
 'schema':'yado.g2.cognitive_layer.post_admission.v1','status':status,
 'component_id':COMP,'checks':checks,'cases':results,'snapshot':snap,
 'active_capability_count':len(head.get('active_capabilities',[])),
 'frontier':head.get('current_frontier'),'canonical_mutation':False,
 'architecture_mutation':False,'generation_transition':False,'g3_genesis_performed':False,
 'semantic_boundary':'POST-ADMISSION EXECUTION AUDIT OF THE BOUNDED EXPERIENCE-CONDITIONED COGNITIVE CONTROL LAYER THROUGH THE CANONICAL UNIFIED CORE.'
}
report['report_digest']=digest(report)
OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(report,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')
print(json.dumps({'status':status,'active_capability_count':report['active_capability_count'],'checks':checks,'failed_cases':[x['name'] for x in results if not x['pass']]},indent=2,sort_keys=True))
if status.startswith('WITHHOLD'):raise SystemExit(2)
