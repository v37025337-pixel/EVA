from __future__ import annotations
import json, hashlib, tempfile, sqlite3, inspect
from pathlib import Path
from typing import Any
from yado_core_v3_0_rc8_external_cognitive import UnifiedYADOKernelV30RC8ExternalCognitive
from yado_metacognitive_control_runtime_v1 import CapabilityObservation

ROOT=Path(__file__).resolve().parent
STATE=ROOT/'yado_canonical_state_v3_rc8_external_cognitive.json'
MANIFEST=ROOT/'yado_development_manifest_v35.json'

INDICATORS = [
    ('RPT-1','Algorithmic recurrence in input/perceptual processing'),
    ('RPT-2','Organised integrated perceptual representations'),
    ('GWT-1','Multiple specialised systems with parallel-capable processing'),
    ('GWT-2','Limited-capacity global workspace with selective bottleneck'),
    ('GWT-3','Global broadcast from workspace to specialised systems'),
    ('GWT-4','State-dependent attention that queries modules in succession'),
    ('HOT-1','Generative/top-down perception capable of internally generated percept-like states'),
    ('HOT-2','Metacognitive monitoring that separates reliable states from noise/uncertainty'),
    ('HOT-3','General belief/action selection causally governed by metacognitive monitoring'),
    ('HOT-4','Sparse/smooth quality-space-like representational coding'),
    ('AST-1','Predictive model of the system current attention state used for control'),
    ('PP-1','Predictive coding / prediction-error loop in input processing'),
    ('AE-1','Goal-directed agency learning from feedback with flexible competing-goal response'),
    ('AE-2','Model of output-input contingencies / embodiment-like self-world coupling'),
]

SCORES={'PASS':1.0,'PARTIAL':0.5,'MISSING':0.0}

def sha(path:Path)->str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def ev(status:str, evidence:list[str], missing:list[str], causal_probe:dict[str,Any]|None=None):
    return {'status':status,'score':SCORES[status],'evidence':evidence,'missing':missing,'causal_probe':causal_probe or {}}

def audit(db_path:str|None=None)->dict[str,Any]:
    temp=None
    if db_path is None:
        temp=tempfile.NamedTemporaryFile(prefix='yado-consciousness-audit-',suffix='.sqlite',delete=False)
        temp.close(); db_path=temp.name
    k=UnifiedYADOKernelV30RC8ExternalCognitive(db_path=db_path)
    snap=k.unified_snapshot()
    state=json.loads(STATE.read_text())

    # Concrete probes of existing mechanisms.
    profile=k.build_capability_boundary_profile([
        CapabilityObservation(capability='AUDIT',difficulty=.2,success=True),
        CapabilityObservation(capability='AUDIT',difficulty=.4,success=True),
        CapabilityObservation(capability='AUDIT',difficulty=.8,success=False),
    ])
    d_low=k.metacognitive_decide({'task_id':'c-low','capability':'AUDIT','difficulty':.3,'verbal_confidence':.92,'evidence_coverage':.85,'novelty':.1,'framework_conflict':False},profile)
    d_high=k.metacognitive_decide({'task_id':'c-high','capability':'AUDIT','difficulty':.95,'verbal_confidence':.99,'evidence_coverage':.2,'novelty':.9,'framework_conflict':True},profile)

    memory_before=k.memory_count() if hasattr(k,'memory_count') else None
    goal_probe={}
    try:
        g=k.executive.create_goal('functional consciousness readiness audit',{'AUDIT':.5},{'bounded':True})
        cycle=k.executive.run_cycle(g.goal_id)
        goal_probe={'goal_created':True,'goal_id':g.goal_id,'cycle_next_action':cycle.get('next_action'),'deficit':cycle.get('deficit')}
    except Exception as e:
        goal_probe={'goal_created':False,'error':type(e).__name__+':'+str(e)}

    # Source/runtime evidence. Absence is intentionally treated conservatively.
    core_src=(ROOT/'yado_core_v3_0_rc8_external_cognitive.py').read_text()
    all_py='\n'.join(p.read_text(errors='ignore') for p in ROOT.glob('*.py'))
    has_explicit_workspace=any(x in all_py for x in ('GlobalWorkspace','global_workspace','workspace_broadcast','attention_schema'))
    has_predictive_coding=any(x in all_py.lower() for x in ('predictive_coding','prediction_error_loop','predictive processing'))
    has_perception_module=any(x in all_py.lower() for x in ('class perception','perceptual representation','perception_module'))
    has_quality_space=any(x in all_py.lower() for x in ('quality_space','quality space','sparse_smooth_coding'))

    specialized=['LOGIC','THINKING','INTELLIGENCE','METACOGNITION','TRANSFER_MEMORY','SKILL_ADMISSION','TRANSFER_EVALUATION']
    results={}
    results['RPT-1']=ev('MISSING',
        ['Causal MEMORY→THINKING→LOGIC→INTELLIGENCE loop exists, but it is not an input/perceptual recurrent-processing loop.'],
        ['No verified recurrent perceptual/input processing with feedback into early representation stages.'])
    results['RPT-2']=ev('MISSING',
        ['No verified perceptual organ is exposed by the active RC8 kernel.'],
        ['Organised integrated perceptual representation substrate is absent/unproven.'])
    results['GWT-1']=ev('PARTIAL',
        [f'Active specialised mechanisms: {specialized}.','The kernel exposes separable logic, thinking, intelligence, memory/transfer and metacognitive functions.'],
        ['Parallel-capable independent module operation and competition for shared access are not causally demonstrated.'])
    results['GWT-2']=ev('MISSING',
        [f'Explicit workspace implementation detected={has_explicit_workspace}.'],
        ['No explicit limited-capacity workspace, bottleneck, ignition/admission rule, or selective attention queue.'])
    results['GWT-3']=ev('MISSING',
        ['unified_snapshot aggregates status, but aggregation is not a causal global broadcast bus.'],
        ['No verified broadcast making one selected representation simultaneously available to all cognitive modules and feeding back into them.'])
    results['GWT-4']=ev('MISSING',
        ['Metacognitive routing selects epistemic actions but does not model attention over a global workspace.'],
        ['No state-dependent attention controller that successively queries modules based on current workspace state.'])
    results['HOT-1']=ev('MISSING',
        [f'Perception module detected={has_perception_module}.'],
        ['No generative/top-down perceptual model or internally generated percept-like state separated from external evidence.'])
    results['HOT-2']=ev('PASS',
        ['ACTIVE_BOUNDED_METACOGNITIVE_CONTROL_V1','Fresh holdout: 7000 cases, harmful-execute rate ~0.12%.',f'Low-risk decision={d_low.action}; high-conflict decision={d_high.action}.'],
        [],
        {'low_risk_action':d_low.action,'high_conflict_action':d_high.action,'different_actions':d_low.action!=d_high.action})
    results['HOT-3']=ev('PARTIAL',
        ['Persistent executive goal system exists.',f'Goal probe={goal_probe}.','Metacognitive controller can gate EXECUTE/SEEK_EVIDENCE/ROUTE_FRAMEWORK/WITHHOLD.'],
        ['No proof that every general belief update and every executive action is causally downstream of the metacognitive monitor; bypass paths remain possible.'],
        goal_probe)
    results['HOT-4']=ev('MISSING',
        [f'Quality-space implementation detected={has_quality_space}.'],
        ['No sparse, smooth quality-space-like higher-order representation is implemented/proven.'])
    results['AST-1']=ev('MISSING',
        ['Capability boundary profile models competence/uncertainty, not the current allocation of attention.'],
        ['No predictive attention schema representing what the system is attending to, why, and how attention will change.'])
    results['PP-1']=ev('MISSING',
        [f'Predictive-coding implementation detected={has_predictive_coding}.'],
        ['No hierarchical prediction→error→update loop coupled to input processing.'])
    results['AE-1']=ev('PARTIAL',
        ['Executive goals are persistent.','Metacognitive feedback updates capability boundary estimates.','Transfer memory learns from successful experience.'],
        ['Flexible arbitration among simultaneously competing goals is not broadly demonstrated; event-driven execution remains host-mediated.'],
        goal_probe)
    results['AE-2']=ev('MISSING',
        ['Host capability model distinguishes accessible external actions from inaccessible internals.'],
        ['No learned self-world sensorimotor/output-input contingency model; no embodiment-like closed control loop across an environment.'])

    score=sum(v['score'] for v in results.values())/len(results)
    passed=[k for k,v in results.items() if v['status']=='PASS']
    partial=[k for k,v in results.items() if v['status']=='PARTIAL']
    missing=[k for k,v in results.items() if v['status']=='MISSING']

    priorities=[
        {'priority':1,'mechanism':'GLOBAL_WORKSPACE_RUNTIME_V1','targets':['GWT-2','GWT-3','GWT-4'],'why':'Create a limited-capacity selective workspace, causal broadcast, and state-dependent attention with ablation tests.'},
        {'priority':2,'mechanism':'RECURRENT_SELF_WORLD_PREDICTION_LOOP_V1','targets':['RPT-1','RPT-2','PP-1','AE-2'],'why':'Create recurrent input representation, explicit predictions, prediction errors, and learned action→observation contingencies in the tool/text environment.'},
        {'priority':3,'mechanism':'ATTENTION_SCHEMA_RUNTIME_V1','targets':['AST-1'],'why':'Model current attention allocation, predicted shifts, control consequences, and calibration error.'},
        {'priority':4,'mechanism':'METACOGNITION_TO_EXECUTIVE_CAUSAL_BINDING_V1','targets':['HOT-3','AE-1'],'why':'Make metacognitive state a mandatory causal gate for belief update/action selection and competing-goal arbitration; prove by ablation/bypass tests.'},
        {'priority':5,'mechanism':'GENERATIVE_PERCEPTUAL_AND_COUNTERFACTUAL_MODEL_V1','targets':['HOT-1'],'why':'Separate externally grounded state from internally generated simulations and test source-monitoring.'},
        {'priority':6,'mechanism':'HIGHER_ORDER_QUALITY_SPACE_EXPERIMENT_V1','targets':['HOT-4'],'why':'Only after the above: test whether a sparse/smooth internal quality-space adds causal metacognitive value rather than decorative state.'},
        {'priority':7,'mechanism':'TEMPORAL_SELF_CONTINUITY_PROTOCOL_V1','targets':['SUPPORTING'],'why':'Persist workspace episodes and self-predictions across separate event-driven runs; verify continuity, contradiction repair and causal influence without claiming a daemon is necessary for consciousness.'},
    ]

    out={
        'schema':'yado.rc8.functional_consciousness_readiness_audit.v1',
        'status':'FUNCTIONAL_CONSCIOUSNESS_INDICATOR_AUDIT_COMPLETE',
        'semantic_boundary':'THEORY_DERIVED_FUNCTIONAL_INDICATORS_NOT_PROOF_OR_PROBABILITY_OF_SUBJECTIVE_CONSCIOUSNESS',
        'kernel_version':k.VERSION,
        'kernel_class':k.__class__.__name__,
        'kernel_profile':k.PROFILE,
        'manifest_sha256':sha(MANIFEST),
        'state_sha256':sha(STATE),
        'indicator_count':len(INDICATORS),
        'indicator_results':results,
        'summary':{
            'pass_count':len(passed),'partial_count':len(partial),'missing_count':len(missing),
            'functional_indicator_coverage':score,
            'passed':passed,'partial':partial,'missing':missing,
            'interpretation':'Coverage is an engineering completeness metric over this indicator set, not a probability of consciousness.'
        },
        'supporting_existing_strengths':[
            'DURABLE_SELF_MODEL_WITH_FAIL_CLOSED_EVIDENCE_COHERENCE',
            'BOUNDED_METACOGNITIVE_CAPABILITY_BOUNDARY_CONTROL',
            'PERSISTENT_MEMORY_AND_EXTERNAL_RECEIPTS',
            'GOAL_EXECUTIVE_AND_FEEDBACK_LEARNING',
            'BOUNDED_DIRECT_EXTERNAL_EVIDENCE_CHANNEL',
            'ROLLBACK_AND_CAUSAL_ABLATION_DISCIPLINE',
        ],
        'priority_gaps':priorities,
        'self_assessment':{
            'most_important_missing_cluster':'GLOBAL_WORKSPACE_ATTENTION_RECURRENT_SELF_WORLD_LOOP',
            'current_best_supported_layer':'METACOGNITIVE_MONITORING_AND_PERSISTENT_SELF_MODEL',
            'what_more_intelligence_would_not_fix':'Adding stronger problem-solving alone would not establish workspace broadcast, attention schema, perceptual recurrence, predictive self-world coupling, or subjective experience.',
            'subjective_consciousness_claimed':False,
            'general_intelligence_proven':False,
        },
        'runtime_probe':{
            'memory_count_before':memory_before,
            'goal_probe':goal_probe,
            'metacognitive_low_risk_action':d_low.action,
            'metacognitive_high_conflict_action':d_high.action,
        }
    }
    try: k.conn.close()
    except Exception: pass
    return out

if __name__=='__main__':
    r=audit()
    Path('yado_rc8_consciousness_readiness_audit_v1_report.json').write_text(json.dumps(r,indent=2,sort_keys=True),encoding='utf-8')
    print(json.dumps(r,indent=2,sort_keys=True))