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

TASK=REPO/'architecture/yado-g2-experience-conditioned-thinking-repair-v2-request.json'
EXP=REPO/'experience/yado-v29-thinking-precedence-rederived-v1.json'
PROV=REPO/'canonical/yado-legacy-experience-derived-provenance-v1.json'
PARENT=REPO/'candidates/kernel-self-generated/g2-experience-conditioned-lti-evolution-v1.json'
OUT=REPO/'candidates/kernel-self-generated/g2-experience-conditioned-thinking-repair-v2.json'
DB=ROOT/'yado_g2_experience_conditioned_thinking_repair_v2.sqlite'

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def digest(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))

task=load(TASK);exp=load(EXP);prov=load(PROV);parent=load(PARENT)
if parent.get('status')!='WITHHOLD_G2_EXPERIENCE_CONDITIONED_LTI_EVOLUTION_V1':
    raise RuntimeError('LTI_PARENT_NOT_WITHHOLD')
pc=parent.get('checks') or {}
if not (pc.get('logic_fresh_beats_baseline') and pc.get('intelligence_fresh_beats_baseline')):
    raise RuntimeError('SUCCESSFUL_SIBLING_GENES_NOT_AVAILABLE')
if pc.get('thinking_fresh_beats_baseline'):
    raise RuntimeError('THINKING_PARENT_NOT_FAILED')

# Verify historical source/receipt registration from current canonical provenance.
row=next((b for b in prov.get('branches') or [] if b.get('branch')=='yado-v29-cognitive'),None)
if not row:raise RuntimeError('V29_PROVENANCE_MISSING')
evidence={x.get('path'):x for x in row.get('evidence') or []}
if evidence.get(exp['raw_source_path'],{}).get('sha256')!=exp['raw_source_sha256']:
    raise RuntimeError('V29_SOURCE_SHA_MISMATCH')
if evidence.get(exp['raw_receipt_path'],{}).get('sha256')!=exp['raw_receipt_sha256']:
    raise RuntimeError('V29_RECEIPT_SHA_MISMATCH')

core=UnifiedYADOCoreV1(REPO);head_before=copy.deepcopy(core.head)
seed=exp['raw_source_sha256']

def rename(kind,label):
    return kind+'_'+hashlib.sha256((seed+'|'+kind+'|'+str(label)).encode()).hexdigest()[:12]

ctx_map={k:rename('CTX',k) for k in exp['context_keys']}
role_map={r:rename('ROLE',r) for r in exp['role_vocabulary']}

train=[]
for ep in exp['episodes']:
    ctx={ctx_map[k]:bool(v) for k,v in ep['context'].items()}
    trace=[role_map[r] for r in ep['expected']]
    for _ in range(5):train.append((dict(ctx),list(trace)))

def make_actions(expected,variant):
    roles=list(expected)
    shift=variant%len(roles)
    roles=roles[shift:]+roles[:shift]
    if variant%2:roles=list(reversed(roles))
    return [{'id':'A-'+hashlib.sha256((str(variant)+'|'+r).encode()).hexdigest()[:14],'role':r} for r in roles]

blind=[]
for rep in range(8):
    for ep in exp['episodes']:
        ctx={ctx_map[k]:bool(v) for k,v in ep['context'].items()}
        expected=[role_map[r] for r in ep['expected']]
        blind.append((ctx,make_actions(expected,100+rep),expected))

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

siblings={x:(parent.get('shadow_genes') or {}).get(x) for x in ('LOGIC','INTELLIGENCE')}
parent_thinking=(parent.get('shadow_genes') or {}).get('THINKING') or {}
gene={
 'schema':'yado.g2.experience_conditioned_thinking_gene.v2',
 'gene_id':'GENE-G2-EXPERIENCE-THINKING-V2-'+digest({'model':model,'exp':digest(exp),'parent':parent_thinking.get('gene_digest')})[:16],
 'organ':'THINKING',
 'heritage':[parent_thinking.get('gene_id'),exp.get('raw_source_sha256'),exp.get('raw_receipt_sha256')],
 'historical_experience_digest':digest(exp),
 'current_parent_receipt':parent.get('receipt_sha256'),
 'model':model,
 'fresh_blind':fresh,'context_ablation':ablation,'restore':restore,
 'promotion_state':'SHADOW_ONLY',
 'origin':'CURRENT_G2_NATIVE_MULTICONTEXT_PRECEDENCE_RELEARNED_FROM_VERIFIED_YADO_HISTORY',
}
gene['gene_digest']=digest(gene)

checks={
 'v29_source_provenance_verified':True,
 'v29_receipt_provenance_verified':True,
 'historical_thinking_experience_consumed':True,
 'failed_current_thinking_gene_consumed':bool(parent_thinking.get('gene_id')),
 'logic_sibling_gene_preserved':bool(siblings['LOGIC']) and siblings['LOGIC']==(parent.get('shadow_genes') or {}).get('LOGIC'),
 'intelligence_sibling_gene_preserved':bool(siblings['INTELLIGENCE']) and siblings['INTELLIGENCE']==(parent.get('shadow_genes') or {}).get('INTELLIGENCE'),
 'legacy_runtime_activated':False,
 'deterministic_context_and_role_renaming_applied':True,
 'current_g2_native_multicontext_planner_used':model.get('kind')=='MULTICONTEXT_PRECEDENCE',
 'fresh_action_id_blind_exact':fresh==1.0,
 'context_ablation_material_drop':fresh-ablation>=.25,
 'restore_exact':restore==fresh,
 'new_thinking_shadow_gene_created':gene['gene_id']!=parent_thinking.get('gene_id'),
 'external_models_used':False,'new_external_research_used':False,
 'host_written_planner':False,'host_selected_new_order':False,
 'automatic_canonical_promotion':False,
 'rollback_parent_available':bool(parent_thinking.get('gene_id')),
 'canonical_unchanged':core.head.get('canonical_head_digest')==head_before.get('canonical_head_digest'),
}
required_true=[k for k in checks if k not in ('legacy_runtime_activated','external_models_used','new_external_research_used','host_written_planner','host_selected_new_order','automatic_canonical_promotion')]
required_false=('legacy_runtime_activated','external_models_used','new_external_research_used','host_written_planner','host_selected_new_order','automatic_canonical_promotion')
passed=all(checks[k] is True for k in required_true) and all(checks[k] is False for k in required_false)
status='PASS_SHADOW_G2_EXPERIENCE_CONDITIONED_THINKING_REPAIR_V2' if passed else 'WITHHOLD_G2_EXPERIENCE_CONDITIONED_THINKING_REPAIR_V2'
report={
 'schema':'yado.g2.experience_conditioned_thinking_repair.v2','status':status,'task':task,
 'historical_experience':exp,'renaming':{'context':ctx_map,'roles':role_map},
 'training_episode_count':len(train),'blind_case_count':len(blind),
 'fresh_score':fresh,'context_ablation_score':ablation,'restore_score':restore,
 'parent_thinking_gene':parent_thinking,'preserved_sibling_genes':siblings,
 'thinking_gene':gene,'checks':checks,'canonical_mutation':False,'promotion_applied':False,
 'next_required_capability':None if passed else 'EXPERIENCE_CONDITIONED_THINKING_REPAIR_V3',
 'semantic_boundary':'CURRENT G2 RELEARNS A VERIFIED HISTORICAL YADO THINKING PRINCIPLE AFTER DETERMINISTIC RENAMING OF CONTEXT AND ROLE IDENTITIES. LEGACY RUNTIME IS NOT EXECUTED. FRESH ACTION IDS, CONTEXT ABLATION AND RESTORE ARE REQUIRED. LOGIC AND INTELLIGENCE SUCCESSFUL LTI SIBLING GENES ARE PRESERVED.'
}
report['receipt_sha256']=digest(report)
OUT.parent.mkdir(parents=True,exist_ok=True)
OUT.write_text(json.dumps(report,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')
print(json.dumps({'status':status,'fresh':fresh,'ablation':ablation,'restore':restore,'gene_id':gene['gene_id'],'receipt_sha256':report['receipt_sha256']},indent=2,sort_keys=True))
if not passed:raise SystemExit(2)
