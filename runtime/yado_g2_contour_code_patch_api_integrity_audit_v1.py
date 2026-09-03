from __future__ import annotations
from pathlib import Path
import ast,copy,hashlib,json,os,py_compile,subprocess,sys

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
PKG=ROOT/'yado_rc8_v36'
sys.path[:0]=[str(ROOT),str(PKG)]

from yado_evolution_ledger_v2 import validate_ledger_v2
from yado_unified_core_v1 import UnifiedYADOCoreV1
from yado_bounded_capability_router_v1 import BoundedCapabilityRouterLearnerV1
from yado_conjunctive_rule_inducer_v1 import ConjunctiveRuleInducerV1
from yado_g2_typed_recurrent_capability_graph_runtime_v1 import G2TypedRecurrentCapabilityGraphRuntimeV1
from yado_g2_contextual_stream_capability_adapter_v1 import ContextualStreamCapabilityAdapterV1
from yado_g2_composite_transfer_repair_adapter_v1 import G2CompositeTransferRepairAdapterV1

OUTDIR=REPO/'audits';OUTDIR.mkdir(exist_ok=True)
OUT=OUTDIR/'yado-g2-contour-code-patch-api-integrity-audit-v1.json'

CAP_CONJ='ALG-CONJUNCTIVE-RULE-INDUCER-V1'
CAP_REL='ALG-BOUNDED-DNF-RELATION-POLICY-INDUCER-V1'
CAP_BUD='ALG-BUDGETED-STAGE-POLICY-V1'
CAP_RES='RESOURCE-PORTFOLIO-V1'
NEW_LOGIC='ALG-G2-BUDGET-ADAPTIVE-COMPOSITIONAL-LOGIC-V2'
NEW_THINK='ALG-G2-WORK-BUDGET-ADAPTIVE-CONTINGENT-PLANNER-V2'
NEW_INTEL='ALG-G2-COVERAGE-PRUNED-COMPOSITIONAL-SCHEMA-ROUTER-V3'

def load(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def add(fs,sev,code,msg,details=None):
    fs.append({'severity':sev,'code':code,'message':msg,'details':details})

head=load(REPO/'canonical/yado-main-head-g2.json')
core=load(REPO/'canonical/yado-unified-core-v1.json')
prov=load(REPO/'canonical/yado-algorithm-provenance-registry-v1.json')
ledger=load(REPO/'architecture/evolution-ledger.json')
arch=load(REPO/'canonical/yado-g2-architecture-v1.json')
portfolio=load(REPO/'resources/yado-unified-external-resource-portfolio-v1.json')
validate_ledger_v2(ledger)
findings=[];checks={}

# Canonical/code integrity.
guard=subprocess.run([sys.executable,str(ROOT/'yado_canonical_invariant_guard_v1.py')],cwd=REPO,capture_output=True,text=True,timeout=60)
checks['canonical_guard']=guard.returncode==0
if not checks['canonical_guard']:add(findings,'CRITICAL','CANONICAL_GUARD_FAIL','Canonical invariant guard failed.',guard.stdout[-4000:]+guard.stderr[-1000:])

compile_errors=[]
compile_scope=list(core.get('active_runtime_sources',[]))+['runtime/yado_unified_core_v1.py']
for rel in sorted(set(compile_scope)):
    p=REPO/rel
    try:py_compile.compile(str(p),doraise=True)
    except Exception as e:compile_errors.append({'path':rel,'error':repr(e)})
checks['active_compile']=not compile_errors
if compile_errors:add(findings,'CRITICAL','ACTIVE_CODE_COMPILE_BREAK','Active G2 code has compile failures.',compile_errors)

# Tracked Python cache is repository garbage, not source.
git_ls=subprocess.run(['git','ls-files'],cwd=REPO,capture_output=True,text=True,timeout=30).stdout.splitlines()
pycache=[x for x in git_ls if x.endswith('.pyc') or '/__pycache__/' in x]
checks['no_tracked_python_cache']=not pycache
if pycache:add(findings,'MEDIUM','TRACKED_PYTHON_CACHE_GARBAGE',f'{len(pycache)} tracked Python cache files should be quarantined/removed.',pycache)

# Architecture plane/component coverage.
planes={p['plane_id']:p for p in core.get('planes',[])}
active_caps=set(head.get('active_capabilities',[]))
plane_components=set()
for p in planes.values():
    plane_components.update(x for x in p.get('active_components',[]) if isinstance(x,str) and not x.endswith('.json'))
unplaced=sorted(c for c in active_caps if c not in plane_components)
checks['active_capabilities_placed']=not unplaced
if unplaced:add(findings,'HIGH','ACTIVE_CAPABILITY_NOT_PLACED_IN_PLANE','Some active capabilities are not represented in an architecture plane.',unplaced)

required_planes={'MEMORY_AND_EXPERIENCE','LOGIC','THINKING_AND_PLANNING','INTELLIGENCE_AND_META_SELECTION','WORKSPACE_AND_INTEGRATION'}
missing_planes=sorted(required_planes-set(planes))
checks['required_contour_planes']=not missing_planes
if missing_planes:add(findings,'CRITICAL','COGNITIVE_PLANE_MISSING','Required cognitive contour plane missing.',missing_planes)

# Build a deterministic current G2 base runtime.
def descriptor(cap,amb=False):
    d={'budget_limited':False,'quota_limited':False,'external_evidence_needed':False,'relation_needed':False,'disjunction_needed':False,'context_ambiguous':amb}
    if not amb:
        if cap==CAP_BUD:d['budget_limited']=True
        elif cap==CAP_RES:d['external_evidence_needed']=True
        elif cap==CAP_REL:d['relation_needed']=True
    return d

def route_cases():
    out=[]
    for _ in range(24):
        for cap in [CAP_CONJ,CAP_REL,CAP_BUD,CAP_RES]:
            out.append({'input':descriptor(cap,False)|{'noise':_ % 3},'expected':cap})
    return out
router=BoundedCapabilityRouterLearnerV1.synthesize(route_cases(),route_cases(),CAP_CONJ,min_support=5)

scalar_cases=[]
for a in [False,True]:
  for b in [False,True]:
    for c in [False,True]:
      for _ in range(5):
        scalar_cases.append({'input':{'condition_a':a,'condition_b':b,'condition_c':c},'expected':'PASS' if a and b and c else 'HOLD'})
scalar=ConjunctiveRuleInducerV1.synthesize('AUDIT_SCALAR','LOGIC',scalar_cases,min_support=2,max_rules=12)

class RelationStub:
    def execute(self,x):
        return 'ALLOW' if x.get('allow') else 'DENY'
relation=RelationStub()
base=G2TypedRecurrentCapabilityGraphRuntimeV1(arch,router,scalar,relation,portfolio)
memory=ContextualStreamCapabilityAdapterV1(base,'BOUNDED_STREAM_CONTEXT_MAP')

# Base contour: intelligence -> logic, intelligence -> thinking, outputs -> memory, memory -> intelligence.
logic_task={'kind':'scalar','descriptor':descriptor(CAP_CONJ),'stream_id':'L1','payload':{'condition_a':True,'condition_b':True,'condition_c':True}}
logic_out=memory.run(logic_task)
checks['base_intelligence_to_logic']=logic_out['context_selected_capability']==CAP_CONJ and logic_out['result']=='PASS'

budget_task={'kind':'budget','descriptor':descriptor(CAP_BUD),'stream_id':'M1','current_confidence':0.2,'target_confidence':0.7,'remaining_budget':5.0,
             'stages':[{'stage_id':'CHEAP','cost':1.0,'expected_gain':0.2,'quota_remaining':1,'available':True,'latency':1.0},
                       {'stage_id':'STRONG','cost':3.0,'expected_gain':0.6,'quota_remaining':1,'available':True,'latency':2.0}]}
bud_out=memory.run(budget_task)
checks['base_intelligence_to_thinking']=bud_out['context_selected_capability']==CAP_BUD and bud_out['result'] in {'CHEAP','STRONG','STOP','WITHHOLD'}
amb=copy.deepcopy(budget_task);amb['descriptor']=descriptor(CAP_BUD,True)
mem_out=memory.run(amb)
abl_out=memory.run(amb,ablated_context=True)
checks['memory_to_intelligence_causal']=mem_out['context_selected_capability']==CAP_BUD and abl_out['context_selected_capability']!=CAP_BUD
checks['logic_thinking_to_memory']=len(base.episodes)>=4 and any(e.get('result')=='PASS' for e in base.episodes) and any(e.get('selected_capability')==CAP_BUD for e in base.episodes)

for k in ['base_intelligence_to_logic','base_intelligence_to_thinking','memory_to_intelligence_causal','logic_thinking_to_memory']:
    if not checks[k]:add(findings,'HIGH','BASE_CONTOUR_BREAK',f'Base recurrent contour check failed: {k}.',{'logic':logic_out,'budget':bud_out,'memory':mem_out,'ablated':abl_out})

# Higher active components work individually.
uc=UnifiedYADOCoreV1(REPO)
rows=[]
for n in range(4):
  for _ in range(4):
    rows.append({'input':{'a':bool(n&1),'b':bool(n&2)},'expected':'EVEN' if bin(n).count('1')%2==0 else 'ODD'})
lm=uc.learn_symmetric_logic(rows)
checks['new_logic_individual']=uc.predict_symmetric_logic(lm,{'a':True,'b':False})=='ODD'
plan=uc.plan_contingent(0.2,0.7,5.0,[{'stage_id':'S1','cost':1,'expected_gain':0.2},{'stage_id':'S2','cost':3,'expected_gain':0.6}])
checks['new_thinking_individual']=plan.action in {'S1','S2'} and plan.feasible
router_model=uc.fit_compositional_capability_router([
 {'input':{'kind':'logic','urgent':False},'expected':NEW_LOGIC},
 {'input':{'kind':'logic','urgent':True},'expected':NEW_LOGIC},
 {'input':{'kind':'plan','urgent':False},'expected':NEW_THINK},
 {'input':{'kind':'plan','urgent':True},'expected':NEW_THINK},
]*4,NEW_LOGIC)
routed=uc.route_capability_set(router_model,{'kind':'plan','urgent':False})
checks['new_intelligence_individual']=NEW_THINK in routed

# Critical integration probe: coordinator cannot execute newer active capabilities through the recurrent dispatcher.
cap_tasks={
 NEW_LOGIC:{'kind':'scalar','payload':{'condition_a':True,'condition_b':True,'condition_c':True}},
 NEW_THINK:{'kind':'budget','requires_capabilities':[NEW_LOGIC],'current_confidence':0.2,'target_confidence':0.7,'remaining_budget':5.0,
            'stages':[{'stage_id':'S1','cost':1,'expected_gain':0.2,'quota_remaining':1,'available':True,'latency':1.0}]}
}
new_dispatch=uc.execute_capability_set(base,[NEW_LOGIC,NEW_THINK],cap_tasks)
checks['new_active_components_recurrently_integrated']=new_dispatch.get('status')=='PASS'
if not checks['new_active_components_recurrently_integrated']:
    add(findings,'HIGH','HIGHER_CONTOUR_DISPATCH_GAP',
        'Newer active logic/thinking components are canonical and individually executable, but the recurrent capability coordinator cannot dispatch them.',
        new_dispatch)

# Memory semantics: current recurrent memory stores task episodes and stream->capability, but higher methods do not consume it automatically.
uc_src=(ROOT/'yado_unified_core_v1.py').read_text(encoding='utf-8')
auto_feedback=any(token in uc_src for token in ['self.runtime.episodes','stream_context']) and 'update_contingent_plan' in uc_src
checks['automatic_semantic_feedback_loop']=auto_feedback
if not auto_feedback:
    add(findings,'HIGH','MEMORY_SEMANTIC_FEEDBACK_GAP',
        'Memory affects ambiguous capability routing, but no automatic result->thinking/logic/intelligence feedback loop is wired in UnifiedYADOCoreV1.',
        {'memory':'episode buffer + bounded stream->capability map','planner_feedback':'caller must pass observed_gain explicitly'})

# Active patch/repair bindings: source hash + receipt hash evidence.
patches=[
 ('PROGRAM_REPAIR_V11','runtime/yado_ambiguity_aware_program_repair_v11.py',core.get('program_execution',{}).get('source_sha256'),core.get('program_execution',{}).get('fresh_admission_receipt_sha256')),
 ('COMPOSITE_TRANSFER_REPAIR','runtime/yado_g2_composite_transfer_repair_adapter_v1.py',core.get('composite_executable_successor_v1',{}).get('runtime_sha256'),core.get('composite_executable_successor_v1',{}).get('fresh_admission_receipt_sha256')),
 ('CONTEXT_MEMORY_ADAPTER','runtime/yado_g2_contextual_stream_capability_adapter_v1.py',core.get('contextual_stream_adapter',{}).get('source_sha256'),core.get('contextual_stream_adapter',{}).get('fresh_admission_receipt_sha256')),
 ('LOGIC_V2','runtime/yado_budget_adaptive_compositional_logic_v2.py',core.get('logic_plateau_v2',{}).get('source_sha256'),core.get('logic_plateau_v2',{}).get('fresh_admission_receipt_sha256')),
 ('THINKING_V2','runtime/yado_work_budget_adaptive_contingent_planner_v2.py',core.get('thinking_plateau_v2',{}).get('source_sha256'),core.get('thinking_plateau_v2',{}).get('fresh_admission_receipt_sha256')),
 ('INTELLIGENCE_V3','runtime/yado_coverage_pruned_compositional_schema_router_v3.py',core.get('intelligence_plateau_v3',{}).get('source_sha256'),core.get('intelligence_plateau_v3',{}).get('functional_fresh_receipt_sha256')),
]
receipt_hashes=set()
for p in (REPO/'receipts').glob('*.json'):
    try:
        j=load(p)
        if j.get('receipt_sha256'):receipt_hashes.add(j['receipt_sha256'])
    except Exception:pass
patch_rows=[]
for name,path,expected,receipt_digest in patches:
    actual=sha(REPO/path)
    row={'name':name,'path':path,'source_hash_ok':bool(expected) and actual==expected,'receipt_bound':bool(receipt_digest) and receipt_digest in receipt_hashes,'expected_sha':expected,'actual_sha':actual}
    patch_rows.append(row)
bad_patches=[x for x in patch_rows if not x['source_hash_ok'] or not x['receipt_bound']]
checks['active_patch_bindings']=not bad_patches
if bad_patches:add(findings,'HIGH','ACTIVE_PATCH_BINDING_GAP','One or more active patch/repair bindings fail source or receipt verification.',bad_patches)

# Functional smoke for the current program repair patch.
repair=uc.repair_program('def f(x):\n    return x + 1\n','f',[((0,),2),((1,),3),((2,),4),((3,),5)],max_candidates=4000)
repair_ok=bool(repair.get('source')) and all(uc.execute_program_task(repair['source'],'f',(x,))==x+2 for x in range(4))
checks['program_repair_smoke']=repair_ok
if not repair_ok:add(findings,'HIGH','PROGRAM_REPAIR_SMOKE_FAIL','Active ambiguity-aware program repair failed a bounded fresh smoke test.',repair)

# Composite repair adapter smoke over a base capability.
comp=G2CompositeTransferRepairAdapterV1(base)
comp_out=comp.run(logic_task)
checks['composite_transfer_repair_smoke']=comp_out.get('result')=='PASS' and comp_out.get('repair_adapter')=='ALG-G2-COMPOSITE-TRANSFER-REPAIR-ADAPTER-V1'
if not checks['composite_transfer_repair_smoke']:add(findings,'HIGH','COMPOSITE_REPAIR_SMOKE_FAIL','Composite transfer repair adapter failed fresh smoke.',comp_out)

# API surface audit.
api_caps=sorted(x for x in active_caps if 'API' in x.upper() or 'HTTP' in x.upper())
api_sources=sorted(x for x in core.get('active_runtime_sources',[]) if 'api' in x.lower() or 'http' in x.lower())
prov_api=[m for m in prov.get('mechanisms',[]) if 'api' in canon(m).lower() or 'http' in canon(m).lower()]
openapi_path=PKG/'yado_openapi_adapter_runtime.py'
openapi_present=openapi_path.exists()
openapi_network_execute_false=False
if openapi_present:
    ns={}
    exec(openapi_path.read_text(encoding='utf-8'),ns)
    cls=ns['OpenAPIContractRuntime']
    state={'policy_tree':{'label':'ALLOW'},'contract_registry':{'X':{'source_id':'S','source_sha':'abc','method':'GET','path':'/x','required':[],'redirect_semantic':False}}}
    planx=cls(state).compile_plan('X')
    openapi_network_execute_false=planx.get('network_execute') is False
checks['api_no_unintended_active_network_surface']=not api_caps and not api_sources and not prov_api and openapi_network_execute_false
api_state={
 'active_api_capabilities':api_caps,'active_api_sources':api_sources,'provenance_api_mechanisms':prov_api,
 'openapi_adapter_present_in_reconstructed_rc8':openapi_present,'openapi_network_execute_false':openapi_network_execute_false,
 'verdict':'SUBSTRATE_PRESENT_NOT_CANONICALLY_BOUND'
}
if not api_caps and openapi_present:
    add(findings,'MEDIUM','API_LAYER_NOT_BOUND_TO_G2','OpenAPI substrate exists in reconstructed RC8, but no API/OpenAPI component is active in canonical G2.',api_state)

# Overall.
rank={'CRITICAL':4,'HIGH':3,'MEDIUM':2,'LOW':1,'INFO':0}
maxsev=max([rank.get(f['severity'],0) for f in findings] or [0])
status='PASS' if maxsev<2 else ('PASS_WITH_LIMITATIONS' if maxsev==2 else 'WITHHOLD_ARCHITECTURE_INTEGRITY')
report={
 'schema':'yado.g2.contour_code_patch_api_integrity_audit.v1',
 'status':status,'generation':head.get('generation_id'),'frontier':head.get('current_frontier'),
 'checks':checks,'findings':sorted(findings,key=lambda x:-rank.get(x['severity'],0)),
 'contour':{
   'base_logic':logic_out,'base_thinking':bud_out,'memory_followup':mem_out,'memory_ablation':abl_out,
   'new_logic_individual':checks['new_logic_individual'],'new_thinking_individual':checks['new_thinking_individual'],
   'new_intelligence_individual':checks['new_intelligence_individual'],'new_dispatch_probe':new_dispatch
 },
 'patches':patch_rows,'api':api_state,'tracked_python_cache_count':len(pycache),
 'canonical_mutation':False,'g3_genesis_performed':False,
 'semantic_boundary':'SOFTWARE ARCHITECTURE AND RUNTIME CONNECTIVITY AUDIT; NOT A CLAIM OF AGI OR SUBJECTIVE CONSCIOUSNESS.'
}
OUT.write_text(json.dumps(report,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')
print(json.dumps({'status':status,'checks':checks,'findings':report['findings'],'patches':patch_rows,'api':api_state},indent=2,sort_keys=True,default=str))
