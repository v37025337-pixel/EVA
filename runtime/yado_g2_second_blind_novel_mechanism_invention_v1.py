from __future__ import annotations
from pathlib import Path
import hashlib,json,os,random,sys

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
PKG=ROOT/'yado_rc8_v36'
sys.path[:0]=[str(ROOT),str(PKG)]

from yado_unified_core_v1 import UnifiedYADOCoreV1
from yado_g2_typed_recurrent_capability_graph_runtime_v1 import G2TypedRecurrentCapabilityGraphRuntimeV1
from yado_g2_unified_execution_fabric_v3 import G2UnifiedExecutionFabricV3
from yado_bounded_capability_router_v1 import BoundedCapabilityRouterLearnerV1
from yado_conjunctive_rule_inducer_v1 import ConjunctiveRuleInducerV1
from yado_evolutionary_genome_v3 import YADOEvolutionaryGenomeV3
from yado_generic_event_state_meta_language_v1 import GenericEventStateMetaLanguageV1

CAP_CONJ='ALG-CONJUNCTIVE-RULE-INDUCER-V1'
CAP_REL='ALG-BOUNDED-DNF-RELATION-POLICY-INDUCER-V1'
CAP_BUD='ALG-BUDGETED-STAGE-POLICY-V1'
CAP_RES='RESOURCE-PORTFOLIO-V1'
CAP_LOGIC_V2='ALG-G2-BUDGET-ADAPTIVE-COMPOSITIONAL-LOGIC-V2'
PREVIOUS=REPO/'candidates/kernel-self-generated/g2-blind-novel-mechanism-invention-v1.json'

def canon(o): return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def digest(o): return hashlib.sha256(canon(o).encode()).hexdigest()

def desc(cap):
    d={'budget_limited':False,'quota_limited':False,'external_evidence_needed':False,'relation_needed':False,'disjunction_needed':False}
    if cap==CAP_BUD: d['budget_limited']=True
    elif cap==CAP_RES: d['external_evidence_needed']=True
    elif cap==CAP_REL: d['relation_needed']=True
    return d

def build_fabric(core):
    route=[]
    for i in range(20):
        for cap in [CAP_CONJ,CAP_REL,CAP_BUD,CAP_RES]:
            route.append({'input':desc(cap)|{'nonce':i%3},'expected':cap})
    router=BoundedCapabilityRouterLearnerV1.synthesize(route,route,CAP_CONJ,min_support=4)
    rows=[]
    for a in [False,True]:
      for b in [False,True]:
        for c in [False,True]:
          for _ in range(4):
            rows.append({'input':{'condition_a':a,'condition_b':b,'condition_c':c},'expected':'PASS' if a and b and c else 'HOLD'})
    scalar=ConjunctiveRuleInducerV1.synthesize('SECOND_BLIND_SCALAR','LOGIC',rows,min_support=2,max_rules=12)
    class Rel:
        def execute(self,x): return 'ALLOW' if x.get('allow') else 'DENY'
    base=G2TypedRecurrentCapabilityGraphRuntimeV1(core.architecture,router,scalar,Rel(),core.portfolio)
    return G2UnifiedExecutionFabricV3(base)

OPEN='Q'; CLOSE='R'

def valid_nested(keys):
    ev=[]
    for k in keys: ev.append((OPEN,k))
    for k in reversed(keys): ev.append((CLOSE,k))
    return tuple(ev)

def invalid_cross(keys):
    ev=[]
    for k in keys: ev.append((OPEN,k))
    for k in keys: ev.append((CLOSE,k))
    return tuple(ev)

def make_examples(rng,domain,depths):
    rows=[]
    for depth in depths:
        keys=[f'{domain}_{rng.randrange(10**9):09d}_{i%max(2,depth//3)}' for i in range(depth)]
        # Proper typed LIFO sequence.
        rows.append({'events':valid_nested(keys),'expected':True,'domain':domain,'depth':depth,'kind':'VALID'})
        # Crossing close order: count/set style mechanisms can be fooled.
        rows.append({'events':invalid_cross(keys),'expected':False,'domain':domain,'depth':depth,'kind':'CROSS'})
        # Premature close/underflow.
        rows.append({'events':tuple([(CLOSE,keys[0])]+list(valid_nested(keys[:max(2,depth//2)]))),'expected':False,'domain':domain,'depth':depth,'kind':'UNDERFLOW'})
        # Unfinished state.
        rows.append({'events':tuple(list(valid_nested(keys))[:-1]),'expected':False,'domain':domain,'depth':depth,'kind':'UNFINISHED'})
        # Wrong-key close while depth remains plausible.
        wrong=f'{domain}_WRONG_{rng.randrange(10**9):09d}'
        ev=list(valid_nested(keys))
        ev[len(keys)]=(CLOSE,wrong)
        rows.append({'events':tuple(ev),'expected':False,'domain':domain,'depth':depth,'kind':'WRONG_KEY'})
        # Repeated same key must still support multiplicity.
        k=f'{domain}_REP_{rng.randrange(10**9):09d}'
        rep=tuple([(OPEN,k)]*depth+[(CLOSE,k)]*depth)
        rows.append({'events':rep,'expected':True,'domain':domain,'depth':depth,'kind':'REPEATED_KEY'})
    rng.shuffle(rows)
    return rows

seed=int(os.getenv('GITHUB_RUN_ID','260903')) ^ 0x5EC0BD
rng=random.Random(seed)
train=make_examples(rng,'TRAIN_EVT',[2,3,4,5,6])
holdout=make_examples(rng,'HOLD_EVT',[7,9,11,13])
transfer=[]
for dom,depth in [('CALLFLOW',8),('LOCKFLOW',10),('TRANSACTION',12),('SCOPEFLOW',14),('RESOURCEFLOW',16),('TAGFLOW',18)]:
    transfer.extend(make_examples(rng,dom,[depth]))

core=UnifiedYADOCoreV1(REPO)
fabric=build_fabric(core)

# 1) Existing canonical logic repeatedly receives the blind deficit.
stall_errors=[]
for i in range(21):
    try:
        fabric.execute_capability(CAP_LOGIC_V2,{
          'operation':'infer_event_state_acceptance',
          'stream_id':'SECOND-BLIND-NOVEL-MECHANISM',
          'deficit_id':'BLIND_VARIABLE_DEPTH_EVENT_STATE',
          'progress_token':{'deficit':'BLIND_VARIABLE_DEPTH_EVENT_STATE','resolution':'UNRESOLVED'},
          'prediction':'EXISTING_MECHANISM_MAY_RESOLVE',
          'cause':'SECOND_BLIND_DEFICIT_ATTEMPT',
          'payload':{'attempt':i},
        })
    except Exception as e:
        stall_errors.append(type(e).__name__+':'+str(e))
stream_state=fabric.temporal_stream_state('SECOND-BLIND-NOVEL-MECHANISM')
stall_records=[e for e in fabric.base.episodes if e.get('kind')=='TEMPORAL_STALL_SIGNAL']
stall_signal=stall_records[-1] if stall_records else {
  'mechanism_change_required':stream_state.get('mechanism_change_required'),
  'no_progress_ticks':stream_state.get('no_progress_ticks'),
  'tick_id':fabric.temporal_snapshot().get('tick_id'),
  'deficit_id':'BLIND_VARIABLE_DEPTH_EVENT_STATE',
}

# 2) Existing genome families are inspected only by identity; no required mechanism name is supplied to synthesis.
known_run=core.evolve_cognitive_code_genome()
parent_gene_ids=[x['gene_id'] for x in known_run['child']['chromosomes'].values()]
active_ids=list(core.head.get('active_capabilities',[]))
known_text=' '.join(parent_gene_ids+active_ids).upper()
known_family_has_event_stack=any(tok in known_text for tok in ('STACK','LIFO','PUSHDOWN','NESTED-EVENT','EVENT-STATE'))

previous=json.loads(PREVIOUS.read_text(encoding='utf-8')) if PREVIOUS.exists() else {}
previous_gene=previous.get('invented',{}).get('gene',{})
previous_program=previous_gene.get('operator_program',{})
previous_output_contract=previous_program.get('output')
previous_gene_contract_incompatible=previous_gene.get('meta_language_component')!='LANG-G2-GENERIC-EVENT-STATE-META-V1' and previous_output_contract!='BOOLEAN'

# 3) Shadow Genome V3 synthesizes from generic event/state primitives only after the stall.
parent_state=core.evolutionary_parent_genome()
v3=YADOEvolutionaryGenomeV3(parent_state['parent'],experience_sources=parent_state['experience'])
invented=v3.invent_event_state_operator_from_examples(
    [{'events':x['events'],'expected':x['expected']} for x in train],
    stall_signal,
    parent_gene_ids,
)
gene=invented.get('gene',{})
program=gene.get('operator_program',{})

def accuracy(program,cases):
    if not program: return 0.0
    return sum(GenericEventStateMetaLanguageV1.execute(program,x['events']) is bool(x['expected']) for x in cases)/len(cases)

train_acc=accuracy(program,train)
hold_acc=accuracy(program,holdout)
transfer_acc=accuracy(program,transfer)

ablations=[]
for a in GenericEventStateMetaLanguageV1.ablations(program) if program else []:
    h=accuracy(a['program'],holdout); t=accuracy(a['program'],transfer)
    ablations.append({'field':a['ablated_field'],'value':a['ablated_value'],'holdout_accuracy':h,'transfer_accuracy':t,'program_digest':a['program']['program_digest']})
best_ablation=max([max(x['holdout_accuracy'],x['transfer_accuracy']) for x in ablations],default=0.0)

# Non-structural baselines: count depth and unordered set memory.
count_program={'open_code':OPEN,'close_code':CLOSE,'state_mode':'COUNT','close_policy':'ANY','underflow_policy':'REJECT','mismatch_policy':'REJECT','final_policy':'EMPTY_AND_VALID'}
set_program={'open_code':OPEN,'close_code':CLOSE,'state_mode':'SET','close_policy':'REMOVE_KEY','underflow_policy':'REJECT','mismatch_policy':'REJECT','final_policy':'EMPTY_AND_VALID'}
baselines={
  'COUNT':{'holdout':accuracy(count_program,holdout),'transfer':accuracy(count_program,transfer)},
  'SET':{'holdout':accuracy(set_program,holdout),'transfer':accuracy(set_program,transfer)},
}

all_active=set(active_ids)
checks={
  'logic_parent_repeated_failure':len(stall_errors)==21 and len(set(stall_errors))==1,
  'temporal_stall_reached_20':stream_state.get('no_progress_ticks')==20,
  'temporal_requests_mechanism_change':stream_state.get('mechanism_change_required') is True and stall_signal.get('mechanism_change_required') is True,
  'known_genome_and_active_family_not_matching':known_family_has_event_stack is False,
  'previous_novel_gene_contract_incompatible':previous_gene_contract_incompatible is True,
  'shadow_v3_self_synthesizes_gene':invented.get('status')=='SELF_SYNTHESIZED_SHADOW_GENE' and gene.get('novel_gene') is True,
  'new_gene_not_parent_gene':gene.get('gene_id') not in set(parent_gene_ids),
  'new_gene_not_active_capability':gene.get('gene_id') not in all_active,
  'new_gene_distinct_from_previous_novel_gene':gene.get('gene_id')!=previous_gene.get('gene_id'),
  'new_meta_language_distinct_from_relational':gene.get('meta_language_component')!='LANG-G2-GENERIC-RELATIONAL-STATE-META-V1',
  'train_exact':train_acc==1.0,
  'fresh_deeper_holdout_exact':hold_acc==1.0,
  'cross_domain_transfer_exact':transfer_acc==1.0,
  'structural_ablation_causes_drop':best_ablation<1.0,
  'count_and_set_baselines_fail':all(v['holdout']<1.0 and v['transfer']<1.0 for v in baselines.values()),
  'gene_remains_shadow':gene.get('promotion_state')=='SHADOW_ONLY',
  'automatic_promotion_false':YADOEvolutionaryGenomeV3.component().get('automatic_canonical_promotion') is False,
  'formal_generation_unchanged':core.head.get('generation_id')=='G2_CANDIDATE_TRCG_V1',
  'frontier_unchanged':core.head.get('current_frontier')=='KERNEL_G2_RAW_REPRESENTATION_V5_CANONICAL_ADMISSION_V1',
  'g3_not_started':core.head.get('g3_genesis_performed') is False,
}
status='PASS_SHADOW_G2_SECOND_BLIND_NOVEL_MECHANISM_INVENTION_V1' if all(checks.values()) else 'WITHHOLD_G2_SECOND_BLIND_NOVEL_MECHANISM_INVENTION_V1'
report={
  'schema':'yado.g2.second_blind_novel_mechanism_invention.v1',
  'status':status,
  'checks':checks,
  'blind_deficit':{
    'deficit_id':'BLIND_VARIABLE_DEPTH_EVENT_STATE',
    'training_case_count':len(train),
    'holdout_case_count':len(holdout),
    'transfer_case_count':len(transfer),
    'holdout_depth_range':[min(x['depth'] for x in holdout),max(x['depth'] for x in holdout)],
    'transfer_domains':sorted({x['domain'] for x in transfer}),
    'domain_specific_operator_name_given_to_synthesizer':False,
  },
  'parent_failure':{
    'logic_error_signature':stall_errors[0] if stall_errors else None,
    'logic_failure_count':len(stall_errors),
    'known_shadow_gene_ids':parent_gene_ids,
    'known_family_has_event_stack':known_family_has_event_stack,
    'previous_novel_gene_id':previous_gene.get('gene_id'),
    'previous_novel_gene_output_contract':previous_output_contract,
  },
  'temporal_stall':{'stream_state':stream_state,'stall_signal':stall_signal,'temporal_snapshot':fabric.temporal_snapshot()},
  'invented':invented,
  'fitness':{
    'train_accuracy':train_acc,
    'holdout_accuracy':hold_acc,
    'cross_domain_transfer_accuracy':transfer_acc,
    'best_structural_ablation_accuracy':best_ablation,
    'baselines':baselines,
  },
  'ablations':ablations,
  'meta_language':GenericEventStateMetaLanguageV1.component(),
  'controller_v3':YADOEvolutionaryGenomeV3.component(),
  'canonical_mutation':False,'architecture_mutation':False,
  'generation_transition':False,'g3_genesis_performed':False,
  'semantic_boundary':'SECOND BLIND SHADOW TEST ON A DIFFERENT DEFICIT FAMILY. SYNTHESIS RECEIVES IO EXAMPLES AND GENERIC EVENT/STATE PRIMITIVES, NOT A STACK/NESTING/PUSHDOWN OPERATOR NAME. SUCCESS DOES NOT PROMOTE THE GENE OR PROVE OPEN-ENDED SELF-EVOLUTION.'
}
report['receipt_sha256']=digest(report)
out=REPO/'candidates/kernel-self-generated/g2-second-blind-novel-mechanism-invention-v1.json'
out.parent.mkdir(parents=True,exist_ok=True)
out.write_text(json.dumps(report,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')
print(json.dumps({
  'status':status,'checks':checks,
  'invented_gene_id':gene.get('gene_id'),
  'invented_program':program,
  'fitness':report['fitness'],
  'temporal_no_progress_ticks':stream_state.get('no_progress_ticks'),
  'receipt_sha256':report['receipt_sha256'],
},indent=2,sort_keys=True,default=str))
if status!='PASS_SHADOW_G2_SECOND_BLIND_NOVEL_MECHANISM_INVENTION_V1':
    raise SystemExit(2)
