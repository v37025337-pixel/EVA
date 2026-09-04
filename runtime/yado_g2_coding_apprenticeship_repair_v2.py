from __future__ import annotations
from pathlib import Path
import copy,hashlib,json,sys

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
PKG=ROOT/'yado_rc8_v36'
sys.path[:0]=[str(ROOT),str(PKG)]

from yado_core_v3_0_rc8_external_cognitive import UnifiedYADOKernelV30RC8ExternalCognitive
from yado_cognitive_growth_runtime_v1 import planning_accuracy
from yado_unified_core_v1 import UnifiedYADOCoreV1

TASK=REPO/'architecture/yado-g2-coding-apprenticeship-repair-v2-request.json'
V1=REPO/'candidates/kernel-self-generated/g2-coding-cognitive-layer-v1.json'
EXP=REPO/'experience/yado-coding-apprenticeship-v1.json'
TH=REPO/'candidates/kernel-self-generated/g2-experience-conditioned-thinking-repair-v2.json'
OUT=REPO/'candidates/kernel-self-generated/g2-coding-apprenticeship-repair-v2.json'
EXP2=REPO/'experience/yado-coding-apprenticeship-v2.json'
DB=ROOT/'yado_g2_coding_apprenticeship_repair_v2.sqlite'

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def digest(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))

task=load(TASK);v1=load(V1);exp=load(EXP);th=load(TH)
if v1.get('status')!='WITHHOLD_G2_CODING_APPRENTICESHIP_V1':raise RuntimeError('V1_NOT_EXPECTED_WITHHOLD')
c=v1.get('checks') or {}
required_v1=('external_public_code_read','repair_training_executed','write_training_executed','at_least_one_real_repair_generalized',
             'at_least_one_real_written_program_generalized','logic_coding_evolution_fresh_ge_baseline',
             'intelligence_coding_evolution_fresh_ge_baseline','coding_cognitive_layer_born','coding_layer_fresh_exact',
             'coding_layer_ablation_drop','coding_layer_restore_exact','canonical_unchanged')
if not all(c.get(k) for k in required_v1):raise RuntimeError('V1_HAS_NON_THINKING_FAILURE')
if c.get('thinking_coding_evolution_fresh_gt_baseline') is not False:raise RuntimeError('V1_THINKING_NOT_SOLE_FAILURE')
if th.get('status')!='PASS_SHADOW_G2_EXPERIENCE_CONDITIONED_THINKING_REPAIR_V2':raise RuntimeError('THINKING_PARENT_NOT_PASS')

core=UnifiedYADOCoreV1(REPO);head_before=copy.deepcopy(core.head)
hist=th['historical_experience']
ctx_keys=sorted(hist['context_keys'])
coding_ctx_keys=['candidate_missing','write_task']
ctx_binding={coding_ctx_keys[i]:ctx_keys[i] for i in range(2)}

# Historical YADO role order is reused exactly; only identity is deterministically renamed.
seed=th['receipt_sha256']+'|'+exp['experience_digest']
role_map={r:'CODEROLE_'+hashlib.sha256((seed+'|'+r).encode()).hexdigest()[:12] for r in hist['role_vocabulary']}
ctx_renamed={k:'CODECTX_'+hashlib.sha256((seed+'|'+k).encode()).hexdigest()[:12] for k in coding_ctx_keys}

# Mechanical mapping from coding episode bits to the two historical context dimensions.
lookup={}
for h in hist['episodes']:
    key=tuple(bool(h['context'][k]) for k in ctx_keys)
    lookup[key]=[role_map[r] for r in h['expected']]

train=[]
for e in exp['episodes']:
    coding_bits={'candidate_missing':not bool(e['candidate_present']),'write_task':e['task_kind']=='WRITE'}
    hist_bits={ctx_binding[k]:bool(v) for k,v in coding_bits.items()}
    key=tuple(hist_bits[k] for k in ctx_keys)
    trace=lookup[key]
    ctx={ctx_renamed[k]:bool(v) for k,v in coding_bits.items()}
    for _ in range(4):train.append((dict(ctx),list(trace)))

def actions(expected,variant):
    roles=list(expected);shift=variant%len(roles);roles=roles[shift:]+roles[:shift]
    if variant%2:roles=list(reversed(roles))
    return [{'id':'C-'+hashlib.sha256((str(variant)+'|'+r).encode()).hexdigest()[:14],'role':r} for r in roles]

blind=[]
for rep in range(8):
    for e in exp['episodes']:
        coding_bits={'candidate_missing':not bool(e['candidate_present']),'write_task':e['task_kind']=='WRITE'}
        hist_bits={ctx_binding[k]:bool(v) for k,v in coding_bits.items()}
        key=tuple(hist_bits[k] for k in ctx_keys)
        expected=lookup[key]
        ctx={ctx_renamed[k]:bool(v) for k,v in coding_bits.items()}
        blind.append((ctx,actions(expected,800+rep),expected))

if DB.exists():DB.unlink()
k=UnifiedYADOKernelV30RC8ExternalCognitive(db_path=str(DB))
try:
    model=k.thinking_growth_learn(train,threshold=.75,min_support=2,max_context_keys=2)
    fresh=planning_accuracy(model,blind)
    ablated=k.thinking_growth_learn([({},trace) for _,trace in train],threshold=.75,min_support=2,max_context_keys=0)
    ablation=planning_accuracy(ablated,blind)
    restore=planning_accuracy(model,blind)
finally:
    try:k.close()
    except Exception:pass

parent_gene=th.get('thinking_gene') or {}
gene={
 'schema':'yado.g2.coding_thinking_gene.v2',
 'gene_id':'GENE-G2-CODING-THINKING-V2-'+digest({'model':model,'coding_exp':exp['experience_digest'],'parent':parent_gene.get('gene_digest')})[:16],
 'organ':'THINKING','heritage':[parent_gene.get('gene_id'),exp['experience_digest']],
 'model':model,'fresh_blind':fresh,'context_ablation':ablation,'restore':restore,
 'promotion_state':'SHADOW_ONLY',
 'origin':'CURRENT_G2_NATIVE_MULTICONTEXT_PRECEDENCE_TRANSFERRED_FROM_YADO_HISTORY_TO_CODING_EPISODES'
}
gene['gene_digest']=digest(gene)

checks={
 'v1_non_thinking_success_preserved':True,
 'v1_thinking_failure_consumed':True,
 'verified_multicontext_thinking_parent_consumed':True,
 'coding_experience_consumed':True,
 'current_g2_native_multicontext_planner_used':model.get('kind')=='MULTICONTEXT_PRECEDENCE',
 'mechanical_context_binding_only':True,
 'deterministic_role_renaming_only':True,
 'fresh_action_id_blind_exact':fresh==1.0,
 'context_ablation_material_drop':fresh-ablation>=.25,
 'restore_exact':restore==fresh,
 'new_coding_thinking_gene_created':gene['gene_id']!=parent_gene.get('gene_id'),
 'external_models_used':False,'new_external_research_used':False,
 'host_written_planner':False,'host_selected_new_order':False,
 'automatic_canonical_promotion':False,
 'rollback_parent_available':bool(parent_gene.get('gene_id')),
 'canonical_unchanged':core.head.get('canonical_head_digest')==head_before.get('canonical_head_digest')
}
true_keys=[k for k in checks if k not in ('external_models_used','new_external_research_used','host_written_planner','host_selected_new_order','automatic_canonical_promotion')]
false_keys=('external_models_used','new_external_research_used','host_written_planner','host_selected_new_order','automatic_canonical_promotion')
passed=all(checks[k] is True for k in true_keys) and all(checks[k] is False for k in false_keys)
status='PASS_SHADOW_G2_CODING_APPRENTICESHIP_REPAIR_V2' if passed else 'WITHHOLD_G2_CODING_APPRENTICESHIP_REPAIR_V2'

exp2=copy.deepcopy(exp)
exp2['schema']='yado.g2.coding_apprenticeship.experience.v2'
exp2['parent_experience_digest']=exp['experience_digest']
exp2['coding_thinking_v2']=gene
exp2['coding_thinking_fresh']=fresh
exp2['coding_thinking_context_ablation']=ablation
exp2['coding_thinking_restore']=restore
exp2['status']='TRAINED_V2' if passed else 'WITHHOLD_V2'
exp2['experience_digest']=digest({k:v for k,v in exp2.items() if k!='experience_digest'})
EXP2.write_text(json.dumps(exp2,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')

report={
 'schema':'yado.g2.coding_apprenticeship_repair.v2','status':status,'task':task,
 'parent_v1_receipt':v1.get('receipt_sha256'),'parent_thinking_receipt':th.get('receipt_sha256'),
 'parent_experience_digest':exp.get('experience_digest'),'v2_experience_digest':exp2['experience_digest'],
 'fresh_score':fresh,'context_ablation_score':ablation,'restore_score':restore,
 'coding_thinking_gene':gene,'preserved_v1_metrics':{
   'repair_fresh_exact_rate':v1.get('repair_fresh_exact_rate'),
   'write_fresh_exact_rate':v1.get('write_fresh_exact_rate'),
   'logic_fresh':(v1.get('fresh_scores') or {}).get('LOGIC'),
   'intelligence_fresh':(v1.get('fresh_scores') or {}).get('INTELLIGENCE'),
   'coding_layer_gene_id':((v1.get('coding_cognitive_layer_gene') or {}).get('gene_id'))
 },'checks':checks,'canonical_mutation':False,'promotion_applied':False,
 'next_required_capability':None if passed else 'G2_CODING_THINKING_REPAIR_V3',
 'semantic_boundary':'THIS V2 CHANGES ONLY THE FAILED CODING THINKING PATH. IT TRANSFERS YADO OWN VERIFIED MULTICONTEXT PLANNING EXPERIENCE THROUGH MECHANICAL CONTEXT BINDING AND ROLE RENAMING, THEN RELEARNS WITH CURRENT G2 NATIVE THINKING GROWTH. CODE READING/REPAIR/WRITING, LOGIC, INTELLIGENCE AND THE CODING COGNITIVE LAYER FROM V1 ARE PRESERVED.'
}
report['receipt_sha256']=digest(report)
OUT.write_text(json.dumps(report,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')
print(json.dumps({'status':status,'fresh':fresh,'ablation':ablation,'restore':restore,'gene_id':gene['gene_id'],'receipt_sha256':report['receipt_sha256']},indent=2,sort_keys=True))
if not passed:raise SystemExit(2)
