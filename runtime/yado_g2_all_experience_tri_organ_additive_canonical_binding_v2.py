from __future__ import annotations

from pathlib import Path
import copy, hashlib, json, os, py_compile, subprocess, sys

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
PKG=ROOT/'yado_rc8_v36'
sys.path[:0]=[str(ROOT),str(PKG)]

from yado_evolution_ledger_v2 import validate_ledger_v2,event_hash

HEAD=REPO/'canonical/yado-main-head-g2.json'
CORE=REPO/'canonical/yado-unified-core-v1.json'
PROV=REPO/'canonical/yado-algorithm-provenance-registry-v1.json'
LEDGER=REPO/'architecture/evolution-ledger.json'
TRI=REPO/'experience/yado-all-experience-tri-organ-genesis-v1.json'
REVIEW=REPO/'candidates/kernel-self-generated/g2-all-experience-tri-organ-canonical-admission-review-v2.json'
DNS=REPO/'candidates/kernel-self-generated/g2-dns-gcp-cross-domain-research-stress-v1.json'
FOUR=REPO/'candidates/kernel-self-generated/g2-four-domain-fresh-stress-v1.json'
RUNTIME=ROOT/'yado_g2_all_experience_tri_organ_runtime_v1.py'
UNIFIED=ROOT/'yado_unified_core_v1.py'
MODULE=ROOT/'yado_g2_unified_module_kernel_v1.py'
FRESH_GATE=ROOT/'yado_g2_unified_module_kernel_fresh_gate_v1.py'
POST_INTEGRITY=ROOT/'yado_g2_post_module_full_integrity_v1.py'
GUARD=ROOT/'yado_canonical_invariant_guard_v1.py'
CANON=REPO/'canonical/yado-g2-all-experience-tri-organ-v1.json'
OUT=REPO/'candidates/kernel-self-generated/g2-all-experience-tri-organ-additive-canonical-binding-v2.json'
MARKER=ROOT/'yado_tri_organ_binding_v2_commit_ready.marker'

FRONT='KERNEL_G2_RAW_REPRESENTATION_V4_ROBUSTNESS_SELF_EVOLUTION_V2'
CAP_LOGIC='ALG-G2-ALL-EXPERIENCE-RELATIONAL-CAUSAL-LOGIC-V1'
CAP_THINK='ALG-G2-ALL-EXPERIENCE-CAUSAL-EVENT-THINKING-V1'
CAP_INTEL='ALG-G2-ALL-EXPERIENCE-CAUSAL-GENE-PORTFOLIO-INTELLIGENCE-V1'
PARENT_LOGIC='ALG-G2-BUDGET-ADAPTIVE-COMPOSITIONAL-LOGIC-V2'
PARENT_THINK='ALG-G2-WORK-BUDGET-ADAPTIVE-CONTINGENT-PLANNER-V2'
PARENT_INTEL='ALG-G2-COVERAGE-PRUNED-COMPOSITIONAL-SCHEMA-ROUTER-V3'
V4='RUNTIME-G2-EXPERIENCE-CONDITIONED-COGNITIVE-LAYER-V4'
V7='CTRL-G2-GLOBAL-EXPERIENCE-META-CONTROLLER-V7'

def load(p): return json.loads(Path(p).read_text(encoding='utf-8'))
def canon(o): return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def h(o): return hashlib.sha256(canon(o).encode()).hexdigest()
def fsha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def cdig(o,field):
    x=copy.deepcopy(o);x.pop(field,None);return h(x)
def write(p,o):
    Path(p).parent.mkdir(parents=True,exist_ok=True)
    Path(p).write_text(json.dumps(o,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')
def replace_once(text,old,new,label):
    if old in text:return text.replace(old,new,1)
    if new in text:return text
    raise RuntimeError('PATCH_ANCHOR_MISSING:'+label)
def run(cmd,timeout=180):
    p=subprocess.run(cmd,cwd=REPO,capture_output=True,text=True,timeout=timeout)
    if p.returncode!=0:
        raise RuntimeError('COMMAND_FAILED:'+repr(cmd)+'\nSTDOUT\n'+p.stdout[-9000:]+'\nSTDERR\n'+p.stderr[-5000:])
    return {'returncode':p.returncode,'stdout_tail':p.stdout[-4000:],'stderr_tail':p.stderr[-2000:]}

if MARKER.exists(): MARKER.unlink()

head,core,prov,ledger,tri,review,dns,four=map(load,[HEAD,CORE,PROV,LEDGER,TRI,REVIEW,DNS,FOUR])
validate_ledger_v2(ledger)
pre_guard=run([sys.executable,str(GUARD)],90)

active=set(head.get('active_capabilities') or [])
new_caps={CAP_LOGIC,CAP_THINK,CAP_INTEL}
parents={PARENT_LOGIC,PARENT_THINK,PARENT_INTEL,V4,V7}
checks={
 'review_pass':review.get('status')=='PASS_REVIEW_G2_ALL_EXPERIENCE_TRI_ORGAN_CANONICAL_ADMISSION_V2',
 'tri_genesis_trained':tri.get('status')=='TRAINED_SHADOW',
 'dns_gcp_pass':dns.get('status')=='PASS_SHADOW_G2_DNS_GCP_CROSS_DOMAIN_RESEARCH_STRESS_V1',
 'four_domain_pass':four.get('status')=='PASS_SHADOW_G2_FOUR_DOMAIN_FRESH_STRESS_V1',
 'generation_g2':head.get('generation_id')=='G2_CANDIDATE_TRCG_V1',
 'frontier_preserved_pre':head.get('current_frontier')==FRONT and core.get('current_frontier')==FRONT and ledger.get('open_deficits')==[FRONT],
 'g3_not_started_pre':head.get('g3_genesis_performed') is False and core.get('g3_genesis_performed') is False,
 'new_caps_not_active_pre':not (new_caps & active),
 'rollback_parents_all_active_pre':parents <= active,
 'review_additive_only':review.get('admission_plan',{}).get('replace_existing_organs') is False,
 'review_next_binding':review.get('next_required_capability')=='TRI_ORGAN_ADDITIVE_CANONICAL_BINDING_V2',
 'pre_guard_pass':True,
}
if not all(checks.values()):
    out={'schema':'yado.g2.all_experience_tri_organ.additive_canonical_binding.v2',
         'status':'WITHHOLD_G2_TRI_ORGAN_ADDITIVE_CANONICAL_BINDING_V2',
         'checks':checks,'canonical_mutation':False,'next_required_capability':'TRI_ORGAN_BINDING_PRECONDITION_REPAIR_V3'}
    out['receipt_sha256']=h(out);write(OUT,out);raise SystemExit(2)

genes=copy.deepcopy(tri['genes'])
genome=copy.deepcopy(tri['genome'])
runtime_sha=fsha(RUNTIME)
canonical_art={
 'schema':'yado.g2.all_experience_tri_organ.canonical.v1',
 'status':'CANONICAL_ACTIVE',
 'genome_id':genome['genome_id'],'genome_digest':genome['genome_digest'],
 'components':{'LOGIC':CAP_LOGIC,'THINKING':CAP_THINK,'INTELLIGENCE':CAP_INTEL},
 'genes':genes,
 'contract_routes':{
   'RELATION_START_TO_STATE':CAP_LOGIC,
   'EVENT_SEQUENCE_TO_BOOLEAN':CAP_THINK,
 },
 'rollback_parents':{'LOGIC':PARENT_LOGIC,'THINKING':PARENT_THINK,'INTELLIGENCE':PARENT_INTEL},
 'v4_preserved':True,'v7_preserved':True,'replace_existing_organs':False,
 'runtime_source':'runtime/yado_g2_all_experience_tri_organ_runtime_v1.py',
 'runtime_sha256':runtime_sha,
 'source_genesis_receipt_sha256':review['evidence']['tri_genesis_receipt_sha256'],
 'source_dns_gcp_receipt_sha256':dns['receipt_sha256'],
 'source_four_domain_receipt_sha256':four['receipt_sha256'],
 'source_admission_review_receipt_sha256':review['receipt_sha256'],
 'cross_domain_floor':copy.deepcopy(review['cross_domain_floor']),
 'automatic_canonical_promotion':False,'generation_transition':False,'g3_genesis_performed':False,
 'semantic_boundary':'SAME-G2 ADDITIVE CANONICAL BINDING OF THREE EXPERIENCE-DERIVED SHADOW ORGAN TYPES. V2/V2/V3 REMAIN ACTIVE ROLLBACK PARENTS. CONTRACT ROUTING IS BOUNDED TO THE TWO FRESHLY PROVEN META-LANGUAGE CONTRACTS. UNSUPPORTED CONTRACTS FAIL CLOSED.'
}
canonical_art['canonical_component_digest']=cdig(canonical_art,'canonical_component_digest')
write(CANON,canonical_art)

# Bind the canonical artifact into the unified core runtime.
us=UNIFIED.read_text(encoding='utf-8')
import_anchor='from yado_g2_global_experience_meta_controller_v7 import G2GlobalExperienceMetaControllerV7\n'
import_line='from yado_g2_all_experience_tri_organ_runtime_v1 import G2AllExperienceTriOrganRuntimeV1\n'
us=replace_once(us,import_anchor,import_anchor+import_line,'UNIFIED_TRI_IMPORT')
init_anchor="        self.global_experience_meta_controller=G2GlobalExperienceMetaControllerV7(self._load('canonical/yado-g2-global-experience-meta-controller-v7.json'))\n"
init_line="        self.all_experience_tri_organ=G2AllExperienceTriOrganRuntimeV1(self._load('canonical/yado-g2-all-experience-tri-organ-v1.json'))\n"
us=replace_once(us,init_anchor,init_anchor+init_line,'UNIFIED_TRI_INIT')
method_anchor='    def cognitive_experience_decide(self,organ:str,payload:dict[str,Any])->dict[str,Any]:\n'
methods="""    def all_experience_logic(self,relation,start)->dict[str,Any]:
        return self.all_experience_tri_organ.logic(relation,start)

    def all_experience_thinking(self,events)->dict[str,Any]:
        return self.all_experience_tri_organ.thinking(events)

    def all_experience_intelligence(self,task:dict[str,Any])->dict[str,Any]:
        return self.all_experience_tri_organ.intelligence(task)

    def all_experience_tri_organ_snapshot(self)->dict[str,Any]:
        return self.all_experience_tri_organ.snapshot()

"""
us=replace_once(us,method_anchor,methods+method_anchor,'UNIFIED_TRI_METHODS')
UNIFIED.write_text(us,encoding='utf-8')

# Bind three additive capabilities into the unified module registry/dispatcher.
ms=MODULE.read_text(encoding='utf-8')
mi="from yado_g2_all_experience_tri_organ_runtime_v1 import CAP_LOGIC as CAP_TRI_LOGIC,CAP_THINKING as CAP_TRI_THINKING,CAP_INTELLIGENCE as CAP_TRI_INTELLIGENCE\n"
import_anchor2='from yado_evolutionary_genome_v1 import YADOEvolutionaryGenomeV1\n'
ms=replace_once(ms,import_anchor2,import_anchor2+mi,'MODULE_TRI_IMPORT')
reg_anchor=" CAP_META_V7:('META_CONTROLLER','runtime/yado_g2_global_experience_meta_controller_v7.py'),\n"
reg_add=""" CAP_TRI_LOGIC:('EXECUTOR','runtime/yado_g2_all_experience_tri_organ_runtime_v1.py'),
 CAP_TRI_THINKING:('EXECUTOR','runtime/yado_g2_all_experience_tri_organ_runtime_v1.py'),
 CAP_TRI_INTELLIGENCE:('META_SELECTOR','runtime/yado_g2_all_experience_tri_organ_runtime_v1.py'),
"""
ms=replace_once(ms,reg_anchor,reg_anchor+reg_add,'MODULE_TRI_REGISTRY')
exec_anchor='        elif mid==CAP_META_V7:\n'
exec_add="""        elif mid==CAP_TRI_LOGIC:
            out=self.core.all_experience_logic(task.get('relation',()),task.get('start'))
        elif mid==CAP_TRI_THINKING:
            out=self.core.all_experience_thinking(task.get('events',()))
        elif mid==CAP_TRI_INTELLIGENCE:
            out=self.core.all_experience_intelligence(task)
"""
ms=replace_once(ms,exec_anchor,exec_add+exec_anchor,'MODULE_TRI_EXEC')
MODULE.write_text(ms,encoding='utf-8')

# Compile the runtime surfaces before touching canonical digests.
for p in [RUNTIME,UNIFIED,MODULE,FRESH_GATE,POST_INTEGRITY]:
    py_compile.compile(str(p),doraise=True)

# Plane placement is explicit and additive.
plane_map={
 'LOGIC':(CAP_LOGIC,'experience_derived_relational_causal_closure_logic'),
 'THINKING_AND_PLANNING':(CAP_THINK,'experience_derived_causal_event_state_thinking'),
 'INTELLIGENCE_AND_META_SELECTION':(CAP_INTEL,'experience_conditioned_causal_gene_portfolio_routing'),
}
for pid,(comp,resp) in plane_map.items():
    plane=next((x for x in core.get('planes',[]) if x.get('plane_id')==pid),None)
    if plane is None: raise RuntimeError('MISSING_PLANE:'+pid)
    plane['active_components']=sorted(set(plane.get('active_components',[])+[comp]))
    plane['responsibilities']=sorted(set(plane.get('responsibilities',[])+[resp]))

core['all_experience_tri_organ_v1']={
 'status':'CANONICAL_ACTIVE','genome_id':genome['genome_id'],'genome_digest':genome['genome_digest'],
 'canonical_component_digest':canonical_art['canonical_component_digest'],
 'components':copy.deepcopy(canonical_art['components']),
 'rollback_parents':copy.deepcopy(canonical_art['rollback_parents']),
 'contract_routes':copy.deepcopy(canonical_art['contract_routes']),
 'runtime_source':canonical_art['runtime_source'],'runtime_sha256':runtime_sha,
 'replace_existing_organs':False,'v4_preserved':True,'v7_preserved':True,
 'automatic_canonical_promotion':False,
}
extra_sources=[
 'runtime/yado_g2_all_experience_tri_organ_runtime_v1.py',
 'runtime/yado_generic_relational_meta_language_v1.py',
 'runtime/yado_generic_event_state_meta_language_v1.py',
]
core['active_runtime_sources']=sorted(set(core.get('active_runtime_sources',[])+extra_sources))
rim=core.get('runtime_integrity_manifest',{})
if not isinstance(rim,dict) or not isinstance(rim.get('sources'),dict):
    raise RuntimeError('RUNTIME_INTEGRITY_MANIFEST_MISSING')
rim['sources']={rel:fsha(REPO/rel) for rel in core['active_runtime_sources']}
rim['manifest_digest']=h(rim['sources'])

# Provenance records the additive nature; old active component fields remain unchanged.
binding=prov['current_g2_binding']
binding.update({
 'current_execution_label':'G2_COGNITIVE_CONTINUITY_V5_PLUS_GLOBAL_EXPERIENCE_META_V7_PLUS_TRI_ORGAN_V1_CANONICAL',
 'frontier':FRONT,
 'all_experience_tri_organ_genome_id':genome['genome_id'],
 'all_experience_tri_organ_component_digest':canonical_art['canonical_component_digest'],
 'all_experience_tri_organ_runtime_sha256':runtime_sha,
 'all_experience_tri_organ_logic_component':CAP_LOGIC,
 'all_experience_tri_organ_thinking_component':CAP_THINK,
 'all_experience_tri_organ_intelligence_component':CAP_INTEL,
 'all_experience_tri_organ_replace_existing_organs':False,
 'all_experience_tri_organ_automatic_promotion':False,
})
mechs=prov.get('mechanisms',[])
existing={x.get('mechanism_id') for x in mechs}
for mid,role,semantic in [
 (CAP_LOGIC,'CANONICAL_ADDITIVE_LOGIC','RELATIONAL_CAUSAL_CLOSURE_OVER_SELF_SYNTHESIZED_META_LANGUAGE_GENE'),
 (CAP_THINK,'CANONICAL_ADDITIVE_THINKING','CAUSAL_EVENT_STATE_STACK_PROCESSING_OVER_SELF_SYNTHESIZED_META_LANGUAGE_GENE'),
 (CAP_INTEL,'CANONICAL_ADDITIVE_INTELLIGENCE','EXPERIENCE_CONDITIONED_CONTRACT_ROUTING_OVER_CAUSALLY_VALIDATED_SELF_SYNTHESIZED_GENE_PORTFOLIO'),
]:
    if mid not in existing:
        mechs.append({
          'mechanism_id':mid,'method':'execute','owner_class':'G2AllExperienceTriOrganRuntimeV1',
          'owner_module':'yado_g2_all_experience_tri_organ_runtime_v1','role':role,'semantic':semantic,
          'signature':'bounded contract-specific runtime dispatch',
          'source_path':'runtime/yado_g2_all_experience_tri_organ_runtime_v1.py','source_sha256':runtime_sha,
          'rollback_parent':canonical_art['rollback_parents'][{'CANONICAL_ADDITIVE_LOGIC':'LOGIC','CANONICAL_ADDITIVE_THINKING':'THINKING','CANONICAL_ADDITIVE_INTELLIGENCE':'INTELLIGENCE'}[role]],
        })
prov['mechanisms']=mechs
prov['registry_digest']=cdig(prov,'registry_digest')
write(PROV,prov)

core['algorithm_provenance_registry_digest']=prov['registry_digest']
core['current_frontier']=FRONT
core['runtime_sha256']=fsha(UNIFIED)
core['core_digest']=cdig(core,'core_digest')
write(CORE,core)

prev_head=head['canonical_head_digest']
head['active_capabilities']=sorted(set(head.get('active_capabilities',[])+list(new_caps)))
head['new_capabilities']=sorted(set(head.get('new_capabilities',[])+list(new_caps)))
head['all_experience_tri_organ_v1']={
 'status':'CANONICAL_ACTIVE','genome_id':genome['genome_id'],'genome_digest':genome['genome_digest'],
 'canonical_component_digest':canonical_art['canonical_component_digest'],
 'components':copy.deepcopy(canonical_art['components']),
 'rollback_parents':copy.deepcopy(canonical_art['rollback_parents']),
 'replace_existing_organs':False,'v4_preserved':True,'v7_preserved':True,
 'automatic_canonical_promotion':False,
}
head['algorithm_provenance_registry']['registry_digest']=prov['registry_digest']
head['algorithm_provenance_registry']['current_execution_label']=binding['current_execution_label']
head['unified_core']['algorithm_provenance_registry_digest']=prov['registry_digest']
head['unified_core']['core_digest']=core['core_digest']
head['unified_core']['runtime_sha256']=core['runtime_sha256']
head['unified_core']['runtime_integrity_manifest_digest']=rim['manifest_digest']
head['unified_core']['logic_additive_components']=sorted(set(head['unified_core'].get('logic_additive_components',[])+[CAP_LOGIC]))
head['unified_core']['thinking_additive_components']=sorted(set(head['unified_core'].get('thinking_additive_components',[])+[CAP_THINK]))
head['unified_core']['intelligence_additive_components']=sorted(set(head['unified_core'].get('intelligence_additive_components',[])+[CAP_INTEL]))
head['current_frontier']=FRONT
head['canonical_head_digest']=cdig(head,'canonical_head_digest')
write(HEAD,head)

# A canonical head digest must always have a causal canonical-mutation event.
# Create a provisional tail event in the ephemeral checkout before running any post-binding
# guard. It is not persistable unless all gates pass and the final receipt rewrites its
# evidence binding below.
run_id=str(os.getenv('GITHUB_RUN_ID') or 'LOCAL')
provisional_event={
 'index':len(ledger['events']),
 'event_id':f"E{len(ledger['events'])+1:04d}_G2_ALL_EXPERIENCE_TRI_ORGAN_ADDITIVE_CANONICAL_BINDING_V2",
 'event_type':'G2_ALL_EXPERIENCE_TRI_ORGAN_ADDITIVE_CANONICAL_BINDING',
 'status':'PASS_CANONICAL','generation':ledger['current_head'],
 'deficit':'EXPERIENCE_DERIVED_TRI_ORGAN_TYPES_SHADOW_ONLY',
 'effect':f"ADDED={CAP_LOGIC},{CAP_THINK},{CAP_INTEL}; PARENTS_PRESERVED=true; ACTIVE_CAPS={len(head['active_capabilities'])}; FRONTIER_UNCHANGED={FRONT}",
 'source_path':'candidates/kernel-self-generated/g2-all-experience-tri-organ-canonical-admission-review-v2.json',
 'source_digest':review['receipt_sha256'],'run_id':run_id,
 'parent_event_hash':ledger['tail_event_hash'],
 'canonical_mutation':True,'canonical_mechanism_mutation':True,'architecture_mutation':False,
 'promotion_applied':False,'generation_transition':False,
 'previous_head_digest':prev_head,'new_head_digest':head['canonical_head_digest']
}
provisional_event['event_hash']=event_hash(provisional_event)
ledger['events'].append(provisional_event)
ledger['event_count']=len(ledger['events'])
ledger['tail_event_hash']=provisional_event['event_hash']
ledger['current_head_digest']=head['canonical_head_digest']
ledger['open_deficits']=[FRONT]
ledger['ledger_digest']=h({k:v for k,v in ledger.items() if k!='ledger_digest'})
validate_ledger_v2(ledger)
write(LEDGER,ledger)

guard_after_mutation=run([sys.executable,str(GUARD)],90)
regression=run([sys.executable,'-m','unittest','discover','-s','tests','-p','test_*.py','-v'],180)
fresh_gate=run([sys.executable,str(FRESH_GATE)],240)
assembly=load(REPO/'candidates/kernel-self-generated/g2-unified-module-kernel-v1.json')
if assembly.get('status')!='PASS_CURRENT_G2_UNIFIED_MODULE_ASSEMBLY_V1' or assembly.get('canonical_ready') is not True:
    raise RuntimeError('TRI_ORGAN_MODULE_ASSEMBLY_WITHHOLD:'+canon(assembly))
post_gate=run([sys.executable,str(POST_INTEGRITY)],240)
post_report=load(REPO/'audits/yado-g2-post-module-full-integrity-v1.json')
if post_report.get('status')!='PASS_G2_POST_MODULE_FULL_INTEGRITY_V1':
    raise RuntimeError('TRI_ORGAN_POST_MODULE_WITHHOLD:'+canon(post_report))

# Only now create the immutable receipt for this same-G2 canonical mechanism mutation.
receipt={
 'schema':'yado.g2.all_experience_tri_organ.additive_canonical_binding.v2',
 'status':'PASS_G2_TRI_ORGAN_ADDITIVE_CANONICAL_BINDING_V2',
 'genome_id':genome['genome_id'],'genome_digest':genome['genome_digest'],
 'components':copy.deepcopy(canonical_art['components']),
 'rollback_parents':copy.deepcopy(canonical_art['rollback_parents']),
 'replace_existing_organs':False,'v4_preserved':True,'v7_preserved':True,
 'active_capability_count_before':len(active),'active_capability_count_after':len(head['active_capabilities']),
 'active_runtime_source_count_after':len(core['active_runtime_sources']),
 'previous_head_digest':prev_head,'new_head_digest':head['canonical_head_digest'],
 'frontier_preserved':FRONT,
 'evidence':{
   'review_receipt_sha256':review['receipt_sha256'],
   'dns_gcp_receipt_sha256':dns['receipt_sha256'],
   'four_domain_receipt_sha256':four['receipt_sha256'],
   'canonical_component_digest':canonical_art['canonical_component_digest'],
 },
 'post_binding_gates':{
   'canonical_guard':True,'regression_tests':True,
   'unified_module_fresh_gate':assembly.get('status'),
   'post_module_integrity':post_report.get('status'),
 },
 'canonical_mutation':True,'canonical_mechanism_mutation':True,
 'architecture_mutation':False,'generation_transition':False,'g3_genesis_performed':False,
 'automatic_canonical_promotion':False,
 'next_required_capability':'TRI_ORGAN_CANONICAL_BURNIN_AND_OLD_PARENT_COMPARATIVE_AB_V1',
 'semantic_boundary':'SAME-G2 ADDITIVE ADMISSION. THE NEW EXPERIENCE-DERIVED LOGIC/THINKING/INTELLIGENCE CAPABILITIES ARE ACTIVE BESIDE, NOT INSTEAD OF, V2/V2/V3. UNSUPPORTED CONTRACTS FAIL CLOSED. MAIN IS NOT UPDATED BY THIS SHADOW BINDING STEP.'
}
receipt['receipt_sha256']=h(receipt)
write(OUT,receipt)
receipt_path=REPO/f'receipts/yado-g2-all-experience-tri-organ-additive-canonical-binding-v2-run-{run_id}.json'
write(receipt_path,receipt)

# Finalize the already-validated provisional tail event with the immutable PASS receipt.
event=ledger['events'][-1]
expected_event_id=f"E{len(ledger['events']):04d}_G2_ALL_EXPERIENCE_TRI_ORGAN_ADDITIVE_CANONICAL_BINDING_V2"
if event.get('event_id')!=expected_event_id:
    raise RuntimeError('PROVISIONAL_EVENT_ID_DRIFT:'+str(event.get('event_id'))+'!='+expected_event_id)
event['source_path']=f'receipts/yado-g2-all-experience-tri-organ-additive-canonical-binding-v2-run-{run_id}.json'
event['source_digest']=receipt['receipt_sha256']
event['event_hash']=event_hash(event)
ledger['tail_event_hash']=event['event_hash']
ledger['ledger_digest']=h({k:v for k,v in ledger.items() if k!='ledger_digest'})
validate_ledger_v2(ledger);write(LEDGER,ledger)

final_guard=run([sys.executable,str(GUARD)],90)
# Re-run post-module after the ledger event is durable in the local candidate tree.
final_post=run([sys.executable,str(POST_INTEGRITY)],240)
final_post_report=load(REPO/'audits/yado-g2-post-module-full-integrity-v1.json')
if final_post_report.get('status')!='PASS_G2_POST_MODULE_FULL_INTEGRITY_V1':
    raise RuntimeError('FINAL_POST_EVENT_INTEGRITY_WITHHOLD:'+canon(final_post_report))

MARKER.write_text(receipt['receipt_sha256']+'\n',encoding='utf-8')
print(json.dumps({
 'status':receipt['status'],'components':receipt['components'],
 'active_capability_count_after':receipt['active_capability_count_after'],
 'active_runtime_source_count_after':receipt['active_runtime_source_count_after'],
 'new_head_digest':receipt['new_head_digest'],'frontier':FRONT,
 'module_assembly':assembly.get('status'),'post_module_integrity':final_post_report.get('status'),
 'next_required_capability':receipt['next_required_capability'],
 'commit_ready_marker':str(MARKER.relative_to(REPO)),
},indent=2,sort_keys=True))
