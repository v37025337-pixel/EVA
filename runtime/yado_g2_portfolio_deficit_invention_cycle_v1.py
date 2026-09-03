from __future__ import annotations
from pathlib import Path
import copy,hashlib,json,os,random,sys

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
PKG=ROOT/'yado_rc8_v36'
sys.path[:0]=[str(ROOT),str(PKG)]

from yado_unified_core_v1 import UnifiedYADOCoreV1
from yado_g2_typed_recurrent_capability_graph_runtime_v1 import G2TypedRecurrentCapabilityGraphRuntimeV1
from yado_g2_unified_execution_fabric_v3 import G2UnifiedExecutionFabricV3
from yado_bounded_capability_router_v1 import BoundedCapabilityRouterLearnerV1
from yado_conjunctive_rule_inducer_v1 import ConjunctiveRuleInducerV1
from yado_g2_adaptive_evolution_controller_v1 import YADOAdaptiveEvolutionControllerV1
from yado_generic_weighted_state_meta_language_v1 import GenericWeightedStateMetaLanguageV1

CAP_CONJ='ALG-CONJUNCTIVE-RULE-INDUCER-V1'
CAP_REL='ALG-BOUNDED-DNF-RELATION-POLICY-INDUCER-V1'
CAP_BUD='ALG-BUDGETED-STAGE-POLICY-V1'
CAP_RES='RESOURCE-PORTFOLIO-V1'
CAP_LOGIC_V2='ALG-G2-BUDGET-ADAPTIVE-COMPOSITIONAL-LOGIC-V2'

def canon(o): return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def digest(o): return hashlib.sha256(canon(o).encode()).hexdigest()

def desc(cap):
    d={'budget_limited':False,'quota_limited':False,'external_evidence_needed':False,'relation_needed':False,'disjunction_needed':False}
    if cap==CAP_BUD:d['budget_limited']=True
    elif cap==CAP_RES:d['external_evidence_needed']=True
    elif cap==CAP_REL:d['relation_needed']=True
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
    scalar=ConjunctiveRuleInducerV1.synthesize('ADAPTIVE_CYCLE_SCALAR','LOGIC',rows,min_support=2,max_rules=12)
    class Rel:
        def execute(self,x):return 'ALLOW' if x.get('allow') else 'DENY'
    return G2UnifiedExecutionFabricV3(G2TypedRecurrentCapabilityGraphRuntimeV1(core.architecture,router,scalar,Rel(),core.portfolio))

def rel_truth(edges,start):
    state={start}
    for _ in range(512):
        nxt=state|{b for a,b in edges if a in state}
        if nxt==state:break
        state=nxt
    return tuple(sorted(state,key=lambda x:(str(type(x)),str(x))))

def rel_case(rng,n,domain):
    token=f'{rng.randrange(10**12):012d}'
    nodes=[f'{domain}_{token}_{i}' for i in range(n)]
    e=[(nodes[i],nodes[i+1]) for i in range(n-1)]
    e.append((nodes[n//2],f'{domain}_{token}_B'))
    e.append((f'{domain}_{token}_D0',f'{domain}_{token}_D1'))
    rng.shuffle(e)
    return {'relation':tuple(e),'start':nodes[0],'expected':rel_truth(e,nodes[0]),'domain':domain}

OPEN='Q';CLOSE='R'
def evt_cases(rng,domain,depths):
    out=[]
    for d in depths:
        keys=[f'{domain}_{rng.randrange(10**12):012d}_{i%max(2,d//4)}' for i in range(d)]
        valid=tuple([(OPEN,k) for k in keys]+[(CLOSE,k) for k in reversed(keys)])
        cross=tuple([(OPEN,k) for k in keys]+[(CLOSE,k) for k in keys])
        out.append({'events':valid,'expected':True,'domain':domain})
        out.append({'events':cross,'expected':False,'domain':domain})
        out.append({'events':tuple(list(valid)[:-1]),'expected':False,'domain':domain})
        out.append({'events':tuple([(CLOSE,keys[0])]+list(valid)),'expected':False,'domain':domain})
        wrong=f'{domain}_WRONG_{rng.randrange(10**12):012d}'
        ev=list(valid);ev[len(keys)]=(CLOSE,wrong)
        out.append({'events':tuple(ev),'expected':False,'domain':domain})
        k=f'{domain}_REP_{rng.randrange(10**12):012d}'
        out.append({'events':tuple([(OPEN,k)]*d+[(CLOSE,k)]*d),'expected':True,'domain':domain})
    return out

def weighted_truth(edges,start):
    dist={start:0}
    for _ in range(1024):
        changed=False
        nxt=dict(dist)
        for a,b,w in edges:
            if a not in dist:continue
            cand=dist[a]+w
            if b not in nxt or cand<nxt[b]:
                nxt[b]=cand;changed=True
        dist=nxt
        if not changed:break
    return tuple(sorted(((k,dist[k]) for k in dist),key=lambda kv:(str(type(kv[0])),str(kv[0]))))

def weighted_case(rng,n,domain):
    token=f'{rng.randrange(10**12):012d}'
    nodes=[f'{domain}_{token}_{i}' for i in range(n)]
    edges=[]
    for i in range(n-1):
        edges.append((nodes[i],nodes[i+1],rng.randint(2,9)))
    # Alternative multi-hop and skip edges force cumulative min-relaxation.
    for i in range(0,n-3,3):
        edges.append((nodes[i],nodes[i+2],rng.randint(7,14)))
        edges.append((nodes[i+1],nodes[i+3],rng.randint(3,7)))
    # Positive back edge/cycle and disconnected weighted decoy.
    if n>=8:edges.append((nodes[-1],nodes[n//3],rng.randint(11,17)))
    edges.append((f'{domain}_{token}_D0',f'{domain}_{token}_D1',rng.randint(1,4)))
    rng.shuffle(edges)
    return {'relation':tuple(edges),'start':nodes[0],'expected':weighted_truth(edges,nodes[0]),'domain':domain,'node_count':n}

def accuracy(program,cases):
    if not program:return 0.0
    ok=0
    for x in cases:
        try:got=GenericWeightedStateMetaLanguageV1.execute(program,x['relation'],x['start'])
        except Exception:got=None
        ok+=(got==x['expected'])
    return ok/len(cases)

seed=int(os.getenv('GITHUB_RUN_ID','260903')) ^ 0x3A7D17
rng=random.Random(seed)
core=UnifiedYADOCoreV1(REPO)
fabric=build_fabric(core)
controller=YADOAdaptiveEvolutionControllerV1(REPO)

# Existing two-gene portfolio is rebuilt from fresh tasks without naming gene IDs.
existing_selection=[
  {'task_id':'REUSE_REL','input_contract':'RELATION_START_TO_STATE','cases':[rel_case(rng,n,'REUSE_REL') for n in [31,33,35,37]]},
  {'task_id':'REUSE_EVT','input_contract':'EVENT_SEQUENCE_TO_BOOLEAN','cases':evt_cases(rng,'REUSE_EVT',[35,39,43])},
]
portfolio=controller.build_existing_portfolio(existing_selection)

# New deficit family: neither accumulated gene supports this input/output contract.
train=[weighted_case(rng,n,'TRAIN_W') for n in [6,7,8,9,10,11,12,13,14,15]]
deficit_task={'task_id':'NEW_WEIGHTED_DEFICIT','input_contract':YADOAdaptiveEvolutionControllerV1.WEIGHTED_CONTRACT,'cases':train}
reuse=controller.attempt_reuse(portfolio,deficit_task)

# Temporal no-progress must occur before invention.
stall_errors=[]
for i in range(21):
    try:
        fabric.execute_capability(CAP_LOGIC_V2,{
          'operation':'infer_weighted_state_map',
          'stream_id':'ADAPTIVE-PORTFOLIO-DEFICIT',
          'deficit_id':'BLIND_WEIGHTED_STATE_RELAXATION',
          'progress_token':{'deficit':'BLIND_WEIGHTED_STATE_RELAXATION','resolution':'UNRESOLVED'},
          'prediction':'EXISTING_PORTFOLIO_MAY_RESOLVE',
          'cause':'REUSE_PORTFOLIO_ATTEMPT',
          'payload':{'attempt':i,'reuse_best_score':reuse['best_score']},
        })
    except Exception as e:
        stall_errors.append(type(e).__name__+':'+str(e))
stream=fabric.temporal_stream_state('ADAPTIVE-PORTFOLIO-DEFICIT')
stalls=[e for e in fabric.base.episodes if e.get('kind')=='TEMPORAL_STALL_SIGNAL']
stall_signal=stalls[-1] if stalls else {
  'mechanism_change_required':stream.get('mechanism_change_required'),
  'no_progress_ticks':stream.get('no_progress_ticks'),
  'tick_id':fabric.temporal_snapshot().get('tick_id'),
  'deficit_id':'BLIND_WEIGHTED_STATE_RELAXATION',
}

parent_state=core.evolutionary_parent_genome()
known=core.evolve_cognitive_code_genome()
parent_gene_ids=[x['gene_id'] for x in known['child']['chromosomes'].values()]

invented=controller.invent_weighted_gene(
    [{'relation':x['relation'],'start':x['start'],'expected':x['expected']} for x in train],
    stall_signal,parent_gene_ids
)
gene=invented.get('gene',{})
program=gene.get('operator_program',{})

holdout=[weighted_case(rng,n,'HOLD_W') for n in [17,19,21,23,25,27]]
transfer=[]
for dom,n in [('SUPPLY_COST',18),('LATENCY_GRAPH',20),('RISK_GRAPH',22),('ENERGY_GRAPH',24),('RESOURCE_COST',26),('ROUTE_COST',28)]:
    transfer.append(weighted_case(rng,n,dom))
hold_acc=accuracy(program,holdout)
transfer_acc=accuracy(program,transfer)
ablations=[]
for a in GenericWeightedStateMetaLanguageV1.ablations(program) if program else []:
    h=accuracy(a['program'],holdout);t=accuracy(a['program'],transfer)
    ablations.append({'field':a['ablated_field'],'value':a['ablated_value'],'holdout_accuracy':h,'transfer_accuracy':t})
best_ablation=max([max(x['holdout_accuracy'],x['transfer_accuracy']) for x in ablations],default=0.0)

extended=controller.expand_portfolio(portfolio,gene,'NEW_WEIGHTED_DEFICIT')
h1=controller.inherit_portfolio(extended,'H1')
h2=controller.inherit_portfolio(h1,'H2')

# H2 must preserve old capabilities and the new one on unseen follow-up tasks.
followups=[
  {'task_id':'FOLLOW_REL','input_contract':'RELATION_START_TO_STATE','cases':[rel_case(rng,n,'FOLLOW_REL') for n in [39,41,43,45]]},
  {'task_id':'FOLLOW_EVT','input_contract':'EVENT_SEQUENCE_TO_BOOLEAN','cases':evt_cases(rng,'FOLLOW_EVT',[47,51,55])},
  {'task_id':'FOLLOW_WEIGHTED','input_contract':YADOAdaptiveEvolutionControllerV1.WEIGHTED_CONTRACT,'cases':[weighted_case(rng,n,'FOLLOW_W') for n in [29,31,33,35,37,39]]},
]
follow_eval={t['task_id']:controller.evaluate_portfolio(h2,t) for t in followups}

# Remove only the newly invented gene from H2; weighted follow-up must fail while old task families remain available.
reduced=copy.deepcopy(h2)
reduced['selected_genes']=[x for x in reduced['selected_genes'] if x['gene'].get('gene_digest')!=gene.get('gene_digest')]
weighted_removed=controller.evaluate_portfolio(reduced,next(t for t in followups if t['task_id']=='FOLLOW_WEIGHTED'))['best_score']
old_rel_reduced=controller.evaluate_portfolio(reduced,next(t for t in followups if t['task_id']=='FOLLOW_REL'))['best_score']
old_evt_reduced=controller.evaluate_portfolio(reduced,next(t for t in followups if t['task_id']=='FOLLOW_EVT'))['best_score']

checks={
  'reuse_attempt_preceded_invention':controller.events and controller.events[0]['event']=='EXISTING_PORTFOLIO_BUILT' and controller.events[1]['event']=='REUSE_ATTEMPT',
  'existing_portfolio_has_two_genes':portfolio.get('selected_gene_count')==2,
  'existing_portfolio_insufficient_for_new_contract':reuse.get('verdict')=='PORTFOLIO_INSUFFICIENT' and reuse.get('best_score')<1.0,
  'temporal_stall_reached_20':stream.get('no_progress_ticks')==20,
  'temporal_requests_mechanism_change':stream.get('mechanism_change_required') is True and stall_signal.get('mechanism_change_required') is True,
  'new_gene_self_synthesized_after_stall':invented.get('status')=='SELF_SYNTHESIZED_SHADOW_GENE' and gene.get('novel_gene') is True,
  'new_gene_not_parent_gene':gene.get('gene_id') not in set(parent_gene_ids),
  'new_gene_not_preexisting_portfolio':gene.get('gene_digest') not in {x['gene'].get('gene_digest') for x in portfolio.get('selected_genes',[])},
  'fresh_weighted_holdout_exact':hold_acc==1.0,
  'cross_domain_weighted_transfer_exact':transfer_acc==1.0,
  'structural_ablation_causes_drop':best_ablation<1.0,
  'expanded_portfolio_has_three_genes':extended.get('selected_gene_count')==3,
  'h1_exact_three_gene_inheritance':h1.get('selected_gene_count')==3 and [x['gene']['gene_digest'] for x in h1['selected_genes']]==[x['gene']['gene_digest'] for x in extended['selected_genes']],
  'h2_exact_three_gene_inheritance':h2.get('selected_gene_count')==3 and [x['gene']['gene_digest'] for x in h2['selected_genes']]==[x['gene']['gene_digest'] for x in h1['selected_genes']],
  'h2_retains_all_three_task_families':all(v['best_score']==1.0 for v in follow_eval.values()),
  'new_gene_removal_breaks_only_new_family':weighted_removed<1.0 and old_rel_reduced==1.0 and old_evt_reduced==1.0,
  'automatic_canonical_promotion_false':extended.get('automatic_canonical_promotion') is False,
  'formal_generation_unchanged':core.head.get('generation_id')=='G2_CANDIDATE_TRCG_V1',
  'frontier_unchanged':core.head.get('current_frontier')=='KERNEL_G2_RAW_REPRESENTATION_V5_CANONICAL_ADMISSION_V1',
  'g3_not_started':core.head.get('g3_genesis_performed') is False,
}
status='PASS_SHADOW_G2_PORTFOLIO_DEFICIT_INVENTION_CYCLE_V1' if all(checks.values()) else 'WITHHOLD_G2_PORTFOLIO_DEFICIT_INVENTION_CYCLE_V1'

report={
  'schema':'yado.g2.portfolio_deficit_invention_cycle.v1',
  'status':status,
  'controller':YADOAdaptiveEvolutionControllerV1.component(),
  'controller_events':controller.events,
  'preexisting_portfolio':portfolio,
  'reuse_attempt':reuse,
  'temporal_stall':{'stream_state':stream,'stall_signal':stall_signal,'error_count':len(stall_errors)},
  'invented':invented,
  'fresh_fitness':{
    'holdout_accuracy':hold_acc,'cross_domain_transfer_accuracy':transfer_acc,
    'best_structural_ablation_accuracy':best_ablation,
  },
  'ablations':ablations,
  'extended_portfolio':extended,'h1':h1,'h2':h2,
  'followup_eval':follow_eval,
  'new_gene_removal':{
    'weighted_followup_score':weighted_removed,
    'relational_followup_score':old_rel_reduced,
    'event_followup_score':old_evt_reduced,
  },
  'checks':checks,
  'canonical_mutation':False,'architecture_mutation':False,
  'generation_transition':False,'g3_genesis_performed':False,
  'semantic_boundary':'BOUNDED SHADOW ADAPTIVE CYCLE: REUSE OF THE EXISTING TWO-GENE PORTFOLIO IS ATTEMPTED FIRST; A FAILED NEW CONTRACT PLUS TEMPORAL STALL OPENS A GENERIC WEIGHTED-STATE INVENTION PATH; THE FRESH-CAUSAL WINNER IS ADDED AS A THIRD SHADOW GENE AND INHERITED THROUGH H1/H2. THIS DOES NOT PROVE OPEN-ENDED SELF-EVOLUTION.'
}
report['receipt_sha256']=digest(report)
out=REPO/'candidates/kernel-self-generated/g2-portfolio-deficit-invention-cycle-v1.json'
out.parent.mkdir(parents=True,exist_ok=True)
out.write_text(json.dumps(report,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')
print(json.dumps({
  'status':status,
  'controller_events':controller.events,
  'preexisting_gene_count':portfolio.get('selected_gene_count'),
  'reuse_attempt':reuse,
  'invented_gene_id':gene.get('gene_id'),
  'invented_program':program,
  'fresh_fitness':report['fresh_fitness'],
  'extended_gene_count':extended.get('selected_gene_count'),
  'followup_eval':follow_eval,
  'new_gene_removal':report['new_gene_removal'],
  'checks':checks,
  'receipt_sha256':report['receipt_sha256'],
},indent=2,sort_keys=True,default=str))
if status!='PASS_SHADOW_G2_PORTFOLIO_DEFICIT_INVENTION_CYCLE_V1':raise SystemExit(2)
