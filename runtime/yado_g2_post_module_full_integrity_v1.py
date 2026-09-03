from __future__ import annotations
from pathlib import Path
import ast,copy,hashlib,json,py_compile,subprocess,sys

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
sys.path.insert(0,str(ROOT))

from yado_evolution_ledger_v2 import validate_ledger_v2
from yado_g2_unified_module_kernel_v1 import MODULE_REGISTRY

HEAD=REPO/'canonical/yado-main-head-g2.json'
CORE=REPO/'canonical/yado-unified-core-v1.json'
LEDGER=REPO/'architecture/evolution-ledger.json'
PATCHES=REPO/'canonical/yado-g2-active-patch-registry-v1.json'
ASSEMBLY=REPO/'candidates/kernel-self-generated/g2-unified-module-kernel-v1.json'
OUT=REPO/'audits/yado-g2-post-module-full-integrity-v1.json'
GRAPH=REPO/'audits/yado-g2-module-dependency-graph-v1.json'

def load(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def digest(o):return hashlib.sha256(canon(o).encode()).hexdigest()

head=load(HEAD);core=load(CORE);ledger=load(LEDGER);patches=load(PATCHES);assembly=load(ASSEMBLY)
validate_ledger_v2(ledger)
active=set(head.get('active_capabilities',[]))
registry=set(MODULE_REGISTRY)

ROLE={}
compat={
 'ALG-BOUNDED-DNF-RELATION-POLICY-INDUCER-V1',
 'ALG-BUDGETED-STAGE-POLICY-V1',
 'ALG-CONJUNCTIVE-RULE-INDUCER-V1',
 'ALG-G2-COMPOSITE-TRANSFER-REPAIR-ADAPTER-V1',
 'ALG-G2-CONTEXTUAL-STREAM-CAPABILITY-ADAPTER-V1',
 'RUNTIME-G2-TYPED-RECURRENT-CAPABILITY-GRAPH-V1',
}
state={
 'ALG-G2-LEGACY-EXPERIENCE-RETRIEVER-V1',
 'COUNTEREXAMPLE_LINEAGE_MEMORY_V1',
 'RESOURCE-PORTFOLIO-V1',
}
control={'ALG-G2-DEEP-SELF-AUDIT-V1',GENOME}
for m in sorted(active):
    if m in compat:ROLE[m]='COMPATIBILITY'
    elif m in state:ROLE[m]='STATE'
    elif m in control:ROLE[m]='CONTROL'
    else:ROLE[m]='PRIMARY'

edges=[]
def edge(a,b,kind,reason):
    if a in active and b in active:
        edges.append({'from':a,'to':b,'kind':kind,'reason':reason})

FAB='RUNTIME-G2-UNIFIED-EXECUTION-FABRIC-V2'
BASE='RUNTIME-G2-TYPED-RECURRENT-CAPABILITY-GRAPH-V1'
ROUTER='ALG-BOUNDED-CAPABILITY-ROUTER-V1'
RAW='ALG-G2-RAW-TASK-REPRESENTATION-V4'
COORD='ALG-G2-BOUNDED-CAPABILITY-SET-COORDINATOR-V1'
CTX='ALG-G2-CONTEXTUAL-STREAM-CAPABILITY-ADAPTER-V1'
COMP='ALG-G2-COMPOSITE-TRANSFER-REPAIR-ADAPTER-V1'
SELECT='ALG-NEUTRAL-EVIDENCE-PROFILE-SELECTOR-V1'
HSR='RUNTIME-G2-HIGH-SCALE-BINDING-V5'
HSM='ALG-G2-HIGH-SCALE-TRIPLE-KNN-V4'
HSROUTE='ALG-G2-SCALE-ROUTE-SEMANTICS-V5'
SCI='ALG-G2-BOUNDED-SCIENTIFIC-DATA-REASONER-V1'
EXP='ALG-G2-LEGACY-EXPERIENCE-RETRIEVER-V1'
API='ALG-G2-OPENAPI-CONTRACT-CAPABILITY-V1'
API_EXEC='ALG-G2-OPENAPI-READONLY-EXECUTOR-V1'
GENOME='CTRL-G2-EVOLUTIONARY-GENOME-V1'
LOGIC2='ALG-G2-BUDGET-ADAPTIVE-COMPOSITIONAL-LOGIC-V2'
THINK2='ALG-G2-WORK-BUDGET-ADAPTIVE-CONTINGENT-PLANNER-V2'
INTEL3='ALG-G2-COVERAGE-PRUNED-COMPOSITIONAL-SCHEMA-ROUTER-V3'
REPAIR='ALG-G2-AMBIGUITY-AWARE-PROGRAM-REPAIR-V11'
SEM='ALG-G2-SEMANTIC-EXPRESSION-SYNTHESIZER-V1'
COUNTER='COUNTEREXAMPLE_LINEAGE_MEMORY_V1'

edge(RAW,ROUTER,'ROUTING','raw representation yields capability/routing descriptor')
edge(ROUTER,FAB,'ROUTING','router selects capability for unified execution fabric')
edge(FAB,BASE,'RUNTIME','unified fabric delegates legacy execution and recurrent memory to base runtime')
for m in ['ALG-CONJUNCTIVE-RULE-INDUCER-V1','ALG-BOUNDED-DNF-RELATION-POLICY-INDUCER-V1','ALG-BUDGETED-STAGE-POLICY-V1','RESOURCE-PORTFOLIO-V1',LOGIC2,THINK2,INTEL3,API]:
    edge(FAB,m,'DISPATCH','canonical unified fabric can dispatch this module')
edge(COORD,FAB,'COORDINATION','capability sets execute through unified fabric')
edge(CTX,FAB,'MEMORY_CONTEXT','bounded stream-context memory wraps current runtime/fabric')
edge(COMP,CTX,'COMPATIBILITY','composite repair uses contextual capability selection')
edge(COMP,COORD,'COMPATIBILITY','composite repair uses bounded capability coordination')
edge(FAB,THINK2,'MEMORY_FEEDBACK','stage outcome episodes can be consumed by Thinking V2')
edge(FAB,COUNTER,'CAUSAL_HISTORY','runtime outcomes coexist with persistent ledger/receipt counterexample memory')
edge(SCI,SELECT,'EVIDENCE_SELECTION','scientific evidence can feed meta-selection')
edge(EXP,SELECT,'EXPERIENCE_SELECTION','registered historical experience can feed meta-selection')
edge(HSR,HSM,'EMBEDDED_MODEL','high-scale binding embeds V4 high-scale model')
edge(HSR,HSROUTE,'EMBEDDED_ROUTE','high-scale binding embeds V5 route semantics')
edge(HSM,SELECT,'EVIDENCE_SELECTION','high-scale prediction can feed meta-selection')
edge(API,SELECT,'PLAN_SELECTION','bounded API plan can feed meta-selection')
edge(API,API_EXEC,'PLAN_TO_READONLY_EXECUTION','approved read-only contract plan gates bounded network execution')
edge(API_EXEC,SELECT,'NETWORK_EVIDENCE_SELECTION','bounded read-only network evidence can feed meta-selection')
edge(SEM,LOGIC2,'SEMANTIC_TO_LOGIC','synthesized semantic result can be classified by Logic V2')
edge(REPAIR,FAB,'REPAIR_EXECUTION','repaired program capability coexists with canonical execution fabric')
edge(EXP,GENOME,'EVOLUTION_EXPERIENCE','verified experience is available to the evolution controller')
edge(COUNTER,GENOME,'EVOLUTION_COUNTEREXAMPLES','counterexample lineage is available to the evolution controller')
edge(GENOME,LOGIC2,'EVOLUTION_TARGET','logic is a bounded evolution target')
edge(GENOME,THINK2,'EVOLUTION_TARGET','thinking is a bounded evolution target')
edge(GENOME,INTEL3,'EVOLUTION_TARGET','intelligence is a bounded evolution target')
edge(GENOME,REPAIR,'EVOLUTION_TARGET','program repair is a bounded evolution target')
edge(INTEL3,COORD,'META_COORDINATION','Intelligence V3 selects/composes capability sets for coordinator')

# Static source-to-source imports for active sources.
sources=sorted(set(core.get('active_runtime_sources',[])))
stem_to_source={Path(x).stem:x for x in sources if x.endswith('.py')}
static_edges=[]
parse_errors=[];compile_errors=[];missing_sources=[]
for rel in sources:
    p=REPO/rel
    if not p.exists():
        missing_sources.append(rel);continue
    if p.suffix=='.py':
        try:py_compile.compile(str(p),doraise=True)
        except Exception as e:compile_errors.append({'path':rel,'error':repr(e)})
        try:tree=ast.parse(p.read_text(encoding='utf-8'))
        except Exception as e:parse_errors.append({'path':rel,'error':repr(e)});continue
        mods=[]
        for n in ast.walk(tree):
            if isinstance(n,ast.Import):mods += [a.name.split('.')[0] for a in n.names]
            elif isinstance(n,ast.ImportFrom) and n.module:mods.append(n.module.split('.')[0])
        for mod in sorted(set(mods)):
            if mod in stem_to_source:
                static_edges.append({'from_source':rel,'to_source':stem_to_source[mod],'kind':'PYTHON_IMPORT'})

incoming={m:0 for m in active};outgoing={m:0 for m in active}
for e in edges:
    outgoing[e['from']]+=1;incoming[e['to']]+=1
orphans=[]
for m in sorted(active):
    if ROLE[m] in {'STATE','CONTROL'}:continue
    if incoming[m]+outgoing[m]==0:orphans.append(m)

# Plane placement.
plane_components=set()
for p in core.get('planes',[]):
    plane_components.update(x for x in p.get('active_components',[]) if isinstance(x,str))
unplaced=sorted(active-plane_components)

# Patch registry verification.
patch_fail=[]
for p in patches.get('patches',[]):
    src=REPO/p['source']
    ok=src.exists() and sha(src)==p.get('expected_source_sha256')==p.get('source_sha256') and p.get('source_hash_ok') is True and p.get('evidence_ok') is True and p.get('status')=='PASS'
    if not ok:patch_fail.append(p.get('patch_id'))

# Canonical guard.
guard=subprocess.run([sys.executable,str(ROOT/'yado_canonical_invariant_guard_v1.py')],cwd=REPO,capture_output=True,text=True,timeout=90)

# Python cache garbage.
ls=subprocess.run(['git','ls-files'],cwd=REPO,capture_output=True,text=True,timeout=30).stdout.splitlines()
pycache=[x for x in ls if x.endswith('.pyc') or '/__pycache__/' in x]

checks={
 'canonical_guard':guard.returncode==0,
 'active_module_count_registry_exact':len(active)==len(registry),
 'registry_exact':active==registry,
 'no_active_module_superseded':all(ROLE[m]!='SUPERSEDED' for m in active),
 'no_orphan_executable_modules':not orphans,
 'all_active_modules_placed_in_planes':not unplaced,
 'nine_architecture_planes':len(core.get('planes',[]))==9,
 'active_runtime_sources_exist':not missing_sources,
 'active_runtime_compile':not compile_errors and not parse_errors,
 'active_patch_registry_verified':patches.get('status')=='CANONICAL_ACTIVE' and patches.get('all_active_patch_bindings_verified') is True and not patch_fail,
 'execution_fabric_canonical':core.get('execution_fabric_v2',{}).get('status')=='CANONICAL_ACTIVE' and FAB in active,
 'memory_readmission_current':core.get('contextual_stream_adapter',{}).get('latest_fresh_readmission_run_id')=='33720696775' and core.get('contextual_stream_adapter',{}).get('source_sha256')==sha(REPO/'runtime/yado_g2_contextual_stream_capability_adapter_v1.py'),
 'python_cache_clean':not pycache,
 'openapi_canonical_plan_only':core.get('openapi_contract_capability_v1',{}).get('status')=='CANONICAL_ACTIVE' and core.get('openapi_contract_capability_v1',{}).get('network_execute') is False and API in active,
 'openapi_readonly_executor_canonical':core.get('openapi_readonly_executor_v1',{}).get('status')=='CANONICAL_ACTIVE' and core.get('openapi_readonly_executor_v1',{}).get('read_only_only') is True and API_EXEC in active,
 'module_assembly_pass':assembly.get('status')=='PASS_CURRENT_G2_UNIFIED_MODULE_ASSEMBLY_V1' and assembly.get('active_module_count')==len(active) and assembly.get('covered_module_count')==len(active) and assembly.get('functional_assembly_pass') is True and assembly.get('canonical_ready') is True,
 'frontier_preserved':head.get('current_frontier')=='KERNEL_G2_RAW_REPRESENTATION_V5_CANONICAL_ADMISSION_V1' and ledger.get('open_deficits')==['KERNEL_G2_RAW_REPRESENTATION_V5_CANONICAL_ADMISSION_V1'],
 'g3_not_started':head.get('g3_genesis_performed') is False and core.get('g3_genesis_performed') is False,
}
status='PASS_G2_POST_MODULE_FULL_INTEGRITY_V1' if all(checks.values()) else 'WITHHOLD_G2_POST_MODULE_FULL_INTEGRITY_V1'

# Conservative quarantine recommendation: only modules that are compatibility AND have no unique current consumer outside compatibility/base path are candidates.
# Current audit does not authorize removal; it records what must remain until a fresh ablation proves dispensability.
compatibility_modules=sorted(m for m,r in ROLE.items() if r=='COMPATIBILITY')
quarantine_candidates=[]
retain_compatibility=[]
for m in compatibility_modules:
    consumers=[e['from'] for e in edges if e['to']==m]
    # Any active primary consumer or direct fabric dependency means retain.
    if any(ROLE.get(x)=='PRIMARY' for x in consumers) or m in {BASE,CTX}:
        retain_compatibility.append(m)
    else:
        quarantine_candidates.append(m)

graph={
 'schema':'yado.g2.module_dependency_graph.v1',
 'generation':head.get('generation_id'),
 'frontier':head.get('current_frontier'),
 'active_module_count':len(active),
 'roles':ROLE,
 'role_counts':{r:sum(1 for x in ROLE.values() if x==r) for r in sorted(set(ROLE.values()))},
 'semantic_edges':edges,
 'semantic_edge_count':len(edges),
 'static_import_edges':static_edges,
 'static_import_edge_count':len(static_edges),
 'orphans':orphans,
 'compatibility_modules':compatibility_modules,
 'retain_compatibility':sorted(retain_compatibility),
 'quarantine_candidates_require_fresh_ablation':sorted(quarantine_candidates),
 'inactive_superseded_policy':'SUPERSEDED MODULES ARE NOT ACTIVE BY PRESENCE; KEEP AS HISTORY/QUARANTINE UNLESS FRESHLY RE-ADMITTED.',
 'removal_authorized':False,
 'semantic_boundary':'DEPENDENCY/ROLE GRAPH OF CURRENT ACTIVE G2. CLASSIFICATION DOES NOT BY ITSELF AUTHORIZE DELETION.'
}
graph['graph_digest']=digest(graph)
GRAPH.write_text(json.dumps(graph,indent=2,sort_keys=True)+'\n',encoding='utf-8')

report={
 'schema':'yado.g2.post_module_full_integrity.v1',
 'status':status,
 'checks':checks,
 'generation':head.get('generation_id'),
 'frontier':head.get('current_frontier'),
 'active_module_count':len(active),
 'role_counts':graph['role_counts'],
 'orphan_modules':orphans,
 'unplaced_active_modules':unplaced,
 'missing_active_runtime_sources':missing_sources,
 'compile_errors':compile_errors,
 'parse_errors':parse_errors,
 'patch_failures':patch_fail,
 'tracked_python_cache':pycache,
 'dependency_graph_digest':graph['graph_digest'],
 'compatibility_retain':sorted(retain_compatibility),
 'compatibility_quarantine_candidates_require_fresh_ablation':sorted(quarantine_candidates),
 'api_boundary':{
   'component_id':API,
   'canonical_active':API in active,
   'network_execute':core.get('openapi_contract_capability_v1',{}).get('network_execute'),
   'mode':'CONTRACT_CLASSIFICATION_AND_PLAN_ONLY'
 },
 'execution_fabric':core.get('execution_fabric_v1'),
 'memory_context':core.get('contextual_stream_adapter'),
 'module_assembly_receipt_sha256':assembly.get('receipt_sha256'),
 'canonical_mutation':False,
 'architecture_mutation':False,
 'generation_transition':False,
 'g3_genesis_performed':False,
 'semantic_boundary':'POST-ASSEMBLY SOFTWARE/ARCHITECTURE INTEGRITY AUDIT. NO GENERATION PROMOTION OR CONSCIOUSNESS CLAIM.'
}
report['report_digest']=digest(report)
OUT.write_text(json.dumps(report,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')
print(json.dumps({'status':status,'checks':checks,'role_counts':graph['role_counts'],'orphans':orphans,'retain_compatibility':retain_compatibility,'quarantine_candidates_require_fresh_ablation':quarantine_candidates,'graph_digest':graph['graph_digest']},indent=2,sort_keys=True))
if status.startswith('WITHHOLD'):raise SystemExit(2)
