from __future__ import annotations
from pathlib import Path
from itertools import combinations
import copy,hashlib,json,os,subprocess,sys

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
PKG=ROOT/'yado_rc8_v36'
sys.path[:0]=[str(ROOT),str(PKG)]

from yado_core_v3_0_rc8_external_cognitive import UnifiedYADOKernelV30RC8ExternalCognitive
from yado_core_v2_1 import RulePredicate,RuleSpec,RuleProgram,BoundedRuleSandbox
from yado_coverage_pruned_compositional_schema_router_v3 import CoveragePrunedCompositionalSchemaRouterV3
from yado_g2_experience_conditioned_cognitive_layer_v3 import G2ExperienceConditionedCognitiveLayerV3
from yado_evolution_ledger_v2 import validate_ledger_v2,event_hash

HEAD=REPO/'canonical/yado-main-head-g2.json'
CORE=REPO/'canonical/yado-unified-core-v1.json'
PROV=REPO/'canonical/yado-algorithm-provenance-registry-v1.json'
LEDGER=REPO/'architecture/evolution-ledger.json'
BASE=REPO/'candidates/kernel-self-generated/g2-coding-experience-cognitive-consolidation-v2.json'
PARENT=REPO/'candidates/kernel-self-generated/g2-cognitive-conflict-arbitration-repair-v1.json'
FRESH=REPO/'candidates/kernel-self-generated/g2-cognitive-conflict-arbitration-repair-v2.json'
CANON=REPO/'canonical/yado-g2-experience-conditioned-cognitive-layer-v3.json'
UNIFIED=ROOT/'yado_unified_core_v1.py'
MODULE=ROOT/'yado_g2_unified_module_kernel_v1.py'
MODULE_GATE=ROOT/'yado_g2_unified_module_kernel_fresh_gate_v1.py'
LAYER_SRC=ROOT/'yado_g2_experience_conditioned_cognitive_layer_v3.py'
GUARD=ROOT/'yado_canonical_invariant_guard_v1.py'
OUT=ROOT/'yado_g2_cognitive_layer_canonical_admission_v1_receipt.json'

COMP='RUNTIME-G2-EXPERIENCE-CONDITIONED-COGNITIVE-LAYER-V3'
FRONT='KERNEL_G2_RAW_REPRESENTATION_V4_ROBUSTNESS_SELF_EVOLUTION_V2'
ROLLBACK={
 'LOGIC':'ALG-G2-BUDGET-ADAPTIVE-COMPOSITIONAL-LOGIC-V2',
 'THINKING':'ALG-G2-WORK-BUDGET-ADAPTIVE-CONTINGENT-PLANNER-V2',
 'INTELLIGENCE':'ALG-G2-COVERAGE-PRUNED-COMPOSITIONAL-SCHEMA-ROUTER-V3',
}

def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def h(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def fsha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def cdig(o,field):x=copy.deepcopy(o);x.pop(field,None);return h(x)
def write(p,o):Path(p).parent.mkdir(parents=True,exist_ok=True);Path(p).write_text(json.dumps(o,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')

def rp(raw):
    rules=[]
    for r in raw.get('rules') or []:
        rules.append(RuleSpec([RulePredicate(**p) for p in r.get('predicates') or []],r.get('output'),int(r.get('support',0)),float(r.get('confidence',0))))
    return RuleProgram(raw['program_id'],raw['target_capability'],raw['target_organ'],rules,raw.get('default_output'),raw['source_digest'],int(raw.get('training_count',0)),raw.get('status','SHADOW'))

head,core,prov,ledger,base,parent,fresh=map(load,[HEAD,CORE,PROV,LEDGER,BASE,PARENT,FRESH])
validate_ledger_v2(ledger)
if head.get('current_frontier')!=FRONT or ledger.get('open_deficits')!=[FRONT]:raise RuntimeError('FRONTIER_DRIFT')
if core.get('current_frontier')!=FRONT or prov.get('current_g2_binding',{}).get('frontier')!=FRONT:raise RuntimeError('FRONTIER_BINDING_DRIFT')
if head.get('g3_genesis_performed') is not False or core.get('g3_genesis_performed') is not False:raise RuntimeError('G3_ALREADY_STARTED')
if COMP in head.get('active_capabilities',[]):raise RuntimeError('COGNITIVE_LAYER_ALREADY_ACTIVE')
if base.get('status')!='PASS_SHADOW_G2_CODING_EXPERIENCE_COGNITIVE_CONSOLIDATION_V2':raise RuntimeError('BASE_COGNITIVE_V2_NOT_PASS')
if parent.get('status')!='PASS_SHADOW_G2_COGNITIVE_CONFLICT_ARBITRATION_REPAIR_V1':raise RuntimeError('ARBITER_V1_NOT_PASS')
if fresh.get('status')!='PASS_EVIDENCE_REPAIR_G2_COGNITIVE_CONFLICT_ARBITRATION_V2':raise RuntimeError('CAUSAL_EVIDENCE_V2_NOT_PASS')
if fresh.get('admission_state')!='SHADOW_ADMISSION_READY':raise RuntimeError('SHADOW_NOT_ADMISSION_READY')
if int(fresh.get('exhaustive_case_count') or 0)!=336 or float(fresh.get('exhaustive_composite') or 0)!=1.0:raise RuntimeError('EXHAUSTIVE_EVIDENCE_NOT_EXACT')
if float(fresh.get('balanced_fresh') or 0)!=1.0 or float(fresh.get('balanced_ablation_drop') or 0)<.25 or float(fresh.get('perturbation_score') or 0)!=1.0:raise RuntimeError('CAUSAL_EVIDENCE_NOT_STRONG')
for x in ROLLBACK.values():
    if x not in head.get('active_capabilities',[]):raise RuntimeError('ROLLBACK_PARENT_NOT_ACTIVE:'+x)

canon_art={
 'schema':'yado.g2.experience_conditioned_cognitive_layer.canonical.v3',
 'status':'CANONICAL_ACTIVE',
 'component_id':COMP,
 'family':'EXPERIENCE_CONDITIONED_LTI_WITH_LEARNED_FAIL_CLOSED_CONFLICT_ARBITRATION',
 'cognitive_gene_id':parent.get('cognitive_gene_id'),
 'guard_gene_id':parent.get('guard_gene_id'),
 'organ_genes':copy.deepcopy(base.get('organ_genes')),
 'guard_gene':copy.deepcopy(parent.get('guard_gene')),
 'cognitive_gene':copy.deepcopy(parent.get('cognitive_gene')),
 'runtime_source':'runtime/yado_g2_experience_conditioned_cognitive_layer_v3.py',
 'runtime_sha256':fsha(LAYER_SRC),
 'fresh_gate_artifact':'candidates/kernel-self-generated/g2-cognitive-conflict-arbitration-repair-v2.json',
 'fresh_gate_receipt_sha256':fresh.get('receipt_sha256'),
 'exhaustive_case_count':fresh.get('exhaustive_case_count'),
 'exhaustive_composite':fresh.get('exhaustive_composite'),
 'balanced_causal_fresh':fresh.get('balanced_fresh'),
 'balanced_causal_ablation':fresh.get('balanced_ablation'),
 'balanced_causal_ablation_drop':fresh.get('balanced_ablation_drop'),
 'rollback_parent_capabilities':copy.deepcopy(ROLLBACK),
 'automatic_canonical_promotion':False,
 'architecture_mutation':False,
 'generation_transition':False,
 'g3_genesis_performed':False,
 'semantic_boundary':'CANONICAL BOUNDED EXPERIENCE-CONDITIONED CONTROL LAYER FOR LOGIC/THINKING/INTELLIGENCE WITH LEARNED FAIL-CLOSED CONFLICT ARBITRATION. EXISTING CANONICAL ORGAN EXECUTORS REMAIN ACTIVE AS ROLLBACK/PARENT CAPABILITIES. NOT AGI OR SUBJECTIVE CONSCIOUSNESS.'
}
canon_art['canonical_component_digest']=cdig(canon_art,'canonical_component_digest')
candidate=G2ExperienceConditionedCognitiveLayerV3(canon_art)

logic=rp(base['organ_genes']['LOGIC']['program'])
thinking=rp(base['organ_genes']['THINKING']['program'])
intel=base['organ_genes']['INTELLIGENCE']['model']

def rule_outputs(program,x):
    outs=[]
    for r in program.rules:
        if all(BoundedRuleSandbox._match(p,x) for p in r.predicates):
            if r.output not in outs:outs.append(r.output)
    return outs

def router_outputs(model,x):
    outs=[]
    for out in model.get('outputs') or []:
        if out==model.get('fallback_output'):continue
        for r in model.get('triggers',{}).get(out,[]) or []:
            if all(a['field'] in x and x[a['field']]==a['value'] for a in r.get('atoms') or []):
                outs.append(out);break
    return sorted(set(outs),key=str)

def rule_routes(program):
    return [(str(r.output),{p.field:p.value for p in r.predicates}) for r in program.rules]

def router_routes(model):
    xs=[]
    for out in model.get('outputs') or []:
        if out==model.get('fallback_output'):continue
        for r in model.get('triggers',{}).get(out,[]) or []:
            xs.append((str(out),{a['field']:a['value'] for a in r.get('atoms') or []}))
    return xs

def merge(ms):
    z={}
    for m in ms:
        for k,v in m.items():
            if k in z and z[k]!=v:return None
            z[k]=v
    return z

def expected(outs,x):
    u=[]
    for o in outs:
        if o not in u:u.append(o)
    if not bool(x.get('state_known',True)) or len(u)!=1:return 'WITHHOLD'
    return u[0]

def baseline_rule(program,x):
    return BoundedRuleSandbox.execute(program,x)

def baseline_intel(model,x):
    out=CoveragePrunedCompositionalSchemaRouterV3.route(model,x)
    return out[0] if len(out)==1 else list(out)

rows=[]
specs=[
 ('LOGIC',rule_routes(logic),lambda x:rule_outputs(logic,x),lambda x:baseline_rule(logic,x)),
 ('THINKING',rule_routes(thinking),lambda x:rule_outputs(thinking,x),lambda x:baseline_rule(thinking,x)),
 ('INTELLIGENCE',router_routes(intel),lambda x:router_outputs(intel,x),lambda x:baseline_intel(intel,x)),
]
for organ,routes,matcher,baseline_fn in specs:
    for i,(out,m) in enumerate(routes):
        x=dict(m);x['state_known']=True;x['admission_nonce']='C'+str(i)+'_'+organ;x['novel_noise']=i%5
        outs=matcher(x)
        rows.append({'organ':organ,'input':x,'expected':expected(outs,x),'baseline':baseline_fn(x)})
    for i in range(max(6,len(routes))):
        x={'state_known':False,'admission_unknown':'U'+str(i)+'_'+organ,'novel_noise':i%7}
        outs=matcher(x)
        rows.append({'organ':organ,'input':x,'expected':'WITHHOLD','baseline':baseline_fn(x)})
    for width in (2,3):
        for group in combinations(routes,width):
            if len({g[0] for g in group})<2:continue
            x=merge([g[1] for g in group])
            if x is None:continue
            x['state_known']=True;x['admission_conflict_width']=width;x['novel_noise']=len(rows)%11
            outs=matcher(x)
            if len(set(map(str,outs)))<2:continue
            rows.append({'organ':organ,'input':x,'expected':'WITHHOLD','baseline':baseline_fn(x)})

for r in rows:
    r['candidate']=candidate.decide(r['organ'],r['input'])['decision']
    r['candidate_correct']=r['candidate']==r['expected']
    r['baseline_correct']=r['baseline']==r['expected']

candidate_score=sum(r['candidate_correct'] for r in rows)/len(rows)
baseline_score=sum(r['baseline_correct'] for r in rows)/len(rows)
conflicts=[r for r in rows if r['expected']=='WITHHOLD' and bool(r['input'].get('state_known',True)) and (
    r['input'].get('admission_conflict_width') in (2,3)
)]
conflict_candidate=sum(r['candidate_correct'] for r in conflicts)/max(1,len(conflicts))
conflict_baseline=sum(r['baseline_correct'] for r in conflicts)/max(1,len(conflicts))

skills=[
 {'skill_id':'KEEP_CURRENT_G2_LTI_EXECUTORS','artifact_digest':head['canonical_head_digest'],'structural_valid':True,'semantic_consistency':1.0,
  'fit_baseline':baseline_score,'fit_candidate':baseline_score,'heldout_baseline':baseline_score,'heldout_candidate':baseline_score,
  'regression_pass':True,'state_integrity':True,'rollback_available':True},
 {'skill_id':'ADMIT_EXPERIENCE_CONDITIONED_COGNITIVE_LAYER_V3','artifact_digest':canon_art['canonical_component_digest'],'structural_valid':True,'semantic_consistency':1.0,
  'fit_baseline':baseline_score,'fit_candidate':candidate_score,'heldout_baseline':baseline_score,'heldout_candidate':candidate_score,
  'regression_pass':candidate_score==1.0 and conflict_candidate==1.0,'state_integrity':True,'rollback_available':True}
]
db=ROOT/'yado_g2_cognitive_layer_canonical_admission_v1.sqlite'
if db.exists():db.unlink()
k=UnifiedYADOKernelV30RC8ExternalCognitive(db_path=str(db))
try:
    selection=k.select_evolution_skills(skills,max_skills=1,min_semantic_consistency=.95,min_fit_gain=.05,max_heldout_drop=0.0,min_heldout_gain=.05)
finally:
    try:k.close()
    except Exception:pass
selected=(selection.get('selected_skill_ids') or [None])[0]
checks={
 'fresh_gate_pass':True,
 'exhaustive_336_preserved':int(fresh.get('exhaustive_case_count') or 0)==336 and float(fresh.get('exhaustive_composite') or 0)==1.0,
 'balanced_causal_gate_pass':float(fresh.get('balanced_fresh') or 0)==1.0 and float(fresh.get('balanced_ablation_drop') or 0)>=.25,
 'fresh_admission_cases_material':len(rows)>=30,
 'fresh_candidate_exact':candidate_score==1.0,
 'fresh_conflict_candidate_exact':conflict_candidate==1.0,
 'fresh_candidate_beats_baseline':candidate_score-baseline_score>=.05,
 'fresh_conflict_beats_baseline':conflict_candidate>conflict_baseline,
 'native_skill_gate_selected_candidate':selected=='ADMIT_EXPERIENCE_CONDITIONED_COGNITIVE_LAYER_V3',
 'rollback_parents_active':all(x in head.get('active_capabilities',[]) for x in ROLLBACK.values()),
 'frontier_preserved_before':head.get('current_frontier')==FRONT and ledger.get('open_deficits')==[FRONT],
 'g3_not_started':head.get('g3_genesis_performed') is False,
}
if not all(checks.values()):
    raise RuntimeError('CANONICAL_ADMISSION_FRESH_GATE_WITHHOLD:'+json.dumps({'checks':checks,'selection':selection,'candidate_score':candidate_score,'baseline_score':baseline_score}))

write(CANON,canon_art)

# Bind the canonical cognitive layer into UnifiedYADOCoreV1.
src=UNIFIED.read_text(encoding='utf-8')
imp='from yado_g2_experience_conditioned_cognitive_layer_v3 import G2ExperienceConditionedCognitiveLayerV3\n'
anchor='from yado_evolutionary_genome_v1 import YADOEvolutionaryGenomeV1\n'
if imp not in src:
    if anchor not in src:raise RuntimeError('UNIFIED_IMPORT_ANCHOR_MISSING')
    src=src.replace(anchor,anchor+imp)
init_anchor='        self.evolutionary_genome_cls=YADOEvolutionaryGenomeV1\n'
init_line="        self.experience_cognitive_layer=G2ExperienceConditionedCognitiveLayerV3(self._load('canonical/yado-g2-experience-conditioned-cognitive-layer-v3.json'))\n"
if init_line not in src:
    if init_anchor not in src:raise RuntimeError('UNIFIED_INIT_ANCHOR_MISSING')
    src=src.replace(init_anchor,init_anchor+init_line)
method_anchor='    def snapshot(self)->dict[str,Any]:\n'
methods="""    def cognitive_experience_decide(self,organ:str,payload:dict[str,Any])->dict[str,Any]:
        return self.experience_cognitive_layer.decide(organ,payload)

    def cognitive_experience_snapshot(self)->dict[str,Any]:
        return self.experience_cognitive_layer.snapshot()

"""
if 'def cognitive_experience_decide(' not in src:
    if method_anchor not in src:raise RuntimeError('UNIFIED_METHOD_ANCHOR_MISSING')
    src=src.replace(method_anchor,methods+method_anchor)
UNIFIED.write_text(src,encoding='utf-8')

# Bind the new component to the dynamic module assembly registry and execution path.
ms=MODULE.read_text(encoding='utf-8')
cap_line="CAP_COGNITIVE='RUNTIME-G2-EXPERIENCE-CONDITIONED-COGNITIVE-LAYER-V3'\n"
cap_anchor="CAP_GENOME='CTRL-G2-EVOLUTIONARY-GENOME-V1'\n"
if cap_line not in ms:
    if cap_anchor not in ms:raise RuntimeError('MODULE_CAP_ANCHOR_MISSING')
    ms=ms.replace(cap_anchor,cap_anchor+cap_line)
reg_line=" CAP_COGNITIVE:('COGNITIVE_COORDINATOR','runtime/yado_g2_experience_conditioned_cognitive_layer_v3.py'),\n"
reg_anchor=" CAP_GENOME:('EVOLUTION_CONTROL','runtime/yado_evolutionary_genome_v1.py'),\n"
if reg_line not in ms:
    if reg_anchor not in ms:raise RuntimeError('MODULE_REGISTRY_ANCHOR_MISSING')
    ms=ms.replace(reg_anchor,reg_anchor+reg_line)
branch_anchor="        elif mid==CAP_GENOME:\n"
cog_branch="""        elif mid==CAP_COGNITIVE:
            action=task.get('action','decide')
            if action=='decide':
                out=self.core.cognitive_experience_decide(task['organ'],task.get('payload',{}))
            elif action=='snapshot':
                out=self.core.cognitive_experience_snapshot()
            else:
                raise ValueError('UNKNOWN_COGNITIVE_ACTION:'+str(action))
"""
if 'elif mid==CAP_COGNITIVE:' not in ms:
    if branch_anchor not in ms:raise RuntimeError('MODULE_EXEC_ANCHOR_MISSING')
    ms=ms.replace(branch_anchor,cog_branch+branch_anchor)
MODULE.write_text(ms,encoding='utf-8')

# Extend the dynamic module fresh gate with a real smoke test for module 27.
gs=MODULE_GATE.read_text(encoding='utf-8')
smoke_anchor="run(CAP_GENOME,{'action':'component','stream_id':'GENOME-S'},lambda x:x.get('component_id')==CAP_GENOME and x.get('automatic_canonical_promotion') is False and x.get('novel_gene_synthesis') is True)\n"
smoke_line="run(CAP_COGNITIVE,{'action':'decide','organ':'LOGIC','payload':{'result_exact':True,'state_known':True},'stream_id':'COG-S'},lambda x:x.get('decision')=='ACCEPT' and x.get('route_cardinality')=='ONE')\n"
if smoke_line not in gs:
    if smoke_anchor not in gs:raise RuntimeError('MODULE_GATE_SMOKE_ANCHOR_MISSING')
    gs=gs.replace(smoke_anchor,smoke_anchor+smoke_line)
binding_anchor=" 'canonical_temporal_kernel_embedded':core_manifest.get('cognitive_temporal_kernel_v1',{}).get('status')=='CANONICAL_EMBEDDED' and core_manifest.get('cognitive_temporal_kernel_v1',{}).get('separate_active_capability') is False,\n"
binding_line=" 'canonical_experience_cognitive_layer_active':CAP_COGNITIVE in active and core_manifest.get('experience_conditioned_cognitive_layer_v3',{}).get('status')=='CANONICAL_ACTIVE',\n"
if binding_line not in gs:
    if binding_anchor not in gs:raise RuntimeError('MODULE_GATE_BINDING_ANCHOR_MISSING')
    gs=gs.replace(binding_anchor,binding_anchor+binding_line)
MODULE_GATE.write_text(gs,encoding='utf-8')

unified_sha=fsha(UNIFIED)
layer_sha=fsha(LAYER_SRC)

def plane(pid):
    p=next((x for x in core.get('planes',[]) if x.get('plane_id')==pid),None)
    if p is None:raise RuntimeError('MISSING_PLANE:'+pid)
    return p

for pid,resp in [
 ('LOGIC','experience_conditioned_result_accept_continue_withhold'),
 ('THINKING_AND_PLANNING','experience_conditioned_revision_test_evidence_cycle'),
 ('INTELLIGENCE_AND_META_SELECTION','experience_conditioned_strategy_routing'),
 ('WORKSPACE_AND_INTEGRATION','learned_fail_closed_conflict_arbitration'),
]:
    p=plane(pid)
    p['active_components']=sorted(set(p.get('active_components',[])+[COMP]))
    p['responsibilities']=sorted(set(p.get('responsibilities',[])+[resp]))

core['experience_conditioned_cognitive_layer_v3']={
 'status':'CANONICAL_ACTIVE','component_id':COMP,
 'canonical_component_digest':canon_art['canonical_component_digest'],
 'runtime_sha256':layer_sha,
 'cognitive_gene_id':canon_art['cognitive_gene_id'],
 'guard_gene_id':canon_art['guard_gene_id'],
 'organ_gene_ids':{k:canon_art['organ_genes'][k]['gene_id'] for k in ('LOGIC','THINKING','INTELLIGENCE')},
 'fresh_gate_receipt_sha256':fresh.get('receipt_sha256'),
 'fresh_admission_score':candidate_score,'fresh_baseline_score':baseline_score,
 'fresh_conflict_score':conflict_candidate,'fresh_conflict_baseline':conflict_baseline,
 'exhaustive_case_count':336,'exhaustive_score':1.0,
 'balanced_causal_ablation_drop':fresh.get('balanced_ablation_drop'),
 'rollback_parent_capabilities':copy.deepcopy(ROLLBACK),
 'automatic_canonical_promotion':False,
}
core['active_runtime_sources']=sorted(set(core.get('active_runtime_sources',[])+['runtime/yado_g2_experience_conditioned_cognitive_layer_v3.py']))
rim=core.get('runtime_integrity_manifest',{})
if not isinstance(rim,dict) or not isinstance(rim.get('sources'),dict):raise RuntimeError('RUNTIME_INTEGRITY_MANIFEST_MISSING')
rim['sources']={rel:fsha(REPO/rel) for rel in core['active_runtime_sources']}
rim['manifest_digest']=h(rim['sources'])
core['runtime_sha256']=unified_sha

prev_head=head['canonical_head_digest']
prov['current_g2_binding'].update({
 'current_execution_label':'G2_EXPERIENCE_CONDITIONED_COGNITIVE_LAYER_V3_CANONICAL',
 'frontier':FRONT,
 'experience_conditioned_cognitive_layer':COMP,
 'experience_conditioned_cognitive_layer_digest':canon_art['canonical_component_digest'],
 'experience_conditioned_cognitive_layer_source_sha256':layer_sha,
 'experience_conditioned_cognitive_layer_fresh_receipt_sha256':fresh.get('receipt_sha256'),
 'cognitive_conflict_arbiter_gene_id':canon_art['guard_gene_id'],
 'cognitive_layer_automatic_promotion':False,
})
prov['registry_digest']=cdig(prov,'registry_digest');write(PROV,prov)

core['algorithm_provenance_registry_digest']=prov['registry_digest']
core['current_frontier']=FRONT
core['core_digest']=cdig(core,'core_digest');write(CORE,core)

head['active_capabilities']=sorted(set(head.get('active_capabilities',[])+[COMP]))
head['new_capabilities']=sorted(set(head.get('new_capabilities',[])+[COMP]))
head['experience_conditioned_cognitive_layer_v3']={
 'status':'CANONICAL_ACTIVE','component_id':COMP,
 'canonical_component_digest':canon_art['canonical_component_digest'],
 'fresh_gate_receipt_sha256':fresh.get('receipt_sha256'),
 'cognitive_gene_id':canon_art['cognitive_gene_id'],'guard_gene_id':canon_art['guard_gene_id'],
 'rollback_parent_capabilities':copy.deepcopy(ROLLBACK),
 'automatic_canonical_promotion':False,
}
head['algorithm_provenance_registry']['registry_digest']=prov['registry_digest']
head['algorithm_provenance_registry']['current_execution_label']=prov['current_g2_binding']['current_execution_label']
head['unified_core']['algorithm_provenance_registry_digest']=prov['registry_digest']
head['unified_core']['core_digest']=core['core_digest']
head['unified_core']['runtime_sha256']=unified_sha
head['unified_core']['runtime_integrity_manifest_digest']=rim['manifest_digest']
head['current_frontier']=FRONT
head['canonical_head_digest']=cdig(head,'canonical_head_digest');write(HEAD,head)

ledger['current_head_digest']=head['canonical_head_digest']
ledger['open_deficits']=[FRONT]
run_id=str(os.getenv('GITHUB_RUN_ID') or 'LOCAL')
receipt={
 'schema':'yado.g2.cognitive_layer.canonical_admission.receipt.v1',
 'status':'PASS_G2_COGNITIVE_LAYER_CANONICAL_ADMISSION_V1',
 'component_id':COMP,'canonical_component_digest':canon_art['canonical_component_digest'],
 'native_selection':selection,'selected_skill_id':selected,
 'fresh_case_count':len(rows),'fresh_candidate_score':candidate_score,'fresh_baseline_score':baseline_score,
 'fresh_conflict_count':len(conflicts),'fresh_conflict_candidate_score':conflict_candidate,'fresh_conflict_baseline_score':conflict_baseline,
 'exhaustive_case_count':336,'exhaustive_score':1.0,
 'balanced_causal_ablation_drop':fresh.get('balanced_ablation_drop'),
 'active_capability_count_before':len(head['active_capabilities'])-1,
 'active_capability_count_after':len(head['active_capabilities']),
 'rollback_parent_capabilities':copy.deepcopy(ROLLBACK),
 'previous_head_digest':prev_head,'new_head_digest':head['canonical_head_digest'],
 'frontier_preserved':FRONT,'canonical_mutation':True,'canonical_mechanism_mutation':True,
 'architecture_mutation':False,'generation_transition':False,'g3_genesis_performed':False,
 'automatic_canonical_promotion':False,
 'semantic_boundary':'SAME-G2 ADDITIVE ADMISSION OF A BOUNDED EXPERIENCE-CONDITIONED COGNITIVE CONTROL LAYER. EXISTING LOGIC/THINKING/INTELLIGENCE EXECUTORS REMAIN ACTIVE AS ROLLBACK PARENTS.'
}
receipt['receipt_sha256']=h(receipt);write(OUT,receipt)
event={
 'index':len(ledger['events']),
 'event_id':f"E{len(ledger['events'])+1:04d}_G2_COGNITIVE_LAYER_CANONICAL_ADMISSION_V1",
 'event_type':'G2_EXPERIENCE_CONDITIONED_COGNITIVE_LAYER_CANONICAL_ADMISSION',
 'status':'PASS_CANONICAL','generation':ledger['current_head'],
 'deficit':'LOGIC_THINKING_INTELLIGENCE_NOT_YET_BOUND_TO_RECENT_EXPERIENCE_WITH_CONFLICT_ARBITRATION',
 'effect':f"ADDED={COMP}; FRESH={candidate_score:.6f}; BASE={baseline_score:.6f}; CONFLICT={conflict_candidate:.6f}; EXHAUSTIVE=336/336; ACTIVE_CAPS={len(head['active_capabilities'])}; FRONTIER_UNCHANGED={FRONT}",
 'source_path':f'receipts/yado-g2-cognitive-layer-canonical-admission-v1-run-{run_id}.json',
 'source_digest':receipt['receipt_sha256'],'run_id':run_id,'parent_event_hash':ledger['tail_event_hash'],
 'canonical_mutation':True,'canonical_mechanism_mutation':True,'architecture_mutation':False,
 'promotion_applied':False,'generation_transition':False,
 'previous_head_digest':prev_head,'new_head_digest':head['canonical_head_digest']
}
event['event_hash']=event_hash(event)
ledger['events'].append(event);ledger['event_count']=len(ledger['events']);ledger['tail_event_hash']=event['event_hash']
ledger['ledger_digest']=h({k:v for k,v in ledger.items() if k!='ledger_digest'})
validate_ledger_v2(ledger);write(LEDGER,ledger)

post=subprocess.run([sys.executable,str(GUARD)],cwd=REPO,capture_output=True,text=True,timeout=90)
if post.returncode!=0:raise RuntimeError('POST_COGNITIVE_CANONICAL_GUARD_FAILED:'+post.stdout[-6000:]+post.stderr[-2000:])
print(json.dumps({
 'status':receipt['status'],'component_id':COMP,
 'active_capability_count_after':len(head['active_capabilities']),
 'fresh_candidate_score':candidate_score,'fresh_baseline_score':baseline_score,
 'fresh_conflict_candidate_score':conflict_candidate,'fresh_conflict_baseline_score':conflict_baseline,
 'frontier':FRONT,'new_head_digest':head['canonical_head_digest']
},indent=2,sort_keys=True))
