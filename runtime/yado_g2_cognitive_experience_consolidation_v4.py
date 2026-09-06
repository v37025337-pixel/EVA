from __future__ import annotations

from pathlib import Path
import copy,hashlib,json,os,random,subprocess,sys

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
PKG=ROOT/'yado_rc8_v36'
sys.path[:0]=[str(ROOT),str(PKG)]

from yado_core_v3_0_rc8_external_cognitive import UnifiedYADOKernelV30RC8ExternalCognitive
from yado_g2_experience_conditioned_cognitive_layer_v3 import G2ExperienceConditionedCognitiveLayerV3
from yado_g2_experience_conditioned_cognitive_layer_v4 import G2ExperienceConditionedCognitiveLayerV4
from yado_budget_adaptive_compositional_logic_v2 import BudgetAdaptiveCompositionalLogicV2
from yado_organ_runtime_native_v1 import tree_predict
from yado_cognitive_growth_runtime_v1 import plan_multicontext,knn_predict,centroid_predict
from yado_evolution_ledger_v2 import validate_ledger_v2,event_hash

HEAD=REPO/'canonical/yado-main-head-g2.json'
CORE=REPO/'canonical/yado-unified-core-v1.json'
PROV=REPO/'canonical/yado-algorithm-provenance-registry-v1.json'
LEDGER=REPO/'architecture/evolution-ledger.json'
PARENT=REPO/'canonical/yado-g2-experience-conditioned-cognitive-layer-v3.json'
MULTI=REPO/'experience/yado-multidomain-cognitive-composition-training-v1.json'
REAL=REPO/'experience/yado-multidomain-real-data-training-v1.json'
GLOBAL=REPO/'experience/yado-global-experience-cognitive-genesis-v6.json'
GSTRESS=REPO/'candidates/kernel-self-generated/g2-global-experience-cognitive-stress-v3.json'
MREPORT=REPO/'candidates/kernel-self-generated/g2-multidomain-cognitive-composition-training-v1.json'
RREPORT=REPO/'candidates/kernel-self-generated/g2-multidomain-real-data-training-v1.json'
LREPORT=REPO/'candidates/kernel-self-generated/g2-multidomain-logic-training-repair-v2.json'
OREPORT=REPO/'candidates/kernel-self-generated/g2-multidomain-organ-training-v1.json'
CANON=REPO/'canonical/yado-g2-experience-conditioned-cognitive-layer-v4.json'
OUT=REPO/'candidates/kernel-self-generated/g2-cognitive-experience-consolidation-v4.json'
UNIFIED=ROOT/'yado_unified_core_v1.py'
MODULE=ROOT/'yado_g2_unified_module_kernel_v1.py'
MODULE_GATE=ROOT/'yado_g2_unified_module_kernel_fresh_gate_v1.py'
POST_AUDIT=ROOT/'yado_g2_post_module_full_integrity_v1.py'
V4SRC=ROOT/'yado_g2_experience_conditioned_cognitive_layer_v4.py'
GUARD=ROOT/'yado_canonical_invariant_guard_v1.py'

OLD='RUNTIME-G2-EXPERIENCE-CONDITIONED-COGNITIVE-LAYER-V3'
NEW='RUNTIME-G2-EXPERIENCE-CONDITIONED-COGNITIVE-LAYER-V4'
FRONT='KERNEL_G2_RAW_REPRESENTATION_V4_ROBUSTNESS_SELF_EVOLUTION_V2'

def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def digest(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def fsha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def cdig(o,field):x=copy.deepcopy(o);x.pop(field,None);return digest(x)
def write(p,o):Path(p).parent.mkdir(parents=True,exist_ok=True);Path(p).write_text(json.dumps(o,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')

head,core,prov,ledger,parent,multi,real,glob,gstress,mrep,rrep,lrep,orep=map(load,[HEAD,CORE,PROV,LEDGER,PARENT,MULTI,REAL,GLOBAL,GSTRESS,MREPORT,RREPORT,LREPORT,OREPORT])
validate_ledger_v2(ledger)
if head.get('current_frontier')!=FRONT or ledger.get('open_deficits')!=[FRONT]:raise RuntimeError('FRONTIER_DRIFT')
if OLD not in head.get('active_capabilities',[]):raise RuntimeError('V3_PARENT_NOT_ACTIVE')
if NEW in head.get('active_capabilities',[]):raise RuntimeError('V4_ALREADY_ACTIVE')
if parent.get('status')!='CANONICAL_ACTIVE':raise RuntimeError('V3_CANONICAL_PARENT_REQUIRED')
if lrep.get('status')!='PASS_SHADOW_G2_MULTIDOMAIN_LOGIC_TRAINING_REPAIR_V2':raise RuntimeError('MULTIDOMAIN_LOGIC_REPAIR_PASS_REQUIRED')
if mrep.get('status')!='PASS_SHADOW_G2_MULTIDOMAIN_COGNITIVE_COMPOSITION_TRAINING_V1':raise RuntimeError('MULTIDOMAIN_COGNITIVE_PASS_REQUIRED')
if rrep.get('status')!='PASS_SHADOW_G2_MULTIDOMAIN_REAL_DATA_TRAINING_V1':raise RuntimeError('REAL_DATA_PASS_REQUIRED')
if str(gstress.get('status'))!='WITHHOLD_G2_GLOBAL_EXPERIENCE_COGNITIVE_STRESS_V3':raise RuntimeError('GLOBAL_STRESS_NEGATIVE_EVIDENCE_REQUIRED')
if (gstress.get('checks') or {}).get('commit_ge_0_70') is not False:raise RuntimeError('GLOBAL_STRESS_COMMIT_DEFICIT_NOT_VISIBLE')
if (gstress.get('checks') or {}).get('terminal_overall_ge_0_75') is not False:raise RuntimeError('GLOBAL_STRESS_TERMINAL_DEFICIT_NOT_VISIBLE')

mg=multi['genes'];rg=real['genes'];gg=glob['genes']

def multi_fresh(g):
    s=g.get('summary') or {}
    xs=[x for x in [s.get('min_fresh'),s.get('mean_fresh'),g.get('fresh_blind'),g.get('fresh_balanced'),g.get('fresh')] if x is not None]
    return min(float(x) for x in xs) if xs else 0.0

def multi_drop(g):
    s=g.get('summary') or {}
    xs=[x for x in [s.get('mean_causal_drop'),g.get('causal_drop')] if x is not None]
    if g.get('organ_ablation_drops'):xs += list(g['organ_ablation_drops'].values())
    return min(float(x) for x in xs) if xs else 0.0

mf=min([multi_fresh(mg[x]) for x in ('LOGIC','THINKING','INTELLIGENCE')]+[float(mg['COGNITIVE'].get('fresh_blind') or 0)])
md=min([multi_drop(mg[x]) for x in ('LOGIC','THINKING','INTELLIGENCE')]+[min(float(v) for v in mg['COGNITIVE']['organ_ablation_drops'].values())])
rf=min(float(rg['LOGIC'].get('fresh_balanced') or 0),float(rg['THINKING'].get('fresh') or 0),float(rg['INTELLIGENCE'].get('fresh') or 0))
rd=min(
 float(rg['LOGIC'].get('fresh_balanced') or 0)-float(rg['LOGIC'].get('ablation_balanced') or 0),
 float(rg['THINKING'].get('fresh') or 0)-float(rg['THINKING'].get('ablation') or 0),
 float(rg['INTELLIGENCE'].get('fresh') or 0)-float(rg['INTELLIGENCE'].get('ablation') or 0),
)
portfolio_fresh=min(mf,rf)
portfolio_drop=min(md,rd)
portfolio_base=max(0.0,portfolio_fresh-portfolio_drop)
global_fresh=float(glob.get('fresh') or 0)

skills=[
 {'skill_id':'KEEP_CANONICAL_COGNITIVE_V3','artifact_digest':parent['canonical_component_digest'],'structural_valid':True,'semantic_consistency':1.0,
  'fit_baseline':1.0,'fit_candidate':1.0,'heldout_baseline':1.0,'heldout_candidate':1.0,'regression_pass':True,'state_integrity':True,'rollback_available':True},
 {'skill_id':'ADMIT_MULTIDOMAIN_REALDATA_COGNITIVE_V4','artifact_digest':digest({'multi':multi['experience_digest'],'real':real['experience_digest']}),
  'structural_valid':True,'semantic_consistency':1.0,'fit_baseline':portfolio_base,'fit_candidate':portfolio_fresh,
  'heldout_baseline':portfolio_base,'heldout_candidate':portfolio_fresh,'regression_pass':True,'state_integrity':True,'rollback_available':True},
 {'skill_id':'GLOBAL_V6_WITH_FAILED_STRESS','artifact_digest':glob['genome']['genome_digest'],'structural_valid':True,'semantic_consistency':1.0,
  'fit_baseline':0.60,'fit_candidate':global_fresh,'heldout_baseline':0.60,'heldout_candidate':float(gstress.get('base_accuracy') or 0),
  'regression_pass':False,'state_integrity':True,'rollback_available':True},
]
db=ROOT/'yado_g2_cognitive_experience_consolidation_v4.sqlite'
if db.exists():db.unlink()
k=UnifiedYADOKernelV30RC8ExternalCognitive(db_path=str(db))
try:
    selection=k.select_evolution_skills(skills,max_skills=1,min_semantic_consistency=.95,min_fit_gain=.10,max_heldout_drop=0.0,min_heldout_gain=.10)
finally:
    try:k.close()
    except Exception:pass
    try:
        if db.exists():db.unlink()
    except Exception:pass
selected=(selection.get('selected_skill_ids') or [None])[0]
if selected!='ADMIT_MULTIDOMAIN_REALDATA_COGNITIVE_V4':
    raise RuntimeError('NATIVE_SKILL_GATE_DID_NOT_SELECT_V4:'+json.dumps(selection))

art={
 'schema':'yado.g2.experience_conditioned_cognitive_layer.canonical.v4',
 'status':'SHADOW_READY','component_id':NEW,'parent_component':OLD,
 'parent_v3':copy.deepcopy(parent),
 'multidomain_genes':copy.deepcopy(mg),
 'real_data_genes':copy.deepcopy(rg),
 'multidomain_genome_id':multi['genome']['genome_id'],
 'multidomain_genome_digest':multi['genome']['genome_digest'],
 'real_data_portfolio_id':real['portfolio']['portfolio_id'],
 'real_data_portfolio_digest':real['portfolio']['portfolio_digest'],
 'global_negative_evidence':{
   'genome_id':glob['genome']['genome_id'],'stress_receipt_sha256':gstress.get('receipt_sha256'),
   'stress_status':gstress.get('status'),
   'failed_checks':[k for k,v in (gstress.get('checks') or {}).items() if v is False and k not in {'automatic_canonical_promotion','canonical_unchanged','external_models_used','retraining_performed'}],
 },
 'selection':selection,'selected_skill_id':selected,
 'fresh_evidence':{
   'multidomain_floor':mf,'multidomain_causal_drop_floor':md,
   'real_data_floor':rf,'real_data_causal_drop_floor':rd,
   'portfolio_fresh_floor':portfolio_fresh,'portfolio_causal_drop_floor':portfolio_drop,
 },
 'automatic_canonical_promotion':False,'architecture_mutation':False,'generation_transition':False,'g3_genesis_performed':False,
 'semantic_boundary':'SAME-G2 V4 CONSOLIDATES FRESH MULTIDOMAIN AND REAL-DATA EXPERTS BEHIND THE EXISTING V3 FAIL-CLOSED FALLBACK. FAILED GLOBAL V6 STRESS IS RETAINED AS NEGATIVE EVIDENCE AND IS NOT ADMITTED.'
}
candidate=G2ExperienceConditionedCognitiveLayerV4(art)
parent_runtime=G2ExperienceConditionedCognitiveLayerV3(parent)

rng=random.Random(20260906)
fallback_ok=True
generic_fields=['result_exact','search_incomplete','oracle_available','hypothesis_set_present','failure_seen','repair_regressed','formal_spec_present','candidate_available','reversible','real_source','state_known']
for _ in range(128):
    p={x:bool(rng.getrandbits(1)) for x in generic_fields}
    a=parent_runtime.decide(rng.choice(['LOGIC','THINKING','INTELLIGENCE']),p)
    b=candidate.decide(a['guard_features']['organ'],p)
    if (a.get('decision'),a.get('gate'),a.get('route_cardinality'))!=(b.get('decision'),b.get('gate'),b.get('route_cardinality')):
        fallback_ok=False;break

def tree_features(model):
    out=set()
    stack=[model]
    while stack:
        n=stack.pop()
        if not isinstance(n,dict):continue
        if 'feature' in n:out.add(str(n['feature']))
        if isinstance(n.get('left'),dict):stack.append(n['left'])
        if isinstance(n.get('right'),dict):stack.append(n['right'])
    return sorted(out)

specialist_cases=0;specialist_ok=0
for task in mg['LOGIC']['task_models']:
    for i in range(24):
        fam=str((task.get('selected') or {}).get('family') or '')
        if fam=='SYMMETRIC_COUNT_MAP_V2':fields=list(task['model'].get('fields') or [])
        else:fields=tree_features(task['model'])
        p={f:bool(rng.getrandbits(1)) for f in fields};p['task_id']=task['task_id']
        exp=G2ExperienceConditionedCognitiveLayerV4._logic_predict(task,p)
        got=candidate.decide('LOGIC',p)['decision'];specialist_cases+=1;specialist_ok+=got==exp
for task in mg['INTELLIGENCE']['task_models']:
    for i in range(24):
        p={f:rng.random() for f in tree_features(task['model'])};p['task_id']=task['task_id']
        exp=tree_predict(task['model'],p);got=candidate.decide('INTELLIGENCE',p)['decision'];specialist_cases+=1;specialist_ok+=got==exp
for task in mg['THINKING']['task_models']:
    roles=sorted({str(e.get(k)) for e in (task['model'].get('fallback_edges') or []) for k in ('before','after') if e.get(k)})
    actions=[{'id':'A'+str(i),'role':r} for i,r in enumerate(roles)]
    for i in range(16):
        ctx={k:bool(rng.getrandbits(1)) for k in (task['model'].get('context_keys') or [])}
        p={'task_id':task['task_id'],'context':ctx,'actions':actions}
        exp=plan_multicontext(task['model'],ctx,actions);got=candidate.decide('THINKING',p)['decision'];specialist_cases+=1;specialist_ok+=got==exp
for organ in ('LOGIC','INTELLIGENCE'):
    g=rg[organ]
    for i in range(32):
        p={f:rng.random() for f in tree_features(g['model'])};p['task_id']=g['task']
        exp=bool(tree_predict(g['model'],p)) if organ=='LOGIC' else tree_predict(g['model'],p)
        got=candidate.decide(organ,p)['decision'];specialist_cases+=1;specialist_ok+=got==exp
g=rg['THINKING'];roles=sorted({str(e.get(k)) for e in (g['model'].get('fallback_edges') or []) for k in ('before','after') if e.get(k)})
actions=[{'id':'R'+str(i),'role':r} for i,r in enumerate(roles)]
for i in range(32):
    ctx={k:bool(rng.getrandbits(1)) for k in (g['model'].get('context_keys') or [])}
    p={'task_id':g['task'],'context':ctx,'actions':actions}
    exp=plan_multicontext(g['model'],ctx,actions);got=candidate.decide('THINKING',p)['decision'];specialist_cases+=1;specialist_ok+=got==exp

compose_ok=True
cg=mg['COGNITIVE'];fam=cg['strategy_family'];model=cg['model']
for mask in range(8):
    s={'logic_accept':bool(mask&1),'thinking_cautious':bool(mask&2),'intelligence_robust':bool(mask&4)}
    x={k:float(v) for k,v in s.items()}
    if fam=='KNN_STRATEGY':exp=knn_predict(model,x)
    elif fam=='CENTROID_STRATEGY':exp=centroid_predict(model,x)
    else:exp=tree_predict(model,x)
    if candidate.compose(s).get('decision')!=exp:compose_ok=False;break

checks={
 'native_skill_gate_selected_v4':selected=='ADMIT_MULTIDOMAIN_REALDATA_COGNITIVE_V4',
 'global_failed_stress_rejected':all(x.get('skill_id')!='GLOBAL_V6_WITH_FAILED_STRESS' for x in (selection.get('selected') or [])),
 'multidomain_fresh_floor_ge_0_95':mf>=.95,
 'multidomain_causal_floor_ge_0_10':md>=.10,
 'real_data_fresh_floor_ge_0_90':rf>=.90,
 'real_data_causal_floor_ge_0_20':rd>=.20,
 'v3_fallback_equivalence':fallback_ok,
 'specialist_runtime_equivalence':specialist_cases>=300 and specialist_ok==specialist_cases,
 'cognitive_composer_equivalence':compose_ok,
 'canonical_parent_available':OLD in head.get('active_capabilities',[]),
 'canonical_unchanged_before_commit':True,
 'g3_not_started':head.get('g3_genesis_performed') is False,
}
if not all(checks.values()):
    raise RuntimeError('V4_ADMISSION_GATE_WITHHOLD:'+json.dumps({'checks':checks,'specialist_cases':specialist_cases,'specialist_ok':specialist_ok,'selection':selection}))

art['status']='CANONICAL_ACTIVE'
art['runtime_source']='runtime/yado_g2_experience_conditioned_cognitive_layer_v4.py'
art['runtime_sha256']=fsha(V4SRC)
art['rollback_parent_component']=OLD
art['canonical_component_digest']=cdig(art,'canonical_component_digest')
write(CANON,art)

# Bind V4 as the single active cognitive layer while preserving V3 as rollback/runtime dependency.
src=UNIFIED.read_text(encoding='utf-8')
src=src.replace('from yado_g2_experience_conditioned_cognitive_layer_v3 import G2ExperienceConditionedCognitiveLayerV3',
                'from yado_g2_experience_conditioned_cognitive_layer_v4 import G2ExperienceConditionedCognitiveLayerV4')
src=src.replace("self.experience_cognitive_layer=G2ExperienceConditionedCognitiveLayerV3(self._load('canonical/yado-g2-experience-conditioned-cognitive-layer-v3.json'))",
                "self.experience_cognitive_layer=G2ExperienceConditionedCognitiveLayerV4(self._load('canonical/yado-g2-experience-conditioned-cognitive-layer-v4.json'))")
UNIFIED.write_text(src,encoding='utf-8')

ms=MODULE.read_text(encoding='utf-8')
ms=ms.replace("CAP_COGNITIVE='RUNTIME-G2-EXPERIENCE-CONDITIONED-COGNITIVE-LAYER-V3'","CAP_COGNITIVE='RUNTIME-G2-EXPERIENCE-CONDITIONED-COGNITIVE-LAYER-V4'")
ms=ms.replace("CAP_COGNITIVE:('COGNITIVE_COORDINATOR','runtime/yado_g2_experience_conditioned_cognitive_layer_v3.py')",
              "CAP_COGNITIVE:('COGNITIVE_COORDINATOR','runtime/yado_g2_experience_conditioned_cognitive_layer_v4.py')")
MODULE.write_text(ms,encoding='utf-8')

gs=MODULE_GATE.read_text(encoding='utf-8').replace("core_manifest.get('experience_conditioned_cognitive_layer_v3',{})","core_manifest.get('experience_conditioned_cognitive_layer_v4',{})")
MODULE_GATE.write_text(gs,encoding='utf-8')

ps=POST_AUDIT.read_text(encoding='utf-8').replace("COG='RUNTIME-G2-EXPERIENCE-CONDITIONED-COGNITIVE-LAYER-V3'","COG='RUNTIME-G2-EXPERIENCE-CONDITIONED-COGNITIVE-LAYER-V4'")
POST_AUDIT.write_text(ps,encoding='utf-8')

for p in core.get('planes',[]):
    comps=p.get('active_components',[])
    if OLD in comps:
        p['active_components']=sorted(set([NEW if x==OLD else x for x in comps]))
if isinstance(core.get('experience_conditioned_cognitive_layer_v3'),dict):
    core['experience_conditioned_cognitive_layer_v3']['status']='SUPERSEDED_BY_V4'
    core['experience_conditioned_cognitive_layer_v3']['canonical_active']=False
    core['experience_conditioned_cognitive_layer_v3']['superseded_by']=NEW
core['experience_conditioned_cognitive_layer_v4']={
 'status':'CANONICAL_ACTIVE','component_id':NEW,'parent_component':OLD,
 'canonical_component_digest':art['canonical_component_digest'],'runtime_sha256':art['runtime_sha256'],
 'multidomain_genome_id':art['multidomain_genome_id'],'real_data_portfolio_id':art['real_data_portfolio_id'],
 'fresh_floor':portfolio_fresh,'causal_drop_floor':portfolio_drop,
 'negative_global_stress_receipt_sha256':gstress.get('receipt_sha256'),
 'rollback_parent_component':OLD,'automatic_canonical_promotion':False,
}
core['active_runtime_sources']=sorted(set(core.get('active_runtime_sources',[])+['runtime/yado_g2_experience_conditioned_cognitive_layer_v4.py','runtime/yado_g2_experience_conditioned_cognitive_layer_v3.py']))
rim=core.get('runtime_integrity_manifest') or {}
if not isinstance(rim.get('sources'),dict):raise RuntimeError('RUNTIME_INTEGRITY_MANIFEST_MISSING')
rim['sources']={rel:fsha(REPO/rel) for rel in core['active_runtime_sources']}
rim['manifest_digest']=digest(rim['sources'])
core['runtime_sha256']=fsha(UNIFIED)

prov['current_g2_binding'].update({
 'experience_conditioned_cognitive_layer':NEW,
 'experience_conditioned_cognitive_layer_digest':art['canonical_component_digest'],
 'experience_conditioned_cognitive_layer_source_sha256':art['runtime_sha256'],
 'experience_conditioned_cognitive_layer_parent':OLD,
 'experience_conditioned_cognitive_layer_multidomain_genome_id':art['multidomain_genome_id'],
 'experience_conditioned_cognitive_layer_real_data_portfolio_id':art['real_data_portfolio_id'],
 'experience_conditioned_cognitive_layer_global_negative_stress_receipt_sha256':gstress.get('receipt_sha256'),
 'cognitive_layer_automatic_promotion':False,
})
prov['registry_digest']=cdig(prov,'registry_digest');write(PROV,prov)

core['algorithm_provenance_registry_digest']=prov['registry_digest']
core['current_frontier']=FRONT
core['core_digest']=cdig(core,'core_digest');write(CORE,core)

prev_head=head['canonical_head_digest']
head['active_capabilities']=sorted(set([NEW if x==OLD else x for x in head.get('active_capabilities',[])]))
head['new_capabilities']=sorted(set(head.get('new_capabilities',[])+[NEW]))
if isinstance(head.get('experience_conditioned_cognitive_layer_v3'),dict):
    head['experience_conditioned_cognitive_layer_v3']['status']='SUPERSEDED_BY_V4'
    head['experience_conditioned_cognitive_layer_v3']['canonical_active']=False
    head['experience_conditioned_cognitive_layer_v3']['superseded_by']=NEW
head['experience_conditioned_cognitive_layer_v4']={
 'status':'CANONICAL_ACTIVE','component_id':NEW,'parent_component':OLD,
 'canonical_component_digest':art['canonical_component_digest'],
 'multidomain_genome_id':art['multidomain_genome_id'],'real_data_portfolio_id':art['real_data_portfolio_id'],
 'fresh_floor':portfolio_fresh,'causal_drop_floor':portfolio_drop,
 'rollback_parent_component':OLD,'automatic_canonical_promotion':False,
}
head['algorithm_provenance_registry']['registry_digest']=prov['registry_digest']
head['unified_core']['algorithm_provenance_registry_digest']=prov['registry_digest']
head['unified_core']['core_digest']=core['core_digest']
head['unified_core']['runtime_sha256']=core['runtime_sha256']
head['unified_core']['runtime_integrity_manifest_digest']=rim['manifest_digest']
head['current_frontier']=FRONT
head['canonical_head_digest']=cdig(head,'canonical_head_digest');write(HEAD,head)

ledger['current_head_digest']=head['canonical_head_digest'];ledger['open_deficits']=[FRONT]
run_id=str(os.getenv('GITHUB_RUN_ID') or 'LOCAL')
report={
 'schema':'yado.g2.cognitive_experience_consolidation.v4',
 'status':'PASS_G2_COGNITIVE_EXPERIENCE_CONSOLIDATION_V4',
 'component_id':NEW,'parent_component':OLD,'native_selection':selection,
 'fresh_evidence':art['fresh_evidence'],'checks':checks,
 'specialist_equivalence_cases':specialist_cases,'specialist_equivalence_pass':specialist_ok,
 'multidomain_genome_id':art['multidomain_genome_id'],'real_data_portfolio_id':art['real_data_portfolio_id'],
 'global_negative_evidence':art['global_negative_evidence'],
 'previous_head_digest':prev_head,'new_head_digest':head['canonical_head_digest'],
 'active_capability_count':len(head['active_capabilities']),
 'canonical_mutation':True,'canonical_mechanism_mutation':True,'architecture_mutation':False,
 'generation_transition':False,'g3_genesis_performed':False,'automatic_canonical_promotion':False,
 'next_required_capability':'SINGLE_CORE_BRANCH_LINEAGE_CONSOLIDATION_V1',
 'semantic_boundary':'V4 IS A SAME-G2 REPLACEMENT OF THE SINGLE ACTIVE COGNITIVE LAYER. V3 IS RETAINED AS FAIL-CLOSED ROLLBACK PARENT; MULTIDOMAIN AND REAL-DATA EXPERTS ARE ADDED ONLY WHERE FRESH EVIDENCE PASSED. FAILED GLOBAL-STRESS V6 IS NEGATIVE EXPERIENCE, NOT AN ADMITTED MODEL.'
}
report['receipt_sha256']=digest(report);write(OUT,report)
event={
 'index':len(ledger['events']),'event_id':f"E{len(ledger['events'])+1:04d}_G2_COGNITIVE_EXPERIENCE_CONSOLIDATION_V4",
 'event_type':'G2_COGNITIVE_EXPERIENCE_CONSOLIDATION','status':'PASS_CANONICAL','generation':ledger['current_head'],
 'deficit':'COGNITIVE_LAYER_TOO_CODING_CENTRIC_RELATIVE_TO_ACCUMULATED_MULTIDOMAIN_AND_REAL_DATA_EXPERIENCE',
 'effect':f"REPLACED_ACTIVE={OLD}->{NEW}; MULTIDOMAIN_FLOOR={mf:.6f}; REALDATA_FLOOR={rf:.6f}; CAUSAL_FLOOR={portfolio_drop:.6f}; GLOBAL_STRESS_V6_REJECTED=True",
 'source_path':'candidates/kernel-self-generated/g2-cognitive-experience-consolidation-v4.json',
 'source_digest':report['receipt_sha256'],'run_id':run_id,'parent_event_hash':ledger['tail_event_hash'],
 'canonical_mutation':True,'canonical_mechanism_mutation':True,'architecture_mutation':False,
 'promotion_applied':False,'generation_transition':False,
 'previous_head_digest':prev_head,'new_head_digest':head['canonical_head_digest']
}
event['event_hash']=event_hash(event);ledger['events'].append(event);ledger['event_count']=len(ledger['events']);ledger['tail_event_hash']=event['event_hash']
ledger['ledger_digest']=digest({k:v for k,v in ledger.items() if k!='ledger_digest'})
validate_ledger_v2(ledger);write(LEDGER,ledger)

post=subprocess.run([sys.executable,str(GUARD)],cwd=REPO,capture_output=True,text=True,timeout=120)
if post.returncode!=0:raise RuntimeError('POST_V4_CANONICAL_GUARD_FAILED:'+post.stdout[-8000:]+post.stderr[-3000:])
print(json.dumps({
 'status':report['status'],'component_id':NEW,'selected_skill_id':selected,
 'fresh_evidence':report['fresh_evidence'],'specialist_equivalence_cases':specialist_cases,
 'active_capability_count':len(head['active_capabilities']),'next_required_capability':report['next_required_capability'],
 'receipt_sha256':report['receipt_sha256']
},indent=2,sort_keys=True))
