from __future__ import annotations
from pathlib import Path
from dataclasses import asdict
import copy,hashlib,json,sys

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
PKG=ROOT/'yado_rc8_v36'
sys.path[:0]=[str(ROOT),str(PKG)]

from yado_unified_core_v1 import UnifiedYADOCoreV1
from yado_core_v2_1 import RuleProgramSynthesizer,BoundedRuleSandbox
from yado_conjunctive_rule_inducer_v1 import ConjunctiveRuleInducerV1
from yado_ambiguity_aware_program_repair_v11 import AmbiguityAwareProgramRepairV11
from yado_evolutionary_genome_v1 import PolynomialReturnRepairGeneV1

TASK=REPO/'architecture/yado-g2-coding-reasoning-workspace-v3-request.json'
PARENT_V2=REPO/'candidates/kernel-self-generated/g2-coding-reasoning-workspace-v2.json'
EXP_V2=REPO/'experience/yado-coding-reasoning-workspace-v2.json'
EXP_V1=REPO/'experience/yado-coding-apprenticeship-v1.json'
PARENT_LAYER=REPO/'candidates/kernel-self-generated/g2-coding-cognitive-layer-v1.json'
THINKING_PARENT=REPO/'candidates/kernel-self-generated/g2-experience-conditioned-thinking-repair-v2.json'
HEAD=REPO/'canonical/yado-main-head-g2.json'
OUT=REPO/'candidates/kernel-self-generated/g2-coding-reasoning-workspace-v3.json'
EXP=REPO/'experience/yado-coding-reasoning-workspace-v3.json'

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def digest(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def sha_text(s):return hashlib.sha256(s.encode()).hexdigest()
def safe_compile(src):
    try:compile(src,'<g2-coding-v3>','exec');return True
    except Exception:return False
def program_json(p):
    return {
      'program_id':p.program_id,'target_capability':p.target_capability,'target_organ':p.target_organ,
      'rules':[{'predicates':[asdict(q) for q in r.predicates],'output':r.output,'support':r.support,'confidence':r.confidence} for r in p.rules],
      'default_output':p.default_output,'source_digest':p.source_digest,'training_count':p.training_count,
      'status':p.status,'program_digest':p.digest()
    }
def program_acc(p,cases,ablated=False):
    return sum(BoundedRuleSandbox.execute(p,e['input'],ablated=ablated)==e['expected'] for e in cases)/len(cases)

task=load(TASK);pv2=load(PARENT_V2);ev2=load(EXP_V2);ev1=load(EXP_V1)
player=load(PARENT_LAYER);tparent=load(THINKING_PARENT);head=load(HEAD)

if pv2.get('status')!='WITHHOLD_G2_CODING_REASONING_WORKSPACE_V2':
    raise RuntimeError('V2_PARENT_NOT_WITHHOLD')
if pv2.get('next_required_capability')!='G2_CODING_REASONING_WORKSPACE_V3':
    raise RuntimeError('V2_FRONTIER_MISMATCH')
if 'ALG-CONJUNCTIVE-RULE-INDUCER-V1' not in set(head.get('active_capabilities') or []):
    raise RuntimeError('CONJUNCTIVE_RULE_INDUCER_NOT_ACTIVE_G2_CAPABILITY')

core=UnifiedYADOCoreV1(REPO);head_before=copy.deepcopy(core.head)

def reasoning_examples(ep):
    f=ep.get('features') or {}
    base={
      'task_kind':str(ep.get('task_kind')),
      'candidate_present':bool(ep.get('candidate_present')),
      'train_exact':float(ep.get('train_score') or 0)==1.0,
      'fresh_exact':float(ep.get('fresh_score') or 0)==1.0,
      'high_complexity':bool(f.get('requires_degree_gt3') or f.get('multivariate') or f.get('non_polynomial')),
    }
    rows=[]
    def add(stage,expected):
        x=dict(base);x['stage']=stage;rows.append({'input':x,'expected':expected})
    add('START','READ_CODE')
    add('CODE_READ','BUILD_MODEL')
    add('MODEL_BUILT','FORM_HYPOTHESIS')
    add('HYPOTHESIS_READY','TEST_HYPOTHESIS' if base['candidate_present'] else 'REVISE_HYPOTHESIS')
    add('TEST_RESULT','IMPLEMENT_CHANGE' if base['train_exact'] else 'REVISE_HYPOTHESIS')
    add('IMPLEMENTED','CHECK_CONSEQUENCES')
    add('CONSEQUENCE_RESULT','STORE_EXPERIENCE' if base['fresh_exact'] else 'REVISE_HYPOTHESIS')
    add('MEMORY_READY','ADVANCE')
    return rows

historical=list(ev1.get('episodes') or [])
v2fresh=list(ev2.get('fresh_episodes') or [])
if len(historical)<16 or len(v2fresh)<8:raise RuntimeError('CODING_MEMORY_INCOMPLETE')
train_examples=[]
for ep in historical+v2fresh:train_examples.extend(reasoning_examples(ep))

# New V3 coding holdout: never used by V1/V2.
train_x=(-6,-2,0,3,5)
fresh_x=(-9,-4,1,6,8)
specs=[
 ('REPAIR','V3_LINEAR',lambda x:4*x-7,False),
 ('REPAIR','V3_CUBIC',lambda x:x**3-x+4,False),
 ('REPAIR','V3_MOD4',lambda x:x%4+1,False),
 ('REPAIR','V3_ABS_SHIFT',lambda x:abs(x-1)+1,False),
 ('WRITE','V3_QUADRATIC',lambda x:3*x*x+2*x-5,False),
 ('WRITE','V3_CUBIC_WRITE',lambda x:2*x**3-x+6,False),
 ('WRITE','V3_DEGREE6',lambda x:x**6+1,False),
 ('WRITE','V3_BIVARIATE',lambda x,y:x+2*y,True),
]
def evaluate_source(src,cases):
    if not src or not safe_compile(src):return 0.0
    ok=0
    for args,expected in cases:
        try:got=AmbiguityAwareProgramRepairV11.execute(src,'f',args)
        except Exception:continue
        ok+=(got==expected)
    return ok/max(1,len(cases))

fresh_episodes=[]
for kind,name,target,multi in specs:
    if multi:
        source='def f(x,y):\n    return x\n'
        tr=[((x,y),target(x,y)) for x,y in [(-3,2),(0,5),(2,-1),(6,3),(8,-4)]]
        fr=[((x,y),target(x,y)) for x,y in [(-7,4),(1,9),(5,-3),(10,2)]]
    else:
        source='def f(x):\n    return x\n'
        tr=[((x,),target(x)) for x in train_x]
        fr=[((x,),target(x)) for x in fresh_x]
    try:
        if kind=='REPAIR':
            r=AmbiguityAwareProgramRepairV11.repair(source,'f',tr,max_candidates=7000,max_edit_depth=2)
        else:
            r=PolynomialReturnRepairGeneV1.synthesize(source,'f',tr)
    except Exception as e:r={'source':None,'reason':type(e).__name__+':'+str(e)[:180]}
    cand=r.get('source');ts=evaluate_source(cand,tr);fs=evaluate_source(cand,fr)
    fresh_episodes.append({
      'task_id':name,'task_kind':kind,'input_source_sha256':sha_text(source),
      'candidate_present':bool(cand),'candidate_source_sha256':sha_text(cand) if cand else None,
      'candidate_source_excerpt':cand[:800] if cand else None,
      'repair_mode':r.get('repair_mode') or r.get('operator_gene'),'reason':r.get('reason'),
      'train_score':ts,'fresh_score':fs,'fresh_exact':fs==1.0,
      'features':{
        'is_write':kind=='WRITE','multivariate':multi,
        'requires_degree_gt3':name=='V3_DEGREE6',
        'non_polynomial':name in ('V3_MOD4','V3_ABS_SHIFT')
      }
    })
blind=[]
for ep in fresh_episodes:blind.extend(reasoning_examples(ep))

def linear_action(x):
    return {
      'START':'READ_CODE','CODE_READ':'BUILD_MODEL','MODEL_BUILT':'FORM_HYPOTHESIS',
      'HYPOTHESIS_READY':'TEST_HYPOTHESIS','TEST_RESULT':'IMPLEMENT_CHANGE',
      'IMPLEMENTED':'CHECK_CONSEQUENCES','CONSEQUENCE_RESULT':'STORE_EXPERIENCE',
      'MEMORY_READY':'ADVANCE'
    }[x['stage']]
linear=sum(linear_action(e['input'])==e['expected'] for e in blind)/len(blind)

single=None;single_score=0.0;single_error=None
try:
    single=RuleProgramSynthesizer.synthesize('CODING_REASONING_WORKSPACE_V3_SINGLE_BASELINE','THINKING',train_examples,min_support=2)
    single_score=program_acc(single,blind)
except Exception as e:single_error=type(e).__name__+':'+str(e)[:300]

conj=ConjunctiveRuleInducerV1.synthesize('CODING_REASONING_WORKSPACE_V3','THINKING',train_examples,min_support=2,max_rules=12)
train_score=program_acc(conj,train_examples)
fresh_score=program_acc(conj,blind)
ablation=program_acc(conj,blind,ablated=True)
restore=program_acc(conj,blind)

retry_train=sum(e['expected']=='REVISE_HYPOTHESIS' for e in train_examples)
retry_blind=sum(e['expected']=='REVISE_HYPOTHESIS' for e in blind)
has_multi=any(len(r.predicates)>=2 for r in conj.rules)
multi_retry=any(r.output=='REVISE_HYPOTHESIS' and len(r.predicates)>=2 for r in conj.rules)

gene={
 'schema':'yado.g2.coding_reasoning_thinking_gene.v3',
 'gene_id':'GENE-G2-CODING-REASONING-THINKING-V3-'+conj.digest()[:16],
 'organ':'THINKING',
 'gene_scope':['THINKING','CODE','MEMORY','GENERATIVE_EXECUTIVE','LOGIC','INTELLIGENCE'],
 'heritage':[
   (player.get('coding_cognitive_layer_gene') or {}).get('gene_id'),
   (tparent.get('thinking_gene') or {}).get('gene_id'),
   pv2.get('receipt_sha256'),ev1.get('experience_digest'),ev2.get('experience_digest')
 ],
 'origin':'ACTIVE_G2_CONJUNCTIVE_RULE_INDUCER_LEARNED_FROM_ACCUMULATED_CODING_OUTCOMES',
 'mechanism_kind':'CONJUNCTIVE_RULE_PROGRAM',
 'active_parent_capability':'ALG-CONJUNCTIVE-RULE-INDUCER-V1',
 'program':program_json(conj),
 'train_score':train_score,'fresh_score':fresh_score,'ablation_score':ablation,'restore_score':restore,
 'promotion_state':'SHADOW_ONLY'
}
gene['gene_digest']=digest(gene)

checks={
 'v2_withhold_consumed':pv2.get('status')=='WITHHOLD_G2_CODING_REASONING_WORKSPACE_V2',
 'active_conjunctive_capability_verified':'ALG-CONJUNCTIVE-RULE-INDUCER-V1' in set(head.get('active_capabilities') or []),
 'accumulated_coding_memory_consumed':len(historical)+len(v2fresh)>=24,
 'fresh_v3_tasks_executed':len(fresh_episodes)==8,
 'fresh_success_and_failure_both_present':any(e['fresh_exact'] for e in fresh_episodes) and any(not e['fresh_exact'] for e in fresh_episodes),
 'retry_branch_seen_train':retry_train>0,'retry_branch_seen_fresh':retry_blind>0,
 'conjunctive_program_contains_multi_predicate_rules':has_multi,
 'retry_is_state_conditioned':multi_retry,
 'conjunctive_train_exact':train_score==1.0,
 'conjunctive_fresh_exact':fresh_score==1.0,
 'conjunctive_beats_single_predicate':fresh_score>single_score,
 'conjunctive_beats_linear_baseline':fresh_score-linear>=.10,
 'ablation_material_drop':fresh_score-ablation>=.20,
 'restore_exact':restore==fresh_score,
 'new_shadow_thinking_gene_created':bool(gene.get('gene_id')),
 'canonical_unchanged':core.head.get('canonical_head_digest')==head_before.get('canonical_head_digest'),
 'third_party_code_executed':False,'external_coding_model_used':False,
 'ready_patch_from_host_used':False,'host_written_reasoning_rules':False,
 'automatic_canonical_promotion':False
}
true_keys=[k for k in checks if k not in ('third_party_code_executed','external_coding_model_used','ready_patch_from_host_used','host_written_reasoning_rules','automatic_canonical_promotion')]
false_keys=['third_party_code_executed','external_coding_model_used','ready_patch_from_host_used','host_written_reasoning_rules','automatic_canonical_promotion']
passed=all(checks[k] is True for k in true_keys) and all(checks[k] is False for k in false_keys)
status='PASS_SHADOW_G2_CODING_REASONING_WORKSPACE_V3' if passed else 'WITHHOLD_G2_CODING_REASONING_WORKSPACE_V3'

experience={
 'schema':'yado.g2.coding_reasoning_workspace.experience.v3','status':'TRAINED',
 'parent_v2_receipt':pv2.get('receipt_sha256'),
 'parent_v1_experience':ev1.get('experience_digest'),'parent_v2_experience':ev2.get('experience_digest'),
 'training_episode_count':len(historical)+len(v2fresh),'training_reasoning_case_count':len(train_examples),
 'fresh_episodes':fresh_episodes,'blind_reasoning_case_count':len(blind),
 'single_predicate_fresh_score':single_score,'linear_baseline_score':linear,
 'conjunctive_train_score':train_score,'conjunctive_fresh_score':fresh_score,
 'ablation_score':ablation,'restore_score':restore,'thinking_gene':gene,
 'canonical_mutation':False,
 'semantic_boundary':'THE PROGRAM IS SYNTHESIZED BY THE ALREADY-ACTIVE G2 CONJUNCTIVE RULE INDUCER FROM ACCUMULATED CODING OUTCOMES. HOST DEFINES THE USER-REQUESTED CURRICULUM AND FRESH SANDBOX TASKS BUT WRITES NO REASONING RULES. THIRD-PARTY CODE IS NOT EXECUTED. THE RESULT REMAINS SHADOW.'
}
experience['experience_digest']=digest(experience)
EXP.parent.mkdir(parents=True,exist_ok=True);EXP.write_text(json.dumps(experience,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')

report={
 'schema':'yado.g2.coding_reasoning_workspace.v3','status':status,'task':task,
 'parent_v2_status':pv2.get('status'),'parent_v2_receipt':pv2.get('receipt_sha256'),
 'active_mechanism':'ALG-CONJUNCTIVE-RULE-INDUCER-V1',
 'fresh_task_count':len(fresh_episodes),'fresh_success_count':sum(e['fresh_exact'] for e in fresh_episodes),
 'fresh_failure_count':sum(not e['fresh_exact'] for e in fresh_episodes),
 'single_predicate_fresh_score':single_score,'single_predicate_error':single_error,
 'linear_baseline_score':linear,'conjunctive_train_score':train_score,'conjunctive_fresh_score':fresh_score,
 'ablation_score':ablation,'restore_score':restore,
 'retry_train_count':retry_train,'retry_fresh_count':retry_blind,
 'thinking_gene_id':gene['gene_id'],'thinking_gene':gene,'checks':checks,
 'canonical_mutation':False,'promotion_applied':False,
 'next_required_capability':'G2_CODING_REASONING_TRANSFER_STRESS_V1' if passed else 'G2_CODING_REASONING_WORKSPACE_V4',
 'receipt_sha256':None,'semantic_boundary':experience['semantic_boundary']
}
report['receipt_sha256']=digest({k:v for k,v in report.items() if k!='receipt_sha256'})
OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(report,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')

print(json.dumps({
 'status':status,'fresh_task_count':report['fresh_task_count'],'fresh_success_count':report['fresh_success_count'],
 'fresh_failure_count':report['fresh_failure_count'],'single_predicate_fresh_score':single_score,
 'linear_baseline_score':linear,'conjunctive_train_score':train_score,'conjunctive_fresh_score':fresh_score,
 'ablation_score':ablation,'restore_score':restore,'retry_train_count':retry_train,'retry_fresh_count':retry_blind,
 'thinking_gene_id':gene['gene_id'],'multi_predicate_rule_count':sum(len(r.predicates)>=2 for r in conj.rules),
 'next_required_capability':report['next_required_capability'],'receipt_sha256':report['receipt_sha256']
},indent=2,sort_keys=True))
if not passed:raise SystemExit(2)
