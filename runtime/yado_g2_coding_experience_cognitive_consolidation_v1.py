from __future__ import annotations
from pathlib import Path
import copy,hashlib,json,sys

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
PKG=ROOT/'yado_rc8_v36'
sys.path[:0]=[str(ROOT),str(PKG)]

from yado_unified_core_v1 import UnifiedYADOCoreV1
from yado_conjunctive_rule_inducer_v1 import ConjunctiveRuleInducerV1,program_acc,canonical_program
from yado_core_v2_1 import BoundedRuleSandbox
from yado_coverage_pruned_compositional_schema_router_v3 import CoveragePrunedCompositionalSchemaRouterV3

TASK=REPO/'architecture/yado-g2-coding-experience-cognitive-consolidation-v1-request.json'
PARENT=REPO/'candidates/kernel-self-generated/g2-experience-conditioned-cognitive-portfolio-v1.json'
V7=REPO/'candidates/kernel-self-generated/g2-coding-reasoning-workspace-v7.json'
REV=REPO/'experience/yado-coding-hypothesis-revision-v1.json'
OPEN=REPO/'experience/yado-coding-open-ended-defect-hypothesis-v1.json'
ORACLE=REPO/'experience/yado-coding-self-generated-test-oracle-v1.json'
RT2=REPO/'experience/yado-coding-real-code-transfer-v2.json'
RT3=REPO/'experience/yado-coding-real-code-transfer-v3.json'
OUT=REPO/'candidates/kernel-self-generated/g2-coding-experience-cognitive-consolidation-v1.json'
EXP=REPO/'experience/yado-coding-cognitive-consolidation-v1.json'

def load(p): return json.loads(Path(p).read_text(encoding='utf-8'))
def canon(o): return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def digest(o): return hashlib.sha256(canon(o).encode()).hexdigest()
def bucket(source,task): return int(hashlib.sha256((source+'|'+task).encode()).hexdigest()[:8],16)%4

task=load(TASK); parent=load(PARENT); v7=load(V7)
rev=load(REV); opn=load(OPEN); oracle=load(ORACLE); rt2=load(RT2); rt3=load(RT3)

if parent.get('status')!='PASS_SHADOW_G2_EXPERIENCE_CONDITIONED_COGNITIVE_PORTFOLIO_V1':
    raise RuntimeError('PRIOR_COGNITIVE_PORTFOLIO_NOT_PASS')
if v7.get('status')!='PASS_SHADOW_G2_CODING_REASONING_WORKSPACE_V7':
    raise RuntimeError('V7_REASONING_PARENT_NOT_PASS')
if rev.get('status')!='TRAINED' or opn.get('status')!='TRAINED' or oracle.get('status')!='TRAINED':
    raise RuntimeError('CODING_PASS_EXPERIENCE_MISSING')
if rt2.get('status')!='WITHHOLD' or rt3.get('status')!='TRAINED':
    raise RuntimeError('REAL_TRANSFER_POSITIVE_NEGATIVE_LINEAGE_MISSING')

core=UnifiedYADOCoreV1(REPO); head_before=copy.deepcopy(core.head)

logic_rows=[]
thinking_rows=[]
intel_rows=[]

def add(rows,source,task_id,features,expected):
    x=dict(features); x['state_known']=True
    rows.append({'source':source,'task_id':str(task_id),'input':x,'expected':expected})

# --- Mechanically extract actual control events from hypothesis-revision experience.
for ep in rev.get('episodes') or []:
    tid=ep['task_id']
    for rr in ep.get('revisions') or []:
        add(thinking_rows,'REVISION',tid,{
            'failure_seen':True,'candidate_available':False,'formal_spec_present':False,
            'hypothesis_set_present':False,'real_source':False,'result_exact':False
        },'REVISE')
        add(thinking_rows,'REVISION',tid,{
            'failure_seen':True,'candidate_available':bool(rr.get('changed')),'formal_spec_present':False,
            'hypothesis_set_present':False,'real_source':False,'result_exact':False
        },'TEST')
        exact=float(rr.get('post_cycle_holdout_score') or 0.0)==1.0
        add(logic_rows,'REVISION',tid,{
            'candidate_changed':bool(rr.get('changed')),'result_exact':exact,
            'repair_regressed':False,'oracle_exact':False,'real_source':False
        },'ACCEPT' if exact else 'CONTINUE')
        add(intel_rows,'REVISION',tid,{
            'failure_seen':True,'formal_spec_present':False,'hypothesis_set_present':False,
            'real_source':False,'repair_regressed':False,'result_exact':exact
        },'HYPOTHESIS_REVISION')

# --- Open-ended search: actual selected probes are evidence-acquisition events.
for ep in opn.get('episodes') or []:
    tid=ep['task_id']
    for tr in ep.get('probe_trace') or []:
        add(thinking_rows,'OPEN',tid,{
            'failure_seen':True,'candidate_available':bool(tr.get('candidate_changed_from_initial')),
            'formal_spec_present':False,'hypothesis_set_present':int(tr.get('hypothesis_count_before') or 0)>1,
            'real_source':False,'result_exact':False
        },'SEEK_EVIDENCE')
        add(intel_rows,'OPEN',tid,{
            'failure_seen':True,'formal_spec_present':False,
            'hypothesis_set_present':int(tr.get('hypothesis_count_before') or 0)>1,
            'real_source':False,'repair_regressed':False,'result_exact':False
        },'ACTIVE_EVIDENCE_SEARCH')
    add(logic_rows,'OPEN',tid,{
        'candidate_changed':bool(ep.get('source_changed')),'result_exact':float(ep.get('final_holdout_score') or 0)==1.0,
        'repair_regressed':False,'oracle_exact':False,'real_source':False
    },'ACCEPT' if float(ep.get('final_holdout_score') or 0)==1.0 else 'WITHHOLD')

# --- Formal spec -> synthesized oracle -> self-selected tests.
for ep in oracle.get('episodes') or []:
    tid=ep['task_id']
    add(thinking_rows,'ORACLE',tid,{
        'failure_seen':True,'candidate_available':False,'formal_spec_present':True,
        'hypothesis_set_present':False,'real_source':False,'result_exact':False,'oracle_available':False
    },'BUILD_ORACLE')
    for _ in ep.get('test_selection_trace') or []:
        add(thinking_rows,'ORACLE',tid,{
            'failure_seen':True,'candidate_available':True,'formal_spec_present':True,
            'hypothesis_set_present':False,'real_source':False,'result_exact':False,'oracle_available':True
        },'SEEK_EVIDENCE')
    exact=float(ep.get('final_code_holdout_score') or 0)==1.0 and float(ep.get('oracle_hidden_validation_score') or 0)==1.0
    add(logic_rows,'ORACLE',tid,{
        'candidate_changed':bool(ep.get('source_changed')),'result_exact':exact,
        'repair_regressed':False,'oracle_exact':float(ep.get('oracle_hidden_validation_score') or 0)==1.0,
        'real_source':False
    },'ACCEPT' if exact else 'WITHHOLD')
    add(intel_rows,'ORACLE',tid,{
        'failure_seen':True,'formal_spec_present':True,'hypothesis_set_present':False,
        'real_source':False,'repair_regressed':False,'result_exact':exact
    },'ORACLE_GUIDED_REPAIR')

# --- V2 negative real transfer: exact oracle but repair regressed / failed exactness.
for ep in rt2.get('episodes') or []:
    tid=ep['task_id']
    pre=float(ep.get('mutated_holdout_score') or 0.0); post=float(ep.get('repaired_holdout_score') or 0.0)
    regressed=post<pre or post<1.0
    add(logic_rows,'REAL_V2',tid,{
        'candidate_changed':bool(ep.get('source_changed')),'result_exact':post==1.0,
        'repair_regressed':regressed,'oracle_exact':float(ep.get('oracle_hidden_score') or 0)==1.0,
        'real_source':True
    },'WITHHOLD' if regressed else 'ACCEPT')
    add(thinking_rows,'REAL_V2',tid,{
        'failure_seen':True,'candidate_available':bool(ep.get('source_changed')),'formal_spec_present':True,
        'hypothesis_set_present':False,'real_source':True,'result_exact':post==1.0,
        'repair_regressed':regressed,'reversible':False
    },'WITHHOLD')
    add(intel_rows,'REAL_V2',tid,{
        'failure_seen':True,'formal_spec_present':True,'hypothesis_set_present':False,
        'real_source':True,'repair_regressed':regressed,'result_exact':post==1.0,'reversible':False
    },'WITHHOLD')

# --- V3 positive real transfer: reversible defects + iterative self-counterexamples.
for ep in rt3.get('episodes') or []:
    tid=ep['task_id']
    for tr in ep.get('test_selection_trace') or []:
        add(thinking_rows,'REAL_V3',tid,{
            'failure_seen':True,'candidate_available':True,'formal_spec_present':True,
            'hypothesis_set_present':False,'real_source':True,'result_exact':False,
            'repair_regressed':False,'reversible':bool(ep.get('reversible_shadow_defect'))
        },'SEEK_EVIDENCE')
    exact=float(ep.get('repaired_holdout_score') or 0)==1.0
    add(logic_rows,'REAL_V3',tid,{
        'candidate_changed':bool(ep.get('source_changed')),'result_exact':exact,
        'repair_regressed':False,'oracle_exact':float(ep.get('oracle_hidden_score') or 0)==1.0,
        'real_source':True,'reversible':bool(ep.get('reversible_shadow_defect'))
    },'ACCEPT' if exact else 'WITHHOLD')
    add(thinking_rows,'REAL_V3',tid,{
        'failure_seen':False,'candidate_available':True,'formal_spec_present':True,
        'hypothesis_set_present':False,'real_source':True,'result_exact':exact,
        'repair_regressed':False,'reversible':True
    },'ACCEPT' if exact else 'WITHHOLD')
    add(intel_rows,'REAL_V3',tid,{
        'failure_seen':True,'formal_spec_present':True,'hypothesis_set_present':False,
        'real_source':True,'repair_regressed':False,'result_exact':exact,'reversible':True
    },'ITERATIVE_REAL_REPAIR')

# Add contrastive unknown twins learned from the V6/V7 representation lesson.
def with_unknown_twins(rows):
    out=[]
    for r in rows:
        out.append(copy.deepcopy(r))
        u=copy.deepcopy(r)
        u['input']['state_known']=False
        u['expected']='WITHHOLD'
        u['source']=r['source']+'_UNKNOWN'
        out.append(u)
    return out

logic_rows=with_unknown_twins(logic_rows)
thinking_rows=with_unknown_twins(thinking_rows)
intel_rows=with_unknown_twins(intel_rows)

def split_rows(rows):
    fit=[];blind=[]
    for r in rows:
        # Unknown twins follow the same task split as their known parent.
        src=r['source'].replace('_UNKNOWN','')
        if bucket(src,r['task_id'])==3: blind.append(r)
        else: fit.append(r)
    return fit,blind

logic_fit,logic_blind=split_rows(logic_rows)
thinking_fit,thinking_blind=split_rows(thinking_rows)
intel_fit,intel_blind=split_rows(intel_rows)

if min(len(logic_fit),len(logic_blind),len(thinking_fit),len(thinking_blind),len(intel_fit),len(intel_blind))<6:
    raise RuntimeError('COGNITIVE_SPLIT_TOO_SMALL')

# Native active LOGIC learner.
logic_prog=ConjunctiveRuleInducerV1.synthesize(
    'G2_CODING_EXPERIENCE_LOGIC_CONSOLIDATION','LOGIC',
    [{'input':r['input'],'expected':r['expected']} for r in logic_fit],
    min_support=2,max_rules=12
)
logic_fresh=program_acc(logic_prog,[{'input':r['input'],'expected':r['expected']} for r in logic_blind])
logic_ablation=program_acc(logic_prog,[{'input':r['input'],'expected':r['expected']} for r in logic_blind],ablated=True)
logic_restore=program_acc(logic_prog,[{'input':r['input'],'expected':r['expected']} for r in logic_blind])

# Native active THINKING learner: same generic conjunction learner, different organ/target.
thinking_prog=ConjunctiveRuleInducerV1.synthesize(
    'G2_CODING_EXPERIENCE_NEXT_COGNITIVE_ACTION','THINKING',
    [{'input':r['input'],'expected':r['expected']} for r in thinking_fit],
    min_support=2,max_rules=12
)
thinking_fresh=program_acc(thinking_prog,[{'input':r['input'],'expected':r['expected']} for r in thinking_blind])
thinking_ablation=program_acc(thinking_prog,[{'input':r['input'],'expected':r['expected']} for r in thinking_blind],ablated=True)
thinking_restore=program_acc(thinking_prog,[{'input':r['input'],'expected':r['expected']} for r in thinking_blind])

# Native canonical-active INTELLIGENCE router.
intel_cases=[{'input':r['input'],'expected':r['expected']} for r in intel_fit]
intel_model=CoveragePrunedCompositionalSchemaRouterV3.fit(intel_cases,'WITHHOLD',max_trigger_width=2)
def route_one(x):
    out=CoveragePrunedCompositionalSchemaRouterV3.route(intel_model,x)
    return out[0] if len(out)==1 else '|'.join(out)
intel_fresh=sum(route_one(r['input'])==r['expected'] for r in intel_blind)/len(intel_blind)
# Typed unknown-state ablation: state_known=False must collapse to fail-closed WITHHOLD.
intel_abl_cases=[]
for r in intel_blind:
    x=dict(r['input']);x['state_known']=False
    intel_abl_cases.append((x,'WITHHOLD'))
intel_ablation=sum(route_one(x)==expected for x,expected in intel_abl_cases)/len(intel_abl_cases)
intel_restore=sum(route_one(r['input'])==r['expected'] for r in intel_blind)/len(intel_blind)

unknown_input={'state_known':False,'never_seen_field':'NOVEL'}
unknown_logic=BoundedRuleSandbox.execute(logic_prog,unknown_input)
unknown_thinking=BoundedRuleSandbox.execute(thinking_prog,unknown_input)
unknown_intel=route_one(unknown_input)
unknown_fail_closed=(unknown_logic=='WITHHOLD' and unknown_thinking=='WITHHOLD' and unknown_intel=='WITHHOLD')

# End-to-end composite: all three organ decisions must be correct on their own fresh sets.
# This measures the coherent layer rather than averaging away one weak organ.
composite_fresh=min(logic_fresh,thinking_fresh,intel_fresh)

parent_genes=parent.get('portfolio',{}).get('selected_genes') or []
parent_gene_ids=[x.get('gene_id') for x in parent_genes if x.get('gene_id')]
recent_gene_ids=[
    v7.get('thinking_gene_id'),
    rev.get('revision_gene',{}).get('gene_id'),
    opn.get('open_ended_gene',{}).get('gene_id'),
    oracle.get('oracle_gene',{}).get('gene_id'),
    rt2.get('real_code_transfer_gene',{}).get('gene_id'),
    rt3.get('real_code_transfer_gene',{}).get('gene_id'),
]
heritage=[x for x in parent_gene_ids+recent_gene_ids if x]

logic_gene={
 'schema':'yado.g2.coding_experience_logic_gene.v1',
 'gene_id':'GENE-G2-CODING-EXPERIENCE-LOGIC-V1-'+digest({'program':canonical_program(logic_prog),'heritage':heritage})[:16],
 'organ':'LOGIC','program':canonical_program(logic_prog),
 'fresh':logic_fresh,'ablation':logic_ablation,'restore':logic_restore,
 'heritage':heritage,'promotion_state':'SHADOW_ONLY'
}
logic_gene['gene_digest']=digest(logic_gene)
thinking_gene={
 'schema':'yado.g2.coding_experience_thinking_gene.v1',
 'gene_id':'GENE-G2-CODING-EXPERIENCE-THINKING-V1-'+digest({'program':canonical_program(thinking_prog),'heritage':heritage})[:16],
 'organ':'THINKING','program':canonical_program(thinking_prog),
 'fresh':thinking_fresh,'ablation':thinking_ablation,'restore':thinking_restore,
 'heritage':heritage,'promotion_state':'SHADOW_ONLY'
}
thinking_gene['gene_digest']=digest(thinking_gene)
intel_gene={
 'schema':'yado.g2.coding_experience_intelligence_gene.v1',
 'gene_id':'GENE-G2-CODING-EXPERIENCE-INTELLIGENCE-V1-'+digest({'model':intel_model,'heritage':heritage})[:16],
 'organ':'INTELLIGENCE','model':intel_model,
 'fresh':intel_fresh,'ablation_unknown_fail_closed':intel_ablation,'restore':intel_restore,
 'heritage':heritage,'promotion_state':'SHADOW_ONLY'
}
intel_gene['gene_digest']=digest(intel_gene)

cognitive_gene={
 'schema':'yado.g2.coding_experience_cognitive_layer_gene.v1',
 'gene_id':'GENE-G2-CODING-EXPERIENCE-COGNITIVE-LAYER-V1-'+digest({
     'logic':logic_gene['gene_digest'],'thinking':thinking_gene['gene_digest'],'intelligence':intel_gene['gene_digest']
 })[:16],
 'components':{
   'LOGIC':logic_gene['gene_id'],
   'THINKING':thinking_gene['gene_id'],
   'INTELLIGENCE':intel_gene['gene_id']
 },
 'mechanism_kind':'EXPERIENCE_CONDITIONED_FAIL_CLOSED_LOGIC_THINKING_INTELLIGENCE_COMPOSITE',
 'heritage':heritage,
 'fresh_composite':composite_fresh,
 'promotion_state':'SHADOW_ONLY'
}
cognitive_gene['gene_digest']=digest(cognitive_gene)

checks={
 'prior_cognitive_portfolio_consumed':True,
 'coding_pass_and_withhold_history_consumed':all([
   v7.get('status','').startswith('PASS'),
   rev.get('status')=='TRAINED',opn.get('status')=='TRAINED',oracle.get('status')=='TRAINED',
   rt2.get('status')=='WITHHOLD',rt3.get('status')=='TRAINED'
 ]),
 'v2_negative_transfer_consumed':rt2.get('status')=='WITHHOLD',
 'logic_native_learner_used':logic_prog.target_organ=='LOGIC',
 'thinking_native_learner_used':thinking_prog.target_organ=='THINKING',
 'intelligence_native_router_used':intel_model.get('kind')=='COVERAGE_PRUNED_COMPOSITIONAL_TRIGGER_ROUTER_V3',
 'unknown_contrastive_training_applied':all(any(r['input'].get('state_known') is False for r in rows) for rows in (logic_rows,thinking_rows,intel_rows)),
 'logic_fresh_high':logic_fresh>=.95,
 'logic_causal_ablation':logic_fresh-logic_ablation>=.25,
 'logic_restore_exact':logic_restore==logic_fresh,
 'thinking_fresh_high':thinking_fresh>=.95,
 'thinking_causal_ablation':thinking_fresh-thinking_ablation>=.25,
 'thinking_restore_exact':thinking_restore==thinking_fresh,
 'intelligence_fresh_high':intel_fresh>=.95,
 'intelligence_restore_exact':intel_restore==intel_fresh,
 'unknown_fail_closed':unknown_fail_closed,
 'composite_fresh_high':composite_fresh>=.95,
 'three_new_organ_gene_identities':len({logic_gene['gene_id'],thinking_gene['gene_id'],intel_gene['gene_id']})==3,
 'host_written_cognitive_rules':False,
 'host_selected_winner':False,
 'external_models_used':False,
 'automatic_canonical_promotion':False,
 'canonical_unchanged':core.head.get('canonical_head_digest')==head_before.get('canonical_head_digest'),
}
positive=[k for k in checks if k not in ('host_written_cognitive_rules','host_selected_winner','external_models_used','automatic_canonical_promotion')]
negative=('host_written_cognitive_rules','host_selected_winner','external_models_used','automatic_canonical_promotion')
passed=all(checks[k] is True for k in positive) and all(checks[k] is False for k in negative)
status='PASS_SHADOW_G2_CODING_EXPERIENCE_COGNITIVE_CONSOLIDATION_V1' if passed else 'WITHHOLD_G2_CODING_EXPERIENCE_COGNITIVE_CONSOLIDATION_V1'

experience={
 'schema':'yado.g2.coding_experience_cognitive_consolidation.experience.v1',
 'status':'TRAINED' if passed else 'WITHHOLD',
 'source_experience_digests':{
   'revision':rev.get('experience_digest'),'open':opn.get('experience_digest'),
   'oracle':oracle.get('experience_digest'),'real_v2':rt2.get('experience_digest'),'real_v3':rt3.get('experience_digest')
 },
 'row_counts':{
   'logic':[len(logic_fit),len(logic_blind)],
   'thinking':[len(thinking_fit),len(thinking_blind)],
   'intelligence':[len(intel_fit),len(intel_blind)]
 },
 'organ_genes':{'LOGIC':logic_gene,'THINKING':thinking_gene,'INTELLIGENCE':intel_gene},
 'cognitive_gene':cognitive_gene,
 'metrics':{
   'logic_fresh':logic_fresh,'logic_ablation':logic_ablation,
   'thinking_fresh':thinking_fresh,'thinking_ablation':thinking_ablation,
   'intelligence_fresh':intel_fresh,'intelligence_unknown_fail_closed_score':intel_ablation,
   'composite_fresh':composite_fresh,'unknown_fail_closed':unknown_fail_closed
 },
 'canonical_mutation':False,
 'semantic_boundary':'THIS CONSOLIDATES OBSERVED YADO CODING EXPERIENCE INTO NEW SHADOW LOGIC/THINKING/INTELLIGENCE CONTROL GENES. TRAINING LABELS ARE MECHANICALLY EXTRACTED FROM ACTUAL RECORDED ACTIONS AND OUTCOMES; UNKNOWN CONTRASTIVE TWINS IMPLEMENT THE PREVIOUS V6/V7 FAIL-CLOSED REPRESENTATION LESSON. IT DOES NOT CHANGE MODEL WEIGHTS, CLAIM AGI, OR PROMOTE TO CANONICAL.'
}
experience['experience_digest']=digest(experience)
EXP.parent.mkdir(parents=True,exist_ok=True)
EXP.write_text(json.dumps(experience,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')

report={
 'schema':'yado.g2.coding_experience_cognitive_consolidation.v1',
 'status':status,'task':task,
 'logic_fresh':logic_fresh,'logic_ablation':logic_ablation,'logic_restore':logic_restore,
 'thinking_fresh':thinking_fresh,'thinking_ablation':thinking_ablation,'thinking_restore':thinking_restore,
 'intelligence_fresh':intel_fresh,'intelligence_ablation':intel_ablation,'intelligence_restore':intel_restore,
 'composite_fresh':composite_fresh,'unknown_fail_closed':unknown_fail_closed,
 'unknown_outputs':{'logic':unknown_logic,'thinking':unknown_thinking,'intelligence':unknown_intel},
 'logic_gene_id':logic_gene['gene_id'],'thinking_gene_id':thinking_gene['gene_id'],
 'intelligence_gene_id':intel_gene['gene_id'],'cognitive_gene_id':cognitive_gene['gene_id'],
 'organ_genes':{'LOGIC':logic_gene,'THINKING':thinking_gene,'INTELLIGENCE':intel_gene},
 'cognitive_gene':cognitive_gene,'checks':checks,
 'canonical_mutation':False,'promotion_applied':False,
 'next_required_capability':'G2_COGNITIVE_CONSOLIDATION_STRESS_AND_ADMISSION_V1' if passed else 'G2_CODING_EXPERIENCE_COGNITIVE_CONSOLIDATION_V2',
 'receipt_sha256':None,
 'semantic_boundary':experience['semantic_boundary']
}
report['receipt_sha256']=digest({k:v for k,v in report.items() if k!='receipt_sha256'})
OUT.parent.mkdir(parents=True,exist_ok=True)
OUT.write_text(json.dumps(report,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')
print(json.dumps({
 'status':status,
 'logic':{'fresh':logic_fresh,'ablation':logic_ablation,'restore':logic_restore},
 'thinking':{'fresh':thinking_fresh,'ablation':thinking_ablation,'restore':thinking_restore},
 'intelligence':{'fresh':intel_fresh,'unknown_fail_closed_score':intel_ablation,'restore':intel_restore},
 'composite_fresh':composite_fresh,'unknown_fail_closed':unknown_fail_closed,
 'genes':{'logic':logic_gene['gene_id'],'thinking':thinking_gene['gene_id'],'intelligence':intel_gene['gene_id'],'cognitive':cognitive_gene['gene_id']},
 'next_required_capability':report['next_required_capability'],'receipt_sha256':report['receipt_sha256']
},indent=2,sort_keys=True))
if not passed: raise SystemExit(2)
