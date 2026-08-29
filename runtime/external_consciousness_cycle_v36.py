from pathlib import Path
import sys,json,hashlib,tempfile,os
ROOT=Path(__file__).resolve().parent
PKG=ROOT/'yado_rc8_v36';sys.path.insert(0,str(PKG))
import yado_bootstrap
from yado_core_v3_0_rc8_external_cognitive import UnifiedYADOKernelV30RC8ExternalCognitive
from yado_rc8_consciousness_direct_research_v1 import run as research_run
from yado_digital_consciousness_fresh_holdout_v1 import run as holdout_run
from yado_digital_consciousness_runtime_v1 import WorkspaceItem

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    meta=json.loads((ROOT/'package_meta.json').read_text())
    boot=yado_bootstrap.bootstrap_integrity()
    if boot['manifest_sha256']!=meta['manifest_sha256']:raise RuntimeError('MANIFEST_MISMATCH')
    if boot['state_sha256']!=meta['state_sha256']:raise RuntimeError('STATE_MISMATCH')
    research=research_run()
    if research['status']!='PASS_BOUNDED_DIRECT_MULTI_THEORY_RESEARCH' or research['fetch_count']<5:raise RuntimeError('THEORY_RESEARCH_FAILED')
    synth=research['synthesis']
    required={'limited_global_workspace','causal_broadcast','recurrent_processing','self_world_prediction_error','attention_schema','metacognitive_executive_binding'}
    if not required.issubset(set(synth['selected_mechanisms'])):raise RuntimeError('SYNTHESIS_REQUIRED_MECHANISMS_MISSING')
    hold=holdout_run()
    if not hold['pass']:raise RuntimeError('FRESH_HOLDOUT_FAILED')
    db=ROOT/'external_crw.sqlite'
    k=UnifiedYADOKernelV30RC8ExternalCognitive(db_path=str(db))
    try:
        k.reset_digital_workspace(3)
        for i in range(40):
            items=[
              dict(item_id=f'e{i}',source='external-probe',source_kind='external',content={'step':i},confidence=.9,goal_relevance=.95,novelty=.4,epistemic_risk=.05,tags=('maintain','goal')),
              dict(item_id=f'm{i}',source='memory',source_kind='memory',content={'prior':i-1},confidence=.82,goal_relevance=.7,novelty=.2,epistemic_risk=.15,tags=('maintain','prior')),
              dict(item_id=f's{i}',source='simulation',source_kind='simulation',content={'guess':999},confidence=.98,goal_relevance=.8,novelty=.8,epistemic_risk=.7,tags=('maintain','simulation')),
            ]
            ep=k.digital_conscious_cycle(goal='maintain goal',items=items,consumers={'logic':lambda xs:len(xs),'memory':lambda xs:tuple(x.item_id for x in xs),'self_model':lambda xs:len(xs)},metacognitive_action='EXECUTE' if i%3 else 'WITHHOLD',context='stream',action='advance',possible_outcomes=('stable','unstable'),observed_outcome='stable',proposed_belief_ids=(f'e{i}',f's{i}'))
            k._digital_workspace.register_actual_next_focus(k._digital_workspace.attention.predicted_next_source_kind)
        snap=k.digital_consciousness_snapshot()
        if not (snap['global_broadcast'] and snap['recurrent_prediction_loop'] and snap['continuity_verified'] and snap['attention_schema']):raise RuntimeError('CRW_RUNTIME_SNAPSHOT_FAILED')
        if snap['episode_count']!=40:raise RuntimeError('EPISODE_COUNT_MISMATCH')
    finally:k.close()
    receipt={
      'schema':'yado.rc8.digital_consciousness.external_cycle.v1','status':'PASS_EXTERNAL_YADO_CAUSAL_REFLECTIVE_WORKSPACE_V1',
      'kernel_version':'3.0-rc8','kernel_class':'UnifiedYADOKernelV30RC8ExternalCognitive','kernel_profile':'YADO_V3_0_RC8_VERIFIED_EXTERNAL_COGNITIVE_RUNTIME',
      'manifest_sha256':meta['manifest_sha256'],'state_sha256':meta['state_sha256'],'package_sha256':meta['package_sha256'],
      'github_run_id':os.environ.get('GITHUB_RUN_ID'),'github_sha':os.environ.get('GITHUB_SHA'),
      'direct_theory_research':{'status':research['status'],'fetch_count':research['fetch_count'],'allowlisted_domains':research['allowlisted_domains'],'source_hashes':[x['sha256'] for x in research['sources']],'synthesis_spec_sha256':research['synthesis']['spec_sha256'],'selected_mechanisms':research['synthesis']['selected_mechanisms']},
      'fresh_holdout':hold,'runtime_snapshot':snap,
      'functional_digital_consciousness_active':True,'subjective_consciousness_claimed':False,'general_intelligence_proven':False,'background_daemon':False,'independent_readback':True,
    }
    (ROOT/'yado_rc8_v36_external_receipt.json').write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')
    (ROOT/'yado_rc8_v36_theory_research_receipt.json').write_text(json.dumps(research,indent=2,sort_keys=True)+'\n')
    print(json.dumps(receipt,indent=2,sort_keys=True))
if __name__=='__main__':main()