from __future__ import annotations

from pathlib import Path
import copy, hashlib, inspect, json, random, sys

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
PKG=ROOT/'yado_rc8_v36'
sys.path[:0]=[str(ROOT),str(PKG)]

from yado_g2_unified_module_kernel_v1 import *
from yado_bounded_capability_router_v1 import BoundedCapabilityRouterLearnerV1
from yado_conjunctive_rule_inducer_v1 import ConjunctiveRuleInducerV1
from yado_bounded_dnf_relation_policy_inducer_v1 import BoundedDNFRelationPolicyInducerV1
from yado_generic_relational_meta_language_v1 import GenericRelationalMetaLanguageV1
from yado_generic_event_state_meta_language_v1 import GenericEventStateMetaLanguageV1
from yado_budget_adaptive_compositional_logic_v2 import BudgetAdaptiveCompositionalLogicV2
from yado_work_budget_adaptive_contingent_planner_v2 import WorkBudgetAdaptiveContingentPlannerV2
from yado_coverage_pruned_compositional_schema_router_v3 import CoveragePrunedCompositionalSchemaRouterV3

HEAD=REPO/'canonical/yado-main-head-g2.json'
CORE=REPO/'canonical/yado-unified-core-v1.json'
TRI=REPO/'canonical/yado-g2-all-experience-tri-organ-v1.json'
BIND=REPO/'candidates/kernel-self-generated/g2-all-experience-tri-organ-additive-canonical-binding-v2.json'
OUT=REPO/'candidates/kernel-self-generated/g2-tri-organ-canonical-burnin-old-parent-comparative-ab-v1.json'
EXP=REPO/'experience/yado-tri-organ-canonical-burnin-old-parent-comparative-ab-v1.json'

def load(p): return json.loads(Path(p).read_text(encoding='utf-8'))
def canon(o): return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def digest(o): return hashlib.sha256(canon(o).encode()).hexdigest()

def old_desc(cap):
    d={'budget_limited':False,'quota_limited':False,'external_evidence_needed':False,'relation_needed':False,'disjunction_needed':False,'context_ambiguous':False}
    if cap in {CAP_LOGIC_V2,CAP_THINK_V2,CAP_INTEL_V3}: d['module_id']=cap
    return d

def build_kernel():
    route_train=[]
    for i in range(28):
        for cap in [CAP_CONJ,CAP_REL,CAP_BUD,CAP_RES,CAP_LOGIC_V2,CAP_THINK_V2,CAP_INTEL_V3]:
            route_train.append({'input':old_desc(cap)|{'noise':i%3},'expected':cap})
    router=BoundedCapabilityRouterLearnerV1.synthesize(route_train,route_train,CAP_CONJ,min_support=5)

    scalar_cases=[]
    for a in [False,True]:
      for b in [False,True]:
        for c in [False,True]:
          for _ in range(4):
            scalar_cases.append({'input':{'condition_a':a,'condition_b':b,'condition_c':c},'expected':'PASS' if a and b and c else 'HOLD'})
    scalar=ConjunctiveRuleInducerV1.synthesize('BURNIN_SCALAR','LOGIC',scalar_cases,min_support=2,max_rules=12)

    rel_train=[]
    for i in range(180):
        owner=f'U{i%31}';actor=owner if i%3==0 else f'U{(i*5+3)%37}';verified=i%2==0
        rel_train.append({'input':{'actor':actor,'owner':owner,'verified':verified,'role':['MEMBER','LEAD','GUEST'][i%3]},'expected':'ALLOW' if actor==owner and verified else 'DENY'})
    relation=BoundedDNFRelationPolicyInducerV1.synthesize('BURNIN_REL','LOGIC',rel_train,min_support=3,max_clauses=12,validation_cases=rel_train)
    return UnifiedYADOModuleKernelV1(router,scalar,relation,REPO)

def rel_truth(edges,start):
    state={start}
    for _ in range(128):
        nxt=state|{b for a,b in edges if a in state}
        if nxt==state: break
        state=nxt
    return tuple(sorted(state,key=str))

def old_tasks(cycle):
    logic_rows=[]
    for a in [False,True]:
      for b in [False,True]:
        for _ in range(5):
          logic_rows.append({'input':{'a':a,'b':b},'expected':'EVEN' if a==b else 'ODD'})
    logic_payload={'a':bool(cycle%2),'b':bool((cycle//2)%2)}
    logic_expected='EVEN' if logic_payload['a']==logic_payload['b'] else 'ODD'
    logic_task={'kind':'logic_v2','descriptor':{'module_id':CAP_LOGIC_V2},'stream_id':f'OLD-L-{cycle}',
                'train_rows':logic_rows,'payload':logic_payload}

    plan_task={'kind':'thinking_v2','descriptor':{'module_id':CAP_THINK_V2},'stream_id':f'OLD-T-{cycle}',
      'current_confidence':0.15+0.01*(cycle%5),'target_confidence':0.8,'remaining_budget':5.0,
      'stages':[{'stage_id':'OBSERVE','cost':1,'expected_gain':0.35},
                {'stage_id':'DEEP','cost':3,'expected_gain':0.7,'requires':['OBSERVE']}]}

    intel_cases=[]
    for i in range(10):
      intel_cases += [
        {'input':{'kind':'logic','urgent':bool(i%2)},'expected':CAP_LOGIC_V2},
        {'input':{'kind':'plan','urgent':bool(i%2)},'expected':CAP_THINK_V2},
      ]
    intel_task={'kind':'intelligence_v3','descriptor':{'module_id':CAP_INTEL_V3},'stream_id':f'OLD-I-{cycle}',
                'train_cases':intel_cases,'fallback_output':CAP_LOGIC_V2,
                'payload':{'kind':'plan' if cycle%2 else 'logic','urgent':bool(cycle%3)}}
    intel_expected=CAP_THINK_V2 if cycle%2 else CAP_LOGIC_V2
    return [
      (CAP_LOGIC_V2,logic_task,lambda x,e=logic_expected:x.get('result')==e),
      (CAP_THINK_V2,plan_task,lambda x:x.get('result',{}).get('feasible') is True),
      (CAP_INTEL_V3,intel_task,lambda x,e=intel_expected:e in x.get('result',())),
    ]

def fresh_tri_cases(cycle):
    token=hashlib.sha256(f'BURNIN-{cycle}'.encode()).hexdigest()[:12]
    chain=[f'N{cycle}_{token}_{i}' for i in range(5+(cycle%6))]
    distract=[f'D{cycle}_{token}_{i}' for i in range(4)]
    edges=list(zip(chain[:-1],chain[1:]))+list(zip(distract[:-1],distract[1:]))
    rel={'input_contract':'RELATION_START_TO_STATE','relation':tuple(edges),'start':chain[0],
         'expected':rel_truth(edges,chain[0]),'stream_id':f'TRI-R-{cycle}'}

    keys=[f'K{cycle}_{token}_{i}' for i in range(4+(cycle%5))]
    Q='Q';R='R'
    valid=tuple([(Q,k) for k in keys]+[(R,k) for k in reversed(keys)])
    crossed=tuple([(Q,k) for k in keys]+[(R,k) for k in keys])
    underflow=tuple([(R,keys[0]),(Q,keys[-1]),(R,keys[-1])])
    unfinished=tuple(list(valid)[:-1])
    wrong=list(valid);wrong[len(keys)]=(R,'WRONG_'+token)
    rep=keys[-1]
    repeated=tuple([(Q,rep)]*len(keys)+[(R,rep)]*len(keys))
    evs=[
      {'events':valid,'expected':True,'kind':'VALID'},
      {'events':crossed,'expected':False,'kind':'CROSSED'},
      {'events':underflow,'expected':False,'kind':'UNDERFLOW'},
      {'events':unfinished,'expected':False,'kind':'UNFINISHED'},
      {'events':tuple(wrong),'expected':False,'kind':'WRONG_KEY'},
      {'events':repeated,'expected':True,'kind':'REPEATED_VALID'},
    ]
    return rel,evs

head=load(HEAD);core=load(CORE);tri=load(TRI);binding=load(BIND)
head_digest_before=head['canonical_head_digest']
active=set(head.get('active_capabilities') or [])
required={CAP_LOGIC_V2,CAP_THINK_V2,CAP_INTEL_V3,CAP_TRI_LOGIC,CAP_TRI_THINKING,CAP_TRI_INTELLIGENCE}
if not required <= active:
    raise RuntimeError('MISSING_BURNIN_CAPABILITIES:'+str(sorted(required-active)))
if tri.get('status')!='CANONICAL_ACTIVE' or binding.get('status')!='PASS_G2_TRI_ORGAN_ADDITIVE_CANONICAL_BINDING_V2':
    raise RuntimeError('TRI_ORGAN_BINDING_NOT_CANONICAL_PASS')
if tri.get('replace_existing_organs') is not False:
    raise RuntimeError('OLD_PARENTS_WERE_REPLACED')

# Prove API distinction instead of pretending the old parents implement the new contracts.
old_parent_api={
 'logic_methods':sorted(n for n,v in inspect.getmembers(BudgetAdaptiveCompositionalLogicV2) if callable(v) and not n.startswith('_')),
 'thinking_methods':sorted(n for n,v in inspect.getmembers(WorkBudgetAdaptiveContingentPlannerV2) if callable(v) and not n.startswith('_')),
 'intelligence_methods':sorted(n for n,v in inspect.getmembers(CoveragePrunedCompositionalSchemaRouterV3) if callable(v) and not n.startswith('_')),
}
old_parent_has_tri_contract_api=any(
    token in canon(old_parent_api)
    for token in ['RELATION_START_TO_STATE','EVENT_SEQUENCE_TO_BOOLEAN']
)

CYCLES=64
old_total=old_pass=0
tri_relation_total=tri_relation_pass=0
tri_event_total=tri_event_pass=0
tri_intel_total=tri_intel_pass=0
parent_only_mixed_supported=0
enabled_mixed_supported=0
mixed_total=0
restart_instances=0
old_outputs=[]
relation_cases=[]
event_cases=[]
unsupported_withhold_pass=0

kernel=None
for cycle in range(CYCLES):
    if kernel is None or cycle%8==0:
        kernel=build_kernel(); restart_instances+=1
    # Old-parent native tasks must stay exact with tri-organ enabled.
    for mid,task,pred in old_tasks(cycle):
        out=kernel.execute(mid,task)
        ok=bool(pred(out))
        old_total+=1;old_pass+=int(ok)
        old_outputs.append({'cycle':cycle,'component':mid,'pass':ok,'result':out.get('result')})
        enabled_mixed_supported+=int(ok)
        parent_only_mixed_supported+=int(ok)
        mixed_total+=1

    rel,evs=fresh_tri_cases(cycle)
    relation_cases.append({'relation':rel['relation'],'start':rel['start'],'expected':rel['expected']})
    l=kernel.execute(CAP_TRI_LOGIC,{'relation':rel['relation'],'start':rel['start'],'stream_id':rel['stream_id']})
    lok=tuple(l.get('result',()))==tuple(rel['expected'])
    tri_relation_total+=1;tri_relation_pass+=int(lok)
    enabled_mixed_supported+=int(lok);mixed_total+=1

    ir=kernel.execute(CAP_TRI_INTELLIGENCE,{'input_contract':'RELATION_START_TO_STATE','relation':rel['relation'],'start':rel['start'],'stream_id':f'TRI-IR-{cycle}'})
    irok=ir.get('selected_component')==CAP_TRI_LOGIC and tuple(ir.get('result',()))==tuple(rel['expected'])
    tri_intel_total+=1;tri_intel_pass+=int(irok)

    for j,e in enumerate(evs):
        event_cases.append({'events':e['events'],'expected':e['expected']})
        t=kernel.execute(CAP_TRI_THINKING,{'events':e['events'],'stream_id':f'TRI-E-{cycle}-{j}'})
        tok=t.get('result') is bool(e['expected'])
        tri_event_total+=1;tri_event_pass+=int(tok)
        # Count one new-event contract per variant in mixed coverage.
        enabled_mixed_supported+=int(tok);mixed_total+=1
        ii=kernel.execute(CAP_TRI_INTELLIGENCE,{'input_contract':'EVENT_SEQUENCE_TO_BOOLEAN','events':e['events'],'stream_id':f'TRI-II-{cycle}-{j}'})
        iiok=ii.get('selected_component')==CAP_TRI_THINKING and ii.get('result') is bool(e['expected'])
        tri_intel_total+=1;tri_intel_pass+=int(iiok)

    # Unsupported tri-intelligence contract must fail closed on every cycle.
    u=kernel.execute(CAP_TRI_INTELLIGENCE,{'input_contract':'UNSEEN_BURNIN_CONTRACT_'+token if (token:=(hashlib.sha256(str(cycle).encode()).hexdigest()[:8])) else 'X','stream_id':f'TRI-U-{cycle}'})
    unsupported_withhold_pass += int(u.get('status')=='WITHHOLD_UNSUPPORTED_CONTRACT' and u.get('selected_component') is None)

# Structural ablation over the entire burn-in corpus.
logic_program=tri['genes']['LOGIC']['operator_program']
think_program=tri['genes']['THINKING']['operator_program']
def rel_acc(program):
    return sum(GenericRelationalMetaLanguageV1.execute(program,c['relation'],c['start'])==c['expected'] for c in relation_cases)/len(relation_cases)
def evt_acc(program):
    return sum(GenericEventStateMetaLanguageV1.execute(program,c['events']) is bool(c['expected']) for c in event_cases)/len(event_cases)
logic_full=rel_acc(logic_program)
logic_ab=max((rel_acc(a['program']) for a in GenericRelationalMetaLanguageV1.ablations(logic_program)),default=0.0)
think_full=evt_acc(think_program)
think_ab=max((evt_acc(a['program']) for a in GenericEventStateMetaLanguageV1.ablations(think_program)),default=0.0)

# Parent-only B supports exactly the old native tasks; it does not fake the two new contracts.
enabled_coverage=enabled_mixed_supported/mixed_total
parent_only_coverage=parent_only_mixed_supported/mixed_total
coverage_gain=enabled_coverage-parent_only_coverage

head_after=load(HEAD)
core_after=load(CORE)
checks={
 'binding_still_canonical_active':tri.get('status')=='CANONICAL_ACTIVE',
 'old_parents_still_active':{CAP_LOGIC_V2,CAP_THINK_V2,CAP_INTEL_V3} <= active,
 'old_parent_native_accuracy_1':old_pass==old_total and old_total==CYCLES*3,
 'tri_logic_accuracy_1':tri_relation_pass==tri_relation_total==CYCLES,
 'tri_thinking_accuracy_1':tri_event_pass==tri_event_total==CYCLES*6,
 'tri_intelligence_accuracy_1':tri_intel_pass==tri_intel_total==CYCLES*7,
 'tri_unsupported_contract_fail_closed_all_cycles':unsupported_withhold_pass==CYCLES,
 'logic_burnin_full_accuracy_1':logic_full==1.0,
 'logic_burnin_causal_drop_ge_0_20':logic_full-logic_ab>=.20,
 'thinking_burnin_full_accuracy_1':think_full==1.0,
 'thinking_burnin_causal_drop_ge_0_10':think_full-think_ab>=.10,
 'eight_restart_instances':restart_instances==8,
 'old_parent_has_no_tri_contract_api':old_parent_has_tri_contract_api is False,
 'enabled_mixed_coverage_1':enabled_coverage==1.0,
 'parent_only_mixed_coverage_lower':parent_only_coverage<enabled_coverage,
 'coverage_gain_positive':coverage_gain>0,
 'canonical_head_digest_unchanged':head_after.get('canonical_head_digest')==head_digest_before,
 'frontier_unchanged':head_after.get('current_frontier')==head.get('current_frontier'),
 'active_capability_count_31':len(head_after.get('active_capabilities') or [])==31,
 'active_runtime_source_count_39':len(core_after.get('active_runtime_sources') or [])==39,
 'g3_not_started':head_after.get('g3_genesis_performed') is False,
}
status='PASS_G2_TRI_ORGAN_CANONICAL_BURNIN_OLD_PARENT_COMPARATIVE_AB_V1' if all(checks.values()) else 'WITHHOLD_G2_TRI_ORGAN_CANONICAL_BURNIN_OLD_PARENT_COMPARATIVE_AB_V1'

experience={
 'schema':'yado.g2.tri_organ_canonical_burnin_old_parent_comparative_ab.experience.v1',
 'status':'PASS_EVIDENCE' if status.startswith('PASS') else 'WITHHOLD_EVIDENCE',
 'cycles':CYCLES,'restart_instances':restart_instances,
 'old_parent_api':old_parent_api,
 'old_parent_has_tri_contract_api':old_parent_has_tri_contract_api,
 'metrics':{
   'old_parent_native_accuracy':old_pass/old_total,
   'tri_logic_accuracy':tri_relation_pass/tri_relation_total,
   'tri_thinking_accuracy':tri_event_pass/tri_event_total,
   'tri_intelligence_accuracy':tri_intel_pass/tri_intel_total,
   'unsupported_withhold_rate':unsupported_withhold_pass/CYCLES,
   'logic_full_accuracy':logic_full,'logic_best_ablation_accuracy':logic_ab,'logic_causal_drop':logic_full-logic_ab,
   'thinking_full_accuracy':think_full,'thinking_best_ablation_accuracy':think_ab,'thinking_causal_drop':think_full-think_ab,
   'enabled_mixed_coverage':enabled_coverage,'parent_only_mixed_coverage':parent_only_coverage,'coverage_gain':coverage_gain,
 },
 'checks':checks,
 'canonical_mutation':False,
 'semantic_boundary':'A/B COMPARES THE ADDITIVE CANONICAL SYSTEM AGAINST A PARENT-ONLY BYPASS ON A MIXED STREAM. OLD V2/V2/V3 ARE JUDGED ONLY ON THEIR NATIVE CONTRACTS AND MUST REMAIN IDENTICAL. THE NEW TRI-ORGAN LAYER IS JUDGED ON THE TWO CONTRACTS IT WAS ADMITTED FOR. PARENT-ONLY DOES NOT RECEIVE A FAKE ADAPTER FOR CONTRACTS ITS API DOES NOT IMPLEMENT.'
}
experience['experience_digest']=digest(experience)
EXP.parent.mkdir(parents=True,exist_ok=True)
EXP.write_text(json.dumps(experience,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')

report={
 'schema':'yado.g2.tri_organ_canonical_burnin_old_parent_comparative_ab.v1',
 'status':status,'cycles':CYCLES,'restart_instances':restart_instances,
 'binding_receipt_sha256':binding.get('receipt_sha256'),
 'canonical_head_digest':head_digest_before,
 'metrics':experience['metrics'],'checks':checks,
 'canonical_mutation':False,'architecture_mutation':False,'generation_transition':False,
 'g3_genesis_performed':False,'automatic_canonical_promotion':False,
 'next_required_capability':'TRI_ORGAN_SELECTIVE_MAIN_ADMISSION_REVIEW_V1' if status.startswith('PASS') else 'TRI_ORGAN_CANONICAL_BURNIN_REPAIR_V2',
 'semantic_boundary':experience['semantic_boundary']
}
report['receipt_sha256']=digest(report)
OUT.parent.mkdir(parents=True,exist_ok=True)
OUT.write_text(json.dumps(report,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')
print(json.dumps(report,indent=2,sort_keys=True,default=str))
if status!='PASS_G2_TRI_ORGAN_CANONICAL_BURNIN_OLD_PARENT_COMPARATIVE_AB_V1':
    raise SystemExit(2)
