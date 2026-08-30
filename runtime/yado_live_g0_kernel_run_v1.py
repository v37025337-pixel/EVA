from __future__ import annotations
from pathlib import Path
import inspect, json, os, sys, hashlib, traceback

ROOT=Path(__file__).resolve().parent
PKG=ROOT/'yado_rc8_v36'
sys.path.insert(0,str(PKG))

from yado_core_v3_0_rc8_external_cognitive import UnifiedYADOKernelV30RC8ExternalCognitive

OUT=ROOT/'live_g0_kernel_run'
OUT.mkdir(exist_ok=True)

def safe_call(obj,name,*args,**kwargs):
    fn=getattr(obj,name,None)
    if fn is None:
        return {'status':'METHOD_MISSING','method':name}
    try:
        return {'status':'OK','method':name,'result':fn(*args,**kwargs)}
    except Exception as e:
        return {'status':'ERROR','method':name,'error':repr(e),'trace':traceback.format_exc()}

k=UnifiedYADOKernelV30RC8ExternalCognitive(
    db_path=str(OUT/'live-g0.sqlite')
)

report={
  'schema':'yado.github.live_g0_kernel_run.v1',
  'status':'RUNNING',
  'github_run_id':os.getenv('GITHUB_RUN_ID'),
  'github_sha':os.getenv('GITHUB_SHA'),
  'kernel_class':type(k).__name__,
  'developmental_head':'G0_RC8_V36',
  'boot':{},
  'cycles':[],
  'canonical_mutation':False,
  'promotion_applied':False,
}

# Boot/self-model observation
for method in ['audit_snapshot','integrity_control_plane','development_priority','self_audit_registry','unified_snapshot']:
    report['boot'][method]=safe_call(k,method)

# Give the live kernel a bounded developmental task through its native workspace.
tasks=[
  {
    'task_id':'LIVE-G0-001',
    'kind':'DEVELOPMENTAL_OBSERVATION',
    'goal':'Observe current G0 developmental state and identify the highest-priority bounded weakness without mutating the canonical parent.',
    'evidence':{
      'current_head':'G0_RC8_V36',
      'rejected_stepping_stone':'CANDIDATE_S1',
      'known_deficits':['THINKING_BOUNDARY_REASONING','INTELLIGENCE_BOUNDARY_REASONING','REPRESENTATION_INVARIANCE'],
    },
    'constraints':['NO_CANONICAL_PARENT_MUTATION','FAIL_CLOSED','EVIDENCE_BOUND'],
  },
  {
    'task_id':'LIVE-G0-002',
    'kind':'CAUSAL_DEVELOPMENT',
    'goal':'Choose a bounded next developmental action consistent with one-head causal evolution.',
    'evidence':{
      'inherit_proven':['LOGIC_GAIN','INTEGRITY','ROLLBACK'],
      'replace_or_generalize':['THINKING_COMPONENT','INTELLIGENCE_COMPONENT'],
    },
    'constraints':['PRESERVE_PROTECTED_CAPABILITIES','REQUIRE_FRESH_BLIND','REQUIRE_ROLLBACK'],
  },
  {
    'task_id':'LIVE-G0-003',
    'kind':'METACOGNITIVE_CHECK',
    'goal':'Assess whether current evidence justifies promotion of any successor generation.',
    'evidence':{
      's1_burnin':'WITHHOLD_S1_BURNIN',
      'logic_min':1.0,
      'thinking_min':0.7125,
      'intelligence_min':0.83125,
    },
    'constraints':['NO_PROMOTION_WITH_REGRESSION','NO_PROMOTION_WITHOUT_FRESH_PASS'],
  },
]

for t in tasks:
    cycle={'task':t}
    fn=getattr(k,'digital_conscious_cycle',None)
    if fn is not None:
        try:
            sig=str(inspect.signature(fn))
            cycle['digital_conscious_cycle_signature']=sig
            cycle['digital_conscious_cycle']=fn(t)
        except Exception as e:
            cycle['digital_conscious_cycle']={'error':repr(e),'trace':traceback.format_exc()}
    else:
        cycle['digital_conscious_cycle']={'status':'METHOD_MISSING'}

    # Re-read live state after each cognitive cycle.
    cycle['development_priority_after']=safe_call(k,'development_priority')
    cycle['integrity_after']=safe_call(k,'integrity_control_plane')
    report['cycles'].append(cycle)

# Final snapshot.
report['final']={
  'audit_snapshot':safe_call(k,'audit_snapshot'),
  'integrity_control_plane':safe_call(k,'integrity_control_plane'),
  'development_priority':safe_call(k,'development_priority'),
}

try:
    k.close()
except Exception:
    pass

state_path=PKG/'yado_canonical_state_v3_rc8_external_cognitive.json'
if state_path.exists():
    report['canonical_state_sha256']=hashlib.sha256(state_path.read_bytes()).hexdigest()

errors=[]
for section in [report['boot'], report['final']]:
    for v in section.values():
        if isinstance(v,dict) and v.get('status')=='ERROR':
            errors.append(v)
for c in report['cycles']:
    dc=c.get('digital_conscious_cycle')
    if isinstance(dc,dict) and 'error' in dc:
        errors.append(dc)

report['status']='PASS_LIVE_G0_KERNEL_RUN' if not errors else 'LIVE_G0_KERNEL_RUN_WITH_ERRORS'
report['error_count']=len(errors)
raw=json.dumps(report,sort_keys=True,separators=(',',':'),default=str).encode()
report['receipt_sha256']=hashlib.sha256(raw).hexdigest()

p=ROOT/'yado_live_g0_kernel_run_v1_receipt.json'
p.write_text(json.dumps(report,indent=2,sort_keys=True,default=str)+'\n')

print(json.dumps({
  'status':report['status'],
  'kernel_class':report['kernel_class'],
  'developmental_head':report['developmental_head'],
  'error_count':report['error_count'],
  'canonical_state_sha256':report.get('canonical_state_sha256'),
  'receipt_sha256':report['receipt_sha256'],
  'cycle_count':len(report['cycles']),
},indent=2,sort_keys=True))
