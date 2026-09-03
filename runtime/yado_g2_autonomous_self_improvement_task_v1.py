from __future__ import annotations
from pathlib import Path
import copy,hashlib,json,os,sys

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
PKG=ROOT/'yado_rc8_v36'
sys.path[:0]=[str(ROOT),str(PKG)]

from yado_unified_core_v1 import UnifiedYADOCoreV1

OUT=REPO/'candidates/kernel-self-generated/g2-autonomous-self-improvement-task-v1.json'
TASK=REPO/'architecture/yado-kernel-autonomous-self-improvement-v1-request.json'

def canon(o): return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def digest(o): return hashlib.sha256(canon(o).encode()).hexdigest()
def load(p): return json.loads(Path(p).read_text(encoding='utf-8'))

task=load(TASK)
audits=sorted((REPO/'receipts').glob('yado-unified-core-deep-self-audit-v1-run-*.json'),key=lambda p:p.stat().st_mtime)
if not audits: raise RuntimeError('NO_SELF_AUDIT_EVIDENCE')
audit=load(audits[-1])
if audit.get('status')!='PASS_YADO_UNIFIED_CORE_DEEP_SELF_AUDIT_V1':
    raise RuntimeError('LATEST_SELF_AUDIT_NOT_PASS')

core=UnifiedYADOCoreV1(REPO)
head_before=copy.deepcopy(core.head)
priority=copy.deepcopy(audit.get('self_selected_priority') or [])
next_step=audit.get('self_selected_next_step')
if not next_step: raise RuntimeError('KERNEL_DID_NOT_SELECT_NEXT_STEP')

tokens=[]
for row in priority[:3]:
    tokens += str(row.get('code','')).lower().replace('_',' ').split()
    tokens += str(row.get('area','')).lower().replace('_',' ').split()
    tokens += str(row.get('recommended_action','')).lower().split()
tokens=[x for x in tokens if len(x)>=4]
experience=core.experience_search(tokens[:12] or ['experience','counterexample'],limit=12)

evolution=core.evolve_cognitive_code_genome()

evidence_paths=[
 'candidates/kernel-self-generated/g2-autonomous-gene-portfolio-selection-v1.json',
 'candidates/kernel-self-generated/g2-portfolio-deficit-invention-cycle-v1.json',
 'candidates/kernel-self-generated/g2-fcm-external-coding-resource-study-v1.json',
]
accumulated=[]
for rel in evidence_paths:
    p=REPO/rel
    if p.exists():
        d=load(p)
        accumulated.append({'path':rel,'status':d.get('status'),'receipt_sha256':d.get('receipt_sha256')})

child=evolution.get('child') if isinstance(evolution,dict) else None
selection=evolution.get('selection') if isinstance(evolution,dict) else None
fitness_gain=evolution.get('fitness_gain') if isinstance(evolution,dict) else None
shadow_change=(selection=='CHILD' and isinstance(child,dict))

report={
 'schema':'yado.g2.autonomous_self_improvement_task.v1',
 'status':'PASS_SHADOW_G2_AUTONOMOUS_SELF_IMPROVEMENT_TASK_V1',
 'task':task,
 'kernel_selected_priority':priority,
 'kernel_selected_next_step':next_step,
 'latest_self_audit_source':str(audits[-1].relative_to(REPO)),
 'latest_self_audit_receipt_sha256':audit.get('receipt_sha256'),
 'experience_query_tokens':tokens[:12],
 'experience_consulted':experience,
 'accumulated_self_generated_evidence':accumulated,
 'native_evolution_result':evolution,
 'shadow_change_produced':shadow_change,
 'selected_child_genome_digest':child.get('genome_digest') if shadow_change else None,
 'fitness_gain':fitness_gain,
 'host_selected_target':False,
 'host_selected_gene':False,
 'host_selected_operator':False,
 'host_wrote_candidate_mechanism':False,
 'canonical_mutation':False,
 'architecture_mutation':False,
 'generation_transition':False,
 'g3_genesis_performed':False,
 'canonical_head_unchanged':core.head.get('canonical_head_digest')==head_before.get('canonical_head_digest'),
 'next_action':'KERNEL_CONTINUE_FROM_SELF_SELECTED_PRIORITY',
 'semantic_boundary':'THE HOST ONLY TRIGGERS AND PERSISTS. YADO SELECTS ITS OWN AUDIT PRIORITY, CONSULTS ITS EXPERIENCE, AND RUNS ITS CANONICAL NATIVE GENOME EVOLUTION. ANY CHANGE REMAINS SHADOW; THIS DOES NOT CLAIM OPEN-ENDED AUTONOMOUS SELF-REWRITING.'
}
report['receipt_sha256']=digest(report)
OUT.parent.mkdir(parents=True,exist_ok=True)
OUT.write_text(json.dumps(report,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')

print(json.dumps({
 'status':report['status'],
 'kernel_selected_next_step':next_step,
 'kernel_selected_priority':priority[:3],
 'shadow_change_produced':shadow_change,
 'selected_child_genome_digest':report['selected_child_genome_digest'],
 'fitness_gain':fitness_gain,
 'canonical_head_unchanged':report['canonical_head_unchanged'],
 'next_action':report['next_action'],
 'receipt_sha256':report['receipt_sha256'],
},indent=2,sort_keys=True,default=str))
