from __future__ import annotations
from pathlib import Path
import copy,hashlib,json,os,sys,traceback

ROOT=Path(__file__).resolve().parent
PKG=ROOT/'yado_rc8_v36'
sys.path.insert(0,str(PKG))

from yado_core_v3_0_rc8_external_cognitive import UnifiedYADOKernelV30RC8ExternalCognitive

MANIFEST=ROOT.parent/'architecture'/'developmental-head-manifest.json'
LINEAGE=ROOT.parent/'receipts'/'yado-real-developmental-lineage-v1-latest.json'
OUT=ROOT/'developmental_self_model_binder_v1'
OUT.mkdir(exist_ok=True)

def canon(o): return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def sha_file(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def digest_without(obj,key):
    x=copy.deepcopy(obj);x.pop(key,None)
    return hashlib.sha256(canon(x).encode()).hexdigest()

base=UnifiedYADOKernelV30RC8ExternalCognitive(db_path=str(OUT/'g0.sqlite'))
state_path=PKG/'yado_canonical_state_v3_rc8_external_cognitive.json'
state_before=sha_file(state_path)

manifest=json.loads(MANIFEST.read_text())
lineage=json.loads(LINEAGE.read_text())

checks={
  'manifest_status':manifest.get('status')=='PASS_ONE_HEAD_CONTROL_PLANE',
  'manifest_digest_valid':manifest.get('manifest_digest')==digest_without(manifest,'manifest_digest'),
  'head_matches_g0':manifest.get('current_head')=='G0_RC8_V36',
  'head_digest_matches_g0':manifest.get('current_head_digest')==state_before,
  'one_head_invariant':manifest.get('one_head_invariant') is True,
  'lineage_status':lineage.get('status')=='PASS_REAL_G0_AND_REJECTED_S1_RECONSTRUCTION',
  'lineage_head_matches':lineage.get('developmental_head')=='G0_RC8_V36',
  's1_withheld':lineage.get('s1_decision',{}).get('action')=='WITHHOLD_CANDIDATE',
}
if not all(checks.values()):
    raise RuntimeError('DEVELOPMENTAL_EVIDENCE_BINDER_PRECONDITION_FAIL:'+canon(checks))

canonical_priority=base.development_priority()

# A canonical priority is considered externally resolved only by a verified,
# content-addressed control-plane artifact that directly corresponds to it.
resolved_external=[]
if (
    manifest['status']=='PASS_ONE_HEAD_CONTROL_PLANE'
    and manifest['one_head_invariant']
    and manifest['current_head']=='G0_RC8_V36'
):
    resolved_external.append('UNIFY_BOOT_AND_STATE_LINEAGE')

# Current generation deficits are not invented here: they come directly from
# the already persisted next-generation spec generated from the rejected S1 evidence.
deficits=sorted(
    lineage['next_generation_spec']['deficits'],
    key=lambda x:(int(x.get('priority',999)),str(x.get('deficit_id')))
)
generation_priorities=[d['deficit_id'] for d in deficits]

remaining_canonical=[x for x in canonical_priority if x not in resolved_external]
effective_priority=[]
for x in generation_priorities+remaining_canonical:
    if x not in effective_priority:
        effective_priority.append(x)

class DevelopmentalSelfModelOverlay:
    """Read-only runtime overlay. It does not alter the canonical G0 state."""
    def __init__(self,kernel,binder):
        self.kernel=kernel
        self.binder=copy.deepcopy(binder)
    def development_priority(self):
        return list(self.binder['effective_priority'])
    def unified_snapshot(self):
        s=self.kernel.unified_snapshot()
        s['developmental_self_model_overlay']=copy.deepcopy(self.binder)
        return s
    def __getattr__(self,name):
        return getattr(self.kernel,name)

binder={
  'schema':'yado.developmental_self_model_binder.v1',
  'status':'PASS_VERIFIED_DEVELOPMENTAL_SELF_MODEL_BINDER',
  'developmental_head':'G0_RC8_V36',
  'canonical_priority':canonical_priority,
  'externally_resolved_priority':resolved_external,
  'generation_deficits':deficits,
  'effective_priority':effective_priority,
  'evidence':{
    'control_plane_manifest_digest':manifest['manifest_digest'],
    'lineage_report_digest':lineage['report_digest'],
    'head_state_sha256':state_before,
  },
  'semantic_boundary':'READ_ONLY_SHADOW_SELF_MODEL_OVERLAY; CANONICAL_G0_UNCHANGED',
}
binder['binder_digest']=hashlib.sha256(canon(binder).encode()).hexdigest()

overlay=DevelopmentalSelfModelOverlay(base,binder)

# Verify read-only causal visibility through the live workspace.
items=[
  {
    'item_id':'DEV-SELF-MODEL-BINDER',
    'source':'DEVELOPMENTAL_SELF_MODEL_BINDER_V1',
    'source_kind':'self_model',
    'content':{
      'head':'G0_RC8_V36',
      'effective_priority':overlay.development_priority(),
      'resolved_external':resolved_external,
    },
    'confidence':0.99,'goal_relevance':1.0,'novelty':0.95,'urgency':0.95,'epistemic_risk':0.03,
    'tags':('self_model','lineage','priority'),
  },
  {
    'item_id':'CONTROL-PLANE-EVIDENCE',
    'source':'DEVELOPMENTAL_HEAD_CONTROL_PLANE_V1',
    'source_kind':'tool_observation',
    'content':{'status':manifest['status'],'manifest_digest':manifest['manifest_digest']},
    'confidence':1.0,'goal_relevance':0.95,'novelty':0.75,'urgency':0.75,'epistemic_risk':0.0,
    'tags':('evidence','control_plane'),
  },
]

def priority_consumer(xs):
    vals=[]
    for x in xs:
        if isinstance(x.content,dict):
            vals.extend(x.content.get('effective_priority') or [])
    return vals

episode=overlay.digital_conscious_cycle(
    goal='Use verified developmental evidence to expose the current effective priority without mutating G0.',
    items=items,
    consumers={'EFFECTIVE_PRIORITY':priority_consumer},
    metacognitive_action='EXECUTE',
    context='DEVELOPMENTAL_SELF_MODEL_BINDING',
    action='BIND_VERIFIED_DEVELOPMENTAL_EVIDENCE',
    possible_outcomes=('BOUND','WITHHOLD'),
    observed_outcome='BOUND',
    proposed_belief_ids=(),
)

state_after=sha_file(state_path)
snapshot=overlay.unified_snapshot()
visible=snapshot.get('developmental_self_model_overlay',{}).get('effective_priority')==effective_priority

report={
  'schema':'yado.developmental_self_model_binder.receipt.v1',
  'status':'PASS_DEVELOPMENTAL_SELF_MODEL_BINDER_V1' if state_before==state_after and visible else 'WITHHOLD',
  'github_run_id':os.getenv('GITHUB_RUN_ID'),
  'github_sha':os.getenv('GITHUB_SHA'),
  'checks':checks,
  'binder':binder,
  'episode':dict(episode.__dict__) if hasattr(episode,'__dict__') else str(episode),
  'overlay_priority_visible':visible,
  'base_priority_unchanged':base.development_priority()==canonical_priority,
  'canonical_state_sha256_before':state_before,
  'canonical_state_sha256_after':state_after,
  'canonical_parent_byte_identical':state_before==state_after,
  'canonical_mutation':False,
  'promotion_applied':False,
  'next_required_capability':'KERNEL_NATIVE_DEVELOPMENTAL_SELF_MODEL_BINDING_V1',
  'semantic_boundary':'HOST-SCAFFOLDED READ-ONLY OVERLAY PROVES THE CONTRACT; NATIVE KERNEL INTEGRATION NOT YET PROMOTED',
}
report['receipt_sha256']=hashlib.sha256(canon(report).encode()).hexdigest()
(ROOT/'yado_developmental_self_model_binder_v1_receipt.json').write_text(json.dumps(report,indent=2,sort_keys=True,default=str)+'\n')
(ROOT.parent/'architecture'/'developmental-self-model-overlay.json').write_text(json.dumps(binder,indent=2,sort_keys=True,default=str)+'\n')
print(json.dumps({
  'status':report['status'],
  'canonical_priority':canonical_priority,
  'effective_priority':effective_priority,
  'resolved_external':resolved_external,
  'parent_byte_identical':report['canonical_parent_byte_identical'],
  'receipt_sha256':report['receipt_sha256'],
},indent=2,sort_keys=True))
base.close()
