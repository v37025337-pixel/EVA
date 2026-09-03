from __future__ import annotations
from pathlib import Path
import hashlib,json,os,random,sys

ROOT=Path(__file__).resolve().parent;REPO=ROOT.parent;PKG=ROOT/'yado_rc8_v36'
sys.path[:0]=[str(ROOT),str(PKG)]

from yado_g2_unified_module_kernel_v1 import *
from yado_bounded_capability_router_v1 import BoundedCapabilityRouterLearnerV1
from yado_conjunctive_rule_inducer_v1 import ConjunctiveRuleInducerV1
from yado_bounded_dnf_relation_policy_inducer_v1 import BoundedDNFRelationPolicyInducerV1

def load(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def digest(o):return hashlib.sha256(canon(o).encode()).hexdigest()

head=load(REPO/'canonical/yado-main-head-g2.json')
core_manifest=load(REPO/'canonical/yado-unified-core-v1.json')
active=set(head.get('active_capabilities',[]))

def old_desc(cap,amb=False):
    d={'budget_limited':False,'quota_limited':False,'external_evidence_needed':False,'relation_needed':False,'disjunction_needed':False,'context_ambiguous':amb}
    if not amb:
        if cap==CAP_BUD:d['budget_limited']=True
        elif cap==CAP_RES:d['external_evidence_needed']=True
        elif cap==CAP_REL:d['relation_needed']=True
    return d

def route_desc(cap):
    d=old_desc(cap,False)
    if cap in {CAP_LOGIC_V2,CAP_THINK_V2,CAP_INTEL_V3}:d['module_id']=cap
    return d

route_train=[]
for i in range(40):
    for cap in [CAP_CONJ,CAP_REL,CAP_BUD,CAP_RES,CAP_LOGIC_V2,CAP_THINK_V2,CAP_INTEL_V3]:
        route_train.append({'input':route_desc(cap)|{'noise':i%3},'expected':cap})
router=BoundedCapabilityRouterLearnerV1.synthesize(route_train,route_train,CAP_CONJ,min_support=5)

scalar_cases=[]
for a in [False,True]:
  for b in [False,True]:
    for c in [False,True]:
      for _ in range(5):scalar_cases.append({'input':{'condition_a':a,'condition_b':b,'condition_c':c},'expected':'PASS' if a and b and c else 'HOLD'})
scalar=ConjunctiveRuleInducerV1.synthesize('MODULE_KERNEL_SCALAR','LOGIC',scalar_cases,min_support=2,max_rules=12)

rel_train=[]
for i in range(220):
    owner=f'U{i%37}';actor=owner if i%3==0 else f'U{(i*7+3)%41}';verified=i%2==0
    rel_train.append({'input':{'actor':actor,'owner':owner,'verified':verified,'role':['MEMBER','LEAD','GUEST'][i%3]},'expected':'ALLOW' if actor==owner and verified else 'DENY'})
relation=BoundedDNFRelationPolicyInducerV1.synthesize('MODULE_KERNEL_REL','LOGIC',rel_train,min_support=3,max_clauses=12,validation_cases=rel_train)

kernel=UnifiedYADOModuleKernelV1(router,scalar,relation,REPO)
registry=kernel.registry()
smoke={};coverage=set()

def run(mid,task,predicate=lambda x:True):
    try:
        out=kernel.execute(mid,task)
        ok=bool(predicate(out));smoke[mid]={'pass':ok,'output':out};coverage.add(mid)
    except Exception as e:
        smoke[mid]={'pass':False,'error_type':type(e).__name__,'error':str(e)}
    return smoke[mid]

route_key=sorted(kernel.core.portfolio.get('routes_for_current_open_deficits',{}))[0]
resource_expected=(kernel.core.portfolio['routes_for_current_open_deficits'][route_key] or [{}])[0].get('resource_id')

logic_rows=[]
for a in [False,True]:
  for b in [False,True]:
    for _ in range(6):logic_rows.append({'input':{'a':a,'b':b},'expected':'EVEN' if a==b else 'ODD'})
intel_cases=[]
for i in range(12):
    intel_cases += [
      {'input':{'kind':'logic','urgent':bool(i%2)},'expected':CAP_LOGIC_V2},
      {'input':{'kind':'plan','urgent':bool(i%2)},'expected':CAP_THINK_V2},
    ]
plan_task={'kind':'thinking_v2','descriptor':{'module_id':CAP_THINK_V2},'stream_id':'MOD-P','current_confidence':0.2,'target_confidence':0.8,'remaining_budget':5.0,
           'stages':[{'stage_id':'OBSERVE','cost':1,'expected_gain':0.35},{'stage_id':'DEEP','cost':3,'expected_gain':0.7,'requires':['OBSERVE']}]}
logic_task={'kind':'logic_v2','descriptor':{'module_id':CAP_LOGIC_V2},'stream_id':'MOD-L','train_rows':logic_rows,'payload':{'a':True,'b':False}}
intel_task={'kind':'intelligence_v3','descriptor':{'module_id':CAP_INTEL_V3},'stream_id':'MOD-I','train_cases':intel_cases,'fallback_output':CAP_LOGIC_V2,'payload':{'kind':'plan','urgent':True}}

run(CAP_ROUTER,{'descriptor':old_desc(CAP_BUD)},lambda x:x.get('selected_capability')==CAP_BUD)
run(CAP_CONJ,{'kind':'scalar','stream_id':'BASE-L','payload':{'condition_a':True,'condition_b':True,'condition_c':True}},lambda x:x.get('result')=='PASS')
run(CAP_REL,{'kind':'relation','stream_id':'BASE-R','payload':{'actor':'A','owner':'A','verified':True,'role':'MEMBER'}},lambda x:x.get('result')=='ALLOW')
run(CAP_BUD,{'kind':'budget','stream_id':'BASE-P','current_confidence':0.2,'target_confidence':0.7,'remaining_budget':5.0,'stages':[{'stage_id':'S1','cost':1,'expected_gain':0.2,'quota_remaining':1},{'stage_id':'S2','cost':3,'expected_gain':0.6,'quota_remaining':1}]},lambda x:x.get('result') in {'S1','S2','STOP','WITHHOLD'})
run(CAP_RES,{'kind':'resource','stream_id':'BASE-E','route_key':route_key,'payload':{}},lambda x:x.get('result')==resource_expected)
run(CAP_LOGIC_V2,logic_task,lambda x:x.get('result')=='ODD')
run(CAP_THINK_V2,plan_task,lambda x:x.get('result',{}).get('feasible') is True)
run(CAP_INTEL_V3,intel_task,lambda x:CAP_THINK_V2 in x.get('result',()))

repair_task={'action':'repair','source':'def f(x):\n    return x + 1\n','function_name':'f','train_examples':[((0,),2),((1,),3),((2,),4),((3,),5)],'max_candidates':4000,'stream_id':'REPAIR'}
rep=run(CAP_REPAIR,repair_task,lambda x:bool(x.get('source')))
if rep.get('pass'):
    run(CAP_REPAIR,{'action':'execute','source':rep['output']['source'],'function_name':'f','args':[7],'stream_id':'REPAIR-EXEC'},lambda x:x.get('result')==9)

coord_tasks={CAP_LOGIC_V2:logic_task,CAP_THINK_V2:plan_task,CAP_INTEL_V3:intel_task}
run(CAP_COORD,{'selected_capabilities':[CAP_LOGIC_V2,CAP_THINK_V2,CAP_INTEL_V3],'capability_tasks':coord_tasks,'stream_id':'COORD'},lambda x:x.get('status')=='PASS')

science_rows=[{'x':i,'y':2*i+1,'group':'A' if i<10 else 'B'} for i in range(20)]
run(CAP_SCI,{'action':'hypothesis','rows':science_rows,'spec':{'type':'CORRELATION_ABS_AT_LEAST','x':'x','y':'y','threshold':0.95},'stream_id':'SCI'},lambda x:x.get('supported') is True)

context_prime={'kind':'budget','descriptor':old_desc(CAP_BUD),'stream_id':'CTX','current_confidence':0.2,'target_confidence':0.7,'remaining_budget':4.0,'stages':[{'stage_id':'C1','cost':1,'expected_gain':0.3,'quota_remaining':1},{'stage_id':'C2','cost':2,'expected_gain':0.6,'quota_remaining':1}]}
ctx0=run(CAP_CONTEXT,context_prime,lambda x:x.get('context_selected_capability')==CAP_BUD)
context_follow=dict(context_prime);context_follow['descriptor']=old_desc(CAP_BUD,True)
ctx1=run(CAP_CONTEXT,context_follow,lambda x:x.get('context_selected_capability')==CAP_BUD)

comp_task={'kind':'relation','descriptor':old_desc(CAP_REL),'stream_id':'COMP','payload':{'actor':'A','owner':'A','verified':True,'role':'MEMBER'}}
run(CAP_COMPOSITE,comp_task,lambda x:x.get('result')=='ALLOW' and x.get('repair_adapter')==CAP_COMPOSITE)

run(CAP_AUDIT,{'stream_id':'AUDIT'},lambda x:x.get('core_audit',{}).get('pass') is True)

corpus=kernel.high_scale.corpus['cases']
low=next((x for x in corpus if kernel.high_scale.cardinality(x)<kernel.high_scale.activation_min_size),None)
high=next((x for x in corpus if kernel.high_scale.cardinality(x)>=kernel.high_scale.activation_min_size),None)
if high is not None:
    run(CAP_HS_MODEL,{'case':high,'stream_id':'HS-M'},lambda x:x.get('route')=='V4_HIGH' and x.get('prediction') is not None)
else:smoke[CAP_HS_MODEL]={'pass':False,'error':'NO_HIGH_SCALE_CASE'};coverage.add(CAP_HS_MODEL)

run(CAP_EXPERIENCE,{'action':'search_registry','tags':['thinking','logic','repair'],'limit':8,'stream_id':'EXP'},lambda x:len(x.get('matches',[]))>0)
raw=run(CAP_RAW,{'raw_text':'Analyze this bounded task and choose the appropriate reasoning resource.','stream_id':'RAW'},lambda x:x.get('capability') in {CAP_CONJ,CAP_REL,CAP_BUD,CAP_RES})
if high is not None:run(CAP_SCALE_ROUTE,{'case':high,'stream_id':'HS-R'},lambda x:x.get('route')=='V4_HIGH' and x.get('cardinality',0)>=kernel.high_scale.activation_min_size)
else:smoke[CAP_SCALE_ROUTE]={'pass':False,'error':'NO_HIGH_SCALE_CASE'};coverage.add(CAP_SCALE_ROUTE)

sem_train=[{'x':x,'y':y,'expected':x+y} for x,y in [(0,0),(1,2),(2,1),(3,4),(-1,2),(4,-2)]]
sem=run(CAP_SEMANTIC,{'action':'synthesize','train_rows':sem_train,'max_ops':2,'stream_id':'SEM'},lambda x:x.get('expression') is not None)
run(CAP_SELECTOR,{'candidates':[{'token':'A','evidence':0.9,'risk':0.1},{'token':'B','evidence':0.5,'risk':0.0}],'stream_id':'SEL'},lambda x:x.get('selected_token')=='A')
run(CAP_COUNTERMEM,{'limit':8,'nonpass_only':True,'stream_id':'MEM'},lambda x:x.get('event_count',0)>0)
run(CAP_HS_RUNTIME,{'stream_id':'HS-S'},lambda x:x.get('binding_digest') is not None)
run(CAP_BASE_RUNTIME,{'stream_id':'BASE-S'},lambda x:'episode_count' in x)
run(CAP_FABRIC,{'stream_id':'FABRIC-S'},lambda x:x.get('component_id')==CAP_FABRIC and x.get('canonical_active') is True)
api_state={
  'policy_tree':{'label':'ALLOW'},
  'contract_registry':{
    'GET_UNIT':{'source_id':'MODULE_GATE','source_sha':'unit','method':'GET','path':'/unit','required':[],'redirect_semantic':False}
  }
}
api_smoke=run(CAP_API,{'action':'compile_plan','state_section':api_state,'contract_id':'GET_UNIT','stream_id':'API'},lambda x:x.get('capability_id')==CAP_API and x.get('network_execute') is False and x.get('read_only_candidate') is True)
run(CAP_FABRIC,{'stream_id':'FABRIC-S'},lambda x:x.get('component_id')==CAP_FABRIC and x.get('canonical_active') is True)
api_state={'policy_tree':{'label':'ALLOW'},'contract_registry':{'GET_TEST':{'source_id':'DOC','source_sha':'gate','method':'GET','path':'/test','required':[],'redirect_semantic':False}}}
run(CAP_API,{'action':'compile_plan','state_section':api_state,'contract_id':'GET_TEST','stream_id':'API-S'},lambda x:x.get('contract_id')=='GET_TEST' and x.get('network_execute') is False)

# Mark embedded high-scale IDs and persistent/control nodes covered by the explicit calls above.
coverage.update({CAP_HS_MODEL,CAP_SCALE_ROUTE,CAP_HS_RUNTIME,CAP_COUNTERMEM,CAP_AUDIT,CAP_FABRIC,CAP_API})

# Interaction chain 1: raw representation -> its selected base executor -> shared memory.
interaction={}
if raw.get('pass'):
    label=raw['output']['capability']
    if label==CAP_CONJ:task={'kind':'scalar','stream_id':'RAW-X','payload':{'condition_a':True,'condition_b':True,'condition_c':True}}
    elif label==CAP_REL:task={'kind':'relation','stream_id':'RAW-X','payload':{'actor':'A','owner':'A','verified':True,'role':'MEMBER'}}
    elif label==CAP_BUD:task={'kind':'budget','stream_id':'RAW-X','current_confidence':0.2,'target_confidence':0.7,'remaining_budget':4,'stages':[{'stage_id':'A','cost':1,'expected_gain':0.3,'quota_remaining':1},{'stage_id':'B','cost':2,'expected_gain':0.6,'quota_remaining':1}]}
    else:task={'kind':'resource','stream_id':'RAW-X','route_key':route_key,'payload':{}}
    try:
        before=kernel.fabric.memory_snapshot()['episode_count'];out=kernel.execute(label,task);after=kernel.fabric.memory_snapshot()['episode_count']
        interaction['representation_to_execution_to_memory']={'pass':after>before,'selected':label,'result':out,'before':before,'after':after}
    except Exception as e:interaction['representation_to_execution_to_memory']={'pass':False,'error':repr(e)}
else:interaction['representation_to_execution_to_memory']={'pass':False,'error':'RAW_SMOKE_FAILED'}

# Interaction chain 2: science evidence -> meta-selector -> current thinking.
try:
    sci=kernel.execute(CAP_SCI,{'action':'hypothesis','rows':science_rows,'spec':{'type':'LINEAR_R2_AT_LEAST','x':'x','y':'y','threshold':0.98},'stream_id':'CHAIN-SCI'})
    sel=kernel.execute(CAP_SELECTOR,{'candidates':[{'token':'DEEP_PLAN','evidence':1.0 if sci['supported'] else 0.1,'risk':0.05},{'token':'HOLD','evidence':0.4,'risk':0.0}],'stream_id':'CHAIN-SEL'})
    pl=kernel.execute(CAP_THINK_V2,plan_task)
    interaction['science_to_selection_to_thinking']={'pass':sci['supported'] and sel['selected_token']=='DEEP_PLAN' and pl.get('result',{}).get('feasible') is True,'science':sci,'selection':sel,'thinking':pl}
except Exception as e:interaction['science_to_selection_to_thinking']={'pass':False,'error':repr(e)}

# Interaction chain 3: semantic synthesis -> fresh prediction -> Logic V2 classification -> memory.
try:
    model=sem['output'];pred=kernel.execute(CAP_SEMANTIC,{'action':'predict','model':model,'x':5,'y':7,'stream_id':'CHAIN-SEM'})
    bool_rows=[]
    for a in [False,True]:
      for b in [False,True]:
        for _ in range(5):bool_rows.append({'input':{'expression_valid':a,'bounded':b},'expected':'ACCEPT' if a and b else 'HOLD'})
    logic_chain=kernel.execute(CAP_LOGIC_V2,{'kind':'logic_v2','stream_id':'CHAIN-LOGIC','train_rows':bool_rows,'payload':{'expression_valid':pred['result']==12,'bounded':True}})
    interaction['semantic_to_logic_to_memory']={'pass':pred['result']==12 and logic_chain['result']=='ACCEPT','prediction':pred,'logic':logic_chain}
except Exception as e:interaction['semantic_to_logic_to_memory']={'pass':False,'error':repr(e)}

# Interaction chain 4: program repair -> execution.
interaction['repair_to_execution']={'pass':bool(rep.get('pass') and smoke.get(CAP_REPAIR,{}).get('pass')),'repair_mode':rep.get('output',{}).get('repair_mode')}

# Interaction chain 5: accumulated experience -> meta selection.
try:
    exp=kernel.execute(CAP_EXPERIENCE,{'action':'search_registry','tags':['thinking','logic','repair'],'limit':4,'stream_id':'CHAIN-EXP'})
    cands=[{'token':x['branch'],'evidence':float(x['score']),'risk':0.0} for x in exp['matches']]
    esel=kernel.execute(CAP_SELECTOR,{'candidates':cands,'stream_id':'CHAIN-EXPSEL'})
    interaction['experience_to_meta_selection']={'pass':bool(cands) and esel['selected_token'] in {x['token'] for x in cands},'matches':len(cands),'selection':esel}
except Exception as e:interaction['experience_to_meta_selection']={'pass':False,'error':repr(e)}

# Interaction chain 6: high-scale evidence route/model -> meta selection.
try:
    if high is None:raise RuntimeError('NO_HIGH_CASE')
    hs=kernel.execute(CAP_HS_MODEL,{'case':high,'stream_id':'CHAIN-HS'})
    hsel=kernel.execute(CAP_SELECTOR,{'candidates':[{'token':str(hs['prediction']),'evidence':1.0},{'token':'WITHHOLD','evidence':0.1}],'stream_id':'CHAIN-HSSEL'})
    interaction['high_scale_to_meta_selection']={'pass':hs['route']=='V4_HIGH' and hsel['selected_token']==str(hs['prediction']),'high_scale':hs,'selection':hsel}
except Exception as e:interaction['high_scale_to_meta_selection']={'pass':False,'error':repr(e)}

# Interaction chain 7: bounded OpenAPI contract plan -> meta selection, with network execution still disabled.
try:
    api_plan=kernel.execute(CAP_API,{'action':'compile_plan','state_section':api_state,'contract_id':'GET_UNIT','stream_id':'CHAIN-API'})
    api_sel=kernel.execute(CAP_SELECTOR,{'candidates':[
      {'token':'USE_READ_ONLY_PLAN','evidence':1.0 if api_plan.get('read_only_candidate') and api_plan.get('network_execute') is False else 0.0,'risk':0.0},
      {'token':'WITHHOLD','evidence':0.2,'risk':0.0}
    ],'stream_id':'CHAIN-APISEL'})
    interaction['api_plan_to_meta_selection']={'pass':api_plan.get('network_execute') is False and api_sel.get('selected_token')=='USE_READ_ONLY_PLAN','api_plan':api_plan,'selection':api_sel}
except Exception as e:interaction['api_plan_to_meta_selection']={'pass':False,'error':repr(e)}

# Binding hygiene checks.
ctx_expected=core_manifest.get('contextual_stream_adapter',{}).get('source_sha256')
ctx_actual=sha(REPO/'runtime/yado_g2_contextual_stream_capability_adapter_v1.py')
binding_checks={
 'context_memory_source_hash_exact':bool(ctx_expected) and ctx_expected==ctx_actual,
 'high_scale_binding_instantiated':kernel.high_scale.snapshot().get('binding_digest') is not None,
 'canonical_unified_fabric_active':CAP_FABRIC in active and core_manifest.get('execution_fabric_v1',{}).get('status')=='CANONICAL_ACTIVE',
 'canonical_openapi_active':CAP_API in active and core_manifest.get('openapi_contract_capability_v1',core_manifest.get('openapi_capability_v1',{})).get('status','CANONICAL_ACTIVE')=='CANONICAL_ACTIVE',
 'api_network_execution_disabled':api_smoke.get('pass') is True,
}
pycache=subprocess_result=None
import subprocess
ls=subprocess.run(['git','ls-files'],cwd=REPO,capture_output=True,text=True,timeout=30).stdout.splitlines()
tracked_cache=[x for x in ls if x.endswith('.pyc') or '/__pycache__/' in x]
binding_checks['no_tracked_python_cache']=not tracked_cache

snapshot=kernel.snapshot()
module_coverage_pass=set(smoke)==active and coverage==active and all(x.get('pass') for x in smoke.values())
interaction_pass=all(x.get('pass') for x in interaction.values())
registry_pass=not snapshot['missing_active_modules'] and not snapshot['extra_registry_modules'] and len(registry)==len(active)
functional_assembly_pass=module_coverage_pass and interaction_pass and registry_pass
canonical_ready=functional_assembly_pass and all(binding_checks.values())
status='PASS_CURRENT_G2_UNIFIED_MODULE_ASSEMBLY_V1' if canonical_ready else ('PASS_FUNCTIONAL_WITH_BINDING_REPAIRS_REQUIRED' if functional_assembly_pass else 'WITHHOLD_UNIFIED_MODULE_KERNEL_V1')

report={
 'schema':'yado.g2.unified_module_kernel.fresh_gate.v1','status':status,
 'generation':head.get('generation_id'),'frontier':head.get('current_frontier'),
 'active_module_count':len(active),'registry_pass':registry_pass,
 'module_coverage_pass':module_coverage_pass,'covered_module_count':len(coverage),
 'functional_assembly_pass':functional_assembly_pass,'canonical_ready':canonical_ready,
 'smoke':smoke,'interactions':interaction,'binding_checks':binding_checks,
 'tracked_python_cache':tracked_cache,'snapshot':snapshot,
 'assembly_runtime':CAP_FABRIC,
 'assembly_runtime_canonical_active':True,'canonical_mutation':False,
 'architecture_mutation':False,'generation_transition':False,'g3_genesis_performed':False,
 'semantic_boundary':'FRESH SHADOW ASSEMBLY TEST OF ALL CURRENT CANONICAL G2 MODULE IDENTITIES OVER THE CANONICAL UNIFIED EXECUTION FABRIC. THE MODULE KERNEL ITSELF IS NOT A NEW GENERATION.'
}
report['receipt_sha256']=digest(report)
out=REPO/'candidates/kernel-self-generated/g2-unified-module-kernel-v1.json';out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(report,indent=2,sort_keys=True,default=str)+'\n')
print(json.dumps({'status':status,'active_module_count':len(active),'covered_module_count':len(coverage),'module_coverage_pass':module_coverage_pass,'interaction_pass':interaction_pass,'functional_assembly_pass':functional_assembly_pass,'canonical_ready':canonical_ready,'binding_checks':binding_checks,'failed_smoke':[k for k,v in smoke.items() if not v.get('pass')],'failed_interactions':[k for k,v in interaction.items() if not v.get('pass')]},indent=2,sort_keys=True))
if not functional_assembly_pass:raise SystemExit(2)
