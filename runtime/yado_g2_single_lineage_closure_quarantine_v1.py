from __future__ import annotations
from pathlib import Path
import copy,hashlib,json,os,re,shutil,subprocess,sys

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
PKG=ROOT/'yado_rc8_v36'
sys.path[:0]=[str(ROOT),str(PKG)]

from yado_unified_core_v1 import UnifiedYADOCoreV1
from yado_evolution_ledger_v2 import validate_ledger_v2,event_hash
from yado_unified_context_kernel_v1 import UnifiedContextKernel

HEAD=REPO/'canonical/yado-main-head-g2.json'
CORE=REPO/'canonical/yado-unified-core-v1.json'
EXP=REPO/'canonical/yado-unified-experience-registry-v1.json'
PROV=REPO/'canonical/yado-algorithm-provenance-registry-v1.json'
CTX=REPO/'canonical/yado-unified-context-kernel-v1.json'
LEDGER=REPO/'architecture/evolution-ledger.json'
BIND=REPO/'canonical/yado-g2-applied-experience-binding-v1.json'
QMAN=REPO/'quarantine/yado-g2-quarantine-manifest-v1.json'
OUT=ROOT/'yado_g2_single_lineage_closure_quarantine_v1_receipt.json'
GUARD=ROOT/'yado_canonical_invariant_guard_v1.py'

ACTIVE='yado-architecture-shadow-search'
FRONT='KERNEL_G2_RAW_REPRESENTATION_V5_CANONICAL_ADMISSION_V1'

PLANE_QUERIES={
 'IDENTITY_AND_LINEAGE':['integrity','lineage','split_brain','verification'],
 'MEMORY_AND_EXPERIENCE':['memory','closed_loop','lineage','experience'],
 'LOGIC':['logic','repair','algorithm'],
 'THINKING_AND_PLANNING':['thinking','planning','repair'],
 'INTELLIGENCE_AND_META_SELECTION':['intelligence','evolution','selection','meta'],
 'WORKSPACE_AND_INTEGRATION':['workspace','consciousness','metacognition','self_model'],
 'RESOURCE_AND_EVIDENCE':['internet','research','external_evidence','resource'],
 'SELF_AUDIT_AND_REPAIR':['self_audit','integrity','repair','consistency'],
 'REPRESENTATION_AND_GROUNDING':['representation','language','grounding','routing'],
}

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def h(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def write(p,o):
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(o,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')
def cdig(o,field):
    x=copy.deepcopy(o);x.pop(field,None);return h(x)

head,core,exp,prov,ctx,ledger=map(load,[HEAD,CORE,EXP,PROV,CTX,LEDGER])
validate_ledger_v2(ledger)
if ledger.get('open_deficits')!=[FRONT]:raise RuntimeError('UNEXPECTED_FRONTIER:'+json.dumps(ledger.get('open_deficits')))
if head.get('g3_genesis_performed') is not False:raise RuntimeError('G3_ALREADY_STARTED')
if exp.get('policy',{}).get('active_branch')!=ACTIVE:raise RuntimeError('ACTIVE_BRANCH_POLICY_DRIFT')

legacy=[b for b in exp.get('branches',[]) if b.get('mode')=='EXPERIENCE_ONLY']
active=[b for b in exp.get('branches',[]) if b.get('mode')=='ACTIVE_LINEAGE']
if len(active)!=1 or active[0].get('branch')!=ACTIVE or len(legacy)!=13:
    raise RuntimeError('BRANCH_REGISTRY_NOT_1_PLUS_13')

hist_names={b['branch'] for b in legacy}
moved=[]
wfdir=REPO/'.github/workflows'
qdir=REPO/'quarantine/legacy-workflows'
qdir.mkdir(parents=True,exist_ok=True)
for p in sorted(list(wfdir.glob('*.yml'))+list(wfdir.glob('*.yaml'))):
    text=p.read_text(encoding='utf-8',errors='replace')
    found=set()
    for m in re.finditer(r'branches:\s*\[([^\]]+)\]',text):
        for x in m.group(1).split(','):
            found.add(x.strip().strip("'\""))
    if ACTIVE not in found and found & hist_names:
        dst=qdir/p.name
        shutil.move(str(p),str(dst))
        moved.append({'source':p.relative_to(REPO).as_posix(),'quarantine':dst.relative_to(REPO).as_posix(),'branches':sorted(found & hist_names)})

(qdir/'README.md').write_text(
    '# Legacy workflow quarantine\n\n'
    'These workflows are historical control-plane artifacts. They are deliberately outside the GitHub workflow execution directory, so they cannot auto-execute. '
    'Their original commits remain part of YADO history and exact evidence is retrieved by registered commit SHA.\n',
    encoding='utf-8'
)

kernel=UnifiedYADOCoreV1(REPO)
plane_bindings={}
used_branches=set()
for plane in core.get('planes',[]):
    pid=plane.get('plane_id')
    queries=PLANE_QUERIES.get(pid,['integrity','evolution'])
    rows=[]
    seen=set()
    for q in queries:
        for r in kernel.experience_search([q],limit=8):
            key=r.get('branch')
            if key in seen:continue
            seen.add(key)
            rows.append(r)
    rows.sort(key=lambda x:(-float(x.get('score',0)),str(x.get('branch'))))
    selected=rows[:4]
    if not selected:
        selected=[{
            'branch':legacy[0]['branch'],'role':legacy[0].get('role'),'score':0,
            'tags':legacy[0].get('tags',[]),'lessons':legacy[0].get('lessons',[]),
            'lesson_provenance':legacy[0].get('lesson_provenance'),
            'rederived_evidence':legacy[0].get('rederived_evidence'),
            'evidence':legacy[0].get('evidence',[])
        }]
    used_branches.update(x.get('branch') for x in selected if x.get('branch'))
    plane_bindings[pid]={
        'queries':queries,
        'selected_history':[{
            'branch':x.get('branch'),'role':x.get('role'),'score':x.get('score'),
            'lessons':x.get('lessons',[]),'evidence':x.get('evidence',[]),
            'lesson_provenance':x.get('lesson_provenance'),
            'rederived_evidence':x.get('rederived_evidence')
        } for x in selected],
        'application_scope':'PRIORITIZATION_GUARDS_TEST_SELECTION_ONLY'
    }

global_history=[{
    'branch':b.get('branch'),'registered_head_sha':b.get('head_sha'),'role':b.get('role'),
    'tags':b.get('tags',[]),'lessons':b.get('lessons',[]),'evidence':b.get('evidence',[]),
    'reuse_requires_fresh_admission':b.get('reuse_requires_fresh_admission',True)
} for b in legacy]

frontier_guidance=[]
for pid in ['REPRESENTATION_AND_GROUNDING','SELF_AUDIT_AND_REPAIR','IDENTITY_AND_LINEAGE','MEMORY_AND_EXPERIENCE']:
    for x in plane_bindings[pid]['selected_history']:
        frontier_guidance.append({
            'plane':pid,'branch':x['branch'],'lessons':x['lessons'],
            'use':'DESIGN_AND_GATE_CONSTRAINTS_ONLY'
        })

binding={
 'schema':'yado.g2.applied_experience_binding.v1',
 'status':'CANONICAL_ACTIVE',
 'generation':head.get('generation_id'),
 'frontier':FRONT,
 'selection_actor':'UnifiedYADOCoreV1.experience_search',
 'selection_mode':'KERNEL_NATIVE_READ_ONLY_LEGACY_EXPERIENCE_RETRIEVAL_AND_TAG_SCORING',
 'plane_bindings':plane_bindings,
 'global_history':global_history,
 'frontier_guidance':frontier_guidance,
 'legacy_branch_count':len(legacy),
 'selected_branch_coverage':len(used_branches),
 'mechanism_reuse_requires_fresh_admission':True,
 'legacy_code_execution':False,
 'canonical_mechanism_mutation':False,
 'semantic_boundary':'HISTORICAL EXPERIENCE IS APPLIED TO G2 PRIORITIZATION, GUARDS, AND TEST SELECTION ONLY. LEGACY CODE OR CAPABILITY CLAIMS ARE NOT ACTIVATED WITHOUT A NEW FRESH ADMISSION GATE.'
}
binding['binding_digest']=cdig(binding,'binding_digest')
write(BIND,binding)

qman={
 'schema':'yado.g2.quarantine_manifest.v1',
 'status':'ACTIVE',
 'active_lineage':ACTIVE,
 'generation':head.get('generation_id'),
 'physical_quarantine':{
   'legacy_workflows':moved,
   'count':len(moved),
   'policy':'OUTSIDE_GITHUB_WORKFLOW_EXECUTION_DIRECTORY'
 },
 'logical_quarantine':{
   'historical_branch_code':'READ_ONLY_BY_REGISTERED_COMMIT_SHA',
   'superseded_candidates':'EVIDENCE_ONLY_UNLESS_FRESH_READMISSION',
   'receipts':'PERSISTENT_EVIDENCE_NOT_RUNTIME_IDENTITY',
   'architecture_history':'CAUSAL_HISTORY_NOT_ACTIVE_RUNTIME'
 },
 'preservation':{
   'delete_historical_receipts':False,
   'delete_registered_evidence':False,
   'legacy_exact_retrieval_component':'ALG-G2-LEGACY-EXPERIENCE-RETRIEVER-V1'
 },
 'operational_target':'ALL_NAMED_YADO_BRANCH_REFS_CONVERGE_TO_G2_AFTER_THIS_CANONICAL_COMMIT'
}
qman['manifest_digest']=cdig(qman,'manifest_digest')
write(QMAN,qman)

for p in core.get('planes',[]):
    pid=p.get('plane_id')
    if pid in plane_bindings:
        p['experience_binding']='canonical/yado-g2-applied-experience-binding-v1.json'
        p['experience_binding_digest']=binding['binding_digest']
        p['experience_sources']=[x['branch'] for x in plane_bindings[pid]['selected_history']]

core['applied_experience_binding']={
    'artifact':'canonical/yado-g2-applied-experience-binding-v1.json',
    'binding_digest':binding['binding_digest'],
    'selection_actor':binding['selection_actor'],
    'application_scope':'PRIORITIZATION_GUARDS_TEST_SELECTION_ONLY'
}
core['quarantine']={
    'manifest':'quarantine/yado-g2-quarantine-manifest-v1.json',
    'manifest_digest':qman['manifest_digest'],
    'legacy_workflow_count':len(moved),
    'legacy_runtime_execution_forbidden':True
}
core['invariants']=list(dict.fromkeys(core.get('invariants',[])+[
    'LEGACY_CONTROL_PLANE_IS_QUARANTINED_OUTSIDE_GITHUB_WORKFLOWS',
    'HISTORICAL_EXPERIENCE_MAY_GUIDE_G2_BUT_LEGACY_MECHANISMS_REQUIRE_FRESH_ADMISSION',
    'ALL_OPERATIONAL_BRANCH_REFS_MUST_CONVERGE_TO_SINGLE_G2_TREE_AFTER_CLOSURE'
]))

for b in legacy:
    b['control_plane_quarantined']=True
    b['physical_ref_closure_target']='G2_SINGLE_LINEAGE_CLOSURE_COMMIT'
exp.setdefault('policy',{})['legacy_control_plane_quarantined']=True
exp['policy']['historical_experience_applied_to_g2_context']=True
exp['policy']['physical_branch_ref_convergence_required']=True
exp['registry_digest']=cdig(exp,'registry_digest')
write(EXP,exp)

core['experience_registry_digest']=exp['registry_digest']
core['core_digest']=cdig(core,'core_digest')
write(CORE,core)

prov['current_g2_binding'].update({
 'current_execution_label':'G2_SINGLE_LINEAGE_QUARANTINED_WITH_APPLIED_EXPERIENCE',
 'frontier':FRONT,
 'applied_experience_binding_digest':binding['binding_digest'],
 'quarantine_manifest_digest':qman['manifest_digest'],
 'legacy_control_plane_quarantined':True
})
prov['registry_digest']=cdig(prov,'registry_digest')
write(PROV,prov)

ctx['branch_policy']['legacy_control_plane_quarantined']=True
ctx['branch_policy']['historical_experience_applied_to_g2_context']=True
ctx['branch_policy']['physical_branch_ref_convergence_required']=True
ctx['memory_planes']['historical_branch_memory']['applied_binding']='canonical/yado-g2-applied-experience-binding-v1.json'
ctx['memory_planes']['historical_branch_memory']['quarantine_manifest']='quarantine/yado-g2-quarantine-manifest-v1.json'
write(CTX,ctx)

prev=head['canonical_head_digest']
head['algorithm_provenance_registry']['registry_digest']=prov['registry_digest']
head['algorithm_provenance_registry']['current_execution_label']=prov['current_g2_binding']['current_execution_label']
head['unified_core']['algorithm_provenance_registry_digest']=prov['registry_digest']
head['unified_core']['experience_registry_digest']=exp['registry_digest']
head['unified_core']['core_digest']=core['core_digest']
head['applied_experience_binding']={'binding_digest':binding['binding_digest'],'artifact':'canonical/yado-g2-applied-experience-binding-v1.json'}
head['quarantine']={'manifest_digest':qman['manifest_digest'],'artifact':'quarantine/yado-g2-quarantine-manifest-v1.json','legacy_workflows_quarantined':len(moved)}
head['branch_history_closure']['physical_ref_convergence_required']=True
head['current_frontier']=FRONT
head['canonical_head_digest']=cdig(head,'canonical_head_digest')
write(HEAD,head)

ledger['current_head_digest']=head['canonical_head_digest']
run_id=str(os.getenv('GITHUB_RUN_ID') or 'LOCAL')
receipt={
 'schema':'yado.g2.single_lineage_closure_quarantine.receipt.v1',
 'status':'PASS_G2_SINGLE_LINEAGE_CLOSURE_QUARANTINE_V1',
 'legacy_branch_count':len(legacy),
 'legacy_workflows_quarantined':len(moved),
 'quarantine_manifest_digest':qman['manifest_digest'],
 'applied_experience_binding_digest':binding['binding_digest'],
 'plane_binding_count':len(plane_bindings),
 'selected_branch_coverage':len(used_branches),
 'global_history_branch_coverage':len(global_history),
 'frontier_unchanged':FRONT,
 'previous_head_digest':prev,'new_head_digest':head['canonical_head_digest'],
 'canonical_mutation':True,'canonical_mechanism_mutation':False,'architecture_mutation':False,
 'generation_transition':False,'g3_genesis_performed':False,
 'physical_ref_convergence_pending':True,
 'semantic_boundary':'G2 CONTROL-PLANE CLOSURE AND EXPERIENCE BINDING. HISTORICAL WORKFLOWS ARE QUARANTINED; HISTORY REMAINS READ-ONLY EVIDENCE; MECHANISM REUSE STILL REQUIRES FRESH ADMISSION.'
}
receipt['receipt_sha256']=h(receipt)
write(OUT,receipt)

e={
 'index':len(ledger['events']),
 'event_id':f"E{len(ledger['events'])+1:04d}_G2_SINGLE_LINEAGE_CLOSURE_QUARANTINE_V1",
 'event_type':'G2_SINGLE_LINEAGE_CLOSURE_QUARANTINE_AND_EXPERIENCE_BINDING',
 'status':'PASS',
 'generation':ledger['current_head'],
 'deficit':'G2_CONTROL_PLANE_FRAGMENTATION_AND_UNAPPLIED_HISTORY',
 'effect':f"LEGACY_WORKFLOWS_QUARANTINED={len(moved)}; EXPERIENCE_PLANES={len(plane_bindings)}; GLOBAL_HISTORY={len(global_history)}; FRONTIER_UNCHANGED={FRONT}; PHYSICAL_REF_CONVERGENCE=PENDING",
 'source_path':f'receipts/yado-g2-single-lineage-closure-quarantine-v1-run-{run_id}.json',
 'source_digest':receipt['receipt_sha256'],'run_id':run_id,
 'parent_event_hash':ledger['tail_event_hash'],'canonical_mutation':True,
 'canonical_mechanism_mutation':False,'architecture_mutation':False,'promotion_applied':False,
 'generation_transition':False,'previous_head_digest':prev,'new_head_digest':head['canonical_head_digest']
}
e['event_hash']=event_hash(e)
ledger['events'].append(e);ledger['event_count']=len(ledger['events']);ledger['tail_event_hash']=e['event_hash']
ledger['ledger_digest']=h({k:v for k,v in ledger.items() if k!='ledger_digest'})
validate_ledger_v2(ledger)
write(LEDGER,ledger)

snapshot=UnifiedContextKernel().snapshot()
if snapshot['current_frontier']!=FRONT or snapshot['active_lineage_count']!=1 or snapshot['historical_branch_memory_count']!=13:
    raise RuntimeError('POST_CLOSURE_CONTEXT_INVALID:'+json.dumps(snapshot))

post=subprocess.run([sys.executable,str(GUARD)],cwd=REPO,capture_output=True,text=True,timeout=60)
if post.returncode!=0:
    raise RuntimeError('POST_CLOSURE_CANONICAL_GUARD_FAILED:'+post.stdout[-5000:]+post.stderr[-2000:])

print(json.dumps({
 'status':receipt['status'],'legacy_workflows_quarantined':len(moved),
 'moved_workflows':moved,'applied_experience_binding_digest':binding['binding_digest'],
 'selected_branch_coverage':len(used_branches),'frontier':FRONT
},indent=2,sort_keys=True))
