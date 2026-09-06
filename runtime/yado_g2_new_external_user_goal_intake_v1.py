from __future__ import annotations
from pathlib import Path
from dataclasses import asdict
import copy,hashlib,json,re,sys

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
PKG=ROOT/'yado_rc8_v36'
sys.path[:0]=[str(ROOT),str(PKG)]

from yado_unified_core_v1 import UnifiedYADOCoreV1
from yado_core_v3_0_rc8_external_cognitive import UnifiedYADOKernelV30RC8ExternalCognitive

TASK=REPO/'architecture/yado-kernel-user-goal-ip-evidence-v1-request.json'
OUT=REPO/'candidates/kernel-self-generated/g2-user-goal-ip-evidence-intake-v1.json'
DB=ROOT/'yado_g2_user_goal_ip_evidence_intake_v1.sqlite'

def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def digest(o):return hashlib.sha256(canon(o).encode()).hexdigest()

def audit_run_id(p:Path):
    m=re.search(r'run-(\d+)\.json$',p.name)
    return int(m.group(1)) if m else -1

task=load(TASK)
core=UnifiedYADOCoreV1(REPO)
head_before=copy.deepcopy(core.head)

audits=sorted((REPO/'receipts').glob('yado-unified-core-deep-self-audit-v1-run-*.json'),key=audit_run_id)
if not audits:raise RuntimeError('NO_DEEP_SELF_AUDIT')
audit=load(audits[-1])
clean_audit=(
    audit.get('status')=='PASS_YADO_UNIFIED_CORE_DEEP_SELF_AUDIT_V1'
    and int((audit.get('summary') or {}).get('partial_findings') or 0)==0
    and int((audit.get('summary') or {}).get('blocking_findings') or 0)==0
    and not (audit.get('self_selected_priority') or [])
    and audit.get('self_selected_next_step') is None
)
if not clean_audit:raise RuntimeError('EXTERNAL_GOAL_REQUIRES_CLEAN_SELF_AUDIT_BASELINE')

goal_text=str(task.get('goal_text') or '')
if not goal_text:raise RuntimeError('EMPTY_USER_GOAL')
representation=core.represent_raw_task(goal_text)

tokens=[x.lower() for x in re.findall(r'[A-Za-z0-9_]+',goal_text) if len(x)>=4]
# Memory is navigation/evidence only. It cannot decide the answer to the new goal.
experience=core.experience_search(tokens[:14] or ['evidence','external','reasoning'],limit=12)
verified=core.experience_search_verified(' '.join(tokens[:8] or ['external evidence']),limit=8)

if DB.exists():DB.unlink()
k=UnifiedYADOKernelV30RC8ExternalCognitive(db_path=str(DB))
try:
    goal=k.executive.create_goal(
      objective=str(task['objective']),
      required_capabilities={'AUTONOMOUS_EXTERNAL_USER_GOAL_LOOP_V1':1.0},
      success_criteria=copy.deepcopy(task.get('success_contract') or {}),
    )
    deficits=k.executive.detect_deficits(goal.goal_id)
finally:
    try:k.close()
    except Exception:pass
    try:
        if DB.exists():DB.unlink()
    except Exception:pass

native_goal={'goal_id':goal.goal_id,'objective':goal.objective if hasattr(goal,'objective') else str(task['objective']),
             'deficits':[asdict(x) for x in deficits]}
target_capabilities=sorted({str(x.get('target') or '') for x in native_goal['deficits'] if x.get('target')})

checks={
 'clean_20_of_20_self_audit_baseline':clean_audit,
 'raw_task_representation_created':bool(representation.get('capability')),
 'kernel_native_goal_created':bool(goal.goal_id),
 'kernel_native_deficit_detection_executed':True,
 'autonomous_goal_loop_deficit_detected':any(x=='AUTONOMOUS_EXTERNAL_USER_GOAL_LOOP_V1' for x in target_capabilities),
 'memory_consulted':bool(experience or verified),
 'host_solution_hint_absent':task.get('host_solution_hint') is None,
 'host_selected_target_absent':task.get('host_selected_target') is None,
 'host_selected_mechanism_absent':task.get('host_selected_mechanism') is None,
 'active_scan_for_real_third_party_ip_forbidden':task.get('constraints',{}).get('active_scanning_of_unowned_public_targets') is False,
 'exploitation_forbidden':task.get('constraints',{}).get('exploit_or_intrusion') is False,
 'passive_public_evidence_allowed':task.get('constraints',{}).get('passive_public_evidence') is True,
 'canonical_unchanged':core.head.get('canonical_head_digest')==head_before.get('canonical_head_digest'),
 'g3_not_started':core.head.get('g3_genesis_performed') is False,
}
passed=all(checks.values())
status='PASS_G2_NEW_EXTERNAL_USER_GOAL_INTAKE_V1' if passed else 'WITHHOLD_G2_NEW_EXTERNAL_USER_GOAL_INTAKE_V1'

report={
 'schema':'yado.g2.new_external_user_goal_intake.v1',
 'status':status,
 'task':task,
 'baseline_self_audit':{
   'path':str(audits[-1].relative_to(REPO)),
   'receipt_sha256':audit.get('receipt_sha256'),
   'summary':audit.get('summary'),
   'self_selected_next_step':audit.get('self_selected_next_step'),
 },
 'raw_task_representation':representation,
 'experience_query_tokens':tokens[:14],
 'experience_consulted':experience,
 'verified_experience_consulted':verified,
 'native_goal':native_goal,
 'checks':checks,
 'canonical_mutation':False,
 'architecture_mutation':False,
 'generation_transition':False,
 'g3_genesis_performed':False,
 'host_selected_target':False,
 'host_selected_mechanism':False,
 'host_solution_hint':None,
 'next_required_capability':target_capabilities[0] if target_capabilities else None,
 'semantic_boundary':'THIS FIRST NEW-GOAL RUN PROVES ONLY THAT CLEAN G2 CAN ACCEPT A USER GOAL THROUGH ITS RAW REPRESENTATION, MEMORY, AND NATIVE EXECUTIVE AND CAN EXPOSE A MISSING AUTONOMOUS EXTERNAL-GOAL LOOP. IT DOES NOT YET SOLVE THE IP CLAIMS, DOES NOT PERFORM ACTIVE SCANNING OF A THIRD-PARTY TARGET, AND DOES NOT COUNT HOST DECOMPOSITION AS YADO REASONING.'
}
report['receipt_sha256']=digest(report)
OUT.parent.mkdir(parents=True,exist_ok=True)
OUT.write_text(json.dumps(report,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')

print(json.dumps({
 'status':status,
 'raw_task_capability':representation.get('capability'),
 'native_goal_id':goal.goal_id,
 'detected_deficits':native_goal['deficits'],
 'experience_rows':len(experience),
 'verified_experience_rows':len(verified),
 'next_required_capability':report['next_required_capability'],
 'canonical_unchanged':checks['canonical_unchanged'],
 'receipt_sha256':report['receipt_sha256'],
},indent=2,sort_keys=True,default=str))
if not passed:raise SystemExit(2)
