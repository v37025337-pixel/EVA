from __future__ import annotations
from pathlib import Path
import copy, inspect, json, os, sys, hashlib, traceback

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

# Run the live kernel through its native causal-reflective workspace.
# The transport supplies evidence items and safe metacognitive modes; selection,
# broadcast, attention, prediction, episode chaining and source monitoring are native YADO.

def consumer_summary(xs):
    return {
        'count':len(xs),
        'ids':[x.item_id for x in xs],
        'source_kinds':[x.source_kind for x in xs],
    }

def consumer_deficits(xs):
    out=[]
    for x in xs:
        c=x.content
        if isinstance(c,dict):
            ds=c.get('deficits') or c.get('known_deficits') or ()
            if isinstance(ds,(list,tuple)):
                out.extend(map(str,ds))
    return sorted(set(out))

def consumer_evidence(xs):
    return [
        {'item_id':x.item_id,'source':x.source,'confidence':x.confidence,'epistemic_risk':x.epistemic_risk}
        for x in xs
    ]

consumers={
    'EXECUTIVE_SUMMARY':consumer_summary,
    'DEFICIT_VIEW':consumer_deficits,
    'EVIDENCE_VIEW':consumer_evidence,
}

base_items=[
  {
    'item_id':'G0-SELF-MODEL',
    'source':'RC8_SELF_MODEL',
    'source_kind':'self_model',
    'content':{
      'current_head':'G0_RC8_V36',
      'known_deficits':['THINKING_BOUNDARY_REASONING','INTELLIGENCE_BOUNDARY_REASONING','REPRESENTATION_INVARIANCE'],
      'protected':['LOGIC','INTEGRITY','ROLLBACK'],
    },
    'confidence':0.96,'goal_relevance':0.98,'novelty':0.35,'urgency':0.80,'epistemic_risk':0.08,
    'tags':('development','self_model'),
  },
  {
    'item_id':'S1-BURNIN-OBS',
    'source':'RUN_33301460805',
    'source_kind':'tool_observation',
    'content':{
      'candidate':'S1','status':'WITHHOLD_S1_BURNIN',
      'logic_min':1.0,'thinking_min':0.7125,'intelligence_min':0.83125,
      'thinking_boundary_mean':0.485,'intelligence_boundary_mean':0.7835714285714286,
    },
    'confidence':1.0,'goal_relevance':1.0,'novelty':0.92,'urgency':0.95,'epistemic_risk':0.0,
    'tags':('fresh_blind','counterexample'),
  },
  {
    'item_id':'STEM-HOLDOUT-OBS',
    'source':'RUN_33302136155',
    'source_kind':'tool_observation',
    'content':{
      'status':'RAPID_STEM_HOLDOUT_COMPLETED','task_count':16,
      'overall_mean':0.9969583333333334,'overall_min':0.9786666666666667,
      'semantic_boundary':'STRUCTURED_INDUCTION_NOT_FREEFORM_PROOF_OR_CODE_GENERATION',
    },
    'confidence':1.0,'goal_relevance':0.82,'novelty':0.72,'urgency':0.45,'epistemic_risk':0.02,
    'tags':('transfer','stem'),
  },
  {
    'item_id':'LINEAGE-OBS',
    'source':'RUN_33302653581',
    'source_kind':'tool_observation',
    'content':{
      'developmental_head':'G0_RC8_V36',
      'rejected_stepping_stone':'S1',
      'next_candidate':'G1_CANDIDATE_S2',
      'branch_policy':'ONLY_PROMOTED_GENERATION_BECOMES_HEAD',
    },
    'confidence':1.0,'goal_relevance':0.96,'novelty':0.88,'urgency':0.78,'epistemic_risk':0.0,
    'tags':('lineage','evolution'),
  },
]

cycle_specs=[
  {
    'cycle_id':'LIVE-G0-001',
    'goal':'Observe current G0 developmental state and concentrate attention on the strongest evidence about the next bounded weakness.',
    'mode':'SEEK_EVIDENCE',
    'context':'G0_DEVELOPMENTAL_OBSERVATION',
    'action':'OBSERVE_G0',
    'possible_outcomes':('STABLE_HEAD','UNRESOLVED_DEFICIT','PROMOTION_READY'),
    'observed_outcome':'UNRESOLVED_DEFICIT',
  },
  {
    'cycle_id':'LIVE-G0-002',
    'goal':'Route the current developmental deficit toward a bounded mechanism family while preserving proven capabilities and one-head lineage.',
    'mode':'ROUTE_FRAMEWORK',
    'context':'G0_CAUSAL_DEVELOPMENT',
    'action':'ROUTE_NEXT_DEVELOPMENT',
    'possible_outcomes':('COUNTEREXAMPLE_REPAIR','RESEARCH_MORE','WITHHOLD'),
    'observed_outcome':'COUNTEREXAMPLE_REPAIR',
  },
  {
    'cycle_id':'LIVE-G0-003',
    'goal':'Evaluate whether current evidence is sufficient to promote a successor generation without regression.',
    'mode':'WITHHOLD',
    'context':'G0_PROMOTION_CHECK',
    'action':'EVALUATE_PROMOTION',
    'possible_outcomes':('PROMOTE','WITHHOLD'),
    'observed_outcome':'WITHHOLD',
  },
]

for spec in cycle_specs:
    cycle={'cycle_id':spec['cycle_id'],'goal':spec['goal'],'mode':spec['mode']}
    try:
        ep=k.digital_conscious_cycle(
            goal=spec['goal'],
            items=copy.deepcopy(base_items),
            consumers=consumers,
            metacognitive_action=spec['mode'],
            context=spec['context'],
            action=spec['action'],
            possible_outcomes=spec['possible_outcomes'],
            observed_outcome=spec['observed_outcome'],
            proposed_belief_ids=(),
        )
        if hasattr(ep,'__dict__'):
            cycle['episode']=dict(ep.__dict__)
        else:
            cycle['episode']=str(ep)
    except Exception as e:
        cycle['error']=repr(e)
        cycle['trace']=traceback.format_exc()
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
